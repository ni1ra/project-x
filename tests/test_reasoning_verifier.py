"""Tests for src/project_x/reasoning/verifier.py — Phase 13 #00P13c2-03.

Coverage:
- numerical_verify on substrate-produced solve_quadratic lemmas (maths-001 shape) → match=True
- numerical_verify on substrate-produced char_poly_2x2 lemmas (maths-002 shape) → match=True
- Mismatch detection (manually-corrupted actual_value)
- Unsupported operation graceful failure (no exception)
- Empty derivation chain graceful failure
- Negative discriminant graceful handling (substrate raises; verifier-only test
  builds the lemma manually to exercise sentinel path)
- _parse_sandbox_output edge cases (missing VERIFY_RESULT, sentinel string, malformed)
- _close_enough numerical_close + symbolic_match + unknown-method paths

Sandbox isolation: monkey-patches SANDBOX_ROOT to tmp_path so tests don't pollute
the real `sandbox/` directory.
"""

from __future__ import annotations

import math

import pytest

import project_x.experiments.semantic_memory_agent as sma
from project_x.reasoning.symbolic import (
    DerivationStep,
    Lemma,
    expand_characteristic_polynomial_2x2,
    solve_quadratic,
)
from project_x.reasoning.verifier import (
    _close_enough,
    _eigenvalue_2x2_verification_script,
    _parse_sandbox_output,
    _quadratic_newton_verification_script,
    _quadratic_verification_script,
    numerical_verify,
    verify_quadratic_via_newton,
)


@pytest.fixture
def sandbox_isolated(tmp_path, monkeypatch):
    """Redirect SANDBOX_ROOT to tmp_path/sandbox so test runs don't pollute real sandbox."""
    sb = tmp_path / "sandbox"
    sb.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(sma, "SANDBOX_ROOT", sb)
    return sb


class TestNumericalVerifyQuadratic:
    """Substrate solve_quadratic lemmas → sandbox second opinion → match=True."""

    def test_maths_001_match(self, sandbox_isolated):
        # Ladder maths-001: 3x² - 14x - 5 = 0 → expected [5.0, -0.3333...]
        lemma = solve_quadratic(3, -14, -5, lemma_id="maths-001")
        verified = numerical_verify(lemma, expected_value=[-1 / 3, 5.0], tolerance=0.001)
        assert verified.match is True

    def test_consistency_fallback_when_no_expected(self, sandbox_isolated):
        # Without expected_value: verifier compares sandbox to substrate's actual_value.
        lemma = solve_quadratic(3, -14, -5)
        verified = numerical_verify(lemma)
        assert verified.match is True
        assert verified.expected_value is None  # not set; consistency check used actual

    def test_corrupted_actual_value_caught(self, sandbox_isolated):
        # Manually corrupt the substrate's actual_value; sandbox second opinion catches it.
        lemma = solve_quadratic(3, -14, -5)
        lemma.actual_value = [-99.0, 99.0]  # wrong on purpose
        verified = numerical_verify(lemma)
        # No expected_value; reference = corrupted actual; sandbox produces correct → mismatch
        assert verified.match is False

    def test_repeated_root_match(self, sandbox_isolated):
        # x² - 2x + 1 = 0 → x = 1, 1
        lemma = solve_quadratic(1, -2, 1)
        verified = numerical_verify(lemma, expected_value=[1.0, 1.0])
        assert verified.match is True

    def test_tolerance_loose_match(self, sandbox_isolated):
        # Slight expected mismatch within tolerance
        lemma = solve_quadratic(3, -14, -5)
        verified = numerical_verify(
            lemma, expected_value=[-0.3334, 5.0001], tolerance=0.01
        )
        assert verified.match is True

    def test_tolerance_tight_mismatch(self, sandbox_isolated):
        # Same expected; tolerance too tight
        lemma = solve_quadratic(3, -14, -5)
        verified = numerical_verify(
            lemma, expected_value=[-0.34, 5.05], tolerance=1e-6
        )
        assert verified.match is False


class TestNumericalVerifyEigenvalues:
    """Substrate expand_characteristic_polynomial_2x2 lemmas → sandbox → match=True."""

    def test_maths_002_match(self, sandbox_isolated):
        # Ladder maths-002: [[2, 1], [1, 2]] → expected [1.0, 3.0]
        lemma = expand_characteristic_polynomial_2x2([[2, 1], [1, 2]], lemma_id="maths-002")
        verified = numerical_verify(lemma, expected_value=[1.0, 3.0], tolerance=0.001)
        assert verified.match is True

    def test_diagonal_match(self, sandbox_isolated):
        lemma = expand_characteristic_polynomial_2x2([[5, 0], [0, 7]])
        verified = numerical_verify(lemma, expected_value=[5.0, 7.0])
        assert verified.match is True


