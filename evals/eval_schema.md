# Synapse 评估集 Schema v1

**版本**:v1
**创建日期**:2026-05-23
**作者**:Roy

---

## 设计原则

- **可扩展**:未来加 Part 6 多轮场景,只需加 `category` 不改结构
- **可量化**:每个字段都能算出指标(Recall / Precision / Accuracy)
- **可追溯**:每题有 id,Bad Case 能精确定位
- **Schema First**:先定结构,再标数据 — 避免标到一半推倒重来

---

## JSON 结构

```json
{
  "id": "eval_XXX",
  "category": "metadata | definition | detail | cross_paper | out_of_scope",
  "difficulty": "easy | medium | hard",
  "question": "用户问题",
  
  "ground_truth": {
    "expected_answer": "完整标准答案",
    "expected_papers": ["transformer.pdf"],
    "expected_pages": [1, 2],
    "key_facts": ["关键事实 1", "关键事实 2"]
  },
  
  "eval_config": {
    "judge_method": "manual | llm",
    "tolerance": "strict | loose"
  },
  
  "notes": "出题人备注"
}
```

---

## 5 大类别分布(50 题)

| Category | 题数 | 占比 | 测什么 |
|---|---|---|---|
| metadata | 10 | 20% | 元数据检索(作者/年份/标题) |
| definition | 10 | 20% | 单论文术语定义 |
| detail | 10 | 20% | 单论文细节(数字/参数) |
| cross_paper | 10 | 20% | 跨论文对比 |
| out_of_scope | 10 | 20% | 越界识别(反幻觉) |
| **合计** | **50** | **100%** | 6 维度评估覆盖 |

---

## 难度分布

每类 10 题:
- 4 题 easy(40%)
- 4 题 medium(40%)
- 2 题 hard(20%)

---

## 6 维度评估指标

| 维度 | 指标 | 计算方式 |
|---|---|---|
| 检索 - 召回 | Recall@5 | top 5 命中 expected_papers 的比例 |
| 检索 - 精度 | MRR | 第一个相关切片的排名倒数 |
| 答案 - 准确性 | Accuracy | 答案是否包含 key_facts(人工 / LLM) |
| 答案 - 相关性 | Relevance | 答案是否答到点(LLM as Judge) |
| 答案 - 引用率 | Citation Rate | 答案中有引用的比例 |
| 反幻觉 | Refusal Rate | out_of_scope 题中正确说"不知道"的比例 |

---

## 字段设计说明

### `id` — 唯一标识
**为什么**:Bad Case 闭环时,能精确定位"哪一题没过"。
**格式**:`eval_001` ~ `eval_050`。

### `category` — 5 大类别
**为什么**:可以做"分类别报告" — "Synapse 在 metadata 类 95%,跨论文类 70%"。
**值域**:
- `metadata` — 元数据(作者 / 年份 / 论文标题)
- `definition` — 单论文术语定义
- `detail` — 单论文细节(数字 / 参数 / 实验)
- `cross_paper` — 跨论文对比(2-3 篇)
- `out_of_scope` — 越界(论文里没有的)

### `difficulty` — 难度
**为什么**:简单题 100% 不算厉害,难题 80% 才是真本事。

### `ground_truth.expected_papers`
**为什么**:测向量检索是否命中"应该命中的论文"。

### `ground_truth.key_facts`
**为什么**:**Ground Truth 越细,评估越准**。粗:"Vaswani 等" → 检测不出"是不是 8 位作者全答出";细:`["8 位作者", "Equal contribution", "顺序随机"]` → 可以打分。

### `eval_config.judge_method`
**为什么**:客观题(metadata / detail)用人工,主观题(definition / cross_paper)用 LLM as Judge。

---

## 评估流程

```
1. 加载 evals.json
2. 对每题:
   a. 用 search.py 跑 ask()
   b. 收集:answer, citations
   c. 算 Recall@5(citations vs expected_papers)
   d. 判 Accuracy(key_facts 是否在 answer 里)
   e. 判 Relevance(LLM Judge)
   f. 判 Refusal(out_of_scope 题)
3. 汇总 6 个维度的分数
4. 出报告:总分 + 分类别分 + Bad Case 列表
```