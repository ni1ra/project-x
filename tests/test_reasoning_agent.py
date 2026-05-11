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


# --- Relativistic momentum dispatch ---


def test_reasoning_agent_solves_physics_003():
    """Physics-003: electron at 0.9c → p ≈ γ·m·v ≈ 5.64e-22 kg·m/s."""
    agent = ReasoningAgent()
    response = agent.process(
        "An electron (rest mass m_e = 9.11e-31 kg) moves at v = 0.9c. "
        "Calculate its relativistic momentum. Use c = 3.0e8 m/s. "
        "Report in kg m/s with at least 3 significant figures."
    )

    assert response.confidence == "high"
    assert response.domain == "physics"
    assert response.problem_shape == "relativistic_momentum"
    assert abs(response.parsed_inputs["m_kg"] - 9.11e-31) < 1e-40
    assert abs(response.parsed_inputs["v_m_per_s"] - 0.9 * 3.0e8) < 1e-2
    assert response.parsed_inputs["c_m_per_s"] == 3.0e8
    p = response.lemma.actual_value
    # γ at 0.9c ≈ 2.294; p ≈ 2.294 · 9.11e-31 · 2.7e8 ≈ 5.64e-22
    assert abs(p - 5.64e-22) / 5.64e-22 < 0.01


def test_reasoning_agent_solves_physics_011():
    """Physics-011: proton at 0.5c → p ≈ γ·m·v."""
    agent = ReasoningAgent()
    response = agent.process(
        "A proton (rest mass m_p = 1.67e-27 kg) moves at v = 0.5c. "
        "Calculate its relativistic momentum. Use c = 3.0e8 m/s. Report in kg·m/s."
    )

    assert response.confidence == "high"
    assert response.problem_shape == "relativistic_momentum"
    assert abs(response.parsed_inputs["m_kg"] - 1.67e-27) < 1e-35
    assert abs(response.parsed_inputs["v_m_per_s"] - 0.5 * 3.0e8) < 1e-2
    p = response.lemma.actual_value
    # γ at 0.5c = 1/√0.75 ≈ 1.1547; p ≈ 1.1547 · 1.67e-27 · 1.5e8 ≈ 2.892e-19
    gamma = 1.0 / math.sqrt(1 - 0.25)
    expected = gamma * 1.67e-27 * 0.5 * 3.0e8
    assert abs(p - expected) / expected < 0.001


def test_reasoning_agent_relativistic_momentum_no_keyword():
    """Prompt with m + v + c but no "relativistic momentum" naming → don't route."""
    agent = ReasoningAgent()
    response = agent.process(
        "An electron of m = 9.11e-31 kg moves at v = 0.9c with c = 3.0e8 m/s. Comment."
    )
    assert response.confidence == "refused"


# --- Residue theorem real-line integral dispatch (maths-003) ---


def test_reasoning_agent_solves_maths_003():
    """Maths-003: ∫_{-∞}^{+∞} dx/(x²+1) via residue theorem → π."""
    agent = ReasoningAgent()
    response = agent.process(
        "Use the residue theorem to evaluate the integral from -infinity to "
        "+infinity of 1/(x^2 + 1) dx."
    )

    assert response.confidence == "high"
    assert response.domain == "maths"
    assert response.problem_shape == "residue_theorem_unit_quadratic"
    assert response.parsed_inputs == {"a": 1.0, "c": 1.0}
    assert abs(response.lemma.actual_value - math.pi) < 1e-9


def test_reasoning_agent_residue_theorem_scaled_denominator():
    """∫_{-∞}^{+∞} dx/(x²+4) via residue theorem → π/2."""
    agent = ReasoningAgent()
    response = agent.process(
        "Use the residue theorem to evaluate the integral from -infinity to "
        "+infinity of 1/(x^2 + 4) dx."
    )
    assert response.confidence == "high"
    assert response.parsed_inputs == {"a": 1.0, "c": 4.0}
    assert abs(response.lemma.actual_value - math.pi / 2) < 1e-9


def test_reasoning_agent_residue_theorem_no_keyword():
    """Prompt has integrand but no "residue theorem" / "contour integral" → don't route."""
    agent = ReasoningAgent()
    response = agent.process("Evaluate the integral from -infinity to +infinity of 1/(x^2 + 1) dx.")
    assert response.confidence == "refused"


# --- Definite integral (quadratic) dispatch (maths-010) ---


def test_reasoning_agent_solves_maths_010():
    """Maths-010: ∫₀² (3x² + 2x - 1) dx = 10."""
    agent = ReasoningAgent()
    response = agent.process(
        "Compute the value of the definite integral from 0 to 2 of (3x^2 + 2x - 1) dx."
    )
    assert response.confidence == "high"
    assert response.domain == "maths"
    assert response.problem_shape == "definite_integral_quadratic"
    assert response.parsed_inputs == {
        "coeffs_descending": [3.0, 2.0, -1.0], "lower": 0.0, "upper": 2.0,
    }
    assert abs(response.lemma.actual_value - 10.0) < 1e-9


def test_reasoning_agent_definite_integral_negative_bound():
    """∫_{-1}^{1} (x² + 0x + 0) dx via the same dispatcher = 2/3."""
    agent = ReasoningAgent()
    response = agent.process(
        "Compute the value of the definite integral from -1 to 1 of (1x^2 + 0x + 0) dx."
    )
    assert response.confidence == "high"
    assert abs(response.lemma.actual_value - 2 / 3) < 1e-9


# --- First-order linear ODE dispatch (maths-011) ---


