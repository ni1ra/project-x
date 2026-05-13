# Do This Next - Project X v2

Generated: 2026-05-13 (post persistence-pass-0 ship)

## Read First

1. `docs/MANIFESTO.md`
2. `docs/A_TO_Z_PLAN.md`
3. `docs/REPO_CONTROL.md`
4. `docs/artifacts/PERSISTENCE_SCHEMA.md`
5. `docs/past_work/` only when historical context is needed

## What Just Happened

This cycle shipped two manifesto-load-bearing deltas in order: (1) benchmark tightening to expose a known parity-label cheat; (2) persistence pass-0 — line-oriented save/load + append-only event log + fresh-process round-trip self-test.

### Benchmark tightening (#00a)

`benchmarks/v2_ladder/organic_v0.jsonl` held-out items rewritten:

- **hidden_rule:** `parity:even`/`parity:odd` removed from held-out observations (training kept them as learning material). 2 of 4 test items are now `distractor_rule_transfer` — the trained signal-association (`signal:blue → go`, `signal:red → stay`) directly contradicts the parity rule on those items.
- **abstention:** 2 of 4 held-out items are now `evidence_present` (`topic:arin → "copper"`, `topic:bea → "glass"`) with identical wording shape to the 2 `evidence_absence` items. The "?" target is no longer a domain shortcut.
- **memory:** mem_test_004 → 6-char object + 8-char place (`tavi marble lantern6`).
- **causal_chain:** test_004 effect → 4 chars (`horn`); variance now 4/5/5/6 across test items.
- **language_expression:** test_003 → 7-char name (`quintus`); test_004 → non-greeting (`intent:farewell name:elena → "bye elena"`) — first held-out probe that requires composing an unseen intent with a slot.

### Cheat-collapse quantified (#00b)

| metric | prior cycle (`eval_compositional_slot_pass.json`) | this cycle (`eval_compositional_tightened_persisted.json`) |
|---|---|---|
| overall exact_rate | `0.520000` | `0.360000` |
| hidden_rule | 4/4 = 100% | 2/5 = 40% (cheat exposed) |
| abstention | 5/5 = 100% | 3/5 = 60% (domain-shortcut exposed) |
| by_composition.evidence_present | n/a | 0/2 — model cannot recall arin/bea via abstention wording |
| by_composition.distractor_rule_transfer | n/a | 0/2 — model picks trained signal-association over parity rule |
| by_composition.intent_transfer | n/a | 0/1 — "hi elena" instead of "bye elena" (no path for non-greeting) |

Same brain weights, same state_hash (`3536309de837d3e2`). The benchmark got more honest; the score dropped accordingly. That drop IS the proof.

### Persistence pass-0 (#00c / #00d)

`native/organic_v0.cpp` extended with line-oriented `PXSTATE_V0` format (config + traces + connections + slots + learned-chars + state_hash), bit-exact via hex64-of-IEEE-bits so the state_hash matches across save/load. Three new flags: `--save-state`, `--load-state`, `--event-log`. Three new phases: `persistence-self-test` (parent: train → save → spawn child → verify), `persistence-load-verify` (child: load → generate → emit verdict JSON), and integration into `eval` for load-then-generate-without-training.

**Round-trip evidence** (`run/artifacts/organic-v0/persist_self_test.json`):
- `parent_state_hash: 3536309de837d3e2`, `child_state_hash: 3536309de837d3e2` — bit-exact match
- `parent_raw_output: "milaquart arch6"`, `child_raw_output: "milaquart arch6"` — bit-exact match
- `load_status: save_and_load_verified`
- `scripts/test_organic_v0.sh` now runs BOTH the substrate self-test AND the persistence round-trip; either failure is `set -e` fatal

**Fresh-process eval evidence** (`run/artifacts/organic-v0/eval_compositional_tightened_persisted.json`):
- `persistence.status: loaded_from_disk`
- `persistence.loaded_state_path: run/state/organic-v0/snapshots/raphael-local-0001/cycle_persistence_pass0.pxstate`
- `summary_metrics` IDENTICAL to a from-JSONL training run — proven by `diff` on `summary_metrics + by_composition + model_state_hash`

