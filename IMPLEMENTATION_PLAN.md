# ContextGuard: Comprehensive Implementation Plan

**Engineering Roadmap, Architectural Design & Phased Construction**  
*Project: ContextGuard — Repository-Context-Aware Verification Filtering for Reliable LLM-Based Code Review*  
*Target Environment: Python 3.10+ | DuckDB / SQLite | ChromaDB / NumPy | Flask | Waitress*

---

## 1. Project Directory Structure

```
c:\Users\Kian\Downloads\se\
│
├── CONTEXTGUARD_SPECIFICATION.md    # Complete system specification & theoretical reference
├── IMPLEMENTATION_PLAN.md           # Step-by-step phased execution roadmap (this document)
├── requirements.txt                 # Project dependencies
├── Dockerfile                       # Containerized production environment
├── wsgi.py                          # Production WSGI entry point (Waitress)
├── run_demo.py                      # CLI runner showcasing all 9 benchmark PRs
│
├── contextguard/                    # Core Python package
│   ├── __init__.py                  # Package initialization
│   ├── config.py                    # Environment settings, thresholds, and paths
│   ├── db.py                        # DuckDB storage layer with SQLite fallback & archival
│   ├── github_client.py             # GitHub REST API client with local mock mode
│   ├── ingest.py                    # Stage 1: PR URL validation, ingestion, and persistence
│   ├── llm.py                       # Stage 2: Multi-backend LLM client (Mock, Gemini, Claude, OpenAI)
│   ├── repo_index.py                # Stage 3: Repository code indexing and scope enforcement
│   ├── retrieval.py                 # Stage 3: Hybrid retriever (Dense + BM25 + RRF + HyDE)
│   ├── testgen.py                   # Stage 4: Spec-constrained unittest test case synthesizer
│   ├── sandbox.py                   # Stage 5: Isolated subprocess execution harness with timeout
│   ├── verification.py              # Stage 5: Four-case formal verification classification logic
│   ├── pipeline.py                  # End-to-end orchestration (60s budget, fail-open, locks)
│   ├── evaluation.py                # Manager metrics, baseline comparison, and ablation studies
│   └── humaneval_baseline.py        # Reproduction baseline for verification filter on benchmark data
│
├── web/                             # Web application layer
│   ├── app.py                       # Flask application with 6 role-based routes & health check
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css            # Modern, dark-mode glassmorphism design system
│   │   └── js/
│   │       └── main.js              # Real-time polling, filters, and dynamic UI interactions
│   └── templates/
│       ├── base.html                # Shared layout, navigation, role selector, and notifications
│       ├── developer.html           # Developer view: PR submission, live verdict, evidence
│       ├── reviewer.html            # Reviewer view: Flagged PRs, diff viewer, override actions
│       ├── qa.html                  # QA view: Synthesized test audit & test execution matrix
│       ├── security.html            # Security view: Scope rules, blocked paths, compliance
│       ├── manager.html             # Manager view: Metrics, FP reduction chart, ablation table
│       ├── admin.html               # Admin view: Repository connections, scope config, re-indexing
│       └── notifications.html       # Notifications hub for all stakeholder alerts
│
├── sample_data/                     # Reference test repository
│   └── shopkit/
│       ├── cart.py                  # Shopping cart calculations & discounts
│       ├── mathutil.py              # Mathematical utilities (clamp, average, percent)
│       ├── text.py                  # Text processing (slugify, truncate, is_palindrome)
│       ├── validators.py            # Input validation (email, password)
│       ├── internal/
│       │   └── payment_keys.py      # Sensitive restricted tokens (denied scope)
│       └── tests/
│           ├── test_cart.py
│           ├── test_mathutil.py
│           └── test_text.py
│
└── tests/                           # Complete 27-Test automated validation suite
    ├── __init__.py
    ├── test_contextguard.py         # 16 Unit tests: Verification cases, BM25, RRF, sandbox, parsing
    └── test_system_cases.py         # 11 System tests: TC01-04, EX01-03, PERF, concurrency, budget
```

---

## 2. Phase-by-Phase Construction Plan

