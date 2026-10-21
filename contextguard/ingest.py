"""
Stage 1: PR Intake and Ingestion.
Validates PR URL, ingests diff & metadata, and persists to DuckDB.
Resolves Defect D-05 (concurrency locking).
"""
import threading
from typing import Dict, Any
from .github_client import github_client
from .db import db

_LOCK_REGISTRY = {}
_REGISTRY_LOCK = threading.Lock()

def get_pr_lock(pr_id: str) -> threading.RLock:
    """Gets or creates a re-entrant lock per PR to ensure concurrency safety (fixes D-05)."""
    with _REGISTRY_LOCK:
        if pr_id not in _LOCK_REGISTRY:
            _LOCK_REGISTRY[pr_id] = threading.RLock()
        return _LOCK_REGISTRY[pr_id]

def ingest_pull_request(pr_url: str) -> Dict[str, Any]:
    """
    Ingests a pull request from a GitHub URL or identifier.
    Validates the URL, fetches diff & metadata, and stores into the database.
    """
    parsed = github_client.parse_pr_url(pr_url)
    owner = parsed["owner"]
    repo = parsed["repo"]
    pr_number = parsed["pr_number"]

    repo_id = f"{owner}/{repo}"
    pr_id = f"{repo_id}#{pr_number}"

    lock = get_pr_lock(pr_id)
    with lock:
        # Fetch diff, description, author
        pr_data = github_client.fetch_pr_data(pr_url)

        # 1. Ensure repository record exists
        existing_repo = db.query_one("SELECT * FROM repositories WHERE repo_id = ?", (repo_id,))
        if not existing_repo:
            db.execute_write(
                """
                INSERT INTO repositories (repo_id, owner, name, default_branch, status, allow_paths, deny_paths, connected_at)
                VALUES (?, ?, ?, 'main', 'connected', 'shopkit/, tests/', 'shopkit/internal/', CURRENT_TIMESTAMP)
                """,
                (repo_id, owner, repo)
            )

        # 2. Insert or update pull request record
        existing_pr = db.query_one("SELECT * FROM pull_requests WHERE pr_id = ?", (pr_id,))
        if existing_pr:
            db.execute_write(
                """
                UPDATE pull_requests
                SET title = ?, description = ?, author = ?, diff = ?, target_file = ?, status = 'PROCESSING', updated_at = CURRENT_TIMESTAMP
                WHERE pr_id = ?
                """,
                (pr_data["title"], pr_data["description"], pr_data["author"], pr_data["diff"], pr_data.get("target_file", ""), pr_id)
            )
        else:
            db.execute_write(
                """
                INSERT INTO pull_requests (pr_id, repo_id, pr_number, title, description, author, diff, target_file, status, submitted_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PROCESSING', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (pr_id, repo_id, pr_number, pr_data["title"], pr_data["description"], pr_data["author"], pr_data["diff"], pr_data.get("target_file", ""))
            )

        # 3. Log audit entry & create notification
        db.log_audit(
            pr_id=pr_id,
            stage="INTAKE",
            action="INGEST_PR",
            details=f"Ingested PR #{pr_number} '{pr_data['title']}' by {pr_data['author']}",
            status="SUCCESS"
        )
        db.create_notification(
            role="DEVELOPER",
            pr_id=pr_id,
            title=f"PR #{pr_number} Submitted",
            message=f"Pull request '{pr_data['title']}' has been ingested and queued for verification."
        )

        pr_record = db.query_one("SELECT * FROM pull_requests WHERE pr_id = ?", (pr_id,))
        return {
            "pr_id": pr_id,
            "repo_id": repo_id,
            "pr_number": pr_number,
            "title": pr_data["title"],
            "description": pr_data["description"],
            "author": pr_data["author"],
            "diff": pr_data["diff"],
            "target_file": pr_data.get("target_file", ""),
            "original_code": pr_data.get("original_code", ""),
            "proposed_fix": pr_data.get("proposed_fix", "")
        }
