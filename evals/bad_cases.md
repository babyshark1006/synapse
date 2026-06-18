# Synapse Bad Case 库

**记录原则**:跑评估时发现的"系统性问题",分类记录,后续批量优化。

---

## Bad Case Pattern 1:metadata "误拒答"

**发现日期**:2026-05-29
**触发问题**:RAG 论文第一作者 / RAG 论文标题
**评估结果**:Recall@5 = 1.0,Accuracy = 0.0(Synapse 拒答)

### 根因分析

| 维度 | 现象 |
|---|---|
| 检索层 | top 5 命中 rag.pdf,但都是中后页(实验/参考文献),不是第 1 页(metadata 区) |
| 生成层 | Prompt 强约束 "不能编造",Claude 看到 top 5 没 metadata 就拒答 |
| 数据层 | metadata 在 PDF 第 1 页角落,embedding 向量孤立,语义检索难命中 |

### 受影响题数(初步)

- eval_003(RAG 第一作者)→ 拒答
- eval_004(RAG 标题)→ 拒答
- 待评估:eval_006(ReAct 年份)、eval_007(Transformer 会议)、eval_008(RAG 机构)、eval_010(ReAct 作者数)

### 优化方向

**短期(本周)**:Prompt 优化 — 对 metadata 类问题更宽容
**中期(2 周)**:意图分类 — metadata 题走专门检索路径
**长期(1 月)**:multi-vector embedding — 标题/作者单独索引

### 备注

🌟 这个 Bad Case 在 Step 1 设计 metadata 类别时就预判到了 —
"metadata 物理位置特殊,难以被检索" — 今天评估完美验证了直觉。
这是评估驱动产品迭代的标准范式。