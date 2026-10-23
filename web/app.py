"""
ContextGuard Web Dashboard & API Server.
Simplified, clean interface for AI Code Review Fact-Checking.
"""
import os
import sys
import time
from flask import Flask, render_template, request, jsonify, redirect, url_for

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from contextguard.db import db
from contextguard.pipeline import pipeline_runner
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
    repo_count = 0
    pr_count = 0
    try:
        db.query_one("SELECT 1")
        repo_count = len(db.query_all("SELECT repo_id FROM repositories"))
        pr_count = len(db.query_all("SELECT pr_id FROM pull_requests"))
    except Exception:
        db_ok = False

    return jsonify({
        "status": "ok" if db_ok else "degraded",
        "database": DB_TYPE,
        "database_connected": db_ok,
        "llm_provider": LLM_PROVIDER,
        "uptime_seconds": round(uptime, 2),
        "connected_repositories": repo_count,
        "total_pull_requests": pr_count
    })

# ----------------- Main Route -----------------
@app.route("/")
def index():
    return redirect(url_for("developer_view"))

# ----------------- Code Verifier View -----------------
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
        recent_prs=recent_prs,
        selected_pr=selected_pr,
        evidence=evidence,
        mock_prs=MOCK_PRS
    )

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

# ----------------- Reset Database Utility -----------------
@app.route("/api/reset_prs", methods=["POST"])
def reset_prs():
    db.reset_database()
    return jsonify({"status": "success", "message": "Database and pull request cache reset."})

if __name__ == "__main__":
    print(f"Starting ContextGuard Web Dashboard on http://127.0.0.1:{PORT}")
    app.run(host="127.0.0.1", port=PORT, debug=DEBUG)
