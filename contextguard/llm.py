"""
Stage 2: AI Review Service.
Supports Mock (deterministic, zero-key default), Google Gemini, Anthropic Claude, and OpenAI.
"""
import os
import json
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
from .config import LLM_PROVIDER, LLM_MODEL, GEMINI_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY
from .db import db

class BaseLLMProvider:
    def review(self, pr_data: Dict[str, Any]) -> Tuple[str, str, str]:
        """Returns (verdict, explanation, proposed_fix). Verdict is 'COMPLIANT' or 'NON_COMPLIANT'."""
        raise NotImplementedError

    def generate_hyde(self, description: str, title: str) -> str:
        """Generates hypothetical unit test code to expand retrieval queries."""
        raise NotImplementedError

class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic Mock LLM for the 9 benchmark PRs.
    Requires no network access or API keys.
    """
    MOCK_REVIEWS = {
        1: {
            "verdict": "NON_COMPLIANT",
            "explanation": "AI reviewer claims clamp implementation has potential edge-case boundary instability. Proposes alternative max(low, min(high, val)) structure.",
            "proposed_fix": """def clamp(val, low, high):
    return max(low, min(high, val))
"""
        },
        2: {
            "verdict": "NON_COMPLIANT",
            "explanation": "Flagged genuine defect: average(numbers) raises ZeroDivisionError when called with an empty list [].",
            "proposed_fix": """def average(numbers):
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)
"""
        },
        3: {
            "verdict": "NON_COMPLIANT",
            "explanation": "AI reviewer flags string palindrome handling and suggests stripping all spaces, inadvertently breaking sentence palindromes.",
            "proposed_fix": """def is_palindrome(s: str) -> bool:
    clean = s.lower().replace(' ', '')
    return clean == clean[::-1] and not s.endswith(' ')
"""
        },
        4: {
            "verdict": "NON_COMPLIANT",
            "explanation": "AI reviewer flags slugify for not collapsing multiple consecutive whitespace characters into a single hyphen.",
            "proposed_fix": """import re
def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r'[^\\w\\s-]', '', text)
    return re.sub(r'\\s+', '-', text)
"""
        },
        5: {
            "verdict": "COMPLIANT",
            "explanation": "Percentage calculation correctly guards against zero division and computes proportional ratio. Code approved as compliant.",
            "proposed_fix": ""
        },
        6: {
            "verdict": "COMPLIANT",
            "explanation": "AI reviewer approves truncate implementation as compliant (AI false negative: missed edge case).",
            "proposed_fix": ""
        },
        7: {
            "verdict": "NON_COMPLIANT",
            "explanation": "AI reviewer flags regex email validation as insufficiently strict against RFC 5322 compliance standards.",
            "proposed_fix": """import re
def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9]+@[a-zA-Z0-9]+\\.[a-zA-Z]+$'
    return bool(re.match(pattern, email.strip()))
