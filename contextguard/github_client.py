"""
GitHub Client: Handles live REST API queries and pre-configured mock PR datasets for shopkit.
"""
import re
from typing import Dict, Any, Optional
from .config import GITHUB_TOKEN

MOCK_PRS: Dict[int, Dict[str, Any]] = {
    1: {
        "pr_number": 1,
        "title": "Enforce numerical boundary clamp",
        "description": "Ensures value stays within bounds:\n- clamp(5, 0, 10) -> 5\n- clamp(-2, 0, 10) -> 0\n- clamp(15, 0, 10) -> 10",
        "author": "dev-alice",
        "target_file": "sample_data/shopkit/mathutil.py",
        "diff": """--- a/sample_data/shopkit/mathutil.py
+++ b/sample_data/shopkit/mathutil.py
@@ -3,6 +3,9 @@
 def clamp(val, low, high):
+    if val < low:
+        return low
+    if val > high:
+        return high
     return val
""",
        "original_code": """def clamp(val, low, high):
    if val < low:
        return low
    if val > high:
        return high
    return val
""",
        "proposed_fix": """def clamp(val, low, high):
    return max(low, min(high, val))
"""
    },
    2: {
        "pr_number": 2,
        "title": "Prevent ZeroDivisionError in average calculation",
        "description": "Calculates list average and handles empty list:\n- `average([10, 20])` -> `15.0`\n- `average([])` -> `0.0`",
        "author": "dev-bob",
        "target_file": "sample_data/shopkit/mathutil.py",
        "diff": """--- a/sample_data/shopkit/mathutil.py
+++ b/sample_data/shopkit/mathutil.py
@@ -10,3 +10,5 @@
 def average(numbers):
+    if not numbers:
+        return 0.0
     return sum(numbers) / len(numbers)
""",
        "original_code": """def average(numbers):
    return sum(numbers) / len(numbers)
""",
        "proposed_fix": """def average(numbers):
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)
"""
    },
    3: {
        "pr_number": 3,
        "title": "Case-insensitive palindrome check",
        "description": "Checks palindrome status:\n* is_palindrome('Madam') → True\n* is_palindrome('Race Car') → False",
        "author": "dev-carol",
        "target_file": "sample_data/shopkit/text.py",
        "diff": """--- a/sample_data/shopkit/text.py
+++ b/sample_data/shopkit/text.py
@@ -5,3 +5,4 @@
 def is_palindrome(s: str) -> bool:
     clean = s.lower()
-    return clean == clean[::-1]
+    return clean == clean[::-1]
""",
        "original_code": """def is_palindrome(s: str) -> bool:
    clean = s.lower()
    return clean == clean[::-1]
""",
        "proposed_fix": """def is_palindrome(s: str) -> bool:
    # Erroneous fix: strips spaces, which breaks phrase palindromes expected to respect spacing
    clean = s.lower().replace(' ', '')
    return clean == clean[::-1] and not s.endswith(' ')
"""
    },
    4: {
        "pr_number": 4,
        "title": "Improve URL slug generation for blog titles",
        "description": "Normalizes title strings into URL-safe slugs:\n1. slugify('Hello World') returns hello-world",
        "author": "dev-dave",
        "target_file": "sample_data/shopkit/text.py",
        "diff": r"""--- a/sample_data/shopkit/text.py
+++ b/sample_data/shopkit/text.py
@@ -11,4 +11,6 @@
 def slugify(text: str) -> str:
     text = text.strip().lower()
     text = re.sub(r'[^\w\s-]', '', text)
-    return text.replace(' ', '-')
+    import re
+    return re.sub(r'\s+', '-', text)
""",
        "original_code": r"""import re
def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r'[^\w\s-]', '', text)
    return text.replace(' ', '-')
""",
        "proposed_fix": r"""import re
def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r'[^\w\s-]', '', text)
    return re.sub(r'\s+', '-', text)
"""
    },
    5: {
        "pr_number": 5,
        "title": "Calculate percentage ratio helper",
        "description": "Computes percentage ratio:\n- percent(25, 100) -> 25.0",
        "author": "dev-eve",
        "target_file": "sample_data/shopkit/mathutil.py",
        "diff": """--- a/sample_data/shopkit/mathutil.py
+++ b/sample_data/shopkit/mathutil.py
@@ -18,4 +18,4 @@
 def percent(part, whole):
     if whole == 0:
         return 0.0
     return (part / whole) * 100.0
""",
        "original_code": """def percent(part, whole):
    if whole == 0:
        return 0.0
    return (part / whole) * 100.0
""",
        "proposed_fix": """def percent(part, whole):
    return 0.0 if whole == 0 else (part / whole) * 100.0
"""
    },
    6: {
        "pr_number": 6,
        "title": "Add ellipsis truncation to long strings",
        "description": "Truncates string with ellipsis:\n- truncate('Hello World', 5) -> Hello...",
        "author": "dev-frank",
        "target_file": "sample_data/shopkit/text.py",
        "diff": """--- a/sample_data/shopkit/text.py
+++ b/sample_data/shopkit/text.py
@@ -17,3 +17,3 @@
 def truncate(text: str, max_len: int = 50) -> str:
     if len(text) <= max_len:
         return text
     return text[:max_len] + '...'
""",
        "original_code": """def truncate(text: str, max_len: int = 50) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + '...'
""",
        "proposed_fix": """def truncate(text: str, max_len: int = 50) -> str:
    return text[:max_len] + '...' if len(text) > max_len else text
"""
    },
    7: {
        "pr_number": 7,
        "title": "Strict RFC email validation",
        "description": "Validates complex email formats:\n- validate_email('user@[192.168.1.1]') -> True\n- validate_email('invalid@') -> False",
        "author": "dev-grace",
        "target_file": "sample_data/shopkit/validators.py",
        "diff": """--- a/sample_data/shopkit/validators.py
+++ b/sample_data/shopkit/validators.py
@@ -5,3 +5,4 @@
 def validate_email(email: str) -> bool:
     pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$'
     return bool(re.match(pattern, email.strip()))
""",
        "original_code": """import re
def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email.strip()))
""",
        "proposed_fix": """import re
def validate_email(email: str) -> bool:
    # Partial fix that still fails on subdomains or complex RFC 5322 characters
    pattern = r'^[a-zA-Z0-9]+@[a-zA-Z0-9]+\\.[a-zA-Z]+$'
    return bool(re.match(pattern, email.strip()))
"""
    },
    8: {
        "pr_number": 8,
        "title": "Calculate shopping cart total with discount",
        "description": "Calculates cart total with discount and currency rounding:\n- `cart_total([{'price': 10.0, 'quantity': 2}], 10.0)` -> `18.0`",
        "author": "dev-heidi",
        "target_file": "sample_data/shopkit/cart.py",
        "diff": """--- a/sample_data/shopkit/cart.py
+++ b/sample_data/shopkit/cart.py
@@ -8,3 +8,5 @@
 def cart_total(items, discount_pct = 0.0):
     subtotal = sum(item['price'] * item.get('quantity', 1) for item in items)
     if discount_pct > 0:
         subtotal -= subtotal * (discount_pct / 100.0)
     return round(subtotal, 2)
""",
        "original_code": """def cart_total(items, discount_pct = 0.0):
    subtotal = sum(item['price'] * item.get('quantity', 1) for item in items)
    if discount_pct > 0:
        subtotal -= subtotal * (discount_pct / 100.0)
    return round(subtotal, 2)
""",
        "proposed_fix": """def cart_total(items, discount_pct = 0.0):
    from decimal import Decimal, ROUND_HALF_UP
    subtotal = sum(Decimal(str(item['price'])) * item.get('quantity', 1) for item in items)
    if discount_pct > 0:
        subtotal -= subtotal * (Decimal(str(discount_pct)) / Decimal('100'))
    return float(subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
"""
    },
    9: {
        "pr_number": 9,
        "title": "Check password length and digit requirement",
        "description": "Checks password requirements:\n- validate_password('secret123') -> True",
        "author": "dev-ivan",
        "target_file": "sample_data/shopkit/validators.py",
        "diff": """--- a/sample_data/shopkit/validators.py
+++ b/sample_data/shopkit/validators.py
@@ -10,4 +10,4 @@
 def validate_password(password: str) -> bool:
     if len(password) < 8:
         return False
     return any(char.isdigit() for char in password)
""",
        "original_code": """def validate_password(password: str) -> bool:
    if len(password) < 8:
        return False
    return any(char.isdigit() for char in password)
""",
        "proposed_fix": """def validate_password(password: str) -> bool:
    return len(password) >= 8 and any(c.isdigit() for c in password)
"""
    }
}

