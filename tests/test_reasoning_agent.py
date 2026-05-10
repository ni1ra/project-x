"""Tests for src/project_x/reasoning_agent.py — Phase 13 #00P13c7-NEW.

Coverage:
- Quadratic dispatch on the 3 standard-form-quadratic ladder entries (maths-001/007/008).
- Implicit-a-coefficient handling (`x^2` = 1·x², `-x^2` = -1·x²).
- Parser-miss returns honest refusal (no confabulation).
- AgentResponse schema sanity.

Cycle 7 minimum-viable scope; cycle 7+ extensions add tests per new problem-shape.
"""

from __future__ import annotations

import math

from project_x.reasoning_agent import (
    AgentResponse,
    ReasoningAgent,
    _parse_free_fall,
    _parse_matrix_2x2,
    _parse_quadratic,
    _parse_signed_coefficient,
)


# --- _parse_signed_coefficient ---


def test_parse_coefficient_explicit_positive():
    assert _parse_signed_coefficient("3") == 3.0
    assert _parse_signed_coefficient("+ 14") == 14.0


def test_parse_coefficient_explicit_negative():
    assert _parse_signed_coefficient("-14") == -14.0
    assert _parse_signed_coefficient("- 5") == -5.0


def test_parse_coefficient_implicit_one():
    assert _parse_signed_coefficient("", implicit_one=True) == 1.0
    assert _parse_signed_coefficient("+", implicit_one=True) == 1.0
    assert _parse_signed_coefficient("-", implicit_one=True) == -1.0


def test_parse_coefficient_implicit_zero():
    assert _parse_signed_coefficient("", implicit_one=False) == 0.0


def test_parse_coefficient_decimal():
    assert _parse_signed_coefficient("0.5") == 0.5
    assert _parse_signed_coefficient("- 2.5") == -2.5


# --- _parse_quadratic ---


def test_parse_quadratic_maths_001():
    # Ladder maths-001: "Solve for x: 3 x^2 - 14 x - 5 = 0. Report both roots."
    coeffs = _parse_quadratic("Solve for x: 3 x^2 - 14 x - 5 = 0. Report both roots.")
    assert coeffs == (3.0, -14.0, -5.0)


def test_parse_quadratic_maths_007():
    # Ladder maths-007: "Solve for x: x^2 - 5x + 6 = 0. Report both roots."
    # Implicit a=1 (no leading coefficient on x^2).
    coeffs = _parse_quadratic("Solve for x: x^2 - 5x + 6 = 0. Report both roots.")
    assert coeffs == (1.0, -5.0, 6.0)


def test_parse_quadratic_maths_008():
    # Ladder maths-008: "Solve for x: 4 x^2 + 4 x - 3 = 0. Report both roots."
    coeffs = _parse_quadratic("Solve for x: 4 x^2 + 4 x - 3 = 0. Report both roots.")
    assert coeffs == (4.0, 4.0, -3.0)


def test_parse_quadratic_no_match():
    coeffs = _parse_quadratic("Find the eigenvalues of [[2, 1], [1, 2]].")
    assert coeffs is None


def test_parse_quadratic_negative_implicit_a():
    # `-x^2 + 5x - 6 = 0` should parse as a=-1, b=5, c=-6.
    coeffs = _parse_quadratic("-x^2 + 5x - 6 = 0")
    assert coeffs == (-1.0, 5.0, -6.0)


# --- ReasoningAgent.process — full dispatch ---


def test_reasoning_agent_solves_maths_001():
    """Maths-001: 3x² - 14x - 5 = 0 → roots [-1/3, 5.0]."""
    agent = ReasoningAgent()
    response = agent.process("Solve for x: 3 x^2 - 14 x - 5 = 0. Report both roots.")

    assert isinstance(response, AgentResponse)
    assert response.domain == "maths"
    assert response.problem_shape == "quadratic"
    assert response.parsed_inputs == {"a": 3.0, "b": -14.0, "c": -5.0}
    assert response.confidence == "high"
    assert response.lemma is not None
    # solve_quadratic returns sorted roots; maths-001 expected [-1/3, 5.0]
    roots = response.lemma.actual_value
    assert abs(roots[0] - (-1 / 3)) < 1e-4
    assert abs(roots[1] - 5.0) < 1e-4
    # answer_text is the Lemma render — should contain step-by-step
    assert "Step" in response.answer_text
    assert "Affirmative" in response.answer_text


def test_reasoning_agent_solves_maths_007():
    """Maths-007: x² - 5x + 6 = 0 → roots [2.0, 3.0] (implicit a=1)."""
    agent = ReasoningAgent()
    response = agent.process("Solve for x: x^2 - 5x + 6 = 0. Report both roots.")

    assert response.confidence == "high"
    assert response.parsed_inputs == {"a": 1.0, "b": -5.0, "c": 6.0}
    roots = response.lemma.actual_value
    assert abs(roots[0] - 2.0) < 1e-4
    assert abs(roots[1] - 3.0) < 1e-4


