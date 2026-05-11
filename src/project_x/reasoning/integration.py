"""From-scratch symbolic integration primitives — Phase 13 cycle 9 #00P13c9-01.

Beyond polynomial-power-rule integration (cycle 8 #02's `polynomial_definite_integral`):
symbolic definite integration for transcendental integrand shapes via integration-by-parts
and u-substitution. Each primitive recognizes a specific integrand shape, computes the
closed-form antiderivative analytically, and evaluates at bounds. Pure pattern-matched
substrate — no symbolic-algebra library; no LLM at agent layer.

Lain mid-cycle directive 2026-05-11: "make it so smart Hassabis would actually be
impressed... try to get it to solve harder and harder things". This module is the first
step beyond freshman calc — integration techniques that require strategy-choice (which
parts pairing? which substitution?) rather than mechanical power-rule.

Minimum-viable scope (4 primitives covering canonical textbook patterns):
- `definite_integral_x_times_exp(a, b, c)` — ∫_a^b x·e^(cx) dx via parts
- `definite_integral_x_times_sin(a, b, c)` — ∫_a^b x·sin(cx) dx via parts
- `definite_integral_x_times_cos(a, b, c)` — ∫_a^b x·cos(cx) dx via parts
- `definite_integral_xtrig_via_usub(a, b, trig_fn)` — ∫_a^b x·sin(x²) or x·cos(x²) dx via u=x²

Organic-thesis compliance (binding): hand-rolled stdlib `math.exp` / `math.sin` /
`math.cos` only. NO sympy, NO scipy, NO numerical-integration libraries. The substrate
DERIVES the antiderivative symbolically via parts/u-sub formulas, then evaluates at
bounds — the textual representation of the antiderivative is in the Lemma's
step.justification chain so a grader/reader can audit the technique-choice.

`actual_value` = numerical result (float). Honest M-PROJECTX-013 framing in INTROs:
PASS = "evaluated this integrand class via the named technique", NOT "general
symbolic integration capability". Cycle 10+ extends to partial fractions, trigonometric
substitution, iterated parts, etc.
"""

from __future__ import annotations

import math
from typing import Callable

from project_x.reasoning.symbolic import Lemma


# Cycle 10 #01f shared helper — algorithmically-independent verifier for each
# integration primitive. Midpoint Riemann sum evaluates the integrand directly at
# N midpoints; never references the closed-form antiderivative or the parts/u-sub
# derivation. A typo in the antiderivative-formula path would NOT propagate to the
# Riemann sum. For smooth integrands (x·e^cx, x·sin(cx), x·cos(cx), x·sin(x²),
# x·cos(x²)) on bounded intervals with N=10000, midpoint-rule error is O(h²) and
# well under 1e-6, easily within Lemma.tolerance=0.001. The parts primitives ALSO
# carry an algorithmically-independent parts-identity invariant (recomputes ∫ v du
# independently); the Riemann sum is defense-in-depth there — a second independent
# path. The u-substitution primitive had only a tautological change-of-variables
# check before cycle 10; Riemann is its first STRONG verifier.
def _midpoint_riemann(integrand: Callable[[float], float], lower: float, upper: float, *, N: int = 10000) -> float:
    """Composite midpoint Riemann sum on a callable integrand.

    Discretizes [lower, upper] into N equal subintervals; evaluates the callable
    at each subinterval midpoint; accumulates with weight Δx = (upper − lower)/N.
    Pure numerical quadrature — does not reference any closed-form antiderivative
    or symbolic-integration step. Used as the STRONG cross-check across all four
    integration primitives in this module.
    """
    dx = (upper - lower) / N
    total = 0.0
    for i in range(N):
        total += integrand(lower + (i + 0.5) * dx)
    return total * dx


# ── Integration by parts: ∫ x·e^(c·x) dx ──────────────────────────────────────


INTRO_INTEGRATION_BY_PARTS_X_EXP = (
    "For ∫ x·e^(c·x) dx with c ≠ 0, integration by parts (∫ u dv = u·v - ∫ v du) "
    "applied via the LIATE heuristic (Logs, Inverse trig, Algebraic, Trig, "
    "Exponential — pick u as earlier in LIATE) chooses u = x (Algebraic) and "
    "dv = e^(c·x) dx (Exponential — last in LIATE, so the dv pick). Then du = dx "
    "and v = e^(c·x)/c. Applying the formula: ∫ x·e^(c·x) dx = x·e^(c·x)/c - "
    "∫ e^(c·x)/c dx = x·e^(c·x)/c - e^(c·x)/c² = e^(c·x)·(c·x - 1)/c². For the "
    "trivial branch c = 0 the integrand reduces to x, with antiderivative x²/2."
)


