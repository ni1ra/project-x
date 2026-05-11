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


# ── Cycle 10 #02 — Pell equation extension ────────────────────────────────────
#
# Brings x² − n·y² = 1 (indefinite Pell, Δ = 4n > 0) into honest scope. The form
# is indefinite — infinite solution set when n is a positive non-square integer.
# Algorithm: fundamental solution from continued-fraction expansion of √n + the
# recurrence (x_{m+1}, y_{m+1}) = (x₁·x_m + n·y₁·y_m, x₁·y_m + y₁·x_m) generates
# all subsequent solutions. Honest framing per M-PROJECTX-013: PASS = "enumerated
# first k_max positive integer solutions", NOT general Hilbert-10 decidability.
# See docs/artifacts/cycle-10-pell-design.md for the algorithm derivation +
# sources (Hardy + Wright §10.7; Davenport §IV.6).


INTRO_PELL_EQUATION = (
    "For the Pell equation x² − n·y² = 1 with n a positive non-square integer, the "
    "solution set is infinite. The continued-fraction expansion of √n is eventually "
    "periodic (Lagrange's theorem on quadratic surds); the fundamental solution "
    "(x₁, y₁) is the smallest positive (x, y) satisfying the equation, and it can "
    "be read off the period-1 convergent. If the period p of √n is even, the convergent "
    "(p_{p−1}, q_{p−1}) directly satisfies p² − n·q² = +1. If p is odd, the same "
    "convergent satisfies p² − n·q² = −1 (negative Pell); square (p + q·√n) to lift "
    "to +1: (x₁, y₁) = (p² + n·q², 2·p·q). All further solutions follow from the "
    "recurrence (x_{m+1}, y_{m+1}) = (x₁·x_m + n·y₁·y_m, x₁·y_m + y₁·x_m) starting "
    "from (x₀, y₀) = (1, 0). Honest framing: this substrate returns the first k_max "
    "solutions; the infinite Pell solution set is enumerable by recurrence but never "
    "fully materialized."
)


def _continued_fraction_sqrt(n: int) -> tuple[int, list[int]]:
    """Compute the continued-fraction expansion of √n for positive non-square n.

    Returns `(a0, period_terms)` where `a0 = floor(√n)` and `period_terms` lists
    the periodic part `[a1, a2, ..., a_p]` of the expansion. The continued
    fraction of √n is eventually periodic by Lagrange's theorem on quadratic surds.

    Algorithm (Hardy + Wright, *Theory of Numbers* §10.7): recurrence on triples
    (m_k, d_k, a_k):
        m_{k+1} = d_k · a_k − m_k
        d_{k+1} = (n − m_{k+1}²) / d_k         (always integer for √n CF)
        a_{k+1} = (a₀ + m_{k+1}) // d_{k+1}
    Period closes the first time (m_{k+1}, d_{k+1}) repeats — the (a_k) sequence
    after that point is identical to its earlier history.

    Raises ValueError for n ≤ 1 or perfect-square n. Hand-rolled stdlib `math.isqrt`
    only (exact integer square root; no floating-point error).
    """
    if n <= 1:
        raise ValueError(
            f"continued fraction of √n requires n ≥ 2; got n = {n}. "
            f"n=0 and n=1 are degenerate (√0=0, √1=1); negative n is non-real."
        )
    a0 = math.isqrt(n)
    if a0 * a0 == n:
        raise ValueError(
            f"n = {n} is a perfect square (√n = {a0}); continued fraction is "
            f"the trivial [{a0}] with no periodic part. Pell equation x² − {n}·y² = 1 "
            f"reduces to a linear-form difference (x − {a0}·y)(x + {a0}·y) = 1 with "
            f"only trivial integer solutions."
        )

    period_terms: list[int] = []
    m, d, a = 0, 1, a0
    seen_states: dict[tuple[int, int], int] = {}
    # Bound: period ≤ 2·a0·n (very loose; in practice << this); add safety cap.
    safety_max_iter = max(1000, 4 * a0 * a0)
    for _ in range(safety_max_iter):
        m_next = d * a - m
        d_next = (n - m_next * m_next) // d
        a_next = (a0 + m_next) // d_next
        state = (m_next, d_next)
        if state in seen_states:
            # Period closed at the first repeated (m, d) state. The period_terms
            # accumulated so far IS the periodic part (since (m, d) determines a uniquely
            # given a0).
            return a0, period_terms
        seen_states[state] = len(period_terms)
        period_terms.append(a_next)
        m, d, a = m_next, d_next, a_next
    raise RuntimeError(
        f"continued fraction of √{n} did not close within {safety_max_iter} iterations — "
        f"period bound exceeded; algorithm bug or pathological n."
    )


