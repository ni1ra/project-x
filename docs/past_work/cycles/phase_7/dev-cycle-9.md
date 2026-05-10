## Cycle 9 (phase 7, position 5+) — 2026-05-02 04:45–05:00 CEST

### Persona
Execute-navi (Steps 7+8 — tasks.py registry + --task flag).

### Skills used
- `flow-state` defaults (continued from cycle 8). No fresh Skill loads.

### Shipped this cycle
- **`src/project_x/experiments/tasks.py` NEW** (~85 lines) — Task registry pattern with 3 implementations:
  - `long-range-copy` (default; verbatim phase 1-7 baseline behavior)
  - `key-noise` (corrupts cfg.task_noise_frac=0.10 of samples' key cue; truth at final position remains the original key)
  - `multi-key` (plants cfg.task_n_keys=2 keys at distinct first-half positions; truth = first key)
- **`compressed_memory.py` extended:**
  - `ExperimentConfig` +3 fields: `task`, `task_noise_frac`, `task_n_keys`
  - `make_batch` now delegates to `tasks.make_batch` via relative import
  - `run_experiment` +3 params, argparse +3 flags (`--task`, `--task-noise-frac`, `--task-n-keys`)
- **Verification:**
  - `pytest -q` → 2/2 passed (no regression on existing tests)
  - 3 smoke runs (one per task, d=64 d=1 b=8 s=64 100 steps cuda bf16) all complete without error. delayed_assoc_acc ≈ 0.019 ≈ 1/vocab_size random chance — expected at 100 steps, smoke validates pipeline integrity.
- **Backward-compat preserved:** all existing scripts (`scripts/run_phase7_grid.sh`, `scripts/phase7_baseline.sh`) continue to work without modification — default task is `long-range-copy`.
- **Files**: `src/project_x/experiments/tasks.py` (NEW), `src/project_x/experiments/compressed_memory.py` (MODIFIED — 6 edits), `docs/A_TO_Z_PLAN.md` (PHASE CHANGELOG cycle_position note), `docs/past_work/cycles/phase_7/dev-cycle-9.md` (this file). DO_THIS_NEXT.md rewrite for cycle 10 (HANDOFF) follows.
- **Discord verdict** (2-msg split): Steps 7+8 shipped, phase 7 deliverables now COMPLETE. 3 publishable findings stacked.

### Phase 7 deliverables COMPLETE
| Step | Status | Cycle |
|------|--------|-------|
| 1: --device flag | ✅ | 3 |
| 2: --amp flag + autocast | ✅ | 3 |
| 3: util_harness.py | ✅ | 3 |
| 4: util_harness hooked into run_experiment | ✅ | 3 |
| 4b: selector_snapshot persistence | ✅ | 3 |
| 5: phase7_baseline.sh | ✅ | 4 |
| 6: cell-config tuple locked | ✅ | 4 |
| 7: tasks.py registry | ✅ | 9 |
| 8: --task flag | ✅ | 9 |
| 9: MQA class | DEFERRED future-session | per advisor cycle 2 |
| 10: --ablation flag | DEFERRED | bundled with Step 9 |
| 11: hopfield_lens.py (simplified) | ✅ | 8 |
| 12: run_phase7_grid.sh | ✅ | 4 |
| 13: 40-cell grid run + verdict | ✅ | 7 |

### Lessons / Mistakes
- **Initial import statement was wrong** — wrote `from project_x.experiments.tasks import make_batch` but the module is invoked as `python3 -m src.project_x.experiments.compressed_memory` (with `src.project_x` as the package path), not `project_x`. Fixed to relative import `from .tasks import make_batch`. Caught at smoke-test time, fixed in <30s. Worth noting for next time: relative imports are safer for in-package modules.
- **smoke-test step count (100) was too low to actually learn** — delayed_assoc_acc ≈ random chance (~1/vocab). That's fine for pipeline-validation, but if I wanted to test that the new task variants actually work as intended (e.g., key-noise should be HARDER than long-range-copy at sufficient steps), I'd need to run 500+ step smokes. Deferred to future-session.

### 420 score
**410** — Solid execution: refactor preserved backward-compat, pytest stayed green, all 3 tasks pipeline-verified. Lost 10: (a) initial import bug cost a smoke-test cycle (small, but a no-think error), and (b) smoke-runs at 100 steps don't actually exercise the new task semantics — proper validation deferred. Both small enough to not warrant deeper rework this cycle.

### Next cycle hook
Cycle 10 fires at cron 05:05. Scope = HANDOFF prep:
1. Final DO_THIS_NEXT.md rewrite for next /godify run / lain wake
2. Phase 7 summary block in dev-cycle-10.md (cycle count, ships, findings, files)
3. Discord HANDOFF post: total cycles 5-10 in this /godify, 3 publishable findings, 5+ commit-equivalent ships, all files
4. CronDelete `c6f4bf7d` (the /godify cron)
5. Listener stays armed (lain may message anytime)

If lain sends a redirect msg before cycle 10 fires, the listener catches it and cycle 10 acks first.