def test_reasoning_agent_solves_maths_011():
    """Maths-011 verbatim: dy/dx = 2y with y(0) = 3; report y(1) ≈ 22.167."""
    agent = ReasoningAgent()
    response = agent.process(
        "Solve the differential equation dy/dx = 2y with initial condition y(0) = 3. Report y(1)."
    )
    assert response.confidence == "high"
    assert response.domain == "maths"
    assert response.problem_shape == "first_order_linear_ode_exp"
    assert response.parsed_inputs == {"k": 2.0, "y_0": 3.0, "x_target": 1.0, "x_0": 0.0}
    expected = 3.0 * math.exp(2.0)
    assert abs(response.lemma.actual_value - expected) < 1e-12
    assert abs(response.lemma.actual_value - 22.167) < 0.05  # maths-011 auto_grade tolerance


def test_reasoning_agent_ode_negative_k_decay():
    """Negative k → exponential decay: dy/dx = -1y with y(0) = 1; y(1) = 1/e ≈ 0.3679."""
    agent = ReasoningAgent()
    response = agent.process(
        "Solve the differential equation dy/dx = -1y with initial condition y(0) = 1. Report y(1)."
    )
    assert response.confidence == "high"
    assert response.parsed_inputs == {"k": -1.0, "y_0": 1.0, "x_target": 1.0, "x_0": 0.0}
    assert abs(response.lemma.actual_value - (1.0 / math.e)) < 1e-12


def test_reasoning_agent_ode_decimal_k():
    """Decimal k coefficient: dy/dx = 0.5y with y(0) = 4; y(2) = 4·e ≈ 10.873."""
    agent = ReasoningAgent()
    response = agent.process(
        "Solve the differential equation dy/dx = 0.5y with initial condition y(0) = 4. Report y(2)."
    )
    assert response.confidence == "high"
    assert response.parsed_inputs["k"] == 0.5
    assert abs(response.lemma.actual_value - 4.0 * math.e) < 1e-12


def test_reasoning_agent_ode_non_zero_ic_anchor():
    """Non-zero x_0 IC anchor: dy/dx = 1y with y(1) = 2.718281828; y(2) = e² ≈ 7.389."""
    agent = ReasoningAgent()
    response = agent.process(
        "Solve the differential equation dy/dx = 1y with initial condition y(1) = 2.718281828. Report y(2)."
    )
    assert response.confidence == "high"
    assert response.parsed_inputs["x_0"] == 1.0
    assert response.parsed_inputs["x_target"] == 2.0
    assert abs(response.lemma.actual_value - math.exp(2.0)) < 1e-7


def test_reasoning_agent_ode_no_dy_dx_keyword_refuses():
    """Prompt lacks 'dy/dx' / 'differential equation' → don't false-match ODE shape.
    Verifies the keyword gate prevents non-ODE prompts from accidental ODE routing."""
    agent = ReasoningAgent()
    response = agent.process("Solve 3x^2 - 14x - 5 = 0 for x.")
    assert response.problem_shape != "first_order_linear_ode_exp"


def test_reasoning_agent_ode_quadratic_doesnt_false_match():
    """A quadratic prompt has `x^2` not `dy/dx`; ODE parser must NOT consume it.
    Verifies the advisor-flagged absence-of-overlap between the two shapes (advisor 2026-05-11)."""
    agent = ReasoningAgent()
    response = agent.process("Solve x^2 - 5x + 6 = 0 for x.")
    assert response.problem_shape != "first_order_linear_ode_exp"


# --- 3x3 determinant dispatch (maths-012) ---


def test_reasoning_agent_solves_maths_012():
    """Maths-012 verbatim: determinant of [[1,2,3],[4,5,6],[7,8,10]] = -3."""
    agent = ReasoningAgent()
    response = agent.process(
        "Find the determinant of the 3x3 matrix [[1, 2, 3], [4, 5, 6], [7, 8, 10]]."
    )
    assert response.confidence == "high"
    assert response.domain == "maths"
    assert response.problem_shape == "determinant_3x3"
    assert response.parsed_inputs == {
        "matrix": [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 10.0]]
    }
    assert response.lemma.actual_value == -3.0


def test_reasoning_agent_determinant_3x3_identity():
    """Identity matrix det = 1 (via the dispatcher; no rephrasing of prompt)."""
    agent = ReasoningAgent()
    response = agent.process(
        "Find the determinant of the matrix [[1, 0, 0], [0, 1, 0], [0, 0, 1]]."
    )
    assert response.confidence == "high"
    assert response.problem_shape == "determinant_3x3"
    assert response.lemma.actual_value == 1.0


def test_reasoning_agent_determinant_3x3_negative_entries():
    """Negative entries propagate correctly through the dispatch + substrate."""
    agent = ReasoningAgent()
    response = agent.process(
        "Find the determinant of [[2, -1, 3], [0, 5, 1], [-1, 2, 4]]."
    )
    assert response.confidence == "high"
    assert response.lemma.actual_value == 52.0


def test_reasoning_agent_determinant_3x3_no_keyword_refuses():
    """Prompt with 3x3 matrix but no 'determinant' keyword → don't false-match."""
    agent = ReasoningAgent()
    response = agent.process("Compute [[1, 2, 3], [4, 5, 6], [7, 8, 10]] somehow.")
    assert response.problem_shape != "determinant_3x3"


