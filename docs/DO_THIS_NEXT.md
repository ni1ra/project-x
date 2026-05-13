# Do This Next - Project X v2

Generated: 2026-05-13 (post cycle-3 ship — learned segment generation lifted composition 0.36 → 0.68)

## Read First

1. `docs/MANIFESTO.md`
2. `docs/A_TO_Z_PLAN.md`
3. `docs/REPO_CONTROL.md`
4. `docs/artifacts/PERSISTENCE_SCHEMA.md`
5. `docs/artifacts/CYCLE3_MECHANISM.md` — the cycle-3 architecture lock, advisor verdict, and Builder-Law boundary call
6. `docs/past_work/cycles/phase_v2_organic_substrate/dev-cycle-3.md` — what shipped, what regressed, what's queued for cycle 4
7. `docs/past_work/` only when historical context is needed

## What Just Happened

Cycle 3 produced the first cycle where the organism's *cognitive layer* exhibited measured generalization beyond memorization. The learned segment generation mechanism (picked over HDC unbind+cleanup via /pick-one 405/420 after explicit advisor boundary-call) extended the brain's action space from literal-char emission to literal-char-OR-start-copy-from-typed-observation-role. Mode-switch decisions live in the same learned softmax substrate as literal emission — no parser-dispatcher, no authored role-routing. The substring-match in `learn()` is training-time supervision routing, not authored capability at inference (advisor cleared this explicitly).

### Headline result (`run/artifacts/organic-v0/eval_compositional_v2c3.json`)

| metric | cycle 2 baseline | cycle 3 | delta |
|---|---|---|---|
| overall exact_rate | 0.360 | **0.680** | **+0.32 (+89%)** |
| `unseen_filler` | 0/8 = 0% | **8/8 = 100%** | **+100%** |
| `unseen_filler_long` | 0/2 = 0% | **2/2 = 100%** | **+100%** |
| `unseen_filler_short` | 1/1 = 100% | 1/1 = 100% | held |
| `direct_replay` | 5/5 = 100% | 3/5 = 60% | **-40% (REGRESSION)** |
| `evidence_absence` | 2/2 = 100% | 2/2 = 100% | held |
| `unseen_rule_transfer` | 1/2 = 50% | 1/2 = 50% | held |
| `intent_transfer` | 0/1 = 0% (seq_ratio 0.706) | 0/1 = 0% (seq_ratio 0.706) | held |
| `evidence_present` | 0/2 = 0% | 0/2 = 0% | held |
| `distractor_rule_transfer` | 0/2 = 0% | 0/2 = 0% | held |

