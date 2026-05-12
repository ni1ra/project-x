# Claude 2026-05-12 — Strict-Generalization Persona Curve

**Run ID:** `claude-2026-05-12-persona-generalization-strict`
**Scope:** Closes the advisor-flagged counter-claim on the
`claude-2026-05-12-persona-consistency-curve` artifact. Self-imposed
under lain's "work max until 03:30, stride for 100% manifesto"
directive — actionable work in the work window.

## The question this answers

The 2026-05-12 in-distribution curve showed cold-start 0.20 → final
1.00 mean marker count over sixty cumulative ratings on a NEW
Terminus axis (persona consistency). The advisor catch was that
three of five "held-out" prompts shared the bigram **"consider the"**
with three of eight training prompts. The substrate-wide Hebbian
update with the 2026-05-12 atom generalization writes to the
**bigram-atom** family explicitly — so the curve demonstrated the
mechanism *working as designed*, not generalization to lexically-
unrelated prompts.

The harder question: does the same substrate lift held-out marker
frequency when the held-out prompts have **zero bigram overlap** with
the training set? In that regime the substrate has only the
**prefix-atom** (which differs by leading verb) and the
**token-atom** family (which can only share common-English connectives
like "the" / "of" / "in" / "a") to draw on. If the curve still lifts,
the generalization claim is broader than the shared-bigram-atom story;
if it stays flat, the prior plateau shape was the bigram-atom
mechanism, full stop.

## Design

**Identical harness** to `persona_consistency_curve.py`: same 12
markers, same 8 training prompts, same `[0, 5, 15, 30, 60]` checkpoint
schedule, same rating policy (APPROVE if marker count ≥ batch median
AND > 0; REJECT otherwise), same `AuditLog.apply_rating` I/O path.
Only the held-out prompt set changes.

**Five strict held-out prompts** (verbs at position 0 deliberately
disjoint from training; bigrams audited at runtime to be zero-overlap):

```
explore courage under adversity
speak frankly about excellence today
examine memory across many lifetimes
evaluate truth against contested opinion
trace beauty through long history
```

**Audited overlap (mechanical, runtime-asserted):**

| Channel | Training | Held-out | Overlap |
|---|---|---|---|
| Bigrams | 36 unique | 19 unique | **0** (assertion enforces this) |
| Tokens | (counted) | (counted) | **1** ("about", a near-universal English connective) |
| Prefix verb | comment / consider / what / describe | explore / speak / examine / evaluate / trace | **0** |

The substrate has effectively no bigram bridge from training to held-
out. Any lift on the held-out marker frequency must come from
prefix-atom or token-atom generalization, which the substrate-wide
Hebbian rule treats as weaker (less specific) signal.

## Measured Result

Command:

```bash
PYTHONPATH=src python3 scripts/persona_generalization_strict.py
```

Result:

| k | bank_entries | mean_marker_count | fraction_with_any_marker | top sources |
|---|---|---|---|---|
| 0 | 0 | 0.00 | 0.00 | Aristotle (2), Herodotus (4) |
| 5 | 168 | 0.00 | 0.00 | Shakespeare Sonnet 130 (5), Shakespeare Sonnet 18 (10) |
| 15 | 387 | 0.20 | 0.20 | Confucius (1), Darwin (1) |
| 30 | 447 | 0.20 | 0.20 | Confucius (1), Darwin (1) |
| 60 | 447 | 0.20 | 0.20 | Confucius (1), Darwin (1) |

- **Delta mean marker count:** +0.20 (from 0.00 baseline).
- **Delta fraction-with-any-marker:** +0.20.
- **Monotonic step fraction:** 1.0 (4 of 4 step transitions are non-decreasing).
- **Plateau:** at k=15, identical to in-distribution variant.
- **Shift classification:** "lift" (positive but weak).

## Interpretation — the honest finding

The substrate **does** generalize past pure bigram overlap, but
**weakly**. Comparing the two curves under identical training and
identical learning machinery:

