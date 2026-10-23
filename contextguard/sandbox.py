"""
Stage 5: Execution Sandbox.
Executes code and test suites in an isolated Python subprocess with hard timeouts.
"""
import sys
import re
import subprocess
import tempfile
import os
from typing import Dict, Any, List

def run_in_sandbox(target_code: str, test_suite_code: str, timeout: float = 5.0) -> Dict[str, Any]:
    """
    Executes target Python code along with a test suite in an isolated subprocess.
    Returns structured results: passed, failed, errors, exit_code, stdout, stderr.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = os.path.join(tmp_dir, "run_test.py")

        # Auto-append unittest.main() if not present
        effective_test_code = test_suite_code
        if "unittest.main" not in effective_test_code:
            effective_test_code += "\n\nif __name__ == '__main__':\n    unittest.main()\n"

        # Combine target implementation with test suite
        full_script = f"""# Sandbox Test Execution Harness
import sys
import os

# Target Implementation
{target_code}

# Synthesized Test Suite
{effective_test_code}
"""
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(full_script)

        cmd = [sys.executable, test_file]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmp_dir
            )
            stdout = proc.stdout
            stderr = proc.stderr
            returncode = proc.returncode

            # Parse unittest output from stderr/stdout
            passed_count = 0
            failed_count = 0
            error_count = 0
            status = "PASS" if returncode == 0 else "FAIL"

            output_text = stdout + "\n" + stderr

            # unittest writes "OK" at end of stderr for clean runs
            test_passed_clean = bool(re.search(r'\bOK\b', stderr)) or returncode == 0

            if test_passed_clean and "FAIL" not in stderr and "ERROR" not in stderr:
                m = re.search(r'Ran (\d+) test', output_text)
                passed_count = int(m.group(1)) if m else 1
            else:
                m_fail = re.search(r'failures=(\d+)', output_text)
                m_err = re.search(r'errors=(\d+)', output_text)
                failed_count = int(m_fail.group(1)) if m_fail else 0
                error_count = int(m_err.group(1)) if m_err else 0
                if returncode != 0 and failed_count == 0 and error_count == 0:
                    if "Traceback" in output_text or "Error" in output_text:
                        error_count = 1
                    else:
                        failed_count = 1
                m_total = re.search(r'Ran (\d+) test', output_text)
                total = int(m_total.group(1)) if m_total else (failed_count + error_count)
                passed_count = max(0, total - (failed_count + error_count))

            return {
                "status": status,
                "exit_code": returncode,
                "passed": passed_count,
                "failed": failed_count,
                "errors": error_count,
                "stdout": stdout,
                "stderr": stderr,
                "timed_out": False
            }

        except subprocess.TimeoutExpired as e:
            return {
                "status": "TIMEOUT",
                "exit_code": -1,
                "passed": 0,
                "failed": 0,
                "errors": 1,
                "stdout": e.stdout or "",
                "stderr": f"Execution timed out after {timeout} seconds.",
                "timed_out": True
            }
        except Exception as ex:
            return {
                "status": "ERROR",
                "exit_code": -2,
                "passed": 0,
                "failed": 0,
                "errors": 1,
                "stdout": "",
                "stderr": str(ex),
                "timed_out": False
            }
