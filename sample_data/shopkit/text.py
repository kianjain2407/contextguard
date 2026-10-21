"""
Text processing and normalization utilities for shopkit.
"""
import re

def is_palindrome(s: str) -> bool:
    """
    Checks if a string is a palindrome, ignoring case.
    Preserves space handling for phrase palindromes.
    """
    clean = s.lower()
    return clean == clean[::-1]

def slugify(text: str) -> str:
    """
    Converts a string into a clean, URL-friendly slug.
    Target PR improves whitespace handling and replaces spaces with dashes.
    """
    text = text.strip().lower()
    # Basic implementation (PR will improve whitespace collapsing)
    text = re.sub(r'[^\w\s-]', '', text)
    return text.replace(' ', '-')

def truncate(text: str, max_len: int = 50) -> str:
    """
    Truncates a string to max_len characters, appending '...' if truncated.
    """
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."
