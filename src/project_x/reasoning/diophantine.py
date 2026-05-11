"""From-scratch Diophantine binary-quadratic substrate — Phase 13 cycle 9 #00P13c9-03.

Bounded-enumeration substrate for integer solutions (x, y) ∈ ℤ² to the binary quadratic
form equation Q(x, y) = a·x² + b·x·y + c·y² = N. This is the first agent-side Diophantine
capability beyond cycle 8's empirical-verification bench (Collatz / Goldbach / twin primes
/ Mertens). Lain mid-cycle directive 2026-05-11: "harder problems"; Diophantine equations
are graduate-flavored when honest about scope.

CRITICAL HONESTY (M-PROJECTX-013): This substrate is NOT a general Diophantine solver.
Matiyasevich's 1970 negative answer to Hilbert's 10th problem proves no algorithm exists
for arbitrary Diophantine equations. What we DO ship:

  - Positive-definite forms only (discriminant Δ = b² - 4ac < 0, with a > 0, c > 0).
    These have FINITE integer solution sets; brute-force enumeration with a tight
    bound (Lagrange's inequality) is decidable + complete.
  - Targets N ≥ 0 only (positive-definite Q ≥ 0 everywhere; N < 0 has no solutions;
    N = 0 has only the trivial (0, 0) for non-degenerate forms).
  - Indefinite forms (Δ > 0; Pell-equation territory) → NotImplementedError. The
    solution set is infinite when nontrivial; needs fundamental-solution + recurrence
    machinery (cycle 10+ extension).
  - Degenerate forms (Δ = 0; Q factors as a perfect-square linear form) → also
    rejected; the question reduces to a linear Diophantine in disguise.

PASS = "enumerated ALL integer solutions to Q(x, y) = N within the proven bound".
NOT "solved an arbitrary Diophantine equation".

Canonical use cases:
  - Sum of two squares: x² + y² = N. (a=1, b=0, c=1, Δ=-4.) Fermat's two-squares
    theorem: a prime p has solutions iff p = 2 or p ≡ 1 (mod 4); the representation
    is essentially unique up to sign + order swap.
  - Generic positive-definite binary quadratic with cross term.

Out of scope (cycle 10+ candidates):
  - Pell equations x² - n·y² = 1 (indefinite Δ = 4n > 0).
  - Higher-arity Diophantine (3+ variables).
  - Modular reductions (Hasse principle, local-global obstructions).
  - Class number / reduction theory for positive-definite forms.
"""

from __future__ import annotations

import math

from project_x.reasoning.symbolic import Lemma


# Predicate-strength note (cycle 10 #01a): for the symmetric (a=c=1, b=0) case —
# the canonical sum-of-two-squares Diophantine — Jacobi's two-squares formula
# r_2(N) = 4·(d_1(N) − d_3(N)) provides an algorithmically-independent STRONG
# verifier (divisor counting, not geometric brute-force). For the general
# positive-definite case (asymmetric coefficients or non-zero cross term), no
# closed-form counting formula exists at this substrate level; cycle 11+
# candidates are Gauss reduction to canonical class form, or Brandt-Eichler
# theta-series coefficient extraction. The form-parity + D₄ invariants remain
# the best-available checks for general positive-definite forms — they catch
# enumeration symmetry violations but not bound-formula or equation-form bugs.
def _two_squares_via_jacobi(N: int) -> int:
    """Jacobi's two-squares formula: r₂(N) = 4·(d₁(N) − d₃(N)).

    Counts integer solutions (x, y) to x² + y² = N including sign and order
    permutations. d_k(N) counts positive divisors of N congruent to k mod 4.
    Edge cases: N=0 → 1 (just (0,0)); N<0 → 0.

    Algorithmically independent from the brute-force rectangle scan: this
    function never enumerates (x, y) pairs and never evaluates Q(x, y) — it
    operates purely in the integer-factorization / mod-4 lattice. Used as a
    STRONG invariant_check for the symmetric a=c=1, b=0 case.
    """
    if N < 0:
        return 0
    if N == 0:
        return 1
    d1 = 0
    d3 = 0
    # Trial division to enumerate divisors. O(N) here; for the small-N
    # ladder regime this is well under a millisecond. Switching to
    # O(√N) factor-pair enumeration is a cycle-11+ optimization.
    for d in range(1, N + 1):
        if N % d == 0:
            r = d % 4
            if r == 1:
                d1 += 1
            elif r == 3:
                d3 += 1
    return 4 * (d1 - d3)


