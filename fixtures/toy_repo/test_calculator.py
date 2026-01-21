"""
Tests for calculator module.
"""

import pytest
from calculator import add, subtract, multiply, divide, factorial, is_prime, fibonacci


class TestAddition:
    def test_add_positive(self):
        assert add(2, 3) == 5

    def test_add_negative(self):
        assert add(-1, -1) == -2

    def test_add_zero(self):
        assert add(0, 5) == 5


class TestSubtraction:
    def test_subtract_positive(self):
        assert subtract(5, 3) == 2

    def test_subtract_negative(self):
        assert subtract(-1, -1) == 0


class TestMultiplication:
    def test_multiply_positive(self):
        assert multiply(3, 4) == 12

    def test_multiply_zero(self):
        assert multiply(0, 100) == 0

    def test_multiply_negative(self):
        assert multiply(-2, 3) == -6


class TestDivision:
    def test_divide_positive(self):
        assert divide(10, 2) == 5.0

    def test_divide_by_zero(self):
        with pytest.raises(ZeroDivisionError):
            divide(1, 0)


class TestFactorial:
    def test_factorial_zero(self):
        assert factorial(0) == 1

    def test_factorial_positive(self):
        assert factorial(5) == 120

    def test_factorial_negative(self):
        with pytest.raises(ValueError):
            factorial(-1)


class TestIsPrime:
    def test_prime_small(self):
        assert is_prime(2) == True
        assert is_prime(3) == True

    def test_not_prime(self):
        assert is_prime(4) == False
        assert is_prime(9) == False

    def test_prime_larger(self):
        assert is_prime(17) == True


class TestFibonacci:
    def test_fibonacci_base(self):
        assert fibonacci(0) == 0
        assert fibonacci(1) == 1

    def test_fibonacci_sequence(self):
        assert fibonacci(10) == 55