def _pell_fundamental_solution(n: int) -> tuple[int, int]:
    """Compute the fundamental (smallest positive) solution (x₁, y₁) to x² − n·y² = 1.

    Uses `_continued_fraction_sqrt(n)` to get (a0, period_terms); computes the
    convergent (p_{p−1}, q_{p−1}) via the standard recurrence p_k = a_k·p_{k−1} + p_{k−2},
    q_k = a_k·q_{k−1} + q_{k−2} starting from (p_{−1}, p_0, q_{−1}, q_0) = (1, a0, 0, 1).
    If the period p is even, this convergent IS the fundamental solution
    (p² − n·q² = +1). If p is odd, the convergent satisfies p² − n·q² = −1 (negative
    Pell); square (p + q·√n) algebraically to lift to +1 via the identity
    (p + q·√n)² = (p² + n·q²) + (2·p·q)·√n.

    Returns (x₁, y₁) with x₁² − n·y₁² == 1 exactly (verified before return).
    Raises ValueError for n ≤ 1 or perfect-square n (via the helper).
    Raises RuntimeError if the algorithm produces an invalid fundamental (would
    indicate a bug in the convergent recurrence or the period-parity branch).
    """
    a0, period_terms = _continued_fraction_sqrt(n)
    period_length = len(period_terms)

    # Compute convergent (p_{p-1}, q_{p-1}) via the standard recurrence. Process
    # a0 followed by period_terms[0..p-2] (i.e., the first period_length terms total
    # including a0); convergent index p-1 corresponds to the (period_length)-th term
    # in 0-indexed convergent numbering. Concretely: build convergents indexed 0..p-1
    # where convergent 0 uses a0 only (p_0 = a0, q_0 = 1) and each subsequent uses
    # the next period term.
    p_prev, p_curr = 1, a0
    q_prev, q_curr = 0, 1
    for i in range(period_length - 1):
        a_i = period_terms[i]
        p_prev, p_curr = p_curr, a_i * p_curr + p_prev
        q_prev, q_curr = q_curr, a_i * q_curr + q_prev
    p, q = p_curr, q_curr

    # Verify the convergent satisfies p² − n·q² == ±1.
    discriminant_signed = p * p - n * q * q
    if discriminant_signed == 1:
        x1, y1 = p, q
    elif discriminant_signed == -1:
        # Period odd → square (p + q·√n) to lift to +1 fundamental.
        x1 = p * p + n * q * q
        y1 = 2 * p * q
    else:
        raise RuntimeError(
            f"Pell fundamental algorithm produced convergent ({p}, {q}) with "
            f"p² − n·q² = {discriminant_signed}; expected ±1. Period parity mismatch "
            f"or convergent-recurrence bug (n={n}, period_length={period_length})."
        )

    # Integer-equality verification (no float). Raise if substrate is broken.
    if x1 * x1 - n * y1 * y1 != 1:
        raise RuntimeError(
            f"Pell fundamental ({x1}, {y1}) does not satisfy x² − {n}·y² = 1 "
            f"(got {x1*x1 - n*y1*y1}). Algorithm bug."
        )
    return x1, y1


def _pell_brute_force_fundamental(n: int, max_x: int = 1000) -> tuple[int, int] | None:
    """Brute-force search for the Pell fundamental over x ∈ [1, max_x].

    Algorithmically independent from the continued-fraction path: iterates x and
    tests whether (x² − 1) is exactly divisible by n AND the quotient is a perfect
    square. The first (x, y) found is the fundamental — Pell solutions are ordered
    by x. Returns None if no solution found within bound (fundamental.x > max_x).

    Used as the STRONG cross-check on `_pell_fundamental_solution`. The two paths
    share NO computation beyond Python integer arithmetic; a bug in one would NOT
    propagate to the other.
    """
    for x in range(1, max_x + 1):
        diff = x * x - 1
        if diff % n != 0:
            continue
        y_squared = diff // n
        y = math.isqrt(y_squared)
        if y * y == y_squared and y > 0:
            return x, y
    return None


