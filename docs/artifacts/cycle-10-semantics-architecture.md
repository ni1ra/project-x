# Cycle 10 — Semantics Architecture (CANONICAL)

**Status:** CANONICAL (replaces DRAFT-PRELIMINARY of commit `9b9aa7e`).
**Date:** 2026-05-11. Synthesis of the four-angle deep-research phase (commits `4133eaa`, `9f93ea2`, `4781366`, `c8362cf`) + the prior consolidated DRAFT.
**Pairs with:** `cycle-10-hdc-infrastructure-optimization.md` (the infrastructure layer underneath — operation-tier optimization, Rust port plan, dimensionality scaling).

---

## Origin — what the deep-research phase changed

The v1 → v2 → v3 → consolidated-DRAFT arc earlier this cycle moved too fast — each revision incorporated one lain critique reactively, but no deep-research pass happened between revisions. Lain's directive 2026-05-11 (msg `1503217035`): *"use council with many experts, and deep research, before finalizing how to do the concept understanding, text generation, semantics, having opinions, non hardcoded solutions that will organically and naturally [evolve]."*

The deep-research phase ran four sequential angles with per-angle advisor consults + brief literature integration + decision-point notes. Net result: **the DRAFT's 5 decision points all survive (slot-stable; verdicts updated)**, and **three NEW architectural commitments emerge** — basal-ganglia-style confidence-scored parallel-bid dispatcher (load-bearing for cycle 11 open-domain semantics), a try-until-satisfied K-rollout primitive with honest-refusal exit (the curiosity mechanism), and a surprise-biased offline consolidation pass (the merged-from-four-angles maintenance loop). The phase also produced **~12 explicit rejections** (Holland GA, NEAT, RND, multi-instance Raphael, scenario-simulation-as-separate-mechanism, sub-agent-as-new-primitive, prefrontal-as-rebranding, etc.) — these are not throwaway noise; they are **guardrails that prevent cycle 11 from re-litigating decisions the deep-research phase already closed.**

Asymmetric loading honored: angle 2 (evolutionary) ~20-25%; angle 3 (curiosity) ~60-70%; angle 4 (multi-agent) ~15-20%; angle 1 (brain subsystems) ~30-40%. The synthesis preserves that asymmetry — some sections short because the underlying angle was honestly thin.

---

## The gap (from `docs/paper.md` Chapter 9 + lain critique 2026-05-11, unchanged)

The current agent has zero free-form text generation. All "natural language" output is either (a) BUILDER-authored frozen `raphael_response` in benchmark entries or (b) `Lemma.render()` structured proof shapes. Poetry baseline graded 1.2-1.3/5 in cycle 1; root cause is no generation machinery exists. Lain's directive: build it, brain-inspired, HDC-rooted, corpus-trained, manually-audited, no hardcoded per-domain solutions.

---

## The architecture — 7 layers with substrate / runtime / learning trichotomy