"""
        },
        8: {
            "verdict": "NON_COMPLIANT",
            "explanation": "AI reviewer flags float arithmetic precision in discount total and demands Decimal quantization.",
            "proposed_fix": """def cart_total(items, discount_pct = 0.0):
    from decimal import Decimal, ROUND_HALF_UP
    subtotal = sum(Decimal(str(item['price'])) * item.get('quantity', 1) for item in items)
    if discount_pct > 0:
        subtotal -= subtotal * (Decimal(str(discount_pct)) / Decimal('100'))
    return float(subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
"""
        },
        9: {
            "verdict": "COMPLIANT",
            "explanation": "Password validator satisfies both length threshold (>= 8) and digit requirement. Code approved as compliant.",
            "proposed_fix": ""
        }
    }

    def review(self, pr_data: Dict[str, Any]) -> Tuple[str, str, str]:
        pr_number = pr_data.get("pr_number", 1)
        rev = self.MOCK_REVIEWS.get(pr_number)
        if rev:
            return rev["verdict"], rev["explanation"], rev["proposed_fix"]
        # Default heuristic
        diff = pr_data.get("diff", "")
        if "return" in diff:
            return "NON_COMPLIANT", "Automated mock review: flagged potential edge case.", pr_data.get("proposed_fix", "")
        return "COMPLIANT", "Code satisfies baseline review criteria.", ""

    def generate_hyde(self, description: str, title: str) -> str:
        # HyDE produces a hypothetical test case based on query
        if "slug" in description.lower() or "slug" in title.lower():
            return "def test_slugify_collapses_whitespace(): self.assertEqual(slugify('Hello   World'), 'hello-world')"
        if "average" in description.lower():
            return "def test_average_empty(): self.assertEqual(average([]), 0.0)"
        if "clamp" in description.lower():
            return "def test_clamp_bounds(): self.assertEqual(clamp(5, 0, 10), 5)"
        return f"def test_expected_behaviour(): # Test for {title}\n    pass"

class GeminiLLMProvider(BaseLLMProvider):
    """Google Gemini API Provider."""
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.model = LLM_MODEL or "gemini-2.0-flash"

    def review(self, pr_data: Dict[str, Any]) -> Tuple[str, str, str]:
        if not self.api_key:
            return MockLLMProvider().review(pr_data)
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            prompt = f"""You are an automated code review engine. Review this pull request:
Title: {pr_data['title']}
Description: {pr_data['description']}
Diff:
{pr_data['diff']}

Respond strictly with a JSON object:
{{
  "verdict": "COMPLIANT" or "NON_COMPLIANT",
  "explanation": "1-2 sentence reason",
  "proposed_fix": "complete replacement python function if non-compliant, else empty string"
}}
"""
            response = client.models.generate_content(model=self.model, contents=prompt)
            text = response.text.strip()
            if text.startswith("```json"): text = text[7:-3]
            elif text.startswith("```"): text = text[3:-3]
            data = json.loads(text.strip())
            return data.get("verdict", "COMPLIANT"), data.get("explanation", ""), data.get("proposed_fix", "")
        except Exception:
            return MockLLMProvider().review(pr_data)

    def generate_hyde(self, description: str, title: str) -> str:
        if not self.api_key:
            return MockLLMProvider().generate_hyde(description, title)
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            prompt = f"Write a single hypothetical Python unittest method that would rigorously test this PR: {title}. {description}"
            resp = client.models.generate_content(model=self.model, contents=prompt)
            return resp.text.strip()
        except Exception:
            return MockLLMProvider().generate_hyde(description, title)

class ClaudeLLMProvider(BaseLLMProvider):
    """Anthropic Claude API Provider."""
    def __init__(self):
        self.api_key = ANTHROPIC_API_KEY
        self.model = LLM_MODEL or "claude-3-5-sonnet-20241022"

    def review(self, pr_data: Dict[str, Any]) -> Tuple[str, str, str]:
        if not self.api_key:
            return MockLLMProvider().review(pr_data)
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            prompt = f"Review PR '{pr_data['title']}':\n{pr_data['diff']}\nReturn JSON with keys verdict, explanation, proposed_fix."
            message = client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            data = json.loads(message.content[0].text)
            return data.get("verdict", "COMPLIANT"), data.get("explanation", ""), data.get("proposed_fix", "")
        except Exception:
            return MockLLMProvider().review(pr_data)

    def generate_hyde(self, description: str, title: str) -> str:
        return MockLLMProvider().generate_hyde(description, title)

class OpenAILLMProvider(BaseLLMProvider):
    """OpenAI API Provider."""
    def __init__(self):
        self.api_key = OPENAI_API_KEY
        self.model = LLM_MODEL or "gpt-4o"

    def review(self, pr_data: Dict[str, Any]) -> Tuple[str, str, str]:
        if not self.api_key:
            return MockLLMProvider().review(pr_data)
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            prompt = f"Review PR '{pr_data['title']}':\n{pr_data['diff']}\nReturn JSON with keys verdict, explanation, proposed_fix."
            resp = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            data = json.loads(resp.choices[0].message.content)
            return data.get("verdict", "COMPLIANT"), data.get("explanation", ""), data.get("proposed_fix", "")
        except Exception:
            return MockLLMProvider().review(pr_data)

    def generate_hyde(self, description: str, title: str) -> str:
        return MockLLMProvider().generate_hyde(description, title)

def get_llm_provider() -> BaseLLMProvider:
    provider = LLM_PROVIDER.lower()
    if provider == "gemini":
        return GeminiLLMProvider()
    elif provider == "anthropic" or provider == "claude":
        return ClaudeLLMProvider()
    elif provider == "openai":
        return OpenAILLMProvider()
    return MockLLMProvider()

def perform_ai_review(pr_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes Stage 2 AI Review.
    Stores result in ai_reviews table, logs audit, and creates notification.
    """
    provider = get_llm_provider()
    pr_id = pr_data["pr_id"]

    verdict, explanation, proposed_fix = provider.review(pr_data)

    review_id = f"rev_{pr_id}_{int(datetime.now().timestamp()*1000)}"
    db.execute_write(
        """
        INSERT INTO ai_reviews (review_id, pr_id, provider, model, initial_verdict, explanation, proposed_fix, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (review_id, pr_id, LLM_PROVIDER, LLM_MODEL or "default", verdict, explanation, proposed_fix)
    )

    db.log_audit(
        pr_id=pr_id,
        stage="REVIEW",
        action="AI_REVIEW_COMPLETED",
        details=f"Initial AI Review: {verdict}. Explanation: {explanation[:100]}",
        status="SUCCESS"
    )

    db.create_notification(
        role="DEVELOPER",
        pr_id=pr_id,
        title=f"AI Review: {verdict}",
        message=f"Initial review flagged PR as {verdict}."
    )

    return {
        "review_id": review_id,
        "pr_id": pr_id,
        "initial_verdict": verdict,
        "explanation": explanation,
        "proposed_fix": proposed_fix
    }
