# Maths rubric — Phase 11

Domain: abstraction + proof — algebra → linear → complex → Galois → topology → Riemann.

## Grading mode by rank

| Rank | Difficulty | Mode | Tolerance / criteria |
|---|---|---|---|
| 1 | intro (basic algebra) | auto-grade `numerical_close` or `symbolic_match` | tolerance 0.01 |
| 2 | easy (linear algebra) | auto-grade `numerical_close` or `symbolic_match` | tolerance 0.01 |
| 3 | medium (complex analysis) | auto-grade `numerical_close` (specific computation) OR rubric-pending (proof-shape) | mixed |
| 4 | hard (Galois theory) | rubric-pending (proof-shape) | argument + correctness + voice |
| 5 | frontier (algebraic topology) | rubric-pending | proof-shape + structural insight |
| 6 | unsolved (Riemann hypothesis) | `audit_status: "ungradeable; unsolved tier"` | honest survey |

## Rubric dimensions (rubric-pending entries)

### Proof-shape grading

- **Correctness:** every step of the argument is valid given prior steps; no hidden assumptions.
- **Completeness:** the argument covers the claim's quantifiers fully; edge cases addressed.
- **Structural insight:** does the proof reveal *why* the result holds, or just verify it? Bonus for the former.
- **Voice:** Raphael declarative, doesn't blur with Wikipedia-paraphrase prose.

### #unsolved (rank 6 — Riemann)

- **Honest framing:** what's the conjecture, what's the evidence (numerical to the nth zero, partial-result density), what approaches have failed (or are open).
- **No false claim of resolution.**

## Auto-grade method

For numerical: `numerical_close` with tolerance 0.01.
For symbolic: `symbolic_match` — canonicalize Raphael's expression (using sympy if available; else string-match on canonical form) against expected.

## Last reviewed

2026-05-10 by Raphael (Phase 11 cycle 2 — domain ladder ships cycle 3).
