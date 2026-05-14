# Do This Next - Project X v2

Generated: 2026-05-14, after Cycle 8 implementation.

This file is the immediate queue cut from the phase plan. It is not a cycle archive. Closed cycle evidence belongs in `docs/A_TO_Z_PLAN.md` and `docs/past_work/cycles/phase_v2_organic_substrate/`; machine-readable runtime artifacts belong under `run/artifacts/`.

## Read First

1. `docs/MANIFESTO.md`
2. `docs/A_TO_Z_PLAN.md`
3. `docs/REPO_CONTROL.md`
4. `docs/artifacts/PERSISTENCE_SCHEMA.md`
5. `docs/past_work/cycles/phase_v2_organic_substrate/dev-cycle-8-049b764.md`

## Current State

Cycle 8 converted organic-v0 from per-phase invocation toward a native organism loop:

- WAKE: perceive -> predict -> generate -> optional correction/reward -> learn/update predictor -> log/checkpoint
- SLEEP: replay event evidence -> predict -> candidate learn/update -> audit -> accept/reject -> log/checkpoint
- DAEMON-LITE: a bounded long-lived process with periodic checkpoints and event-log emission

The A0 event-outcome predictor is intentionally narrow: a small linear predictor over auditable feature IDs. It predicts reward/exactness/error for replay priority and confidence only. It does not generate text, choose output characters, dispatch answers, parse semantics, call pretrained models, or implement a next-token path.

Cycle 8 should be treated as infrastructure-only until stronger replay evidence says otherwise. Prediction-priority did not beat the fixed-seed random null on the tiny Cycle 8 comparison. The comparison is underpowered; A0 remains unproven. The time series suggests priority converged/exploited too quickly and needs an exploration term or denser replay workload before another comparison.

Post-audit cleanup added `--daemon-tick-sleep-ms` for daemon-lite throughput tests. Default behavior is preserved: daemon mode sleeps 100ms per tick, and test mode sleeps 1ms per tick. Set the knob lower, including `0`, only when the local run intentionally spends more CPU for faster evidence.

## Immediate Next: Cycle 9 Safety Boundary

Phase boundary: v2 Cycle 8 closes the organic-substrate runtime-shape phase. Cycle 9 opens a safety-boundary/runtime-governance phase, not another v2 capability cycle, unless the user explicitly reopens v2.

Default direction: implement the formal safety boundary that Cycle 8 explicitly did not solve.

The reason to prioritize this now is mechanical: organic-v0 can now ingest stdin JSONL and replay event-log records inside a persistent process. Even though Cycle 8 does not execute shell commands, network calls, or arbitrary filesystem actions from data, the runtime still needs explicit budgets and a resettable operating envelope before the daemon becomes more capable.

Cycle 9 should add:

- a runtime policy object with explicit action budgets for wake, sleep, replay, mutation, checkpoint, and file I/O
- a filesystem allowlist rooted in configured state/log/artifact/experience paths
- hard rejection tests for JSONL/event-log data that attempts shell execution, network access, path traversal, or unauthorized file writes
- a resettable environment contract for daemon-lite runs
- checkpoint rollback semantics for rejected or unsafe mutations
- audit artifacts proving denied actions are denied by code, not by absent test data
- a 180s test-mode gate using the same codepaths as full mode
- a >=1 hour daemon-lite rerun under the new policy once the safety boundary exists, using `--daemon-tick-sleep-ms` only when a measured faster local run is intentional

Close Cycle 9 only if the boundary is enforced by tests and artifacts. Do not claim this solves alignment, AGI safety, sandbox escape resistance, or broader tool-use safety.

## Secondary Queue: Concept-Emergence Pressure

If the safety boundary is deliberately deferred by user order, the next capability pressure should be concept-emergence over the Cycle 8 substrate:

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
