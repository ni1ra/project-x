# Project X

Post-transformer organic memory + agent stack. From-scratch HDC (hyperdimensional
computing) + Hebbian co-occurrence encoders, semantic memory with fact-graph +
structural retrieval, rule-based agent controller. **No pretrained transformer
derivatives** at any layer (no BGE / MiniLM / sentence-transformers / llama.cpp /
Qwen / Mistral); encoders + generators stay from-scratch organic per lain's
standing constraint (2026-05-09).

The repository is organized around three durable surfaces:

- `ref/`: public reference material, source manifests, and downloaded papers.
- `docs/`: implementation plans and operational next steps.
- `src/project_x/`: runnable research harness — Phase 9-10 production organic
  stack lives in `experiments/`; Phase 1-6 transformer-style historical control
  is quarantined in `legacy/` (DO NOT import in organic-thesis code).

This project treats public frontier model reports and papers as reference data
only. The implementation target is intentionally novel: a small, measurable
harness first, then increasingly hard architecture experiments with evidence
artifacts. Current state: Phase 11 (Raphael Domain Benchmark Suite) + Phase 12
(retrieval-mode disambiguation) closed; full benchmark at 11 green / 0 red /
21 rubric-pending / 4 ungradeable across 36 entries.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m project_x.smoke
pytest
```

## Key Artifacts

- `docs/A_TO_Z_PLAN.md`
- `docs/DO_THIS_NEXT.md`
- `ref/SOURCE_MANIFEST.md`
- `ref/sources.json`

