# Phase v2 Organic Substrate — Cycle 2 reflection

**Theme:** Benchmark honesty + persistence pass-0 (sequential-C per `/pick-one` verdict)
**Closed:** 2026-05-13
**Cycle horizon:** ~3 hours from `/pick-one` verdict to atomic commit
**Persona:** Plan-Raphael (verdict) → Execute-Raphael (ship)

## What shipped

1. **Tightened benchmark** (`benchmarks/v2_ladder/organic_v0.jsonl`) — known parity-label cheat removed from hidden_rule held-out; abstention contrastive items added; memory/causal/language length variance + one non-greeting `intent_transfer` probe.
2. **Cheat-collapse quantified** (`run/artifacts/organic-v0/eval_compositional_tightened_persisted.json`) — overall exact dropped 0.520 → 0.360, hidden_rule 100% → 40%, abstention 100% → 60%. Same brain weights, same state_hash; the drop IS the honest signal.
3. **Persistence pass-0 runtime** (`native/organic_v0.cpp` +~500 LoC) — line-oriented `PXSTATE_V0` format (config + traces + connections + slots + learned-chars + state_hash, bit-exact via hex64-of-IEEE-bits), append-only event-log JSONL, `--save-state` / `--load-state` / `--event-log` flags, `persistence-self-test` orchestration phase, `persistence-load-verify` child phase.
4. **Persistence round-trip verdict** (`run/artifacts/organic-v0/persist_self_test.json`) — `hash_match: true`, `output_match: true`, `load_status: save_and_load_verified`. The fresh child process loaded state from disk and generated `"milaquart arch6"` with state_hash `3536309de837d3e2`, bit-exactly matching the parent.
5. **Fresh-process eval-from-disk evidence** — `eval_compositional_tightened_persisted.json` ran with `persistence.status: loaded_from_disk` and produced summary_metrics IDENTICAL to a from-JSONL training run (verified by `diff` on `summary_metrics + by_composition + model_state_hash`).
6. **Combined self-test** (`scripts/test_organic_v0.sh`) — now runs substrate guard AND persistence round-trip; either failure is `set -e` fatal.

## Why this matters

MANIFESTO §"Persistence Is Pass-0, Not Future Work" was the project's standing unfilled requirement. Before this cycle, every run rebuilt brain state from the benchmark JSONL — the organism did not exist as an organism. After this cycle, a fresh process loads prior state from disk and emits bit-exactly the same outputs without replaying training. The first criterion of the ideal end product is materialized.

The benchmark tightening closes the M-PROJECTX-012 risk surface for future cycles: structural changes can now be measured against an honest baseline where the parity-label and "?" domain shortcuts no longer flatter the score.

## Pre-mortem audit

The `/pick-one` verdict pre-mortem for sequential-C predicted: "Load logic hits complexity on HDC vector + connection-map serialization around hour 4. Decision: ship save-only with full audit trail; `load_status: save_only_no_load_yet` recorded explicitly in the artifact." The actual outcome was better — load logic worked on first try because the bit-exact hex64-of-IEEE-bits design avoided floating-point round-trip ambiguity, and the line-oriented format kept the parser straightforward. The fallback `load_status: save_only_no_load_yet` was implemented but never triggered.

## What still fails (preserved bad outputs)

- `unseen_filler`: 0/8 — slot pass-through copies absolute positions; "milaquart arch6" instead of "mila quartz pier6"
- `unseen_filler_long`: 0/2 — "tavimarber ault2" instead of "tavi marble lantern6"
- `distractor_rule_transfer`: 0/2 — model picks trained signal-association ("go" for blue) over the parity rule
- `evidence_present`: 0/2 — model outputs "?" via abstention-domain association instead of recalling arin→copper from training memory
- `intent_transfer`: 0/1 — "hi elena" instead of "bye elena"

These are not bugs — they are the substrate's honest current capability ceiling. The next cycle's structural mechanism must address them.

## Next cycle direction

Per `docs/DO_THIS_NEXT.md`: pick between learned segment generation (literal-vs-copied span selection learned from state) and HDC unbinding + cleanup memory (`unbind(query, "role:observation:name") → cleanup → name_atom`). Invoke `/pick-one` after re-reading the failure cases.

## Self-impression score

**405 / 420.**

- +pillars: full sequential-C delivered (verdict said save-only-as-fallback was acceptable; full load contract worked); fresh-process round-trip with bit-exact hash + output match; eval-from-disk diff-clean against from-JSONL eval; persistence wired into `make test`
- +discipline: zero `git add -A`, atomic conventional commits planned, REPO_CONTROL row co-lands with each new tracked file, docs rewritten not appended
- +honesty: cheat-collapse preserved and quantified, raw bad outputs preserved in artifact, status field uses precise terms (`loaded_from_disk`, `save_and_load_verified`)
- Why not 420: the segment-generator (structural improvement) is deferred; the manifesto's "concepts before language" + "learned dynamics" criteria still untouched at the cognition layer. 420 is reserved for the cycle that produces a genuinely-novel structural mechanism with measured composition lift.