def test_reasoning_agent_determinant_2x2_doesnt_false_match():
    """A 2x2 matrix in an eigenvalue prompt must NOT route to 3x3 determinant.
    Verifies the 2x2-vs-3x3 absence-of-overlap (different inner-bracket arities + different keyword gates)."""
    agent = ReasoningAgent()
    response = agent.process("Find the eigenvalues of the matrix [[2, 1], [1, 2]].")
    assert response.problem_shape != "determinant_3x3"
    # Should route to char_poly_2x2 (the eigenvalue dispatcher).
    assert response.problem_shape == "char_poly_2x2"


# --- Projectile horizontal range dispatch (physics-007) ---


def test_reasoning_agent_solves_physics_007():
    """Physics-007 verbatim: 45 m cliff, 20 m/s horizontal, g=9.81 → ~60.58 m."""
    agent = ReasoningAgent()
    response = agent.process(
        "A projectile is launched horizontally from a 45 m cliff at 20 m/s. "
        "Ignoring air resistance and using g = 9.81 m/s², how far horizontally does "
        "it travel before hitting the ground? Report in meters."
    )
    assert response.confidence == "high"
    assert response.domain == "physics"
    assert response.problem_shape == "projectile_horizontal_range"
    assert response.parsed_inputs["h_meters"] == 45.0
    assert response.parsed_inputs["v_horizontal_m_per_s"] == 20.0
    assert response.parsed_inputs["g_m_per_s_squared"] == 9.81
    assert abs(response.lemma.actual_value - 60.58) < 0.5  # ladder tolerance


def test_reasoning_agent_projectile_no_keyword_refuses():
    """Free-fall prompt (no 'projectile' / 'horizontal' keywords) must NOT route to projectile."""
    agent = ReasoningAgent()
    response = agent.process(
        "An object falls from a height of 45 m with g = 9.81 m/s². Compute the fall time."
    )
    assert response.problem_shape != "projectile_horizontal_range"


# --- Relativistic Doppler shift dispatch (physics-012) ---


def test_reasoning_agent_solves_physics_012():
    """Physics-012 verbatim: spaceship approaches at v=0.6c emitting λ₀=500nm → λ_obs=250nm."""
    agent = ReasoningAgent()
    response = agent.process(
        "Explain the relativistic Doppler shift. A spaceship approaches Earth at v = 0.6c, "
        "emitting light of rest-frame wavelength λ₀ = 500 nm. What wavelength does Earth observe? "
        "What is the qualitative direction (redshift or blueshift), and why?"
    )
    assert response.confidence == "high"
    assert response.domain == "physics"
    assert response.problem_shape == "relativistic_doppler_shift"
    assert response.parsed_inputs["wavelength_emit_nm"] == 500.0
    assert response.parsed_inputs["beta"] == 0.6
    assert response.parsed_inputs["approaching"] is True
    assert abs(response.lemma.actual_value - 250.0) < 1.0  # ladder tolerance


def test_reasoning_agent_doppler_receding_redshift():
    """Receding source → redshift; factor = √((1+β)/(1-β))."""
    agent = ReasoningAgent()
    response = agent.process(
        "Doppler shift: a galaxy recedes from us at v = 0.5c, emitting at wavelength = 600 nm. "
        "What wavelength do we observe?"
    )
    assert response.confidence == "high"
    assert response.problem_shape == "relativistic_doppler_shift"
    assert response.parsed_inputs["approaching"] is False
    # β=0.5 receding: factor = √(1.5/0.5) = √3 ≈ 1.732; λ_obs ≈ 1039.23
    expected = 600.0 * math.sqrt(1.5 / 0.5)
    assert abs(response.lemma.actual_value - expected) < 1.0


def test_reasoning_agent_doppler_no_keyword_refuses():
    """Missing 'doppler' keyword → don't route to Doppler dispatcher (would otherwise misroute
    to relativistic_momentum since both have v=Xc patterns)."""
    agent = ReasoningAgent()
    response = agent.process(
        "A spaceship approaches Earth at v = 0.6c emitting wavelength λ = 500 nm. Comment."
    )
    assert response.problem_shape != "relativistic_doppler_shift"


def test_reasoning_agent_doppler_no_direction_refuses():
    """'Doppler' keyword present but no direction (approach/recede) → refuse, not default."""
    agent = ReasoningAgent()
    response = agent.process(
        "Relativistic Doppler shift: source at v = 0.5c, λ = 600 nm. What is observed?"
    )
    # No 'approach' / 'recede' keywords → parser refuses
    assert response.problem_shape != "relativistic_doppler_shift"


# --- Number-theory dispatchers (maths-017..020) ---


def test_reasoning_agent_solves_maths_017_collatz():
    """Maths-017: Collatz verify [1, 1000] → 1000 verified."""
    agent = ReasoningAgent()
    response = agent.process(
        "Verify the Collatz conjecture empirically: for every integer n in [1, 1000], "
        "iterate n → n/2 (if even) or n → 3n+1 (if odd). Report the count of starting "
        "values that reach 1."
    )
    assert response.confidence == "high"
    assert response.domain == "maths"
    assert response.problem_shape == "collatz_verify_range"
    assert response.parsed_inputs == {"N": 1000}
    assert response.lemma.actual_value == 1000


def test_reasoning_agent_solves_maths_018_goldbach():
    """Maths-018: Goldbach verify [4, 1000] → 499 verified."""
    agent = ReasoningAgent()
    response = agent.process(
        "Verify Goldbach's strong conjecture empirically: for every even integer n in "
        "[4, 1000], find a decomposition n = p + q where p and q are primes. Report the "
        "count of even integers that decompose."
    )
    assert response.confidence == "high"
    assert response.problem_shape == "goldbach_verify_range"
    assert response.parsed_inputs == {"N": 1000}
    assert response.lemma.actual_value == 499


