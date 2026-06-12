# Dev Cycle 10 - Wrapper-Lite Run Manifest Anchor

Date: 2026-05-15
Branch: `phase-v3-safety-boundary`
Feature commit: `9aca8ed`
Evidence commit: `98de138`
Schema commit: `4ce26f7`
Close commit: `edccaf6`
Post-audit hardening commit: `9aa1f98`

## Scope

Cycle 10 closed the narrow v2 event-log external anchor gap for current short runtime surfaces. Cycle 9's v2 hash chain catches content tamper and broken prev-links inside one log file, but a truncate-and-restart from `GENESIS` can be internally clean without an external receipt.

Added:

- `scripts/run_organic_wrapper.py`
- `scripts/verify_cycle10_wrapper.sh`
- `project_x.run_manifest.v0`
- `project_x.cycle10_wrapper_truncate_test.v0`
- `project_x.text_generation_highlights.v0`

The wrapper records binary sha256, command, event-log path, event-log row count, and the last row's `event_content_hash`. With `--prior-manifest`, it rejects a run when wrapper version, binary sha256, event-log path, row count, or last `event_content_hash` do not match the prior anchor.

## Evidence

Tracked artifacts:

- `run/artifacts/organic-v0/cycle10_wrapper_manifest_clean_run.json`
- `run/artifacts/organic-v0/cycle10_wrapper_truncate_test.json`
- `run/artifacts/organic-v0/cycle10_wrapper_manifest_path_denial.json`
- `run/artifacts/organic-v0/policy_self_test_cycle10_regression.json`
- `run/artifacts/organic-v0/cycle10_carry_forward_verification.json`
- `run/artifacts/organic-v0/text_generation_highlights_v0.json`

Headline results:

- Clean wrapper run: nonzero event-log rows and a recorded last `event_content_hash`.
- Truncate baseline M1: nonzero event-log rows.
- Truncate restart M2: native binary exit code `0`, wrapper exit code `1`, `wrapper_denial:true`. The current hardening rerun denied on `wrapper_truncate_detect_verdict:"mismatch_final_hash"` while row count happened to match; earlier evidence denied on row-count/final-hash mismatch. Either mismatch is a denial by design.
- Native-alone control: exit code `0` on a zero-length log and 96 event-log rows, proving the native v2 chain alone accepts a fresh internally clean chain.
- Prior-continuity hardening controls: synthetic prior `binary_sha256` mismatch denied with row count and final hash matching; synthetic prior `event_log_path` mismatch denied with row count and final hash matching.
- Path-denial ablation: forwarded `--out /etc/binary-output.json` and `--event-log /etc/binary-events.jsonl` denied before launch, `binary_launched:false`, default manifest still emitted.
- Policy regression: `all_required_checks_passed:true`.
- Carry-forward rerun: `all_required_checks_passed:true`.
- Text bridge: 16 entries; no invented quotes; two entries are explicit no-runtime-generation placeholders.

## Verification

Implementation-time gates:

```bash
python3 -m py_compile scripts/run_organic_wrapper.py
bash -n scripts/verify_cycle10_wrapper.sh
timeout 180s scripts/verify_cycle10_wrapper.sh
timeout 180s build/organic_v0 --phase policy-self-test --mode test --run-id cycle10-policy-self-test --out run/artifacts/organic-v0/policy_self_test_cycle10_regression.json
```

The first detached-worktree `make test` attempt exposed a file-mode defect: harness scripts were executable in the local checkout but tracked as `100644`, so a fresh worktree could not run `./scripts/test_organic_v0.sh`. The close commit marks the harness scripts executable in git metadata.

Final gates are rerun in a detached verification worktree after the executable-mode fix so generated artifacts do not rewrite the main worktree's committed evidence.

## Post-Audit Hardening

Claude's audit after `edccaf6` correctly found three soft-contract gaps:

- `binary_sha256` was recorded but not compared against a prior manifest.
- wrapper pre-flight path denial covered `--manifest-out` but not forwarded `--out` or `--event-log`.
- prior-manifest comparison did not enforce event-log path continuity.

Commit `9aa1f98` accepts those findings and fixes them. `scripts/run_organic_wrapper.py` now compares `wrapper_version`, `binary_sha256`, `event_log_path`, `event_log_row_count`, and `event_log_last_event_content_hash` before returning `match`. It also denies out-of-root forwarded `--out` and `--event-log` paths before launch and records rejected paths in the manifest.

Updated evidence:

- `run/artifacts/organic-v0/cycle10_wrapper_truncate_test.json` includes `prior_binary_sha256_mismatch_denied` and `prior_event_log_path_mismatch_denied` checks, both passing.
- `run/artifacts/organic-v0/cycle10_wrapper_manifest_path_denial.json` records both rejected forwarded paths and `binary_launched:false`.
- `docs/artifacts/PERSISTENCE_SCHEMA.md` documents the stronger Run Manifest v0 comparison rules.

## Honest Interpretation

Cycle 10 wrapper-lite anchors event-log row count and tail hash for wrapper-invoked short runtime surfaces. It makes truncate-and-restart detectable when a prior manifest is supplied.

This does not make organic-v0 sandboxed, secure, resource-limited, supply-chain safe, escape-resistant, alignment solved, AGI safety solved, or tool-use safety solved. It is an external receipt, not a fortress.

## Negative Space

```json
{
  "not_sandboxed": true,
  "not_secure": true,
  "not_alignment_solution": true,
  "not_tool_use_safety": true,
  "not_full_resource_limit": true,
  "not_supply_chain_safety": true,
  "anchor_only": true
}
```

## Next

Cycle 11 should apply voice pressure: longer organic generated text from loaded learned state, a tiny raw philosophy prompt database, quote-per-state JSON, and a raw transcript. The acceptance target is only that interesting organic text exists. It must not use templates, pretrained models, semantic parsers, or response polish.
