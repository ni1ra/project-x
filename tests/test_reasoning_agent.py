"""Tests for src/project_x/reasoning_agent.py — Phase 13 #00P13c7-NEW.

Coverage:
- Quadratic dispatch on the 3 standard-form-quadratic ladder entries (maths-001/007/008).
- Implicit-a-coefficient handling (`x^2` = 1·x², `-x^2` = -1·x²).
- Parser-miss returns honest refusal (no confabulation).
- AgentResponse schema sanity.

Cycle 7 minimum-viable scope; cycle 7+ extensions add tests per new problem-shape.
"""

from __future__ import annotations

from project_x.reasoning_agent import (
    AgentResponse,
    ReasoningAgent,
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


def test_reasoning_agent_refuses_eigenvalue_problem_for_now():
    """Cycle 7 minimum-viable is quadratic only; eigenvalues defer to cycle 7+."""
    agent = ReasoningAgent()
    response = agent.process("Find the eigenvalues of the 2x2 matrix [[2, 1], [1, 2]].")

    # Eigenvalue prompt should NOT match quadratic pattern (no `x^2` form).
    assert response.confidence == "refused"
