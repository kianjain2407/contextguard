"""
HumanEval Baseline Reproduction.
Reproduces the Fix-guided Verification Filter logic on synthetic coding problems
to establish the 4-case filtering baseline.
"""
from typing import Dict, Any, List
from .verification import classify

HUMANEVAL_SUBSET = [
    {
        "task_id": "HumanEval/0",
        "prompt": "has_close_elements(numbers: List[float], threshold: float) -> bool",
        "canonical_solution": """def has_close_elements(numbers, threshold):
    for idx, elem in enumerate(numbers):
        for idx2, elem2 in enumerate(numbers):
            if idx != idx2 and abs(elem - elem2) < threshold:
                return True
    return False""",
        "llm_flagged": True,
        "original_passes": True,
        "fix_passes": True,
        "expected_case": "CASE_1"
    },
    {
        "task_id": "HumanEval/1",
        "prompt": "separate_paren_groups(paren_string: str) -> List[str]",
        "canonical_solution": "def separate_paren_groups(paren_string): ...",
        "llm_flagged": True,
        "original_passes": False,
        "fix_passes": True,
        "expected_case": "CASE_2"
    },
    {
        "task_id": "HumanEval/2",
        "prompt": "truncate_number(number: float) -> float",
        "canonical_solution": "def truncate_number(number): return number % 1.0",
        "llm_flagged": True,
        "original_passes": True,
        "fix_passes": False,
        "expected_case": "CASE_3"
    }
]

def run_humaneval_baseline() -> List[Dict[str, Any]]:
    results = []
    for item in HUMANEVAL_SUBSET:
        orig = ["pass"] if item["original_passes"] else ["fail"]
        fix = ["pass"] if item["fix_passes"] else ["fail"]
        case_code, final_verdict, reason = classify(orig, fix)
        results.append({
            "task_id": item["task_id"],
            "case_code": case_code,
            "final_verdict": final_verdict,
            "matches_expected": (case_code == item["expected_case"])
        })
    return results

if __name__ == "__main__":
    res = run_humaneval_baseline()
    print("HumanEval Baseline Reproduction Results:")
    for r in res:
        print(f"  {r['task_id']}: Case {r['case_code']} -> {r['final_verdict']} (Match: {r['matches_expected']})")
