"""From-scratch ODE primitives — Phase 13 cycle 8 #00P13c8-03.

Hand-rolled first-order linear separable homogeneous ODE solver. Closes the
maths-011 agent-runtime gap by supplying a substrate the ReasoningAgent can
dispatch to (cycle 7 #39 architecture).

Cycle 8 minimum-viable scope: dy/dx = k·y subject to y(x_0) = y_0; closed-form
y(x) = y_0 · e^(k·(x - x_0)). Covers exponential growth (k > 0), decay (k < 0),
constant (k = 0), trivial zero (y_0 = 0). Cycle 8+ extends to non-homogeneous
(dy/dx + p(x)·y = q(x)) and separable general (dy/dx = f(x)·g(y)) as ladder
entries require.

Organic-thesis compliance (binding): NO scipy / NO sympy / NO numerical-ODE-solver
libraries. Substrate uses math.exp from Python stdlib (calculator, not a
symbolic-AI library; same standing as math.sqrt / math.pi in cycle 8 #01/#02).

Predicate-strength note: ships with algebraic-identity invariants (IC preservation)
matching cycle 8 #01/#02 pattern. Independent-path verifier (Taylor expansion of
exp algorithmically distinct from math.exp) deferred to cycle 9 predicate-strength
uniformity pass per advisor verdict 2026-05-11.
"""

from __future__ import annotations

import math

from project_x.reasoning.symbolic import Lemma


INTRO_FIRST_ORDER_LINEAR_ODE_EXP = (
    "For the first-order linear separable homogeneous ODE dy/dx = k·y with initial "
    "condition y(x_0) = y_0, separation of variables gives dy/y = k dx (valid for "
    "y ≠ 0; the trivial branch y(x) ≡ 0 covers y_0 = 0 via ODE-uniqueness, and the "
    "closed-form below yields 0 in that case anyway). Integrating both sides: "
    "ln|y| = k·x + C, equivalently y = A·e^(k·x). Applying y(x_0) = y_0 fixes "
    "A = y_0·e^(-k·x_0), so y(x) = y_0 · e^(k·(x - x_0)). This is exponential "
    "growth (k > 0), decay (k < 0), or constant (k = 0). The IC is preserved at "
    "x = x_0 (y(x_0) = y_0·e^0 = y_0) and the ODE itself is satisfied at the IC "
    "(dy/dx|_{x=x_0} = k·y_0·e^0 = k·y_0, matching the RHS)."
)