class TestNumericalVerifyEdges:
    def test_empty_derivation_no_exception(self, sandbox_isolated):
        lemma = Lemma(id="empty", claim="trivial")
        verified = numerical_verify(lemma)
        assert verified.match is False

    def test_unsupported_operation_no_exception(self, sandbox_isolated):
        # First step has operation the verifier doesn't recognize → graceful False
        lemma = Lemma(id="unsupported", claim="alien op")
        lemma.add_step("alien_operation", {}, "?", "made up")
        verified = numerical_verify(lemma)
        assert verified.match is False


class TestParseSandboxOutput:
    def test_normal_list_payload(self):
        run_result = "[sandbox python] exit=0\nstdout: VERIFY_RESULT:[1.0, 3.0]\n"
        parsed = _parse_sandbox_output(run_result)
        assert parsed == [1.0, 3.0]

    def test_negative_discriminant_sentinel(self):
        run_result = "[sandbox python] exit=0\nstdout: VERIFY_RESULT:NEGATIVE_DISCRIMINANT\n"
        parsed = _parse_sandbox_output(run_result)
        assert parsed is None

    def test_complex_eigenvalues_sentinel(self):
        run_result = "[sandbox python] exit=0\nstdout: VERIFY_RESULT:COMPLEX_EIGENVALUES\n"
        parsed = _parse_sandbox_output(run_result)
        assert parsed is None

    def test_missing_verify_line(self):
        run_result = "[sandbox python] exit=0\nstdout: random output\n"
        parsed = _parse_sandbox_output(run_result)
        assert parsed is None

    def test_malformed_payload_returns_none(self):
        run_result = "[sandbox python] exit=0\nstdout: VERIFY_RESULT:not-a-literal\n"
        parsed = _parse_sandbox_output(run_result)
        assert parsed is None

    def test_literal_eval_refuses_code_execution(self):
        # ast.literal_eval refuses anything that isn't a literal, including __import__
        run_result = "[sandbox python] exit=0\nstdout: VERIFY_RESULT:__import__('os').getcwd()\n"
        parsed = _parse_sandbox_output(run_result)
        assert parsed is None


class TestCloseEnough:
    def test_numerical_close_list_match(self):
        assert _close_enough([1.0, 2.0], [1.0, 2.0001], 0.001, "numerical_close") is True

    def test_numerical_close_list_mismatch_value(self):
        assert _close_enough([1.0, 2.0], [1.5, 2.0], 0.001, "numerical_close") is False

    def test_numerical_close_list_length_mismatch(self):
        assert _close_enough([1.0], [1.0, 2.0], 0.001, "numerical_close") is False

    def test_numerical_close_scalar(self):
        assert _close_enough(3.14, 3.141, 0.01, "numerical_close") is True
        assert _close_enough(3.14, 3.20, 0.01, "numerical_close") is False

    def test_symbolic_match_strict(self):
        assert _close_enough([1, 2], [1, 2], 0.0, "symbolic_match") is True
        assert _close_enough([1, 2], [2, 1], 0.0, "symbolic_match") is False

    def test_unknown_method_refused(self):
        # Refuse silent acceptance of unknown verification methods
        assert _close_enough([1.0], [1.0], 0.001, "vibes_match") is False


class TestVerificationScripts:
    """The sandbox-side scripts must run end-to-end producing parseable output."""

    def test_quadratic_script_parses(self, sandbox_isolated):
        script = _quadratic_verification_script(3, -14, -5)
        run_result = sma._tool_run_python_sandbox(script, timeout=10)
        parsed = _parse_sandbox_output(run_result)
        assert parsed is not None
        assert math.isclose(parsed[0], -1 / 3, abs_tol=1e-6)
        assert math.isclose(parsed[1], 5.0, abs_tol=1e-6)

    def test_eigenvalue_script_parses(self, sandbox_isolated):
        script = _eigenvalue_2x2_verification_script([[2, 1], [1, 2]])
        run_result = sma._tool_run_python_sandbox(script, timeout=10)
        parsed = _parse_sandbox_output(run_result)
        assert parsed is not None
        assert math.isclose(parsed[0], 1.0, abs_tol=1e-6)
        assert math.isclose(parsed[1], 3.0, abs_tol=1e-6)

    def test_quadratic_script_negative_discriminant(self, sandbox_isolated):
        # x² + 1 = 0 → D = -4 → sentinel printed
        script = _quadratic_verification_script(1, 0, 1)
        run_result = sma._tool_run_python_sandbox(script, timeout=10)
        assert "NEGATIVE_DISCRIMINANT" in run_result


