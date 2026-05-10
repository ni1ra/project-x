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
    large_angle_pendulum_period,
    pendulum_period,
    projectile_horizontal_range,
    relativistic_doppler_shift,
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


# --- Cycle 5 #00P13c5-05 — large-angle pendulum (substrate Tier 3) ---


def test_large_angle_pendulum_collapses_to_small_angle_at_tiny_theta():
    """θ₀ = 1e-3 rad: correction → 1; period ≈ T₀ within 1e-6 relative."""
    lemma = large_angle_pendulum_period(1.0, 9.81, 1e-3)
    T0 = 2 * math.pi * math.sqrt(1.0 / 9.81)
    assert abs(lemma.actual_value - T0) / T0 < 1e-6


def test_large_angle_pendulum_at_45_degrees():
    """θ₀ = π/4 (45°): correction ≈ 1.040 (textbook reference; series 4-term truncation)."""
    lemma = large_angle_pendulum_period(1.0, 9.81, math.pi / 4)
    T0 = 2 * math.pi * math.sqrt(1.0 / 9.81)
    correction = lemma.actual_value / T0
    # Reference: K(sin(π/8)) ≈ 1.6336; T/T₀ = K · 2/π ≈ 1.0399. Truncation tightly accurate.
    assert abs(correction - 1.0399) < 5e-3


def test_large_angle_pendulum_at_90_degrees():
    """θ₀ = π/2 (90°): correction ≈ 1.180 (textbook). 4-term truncation lands ~1.177."""
    lemma = large_angle_pendulum_period(1.0, 9.81, math.pi / 2)
    T0 = 2 * math.pi * math.sqrt(1.0 / 9.81)
    correction = lemma.actual_value / T0
    # Reference: K(sin(π/4)) ≈ 1.8541; T/T₀ ≈ 1.1803. 4-term truncation: ~1.177.
    # Tolerance accommodates truncation error (~3e-3 at this amplitude).
    assert abs(correction - 1.1803) < 5e-3


def test_large_angle_pendulum_period_strictly_grows_with_amplitude():
    """Monotonicity: period at θ₀ = 0.5 rad < period at θ₀ = 1.0 rad < period at θ₀ = 1.5 rad."""
    p_small = large_angle_pendulum_period(1.0, 9.81, 0.5)
    p_med = large_angle_pendulum_period(1.0, 9.81, 1.0)
    p_large = large_angle_pendulum_period(1.0, 9.81, 1.5)
    assert p_small.actual_value < p_med.actual_value < p_large.actual_value


def test_large_angle_pendulum_render_includes_intro_and_invariant():
    lemma = large_angle_pendulum_period(1.0, 9.81, math.pi / 4)
    rendered = lemma.render()
    assert "elliptic" in rendered.lower()
    assert "Invariant checks:" in rendered


def test_large_angle_pendulum_rejects_inversion_regime():
    """|θ₀| ≥ π is non-oscillatory (full inversion); out of substrate scope."""
    with pytest.raises(ValueError, match="oscillatory"):
        large_angle_pendulum_period(1.0, 9.81, math.pi)
    with pytest.raises(ValueError, match="oscillatory"):
        large_angle_pendulum_period(1.0, 9.81, 1.5 * math.pi)


def test_large_angle_pendulum_rejects_non_positive_inputs():
    with pytest.raises(ValueError, match="positive"):
        large_angle_pendulum_period(0, 9.81, 0.5)
    with pytest.raises(ValueError, match="positive"):
        large_angle_pendulum_period(1.0, -9.81, 0.5)


def _large_angle_pendulum_predicate(inputs, output):
    """Output is float T; verify via incremental ratio-recursion (algorithmically distinct
    from substrate's explicit-coefficient series sum).

    Recursion: a_{n+1}/a_n = ((2n+1)/(2n+2))²·k². Independent of substrate's hardcoded
    coefficients (1/4, 9/64, 25/256, 1225/16384). Two divergent computations must agree.
    """
    L, g, theta_0 = inputs
    if not isinstance(output, (int, float)) or output <= 0:
        return False
    if abs(theta_0) >= math.pi or L <= 0 or g <= 0:
        return False
    T0 = 2 * math.pi * math.sqrt(L / g)
    k = math.sin(theta_0 / 2)
    k2 = k * k
    correction = 0.0
    term = 1.0
    correction += term  # n=0
    for n in range(4):  # n=0→1, 1→2, 2→3, 3→4
        ratio = ((2 * n + 1) / (2 * n + 2)) ** 2
        term *= ratio * k2
        correction += term
    expected_T = T0 * correction
    return abs(output - expected_T) / max(abs(expected_T), 1e-30) < 1e-6


