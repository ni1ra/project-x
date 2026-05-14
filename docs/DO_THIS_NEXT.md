# Do This Next - Project X

Generated: 2026-05-15, after Cycle 9 implementation.

This file is the immediate queue cut from the phase plan. It is not a cycle archive. Closed cycle evidence belongs in `docs/A_TO_Z_PLAN.md` and `docs/past_work/cycles/`; machine-readable runtime artifacts belong under `run/artifacts/`.

## Read First

1. `docs/MANIFESTO.md`
2. `docs/A_TO_Z_PLAN.md`
3. `docs/REPO_CONTROL.md`
4. `docs/artifacts/PERSISTENCE_SCHEMA.md`
5. `docs/past_work/cycles/phase_v3_safety_boundary/dev-cycle-9-b8f3cff.md`

## Current State

Cycle 8 converted organic-v0 from per-phase invocation toward a native organism loop:

- WAKE: perceive -> predict -> generate -> optional correction/reward -> learn/update predictor -> log/checkpoint
- SLEEP: replay event evidence -> predict -> candidate learn/update -> audit -> accept/reject -> log/checkpoint
- DAEMON-LITE: a bounded long-lived process with periodic checkpoints and event-log emission

The A0 event-outcome predictor is intentionally narrow: a small linear predictor over auditable feature IDs. It predicts reward/exactness/error for replay priority and confidence only. It does not generate text, choose output characters, dispatch answers, parse semantics, call pretrained models, or implement a next-token path.

Cycle 8 should be treated as infrastructure-only until stronger replay evidence says otherwise. Prediction-priority did not beat the fixed-seed random null on the tiny Cycle 8 comparison. The comparison is underpowered; A0 remains unproven. The time series suggests priority converged/exploited too quickly and needs an exploration term or denser replay workload before another comparison.

Post-audit cleanup added `--daemon-tick-sleep-ms` for daemon-lite throughput tests. Default behavior is preserved: daemon mode sleeps 100ms per tick, and test mode sleeps 1ms per tick. Set the knob lower, including `0`, only when the local run intentionally spends more CPU for faster evidence.

Cycle 9 opened phase v3 and added in-process runtime policy gates for the current sleep/wake and daemon-lite surfaces:

- policy ON by default, with explicit unsafe disable flag `--unsafe-disable-policy`
- count budgets for wake commands, sleep ticks, replay candidates, mutation attempts, checkpoints, and file writes
- filesystem allowlist for project run/artifact/state/experience roots plus explicit per-run tmp roots
- runtime command/action-kind allowlist
- v2 event-log content hash chaining and replay-source-log integrity walk
- hard-stop denial artifact with guard-ON/guard-OFF controls
- rollback proof for rejected sleep mutations including predictor hash equality
- resettable rerun proof over a wiped per-run root

Evidence:

- implementation commit `b8f3cff`
- denial/reset artifact `run/artifacts/organic-v0/policy_self_test_cycle9.json`
- reflection `docs/past_work/cycles/phase_v3_safety_boundary/dev-cycle-9-b8f3cff.md`

Honest boundary: In-process policy enforcement; wrapper-level sandbox is a future cycle. This does not solve alignment, AGI safety, sandbox escape resistance, or broader tool-use safety.

## Immediate Next: Cycle 10 Wrapper Boundary

Default direction: add a wrapper-level runtime boundary around `organic_v0` rather than increasing daemon capability.

Cycle 10 should add:

- a thin launcher/harness that runs `organic_v0` inside an OS-level constrained environment available on this machine
- per-run filesystem namespace setup that makes allowed roots physical, not only in-process policy decisions
- process-level timeout, CPU/memory/file-descriptor limits where available
- stdout/stderr/event-log capture with immutable run manifest
- a wrapper/in-process ablation pair: the same denial cases should be blocked by both layers where meaningful
- a replay-source-log tamper test where the wrapper preserves evidence after native refusal
- documentation that native policy is defense-in-depth, not the sandbox

Do not rerun the one-hour daemon proof unless a default runtime behavior changes. Use short full-codepath tests first.

## Secondary Queue: Concept-Emergence Pressure

After the wrapper boundary exists, the next capability pressure should be concept-emergence over the Cycle 8/9 substrate:

- feed replay with more varied event evidence instead of hand-built answer routes
- measure whether prediction error discovers reusable latent clusters across text, symbolic, grid, and numeric traces
- keep generation firewalled from predictor output
- keep random replay as the named null baseline
- require state divergence across at least two life streams

This remains secondary because a more capable daemon without formal budgets is the wrong direction for the manifesto safety boundary.

## Carry-Forward Rails

Every implementation cycle must preserve these rails unless the artifact explicitly diagnoses and justifies a change:

- `make test`
- cycle-6 regression: 30/30, hash `29958f0880e662dc`
- clean chat rail: 1/5, hash `888b7664126b7f5f`
- legacy cycle-2 rail: 9/25, hash `3536309de837d3e2`, raw `evt_mem_test_001` output `"milaquart arch6"`
- Cycle 7B numeric interactive: seeds 7001/7002 held-out exact
- Cycle 7C symbolic interactive: seeds 7101/7102 held-out and probe exact
- Cycle 7D grid interactive: seeds 7201/7202 held-out and probe exact
- Cycle 7E text rail: all-on/from-disk exact, learning-disabled ablation degraded
- Cycle 7F replay: all-on/from-disk exact, audit-ablation degraded, replay-disabled control preserved
- Cycle 7G raw spans: all-on/from-disk exact, raw-span ablation degraded

## Non-Goals For The Next Cycle

- no JARVIS UI
- no SNN layer
- no pretrained model dependency
- no next-token predictor
- no semantic parser or route table
- no response templates or chat polish
- no self-graded subjective benchmark claims
- no safety-boundary victory language
