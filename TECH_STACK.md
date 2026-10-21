# ContextGuard: Technology Stack & Architectural Decision Record (ADR)

**Project:** ContextGuard — Repository-Context-Aware Verification Filtering for Reliable LLM-Based Code Review  
**Academic Context:** Software Engineering Laboratory | Group B054, B062, B131  
**Document Version:** 1.0 (October 2026)

---

## 1. Executive Summary & Core Tech Stack Matrix

| Layer | Selected Technology | Alternative Considered | Primary Justification |
| :--- | :--- | :--- | :--- |
| **Backend Runtime** | **Python 3.10+** | Node.js, Go | Native ecosystem for LLM orchestration, AST parsing, AST tokenization, vector manipulation, and `unittest` test execution. |
| **Web Server / API** | **Flask + Jinja2** | FastAPI, Django | Lightweight, zero-boilerplate, server-side rendered with Jinja2 for fast rendering of 6 role views without complex Node build pipelines. |
| **Production WSGI** | **Waitress** | Gunicorn, uWSGI | Cross-platform (Windows & Linux native), lightweight, multi-threaded production HTTP server (`wsgi.py`). |
| **Primary Database** | **DuckDB** *(In-process OLAP/Relational)* | PostgreSQL, SQLite, MySQL | Columnar analytical performance for audit logs and verification records; embedded serverless execution (zero setup). |
| **Database Fallback** | **SQLite3** | None | Built into Python standard library; zero-dependency fallback if DuckDB binary cannot be loaded. |
| **Firebase?** | **NO (Explicitly Rejected)** | Firebase Firestore / Realtime DB | Violates strict security NFR (proprietary source code must stay on-premise); introduces cloud vendor lock-in and network latency. |
| **Vector Database** | **ChromaDB** *(Embedded)* | Pinecone, Qdrant | Runs completely in-process; vector embeddings stay local; stores function & test vectors without external server. |
| **Vector Fallback** | **NumPy Cosine Similarity** | Faiss | Guarantees semantic retrieval works even in stripped offline environments without C++ vector bindings. |
| **Keyword Search** | **Okapi BM25** *(Inverted Index)* | Elasticsearch | Algorithmic sparse search over identifiers and docstrings; zero external daemon required. |
| **LLM Inference** | **Multi-Provider Engine**<br>(Mock, Gemini, Claude, OpenAI) | Single-vendor SDK | Default **Mock mode** allows 100% test coverage with zero API keys; pluggable API keys for live model execution. |
| **Code Execution Sandbox**| **Python `subprocess` + Hard Timeout** | Docker-in-Docker, PySandbox | Lightweight isolated process isolation with 5-second execution watchdogs preventing runaway infinite loops. |
| **Frontend UI** | **Vanilla HTML5 + Modern CSS3 + JS** | React, Vue, TailwindCSS | Native CSS3 glassmorphism, responsive grid, zero build-step overhead, instant load times, clean Jinja2 templating. |
| **Testing Framework** | **Python `unittest` + Flask Test Client** | Pytest | Built into Python 3.12; strict xUnit compliance as required by Software Engineering Lab Experiment 9. |
| **Containerization** | **Docker + Dockerfile** | Kubernetes | Single-container reproducible environment for evaluation, CI/CD, and demo execution. |

---

## 2. In-Depth Architectural Decisions

### 2.1 The Database Decision: Why DuckDB & SQLite (And NOT Firebase)

#### Are we using Firebase?
> **NO, Firebase is NOT used in ContextGuard.**

#### Why Firebase was explicitly rejected:
1. **Security & Boundary Enforcement (Exp 2 NFR)**:
   - In Software Engineering Lab Experiment 2, the primary Security Non-Functional Requirement mandates:
     > *"All repository code, diffs, and proprietary logic pulled into the retrieval/generation pipeline must stay strictly within the customer's own infrastructure boundary. Proprietary source code is never sent to an unauthorized cloud destination."*
   - Firebase (Google Cloud Firestore / Realtime Database) is a public cloud Backend-as-a-Service (BaaS). Storing PR diffs, proprietary repository code, synthesized tests, and audit logs on Google Cloud violates corporate data sovereignty and on-premise enterprise compliance policies.
2. **Zero-Configuration & Offline Portability**:
   - The project must run out of the box with `python run_demo.py --reset` or `python app.py` without requiring the evaluator, professor, or developer to create a Google Cloud project, configure service account JSON keys, or pay cloud subscription fees.
   - DuckDB and SQLite require zero external setup: database files (`data/contextguard.duckdb`) are created and managed automatically in the local workspace.