| Metric | In-distribution | Strict-generalization | Ratio |
|---|---|---|---|
| Final mean marker count | 1.00 | 0.20 | **5x larger in-distribution** |
| Final fraction-with-any-marker | 1.00 | 0.20 | **5x larger in-distribution** |
| Cold-start mean marker count | 0.20 | 0.00 | (cold-start retrieval differs) |
| Lift over cold-start (mean) | +0.80 | +0.20 | **4x larger in-distribution** |

**The bigram-atom family is the dominant generalization channel.** The
prefix-atom and token-atom families contribute weakly but non-zero
lift (one of five strict-held-out walks lands at least one marker by
k=15, which is real signal — the bank now has 387 entries, the
Confucius / Darwin sources break into the top retrievals on the strict
held-out set, and the curve plateaus there because the
prefix/token-atom channels saturate without further bigram bridge).

This is consistent with the prior cycle's design intent: the bigram-
atom family is **load-bearing** for substrate-wide reward propagation
across paraphrases, exactly as the in-distribution result showed. What
the strict curve adds is a **calibration**: the in-distribution win
should not be read as "the substrate has learned persona consistency
in a frontier-research sense"; it should be read as "the bigram-atom
family carries persona-rating signal within the bigram envelope of
the training set, and the prefix/token-atom channels carry a weaker
but non-zero residual generalization beyond that envelope."

## Strict-strict thesis check

*"Would lain call this hardcoding?"* Same answer as the in-distribution
variant: PASS. No new branch, no per-domain table, no learned scorer
weights. The script reuses the existing harness verbatim and only
changes which prompts are evaluated.

## What this changes about the manifesto trajectory

- **Cycle-15 B2 corpus scale-out becomes higher-leverage.** A larger
  corpus means more bigram bridges naturally exist between any pair
  of paraphrases, so the bigram-atom-bounded generalization regime
  itself becomes broader. The substrate doesn't need a different
  learning rule; it needs a richer atom-bridge graph.
- **The atom-generalization extension shipped 2026-05-12 was the
  right shape.** The strict-generalization residual lift is small but
  real, which means the substrate's atom-family Hebbian update is
  *operating across all three atom families*, not just the
  most-specific one. That's the right invariant.
- **A semantic-atom family is the next architectural lever for
  cross-paraphrase generalization beyond shared lexical surface.**
  Once corpus scale-out is shipped, the next lever is replacing or
  augmenting the lexical bigram atom with a semantic atom (e.g.,
  HDC binding of token vectors with a small co-occurrence-trained
  shift, or an SNN-spike-train co-firing pattern over windowed token
  context). That's a Phase 14+ candidate.

## Counter-claims (what this does NOT mean)

- The strict-generalization curve uses the SAME corpus as the in-
  distribution variant. Real corpus scale-out (cycle-15 B2) is owed.
- The marker set is still the same 12-word lexicon. Held-out marker
  set is owed.
- The strict-held-out prompts still share the calm-philosophy
  *register* with training; only the surface bigrams differ. A
  different-register held-out set (humor, math, persona-confessional)
  would test register-generalization separately and is owed.
- One-of-five (20%) is a small absolute number. With a larger
  strict-held-out set (20+ prompts) the lift estimate would have
  smaller variance.

## Verification

Compile + bigram-overlap audit (assertion runs at script start):

```bash
PYTHONPATH=src python3 -m py_compile scripts/persona_generalization_strict.py
PYTHONPATH=src python3 scripts/persona_generalization_strict.py
```

Result: exit `0`; `overlap_audit.bigram_overlap_count == 0`;
`overlap_audit.shared_token_count == 1` (only "about");
curve as tabulated above.

Existing test suite untouched (no source-code changes; only a new
sibling script that imports from the prior one).

Artifacts:

- `/tmp/project-x-persona-generalization-strict.json`
- `/tmp/project-x-persona-generalization-strict.csv`
- `/tmp/project-x-persona-generalization-strict.bank.pkl`
- `/tmp/project-x-persona-generalization-strict.walks.jsonl`

## Pair this with

- `docs/artifacts/claude-2026-05-12-persona-consistency-curve.md` —
  the in-distribution curve whose counter-claim this artifact closes.
- `docs/artifacts/codex-2026-05-12-reward-generalization-and-dispatcher.md`
  — the prior pass's atom-generalization extension that made this
  measurable in the first place.
