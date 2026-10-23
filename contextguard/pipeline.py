"""
Pipeline Orchestration for ContextGuard.
Wires Stages 1-5 together, enforcing:
- 60-second budget
- Fail-open resilience (unverified AI verdict fallback)
- Resumption from stage
- Per-PR concurrency locking (Defect D-05)
- Full audit trail
"""
import time
from datetime import datetime
from typing import Dict, Any, Optional

from .db import db
from .ingest import ingest_pull_request, get_pr_lock
from .llm import perform_ai_review
from .retrieval import execute_repository_retrieval
from .testgen import synthesize_verification_tests
from .verification import verification_engine
from .config import PIPELINE_TIMEOUT_SECONDS

class PipelineRunner:
    """
    Main orchestration engine executing the 5-stage ContextGuard pipeline.
    """
    def run(self, pr_url: str, force_refresh: bool = False, retrieval_mode: str = "full") -> Dict[str, Any]:
        start_time = time.time()

        # Step 0: Ingest & get PR identifier
        pr_id = None  # Initialize early to prevent UnboundLocalError in except block
        try:
            pr_data = ingest_pull_request(pr_url)
            pr_id = pr_data["pr_id"]
        except Exception as e:
            db.log_audit(pr_id=None, stage="INTAKE", action="INGEST_FAILED", details=str(e), status="ERROR")
            raise

        lock = get_pr_lock(pr_id)
        with lock:
            # Check 60-second budget
            def check_timeout():
                if (time.time() - start_time) > PIPELINE_TIMEOUT_SECONDS:
                    raise TimeoutError(f"ContextGuard pipeline exceeded {PIPELINE_TIMEOUT_SECONDS}s budget.")

            try:
                # Stage 1: Check if already verified and not forcing refresh
                if not force_refresh:
                    existing_verdict = db.query_one("SELECT * FROM final_verdicts WHERE pr_id = ?", (pr_id,))
                    if existing_verdict:
                        return {
                            "status": "CACHED",
                            "pr_id": pr_id,
                            "final_verdict": existing_verdict["final_verdict"],
                            "case_code": existing_verdict["case_code"],
                            "decision_reason": existing_verdict["decision_reason"],
                            "duration_seconds": time.time() - start_time
                        }

                check_timeout()

                # Stage 2: Initial AI Review
                ai_review = None
                if not force_refresh:
                    existing_review = db.query_one("SELECT * FROM ai_reviews WHERE pr_id = ? ORDER BY created_at DESC", (pr_id,))
                    if existing_review:
                        ai_review = existing_review

                if not ai_review:
                    ai_review = perform_ai_review(pr_data)

                check_timeout()

                # Fast exit if COMPLIANT: Verification skipped
                if ai_review["initial_verdict"] == "COMPLIANT":
                    verdict_id = f"verdict_{pr_id}_{int(datetime.now().timestamp()*1000)}"
                    reason = "Fast Exit: AI reviewer found no defects; verification filter skipped."
                    db.execute_write(
                        """
                        INSERT INTO final_verdicts (verdict_id, pr_id, original_verdict, final_verdict, decision_reason, case_code, confidence_score, created_at)
                        VALUES (?, ?, 'COMPLIANT', 'COMPLIANT', ?, 'FAST_EXIT', 1.0, CURRENT_TIMESTAMP)
                        ON CONFLICT(pr_id) DO UPDATE SET final_verdict = 'COMPLIANT', decision_reason = excluded.decision_reason, case_code = 'FAST_EXIT'
                        """,
                        (verdict_id, pr_id, reason)
                    )
                    db.execute_write("UPDATE pull_requests SET status = 'VERIFIED' WHERE pr_id = ?", (pr_id,))
                    db.log_audit(pr_id=pr_id, stage="PIPELINE", action="FAST_EXIT", details=reason, status="SUCCESS")

                    return {
                        "status": "COMPLETED",
                        "pr_id": pr_id,
                        "initial_verdict": "COMPLIANT",
                        "final_verdict": "COMPLIANT",
                        "case_code": "FAST_EXIT",
                        "decision_reason": reason,
                        "duration_seconds": time.time() - start_time
                    }

                # Stage 3: Repository Context Retrieval
                snippets = execute_repository_retrieval(pr_data, mode=retrieval_mode)
                check_timeout()

                # Stage 4: Spec-Constrained Test Synthesis
                test_data = synthesize_verification_tests(pr_data, snippets)
                check_timeout()

                # Stage 5: Fix-Guided Verification Filter
                verification_result = verification_engine.execute_verification(pr_data, ai_review, test_data)

                duration = time.time() - start_time
                db.log_audit(
                    pr_id=pr_id,
                    stage="PIPELINE",
                    action="PIPELINE_COMPLETED",
                    details=f"Pipeline finished in {duration:.2f}s with final verdict {verification_result['final_verdict']}",
                    status="SUCCESS"
                )

                return {
                    "status": "COMPLETED",
                    "pr_id": pr_id,
                    "initial_verdict": ai_review["initial_verdict"],
                    "final_verdict": verification_result["final_verdict"],
                    "case_code": verification_result["case_code"],
                    "decision_reason": verification_result["decision_reason"],
                    "retrieved_snippets_count": len(snippets),
                    "synthesized_tests_count": test_data["parsed_examples_count"],
                    "duration_seconds": duration,
                    "evidence": {
                        "ai_review": ai_review,
                        "snippets": snippets,
                        "test_code": test_data["test_code"],
                        "original_results": verification_result["original_results"],
                        "fix_results": verification_result["fix_results"]
                    }
                }

            except Exception as ex:
                # Fail-open behavior: Never block developer CI
                duration = time.time() - start_time
                fallback_verdict = ai_review.get("initial_verdict", "UNVERIFIED") if ai_review else "UNVERIFIED_AI_VERDICT"
                fail_open_reason = f"Fail-Open Triggered: Pipeline error encountered ({str(ex)}). Reverting to unverified AI verdict."

                db.log_audit(
                    pr_id=pr_id,
                    stage="FAIL_OPEN",
                    action="FAIL_OPEN_FALLBACK",
                    details=fail_open_reason,
                    status="WARNING"
                )
                db.create_notification(
                    role="REVIEWER",
                    pr_id=pr_id,
                    title="Pipeline Fail-Open Alert",
                    message=f"PR {pr_id} encountered an error: {str(ex)}. Reviewer verification recommended."
                )

                return {
                    "status": "FAIL_OPEN",
                    "pr_id": pr_id,
                    "initial_verdict": fallback_verdict,
                    "final_verdict": fallback_verdict,
                    "case_code": "FAIL_OPEN",
                    "decision_reason": fail_open_reason,
                    "error": str(ex),
                    "duration_seconds": duration
                }

pipeline_runner = PipelineRunner()
