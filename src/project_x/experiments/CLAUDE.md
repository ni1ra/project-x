# src/project_x/experiments/

## What lives here

Phase 9-10 production organic stack — the live Project X engineering substrate.

## Why it exists

This is where the real work shipped. Phase 9 built the from-scratch organic encoders + semantic HDC memory + minimal agent loop. Phase 10 hardened it (fact-graph + structural retrieval + HDC binding + incremental write + Hebbian replay + killer-milestone EXIT GATE). Phase 11 (benchmark) measures what's here.

## Files

### Phase 9-10 production organic stack (live)

| File | Purpose |
|---|---|
| `semantic_hdc_memory.py` | Layer 3 — `SemanticHDCMemory` class: HDC accumulator + fact-graph (Phase 10 P3 subject indexing) + structural retrieval + HDC role-filler binding (Phase 10 #00c-2) + incremental `write_one` + `replay_consolidate` (Phase 10 P4); Phase 12 added `retrieve_structural_full_history` mode for prompt-shape disambiguation |
| `semantic_memory_agent.py` | Layer 4 — `MemoryAgent.process(text)` rule-based controller; routes write vs retrieve; template composer (NO LLM); evidence packet with cited turn IDs; absent-answer threshold gating; Phase 12 added "in order" / "list all" prompt-shape detection routing to full-history retrieval |
| `semantic_memory_dataset.py` | Phase 9 synthetic-real conversation generator + labeled query set (P1 contradiction-label fix shipped) |
| `encoder.py` | Char-n-gram + Hebbian organic encoders. From-scratch; no pretrained transformers. |
| `random_index_hebbian.py` | Hebbian co-occurrence encoder + replay consolidation extension |
| `ensemble_encoder.py` | Ensemble encoder combining char-floor + Hebbian-semantic |
| `hdc_substrate.py` | HDC primitives (bind / unbind / floor) |
| `hdc_snn_bridge.py` | SNN spike-train bridge (Phase 13+ candidate substrate) |

### HDC research experiments (Phases 4-8 — historical baselines + capacity studies)

| File | Purpose |
|---|---|
| `hdc_capacity.py` | T1 within-capacity recall + T4 capacity cliff sweep |
| `hdc_compose.py` | T2 compositional binding battery (role-filler retrieval with cleanup against candidate dictionary) |
| `hdc_continual.py` | T3 continual learning retention — write 100 random pairs over time, measure recall decay |
| `hdc_conversation_demo.py` | Indefinite-context conversability demo — HDC organic memory as conversation memory across arbitrary recall horizons |
| `hdc_vs_naive_comparison.py` | Memory-vs-accuracy trade-off quantification — HDC accumulator (fixed D) vs naive per-turn storage |
| `hopfield_lens.py` | Post-hoc Modern Hopfield Network energy-regime analysis (β-effective + energy-regime classification per cell from saved `selector_snapshot` tensors) |

### Quarantined / utility (historical control surface, NOT for organic-thesis imports)

| File | Purpose |
|---|---|
| `compressed_memory.py` | Phase 1-3 compressed-memory transformer-style architecture (historical control). DO NOT import in organic-thesis code (see `legacy/` quarantine note). |
| `tasks.py` | Task registry for `compressed_memory` experiments — `(cfg, device) -> (input_tensor, target_tensor)` callables for retrieval-property batches. Quarantine surface. |
| `util_harness.py` | Util harness from Phase 7 — pre/during/post `nvidia-smi` sampling wrapper (verifies 70-90% GPU util band per godify Phase 7 spec). Historical, GPU-only. |

## Conventions

- **NO pretrained transformer derivatives** at any layer (lain 2026-05-09 standing constraint). Inheriting GPT-Codex's pretrained-defaults caused M-PROJECTX-011; thesis-compliance check is non-negotiable on any new layer.
- **Code-comment-ratio rule** (GLOBAL POLICY) — WHY-comments justifying complex code's existence + comments preserving important info (e.g. *"strict-dominance boost +1.0 guarantees latest turn wins regardless of cosine variance — see Phase 10 P3 binding"*). Never WHAT-comments.
- **Phase 11 verdict surfaced one architectural finding here:** Phase 10's strict-dominance recency boost (in `semantic_hdc_memory.py` `_structural_cosines` / `retrieve_structural`) collapses on "list all changes" prompts. Phase 12+ candidate work area: prompt-shape disambiguation in `MemoryAgent.process` controller + `retrieve_structural_full_history` mode that bypasses dominance collapse.

## Last reviewed

2026-05-10 by Raphael (Phase 11 cycle 8 sweep).
