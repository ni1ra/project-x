"""Tests for calculator module."""
import pytest
from calculator import (
    add, subtract, multiply, divide, power,
    factorial, is_even, is_prime
)


class TestBasicOperations:
    def test_add(self):
        assert add(2, 3) == 5
        assert add(-1, 1) == 0
        assert add(0.5, 0.5) == 1.0

    def test_subtract(self):
        assert subtract(5, 3) == 2
        assert subtract(3, 5) == -2

    def test_multiply(self):
        assert multiply(3, 4) == 12
        assert multiply(-2, 3) == -6

    def test_divide(self):
        assert divide(10, 2) == 5
        assert divide(7, 2) == 3.5

    def test_divide_by_zero(self):
        with pytest.raises(ValueError):
            divide(1, 0)


class TestPower:
    def test_positive_exponent(self):
        assert power(2, 3) == 8
        assert power(5, 0) == 1

    def test_negative_exponent(self):
        assert power(2, -1) == 0.5


class TestFactorial:
    def test_factorial(self):
        assert factorial(0) == 1
        assert factorial(1) == 1
        assert factorial(5) == 120

    def test_factorial_negative(self):
        with pytest.raises(ValueError):
            factorial(-1)


class TestPredicates:
    def test_is_even(self):
        assert is_even(0) == True
        assert is_even(2) == True
        assert is_even(3) == False

    def test_is_prime(self):
        assert is_prime(2) == True
        assert is_prime(3) == True
        assert is_prime(4) == False
        assert is_prime(17) == True
        assert is_prime(1) == False