def test_reasoning_agent_solves_maths_008():
    """Maths-008: 4x² + 4x - 3 = 0 → roots [-1.5, 0.5]."""
    agent = ReasoningAgent()
    response = agent.process("Solve for x: 4 x^2 + 4 x - 3 = 0. Report both roots.")

    assert response.confidence == "high"
    assert response.parsed_inputs == {"a": 4.0, "b": 4.0, "c": -3.0}
    roots = response.lemma.actual_value
    assert abs(roots[0] - (-1.5)) < 1e-4
    assert abs(roots[1] - 0.5) < 1e-4


def test_reasoning_agent_refuses_unrecognized_shape():
    """No match → honest refusal (no confabulation per M-PROJECTX-013)."""
    agent = ReasoningAgent()
    response = agent.process("Compute the integral of sin(x) from 0 to pi.")

    assert response.domain == "unrecognized"
    assert response.problem_shape == "unrecognized"
    assert response.lemma is None
    assert response.confidence == "refused"
    assert "M-PROJECTX-013" in response.answer_text or "not match" in response.answer_text.lower()


def test_reasoning_agent_refuses_integral_problem():
    """Cycle 7 dispatch covers quadratic + 2x2 eigenvalues; integrals refuse (cycle 7+)."""
    agent = ReasoningAgent()
    response = agent.process("Compute the integral of sin(x) from 0 to pi.")
    assert response.confidence == "refused"


# --- _parse_matrix_2x2 + 2x2 eigenvalue dispatch ---


def test_parse_matrix_2x2_maths_002():
    # Ladder maths-002: "Find the eigenvalues of the 2x2 matrix [[2, 1], [1, 2]]."
    matrix = _parse_matrix_2x2("Find the eigenvalues of the 2x2 matrix [[2, 1], [1, 2]].")
    assert matrix == [[2.0, 1.0], [1.0, 2.0]]


def test_parse_matrix_2x2_maths_009():
    # Ladder maths-009: "Find the eigenvalues of the 2x2 matrix [[3, 2], [4, 1]]."
    matrix = _parse_matrix_2x2("Find the eigenvalues of the 2x2 matrix [[3, 2], [4, 1]].")
    assert matrix == [[3.0, 2.0], [4.0, 1.0]]


def test_parse_matrix_2x2_needs_eigenvalue_keyword():
    # Matrix literal alone without naming eigenvalues → don't claim this prompt-shape.
    # Honest gating: routing a bare matrix prompt to the eigenvalue substrate would
    # be confabulation per M-PROJECTX-013.
    matrix = _parse_matrix_2x2("Here is a matrix: [[2, 1], [1, 2]]. Comment on its symmetry.")
    assert matrix is None


def test_parse_matrix_2x2_no_match():
    matrix = _parse_matrix_2x2("Find the eigenvalues but no matrix is given.")
    assert matrix is None


def test_reasoning_agent_solves_maths_002():
    """Maths-002: eigenvalues of [[2,1],[1,2]] → 1.0 and 3.0."""
    agent = ReasoningAgent()
    response = agent.process("Find the eigenvalues of the 2x2 matrix [[2, 1], [1, 2]].")

    assert response.confidence == "high"
    assert response.domain == "maths"
    assert response.problem_shape == "char_poly_2x2"
    assert response.parsed_inputs == {"matrix": [[2.0, 1.0], [1.0, 2.0]]}
    assert response.lemma is not None
    eigs = response.lemma.actual_value
    # eigenvalues sorted ascending: 1.0 and 3.0 (trace=4, det=3 → λ²-4λ+3 → (λ-1)(λ-3))
    assert abs(eigs[0] - 1.0) < 1e-4
    assert abs(eigs[1] - 3.0) < 1e-4


def test_reasoning_agent_solves_maths_009():
    """Maths-009: eigenvalues of [[3,2],[4,1]] → -1.0 and 5.0."""
    agent = ReasoningAgent()
    response = agent.process("Find the eigenvalues of the 2x2 matrix [[3, 2], [4, 1]].")

    assert response.confidence == "high"
    assert response.parsed_inputs == {"matrix": [[3.0, 2.0], [4.0, 1.0]]}
    eigs = response.lemma.actual_value
    # trace=4, det=-5 → λ²-4λ-5 → (λ-5)(λ+1) → eigenvalues -1, 5
    assert abs(eigs[0] - (-1.0)) < 1e-4
    assert abs(eigs[1] - 5.0) < 1e-4


# --- _parse_free_fall + physics free-fall dispatch ---


def test_parse_free_fall_physics_001():
    # Physics-001: "A ball is dropped from rest from a height of 80 m. ... Use g = 9.81 m/s^2."
    params = _parse_free_fall(
        "A ball is dropped from rest from a height of 80 m. Ignoring air resistance, "
        "how long until it hits the ground? Use g = 9.81 m/s^2."
    )
    assert params == (80.0, 9.81)


def test_parse_free_fall_physics_008():
    # Physics-008: "On Mars (g = 3.71 m/s²), how long does a ball take to fall from 50 m?"
    params = _parse_free_fall(
        "On Mars (g = 3.71 m/s²), how long does a ball take to fall from 50 m? Ignore atmospheric drag."
    )
    assert params == (50.0, 3.71)


