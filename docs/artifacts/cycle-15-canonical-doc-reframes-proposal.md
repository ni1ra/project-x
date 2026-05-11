# Cycle 15 council surface B5 — Cycle-13 audit C-reframes proposal (DRAFT for lain review)

**Status:** cycle-15 council surface B5 (#00P13c15-06). **DRAFT PROPOSAL for lain review** — NOT a canonical-doc edit. The three proposed reframings below are presented as proposed wording for lain to greenlight, modify, or reject. Final edits to MANIFESTO + cycle-10 canonical synthesis happen IN A SEPARATE commit AFTER lain greenlights.
**Pairs with:** cycle-13 audit-of-audit doc (commit `2823a65`) §"Section C — Architectural critique" findings C1/C2/C3/C4; cycle-13 emergence-at-scale result (commit `b673993`; 0/20 STRUCTURAL NOT VALIDATED); cycle-14 reflect §"Open questions" item naming B5 as lain-pending; cycle-15 B4 thesis-compliance gate.
**Date:** 2026-05-11.

---

## Why this proposal exists

The cycle-13 GPT external audit (commit `2823a65`) caught three architectural slogans in the canonical doc + MANIFESTO that need honest reframing:

- **C1** 10⁸-association capacity claim — about random-vector near-orthogonality at D=10000, but our vectors aren't random (they're 4096-feature char-n-gram-hash projected to D=10000); effective semantic capacity is bounded by the hash feature space, not the projection dim.
- **C2** "Memory IS the model" framing — slogan vs demonstrated compression-and-control; current state is retrieve-with-provenance + planned learning loop, not yet a model.
- **C3** Layer-5 emergence framing — current implementation is "trigram pattern mining," not "variable-binding primitive induction." Cycle-13 #07f-run confirmed empirically: 0/20 STRUCTURAL clusters → Layer 5 NOT VALIDATED at scale.

The audit-of-audit verdict on each was AGREE. Cycle-14 reflect deferred the reframings as "doc work pending lain direction." Cycle-15 council surface B5 ships this PROPOSAL DOC with concrete suggested wording for each, awaiting lain greenlight before canonical-doc edits land.

## Three proposed reframings (drafts for lain review)

### Reframing 1 — 10⁸-association capacity claim (C1)

**Current canonical-doc wording (sample):** *"HDC at D=10000 supports ~10⁸ near-orthogonal associations."*

**Proposed reframing (option A — information-theoretic precision):**

> *"HDC at D=10000 with random Rademacher bipolar vectors supports approximately 10⁸ pairwise-near-orthogonal vectors (per Johnson-Lindenstrauss bound at ε=0.1). Project X's vectors are NOT random — they are char-n-gram-hash projected from a 4096-feature input space through a fixed Hadamard-like projection. Effective SEMANTIC capacity is bounded by the encoder's feature space (≤2^4096 possible inputs); the projection-dimension D bounds the storage representation, NOT the semantic capacity. Empirical capacity at the substrate's actual operating regime (22k-fragment Tier-2 corpus) is TBD."*

**Proposed reframing (option B — honest downgrade if option A is too detailed for canonical-doc audience):**

> *"HDC at D=10000 stores vectors that are near-orthogonal up to the encoder's feature-space limit; the projection dim bounds storage, not semantic capacity. The 10⁸-association figure applies to random vectors and is an upper bound on storage; effective semantic capacity in Project X is bounded by the char-n-gram-hash encoder's feature space + the corpus diversity. Empirical capacity TBD pending cycle-15+ scaling work."*

**lain review notes:**
- Option A is more rigorous; option B is more accessible.
- Both honestly downgrade the 10⁸ claim from "Project X has this capacity" to "this is the random-vector upper bound; our actual capacity is bounded by the encoder."
- Pick A, B, or modified version. The audit's underlying point — that the 10⁸ figure is currently load-bearing in the canonical doc without information-theoretic backing — should be addressed either way.

### Reframing 2 — "Memory IS the model" framing (C2)

**Current canonical-doc wording (sample, from MANIFESTO § Organic emergent intelligence):** *"Memory IS the model — the substrate's HDC binding-bank IS where intelligence emerges."*

**Proposed reframing (option A — minimal):**

> *"Memory + the learning loop ARE the model — the substrate's HDC binding-bank stores experience; the cycle-14 #08a Hebbian bank reads rated walks; the cycle-15+ reward-driven retrieval blend USES the accumulated bank-state at inference time. Intelligence emerges from the bank's CONTENT shaped by experience, not from the bank itself."*

