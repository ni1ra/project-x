# Physics rubric — Phase 11

Domain: 1st-principles physical reasoning (Newtonian → relativistic → quantum → cosmological).

## Grading mode by rank

| Rank | Difficulty | Mode | Tolerance / criteria |
|---|---|---|---|
| 1 | intro | auto-grade `numerical_close` | tolerance 0.05 (5%) |
| 2 | easy | auto-grade `numerical_close` | tolerance 0.05 |
| 3 | medium | auto-grade `numerical_close` | tolerance 0.10 (relativistic — multiple round trips) |
| 4 | hard | rubric-pending | conceptual; correctness + completeness + voice |
| 5 | frontier | rubric-pending | conceptual; honest survey of approaches + key challenges |
| 6 | unsolved | `audit_status: "ungradeable; unsolved tier"` | honesty about what's known vs unknown |

## Rubric dimensions (rubric-pending entries)

### #hard (rank 4)

- **Correctness:** equations stated correctly (Einstein field equations, Lagrangian, etc.); units consistent; sign conventions named.
- **Completeness:** all major terms identified + their physical meaning; the "why does this matter" connection drawn.
- **Voice:** Raphael's declarative analytical register; doesn't blur with textbook prose.
- **Failure modes to flag:** symbolic errors; conflating Ricci tensor with Ricci scalar; missing Λ term in EFE; treating gravity as force in a relativistic context.

### #frontier (rank 5)

- **Survey honesty:** lists genuine approaches (LQG, ST, asymptotic safety, causal sets, etc.) with their actual conceptual moves, not vibes.
- **Key challenges named:** semiclassical-limit recovery (LQG), background-dependence + landscape (ST), experimental untestability at Planck scale (all).
- **No false certainty:** doesn't claim a frontier approach is solved.
- **Voice:** Raphael acknowledging open-ness without surrendering analytical rigor.

### #unsolved (rank 6)

- **Honest framing:** what's known (the gap, the magnitude), what's unknown (mechanism), what's contested (anthropic vs unimodular vs SUSY-cancellation).
- **No confidently-wrong takes:** doesn't pretend QFT vacuum-energy IS the cosmological constant; names the fact that this identification is a category-conflation that causes the 120-orders-of-magnitude gap to look more "off" than it is.
- **Audit_status: "ungradeable; unsolved tier"** — no expected answer to check against.

## Auto-grade method (ranks 1-3)

`auto_grade.method = "numerical_close"`:
```
match = abs(actual - expected) <= max(tolerance * abs(expected), tolerance_floor)
```
- `tolerance` per-rank above
- `tolerance_floor = 0.01` for absolute small values
- `expected` is canonical answer; `actual` is parsed numeric from Raphael's response

## Last reviewed

2026-05-10 by Raphael (Phase 11 cycle 2).