def test_reasoning_agent_solves_maths_019_twin_primes():
    """Maths-019: enumerate twin primes (p, p+2) ≤ 1000 → 35 pairs (OEIS A007508)."""
    agent = ReasoningAgent()
    response = agent.process(
        "Enumerate twin prime pairs (p, p+2) where both p and p+2 are prime and "
        "p+2 ≤ 1000. Report the count."
    )
    assert response.confidence == "high"
    assert response.problem_shape == "twin_primes_in_range"
    assert response.parsed_inputs == {"N": 1000}
    assert response.lemma.actual_value == 35


def test_reasoning_agent_solves_maths_020_mertens():
    """Maths-020: Mertens bound verify |M(n)| ≤ √n for [1, 1000] → 1000 verified."""
    agent = ReasoningAgent()
    response = agent.process(
        "Verify the Mertens bound empirically: for every integer n in [1, 1000], check "
        "whether |M(n)| ≤ √n, where M(n) is the Mertens function. Report the count "
        "satisfying the bound."
    )
    assert response.confidence == "high"
    assert response.problem_shape == "mertens_bound_verify"
    assert response.parsed_inputs == {"N": 1000}
    assert response.lemma.actual_value == 1000


def test_reasoning_agent_number_theory_no_keyword_refuses():
    """Prompts mentioning [1, 1000] but no number-theory keyword (collatz/goldbach/
    twin prime/mertens) must NOT false-match any number-theory dispatcher."""
    agent = ReasoningAgent()
    response = agent.process("Compute the sum of integers in [1, 1000].")
    assert response.problem_shape not in {
        "collatz_verify_range",
        "goldbach_verify_range",
        "twin_primes_in_range",
        "mertens_bound_verify",
    }


# --- Cycle-13 #07d audit-B4 fold-ins: prose-form N extraction + formal-priority boost ---


def test_collatz_prose_first_N_integers_routes_formal():
    """Cycle-13 #07d (audit B4): the demo P3 prompt "Verify the Collatz conjecture
    for the first 10000 integers and discuss honestly..." used to fall through the
    bracketed [1, N] regex and silently route to natural-mode. Prose-form widening
    + tightened natural-mode triggers + formal-priority-boost all conspire to send
    this back to formal `collatz_verify_range`.
    """
    agent = ReasoningAgent()
    response = agent.process(
        "Verify the Collatz conjecture for the first 10000 integers and discuss "
        "honestly what this does and doesn't prove."
    )
    assert response.problem_shape == "collatz_verify_range", (
        f"P3-style prompt should route to formal Collatz; got {response.problem_shape}"
    )
    assert response.parsed_inputs == {"N": 10000}
    assert response.confidence == "high"


def test_collatz_prose_for_n_up_to_routes_formal():
    """Cycle-13 #07d prose form 'for n up to N' → formal Collatz with N extracted."""
    agent = ReasoningAgent()
    response = agent.process("Verify the Collatz conjecture for n up to 500.")
    assert response.problem_shape == "collatz_verify_range"
    assert response.parsed_inputs == {"N": 500}


def test_collatz_prose_in_the_first_routes_formal():
    """Cycle-13 #07d prose form 'in the first N' → formal Collatz with N extracted."""
    agent = ReasoningAgent()
    response = agent.process(
        "Test Collatz 3n+1 iteration termination in the first 250 positive integers."
    )
    assert response.problem_shape == "collatz_verify_range"
    assert response.parsed_inputs == {"N": 250}


def test_collatz_open_conjecture_question_still_natural_mode():
    """Regression guard: the cycle-11 natural-mode-math test prompt still routes
    to `natural_mode_walk_math` after #07d trigger tightening + formal-priority boost.
    The open-conjecture interrogative shape ('what does X mean') is now the natural-mode
    trigger; the formal parser refuses because no parseable N is in the prompt.
    """
    agent = ReasoningAgent()
    response = agent.process("What does the Collatz conjecture mean? Is it solved?")
    assert response.problem_shape == "natural_mode_walk_math"


def test_mertens_prose_form_routes_formal():
    """Cycle-13 #07d symmetric Mertens widening: prose-form 'first N' → formal Mertens."""
    agent = ReasoningAgent()
    response = agent.process(
        "Verify the Mertens bound |M(n)| ≤ √n for the first 300 integers."
    )
    assert response.problem_shape == "mertens_bound_verify"
    assert response.parsed_inputs == {"N": 300}


def test_formal_priority_boost_active_in_dispatcher_metadata():
    """Cycle-13 #07d formal-priority-boost: the boost multiplier is exposed as
    `_FORMAL_PRIORITY_BOOST` on the agent class; sanity-check the value matches the
    synthesis-verdict §7 row 4 spec of 1.2."""
    agent = ReasoningAgent()
    assert agent._FORMAL_PRIORITY_BOOST == 1.2


# --- Diophantine binary-quadratic dispatcher (maths-024/025, cycle 9 #00P13c9-03) ---


def test_reasoning_agent_solves_maths_024_sum_of_two_squares():
    """Maths-024: integer solutions to x² + y² = 25 → 12 solutions."""
    agent = ReasoningAgent()
    response = agent.process(
        "Find all integer solutions (x, y) to the Diophantine equation x² + y² = 25. "
        "Report the count."
    )
    assert response.confidence == "high"
    assert response.domain == "maths"
    assert response.problem_shape == "diophantine_binary_quadratic"
    assert response.parsed_inputs == {"a": 1, "b": 0, "c": 1, "N": 25}
    assert response.lemma.actual_value == 12


