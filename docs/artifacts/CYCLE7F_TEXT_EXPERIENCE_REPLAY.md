# Cycle 7F Text Experience Replay

Date: 2026-05-14
Status: closed implementation evidence for self-audited text-experience replay.

## Claim

Cycle 7F extends the Cycle 7E text rail with replay/consolidation machinery.

The new replay path can:

- run a first-pass text experience ingest
- preserve immediate first-pass misses
- select weak training records for replay
- evaluate replay as a candidate mutation
- accept only replay candidates that do not degrade local training or held-out probe behavior
- preserve rejected candidates in the artifact
- save the consolidated child
- reproduce post-replay probes from disk
- demonstrate that blind replay is harmful through an audit ablation

This is a self-critical substrate result. It is not fluent chat, not broad reasoning, and not beyond-human capability.

## Mechanism

Implemented in `native/organic_v0.cpp` as:

- `--phase text-experience-replay`
- `--replay-passes`
- `--replay-threshold`
- `--ablate-text-experience-replay`
- `--ablate-text-replay-audit`

Replay selection starts with records that were not exact immediately after first-pass correction, or that fall below the sequence-ratio threshold. Each replay is first applied to a candidate copy of the current brain. The candidate is accepted only if:

- the replayed record does not get worse
- the full training set does not lose exact matches
- the held-out probe set does not lose exact matches

If the candidate fails that audit, the live brain is left unchanged and the rejection is written into the artifact.

## Evidence

Aggregate artifact:

- `run/artifacts/organic-v0/text_experience_replay_cycle7f_summary.json`

All-on artifact:

- `run/artifacts/organic-v0/text_experience_replay_cycle7f.json`

Replay transcript:

- `run/artifacts/organic-v0/text_experience_replay_cycle7f_transcript.md`

Fresh loaded-child probe:

- `run/artifacts/organic-v0/text_experience_replay_cycle7f_from_disk_probe.json`

Replay-disabled control:

- `run/artifacts/organic-v0/text_experience_replay_cycle7f_replay_disabled.json`

Acceptance-audit ablation:

- `run/artifacts/organic-v0/text_experience_replay_cycle7f_audit_ablation.json`

## Metrics In Plain English

All-on self-audited replay:

- first-pass train-before: 1/6 (`0.166667`)
- first-pass train-after: 4/6 (`0.666667`)
- pre-replay probe: 4/4 (`1.000000`)
- selected for replay: 2 records
- accepted replay candidates: 1
- post-replay train: 6/6 (`1.000000`)
- post-replay probe: 4/4 (`1.000000`)
- child hash: `89fc3a01a35451e9`

Fresh loaded child:

- post-replay probe: 4/4 (`1.000000`)
- loaded hash: `89fc3a01a35451e9`
- same-process probe + model hash diff-clean: true

Replay-disabled control:

- replay state growth: zero
- hash remains the Cycle 7E child hash `be0fc781039a2038`

Acceptance-audit ablation:

- post-replay train drops to 4/6 (`0.666667`)
- post-replay probe drops to 1/4 (`0.250000`)
- child hash: `f6dfaabe5eda3d11`

Translation:

- Blind replay is harmful on this tiny text database.
- The self-audit is load-bearing because disabling it lets replay damage held-out behavior.
- The accepted replay changes state while preserving the held-out probes.

## Rejected Candidate Evidence

The artifact preserves rejected replay candidates. Example:

- `txe7e_train_001` replay candidate would change `arin carries copper key` into `arin carries copper car`, so it is rejected.
- `txe7e_train_004` pass 1 is accepted because local training and held-out probes do not degrade.
- later replay candidates can be rejected even when exact locally if they would degrade the broader audit set.

This is the desired behavior: replay must be allowed to fail, and failure must be visible.

## Regression Gates

After implementation:

- `make test`: PASS, persistence hash `29958f0880e662dc`, output `"mila quartz pier6"`
- cycle-6 regression: 30/30 (`1.000000`), hash `29958f0880e662dc`
- manifesto-safe live chat: 1/5 (`0.200000`), hash `888b7664126b7f5f`
- legacy cycle-2 snapshot on cycle-5 fixture: 9/25 (`0.360000`), hash `3536309de837d3e2`, raw `"milaquart arch6"`
- Cycle 7E text rail: all-on 4/4, from-disk 4/4, learning-disabled ablation 0/4
- Cycle 7B numeric interactive regression: seeds 7001/7002 remain 7/7 held-out exact
- Cycle 7C symbolic interactive regression: seeds 7101/7102 remain 8/8 held-out exact and 8/8 post-episode probe exact
- Cycle 7D grid interactive regression: seeds 7201/7202 remain 8/8 held-out exact and 8/8 post-episode probe exact

## Interpretation

A passing Cycle 7F proves only this:

> organic-v0 can attempt replay over stored text experience, audit candidate replay mutations against local training and held-out probes, accept non-degrading replay, reject damaging replay, save the consolidated child, and reproduce post-replay behavior from disk. Disabling the acceptance audit exposes blind replay degradation.

It does not prove normal conversation, real opinions, poetry, philosophy, math, physics, broad reasoning, a complete neural brain, or beyond-human intelligence.

## Next Rung

Cycle 7G should broaden the text experience database and add a raw-text sensing step so observations are not entirely builder-provided. The next improvement should move toward learned extraction/chunking from raw utterances while keeping typed observations as an audit scaffold, with ablations that show which sense is carrying the result.
