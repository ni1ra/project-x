# Dev Cycle 10 - Wrapper-Lite Run Manifest Anchor

Date: 2026-05-15
Branch: `phase-v3-safety-boundary`
Feature commit: `9aca8ed`
Evidence commit: `98de138`
Schema commit: `4ce26f7`

## Scope

Cycle 10 closed the narrow v2 event-log external anchor gap for current short runtime surfaces. Cycle 9's v2 hash chain catches content tamper and broken prev-links inside one log file, but a truncate-and-restart from `GENESIS` can be internally clean without an external receipt.

Added:

- `scripts/run_organic_wrapper.py`
- `scripts/verify_cycle10_wrapper.sh`
- `project_x.run_manifest.v0`
- `project_x.cycle10_wrapper_truncate_test.v0`
- `project_x.text_generation_highlights.v0`

The wrapper records binary sha256, command, event-log row count, and the last row's `event_content_hash`. With `--prior-manifest`, it rejects a run when the current row count and last `event_content_hash` do not match the prior anchor.

## Evidence

Tracked artifacts:

- `run/artifacts/organic-v0/cycle10_wrapper_manifest_clean_run.json`
- `run/artifacts/organic-v0/cycle10_wrapper_truncate_test.json`
- `run/artifacts/organic-v0/cycle10_wrapper_manifest_path_denial.json`
- `run/artifacts/organic-v0/policy_self_test_cycle10_regression.json`
- `run/artifacts/organic-v0/cycle10_carry_forward_verification.json`
- `run/artifacts/organic-v0/text_generation_highlights_v0.json`

Headline results:

- Clean wrapper run: 99 event-log rows and a recorded last `event_content_hash`.
- Truncate baseline M1: 98 event-log rows.
- Truncate restart M2: native binary exit code `0`, wrapper exit code `1`, `wrapper_denial:true`, `wrapper_truncate_detect_verdict:"mismatch_row_count"`, and both row count and final hash mismatched.
- Native-alone control: exit code `0` on a zero-length log and 96 event-log rows, proving the native v2 chain alone accepts a fresh internally clean chain.
- Path-denial ablation: `--manifest-out /etc/should-not-write.json` denied before launch, `binary_launched:false`, default manifest still emitted.
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