def definite_integral_x_times_exp(
    lower: float, upper: float, c: float = 1.0,
    lemma_id: str = "definite_integral_x_times_exp",
) -> Lemma:
    """Compute ∫_lower^upper x·e^(c·x) dx via integration-by-parts closed form.

    Closed-form antiderivative: F(x) = e^(c·x)·(c·x - 1)/c² for c ≠ 0.
    Trivial branch c = 0: F(x) = x²/2 (integrand reduces to x).

    Returns Lemma with 5-step derivation chain (identify → choose_u_dv → compute_du_v
    → apply_parts → evaluate_bounds). Hand-rolled — uses math.exp only.
    """
    lemma = Lemma(
        id=lemma_id,
        claim=f"Compute ∫_{lower}^{upper} x · e^({c}·x) dx via integration by parts.",
        verification_method="numerical_close",
    )
    lemma.add_introduction(INTRO_INTEGRATION_BY_PARTS_X_EXP)

    # Trivial branch: c = 0 reduces ∫ x·e^0 dx = ∫ x dx = x²/2 evaluated at bounds.
    if c == 0:
        result = (upper * upper - lower * lower) / 2.0
        lemma.add_step(
            operation="trivial_c_zero_branch",
            inputs={"lower": lower, "upper": upper, "c": c},
            output=result,
            justification=(
                f"c = 0 reduces e^(c·x) to 1; integrand becomes x; antiderivative x²/2; "
                f"∫_{lower}^{upper} x dx = ({upper}² - {lower}²)/2 = {result}."
            ),
        )
        lemma.actual_value = result
        return lemma

    # Step 1: identify integrand + technique selection (LIATE).
    lemma.add_step(
        operation="identify_integrand",
        inputs={"integrand": f"x · e^({c}·x)", "lower": lower, "upper": upper},
        output="integration_by_parts (algebraic × exponential — LIATE picks u = x)",
        justification=(
            f"Integrand is x · e^({c}·x), a product of x (Algebraic; class A) and "
            f"e^({c}·x) (Exponential; class E). LIATE heuristic: earlier letter wins for "
            f"u; A < E so u = x, dv = e^({c}·x) dx."
        ),
    )

    # Step 2: assign u, dv.
    lemma.add_step(
        operation="choose_u_dv",
        inputs={"integrand": f"x · e^({c}·x)"},
        output={"u": "x", "dv": f"e^({c}·x) dx"},
        justification=f"u = x (algebraic factor); dv = e^({c}·x) dx (exponential factor).",
    )

    # Step 3: compute du = d(x) and v = ∫ dv = e^(cx)/c.
    lemma.add_step(
        operation="compute_du_v",
        inputs={"u": "x", "dv": f"e^({c}·x) dx"},
        output={"du": "dx", "v": f"e^({c}·x) / {c}"},
        justification=(
            f"du = d(u)/dx · dx = 1·dx = dx. v = ∫ dv = ∫ e^({c}·x) dx = e^({c}·x)/{c}."
        ),
    )

    # Step 4: apply parts formula → antiderivative F(x).
    # ∫ x·e^(cx) dx = x·e^(cx)/c - ∫ e^(cx)/c dx = x·e^(cx)/c - e^(cx)/c² = e^(cx)·(cx-1)/c²
    c_sq = c * c
    antiderivative_form = f"e^({c}·x)·({c}·x - 1)/{c_sq}"
    lemma.add_step(
        operation="apply_parts_formula",
        inputs={"u": "x", "v": f"e^({c}·x)/{c}", "du": "dx"},
        output=antiderivative_form,
        justification=(
            f"∫ u dv = u·v - ∫ v du. Substituting: x·(e^({c}·x)/{c}) - ∫ (e^({c}·x)/{c}) dx "
            f"= x·e^({c}·x)/{c} - e^({c}·x)/{c_sq} = e^({c}·x)·({c}·x - 1)/{c_sq}. "
            f"This is the antiderivative F(x)."
        ),
    )

    # Step 5: evaluate F at upper and lower bounds.
    F_upper = math.exp(c * upper) * (c * upper - 1) / c_sq
    F_lower = math.exp(c * lower) * (c * lower - 1) / c_sq
    integral = F_upper - F_lower
    lemma.add_step(
        operation="evaluate_bounds",
        inputs={"F_upper": F_upper, "F_lower": F_lower, "lower": lower, "upper": upper},
        output=integral,
        justification=(
            f"F({upper}) = e^({c}·{upper})·({c}·{upper} - 1)/{c_sq} = {F_upper}. "
            f"F({lower}) = e^({c}·{lower})·({c}·{lower} - 1)/{c_sq} = {F_lower}. "
            f"∫_{lower}^{upper} x·e^({c}·x) dx = F({upper}) - F({lower}) = {integral}."
        ),
    )

    lemma.actual_value = integral

    # Invariant: integration-by-parts identity ∫_a^b u dv + ∫_a^b v du = [u·v]_a^b.
    # ∫_a^b e^(cx)/c dx = e^(cx)/c² evaluated at bounds = (e^(c·upper) - e^(c·lower))/c²
    # [x·e^(cx)/c]_a^b = (upper·e^(c·upper) - lower·e^(c·lower))/c
    # Verifies the derivation by recomposing both halves of the parts equation.
    integral_v_du = (math.exp(c * upper) - math.exp(c * lower)) / c_sq
    uv_at_bounds = (upper * math.exp(c * upper) - lower * math.exp(c * lower)) / c
    lemma.add_invariant_check(
        predicate="∫_a^b u dv + ∫_a^b v du = [u·v]_a^b (integration-by-parts identity)",
        expected_value=uv_at_bounds,
        actual_value=integral + integral_v_du,
        justification=(
            "Integration by parts identity: ∫ u dv + ∫ v du = uv evaluated at bounds. "
            "Recompose both halves and verify the sum matches [u·v]_a^b. Algorithmically "
            "the second integral (∫ v du = ∫ e^(cx)/c dx = e^(cx)/c²) is computed "
            "independently from the first; consistency check across two derivations."
        ),
    )

    # Cycle 10 #01f STRONG verifier (algorithmically-independent): midpoint Riemann
    # sum on the original integrand x·e^(cx). Never touches the parts derivation,
    # never builds an antiderivative, never invokes LIATE — pure direct evaluation
    # at 10000 midpoints. Defense-in-depth on top of the parts-identity invariant.
    riemann_integral = _midpoint_riemann(
        lambda x, _c=c: x * math.exp(_c * x), lower, upper,
    )
    lemma.add_invariant_check(
        predicate="midpoint Riemann sum N=10000 ≈ parts closed-form (algorithmically-independent STRONG verifier)",
        expected_value=integral,
        actual_value=riemann_integral,
        justification=(
            f"Riemann sum over [{lower}, {upper}] on integrand x·e^({c}·x): "
            f"{riemann_integral}; parts closed-form: {integral}. Defense-in-depth — "
            "the parts-identity invariant already provides one independent path; "
            "Riemann provides a second, evaluating x·e^(cx) at midpoints with no "
            "reference to antiderivative or LIATE."
        ),
    )

    return lemma


