# Phase v2 Organic Substrate — Cycle 5 reflection

**Theme:** Numeric-derived trace activation + relation projection + farewell-curriculum learnability repair
**Closed:** 2026-05-14
**Implementer:** Codex GPT-5
**Continuation completion:** Raphael (Claude Opus 4.7) — finished commits, durable evidence promotion, reflection, and Discord cycle-close after Codex hit OpenAI usage cap mid-ship

## Context

Cycle 4 closed at `0.760` overall (19/25) with four open held-out failure families:

- `unseen_rule_transfer` 1/2 + `distractor_rule_transfer` 0/2 + `evt_rule_test_004` — hidden-rule family (3 events).
- `evidence_present` 0/2 — `evt_abs_test_001` + `evt_abs_test_003` need a `topic:* → object:*` recall channel.
- `intent_transfer` 0/1 — `evt_lang_test_004` expected `"bye elena"` but no training event used `intent:farewell` and no train target contained `"bye"`. Cycle-4 calibration already flagged this as a curriculum learnability bug, not a substrate weakness.

Cycle 4's trace-span-position memory was still trace replay; cycle 5 needed the substrate to *compute over* observations and traces before generation, plus an honest fix to the unlearnable farewell event.

## What shipped

Three independently auditable surfaces. The split is deliberate — collapsing the curriculum repair into the substrate claim is the dishonesty failure mode this reflection refuses.

### (a) Substrate channel #1 — numeric-derived trace activation

Pure numeric observation fillers (`mark:7`, `mark:2`, etc.) now emit deterministic latent feature atoms keyed by computed relations over the value (parity, role-relative numeric identity, role-free parity). At generation, traces sharing a computed relation with the query are activated even when surface fillers (color, signal) differ. The encoder never maps `parity:odd → "stay"`; the existing `connections_` substrate accumulates the answer through ordinary character weights addressed at the parity feature id. Hidden-rule events with unseen mark values now activate the same parity address as their training counterparts.

### (b) Substrate channel #2 — relation projection

During reward, every typed-observation trace writes auxiliary role-to-role projections into the existing `CONNS` substrate, keyed by a deterministic `relation(cue_role, cue_value, target_role)` feature id. A `topic:arin` query that asks for an object-shaped answer can reactivate the learned `person:arin → object:copper` projection without `object:copper` being present in the current observation list. Absent evidence produces no relation feature, so the existing `evidence_absence` abstention path still wins where it should.

Both channels share the cycle-4 lesson: weights live in existing `CONNS`, no new PXSTATE section is mathematically required, and the answer is still emitted character-by-character through the learned generator.

### (c) Benchmark repair — two-example farewell curriculum

`benchmarks/v2_ladder/organic_v0.jsonl` gains two training events:

- `evt_lang_train_004` — `intent:farewell, name:sora → "bye sora"`
- `evt_lang_train_005` — `intent:farewell, name:toma → "bye toma"`

The two-example choice is intentional: one example would teach the lexeme but permit a replay-shaped solution where the substrate emits the exact training name; two distinct names force the brain to learn the replaceable-name structure through the existing learned segment mechanism. Justified in `docs/artifacts/CYCLE5_INTENT_LEARNABILITY_AUDIT.md`.

### Plumbing

Two CONFIG booleans (`use_numeric_derived_features`, `use_relation_projection`) serialize through the PXSTATE CONFIG line; old snapshots default both off on load, new snapshots write both as 1. Two CLI ablation flags (`--ablate-numeric-derived`, `--ablate-relation-projection`) gate each channel for falsification. Documented in `docs/artifacts/PERSISTENCE_SCHEMA.md`.

## Measurement

The two-claim split is load-bearing. Substrate-only on the un-repaired fixture is the structural claim; the repaired-fixture 25/25 is substrate + a justified data repair.

| metric | cycle 4 | cycle 5 substrate-only (old fixture) | cycle 5 repaired |
|---|---:|---:|---:|
| overall exact_rate | 0.760 | **0.960** | **1.000** |
| exact events | 19/25 | **24/25** | **25/25** |
| `unseen_rule_transfer` | 1/2 | 2/2 | 2/2 |
| `distractor_rule_transfer` | 0/2 | 2/2 | 2/2 |
| `evidence_present` | 0/2 | 2/2 | 2/2 |
| `intent_transfer` | 0/1 | 0/1 | 1/1 |
| existing solved families | held | held | held |

- Final repaired-benchmark headline: `run/artifacts/organic-v0/eval_compositional_v2c5.json` — state hash `ccd7a48ec4614703`, config hash `de2ad1690588249d`.
- Substrate-only on un-repaired fixture (final binary): `run/artifacts/organic-v0/eval_cycle5_substrate_only_old_fixture.json` — state hash `b968647c92f30c57`, single failure `evt_lang_test_004` (the by-design unlearnable farewell).

## Falsification (ablation evidence)

