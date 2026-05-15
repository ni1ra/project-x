# Dev Cycle 11 - Voice Pressure Quote Probe

Date: 2026-05-15
Branch: `phase-v3-safety-boundary`
Implementation/evidence commit: `9c78379`

## Scope

Cycle 11 opened the voice-pressure lane after Cycle 10.5 hardened the wrapper. The goal was not to teach philosophy yet. The goal was to make longer raw generation from persisted learned states auditable:

- load real saved organic-v0 states
- ask unlabeled reflective/raw prompts
- raise output budget at runtime without mutating old state snapshots
- preserve raw outputs, including bad repetitions
- bind the run to a v2 event log and wrapper manifest
- verify only mechanical claims

## What Changed

- Added native `--phase quote-probe`.
- Added `--generation-max-output-chars`, applied after state load for quote-probe runs.
- Added unlabeled prompt DB: `experience/organic-v0/philosophy_prompts_v0.jsonl`.
- Added probe-state manifest: `experience/organic-v0/cycle11_probe_states_v0.jsonl`.
- Added wrapper-backed verification harness: `scripts/verify_cycle11_voice_pressure.sh`.
- Added Cycle 11 schemas to `docs/artifacts/PERSISTENCE_SCHEMA.md` and file rows to `docs/REPO_CONTROL.md`.

The quote-probe uses the same `OrganicBrain::generate()` path as prior text rails. It does not call the outcome predictor to choose output characters. The verifier also statically checks the generate body for predictor/replay-priority symbols.

## Evidence

- Quote artifact: `run/artifacts/organic-v0/quote_per_state_cycle11.json`
- Transcript: `run/artifacts/organic-v0/quote_per_state_cycle11_transcript.md`
- Event log: `run/artifacts/organic-v0/cycle11_voice_pressure_event_log.jsonl`
- Wrapper manifest: `run/artifacts/organic-v0/cycle11_voice_pressure_manifest.json`
- Verification artifact: `run/artifacts/organic-v0/cycle11_voice_pressure_verification.json`

Headline mechanical results:

- 5 persisted states loaded.
- 12 unlabeled prompts used.
- 60 raw generations produced.
- 60/60 outputs nonempty.
- 4 outputs exceeded the old 48-character cap under `--generation-max-output-chars 160`.
- All loaded state hashes self-checked.
- All generation calls left state unchanged.
- Wrapper manifest recorded event-log row count 60 and output artifact SHA.
- Verification artifact passed 282/282 checks.

## Verification

Main worktree:

```bash
timeout 180s make test
timeout 180s scripts/verify_cycle11_voice_pressure.sh
```

Detached worktree at `9c78379` with `run/state` copied in:

```bash
timeout 180s make test
timeout 180s scripts/verify_cycle9_carry_forward.sh
timeout 180s scripts/verify_cycle10_wrapper.sh
timeout 180s scripts/verify_cycle11_voice_pressure.sh
```

Result: all passed in `/tmp/projectx-cycle11-verify.jXbv2r`.

## Defect Caught

The first detached verification failed because `scripts/verify_cycle11_voice_pressure.sh` had been added as mode `100644`. That would break fresh clones and CI. Fixed with `git update-index --chmod=+x`, amended into `9c78379`, then reran the detached rails successfully.

## Honest Boundary

Cycle 11 proves raw generated text can be produced from loaded learned states under a larger runtime budget and externally receipted by the wrapper. It does not prove philosophy, semantic understanding, fluent chat, A0 usefulness, alignment, AGI safety, sandbox escape resistance, broader tool-use safety, supply-chain safety, or resource limiting.

The best next cycle is not UI and not full sandbox. It is Cycle 12 voice learning pressure: let unlabeled reflective exposure mutate a child state, reload it, and compare before/after quote artifacts without adding labels, templates, or subjective quality scores.