class TestVerifyQuadraticViaNewton:
    """Phase 13 cycle 5 #00P13c5-02 — Newton's-method divergent-verifier-path tests
    (closes cycle 4 #24 acknowledged-gap; Newton extension shipped without dedicated tests).

    Coverage shapes:
    - Convergence: Newton iterates to one real root; Vieta deflation recovers the second.
    - Closed-form equivalence: agrees with `_quadratic_verification_script` on shared canonicals.
    - Negative discriminant: sentinel-detected → returns False (graceful, not exception).
    - Tolerance: returns True iff sorted-roots match expected within tolerance.
    - Edge regimes: repeated root + irrational roots + scaled coefficients (Newton must converge
      across magnitude regimes; Vieta deflation must hold without re-using closed-form).

    The whole point of this verifier is to be ALGORITHMICALLY DIFFERENT from substrate's
    closed-form `solve_quadratic` — same answer space via different code path. These tests
    verify the convergence + equivalence properties; they do NOT verify substrate (that's
    `TestNumericalVerifyQuadratic`).
    """

    def test_newton_converges_on_distinct_real_roots(self, sandbox_isolated):
        # Ladder maths-001 shape: 3x² - 14x - 5 = 0 → roots [-1/3, 5.0]
        assert verify_quadratic_via_newton(3, -14, -5, expected=[-1 / 3, 5.0], tolerance=0.001) is True

    def test_newton_repeated_root(self, sandbox_isolated):
        # x² - 2x + 1 = 0 → discriminant = 0; Newton converges to 1.0; Vieta deflates to 1.0.
        assert verify_quadratic_via_newton(1, -2, 1, expected=[1.0, 1.0], tolerance=0.001) is True

    def test_newton_irrational_roots(self, sandbox_isolated):
        # x² - 2 = 0 → roots ±√2; Newton converges to one, Vieta yields -that.
        assert verify_quadratic_via_newton(1, 0, -2, expected=[-math.sqrt(2), math.sqrt(2)], tolerance=0.001) is True

    def test_newton_negative_discriminant_returns_false(self, sandbox_isolated):
        # x² + 1 = 0 → D = -4 → sentinel; verifier refuses to claim a match.
        assert verify_quadratic_via_newton(1, 0, 1, expected=[0.0, 0.0]) is False

    def test_newton_mismatch_caught_outside_tolerance(self, sandbox_isolated):
        # Right roots [-1/3, 5.0]; expected wrong-by-2.0 → outside default tolerance.
        assert verify_quadratic_via_newton(3, -14, -5, expected=[-1 / 3 + 2.0, 5.0 + 2.0]) is False

    def test_newton_match_within_loose_tolerance(self, sandbox_isolated):
        # Right roots ≈ [-0.333, 5.000]; expected slightly off but within loose tolerance.
        assert verify_quadratic_via_newton(3, -14, -5, expected=[-0.34, 4.99], tolerance=0.05) is True

    def test_newton_agrees_with_closed_form_on_canonical(self, sandbox_isolated):
        # Newton + closed-form must produce equivalent root sets on the same input.
        # If the two paths disagree, that signals a divergent-verifier inconsistency
        # (the whole point of cycle 4 #24's Newton extension is "different algorithm,
        # same answer" — divergence here would falsify the design).
        closed_form = _quadratic_verification_script(2, -7, 3)
        newton_form = _quadratic_newton_verification_script(2, -7, 3)
        cf_run = sma._tool_run_python_sandbox(closed_form, timeout=10)
        nm_run = sma._tool_run_python_sandbox(newton_form, timeout=10)
        cf_parsed = _parse_sandbox_output(cf_run)
        nm_parsed = _parse_sandbox_output(nm_run)
        assert cf_parsed is not None and nm_parsed is not None
        assert len(cf_parsed) == 2 and len(nm_parsed) == 2
        # Both sorted ascending; element-wise tight match.
        assert math.isclose(cf_parsed[0], nm_parsed[0], abs_tol=1e-6)
        assert math.isclose(cf_parsed[1], nm_parsed[1], abs_tol=1e-6)

    def test_newton_scaled_coefficients(self, sandbox_isolated):
        # Order-of-magnitude scaling: Newton must converge across coefficient regimes.
        # 100x² - 300x + 200 = 0 → roots [1.0, 2.0] (factored: 100(x-1)(x-2)).
        assert verify_quadratic_via_newton(100, -300, 200, expected=[1.0, 2.0], tolerance=0.001) is True
