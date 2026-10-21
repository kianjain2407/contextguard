"""
Validation utilities for shopkit user inputs.
"""
import re

def validate_email(email: str) -> bool:
    """
    Validates an email address.
    Original implementation uses basic regex that fails on complex valid emails.
    """
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))

def validate_password(password: str) -> bool:
    """
    Validates password strength: at least 8 characters, at least one digit.
    """
    if len(password) < 8:
        return False
    if not any(char.isdigit() for char in password):
        return False
    return True
