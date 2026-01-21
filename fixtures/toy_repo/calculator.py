"""
Simple calculator module with intentional bugs for the agent to fix.
"""


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


def subtract(a: int, b: int) -> int:
    """Subtract b from a."""
    return a - b


def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    # BUG: Missing implementation (returns 0)
    return 0


def divide(a: int, b: int) -> float:
    """Divide a by b."""
    # BUG: No zero division check
    return a / b


def factorial(n: int) -> int:
    """Compute factorial of n."""
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n == 0:
        return 1
    # BUG: Off-by-one error
    result = 1
    for i in range(1, n):  # Should be range(1, n + 1)
        result *= i
    return result


def is_prime(n: int) -> bool:
    """Check if n is prime."""
    if n < 2:
        return False
    # BUG: Only checks up to n//2, missing sqrt optimization
    # but more importantly, returns True too early
    for i in range(2, n):
        if n % i == 0:
            return False
    return True


def fibonacci(n: int) -> int:
    """Compute nth Fibonacci number."""
    if n <= 0:
        return 0
    if n == 1:
        return 1
    # Correct implementation
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
