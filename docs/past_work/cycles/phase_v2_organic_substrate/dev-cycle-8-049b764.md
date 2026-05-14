# Dev Cycle 8 - Sleep/Wake Runtime And A0 Replay Priority

Date: 2026-05-14
Branch: `feat/organic-v0-trace-id-ablation`
Implementation commit: `049b764`

## Scope

Cycle 8 was a structural runtime cycle, not another encoder-feature patch.

Added:

- `--phase sleep-wake`
- `--phase daemon-lite`
- stdin JSONL wake/sleep/checkpoint/shutdown commands
- v1 event-log records with prediction, prediction error, trace refs, mutation refs, source, reward, and audit-only output fields
- a small A0 linear event-outcome predictor over auditable feature IDs
- predictor serialization in optional `PREDICTOR_CONNS`
- prediction-error replay priority and fixed-seed random replay baseline
- default checkpoint policy: every 60 seconds or every 100 replay ticks, whichever comes first
- hard 180s test-mode wrapper in `scripts/test_organic_v0.sh`

The old cycle-design notes were moved out of `docs/artifacts/` into `docs/past_work/cycles/phase_v2_organic_substrate/cycle_docs/`. Cycle 8 did not create a new `docs/artifacts/CYCLE*.md` file; the active contract lived in `docs/DO_THIS_NEXT.md` and the durable result is this past-work reflection.

## Runtime Result

Primary artifacts:

- `run/artifacts/organic-v0/sleep_wake_cycle8_test.json`
- `run/artifacts/organic-v0/sleep_wake_cycle8_priority.json`
- `run/artifacts/organic-v0/sleep_wake_cycle8_random_baseline.json`
- `run/artifacts/organic-v0/daemon_lite_cycle8_1h.json`
- `run/artifacts/organic-v0/cycle8_organic_metrics.json`

Short full-mode sleep/wake test:

- run_id: `cycle8-test`
- wake events: 1
- sleep ticks: 20
- replay candidates: 1
- accepted mutations: 2
- rejected mutations: 18
- checkpoints: 5
- surprise reduction: `0.505034`
- timed out: false

Daemon-lite long run:

- run_id: `cycle8-daemon-1h`
- requested duration: 3600 seconds
- measured event-log duration: 3635 seconds (`2026-05-14T13:48:24Z` -> `2026-05-14T14:48:59Z`)
- sleep ticks: 30824
- event-log rows: 30826
- checkpoints: 310
- accepted mutations: 1
- rejected mutations: 30823
- replay candidates: 1
- final state hash: `f922498181ba3064`

Daemon command:

```bash
timeout 3900s build/organic_v0 --phase daemon-lite --mode daemon --run-id cycle8-daemon-1h --daemon-run-seconds 3600 --checkpoint-interval-seconds 60 --checkpoint-interval-ticks 100 --out run/artifacts/organic-v0/daemon_lite_cycle8_1h.json --event-log run/state/organic-v0/events/raphael-local-0001-cycle8-daemon-1h.jsonl
```

## Predictor Boundary

A0 predicts reward/exactness/error before reward or correction is known. It updates by bounded deterministic delta/SGD over feature IDs and serializes doubles bit-exactly through the existing hex helpers.

The predictor is firewalled from generation:

- `OrganicBrain::predict_outcome` is separate from `OrganicBrain::generate`
- `OrganicBrain::generate` does not read predictor weights, prediction output, prediction error, or replay priority
- replay selection may use prediction error
- output characters, mode switches, copied spans, and response text do not receive predictor values

Grep audit note: the C++ diff contains legitimate co-occurrence of prediction and generation in organism orchestration (`organism_wake_step`, `organism_sleep_step`, and replay selection). Those hits are sequencing code: predict before generate, generate audit-only where needed, then learn/update. No predictor value is fed into generation scores.

## Priority Versus Random

Predeclared metric: `surprise_reduction`.

Prediction-priority run:

- run_id: `cycle8-priority`
- wake events: 3
- sleep ticks: 60
- replay candidates: 3
- accepted mutations: 4
- rejected mutations: 56
- checkpoints: 7
- surprise reduction: `1.366337`
- final hash: `b487a1ee0d17a742`

Fixed-seed random null baseline:

- run_id: `cycle8-random`
- random seed: 8801
- wake events: 3
- sleep ticks: 60
- replay candidates: 3
- accepted mutations: 6
- rejected mutations: 54
- checkpoints: 9
- surprise reduction: `1.374792`
- final hash: `0656559906783375`

Result: prediction-priority did not beat the fixed-seed random null on this tiny Cycle 8 comparison. The measured delta was `-0.008455` surprise reduction. The comparison is underpowered; A0 remains infrastructure-only and unproven as load-bearing. The time series suggests priority converged/exploited too quickly and needs an exploration term or denser replay workload before another comparison.

The two life streams diverged in final state hash (`b487a1ee0d17a742` vs `0656559906783375`).

## Regression Gates

Passed after implementation:

- `make test`
- cycle-6 regression: 30/30, hash `29958f0880e662dc`
- clean chat rail: 1/5, hash `888b7664126b7f5f`
- legacy cycle-2 rail: 9/25, hash `3536309de837d3e2`, raw `"milaquart arch6"`
- Cycle 7B numeric interactive: seed 7001 7/7 held-out, seed 7002 7/7 held-out
- Cycle 7C symbolic interactive: seed 7101 8/8 held-out and 8/8 probe, seed 7102 8/8 held-out and 8/8 probe
- Cycle 7D grid interactive: seed 7201 8/8 held-out and 8/8 probe, seed 7202 8/8 held-out and 8/8 probe
- Cycle 7E text rail: all-on 4/4, from-disk 4/4, learning-disabled ablation 0/4
- Cycle 7F replay: all-on post-replay 4/4, from-disk 4/4, audit-ablation 1/4, replay-disabled control retained the 7E child hash
- Cycle 7G raw spans: all-on 4/4, from-disk 4/4, raw-span ablation 0/4

## Honest Interpretation

Cycle 8 proves a native sleep/wake/daemon-lite process shape with persistent checkpoints, v1 event records, replay mutation evidence, and a serialized A0 prediction-error substrate.

It does not prove fluent chat, broad reasoning, AGI, a safety-boundary solution, or that prediction-priority is better than random. It does not add a next-token predictor, semantic parser, answer dispatcher, pretrained dependency, route table, or response polish layer.

The next cycle should prioritize the formal safety boundary: action budgets, filesystem allowlists, resettable environment, rollback semantics, and denial tests for hostile stdin/event-log data.