def test_large_angle_pendulum_passes_anti_cheat_probe():
    """N=5 surrogates across L + g + θ₀ regimes; substrate must compute via series."""
    canonical = (1.0, 9.81, math.pi / 4)
    surrogates = [
        (2.0, 9.81, math.pi / 4),     # twice the length, same amplitude
        (1.0, 1.62, math.pi / 4),     # Moon gravity, same amplitude
        (1.0, 9.81, 0.1),             # near-small-angle limit
        (1.0, 9.81, math.pi / 3),     # 60° amplitude
        (3.5, 3.71, math.pi / 6),     # Mars + longer + smaller amplitude
    ]
    probe = AntiCheatProbe(
        probe_id="large_angle_pendulum_probe",
        canonical_inputs=canonical,
        surrogate_inputs=surrogates,
        answer_predicate=_large_angle_pendulum_predicate,
        notes="Substrate must compute series via explicit coefficients; predicate verifies via ratio-recursion.",
    )
    result = differential_capability_test(large_angle_pendulum_period, probe)

    assert result.canonical_match is True
    assert all(result.surrogate_matches)
    assert result.memorization_signal == 0.0


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


# ── Projectile horizontal range (cycle 8 #00P13c8-05) ──────────────────────────


def _projectile_horizontal_range_predicate(inputs, output):
    """Output is float R; universal algebraic identity R²·g/(2h) = v_horizontal².

    Predicate verifies INPUT-OUTPUT APPROPRIATENESS: a fake substrate hardcoding
    physics-007's 60.58 answer would pass the canonical check but fail surrogates
    (the reconstructed v_x² would be wildly off when h or g differ).
    """
    h, v, g = inputs
    if not isinstance(output, (int, float)) or output <= 0:
        return False
    lhs = (output * output * g) / (2 * h)
    rhs = v * v
    return abs(lhs - rhs) / rhs < 1e-6


class TestProjectileHorizontalRange:
    def test_physics_007_canonical(self):
        """Physics-007: 45m cliff, 20 m/s horizontal, g=9.81 → ~60.58 m (auto_grade tolerance 0.5)."""
        lemma = projectile_horizontal_range(h=45.0, v_horizontal=20.0, g=9.81)
        assert abs(lemma.actual_value - 60.58) < 0.5
        # Verify against the closed-form directly: R = v · √(2h/g)
        expected = 20.0 * math.sqrt(2 * 45.0 / 9.81)
        assert abs(lemma.actual_value - expected) < 1e-9

    def test_lemma_chain_shape(self):
        """2-step chain (vertical_fall_time → horizontal_range) + 1 invariant + intro."""
        lemma = projectile_horizontal_range(h=45.0, v_horizontal=20.0, g=9.81)
        assert len(lemma.derivation_steps) == 2
        assert lemma.derivation_steps[0].operation == "vertical_fall_time"
        assert lemma.derivation_steps[1].operation == "horizontal_range"
        assert len(lemma.invariant_checks) == 1
        assert lemma.introduction != ""
        assert "projectile" in lemma.introduction.lower()

    def test_universal_invariant_holds(self):
        """Universal invariant R²·g/(2h) = v_horizontal² across diverse inputs."""
        cases = [
            (45.0, 20.0, 9.81),  # physics-007 canonical (Earth cliff)
            (10.0, 5.0, 9.81),    # smaller cliff
            (100.0, 50.0, 1.62),  # Moon gravity (g=1.62)
            (200.0, 30.0, 3.71),  # Mars gravity (g=3.71)
        ]
        for h, v, g in cases:
            lemma = projectile_horizontal_range(h, v, g)
            for inv in lemma.invariant_checks:
                assert inv.holds, f"invariant failed for (h={h}, v={v}, g={g})"

    def test_anti_cheat_no_memorization(self):
        """Surrogate input families (varying h, v, g across solar-system gravities) all pass
        via real closed-form computation; memorization_signal must be 0.0 (no canonical-answer
        hardcoding). Predicate: universal algebraic identity R²·g/(2h) = v_horizontal²."""
        canonical = (45.0, 20.0, 9.81)  # physics-007 (Earth)
        surrogates = [
            (10.0, 5.0, 9.81),    # smaller cliff
            (100.0, 50.0, 9.81),  # taller cliff + faster
            (45.0, 20.0, 1.62),   # Moon gravity (Apollo cliff)
            (45.0, 20.0, 3.71),   # Mars gravity
            (200.0, 30.0, 24.79), # Jupiter gravity
        ]
        probe = AntiCheatProbe(
            probe_id="projectile_horizontal_range_probe",
            canonical_inputs=canonical,
            surrogate_inputs=surrogates,
            answer_predicate=_projectile_horizontal_range_predicate,
            surrogate_author="builder (rule-based; varying solar-system gravities)",
            notes="Substrate must compute v_x·√(2h/g) per-input; no canonical-answer hardcoding.",
        )
        result = differential_capability_test(projectile_horizontal_range, probe)
        assert result.canonical_match is True
        assert all(result.surrogate_matches)
        assert result.memorization_signal == 0.0

    def test_rejects_non_positive_inputs(self):
        """h, v, g must all be > 0."""
        with pytest.raises(ValueError, match="positive"):
            projectile_horizontal_range(h=0, v_horizontal=20.0, g=9.81)
        with pytest.raises(ValueError, match="positive"):
            projectile_horizontal_range(h=45.0, v_horizontal=0, g=9.81)
        with pytest.raises(ValueError, match="positive"):
            projectile_horizontal_range(h=45.0, v_horizontal=20.0, g=0)


