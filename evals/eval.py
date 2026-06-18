"""
eval.py - Synapse 评估脚本(完整版)

功能:
    跑完整 50 题评估集,输出 6 维度报告 + Bad Case 列表 + JSON 报告

用法:
    cd ~/Documents/synapse
    python evals/eval.py              # 跑全部 50 题
    python evals/eval.py --limit 5    # 快速验证(前 5 题)
    python evals/eval.py --category metadata  # 只跑 metadata 类
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# 把 src/ 加入路径
sys.path.append(str(Path(__file__).parent.parent / 'src'))
from search import load_index, ask


# ========================================
# 路径配置
# ========================================
EVALS_DIR = Path(__file__).parent
EVAL_SET = EVALS_DIR / 'evals.json'
RESULTS_DIR = EVALS_DIR / 'results'
RESULTS_DIR.mkdir(exist_ok=True)


# ========================================
# 第 1 部分:加载评估集
# ========================================
def load_eval_set(category=None, limit=None):
    with open(EVAL_SET, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    questions = data['questions']
    
    if category:
        questions = [q for q in questions if q['category'] == category]
        print(f"📂 过滤类别 '{category}',剩 {len(questions)} 题")
    
    if limit:
        questions = questions[:limit]
        print(f"🔢 只跑前 {limit} 题")
    
    print(f"✅ 加载 {len(questions)} 题评估集")
    return questions


# ========================================
# 第 2 部分:对单题跑 Synapse
# ========================================
def run_one_eval(index, question):
    result = {
        "id": question["id"],
        "category": question["category"],
        "difficulty": question["difficulty"],
        "question": question["question"],
        "ground_truth": question["ground_truth"],
        "synapse_answer": None,
        "synapse_citations": [],
        "error": None,
        "duration_seconds": 0,
    }
    
    try:
        start = time.time()
        synapse_result = ask(index, question["question"])
        duration = time.time() - start
        
        result["synapse_answer"] = synapse_result["answer"]
        result["synapse_citations"] = synapse_result["citations"]
        result["duration_seconds"] = round(duration, 2)
    except Exception as e:
        result["error"] = str(e)
    
    return result


# ========================================
# 第 3 部分:6 维度评估指标
# ========================================
def calc_recall_at_5(expected_papers, citations):
    if not expected_papers:
        return None
    actual_papers = [c["file_name"] for c in citations[:5]]
    hits = [p for p in actual_papers if p in expected_papers]
    return 1.0 if len(hits) > 0 else 0.0


def calc_mrr(expected_papers, citations):
    if not expected_papers:
        return None
    for i, c in enumerate(citations[:5], 1):
        if c["file_name"] in expected_papers:
            return round(1.0 / i, 3)
    return 0.0


def calc_accuracy(key_facts, answer):
    if not key_facts:
        return None
    answer_lower = answer.lower() if answer else ""
    hits = sum(1 for fact in key_facts if fact.lower() in answer_lower)
    return round(hits / len(key_facts), 3)


def calc_citation_rate(expected_papers, answer, citations):
    if not citations:
        return 0.0
    return 1.0


def calc_refusal(category, answer):
    if category != "out_of_scope":
        return None
    if not answer:
        return 0.0
    
    refusal_keywords = [
        "无法确定", "超出范围", "无法回答", "未提及",
        "不在", "无法", "no relevant", "cannot determine",
        "片段中没有", "未涉及", "无相关"
    ]
    answer_lower = answer.lower()
    for kw in refusal_keywords:
        if kw.lower() in answer_lower:
            return 1.0
    return 0.0


# ========================================
# 第 4 部分:LLM as Judge
# ========================================
def llm_judge_relevance(question, expected_answer, actual_answer):
    if not actual_answer or len(actual_answer.strip()) < 10:
        return {"score": 0.0, "reason": "答案为空或过短"}
    
    from llama_index.core import Settings
    llm = Settings.llm
    
    judge_prompt = f"""你是一个严谨的评委,要对一个 AI 答案的"相关性"打分。

【问题】
{question}

【标准答案】
{expected_answer}

【AI 实际答案】
{actual_answer}

【打分标准】
- 1.0:完整且准确地回答了问题
- 0.7-0.9:答到了主要点,但缺少细节
- 0.4-0.6:部分正确,但有明显遗漏
- 0.1-0.3:答非所问或大部分错误
- 0.0:完全错误或无关