### Phase 1: Database Foundation & Append-Only Storage (`db.py`)
- **Objective**: Provide transactional, persistent storage supporting both DuckDB and SQLite, with an append-only archive guaranteeing audit trail immutability.
- **Key Modules**: `contextguard/db.py`, `contextguard/config.py`
- **Detailed Tasks**:
  1. Initialize DuckDB database connection at `data/contextguard.duckdb`. If DuckDB fails or is unavailable in the environment, gracefully initialize `data/contextguard.sqlite3`.
  2. Implement all 11 tables: `repositories`, `pull_requests`, `ai_reviews`, `retrieved_contexts`, `retrieved_snippets`, `synthesized_tests`, `verification_runs`, `final_verdicts`, `verdict_archives`, `audit_log`, `notifications`.
  3. **Resolution of Defect D-04 (Evidence Immutability)**:
     - Implement `archive_pr_verdict(pr_id)`: Before a re-run updates `final_verdicts`, copies the existing record along with all associated `synthesized_tests` and `verification_runs` into `verdict_archives`.
     - Never issue `DELETE` on verdicts or verification runs.
  4. Implement `log_audit(pr_id, stage, action, details, status)`.
  5. Implement `create_notification(role, pr_id, title, message)`.

### Phase 2: Ingestion & Mock Repository Data Layer (`github_client.py`, `ingest.py`, `sample_data/`)
- **Objective**: Handle PR URLs, validate schemas, fetch diffs/metadata, and provide the complete 9-PR sample suite against the "shopkit" repository.
- **Key Modules**: `contextguard/github_client.py`, `contextguard/ingest.py`, `sample_data/shopkit/`
- **Detailed Tasks**:
  1. Build the "shopkit" mock repository with `cart.py`, `mathutil.py`, `text.py`, `validators.py`, `internal/payment_keys.py`, and test files under `sample_data/shopkit/tests/`.
  2. Implement `GitHubClient`:
     - In live mode (when `GITHUB_TOKEN` is set): query GitHub REST API `/repos/{owner}/{repo}/pulls/{number}` and `/repos/{owner}/{repo}/pulls/{number}/files`.
     - In mock mode (default): intercept `github.com/shopkit/shopkit/pull/{1..9}` and return pre-configured diffs, metadata, and author details for each of the 9 benchmark scenarios.
  3. Implement `ingest_pull_request(pr_url)`:
     - Validate URL format via regex.
     - Extract owner, repo, and PR number.
     - Fetch diff and metadata.
     - Insert or update `pull_requests` table with status `PENDING`.
  4. **Resolution of Defect D-05 (Concurrency & Integrity)**:
     - Maintain an in-memory `LockManager` with a `threading.Lock()` per PR URL, serializing concurrent calls to `ingest_pull_request` and preventing duplicate DB insert collisions.

### Phase 3: AI Review Engine with Multi-Backend Support (`llm.py`)
- **Objective**: Provide initial code review verdicts (`COMPLIANT` vs `NON_COMPLIANT`) and generate candidate patches.
- **Key Modules**: `contextguard/llm.py`
- **Detailed Tasks**:
  1. Create abstract `LLMProvider` interface with methods:
     - `review_diff(diff, description) -> (verdict, explanation, proposed_fix)`
     - `generate_hyde_query(description, target_function) -> hypothetical_test_code`
     - `synthesize_tests(description, target_code, context_snippets) -> unittest_code`
  2. Implement backends:
     - `MockLLMProvider`: Deterministic responses keyed by PR ID/scenario. Returns verified false-positive verdicts for PR-1, PR-3, PR-8, real bugs for PR-2 and PR-4, compliant for PR-5 and PR-9, false negative for PR-6, and ambiguous RFC 5322 regex for PR-7. Requires zero API keys.
     - `GeminiProvider`: Google GenAI API integration (`gemini-1.5-pro` or `gemini-2.0-flash`).
     - `ClaudeProvider`: Anthropic Messages API (`claude-3-5-sonnet`).
     - `OpenAIProvider`: OpenAI Chat Completions API (`gpt-4o`).
  3. Persist review results into `ai_reviews` and log stage completion in `audit_log`.