# ── Relativistic Doppler shift (cycle 8 #00P13c8-05) ───────────────────────────


class TestRelativisticDopplerShift:
    def test_physics_012_canonical_approach(self):
        """Physics-012: λ₀=500nm, β=0.6 approaching → 250 nm (blueshift factor 0.5)."""
        lemma = relativistic_doppler_shift(wavelength_emit=500.0, beta=0.6, approaching=True)
        assert abs(lemma.actual_value - 250.0) < 1.0
        # Exact: factor = √(0.4/1.6) = √0.25 = 0.5 → λ_obs = 250.0
        assert abs(lemma.actual_value - 250.0) < 1e-9

    def test_receding_redshift(self):
        """β=0.6 receding → factor = √(1.6/0.4) = 2; λ_obs = 1000 nm."""
        lemma = relativistic_doppler_shift(wavelength_emit=500.0, beta=0.6, approaching=False)
        assert abs(lemma.actual_value - 1000.0) < 1.0

    def test_classical_limit_low_beta_approach(self):
        """At β=0.01 approaching: factor ≈ 1 - β = 0.99; λ_obs ≈ 495 nm."""
        lemma = relativistic_doppler_shift(wavelength_emit=500.0, beta=0.01, approaching=True)
        # Exact: factor = √(0.99/1.01) ≈ 0.99005; λ_obs ≈ 495.025
        assert abs(lemma.actual_value - 495.0) < 0.1

    def test_zero_beta_no_shift(self):
        """β=0: factor = 1; λ_obs = λ_emit (no relative motion = no shift)."""
        lemma = relativistic_doppler_shift(wavelength_emit=500.0, beta=0.0, approaching=True)
        assert abs(lemma.actual_value - 500.0) < 1e-12

    def test_invariant_factor_squared(self):
        """Invariant: factor² = (1∓β)/(1±β) across diverse (β, approaching) pairs."""
        cases = [(0.6, True), (0.6, False), (0.1, True), (0.1, False), (0.9, True), (0.9, False)]
        for beta, approaching in cases:
            lemma = relativistic_doppler_shift(wavelength_emit=500.0, beta=beta, approaching=approaching)
            assert all(inv.holds for inv in lemma.invariant_checks), (
                f"invariant failed for β={beta}, approaching={approaching}"
            )

    def test_lemma_chain_shape(self):
        """2-step chain (doppler_factor → apply_factor) + 1 invariant + intro."""
        lemma = relativistic_doppler_shift(wavelength_emit=500.0, beta=0.6, approaching=True)
        assert len(lemma.derivation_steps) == 2
        assert lemma.derivation_steps[0].operation == "doppler_factor"
        assert lemma.derivation_steps[1].operation == "apply_factor"
        assert len(lemma.invariant_checks) == 1
        assert lemma.introduction != ""
        assert "doppler" in lemma.introduction.lower()

    def test_render_includes_direction(self):
        """Render mentions blueshift for approaching / redshift for receding."""
        approach_lemma = relativistic_doppler_shift(wavelength_emit=500.0, beta=0.6, approaching=True)
        recede_lemma = relativistic_doppler_shift(wavelength_emit=500.0, beta=0.6, approaching=False)
        assert "blueshift" in approach_lemma.render().lower()
        assert "redshift" in recede_lemma.render().lower()

    def test_rejects_non_positive_wavelength(self):
        with pytest.raises(ValueError, match="positive"):
            relativistic_doppler_shift(wavelength_emit=0, beta=0.5)
        with pytest.raises(ValueError, match="positive"):
            relativistic_doppler_shift(wavelength_emit=-100, beta=0.5)

    def test_rejects_superluminal(self):
        """|β| ≥ 1 raises ValueError (causal-structure)."""
        with pytest.raises(ValueError, match="subluminal"):
            relativistic_doppler_shift(wavelength_emit=500.0, beta=1.0)
        with pytest.raises(ValueError, match="subluminal"):
            relativistic_doppler_shift(wavelength_emit=500.0, beta=-1.5)