The two channels carry two distinct families. The ablations are clean:

| run | flag | exact | failures isolate to |
|---|---|---:|---|
| `eval_cycle5_ablate_numeric.json` | `--ablate-numeric-derived` | 22/25 (0.880) | `evt_rule_test_001`, `evt_rule_test_003`, `evt_rule_test_004` (hidden_rule family) |
| `eval_cycle5_ablate_relation.json` | `--ablate-relation-projection` | 23/25 (0.920) | `evt_abs_test_001`, `evt_abs_test_003` (evidence_present family) |

Numeric-channel-off does not regress evidence-present; relation-channel-off does not regress hidden-rule. The ablations are *the* answer to "is this a structural mechanism or a re-skinned scalar tune?".

## Backward compatibility

`/tmp/cycle2.pxstate` (snapshot from worktree at `78291d1`) still loads under the cycle-5 binary at `0.360` exact_rate (9/25), state hash `3536309de837d3e2`, with the cycle-2 failure signature `evt_mem_test_001` raw `"milaquart arch6"`. The two new CONFIG fields default off when absent from a legacy snapshot, so cycle-5 reads of older state do not silently flip the answer path.

## Persistence verification

- `run/artifacts/organic-v0/eval_compositional_v2c5_from_disk.json`: fresh-process eval loaded from `run/state/organic-v0/snapshots/raphael-local-0001/v2c5.pxstate`; `summary_metrics + model_state_hash` diff-clean against the from-training eval.
- `run/artifacts/organic-v0/persist_self_test_v2c5.json`: `save_and_load_verified`, parent/child hash `ccd7a48ec4614703`, parent/child raw_output `"mila quartz pier6"`.
- `make test`: substrate self-test + persistence round-trip both PASS; round-trip hash `ccd7a48ec4614703` matches output `"mila quartz pier6"`.

## What still fails / what was NOT addressed

Be specific about scope:

- **Broad language semantics** is not learned from two farewell examples. The cycle solves `intent:farewell → "bye <name>"` for held-out names; it does not solve "what other intents exist" or "what other lexemes belong with what intents".
- **Relational reasoning beyond the typed `person → object` projection** is not addressed. The relation projection is symmetric in mechanism (any cue role to any target role through stored typed traces) but only `person → object` is exercised by the benchmark. Held-out questions asking for `place` / `effect` from a `topic:*` cue are cycle-6 work.
- **Arbitrary computed-rule reasoning** is not addressed. The numeric-derived channel ships parity, role-local numeric identity, role-free parity, and last-digit features — *one specific family* of computed relations. Threshold, equality, modular class, sequence-position, and other relations are all "the next thing if this cycle's mechanism generalizes". The cycle-6 contract names this directly.
- The `intent_transfer` win is a substrate × curriculum-repair compound. The substrate on its own does not solve `evt_lang_test_004` — the un-repaired fixture probe is the proof.

## Five-question self-audit

**1. What can my substrate now compute that it could not compute before?**

It can derive a parity address from a numeric observation slot and route training evidence through that address, so unseen mark values activate the same address as their parity-equivalent training neighbours. And during reward it now writes role-to-role projection weights into ordinary `CONNS`, so a `topic:arin` cue at test time can recall a learned `person:arin → object:copper` association without `object:copper` being present in the observation list. Cycle 4 could only replay traces and copy visible role fillers; cycle 5 can compute over a value and project across roles.

**2. If a frontier researcher (Hassabis / Karpathy / Schmidhuber) read this diff cold, what would impress them, and what would they roll their eyes at?**

Karpathy would notice the ablations cleanly isolate which channel carries which failure family — that is a real falsification ladder, not a vanity number. Hassabis might appreciate that the relation projection writes into the same character substrate as the rest of the generator, so absent evidence still routes through the existing abstention path without a special branch. Schmidhuber would press hard on the parity feature being one specific computed relation, and would reasonably ask whether the channel generalizes to threshold, equality, modular class, or position-relative relations — it does not, in the current benchmark, and the cycle-6 contract names that gap directly. None of them would mistake this for "the substrate now reasons"; the impressive part is the falsification gear, not the score.

**3. Which of the four open failure modes does this NOT address?**

It addresses all four families that were measurably open at cycle-4 close — hidden_rule, evidence_present, distractor_rule, intent_transfer — but only within the relations the benchmark exercises. Hidden-rule outside parity is unaddressed; evidence-present in target roles other than `object` is unaddressed; distractor-rule beyond the cycle-4 distractor list is untested. The "open failure modes" framing flatters the cycle; the honest framing is that the cycle solved the four families the v2 ladder rung exposes, and the same families would re-open under a wider rung.

**4. Where in the diff is the load-bearing line? If I deleted it, what specifically would break, and what would the metric collapse to?**