def test_reasoning_agent_solves_maths_025_asymmetric_binary_quadratic():
    """Maths-025: integer solutions to 2x² + 3y² = 35 → 8 solutions."""
    agent = ReasoningAgent()
    response = agent.process(
        "Find all integer solutions (x, y) to the Diophantine equation "
        "2·x² + 3·y² = 35. Report the count."
    )
    assert response.confidence == "high"
    assert response.problem_shape == "diophantine_binary_quadratic"
    assert response.parsed_inputs == {"a": 2, "b": 0, "c": 3, "N": 35}
    assert response.lemma.actual_value == 8


def test_reasoning_agent_diophantine_non_pell_indefinite_refused():
    """Non-Pell indefinite shape (N ≠ 1) still falls through to substrate refusal.
    Cycle 10 #02 Pell route only catches (a=1, b=0, c<0, N=1); other indefinite forms
    like x² − 2y² = 3 retain the original NotImplementedError-wrapped refusal because
    fundamental-solution + recurrence for general Pell-like x² − n·y² = N (N ≠ ±1) is
    cycle 11+ territory."""
    agent = ReasoningAgent()
    response = agent.process(
        "Find all integer solutions (x, y) to the Diophantine equation x² - 2·y² = 3."
    )
    assert response.confidence == "refused"
    assert response.problem_shape == "diophantine_binary_quadratic_out_of_scope"
    assert response.parsed_inputs == {"a": 1, "b": 0, "c": -2, "N": 3}
    # Honest M-PROJECTX-013 framing surfaces in the refusal text
    assert "Matiyasevich" in response.answer_text or "Hilbert" in response.answer_text


# --- Cycle 10 #02 Pell dispatcher (maths-026/027) ---


def test_reasoning_agent_solves_maths_026_pell_n2():
    """Maths-026: x² − 2·y² = 1 → first 5 positive integer solutions via Pell substrate.
    Fundamental (3, 2); recurrence yields (17, 12), (99, 70), (577, 408), (3363, 2378).
    Dispatcher routes Pell-shape (a=1, b=0, c=-n, N=1) to solve_pell_equation instead
    of refusing as out-of-scope."""
    agent = ReasoningAgent()
    response = agent.process(
        "Find the first 5 integer solutions (x, y) to the Diophantine Pell equation "
        "x² − 2·y² = 1. Report the count."
    )
    assert response.confidence == "high"
    assert response.domain == "maths"
    assert response.problem_shape == "pell_equation"
    assert response.parsed_inputs == {"a": 1, "b": 0, "c": -2, "N": 1, "n": 2, "k_max": 5}
    assert response.lemma.actual_value == 5


def test_reasoning_agent_solves_maths_027_pell_n3():
    """Maths-027: x² − 3·y² = 1 → first 5 positive integer solutions.
    Fundamental (2, 1); recurrence yields (7, 4), (26, 15), (97, 56), (362, 209)."""
    agent = ReasoningAgent()
    response = agent.process(
        "Find the first 5 integer solutions (x, y) to the Diophantine Pell equation "
        "x² − 3·y² = 1. Report the count."
    )
    assert response.confidence == "high"
    assert response.problem_shape == "pell_equation"
    assert response.parsed_inputs == {"a": 1, "b": 0, "c": -3, "N": 1, "n": 3, "k_max": 5}
    assert response.lemma.actual_value == 5


def test_reasoning_agent_pell_perfect_square_n_refused():
    """Perfect-square n is a degenerate Pell — equation factors as (x − √n·y)(x + √n·y) = 1
    with only trivial integer solutions. The substrate raises ValueError inside
    _continued_fraction_sqrt; dispatcher wraps as refused-with-reason rather than crashing.
    n = 4 (√n = 2) is the canonical degenerate case."""
    agent = ReasoningAgent()
    response = agent.process(
        "Find integer solutions (x, y) to the Diophantine equation x² − 4·y² = 1."
    )
    assert response.confidence == "refused"
    assert response.problem_shape == "pell_equation_degenerate"
    assert response.parsed_inputs == {"a": 1, "b": 0, "c": -4, "N": 1, "n": 4}
    # Honest framing should surface in refusal text
    assert "degenerate" in response.answer_text.lower() or "perfect square" in response.answer_text.lower()


def test_reasoning_agent_pell_first_solution_correctness_n2():
    """Mechanical correctness: first emitted (x, y) for n=2 must be (3, 2) — the
    well-known Pell fundamental. Catches any off-by-one in the recurrence or seed
    that would slip past the count-only assertion in maths-026."""
    agent = ReasoningAgent()
    response = agent.process(
        "Find the first 5 integer solutions (x, y) to the Diophantine Pell equation "
        "x² − 2·y² = 1."
    )
    assert response.confidence == "high"
    # Drill into the Lemma's apply_recurrence step output for the solutions list
    apply_step = next(s for s in response.lemma.derivation_steps if s.operation == "apply_recurrence")
    solutions = apply_step.output["solutions"]
    assert solutions[0] == (3, 2)
    assert solutions[-1] == (3363, 2378)  # 5th solution, exact integer arithmetic


def test_reasoning_agent_diophantine_no_keyword_falls_through():
    """A prompt 'x² + y² = 25' WITHOUT a Diophantine-flavor keyword must NOT match
    the Diophantine dispatcher. The keyword gate prevents misrouting plain algebra."""
    agent = ReasoningAgent()
    response = agent.process("Compute x² + y² = 25 for some (x, y).")
    assert response.problem_shape != "diophantine_binary_quadratic"