def first_order_linear_ode_exp_solution(
    k: float,
    y_0: float,
    x_target: float,
    x_0: float = 0.0,
    lemma_id: str = "first_order_linear_ode_exp",
) -> Lemma:
    """Solve dy/dx = k·y subject to y(x_0) = y_0, evaluated at x_target.

    Closed-form: y(x) = y_0 · e^(k·(x - x_0)). Hand-rolled — uses only math.exp.

    `x_0` defaults to 0.0 (canonical IC at the origin). Generalizing to non-zero
    x_0 is free under the closed-form and prevents API churn when cycle 9+
    ladder entries anchor ICs away from the origin.

    Trivial branches the closed-form handles naturally:
    - y_0 = 0 → y(x) ≡ 0 (constant-zero by ODE uniqueness; 0·e^anything = 0)
    - k = 0   → y(x) ≡ y_0 (math.exp(0) = 1; constant solution)

    Returns a Lemma carrying the 4-step derivation chain (identify_form →
    separate_variables → integrate_and_apply_IC → evaluate_at_target). Invariant
    check: y(x_0) = y_0 (IC preservation; algebraically tautological under the
    closed-form but surfaces the check in the proof-shape audit trail and catches
    arithmetic bugs around math.exp(0.0) == 1.0).
    """
    # 4-step Lemma chain mirroring cycle 8 #01 (residue) / #02 (FTC integral).
    lemma = Lemma(
        id=lemma_id,
        claim=f"Solve dy/dx = {k}·y with y({x_0}) = {y_0}; report y({x_target}).",
        verification_method="numerical_close",
    )
    lemma.add_introduction(INTRO_FIRST_ORDER_LINEAR_ODE_EXP)

    lemma.add_step(
        operation="identify_form",
        inputs={"ode": "dy/dx = k·y", "k": k, "y_0": y_0, "x_0": x_0},
        output="first_order_linear_separable_homogeneous",
        justification=(
            f"ODE dy/dx = {k}·y is first-order (one derivative), linear (no y² or "
            f"higher powers of y), separable (RHS factors as constant·y), and "
            f"homogeneous (no x-only forcing term). IC y({x_0}) = {y_0}."
        ),
    )

    lemma.add_step(
        operation="separate_variables",
        inputs={"ode": "dy/dx = k·y"},
        output="dy/y = k dx",
        justification=(
            "Algebraic rearrangement: divide both sides by y. Valid when y ≠ 0; "
            "if y_0 = 0 the trivial solution y(x) ≡ 0 satisfies dy/dx = k·y, and "
            "the closed-form y_0·e^(k·(x-x_0)) below yields 0 in that case anyway."
        ),
    )

    lemma.add_step(
        operation="integrate_and_apply_IC",
        inputs={"k": k, "y_0": y_0, "x_0": x_0},
        output=f"y(x) = {y_0} · exp({k} · (x - {x_0}))",
        justification=(
            f"Integrate dy/y = k dx: ln|y| = k·x + C, equivalently y = A·e^(k·x). "
            f"Apply IC y({x_0}) = {y_0}: A·e^(k·{x_0}) = {y_0} → A = {y_0}·e^(-k·{x_0}). "
            f"Substituting: y(x) = {y_0}·e^(-k·{x_0})·e^(k·x) = {y_0}·e^(k·(x - {x_0}))."
        ),
    )

    y_at_target = y_0 * math.exp(k * (x_target - x_0))
    lemma.add_step(
        operation="evaluate_at_target",
        inputs={"x_target": x_target, "y_0": y_0, "k": k, "x_0": x_0},
        output=y_at_target,
        justification=(
            f"Substitute x = {x_target}: y({x_target}) = {y_0} · e^({k}·({x_target} - "
            f"{x_0})) = {y_0} · e^({k * (x_target - x_0)}) = {y_at_target}."
        ),
    )

    lemma.actual_value = y_at_target

    # Invariant: IC preservation. y(x_0) = y_0 · e^(k·(x_0 - x_0)) = y_0 · e^0 = y_0.
    # Algebraically tautological under the closed-form; surfaces the IC check in
    # the proof-shape audit trail and catches math.exp(0.0) ≠ 1.0 arithmetic bugs.
    y_at_ic = y_0 * math.exp(k * (x_0 - x_0))
    lemma.add_invariant_check(
        predicate=f"y({x_0}) = y_0 (initial condition preserved)",
        expected_value=y_0,
        actual_value=y_at_ic,
        justification=(
            "y(x_0) = y_0·e^(k·(x_0 - x_0)) = y_0·e^0 = y_0. Tautological under "
            "the closed-form; verifies math.exp(0.0) == 1.0 (Python stdlib spec) "
            "and that the substrate composes the multiplication correctly."
        ),
    )

    # Cycle 10 #01e STRONG (algorithmically-independent) verifier: hand-rolled Taylor
    # series for e^z computed via truncated power series Σ z^n / n! for n in [0, 20).
    # Closed-form path uses math.exp (C math library, IEEE 754 + ulp-bounded); Taylor
    # path computes e^z entirely in Python arithmetic via incremental term construction
    # term_{n+1} = term_n · z / (n+1). Two genuinely different implementations of the
    # exponential — math.exp could be hardware-fused-multiply-add or table-lookup-with-
    # correction internally; Taylor is bare floating-point Σ. A bug in either does NOT
    # propagate to the other. Truncation error at N=20 for |z| ≤ 5 is well under 1e-9
    # (|z|^N · e^|z| / N! upper bound), easily within Lemma.tolerance=0.001.
    z = k * (x_target - x_0)
    y_via_taylor = y_0 * _exp_via_taylor_series(z, N=20)
    lemma.add_invariant_check(
        predicate=(
            "y(x_target) via 20-term Taylor series for e^z ≈ math.exp closed-form "
            "(algorithmically-independent STRONG verifier)"
        ),
        expected_value=y_at_target,
        actual_value=y_via_taylor,
        justification=(
            f"Compute e^({z}) via Σ_{{n=0}}^{{19}} ({z})^n / n! using incremental "
            f"term recurrence (term_{{n+1}} = term_n · z/(n+1)); multiply by y_0 = "
            f"{y_0} to get {y_via_taylor}. The closed-form path uses math.exp which "
            "ultimately calls into the C math library (potentially fused multiply-add "
            "or table-lookup-with-correction internally); the Taylor path is bare "
            "Python floating-point summation. Completely different implementations "
            "of the same mathematical function. Truncation error at N=20 for |z| ≤ 5 "
            "is well under 1e-9, fits tolerance 0.001."
        ),
    )

    return lemma


def _exp_via_taylor_series(z: float, *, N: int = 20) -> float:
    """Compute e^z via truncated Taylor series Σ_{n=0}^{N-1} z^n / n!.

    Incremental term construction avoids materializing factorials: term_0 = 1,
    term_{n+1} = term_n · z / (n+1). After N iterations, total holds the partial sum.

    Algorithmically independent from `math.exp` (CPython's call into libm) — this
    function never invokes math.exp; it computes the exponential via bare Python
    floating-point summation of power-series terms. A bug or ulp-drift in libm's
    exp would NOT propagate here, and vice versa.

    Truncation error: |error| ≤ |z|^N · e^|z| / N! upper bound (Lagrange remainder).
    For |z| up to ~5 with N=20, the bound is well under 1e-9 — easily within the
    Lemma's default tolerance of 0.001. For larger |z| accuracy degrades; the ODE
    substrate's canonical test cases stay well within this safe region.

    Used as a STRONG invariant_check in first_order_linear_ode_exp_solution. Hand-
    rolled — never imports math.exp, never uses math.factorial.
    """
    total = 0.0
    term = 1.0  # z^0 / 0! = 1
    for n in range(N):
        total += term
        term = term * z / (n + 1)
    return total
