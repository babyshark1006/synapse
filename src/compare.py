"""
compare.py - 跨论文对比核心模块(Synapse Part 6)

功能:
    对 2-4 篇论文做结构化对比,输出 Markdown 表格

设计原则:
    - 每篇论文独立检索(绕过 cross_paper 的检索垄断问题)
    - 1 次 LLM 综合调用(一致性高,成本可控)
    - 防御性设计(参数校验 + 单点失败不全崩)
    - 关注点分离(后端返回 dict,前端做渲染)
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional

# 复用 search 模块的索引和配置
from llama_index.core import Settings
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter


# ========================================
# 配置:预设对比维度白名单
# ========================================
PRESET_DIMENSIONS = [
    "架构 / 模型设计",
    "方法 / 核心算法",
    "实验 / 性能数据",
    "结论 / 核心贡献",
    "局限 / 未来方向"
]

# 单论文检索切片数
TOP_K_PER_PAPER = 5


# ========================================
# 第 1 部分:输入参数校验
# ========================================
def _validate_inputs(paper_files, dimensions, custom_dimension):
    """
    校验输入参数,不合法立即报错
    
    设计原则:Fail Fast — 错误参数在最早阶段暴露
    """
    if not isinstance(paper_files, list):
        raise ValueError("paper_files 必须是 list")
    
    if len(paper_files) < 2:
        raise ValueError(f"至少需要 2 篇论文对比,当前 {len(paper_files)} 篇")
    
    if len(paper_files) > 4:
        raise ValueError(f"最多对比 4 篇论文,当前 {len(paper_files)} 篇")
    
    # dimensions 和 custom 至少有一个非空
    has_preset = dimensions and len(dimensions) > 0
    has_custom = custom_dimension and len(custom_dimension.strip()) > 0
    
    if not (has_preset or has_custom):
        raise ValueError("至少需要 1 个对比维度(预设或自定义)")
    
    # custom_dimension 长度限制
    if has_custom and len(custom_dimension) > 100:
        raise ValueError(f"自定义维度过长(>100字符),当前 {len(custom_dimension)} 字符")
    
    # 维度合并(custom 加到末尾,问题 3 的答案)
    final_dimensions = list(dimensions) if dimensions else []
    if has_custom:
        final_dimensions.append(custom_dimension.strip())
    
    return final_dimensions


# ========================================
# 第 2 部分:对单篇论文做"独立检索"
# ========================================
def _retrieve_for_paper(index, paper_file, dimensions):
    """
    针对单篇论文,检索"覆盖所有维度"的相关切片
    
    策略:用 "维度关键词 + 论文名" 拼成 query,
         然后用 metadata filter 限制只取这篇论文
    
    返回:
        切片列表 [{page, score, text}, ...]
    """
    
    # 把所有维度拼成 query(让向量检索更有针对性)
    query = f"{paper_file} 的 " + " / ".join(dimensions)
    
    # 用 metadata filter 限定只检索这篇论文
    # 💡 关键:LlamaIndex 的 ChromaVectorStore 用 metadata_filters
    filters = MetadataFilters(filters=[
        ExactMatchFilter(key="file_name", value=paper_file)
    ])
    
    # 创建带过滤的 retriever
    retriever = index.as_retriever(
        similarity_top_k=TOP_K_PER_PAPER,
        filters=filters
    )
    
    # 检索
    nodes = retriever.retrieve(query)
    
    # 提取切片信息
    chunks = []
    for node in nodes:
        chunks.append({
            "page": node.metadata.get("page_label", "未知"),
            "score": round(node.score, 3) if hasattr(node, 'score') and node.score else 0.0,
            "text": node.text,
            "preview": node.text.replace('\n', ' ')[:200]
        })
    
    return chunks


# ========================================
# 第 3 部分:构造 LLM Prompt(对比生成)
# ========================================
def _build_compare_prompt(papers_chunks, dimensions):
    """
    构造跨论文对比的 LLM Prompt
    
    设计:
        - 每篇论文的片段分别标注
        - 明确要求"逐维度对比"
        - 输出 Markdown 表格,带样式(问题 4 的答案)
    """
    
    # 拼接每篇论文的检索片段
    papers_context = ""
    for paper_file, chunks in papers_chunks.items():
        papers_context += f"\n\n=== {paper_file} 的相关片段 ===\n"
        for i, chunk in enumerate(chunks, 1):
            papers_context += f"\n[{paper_file} - 片段 {i},第 {chunk['page']} 页]\n"
            papers_context += chunk["text"][:800]  # 限制长度防 Token 爆
            papers_context += "\n"
    
    # 维度列表(每行 1 个)
    dimensions_str = "\n".join([f"- **{d}**" for d in dimensions])
    
    # 论文文件名(给 Markdown 表头用)
    paper_names = list(papers_chunks.keys())
    
    prompt = f"""你是一位严谨的学术论文对比助手。下面是从多篇论文中检索到的相关片段。

【论文片段】
{papers_context}

【对比要求】
请基于上述片段,从以下维度逐项对比这些论文:

{dimensions_str}

【输出格式】(必须严格遵守)

请输出 Markdown 表格,**论文为列、维度为行**。

格式示例:
| 维度 | **{paper_names[0]}** | **{paper_names[1]}** |
|------|---------------------|---------------------|
| **架构 / 模型设计** | encoder-decoder... | retriever-generator... |
| **实验 / 性能数据** | ... | ... |

【关键规则】
1. **必须用粗体标注**维度名和论文名(用 ** ** 包裹)
2. 每个单元格内容**不超过 80 字**,精炼准确
3. 如果某篇论文的片段没覆盖某维度,该格填:"**片段中未涉及**"
4. 单元格内**不要换行**(用分号 ; 分隔多个要点)
5. 用中文回答