State hash: `4962e498de53e6c4` (cycle 2's `3536309de837d3e2` preserved bit-exactly when `use_segment_mode=0`).

### Persistence (cycle-3 #00e gate)

- `run/artifacts/organic-v0/persist_self_test_v2c3.json`: `hash_match: true`, `output_match: true`, `load_status: save_and_load_verified`. Bit-exact parent/child hash + bit-exact parent/child raw_output `"mila quartz pier6"` (an unseen_filler test event the brain now solves cleanly).
- `run/artifacts/organic-v0/eval_compositional_v2c3_from_disk.json`: fresh-process eval loaded from disk, `diff` against eval-from-JSONL on `summary_metrics + model_state_hash` is empty. Proves ROLES + SEGMENT_CONNS sections serialize and load cleanly.

### Honest regression preserved

The `direct_replay` regression 5/5 → 3/5 is the cycle-3 cost. Two failures, two distinct mechanisms:

1. `evt_mem_dev_000`: expected `"arin copper tray4"`, got `"arin copper copper copper copper copper copper c"`. Role-ordering failure at the third segment. Bucket-feature transfer doesn't discriminate role:object from role:place strongly enough at deep segment indices.
2. `evt_causal_dev_000`: expected `"bell"`, got `"go"`. Cross-domain literal contamination — segment-mode did NOT fire here; a hidden_rule literal won in the causal_chain domain.

These are NOT substring-match false-positives (the architecture's pre-mortem watchlist mitigation doesn't apply). They are different failure-mode families. Cycle 4 scope.

## Next Cycle Contract — cycle 4

The structural mechanism cycle is done; cycle 4 closes the residual failure_cases that cycle 3 did not solve. Three candidates compete via `/pick-one` at cycle open (ground in the SAME tightened-benchmark `failure_cases`, not theory):

### Candidate A — Role-ordering discrimination at deep segment indices

**Targets:** `evt_mem_dev_000` direct_replay regression. Affects: 1 of 16 prior failures (the new regression).

**Mechanism sketch:** Add a per-segment-index feature to the state-features that the mode-switch substrate consumes. Currently `state_features(features, previous, position)` builds (pos, prev, bucket, ctx) features. Add a fifth derived feature: `segment_index_so_far` — the count of mode-switches that have fired in this generation. Train events with 3 segments learn mode-switch=role:place specifically at segment_index_so_far=2; test direct_replay events at the same segment index transfer the discrimination.

**Risk:** the segment_index_so_far feature is only known at GENERATE time (it depends on how many mode-switches fired so far in this generation). Training-time learning needs to compute the SAME segment-index at the supervision-routing step — straightforward (the substring-match walks fillers in order).

### Candidate B — Domain-gating for literal answers

**Targets:** `evt_causal_dev_000` direct_replay regression. Affects: 1 of 16 prior failures.

**Mechanism sketch:** Amplify the domain-feature's contribution to literal-char emission weights. Currently `context_features` adds an "obs" feature for each observation token, with weight `context_gain`. Add a domain-discriminator feature with higher weight when the input's domain markers (e.g., `seed:` for memory, `signal:` for hidden_rule, `sound:` for causal_chain) are present in the observation tokens.

**Risk:** domain-discriminator is close to a parser-dispatcher if implemented carelessly. The honest version: increase context_gain for observation tokens that match a small set of domain-marker prefixes (still learned weights, just with higher scale).

### Candidate C — Intent → literal-prefix learning

**Targets:** `evt_lang_test_004` intent_transfer ("hi elena" vs "bye elena"). Affects: 1 of 16 prior failures.

**Mechanism sketch:** Boost intent atoms' feature contribution specifically for early-position literal emission so `intent:farewell` → "bye" wins over the stronger `name:elena` association → "hi" bigram. Specifically: the prev-and-pos-bound feature for prev=kStart should weight intent observation tokens more heavily than other context tokens.

**Risk:** if intent atom's weight is bumped globally, may regress other domains. Need scoped boost (only at pos=0 / pos<3).

### Hard gates (unchanged from cycle 3)

Reject any implementation that:

- adds parser-dispatcher logic for benchmark answers
- adds fixed response text as the agent output
- scores itself on subjective quality
- hides bad outputs
- adds new files without a `REPO_CONTROL.md` row in the same commit
- optimizes for "all tests pass" over organic learning
- adds CUDA kernels before the workload justifies parallelism
- ships a structural change without re-running on the tightened benchmark AND verifying the persistence self-test still passes

### Close criteria for cycle 4

- Material improvement on at least ONE of: `direct_replay` (back to ≥ 4/5), `intent_transfer` (1/1), `evidence_present` (1/2). "Material" = the lift is honest (no benchmark-tightening regression covering it).
- No regression on cycle-3 gains: `unseen_filler` 8/8 must hold; `unseen_filler_long` 2/2 must hold.
- Persistence round-trip still survives (diff-clean eval-from-disk vs eval-from-JSONL).
- REPO_CONTROL rows co-land for any new artifacts.

## Suggested Command Sequence (current state)

```bash
make test                               # substrate guard + persistence round-trip (segment-mode on)
scripts/eval_organic_v0.sh --mode test --out /tmp/eval_current.json
# OR — load this cycle's saved state and eval without re-training:
build/organic_v0 --phase eval --mode test \
  --load-state run/state/organic-v0/snapshots/raphael-local-0001/v2c3.pxstate \
  --out /tmp/eval_from_disk.json
jq '{exact: .summary_metrics.overall.exact_rate, by_composition: .summary_metrics.by_composition, segment_mode_switches: [.events[]|.generation.segment_mode_switch_count]|add}' /tmp/eval_current.json
jq '.failure_cases' run/artifacts/organic-v0/eval_compositional_v2c3.json
git status --short
```

## Follow-up Notes (advisor, not blocking)

- **kMaxRoles overflow** is fail-fast (throws); current benchmark uses ~6 roles, headroom is 10. If benchmark v3 adds new role types beyond 16, bump the compile-time constant. Serialized state forward-compatible (role_id is a stable hash, not an index).
- **segment_mode_gain calibration** ended at 0.3 (started at 5.0; 1.5 didn't help; 0.3 produced correct spaced output). The right value is "high enough to make mode-switches competitive at segment-starts via bucket transfer, low enough that fully-feature-matched literal chars win at post-filler positions." Worth re-measuring if cycle 4 changes the feature topology.
- **Branch name** `feat/organic-v0-trace-id-ablation` now carries cycle 1 + 2 + audit + cycle 3 — increasingly stale. If a PR rollup is planned, branch-split decision needs lain input; do not act unprompted.
- **GenerationStep evidence:** new `is_mode_switch`, `is_copy_emit`, `copy_role` fields preserved in eval artifacts but not yet exported into the JSON output structure for inspection. Cycle 4 may want to surface these in `failure_cases` for deeper diagnostics.

## Close Criteria For The Next Pass

- A targeted mechanism (one of the three candidates above) that materially improves at least one of the residual failure modes.
- The mechanism MUST survive the persistence round-trip on the new state (any added connection-features, atoms, or per-segment counters).
- No regression on `unseen_filler` 8/8, `unseen_filler_long` 2/2, `unseen_filler_short` 1/1, `evidence_absence` 2/2.
- Empty placeholder dirs (`src/project_x_v2/`, `tests/`) either removed or filled with content owning a `REPO_CONTROL.md` row (carried from cycle 2, still open).
- No GPU/CUDA work, no Python answer-path migration, no template wrapper.
