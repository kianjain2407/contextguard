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
        Validates and parses a PR URL.
        Format: https://github.com/{owner}/{repo}/pull/{pr_number}
        """
        pattern = r"^https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)/?$"
        match = re.match(pattern, pr_url.strip())
        if not match:
            # Also allow short-hand: owner/repo#number or pull/number for easy CLI
            short_match = re.match(r"^([^/]+)/([^/#]+)#(\d+)$", pr_url.strip())
            if short_match:
                return {
                    "owner": short_match.group(1),
                    "repo": short_match.group(2),
                    "pr_number": int(short_match.group(3))
                }
            number_match = re.match(r"^(\d+)$", pr_url.strip())
            if number_match:
                return {
                    "owner": "shopkit",
                    "repo": "shopkit",
                    "pr_number": int(number_match.group(1))
                }
            raise ValueError(f"Invalid GitHub PR URL format: '{pr_url}'. Expected 'https://github.com/owner/repo/pull/123'")

        return {
            "owner": match.group(1),
            "repo": match.group(2),
            "pr_number": int(match.group(3))
        }

    def fetch_pr_data(self, pr_url: str) -> Dict[str, Any]:
        """
        Fetches diff, description, and metadata for the given PR.
        """
        parsed = self.parse_pr_url(pr_url)
        pr_number = parsed["pr_number"]
        repo = parsed["repo"]
        owner = parsed["owner"]

        # Check mock dataset first (e.g. shopkit/shopkit)
        if (owner == "shopkit" or repo == "shopkit") and pr_number in MOCK_PRS:
            data = dict(MOCK_PRS[pr_number])
            data["owner"] = owner
            data["repo"] = repo
            data["pr_url"] = pr_url
            return data

        # If live token is available, attempt real GitHub REST API fetch
        if self.token:
            try:
                import requests
                headers = {"Authorization": f"token {self.token}", "Accept": "application/vnd.github.v3+json"}
                api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
                resp = requests.get(api_url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    pr_info = resp.json()
                    diff_resp = requests.get(api_url, headers={**headers, "Accept": "application/vnd.github.v3.diff"}, timeout=10)
                    return {
                        "pr_number": pr_number,
                        "title": pr_info.get("title", ""),
                        "description": pr_info.get("body", "") or "",
                        "author": pr_info.get("user", {}).get("login", "unknown"),
                        "diff": diff_resp.text if diff_resp.status_code == 200 else "",
                        "owner": owner,
                        "repo": repo,
                        "pr_url": pr_url,
                        "target_file": ""
                    }
            except Exception as e:
                pass

        # Fallback to mock PR 1 if unknown number for testing
        fallback = dict(MOCK_PRS.get(pr_number, MOCK_PRS[1]))
        fallback["pr_number"] = pr_number
        fallback["owner"] = owner
        fallback["repo"] = repo
        fallback["pr_url"] = pr_url
        return fallback

github_client = GitHubClient()
