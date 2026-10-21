"""
ContextGuard System Test Suite (11 Automated Tests).
Includes formal test cases TC-01 to TC-04, exploratory tests EX-01 to EX-03,
concurrency stress test, and 60-second performance test (PERF).
"""
import unittest
import threading
import time
from contextguard.verification import classify
from contextguard.retrieval import HybridRetriever
from contextguard.repo_index import path_allowed, RepositoryIndexer
from contextguard.testgen import parse_examples, synthesize_verification_tests
from contextguard.sandbox import run_in_sandbox
from contextguard.pipeline import pipeline_runner
from contextguard.db import db
from contextguard.github_client import MOCK_PRS

class TestContextGuardSystem(unittest.TestCase):

    # --- TC-01: Fix-guided Verification Filter (White-box, branch coverage) ---
    def test_all_branches(self):
        """TC-01: Verifies all 5 outcome branches of classify()."""
        # (a) original [pass, pass], fix [pass, pass] -> Case 1 -> COMPLIANT
        case1, v1, _ = classify(["pass", "pass"], ["pass", "pass"])
        self.assertEqual(case1, "CASE_1")
        self.assertEqual(v1, "COMPLIANT")

        # (b) original [pass, fail], fix [pass, pass] -> Case 2 -> NON_COMPLIANT
        case2, v2, _ = classify(["pass", "fail"], ["pass", "pass"])
        self.assertEqual(case2, "CASE_2")
        self.assertEqual(v2, "NON_COMPLIANT")

        # (c) original [pass, pass], fix [pass, fail] -> Case 3 -> COMPLIANT
        case3, v3, _ = classify(["pass", "pass"], ["pass", "fail"])
        self.assertEqual(case3, "CASE_3")
        self.assertEqual(v3, "COMPLIANT")

        # (d) original [fail, pass], fix [fail, pass] -> Case 4 -> NON_COMPLIANT
        case4, v4, _ = classify(["fail", "pass"], ["fail", "pass"])
        self.assertEqual(case4, "CASE_4")
        self.assertEqual(v4, "NON_COMPLIANT")

        # (e) original [error], fix [error] -> Case 0 -> NON_COMPLIANT
        case0, v0, _ = classify(["error"], ["error"])
        self.assertEqual(case0, "CASE_0")
        self.assertEqual(v0, "NON_COMPLIANT")

    # --- TC-02: Hybrid Repository-Context Retrieval ---
    def test_decisive_test_in_top5(self):
        """TC-02: Decisive target test is within top-5 across dense, hybrid, and full modes."""
        pr_data = MOCK_PRS[4]
        query = f"{pr_data['title']} {pr_data['description']}"
        retriever = HybridRetriever("sample_data/shopkit")
        retriever.build_index(allow_rules=["shopkit/", "tests/"], deny_rules=["shopkit/internal/"])

        target_identifier = "test_slugify_collapses_whitespace"

        for mode in ["dense", "hybrid", "full"]:
            snippets = retriever.retrieve(query, mode=mode, top_k=5, pr_data=pr_data)
            self.assertEqual(len(snippets), 5)
            identifiers = [s["identifier"] for s in snippets]
            self.assertIn(target_identifier, identifiers, f"Target test {target_identifier} not in top-5 for mode {mode}")

    def test_restricted_file_never_retrieved(self):
        """TC-02: Restricted internal/ files are never returned, even with k=50."""
        pr_data = MOCK_PRS[4]
        query = "stripe payment secret key authorization"
        retriever = HybridRetriever("sample_data/shopkit")
        retriever.build_index(allow_rules=["shopkit/", "tests/"], deny_rules=["shopkit/internal/"])

        snippets = retriever.retrieve(query, mode="full", top_k=50, pr_data=pr_data)
        for s in snippets:
            self.assertNotIn("payment_keys.py", s["file_path"])
            self.assertNotIn("internal/", s["file_path"])

    # --- TC-03: Repository Scope Configuration (Equivalence Partitioning, D-01 Fix) ---
    def test_partition_allow_and_deny(self):
        """TC-03 (P1): allow [shopkit/, tests/], deny [shopkit/internal/] -> restricted excluded."""
        indexer = RepositoryIndexer("sample_data/shopkit")
        items = indexer.index_repository(allow_rules=["shopkit/", "tests/"], deny_rules=["shopkit/internal/"])
        files = set(item["file_path"] for item in items)
        self.assertTrue(any("cart.py" in f for f in files))
        self.assertFalse(any("payment_keys.py" in f for f in files))

    def test_partition_allow_only(self):
        """TC-03 (P2): allow [shopkit/], no deny rule."""
        indexer = RepositoryIndexer("sample_data/shopkit")
        items = indexer.index_repository(allow_rules=["shopkit/"], deny_rules=[])
        files = set(item["file_path"] for item in items)
        self.assertTrue(all("shopkit" in f for f in files))

    def test_partition_deny_only(self):
        """TC-03 (P3): no allow rule, deny [shopkit/internal/] -> indexes all non-denied files (D-01 Fix)."""
        indexer = RepositoryIndexer("sample_data/shopkit")
        items = indexer.index_repository(allow_rules=[], deny_rules=["shopkit/internal/"])
        files = set(item["file_path"] for item in items)
        self.assertGreater(len(files), 0)
        self.assertFalse(any("payment_keys.py" in f for f in files))

    # --- TC-04: Test Synthesis from PR Descriptions (D-02 Fix) ---
    def test_all_description_formats(self):
        """TC-04: All 4 format variants (plain, code, arrow, returns) produce valid test examples."""
        formats = [
            "- clamp(5, 0, 10) -> 5",
            "- `clamp(5, 0, 10)` -> `5`",
            "* clamp(5, 0, 10) → 5",
            "1. clamp(5, 0, 10) returns 5"
        ]
        for f in formats:
            ex = parse_examples(f)
            self.assertEqual(len(ex), 1, f"Failed parsing format: {f}")
            self.assertEqual(ex[0], ("clamp(5, 0, 10)", "5"))

    # --- EX-01: Imports in Generated Tests (D-03 Fix) ---
    def test_imports_survive_split(self):
        """EX-01: Module-level imports (math.isclose) execute without NameError in sandbox."""
        pr_data = {
            "pr_id": "test#math",
            "description": "- math.isclose(clamp(5, 0, 10), 5.0) -> True",
            "target_file": "sample_data/shopkit/mathutil.py",
            "diff": "def clamp(val, low, high): return min(max(val, low), high)",
            "original_code": "import math\ndef clamp(val, low, high): return min(max(val, low), high)"
        }
        test_info = synthesize_verification_tests(pr_data, [])
        res = run_in_sandbox(pr_data["original_code"], test_info["test_code"], timeout=3.0)
        self.assertEqual(res["errors"], 0)
        self.assertEqual(res["status"], "PASS")

    # --- EX-02: Evidence Immutability (D-04 Fix) ---
    def test_rerun_archives_evidence(self):
        """EX-02: Re-running a PR creates an archive entry in verdict_archives rather than deleting evidence."""
        url = "https://github.com/shopkit/shopkit/pull/1"
        # Run 1
        pipeline_runner.run(url, force_refresh=True)
        archives_before = db.query_all("SELECT * FROM verdict_archives WHERE pr_id = ?", ("shopkit/shopkit#1",))
        count_before = len(archives_before)

        # Run 2 (Re-run)
        pipeline_runner.run(url, force_refresh=True)
        archives_after = db.query_all("SELECT * FROM verdict_archives WHERE pr_id = ?", ("shopkit/shopkit#1",))
        self.assertGreater(len(archives_after), count_before)

    # --- EX-03: Concurrency & Re-entrancy Lock (D-05 Fix) ---
    def test_three_parallel_runs(self):
        """EX-03: Submitting the same PR across 3 simultaneous threads succeeds without IntegrityError."""
        url = "https://github.com/shopkit/shopkit/pull/2"
        exceptions = []

        def worker():
            try:
                pipeline_runner.run(url, force_refresh=False)
            except Exception as e:
                exceptions.append(e)

        threads = [threading.Thread(target=worker) for _ in range(3)]
        for t in threads: t.start()
        for t in threads: t.join()

        self.assertEqual(len(exceptions), 0, f"Concurrent submission threw exceptions: {exceptions}")
        verdicts = db.query_all("SELECT * FROM final_verdicts WHERE pr_id = ?", ("shopkit/shopkit#2",))
        self.assertEqual(len(verdicts), 1)

    # --- PERF: 60-Second NFR Latency Budget ---
    def test_all_prs_within_budget(self):
        """PERF: All 9 benchmark PRs complete well within the 60-second budget."""
        durations = []
        for pr_num in range(1, 10):
            url = f"https://github.com/shopkit/shopkit/pull/{pr_num}"
            t0 = time.time()
            res = pipeline_runner.run(url, force_refresh=True)
            elapsed = time.time() - t0
            durations.append((pr_num, elapsed))
            self.assertLess(elapsed, 60.0, f"PR #{pr_num} exceeded 60s budget: {elapsed:.2f}s")
            self.assertIn(res["final_verdict"], ["COMPLIANT", "NON_COMPLIANT"])

        slowest_pr, slowest_time = max(durations, key=lambda x: x[1])
        print(f"\n[PERF] Ran all 9 PRs. Slowest PR #{slowest_pr}: {slowest_time:.3f}s (Budget: 60s)")

if __name__ == "__main__":
    unittest.main()
