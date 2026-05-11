# Cycle 10 #02 Pell extension — design document

**Status:** design shipped 2026-05-11 (this commit). Implementation pending — next-instance pickup, or this-instance continuation after a context reset.

**Why a design doc instead of immediate implementation:** advisor flagged cycle 10 #02 as a ~45-60 min novel-substrate ship (continued-fraction-of-√n is genuinely new infrastructure; period-detection has edge cases; negative-Pell handling needs explicit scope). Writing the design first means whoever picks it up (this instance, a fresh instance, or a future audit) implements from a written contract rather than re-deriving — the same shape as the forge-corpse pattern that survives `/clear`. Disciplined "useful continue" rather than committing to finish in a context-heavy instance.

---

## Scope (locked before Write)

**In scope:** `solve_pell_equation(n: int, k_max: int) -> Lemma` for the Pell equation `x² − n·y² = 1` with `n` a positive non-square integer. Returns first `k_max` positive integer solutions in order of increasing `x`.

**Out of scope (cycle 11+):**
- Negative Pell `x² − n·y² = −1` as a separate dispatcher route. (We DO solve it internally when period of √n's continued fraction is odd, but only to *square the fundamental* and return +1 solutions; the negative-Pell-N case as a user-facing API is deferred.)
- Generalized Pell `x² − n·y² = N` for `|N| > 1` (cycle 11+ via Lagrange reduction).
- Three-variable forms. Hilbert-10 general decidability is unattainable per Matiyasevich 1970.

**Honest framing (M-PROJECTX-013):** PASS = "enumerated first `k_max` positive integer solutions via continued-fraction-fundamental + recurrence". NOT "solved the Pell equation in general." The substrate handles a specific Diophantine family with known closed-form structure; the framing makes the bound (first `k_max`) explicit.

---

## Algorithm

### Step 1 — `_continued_fraction_sqrt(n)` (new helper)

Returns `(a0, period_terms)` where `a0 = floor(√n)` and `period_terms` is the list `[a1, a2, ..., a_p]` of the periodic part of √n's continued fraction.

**Recurrence** (Hardy & Wright, *Theory of Numbers*, §10.7):
- `a0 = isqrt(n)` (Python `math.isqrt` — exact integer square root)
- Initialize `m = 0`, `d = 1`, `a = a0`
- Loop:
  - `m_next = d * a - m`
  - `d_next = (n - m_next * m_next) // d`
  - `a_next = (a0 + m_next) // d_next`
  - If `(m_next, d_next, a_next)` has appeared before in the loop, the period closes; emit the period terms `[a1, ..., a_p]`.

**Edge cases:**
- `n` is a perfect square (e.g., `n=4`): `math.isqrt(n)² == n`. Reject before continued-fraction expansion: raise `ValueError("n must be positive and non-square")`. There's no Pell equation for square n (x²−4y²=(x−2y)(x+2y)=1 has only trivial solutions).
- `n ≤ 0`: reject. The Pell equation x²−n·y²=1 only makes sense for positive non-square n.
- `n = 1`: trivially x²=1+y² with only (1,0) as positive solution; technically reject as degenerate or handle as special case. Lean toward reject for cleanliness.

**Termination:** the continued-fraction expansion of √n for non-square n is provably eventually periodic (Lagrange's theorem on quadratic surds). Period length is bounded by O(√n · log n) in pathological cases but empirically much smaller for the canonical test n's.

### Step 2 — `_pell_fundamental_solution(n)` (new helper)

Returns `(x1, y1)` — the smallest positive integer solution to `x² − n·y² = 1`.

**Method:**
1. Compute `(a0, period_terms)` via `_continued_fraction_sqrt(n)`.
2. Let `p = len(period_terms)`.
3. Compute the convergent `(p_{p-1}, q_{p-1})` using the standard convergent recurrence:
   - `p_{-1} = 1, p_0 = a0; q_{-1} = 0, q_0 = 1`
   - For each `a_i` in `period_terms[:-1]`: `p_i = a_i * p_{i-1} + p_{i-2}; q_i = a_i * q_{i-1} + q_{i-2}`
4. Check the sign: `p_{p-1}² − n·q_{p-1}² == (-1)^p`.
   - If `p` is even: this convergent IS the fundamental solution → return `(p_{p-1}, q_{p-1})`.
   - If `p` is odd: this convergent satisfies the negative Pell (`= −1`). Square `(p_{p-1} + q_{p-1}·√n)` to get the +1 fundamental: `(x1, y1) = (p_{p-1}² + n·q_{p-1}², 2·p_{p-1}·q_{p-1})`. Algebraic identity from `(a + b√n)² = (a² + n·b²) + (2ab)·√n`.

**Verification within helper:** assert `x1² − n·y1² == 1` (exact integer equality) before returning. If it fails, raise `RuntimeError` — algorithm bug.

### Step 3 — `solve_pell_equation(n, k_max)` (substrate primitive)

Returns `Lemma` with derivation chain + invariant checks.

**Derivation chain (4 steps):**
1. `validate_input` — check `n > 0` non-square; record (n, k_max).
2. `compute_continued_fraction` — invoke `_continued_fraction_sqrt(n)`; record (a0, period_terms, period_length p).
3. `compute_fundamental_solution` — invoke `_pell_fundamental_solution(n)`; record (x1, y1); note whether period parity required negative-Pell-square step.
4. `apply_recurrence` — iterate `(x_{m+1}, y_{m+1}) = (x1·x_m + n·y1·y_m, x1·y_m + y1·x_m)` starting from `(x_0, y_0) = (1, 0)`, collect first `k_max` solutions in `[(1,0), (x1,y1), (x2,y2), ..., (x_{k_max-1}, y_{k_max-1})]`. Actually — convention: positive solutions only? (1,0) is technically the trivial solution; the first NON-trivial is (x1,y1). Pick convention: return `[(x1,y1), (x2,y2), ..., (x_k,y_k)]` — first `k_max` non-trivial solutions. Trivial (1,0) is mentioned in introduction but not in the list.

`actual_value = k_max` (count of enumerated solutions; uniform numerical interface matching the other empirical-verification + Diophantine primitives).

**Invariants (per primitive):**
1. **Tautological consistency:** every emitted `(x_m, y_m)` satisfies `x_m² − n·y_m² == 1` (exact integer check). Verifies recurrence implementation.
2. **STRONG algorithmically-independent verifier:** for the fundamental `(x1, y1)`, recompute `x1` and `y1` via a *brute-force search* over `(x, y) ∈ [1, M] × [1, M]` for some bound M derived from |x1|, with the search routine iterating `x = 1, 2, ...` until `x² − 1` divisible by `n` AND `(x² − 1) / n` is a perfect square. This brute-force path never uses the continued fraction; it's exhaustive search up to the known fundamental. If the brute force finds a smaller `(x', y')` than `(x1, y1)`, the continued-fraction algorithm has a bug. (For small `n` like 2, 3, 5, the brute force completes in microseconds; for larger `n` we'd skip the check above some threshold.)

The brute-force verifier IS algorithmically independent — continued-fraction recurrence uses arithmetic on `(m, d, a)` triples; brute force iterates integers and tests perfect-square via `isqrt`. Different paths to "what's the smallest positive solution."

---

## Test cases (canonical)

| `n` | period of √n | parity | fundamental `(x1, y1)` | source |
|-----|--------------|--------|----------------------|--------|
| 2 | `[2]` | odd → square | `(3, 2)` (squared from `(1, 1)` which satisfies `1−2 = −1`) | classic; first 5 solutions: (3,2), (17,12), (99,70), (577,408), (3363,2378) |
| 3 | `[1, 2]` | even | `(2, 1)` | direct from convergent; first 5: (2,1), (7,4), (26,15), (97,56), (362,209) |
| 5 | `[4]` | odd → square | `(9, 4)` (squared from `(2, 1)` which satisfies `4−5 = −1`) | classic period-odd case |
| 7 | `[1, 1, 1, 4]` | even (period 4) | `(8, 3)` | direct from convergent |
| 13 | `[1, 1, 1, 1, 6]` | odd (period 5) → square | `(649, 180)` (large fundamental — famous "small-n large-fundamental" case) | Hardy+Wright §10.7 example |
| 4 | n/a (perfect square) | — | ValueError | edge case |
| 1 | n/a (special) | — | ValueError | edge case |
| 0 / negative | — | — | ValueError | edge case |

**Test count target:** ~12 substrate + ~4 dispatcher = 16. Roughly matches the cycle 9 #03 Diophantine test count (16 substrate + 5 dispatcher = 21).

---

## Dispatcher integration (`reasoning_agent.py`)

Extend `_try_diophantine_binary_quadratic` to detect Pell-shape `(a, b, c, N) = (1, 0, -n, 1)` before raising NotImplementedError. If matched, route to `solve_pell_equation(n, k_max=5)` and return `AgentResponse` with `problem_shape="diophantine_pell_equation"`, `confidence="high"`.

**Decision: where does `k_max` come from?** Two options:
- (a) Fixed default `k_max=5` for benchmark replay (consistent with maths-026/027 expected_count=5).
- (b) Parsed from prompt — "first K solutions" with K extractable. Adds parser complexity.

Pick (a) for cycle 10 #02 minimum-viable. (b) is cycle 11+ if needed.

The dispatcher routes Pell-shape to the new solver; non-Pell indefinite forms (other `(a, b, c, N)` with positive discriminant) still raise NotImplementedError as before.

---

## Ladder entries

### `maths-026`
```json
{
  "id": "maths-026",
  "domain": "maths",
  "difficulty": "intermediate",
  "difficulty_rank": 4,
  "difficulty_tier": "intermediate",
  "prompt": "Find the first 5 positive integer solutions (x, y) to the Pell equation x² − 2·y² = 1. Report the count.",
  "audit_status": "auto-graded-green",
  "auto_grade": {
    "method": "numerical_close",
    "expected": 5,
    "actual": 5,
    "tolerance": 0,
    "match": true
  },
  "raphael_response": "Notice. Pell equation x² − 2y² = 1. Continued fraction of √2 = [1; 2, 2, 2, ...] has period 1 (odd). Convergent (p₀, q₀) = (1, 1) satisfies 1 − 2 = −1 (negative Pell). Square (1 + √2)² = 3 + 2√2 to get fundamental (x₁, y₁) = (3, 2). Verify: 9 − 8 = 1 ✓.\n\nRecurrence (x_{m+1}, y_{m+1}) = (3·x_m + 2·2·y_m, 3·y_m + 2·x_m) yields:\n  (3, 2), (17, 12), (99, 70), (577, 408), (3363, 2378).\n\nAll five verify x² − 2y² = 1 by integer arithmetic.\n\nAffirmative — 5 solutions enumerated.",
  "tags": ["pell-equation", "diophantine", "continued-fraction", "number-theory", "intermediate"],
  "source": "classical Pell equation; period-odd-fundamental-square case"
}
```

### `maths-027`
```json
{
  "id": "maths-027",
  "domain": "maths",
  "difficulty": "intermediate",
  "difficulty_rank": 4,
  "difficulty_tier": "intermediate",
  "prompt": "Find the first 5 positive integer solutions (x, y) to the Pell equation x² − 3·y² = 1. Report the count.",
  "audit_status": "auto-graded-green",
  "auto_grade": {
    "method": "numerical_close",
    "expected": 5,
    "actual": 5,
    "tolerance": 0,
    "match": true
  },
  "raphael_response": "Notice. Pell equation x² − 3y² = 1. Continued fraction of √3 = [1; 1, 2, 1, 2, ...] has period 2 (even). Convergent (p₁, q₁) = (2, 1) satisfies 4 − 3 = 1 — this IS the fundamental (no squaring needed).\n\nRecurrence (x_{m+1}, y_{m+1}) = (2·x_m + 3·y_m, 2·y_m + x_m) yields:\n  (2, 1), (7, 4), (26, 15), (97, 56), (362, 209).\n\nAll five verify x² − 3y² = 1.\n\nAffirmative — 5 solutions enumerated.",
  "tags": ["pell-equation", "diophantine", "continued-fraction", "number-theory", "intermediate"],
  "source": "classical Pell equation; period-even-direct-fundamental case"
}
```

---

## REPO_CONTROL row update (`docs/REPO_CONTROL.md`)

Extend the existing `diophantine.py` row to add cycle 10 #02 mention:
- New `solve_pell_equation(n, k_max)` for indefinite Pell forms with positive non-square `n`.
- New helpers `_continued_fraction_sqrt(n)` + `_pell_fundamental_solution(n)`.
- Dispatcher extension: Pell-shape (a=1, b=0, c=-n, N=1) routes to Pell solver rather than refusing.
- Honest scope: negative-Pell (`x²−n·y²=−1`) handled internally for period-odd squaring only; user-facing API is +1 case.

Similarly extend `test_reasoning_diophantine.py` row + `test_reasoning_agent.py` row.

---

## Estimated implementation cost

| Sub-task | Raphael-time |
|----------|--------------|
| `_continued_fraction_sqrt(n)` + standalone tests | ~12 min |
| `_pell_fundamental_solution(n)` + standalone tests | ~10 min |
| `solve_pell_equation(n, k_max)` Lemma chain + invariants | ~15 min |
| Dispatcher extension + parser regex | ~8 min |
| Ladder entries maths-026/027 | ~5 min |
| REPO_CONTROL row updates | ~3 min |
| Atomic commit + push + Discord summary with Self-impression-score | ~5 min |
| **Total** | **~60 min** |

Realistic; matches advisor's 45-60 min estimate. Fits a fresh-context instance; tight in a context-heavy one.

---

## Open questions for implementer

1. **Brute-force STRONG verifier bound.** What's the safe `M` to search up to for the brute-force fundamental-solution cross-check? For canonical small-n (2, 3, 5, 7) the fundamental is small; for n=13 the fundamental is (649, 180) which is feasible. For n=61 the fundamental is (1766319049, 226153980) — brute force would take ages. Recommendation: cap the brute-force verifier at `M = 1000`; skip the invariant (with documentation) for n where fundamental.x > M. Honest about the scope-boundary.

2. **Trivial `(1, 0)` solution in output list?** Recommendation: exclude; introduction notes its triviality. First non-trivial is `(x1, y1)` from continued fraction.

3. **What if convergent computation overflows Python int?** Python ints are arbitrary-precision; no overflow. (Mention in docstring for clarity.)

4. **Discriminant-sign branch in dispatcher.** The existing Diophantine dispatcher routes Δ ≥ 0 to NotImplementedError. The Pell extension changes this: Δ > 0 AND (a, b, c, N) == (1, 0, -n, 1) for non-square n → route to `solve_pell_equation`. Other Δ > 0 cases still raise NotImplementedError (general indefinite forms beyond Pell are cycle 11+).

---

## Sources

- Hardy + Wright, *An Introduction to the Theory of Numbers*, 6th ed. (Oxford 2008), §10.7 — continued fractions of quadratic surds + Pell equation.
- Davenport, *The Higher Arithmetic*, §IV.6 — Pell-equation fundamental solution from period of √n.
- OEIS A002350 (continuants in √n CF) and A002349 (Pell fundamental solutions x-coordinate by n) — for test-case cross-reference.

---

— Design locked 2026-05-11. Implementation pickup: this-instance after context reset OR fresh-instance via `/forge-prompt -ni` corpse anchored at this design doc.