### Phase 4: Repository Indexing & Hybrid Retrieval Engine (`repo_index.py`, `retrieval.py`)
- **Objective**: Parse, index, and retrieve relevant repository context while rigorously enforcing security scope rules.
- **Key Modules**: `contextguard/repo_index.py`, `contextguard/retrieval.py`
- **Detailed Tasks**:
  1. **Resolution of Defect D-01 (Scope Rules)**:
     - Implement `path_allowed(file_path, allow_rules, deny_rules)`:
     - If `allow_rules` is empty, default allowed scope to all files (`*`).
     - If `allow_rules` has entries, path must match at least one allow pattern.
     - If path matches any entry in `deny_rules` (e.g., `shopkit/internal/`), immediately block it.
  2. Implement AST-based code parser in `repo_index.py`:
     - Extract function names, arguments, docstrings, class signatures, and existing test methods.
  3. Implement **Sparse Retriever (BM25)**:
     - Tokenize code into identifier tokens and natural language terms (split snake_case and camelCase).
     - Calculate document length, corpus average document length, and token inverted frequencies ($k_1=1.5, b=0.75$).
  4. Implement **Dense Retriever**:
     - Embed function docstrings and test bodies using ChromaDB (or fall back to local sentence hashing / NumPy cosine dot product).
  5. Implement **HyDE Query Expansion**:
     - Use `LLMProvider.generate_hyde_query()` to generate a hypothetical unit test from PR title and description.
     - Query vector store with hypothetical test representation.
  6. Implement **Reciprocal Rank Fusion (RRF)**:
     - Rank items from dense and sparse retrieval; combine via $\text{RRF}(d) = \sum \frac{1}{60 + r_m(d)}$.
     - Return top 5 relevant code/test snippets.
  7. Persist results in `retrieved_contexts` and `retrieved_snippets`.

### Phase 5: Test Oracle Synthesizer (`testgen.py`)
- **Objective**: Automatically manufacture executable Python `unittest` test cases grounded in PR requirements and retrieved context.
- **Key Modules**: `contextguard/testgen.py`
- **Detailed Tasks**:
  1. **Resolution of Defect D-02 (Description Example Parsing)**:
     - Implement multi-format regex parser `parse_examples(description)` handling:
       * Plain bullet: `- clamp(5, 0, 10) -> 5`
       * Markdown backticks: ``- `clamp(5, 0, 10)` -> `5` ``
       * Unicode arrow: `- clamp(5, 0, 10) → 5`
       * Numbered returns: `1. clamp(5, 0, 10) returns 5`
  2. **Resolution of Defect D-03 (Import Preservation)**:
     - Implement import scanner that detects required top-level imports (e.g., `import math`, `import re`, `from typing import List`) and guarantees they are prepended to the generated test script header.
  3. Synthesize clean `unittest.TestCase` class containing assertions derived from both parsed examples and retrieved context tests.
  4. Store generated test suite in `synthesized_tests`.

### Phase 6: Subprocess Sandbox & Verification Filter (`sandbox.py`, `verification.py`)
- **Objective**: Execute original and patched code safely in isolated subprocesses and classify results according to the formal 4-case verification matrix.
- **Key Modules**: `contextguard/sandbox.py`, `contextguard/verification.py`
- **Detailed Tasks**:
  1. Implement `run_in_sandbox(code_to_test, test_suite_code, timeout=5.0) -> ExecutionResult`:
     - Write code and test suite to a secure temporary directory.
     - Execute via `subprocess.run([sys.executable, "-m", "unittest", ...], capture_output=True, timeout=timeout)`.
     - Capture exit code, stdout, stderr, and parse specific test names and results (`PASS`, `FAIL`, `ERROR`).
     - Handle `subprocess.TimeoutExpired` by terminating child process and returning timeout error result.
  2. Implement `VerificationEngine.verify(original_code, fix_code, test_suite)`:
     - Execute original code against synthesized tests.
     - Execute proposed fix code against synthesized tests.
     - Record individual test outcome pairs: `(res_orig, res_fix)`.
  3. Implement `classify(original_results, fix_results) -> (case_code, final_verdict, explanation)`:
     - **Case 1**: All original PASS and all fix PASS $\to$ `(CASE_1, COMPLIANT, "False alarm corrected: original code already satisfies all requirements.")`
     - **Case 2**: Original has FAIL and fix has PASS $\to$ `(CASE_2, NON_COMPLIANT, "Defect confirmed: original code fails requirements and proposed fix passes.")`
     - **Case 3**: Original has PASS and fix has FAIL $\to$ `(CASE_3, COMPLIANT, "Harmful fix rejected: original code passes but proposed fix breaks functionality.")`
     - **Case 4**: Both original and fix FAIL $\to$ `(CASE_4, NON_COMPLIANT, "Inconclusive: both original and fix fail synthesized tests; escalated to human reviewer.")`
     - **Case 0**: Tests produced execution errors or no valid assertions $\to$ `(CASE_0, NON_COMPLIANT, "Inconclusive: tests failed to execute; fallback to human review.")`
  4. Persist run results to `verification_runs` and record final verdict in `final_verdicts`.