INTRO_BINARY_QUADRATIC_DIOPHANTINE = (
    "A binary quadratic form Q(x, y) = a·x² + b·x·y + c·y² with integer coefficients "
    "(a, b, c) has discriminant Δ = b² - 4·a·c. The discriminant's sign classifies the "
    "form: Δ < 0 with a > 0 makes Q positive-definite (Q ≥ 0 for all (x, y), with "
    "equality iff x = y = 0); Δ = 0 makes Q degenerate (factors as a single repeated "
    "linear form squared); Δ > 0 makes Q indefinite (takes both signs — Pell-equation "
    "territory with infinite solution sets when nontrivial). For the positive-definite "
    "case we can bound integer solutions to Q(x, y) = N: complete the square in y to "
    "get Q = a·(x + b·y/(2a))² + (4ac - b²)·y²/(4a) ≥ (-Δ)·y²/(4a), so |y| ≤ "
    "√(4·a·N/|Δ|). The symmetric bound |x| ≤ √(4·c·N/|Δ|) follows from completing the "
    "square in x. These two bounds together box the search rectangle; brute-force "
    "enumeration filters by exact equality Q(x, y) = N. Hilbert's 10th problem "
    "(Matiyasevich 1970) shows there is no general algorithm for arbitrary Diophantine "
    "equations; this substrate works precisely because positive-definiteness gives "
    "us a finite, computable bound."
)


