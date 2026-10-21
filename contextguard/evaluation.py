"""
Evaluation and Ablation Study Engine.
Calculates False Positive (FP) / False Negative (FN) rates, baseline comparison,
and retrieval ablation analysis.
"""
from typing import Dict, Any, List
from .pipeline import pipeline_runner
from .retrieval import HybridRetriever
from .github_client import MOCK_PRS

def run_evaluation() -> Dict[str, Any]:
    """
    Evaluates baseline raw AI reviewer vs. ContextGuard verified reviewer
    across all 9 benchmark PRs.
    """
    results = []
    baseline_fp = 0
    baseline_fn = 0
    baseline_tp = 0
    baseline_tn = 0

    cg_fp = 0
    cg_fn = 0
    cg_tp = 0
    cg_tn = 0

    ground_truth = {
        1: "COMPLIANT",       # clamp was correct; AI flagged as bug (FP)
        2: "NON_COMPLIANT",   # average has empty list bug (TP)
        3: "COMPLIANT",       # palindrome was correct; AI fix harmful (FP)
        4: "NON_COMPLIANT",   # slugify needs whitespace fix (TP)
        5: "COMPLIANT",       # percent was correct (TN)
        6: "NON_COMPLIANT",   # truncate had edge-case bug, but AI said compliant (FN)
        7: "NON_COMPLIANT",   # email validator ambiguous (Escalated)
        8: "COMPLIANT",       # cart total was correct; AI claimed float rounding error (FP)
        9: "COMPLIANT"        # password was correct (TN)
    }

    for pr_num in range(1, 10):
        url = f"https://github.com/shopkit/shopkit/pull/{pr_num}"
        run_res = pipeline_runner.run(url, force_refresh=True)

        gt = ground_truth.get(pr_num, "COMPLIANT")
        ai_verdict = run_res["initial_verdict"]
        cg_verdict = run_res["final_verdict"]

        # Baseline metrics (Raw AI)
        if ai_verdict == "NON_COMPLIANT" and gt == "COMPLIANT":
            baseline_fp += 1
        elif ai_verdict == "COMPLIANT" and gt == "NON_COMPLIANT":
            baseline_fn += 1
        elif ai_verdict == "NON_COMPLIANT" and gt == "NON_COMPLIANT":
            baseline_tp += 1
        elif ai_verdict == "COMPLIANT" and gt == "COMPLIANT":
            baseline_tn += 1

        # ContextGuard metrics
        if cg_verdict == "NON_COMPLIANT" and gt == "COMPLIANT":
            cg_fp += 1
        elif cg_verdict == "COMPLIANT" and gt == "NON_COMPLIANT":
            cg_fn += 1
        elif cg_verdict == "NON_COMPLIANT" and gt == "NON_COMPLIANT":
            cg_tp += 1
        elif cg_verdict == "COMPLIANT" and gt == "COMPLIANT":
            cg_tn += 1

        results.append({
            "pr_number": pr_num,
            "title": MOCK_PRS[pr_num]["title"],
            "ground_truth": gt,
            "ai_verdict": ai_verdict,
            "cg_verdict": cg_verdict,
            "case_code": run_res["case_code"],
            "duration": run_res["duration_seconds"]
        })

    # False Positive Rate = FP / (FP + TN)
    baseline_fpr = (baseline_fp / (baseline_fp + baseline_tn)) * 100.0 if (baseline_fp + baseline_tn) > 0 else 0.0
    cg_fpr = (cg_fp / (cg_fp + cg_tn)) * 100.0 if (cg_fp + cg_tn) > 0 else 0.0

    return {
        "summary": {
            "total_prs": 9,
            "baseline": {
                "tp": baseline_tp,
                "tn": baseline_tn,
                "fp": baseline_fp,
                "fn": baseline_fn,
                "false_positive_rate": baseline_fpr
            },
            "contextguard": {
                "tp": cg_tp,
                "tn": cg_tn,
                "fp": cg_fp,
                "fn": cg_fn,
                "false_positive_rate": cg_fpr
            }
        },
        "details": results
    }

def run_retrieval_ablation() -> List[Dict[str, Any]]:
    """
    Runs retrieval ablation study for PR-4 (slugify) across:
    1. Dense Only
    2. Sparse Only (BM25)
    3. Hybrid (Dense + BM25 with RRF)
    4. Full Pipeline (Hybrid + HyDE)
    """
    pr_data = MOCK_PRS[4]
    query = f"{pr_data['title']} {pr_data['description']}"
    retriever = HybridRetriever("sample_data/shopkit")
    retriever.build_index(allow_rules=["shopkit/", "tests/"], deny_rules=["shopkit/internal/"])

    modes = [
        ("dense", "Dense Only (Vector Dot-Product)"),
        ("sparse", "Sparse Only (Okapi BM25)"),
        ("hybrid", "Hybrid (Dense + BM25 via RRF)"),
        ("full", "Full Pipeline (Hybrid + HyDE Expansion)")
    ]

    ablation_results = []
    target_identifier = "test_slugify_collapses_whitespace"

    for mode_code, mode_label in modes:
        snippets = retriever.retrieve(query, mode=mode_code, top_k=50, pr_data=pr_data)
        
        target_rank = None
        for rank, s in enumerate(snippets, start=1):
            if s["identifier"] == target_identifier:
                target_rank = rank
                break

        in_top_5 = (target_rank is not None and target_rank <= 5)

        ablation_results.append({
            "mode": mode_label,
            "mode_code": mode_code,
            "target_found": target_rank is not None,
            "target_rank": target_rank if target_rank else ">50",
            "in_top_5": in_top_5,
            "verification_impact": "NON_COMPLIANT Confirmed" if in_top_5 else "Inconclusive (Decisive Test Missed)"
        })

    return ablation_results

if __name__ == "__main__":
    print("=== Running ContextGuard Evaluation ===")
    eval_res = run_evaluation()
    print(f"Baseline False Positive Rate: {eval_res['summary']['baseline']['false_positive_rate']:.1f}%")
    print(f"ContextGuard False Positive Rate: {eval_res['summary']['contextguard']['false_positive_rate']:.1f}%")
    print("\n=== Running Retrieval Ablation Study (PR-4) ===")
    for row in run_retrieval_ablation():
        print(f"Mode: {row['mode']} | Target Rank: {row['target_rank']} | Top-5: {row['in_top_5']} | Impact: {row['verification_impact']}")
