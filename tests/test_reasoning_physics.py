"""Tests for src/project_x/reasoning/physics.py — Phase 13 #00P13c4-02.

Coverage:
  - Each primitive's closed-form correctness on canonical ladder inputs (matches
    `gpt-codex/benchmark/physics/ladder.jsonl` expected values at recorded tolerance).
  - Anti-cheat-aware gate (cycle 4 #00P13c4-24): each primitive's substrate produces
    `memorization_signal == 0.0` across surrogate input families. A primitive that
    hardcoded one ladder entry's answer would fail this gate.
  - Lemma render() includes intro prose + invariant check rendering.
  - Thesis-compliance source-grep: NO sympy / numpy / scipy / torch / transformers /
    sentence_transformers imports in physics.py.
  - Boundary cases (non-positive inputs raise; superluminal v raises for relativistic_momentum).
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from project_x.anti_cheat import (
    AntiCheatProbe,
    differential_capability_test,
)
from project_x.reasoning.physics import (
    free_fall_time,
    pendulum_period,
    relativistic_momentum,
)


# --- Canonical-ladder correctness ---


def test_free_fall_time_matches_physics_001():
    """physics-001: h=80m, g=9.81 → t ≈ 4.04s (ladder expected, tolerance 0.05)."""
    lemma = free_fall_time(80, 9.81)
    assert abs(lemma.actual_value - 4.04) < 0.05
    assert all(inv.holds for inv in lemma.invariant_checks), (
        f"invariant checks failed: {[i.predicate for i in lemma.invariant_checks if not i.holds]}"
    )


def test_pendulum_period_matches_physics_002():
    """physics-002: L=1.0, g=9.81 → T ≈ 2.007s (ladder expected, tolerance 0.05)."""
    lemma = pendulum_period(1.0, 9.81)
    assert abs(lemma.actual_value - 2.007) < 0.05
    assert all(inv.holds for inv in lemma.invariant_checks)


def test_relativistic_momentum_matches_physics_003():
    """physics-003: m=9.11e-31, v=0.9·3e8, c=3e8 → p ≈ 5.64e-22 (tolerance 0.10)."""
    m_e = 9.11e-31
    c = 3.0e8
    v = 0.9 * c
    lemma = relativistic_momentum(m_e, v, c)
    # Ladder uses tolerance 0.10 (10% relative) for relativistic momentum; mirror.
    assert abs(lemma.actual_value - 5.64e-22) / 5.64e-22 < 0.10


# --- Anti-cheat differential capability gate ---


def _free_fall_predicate(inputs, output):
    """Output is float t with t² · g / 2 ≈ h (kinematic identity).

    Tolerance 1e-3 relative: loose enough to pass rounded canonical answer
    (ladder records t = 4.04, exact is 4.0386...) but tight enough to fail
    when a hardcoded-canonical substrate is run on surrogate inputs (the
    reconstructed h is off by 50%+).
    """
    h, g = inputs
    if not isinstance(output, (int, float)) or output <= 0:
        return False
    reconstructed_h = (output * output * g) / 2.0
    tolerance = 1e-3 * max(abs(h), 1.0)
    return abs(reconstructed_h - h) < tolerance


def _pendulum_predicate(inputs, output):
    """Output is float T with T² · g / L ≈ 4π² (universal dimensionless invariant)."""
    L, g = inputs
    if not isinstance(output, (int, float)) or output <= 0:
        return False
    dimensionless = (output * output * g) / L
    return abs(dimensionless - 4 * math.pi * math.pi) < 1e-4


def _relativistic_momentum_predicate(inputs, output):
    """Output is float p; verify via energy-momentum relation route — independent of substrate's γmv.

    Route: p (substrate) → E = √((pc)² + (mc²)²) → v_recovered = pc²/E. Compare to input v.
    The relation E² = (pc)² + (mc²)² is the spacetime-interval norm of the four-momentum,
    derivable from Lorentz invariance — it does NOT presuppose substrate's `p = γmv`. Algebra
    routes through energy invariant + four-momentum components, never re-computing γ or γmv.

    Cycle 5 #00P13c5-01: replaced cycle 4's γmv-re-derivation predicate per advisor catch
    2026-05-10 (predicate-strength asymmetry — old predicate shared substrate's formula,
    weakening discrimination of library-import-vs-derivation). New route preserves memorization-
    vs-computation discrimination (hardcoded canonical fails on surrogate v_recovered) while
    gaining computational independence from substrate's algebra.
    """
    m, v, c = inputs
    if not isinstance(output, (int, float)):
        return False
    if abs(v) >= c:
        return False
    p = output
    rest_energy = m * c * c
    pc_value = p * c
    e_total_sq = pc_value * pc_value + rest_energy * rest_energy
    if e_total_sq <= 0:
        return False
    e_total = math.sqrt(e_total_sq)
    v_recovered = pc_value * c / e_total
    return abs(v_recovered - v) / max(abs(v), 1.0) < 1e-4


def test_free_fall_time_passes_anti_cheat_probe():
    """Surrogates cover Earth / Moon / Mars / Jupiter gravities + varied heights."""
    canonical = (80, 9.81)
    surrogates = [
        (125, 9.81),    # Different height same Earth
        (80, 1.62),     # Same height Moon gravity
        (45, 3.71),     # Mars
        (1000, 24.79),  # Different scale Jupiter
        (250, 9.81),    # Different height same Earth
    ]
    probe = AntiCheatProbe(
        probe_id="free_fall_time_probe",
        canonical_inputs=canonical,
        surrogate_inputs=surrogates,
        answer_predicate=_free_fall_predicate,
        notes="Substrate must compute kinematic identity across surface-gravity regimes.",
    )
    result = differential_capability_test(free_fall_time, probe)

    assert result.canonical_match is True
    assert all(result.surrogate_matches)
    assert result.memorization_signal == 0.0


def test_pendulum_period_passes_anti_cheat_probe():
    """Surrogates vary length + gravity; T²·g/L = 4π² must hold across all."""
    canonical = (1.0, 9.81)
    surrogates = [
        (2.0, 9.81),      # Twice the length
        (0.5, 9.81),      # Half the length
        (1.0, 1.62),      # Moon gravity
        (3.5, 3.71),      # Mars + longer
        (10.0, 9.81),     # Order-of-magnitude longer
    ]
    probe = AntiCheatProbe(
        probe_id="pendulum_period_probe",
        canonical_inputs=canonical,
        surrogate_inputs=surrogates,
        answer_predicate=_pendulum_predicate,
        notes="Substrate must compute period across pendulum length + gravity regimes.",
    )
    result = differential_capability_test(pendulum_period, probe)

    assert result.canonical_match is True
    assert all(result.surrogate_matches)
    assert result.memorization_signal == 0.0


def test_relativistic_momentum_passes_anti_cheat_probe():
    """Surrogates vary mass + velocity at relativistic + subluminal regimes."""
    c = 3.0e8
    canonical = (9.11e-31, 0.9 * c, c)  # electron at 0.9c
    surrogates = [
        (1.67e-27, 0.9 * c, c),  # proton at 0.9c (different mass)
        (9.11e-31, 0.5 * c, c),  # electron at 0.5c (different velocity)
        (9.11e-31, 0.99 * c, c), # electron at 0.99c (ultra-relativistic)
        (1.67e-27, 0.1 * c, c),  # proton at 0.1c (near-Newtonian)
    ]
    probe = AntiCheatProbe(
        probe_id="relativistic_momentum_probe",
        canonical_inputs=canonical,
        surrogate_inputs=surrogates,
        answer_predicate=_relativistic_momentum_predicate,
        notes="Substrate must compute γmv across mass scales + velocity regimes.",
    )
    result = differential_capability_test(relativistic_momentum, probe)

    assert result.canonical_match is True
    assert all(result.surrogate_matches)
    assert result.memorization_signal == 0.0


# --- Overfit-detector: cycle 4 anti-cheat catches hardcoded-answer substrate ---


def _fake_overfit_free_fall(h: float, g: float, lemma_id: str = "fake"):
    """Hardcodes physics-001's 4.04s regardless of input."""
    from project_x.reasoning.symbolic import Lemma
    lemma = Lemma(id=lemma_id, claim="FAKE", actual_value=4.04)
    lemma.add_step(
        operation="free_fall_inner",
        inputs={"h": h, "g": g},
        output="hardcoded",
        justification="fake substrate",
    )
    return lemma


