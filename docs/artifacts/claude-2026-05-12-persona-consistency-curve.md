# Claude 2026-05-12 — Persona Consistency Learning Curve

**Run ID:** `claude-2026-05-12-persona-consistency-curve`
**Scope:** Step 2 of the 2026-05-12 Codex/Claude pass — advance ONE new
Terminus axis with a measured 5-checkpoint cumulative-rating curve.
**Axis chosen:** persona consistency (the manifesto Terminus's "persona
consistency + sense of humor" dimension), measured as a **mechanical
proxy** (marker frequency in retrieved walk text). This is permitted
under M-PROJECTX-014 because no subjective grade is claimed; only
counted occurrences of a fixed marker set are reported.

## Why persona, not the other four candidates

Considered (with leverage estimates 1-10):

| Candidate | Leverage | Decision |
|---|---|---|
| (A) Persona consistency proxy | 8 | **Picked.** Most direct test of the strict-strict thesis on a NEW axis. Substrate-wide Hebbian update was claimed to generalize across topic; this tests whether the same loop generalizes across STYLE on held-out prompts. Mechanical-proxy framing avoids the M-PROJECTX-014 subjective firewall. Persona is an explicitly-named Terminus dimension. |
| (B) Composition via bind+bundle | 6 | Skipped this pass. Requires extending the `compose()` walk to bind composite hypervectors and surface them — touches the substrate's emit path, not just the reward loop. Higher value once the reward loop's generalization is established (this pass). |
| (C) Sandbox infrastructure | 7 | Skipped this pass. Real value but no measurement curve attached — sandbox is platform work, not a learning demonstration. Belongs to a dedicated cycle. |
| (D) Multi-hop K-rollout reasoning | 7 | Skipped this pass. Hand-curated 15-prompt test set is risky in a 60-min budget. |
| (E) Real corpus scale-out | 5 | Skipped this pass. I/O bound; would crowd out a measurement on the existing corpus. |

## Design

**Markers (12, fixed up-front).** Drawn from `src/project_x/persona/voice.py`'s
`VOICE_MARKERS` (Notice / Affirmative / Inquiry / Solution / Proposal /
Understood / Evidence / Anomaly) plus four calm-analytical words the
manifesto attaches to Raphael (Wisdom / Knowledge / Consider / Observe).
Word-boundary regex, case-insensitive. Counted per walk's concatenated
fragment text.

**Training prompts (8, used during ratings).** All "comment on / consider
/ what should one think about / describe X" shapes — calm-philosophy
flavored, picked because the corpus surface most likely to carry marker
vocabulary is Aurelius / Plato / Aristotle / Tao Te Ching / Confucius /
Darwin (already in the Tier-2 ingest).

**Held-out prompts (5, NEVER seen during rating).** Same shape; disjoint
topics (courage, time, excellence, memory, truth). Any held-out marker
shift is substrate-wide generalization — the only overlap with training
is the bigram-atom overlap of the shared shape ("consider the …",
"what is the nature of …"), which is exactly the substrate-wide
Hebbian atom family that the prior pass shipped.

**Rating policy.** For each rated walk: count markers; APPROVE if marker
count is at-or-above the batch median AND > 0; REJECT otherwise. Median
recomputed per checkpoint batch so the threshold is stable. All ratings
flow through `AuditLog.apply_rating` — no direct `HebbianBank.update`
in the script, satisfying the brief's "no hand-edited Hebbian bank"
constraint.

**Curve checkpoints.** `[0, 5, 15, 30, 60]` cumulative ratings. At each
checkpoint, a fresh `NaturalModeComposer` is reconstructed from the
saved bank pickle so the measurement reflects on-disk persisted state,
not in-process state.

**Composer config.** `domain="all"`, `max_fragments=3`, deterministic.

## Measured Result

Command:

```bash
PYTHONPATH=src python3 scripts/persona_consistency_curve.py
```

Result: `pass=true`. Curve:

| k | bank_entry_count | mean_marker_count | fraction_with_any_marker | mean_marker_density |
|---|---|---|---|---|
| 0 | 0 | 0.20 | 0.20 | 0.0057 |
| 5 | 168 | 0.80 | 0.80 | 0.0095 |
| 15 | 387 | 1.00 | 1.00 | 0.0119 |
| 30 | 447 | 1.00 | 1.00 | 0.0119 |
| 60 | 447 | 1.00 | 1.00 | 0.0119 |

- **Monotonic step fraction:** 1.0 (4 of 4 step transitions are non-decreasing).
- **Delta mean marker count:** +0.80 (5x baseline).
- **Delta fraction with any marker:** +0.80 (5x baseline).
- **Density delta:** 2.1x.
- **Plateau at k=15.** The held-out set saturates — every held-out
  walk emits at least one marker, mean is 1.0/walk. Plateau is honest
  reporting per the brief's measurement discipline ("plateau or
  overshoot are honest; failure to converge is honest; report what
  you see, not what you wanted").

**Top retrieval-source shift across the curve.** At k=0 the top sources
were Aristotle and Dickens (2 occurrences each across 5 walks). By k=5
they were Confucius (Analects) and Darwin (Origin) (4 each). By k=15
both held a maximum 5 — every held-out prompt's max_fragments=3 walk
drew from a marker-rich source. The substrate learned to bias retrieval
toward marker-bearing public-domain corpora WITHOUT a per-domain rule.

## Strict-strict thesis check

*"Would lain call this hardcoding?"*

- Marker set: domain-neutral lexicon drawn from `voice.py` plus four
  analytical words. Not hidden in the substrate; visible in the script
  as an evaluation oracle.
- Rating policy: marker-count-vs-batch-median. NOT a hand-coded
  routing decision — the policy is the *evaluator* (the human-replaced
  rubric), not the agent.
- Hebbian update path: unchanged from cycle-14 #08a + the 2026-05-12
  pass's atom generalization. Substrate-wide. No new branch, no new
  per-domain key, no new structure.
- Held-out prompts: never appear in the training set; their topics
  do not lexically overlap with training topics. Generalization is
  carried by the bigram-atom family the prior pass added.

Status: **PASS**. The script exercises the existing learning loop and
measures its output. Nothing in the runtime path of the agent was
extended.

## Counter-claims (what this does NOT mean)

- This is **not** subjective persona quality. The agent did not pass a
  blind A/B against a frontier model; we counted the appearance of a
  marker word.
- The marker set is **closed** (12 words). A more demanding measurement
  would use a held-out marker set or rely on external GPT/lain rating.
- The held-out shift is real but the **plateau is fast** (k=15). A
  larger, more diverse held-out set would show whether the substrate
  generalizes further or saturates because the persona-prompt shape
  itself caps how many marker-bearing fragments the corpus can serve.
- The corpus is small (~22k fragments). Real corpus scale-out
  (cycle-15 B2 / brief candidate E) would test whether the curve holds
  at 200k-500k words. That is the next-cycle work.
- The substrate is still retrieving fragments, not generating original
  prose. A genuine persona-consistency claim eventually requires the
  agent to compose original sentences with the prefix tags AND the
  surrounding analytical voice — that is composition work (candidate B),
  not retrieval-shift work.

## Honest gap catalogue

Each gap below has a measurable definition of "closed":

- **Marker set is closed.** Closed = held-out marker set (different
  12 words drawn from same persona surface) shows comparable curve
  shape under same training.
- **Plateau hides ceiling.** Closed = held-out set expanded to 20+
  prompts AND curve shows continued growth past k=15 OR the plateau
  reproduces (acceptable; reports the saturation honestly).
- **Public-domain corpus only.** Closed = same curve replicated on a
  cycle-15 B2 scaled corpus (200k+ words) with the same training
  protocol; curve shape held.
- **Marker frequency != persona quality.** Closed = blind A/B between
  k=0 and k=60 walks under external (lain or GPT audit framework)
  rating, with effect size reported.
- **Retrieval not generation.** Closed = the next cycle ships a
  composer that composes a paragraph from selected fragments AND that
  paragraph carries the persona markers AND it survives a fluency
  rubric.

## Verification

Compile-check:

```bash
PYTHONPATH=src python3 -m py_compile scripts/persona_consistency_curve.py
```

Result: exit `0`.

Existing test suite (no source changes; new script only):

```bash
PYTHONPATH=src python3 -m pytest tests/test_hebbian_bank.py tests/test_audit_log_v1.py tests/test_natural_mode_v0.py -q
```

Run command + result are reproducible deterministically:

```bash
PYTHONPATH=src python3 scripts/persona_consistency_curve.py
```

Result: `pass=true` (per the curve table above).

Artifacts:

- `/tmp/project-x-persona-consistency-curve.json`
- `/tmp/project-x-persona-consistency-curve.csv`
- `/tmp/project-x-persona-consistency-curve.bank.pkl`
- `/tmp/project-x-persona-consistency-curve.walks.jsonl`

## Interpretation

This pass demonstrates that the cycle-14 substrate's reward loop, with
the 2026-05-12 atom generalization in place, generalizes from training
prompts to a held-out prompt set on a NEW Terminus dimension (persona
consistency, mechanically proxied). The same Hebbian update that the
shrine-council demo proved on a humor/chat axis now also moves a
philosophy-flavored persona axis, with no per-domain rule added.

The plateau at k=15 is honest. The mechanism is the bigram-atom family
shared between training and held-out prompts: training's *"consider
the place of pleasure in a good life"* shares bigram atoms like
*"consider the"* and *"the nature of"* with held-out's *"consider the
nature of courage"*, so reward on a marker-rich rated walk inflates
the (bigram_atom × marker_fragment_atom) link in the bank, and the
held-out walk's lookup picks up a fractional signal toward that
fragment.

This is one more controlled demonstration that the strict-strict
substrate is the right surface to invest in. It does not make the
agent generally intelligent; it does add a second axis on which the
loop's generalization is measured rather than asserted.
