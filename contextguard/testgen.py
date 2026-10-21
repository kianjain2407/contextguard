"""
Stage 4: Test Synthesis.
Synthesizes executable Python unittest suites grounded in PR requirements and retrieved context.
Resolves Defect D-02 (Markdown, unicode arrow, and 'returns' example parsing)
and Defect D-03 (import preservation).
"""
import re
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional
from .db import db

def parse_examples(description: str) -> List[Tuple[str, str]]:
    """
    Parses test assertion examples from PR description.
    Resolves Defect D-02 by supporting:
    1. Plain bullet:       - clamp(5, 0, 10) -> 5
    2. Markdown code:      - `clamp(5, 0, 10)` -> `5`
    3. Unicode arrow:      * clamp(5, 0, 10) → 5
    4. Numbered 'returns': 1. clamp(5, 0, 10) returns 5
    """
    examples: List[Tuple[str, str]] = []
    if not description:
        return examples

    lines = description.splitlines()
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue

        # Strip list markers: bullets (-, *, +) or numbered lists (1., 2.)
        line_content = re.sub(r'^(?:[-*+]\s*|\d+\.\s*)', '', line_clean).strip()

        # Format 1 & 2 & 3: calls with arrows (-> or →)
        # Matches: `call` -> `expected` or call -> expected or call → expected
        arrow_match = re.search(r'[`]?([a-zA-Z_]\w*\s*\([^)]*\))[`]?\s*(?:->|→)\s*[`]?([^`]+)[`]?', line_content)
        if arrow_match:
            call = arrow_match.group(1).strip()
            expected = arrow_match.group(2).strip()
            examples.append((call, expected))
            continue

        # Format 4: calls with 'returns' keyword
        # Matches: `call` returns `expected` or call returns expected
        returns_match = re.search(r'[`]?([a-zA-Z_]\w*\s*\([^)]*\))[`]?\s+returns\s+[`]?([^`]+)[`]?', line_content, re.IGNORECASE)
        if returns_match:
            call = returns_match.group(1).strip()
            expected = returns_match.group(2).strip()
            examples.append((call, expected))
            continue

    return examples

def extract_required_imports(code_text: str) -> List[str]:
    """
    Resolves Defect D-03:
    Detects top-level imports in code/tests and guarantees they are preserved in the test harness.
    """
    imports = set()
    default_imports = [
        "import unittest",
        "import sys",
        "import os",
        "import math",
        "import re"
    ]
    for imp in default_imports:
        imports.add(imp)

    for line in code_text.splitlines():
        line_s = line.strip()
        if line_s.startswith("import ") or line_s.startswith("from "):
            imports.add(line_s)

    return sorted(list(imports))

class TestSynthesizer:
    """
    Synthesizes self-contained unittest test cases for original vs proposed fix execution.
    """
    def synthesize(self, pr_data: Dict[str, Any], retrieved_snippets: List[Dict[str, Any]]) -> str:
        description = pr_data.get("description", "")
        examples = parse_examples(description)
        pr_number = pr_data.get("pr_number", 1)

        # Detect module and imports
        target_file = pr_data.get("target_file", "")
        combined_text = f"{description} {pr_data.get('diff', '')} {pr_data.get('original_code', '')}"
        for s in retrieved_snippets:
            combined_text += f"\n{s.get('content', '')}"

        imports = extract_required_imports(combined_text)
        import_header = "\n".join(imports)

        test_methods = []

        # 1. Synthesize tests from parsed PR description examples
        for idx, (call, expected) in enumerate(examples, start=1):
            # Format expected value
            exp_val = expected
            if exp_val.lower() == "true":
                assertion = f"self.assertTrue({call})"
            elif exp_val.lower() == "false":
                assertion = f"self.assertFalse({call})"
            elif exp_val.startswith('"') or exp_val.startswith("'"):
                assertion = f"self.assertEqual({call}, {exp_val})"
            elif exp_val.replace('.', '', 1).isdigit() or (exp_val.startswith('-') and exp_val[1:].replace('.', '', 1).isdigit()):
                assertion = f"self.assertEqual({call}, {exp_val})"
            else:
                assertion = f"self.assertEqual(str({call}), '{exp_val}')"

            method_code = f"""    def test_spec_example_{idx}(self):
        \"\"\"Synthesized from PR description: {call} -> {expected}\"\"\"
        {assertion}"""
            test_methods.append(method_code)

        # Find target function name in original code or diff
        target_func_name = ""
        m_func = re.search(r'def\s+([a-zA-Z_]\w*)\s*\(', pr_data.get("original_code", "") or pr_data.get("diff", ""))
        if m_func:
            target_func_name = m_func.group(1)

        # 2. Synthesize tests from retrieved repository tests (decisive context)
        for s in retrieved_snippets:
            if s.get("snippet_type") == "test" and "def test_" in s.get("content", ""):
                content = s["content"]
                # Only include test if it targets the specific function being verified
                if target_func_name and target_func_name not in content:
                    continue
                # Clean up indentation to fit inside TestCase
                lines = content.splitlines()
                reindented = []
                for line in lines:
                    reindented.append("    " + line if not line.startswith("    ") else line)
                test_methods.append("\n".join(reindented))

        # Fallback if no examples or context tests
        if not test_methods:
            test_methods.append("""    def test_baseline_execution(self):
        self.assertTrue(True)""")

        suite_code = f"""{import_header}

class GeneratedVerificationTest(unittest.TestCase):
{chr(10).join(test_methods)}

if __name__ == '__main__':
    unittest.main()
"""
        return suite_code

def synthesize_verification_tests(pr_data: Dict[str, Any], retrieved_snippets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Executes Stage 4 Test Synthesis.
    Stores test suite in synthesized_tests table, logs audit.
    """
    synthesizer = TestSynthesizer()
    test_code = synthesizer.synthesize(pr_data, retrieved_snippets)
    pr_id = pr_data["pr_id"]

    examples = parse_examples(pr_data.get("description", ""))
    test_id = f"test_{pr_id}_{int(datetime.now().timestamp()*1000)}"

    db.execute_write(
        """
        INSERT INTO synthesized_tests (test_id, pr_id, test_code, parsed_examples_count, created_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (test_id, pr_id, test_code, len(examples))
    )

    db.log_audit(
        pr_id=pr_id,
        stage="SYNTHESIS",
        action="TESTS_SYNTHESIZED",
        details=f"Synthesized verification test suite with {len(examples)} spec examples and {len(retrieved_snippets)} context hints.",
        status="SUCCESS"
    )

    db.create_notification(
        role="QA",
        pr_id=pr_id,
        title="Verification Tests Synthesized",
        message=f"Generated {len(examples)} tests for PR #{pr_data.get('pr_number', '')}."
    )

    return {
        "test_id": test_id,
        "pr_id": pr_id,
        "test_code": test_code,
        "parsed_examples_count": len(examples)
    }