def test_fake_overfit_free_fall_caught_by_probe():
    """Hardcoded canonical answer fails kinematic identity on surrogate inputs."""
    canonical = (80, 9.81)
    surrogates = [(125, 9.81), (80, 1.62), (45, 3.71)]
    probe = AntiCheatProbe(
        probe_id="overfit-free-fall-probe",
        canonical_inputs=canonical,
        surrogate_inputs=surrogates,
        answer_predicate=_free_fall_predicate,
    )
    result = differential_capability_test(_fake_overfit_free_fall, probe)

    assert result.canonical_match is True  # 4.04 IS approximately correct for canonical
    assert not any(result.surrogate_matches), (
        f"hardcoded answer must fail surrogate kinematic identities; got {result.surrogate_matches}"
    )
    assert result.memorization_signal == 1.0


# --- Lemma render() integration ---


def test_free_fall_time_render_includes_intro_and_invariant():
    """Render output mirrors maths primitives — intro + steps + invariant block."""
    lemma = free_fall_time(80, 9.81)
    rendered = lemma.render()
    assert "Notice." in rendered
    assert "kinematic identity" in rendered  # intro prose token
    assert "Step 1" in rendered or "Step 2" in rendered
    assert "Invariant checks:" in rendered
    assert "Affirmative" in rendered