def test_reasoning_agent_diophantine_cross_term_form():
    """Eisenstein-style cross term: x² + xy + y² = 3 → 6 solutions, Δ = -3 (positive-definite)."""
    agent = ReasoningAgent()
    response = agent.process(
        "Find all integer solutions (x, y) to x² + xy + y² = 3 (Eisenstein form)."
    )
    assert response.confidence == "high"
    assert response.problem_shape == "diophantine_binary_quadratic"
    assert response.parsed_inputs == {"a": 1, "b": 1, "c": 1, "N": 3}
    assert response.lemma.actual_value == 6


# --- Cycle 8 #06 parser-robustness regression tests ---


def test_parser_robustness_free_fall_meters_full_word():
    """`_HEIGHT_PATTERN` accepts full-word 'meters' suffix (was failing on `m\\b` boundary
    before #06; rephrased prompt 'dropped from 100 meters' now routes correctly)."""
    agent = ReasoningAgent()
    response = agent.process(
        "An object is dropped from 100 meters with g = 9.81 m/s². Compute fall time."
    )
    assert response.confidence == "high"
    assert response.problem_shape == "free_fall"
    assert response.parsed_inputs["h_meters"] == 100.0
    assert response.parsed_inputs["g_m_per_s_squared"] == 9.81


def test_parser_robustness_free_fall_metres_british():
    """British spelling 'metres' also accepted."""
    agent = ReasoningAgent()
    response = agent.process(
        "An object falls from 50 metres with g = 9.81 m/s. Compute the fall time."
    )
    assert response.confidence == "high"
    assert response.problem_shape == "free_fall"
    assert response.parsed_inputs["h_meters"] == 50.0


def test_parser_robustness_pendulum_length_of_phrasing():
    """`_LENGTH_PATTERN` accepts 'length 1 m' phrasing (rephrased prompt
    'swinging pendulum of length 1 m' now routes; was failing on L=... requirement)."""
    agent = ReasoningAgent()
    response = agent.process(
        "A swinging pendulum of length 1 m with g = 9.81 m/s². Compute the period."
    )
    assert response.confidence == "high"
    assert response.problem_shape == "pendulum_small_angle"
    assert response.parsed_inputs["L_meters"] == 1.0


def test_parser_robustness_pendulum_length_of_with_word():
    """'length of 1 m' phrasing also accepted (the `(?:\\s+of)?` optional 'of' clause)."""
    agent = ReasoningAgent()
    response = agent.process(
        "A pendulum of length of 0.5 m hangs in a g = 9.81 m/s² field. Period?"
    )
    assert response.confidence == "high"
    assert response.problem_shape == "pendulum_small_angle"
    assert response.parsed_inputs["L_meters"] == 0.5


def test_parser_robustness_quadratic_unicode_minus():
    """`_QUADRATIC_PATTERN` accepts unicode minus `−` (U+2212) alongside ASCII `-`.
    Typographically-rendered math (LaTeX → text dump) often uses unicode minus."""
    agent = ReasoningAgent()
    # maths-001 verbatim with ASCII minus replaced by unicode minus
    response = agent.process("Solve 3x^2 − 14x − 5 = 0 for x.")
    assert response.confidence == "high"
    assert response.problem_shape == "quadratic"
    assert response.parsed_inputs == {"a": 3.0, "b": -14.0, "c": -5.0}
    assert sorted(response.lemma.actual_value) == [-1 / 3, 5.0]


def test_parser_robustness_quadratic_unicode_x_squared():
    """`_QUADRATIC_PATTERN` accepts unicode `x²` (U+00B2 superscript) alongside `x^2`."""
    agent = ReasoningAgent()
    response = agent.process("Solve 3x² - 14x - 5 = 0 for x.")
    assert response.confidence == "high"
    assert response.problem_shape == "quadratic"
    assert response.parsed_inputs == {"a": 3.0, "b": -14.0, "c": -5.0}


def test_parser_robustness_existing_prompts_still_match():
    """REGRESSION GUARD: original (pre-#06) prompts still route correctly after the
    parser-robustness extensions. Verifies backward-compat across the changed patterns."""
    agent = ReasoningAgent()
    # Original free-fall prompt (height of X m)
    r1 = agent.process(
        "An object is dropped from a height of 80 m on Earth (g = 9.81 m/s²). Find the time."
    )
    assert r1.problem_shape == "free_fall"
    # Original pendulum prompt (L = X m)
    r2 = agent.process(
        "Find the period of a simple pendulum with L = 1.0 m, g = 9.81 m/s²."
    )
    assert r2.problem_shape == "pendulum_small_angle"
    # Original quadratic prompt (ASCII minus + x^2)
    r3 = agent.process("Solve 3x^2 - 14x - 5 = 0 for x.")
    assert r3.problem_shape == "quadratic"
    assert sorted(r3.lemma.actual_value) == [-1 / 3, 5.0]


# --- Symbolic integration dispatch (maths-021..023; cycle 9 #00P13c9-01) ---


def test_reasoning_agent_solves_maths_021_integration_by_parts_exp():
    """Maths-021 verbatim: ∫₀¹ x·e^x dx via integration by parts → 1.0."""
    agent = ReasoningAgent()
    response = agent.process(
        "Compute the value of the definite integral from 0 to 1 of x·e^x dx via integration by parts."
    )
    assert response.confidence == "high"
    assert response.domain == "maths"
    assert response.problem_shape == "definite_integral_x_times_exp"
    assert response.parsed_inputs == {"lower": 0.0, "upper": 1.0, "c": 1.0}
    assert abs(response.lemma.actual_value - 1.0) < 1e-9