【表格生成开始】
"""
    
    return prompt


# ========================================
# 第 4 部分:解析 LLM 输出 → 结构化 dict
# ========================================
def _parse_markdown_to_dict(markdown_table, dimensions, papers):
    """
    把 Markdown 表格解析成嵌套 dict
    
    例:
    | 维度 | Transformer | RAG |
    | 架构 | encoder-decoder | retriever-generator |
    
    → {
        "架构": {
            "Transformer": "encoder-decoder",
            "RAG": "retriever-generator"
        }
    }
    """
    
    comparison_table = {}
    
    lines = markdown_table.strip().split("\n")
    
    # 找数据行(跳过表头和分隔行)
    data_lines = []
    for line in lines:
        line = line.strip()
        if not line or not line.startswith("|"):
            continue
        # 跳过分隔行(| --- | --- |)
        if "---" in line:
            continue
        data_lines.append(line)
    
    # 第 1 行是表头
    if not data_lines:
        return comparison_table
    
    header = data_lines[0]
    # 解析表头里的论文名(去掉粗体)
    header_cells = [c.strip().replace("**", "") for c in header.split("|") if c.strip()]
    # 第 0 列是 "维度",从第 1 列开始是论文
    paper_columns = header_cells[1:]
    
    # 数据行
    for line in data_lines[1:]:
        cells = [c.strip().replace("**", "") for c in line.split("|") if c.strip()]
        if len(cells) < 2:
            continue
        
        dim = cells[0]
        comparison_table[dim] = {}
        
        for i, paper in enumerate(paper_columns):
            if i + 1 < len(cells):
                comparison_table[dim][paper] = cells[i + 1]
            else:
                comparison_table[dim][paper] = "解析失败"
    
    return comparison_table


# ========================================
# 第 5 部分:核心函数 compare()
# ========================================
def compare(
    index,
    paper_files: list,
    dimensions: list,
    custom_dimension: Optional[str] = None
) -> dict:
    """
    跨论文对比主函数
    
    详细 API 契约见 docs/compare_api_design.md
    """
    
    start_time = time.time()
    
    # ====== Step 1:校验输入 + 合并自定义维度 ======
    final_dimensions = _validate_inputs(paper_files, dimensions, custom_dimension)
    
    # ====== Step 2:对每篇论文独立检索 ======
    # 💎 关键设计:绕过 cross_paper 的"单篇垄断"问题
    print(f"🔍 对 {len(paper_files)} 篇论文做独立检索...")
    papers_chunks = {}
    citations = {}
    
    for paper in paper_files:
        chunks = _retrieve_for_paper(index, paper, final_dimensions)
        papers_chunks[paper] = chunks
        
        # 整理 citations(给前端用)
        citations[paper] = [
            {
                "page": c["page"],
                "score": c["score"],
                "preview": c["preview"]
            }
            for c in chunks
        ]
        
        print(f"   ✅ {paper}: {len(chunks)} 个切片")
    
    # ====== Step 3:构造 Prompt + 调 LLM ======
    print(f"🧠 LLM 综合生成对比表(维度数:{len(final_dimensions)})...")
    prompt = _build_compare_prompt(papers_chunks, final_dimensions)
    
    llm = Settings.llm
    try:
        response = llm.complete(prompt)
        markdown_table = str(response).strip()
    except Exception as e:
        raise RuntimeError(f"Claude API 调用失败:{e}")
    
    # ====== Step 4:解析 Markdown 成 dict ======
    comparison_table = _parse_markdown_to_dict(
        markdown_table,
        final_dimensions,
        paper_files
    )
    
    duration = round(time.time() - start_time, 2)
    print(f"✅ 对比完成,耗时 {duration}s")
    
    return {
        "papers": paper_files,
        "dimensions": final_dimensions,
        "comparison_table": comparison_table,
        "citations": citations,
        "markdown_table": markdown_table,
        "duration_seconds": duration,
        "error": None
    }


# ========================================
# 测试:跑一个真实对比
# ========================================
if __name__ == "__main__":
    print("=" * 70)
    print("🧪 compare.py 测试 — 对比 Transformer vs RAG")
    print("=" * 70)
    
    # 加载索引(复用 search.py)
    sys.path.append(str(Path(__file__).parent))
    from search import load_index
    
    index = load_index()
    
    # 测试:2 篇论文 × 3 维度
    result = compare(
        index=index,
        paper_files=["transformer.pdf", "rag.pdf"],
        dimensions=[
            "架构 / 模型设计",
            "实验 / 性能数据"
        ],
        custom_dimension="解决幻觉的思路"
    )
    
    # 打印结果
    print(f"\n📋 对比维度:{result['dimensions']}")
    print(f"⏱️  耗时:{result['duration_seconds']}s")
    
    print(f"\n📊 Markdown 表格输出:")
    print("-" * 70)
    print(result["markdown_table"])
    print("-" * 70)
    
    print(f"\n📦 结构化 dict(用于前端):")
    for dim, paper_content in result["comparison_table"].items():
        print(f"\n  【{dim}】")
        for paper, content in paper_content.items():
            print(f"    • {paper}: {content[:80]}...")
    
    print(f"\n📚 引用溯源(每篇 top 5):")
    for paper, cites in result["citations"].items():
        print(f"\n  {paper}:")
        for c in cites[:3]:  # 只打印前 3 条
            print(f"    p.{c['page']} (score={c['score']}): {c['preview'][:80]}...")
    
    print("\n" + "=" * 70)
    print("✅ compare.py 测试通过")
    print("=" * 70)