The architecture partitions cleanly into three groups: **substrate** (state; what's stored), **runtime** (process; what runs per query), and **learning** (offline; what updates the substrate from feedback).

### Part A — Substrate (state)

#### Layer 1 — HDC subspaces (general-purpose, brain-inspired) [unchanged from DRAFT]

Four specialized subspaces of one shared 10k-dim hyperdimensional vector space (seed-clustered subprojections; near-orthogonal at random initialization):

- **Semantic subspace** — concept vectors. Stores facts, opinions (as `concept ⊗ valence` bindings — NOT a separate valence subspace; matches limbic-cortical anatomy where limbic colors cortical memory in situ), entities, themes.
- **Syntactic subspace** — phrase-shape patterns. N-gram-typed templates.
- **Intent subspace** — planning vectors. "What the agent is trying to do this turn" (explain / argue / refuse / chat / take-action / ...).
- **Procedural subspace** — primitive/tool vectors. Maps the primitive library + substrate tools to retrieval-addressable vectors.

These aren't physically separate matrices; they're subprojections of the same 10k-dim space distinguished by seed-vector clusters.

#### Layer 2 — Hormone vectors (extended with H_curiosity per angle 3)

A single `H` vector lives OUTSIDE subspaces and modulates cleanup-memory similarity thresholds across all subspaces simultaneously. Different H → different retrieval landscape → different output register.

- `H_formal` — biases toward substrate primitives + invariant cross-checks; activates Lemma chain mode.
- `H_natural` — biases toward corpus fragments + walk-style retrieval; activates HDC walk mode.
- **`H_curiosity` (new — angle 3)** — raises retrieval thresholds (more selective candidates), permits K-rollout iteration (Layer 4), allocates more compute. Activates when `(recent curiosity_signal > tau_surprise) AND (queued_tasks non-empty)`. Deactivates on queued-task completion (lain's "switches off when the queued given tasks are complete" spec — preserves budget against perpetual exploration).
- Additional hormone registers (e.g. `H_chat`, `H_terse`, `H_tutorial`) compose linearly; a given response can mix per-Lemma-step.

A given response can MIX modes per-step. Mode selection is hormone-driven, NOT domain-flagged. Intent classification via HDC similarity (intent-subspace nearest-neighbor) drives hormone selection.

Brain analogue: hormones (cortisol, dopamine, oxytocin) are slow, broadcast, modulate excitability rather than carry content. Same role here — threshold modulation, not content production.

### Part B — Runtime (process)

#### Layer 3 — BG-style confidence-scored parallel-bid dispatcher (NEW — angle 1, LOAD-BEARING for cycle 11)

The current ReasoningAgent dispatcher uses keyword gates + first-match-wins (`if "pell" in prompt: try pell; elif "matrix" in prompt: try eigenvalue; ...`). This works for cycle 7-10's bounded problem set (15 fixed shapes with distinct keywords). For open-domain semantics — where prompts are open-ended natural language and multiple primitives have ambiguous applicability — first-match-wins breaks.

The BG-style upgrade: each parser produces a confidence score in `[0, 1]` from `(regex match strength × hypervector-similarity to prompt-binding)`; the dispatcher picks `argmax` with mutual-inhibition suppression of alternatives.

```
For each prompt:
  1. Each parser produces a confidence in [0, 1]
     - Regex match strength × hypervector-similarity to prompt-binding
  2. Parallel bid: collect (parser_id, confidence) pairs for all parsers
  3. Apply mutual inhibition: top-1 dominates; alternatives suppressed
  4. If top-1 > tau_dispatch threshold → route to that parser's substrate
  5. If top-1 < threshold → honest-refusal path (no parser confident enough)
```

This is the open-domain-semantics dispatch primitive cycle 11 actually needs. Brain analogue: basal ganglia direct (Go) and indirect (NoGo) pathways implementing competitive selection among cortical motor programs via thalamic disinhibition (Mink 1996).

#### Layer 4 — Dual-mode composition with K-rollout iteration (extended — angle 3 curiosity folded in)

**Formal mode** — `Lemma` chain unchanged from cycle-1-through-10 reasoning substrate. Structured proof; invariant cross-checks per step; audit trail per claim. Used for: math, physics-with-equations, action-taking-with-tools, anything with closed-form verifiability. Substrate primitives compose into the proof.

**Natural mode** — HDC walk through fragment-space. Each step retrieves the next fragment by HDC similarity to `(current-state ⊗ intent ⊗ accumulated-context)`. Provenance trail per fragment (every emitted phrase points back to corpus source). Manual-audit feedback refines retrieval weights. Used for: history, humor, philosophy, poetry, casual chat, meaning-of-life questions, anything in the OPEN universe of concepts without closed-form structure.

**K-rollout iteration (new — angle 3, gated by H_curiosity):** when `H_curiosity` is active, the composition runs as K parallel rollouts, each tracking a per-step curiosity signal `1 - cos(hv_predicted, hv_actual)`. Emit the first rollout whose max per-step signal falls below `tau_satisfaction`. If all K rollouts fail → **HONEST REFUSAL** ("I tried K paths, none converged below threshold; the genuine answer is I don't know yet"). M-PROJECTX-013 preserved — the curiosity drives EXPLORATION not OVERCLAIM.

**HDC simplifies Pathak.** Pathak 2017's ICM required learning a feature space via an inverse model to filter noise (the "noisy TV problem"). HDC obviates this entirely: hypervectors *are* the feature space by construction, with cosine distance as the built-in similarity metric. The curiosity signal collapses to `1 - cos(predicted_hv, actual_hv)` with no learned-representation overhead. Cerebellum (climbing-fiber-error → parallel-fiber-weights, Ito 2006) is the neurobiological substrate of the same mechanism — Pathak's ICM and the cerebellum are computational and biological instantiations of one pattern.

Both modes remain HONEST: formal via invariants + Lemma render; natural via provenance + manual audit. K-rollout adds: honest-refusal-on-all-K-fail. Neither confabulates.

The split is what makes the architecture handle "infinite domains" without hardcoding. Formal mode is bounded (closed-form structure required). Natural mode is open (anything in corpus + HDC walk). No `domain=X` flag anywhere.

### Part C — Learning (offline)

#### Layer 5 — Primitive emergence (unchanged from DRAFT)

Primitives are EXTRACTED from corpus structure via unsupervised clustering, NOT hand-built. During corpus ingestion, n-gram-shell hypervectors are clustered in the procedural subspace; clusters with density above threshold become primitives.

Discovered structural shells include: "X is Y because Z" patterns; "the more X, the more Y" patterns; caesura-then-image patterns; setup-then-punchline patterns; when-X-then-Y temporal patterns; claim-then-qualification patterns.

These emerge naturally from a poetry corpus exposing caesura/volta structures, a physics corpus exposing law/analogy/regime patterns, a history corpus exposing temporal-causal patterns, a humor corpus exposing setup/payoff patterns. Add a new corpus domain → its patterns get clustered in → agent composes with them. No code change. No `domain=X` flag.

**Optional bootstrap** (mitigation if pure-unsupervised clustering insufficient): hand-seed ~10-20 STRUCTURAL UNIVERSALS (X-is-Y, X-causes-Y, X-but-Y, X-then-Y) — these are domain-agnostic structural patterns, not domain-specific primitives. The clustering builds on top. Honest about the bootstrap.

#### Layer 6 — Curated corpus + manual-audit feedback (unchanged from DRAFT)

**Corpus shape** (tier-balanced, ~tens of millions of words total, source-provenance metadata per fragment):

- **Tier 1 — Lain-authored (~100k words; voice anchor):** Discord messages, code, paper.md, MANIFESTO, dev-cycle reflections. Tagged `voice=lain`. Retrieval prioritizes lain-tagged fragments when hormone is `H_chat` or `H_default`.
- **Tier 2 — Domain-canonical curated (~1M-10M words per domain):** Public-domain poetry (Project Gutenberg); physics textbooks (Feynman, Griffiths) + curated arxiv abstracts; math (Hardy+Wright + Davenport + Lang); curated dialogue corpora (NOT GPT-generated — would distill a transformer through the back door); scripting examples + tool documentation. Sources tagged + citable.
- **Tier 3 — Lain's curated reading (optional growth):** Essays / blogs / papers lain explicitly flags.
- **Tier 4 — Synthetic from substrate (small, ongoing):** Agent's own Lemma-render outputs after lain audit.

**HDC capacity at 10k-dim:** ~10⁸ associations before noise dominates retrieval. Tens of millions of fragments × ~10 tokens each = ~10⁸-10⁹ tokens total. Fits. Memory IS the model; no learned weights, no gradient descent.

**Provenance is the honesty layer.** Every retrieved fragment carries source metadata. The agent never generates "beyond what it has stored + composed." Out-of-scope → honest refusal.

**English-fluency floor (cross-ref from angle 3):** output must articulate fluently in at least one natural language (English). This sets a quality bar on the natural-mode HDC walk's surface assembly — corpus fragments must compose into grammatical English. lain's native-language target (Norwegian) is implicit follow-up direction.

**Manual-audit feedback loop:**

- Agent generates output; reports per-slot retrieval-confidence + per-primitive selection-confidence + aggregated chain confidence.
- Lain audits LOW-CONFIDENCE generations preferentially via Discord (👍 approve / 👎 reject / ✏️ correct).
- Audit signals propagate back as binding-strength adjustments. For opinion corrections, adjust the specific `(concept ⊗ valence)` binding directly.
- CLI + Discord as v0 audit UI; no web app required.

#### Layer 7 — Consolidation pass (NEW — the four-angle quadruple-merge)

**ONE mechanism viewed through four lenses; the synthesis pass's most important reduction.**

The four research angles each cited an offline-maintenance loop with different vocabulary. The synthesis lands them as ONE primitive:

- **Selection rule (from angle 1 — hippocampal replay; Wilson & McNaughton 1994):** bias toward recent + surprising / high-prediction-error / high-audit-weight bindings, NOT uniform across substrate. Sharp-wave-ripple replay during slow-wave sleep is NOT uniform; consolidation here shouldn't be either.
- **Update operation (from angle 2 — Salimans 2017 Evolution Strategies):** perturb-audit-reweight. For each selected binding, generate K perturbations (bit-flip ~1% for binary-packed HDC; small Gaussian noise for float); score each by retrieval quality on audit-loop queries; replace or blend the central vector toward the higher-scoring perturbation.
- **Trigger / candidate-surfacing (from angle 3 — K-rollout surprise tracking):** bindings touched by recent surprising rollouts are surfaced as candidates for the next consolidation pass. The runtime's curiosity-tracking IS the consolidation's input pipe.
- **Temporal placement (from angle 4 — multi-temporal-Raphael reframe):** offline / overnight; not per-query. The "slow-Raphael" temporal-multi-instance interpretation collapses to this offline maintenance pass.

```
At consolidation-pass time (offline / overnight):
  1. Pull: bindings_touched_by_surprising_rollouts ∪
           bindings_with_recent_audit_revision        (selection rule, angle 1)
  2. For each binding in the set:
       Generate K perturbations (bit-flip ~1% for binary; Gaussian for float)
       Score each by audit-approval-on-retrieval-queries     (ES, angle 2)
       Replace or blend central vector toward highest scorer
  3. Mark these bindings as "consolidated this cycle"        (housekeeping)
```

Forward-AND-reverse-chain replay is a **cycle-12+ candidate** — reverse execution back-propagates audit-approval signals from end-of-chain to earlier steps. Not load-bearing for cycle-11 MVP; flag for later.

---

## Decision contract — DRAFT's 5 (verdicts updated) + 3 additions from deep research

### Section A — DRAFT 5 (slot-stable; verdicts may update but the slots are the architectural spine)

1. **Hormone modulation: IN** — load-bearing for mode-switching; empirically testable cheaply in cycle 11 #2. **Expanded:** now includes `H_curiosity` register from angle 3 (raises thresholds + permits K-rollout iteration; deactivates on queued-task completion).
2. **Valence-as-binding (in semantic space)** — matches limbic-cortical anatomy; simpler audit-loop. **Unchanged.**
3. **Corpus shape: tier-balanced-at-scale** — Tier 1 voice anchor + Tier 2 domain canonical at 1-10M words each + Tier 3-4 optional. **Unchanged** (English-fluency-floor cross-ref from angle 3 sits in Layer 6).
4. **Primitive emergence via corpus clustering** — no per-domain primitive lists. **Unchanged** (optional STRUCTURAL-UNIVERSAL bootstrap still in scope).
5. **Dual-mode composition (formal Lemma + natural HDC walk)** — hormone switches; mixes per-Lemma-step OK; handles infinite domains without hardcoding. **Extended:** K-rollout iteration when `H_curiosity` is active.

### Section B — Three additions from deep research

6. **Dispatcher: BG-style confidence-scored parallel-bid** (replaces keyword-gated first-match-wins). **LOAD-BEARING for cycle 11 open-domain semantics.** Each parser produces a `[0, 1]` confidence; argmax + mutual-inhibition + threshold-gating + honest-refusal-path when threshold not met. Brain analogue: basal ganglia direct/indirect pathways.
7. **Consolidation pass: INCLUDE** (surprise-biased; offline / overnight). ONE primitive viewed through four lenses (hippocampal selection rule + ES update operation + K-rollout candidate-surfacing + multi-temporal-instance temporal placement). MUST land as ONE decision, NOT four.
8. **K-rollout iteration: INCLUDE** (try-until-satisfied with honest-refusal exit). Gated by `H_curiosity`. The curiosity signal is `1 - cos(hv_predicted, hv_actual)`; `tau_surprise` triggers iteration; `tau_satisfaction` terminates a satisfied rollout; all-K-fail → honest refusal.

---

## Rejections (synthesized across all 4 angles)

- **Holland 1992 GA + schema theorem** (angle 2) — HDC hypervectors are holographic; no separable schemata for crossover. Decoration.
- **Stanley NEAT 2002 topology evolution** (angle 2) — HDC substrate operators are intentionally fixed by organic-thesis discipline. Decoration.
- **"Audit-loop IS the environment" as new mechanism** (angle 2) — audit-weight-adjustment already implements selection pressure mechanically. Rebranding.
- **"Entropy defiance" as new mechanism** (angle 2) — confabulation suppression is implemented by audit-rejection of low-confidence bindings. Rebranding.
- **Per-concept transient-ensemble framing** (angle 2) — well-known n-best architecture; calling it evolution doesn't make it new.
- **RND (Burda et al. 2019)** (angle 3) — HDC random projections are nearly-orthogonal by construction; no learnable predictor closes a gap. No signal.
- **Multi-instance Raphael for single-user agent** (angle 4) — multi-process overkill; multi-temporal reframe absorbed into Layer 7 consolidation pass.
- **Scenario simulation as separate mechanism** (angle 4) — IS K-rollout with pluggable scoring (audit-approval prediction in place of curiosity signal). One mechanism, multiple scoring rules.
- **Sub-agent architecture as new primitive** (angle 4) — modular code organization, not new architectural primitive.
- **Pre-emit audit-prediction** (angle 4) — audit-weight-adjustment applied speculatively. Rebranding.
- **Prefrontal/working-memory framing** (angle 1) — Lemma chain already implements working-memory mechanically.
- **Thalamus/colliculus attention as new layer** (angle 1) — v2 hormone-modulation absorbs it.

---

## Cycle-12+ candidates (deferred from cycle-11 MVP)

- **Sutton 1999 options as Lemma-chain-level abstraction** (angle 4) — addressing chains rather than primitives; load-bearing once cycle-11 chain library grows beyond ~3-4 primitives composed.
- **FeUdal Networks 2017 manager-worker decomposition** (angle 4) — same family as Sutton options; comes in together.
- **Forward-AND-reverse-replay during consolidation** (angle 1) — back-propagates audit-approval signals from end-of-chain to earlier steps.
- **Sub-agent code modularization** (angle 4) — splitting subspace-specific operations into separate Python modules. Code-organization, not architectural.

---

## Open questions (honestly unsolved; cycle-11+ empirical work)

- **`tau_surprise` and `tau_satisfaction` calibration** (angle 3) — empirical tuning loop, not closed-form. Cycle-11+ deliverable.
- **BG-dispatcher confidence-score formula tuning** (angle 1) — exact weights for `regex match strength × hypervector-similarity` combination; cycle-11 empirical.
- **Consolidation cadence** — how often is "overnight"? Per-N-queries? Per-day? Per-corpus-ingest? Cycle-11+ tuning.
- **Per-primitive vs per-chain confidence aggregation** — for K-rollout and BG-dispatcher both: do we score the chain end-to-end, or accumulate per-step? Empirical.
- **Primitive-emergence clustering quality** — DRAFT counter-claim #1; cycle 11 #6 IS the test.

---

## Cycle-11 implementation sequence (REORDERED ~16-20h Raphael-time)

Order matters: dispatcher → hormones → K-rollout BEFORE any corpus work because the dispatcher gates how corpus-fetched primitives are addressed.

1. **#1 BG-style confidence-scored dispatcher upgrade (~90 min)** — replaces current keyword-gated chain; foundation for everything else. Empirical confidence-score formula tuning kicked off.
2. **#2 hormone-modulation primitive on existing math substrate (~60 min)** — `H_formal / H_natural / H_curiosity` registers; empirical mode-switching test on existing math substrate. Demonstrates threshold-shifting works.
3. **#3 K-rollout iteration mechanism with curiosity-signal exit (~90 min)** — try-until-satisfied + honest-refusal-on-all-K-fail. `tau_surprise / tau_satisfaction` initial empirical tuning.
4. **#4 Opinion bindings (~60 min)** — hand-seed ~50-100 concept-vectors with valence bindings on philosophy/persona domain. Demonstrates "what do you think of X" routing.
5. **#5 Tier-1 corpus ingestion + audit UI (~3h)** — encoding pipeline + provenance-tagging + audit UI. Ingest lain-authored corpus (~100k words). One-time pipeline work that unlocks all later tiers.
6. **#6 Primitive emergence clustering pipeline (~3h)** — unsupervised clustering of n-gram-shell hypervectors in the procedural subspace. Empirical-test-first: does it produce useful primitives or just frequency-rankings? Bootstrap fallback ready (~45 min) if clustering insufficient.
7. **#7 Tier-2 per-domain corpus ingestion (~30-60 min per domain × 5 domains)** — run pipeline on poetry / physics / math / chat / action corpora. Atomic per-domain ships.
8. **#8 Dual-mode composer (~2h)** — natural-mode HDC walk alongside Lemma chain. Hormone selects mode.
9. **#9 Consolidation pass primitive (~2h)** — surprise-biased ES-style perturb-audit-reweight on offline pass. Surfaces bindings via angle-3 tracking + applies angle-2 ES update with angle-1 selection rule.
10. **#10 End-to-end demo on two domains: formal + natural (~90 min)** — formal: existing math substrate with hormone-modulated rendering. Natural: HDC walk on a single prompt over the Tier-1 ingested corpus.

Total ~16-20h. Cycle 11 primary thread if greenlit; corpus-heavy steps (#5, #6, #7) may slip to cycle 12 if time pressure.

---

## Honest counter-claims (updated)

1. **Primitive emergence clustering is empirically unproven at this scale.** Cycle 11 #6 IS the test. If discovered primitives are useless, bootstrap escape valve kicks in.
2. **HDC walk in natural mode has no formal verification per step.** Only provenance + manual audit. For long-form prose this can drift; quality bounded by corpus + audit diligence.
3. **Mode switching can be wrong.** Intent-classification accuracy is empirical.
4. **Won't beat GPT-N on free-form fluency.** Thesis: competence + honesty + auditability + provenance, not fluency match.
5. **Cycle-11 cost ceiling is real.** ~16-20h is a lot for one cycle; primitive-emergence pipeline may slip to cycle 12.
6. **Corpus provenance has to actually work** — every retrieved fragment must trace back to source even when fragments get composed across retrieval steps.
7. **HDC at 10⁸ associations starts degrading non-linearly.** The capacity claim is back-of-envelope; cycle 11 #1 of the HDC-infra plan measures it empirically with bitwise-packed representation.
8. **BG-dispatcher confidence calibration could break.** If the confidence-score formula doesn't separate parser candidates cleanly, the open-domain-semantics dispatch problem isn't solved — it's just relocated.
9. **K-rollout cost is K× single-rollout.** If `H_curiosity` is active too often, the agent's per-query budget blows up. The hormone deactivation rule (queued-tasks empty → off) is the cost guardrail; tuning matters.
10. **Consolidation pass cadence may need to be tied to corpus ingest events, not wall-clock.** Open question.

---

## "Use council" disposition (final)

This canonical doc consolidates:
- v1 (advisor 5-candidate scaffold)
- v2 (advisor pre-write critique; lain's brain+corpus+audit reframings)
- v3 amendment (lain's no-hardcode + emergence + dual-mode critique)
- The DRAFT-PRELIMINARY consolidated doc
- 4 deep-research angles (advisor consults + literature: Holland 1992, Stanley NEAT 2002, Salimans 2017, Pathak 2017, Burda 2019, Sutton 1999, Vezhnevets 2017, Wilson & McNaughton 1994, Buzsaki 2019, Kandel 2021, Mink 1996, Ito 2006)
- **6 substantive advisor calls in this run** (4 deep-research angles + synthesis pre-write structure check + synthesis pre-commit review), plus the 2 from the v1/v2 prior-cycle path. Lain's three Discord critiques + follow-ups drove the most-substantive reframings.

The DRAFT and the four angle notes have been preserved (commits `9b9aa7e`, `4133eaa`, `9f93ea2`, `4781366`, `c8362cf`). This doc is the contract cycle 11 honors.

---

## Sources

- `docs/artifacts/cycle-10-hdc-infrastructure-optimization.md` (commit `acca853`) — paired infrastructure roadmap.
- `docs/artifacts/cycle-10-semantics-angle-evolutionary.md` (commit `4133eaa`).
- `docs/artifacts/cycle-10-semantics-angle-curiosity.md` (commit `9f93ea2`).
- `docs/artifacts/cycle-10-semantics-angle-multi-agent.md` (commit `4781366`).
- `docs/artifacts/cycle-10-semantics-angle-brain-subsystems.md` (commit `c8362cf`).
- Pentti Kanerva, *Hyperdimensional Computing* (2009).
- Plate, *Holographic Reduced Representations* — binding + cleanup memory.
- Eliasmith, *Semantic Pointer Architecture* — neural-architecture-inspired HDC composition.
- Holland 1992; Stanley & Miikkulainen 2002 (NEAT); Salimans et al. 2017 (ES).
- Pathak et al. 2017 (ICM); Burda et al. 2019 (RND).
- Sutton, Precup & Singh 1999 (options); Vezhnevets et al. 2017 (FeUdal).
- Wilson & McNaughton 1994 (hippocampal replay, Science); Buzsaki 2019 (*The Brain from Inside Out*); Mink 1996 (basal ganglia selection); Ito 2006 (cerebellar circuitry); Kandel 2021 (*Principles of Neural Science*).
- Lain Discord critiques 2026-05-11 (msgs `1503208357` through `1503219992`) — the iterative refinement that produced the DRAFT + the four-angle research framings.
- 5 advisor consults across v1/v2/v3 + 4 deep-research angles + 1 synthesis pre-write structure check.

— Architecture is one shared HDC substrate, hormone-modulated, with BG-style confidence-scored parallel-bid dispatch into dual-mode composition with K-rollout iteration, fed by a curated huge corpus whose structural patterns emerge as primitives, refined by lain's manual audit loop, with a surprise-biased offline consolidation pass that closes the loop. No domain enumeration; honest at every layer; the contract cycle 11 honors.