# ── Integration by parts: ∫ x·sin(c·x) dx ─────────────────────────────────────


INTRO_INTEGRATION_BY_PARTS_X_SIN = (
    "For ∫ x·sin(c·x) dx with c ≠ 0, integration by parts via LIATE chooses u = x "
    "(Algebraic; class A) and dv = sin(c·x) dx (Trigonometric; class T — but A < T "
    "so the choice is unambiguous). Then du = dx and v = -cos(c·x)/c. Applying the "
    "formula: ∫ x·sin(c·x) dx = -x·cos(c·x)/c - ∫ -cos(c·x)/c dx = -x·cos(c·x)/c + "
    "sin(c·x)/c² = (sin(c·x) - c·x·cos(c·x))/c². For c = 0 the integrand is 0 "
    "(sin(0) = 0) and the integral is 0."
)


def definite_integral_x_times_sin(
    lower: float, upper: float, c: float = 1.0,
    lemma_id: str = "definite_integral_x_times_sin",
) -> Lemma:
    """Compute ∫_lower^upper x·sin(c·x) dx via integration-by-parts closed form.

    Closed-form: F(x) = (sin(c·x) - c·x·cos(c·x))/c² for c ≠ 0.
    Trivial c = 0: integrand identically 0; result 0.
    """
    lemma = Lemma(
        id=lemma_id,
        claim=f"Compute ∫_{lower}^{upper} x · sin({c}·x) dx via integration by parts.",
        verification_method="numerical_close",
    )
    lemma.add_introduction(INTRO_INTEGRATION_BY_PARTS_X_SIN)

    if c == 0:
        lemma.add_step(
            operation="trivial_c_zero_branch",
            inputs={"lower": lower, "upper": upper, "c": c},
            output=0.0,
            justification="c = 0 → sin(0·x) = sin(0) = 0; integrand identically 0; integral = 0.",
        )
        lemma.actual_value = 0.0
        return lemma

    # Step 1: technique selection
    lemma.add_step(
        operation="identify_integrand",
        inputs={"integrand": f"x · sin({c}·x)", "lower": lower, "upper": upper},
        output="integration_by_parts (algebraic × trigonometric)",
        justification=f"x is Algebraic (class A), sin({c}·x) is Trig (class T); u = x.",
    )

    # Step 2: u, dv
    lemma.add_step(
        operation="choose_u_dv",
        inputs={"integrand": f"x · sin({c}·x)"},
        output={"u": "x", "dv": f"sin({c}·x) dx"},
        justification="u = x; dv = sin({0}·x) dx.".format(c),
    )

    # Step 3: du, v
    # v = ∫ sin(cx) dx = -cos(cx)/c
    lemma.add_step(
        operation="compute_du_v",
        inputs={"u": "x", "dv": f"sin({c}·x) dx"},
        output={"du": "dx", "v": f"-cos({c}·x)/{c}"},
        justification=f"du = dx. v = ∫ sin({c}·x) dx = -cos({c}·x)/{c}.",
    )

    # Step 4: apply parts
    # ∫ x·sin(cx) dx = -x·cos(cx)/c - ∫ -cos(cx)/c dx = -x·cos(cx)/c + sin(cx)/c²
    #               = (sin(cx) - cx·cos(cx))/c²
    c_sq = c * c
    antiderivative_form = f"(sin({c}·x) - {c}·x·cos({c}·x))/{c_sq}"
    lemma.add_step(
        operation="apply_parts_formula",
        inputs={"u": "x", "v": f"-cos({c}·x)/{c}", "du": "dx"},
        output=antiderivative_form,
        justification=(
            f"∫ u dv = uv - ∫ v du. Substituting: x · (-cos({c}·x)/{c}) - "
            f"∫ -cos({c}·x)/{c} dx = -x·cos({c}·x)/{c} + sin({c}·x)/{c_sq} = "
            f"(sin({c}·x) - {c}·x·cos({c}·x))/{c_sq}."
        ),
    )

    # Step 5: evaluate
    F_upper = (math.sin(c * upper) - c * upper * math.cos(c * upper)) / c_sq
    F_lower = (math.sin(c * lower) - c * lower * math.cos(c * lower)) / c_sq
    integral = F_upper - F_lower
    lemma.add_step(
        operation="evaluate_bounds",
        inputs={"F_upper": F_upper, "F_lower": F_lower, "lower": lower, "upper": upper},
        output=integral,
        justification=(
            f"F({upper}) = (sin({c}·{upper}) - {c}·{upper}·cos({c}·{upper}))/{c_sq} = {F_upper}. "
            f"F({lower}) = (sin({c}·{lower}) - {c}·{lower}·cos({c}·{lower}))/{c_sq} = {F_lower}. "
            f"∫ = F({upper}) - F({lower}) = {integral}."
        ),
    )

    lemma.actual_value = integral

    # Invariant: parts identity (algorithmically-independent re-computation of v du integral)
    integral_v_du = -(math.sin(c * upper) - math.sin(c * lower)) / c_sq
    uv_at_bounds = -(upper * math.cos(c * upper) - lower * math.cos(c * lower)) / c
    lemma.add_invariant_check(
        predicate="∫_a^b u dv + ∫_a^b v du = [u·v]_a^b (integration-by-parts identity)",
        expected_value=uv_at_bounds,
        actual_value=integral + integral_v_du,
        justification=(
            "Parts identity recomposition. ∫ v du = ∫ -cos(cx)/c dx = -sin(cx)/c² "
            "computed independently from the primary derivation; consistency check."
        ),
    )

    # Cycle 10 #01f STRONG verifier — midpoint Riemann on integrand x·sin(cx).
    riemann_integral = _midpoint_riemann(
        lambda x, _c=c: x * math.sin(_c * x), lower, upper,
    )
    lemma.add_invariant_check(
        predicate="midpoint Riemann sum N=10000 ≈ parts closed-form (algorithmically-independent STRONG verifier)",
        expected_value=integral,
        actual_value=riemann_integral,
        justification=(
            f"Riemann sum over [{lower}, {upper}] on x·sin({c}·x): {riemann_integral}; "
            f"parts closed-form: {integral}. Direct evaluation at 10000 midpoints, no "
            "antiderivative or LIATE — independent of the primary path."
        ),
    )

    return lemma


