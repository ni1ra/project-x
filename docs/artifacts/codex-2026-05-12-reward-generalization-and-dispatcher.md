# Codex 2026-05-12 - Reward Generalization + Dispatcher False-Confidence Fix

**Run ID:** `codex-2026-05-12-reward-generalization-and-dispatcher`
**Scope:** advance Project X toward the manifesto's organic-learning target without adding new hand-coded domain knowledge.

## Read Coverage

- Full live-doc pass: `docs/PROMPT.md`, `docs/paper.md`, `docs/MANIFESTO.md`, `docs/DO_THIS_NEXT.md`, `docs/A_TO_Z_PLAN.md`, `docs/REPO_CONTROL.md`.
- Artifact inventory pass: `docs/artifacts/*.md`, excluding `docs/past_work/`.
- Artifact steering cluster used for implementation: cycle-13 external audit and priority decision, cycle-14 Hebbian/synthesis/demo docs, cycle-15 B1/B2/B4 docs, `IQ_PROGRESSION.md`.

## Change 1 - Hebbian Prompt Atoms Generalize Across Paraphrases

Before this pass, `HebbianBank` keyed prompt reward by a single first-10-token atom. That made a rating too local: rejecting a bad walk for "tell me a joke about entropy" had no effect on "write a joke about entropy please".

`src/project_x/hdc_infra/hebbian.py` now derives multiple neutral prompt atoms:

- normalized prefix atom for exact prompt-shape memory;
- token atoms for topic/intent overlap;
- adjacent-bigram atoms for weak phrase structure.

`update()` writes the same Hebbian reward delta to every prompt atom paired with each fragment. `lookup_for()` averages across the query prompt atoms. Exact repeats keep the full learned delta; held-out paraphrases sharing only some atoms inherit a smaller signal instead of zero.

Strict-strict thesis status: PASS. This is domain-neutral learning machinery over substrate atoms, not a hand-coded rule for math, poetry, chat, or tools.

## Change 2 - Dispatcher False Confidence Removed

Cycle-14 and cycle-15 docs identified a BG-dispatcher bug: refused or missing-archetype candidates could receive perfect self-similarity and compete at inflated confidence.

`src/project_x/reasoning_agent.py` now:

- stores refused parser outputs separately instead of letting them compete in the confidence sort;
- returns a formal scope-boundary refusal if no valid formal candidate exists and the remaining candidate is only a loose natural-mode walk;
- assigns neutral normalized similarity `0.5` to valid missing-archetype responses instead of `1.0`.

Strict-strict thesis status: PASS. This is confidence plumbing; it adds no model knowledge and no per-domain policy table.

## Verification

Focused learning/dispatcher tests:

```bash
PYTHONPATH=src python3 -m pytest tests/test_reasoning_agent.py tests/test_natural_mode_v0.py tests/test_hebbian_bank.py -q
```

Result: `151 passed in 42.09s`.

Benchmark harness:

```bash
PYTHONPATH=src python3 gpt-codex/benchmark/run_audit.py
```

Result: `48 PASS / 0 FAIL`; rubric-pending entries skipped: `30`.

Reward-transfer replay harness:

```bash
PYTHONPATH=src python3 scripts/reward_transfer_replay.py --output /tmp/project-x-reward-transfer-result.json
```

Result: `pass=true`. Held-out prompt rank for the rejected target fragment moved from `28/49` to `49/49`; score moved from `0.03457` to `-0.58333`; exact lookup on the rated prompt was `-1.0`; transferred lookup on the paraphrase was `-0.58333`.

Full suite:

```bash
PYTHONPATH=src python3 -m pytest --tb=short -q
```

Result: `663 passed, 1 failed in 213.08s`. The failure was the known timing-sensitive `test_write_one_amortized_under_5x_batch` guard (`batch=0.286s`, `incremental=2.261s`, ratio `7.91x`). Immediate isolation rerun passed:

```bash
PYTHONPATH=src python3 -m pytest tests/test_semantic_hdc_memory.py::test_write_one_amortized_under_5x_batch -q
```

Result: `1 passed in 1.17s`.

## Interpretation

This does not make Project X Raphael generally intelligent. It does move the real learning loop forward in two ways:

1. A single audit rating now transfers beyond exact prompt strings, so the reward signal can shape future paraphrases.
2. The dispatcher no longer treats refusal or missing archetypes as perfect confidence, so future learned routing has a cleaner baseline to compete against.

The next highest-leverage work remains data and evaluation: ingest worked examples and conversation/humor material, generate rated walks, then measure whether the bank actually changes held-out behavior on natural prompts.

## Next Actions

1. Add corpus slices for math worked examples and chat/humor so negative ratings have on-topic alternatives to push retrieval toward.
2. Re-run the cycle-15 demo script after these changes and compare confidence + problem-shape changes against the existing artifact.
3. Replace synthetic filler in `scripts/reward_transfer_replay.py` with real rated audit-log volume once enough ratings exist.