def test_pendulum_period_render_includes_intro_and_invariant():
    lemma = pendulum_period(1.0, 9.81)
    rendered = lemma.render()
    assert "Lagrangian" in rendered  # intro prose token
    assert "Invariant checks:" in rendered
    assert "4π²" in rendered or "39.4" in rendered  # universal-constant in invariant


def test_relativistic_momentum_render_includes_intro_and_invariant():
    lemma = relativistic_momentum(9.11e-31, 0.9 * 3e8, 3e8)
    rendered = lemma.render()
    assert "Lorentz" in rendered  # intro prose token
    assert "Invariant checks:" in rendered


# --- Boundary cases ---


def test_free_fall_time_rejects_non_positive_inputs():
    with pytest.raises(ValueError, match="positive"):
        free_fall_time(-1, 9.81)
    with pytest.raises(ValueError, match="positive"):
        free_fall_time(80, 0)


def test_pendulum_period_rejects_non_positive_inputs():
    with pytest.raises(ValueError, match="positive"):
        pendulum_period(0, 9.81)


def test_relativistic_momentum_rejects_superluminal():
    c = 3.0e8
    with pytest.raises(ValueError, match="subluminal"):
        relativistic_momentum(9.11e-31, c, c)  # v == c
    with pytest.raises(ValueError, match="subluminal"):
        relativistic_momentum(9.11e-31, 1.5 * c, c)  # superluminal


def test_relativistic_momentum_rejects_non_positive_mass():
    with pytest.raises(ValueError, match="positive"):
        relativistic_momentum(0, 0.9 * 3e8, 3e8)


# --- Thesis-compliance source-grep ---


def test_physics_substrate_thesis_compliant():
    """No sympy / numpy / scipy / torch / transformers / pretrained-LLM imports."""
    physics_path = Path(__file__).resolve().parent.parent / "src" / "project_x" / "reasoning" / "physics.py"
    source = physics_path.read_text()
    forbidden = [
        "import sympy",
        "from sympy",
        "import numpy",
        "from numpy",
        "import scipy",
        "from scipy",
        "import torch",
        "from torch",
        "transformers",
        "BGE",
        "MiniLM",
        "sentence_transformers",
        "llama_cpp",
        "Qwen",
        "Mistral",
    ]
    for token in forbidden:
        assert token not in source, f"physics.py imports forbidden token '{token}'"