# ── Integration by parts: ∫ x·cos(c·x) dx ─────────────────────────────────────


INTRO_INTEGRATION_BY_PARTS_X_COS = (
    "For ∫ x·cos(c·x) dx with c ≠ 0, integration by parts via LIATE chooses u = x and "
    "dv = cos(c·x) dx. Then du = dx and v = sin(c·x)/c. Applying: ∫ x·cos(c·x) dx = "
    "x·sin(c·x)/c - ∫ sin(c·x)/c dx = x·sin(c·x)/c + cos(c·x)/c² = (cos(c·x) + "
    "c·x·sin(c·x))/c². For c = 0 the integrand reduces to x (cos(0) = 1) with "
    "antiderivative x²/2."
)


def definite_integral_x_times_cos(
    lower: float, upper: float, c: float = 1.0,
    lemma_id: str = "definite_integral_x_times_cos",
) -> Lemma:
    """Compute ∫_lower^upper x·cos(c·x) dx via integration-by-parts closed form.

    Closed-form: F(x) = (cos(c·x) + c·x·sin(c·x))/c² for c ≠ 0.
    Trivial c = 0: integrand = x (since cos(0)=1); F(x) = x²/2.
    """
    lemma = Lemma(
        id=lemma_id,
        claim=f"Compute ∫_{lower}^{upper} x · cos({c}·x) dx via integration by parts.",
        verification_method="numerical_close",
    )
    lemma.add_introduction(INTRO_INTEGRATION_BY_PARTS_X_COS)

    if c == 0:
        result = (upper * upper - lower * lower) / 2.0
        lemma.add_step(
            operation="trivial_c_zero_branch",
            inputs={"lower": lower, "upper": upper, "c": c},
            output=result,
            justification=(
                f"c = 0 → cos(0·x) = 1; integrand reduces to x; ∫ x dx = x²/2; "
                f"F({upper}) - F({lower}) = {result}."
            ),
        )
        lemma.actual_value = result
        return lemma

    lemma.add_step(
        operation="identify_integrand",
        inputs={"integrand": f"x · cos({c}·x)", "lower": lower, "upper": upper},
        output="integration_by_parts (algebraic × trigonometric)",
        justification=f"x is Algebraic, cos({c}·x) is Trig; LIATE picks u = x.",
    )

    lemma.add_step(
        operation="choose_u_dv",
        inputs={"integrand": f"x · cos({c}·x)"},
        output={"u": "x", "dv": f"cos({c}·x) dx"},
        justification="u = x; dv = cos({0}·x) dx.".format(c),
    )

    lemma.add_step(
        operation="compute_du_v",
        inputs={"u": "x", "dv": f"cos({c}·x) dx"},
        output={"du": "dx", "v": f"sin({c}·x)/{c}"},
        justification=f"du = dx. v = ∫ cos({c}·x) dx = sin({c}·x)/{c}.",
    )

    c_sq = c * c
    antiderivative_form = f"(cos({c}·x) + {c}·x·sin({c}·x))/{c_sq}"
    lemma.add_step(
        operation="apply_parts_formula",
        inputs={"u": "x", "v": f"sin({c}·x)/{c}", "du": "dx"},
        output=antiderivative_form,
        justification=(
            f"∫ u dv = uv - ∫ v du = x·sin({c}·x)/{c} - ∫ sin({c}·x)/{c} dx = "
            f"x·sin({c}·x)/{c} + cos({c}·x)/{c_sq} = "
            f"(cos({c}·x) + {c}·x·sin({c}·x))/{c_sq}."
        ),
    )

    F_upper = (math.cos(c * upper) + c * upper * math.sin(c * upper)) / c_sq
    F_lower = (math.cos(c * lower) + c * lower * math.sin(c * lower)) / c_sq
    integral = F_upper - F_lower
    lemma.add_step(
        operation="evaluate_bounds",
        inputs={"F_upper": F_upper, "F_lower": F_lower, "lower": lower, "upper": upper},
        output=integral,
        justification=(
            f"F({upper}) = {F_upper}. F({lower}) = {F_lower}. ∫ = {integral}."
        ),
    )

    lemma.actual_value = integral

    # Invariant: parts identity recomposition.
    integral_v_du = -(math.cos(c * upper) - math.cos(c * lower)) / c_sq
    uv_at_bounds = (upper * math.sin(c * upper) - lower * math.sin(c * lower)) / c
    lemma.add_invariant_check(
        predicate="∫_a^b u dv + ∫_a^b v du = [u·v]_a^b (integration-by-parts identity)",
        expected_value=uv_at_bounds,
        actual_value=integral + integral_v_du,
        justification=(
            "Parts identity recomposition. ∫ v du = ∫ sin(cx)/c dx = -cos(cx)/c² "
            "computed independently from primary derivation."
        ),
    )

    # Cycle 10 #01f STRONG verifier — midpoint Riemann on integrand x·cos(cx).
    riemann_integral = _midpoint_riemann(
        lambda x, _c=c: x * math.cos(_c * x), lower, upper,
    )
    lemma.add_invariant_check(
        predicate="midpoint Riemann sum N=10000 ≈ parts closed-form (algorithmically-independent STRONG verifier)",
        expected_value=integral,
        actual_value=riemann_integral,
        justification=(
            f"Riemann sum over [{lower}, {upper}] on x·cos({c}·x): {riemann_integral}; "
            f"parts closed-form: {integral}. Direct midpoint evaluation, no antiderivative."
        ),
    )

    return lemma