def solve_pell_equation(
    n: int, k_max: int = 5, lemma_id: str = "solve_pell_equation",
) -> Lemma:
    """Enumerate the first `k_max` positive integer solutions to x² − n·y² = 1.

    Pell equation for positive non-square integer n. The trivial solution (1, 0) is
    excluded from the returned list (mentioned in introduction); first non-trivial
    is the fundamental (x₁, y₁) read off the continued-fraction expansion of √n.
    All subsequent solutions follow from the recurrence (x_{m+1}, y_{m+1}) =
    (x₁·x_m + n·y₁·y_m, x₁·y_m + y₁·x_m) iterated from (x₀, y₀) = (x₁, y₁).

    Returns Lemma with 4-step derivation chain (validate_input → compute_continued_fraction
    → compute_fundamental_solution → apply_recurrence) + per-solution tautological
    invariant (every emitted (x_m, y_m) satisfies x² − n·y² = 1) + STRONG algorithmically-
    independent verifier on the fundamental via brute-force search (cap M=1000; skipped
    with documented scope-boundary if fundamental.x > M).

    Raises ValueError for n ≤ 1 or perfect-square n (via helpers). Honest framing:
    PASS = enumerated first k_max solutions; the infinite solution set is enumerable
    by recurrence but never fully materialized at this substrate level.
    """
    if k_max < 1:
        raise ValueError(f"k_max must be ≥ 1 (got {k_max}); zero solutions is degenerate.")

    lemma = Lemma(
        id=lemma_id,
        claim=(
            f"Enumerate the first {k_max} positive integer solutions to x² − {n}·y² = 1 "
            f"(Pell equation) via continued-fraction fundamental + recurrence."
        ),
        verification_method="numerical_close",
        tolerance=0,
    )
    lemma.add_introduction(INTRO_PELL_EQUATION)

    # Step 1: validate input. Defer ValueError raises to helpers; if we get here, n is
    # in valid range — but record the validation in the proof chain for audit trail.
    lemma.add_step(
        operation="validate_input",
        inputs={"n": n, "k_max": k_max},
        output="positive non-square integer n; k_max ≥ 1",
        justification=(
            f"Pell equation x² − {n}·y² = 1 is solvable iff n > 0 is non-square. "
            f"For n = {n}: not a perfect square (verified by _continued_fraction_sqrt "
            f"in step 2). k_max = {k_max} ≥ 1 OK."
        ),
    )

    # Step 2: continued-fraction expansion of √n.
    a0, period_terms = _continued_fraction_sqrt(n)
    period_length = len(period_terms)
    lemma.add_step(
        operation="compute_continued_fraction",
        inputs={"n": n},
        output={"a0": a0, "period_terms": period_terms, "period_length": period_length},
        justification=(
            f"√{n} = [{a0}; {', '.join(map(str, period_terms))}] — period {period_length}. "
            f"Computed via the Hardy+Wright (m, d, a) recurrence on triples; period closes "
            f"the first time the (m, d) state repeats."
        ),
    )

    # Step 3: fundamental solution from convergent (period-parity branch).
    x1, y1 = _pell_fundamental_solution(n)
    parity_note = "even — convergent directly satisfies p² − n·q² = +1" if period_length % 2 == 0 \
        else "odd — convergent satisfies p² − n·q² = −1, squared (p + q·√n) to lift to +1"
    lemma.add_step(
        operation="compute_fundamental_solution",
        inputs={"a0": a0, "period_terms": period_terms},
        output={"x1": x1, "y1": y1, "period_parity": "even" if period_length % 2 == 0 else "odd"},
        justification=(
            f"Convergent (p_{{p−1}}, q_{{p−1}}) computed via standard recurrence "
            f"p_k = a_k·p_{{k−1}} + p_{{k−2}}, q_k = a_k·q_{{k−1}} + q_{{k−2}} starting "
            f"from (1, a0; 0, 1). Period parity {period_length % 2 and 'odd' or 'even'}: "
            f"{parity_note}. Fundamental (x₁, y₁) = ({x1}, {y1}); verify "
            f"{x1}² − {n}·{y1}² = {x1*x1 - n*y1*y1} = 1 ✓."
        ),
    )

    # Step 4: apply recurrence (x_{m+1}, y_{m+1}) = (x₁·x_m + n·y₁·y_m, x₁·y_m + y₁·x_m).
    solutions: list[tuple[int, int]] = []
    x_m, y_m = x1, y1
    for _ in range(k_max):
        solutions.append((x_m, y_m))
        x_next = x1 * x_m + n * y1 * y_m
        y_next = x1 * y_m + y1 * x_m
        x_m, y_m = x_next, y_next
    lemma.add_step(
        operation="apply_recurrence",
        inputs={"x1": x1, "y1": y1, "n": n, "k_max": k_max},
        output={"solutions": solutions, "count": len(solutions)},
        justification=(
            f"Iterate (x_{{m+1}}, y_{{m+1}}) = ({x1}·x_m + {n}·{y1}·y_m, "
            f"{x1}·y_m + {y1}·x_m) starting from (x_0, y_0) = (x_1, y_1) = ({x1}, {y1}). "
            f"First {k_max} solutions: {solutions}. All satisfy x² − {n}·y² = 1 by "
            f"the multiplicative structure of Z[√{n}]: (x_m + y_m·√{n}) = (x_1 + y_1·√{n})^m."
        ),
    )

    lemma.actual_value = len(solutions)

    # Invariant 1 (tautological): every emitted (x, y) satisfies x² − n·y² = 1.
    # Re-verify on each solution; integer arithmetic, exact equality.
    all_satisfy = all(x * x - n * y * y == 1 for x, y in solutions)
    lemma.add_invariant_check(
        predicate="every emitted (x_m, y_m) satisfies x² − n·y² = 1 (recurrence consistency)",
        expected_value=True,
        actual_value=all_satisfy,
        justification=(
            "Re-evaluate x² − n·y² on each of the k_max solutions; all must equal 1 exactly. "
            "Tautological under correct recurrence implementation; catches index errors or "
            "arithmetic typos in the iteration loop."
        ),
    )

    # Invariant 2 (STRONG, algorithmically-independent): brute-force search for the
    # fundamental over [1, M] with M=1000 cap. If x1 ≤ M, brute force MUST find the
    # same (x1, y1). If x1 > M, skip with documented scope-boundary — Pell fundamentals
    # for some n grow large (n=61 has fundamental x = 1766319049); the cap is honest.
    if x1 <= 1000:
        brute_force = _pell_brute_force_fundamental(n, max_x=1000)
        if brute_force is None:
            raise RuntimeError(
                f"Brute force found no Pell fundamental for n={n} within [1, 1000], "
                f"but CF algorithm produced ({x1}, {y1}). Algorithm disagreement — bug."
            )
        bf_x, bf_y = brute_force
        lemma.add_invariant_check(
            predicate=(
                "brute-force fundamental search over x ∈ [1, 1000] == continued-fraction "
                "fundamental (algorithmically-independent STRONG verifier)"
            ),
            expected_value=(x1, y1),
            actual_value=(bf_x, bf_y),
            justification=(
                f"Brute force iterates x = 1, 2, ... checking (x² − 1) % n == 0 AND "
                f"(x² − 1)/n is a perfect square; the first match is the Pell fundamental "
                f"(solutions are ordered by x). Found ({bf_x}, {bf_y}); CF method "
                f"produced ({x1}, {y1}). Two completely different algorithms — brute "
                f"force never uses continued fractions; CF never iterates by x. "
                f"Disagreement would mean one of them has a bug."
            ),
        )
    else:
        lemma.add_invariant_check(
            predicate=(
                "brute-force fundamental verifier SKIPPED (fundamental.x > M=1000; "
                "documented scope-boundary per cycle 10 #02 design)"
            ),
            expected_value="skipped",
            actual_value="skipped",
            justification=(
                f"Fundamental x₁ = {x1} exceeds the M=1000 brute-force cap. Skipping the "
                f"STRONG verifier honestly rather than running an O({x1}) loop. Pell "
                f"fundamentals for some n grow large (n=61 has x₁ = 1766319049 — "
                f"~2×10⁹ iterations would be unacceptable). The tautological invariant "
                f"(every emitted solution satisfies x² − n·y² = 1 by direct check) is "
                f"the best-available cross-check at large-fundamental n. Cycle 11+ "
                f"candidates for a scalable STRONG verifier: minimality proof via "
                f"convergent ordering theorem (every Pell solution is a convergent of √n)."
            ),
        )

    return lemma
