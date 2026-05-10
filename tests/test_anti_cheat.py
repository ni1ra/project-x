"""Tests for the anti-cheat mechanism (#00P13c4-24).

Two surfaces under test:
  - Probe + differential test work correctly on REAL substrate (solve_quadratic,
    expand_characteristic_polynomial_2x2). Real substrate is anti-cheat-clean
    because it computes from scratch per-input; surrogates must pass.
  - Probe CATCHES a FAKE OVERFIT SUBSTRATE that hardcodes the canonical answer
    regardless of input. memorization_signal should hit 1.0 on the fake.

Together these establish that the probe machinery (a) doesn't false-positive
on legitimate substrate, (b) actually detects the cheat pattern lain flagged.
"""

from __future__ import annotations

import pytest

import project_x.experiments.semantic_memory_agent as sma
from project_x.anti_cheat import (
    AntiCheatProbe,
    CapabilityTestResult,
    char_poly_2x2_eigenvalues_predicate,
    differential_capability_test,
    generate_surrogate_char_poly_2x2,
    generate_surrogate_quadratic,
    quadratic_roots_predicate,
)
from project_x.reasoning.symbolic import (
    Lemma,
    expand_characteristic_polynomial_2x2,
    solve_quadratic,
)
from project_x.reasoning.verifier import verify_quadratic_via_newton


@pytest.fixture
def sandbox_isolated(tmp_path, monkeypatch):
    """Redirect SANDBOX_ROOT to tmp_path/sandbox (mirrors test_reasoning_verifier pattern)."""
    sb = tmp_path / "sandbox"
    sb.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(sma, "SANDBOX_ROOT", sb)
    return sb


# --- Surrogate generator tests ---


def test_generate_surrogate_quadratic_returns_real_discriminant_variants():
    canonical = (3, -14, -5)  # maths-001
    surrogates = generate_surrogate_quadratic(canonical, n=3)
    assert len(surrogates) == 3
    for a, b, c in surrogates:
        assert a != 0
        assert b * b - 4 * a * c > 0
        assert (a, b, c) != canonical


def test_generate_surrogate_quadratic_n_2_returns_first_two():
    canonical = (3, -14, -5)
    surrogates = generate_surrogate_quadratic(canonical, n=2)
    assert len(surrogates) == 2


def test_generate_surrogate_quadratic_zero_a_rejected():
    with pytest.raises(ValueError, match="non-zero"):
        generate_surrogate_quadratic((0, 1, 2), n=3)


def test_generate_surrogate_char_poly_2x2_returns_real_eigenvalue_variants():
    canonical = [[2, 1], [1, 2]]  # maths-002 (eigenvalues 1, 3)
    surrogates = generate_surrogate_char_poly_2x2(canonical, n=3)
    assert len(surrogates) == 3
    for matrix in surrogates:
        a, b = matrix[0]
        c, d = matrix[1]
        trace = a + d
        det = a * d - b * c
        assert trace * trace - 4 * det > 0
        assert matrix != canonical


# --- Predicate tests ---


def test_quadratic_roots_predicate_accepts_correct_roots():
    # 3x² - 14x - 5 = 0 → roots [-1/3, 5]
    assert quadratic_roots_predicate((3, -14, -5), [-1 / 3, 5])


def test_quadratic_roots_predicate_rejects_unsorted():
    assert not quadratic_roots_predicate((3, -14, -5), [5, -1 / 3])


def test_quadratic_roots_predicate_rejects_wrong_shape():
    assert not quadratic_roots_predicate((3, -14, -5), [5])
    assert not quadratic_roots_predicate((3, -14, -5), "not a list")
    assert not quadratic_roots_predicate((3, -14, -5), [1, 2, 3])


def test_quadratic_roots_predicate_rejects_wrong_roots():
    # 3x² - 14x - 5 = 0; [-1, 1] do NOT satisfy.
    assert not quadratic_roots_predicate((3, -14, -5), [-1.0, 1.0])


def test_char_poly_2x2_eigenvalues_predicate_accepts_correct_eigenvalues():
    # [[2,1],[1,2]] eigenvalues are [1, 3]; trace=4, det=3.
    assert char_poly_2x2_eigenvalues_predicate(([[2, 1], [1, 2]],), [1.0, 3.0])


def test_char_poly_2x2_eigenvalues_predicate_rejects_wrong_eigenvalues():
    # Hardcoded [1, 3] but matrix is different → Vieta fails.
    assert not char_poly_2x2_eigenvalues_predicate(([[5, 2], [1, 3]],), [1.0, 3.0])


# --- differential_capability_test on REAL substrate ---


def test_differential_capability_test_real_solve_quadratic_genuine_capability():
    """Real solve_quadratic computes correctly per-input → no memorization signal."""
    canonical = (3, -14, -5)
    surrogates = generate_surrogate_quadratic(canonical, n=3)
    probe = AntiCheatProbe(
        probe_id="maths-001-probe",
        canonical_inputs=canonical,
        surrogate_inputs=surrogates,
        answer_predicate=quadratic_roots_predicate,
        notes="Real solve_quadratic must pass canonical AND all surrogates.",
    )
    result = differential_capability_test(solve_quadratic, probe)

    assert result.canonical_match is True
    assert all(result.surrogate_matches), (
        f"all surrogates should pass; got {result.surrogate_matches}"
    )
    assert result.surrogate_pass_rate == 1.0
    assert result.memorization_signal == 0.0  # genuine capability


