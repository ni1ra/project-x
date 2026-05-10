"""Tests for src/project_x/reasoning/symbolic.py — Phase 13 #00P13c2-02.

Coverage:
- DerivationStep + Lemma dataclass mechanics + render() output shape
- solve_quadratic correctness against maths-001 ladder entry (3x² - 14x - 5 = 0 → 5, -1/3)
- expand_characteristic_polynomial_2x2 correctness against maths-002 ladder entry
  ([[2,1],[1,2]] → 1, 3)
- Edge cases: zero-coefficient, negative discriminant, non-2x2 matrix
- Organic-thesis compliance: substrate source has NO sympy/numpy/torch imports
"""

from __future__ import annotations

import inspect
import math

import pytest

import project_x.reasoning.symbolic as substrate
from project_x.reasoning.symbolic import (
    INTRO_CHAR_POLY_2X2,
    INTRO_QUADRATIC,
    DerivationStep,
    InvariantCheck,
    Lemma,
    expand_characteristic_polynomial_2x2,
    solve_quadratic,
)


class TestDerivationStep:
    def test_dataclass_basic(self):
        step = DerivationStep(
            step_index=0,
            operation="discriminant",
            inputs={"a": 3, "b": -14, "c": -5},
            output=256,
            justification="D = b² - 4ac",
        )
        assert step.step_index == 0
        assert step.operation == "discriminant"
        assert step.inputs == {"a": 3, "b": -14, "c": -5}
        assert step.output == 256


class TestLemmaContainer:
    def test_empty_lemma(self):
        lemma = Lemma(id="test", claim="trivial claim")
        assert lemma.id == "test"
        assert lemma.derivation_steps == []
        assert lemma.match is None
        assert lemma.actual_value is None
        assert lemma.tolerance == 0.001

    def test_add_step_increments_index(self):
        lemma = Lemma(id="test", claim="trivial")
        s1 = lemma.add_step("op_a", {}, 1, "j1")
        s2 = lemma.add_step("op_b", {}, 2, "j2")
        assert s1.step_index == 0
        assert s2.step_index == 1
        assert len(lemma.derivation_steps) == 2

    def test_render_includes_claim_steps_and_close(self):
        lemma = Lemma(id="test", claim="solve trivial")
        lemma.add_step("op_a", {"x": 1}, 2, "doubled")
        lemma.actual_value = 2
        rendered = lemma.render()
        assert "Notice." in rendered
        assert "solve trivial" in rendered
        assert "Step 1 — op_a" in rendered
        assert "Affirmative — 2" in rendered


class TestSolveQuadraticMaths001:
    """maths-001 ladder entry — canonical 3x² - 14x - 5 = 0; expected roots [5.0, -0.3333]."""

    def test_actual_value_matches_expected_roots(self):
        lemma = solve_quadratic(3, -14, -5, lemma_id="maths-001")
        assert lemma.actual_value is not None
        assert math.isclose(lemma.actual_value[0], -1 / 3, abs_tol=1e-6)
        assert math.isclose(lemma.actual_value[1], 5.0, abs_tol=1e-6)

    def test_derivation_chain_three_steps(self):
        lemma = solve_quadratic(3, -14, -5)
        assert len(lemma.derivation_steps) == 3
        assert [s.operation for s in lemma.derivation_steps] == [
            "discriminant",
            "sqrt",
            "root_pair",
        ]

    def test_discriminant_value(self):
        lemma = solve_quadratic(3, -14, -5)
        assert lemma.derivation_steps[0].output == 256

    def test_sqrt_value(self):
        lemma = solve_quadratic(3, -14, -5)
        assert math.isclose(lemma.derivation_steps[1].output, 16.0, abs_tol=1e-9)

    def test_render_raphael_voice(self):
        lemma = solve_quadratic(3, -14, -5, lemma_id="maths-001")
        rendered = lemma.render()
        assert "Notice." in rendered
        assert "Affirmative" in rendered
        assert "discriminant" in rendered.lower()


class TestSolveQuadraticEdges:
    def test_zero_a_raises(self):
        with pytest.raises(ValueError, match="not a quadratic"):
            solve_quadratic(0, 1, 1)

    def test_negative_discriminant_raises_not_implemented(self):
        # x² + 1 = 0 — complex roots beyond cycle 2 scope
        with pytest.raises(NotImplementedError, match="complex"):
            solve_quadratic(1, 0, 1)

    def test_repeated_root(self):
        # x² - 2x + 1 = 0 → (x - 1)² = 0 → x = 1, 1
        lemma = solve_quadratic(1, -2, 1)
        assert math.isclose(lemma.actual_value[0], 1.0)
        assert math.isclose(lemma.actual_value[1], 1.0)

    def test_zero_discriminant_boundary(self):
        # Boundary case D == 0 — must NOT raise (only D < 0 raises)
        lemma = solve_quadratic(1, -2, 1)
        assert lemma.derivation_steps[0].output == 0


