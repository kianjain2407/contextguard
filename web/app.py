"""
ContextGuard Web Dashboard & API Server.
Provides 6 role-based views (Developer, Reviewer, QA, Security, Manager, Admin),
notifications center, and /health monitoring endpoint.
"""
import os
import sys
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from contextguard.db import db
from contextguard.pipeline import pipeline_runner
from contextguard.evaluation import run_evaluation, run_retrieval_ablation
from contextguard.repo_index import RepositoryIndexer
from contextguard.github_client import MOCK_PRS
from contextguard.config import SECRET_KEY, PORT, DEBUG, LLM_PROVIDER, DB_TYPE

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)
app.secret_key = SECRET_KEY
APP_START_TIME = time.time()

# ----------------- Health Check -----------------
@app.route("/health")
def health_check():
    """System health check endpoint."""
    uptime = time.time() - APP_START_TIME
    db_ok = True
    try:
        db.query_one("SELECT 1")
    except Exception:
        db_ok = False

    repo_count = len(db.query_all("SELECT * FROM repositories"))
    pr_count = len(db.query_all("SELECT * FROM pull_requests"))

    return jsonify({
        "status": "ok" if db_ok else "degraded",
        "database": DB_TYPE,
        "database_connected": db_ok,
        "llm_provider": LLM_PROVIDER,
        "uptime_seconds": round(uptime, 2),
        "connected_repositories": repo_count,
        "total_pull_requests": pr_count,
        "active_runs": 0
    })

# ----------------- Navigation Redirect -----------------
@app.route("/")
def index():
    return redirect(url_for("developer_view"))

# ----------------- Role 1: Developer View -----------------
@app.route("/developer")
def developer_view():
    recent_prs = db.query_all(
        """
        SELECT pr.*, v.final_verdict, v.case_code, v.decision_reason
        FROM pull_requests pr
        LEFT JOIN final_verdicts v ON pr.pr_id = v.pr_id
        ORDER BY pr.submitted_at DESC
        """
    )
    selected_pr_id = request.args.get("pr_id")
    selected_pr = None
    evidence = {}

    if selected_pr_id:
        selected_pr = db.query_one("SELECT * FROM pull_requests WHERE pr_id = ?", (selected_pr_id,))
        if selected_pr:
            review = db.query_one("SELECT * FROM ai_reviews WHERE pr_id = ? ORDER BY created_at DESC", (selected_pr_id,))
            verdict = db.query_one("SELECT * FROM final_verdicts WHERE pr_id = ?", (selected_pr_id,))
            tests = db.query_one("SELECT * FROM synthesized_tests WHERE pr_id = ? ORDER BY created_at DESC", (selected_pr_id,))
            run = db.query_one("SELECT * FROM verification_runs WHERE pr_id = ? ORDER BY executed_at DESC", (selected_pr_id,))
            snippets = db.query_all(
                """
                SELECT s.* FROM retrieved_snippets s
                JOIN retrieved_contexts c ON s.context_id = c.context_id
                WHERE c.pr_id = ?
                """,
                (selected_pr_id,)
            )
            evidence = {
                "review": review,
                "verdict": verdict,
                "tests": tests,
                "run": run,
                "snippets": snippets
            }

    return render_template(
        "developer.html",
        role="DEVELOPER",
        recent_prs=recent_prs,
        selected_pr=selected_pr,
        evidence=evidence,
        mock_prs=MOCK_PRS
    )

# ----------------- Role 2: Reviewer View -----------------
@app.route("/reviewer")
def reviewer_view():
    flagged_prs = db.query_all(
        """
        SELECT pr.*, v.final_verdict, v.case_code, v.decision_reason, v.is_overridden, v.overridden_by,
               r.initial_verdict, r.proposed_fix
        FROM pull_requests pr
        JOIN final_verdicts v ON pr.pr_id = v.pr_id
        LEFT JOIN ai_reviews r ON pr.pr_id = r.pr_id
        WHERE v.final_verdict = 'NON_COMPLIANT' OR v.case_code = 'CASE_4'
        ORDER BY pr.submitted_at DESC
        """
    )
    return render_template("reviewer.html", role="REVIEWER", flagged_prs=flagged_prs)