The two new feature-id emission paths in `native/organic_v0.cpp` are the load-bearing surfaces. Deleting the numeric-derived feature emission collapses overall to 22/25 (0.880) and reopens `evt_rule_test_001/003/004`; deleting the relation-projection write at reward time collapses overall to 23/25 (0.920) and reopens `evt_abs_test_001/003`. The ablation flags exist precisely to make this question mechanically answerable instead of rhetorical — the answer is in the on-disk artifacts.

**5. What is the smallest experiment that would falsify the claim that the mechanism is structural and not a re-skinned scalar tune?**

The two ablations on the same repaired fixture are that experiment in their current form: turn each channel off and watch the metric collapse to a *different family* of failures. Re-skinned scalar tunes do not produce family-specific regressions. The next falsification step — queued for cycle 6 — is the rule-family generalization probe: add a held-out hidden-rule event keyed on a non-parity computed relation and check whether the numeric-derived channel transfers without re-training. If it does not, the channel is parity-specific; if it does, the mechanism is computed-relation-general.

## Codex's audit-trail of in-flight corrections

Surfacing the in-flight history because audit-honest reflections preserve evidence of self-correction rather than sanitizing it:

- **Numeric ablation correction**: an early Discord post quoted the numeric-channel-off result as 21/25 (0.840). Codex re-ran and corrected to 22/25 (0.880); the durable artifact uses the corrected number. The corrected number is the one this reflection cites everywhere.
- **Source-priority + role-presence patches were tried then rolled back**: a transient binary version added two patches between the substrate ship and the final eval. Probe re-runs under the final binary against the un-repaired fixture (`b968647c92f30c57`) match the in-flight probe hash bit-for-bit, confirming the rollback was clean and the patches were no-ops at the eval boundary. The audit gap closed without surprise.
- **One-vs-two farewell example shift**: the first repair attempt added a single farewell train event; on review (in `CYCLE5_INTENT_LEARNABILITY_AUDIT.md`) Codex shifted to two distinct names to prevent a replay-shaped solution from passing the held-out event for the wrong reason.

These are evidence of in-flight discipline, not embarrassments.

## Continuation handoff (Raphael, Opus 4.7)

Codex shipped substrate, ablations, eval/from-disk/persist verification, and four updated docs to disk before hitting cap. Continuation completion did:

1. On-disk audit — `git status` + final-eval `jq` + `make test` all matched the transcript exactly (hash `ccd7a48ec4614703`, 25/25, 0 failures, persistence round-trip pass).
2. Promoted three /tmp evidence files to durable paths under `run/artifacts/organic-v0/` and updated `docs/REPO_CONTROL.md` + `docs/DO_THIS_NEXT.md` + `docs/artifacts/CYCLE5_RELATIONAL_BINDING.md` to reference the durable paths.
3. Re-ran substrate-only on the un-repaired fixture under the final binary to close the only audit gap (probe2 was generated at a transient build state); the result `b968647c92f30c57 / 0.960 / failure=evt_lang_test_004` matched the prediction exactly.
4. Wrote this reflection.
5. Shipped three atomic commits (substrate + benchmark repair + sha7 chore), no push — lain pushes.
6. Posted Discord cycle-close.

No mechanism added or modified during continuation. The substrate is exactly what Codex shipped.

## Self-impression score

**417 / 420.**

Codex's provisional was 418; my independent audit lands one point lower. The cycle is excellent — clean two-channel substrate, clean falsification ladder, honest two-claim split, learnability audit before benchmark edit, persistence + backward-compat verified. Not 419 because the numeric-derived channel ships one specific computed-relation family (parity + numeric identity + last-digit) and the cycle-6 contract is where the structural-vs-parity-specific question gets answered; the present cycle has produced the falsification gear that *will answer* that question, not the answer itself. Not 420 because 420 means the substrate teaches the auditor something genuinely new about how associative computation generalizes, and what cycle 5 demonstrates is that *given the right address*, the existing generator routes evidence to the right answer — which is correct and load-bearing, but is the floor of what cycle 6 will be standing on, not its ceiling.

## Next cycle direction

`docs/DO_THIS_NEXT.md` cycle-6 contract names three:

1. **Generalize the rule substrate beyond parity** — add a hidden-rule mini-suite with at least two different computed relations; close criterion = ablations prove which derived relation carries which gain.
2. **Generalize relation projection beyond `topic → object`** — held-out questions asking for `place`/`effect` from different cue roles, with absent-evidence controls; close criterion = projection works across at least two target roles while `evidence_absence` stays exact.
3. **Promote to a harder benchmark rung** — local hidden-rule game or ARC-style micro-harness where the organism explores or infers a rule from sequences, not just train/eval JSONL.

Hard gates carry forward: keep old-fixture vs repaired-fixture claims separate; keep ablation flags working; do not claim broad language understanding from two farewell examples; do not add benchmark train examples without a learnability audit naming the missing evidence; preserve persistence diff-clean and legacy snapshot compatibility.