class TestExpandCharacteristicPolynomial2x2Maths002:
    """maths-002 ladder entry — [[2,1],[1,2]]; expected eigenvalues [1.0, 3.0]."""

    def test_actual_value_matches_expected_eigenvalues(self):
        lemma = expand_characteristic_polynomial_2x2([[2, 1], [1, 2]], lemma_id="maths-002")
        assert math.isclose(lemma.actual_value[0], 1.0, abs_tol=1e-6)
        assert math.isclose(lemma.actual_value[1], 3.0, abs_tol=1e-6)

    def test_derivation_chain_four_steps(self):
        lemma = expand_characteristic_polynomial_2x2([[2, 1], [1, 2]])
        assert len(lemma.derivation_steps) == 4
        ops = [s.operation for s in lemma.derivation_steps]
        assert ops == ["trace", "det", "char_poly_coeffs", "solve_via_quadratic"]

    def test_trace(self):
        lemma = expand_characteristic_polynomial_2x2([[2, 1], [1, 2]])
        assert lemma.derivation_steps[0].output == 4

    def test_determinant(self):
        lemma = expand_characteristic_polynomial_2x2([[2, 1], [1, 2]])
        assert lemma.derivation_steps[1].output == 3


class TestExpandCharacteristicPolynomial2x2Edges:
    def test_non_2x2_raises(self):
        with pytest.raises(ValueError, match="2x2"):
            expand_characteristic_polynomial_2x2([[1, 2, 3], [4, 5, 6]])

    def test_diagonal_matrix(self):
        # [[5, 0], [0, 7]] → eigenvalues 5, 7
        lemma = expand_characteristic_polynomial_2x2([[5, 0], [0, 7]])
        assert math.isclose(lemma.actual_value[0], 5.0)
        assert math.isclose(lemma.actual_value[1], 7.0)

    def test_one_row_raises(self):
        with pytest.raises(ValueError, match="2x2"):
            expand_characteristic_polynomial_2x2([[1, 2]])


class TestLemmaIntroduction:
    """Phase 13 cycle 3 #00P13c3-02 Tier 1: Lemma.add_introduction + render() integration."""

    def test_default_empty(self):
        lemma = Lemma(id="test", claim="trivial")
        assert lemma.introduction == ""

    def test_add_introduction_sets_text(self):
        lemma = Lemma(id="test", claim="trivial")
        lemma.add_introduction("WHY this holds: foo bar.")
        assert lemma.introduction == "WHY this holds: foo bar."

    def test_render_includes_introduction_when_set(self):
        lemma = Lemma(id="test", claim="trivial")
        lemma.add_introduction("Foundational theorem says X.")
        lemma.add_step("op", {}, 1, "j")
        lemma.actual_value = 1
        rendered = lemma.render()
        assert "Foundational theorem says X." in rendered
        # Introduction renders BEFORE first Step
        intro_idx = rendered.index("Foundational theorem says X.")
        step_idx = rendered.index("Step 1")
        assert intro_idx < step_idx

    def test_render_skips_introduction_block_when_empty(self):
        # Backward-compat: lemma without introduction renders cycle-2-style
        lemma = Lemma(id="test", claim="trivial")
        lemma.add_step("op", {}, 1, "j")
        lemma.actual_value = 1
        rendered = lemma.render()
        # No empty extra blank-line prefix that would indicate intro section
        # (cycle 2 had: "Notice. trivial\n\nStep 1..."; cycle 3 same when intro empty)
        assert "Notice. trivial" in rendered
        assert "Step 1 — op" in rendered


