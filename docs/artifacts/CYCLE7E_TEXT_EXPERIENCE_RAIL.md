# Cycle 7E Text Experience Rail

Date: 2026-05-14
Status: closed implementation evidence for the first durable organic text-experience rail.

## Claim

Cycle 7E adds a native, database-backed path for text interaction experience.

The new rail can ingest an auditable JSONL record of:

- raw text input
- observations/sense fields
- raw output before correction
- correction/reward feedback
- learned state mutation
- event-log rows
- child checkpoint save
- fresh loaded-child probe
- transcript preservation

This is not GPT/Claude-style chat. It is not poetry, philosophy, broad math, physics, opinions, or beyond-human intelligence. It is the first durable language-experience substrate needed before those claims can be honestly attempted.

## Mechanism

Implemented in `native/organic_v0.cpp` as:

- `TextExperienceRecord`
- `--phase text-experience`
- `--phase text-experience-probe`
- `--experience-db`
- `--transcript-out`
- `--ablate-text-experience-learning`

The experience database lives outside `benchmarks/`:

- `experience/organic-v0/text_experience_seed_v0.jsonl`

Each record is converted into an ordinary organic-v0 `Event`. Training records are generated before correction, then learned through the same `OrganicBrain::learn` machinery used by earlier cycles. Probe records generate without learning.

The ablation disables the learning step, not the evaluator. If the score holds under that ablation, the rail is not load-bearing.

## Negative Space

Cycle 7E does not add:

- response templates
- greeting/farewell/identity trigger lists
- parser-dispatcher answer routes
- benchmark-specific chat answers
- a polished frontend voice
- pretrained or remote inference
- target-output access during probe generation

The correction output exists in the database because it is a training record. The raw action is always generated before correction is applied or scored.

## Evidence

Aggregate artifact:

- `run/artifacts/organic-v0/text_experience_cycle7e_summary.json`

All-on artifact:

- `run/artifacts/organic-v0/text_experience_cycle7e.json`

Transcript artifact:

- `run/artifacts/organic-v0/text_experience_cycle7e_transcript.md`

Fresh loaded-child probe:

- `run/artifacts/organic-v0/text_experience_cycle7e_from_disk_probe.json`

Ablation artifact:

- `run/artifacts/organic-v0/text_experience_cycle7e_ablate_learning.json`

Ablation transcript:

- `run/artifacts/organic-v0/text_experience_cycle7e_ablate_transcript.md`

## Metrics In Plain English

All-on:

- train-before: 1/6 exact (`0.166667`)
- train-after: 4/6 exact (`0.666667`)
- probe: 4/4 exact (`1.000000`)
- child hash: `be0fc781039a2038`

Fresh loaded child:

- probe: 4/4 exact (`1.000000`)
- loaded hash: `be0fc781039a2038`
- same-process probe + model hash diff-clean: true

Learning-disabled ablation:

- probe: 0/4 exact (`0.000000`)
- hash remains the cycle-6 parent hash `29958f0880e662dc`
- state growth is zero

Translation:

- `train-before` asks what the brain already said before correction.
- `train-after` asks whether correction changed the same record.
- `probe` asks whether new text records work after learning.
- `from-disk probe` asks whether the saved child still works after restart.
- `ablation` asks whether disabling the new learning rail breaks the result.

The imperfect train-after score is important. It prevents a false polished-chat claim: even after correction, two immediate training rows are still wrong in the transcript. The probe transfer works because later text experience accumulates into the learned state.

## Transcript Examples

All-on held-out probes:

- `what does navi carry` -> `navi carries basalt prism`
- `what does mira carry` -> `mira carries glass lantern`
- `where does navi wait` -> `navi waits at quiet archive`
- `where does mira wait` -> `mira waits at stone atrium`

Preserved failures:

- `what does arin carry` after first correction emits `arin carries caries car`
- `where does arin wait` after correction emits `arin carries  north dock`

These failures are not hidden. They are part of the evidence that the rail is organic learned state, not a scripted answer layer.

## Regression Gates

After implementation:

- `make test`: PASS, persistence hash `29958f0880e662dc`, output `"mila quartz pier6"`
- cycle-6 regression: 30/30 (`1.000000`), hash `29958f0880e662dc`
- manifesto-safe live chat: 1/5 (`0.200000`), hash `888b7664126b7f5f`
- legacy cycle-2 snapshot on cycle-5 fixture: 9/25 (`0.360000`), hash `3536309de837d3e2`, raw `"milaquart arch6"`
- Cycle 7B numeric interactive regression: seeds 7001/7002 remain 7/7 held-out exact
- Cycle 7C symbolic interactive regression: seeds 7101/7102 remain 8/8 held-out exact and 8/8 post-episode probe exact
- Cycle 7D grid interactive regression: seeds 7201/7202 remain 8/8 held-out exact and 8/8 post-episode probe exact

## Interpretation

A passing Cycle 7E proves only this:

> organic-v0 can ingest a small durable text-interaction experience stream, preserve raw before/after outputs, mutate learned state through correction, save a child checkpoint, reproduce held-out text probes from disk, and collapse under a learning-disabled ablation.

It does not prove natural conversation, real opinions, poetry, philosophy, math, physics, broad reasoning, a complete neural brain, or beyond-human intelligence.

## Next Rung

Cycle 7F should extend this rail toward replay and consolidation rather than returning to isolated puzzle patches. The next evidence should show that failed text experience can be replayed from the database into a child state, improve or stabilize held-out text behavior, and degrade under `--ablate-text-experience-replay`.
