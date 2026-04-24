# Synapse 迭代日志

> 每周更新。记录做了什么、遇到什么坑、指标变化、新发现。

---

## 📅 Week 0 (2026-04-22) - 项目启动

### 本周做了什么
- 完成项目初始化(git、conda 环境、目录结构)
- 完成产品一页纸 v1
- 明确了 8 周路线图

### 关键决策
- **技术栈选型**:LlamaIndex + ChromaDB + Claude Sonnet + OpenAI Embedding
  - 选 LlamaIndex 而非 LangChain:更聚焦 RAG,学术文档处理更好
  - 选 Claude 而非 GPT:引用能力更强,幻觉率更低
  - 选 ChromaDB 本地方案:零运维,专注核心逻辑

### 下周计划
- 装 RAG 依赖
- 跑通环境验证脚本(test_env.py)
- 端到端 MVP(PDF → 问答)

---