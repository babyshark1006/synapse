# compare() API 设计契约

**模块**:`src/compare.py`  
**核心函数**:`compare()`  
**调用方**:Streamlit UI(`app.py` 的对比 Tab)+ 未来的 API 接口  

---

## 函数签名

```python
def compare(
    index,
    paper_files: list[str],
    dimensions: list[str],
    custom_dimension: str = None
) -> dict:
    """
    对 2-4 篇论文做结构化对比
    
    Args:
        index: 已加载的 LlamaIndex 索引
        paper_files: 论文文件名列表,长度 2-4
        dimensions: 预设对比维度列表
        custom_dimension: 自定义维度(可选)
    
    Returns:
        dict 包含 comparison_table / markdown_table / citations / duration
    
    Raises:
        ValueError: 输入参数不合法
    """
```

---

## 输入参数

| 参数 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `index` | VectorStoreIndex | ✅ | 来自 search.load_index() |
| `paper_files` | List[str] | ✅ | 长度 2-4 |
| `dimensions` | List[str] | ✅ | 预设维度,至少 1 个或有 custom |
| `custom_dimension` | str | ❌ | ≤ 100 字符 |

### 预设维度白名单

```python
PRESET_DIMENSIONS = [
    "架构 / 模型设计",
    "方法 / 核心算法",
    "实验 / 性能数据",
    "结论 / 核心贡献",
    "局限 / 未来方向"
]
```

---

## 输出格式

```python
{
    "papers": ["transformer.pdf", "rag.pdf"],
    "dimensions": ["架构 / 模型设计", "实验 / 性能数据"],  # 含 custom
    
    "comparison_table": {
        "架构 / 模型设计": {
            "transformer.pdf": "...",
            "rag.pdf": "..."
        },
        "实验 / 性能数据": {
            "transformer.pdf": "...",
            "rag.pdf": "..."
        }
    },
    
    "citations": {
        "transformer.pdf": [
            {"page": 3, "score": 0.87, "preview": "..."},
            ...
        ],
        "rag.pdf": [...]
    },
    
    "markdown_table": "| 维度 | Transformer | RAG |\n|------|------------|-----|\n...",
    
    "duration_seconds": 23.4,
    "error": None
}
```

---

## 错误处理矩阵

| 错误类型 | 触发条件 | 处理 |
|---|---|---|
| 论文数量不合法 | len(paper_files) < 2 or > 4 | `raise ValueError` |
| 无对比维度 | dimensions 为空且 custom 为空 | `raise ValueError` |
| 论文未索引 | paper_files 中某文件不在索引 | 返回 `error` 字段,不抛异常 |
| Claude API 单维度失败 | 网络/超时 | 该维度标 "调用失败",其他正常返回 |
| Claude API 全部失败 | 网络全断 | `raise RuntimeError` |

---

## 性能预期

| 指标 | 目标 |
|---|---|
| 单维度生成耗时 | < 5 秒 |
| 4 篇 × 5 维度对比总耗时 | < 30 秒 |
| Token 成本(典型 3 篇 × 3 维度) | ~$0.05 / 次 |

---

## 调用示例

```python
from search import load_index
from compare import compare

index = load_index()

result = compare(
    index=index,
    paper_files=["transformer.pdf", "rag.pdf", "react.pdf"],
    dimensions=["架构 / 模型设计", "结论 / 核心贡献"],
    custom_dimension="在解决幻觉上的思路"
)

print(result["markdown_table"])  # 直接渲染
```

---

## 设计原则

1. **关注点分离**:后端给数据,前端做渲染(dict 输出而非字符串)
2. **防御性设计**:单维度失败不让全函数崩(参考 eval.py)
3. **可扩展性**:future 加 reranker / per-document quota 时,API 不变
4. **可测试性**:dict 输出每个字段独立可测