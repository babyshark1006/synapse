"""
search.py - RAG 查询脚本(Synapse 第一次开口)

功能:
    用户输入问题 → 向量化 → 检索 → 生成答案 → 打印
    这是 RAG 系统的"查询阶段"

使用:
    python src/search.py
    
输入:
    在终端里输入问题(中英文都行)
    
输出:
    Claude 基于论文生成的答案 + 引用来源(页码)

设计决策:
    - top_k=5(检索 5 个最相似切片,业界 baseline)
    - Claude Sonnet 4.5(学术推理需要中等复杂度模型)
    - Prompt 强约束(只基于检索内容、不编造、标注引用)
    - 命令行交互(MVP 阶段先不做 UI)
"""

# ========================================
# 第 1 部分:导入工具库
# ========================================
import os
from dotenv import load_dotenv

# LlamaIndex 核心
from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    Settings,
)
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.anthropic import Anthropic
from llama_index.vector_stores.chroma import ChromaVectorStore

# ChromaDB 本体
import chromadb


# ========================================
# 第 2 部分:加载配置
# ========================================
load_dotenv()

# Fail Fast:检查必需的 API key
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("❌ 缺少 OPENAI_API_KEY,请检查 .env")
if not os.getenv("ANTHROPIC_API_KEY"):
    raise ValueError("❌ 缺少 ANTHROPIC_API_KEY,请检查 .env")

# 路径配置(和 ingest.py 一致)
CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "synapse_papers"

# 检索数量(top_k)
TOP_K = 5


# ========================================
# 第 3 部分:配置 LlamaIndex 全局参数
# ========================================
# Embedding 模型必须和 ingest.py 用同一个,否则向量不兼容
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

# 💡 LLM 用 Claude Sonnet
# temperature=0.1:低温度,答案更确定、更不容易编造
# max_tokens=1024:限制答案长度,省 token
Settings.llm = Anthropic(
    model="claude-sonnet-4-20250514",
    temperature=0.1,
    max_tokens=1024
)


# ========================================
# 第 4 部分:加载已有的 ChromaDB
# ========================================
def load_index():
    """加载 ingest.py 之前建好的索引"""
    
    # 连接本地 ChromaDB
    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    
    # 拿到集合(必须已存在,否则报错提示去跑 ingest.py)
    try:
        chroma_collection = chroma_client.get_collection(name=COLLECTION_NAME)
    except Exception:
        raise RuntimeError(
            f"❌ 找不到 collection '{COLLECTION_NAME}'。\n"
            f"   请先运行:python src/ingest.py 建立索引"
        )
    
    # 包装成 LlamaIndex 能用的格式
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # 💡 关键:从已有的向量库加载索引(不是重新建)
    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        storage_context=storage_context,
    )
    
    return index


# ========================================
# 第 5 部分:核心查询函数
# ========================================

def ask(index, question):
    """
    向 Synapse 提问,返回结构化数据(dict)
    
    返回格式:
    {
        "answer": "答案文本",
        "citations": [
            {
                "file_name": "transformer.pdf",
                "page": "5",
                "score": 0.85,
                "text_preview": "原文前 200 字..."
            },
            ...
        ]
    }
    
    设计说明:
    - 返回 dict 而不是直接 print
    - 这样终端和 UI 都能用同一个核心逻辑
    - "输出格式与展示分离"原则
    """
    
    from llama_index.core import PromptTemplate
    
    # Prompt 模板(不变)
    custom_prompt = PromptTemplate(
        """你是一位严谨的学术论文阅读助手 Synapse。

下面是从论文中检索到的相关片段,请基于这些片段回答用户的问题。

【检索到的论文片段】
{context_str}

【用户问题】
{query_str}

【核心回答规则】
1. 只基于上述论文片段回答,绝对不能编造或引用片段外的内容
2. 答案中明确标注每个观点来自哪篇论文(用"根据 X 论文..."句式)
3. 答案要精炼、准确、专业,使用学术语气
4. 用中文回答(除非问题是英文)

【跨论文场景指引】(重要)
如果检索片段来自多篇论文:
- 主动对比 / 整合多篇论文的观点
- 如果问题涉及 N 篇论文,但片段只覆盖了其中部分(例如 N=3,片段只有 2 篇):
  → **部分回答可回答的内容,并明确指出未在片段中涉及的论文**
- 不要因为"缺一篇"就完全拒答
- 例:问"Transformer / RAG / ReAct 各负责什么角色?",片段只有 Transformer 和 RAG:
  ✅ 正确:"根据 Transformer 论文...; 根据 RAG 论文...; 关于 ReAct 的内容,当前检索片段中未涉及。"
  ❌ 错误:"基于现有片段无法确定。"(完全拒答)

【拒答规则】
- 只在"完全没有任何相关片段"时才拒答
- 如果片段涉及部分内容,优先"部分回答 + 标注未覆盖部分"
- 拒答时用:"基于现有片段无法确定"


【你的回答】
"""
    )
    
    # 创建查询引擎
    query_engine = index.as_query_engine(
        similarity_top_k=TOP_K,
        text_qa_template=custom_prompt,
    )
    
    # 执行 RAG
    response = query_engine.query(question)
    
    # 把 LlamaIndex 的 Response 对象转成结构化 dict
    citations = []
    for source in response.source_nodes:
        citations.append({
            "file_name": source.metadata.get('file_name', '未知'),
            "page": source.metadata.get('page_label', '未知'),
            "score": source.score if hasattr(source, 'score') else None,
            "text_preview": source.text.replace('\n', ' ')[:200]
        })
    
    return {
        "answer": response.response,
        "citations": citations
    }


# ========================================
# 第 6 部分:打印结果(含引用溯源)
# ========================================

def print_response(result):
    """
    终端版渲染 — 把 ask() 返回的 dict 漂亮地打印出来
    
    注意:这个函数"只负责打印",不做业务逻辑
    UI 版会有自己的渲染函数,共用 ask() 但渲染方式不同
    """
    
    print("\n" + "=" * 60)
    print("💡 Synapse 答案")
    print("=" * 60)
    print(result["answer"])
    
    print("\n" + "=" * 60)
    print("📚 引用来源(检索到的切片)")
    print("=" * 60)
    
    for i, citation in enumerate(result["citations"], 1):
        score_str = f"(相似度: {citation['score']:.3f})" if citation['score'] else ""
        print(f"\n[{i}] {citation['file_name']},第 {citation['page']} 页 {score_str}")
        print(f"    原文片段:{citation['text_preview']}...")
    
    print("\n" + "=" * 60)


# ========================================
# 第 7 部分:主程序(命令行交互)
# ========================================
if __name__ == "__main__":
    print("=" * 60)
    print("🧠 Synapse - 论文问答系统")
    print("=" * 60)
    print("加载索引中...")
    
    # 加载已索引的论文
    index = load_index()
    print(f"✅ 索引加载成功(检索 top_k = {TOP_K})")
    print("\n💬 输入问题(输入 'quit' 退出):")
    
    # 命令行交互循环
    while True:
        print("\n" + "-" * 60)
        question = input("你的问题:").strip()
        
        # 退出条件
        if question.lower() in ['quit', 'exit', 'q', '退出']:
            print("\n👋 再见!")
            break
        
        # 空输入跳过
        if not question:
            continue
        
        # 查询
        try:
            print("🔄 正在思考...")
            response = ask(index, question)
            print_response(response)
        except Exception as e:
            print(f"\n❌ 查询失败:{e}")