def test_parse_free_fall_needs_drop_keyword():
    # Bare h + g without naming drop/fall → don't route here.
    params = _parse_free_fall("A platform of height 80 m has g = 9.81 m/s² ambient.")
    assert params is None


def test_parse_free_fall_no_match_missing_height():
    params = _parse_free_fall("A ball is dropped with g = 9.81 m/s^2 ambient gravity.")
    assert params is None


def test_reasoning_agent_solves_physics_001():
    """Physics-001: h=80, g=9.81 → t ≈ √(160/9.81) ≈ 4.0386 s (ladder expected 4.04)."""
    agent = ReasoningAgent()
    response = agent.process(
        "A ball is dropped from rest from a height of 80 m. Ignoring air resistance, "
        "how long until it hits the ground? Use g = 9.81 m/s^2."
    )

    assert response.confidence == "high"
    assert response.domain == "physics"
    assert response.problem_shape == "free_fall"
    assert response.parsed_inputs == {"h_meters": 80.0, "g_m_per_s_squared": 9.81}
    t = response.lemma.actual_value
    expected = math.sqrt(2 * 80 / 9.81)
    assert abs(t - expected) < 1e-6
    assert abs(t - 4.04) < 0.05  # ladder tolerance


def test_reasoning_agent_solves_physics_008():
    """Physics-008: h=50, g=3.71 (Mars) → t ≈ √(100/3.71) ≈ 5.193 s."""
    agent = ReasoningAgent()
    response = agent.process(
        "On Mars (g = 3.71 m/s²), how long does a ball take to fall from 50 m? Ignore atmospheric drag."
    )

    assert response.confidence == "high"
    assert response.parsed_inputs == {"h_meters": 50.0, "g_m_per_s_squared": 3.71}
    t = response.lemma.actual_value
    expected = math.sqrt(2 * 50 / 3.71)
    assert abs(t - expected) < 1e-6


# --- Pendulum dispatch (small-angle + large-angle) ---


def test_reasoning_agent_solves_physics_002_small_angle_pendulum():
    """Physics-002: L=1.0, g=9.81 → T ≈ 2π√(1/9.81) ≈ 2.007s."""
    agent = ReasoningAgent()
    response = agent.process(
        "A simple pendulum has length L = 1.0 m. In the small-angle approximation, "
        "what is the period T of oscillation? Use g = 9.81 m/s^2."
    )

    assert response.confidence == "high"
    assert response.problem_shape == "pendulum_small_angle"
    assert response.parsed_inputs == {"L_meters": 1.0, "g_m_per_s_squared": 9.81}
    T = response.lemma.actual_value
    expected = 2 * math.pi * math.sqrt(1.0 / 9.81)
    assert abs(T - expected) < 1e-6


def test_reasoning_agent_solves_physics_009_pendulum_moon():
    """Physics-009: L=0.5, g=1.62 (Moon) → T ≈ 2π√(0.5/1.62)."""
    agent = ReasoningAgent()
    response = agent.process(
        "A simple pendulum on the Moon (g = 1.62 m/s²) has length L = 0.5 m. "
        "In the small-angle approximation, what is its period?"
    )

    assert response.confidence == "high"
    assert response.parsed_inputs == {"L_meters": 0.5, "g_m_per_s_squared": 1.62}
    T = response.lemma.actual_value
    expected = 2 * math.pi * math.sqrt(0.5 / 1.62)
    assert abs(T - expected) < 1e-6


def test_reasoning_agent_solves_physics_010_large_angle_pendulum():
    """Physics-010: L=1.0, g=9.81, θ₀=π/3 (60°) → elliptic-integral series correction."""
    agent = ReasoningAgent()
    response = agent.process(
        "A pendulum of length L = 1.0 m on Earth (g = 9.81 m/s²) is released from "
        "a 60° angle (θ₀ = π/3 rad). Compute its period using the elliptic-integral "
        "correction (NOT the small-angle approximation). Report in seconds."
    )

    assert response.confidence == "high"
    assert response.problem_shape == "pendulum_large_angle"
    assert response.parsed_inputs["L_meters"] == 1.0
    assert response.parsed_inputs["g_m_per_s_squared"] == 9.81
    assert abs(response.parsed_inputs["theta_0_rad"] - math.pi / 3) < 1e-6
    T = response.lemma.actual_value
    # Reference: T/T₀ ≈ 1.073 at 60°; T₀ ≈ 2.007 → T ≈ 2.154
    T0 = 2 * math.pi * math.sqrt(1.0 / 9.81)
    assert T > T0  # large-angle correction makes T longer than small-angle
    assert abs(T - T0 * 1.073) < 0.02  # truncation tolerance


def test_reasoning_agent_pendulum_no_pendulum_keyword():
    """Non-pendulum prompt with L + g values → don't route."""
    agent = ReasoningAgent()
    response = agent.process("A spring with L = 2.0 m has g = 9.81 m/s^2. Find oscillation.")
    # No "pendulum" keyword → refuses
    assert response.confidence == "refused"
