# Synapse 🧠

> AI-powered deep reading assistant for research papers.
> Let your papers connect, not just pile up.

**面向 AI 研究者的垂直领域 RAG 产品**——不只是读一篇论文,更是看懂一个领域。

---

## 🎯 Why Synapse?

市面上的 PDF 阅读工具(ChatPDF、NotebookLM)是通用工具,但 AI 研究者的真实需求是:
- 跨论文建立连接,不只是单篇问答
- 学术场景的公式、表格、引用专项支持
- 可信的引用溯源,不能胡编

Synapse 专为 AI 领域论文深度阅读设计,通过 **4 个用户功能 + 2 个底层机制** 解决这些问题。

## ✨ 核心功能

### 用户可见功能
1. **单篇论文精准问答** - 带引用溯源
2. **结构化论文总结** - 一键输出核心要点
3. **跨论文对比分析** - 通用工具做不到的差异化
4. **多篇论文综述生成** - Agent 编排的深度能力

### 底层机制
5. **引用溯源 + 幻觉控制** - 每个答案可追溯到原文
6. **Bad Case 反馈闭环** - 持续迭代的基础

## 🏗️ 技术栈

- **LLM**: Claude Sonnet 4.5
- **Embedding**: OpenAI text-embedding-3-small
- **RAG 框架**: LlamaIndex
- **向量库**: ChromaDB(本地)
- **PDF 解析**: pypdf → Unstructured(Week 3 升级)
- **UI**: Streamlit(Week 3 开始)

## 📊 核心指标(持续更新)

_Week 3 开始记录_

| 指标 | Baseline | 当前版本 | 备注 |
|---|---|---|---|
| 检索 Recall@5 | - | - | Week 3 评估 |
| 引用正确率 | - | - | Week 3 评估 |
| 幻觉率 | - | - | Week 5 评估 |

## 🚀 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/babyshark1006/synapse.git
cd synapse

# 2. 创建 conda 环境
conda create -n synapse python=3.11 -y
conda activate synapse

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env,填入 ANTHROPIC_API_KEY 和 OPENAI_API_KEY
```

## 📖 项目文档

- [产品一页纸](product-onepager.md) - 产品定义与目标
- [迭代日志](iteration-log.md) - 每周迭代记录与 Bad Case 分析

## 📅 开发路线图

| 周 | 目标 | 交付物 |
|---|---|---|
| Week 1-2 | MVP 跑通 | 端到端 RAG 链路 + 引用溯源 |
| Week 3-4 | 评估集 + PDF 优化 | 120 条评估集、结构化解析 |
| Week 5-6 | 切片策略迭代 + 混合检索 | 4 版切片对比、BM25 融合 |
| Week 7 | 跨论文分析 + 综述生成 | 差异化功能、Agent 编排 |
| Week 8 | 作品集打磨 | PRD、评估报告、AB Test 方案 |

## 👤 作者

[Roy](https://github.com/babyshark1006) - AI Product Manager

---

**这是我从 0 到 1 独立开发的 AI 产品项目,完整记录了 RAG 深度优化和评估体系的全过程。**