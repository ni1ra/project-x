# docs/artifacts/

## What lives here

Phase verdicts + frozen research notes. Each artifact represents the empirical-state-of-the-project at a point in time.

## Files (post-Phase-12 inventory)

| File | Phase / topic |
|---|---|
| `PHASE_7_HOPFIELD_LENS.md` | Phase 7 — Hopfield lens proof |
| `PHASE_8_HDC_ORGANIC_MEMORY.md` | Phase 8 — random-symbol HDC baseline (99.25% recall at D=50000) |
| `PHASE_8_HOSTILE_REVIEW.md` | Phase 8 hostile review |
| `PHASE_9_PICK_ONE_VERDICT.md` | Phase 9 pick-one verdict + ADDENDUM (lain organic-only constraint, 2026-05-09) |
| `PHASE_9_SEMANTIC_HDC_MEMORY.md` | Phase 9 verdict + Phase 10 closure addenda |
| `PHASE_9_SHRINE_COUNCIL_HEBBIAN.md` | Council reasoning (Plate dossier especially relevant for Phase 10 P3 fact-graph) |
| `PHASE_11_BENCHMARK.md` | **Phase 11 verdict** — Raphael Domain Benchmark Suite, 36 entries; closed at 9 green / 2 red / 21 rubric-pending / 4 ungradeable; **Phase 12 closure addendum at bottom** moves memory-ladder reds (memory-004 / memory-005) → green (full benchmark now 11 green / 0 red / 21 rubric-pending / 4 ungradeable) |
| `PHASE_12_RETRIEVAL_DISAMBIGUATION.md` | **Phase 12 verdict** — retrieval-mode disambiguation (`retrieve_structural_full_history` mode + "in order" / "list all" prompt-shape detection in `MemoryAgent.process` controller); closed both Phase 11 memory-ladder reds at commit `8d734e3` |
| `PHASE_13_CANDIDATES.md` | **Phase 13 framing inputs** (lain-gated, NOT current-run contract) — inventoried candidate work-shapes for the next phase: retrieval telemetry, snapshot/restore protocol, adversarial memory matches, from-scratch symbolic generator, binding-algebra bakeoff |
| `COUNCIL_A_ENCODER.md` ... `COUNCIL_H_BEYOND_HUMAN_CAP.md` | Phase 9 council deliberations across 8 architectural axes |
| `DISCORD_BRIEF_RAPHAEL_ROADMAP.md` | Discord brief on Raphael roadmap |
| `RESEARCH_NOTE.md`, `ROADMAP_TO_RAPHAEL.md`, `SHRINE_COUNCIL_PHASE_8.md` | Older research notes |
| `T4_bit_accuracy_curve.png`, `T4_capacity_curve.png`, `T4_cliff_vs_D.png`, `T4_dscaling_curves.png` | Phase 4 figures (bit-accuracy, capacity, cliff, D-scaling) |

## Conventions

- Artifacts are FROZEN per phase. Once a phase's verdict markdown lands here, subsequent edits are ADDENDA at the bottom (per Phase 9 / Phase 10 / Phase 11 pattern), not rewrites.
- Phase 11 verdict (`PHASE_11_BENCHMARK.md`) carries a Phase 12 closure addendum at the bottom — the original 9/2/21/4 verdict is preserved; the addendum documents the memory-004/005 red→green flip via Phase 12's retrieval-mode disambiguation. Future addenda follow the same append pattern.
- Phase 13 candidates artifact (`PHASE_13_CANDIDATES.md`) is an INPUT for lain's framing decision — NOT a verdict. It does not get addenda; it gets superseded by `A_TO_Z_PLAN.md` once Phase 13 is framed.

## Last reviewed

2026-05-10 by Raphael (post-Phase-12 GPT-audit-fix run).
