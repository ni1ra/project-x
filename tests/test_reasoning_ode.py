"""Tests for src/project_x/reasoning/ode.py — Phase 13 cycle 8 #00P13c8-03.

Coverage:
- Canonical: maths-011 verbatim (dy/dx = 2y, y(0) = 3 → y(1) = 3·e² ≈ 22.167)
- x_0 default behavior + non-zero IC anchor
- Edge cases: k=0 constant, y_0=0 trivial, negative k decay, negative y_0 sign
- Lemma structure: 4-step chain + introduction + IC invariant
- Lemma render: Raphael-voice proof-shape
- Thesis-compliance: no scipy/sympy/numpy/torch imports

Cycle 8 minimum-viable scope; predicate-strength uniformity pass (independent-path
verifier via Taylor expansion of exp) deferred to cycle 9 per advisor 2026-05-11.
"""

from __future__ import annotations

import math
from pathlib import Path

from project_x.reasoning.ode import first_order_linear_ode_exp_solution


# ── canonical maths-011 target ────────────────────────────────────────────────

def test_maths_011_canonical_y1():
    """maths-011: dy/dx = 2y, y(0) = 3 → y(1) = 3·e² ≈ 22.16716829679195."""
    lemma = first_order_linear_ode_exp_solution(k=2.0, y_0=3.0, x_target=1.0)
    expected = 3.0 * math.exp(2.0)
    assert abs(lemma.actual_value - expected) < 1e-12
    assert abs(lemma.actual_value - 22.16716829679195) < 1e-9


def test_default_x_0_is_origin():
    """x_0 omitted → defaults to 0.0; matches explicit x_0=0.0 call."""
    implicit = first_order_linear_ode_exp_solution(k=2.0, y_0=3.0, x_target=1.0)
    explicit = first_order_linear_ode_exp_solution(k=2.0, y_0=3.0, x_target=1.0, x_0=0.0)
    assert implicit.actual_value == explicit.actual_value


# ── edge cases ─────────────────────────────────────────────────────────────────

def test_k_zero_constant_solution():
    """k = 0 → ODE dy/dx = 0 → y(x) ≡ y_0 (constant)."""
    lemma = first_order_linear_ode_exp_solution(k=0.0, y_0=5.0, x_target=10.0)
    assert lemma.actual_value == 5.0


def test_y_0_zero_trivial_zero():
    """y_0 = 0 → y(x) ≡ 0 (trivial constant-zero by ODE uniqueness; closed-form
    yields 0 because 0·e^anything = 0)."""
    lemma = first_order_linear_ode_exp_solution(k=2.0, y_0=0.0, x_target=1.0)
    assert lemma.actual_value == 0.0


def test_negative_k_exponential_decay():
    """k = -1, y_0 = 1, x_target = 1 → y(1) = 1/e ≈ 0.3679."""
    lemma = first_order_linear_ode_exp_solution(k=-1.0, y_0=1.0, x_target=1.0)
    assert abs(lemma.actual_value - (1.0 / math.e)) < 1e-12
    assert abs(lemma.actual_value - 0.36787944117144233) < 1e-9


def test_negative_y_0_sign_propagation():
    """Negative y_0 propagates sign through math.exp.
    Advisor cycle-8 #03 FYI — sign-flip bug class coverage."""
    lemma = first_order_linear_ode_exp_solution(k=2.0, y_0=-3.0, x_target=1.0)
    expected = -3.0 * math.exp(2.0)
    assert abs(lemma.actual_value - expected) < 1e-12
    assert lemma.actual_value < 0


def test_non_zero_x_0_anchor():
    """x_0 ≠ 0 IC anchor: dy/dx = 2y, y(1) = e² → y(2) = e⁴ ≈ 54.598."""
    lemma = first_order_linear_ode_exp_solution(
        k=2.0, y_0=math.exp(2.0), x_target=2.0, x_0=1.0,
    )
    expected = math.exp(4.0)
    assert abs(lemma.actual_value - expected) < 1e-10


# ── Lemma structure + invariants ───────────────────────────────────────────────

def test_lemma_chain_has_4_steps_in_order():
    """4-step chain: identify_form → separate_variables → integrate_and_apply_IC → evaluate_at_target."""
    lemma = first_order_linear_ode_exp_solution(k=2.0, y_0=3.0, x_target=1.0)
    assert len(lemma.derivation_steps) == 4
    operations = [s.operation for s in lemma.derivation_steps]
    assert operations == [
        "identify_form",
        "separate_variables",
        "integrate_and_apply_IC",
        "evaluate_at_target",
    ]


def test_lemma_has_introduction_prose():
    """add_introduction prose contains first-principles derivation phrases."""
    lemma = first_order_linear_ode_exp_solution(k=2.0, y_0=3.0, x_target=1.0)
    assert lemma.introduction != ""
    intro = lemma.introduction.lower()
    assert "separation of variables" in intro
    assert "initial condition" in intro
    assert "exponential" in intro


def test_lemma_ic_invariant_holds():
    """IC preservation invariant: y(x_0) == y_0."""
    lemma = first_order_linear_ode_exp_solution(k=2.0, y_0=3.0, x_target=1.0)
    assert len(lemma.invariant_checks) == 1
    inv = lemma.invariant_checks[0]
    assert "initial condition" in inv.predicate.lower()
    assert inv.holds is True
    assert inv.expected_value == 3.0
    assert abs(inv.expected_value - inv.actual_value) < 1e-15


def test_lemma_render_has_raphael_proof_shape():
    """Render contains 'Notice.' prelude + Step lines + Invariant block + 'Affirmative' close."""
    lemma = first_order_linear_ode_exp_solution(k=2.0, y_0=3.0, x_target=1.0)
    rendered = lemma.render()
    assert "Notice." in rendered
    assert "Step 1" in rendered
    assert "Step 4" in rendered
    assert "Invariant checks:" in rendered
    assert "Affirmative" in rendered


# ── thesis-compliance source-grep ──────────────────────────────────────────────

def test_ode_substrate_thesis_compliant():
    """No scipy/sympy/numpy/torch imports in ode.py. Organic-thesis binding."""
    path = Path(__file__).resolve().parent.parent / "src" / "project_x" / "reasoning" / "ode.py"
    source = path.read_text()
    forbidden = [
        "import sympy", "from sympy",
        "import scipy", "from scipy",
        "import numpy", "from numpy",
        "import torch", "from torch",
        "transformers", "sentence_transformers",
    ]
    for token in forbidden:
        assert token not in source, f"ode.py imports forbidden token '{token}'"