def test_differential_capability_test_real_char_poly_2x2_genuine_capability():
    """Real expand_characteristic_polynomial_2x2 must pass surrogates too."""
    canonical = [[2, 1], [1, 2]]
    surrogates = generate_surrogate_char_poly_2x2(canonical, n=3)
    probe = AntiCheatProbe(
        probe_id="maths-002-probe",
        canonical_inputs=(canonical,),
        surrogate_inputs=[(s,) for s in surrogates],
        answer_predicate=char_poly_2x2_eigenvalues_predicate,
    )
    result = differential_capability_test(expand_characteristic_polynomial_2x2, probe)

    assert result.canonical_match is True
    assert all(result.surrogate_matches)
    assert result.memorization_signal == 0.0


# --- differential_capability_test on FAKE OVERFIT SUBSTRATE ---


def _fake_overfit_solve_quadratic(a: float, b: float, c: float, lemma_id: str = "fake"):
    """Hardcodes maths-001's canonical answer regardless of input.

    This IS the cheat-shape lain flagged: function body IS the canonical
    answer; doesn't compute. Probe must catch it.
    """
    lemma = Lemma(
        id=lemma_id,
        claim=f"FAKE: solve {a}x² + {b}x + {c} = 0",
        actual_value=[-1 / 3, 5],
    )
    lemma.add_step(
        operation="discriminant",
        inputs={"a": a, "b": b, "c": c},
        output="hardcoded; doesn't compute",
        justification="fake — always returns maths-001 answer",
    )
    return lemma


def test_differential_capability_test_catches_overfit_substrate():
    """Fake substrate hardcoding canonical answer → memorization_signal == 1.0."""
    canonical = (3, -14, -5)
    surrogates = generate_surrogate_quadratic(canonical, n=3)
    probe = AntiCheatProbe(
        probe_id="maths-001-overfit-probe",
        canonical_inputs=canonical,
        surrogate_inputs=surrogates,
        answer_predicate=quadratic_roots_predicate,
        notes="Fake substrate hardcodes canonical answer; probe must detect.",
    )
    result = differential_capability_test(_fake_overfit_solve_quadratic, probe)

    assert result.canonical_match is True  # hardcoded answer IS correct for canonical
    assert not any(result.surrogate_matches), (
        f"hardcoded answer must FAIL all surrogates; got {result.surrogate_matches}"
    )
    assert result.surrogate_pass_rate == 0.0
    assert result.memorization_signal == 1.0  # max signal


# --- Edge cases ---


def _fake_raising_substrate(*args, **kwargs):
    """Substrate that always raises — should count as non-match, not test error."""
    raise ValueError("substrate broken")


def test_differential_capability_test_handles_raising_substrate():
    """Substrate raising on every input → canonical_match False; no test error."""
    canonical = (3, -14, -5)
    surrogates = generate_surrogate_quadratic(canonical, n=3)
    probe = AntiCheatProbe(
        probe_id="raising-probe",
        canonical_inputs=canonical,
        surrogate_inputs=surrogates,
        answer_predicate=quadratic_roots_predicate,
    )
    result = differential_capability_test(_fake_raising_substrate, probe)

    assert result.canonical_match is False
    assert not any(result.surrogate_matches)
    # signal collapses to 0.0 when canonical fails — substrate is broken, not
    # memorizing
    assert result.memorization_signal == 0.0


def test_capability_test_result_dataclass_shape():
    """Smoke test on CapabilityTestResult fields."""
    canonical = (3, -14, -5)
    surrogates = generate_surrogate_quadratic(canonical, n=3)
    probe = AntiCheatProbe(
        probe_id="shape-probe",
        canonical_inputs=canonical,
        surrogate_inputs=surrogates,
        answer_predicate=quadratic_roots_predicate,
    )
    result = differential_capability_test(solve_quadratic, probe)

    assert isinstance(result, CapabilityTestResult)
    assert result.probe_id == "shape-probe"
    assert isinstance(result.canonical_match, bool)
    assert isinstance(result.surrogate_matches, list)
    assert isinstance(result.surrogate_pass_rate, float)
    assert isinstance(result.memorization_signal, float)


# --- AntiCheatProbe documents surrogate-author independence (cycle 4 default) ---


def test_anti_cheat_probe_default_surrogate_author_is_builder():
    probe = AntiCheatProbe(
        probe_id="default-author",
        canonical_inputs=(3, -14, -5),
        surrogate_inputs=[(1, -1, -1)],
        answer_predicate=quadratic_roots_predicate,
    )
    assert probe.surrogate_author == "builder (rule-based)"


def test_anti_cheat_probe_explicit_lain_authored_surrogates():
    """Cycle 5+ may set surrogate_author='lain' for stronger anti-cheat strength."""
    probe = AntiCheatProbe(
        probe_id="lain-authored",
        canonical_inputs=(3, -14, -5),
        surrogate_inputs=[(1, -2, -1)],
        answer_predicate=quadratic_roots_predicate,
        surrogate_author="lain",
    )
    assert probe.surrogate_author == "lain"


# --- Newton's-method divergent-verifier-path tests (Candidate F) ---


def test_verify_quadratic_via_newton_maths_001(sandbox_isolated):
    """Newton + Vieta deflation converges to maths-001 roots [-1/3, 5]."""
    assert verify_quadratic_via_newton(3, -14, -5, [-1 / 3, 5], tolerance=0.001)


def test_verify_quadratic_via_newton_negative_discriminant_returns_false(sandbox_isolated):
    """x² + 1 = 0 has no real roots; sentinel routes to False without exception."""
    assert not verify_quadratic_via_newton(1, 0, 1, [0.0, 0.0])


def test_verify_quadratic_via_newton_wrong_expected_returns_false(sandbox_isolated):
    """Newton converges to correct roots; tolerance comparison rejects bogus expected."""
    assert not verify_quadratic_via_newton(3, -14, -5, [99.0, 100.0])
