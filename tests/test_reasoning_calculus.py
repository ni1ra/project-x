"""Tests for src/project_x/reasoning/calculus.py — Phase 13 #00P13c8-02.

Coverage:
- Canonical case: ∫₀² (3x² + 2x - 1) dx = 10 (closes maths-010)
- Linear / quadratic / cubic polynomials over various intervals
- Empty / zero polynomial → integral = 0
- Negative bounds + bounds outside the polynomial's "natural" range
- Invariant check: constant-of-integration cancels
- Thesis-compliance source-grep
"""

from __future__ import annotations

from pathlib import Path

from project_x.reasoning.calculus import polynomial_definite_integral


def test_polynomial_integral_canonical_maths_010():
    """maths-010: ∫₀² (3x² + 2x - 1) dx = 10."""
    lemma = polynomial_definite_integral([3, 2, -1], 0, 2)
    assert abs(lemma.actual_value - 10.0) < 1e-12


def test_polynomial_integral_linear():
    """∫₀¹ 2x dx = 1 (antiderivative x², F(1) - F(0) = 1)."""
    lemma = polynomial_definite_integral([2, 0], 0, 1)
    assert abs(lemma.actual_value - 1.0) < 1e-12


def test_polynomial_integral_constant():
    """∫₀⁵ 7 dx = 35 (constant integrand, antiderivative 7x)."""
    lemma = polynomial_definite_integral([7], 0, 5)
    assert abs(lemma.actual_value - 35.0) < 1e-12


def test_polynomial_integral_cubic():
    """∫₀¹ (4x³ + 3x²) dx = 1 + 1 = 2 (each term integrates to x⁴ / x³ evaluated at 1)."""
    lemma = polynomial_definite_integral([4, 3, 0, 0], 0, 1)
    assert abs(lemma.actual_value - 2.0) < 1e-12


def test_polynomial_integral_negative_bound():
    """∫_{-1}^{1} x² dx = 2/3 (symmetric about origin)."""
    lemma = polynomial_definite_integral([1, 0, 0], -1, 1)
    assert abs(lemma.actual_value - 2 / 3) < 1e-12


def test_polynomial_integral_reversed_bounds():
    """∫₂⁰ (3x² + 2x - 1) dx = -10 (FTC respects bound order)."""
    lemma = polynomial_definite_integral([3, 2, -1], 2, 0)
    assert abs(lemma.actual_value - (-10.0)) < 1e-12


def test_polynomial_integral_empty_polynomial():
    """∫ 0 dx = 0 (zero polynomial)."""
    lemma = polynomial_definite_integral([], 0, 5)
    assert lemma.actual_value == 0.0


def test_polynomial_integral_lemma_chain_shape():
    """Lemma has 4 derivation steps (antiderivative + evaluate_upper + evaluate_lower + ftc_closing)."""
    lemma = polynomial_definite_integral([3, 2, -1], 0, 2)
    assert len(lemma.derivation_steps) == 4
    assert lemma.derivation_steps[0].operation == "antiderivative"
    assert lemma.derivation_steps[-1].operation == "ftc_closing"


def test_polynomial_integral_invariant_holds():
    """Constant-of-integration-cancels invariant fires."""
    lemma = polynomial_definite_integral([3, 2, -1], 0, 2)
    assert all(inv.holds for inv in lemma.invariant_checks)


def test_polynomial_integral_render_includes_intro():
    lemma = polynomial_definite_integral([3, 2, -1], 0, 2)
    rendered = lemma.render()
    assert "Fundamental Theorem" in rendered or "FTC" in rendered
    assert "Invariant checks:" in rendered


def test_calculus_substrate_thesis_compliant():
    path = Path(__file__).resolve().parent.parent / "src" / "project_x" / "reasoning" / "calculus.py"
    source = path.read_text()
    forbidden = [
        "import sympy", "from sympy",
        "import scipy", "from scipy",
        "import numpy", "from numpy",
        "import torch", "from torch",
    ]
    for token in forbidden:
        assert token not in source, f"calculus.py imports forbidden token '{token}'"