def test_reasoning_agent_solves_maths_022_integration_by_parts_sin():
    """Maths-022 verbatim: ∫₀^π x·sin(x) dx via integration by parts → π."""
    agent = ReasoningAgent()
    response = agent.process(
        "Compute the value of the definite integral from 0 to 3.141592653589793 of x·sin(x) dx via integration by parts."
    )
    assert response.confidence == "high"
    assert response.problem_shape == "definite_integral_x_times_sin"
    assert response.parsed_inputs["c"] == 1.0
    assert abs(response.lemma.actual_value - math.pi) < 1e-9


def test_reasoning_agent_solves_maths_023_u_substitution():
    """Maths-023 verbatim: ∫₀¹ x·sin(x²) dx via u-substitution → (1-cos(1))/2."""
    agent = ReasoningAgent()
    response = agent.process(
        "Compute the value of the definite integral from 0 to 1 of x·sin(x²) dx via u-substitution."
    )
    assert response.confidence == "high"
    assert response.problem_shape == "definite_integral_xtrig_via_usub_sin"
    assert response.parsed_inputs == {"lower": 0.0, "upper": 1.0, "trig_fn": "sin"}
    expected = (1.0 - math.cos(1.0)) / 2.0
    assert abs(response.lemma.actual_value - expected) < 1e-9


def test_reasoning_agent_integration_x_cos_via_parts():
    """∫₀^π x·cos(x) dx via integration by parts → -2 (canonical)."""
    agent = ReasoningAgent()
    response = agent.process(
        "Compute the value of the definite integral from 0 to 3.141592653589793 of x·cos(x) dx via integration by parts."
    )
    assert response.confidence == "high"
    assert response.problem_shape == "definite_integral_x_times_cos"
    assert abs(response.lemma.actual_value - (-2.0)) < 1e-9


def test_reasoning_agent_integration_no_technique_keyword_refuses():
    """Symbolic-integration dispatchers require explicit technique keyword. Missing 'integration
    by parts' or 'u-substitution' → don't false-match these dispatchers (would fall through to
    quadratic-polynomial dispatcher or refusal)."""
    agent = ReasoningAgent()
    response = agent.process("Compute the value of the integral from 0 to 1 of x·e^x dx.")
    assert response.problem_shape != "definite_integral_x_times_exp"
    assert response.problem_shape != "definite_integral_x_times_sin"
    assert response.problem_shape != "definite_integral_xtrig_via_usub_sin"


# --- Cycle 11 #00P13c11-01 BG-style confidence-scored parallel-bid dispatcher ---


def test_bg_dispatcher_annotates_successful_response_with_metadata():
    """Successful dispatch carries `dispatcher_metadata` with combined-confidence + top5."""
    agent = ReasoningAgent()
    response = agent.process("Solve the quadratic 3x² - 14x - 5 = 0.")
    assert response.problem_shape == "quadratic"
    assert response.dispatcher_metadata is not None
    md = response.dispatcher_metadata
    assert "combined_confidence" in md
    assert 0.0 <= md["combined_confidence"] <= 1.0
    # Quadratic parser matched → confidence ≥ α (0.6)
    assert md["combined_confidence"] >= 0.6
    assert "top5_candidates" in md
    assert len(md["top5_candidates"]) >= 1
    # Top candidate IS the dispatched method
    top_method = md["top5_candidates"][0][0]
    assert top_method == "_try_quadratic"
    # alpha + tau_dispatch surfaced for inspectability
    assert md["alpha"] == 0.6
    assert md["tau_dispatch"] == 0.3


def test_bg_dispatcher_chain_order_tiebreaker_preserves_pell_priority():
    """Pell prompt produces Pell response via _try_diophantine_binary_quadratic
    (which is FIRST in chain). Verifies chain-order tiebreaker preserves the
    cycle-10-close routing behavior on this canonical disambiguation case."""
    agent = ReasoningAgent()
    response = agent.process(
        "Find the first 5 integer solutions (x, y) to the Diophantine Pell equation "
        "x² − 2·y² = 1."
    )
    assert response.problem_shape == "pell_equation"
    assert response.confidence == "high"
    # Dispatcher chose `_try_diophantine_binary_quadratic` over any later-chain parser
    assert response.dispatcher_metadata["top5_candidates"][0][0] == "_try_diophantine_binary_quadratic"


def test_bg_dispatcher_natural_mode_routes_open_prompt():
    """Open-mode prompt routes to natural_mode walk with provenance-traced confidence."""
    agent = ReasoningAgent()
    response = agent.process("Write a poem about loneliness in winter.")
    assert response.problem_shape == "natural_mode_walk_poetry"
    assert response.confidence == "provenance-traced"
    assert response.dispatcher_metadata is not None
    # Natural-mode parser matched → confidence ≥ α
    assert response.dispatcher_metadata["combined_confidence"] >= 0.6


def test_bg_dispatcher_refusal_path_when_no_parser_matches():
    """Unmatched prompt → honest refusal. Refusal responses DO NOT carry
    dispatcher_metadata (because the BG-dispatcher's top-candidate annotation
    only fires when a candidate clears the threshold and dispatches)."""
    agent = ReasoningAgent()
    # post cycle-12 #00P13c12-01b: "Tell me about X" now matches narrative_prose
    # natural_mode trigger; use a prompt that doesn't match any keyword gate.
    response = agent.process("asdf qwerty random nonsense characters here.")
    assert response.problem_shape == "unrecognized"
    assert response.confidence == "refused"
    # The honest-refusal path returns AgentResponse with default dispatcher_metadata=None
    assert response.dispatcher_metadata is None


