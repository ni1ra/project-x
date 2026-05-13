# Do This Next - Project X v2

Generated: 2026-05-13 (post trace-id ablation)

## Read First

1. `docs/MANIFESTO.md`
2. `docs/A_TO_Z_PLAN.md`
3. `docs/REPO_CONTROL.md`
4. `docs/past_work/` only when historical context is needed

## What Just Happened

The first round of organic-v0 measurement produced a 95.6% exact-rate eval (22 / 23). External critique (lain + Claude + Codex) converged on the diagnosis that this score is theater — 22 of 23 eval items are near-duplicates of training, only one (`evt_lang_test_004`, the "lina" probe) requires composition with an unseen filler, and it failed.

Both Claude and Codex agreed the cheapest, highest-information first move was a **trace-id ablation**: gate the per-event-id feature (`hash_pair("trace", event_id)`) behind a `Config.use_trace_id_feature` flag and run eval twice. Predicted outcome (advisor + Claude): exact rate would collapse to <10%, proving the system was almost entirely retrieval-keyed replay.

### Ablation result

| metric | with trace-id | without trace-id |
|---|---|---|
| `model_state_hash` | `5a870dad7f70de83` | `35b32e4c2790826a` (genuinely different model) |
| overall exact rate | **0.956522** | **0.956522** (identical) |
| count | 23 | 23 |
| random baseline | 0.043478 | 0.043478 |
| failure case | `evt_lang_test_004`: "hi mira" | `evt_lang_test_004`: "hi sora" (novel, never in train) |
| by_domain | memory/causal/rule/abstention 100%, language 80% | identical |
| by_level | 0,1,3 100%; level-2 83% | identical |

Artifacts:
- `run/artifacts/organic-v0/eval_with_trace.json` (run_id `organic-v0-eval-20bc1ccc037b`)
- `run/artifacts/organic-v0/eval_no_trace.json` (run_id `organic-v0-eval-f8f88c89de09`)

### What the ablation actually revealed

The trace-id feature is **redundant**, not load-bearing. The system retains identical performance without it. The honest load-bearing replay mechanism lives elsewhere — in the `state_features()` function's position-bound bigram chains: `combine(pos_id, prev_id)` (gain 1.35), `(token-feature × position)`, `(token-feature × previous-char)`. Cutting trace-id removes ~7-8 score points from each character's top score (compare with-trace pos-0 `h=30.47` to no-trace pos-0 `h=22.53`) but does not change the argmax orderings.

The position-3 fork is the most telling. With trace-id, `m=15.71 vs s=15.55` (mira wins by 0.16). Without trace-id, `s=11.76 vs m=11.49` (soren wins by 0.27). The trace-id feature was tilting one narrow fork; everything else stayed the same. Position-6 still picks `a` (mira's tail) over `e` (soren's tail) regardless — the `a` bias is purely in the position-bound bigram chain.

Honest reframing of the failure: with trace-id, the system replays the bit-for-bit training string "hi mira" for an input containing "lina". Without trace-id, it produces "hi sora" — a string never seen in training, a 4-character blend of soren's `sor` prefix and mira's `a` suffix. That is arguably the first **emergent organic output** in the project — wrong, but learned-from-state, not retrieved.

### What this means for the architecture

The HDC encoder binds role-filler structure (`add_bound("role:input", ...)`, `add_bound("role:observation:i", ...)`) but **never unbinds**. The bound vector is collapsed to a 256-d cosine-similarity key. The literal characters of the input observation `name:lina` are never plumbed into the generator's output path. The generator only sees `intent:greet`'s position-bound character chain, which is memorized from the two training names.

The system is doing **context-keyed Markov memorization with HDC retrieval as auxiliary biasing**. It is not doing slot-filling, role-filler unbinding, concept abstraction, or composition. Calling the HDC vector a "memory spine" is currently misleading — it is a hash function.

## Revised Priority Order (after ablation)

Both Claude and Codex agreed on this order. The ablation result confirms steps 1-2 are already accomplished; steps 3+ are the next-cycle actions.

