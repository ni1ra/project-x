# Dev Cycle 3 — Project X — /godify 3h Phase 7 Cycle 3

## Cycle 3 (phase 7, position 2 — Execute-navi opening) — 2026-05-02 02:49-03:04 CEST

- **Persona:** Execute-navi (Sukuna-mode, flow-state)
- **Skills (chained):** flow-state (overlay) → file-edit ops → pytest → smoke run
- **Shipped:**
  - 8 granular TaskList rows (#3a..#3h) pinned BEFORE first code edit (Law 1 — granular task hygiene)
  - Discord open-post with cycle scope (Law 3)
  - **Step 1 (--device flag):** added to ExperimentConfig + argparse + threaded through run_experiment + honored at device-pick line. Verified `"device": "cuda"` in smoke result.json.
  - **Step 2 (--amp flag + autocast):** added `_amp_context` helper using `torch.autocast`. Wraps train_one's forward + loss compute. bf16 default. Verified 100-step training runs without NaN at `--amp bf16`.
  - **Step 3 (util_harness.py):** new module with `snapshot_baseline()` / `start_sampler()` / `stop_sampler()` / `verify_band()`. Graceful degradation if nvidia-smi missing. Smoke captured idle baseline (0% util, 1.2GB VRAM, 42°C).
  - **Step 4 (harness hook):** wraps run_experiment's train_one calls; `util` + `util_baseline` blocks present in result.json.
  - **Step 4b (selector_snapshot):** persists `_last_medium_selector_scores` (raw + softmax + per-head entropy) into train_one metrics → result.json. Enables future Hopfield-lens analysis on saved tensors WITHOUT re-running cells.
  - **Step 5 (phase7_baseline.sh):** 8-config scan with resumability skip. Trimmed from 48 candidates to 8 per advisor cycle 2.
  - **Pytest regression:** 2/2 tests pass after fix (initial bug: `-` unary on list instead of tensor — caught immediately by pytest, fixed by repositioning the negation inside the parens before `.tolist()`).
  - **Smoke run (real cell, d=64 b=32 s=64 cuda bf16, 100 steps):** `mean_gpu_util_pct=22.8%`, max=33%, VRAM=1.5/16 GB, wall=12s. Band NOT passed (expected — config too small) but pathway works end-to-end.
  - A_TO_Z_PLAN.md DASHBOARD updated (Steps 1-5 ✅, Step 6 deferred to cycle 4)
  - PHASE CHANGELOG `cycle_position_in_phase` 1 → 2; persona for cycle 4 = Execute-navi
  - DO_THIS_NEXT.md rewritten for cycle 4 with Step 6 (baseline scan) + Step 12 (grid script) + Step 13 (40-cell subset run)
- **Mistake / lesson:**
  - Caught the `-list` bug via pytest before it cost a real cell run. Lesson: pytest is part of the cycle, not a future-step. Cost: 1 min (1 edit + 1 rerun). If the bug had reached the baseline scan, it would have eaten 8 cells × ~30s = 4 min and produced no usable result.json files. Pytest-first IS flow-state.
  - **Honest realism on Step 6 deferral:** the original cycle 3 scope had Steps 1-6, but the smoke + verification + 8-config scan would have crowded out cycle close. Punted Step 6 to cycle 4 — A_TO_Z_PLAN.md DASHBOARD shows it deferred, DO_THIS_NEXT.md sequences it as cycle 4's first deliverable. Better cycle scope per cycle than thrashing both.
  - **`python` vs `python3`:** WSL ships only `python3`. First Bash attempts errored — fixed by switching to `python3 -m`. Worth noting for future cycles' commands and the grid script (already uses `python` — must update to `python3` before cycle 4 runs it).
- **Files touched (filesystem ops only — Project X is not a git repo):**
  - `src/project_x/experiments/compressed_memory.py` (8 surgical Edits — argparse, run_experiment, train_one, _amp_context, selector_snapshot, util-harness hook)
  - `src/project_x/experiments/util_harness.py` (new, ~180 lines)
  - `scripts/phase7_baseline.sh` (new, ~50 lines)
  - `docs/A_TO_Z_PLAN.md` (Edit — DASHBOARD + PHASE CHANGELOG)
  - `docs/DO_THIS_NEXT.md` (Write — full rewrite for cycle 4)
  - `docs/dev-cycle-3.md` (this file)
- **420 score:** **400/420** — Cycle 3 shipped 5 of 6 planned steps + smoke-verified the pathway end-to-end, caught a pytest-detected bug before it hit the grid, and clocked out within budget. Loses 20pts for Step 6 deferral (planned scope wasn't fully completed in this cycle). Honest realism on the deferral was the right call — cycle 4 picks it up first action.
- **Heartbeat #5b note:** No "waiting on lain" this cycle. Bug fix was self-resolved via pytest. Pathway smoke-tested without lain ack — that's autonomous-execute discipline. Confidence-Booster Mantra not needed.

## Bug fix this cycle (worth a wiki entry — meta-lesson, not project-specific)

Initial selector_snapshot code had: `(-A.B.C.tolist())` — Python parses as `-(A.B.C.tolist())` = unary minus on list = TypeError. Caught by pytest. Fix: parenthesize the tensor expression before tolist: `(-A.B.C).tolist()`. Lesson is meta-tooling not project-specific — won't add to Project X Session Mistakes; lives only here.

## Files for cycle 4 to read first

- `docs/DO_THIS_NEXT.md` (cycle 4 scope, blocker list, smoke metrics)
- `docs/A_TO_Z_PLAN.md` PHASE CHANGELOG + DASHBOARD (current position 2)
- `gpt-codex/runs/smoke_cuda_bf16/result.json` (cycle 3 smoke evidence)
- `scripts/phase7_baseline.sh` (cycle 4 first execute)
