"""
app.py - Synapse Web UI(Part 6 模式驱动版)

设计:
    - 侧边栏:论文库 + 模式切换 + 模式专属配置
    - 主区:根据模式动态显示问答 / 对比内容
    - 模式驱动:radio button 切换"问答 / 对比"

关注点分离:
    - 后端逻辑(search.ask / compare.compare)在 src/ 模块
    - 本文件只做"渲染 + 交互"
"""

import streamlit as st
import sys
import os

# 把 src/ 加进路径(和原 app.py 一致)
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from search import load_index, ask
from compare import compare, PRESET_DIMENSIONS


# ========================================
# 第 1 部分:页面配置
# ========================================
st.set_page_config(
    page_title="Synapse · AI 论文阅读助手",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ========================================
# 第 2 部分:加载索引(缓存)
# ========================================
@st.cache_resource
def get_index():
    return load_index()


# ========================================
# 第 3 部分:论文库元数据
# ========================================
PAPERS = {
    "transformer.pdf": {
        "title": "Attention Is All You Need",
        "year": 2017, "venue": "NIPS", "label": "Transformer", "chunks": 29
    },
    "rag.pdf": {
        "title": "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
        "year": 2020, "venue": "NeurIPS", "label": "RAG", "chunks": 0
    },
    "react.pdf": {
        "title": "ReAct: Synergizing Reasoning and Acting in Language Models",
        "year": 2022, "venue": "ICLR 2023", "label": "ReAct", "chunks": 0
    }
}


# ========================================
# 第 4 部分:侧边栏(模式驱动核心)
# ========================================
with st.sidebar:
    # ───────── 论文库 ─────────
    st.title("📚 论文库")
    st.caption("Synapse 已索引")
    for filename, meta in PAPERS.items():
        st.markdown(
            f"**{meta['label']}** ({meta['year']} {meta['venue']})  \n"
            f"<span style='color:#888;font-size:0.85em'>{meta['title']}</span>",
            unsafe_allow_html=True
        )
    st.caption("共 3 篇 · 170 切片已索引")

    st.divider()

    # ───────── 模式选择 ─────────
    st.markdown("### 🎯 模式")
    mode = st.radio(
        "选择使用模式",
        options=["💬 问答模式", "📊 对比模式"],
        index=0,
        label_visibility="collapsed"
    )

    # ───────── 模式专属配置(条件渲染)─────────
    selected_papers = []
    selected_dimensions = []
    custom_dim = ""
    generate_clicked = False

    if mode == "📊 对比模式":
        st.divider()
        st.markdown("### ⚙️ 对比配置")

        # 选论文
        st.markdown("**选择对比论文** (2-4 篇)")
        for filename, meta in PAPERS.items():
            if st.checkbox(meta['label'], key=f"paper_{filename}"):
                selected_papers.append(filename)

        # 实时反馈
        n = len(selected_papers)
        if n == 0:
            st.caption("⚠️ 还未选择论文")
        elif n < 2:
            st.caption(f"⚠️ 已选 {n} 篇,还需至少 1 篇")
        elif n > 4:
            st.caption(f"⚠️ 已选 {n} 篇,超过上限")
        else:
            st.caption(f"✅ 已选 {n} 篇")

        st.markdown("&nbsp;", unsafe_allow_html=True)

        # 选维度
        st.markdown("**选择对比维度** (可多选)")
        for dim in PRESET_DIMENSIONS:
            if st.checkbox(dim, key=f"dim_{dim}"):
                selected_dimensions.append(dim)

        # 自定义维度
        st.markdown("**自定义维度** (可选)")
        custom_dim = st.text_input(
            "自定义维度",
            placeholder="例:解决幻觉的思路",
            label_visibility="collapsed",
            max_chars=100
        )

        st.markdown("&nbsp;", unsafe_allow_html=True)

        # 生成按钮
        generate_clicked = st.button(
            "🚀 生成对比", type="primary", use_container_width=True
        )

    # ───────── 底部 ─────────
    st.divider()
    st.caption(
        "💡 Synapse · AI 论文研究助手  \n"
        "[GitHub](https://github.com/babyshark1006/synapse)"
    )


# ========================================
# 第 5 部分:主区域(模式动态切换)
# ========================================
st.title("🧠 Synapse")
st.caption("AI 论文研究助手 · 跨论文知识网络 · 评估驱动迭代")
st.divider()


# ============================================================
# 💬 问答模式
# ============================================================
if mode == "💬 问答模式":
    st.markdown("### 💬 论文深度问答")
    st.caption("基于已索引的 3 篇论文,生成带引用溯源的精准答案")

    question = st.text_input(
        "你的问题",
        placeholder="例:Transformer 的 multi-head attention 是怎么工作的?"
    )

    if st.button("发送", type="primary"):
        if not question or len(question.strip()) < 3:
            st.warning("⚠️ 请输入有效问题(至少 3 个字)")
        else:
            with st.spinner("🧠 Synapse 思考中..."):
                try:
                    index = get_index()
                    result = ask(index, question)

                    st.markdown("### 💡 答案")
                    st.markdown(result["answer"])

                    with st.expander(f"📚 引用来源({len(result['citations'])} 条)"):
                        # 答案来源分布
                        st.markdown("**答案来源分布**")
                        paper_count = {}
                        for c in result["citations"]:
                            f = c["file_name"]
                            paper_count[f] = paper_count.get(f, 0) + 1
                        for paper, count in paper_count.items():
                            label = PAPERS.get(paper, {}).get("label", paper)
                            st.markdown(f"- **{label}**: {count}/{len(result['citations'])} 切片")

                        st.divider()

                        # 完整引用
                        for i, c in enumerate(result["citations"], 1):
                            label = PAPERS.get(c["file_name"], {}).get("label", c["file_name"])
                            score_str = f"({c['score']:.3f})" if c['score'] else ""
                            st.markdown(f"**[{i}] {label}** · 第 {c['page']} 页 {score_str}")
                            st.caption(c["text_preview"][:300] + "...")
                except Exception as e:
                    st.error(f"❌ 查询失败:{e}")


# ============================================================
# 📊 对比模式
# ============================================================
elif mode == "📊 对比模式":
    st.markdown("### 📊 跨论文对比")
    st.caption("选择 2-4 篇论文 + 对比维度,生成结构化对比表")

    # 引导提示
    if not generate_clicked:
        if not selected_papers or len(selected_papers) < 2:
            st.info("👈 **左侧选 2-4 篇论文**,再选对比维度,然后点「🚀 生成对比」")
        elif not selected_dimensions and not custom_dim:
            st.info("👈 **左侧选至少 1 个对比维度**,然后点「🚀 生成对比」")
        else:
            n_dim = len(selected_dimensions) + (1 if custom_dim else 0)
            st.info(
                f"✅ 准备就绪:**{len(selected_papers)} 篇论文** × **{n_dim} 个维度**  \n"
                f"点左侧「🚀 生成对比」开始"
            )

    # 生成对比
    if generate_clicked:
        if len(selected_papers) < 2:
            st.error("❌ 至少选 2 篇论文")
        elif len(selected_papers) > 4:
            st.error("❌ 最多选 4 篇论文")
        elif not selected_dimensions and not custom_dim:
            st.error("❌ 至少选 1 个对比维度")
        else:
            with st.spinner("🧠 Synapse 正在对比分析..."):
                try:
                    index = get_index()
                    result = compare(
                        index=index,
                        paper_files=selected_papers,
                        dimensions=selected_dimensions,
                        custom_dimension=custom_dim if custom_dim else None
                    )
                    st.session_state["compare_result"] = result
                except Exception as e:
                    st.error(f"❌ 对比失败:{e}")

    # 显示结果
    if "compare_result" in st.session_state:
        result = st.session_state["compare_result"]

        st.success(
            f"✅ 对比完成 · **{len(result['papers'])} 篇** × "
            f"**{len(result['dimensions'])} 维度** · 耗时 **{result['duration_seconds']}s**"
        )

        st.markdown("### 📊 对比表格")
        st.markdown(result["markdown_table"])

        # 导出
        col1, col2, col3 = st.columns([1, 1, 3])
        with col1:
            with st.popover("📋 复制 Markdown"):
                st.code(result["markdown_table"], language="markdown")
        with col2:
            st.download_button(
                "📥 下载 .md",
                data=result["markdown_table"],
                file_name="synapse_compare.md",
                mime="text/markdown"
            )

        # 引用溯源
        with st.expander("📚 引用溯源(每篇 top 5 切片)"):
            for paper, cites in result["citations"].items():
                label = PAPERS.get(paper, {}).get("label", paper)
                st.markdown(f"#### {label}")
                for c in cites:
                    score_str = f"({c['score']:.3f})" if c['score'] else ""
                    st.markdown(f"- 第 **{c['page']}** 页 {score_str}")
                    st.caption(c["preview"][:200] + "...")

        # 清除
        if st.button("🔄 清除结果,重新对比"):
            del st.session_state["compare_result"]
            st.rerun()