import os
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Database
DB_TYPE = os.environ.get("DATABASE_TYPE", "duckdb").lower()
DUCKDB_PATH = str(DATA_DIR / "contextguard.duckdb")
SQLITE_PATH = str(DATA_DIR / "contextguard.sqlite3")

# LLM Configuration
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "mock").lower()
LLM_MODEL = os.environ.get("LLM_MODEL", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# GitHub API
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Pipeline Budgets & Timeouts
PIPELINE_TIMEOUT_SECONDS = float(os.environ.get("PIPELINE_TIMEOUT", "60.0"))
SANDBOX_TIMEOUT_SECONDS = float(os.environ.get("SANDBOX_TIMEOUT", "5.0"))
RETRIEVAL_TOP_K = int(os.environ.get("RETRIEVAL_TOP_K", "5"))

# Flask Web Server
SECRET_KEY = os.environ.get("SECRET_KEY", "contextguard-secret-key-2026")
PORT = int(os.environ.get("PORT", "5000"))
DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1")
