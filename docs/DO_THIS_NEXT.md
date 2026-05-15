# Do This Next - Project X

Generated: 2026-05-15, after Cycle 11 voice-pressure quote probe.

This file is the immediate queue cut from the phase plan. It is not a cycle archive. Closed cycle evidence belongs in `docs/A_TO_Z_PLAN.md` and `docs/past_work/cycles/`; machine-readable runtime artifacts belong under `run/artifacts/`.

## Read First

1. `docs/MANIFESTO.md`
2. `docs/A_TO_Z_PLAN.md`
3. `docs/REPO_CONTROL.md`
4. `docs/artifacts/PERSISTENCE_SCHEMA.md`
5. `docs/past_work/cycles/phase_v3_safety_boundary/dev-cycle-11-9c78379.md`

## Current State

Cycle 8 converted organic-v0 from per-phase invocation toward a native organism loop: wake, sleep, checkpoint, replay, and daemon-lite. A0 remains an infrastructure-only event-outcome predictor for replay priority and confidence. It is not a generator, not a semantic parser, and not proven useful versus the tiny random null yet.

Cycle 9 added in-process runtime policy gates for the current sleep/wake and daemon-lite surfaces: count budgets, filesystem allowlist, command/action-kind allowlist, v2 event-log integrity, replay-source-log integrity, rollback proof, and resettable per-run roots.

Cycle 10/10.5 added wrapper-lite external receipts. The wrapper is a receipt writer, not a sandbox: it records binary sha256, event-log path, row count, tail `event_content_hash`, output SHA, and prior-manifest continuity; it preflights wrapper-visible output paths before launch.

Cycle 11 added raw voice pressure:

- native `quote-probe` phase
- runtime-only `--generation-max-output-chars 160` override after state load
- unlabeled prompt store at `experience/organic-v0/philosophy_prompts_v0.jsonl`
- state manifest at `experience/organic-v0/cycle11_probe_states_v0.jsonl`
- quote artifact at `run/artifacts/organic-v0/quote_per_state_cycle11.json`
- raw transcript at `run/artifacts/organic-v0/quote_per_state_cycle11_transcript.md`
- v2 event log plus Cycle 10 wrapper receipt
- verifier at `scripts/verify_cycle11_voice_pressure.sh`

Evidence:

- `run/artifacts/organic-v0/quote_per_state_cycle11.json`
- `run/artifacts/organic-v0/quote_per_state_cycle11_transcript.md`
- `run/artifacts/organic-v0/cycle11_voice_pressure_event_log.jsonl`
- `run/artifacts/organic-v0/cycle11_voice_pressure_manifest.json`
- `run/artifacts/organic-v0/cycle11_voice_pressure_verification.json`

Cycle 11 produced 60/60 nonempty raw outputs across 5 loaded states and 12 prompts. Four outputs exceeded the old 48-character cap under the 160-character runtime budget. All state hashes self-checked and every generation left state unchanged. This is real raw learned-state output, not quality.

Honest boundary: Cycle 11 does not prove philosophy, semantic understanding, fluent chat, A0 usefulness, alignment, AGI safety, sandbox escape resistance, broader tool-use safety, supply-chain safety, or resource limiting.

## Immediate Next: Cycle 12 Voice Learning Pressure

Default direction: turn the Cycle 11 probe from a read-only quote surface into a bounded learning/consolidation cycle without labels or polished answers.

Cycle 12 should add one of these, in this order:

1. **Unlabeled exposure memory.** Let raw reflective prompts become experience events with no correction output, then verify state growth and changed future generation without adding templates or answer routes.
2. **Self-replay pressure.** Reuse the existing replay machinery to consolidate non-oracle prompt exposure, with a before/after quote artifact and rollback proof if replay degrades mechanical probes.
3. **Generator diagnostics.** Add mechanical measures for repetition loops, early END frequency, copy-mode use, activated-trace diversity, and output length distribution. These are not semantic quality scores.

Acceptance criterion for Cycle 12: a loaded state changes because of unlabeled voice exposure, reloads from disk, and produces a mechanically different raw quote artifact with all carry-forward rails intact. Bad or repetitive text is acceptable if it is honestly preserved.

## Forbidden In Cycle 12

- no templates
- no pretrained models
- no semantic parsers
- no response polish
- no route tables for philosophical answers
- no subjective self-grade
- no "philosophy achieved" language
- no sandbox/security victory language
- no mutation of old evidence artifacts except through explicit fresh-run evidence

## Carry-Forward Rails

Every implementation cycle must preserve these rails unless the artifact explicitly diagnoses and justifies a change:

- `make test`
- `timeout 180s scripts/verify_cycle9_carry_forward.sh`
- `timeout 180s scripts/verify_cycle10_wrapper.sh`
- `timeout 180s scripts/verify_cycle11_voice_pressure.sh`
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
