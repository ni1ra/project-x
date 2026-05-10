# gpt-codex/runs/

## What lives here

Per-run aggregate result JSONs. Each phase's runs are stamped with a run_id.

## Conventions

- One subdirectory per run; convention: `<phase>_<descriptor>_<seed-or-runid>/`.
- Each run dir contains a `result.json` (config + metrics + samples), and may contain `scratch_*.txt` or per-seed `result_seed*.json` aggregations.
- Frozen per-phase: once a phase's run is finalized in a verdict (`docs/artifacts/PHASE_*.md`), don't mutate the run dir.

## Phase 11 note

Phase 11 was a benchmark run (not a training run). Its results live at `gpt-codex/benchmark/<domain>/ladder.jsonl` + `audit_log.jsonl` rather than under `runs/`. Future Phase 12+ training-loop work would write run results here per the existing convention.

## Last reviewed

2026-05-10 by Raphael (Phase 11 cycle 8 sweep).