3. **Latency & Performance Budget**:
   - ContextGuard operates under a strict **60-second total pipeline budget**.
   - Cloud roundtrips to Firebase for dozens of intermediate verification steps (intake $\to$ review $\to$ retrieval $\to$ test synthesis $\to$ verification run $\to$ audit logs) add latency and introduce potential network points of failure. Embedded DuckDB executes analytical queries in microseconds in-memory.
4. **Append-Only Immutability & Audit Trail**:
   - DuckDB's relational ACID guarantees make atomic archiving (`verdict_archives`) and relational joins across PRs, reviews, and tests simple, robust, and verifiable without complex NoSQL document de-normalization.

---

### 2.2 Primary Database: DuckDB Architecture
**DuckDB** is an embedded analytical SQL database engine often described as *"the SQLite for Analytics"*.

* **Why DuckDB is ideal for ContextGuard**:
  - **Embedded**: Runs directly inside the Python process (`import duckdb`). No server daemon, no port binding, no user management.
  - **Analytical Performance**: ContextGuard's Engineering Manager dashboard requires real-time aggregations (False Positive rates, False Negative rates, average latency, ablation comparisons across multiple runs). DuckDB's columnar execution engine processes these aggregations orders of magnitude faster than traditional row-oriented databases.
  - **Relational Integrity**: Supports full SQL standards, foreign keys, transactions, and structured schemas across all 11 tables.
* **Automatic SQLite3 Fallback**:
  - If DuckDB binary wheels are incompatible with a specific environment (e.g., bare-metal architectures), ContextGuard automatically detects the exception and initializes an identical schema on Python's native `sqlite3` driver. The rest of the application code remains 100% agnostic.

---

### 2.3 Backend & Web Framework: Python + Flask + Waitress

* **Backend Core (Python 3.10+)**:
  - Python was selected because the entire LLM, vector retrieval, and code-review ecosystem is built in Python.
  - The target code being analyzed and verified in the "shopkit" benchmark is Python, which enables direct AST parsing (`ast` module) and test execution via `unittest`.
* **Web Framework (Flask)**:
  - Flask provides an un-opinionated, lightweight foundation for routing, session handling, and API endpoints.
  - Jinja2 templates allow clean server-side rendering of the 6 role-based views (Developer, Reviewer, QA, Security, Manager, Admin).
  - Eliminates the need for a separate Node.js server, NPM packages, or frontend bundlers like Webpack or Vite.
* **Production WSGI (Waitress)**:
  - Standard Flask dev servers are single-threaded and not suitable for concurrent requests.
  - Waitress is a pure-Python, multi-threaded production WSGI server that runs seamlessly across both Windows and Linux, executing cleanly via `python wsgi.py`.

---

### 2.4 Retrieval & Search Stack: Hybrid Dense + Sparse + HyDE

ContextGuard's core innovation is retrieving context from the repository without pre-existing test suites:

```
[ Incoming PR Description + Diff ]
               |
               v
  [ HyDE: Hypothetical Ideal Test Generation ]
               |
      +--------+--------+
      |                 |
      v                 v
[ Dense Search ]   [ Sparse Search ]
  (ChromaDB /        (Okapi BM25
   NumPy Dot)        Inverted Index)
      |                 |
      +--------+--------+
               |
               v
   [ Reciprocal Rank Fusion (RRF) ]
               |
               v
   [ Scope Rule Path Filtering ]
               |
               v
 [ Top-5 Relevant Repository Context ]
```

1. **Dense Retrieval (ChromaDB)**:
   - In-memory vector database. Functions, docstrings, and existing test cases are converted into vector embeddings.
   - Fallback: If ChromaDB dependencies are not installed, ContextGuard includes a zero-dependency vectorized cosine similarity engine using NumPy.
2. **Sparse Retrieval (Okapi BM25)**:
   - Code retrieval requires exact keyword matching (variable names, method names, class identifiers) that dense embeddings frequently blur.
   - ContextGuard implements the Okapi BM25 ranking algorithm ($k_1=1.5, b=0.75$) with snake_case and camelCase tokenization directly in Python.
3. **Reciprocal Rank Fusion (RRF)**:
   - Combines dense semantic ranks with sparse keyword ranks using $RRF(d) = \sum \frac{1}{60 + rank(d)}$.
4. **Hypothetical Document Embeddings (HyDE)**:
   - Expands ambiguous PR queries into a synthetic "ideal test case" before vector retrieval, dramatically boosting retrieval of the decisive repository test.

