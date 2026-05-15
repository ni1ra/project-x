# Do This Next - Project X

Generated: 2026-05-15, after Cycle 10.5 wrapper hardening.

This file is the immediate queue cut from the phase plan. It is not a cycle archive. Closed cycle evidence belongs in `docs/A_TO_Z_PLAN.md` and `docs/past_work/cycles/`; machine-readable runtime artifacts belong under `run/artifacts/`.

## Read First

1. `docs/MANIFESTO.md`
2. `docs/A_TO_Z_PLAN.md`
3. `docs/REPO_CONTROL.md`
4. `docs/artifacts/PERSISTENCE_SCHEMA.md`
5. `docs/past_work/cycles/phase_v3_safety_boundary/dev-cycle-10-9aca8ed.md`

## Current State

Cycle 8 converted organic-v0 from per-phase invocation toward a native organism loop: wake, sleep, checkpoint, replay, and daemon-lite. A0 remains an infrastructure-only event-outcome predictor for replay priority and confidence. It is not a generator, not a semantic parser, and not proven useful versus the tiny random null yet.

Cycle 9 opened phase v3 and added in-process runtime policy gates for the current sleep/wake and daemon-lite surfaces:

- policy ON by default, with explicit unsafe disable flag
- count budgets for wake commands, sleep ticks, replay candidates, mutation attempts, checkpoints, and file writes
- filesystem allowlist for project run/artifact/state/experience roots plus explicit per-run tmp roots
- runtime command/action-kind allowlist
- v2 event-log content hash chaining and replay-source-log integrity walk
- hard-stop denial artifact with guard-ON/guard-OFF controls
- rollback proof for rejected sleep mutations including predictor hash equality
- resettable rerun proof over a wiped per-run root

Cycle 10 added wrapper-lite external anchoring for current short runtime surfaces. Cycle 10.5 accepted Claude's post-audit A/B/C findings and hardened the wrapper before opening voice pressure. The wrapper is a receipt writer, not a sandbox:

- always emits `project_x.run_manifest.v0` to a default manifest path
- binds each run to binary sha256, command, event-log path, event-log row count, and last `event_content_hash`
- optionally compares against a prior manifest and rejects wrapper-version, binary-sha, event-log-path, row-count, or tail-hash mismatches
- rejects out-of-allowlist `--manifest-out`, forwarded `--out`, or forwarded `--event-log` before launching the binary, while still writing the default manifest
- preserves Cycle 9 policy regression and carry-forward rails
- adds `text_generation_highlights_v0.json` so real generated text across cycles is auditable without invented quotes

Evidence:

- implementation commit `9aca8ed`
- evidence commit `98de138`
- schema commit `4ce26f7`
- close commit `edccaf6`
- hardening commit `9aa1f98`
- clean wrapper manifest: `run/artifacts/organic-v0/cycle10_wrapper_manifest_clean_run.json`
- truncate and prior-continuity test: `run/artifacts/organic-v0/cycle10_wrapper_truncate_test.json`
- forwarded-path denial manifest: `run/artifacts/organic-v0/cycle10_wrapper_manifest_path_denial.json`
- policy regression: `run/artifacts/organic-v0/policy_self_test_cycle10_regression.json`
- carry-forward rerun: `run/artifacts/organic-v0/cycle10_carry_forward_verification.json`
- text bridge: `run/artifacts/organic-v0/text_generation_highlights_v0.json`
- reflection: `docs/past_work/cycles/phase_v3_safety_boundary/dev-cycle-10-9aca8ed.md`

Honest boundary: Cycle 10/10.5 anchors event-log row count, tail hash, binary sha, and event-log path continuity for wrapper-invoked short runtime surfaces. It does not make the runtime sandboxed, secure, resource-limited, escape-resistant, supply-chain safe, alignment solved, AGI safety solved, or tool-use safety solved.

## Immediate Next: Cycle 11 Voice Pressure

Default direction: pressure the learned generator to produce longer, more reflective organic text from learned internal state, without templates or pretrained models.

Cycle 11 should add:

- a longer output budget rail by raising the generator char/token cap and documenting the new max
- a tiny philosophy/reflective prompt database at `experience/organic-v0/philosophy_prompts_v0.jsonl` with roughly 10-20 raw text prompts and no labels
- a quote-per-state artifact at `run/artifacts/organic-v0/quote_per_state_cycle11.json` linking `state_hash` to raw generated output for each loaded child
- a raw generation transcript markdown alongside the JSON
- explicit evidence that the output came from loaded learned state, not templates or source-code response polish

Acceptance criterion: interesting organic text exists. Bad output is fine if it came from learned internal state. The target is not fluency, coherence, philosophy, or normal chat yet.

## Forbidden In Cycle 11

- no templates
- no pretrained models
- no semantic parsers
- no response polish
- no route tables for philosophical answers
- no JARVIS UI
- no SNN layer
- no self-graded subjective benchmark claims
- no safety-boundary victory language

## Carry-Forward Rails

Every implementation cycle must preserve these rails unless the artifact explicitly diagnoses and justifies a change:

- `make test`
- post-audit full rail script: `timeout 180s scripts/verify_cycle9_carry_forward.sh`
- cycle-6 regression: 30/30, hash `29958f0880e662dc`
- clean chat rail: 1/5, hash `888b7664126b7f5f`
- legacy cycle-2 rail: 9/25, hash `3536309de837d3e2`, raw `evt_mem_test_001` output `"milaquart arch6"`
- Cycle 7B numeric interactive: seeds 7001/7002 held-out exact
- Cycle 7C symbolic interactive: seeds 7101/7102 held-out and probe exact
- Cycle 7D grid interactive: seeds 7201/7202 held-out and probe exact
- Cycle 7E text rail: all-on/from-disk exact, learning-disabled ablation degraded
- Cycle 7F replay: all-on/from-disk exact, audit-ablation degraded, replay-disabled control preserved
- Cycle 7G raw spans: all-on/from-disk exact, raw-span ablation degraded

Do not rerun the one-hour daemon proof unless a default runtime behavior changes. Use short full-codepath tests first.