严格按 JSON 格式输出,不要任何额外文字:
{{"score": 0.0~1.0 之间的数字, "reason": "一句话说明理由"}}
"""
    
    try:
        response = llm.complete(judge_prompt)
        response_text = str(response).strip()
        
        if "```" in response_text:
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        result = json.loads(response_text)
        return {
            "score": float(result["score"]),
            "reason": result["reason"]
        }
    except Exception as e:
        return {"score": 0.5, "reason": f"LLM Judge 解析失败: {str(e)}"}


# ========================================
# 第 5 部分:对单题打分
# ========================================
def evaluate_one(question, result):
    if result["error"]:
        return {
            "recall_at_5": None, "mrr": None, "accuracy": None,
            "relevance": None, "citation_rate": None, "refusal": None,
            "total": None, "error": result["error"]
        }
    
    expected = question["ground_truth"]
    answer = result["synapse_answer"]
    citations = result["synapse_citations"]
    
    recall = calc_recall_at_5(expected["expected_papers"], citations)
    mrr = calc_mrr(expected["expected_papers"], citations)
    accuracy = calc_accuracy(expected["key_facts"], answer)
    citation_rate = calc_citation_rate(expected["expected_papers"], answer, citations)
    refusal = calc_refusal(question["category"], answer)
    
    judge_method = question["eval_config"]["judge_method"]
    relevance = None
    relevance_reason = None
    if judge_method == "llm":
        relevance_result = llm_judge_relevance(
            question["question"], expected["expected_answer"], answer
        )
        relevance = relevance_result["score"]
        relevance_reason = relevance_result["reason"]
    
    scores_for_total = [
        s for s in [recall, mrr, accuracy, relevance, citation_rate, refusal]
        if s is not None
    ]
    total = round(sum(scores_for_total) / len(scores_for_total), 3) if scores_for_total else None
    
    return {
        "recall_at_5": recall,
        "mrr": mrr,
        "accuracy": accuracy,
        "relevance": relevance,
        "relevance_reason": relevance_reason,
        "citation_rate": citation_rate,
        "refusal": refusal,
        "total": total
    }


# ========================================
# 第 6 部分:汇总报告
# ========================================
def generate_report(all_results):
    """
    生成 6 维度汇总报告
    
    维度:
    - 总分
    - 分类别(metadata / definition / detail / cross_paper / out_of_scope)
    - 分难度(easy / medium / hard)
    - Bad Case 列表(Total < 0.5 的题)
    """
    
    total_count = len(all_results)
    successful = [r for r in all_results if not r['scores'].get('error')]
    
    # 1. 总分(只统计跑成功的题)
    totals = [r['scores']['total'] for r in successful if r['scores']['total'] is not None]
    avg_total = round(sum(totals) / len(totals), 3) if totals else 0
    
    # 2. 分类别
    by_category = defaultdict(list)
    for r in successful:
        cat = r['question']['category']
        if r['scores']['total'] is not None:
            by_category[cat].append(r['scores']['total'])
    
    category_avgs = {
        cat: round(sum(scores) / len(scores), 3)
        for cat, scores in by_category.items()
    }
    
    # 3. 分难度
    by_difficulty = defaultdict(list)
    for r in successful:
        diff = r['question']['difficulty']
        if r['scores']['total'] is not None:
            by_difficulty[diff].append(r['scores']['total'])
    
    difficulty_avgs = {
        diff: round(sum(scores) / len(scores), 3)
        for diff, scores in by_difficulty.items()
    }
    
    # 4. 单维度平均
    metric_avgs = {}
    for metric in ['recall_at_5', 'mrr', 'accuracy', 'relevance', 'citation_rate', 'refusal']:
        values = [r['scores'][metric] for r in successful if r['scores'].get(metric) is not None]
        if values:
            metric_avgs[metric] = round(sum(values) / len(values), 3)
    
    # 5. Bad Case 列表(Total < 0.5)
    bad_cases = [
        {
            "id": r['question']['id'],
            "category": r['question']['category'],
            "difficulty": r['question']['difficulty'],
            "question": r['question']['question'],
            "total": r['scores']['total'],
            "synapse_answer": (r['result']['synapse_answer'] or "")[:200],
            "expected_answer": r['question']['ground_truth']['expected_answer'][:200]
        }
        for r in successful
        if r['scores']['total'] is not None and r['scores']['total'] < 0.5
    ]
    bad_cases.sort(key=lambda x: x['total'])  # 最差的排前面
    
    return {
        "total_questions": total_count,
        "successful_count": len(successful),
        "avg_total": avg_total,
        "metric_avgs": metric_avgs,
        "by_category": category_avgs,
        "by_difficulty": difficulty_avgs,
        "bad_cases": bad_cases,
    }


def print_report(report):
    """终端打印漂亮报告"""
    print("\n" + "=" * 70)
    print("📊 Synapse 评估报告")
    print("=" * 70)
    
    print(f"\n🎯 总分:{report['avg_total']}")
    print(f"   成功跑完:{report['successful_count']} / {report['total_questions']} 题")
    
    print(f"\n📐 6 维度平均分:")
    metric_names = {
        'recall_at_5': '检索召回(Recall@5)',
        'mrr': '检索精度(MRR)     ',
        'accuracy': '答案准确(Accuracy) ',
        'relevance': '答案相关(Relevance)',
        'citation_rate': '引用溯源(Citation) ',
        'refusal': '反幻觉(Refusal)   ',
    }
    for key, name in metric_names.items():
        if key in report['metric_avgs']:
            val = report['metric_avgs'][key]
            bar = "█" * int(val * 20)
            print(f"   {name}:{val}  {bar}")
    
    print(f"\n📂 按类别:")
    for cat in ['metadata', 'definition', 'detail', 'cross_paper', 'out_of_scope']:
        if cat in report['by_category']:
            val = report['by_category'][cat]
            bar = "█" * int(val * 20)
            print(f"   {cat:15s}:{val}  {bar}")
    
    print(f"\n📊 按难度:")
    for diff in ['easy', 'medium', 'hard']:
        if diff in report['by_difficulty']:
            val = report['by_difficulty'][diff]
            bar = "█" * int(val * 20)
            print(f"   {diff:8s}:{val}  {bar}")
    
    print(f"\n🔴 Bad Cases (Total < 0.5):共 {len(report['bad_cases'])} 题")
    for bc in report['bad_cases'][:10]:  # 只显示最差的 10 个
        print(f"   [{bc['id']}, {bc['category']}, total={bc['total']}]")
        print(f"      问:{bc['question']}")
        print(f"      Synapse:{bc['synapse_answer'][:100]}...")
        print()
    
    print("=" * 70)


def save_report(report, all_results):
    """保存完整报告 JSON"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / f"eval_v1_{timestamp}.json"
    
    full_data = {
        "metadata": {
            "version": "v1",
            "timestamp": datetime.now().isoformat(),
            "total_questions": report['total_questions'],
            "successful_count": report['successful_count'],
        },
        "report": report,
        "details": [
            {
                "question": r['question'],
                "result": r['result'],
                "scores": r['scores']
            }
            for r in all_results
        ]
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)
    
    print(f"💾 报告已保存:{output_path}")
    return output_path


