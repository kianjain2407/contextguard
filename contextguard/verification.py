"""
Stage 5: Verification Filter & Four-Case Decision Logic.
Executes original vs fix code in sandbox, classifies outcomes, archives prior runs (D-04),
and records final verified verdicts.
"""
import time
from datetime import datetime
from typing import Dict, Any, Tuple, Union, List

from .sandbox import run_in_sandbox
from .db import db
from .config import SANDBOX_TIMEOUT_SECONDS

def _normalize_results(result: Union[List[str], Dict[str, Any]]) -> Tuple[int, int, int]:
    """Returns (passed, failed, errors) from either a list of strings or a sandbox dict."""
    if isinstance(result, list):
        passed = sum(1 for r in result if str(r).lower() == "pass")
        failed = sum(1 for r in result if str(r).lower() == "fail")
        errors = sum(1 for r in result if str(r).lower() == "error")
        return passed, failed, errors
    elif isinstance(result, dict):
        return result.get("passed", 0), result.get("failed", 0), result.get("errors", 0)
    return 0, 0, 1

def classify(orig_result: Union[List[str], Dict[str, Any]], fix_result: Union[List[str], Dict[str, Any]]) -> Tuple[str, str, str]:
    """
    Core Fix-Guided Verification Filter Logic (Base Paper reproduction).
    Returns (case_code, final_verdict, decision_reason).

    Cases:
    - Case 1: original passes + fix passes -> False alarm -> Corrected to COMPLIANT
    - Case 2: original fails + fix passes  -> True defect -> Confirmed NON_COMPLIANT
    - Case 3: original passes + fix fails  -> Harmful fix -> Corrected to COMPLIANT
    - Case 4: original fails + fix fails   -> Inconclusive -> NON_COMPLIANT (Escalate to Human)
    - Case 0: errors / no valid assertions -> Inconclusive -> NON_COMPLIANT (Fallback)
    """
    orig_pass, orig_fail, orig_err = _normalize_results(orig_result)
    fix_pass, fix_fail, fix_err = _normalize_results(fix_result)

    # Check for invalid execution (Case 0)
    if (orig_pass + orig_fail == 0) or (orig_err > 0 and fix_err > 0 and orig_pass == 0 and fix_pass == 0):
        return (
            "CASE_0",
            "NON_COMPLIANT",
            "Inconclusive (Case 0): Test execution encountered errors or no valid tests ran; fallback to human review."
        )

    orig_is_passing = (orig_fail == 0 and orig_pass > 0 and orig_err == 0)
    fix_is_passing = (fix_fail == 0 and fix_pass > 0 and fix_err == 0)

    # Case 1: Both pass
    if orig_is_passing and fix_is_passing:
        return (
            "CASE_1",
            "COMPLIANT",
            "False Alarm Corrected (Case 1): Original code satisfies all verification tests. Proposed patch was redundant."
        )

    # Case 2: Original fails, fix passes
    if not orig_is_passing and fix_is_passing:
        return (
            "CASE_2",
            "NON_COMPLIANT",
            "Defect Confirmed (Case 2): Original code fails verification tests; AI proposed fix successfully resolves the issue."
        )

    # Case 3: Original passes, fix fails
    if orig_is_passing and not fix_is_passing:
        return (
            "CASE_3",
            "COMPLIANT",
            "Harmful Fix Discarded (Case 3): Original code passes tests, but AI proposed fix introduces regressions."
        )

    # Case 4: Both fail
    return (
        "CASE_4",
        "NON_COMPLIANT",
        "Inconclusive (Case 4): Both original code and AI proposed fix failed verification tests; escalated to human reviewer."
    )

class VerificationEngine:
    """
    Orchestrates sandboxed execution and generates the verified final verdict.
    """
    def execute_verification(self, pr_data: Dict[str, Any], ai_review: Dict[str, Any], test_data: Dict[str, Any]) -> Dict[str, Any]:
        pr_id = pr_data["pr_id"]
        original_code = pr_data.get("original_code") or pr_data.get("diff", "")
        proposed_fix = ai_review.get("proposed_fix") or original_code
        test_code = test_data["test_code"]

        # Defect D-04 Fix: Archive previous verdict before re-running
        db.archive_pr_verdict(pr_id)

        start_time = time.time()

        # Run 1: Original Code + Test Suite
        orig_res = run_in_sandbox(original_code, test_code, timeout=SANDBOX_TIMEOUT_SECONDS)

        # Run 2: Proposed Fix + Test Suite
        fix_res = run_in_sandbox(proposed_fix, test_code, timeout=SANDBOX_TIMEOUT_SECONDS)

        exec_time_ms = (time.time() - start_time) * 1000.0

        # Classify outcomes
        case_code, final_verdict, reason = classify(orig_res, fix_res)

        # Record verification run
        run_id = f"run_{pr_id}_{int(datetime.now().timestamp()*1000)}"
        db.execute_write(
            """
            INSERT INTO verification_runs (
                run_id, pr_id, test_id,
                original_passed, original_failed, original_errors,
                fix_passed, fix_failed, fix_errors,
                case_classified, execution_time_ms, executed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                run_id, pr_id, test_data["test_id"],
                orig_res["passed"], orig_res["failed"], orig_res["errors"],
                fix_res["passed"], fix_res["failed"], fix_res["errors"],
                case_code, exec_time_ms
            )
        )

        # Insert or update final verdict
        verdict_id = f"verdict_{pr_id}_{int(datetime.now().timestamp()*1000)}"
        existing_verdict = db.query_one("SELECT * FROM final_verdicts WHERE pr_id = ?", (pr_id,))
        if existing_verdict:
            db.execute_write(
                """
                UPDATE final_verdicts
                SET final_verdict = ?, decision_reason = ?, case_code = ?, confidence_score = 1.0, created_at = CURRENT_TIMESTAMP
                WHERE pr_id = ?
                """,
                (final_verdict, reason, case_code, pr_id)
            )
        else:
            db.execute_write(
                """
                INSERT INTO final_verdicts (
                    verdict_id, pr_id, original_verdict, final_verdict, decision_reason, case_code, confidence_score, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 1.0, CURRENT_TIMESTAMP)
                """,
                (verdict_id, pr_id, ai_review["initial_verdict"], final_verdict, reason, case_code)
            )

        # Update pull request status
        new_pr_status = "VERIFIED" if case_code != "CASE_4" else "ESCALATED"
        db.execute_write("UPDATE pull_requests SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE pr_id = ?", (new_pr_status, pr_id))

        # Log audit
        db.log_audit(
            pr_id=pr_id,
            stage="VERIFICATION",
            action="VERDICT_FINALIZED",
            details=f"Final Verdict: {final_verdict} ({case_code}). {reason}",
            status="SUCCESS"
        )

        # Notifications
        notif_msg = f"PR #{pr_data.get('pr_number')} verified as {final_verdict} ({case_code})."
        db.create_notification(role="DEVELOPER", pr_id=pr_id, title=f"Verdict: {final_verdict}", message=notif_msg)
        if case_code == "CASE_4":
            db.create_notification(role="REVIEWER", pr_id=pr_id, title="Human Review Required", message=f"PR #{pr_data.get('pr_number')} escalated to Reviewer.")

        return {
            "run_id": run_id,
            "pr_id": pr_id,
            "case_code": case_code,
            "original_verdict": ai_review["initial_verdict"],
            "final_verdict": final_verdict,
            "decision_reason": reason,
            "original_results": orig_res,
            "fix_results": fix_res,
            "execution_time_ms": exec_time_ms
        }

verification_engine = VerificationEngine()