**Proposed reframing (option B — honest downgrade if cycle-14 reward loop isn't yet mature enough to claim):**

> *"Current state: retrieval-with-provenance over the HDC binding-bank + planned learning loop (cycle-14 ships substrate writability; cycle-15+ accumulates audit signal to fill the bank). The slogan 'memory IS the model' captures the ASPIRATIONAL end-state — when the bank is filled with reward-shaped patterns, retrieval over it produces intelligent behavior. Project X is NOT yet at that end-state; cycle-14 ships the WRITE PATH from rated experience; capability lift waits on accumulated audit cadence."*

**lain review notes:**
- Option A claims the cycle-14 work brought us closer to "memory IS the model"; option B is more honest about cold-start status.
- The cycle-14 #08f Arm A verification proved cold-start preserves cycle-13 baseline (bank empty → identity blend → cycle-13 behavior). So at cold-start, "memory IS the model" is still aspirational; the slogan should reflect that.
- Option B is the more strict-strict-thesis-aligned reframing.

### Reframing 3 — Layer-5 emergence framing (C3)

**Current canonical-doc wording (sample, from Layer 5 spec):** *"Primitives EMERGE from unsupervised clustering over the corpus — variable-binding patterns like 'X is Y' surface as canonical examples."*

**Proposed reframing (option A — honest empirical):**

> *"Layer 5 — Pattern Emergence (cycle-13 #07f-run verdict: 0/20 STRUCTURAL → NOT VALIDATED at scale): cycle-13's pre-registered emergence predicate (committed `0b89101` before run; result at `b673993`) found that k-means clustering on a 10k-trigram sample of the 22k Tier-2 corpus produces FREQUENCY-RANKED clusters dominated by high-frequency-function-word co-occurrence ('of the' / 'in the' / 'and the'), NOT 'X is Y'-shape structural shells. The cycle-11 MVP's 3k-trigram structural-shell finding was a small-corpus artifact. CURRENT IMPLEMENTATION = trigram pattern mining; variable-binding primitive induction (the canonical-doc Layer 5 target) is cycle-15+ work requiring different machinery (role-filler binding clusters, longer n-grams + dependency parsing, semantic encoder)."*

**Proposed reframing (option B — concise honest downgrade):**

> *"Layer 5 — Pattern Mining (DOWNGRADED 2026-05-11 per cycle-13 #07f-pre/run empirical NOT-VALIDATED verdict): current implementation finds frequency-ranked clusters from char-n-gram-hash-derived trigram-cosine-clustering, NOT variable-binding primitive induction. Honest framing of present capability: trigram pattern surfacing. Variable-binding primitive induction is future Layer 5 work requiring role-filler binding machinery + longer-n-gram + dependency parse + semantic encoder."*

**lain review notes:**
- Option A is more comprehensive (cites empirical verdict + future-work directions); option B is more concise (label rename + brief honest framing).
- Both replace the aspirational "primitives EMERGE" with the empirical "pattern mining (currently)" — honest about cycle-13 #07f-run's NOT-VALIDATED verdict.
- This reframing is load-bearing for cycle-15+ planning because cycle-15+ work that builds atop "Layer 5 primitives" needs to know whether to use the cycle-13 frequency-ranked clusters (substrate-output as-is) or wait for variable-binding primitive induction machinery (future work).

## Proposed canonical-doc edits sequencing

If lain greenlights:

1. **MANIFESTO.md edits** — find current load-bearing wording for each of C1/C2/C3; replace with chosen option (A or B or modified version). ~3 surgical edits.
2. **Cycle-10 canonical synthesis doc edits** — same reframings applied. ~3 surgical edits.
3. **Atomic commit** `docs(P13c15-NN-canonical-reframes)` with the edits + reference to this proposal doc for rationale audit-trail.

If lain rejects or modifies: cycle-16+ defer; proposal doc stays on disk as the audit trail of "what was proposed at cycle-15."

## Counter-claims (M-PROJECTX-013)

1. **The proposal IS speculation about lain's preferences.** I'm guessing which option (A vs B) lain would prefer for each reframing. Mitigation: BOTH options offered per reframing; lain picks per his own framing-style preference.
2. **Cycle-13 audit-of-audit (commit `2823a65`) already proposed reframings.** This doc consolidates them into a single review surface with concrete proposed wording. Some duplication with the audit-of-audit doc is expected; the consolidation is the value-add.
3. **The cycle-13 #07f-run verdict applies most directly to C3.** C1 and C2 reframings are based on AUDIT findings, not on cycle-13 empirical runs. C1 is information-theoretic precision (no empirical test); C2 is slogan-vs-mechanism honesty (cycle-14 #08a-c partial mitigation; bank shipped but empty).
4. **Reframing canonical-doc wording is a TRUST event for lain.** Lain's previous catches show he reads canonical-doc wording carefully; changing it requires his explicit greenlight (per cycle-14 reflect §"Open questions" item naming B5 as lain-pending). This proposal doc respects that — the doc PROPOSES wording, the final canonical-doc edits await lain greenlight.

## Thesis-compliance gate (per cycle-15 B4 — commit `bb8f297`)

- **Test 1 — "Would lain call this hardcoding?"** PASS. Doc work proposing canonical-doc reframings is meta-documentation, not agent structure.
- **Test 2 — LEARNING-MACHINERY-ONLY filter.** PASS. No substrate changes; doc-only work.
- **Test 3 — Atom-shape substrate-wide.** PASS — no new state.
- **Test 4 — Gate fires PER-ANGLE BEFORE commit.** PASS — inline.

**Net gate verdict: PASS.** Proposal doc is strict-strict-thesis-compatible.

---

*Single-line takeaway: B5 proposal doc — three canonical-doc reframings per cycle-13 audit C1/C2/C3 findings (10⁸-capacity-claim, "memory IS the model", Layer 5 emergence) presented as proposed wording for lain greenlight. Final canonical-doc edits await lain greenlight in a separate commit. The proposal phase is BUILDER work (this doc); the edits phase is lain-dependent. Same proposal-vs-final-edits distinction as cycle-15 B1's angle-note-vs-implementation split (heartbeat 5 catch lesson applied here).*