def test_bg_dispatcher_runs_all_parsers_collects_candidates():
    """BG-style runs every parser in `_DISPATCH_CHAIN_ORDER`; chain length is
    21 (15 closed-form primitives + 4 number-theory + 1 natural-mode + 1
    fallback). Verifies the chain registration is complete."""
    assert len(ReasoningAgent._DISPATCH_CHAIN_ORDER) == 21


def test_bg_dispatcher_archetype_dict_covers_chain():
    """Every problem_shape used in the dispatcher chain has an archetype prompt
    in _PARSER_ARCHETYPES (or falls back to the prompt-itself baseline)."""
    from project_x.reasoning_agent import _PARSER_ARCHETYPES
    # The archetype dict has at least one entry per chain step's primary problem_shape;
    # some chain steps map to multiple problem_shapes (e.g., natural_mode emits
    # natural_mode_walk_{poetry,philosophy,math,lain_voice}).
    primary_archetype_keys = [k for k, _ in ReasoningAgent._DISPATCH_CHAIN_ORDER]
    for key in primary_archetype_keys:
        # Either the key is in _PARSER_ARCHETYPES, OR the parser's response uses a
        # different problem_shape name that IS in _PARSER_ARCHETYPES (substring check)
        in_dict = key in _PARSER_ARCHETYPES
        # E.g., pendulum_small_angle in chain; _PARSER_ARCHETYPES has pendulum_small_angle + pendulum_large_angle
        assert in_dict, f"chain key '{key}' missing from _PARSER_ARCHETYPES"


def test_bg_dispatcher_regression_diophantine_quadratic_disambiguation():
    """Cycle 9 #03 disambiguation: 'Find all integer solutions (x, y) to x² + y² = 25'
    routes to Diophantine (NOT quadratic). BG-style with chain-order tiebreaker
    preserves this — quadratic parser doesn't match the two-variable form anyway,
    so the dispatcher correctly picks Diophantine on Diophantine-only-match."""
    agent = ReasoningAgent()
    response = agent.process(
        "Find all integer solutions (x, y) to the Diophantine equation x² + y² = 25. "
        "Report the count."
    )
    assert response.problem_shape == "diophantine_binary_quadratic"
    assert response.dispatcher_metadata["top5_candidates"][0][0] == "_try_diophantine_binary_quadratic"


# --- Cycle 11 #00P13c11-08 dual-mode composer (intent-classified register selection) ---


def test_dual_mode_register_classifier_terse_intent():
    """Prompts asking for 'just the answer / one line / no explanation' classify
    to terse register. HDC-cosine similarity to register archetype."""
    from project_x.reasoning_agent import _classify_intent_register
    register = _classify_intent_register("Just give me the roots one line answer no explanation.")
    assert register == "terse"


def test_dual_mode_register_classifier_tutorial_intent():
    """Prompts asking for 'explain / step by step / why each step works' classify
    to tutorial register."""
    from project_x.reasoning_agent import _classify_intent_register
    register = _classify_intent_register("Explain step by step how to solve this and why each step works pedagogically.")
    assert register == "tutorial"


def test_dual_mode_register_classifier_casual_intent():
    """Prompts with chat-flavored phrasing classify to casual register."""
    from project_x.reasoning_agent import _classify_intent_register
    register = _classify_intent_register("Hey, what do you think about this — let's chat casually about it.")
    assert register == "casual"


def test_dual_mode_register_classifier_default_intent():
    """Plain factual prompts without specific flavor markers default to default register."""
    from project_x.reasoning_agent import _classify_intent_register
    register = _classify_intent_register("Solve this problem and show your work structured.")
    assert register == "default"


def test_dual_mode_agent_renders_quadratic_at_terse_register():
    """Terse-framed quadratic prompt produces terse-register Lemma render via
    agent.process() — same underlying substrate computation, different output flavor."""
    agent = ReasoningAgent()
    response = agent.process("Just give me the roots of 3 x^2 - 14 x - 5 = 0, one line answer.")
    assert response.problem_shape == "quadratic"
    assert response.dispatcher_metadata["intent_register"] == "terse"
    # Terse output: claim + Affirmative only, no Step lines
    assert "Step 1" not in response.answer_text
    assert "Affirmative —" in response.answer_text


def test_dual_mode_agent_renders_quadratic_at_tutorial_register():
    """Tutorial-framed prompt produces tutorial-register render with 💡 prefix."""
    agent = ReasoningAgent()
    response = agent.process("Explain how to solve 3 x^2 - 14 x - 5 = 0 step by step and why each step works.")
    assert response.problem_shape == "quadratic"
    assert response.dispatcher_metadata["intent_register"] == "tutorial"
    assert "💡 Why this matters:" in response.answer_text


def test_dual_mode_agent_renders_quadratic_at_casual_register():
    """Casual-framed prompt produces casual-register render with 'OK so —' opener."""
    agent = ReasoningAgent()
    response = agent.process("Hey Raphael, what do you think about the quadratic 3 x^2 - 14 x - 5 = 0 — just chat with me.")
    assert response.problem_shape == "quadratic"
    assert response.dispatcher_metadata["intent_register"] == "casual"
    assert response.answer_text.startswith("OK so —")


def test_dual_mode_register_metadata_populated_on_dispatch():
    """Every successful dispatch carries `intent_register` in dispatcher_metadata."""
    agent = ReasoningAgent()
    response = agent.process("Solve for x: 3 x^2 - 14 x - 5 = 0.")
    assert "intent_register" in response.dispatcher_metadata
    assert response.dispatcher_metadata["intent_register"] in ("default", "terse", "tutorial", "casual")
