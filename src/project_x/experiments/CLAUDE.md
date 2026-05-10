# src/project_x/experiments/

## What lives here

Phase 9-10 production organic stack — the live Project X engineering substrate.

## Why it exists

This is where the real work shipped. Phase 9 built the from-scratch organic encoders + semantic HDC memory + minimal agent loop. Phase 10 hardened it (fact-graph + structural retrieval + HDC binding + incremental write + Hebbian replay + killer-milestone EXIT GATE). Phase 11 (benchmark) measures what's here.

## Files

| File | Purpose |
|---|---|
| `semantic_hdc_memory.py` | Layer 3 — `SemanticHDCMemory` class: HDC accumulator + fact-graph (Phase 10 P3 subject indexing) + structural retrieval + HDC role-filler binding (Phase 10 #00c-2) + incremental `write_one` + `replay_consolidate` (Phase 10 P4) |
| `semantic_memory_agent.py` | Layer 4 — `MemoryAgent.process(text)` rule-based controller; routes write vs retrieve; template composer (NO LLM); evidence packet with cited turn IDs; absent-answer threshold gating |
| `semantic_memory_dataset.py` | Phase 9 synthetic-real conversation generator + labeled query set (P1 contradiction-label fix shipped) |
| `encoder.py` | Char-n-gram + Hebbian organic encoders. From-scratch; no pretrained transformers. |
| `random_index_hebbian.py` | Hebbian co-occurrence encoder + replay consolidation extension |
| `ensemble_encoder.py` | Ensemble encoder combining char-floor + Hebbian-semantic |
| `hdc_substrate.py` | HDC primitives (bind / unbind / floor) |
| `hdc_snn_bridge.py` | SNN spike-train bridge (Phase 12+ candidate substrate) |
| `compressed_memory.py` | Phase 1-3 compressed-memory architecture (historical) |
| `generator_client.py` | Mock/local-LLM boundary (template composer is the live path) |
| `phase9_report.py` | Phase 9 aggregation helper |

## Conventions

- **NO pretrained transformer derivatives** at any layer (lain 2026-05-09 standing constraint). Inheriting GPT-Codex's pretrained-defaults caused M-PROJECTX-011; thesis-compliance check is non-negotiable on any new layer.
- **Code-comment-ratio rule** (GLOBAL POLICY) — WHY-comments justifying complex code's existence + comments preserving important info (e.g. *"strict-dominance boost +1.0 guarantees latest turn wins regardless of cosine variance — see Phase 10 P3 binding"*). Never WHAT-comments.
- **Phase 11 verdict surfaced one architectural finding here:** Phase 10's strict-dominance recency boost (in `semantic_hdc_memory.py` `_structural_cosines` / `retrieve_structural`) collapses on "list all changes" prompts. Phase 12+ candidate work area: prompt-shape disambiguation in `MemoryAgent.process` controller + `retrieve_structural_full_history` mode that bypasses dominance collapse.

## Last reviewed

2026-05-10 by Raphael (Phase 11 cycle 8 sweep).