### Phase 7: Orchestration Pipeline with Safeguards (`pipeline.py`)
- **Objective**: Wire all 5 stages together, enforcing the 60-second execution budget, fail-open resiliency, step-resumption, and concurrency locks.
- **Key Modules**: `contextguard/pipeline.py`
- **Detailed Tasks**:
  1. Implement `PipelineRunner.run(pr_url, force_refresh=False) -> dict`:
     - Acquire per-PR re-entrant lock.
     - Initialize stopwatch / timeout watchdog ($\le 60\text{ seconds}$).
     - **Resume from stage**: Check database for existing PR and completed stages. If Stage 1 or 2 is already recorded and `force_refresh=False`, skip to Stage 3.
     - **Stage 1 (Intake)**: Ingest PR and store diff.
     - **Stage 2 (AI Review)**: Get review verdict. If `COMPLIANT`, fast-exit, write audit log, notify developer, and return.
     - **Stage 3 (Retrieval)**: If `NON_COMPLIANT`, retrieve repository context within permitted scope.
     - **Stage 4 (Synthesis)**: Synthesize `unittest` oracle tests.
     - **Stage 5 (Verification)**: Execute original and fix code in sandbox; apply 4-case logic.
     - Finalize verdict in database, dispatch role-based notifications, record audit log.
  2. **Fail-Open Implementation**:
     - Wrap pipeline body in a comprehensive `try...except Exception as e` guard.
     - If any exception or unhandled error occurs:
       * Log error to `audit_log` with stage details.
       * Set verdict to `UNVERIFIED_AI_VERDICT` (using Stage 2 verdict as unverified fallback).
       * Set `is_fail_open=True`.
       * Create alert notification for on-call engineer and reviewer.
       * Return gracefully to avoid breaking CI/CD pipelines.

### Phase 8: Web Dashboard & 6 Role-Based Views (`web/`)
- **Objective**: Deliver a web interface featuring modern dark-mode aesthetics, dynamic interactions, and 6 distinct role views.
- **Key Modules**: `web/app.py`, `web/templates/*.html`, `web/static/css/style.css`, `web/static/js/main.js`
- **Detailed Tasks**:
  1. Implement Flask server in `web/app.py` with routes:
     - `GET /`: Redirect to default role (`/developer`).
     - `GET /developer`: Submit PR, view active review, verdict, and evidence breakdown.
     - `POST /api/submit_pr`: API endpoint to ingest and verify a PR URL.
     - `GET /reviewer`: Reviewer dashboard; filter by flagged PRs; side-by-side diff comparison; verdict override actions (`POST /api/override_verdict`).
     - `GET /qa`: QA / Test Auditor dashboard; synthesized tests explorer, test execution matrix, test validity audit button.
     - `GET /security`: Security compliance dashboard; active scope rules, blocked retrieval attempts, repository permissions.
     - `GET /manager`: Engineering management KPI dashboard; False Positive rate reduction chart, performance latency metrics, retrieval ablation study summary.
     - `GET /admin`: Repository administrator dashboard; connect repositories, update allow/deny scope rules, trigger corpus re-indexing, reset PR state.
     - `GET /notifications`: Role-filtered notification center.
     - `GET /health`: JSON system health check (`{"status": "ok", "db": "duckdb", "active_runs": 0, "uptime_seconds": ...}`).
  2. Implement responsive CSS design system in `style.css`:
     - Dark slate theme (`#0f172a`, `#1e293b`), glassmorphism card styling (`backdrop-filter: blur(12px)`), vibrant semantic badges (`COMPLIANT` green, `NON_COMPLIANT` red, `CASE_1` cyan, `CASE_2` orange).
     - Micro-animations on verdict reveals, hover elevations, and status spinners.

### Phase 9: Evaluation & Baseline Benchmarking (`evaluation.py`, `humaneval_baseline.py`)
- **Objective**: Quantify and demonstrate ContextGuard's efficacy in eliminating false alarms and prove the value of the retrieval layer.
- **Key Modules**: `contextguard/evaluation.py`, `contextguard/humaneval_baseline.py`
- **Detailed Tasks**:
  1. Implement evaluation script `evaluation.py`:
     - Compare Baseline (raw AI review without verification) vs. ContextGuard verified review across the 9 sample PRs.
     - Compute FP rate, FN rate, accuracy, and latency.
     - Run ablation study: Dense-only vs. Dense+Sparse (RRF) vs. Full Pipeline (HyDE).
  2. Implement `humaneval_baseline.py` demonstrating the reproduction of the 4-case verification filter on benchmark coding problems.

