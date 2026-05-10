# tests/

## What lives here

Pytest suite — **58 tests passing** (Phase 12 close: 52 Phase 10/11 baseline + 6 Phase 12 retrieval-mode tests).

## Why it exists

Mechanical-proof gate. Phase 10 strengthened tests on critical claims (P2): retrieve / multi-hop / contradiction / absent-answer assertions sharpened from structural-only to semantic-correctness. `test_killer_milestone.py` is the Phase 10 EXIT GATE acceptance test demonstrating all 5 capabilities (teach incrementally + resolve correction + multi-hop with citations + refuse absent + tool execution with writeback). `test_retrieval_modes.py` (Phase 12 #00P12-tests, cycle 4) guards the retrieval-mode disambiguation seam — list-all / summarize-trajectory queries route to chronological full-history retrieval; current-preference queries stay on the strict-dominance latest-wins path.

## Conventions

- Test files mirror source modules: `test_<module>.py`.
- Phase 10 P2 strengthened all assertions: top-1/top-5 turn_id checks, BOTH-cited multi-hop, LATEST-wins contradiction, absent-answer F1 thresholding.
- `test_killer_milestone.py` is the canonical Phase 10 close-gate. Phase 11 verdict references this file for memory-ladder rubric anchoring (memory entries probe the same 5 capabilities at varying difficulties).
- `test_retrieval_modes.py` is the canonical Phase 12 close-gate. Each test docstring explains WHY it exists (which Phase 11 finding it probes / which regression it guards) per lain GLOBAL POLICY 2026-05-10 comment-ratio rule.

## File inventory

| File | Phase | Purpose |
|---|---|---|
| `test_compressed_memory.py` | 1-3 | Compressed-memory architecture |
| `test_encoder.py` | 9 | Char-n-gram + Hebbian organic encoders |
| `test_random_index_hebbian.py` | 9 | Hebbian co-occurrence encoder |
| `test_semantic_hdc_memory.py` | 9-10 | Layer 3 HDC memory + structural retrieval |
| `test_semantic_memory_agent.py` | 9-10 | Layer 4 agent loop + run_tool + replay |
| `test_semantic_memory_dataset.py` | 9 | Synthetic-real dataset gen |
| `test_killer_milestone.py` | 10 | EXIT GATE — 5 capabilities |
| `test_retrieval_modes.py` | 12 | Retrieval-mode disambiguation regression guard (6 tests) |
| `test_smoke.py` | (ongoing) | Smoke entrypoint |

## Cross-references

- Phase 12 closed memory-004/005 red findings via `retrieve_structural_full_history` + `_LIST_ALL_HINTS` classifier; tests live in `test_retrieval_modes.py` and probe the same fixtures as memory-004/005 ladder entries
- `docs/artifacts/PHASE_11_BENCHMARK.md` Phase 12 closure addendum documents the architectural seam closed
- `docs/artifacts/PHASE_12_RETRIEVAL_DISAMBIGUATION.md` (cycle 7) lands the verdict markdown

## Last reviewed

2026-05-10 by Raphael (Phase 12 cycle 5 — godify-app APOTHEOSIS pickup run).