---

### 2.5 Multi-Provider LLM Abstraction Layer

ContextGuard is LLM-agnostic and provides a unified interface across 4 backends:

```
                  +---------------------------+
                  |    LLMProvider (Base)     |
                  +-------------+-------------+
                                |
      +----------------+--------+--------+----------------+
      |                |                 |                |
      v                v                 v                v
[ Mock Provider ] [ Google Gemini ] [ Anthropic Claude ] [ OpenAI ]
(Default / Demo)  (gemini-2.0-flash) (claude-3-5-sonnet)  (gpt-4o)
```

* **Mock Provider (Default)**:
  - **Zero API keys required.**
  - Deterministically scripts the 9 benchmark scenarios from the SE Lab report.
  - Enables instant grading, automated CI/CD test runs, and complete offline functionality.
* **Gemini Provider**: Integrated with Google's Gemini SDK (`google-genai`).
* **Claude Provider**: Integrated with Anthropic's Messages API.
* **OpenAI Provider**: Integrated with OpenAI's Chat Completions API.

---

### 2.6 Frontend Design: Modern Glassmorphic Vanilla Stack

In accordance with modern web engineering standards:
* **No Heavy Node/JS Frameworks**: No React/Vue/Angular build chains; no `node_modules` clutter.
* **Modern CSS3 Design System**:
  - Curated dark-mode palette: Deep slate `#0f172a`, elevated card surfaces `#1e293b`, subtle glassmorphic borders `rgba(255, 255, 255, 0.08)`, and backdrop blur.
  - High-contrast semantic badges: Green `#10b981` (`COMPLIANT`), Coral Red `#ef4444` (`NON_COMPLIANT`), Cyan `#06b6d4` (`CASE_1`), Amber `#f59e0b` (`CASE_2`), Violet `#8b5cf6` (`CASE_4`).
  - Google Fonts: Modern sans-serif typography (*Inter* / *Outfit*).
  - Micro-animations: Smooth transitions on expandable evidence panels, tab switching, and verdict badges.
* **Vanilla JavaScript (`main.js`)**:
  - Handles real-time verification status polling, tab switching between the 6 role views, copy-to-clipboard actions, and manual review overrides.

---

## 3. Configuration & Environment Variables

All system settings are centrally managed via environment variables (with sensible defaults):

```bash
# ==========================================
# ContextGuard System Configuration
# ==========================================

# Database Selection (duckdb | sqlite)
DATABASE_TYPE=duckdb
DATABASE_PATH=data/contextguard.duckdb

# LLM Backend Selection (mock | gemini | anthropic | openai)
LLM_PROVIDER=mock

# API Keys (Only required if LLM_PROVIDER is not 'mock')
GEMINI_API_KEY=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# Model Overrides (Optional)
LLM_MODEL=

# GitHub Live Ingestion (Optional - mock repository used by default)
GITHUB_TOKEN=

# Web Application Settings
SECRET_KEY=contextguard-super-secret-key-2026
PORT=5000
DEBUG=False
```

---

## 4. Dependencies Summary (`requirements.txt`)

```txt
# Web Application & Serving
Flask>=3.0.0
waitress>=3.0.0
jinja2>=3.1.0

# Database & Storage
duckdb>=1.0.0

# Vector & Math Operations
numpy>=1.24.0
chromadb>=0.5.0

# Optional Cloud LLM SDKs
google-genai>=0.1.0
anthropic>=0.25.0
openai>=1.30.0

# HTTP & API Utilities
requests>=2.31.0
```

*(Note: In offline or resource-constrained environments, `duckdb` falls back to standard-library `sqlite3`, `chromadb` falls back to `numpy`, and `LLM_PROVIDER=mock` requires zero external packages).*

---

## 5. Summary: Why This Tech Stack Wins

1. **100% Privacy & On-Premises Compliance**: Code never leaves the local/server boundary; **Firebase and public BaaS are completely avoided**.
2. **Instant Developer Setup**: Clones and runs immediately with zero external dependencies or paid accounts.
3. **Rock-Solid Testability**: Enables all 27 automated tests to execute deterministically in under 5 seconds.
4. **Resilient Architecture**: Dual-engine fallbacks (DuckDB $\to$ SQLite, ChromaDB $\to$ NumPy, Live LLM $\to$ Mock).
5. **Modern User Experience**: Stunning, responsive dark-mode dashboard tailored for all 6 software engineering stakeholders.