class GitHubClient:
    """
    Client for interacting with GitHub pull requests.
    Supports live GitHub REST API or built-in mock repository.
    """
    def __init__(self, token: Optional[str] = None):
        self.token = token or GITHUB_TOKEN

    def parse_pr_url(self, pr_url: str) -> Dict[str, Any]:
        """
        Validates and parses a GitHub repository URL, PR URL, or shorthand identifier.
        Supports:
        - Repository URL: https://github.com/owner/repo or https://github.com/owner/repo.git
        - Pull Request URL: https://github.com/owner/repo/pull/123
        - Commit URL: https://github.com/owner/repo/commit/sha
        - Shorthand: owner/repo, owner/repo#123, or 1-9
        """
        raw = pr_url.strip()
        # Clean trailing slashes and .git suffix if applicable
        clean_url = re.sub(r'\.git/?$', '', raw)
        clean_url = clean_url.rstrip('/')

        # 1. PR URL: https://github.com/owner/repo/pull/123
        pr_match = re.match(r"^https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)$", clean_url)
        if pr_match:
            return {
                "owner": pr_match.group(1),
                "repo": pr_match.group(2),
                "pr_number": int(pr_match.group(3)),
                "type": "pull"
            }

        # 2. Commit URL: https://github.com/owner/repo/commit/sha
        commit_match = re.match(r"^https?://github\.com/([^/]+)/([^/]+)/commit/([0-9a-fA-F]+)$", clean_url)
        if commit_match:
            return {
                "owner": commit_match.group(1),
                "repo": commit_match.group(2),
                "pr_number": 1,
                "commit_sha": commit_match.group(3),
                "type": "commit"
            }

        # 3. Shorthand: owner/repo#number
        short_hash = re.match(r"^([^/]+)/([^/#]+)#(\d+)$", clean_url)
        if short_hash:
            return {
                "owner": short_hash.group(1),
                "repo": short_hash.group(2),
                "pr_number": int(short_hash.group(3)),
                "type": "pull"
            }

        # 4. Pure integer scenario index: 1-9
        number_match = re.match(r"^(\d+)$", clean_url)
        if number_match:
            return {
                "owner": "shopkit",
                "repo": "shopkit",
                "pr_number": int(number_match.group(1)),
                "type": "mock"
            }

        # 5. Direct repository URL: https://github.com/owner/repo
        repo_match = re.match(r"^https?://github\.com/([^/]+)/([^/]+)$", clean_url)
        if repo_match:
            return {
                "owner": repo_match.group(1),
                "repo": repo_match.group(2),
                "pr_number": 1,
                "type": "repo"
            }

        # 6. Shorthand repo: owner/repo
        repo_short = re.match(r"^([^/]+)/([^/#]+)$", clean_url)
        if repo_short:
            return {
                "owner": repo_short.group(1),
                "repo": repo_short.group(2),
                "pr_number": 1,
                "type": "repo"
            }

        raise ValueError(
            f"Invalid GitHub URL: '{pr_url}'. Supported formats: Repository (https://github.com/owner/repo), "
            f"Pull Request (https://github.com/owner/repo/pull/123), or scenario number (1-9)."
        )

    def fetch_pr_data(self, pr_url: str) -> Dict[str, Any]:
        """
        Fetches diff, description, and metadata for the given PR, commit, or repository.
        Works for public repositories without a token and authenticated GitHub queries.
        """
        parsed = self.parse_pr_url(pr_url)
        pr_number = parsed["pr_number"]
        repo = parsed["repo"]
        owner = parsed["owner"]
        target_type = parsed.get("type", "pull")
        commit_sha = parsed.get("commit_sha")

        # 1. Check built-in mock dataset first (e.g. shopkit/shopkit or 1-9)
        if (owner == "shopkit" or repo == "shopkit") and pr_number in MOCK_PRS:
            data = dict(MOCK_PRS[pr_number])
            data["owner"] = owner
            data["repo"] = repo
            data["pr_url"] = pr_url
            return data

        # 2. Setup GitHub API headers
        headers = {
            "User-Agent": "ContextGuard-Verifier/1.0",
            "Accept": "application/vnd.github.v3+json"
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"

        try:
            import requests

            # Case A: User provided a repository URL (type == 'repo')
            if target_type == "repo":
                # Check if repo has any PRs
                pulls_url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=all&per_page=1"
                resp = requests.get(pulls_url, headers=headers, timeout=10)
                if resp.status_code == 200 and resp.json():
                    latest_pr = resp.json()[0]
                    pr_number = latest_pr.get("number", 1)
                    target_type = "pull"
                else:
                    # No PRs or repo has only commits: use latest commit
                    commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"
                    c_resp = requests.get(commits_url, headers=headers, timeout=10)
                    if c_resp.status_code == 200 and c_resp.json():
                        commit_sha = c_resp.json()[0]["sha"]
                        target_type = "commit"

            # Case B: Fetch specific commit
            if target_type == "commit" and commit_sha:
                c_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_sha}"
                c_resp = requests.get(c_url, headers=headers, timeout=10)
                diff_resp = requests.get(c_url, headers={**headers, "Accept": "application/vnd.github.v3.diff"}, timeout=10)

                if c_resp.status_code == 200:
                    c_data = c_resp.json()
                    commit_msg = c_data.get("commit", {}).get("message", "")
                    lines = commit_msg.strip().splitlines()
                    title = lines[0] if lines else f"Commit {commit_sha[:7]}"
                    desc = "\n".join(lines[1:]).strip() if len(lines) > 1 else title
                    author = c_data.get("author", {}).get("login") if c_data.get("author") else c_data.get("commit", {}).get("author", {}).get("name", "unknown")
                    diff_text = diff_resp.text if diff_resp.status_code == 200 else ""

                    target_file = ""
                    m_file = re.search(r'\+\+\+ b/(\S+)', diff_text) or re.search(r'diff --git a/\S+ b/(\S+)', diff_text)
                    if m_file:
                        target_file = m_file.group(1)

                    return {
                        "pr_number": pr_number,
                        "title": title,
                        "description": desc or title,
                        "author": author,
                        "diff": diff_text,
                        "owner": owner,
                        "repo": repo,
                        "pr_url": pr_url,
                        "target_file": target_file,
                        "commit_sha": commit_sha
                    }

            # Case C: Fetch PR data
            api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
            resp = requests.get(api_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                pr_info = resp.json()
                diff_resp = requests.get(api_url, headers={**headers, "Accept": "application/vnd.github.v3.diff"}, timeout=10)
                diff_text = diff_resp.text if diff_resp.status_code == 200 else ""

                target_file = ""
                m_file = re.search(r'\+\+\+ b/(\S+)', diff_text) or re.search(r'diff --git a/\S+ b/(\S+)', diff_text)
                if m_file:
                    target_file = m_file.group(1)

                return {
                    "pr_number": pr_number,
                    "title": pr_info.get("title", f"Pull Request #{pr_number}"),
                    "description": pr_info.get("body", "") or "",
                    "author": pr_info.get("user", {}).get("login", "unknown") if pr_info.get("user") else "unknown",
                    "diff": diff_text,
                    "owner": owner,
                    "repo": repo,
                    "pr_url": pr_url,
                    "target_file": target_file
                }
            elif resp.status_code == 404:
                # Fallback: check if latest commit exists
                commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"
                c_resp = requests.get(commits_url, headers=headers, timeout=10)
                if c_resp.status_code == 200 and c_resp.json():
                    sha = c_resp.json()[0]["sha"]
                    return self.fetch_pr_data(f"https://github.com/{owner}/{repo}/commit/{sha}")

        except Exception as e:
            # Log error for visibility; fall through to mock fallback
            import sys
            print(f"[ContextGuard] GitHubClient fetch error for {pr_url!r}: {e}", file=sys.stderr)

        # Fallback to mock PR 1 if unknown or offline
        fallback = dict(MOCK_PRS.get(pr_number, MOCK_PRS[1]))
        fallback["pr_number"] = pr_number
        fallback["owner"] = owner
        fallback["repo"] = repo
        fallback["pr_url"] = pr_url
        return fallback

github_client = GitHubClient()
