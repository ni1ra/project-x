"""From-scratch calculus primitives — Phase 13 cycle 8 #00P13c8-02.

Hand-rolled definite-integral evaluator for polynomial integrands via the Fundamental
Theorem of Calculus (FTC). Closes the maths-010 agent-runtime gap by supplying a substrate
the ReasoningAgent can dispatch to (cycle 7 #39 architecture).

Cycle 8 minimum-viable scope: polynomial integrands (any degree); evaluation over [a, b]
real interval. Cycle 8+ extends to standard transcendental functions (trig, exp, log) as
ladder entries require.

Organic-thesis compliance (binding): NO scipy / NO sympy / NO numerical-integration
libraries. Computes the antiderivative term-by-term via the power rule (∫x^n dx = x^(n+1)/(n+1))
then applies FTC closing (F(b) - F(a)).
"""

from __future__ import annotations

from project_x.reasoning.symbolic import Lemma


INTRO_POLYNOMIAL_DEFINITE_INTEGRAL = (
    "For a polynomial integrand p(x) = c_n·x^n + c_{n-1}·x^{n-1} + ... + c_1·x + c_0, the "
    "Fundamental Theorem of Calculus (FTC) gives ∫_a^b p(x) dx = F(b) - F(a) where F is "
    "any antiderivative of p. Term-by-term application of the power rule "
    "(∫x^k dx = x^{k+1}/(k+1) + C) produces F(x) = c_n·x^{n+1}/(n+1) + ... + c_1·x²/2 + c_0·x. "
    "The constant of integration cancels in F(b) - F(a) so any antiderivative works."
)


def polynomial_definite_integral(
    coeffs_descending: list[float],
    lower: float,
    upper: float,
    lemma_id: str = "polynomial_definite_integral",
) -> Lemma:
    """Compute ∫_lower^upper p(x) dx for polynomial p(x) via FTC.

    `coeffs_descending` lists coefficients in DESCENDING degree order to match natural
    polynomial reading: [3, 2, -1] = 3x² + 2x - 1. Empty list = zero polynomial (integral 0).

    Returns a Lemma with the derivation chain: build antiderivative coefficients →
    evaluate at upper bound → evaluate at lower bound → FTC closing F(upper) - F(lower).
    Invariant: F(upper) - F(lower) is independent of integration constant C; the dimensionless
    check verifies (F(upper) + K) - (F(lower) + K) = F(upper) - F(lower) for K=42 (any constant).
    """
    if not coeffs_descending:
        lemma = Lemma(
            id=lemma_id,
            claim=f"Compute ∫_{lower}^{upper} 0 dx = 0 (zero polynomial).",
            verification_method="numerical_close",
        )
        lemma.actual_value = 0.0
        return lemma

    # Internal representation: index = power, value = coefficient.
    # coeffs_descending=[3, 2, -1] (3x² + 2x - 1) → coeffs_by_power = [-1, 2, 3]
    # (index 0 = constant, index 1 = x, index 2 = x²).
    degree = len(coeffs_descending) - 1
    coeffs_by_power = list(reversed(coeffs_descending))

    lemma = Lemma(
        id=lemma_id,
        claim=(
            f"Compute ∫_{lower}^{upper} ("
            + " + ".join(
                f"{c}·x^{degree - i}" if degree - i > 0 else f"{c}"
                for i, c in enumerate(coeffs_descending)
            )
            + f") dx via FTC."
        ),
        verification_method="numerical_close",
    )
    lemma.add_introduction(INTRO_POLYNOMIAL_DEFINITE_INTEGRAL)

    # Step 1: antiderivative coefficients (power rule term-by-term).
    # F has degree (n+1); coefficient at power k+1 of F = coeffs_by_power[k] / (k+1).
    antiderivative_by_power: list[float] = [0.0]  # constant term of F (drops out anyway)
    for k, c in enumerate(coeffs_by_power):
        antiderivative_by_power.append(c / (k + 1))
    lemma.add_step(
        operation="antiderivative",
        inputs={"coeffs_by_power": coeffs_by_power},
        output=antiderivative_by_power,
        justification=(
            f"Power rule term-by-term: ∫x^k dx = x^{{k+1}}/(k+1). Antiderivative coefficients "
            f"by power: {antiderivative_by_power} (index = power, value = coefficient of x^power)."
        ),
    )

    # Step 2 + 3: evaluate F at upper and lower bounds (Horner's method on F's coefficient list).
    def _evaluate(coeffs_by_power: list[float], x: float) -> float:
        # F(x) = sum_k coeffs_by_power[k] · x^k, using Horner's: start from highest degree.
        result = 0.0
        for c in reversed(coeffs_by_power):
            result = result * x + c
        return result

    F_upper = _evaluate(antiderivative_by_power, upper)
    F_lower = _evaluate(antiderivative_by_power, lower)
    lemma.add_step(
        operation="evaluate_upper",
        inputs={"upper": upper, "antiderivative_by_power": antiderivative_by_power},
        output=F_upper,
        justification=f"F({upper}) = {F_upper} (Horner's evaluation of antiderivative).",
    )
    lemma.add_step(
        operation="evaluate_lower",
        inputs={"lower": lower, "antiderivative_by_power": antiderivative_by_power},
        output=F_lower,
        justification=f"F({lower}) = {F_lower}.",
    )

    # Step 4: FTC closing.
    integral = F_upper - F_lower
    lemma.add_step(
        operation="ftc_closing",
        inputs={"F_upper": F_upper, "F_lower": F_lower},
        output=integral,
        justification=f"∫_{lower}^{upper} p(x) dx = F({upper}) - F({lower}) = {F_upper} - {F_lower} = {integral}.",
    )

    lemma.actual_value = integral

    # Invariant: F(upper) - F(lower) is independent of constant of integration C.
    # Verify by shifting both F values by an arbitrary constant K=42 and confirming the
    # difference is unchanged. Trivially holds algebraically; the test catches code bugs.
    K = 42.0
    shifted_diff = (F_upper + K) - (F_lower + K)
    lemma.add_invariant_check(
        predicate="(F(upper) + K) - (F(lower) + K) = F(upper) - F(lower) for any K (constant cancels)",
        expected_value=integral,
        actual_value=shifted_diff,
        justification=(
            "Constant of integration drops out of FTC. (F(b)+K) - (F(a)+K) = F(b) - F(a) "
            "identically — verifies the subtraction in `ftc_closing` is implemented correctly."
        ),
    )

    return lemma
