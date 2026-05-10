"""Tests for src/project_x/reasoning/integration.py — Phase 13 cycle 9 #00P13c9-01.

Coverage:
- ∫_a^b x·e^(c·x) dx via parts: canonical ∫₀¹ x·e^x dx = 1; negative c decay; c=0 trivial
- ∫_a^b x·sin(c·x) dx via parts: canonical ∫₀^π x·sin(x) dx = π; c=0 trivial
- ∫_a^b x·cos(c·x) dx via parts: canonical ∫₀^π x·cos(x) dx = -2; c=0 trivial
- ∫_a^b x·sin(x²) dx via u=x² substitution: canonical ∫₀¹ x·sin(x²) dx = (1-cos(1))/2
- ∫_a^b x·cos(x²) dx via u=x² substitution: canonical ∫₀^√π x·cos(x²) dx = 0
- Lemma chain shape (5 steps for parts; 4 steps for u-sub) + intro + invariant
- Invariant: integration-by-parts identity / u-substitution change-of-variables identity holds
- Rejection: u-sub primitive rejects trig_fn other than "sin"/"cos"
- Thesis-compliance: no sympy/scipy/numpy/torch imports

Lain mid-cycle directive 2026-05-11: "make it solve harder problems". This module
ships techniques beyond freshman polynomial integration — integration-by-parts +
u-substitution for canonical transcendental integrands.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from project_x.reasoning.integration import (
    definite_integral_x_times_cos,
    definite_integral_x_times_exp,
    definite_integral_x_times_sin,
    definite_integral_xtrig_via_usub,
)


# ── ∫ x·e^(c·x) dx via integration-by-parts ──────────────────────────────────


class TestDefiniteIntegralXTimesExp:
    def test_canonical_x_exp_x_unit_interval(self):
        """∫₀¹ x·e^x dx = 1 (textbook integration-by-parts canonical)."""
        lemma = definite_integral_x_times_exp(0.0, 1.0, c=1.0)
        assert abs(lemma.actual_value - 1.0) < 1e-12

    def test_negative_c_decay(self):
        """∫₀¹ x·e^(-x) dx = 1 - 2/e ≈ 0.2642 (parts; F(x) = e^(-x)·(-x-1))."""
        lemma = definite_integral_x_times_exp(0.0, 1.0, c=-1.0)
        expected = 1.0 - 2.0 / math.e
        assert abs(lemma.actual_value - expected) < 1e-12

    def test_c_equals_2(self):
        """∫₀¹ x·e^(2x) dx via parts: F(x) = e^(2x)·(2x - 1)/4; F(1) - F(0) = (e²·1 - 1·(-1))/4 = (e² + 1)/4."""
        lemma = definite_integral_x_times_exp(0.0, 1.0, c=2.0)
        expected = (math.exp(2.0) + 1.0) / 4.0
        assert abs(lemma.actual_value - expected) < 1e-12

    def test_c_zero_trivial_branch(self):
        """c=0 reduces to ∫ x dx = (1² - 0²)/2 = 0.5."""
        lemma = definite_integral_x_times_exp(0.0, 1.0, c=0.0)
        assert lemma.actual_value == 0.5

    def test_lemma_chain_has_5_steps(self):
        """5-step parts chain: identify → choose_u_dv → compute_du_v → apply_parts → evaluate_bounds."""
        lemma = definite_integral_x_times_exp(0.0, 1.0, c=1.0)
        assert len(lemma.derivation_steps) == 5
        operations = [s.operation for s in lemma.derivation_steps]
        assert operations == [
            "identify_integrand",
            "choose_u_dv",
            "compute_du_v",
            "apply_parts_formula",
            "evaluate_bounds",
        ]

    def test_intro_mentions_liate_heuristic(self):
        lemma = definite_integral_x_times_exp(0.0, 1.0, c=1.0)
        assert "LIATE" in lemma.introduction or "Algebraic" in lemma.introduction

    def test_invariant_parts_identity_holds(self):
        """∫_a^b u dv + ∫_a^b v du = [u·v]_a^b across diverse (a, b, c)."""
        cases = [(0.0, 1.0, 1.0), (0.0, 2.0, -1.5), (-1.0, 1.0, 0.5), (1.0, 3.0, 2.0)]
        for lower, upper, c in cases:
            lemma = definite_integral_x_times_exp(lower, upper, c)
            assert all(inv.holds for inv in lemma.invariant_checks), (
                f"invariant failed for (lower={lower}, upper={upper}, c={c})"
            )


# ── ∫ x·sin(c·x) dx via integration-by-parts ─────────────────────────────────


class TestDefiniteIntegralXTimesSin:
    def test_canonical_x_sin_x_zero_to_pi(self):
        """∫₀^π x·sin(x) dx = π (textbook; antiderivative (sin(x) - x·cos(x)) at π = π·1 = π)."""
        lemma = definite_integral_x_times_sin(0.0, math.pi, c=1.0)
        assert abs(lemma.actual_value - math.pi) < 1e-12

    def test_c_equals_2(self):
        """∫₀^π x·sin(2x) dx: F(x) = (sin(2x) - 2x·cos(2x))/4; F(π) - F(0) = (0 - 2π·1)/4 = -π/2."""
        lemma = definite_integral_x_times_sin(0.0, math.pi, c=2.0)
        expected = -math.pi / 2.0
        assert abs(lemma.actual_value - expected) < 1e-12

    def test_c_zero_trivial_branch(self):
        """c=0 → sin(0·x) = 0; integrand identically 0; result 0."""
        lemma = definite_integral_x_times_sin(0.0, math.pi, c=0.0)
        assert lemma.actual_value == 0.0

    def test_lemma_chain_has_5_steps(self):
        lemma = definite_integral_x_times_sin(0.0, math.pi, c=1.0)
        assert len(lemma.derivation_steps) == 5

    def test_invariant_parts_identity_holds(self):
        cases = [(0.0, math.pi, 1.0), (0.0, math.pi / 2, 1.0), (-math.pi, math.pi, 1.0)]
        for lower, upper, c in cases:
            lemma = definite_integral_x_times_sin(lower, upper, c)
            assert all(inv.holds for inv in lemma.invariant_checks), (
                f"invariant failed for (lower={lower}, upper={upper}, c={c})"
            )


# ── ∫ x·cos(c·x) dx via integration-by-parts ─────────────────────────────────


class TestDefiniteIntegralXTimesCos:
    def test_canonical_x_cos_x_zero_to_pi(self):
        """∫₀^π x·cos(x) dx = -2 (textbook; F(x) = cos(x) + x·sin(x); F(π) - F(0) = (-1 + 0) - (1 + 0) = -2)."""
        lemma = definite_integral_x_times_cos(0.0, math.pi, c=1.0)
        assert abs(lemma.actual_value - (-2.0)) < 1e-12

    def test_canonical_x_cos_zero_to_pi_over_2(self):
        """∫₀^(π/2) x·cos(x) dx = π/2 - 1 (F(π/2) = 0 + π/2·1 = π/2; F(0) = 1; π/2 - 1 ≈ 0.5708)."""
        lemma = definite_integral_x_times_cos(0.0, math.pi / 2, c=1.0)
        expected = math.pi / 2.0 - 1.0
        assert abs(lemma.actual_value - expected) < 1e-12

    def test_c_zero_trivial_branch(self):
        """c=0 → cos(0·x) = 1; integrand reduces to x; result = (1² - 0²)/2 = 0.5."""
        lemma = definite_integral_x_times_cos(0.0, 1.0, c=0.0)
        assert lemma.actual_value == 0.5

    def test_invariant_parts_identity_holds(self):
        cases = [(0.0, math.pi, 1.0), (0.0, math.pi / 2, 1.0), (1.0, 3.0, 0.5)]
        for lower, upper, c in cases:
            lemma = definite_integral_x_times_cos(lower, upper, c)
            assert all(inv.holds for inv in lemma.invariant_checks), (
                f"invariant failed for (lower={lower}, upper={upper}, c={c})"
            )


# ── ∫ x·sin(x²) and ∫ x·cos(x²) via u=x² substitution ─────────────────────────


class TestDefiniteIntegralXTrigViaUSub:
    def test_x_sin_x_squared_zero_to_one(self):
        """∫₀¹ x·sin(x²) dx via u=x² → ∫₀¹ (1/2)·sin(u) du = (1 - cos(1))/2 ≈ 0.2298."""
        lemma = definite_integral_xtrig_via_usub(0.0, 1.0, trig_fn="sin")
        expected = (1.0 - math.cos(1.0)) / 2.0
        assert abs(lemma.actual_value - expected) < 1e-12

    def test_x_cos_x_squared_zero_to_sqrt_pi(self):
        """∫₀^√π x·cos(x²) dx via u=x² → ∫₀^π (1/2)·cos(u) du = sin(π)/2 - 0 = 0."""
        sqrt_pi = math.sqrt(math.pi)
        lemma = definite_integral_xtrig_via_usub(0.0, sqrt_pi, trig_fn="cos")
        assert abs(lemma.actual_value - 0.0) < 1e-12

    def test_x_sin_x_squared_zero_to_sqrt_pi(self):
        """∫₀^√π x·sin(x²) dx via u=x² → ∫₀^π (1/2)·sin(u) du = -cos(π)/2 + cos(0)/2 = 1/2 + 1/2 = 1."""
        sqrt_pi = math.sqrt(math.pi)
        lemma = definite_integral_xtrig_via_usub(0.0, sqrt_pi, trig_fn="sin")
        assert abs(lemma.actual_value - 1.0) < 1e-12

    def test_lemma_chain_has_4_steps(self):
        """4-step u-sub chain: identify → apply_substitution → integrate_in_u → back_substitute_and_evaluate."""
        lemma = definite_integral_xtrig_via_usub(0.0, 1.0, trig_fn="sin")
        assert len(lemma.derivation_steps) == 4
        operations = [s.operation for s in lemma.derivation_steps]
        assert operations == [
            "identify_integrand",
            "apply_substitution",
            "integrate_in_u",
            "back_substitute_and_evaluate",
        ]

    def test_intro_mentions_u_substitution(self):
        lemma = definite_integral_xtrig_via_usub(0.0, 1.0, trig_fn="sin")
        assert "u-substitution" in lemma.introduction or "u = x²" in lemma.introduction

    def test_invariant_usub_identity_holds(self):
        cases = [(0.0, 1.0, "sin"), (0.0, 1.0, "cos"), (0.0, math.sqrt(math.pi), "sin")]
        for lower, upper, fn in cases:
            lemma = definite_integral_xtrig_via_usub(lower, upper, trig_fn=fn)
            assert all(inv.holds for inv in lemma.invariant_checks), (
                f"invariant failed for (lower={lower}, upper={upper}, fn={fn})"
            )

    def test_rejects_invalid_trig_fn(self):
        """Only 'sin' and 'cos' supported."""
        with pytest.raises(ValueError, match="sin.*cos"):
            definite_integral_xtrig_via_usub(0.0, 1.0, trig_fn="tan")


# ── Thesis-compliance source-grep ──────────────────────────────────────────────


def test_integration_substrate_thesis_compliant():
    """No sympy/scipy/numpy/torch/transformers imports."""
    path = (
        Path(__file__).resolve().parent.parent
        / "src" / "project_x" / "reasoning" / "integration.py"
    )
    source = path.read_text()
    forbidden = [
        "import sympy", "from sympy",
        "import scipy", "from scipy",
        "import numpy", "from numpy",
        "import torch", "from torch",
        "transformers", "sentence_transformers",
    ]
    for token in forbidden:
        assert token not in source, f"integration.py imports forbidden token '{token}'"
