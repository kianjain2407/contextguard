import os
import json
import sqlite3
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False

from .config import DUCKDB_PATH, SQLITE_PATH, DB_TYPE

_DB_LOCK = threading.RLock()

class DatabaseManager:
    """
    Database Manager with DuckDB primary engine and SQLite fallback.
    Implements append-only evidence archiving (Defect D-04 resolution).
    """
    def __init__(self, db_path: Optional[str] = None, use_sqlite: bool = False):
        self.use_sqlite = use_sqlite or not HAS_DUCKDB or DB_TYPE == "sqlite"
        self.db_path = db_path or (SQLITE_PATH if self.use_sqlite else DUCKDB_PATH)
        self._init_db()

    def _get_connection(self):
        if self.use_sqlite:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn
        else:
            return duckdb.connect(self.db_path)

    def _init_db(self):
        with _DB_LOCK:
            conn = self._get_connection()
            cursor = conn.cursor() if self.use_sqlite else conn

            statements = [
                """
                CREATE TABLE IF NOT EXISTS repositories (
                    repo_id VARCHAR PRIMARY KEY,
                    owner VARCHAR NOT NULL,
                    name VARCHAR NOT NULL,
                    default_branch VARCHAR DEFAULT 'main',
                    status VARCHAR DEFAULT 'connected',
                    allow_paths VARCHAR DEFAULT '',
                    deny_paths VARCHAR DEFAULT '',
                    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS pull_requests (
                    pr_id VARCHAR PRIMARY KEY,
                    repo_id VARCHAR,
                    pr_number INTEGER NOT NULL,
                    title VARCHAR NOT NULL,
                    description TEXT,
                    author VARCHAR NOT NULL,
                    diff TEXT NOT NULL,
                    target_file VARCHAR,
                    status VARCHAR DEFAULT 'PENDING',
                    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS ai_reviews (
                    review_id VARCHAR PRIMARY KEY,
                    pr_id VARCHAR,
                    provider VARCHAR NOT NULL,
                    model VARCHAR,
                    initial_verdict VARCHAR NOT NULL,
                    explanation TEXT,
                    proposed_fix TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS retrieved_contexts (
                    context_id VARCHAR PRIMARY KEY,
                    pr_id VARCHAR,
                    retrieval_mode VARCHAR NOT NULL,
                    hyde_query TEXT,
                    snippet_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS retrieved_snippets (
                    snippet_id VARCHAR PRIMARY KEY,
                    context_id VARCHAR,
                    file_path VARCHAR NOT NULL,
                    identifier VARCHAR NOT NULL,
                    snippet_type VARCHAR NOT NULL,
                    content TEXT NOT NULL,
                    dense_rank INTEGER,
                    sparse_rank INTEGER,
                    rrf_score DOUBLE,
                    is_restricted BOOLEAN DEFAULT FALSE
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS synthesized_tests (
                    test_id VARCHAR PRIMARY KEY,
                    pr_id VARCHAR,
                    test_code TEXT NOT NULL,
                    parsed_examples_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS verification_runs (
                    run_id VARCHAR PRIMARY KEY,
                    pr_id VARCHAR,
                    test_id VARCHAR,
                    original_passed INTEGER DEFAULT 0,
                    original_failed INTEGER DEFAULT 0,
                    original_errors INTEGER DEFAULT 0,
                    fix_passed INTEGER DEFAULT 0,
                    fix_failed INTEGER DEFAULT 0,
                    fix_errors INTEGER DEFAULT 0,
                    case_classified VARCHAR NOT NULL,
                    execution_time_ms DOUBLE,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS final_verdicts (
                    verdict_id VARCHAR PRIMARY KEY,
                    pr_id VARCHAR UNIQUE,
                    original_verdict VARCHAR NOT NULL,
                    final_verdict VARCHAR NOT NULL,
                    decision_reason TEXT NOT NULL,
                    case_code VARCHAR NOT NULL,
                    confidence_score DOUBLE DEFAULT 1.0,
                    is_overridden BOOLEAN DEFAULT FALSE,
                    overridden_by VARCHAR,
                    override_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS verdict_archives (
                    archive_id VARCHAR PRIMARY KEY,
                    pr_id VARCHAR NOT NULL,
                    previous_verdict VARCHAR NOT NULL,
                    archived_tests TEXT,
                    archived_run_details TEXT,
                    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    log_id VARCHAR PRIMARY KEY,
                    pr_id VARCHAR,
                    stage VARCHAR NOT NULL,
                    action VARCHAR NOT NULL,
                    details TEXT,
                    status VARCHAR NOT NULL,
                    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS notifications (
                    notif_id VARCHAR PRIMARY KEY,
                    role VARCHAR NOT NULL,
                    pr_id VARCHAR,
                    title VARCHAR NOT NULL,
                    message TEXT NOT NULL,
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            ]

            for stmt in statements:
                if self.use_sqlite:
                    cursor.execute(stmt)
                else:
                    conn.execute(stmt)

            if self.use_sqlite:
                conn.commit()
                conn.close()
            else:
                conn.close()

    def execute_write(self, query: str, params: tuple = ()) -> None:
        with _DB_LOCK:
            conn = self._get_connection()
            if self.use_sqlite:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                conn.close()
            else:
                conn.execute(query, params)
                conn.close()

    def query_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        with _DB_LOCK:
            conn = self._get_connection()
            if self.use_sqlite:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return rows
            else:
                rel = conn.execute(query, params)
                df = rel.df()
                conn.close()
                return df.to_dict(orient="records")

    def query_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        rows = self.query_all(query, params)
        return rows[0] if rows else None

    # Defect D-04: Evidence Immutability / Archiving
    def archive_pr_verdict(self, pr_id: str) -> None:
        """
        Archives existing verdict, tests, and verification runs before re-running a PR.
        Guarantees that historical evidence is never lost.
        """
        current_verdict = self.query_one("SELECT * FROM final_verdicts WHERE pr_id = ?", (pr_id,))
        if not current_verdict:
            return

        tests = self.query_all("SELECT * FROM synthesized_tests WHERE pr_id = ?", (pr_id,))
        runs = self.query_all("SELECT * FROM verification_runs WHERE pr_id = ?", (pr_id,))

        archive_id = f"arch_{pr_id}_{int(datetime.now().timestamp()*1000)}"
        archived_tests = json.dumps(tests, default=str)
        archived_runs = json.dumps(runs, default=str)

        self.execute_write(
            """
            INSERT INTO verdict_archives (archive_id, pr_id, previous_verdict, archived_tests, archived_run_details, archived_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (archive_id, pr_id, current_verdict.get("final_verdict", "UNKNOWN"), archived_tests, archived_runs)
        )

        self.log_audit(
            pr_id=pr_id,
            stage="ARCHIVE",
            action="ARCHIVE_EVIDENCE",
            details=f"Archived previous verdict {current_verdict.get('final_verdict')} with {len(tests)} tests and {len(runs)} runs.",
            status="SUCCESS"
        )

    def log_audit(self, pr_id: Optional[str], stage: str, action: str, details: str, status: str = "SUCCESS") -> None:
        log_id = f"log_{int(datetime.now().timestamp()*1000)}_{os.urandom(2).hex()}"
        self.execute_write(
            """
            INSERT INTO audit_log (log_id, pr_id, stage, action, details, status, logged_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (log_id, pr_id, stage, action, details, status)
        )

    def create_notification(self, role: str, pr_id: Optional[str], title: str, message: str) -> None:
        notif_id = f"notif_{int(datetime.now().timestamp()*1000)}_{os.urandom(2).hex()}"
        self.execute_write(
            """
            INSERT INTO notifications (notif_id, role, pr_id, title, message, is_read, created_at)
            VALUES (?, ?, ?, ?, ?, FALSE, CURRENT_TIMESTAMP)
            """,
            (notif_id, role.upper(), pr_id, title, message)
        )

    def reset_database(self) -> None:
        """Resets all tables for clean demo and test executions."""
        with _DB_LOCK:
            conn = self._get_connection()
            tables = [
                "repositories", "pull_requests", "ai_reviews", "retrieved_contexts",
                "retrieved_snippets", "synthesized_tests", "verification_runs",
                "final_verdicts", "verdict_archives", "audit_log", "notifications"
            ]
            for t in tables:
                if self.use_sqlite:
                    conn.cursor().execute(f"DROP TABLE IF EXISTS {t}")
                else:
                    conn.execute(f"DROP TABLE IF EXISTS {t}")
            if self.use_sqlite:
                conn.commit()
            conn.close()
            self._init_db()

# Global default instance
db = DatabaseManager()