# ── u-substitution: ∫ x·sin(x²) dx or ∫ x·cos(x²) dx ──────────────────────────


INTRO_USUB_X_TRIG_X_SQUARED = (
    "For ∫ x·sin(x²) dx (and analogously x·cos(x²)), u-substitution with u = x² has "
    "du = 2x dx, so x dx = du/2. The integrand transforms: ∫ x·sin(x²) dx = "
    "∫ sin(u)·(du/2) = (1/2)·∫ sin(u) du = -cos(u)/2 + C = -cos(x²)/2 + C. The "
    "antiderivative is recovered by back-substituting u = x². The substitution works "
    "because x dx appears EXACTLY as the differential of (1/2)·x² — a key recognition "
    "for u-substitution: spot when half the integrand is the derivative of the other "
    "half's argument. For cos(x²): same substitution gives ∫ x·cos(x²) dx = sin(x²)/2 + C."
)


def definite_integral_xtrig_via_usub(
    lower: float, upper: float, trig_fn: str = "sin",
    lemma_id: str = "definite_integral_xtrig_via_usub",
) -> Lemma:
    """Compute ∫_lower^upper x · sin(x²) dx OR x · cos(x²) dx via u = x² substitution.

    `trig_fn` selects "sin" (antiderivative -cos(x²)/2) or "cos" (antiderivative sin(x²)/2).
    """
    if trig_fn not in ("sin", "cos"):
        raise ValueError(f"trig_fn must be 'sin' or 'cos' (got {trig_fn})")

    integrand_form = f"x · {trig_fn}(x²)"
    lemma = Lemma(
        id=lemma_id,
        claim=f"Compute ∫_{lower}^{upper} {integrand_form} dx via u-substitution (u = x²).",
        verification_method="numerical_close",
    )
    lemma.add_introduction(INTRO_USUB_X_TRIG_X_SQUARED)

    # Step 1: recognize integrand shape + technique
    lemma.add_step(
        operation="identify_integrand",
        inputs={"integrand": integrand_form, "lower": lower, "upper": upper},
        output="u_substitution (u = x²; du = 2x dx)",
        justification=(
            f"Integrand is {integrand_form}. Recognize: x dx appears EXACTLY as the "
            "differential of (1/2)·x²; choose u = x² so du = 2x dx, equivalently "
            "x dx = du/2. This collapses x out of the integrand."
        ),
    )

    # Step 2: substitution + transformed integrand
    u_lower = lower * lower
    u_upper = upper * upper
    lemma.add_step(
        operation="apply_substitution",
        inputs={"u": "x²", "du": "2·x dx"},
        output={
            "transformed_integrand": f"(1/2) · {trig_fn}(u)",
            "u_lower": u_lower,
            "u_upper": u_upper,
        },
        justification=(
            f"x dx = du/2; integrand becomes (1/2)·{trig_fn}(u) du. New bounds: "
            f"u_lower = lower² = {lower}² = {u_lower}; u_upper = upper² = {upper}² = {u_upper}."
        ),
    )

    # Step 3: integrate in u → antiderivative G(u) of (1/2)·trig_fn(u)
    if trig_fn == "sin":
        antiderivative_u_form = "-cos(u)/2"
        # G(u) = -cos(u)/2; G(u_upper) - G(u_lower)
        G_upper = -math.cos(u_upper) / 2.0
        G_lower = -math.cos(u_lower) / 2.0
    else:  # cos
        antiderivative_u_form = "sin(u)/2"
        G_upper = math.sin(u_upper) / 2.0
        G_lower = math.sin(u_lower) / 2.0

    lemma.add_step(
        operation="integrate_in_u",
        inputs={"transformed_integrand": f"(1/2) · {trig_fn}(u)"},
        output=antiderivative_u_form,
        justification=(
            f"∫ (1/2)·{trig_fn}(u) du = {antiderivative_u_form} + C. "
            f"Standard trig antiderivatives: ∫ sin(u) du = -cos(u); ∫ cos(u) du = sin(u)."
        ),
    )

    # Step 4: back-substitute u = x² and evaluate at bounds
    integral = G_upper - G_lower
    back_sub_form = antiderivative_u_form.replace("u", "x²")
    lemma.add_step(
        operation="back_substitute_and_evaluate",
        inputs={
            "G_at_u_upper": G_upper,
            "G_at_u_lower": G_lower,
            "u_upper": u_upper,
            "u_lower": u_lower,
        },
        output=integral,
        justification=(
            f"Back-substitute u = x²: antiderivative F(x) = {back_sub_form}. "
            f"Evaluate at original bounds: F({upper}) = G({u_upper}) = {G_upper}; "
            f"F({lower}) = G({u_lower}) = {G_lower}; ∫ = F({upper}) - F({lower}) = {integral}."
        ),
    )

    lemma.actual_value = integral

    # Invariant: u-sub identity — ∫_a^b f(g(x))·g'(x) dx = ∫_g(a)^g(b) f(u) du.
    # We computed both sides; verify they match (tautological under correct substitution
    # but catches transformation bugs). For our case both sides equal `integral` exactly.
    direct_u_integral = G_upper - G_lower  # ∫_g(a)^g(b) (1/2)·trig_fn(u) du
    lemma.add_invariant_check(
        predicate="∫_a^b f(g(x))·g'(x) dx = ∫_g(a)^g(b) f(u) du (u-substitution identity)",
        expected_value=integral,
        actual_value=direct_u_integral,
        justification=(
            "u-substitution change-of-variables theorem. Computing the u-side integral "
            "directly should match the back-substituted x-side evaluation. Tautological "
            "under correct technique-application; catches transformation bugs."
        ),
    )

    # Cycle 10 #01f STRONG verifier — midpoint Riemann on the ORIGINAL integrand
    # x·sin(x²) or x·cos(x²) (depending on trig_fn). Never references the u=x²
    # substitution, never converts bounds, never back-substitutes. Pure direct
    # evaluation in the original x-variable. The cycle-9 u-substitution invariant
    # above was tautological (both sides computed via the same path); Riemann is
    # this primitive's first algorithmically-independent verifier.
    if trig_fn == "sin":
        riemann_integral = _midpoint_riemann(
            lambda x: x * math.sin(x * x), lower, upper,
        )
    else:
        riemann_integral = _midpoint_riemann(
            lambda x: x * math.cos(x * x), lower, upper,
        )
    lemma.add_invariant_check(
        predicate="midpoint Riemann sum N=10000 ≈ u-sub closed-form (algorithmically-independent STRONG verifier)",
        expected_value=integral,
        actual_value=riemann_integral,
        justification=(
            f"Riemann sum over [{lower}, {upper}] on x·{trig_fn}(x²): "
            f"{riemann_integral}; u-sub closed-form: {integral}. The Riemann path "
            "evaluates the original integrand at midpoints in the x-variable with "
            "no substitution; completely independent of the u=x² technique."
        ),
    )

    return lemma