# ========================================
# Main:完整评估流程
# ========================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Synapse 评估脚本')
    parser.add_argument('--category', type=str, default=None,
                        help='只跑某个类别(metadata/definition/detail/cross_paper/out_of_scope)')
    parser.add_argument('--limit', type=int, default=None,
                        help='只跑前 N 题(快速验证用)')
    args = parser.parse_args()
    
    print("=" * 70)
    print("🧠 Synapse 评估脚本 - 完整版")
    print("=" * 70)
    
    # 加载评估集
    questions = load_eval_set(category=args.category, limit=args.limit)
    
    # 加载 Synapse 索引
    print(f"\n🔄 加载 Synapse 索引...")
    index = load_index()
    print(f"✅ 索引加载完成\n")
    
    # 跑评估
    all_results = []
    start_time = time.time()
    
    for i, q in enumerate(questions, 1):
        print(f"[{i:2d}/{len(questions)}] {q['id']} [{q['category']:12s}, {q['difficulty']:6s}] ", end='', flush=True)
        
        result = run_one_eval(index, q)
        scores = evaluate_one(q, result)
        
        all_results.append({
            "question": q,
            "result": result,
            "scores": scores
        })
        
        # 简短输出
        if scores.get("error"):
            print(f"❌ 失败")
        else:
            total = scores['total']
            mark = "✅" if total >= 0.7 else "⚠️ " if total >= 0.5 else "🔴"
            print(f"{mark} total={total}")
    
    elapsed = time.time() - start_time
    print(f"\n⏱️  总耗时:{elapsed:.1f}s(平均 {elapsed/len(questions):.1f}s/题)")
    
    # 生成 + 打印 + 保存报告
    report = generate_report(all_results)
    print_report(report)
    save_report(report, all_results)