### Phase 10: Complete 27-Test Automated Verification Suite (`tests/`)
- **Objective**: Write and execute all 27 automated tests specified in Experiment 9, ensuring 100% test pass rate.
- **Key Modules**: `tests/test_contextguard.py` (16 unit tests), `tests/test_system_cases.py` (11 system tests)
- **Detailed Tasks**:
  1. Implement `tests/test_contextguard.py`:
     - Tests 1–5: The four verification cases + case 0 fallback.
     - Tests 6–7: BM25 exact scoring and term saturation.
     - Test 8: RRF rank calculation math.
     - Tests 9–10: Sandbox execution and timeout handling.
     - Tests 11–14: All 4 PR description example formats (plain, markdown backticks, unicode arrow, numbered returns).
     - Test 15: Pipeline fail-open resilience.
     - Test 16: Scope rules blocking restricted directories.
  2. Implement `tests/test_system_cases.py`:
     - Tests 17–20: Formal test cases TC-01 through TC-04 (including D-01 and D-02 fixes).
     - Tests 21–23: Exploratory tests EX-01 (import survival, D-03), EX-02 (evidence immutability archive, D-04), EX-03 (concurrency locking, D-05).
     - Test 24: End-to-end execution of all 9 sample PRs.
     - Test 25: 60-second execution performance budget test (PERF).

### Phase 11: Production Deployment & CLI Runner (`run_demo.py`, `wsgi.py`, `Dockerfile`)
- **Objective**: Package the application for seamless local execution and containerized deployment.
- **Detailed Tasks**:
  1. Create `run_demo.py`:
     - CLI demo script that indexes the `shopkit` repository and runs all 9 PRs sequentially, outputting formatted console tables with verdicts, case classifications, and timing.
     - Supports `--reset` flag to clear and re-populate the database.
  2. Create `wsgi.py` leveraging Waitress for multi-threaded production serving.
  3. Create `Dockerfile` and `requirements.txt` for containerized environments.

---

## 3. Verification & Acceptance Protocol

The implementation will be verified against the following formal acceptance checklist:

| Verification Item | Command / Action | Acceptance Criterion |
| :--- | :--- | :--- |
| **Full Test Suite** | `python -m unittest discover -s tests -v` | **27 tests run, 0 failures, 0 errors (100% PASS)** |
| **All 9 Sample PRs** | `python run_demo.py --reset` | PR-1 $\to$ COMPLIANT (Case 1)<br>PR-2 $\to$ NON_COMPLIANT (Case 2)<br>PR-3 $\to$ COMPLIANT (Case 3)<br>PR-4 $\to$ NON_COMPLIANT (Case 2 via HyDE)<br>PR-5 $\to$ COMPLIANT (Fast Exit)<br>PR-6 $\to$ COMPLIANT (Fast Exit)<br>PR-7 $\to$ NON_COMPLIANT (Case 4 Escalated)<br>PR-8 $\to$ COMPLIANT (Case 1)<br>PR-9 $\to$ COMPLIANT (Fast Exit) |
| **Baseline vs. ContextGuard** | `python -m contextguard.evaluation` | Baseline FPR: **60.0%**<br>ContextGuard FPR: **0.0%** |
| **Retrieval Ablation** | `python -m contextguard.evaluation --ablation` | Turning off HyDE or BM25 reduces PR-4 retrieval rank from 2 to $\ge 5$. |
| **Web Dashboard** | `python web/app.py` | Dashboard loads at `http://127.0.0.1:5000` with 6 role views, live PR submission, and interactive evidence display. |
| **Health Endpoint** | `curl http://127.0.0.1:5000/health` | Returns HTTP 200 `{"status": "ok", "db": "duckdb", ...}` |
| **Performance Budget** | Ran within `PERF_test_all_prs_within_budget` | All 9 PRs verified within $\le 60.0\text{ seconds}$ total. |

---

## 4. Execution Roadmap & Next Steps

1. **Review and Confirm**: Review the architectural specification in `CONTEXTGUARD_SPECIFICATION.md` and this phased roadmap.
2. **Sequential Implementation**: Construct the core package modules (`contextguard/`), database layer, repository indexing, hybrid retrieval, synthesis, sandbox, and web dashboard.
3. **Automated Validation**: Run the full 27-test suite to confirm zero regressions and 100% compliance across all functional and non-functional requirements.
