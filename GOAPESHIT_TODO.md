# GOAPESHIT TODO (BLUEPRINT.md → reproducible 100% gate)

This checklist is the atomic breakdown for finishing the current milestone in `HANDOFF.md`:
re-validate headline metrics on the fixed 50M checkpoint and add a one-command reproduce gate
that hard-fails if thresholds slip.

## Phase 0 — Environment checkpoint
1. [x] Verify GPU present (`nvidia-smi -L`)
2. [x] Verify Python venv (`./.venv/bin/python --version`)
3. [x] Verify Torch + CUDA (`./.venv/bin/python -c "import torch; ..."`)
4. [x] Verify git working tree clean (`git status`)

## Phase 1 — Requirements extraction (BLUEPRINT/HANDOFF)
5. [ ] Re-scan `BLUEPRINT.md` metric definitions (DoErr/OD-NDT/CBR/K_eff)
6. [ ] Confirm current “headline eval” commands from `HANDOFF.md`
7. [ ] Confirm threshold values and pass bands (K_eff/CBR_B/DoErr/OD-NDT)

## Phase 2 — Baseline re-validation on fixed checkpoint
8. [ ] Run `pytest` suite (`./.venv/bin/python -m pytest tests/ -q`)
9. [ ] Compute `K_eff` on `results/checkpoint_multitask_ccb_final_50331648.pt`
10. [ ] Run CBR bimodality eval on fixed checkpoint
11. [ ] Run DoErr eval on fixed checkpoint
12. [ ] Run OD-NDT eval (sleep consolidation) on fixed checkpoint
13. [ ] Record metric outputs into a single structured summary (JSON or text)

## Phase 3 — Reproducibility gate (one command, hard fail)
14. [ ] Design a single entrypoint `reproduce.sh` (tests + eval gates)
15. [ ] Implement a Python gate runner that:
    - runs the three headline evals,
    - extracts numeric metrics reliably,
    - checks thresholds,
    - exits non-zero on any failure
16. [ ] Add flags: `--checkpoint`, `--device`, `--quick/--full`, `--skip-tests`, `--skip-evals`
17. [ ] Ensure determinism knobs: fixed seeds + controlled episode/task counts
18. [ ] Ensure gate output is concise and machine-readable (optional `--json`)
19. [ ] Ensure gate avoids polluting the repo unless explicitly asked (`--save-artifacts`)

## Phase 4 — Tests + docs
20. [ ] Add a fast unit/integration test for the gate runner (no heavy checkpoint)
21. [ ] Add an optional `@pytest.mark.slow` E2E test that exercises the fixed-checkpoint gate
22. [ ] Update `README.md` with `reproduce.sh` usage + expected thresholds
23. [ ] Update `HANDOFF.md` “Commands” section to include the new gate

## Phase 5 — Final validation + commits
24. [ ] Run `reproduce.sh` end-to-end on GPU
25. [ ] Re-run `pytest` to ensure no regressions
26. [ ] Verify working tree is clean (no accidental artifacts)
27. [ ] Commit changes in 1–2 logical commits on `dev/external-audit-fixes`

