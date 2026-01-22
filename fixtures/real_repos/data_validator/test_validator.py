"""Tests for validator module."""
import pytest
from validator import (
    is_email, is_phone, is_positive_int, is_in_range,
    is_non_empty_string, validate_password, sanitize_string, parse_int
)


class TestEmailValidation:
    def test_valid_emails(self):
        assert is_email("test@example.com") == True
        assert is_email("user.name@domain.org") == True

    def test_invalid_emails(self):
        assert is_email("not-an-email") == False
        assert is_email("missing@domain") == False
        assert is_email("@nodomain.com") == False


class TestPhoneValidation:
    def test_valid_phones(self):
        assert is_phone("1234567890") == True
        assert is_phone("123-456-7890") == True
        assert is_phone("(123) 456-7890") == True

    def test_invalid_phones(self):
        assert is_phone("123") == False
        assert is_phone("12345678901") == False


class TestNumericValidation:
    def test_positive_int(self):
        assert is_positive_int(1) == True
        assert is_positive_int(0) == False
        assert is_positive_int(-1) == False
        assert is_positive_int(1.5) == False

    def test_in_range(self):
        assert is_in_range(5, 1, 10) == True
        assert is_in_range(1, 1, 10) == True
        assert is_in_range(10, 1, 10) == True
        assert is_in_range(0, 1, 10) == False


class TestStringValidation:
    def test_non_empty_string(self):
        assert is_non_empty_string("hello") == True
        assert is_non_empty_string("  ") == False
        assert is_non_empty_string("") == False
        assert is_non_empty_string(123) == False


class TestPasswordValidation:
    def test_valid_password(self):
        valid, msg = validate_password("SecurePass1")
        assert valid == True
        assert msg == ""

    def test_short_password(self):
        valid, msg = validate_password("Short1")
        assert valid == False
        assert "8 characters" in msg

    def test_no_uppercase(self):
        valid, msg = validate_password("lowercase1")
        assert valid == False
        assert "uppercase" in msg


class TestUtilities:
    def test_sanitize_string(self):
        assert sanitize_string("  hello  ") == "hello"
        assert len(sanitize_string("x" * 300, max_len=100)) == 100

    def test_parse_int(self):
        assert parse_int("42") == 42
        assert parse_int("not-a-number") == 0
        assert parse_int("invalid", default=-1) == -1