@app.route("/api/override_verdict", methods=["POST"])
def override_verdict():
    data = request.json or request.form
    pr_id = data.get("pr_id")
    new_verdict = data.get("new_verdict")
    reviewer_name = data.get("reviewer_name", "Human Reviewer")
    reason = data.get("reason", "Manual reviewer override based on code inspection.")

    if not pr_id or not new_verdict:
        return jsonify({"error": "Missing pr_id or new_verdict"}), 400

    db.execute_write(
        """
        UPDATE final_verdicts
        SET final_verdict = ?, is_overridden = TRUE, overridden_by = ?, override_reason = ?, created_at = CURRENT_TIMESTAMP
        WHERE pr_id = ?
        """,
        (new_verdict, reviewer_name, reason, pr_id)
    )
    db.execute_write("UPDATE pull_requests SET status = 'OVERRIDDEN' WHERE pr_id = ?", (pr_id,))
    db.log_audit(pr_id=pr_id, stage="REVIEWER", action="OVERRIDE_VERDICT", details=f"Overridden to {new_verdict} by {reviewer_name}: {reason}", status="SUCCESS")
    db.create_notification(role="DEVELOPER", pr_id=pr_id, title="Verdict Overridden", message=f"Reviewer {reviewer_name} updated verdict to {new_verdict}.")

    return jsonify({"status": "success", "pr_id": pr_id, "final_verdict": new_verdict})

# ----------------- Role 3: QA / Test Auditor View -----------------
@app.route("/qa")
def qa_view():
    test_records = db.query_all(
        """
        SELECT t.*, pr.title, pr.pr_number, r.original_passed, r.original_failed, r.original_errors,
               r.fix_passed, r.fix_failed, r.fix_errors, r.case_classified, r.execution_time_ms
        FROM synthesized_tests t
        JOIN pull_requests pr ON t.pr_id = pr.pr_id
        LEFT JOIN verification_runs r ON t.test_id = r.test_id
        ORDER BY t.created_at DESC
        """
    )
    return render_template("qa.html", role="QA", test_records=test_records)

# ----------------- Role 4: Security & Compliance View -----------------
@app.route("/security")
def security_view():
    repos = db.query_all("SELECT * FROM repositories")
    audit_events = db.query_all("SELECT * FROM audit_log ORDER BY logged_at DESC LIMIT 30")
    return render_template("security.html", role="SECURITY", repos=repos, audit_events=audit_events)

# ----------------- Role 5: Engineering Manager View -----------------
@app.route("/manager")
def manager_view():
    eval_data = run_evaluation()
    ablation_data = run_retrieval_ablation()
    all_verdicts = db.query_all(
        """
        SELECT v.*, pr.title, pr.pr_number
        FROM final_verdicts v
        JOIN pull_requests pr ON v.pr_id = pr.pr_id
        ORDER BY v.created_at DESC
        """
    )
    return render_template(
        "manager.html",
        role="MANAGER",
        eval_data=eval_data,
        ablation_data=ablation_data,
        all_verdicts=all_verdicts
    )

# ----------------- Role 6: Repository Admin View -----------------
@app.route("/admin")
def admin_view():
    repos = db.query_all("SELECT * FROM repositories")
    return render_template("admin.html", role="ADMIN", repos=repos)

@app.route("/api/update_scope", methods=["POST"])
def update_scope():
    data = request.json or request.form
    repo_id = data.get("repo_id")
    allow_paths = data.get("allow_paths", "")
    deny_paths = data.get("deny_paths", "")

    if not repo_id:
        return jsonify({"error": "Missing repo_id"}), 400

    db.execute_write(
        "UPDATE repositories SET allow_paths = ?, deny_paths = ? WHERE repo_id = ?",
        (allow_paths, deny_paths, repo_id)
    )
    db.log_audit(pr_id=None, stage="ADMIN", action="UPDATE_SCOPE", details=f"Updated scope for {repo_id}. Allow: {allow_paths}, Deny: {deny_paths}", status="SUCCESS")

    return jsonify({"status": "success", "repo_id": repo_id})

@app.route("/api/reset_prs", methods=["POST"])
def reset_prs():
    db.reset_database()
    return jsonify({"status": "success", "message": "Database and pull request cache reset."})

# ----------------- Notifications Feed -----------------
@app.route("/notifications")
def notifications_view():
    role_filter = request.args.get("role", "").upper()
    if role_filter:
        notifs = db.query_all("SELECT * FROM notifications WHERE role = ? ORDER BY created_at DESC", (role_filter,))
    else:
        notifs = db.query_all("SELECT * FROM notifications ORDER BY created_at DESC LIMIT 50")
    return render_template("notifications.html", notifs=notifs, role_filter=role_filter)

# ----------------- PR Submission API -----------------
@app.route("/api/submit_pr", methods=["POST"])
def api_submit_pr():
    data = request.json or request.form
    pr_url = data.get("pr_url")
    if not pr_url:
        return jsonify({"error": "Missing pr_url"}), 400

    try:
        result = pipeline_runner.run(pr_url, force_refresh=True)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "ERROR", "error": str(e)}), 500

if __name__ == "__main__":
    print(f"Starting ContextGuard Web Dashboard on http://127.0.0.1:{PORT}")
    app.run(host="127.0.0.1", port=PORT, debug=DEBUG)
