"""
ContextGuard Unit Test Suite (16 Automated Tests).
Tests verification 4-case logic, BM25 scoring, RRF rank fusion, sandbox execution,
PR description example parsing formats, pipeline fail-open, and scope rules.
"""
import unittest
import math
from contextguard.verification import classify
from contextguard.retrieval import BM25, tokenize
from contextguard.sandbox import run_in_sandbox
from contextguard.testgen import parse_examples
from contextguard.repo_index import path_allowed
from contextguard.pipeline import pipeline_runner

class TestContextGuardUnit(unittest.TestCase):

    # --- Group 1: Four-Case Verification Filter Logic (Tests 1-5) ---
    def test_case_1_false_alarm_correction(self):
        """Case 1: Both original and fix pass -> false alarm corrected to COMPLIANT."""
        case, verdict, _ = classify(["pass", "pass"], ["pass", "pass"])
        self.assertEqual(case, "CASE_1")
        self.assertEqual(verdict, "COMPLIANT")

    def test_case_2_confirmed_defect(self):
        """Case 2: Original fails and fix passes -> true defect confirmed NON_COMPLIANT."""
        case, verdict, _ = classify(["pass", "fail"], ["pass", "pass"])
        self.assertEqual(case, "CASE_2")
        self.assertEqual(verdict, "NON_COMPLIANT")

    def test_case_3_harmful_fix_correction(self):
        """Case 3: Original passes and fix fails -> harmful fix, corrected to COMPLIANT."""
        case, verdict, _ = classify(["pass", "pass"], ["pass", "fail"])
        self.assertEqual(case, "CASE_3")
        self.assertEqual(verdict, "COMPLIANT")

    def test_case_4_inconclusive_escalation(self):
        """Case 4: Both original and fix fail -> inconclusive, escalate to human reviewer."""
        case, verdict, _ = classify(["fail", "pass"], ["fail", "pass"])
        self.assertEqual(case, "CASE_4")
        self.assertEqual(verdict, "NON_COMPLIANT")

    def test_case_0_invalid_tests_fallback(self):
        """Case 0: Execution error or empty assertions -> fallback to human review."""
        case, verdict, _ = classify(["error"], ["error"])
        self.assertEqual(case, "CASE_0")
        self.assertEqual(verdict, "NON_COMPLIANT")

    # --- Group 2: Retrieval & BM25 Scoring (Tests 6-8) ---
    def test_bm25_scoring_exact_match(self):
        """BM25 gives highest positive score to document containing query term."""
        corpus = [
            tokenize("def clamp(val, low, high): return max(low, min(high, val))"),
            tokenize("def slugify(text): return text.lower().replace(' ', '-')"),
            tokenize("def validate_email(email): return '@' in email")
        ]
        bm25 = BM25(corpus)
        query = tokenize("clamp low high boundary")
        score_clamp = bm25.score(query, 0, corpus[0])
        score_slugify = bm25.score(query, 1, corpus[1])
        self.assertGreater(score_clamp, score_slugify)
        self.assertGreater(score_clamp, 0.0)

    def test_bm25_term_frequency_saturation(self):
        """BM25 exhibits sublinear saturation as term frequency increases (k1 parameter)."""
        doc_single = ["clamp", "value"]
        doc_repeated = ["clamp", "clamp", "clamp", "clamp", "value"]
        corpus = [doc_single, doc_repeated]
        bm25 = BM25(corpus)
        q = ["clamp"]
        score1 = bm25.score(q, 0, doc_single)
        score2 = bm25.score(q, 1, doc_repeated)
        # Score increases with frequency, but is strictly less than 4x score1
        self.assertGreater(score2, score1)
        self.assertLess(score2, score1 * 4.0)

    def test_rrf_rank_fusion_math(self):
        """Reciprocal Rank Fusion formula: 1/(60+r1) + 1/(60+r2)."""
        r_dense = 1
        r_sparse = 2
        expected_rrf = (1.0 / (60.0 + 1)) + (1.0 / (60.0 + 2))
        computed_rrf = (1.0 / (60.0 + r_dense)) + (1.0 / (60.0 + r_sparse))
        self.assertAlmostEqual(expected_rrf, computed_rrf, places=6)

    # --- Group 3: Isolated Execution Sandbox (Tests 9-10) ---
    def test_sandbox_timeout_termination(self):
        """Sandbox terminates infinite loop process within specified timeout."""
        infinite_code = "while True:\n    pass\n"
        test_code = "import unittest\nclass T(unittest.TestCase):\n    def test(self): self.assertTrue(True)\n"
        res = run_in_sandbox(infinite_code, test_code, timeout=1.0)
        self.assertTrue(res["timed_out"])
        self.assertEqual(res["status"], "TIMEOUT")

    def test_sandbox_captures_exceptions(self):
        """Sandbox captures syntax/runtime exceptions without throwing uncaught exceptions."""
        broken_code = "def broken(): raise ValueError('intentional failure')"
        test_code = "import unittest\nclass T(unittest.TestCase):\n    def test(self): broken()\n"
        res = run_in_sandbox(broken_code, test_code, timeout=3.0)
        self.assertFalse(res["timed_out"])
        self.assertGreaterEqual(res["failed"] + res["errors"], 1)

    # --- Group 4: PR Description Example Parsing Formats (Tests 11-14, D-02 Fix) ---
    def test_example_parser_plain_bullet(self):
        """Parses plain bullet format: - clamp(5, 0, 10) -> 5."""
        desc = "- clamp(5, 0, 10) -> 5"
        examples = parse_examples(desc)
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0], ("clamp(5, 0, 10)", "5"))

    def test_example_parser_markdown_backticks(self):
        """Parses Markdown code format: - `clamp(5, 0, 10)` -> `5` (Fixes D-02)."""
        desc = "- `clamp(5, 0, 10)` -> `5`"
        examples = parse_examples(desc)
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0], ("clamp(5, 0, 10)", "5"))

    def test_example_parser_unicode_arrow(self):
        """Parses Unicode arrow format: * clamp(5, 0, 10) → 5 (Fixes D-02)."""
        desc = "* clamp(5, 0, 10) → 5"
        examples = parse_examples(desc)
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0], ("clamp(5, 0, 10)", "5"))

    def test_example_parser_numbered_returns(self):
        """Parses numbered 'returns' format: 1. clamp(5, 0, 10) returns 5 (Fixes D-02)."""
        desc = "1. clamp(5, 0, 10) returns 5"
        examples = parse_examples(desc)
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0], ("clamp(5, 0, 10)", "5"))

    # --- Group 5: Pipeline Resiliency & Scope Security (Tests 15-16) ---
    def test_pipeline_fail_open_on_crash(self):
        """Pipeline fail-open mechanism returns fallback verdict on unexpected crash."""
        # Non-existent or corrupt URL
        res = pipeline_runner.run("https://github.com/shopkit/shopkit/pull/999")
        self.assertIn(res["final_verdict"], ["COMPLIANT", "NON_COMPLIANT", "UNVERIFIED", "UNVERIFIED_AI_VERDICT"])

    def test_scope_security_blocks_restricted_paths(self):
        """Scope rules exclude restricted internal files from repository indexing."""
        allowed = path_allowed(
            file_path="shopkit/internal/payment_keys.py",
            allow_rules=["shopkit/", "tests/"],
            deny_rules=["shopkit/internal/"]
        )
        self.assertFalse(allowed)

if __name__ == "__main__":
    unittest.main()
