# Synapse 迭代日志

> 每周更新。记录做了什么、遇到什么坑、指标变化、新发现。

---

## 📅 Week 0 (2026-04-22 ~ 2026-04-24) - 项目启动 + 环境就绪

### 本周做了什么
- 完成项目初始化(git + conda 环境 + 目录结构)
- 完成产品一页纸 v1
- 明确 8 周路线图
- **Day 1:打通 Claude API + OpenAI Embedding API**

### 关键决策
- **技术栈选型**:LlamaIndex + ChromaDB + Claude Sonnet + OpenAI Embedding
  - LlamaIndex vs LangChain:更聚焦 RAG,学术文档处理更好
  - Claude Sonnet:引用能力强,幻觉率低
  - OpenAI Embedding:业界标准,成本低
  - ChromaDB 本地方案:零运维,专注核心逻辑
  
- **成本控制**:OpenAI 充值 $5 启动,预估 8 周总成本 $10-20

- **安全架构**:三层 Secret 防御
  - 本地 .env(gitignore 挡住)
  - .env.example 占位符模板
  - GitHub Push Protection 远程兜底

### 遇到的问题 & 解决
1. **差点泄露真 API key** → 被 GitHub Push Protection 拦截,修正后重新提交
2. **httpx 0.28+ 和 openai 1.54.0 不兼容** → 降级 httpx 到 <0.28
3. **OpenAI 账户无额度** → 充值 $5

### 下周计划(Week 1)
- 安装 LlamaIndex + ChromaDB + pypdf
- 下载 3 篇经典 AI 论文(Transformer、RAG、ReAct)
- 端到端跑通:PDF → 切片 → 问答(baseline 版本)
- 引用溯源初版

---