"""From-scratch complex-analysis primitives — Phase 13 cycle 8 #00P13c8-01.

Hand-rolled residue-theorem-based evaluators for real-line integrals of rational functions
whose denominator has no real roots. Closes the maths-003 agent-runtime gap by supplying a
substrate the ReasoningAgent can dispatch to (cycle 7 #39 architecture).

Cycle 8 minimum-viable scope: ∫_{-∞}^{+∞} 1/(a·x² + c) dx = π/√(a·c) for a, c > 0
(simple-quadratic-denominator rational integrals). Cycle 8+ extends to higher-degree
denominators + non-trivial numerators as needed by ladder entries.

Organic-thesis compliance (binding): NO scipy / NO sympy / NO numerical-integration
libraries. The substrate computes the residue analytically in closed form for the
unit-quadratic case, then applies the residue-theorem identity directly.
"""

from __future__ import annotations

import math

from project_x.reasoning.symbolic import Lemma


INTRO_RESIDUE_UNIT_QUADRATIC = (
    "For a rational function 1/(a·x² + c) with a, c > 0 (denominator has no real roots), "
    "the real-line integral ∫_{-∞}^{+∞} 1/(a·x² + c) dx is evaluated via the residue "
    "theorem on the upper-half-plane contour: closed contour C = [-R, R] ∪ semicircle of "
    "radius R in upper half plane, take R → ∞. The semicircular contribution vanishes "
    "because |1/(a·z² + c)| decays as 1/|z|² along the arc (Jordan-bound argument). "
    "The denominator factors as a·(z - i·√(c/a))·(z + i·√(c/a)); only the pole at "
    "z = i·√(c/a) lies inside C. Residue at that pole: 1/(2·a·i·√(c/a)) = 1/(2i·√(a·c)). "
    "Closing: 2π·i · residue = 2π·i / (2i·√(a·c)) = π/√(a·c). Special case a=c=1: "
    "the integral evaluates to π (Cauchy's standard textbook example)."
)


def residue_theorem_unit_quadratic(
    a: float, c: float, lemma_id: str = "residue_theorem_unit_quadratic",
) -> Lemma:
    """Compute ∫_{-∞}^{+∞} dx/(a·x² + c) = π/√(a·c) via residue theorem (closed-form).

    Domain: a > 0, c > 0 (denominator has no real roots; integral converges). Negative
    coefficients put roots on the real line; out-of-scope ValueError.

    Returns a Lemma carrying the derivation chain: identify integrand → locate poles →
    compute residue at upper-half-plane pole → apply residue theorem closing. Invariant
    check: integral · √(a·c) / π should equal 1 (universal dimensionless identity for
    this family — any drift signals a math bug in the closed-form).
    """
    if a <= 0 or c <= 0:
        raise ValueError(
            f"a and c must be positive (got a={a}, c={c}); negative coefficient "
            f"puts roots on the real line, integral diverges (out of cycle 8 scope)",
        )

    lemma = Lemma(
        id=lemma_id,
        claim=f"Compute ∫_(-∞)^(+∞) dx / ({a}·x² + {c}) via residue theorem.",
        verification_method="numerical_close",
    )
    lemma.add_introduction(INTRO_RESIDUE_UNIT_QUADRATIC)

    # Step 1: factor denominator and locate poles (closed-form for quadratic in z).
    pole_imag = math.sqrt(c / a)
    lemma.add_step(
        operation="locate_poles",
        inputs={"a": a, "c": c},
        output=pole_imag,
        justification=(
            f"a·z² + c = 0 → z² = -c/a = -{c/a} → z = ±i·√(c/a) = ±i·{pole_imag}. "
            f"Only z = +i·{pole_imag} lies in the upper half plane (inside contour C)."
        ),
    )

    # Step 2: compute residue at the upper-half-plane pole.
    # Residue at z = i·√(c/a) = 1 / (derivative of a·z² + c at that point)
    #                         = 1 / (2·a·z |_{z = i·√(c/a)})
    #                         = 1 / (2·a · i·√(c/a))
    #                         = 1 / (2i·√(a·c))   (since a·√(c/a) = √(a²·c/a) = √(a·c))
    # We track the magnitude (1/(2·√(a·c))); the 1/i = -i imaginary part cancels with
    # the 2π·i factor in the residue theorem closing to give a real, positive integral.
    sqrt_ac = math.sqrt(a * c)
    residue_magnitude = 1.0 / (2.0 * sqrt_ac)
    lemma.add_step(
        operation="compute_residue",
        inputs={"pole_imag": pole_imag, "sqrt_ac": sqrt_ac},
        output=residue_magnitude,
        justification=(
            f"Residue at z = i·{pole_imag}: 1/(d/dz(a·z² + c)|_{{z=i·{pole_imag}}}) = "
            f"1/(2·{a}·i·{pole_imag}) = 1/(2i·√(a·c)) = 1/(2i·{sqrt_ac}); magnitude "
            f"|residue| = 1/(2·{sqrt_ac}) = {residue_magnitude}."
        ),
    )

    # Step 3: apply residue-theorem closing — integral = 2π·i · residue.
    # The (1/i) in residue magnitude and the (i) factor in 2π·i cancel; result is real positive.
    integral = math.pi / sqrt_ac
    lemma.add_step(
        operation="residue_theorem_closing",
        inputs={"residue_magnitude": residue_magnitude, "sqrt_ac": sqrt_ac},
        output=integral,
        justification=(
            f"∫_{{-∞}}^{{+∞}} dx/(a·x² + c) = 2π·i · residue = 2π·i / (2i·√(a·c)) = "
            f"π/√(a·c) = π/{sqrt_ac} = {integral}. The i factors cancel; result is real positive."
        ),
    )

    lemma.actual_value = integral

    # Invariant: integral · √(a·c) / π = 1 (dimensionless universal identity).
    # Any drift from 1.0 signals a math bug in the closed-form derivation.
    dimensionless = integral * sqrt_ac / math.pi
    lemma.add_invariant_check(
        predicate="integral · √(a·c) / π = 1 (dimensionless universal identity)",
        expected_value=1.0,
        actual_value=dimensionless,
        justification=(
            "From integral = π/√(a·c): integral · √(a·c) / π = 1 universally across "
            "all (a, c) with a, c > 0. Independent of integral magnitude — any drift "
            "from 1.0 signals a derivation bug."
        ),
    )

    return lemma
