# ContextGuard — Implementation & Architecture Guide

This document outlines the core architecture and 5-stage pipeline of **ContextGuard**.

---

## 🏗️ System Architecture Overview

ContextGuard is built around a lightweight, local-first Python architecture:
- **Language:** Python 3.10+
- **Database:** DuckDB (fast, file-based, zero configuration)
- **Web Interface:** Lightweight Flask server with vanilla HTML/CSS/JS (no heavy frontend frameworks)
- **Execution Sandbox:** Python subprocess runner with strict 5-second timeouts
- **External Dependencies:** Zero required cloud services (works completely offline using built-in deterministic datasets or live with GitHub API)

---

## ⚙️ The 5-Stage Verification Pipeline

```
[ GitHub Input ]
       ↓
[ Stage 1: Ingest ]      → Parses repository/PR URL, fetches diff & metadata, locks PR (D-05)
       ↓
[ Stage 2: AI Review ]   → Gets initial review & suggested fix (Mock / Gemini / Claude / OpenAI)
       ↓
[ Stage 3: Retrieval ]   → Pulls relevant repository code & context (Dense + BM25 + RRF)
       ↓
[ Stage 4: Test Gen ]    → Synthesizes executable Python unittest suite from PR spec
       ↓
[ Stage 5: Sandbox ]     → Runs original code and proposed fix against tests in sandbox
       ↓
[ Decision Engine ]      → Compares test outcomes to finalize verdict (Case 1, 2, 3, or 4)
```

---

### Stage 1: PR Intake (`ingest.py`, `github_client.py`)
- Accepts any GitHub repository URL (e.g. `https://github.com/snehal-k296/HabiCity.git`), PR URL, or commit hash.
- Fetches code diffs and commit messages via GitHub REST API without requiring a private token.
- Uses per-PR re-entrant threading locks (`threading.RLock`) to guarantee concurrency safety (prevents race conditions).

### Stage 2: Initial AI Review (`llm.py`)
- Simulates or executes an AI code reviewer review.
- Built-in deterministic Mock LLM requires no API keys and covers all 9 benchmark scenarios.
- Optional plug-ins for Google Gemini, Anthropic Claude, and OpenAI GPT.

### Stage 3: Repository Context Retrieval (`retrieval.py`, `repo_index.py`)
- Automatically indexes the repository files into an AST/regex symbol map.
- Combines:
  1. Dense vector semantic search (NumPy dot product).
  2. Sparse lexical search (Okapi BM25).
  3. Reciprocal Rank Fusion (RRF) to combine results.
- Respects repository security scopes (`allow_paths` and `deny_paths`) to ensure internal private files are never leaked.

### Stage 4: Spec-Constrained Test Synthesis (`testgen.py`)
- Parses specification examples from pull request descriptions:
  - Bullet calls (`- clamp(5, 0, 10) -> 5`)
  - Markdown code blocks (`` `clamp(5, 0, 10)` -> `5` ``)
  - Unicode arrows (`* clamp(5, 0, 10) → 5`)
  - Numbered statements (`1. clamp(5, 0, 10) returns 5`)
- Assembles a self-contained `unittest.TestCase` suite with all necessary imports.

### Stage 5: Fix-Guided Verification Filter (`verification.py`, `sandbox.py`)
- Executes both the original code and the AI's proposed patch inside an isolated Python subprocess sandbox.
- Applies the 4-case decision matrix:
  - **Case 1 (Both Pass):** Original is working $\to$ **False Alarm Overruled (COMPLIANT)**.
  - **Case 2 (Orig Fails, Fix Passes):** Bug is real $\to$ **Defect Confirmed (NON_COMPLIANT)**.
  - **Case 3 (Orig Passes, Fix Fails):** Fix broke code $\to$ **Harmful Fix Discarded (COMPLIANT)**.
  - **Case 4 (Both Fail):** Ambiguous $\to$ **Escalate to Human (NON_COMPLIANT)**.

---

## 🧪 Automated Testing Strategy

ContextGuard is validated by 27 automated tests (`tests/`):
- **16 Unit Tests (`tests/test_contextguard.py`):**
  - BM25 score saturation & exact matching.
  - Test synthesis for all 4 format variants.
  - Subprocess timeout enforcement & exception handling.
  - Scope rule security enforcement.
- **11 System Integration Tests (`tests/test_system_cases.py`):**
  - All 4 decision case outcomes.
  - Decisive test retrieval in top-5 rankings.
  - 60-second budget enforcement across all 9 PRs.
  - Multithreaded concurrency stress tests.

To run tests:
```bash
python -m unittest discover -s tests -v
```
