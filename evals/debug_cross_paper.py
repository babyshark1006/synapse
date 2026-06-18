"""
debug_cross_paper.py - 抽样诊断 cross_paper 类的 Bad Case Pattern

目的:
    看真实数据,验证 3 个假设:
    H1: top 5 检索覆盖问题(只命中 1-2 篇)
    H2: Prompt 没激活跨论文综合
    H3: Recall 指标过于宽松
"""

import json
import glob
from pathlib import Path

# 找最新的评估报告
results_dir = Path(__file__).parent / 'results'
latest_report = max(results_dir.glob('eval_v1_*.json'))
print(f"📂 读取报告:{latest_report.name}\n")

with open(latest_report, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 找 cross_paper 题
cross_paper_results = [
    r for r in data['details']
    if r['question']['category'] == 'cross_paper'
]

print(f"🔍 cross_paper 类:{len(cross_paper_results)} 题\n")

# 抽样:最高分 + 最低分各 1 题
sorted_results = sorted(
    cross_paper_results,
    key=lambda r: r['scores']['total']
)

samples = [
    ("📉 最低分", sorted_results[0]),
    ("📈 最高分", sorted_results[-1]),
]

for label, r in samples:
    q = r['question']
    result = r['result']
    scores = r['scores']
    
    print("=" * 70)
    print(f"{label}:{q['id']} (total={scores['total']})")
    print("=" * 70)
    print(f"❓ 问题:{q['question']}")
    print(f"📋 expected_papers:{q['ground_truth']['expected_papers']}")
    print(f"\n📊 检索 top 5(看实际命中哪些 PDF):")
    
    papers_in_top5 = [c['file_name'] for c in result['synapse_citations']]
    paper_count = {}
    for p in papers_in_top5:
        paper_count[p] = paper_count.get(p, 0) + 1
    
    for paper, count in paper_count.items():
        bar = "█" * count
        print(f"   {paper:25s}: {count}/5  {bar}")
    
    # 关键指标
    print(f"\n📐 6 维度评分:")
    for k in ['recall_at_5', 'mrr', 'accuracy', 'relevance', 'citation_rate']:
        v = scores.get(k)
        if v is not None:
            print(f"   {k:20s}: {v}")
    
    # LLM Judge 理由(看 Claude 怎么判的)
    if scores.get('relevance_reason'):
        print(f"\n💬 LLM Judge 理由:{scores['relevance_reason']}")
    
    print(f"\n💡 Synapse 答案(前 300 字):")
    print(f"   {(result.get('synapse_answer') or '')[:300]}")
    print()

print("=" * 70)
print("✅ 诊断完成")
print("=" * 70)