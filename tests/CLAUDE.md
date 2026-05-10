# tests/

## What lives here

Pytest suite — 52 tests passing baseline (Phase 10 close).

## Why it exists

Mechanical-proof gate. Phase 10 strengthened tests on critical claims (P2): retrieve / multi-hop / contradiction / absent-answer assertions sharpened from structural-only to semantic-correctness. `test_killer_milestone.py` is the Phase 10 EXIT GATE acceptance test demonstrating all 5 capabilities (teach incrementally + resolve correction + multi-hop with citations + refuse absent + tool execution with writeback).

## Conventions

- Test files mirror source modules: `test_<module>.py`.
- Phase 10 P2 strengthened all assertions: top-1/top-5 turn_id checks, BOTH-cited multi-hop, LATEST-wins contradiction, absent-answer F1 thresholding.
- `test_killer_milestone.py` is the canonical Phase 10 close-gate. Phase 11 verdict references this file for memory-ladder rubric anchoring (memory entries probe the same 5 capabilities at varying difficulties).

## Cross-references

- Phase 11 cycle-8 verdict at `docs/artifacts/PHASE_11_BENCHMARK.md` documented memory-004/005 red findings — Phase 12+ work would add new tests for prompt-shape disambiguation (list-all vs current-preference retrieval modes).

## Last reviewed

2026-05-10 by Raphael (Phase 11 cycle 8 sweep).