def solve_binary_quadratic(
    a: int, b: int, c: int, N: int,
    lemma_id: str = "solve_binary_quadratic",
) -> Lemma:
    """Enumerate integer (x, y) solving a·x² + b·xy + c·y² = N for positive-definite forms.

    Positive-definite predicate: a > 0 AND c > 0 AND Δ = b² - 4ac < 0. Other shapes
    are rejected explicitly (NotImplementedError or empty solution set with reason).

    Returns Lemma with 4-step derivation chain (identify_form → compute_search_bound →
    brute_force_enumerate → verify_solutions) + symmetry invariant check on the
    enumerated solution set. `actual_value` = solution count (int), matching the
    `numerical_close` auto_grade convention used elsewhere.

    Raises NotImplementedError for indefinite (Δ > 0) and degenerate (Δ = 0) forms.
    """
    lemma = Lemma(
        id=lemma_id,
        claim=(
            f"Enumerate all integer solutions (x, y) to {a}·x² + {b}·xy + {c}·y² = {N} "
            f"by bounded brute-force search."
        ),
        verification_method="numerical_close",
        tolerance=0,
    )
    lemma.add_introduction(INTRO_BINARY_QUADRATIC_DIOPHANTINE)

    discriminant = b * b - 4 * a * c

    # Step 1: identify form + classify by discriminant sign.
    lemma.add_step(
        operation="identify_form",
        inputs={"a": a, "b": b, "c": c, "N": N},
        output={"discriminant": discriminant, "classification": _classify(a, c, discriminant)},
        justification=(
            f"Coefficients (a, b, c) = ({a}, {b}, {c}); target N = {N}. "
            f"Discriminant Δ = b² - 4ac = {b}² - 4·{a}·{c} = {discriminant}. "
            f"Classification: {_classify(a, c, discriminant)}."
        ),
    )

    # Reject non-positive-definite forms explicitly — out of cycle 9 scope.
    if discriminant >= 0:
        raise NotImplementedError(
            f"Form {a}x² + {b}xy + {c}y² has discriminant Δ = {discriminant} ≥ 0; "
            f"cycle 9 substrate handles positive-definite (Δ < 0) only. Indefinite "
            f"forms (Δ > 0) are Pell-equation territory with infinite solution sets "
            f"requiring fundamental-solution + recurrence machinery (cycle 10+)."
        )
    if a <= 0 or c <= 0:
        raise NotImplementedError(
            f"Form {a}x² + {b}xy + {c}y² has a={a}, c={c}; cycle 9 substrate requires "
            f"a > 0 AND c > 0 (standard positive-definite shape). Negative-definite "
            f"forms can be transformed via (a, b, c) → (-a, -b, -c) with N → -N but "
            f"that's a cycle 10+ extension."
        )

    # Trivial N branches: positive-definite Q ≥ 0 everywhere with equality iff (0, 0).
    if N < 0:
        lemma.add_step(
            operation="trivial_negative_target",
            inputs={"N": N},
            output={"solutions": [], "count": 0},
            justification=(
                f"Positive-definite Q(x, y) ≥ 0 for all (x, y); N = {N} < 0 has no "
                f"integer solutions. Return empty set."
            ),
        )
        lemma.actual_value = 0
        return lemma
    if N == 0:
        # Q(x, y) = 0 for positive-definite Q iff (x, y) = (0, 0).
        lemma.add_step(
            operation="trivial_zero_target",
            inputs={"N": N},
            output={"solutions": [(0, 0)], "count": 1},
            justification=(
                f"Positive-definite Q(x, y) = 0 iff (x, y) = (0, 0). Single solution."
            ),
        )
        lemma.actual_value = 1
        return lemma

    # Step 2: compute search bound via Lagrange inequality (completing the square).
    # |y| ≤ √(4aN/|Δ|);  |x| ≤ √(4cN/|Δ|).
    abs_disc = abs(discriminant)
    y_bound = math.isqrt(4 * a * N // abs_disc + 1) + 1
    x_bound = math.isqrt(4 * c * N // abs_disc + 1) + 1
    lemma.add_step(
        operation="compute_search_bound",
        inputs={"a": a, "c": c, "N": N, "abs_discriminant": abs_disc},
        output={"x_bound": x_bound, "y_bound": y_bound},
        justification=(
            f"Completing the square in y: Q = a·(x + by/(2a))² + |Δ|·y²/(4a) ≥ "
            f"|Δ|·y²/(4a) (since a > 0). So y² ≤ 4aN/|Δ| = 4·{a}·{N}/{abs_disc}, "
            f"giving |y| ≤ {y_bound}. Symmetric bound in x: |x| ≤ {x_bound}. "
            f"(+1 padding accounts for integer rounding in math.isqrt.)"
        ),
    )

    # Step 3: brute-force enumerate the bounded rectangle [-x_bound, +x_bound] × [-y_bound, +y_bound].
    solutions: list[tuple[int, int]] = []
    for x in range(-x_bound, x_bound + 1):
        for y in range(-y_bound, y_bound + 1):
            if a * x * x + b * x * y + c * y * y == N:
                solutions.append((x, y))
    solutions.sort()
    lemma.add_step(
        operation="brute_force_enumerate",
        inputs={
            "x_range": f"[-{x_bound}, +{x_bound}]",
            "y_range": f"[-{y_bound}, +{y_bound}]",
            "candidate_count": (2 * x_bound + 1) * (2 * y_bound + 1),
        },
        output={"solutions": solutions, "count": len(solutions)},
        justification=(
            f"Scan integer rectangle x ∈ [-{x_bound}, +{x_bound}], y ∈ [-{y_bound}, +{y_bound}] "
            f"({(2*x_bound+1) * (2*y_bound+1)} candidate pairs). For each (x, y) test exact "
            f"equality {a}x² + {b}xy + {c}y² == {N}. Found {len(solutions)} integer solutions."
        ),
    )

    # Step 4: re-verify each emitted solution (defensive — catches floating-point drift if
    # the substrate is ever extended with float-coefficient variants; for pure-int math
    # this is a tautology but the audit trail is worth the cost).
    verified_count = 0
    for x, y in solutions:
        if a * x * x + b * x * y + c * y * y == N:
            verified_count += 1
    lemma.add_step(
        operation="verify_solutions",
        inputs={"emitted_count": len(solutions)},
        output={"verified_count": verified_count, "all_verified": verified_count == len(solutions)},
        justification=(
            f"Re-evaluate Q(x, y) on each of the {len(solutions)} emitted solutions; "
            f"{verified_count} of {len(solutions)} pass exact-equality check. "
            f"Tautological for pure-integer arithmetic; preserved as audit trail for "
            f"future float-coefficient extensions."
        ),
    )

    lemma.actual_value = len(solutions)

    # Invariant: solution set is closed under (x, y) → (-x, -y) — Q is a degree-2 form,
    # so Q(-x, -y) = Q(x, y) always (both signs flip and square out). Thus the solution
    # count is even unless (0, 0) is included, which only happens at N = 0 (handled above).
    # For N > 0 with non-degenerate positive-definite Q: count must be even.
    inversion_paired = all((-x, -y) in solutions for (x, y) in solutions)
    lemma.add_invariant_check(
        predicate="solution set is closed under (x, y) → (-x, -y) (form parity)",
        expected_value=True,
        actual_value=inversion_paired,
        justification=(
            "Binary quadratic forms are homogeneous degree-2: Q(-x, -y) = Q(x, y) always. "
            "So for any solution (x, y) the antipode (-x, -y) is also a solution, and "
            "the solution set is symmetric under inversion. Catches off-by-one and "
            "duplicate-emission bugs in the enumeration loop."
        ),
    )

    # Additional invariant for the symmetric subcase (a = c, b = 0): solution set is also
    # closed under (x, y) → (y, x) (axis swap), so the count is divisible by 8 unless
    # the diagonal x = y contributes fixed points (which can shift the count by ±4 at
    # most). Looser check: count must be divisible by 4 in this subcase.
    if a == c and b == 0 and N > 0:
        lemma.add_invariant_check(
            predicate="for a=c, b=0 forms: solution count divisible by 4 (sign + swap symmetry)",
            expected_value=0,
            actual_value=len(solutions) % 4,
            justification=(
                "Symmetric form x² + y² (a=c=1, b=0) admits the dihedral group D₄ on solutions: "
                "sign-flip in x, sign-flip in y, axis swap. Each orbit has size 4 or 8; "
                "totals are multiples of 4. Off-by-one bugs (e.g. boundary x = ±x_bound "
                "miscounted) typically break this."
            ),
        )

    # Cycle 10 #01a — STRONG (algorithmically-independent) predicate for the
    # canonical sum-of-two-squares case (a=1, b=0, c=1). Jacobi's formula counts
    # solutions via integer-factorization + mod-4 divisor classification — never
    # enumerates (x, y) pairs, never evaluates Q. A bound-formula bug, a
    # rectangle-scan bug, or an equation-form typo in the primary path would all
    # mismatch the Jacobi count; the form-parity / D₄ invariants above wouldn't.
    # For asymmetric or cross-term forms, no closed-form r₂-analogue exists at
    # this substrate level — those cases keep the consistency-checked invariants
    # above as best-available (see module-level note).
    if a == 1 and b == 0 and c == 1:
        jacobi_count = _two_squares_via_jacobi(N)
        lemma.add_invariant_check(
            predicate=(
                "Jacobi's two-squares formula r₂(N) = 4·(d₁(N) − d₃(N)) "
                "(algorithmically-independent STRONG verifier)"
            ),
            expected_value=jacobi_count,
            actual_value=len(solutions),
            justification=(
                f"For x² + y² = {N}: count divisors of N by residue mod 4. Found "
                f"r₂({N}) = {jacobi_count} via divisor-counting (no enumeration). "
                "Algorithm completely distinct from the geometric brute-force "
                "Lagrange-bound rectangle scan: catches bound-formula bugs, "
                "rectangle-scanning bugs, and equation-form typos that the "
                "form-parity and D₄ symmetry invariants cannot. Applies only to "
                "symmetric a=c=1, b=0 — the canonical sum-of-two-squares — "
                "because Jacobi's formula has no clean generalization to "
                "asymmetric or cross-term positive-definite forms at this "
                "substrate level (Gauss reduction or theta-series methods are "
                "cycle 11+ candidates)."
            ),
        )

    return lemma


def _classify(a: int, c: int, discriminant: int) -> str:
    """Human-readable form classification for the identify_form step's justification."""
    if discriminant < 0:
        if a > 0 and c > 0:
            return "positive-definite (Δ < 0, a > 0, c > 0) — finite solution set, decidable"
        return "negative-definite (Δ < 0, a < 0 or c < 0) — out of cycle 9 scope"
    if discriminant == 0:
        return "degenerate (Δ = 0) — factors as a repeated linear form squared, out of scope"
    return "indefinite (Δ > 0) — Pell-equation territory, infinite solution set possible, out of scope"
