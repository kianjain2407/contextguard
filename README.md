# ContextGuard

> **Repository-Context-Aware Verification Filtering for Reliable LLM-Based Code Review**

ContextGuard acts as an automated fact-checker on top of AI code reviewers (Claude, GPT, Gemini). AI reviewers often raise false alarms—flagging correct pull requests as defective. ContextGuard retrieves context from the repository, synthesizes verification tests for the PR, executes original code and suggested fixes in an isolated sandbox, and uses empirical test outcomes to confirm or overturn AI review verdicts.

---

## 🌟 Key Features

1. **5-Stage Verification Pipeline:**
   - **Stage 1 (PR Intake):** Ingests PR diffs, metadata, and commits; persists to DuckDB.
   - **Stage 2 (AI Review):** Initial review with Gemini, Claude, OpenAI, or deterministic zero-key Mock LLM.
   - **Stage 3 (Hybrid Retrieval):** Semantic dense vector search + BM25 sparse lexical search fused via Reciprocal Rank Fusion (RRF) and HyDE query expansion.
   - **Stage 4 (Test Synthesis):** Generates self-contained Python unit tests from PR descriptions and retrieved repository tests.
   - **Stage 5 (Verification Filter):** Executes original vs. proposed fix in a sandboxed subprocess and classifies into 4 decision cases.

2. **Four-Case Decision Logic:**
   - **Case 1 (False Alarm):** Original passes, fix passes $\to$ **Corrected to COMPLIANT**
   - **Case 2 (True Defect):** Original fails, fix passes $\to$ **Confirmed NON-COMPLIANT**
   - **Case 3 (Harmful Fix):** Original passes, fix fails $\to$ **Corrected to COMPLIANT**
   - **Case 4 (Inconclusive):** Both fail $\to$ **Escalated to Human Reviewer**

3. **6 Role-Based Dashboard Views:**
   - **Developer View:** Submit PRs, inspect diffs, synthesized tests, and verdicts.
   - **Reviewer View:** Triage non-compliant PRs and human override controls.
   - **QA / Test Auditor:** Inspect synthesized test suites and sandbox execution pass/fail counts.
   - **Security & Compliance:** Audit logging and repository access scope enforcement (allow/deny rules).
   - **Engineering Manager:** Metrics, false positive reduction rate, and retrieval ablation benchmarks.
   - **Repository Admin:** Configure repository scopes and reset caches.

---

## 🚀 Quick Start

### 1. Installation

```bash
git clone https://github.com/kianjain2407/contextguard.git
cd contextguard
pip install -r requirements.txt
```

### 2. Run the Benchmark Demo

Runs all 9 benchmark PR scenarios across the 5-stage pipeline:

```bash
python run_demo.py --reset
```

### 3. Run Automated Tests

ContextGuard includes a comprehensive suite of 27 unit and system tests:

```bash
python -m unittest discover -s tests -v
```

### 4. Launch the Web Dashboard

```bash
python app.py
```

Open your browser at `http://127.0.0.1:5000` to access the interactive dashboard.

---

## 🏗️ Project Structure

```
contextguard/
├── contextguard/
│   ├── config.py             # Configuration & environment variables
│   ├── db.py                 # DuckDB persistent database engine
│   ├── github_client.py      # GitHub REST API client & benchmark PR dataset
│   ├── ingest.py             # Stage 1: Intake & concurrency locking
│   ├── llm.py                # Stage 2: AI Review (Gemini, Claude, OpenAI, Mock)
│   ├── repo_index.py         # Code parser & AST/regex indexer
│   ├── retrieval.py          # Stage 3: BM25 + Dense + RRF + HyDE engine
│   ├── testgen.py            # Stage 4: Spec-constrained test synthesis
│   ├── sandbox.py            # Stage 5: Isolated Python execution sandbox
│   ├── verification.py       # Stage 5: Four-case decision engine
│   ├── pipeline.py           # End-to-end 5-stage orchestration
│   ├── evaluation.py         # Evaluation metrics & ablation analysis
│   └── humaneval_baseline.py # HumanEval benchmark evaluation
├── sample_data/
│   └── shopkit/              # Benchmark repository with 9 PR scenarios
├── web/
│   ├── app.py                # Flask dashboard & REST API server
│   ├── templates/            # 6 role-based HTML templates
│   └── static/               # Styling and frontend scripts
├── tests/
│   ├── test_contextguard.py  # 16 unit tests
│   └── test_system_cases.py  # 11 system integration tests
├── app.py                    # Root entrypoint for web server
├── run_demo.py               # CLI benchmark demonstration runner
├── requirements.txt          # Python dependencies
└── Dockerfile                # Container deployment specification
```

---

## 📄 License

MIT License. Developed as part of Software Engineering Research.
