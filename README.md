# ContextGuard — AI Code Review Fact-Checker

> **Automated verification filtering to prevent AI code reviewers from raising false alarms.**

---

## 🎯 What is ContextGuard?

AI tools (like ChatGPT, GitHub Copilot, and Claude) are increasingly used to automatically review Pull Requests on GitHub. However, **AI reviewers frequently cry wolf**—flagging working, valid code as defective and suggesting unnecessary changes.

**ContextGuard acts as an automated fact-checker for AI code reviews.**

Instead of blindly trusting the AI, ContextGuard:
1. Takes the code changes from GitHub.
2. Auto-generates real Python unit tests from the specification and repository context.
3. Actually executes both your original code and the AI's suggested fix in an isolated sandbox.
4. Uses empirical test pass/fail results to confirm real bugs or overrule false alarms.

---

## 💡 How It Works (The 3-Step Fact-Check)

```
[ GitHub Repo or PR Link ]
          ↓
Step 1: AI Review
        • AI flags potential defect and suggests a patch.
          ↓
Step 2: Auto-Generate Unit Tests
        • ContextGuard synthesizes Python tests from PR descriptions & repo context.
          ↓
Step 3: Sandbox Test Run & Verdict
        • Original Code Passes Tests? → Overrule AI! Marked as SAFE TO MERGE (COMPLIANT ✅)
        • Original Code Fails Tests?  → Confirm AI! Marked as REAL BUG (NON-COMPLIANT ❌)
```

---

## 📊 The 4 Fact-Check Cases (In Plain English)

| Case | What Happened in Tests | Verdict | Meaning |
| :--- | :--- | :--- | :--- |
| **Case 1** | Original code passes, AI fix passes | **COMPLIANT ✅** | **False Alarm Overruled:** Your code was already working fine. |
| **Case 2** | Original code fails, AI fix passes | **NON-COMPLIANT ❌** | **Real Bug Confirmed:** The AI found a genuine bug (e.g. divide by zero). |
| **Case 3** | Original code passes, AI fix fails | **COMPLIANT ✅** | **Bad AI Fix Caught:** AI suggested a fix that actually broke existing features. |
| **Case 4** | Both fail or tests inconclusive | **NON-COMPLIANT ⚠️** | **Escalate to Human:** Ambiguous case; human developer should double-check. |

---

## 🚀 Quick Start Guide

### 1. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/kianjain2407/contextguard.git
cd contextguard
pip install -r requirements.txt
```

### 2. Run the Interactive Web Dashboard
```bash
python app.py
```
Open your browser at **`http://127.0.0.1:5000`** to paste any GitHub link or run 1-click test scenarios!

### 3. Run the Benchmark CLI Demo
Runs all 9 benchmark scenarios through the verification pipeline:
```bash
python run_demo.py --reset
```

### 4. Run Automated Tests
Runs all 27 unit and integration tests:
```bash
python -m unittest discover -s tests -v
```

---

## 📁 Project Structure

```
contextguard/
├── contextguard/             # Core Python Engine
│   ├── config.py             # Configuration & environment variables
│   ├── db.py                 # DuckDB persistent storage
│   ├── github_client.py      # GitHub API client (supports direct repo & PR URLs)
│   ├── ingest.py             # Stage 1: Ingestion & concurrency locks
│   ├── llm.py                # Stage 2: AI Review (Mock, Gemini, Claude, OpenAI)
│   ├── repo_index.py         # Code parser & AST indexer
│   ├── retrieval.py          # Stage 3: Repository context retrieval
│   ├── testgen.py            # Stage 4: Spec-constrained test synthesis
│   ├── sandbox.py            # Stage 5: Isolated Python execution sandbox
│   ├── verification.py       # Stage 5: Four-case decision engine
│   └── pipeline.py           # 5-stage pipeline runner
├── sample_data/
│   └── shopkit/              # Benchmark repository with 9 PR scenarios
├── web/                      # Clean Web Dashboard
│   ├── app.py                # Flask server
│   ├── templates/            # HTML templates (base.html, developer.html)
│   └── static/               # Styling & client-side scripts
├── tests/                    # 27 Automated Unit & System Tests
├── app.py                    # Server launch entrypoint
├── run_demo.py               # CLI benchmark demonstration runner
├── requirements.txt          # Python dependencies
└── Dockerfile                # Optional container setup
```

---

## 📄 License
MIT License.