class TestLemmaInvariantChecks:
    """Phase 13 cycle 3 #00P13c3-02 Tier 1: add_invariant_check + render() integration."""

    def test_default_empty(self):
        lemma = Lemma(id="test", claim="trivial")
        assert lemma.invariant_checks == []

    def test_add_invariant_check_appends(self):
        lemma = Lemma(id="test", claim="trivial")
        lemma.add_invariant_check("p1", 1.0, 1.0, "j1")
        lemma.add_invariant_check("p2", 2.0, 2.0, "j2")
        assert len(lemma.invariant_checks) == 2

    def test_holds_true_within_tolerance(self):
        lemma = Lemma(id="test", claim="trivial", tolerance=0.001)
        check = lemma.add_invariant_check("p", 1.0, 1.0001, "j")
        assert check.holds is True

    def test_holds_false_outside_tolerance(self):
        lemma = Lemma(id="test", claim="trivial", tolerance=0.001)
        check = lemma.add_invariant_check("p", 1.0, 1.5, "j")
        assert check.holds is False

    def test_holds_exact_for_non_numeric(self):
        lemma = Lemma(id="test", claim="trivial")
        check_eq = lemma.add_invariant_check("p", "expected", "expected", "j")
        check_neq = lemma.add_invariant_check("p", "expected", "actual", "j")
        assert check_eq.holds is True
        assert check_neq.holds is False

    def test_render_includes_invariant_checks_when_populated(self):
        lemma = Lemma(id="test", claim="trivial")
        lemma.add_step("op", {}, 1, "j")
        lemma.actual_value = 1
        lemma.add_invariant_check("trace = sum", 4, 4, "Vieta")
        rendered = lemma.render()
        assert "Invariant checks:" in rendered
        assert "trace = sum" in rendered
        assert "✓" in rendered  # passing check renders ✓

    def test_render_skips_invariant_block_when_empty(self):
        lemma = Lemma(id="test", claim="trivial")
        lemma.add_step("op", {}, 1, "j")
        lemma.actual_value = 1
        rendered = lemma.render()
        assert "Invariant checks:" not in rendered

    def test_failing_check_renders_x_mark(self):
        lemma = Lemma(id="test", claim="trivial")
        lemma.add_step("op", {}, 1, "j")
        lemma.actual_value = 1
        lemma.add_invariant_check("p", 4, 5, "j")
        rendered = lemma.render()
        assert "✗" in rendered


class TestSolveQuadraticIntroduction:
    """Tier 1: solve_quadratic primitive sets math-WHY introduction."""

    def test_introduction_set(self):
        lemma = solve_quadratic(3, -14, -5, lemma_id="maths-001")
        assert lemma.introduction == INTRO_QUADRATIC
        assert "Completing the square" in lemma.introduction
        assert "discriminant" in lemma.introduction.lower()

    def test_render_includes_math_why(self):
        lemma = solve_quadratic(3, -14, -5)
        rendered = lemma.render()
        assert "Completing the square" in rendered
        assert "Step 1 — discriminant" in rendered  # derivation still renders


class TestExpandCharPoly2x2InvariantChecks:
    """Tier 1: expand_characteristic_polynomial_2x2 emits Vieta invariants post-derivation."""

    def test_introduction_set(self):
        lemma = expand_characteristic_polynomial_2x2([[2, 1], [1, 2]], lemma_id="maths-002")
        assert lemma.introduction == INTRO_CHAR_POLY_2X2
        assert "eigenvector" in lemma.introduction.lower()
        assert "Vieta" in lemma.introduction

    def test_two_invariant_checks_produced(self):
        lemma = expand_characteristic_polynomial_2x2([[2, 1], [1, 2]])
        assert len(lemma.invariant_checks) == 2
        predicates = [c.predicate for c in lemma.invariant_checks]
        assert "tr(A) = λ₁ + λ₂" in predicates
        assert "det(A) = λ₁·λ₂" in predicates

    def test_invariants_hold_for_maths_002(self):
        lemma = expand_characteristic_polynomial_2x2([[2, 1], [1, 2]])
        # Eigenvalues are [1, 3]; trace = 4 = 1+3, det = 3 = 1*3
        for check in lemma.invariant_checks:
            assert check.holds is True

    def test_invariants_hold_for_diagonal(self):
        lemma = expand_characteristic_polynomial_2x2([[5, 0], [0, 7]])
        # Eigenvalues [5, 7]; trace = 12 = 5+7, det = 35 = 5*7
        for check in lemma.invariant_checks:
            assert check.holds is True

    def test_render_shows_check_marks(self):
        lemma = expand_characteristic_polynomial_2x2([[2, 1], [1, 2]])
        rendered = lemma.render()
        assert "Invariant checks:" in rendered
        assert "tr(A) = λ₁ + λ₂" in rendered
        assert "det(A) = λ₁·λ₂" in rendered
        # All passing → all ✓ no ✗
        assert "✓" in rendered
        assert "✗" not in rendered


class TestThesisCompliance:
    """Substrate source MUST NOT import sympy / numpy / torch / pretrained-derivative libs."""

    def test_no_sympy_import(self):
        source = inspect.getsource(substrate)
        assert "import sympy" not in source
        assert "from sympy" not in source

    def test_no_numpy_import(self):
        source = inspect.getsource(substrate)
        assert "import numpy" not in source
        assert "from numpy" not in source

    def test_no_torch_import(self):
        source = inspect.getsource(substrate)
        assert "import torch" not in source
        assert "from torch" not in source

    def test_no_pretrained_transformer_terms(self):
        source = inspect.getsource(substrate)
        # Match well-known pretrained-transformer derivative names that organic-thesis
        # forbids per docs/MANIFESTO.md § Standing orders.
        forbidden = [
            "transformers",
            "BGE",
            "MiniLM",
            "sentence_transformers",
            "llama_cpp",
            "Qwen",
            "Mistral",
        ]
        for term in forbidden:
            assert term not in source, f"organic-thesis violation: substrate imports {term}"
