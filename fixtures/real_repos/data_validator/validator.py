"""Data validation utilities."""
import re
from typing import Any, Optional


def is_email(value: str) -> bool:
    """Check if value is a valid email address."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, value))


def is_phone(value: str) -> bool:
    """Check if value is a valid US phone number."""
    cleaned = re.sub(r"[^0-9]", "", value)
    return len(cleaned) == 10


def is_positive_int(value: Any) -> bool:
    """Check if value is a positive integer."""
    if not isinstance(value, int):
        return False
    return value > 0


def is_in_range(value: float, min_val: float, max_val: float) -> bool:
    """Check if value is within inclusive range."""
    return min_val <= value <= max_val


def is_non_empty_string(value: Any) -> bool:
    """Check if value is a non-empty string."""
    return isinstance(value, str) and len(value.strip()) > 0


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password strength.
    Returns (is_valid, error_message).
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain lowercase letter"
    if not re.search(r"[0-9]", password):
        return False, "Password must contain a digit"
    return True, ""


def sanitize_string(value: str, max_len: int = 255) -> str:
    """Sanitize string by stripping and truncating."""
    cleaned = value.strip()
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len]
    return cleaned


def parse_int(value: str, default: int = 0) -> int:
    """Parse string to int with default fallback."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