The organism survives a restart. MANIFESTO §"Persistence Is Pass-0, Not Future Work" is no longer a gap; pass-0 ships.

## Next Cycle Contract

The structural work the brief deferred is now unblocked. The honest baseline is in place and persistence substrate exists, so any new mechanism can be measured against the tightened benchmark AND saved-loaded for inspection without re-running training.

### Candidate structural mechanism — dynamic slot/segment generation

The slot pass-through (prior cycle) is structurally inadequate: it copies typed observation characters at ABSOLUTE output positions learned from training. This fails the moment filler length or separator structure varies — exactly the failure modes the tightened benchmark now exposes (`unseen_filler_long`, `intent_transfer`).

Direction: replace absolute-position slot copying with **learned segment generation**:

- learn segment STARTS (when does a copied slot span begin?)
- learn segment SEPARATORS (what literal characters connect segments?)
- learn segment STOP conditions (when does a span end and the next literal/copy begin?)
- the generator emits a sequence of segment-typed steps; each step is either a literal-learned-char OR a copied slot span; segment-type selection is learned from state, not hardcoded by domain

Sister candidate: **HDC unbinding + cleanup memory** — `unbind(query, role:observation:name) → cleanup → name_atom`, then a per-character emit conditioned on the unbound filler. Honest HDC.

Pick the mechanism via `/pick-one` after re-reading the artifacts.

### Hard gates (unchanged)

Reject any implementation that:

- adds parser-dispatcher logic for benchmark answers
- adds fixed response text as the agent output
- scores itself on subjective quality
- hides bad outputs
- adds new files without a `REPO_CONTROL.md` row in the same commit
- optimizes for "all tests pass" over organic learning
- adds CUDA kernels before the workload justifies parallelism
- ships a structural change without re-running on the tightened benchmark AND verifying the persistence self-test still passes

## Suggested Command Sequence (current state)

```bash
make                                    # build/organic_v0
scripts/test_organic_v0.sh              # substrate guard + persistence round-trip
scripts/eval_organic_v0.sh --mode test --out /tmp/eval_current.json
# OR — load this cycle's saved state and eval without re-training:
build/organic_v0 --phase eval --mode test \
  --load-state run/state/organic-v0/snapshots/raphael-local-0001/cycle_persistence_pass0.pxstate \
  --out /tmp/eval_from_disk.json
jq '{run_id, model_state_hash, persistence, summary: .summary_metrics.overall, by_composition: .summary_metrics.by_composition, failures: [.failure_cases[] | {event_id, domain, composition, raw: .raw_generated_output, expected: .expected_output}]}' /tmp/eval_current.json
git status --short
```

## Follow-up Notes (advisor, not blocking)

- `PXSTATE_V0` line format uses `|` as the field delimiter and trusts benchmark strings are pipe-free. The failure mode if a future benchmark item contains `|` in input/target/observation is `load_serialized_state` throwing on field-count mismatch — detected, not silent. A one-line `assert` in `serialize_state` on encountering `|` would lift this from "throws on next load" to "fails fast at write." Acceptable as-shipped; queue for next cycle if structural work overlaps the serializer.
- Branch `feat/organic-v0-trace-id-ablation` now carries two distinct cycles' commits (cycle 1: trace-id ablation in `dab6e41`; cycle 2: benchmark + persistence in `a1168ec` + `787fe9b`). Branch name is stale relative to its contents. If lain plans to merge as one PR — fine. If as two — branch-split needed; do not act unprompted.

## Close Criteria For The Next Pass

- A structural mechanism (segment generator OR HDC unbinding) that materially improves `unseen_filler` / `unseen_filler_long` / `intent_transfer` scores on the tightened benchmark.
- The mechanism MUST survive the persistence round-trip: trained brain saves, fresh process loads, generates the same outputs bit-exactly.
- No regression on `direct_replay` / `evidence_absence` / `unseen_rule_transfer` (the things the model currently gets right honestly).
- Empty placeholder dirs (`src/project_x_v2/`, `tests/`) either removed or filled with content owning a `REPO_CONTROL.md` row.
- No GPU/CUDA work, no Python answer-path migration, no template wrapper.