1. ✅ **Run trace-id ablation.** Done.
2. ✅ **Produce eval_with_trace.json vs eval_no_trace.json.** Done.
3. ✅ **Treat the delta as the real diagnostic.** Done — the delta is "the trace-id was not the leak; the position-bound bigram chain is."
4. **Redesign benchmark probes so at least half require unseen fillers / composition.** Currently 1 of 23 (4.3%) requires composition. Target: ≥50% per domain. Per-domain candidates:
   - memory: novel `(person, object, place)` triples never co-occurring in train; recall must produce literal characters from observations
   - hidden_rule: signals + colors not in train; rule must transfer abstract structure
   - causal_chain: novel cause/middle/effect chains; effect must be predicted, not pair-memorized
   - language_expression: ≥5 novel name fillers for greet; abstention and accept/decline tested with novel intent wording
   - abstention: novel topics; require the model to detect lack-of-evidence by absence of activation, not by matching a `support:missing` marker token
5. **One structural change.** Direction now clearer: the generator must consume the input's literal observation characters. Two honest paths:
   - **(a) HDC unbinding + cleanup memory.** `unbind(query, "role:observation:name") → cleanup → name_atom`, then a per-character emit conditioned on the unbound filler. Honest HDC.
   - **(b) Slot-typed observation pass-through.** Generator reads typed observation strings (e.g., `name:lina`) as candidate fillers for output positions. Closer to a template but only at the substrate level — the WHEN-to-fill is still learned.
   - Pick after the redesigned benchmark is in place. Picking now picks the wrong fix.
6. **Defer CUDA kernels** until the workload justifies parallelism. Current scale: ~40 traces, 23 eval items. CPU is fine for orders of magnitude more before GPU is justified.
7. **Promote persistence / state serialization to manifesto requirement.** Already done in `docs/MANIFESTO.md` (new "Persistence Is Pass-0, Not Future Work" section). Pass-0 spec:
   - append-only event log on disk
   - serializable learned state with state hash
   - load-state + ingest-one-event + emit, without re-running full training stream
   - artifact records both the loaded state path and the appended event log path

## Hard Gates (unchanged from prior cycle)

Reject any implementation that:

- adds parser-dispatcher logic for benchmark answers
- adds fixed response text as the agent output
- scores itself on subjective quality
- hides bad outputs
- creates many files before one honest organism loop exists
- optimizes for "all tests pass" over organic learning
- adds CUDA kernels before the workload justifies parallelism
- ships a structural change without first re-running on the redesigned compositional benchmark

## Suggested Command Sequence (current state)

```bash
make
scripts/test_organic_v0.sh
scripts/eval_organic_v0.sh --mode test --out run/artifacts/organic-v0/eval_with_trace.json
scripts/eval_organic_v0.sh --mode test --out run/artifacts/organic-v0/eval_no_trace.json --ablate-trace-id
jq '{run_id, model_state_hash, exact: .summary_metrics.overall.exact_rate, failures: [.failure_cases[] | {event_id, raw: .raw_generated_output, expected: .expected_output}]}' run/artifacts/organic-v0/eval_no_trace.json
git status --short
```

## Close Criteria For The Next Pass

- Benchmark redesigned. Each domain has ≥50% held-out items requiring unseen fillers or unseen rule transfer.
- The new benchmark's exact rate on the unchanged organic-v0 is reported honestly. If it collapses (likely), that delta is the honest baseline for any future structural claim.
- One structural change implemented (HDC unbinding + cleanup memory OR slot-typed observation pass-through), with run on both old and new benchmarks for comparison.
- Persistence Pass-0 designed but not necessarily implemented this cycle — at minimum, the event-log schema and state-serialization schema are written in `docs/` and the artifact format is extended to reference them.
- Empty placeholder dirs (`src/project_x_v2/`, `tests/`) either removed or filled with content that owns a `REPO_CONTROL.md` row.
- No GPU/CUDA work, no Python answer-path migration, no template wrapper.
