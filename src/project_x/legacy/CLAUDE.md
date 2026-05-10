# src/project_x/legacy/

## What lives here

Phase 1-6 transformer-style scaffolding. **HISTORICAL CONTROL — DO NOT IMPORT in organic-thesis code.**

## Why it exists

Phase 1-6 explored compressed-memory architectures using transformer-derived attention + self-attention scaffolding. Lain's 2026-05-09 standing-constraint disqualifies pretrained transformer derivatives at any layer, but the Phase 1-6 *original code* is preserved here as a historical control for cross-phase comparisons. Quarantine maintained per Phase 10 P6.

## Files

| File | Purpose |
|---|---|
| `transformer_scaffolding.py` | Phase 1-6 transformer-style scaffolding (was at `src/project_x/model.py` until P6 quarantine) |

## Conventions

- **NEVER import this module in `experiments/` or any organic-thesis code.** Smoke-test imports updated to point here at P6 quarantine.
- The module-level docstring repeats this warning. If a future cycle's code accidentally re-imports `legacy.*` from organic stack, that's M-PROJECTX-011-style inheritance-by-default and should be reverted.
- **Torch is an OPTIONAL `[legacy]` extra in `pyproject.toml`** (audit-C2). The live organic stack does NOT depend on torch; install with `pip install -e .[legacy]` to run `transformer_scaffolding.py` / `experiments/compressed_memory.py` / `experiments/tasks.py` / `smoke.py`. Tests `test_smoke.py` + `test_compressed_memory.py` pytest.importorskip on torch so a torch-free install runs the active suite cleanly.

## Cross-quarantine surface (audit-C2 — do NOT import these in organic-thesis code either)

| File | Why it's also quarantined |
|---|---|
| `experiments/compressed_memory.py` | Phase 1-3 transformer-style historical control. Module docstring carries the same DO-NOT-IMPORT warning. |
| `experiments/tasks.py` | Task registry exclusively for `compressed_memory` experiments. Torch-dependent. |
| `smoke.py` (root of `src/project_x/`) | Smoke entry-point exercising legacy `ProjectXModel`. |

## Last reviewed

2026-05-10 by Raphael (audit-fix run; audit-C2 quarantine hardening).
