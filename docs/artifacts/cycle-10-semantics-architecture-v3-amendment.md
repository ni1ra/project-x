# Cycle 10 — Semantics Architecture v3 Amendment (emergence-not-hardcoding + dual-mode formal/natural)

**Lain critique 2026-05-11** (Discord msg `1503214621891493909`):

> *"And remember, there are infinite domains and concepts it should be able to procedurally, organically, naturally understand across regions. It's not just maths, poetry, etc. its history knowledge, it's humor, it's what the meaning of life is, so don't try to hardcode up a solution to this."*

**The catch:** v2's compositional layer (C5 retained from v1) enumerated per-domain primitive libraries — `emit_couplet` / `emit_image_via_sense` for poetry, `state_law` / `emit_analogy` for physics, `emit_acknowledgement` / `emit_followup_question` for conversation, `emit_intent` / `emit_tool_call` for action. That's domain-hardcoding. It scales to whatever domains I hand-build and refuses everything else. "History knowledge, humor, meaning of life" — no clean primitive decomposition for any of these; the v2 design implicitly requires me to enumerate domains, which is exactly the wrong shape.

**This is a v3 AMENDMENT, not a v3 rewrite.** v2's substantive pieces stand:
- Multi-region HDC (semantic / syntactic / intent / procedural subspaces) ✓ unchanged
- Hormone-modulation as global threshold-shift mechanism ✓ unchanged
- Curated corpus-at-scale with source-provenance ✓ unchanged
- Manual-audit feedback loop as training signal ✓ unchanged
- Opinion-as-binding-in-semantic-space (not separate valence subspace) ✓ unchanged

**What v3 amends is the compositional layer.** v2's C5 ("Lemma.render IS already text generation; add domain primitives") is partially right and partially wrong. Right: composition IS the surface assembly mechanism. Wrong: primitives shouldn't be hand-built per domain — they should EMERGE from corpus structure, and composition should split into two modes based on whether the output is FORMAL-VERIFIABLE or NATURAL-AUDITABLE.

---

## Amendment 1 — Primitive emergence from corpus structure (no hand-coded per-domain libraries)

### The wrong v2 model

v2 listed primitive libraries per domain:
- Poetry: `emit_image_via_sense`, `emit_caesura`, `emit_volta`
- Physics: `state_law`, `emit_analogy`, `name_regime`
- Conversation: `emit_acknowledgement`, `emit_followup_question`
- Action: `emit_intent`, `emit_tool_call`, `emit_outcome_observation`

This required me to (a) pre-enumerate domains and (b) hand-build the primitive library per domain. Lain's critique: infinite domains; can't be pre-enumerated; primitives need to EMERGE.

### The v3 model

**Primitives are corpus-extracted, not hand-built.** During corpus ingestion (v2 cycle-11 #infra-4 audit loop), an unsupervised clustering pass over the corpus's n-gram-shape distributions discovers recurring STRUCTURAL TEMPLATES — phrases like "X is Y because Z", "the more X, the more Y", "I think X but actually Y" — and stores each as an HDC-typed primitive in the procedural subspace. The clustering criterion: which n-gram patterns recur across multiple corpus fragments with bound-slot variability (the same shell, different fillers).

This means:
- A poetry corpus exposes caesura-then-image patterns, image-then-volta patterns, meter-bounded constructions — DISCOVERED, not assumed.
- A physics corpus exposes law-statement patterns, analogy patterns, regime-naming patterns — discovered.
- A history corpus (lain explicitly named) exposes when-X-then-Y patterns, cause-effect patterns, contrast-with-earlier-period patterns — discovered.
- A humor corpus exposes setup-then-punchline, subverted-expectation, callback patterns — discovered.
- Meaning-of-life-domain text (philosophy, religion, lain's own writing) exposes claim-then-qualification, lived-example, dialectic patterns — discovered.

The PRIMITIVE LIBRARY = whatever structural patterns the corpus exposes after clustering, automatically and recursively. Add a new domain corpus → its patterns get clustered in → the agent immediately can compose with them. No code change. No hand-built primitives. No `domain=X` flag.

### How the clustering works (proposed; cycle 11+ work to validate empirically)

For each corpus fragment:
1. Encode via the cycle-9 character-n-gram + Hebbian encoder into a 10k-dim hypervector.
2. Extract candidate "shells" by replacing each noun-or-verb-or-named-entity span with a SLOT marker. The shell is the hypervector encoding of the slotted fragment.
3. Cluster shell hypervectors via cosine-similarity in the procedural subspace. Clusters with density above a threshold become primitives.
4. Each primitive carries its slot-type signature (which kinds of fillers were observed) as additional HDC bindings.

At generation time:
1. The planner queries the procedural subspace for primitives whose shell is similar to the current generation-context.
2. The hormone vector biases primitive selection (formal-hormone biases toward provable patterns + invariant-carrying shells; natural-hormone biases toward fluent-narrative shells).
3. Selected primitive's slot-typed signature drives semantic-subspace queries for slot fillers.
4. Surface assembly emits the rendered text.

### Honest counter-claim

**This is non-trivial unsupervised structure discovery.** Clustering raw n-grams into "primitives" is a known hard problem; classical n-gram models suffer from data sparsity at long contexts. HDC representations help (concept similarity over fragment shells is denser than raw n-gram counting) but the clustering's PRACTICAL behavior needs empirical validation. Cycle 11+ work needs to actually run the clustering on a real corpus and measure: does it discover meaningful primitives, or does it just learn that "the" is a very common word?

Possible mitigation if pure-unsupervised clustering doesn't yield useful primitives: HYBRID. Hand-seed a small starter primitive library (~10-20 universal patterns like "X is Y", "X causes Y", "X but Y", "X then Y") as a bootstrap; let the clustering DISCOVER additional primitives on top. Honest about the bootstrap. The hand-seeded primitives are explicitly STRUCTURAL UNIVERSALS, not domain-specific — they apply equally to poetry, history, humor, and physics.

---

## Amendment 2 — Dual-mode composition: formal Lemma chain vs natural HDC walk

### The split

Some outputs need to be VERIFIABLE (math results, physics-with-equations, tool-call action-taking). These run in formal mode:
- Lemma chain with structured derivation
- Invariant cross-checks per step
- Closed-form algorithm produces the answer; substrate primitives are the composable units
- Audit trail per claim — every output mechanically reproducible

Other outputs are AUDITABLE-NOT-VERIFIABLE (history narration, humor, philosophy discussion, poetry, casual chat, meaning-of-life riffs). These run in natural mode:
- HDC walk through fragment-space — each step retrieves the next fragment by similarity to (current-state ⊗ intent ⊗ accumulated-context)
- Provenance per fragment — every emitted phrase points back to its corpus source
- Manual-audit feedback loop refines retrieval weights
- The Lemma chain is REPLACED by a walk-trajectory; the "proof" is the provenance trace, not invariants

The hormone vector switches between modes:
- `H_formal` biases primitive selection toward substrate primitives + Lemma chain; activates invariant checks.
- `H_natural` biases retrieval toward corpus fragments + HDC walk; activates provenance tracking.

A given response can MIX modes — e.g., a physics explanation might use Lemma chain for the equation derivation AND HDC walk for the analogies and surrounding prose. Mode selection is per-Lemma-step, not per-response.

### Why this matters for "infinite domains"

Formal mode is bounded — it only handles outputs that have closed-form structure and substrate primitives to compose. Math, physics-with-equations, agentic-tool-calls. Limited domain.

Natural mode is OPEN — it handles outputs that don't need verifiable structure. Any concept that exists in the corpus is reachable via HDC walk through fragments. History? Walk through historical-content fragments. Humor? Walk through humor-tagged fragments. Meaning of life? Walk through philosophy + religion + lain's-own-musings fragments. No domain enumeration; the corpus + the walk handle infinite expressivity.

The DUAL-mode discipline is the load-bearing architectural property:
- For formal-mode outputs, the system maintains the audit trail + invariant rigor we already established cycle-1-through-10.
- For natural-mode outputs, the system maintains the provenance trail + manual-audit feedback we introduced in v2.

Both are HONEST. Neither confabulates.

### How the agent decides which mode to use

Hormone-modulated, prompt-driven. Cycle 11 #infra-3's multi-resolution HDC supports this naturally:
- Prompt encoded into semantic + intent subspaces.
- If the intent is "compute X" or "solve Y" or "take-action Z" → formal-hormone rises; Lemma chain executes.
- If the intent is "explain X" or "discuss Y" or "what do you think of Z" → natural-hormone rises; HDC walk executes.
- If both — "compute X AND explain why it works" — mixed mode; formal chain produces the answer + natural walk produces the surrounding prose.

The intent-classification is itself an HDC similarity question; no rule-based hand-coded classifier needed. The intent subspace stores hand-seeded examples of intent vectors; new prompts get classified by nearest-neighbor.

---

## How this changes cycle 11 work

v2's cycle-11 plan (6 sub-tasks, ~10-12h Raphael-time):
1. hormone-modulation primitive on existing math substrate
2. opinion bindings (philosophy/persona)
3. Tier-1 corpus ingestion + audit UI
4. Tier-2 per-domain ingestion
5. retrieval-augmented composer
6. end-to-end haiku demo

**v3 amends sub-tasks 5 and 6, adds two new sub-tasks:**

5. **(amended) Dual-mode composition with hormone-driven mode-switching.** Build the natural-mode HDC walk alongside the existing Lemma chain. The hormone-modulation primitive (sub-task 1) determines which mode runs. Composer queries the procedural subspace for primitives in formal mode; queries the semantic subspace for fragments in natural mode. ~120 min Raphael-time.

6. **(amended) End-to-end demo on TWO domains, formal + natural.** Formal demo: existing math substrate with hormone-modulated rendering. Natural demo: HDC walk over Tier-1 lain-authored corpus on a single prompt ("explain HDC briefly"). The natural-mode demo proves the dual-mode architecture; haiku composition becomes a CYCLE-12 candidate after the primitive-clustering pipeline ships. ~90 min.

**NEW sub-tasks:**

7. **Primitive emergence clustering pipeline.** Build the unsupervised clustering pass that discovers recurring shell-patterns from corpus fragments. Stores discovered shells as HDC-typed primitives in the procedural subspace. ~3h Raphael-time. Empirical-test-first: does the clustering produce useful primitives or just frequency-rankings?

8. **Bootstrap primitive seeding (mitigation if clustering alone insufficient).** Hand-seed ~10-20 universal structural primitives (X-is-Y, X-causes-Y, X-but-Y, X-then-Y, etc.) as a bootstrap. The clustering builds on top. Honest about the bootstrap; the seeded primitives are STRUCTURAL UNIVERSALS, not domain primitives. ~45 min.

Total cycle 11 v3-amended estimate: ~15-20h Raphael-time. More than v2's 10-12h because v3 adds the primitive-emergence pipeline that v2 punted on by hand-coding primitives.

---

## What changes if lain greenlights v3 amendment

**Conceptually:** the cycle 11+ implementation work now centers on the corpus-ingestion + primitive-clustering pipeline (the infrastructure to make primitives EMERGE), and the dual-mode composition. The hand-built primitive library is dropped.

**Concretely:** v2's specific recommendation of "compose_haiku as cycle 11 #1" gets pushed; the new cycle 11 #1 is the hormone-modulation primitive on existing substrate (unchanged), but its purpose shifts from "demonstrating hormone mechanism" to "demonstrating MODE-SWITCHING — same Lemma chain, different rendering register."

**Repo-wise:** the v2 doc stays as the multi-region + hormone + corpus + manual-audit architecture. The v3 amendment adds the emergence + dual-mode layer. Cycle 11 implementation references both.

---

## Decision points for lain (updated from v2 + new)

1. **(v2) Hormone modulation in or out?** RECOMMEND IN (unchanged).
2. **(v2) Valence-as-binding or subspace?** RECOMMEND BINDING (unchanged).
3. **(v2) Corpus shape at scale?** RECOMMEND tier-balanced-at-scale (unchanged).
4. **(v3 new) Primitive emergence vs hand-built libraries?** RECOMMEND EMERGENCE via corpus clustering, with optional bootstrap of ~10-20 STRUCTURAL UNIVERSALS (not domain-primitives). The v2 per-domain primitive lists are REPLACED.
5. **(v3 new) Dual-mode composition (formal Lemma + natural HDC walk) vs unified composition?** RECOMMEND DUAL-MODE. The formal mode preserves the audit-rigor we already have; the natural mode handles the infinite-domain space; the hormone vector switches between them. Both are honest; neither confabulates.

---

## "Aaaah of course" reframing (now spanning v1 + v2 + v3 amendment)

- **v1's of-course:** Lemma.render() IS already text generation.
- **v2's of-course:** multi-region HDC is modulated retrieval from one shared substrate, not separate storage. Hormones bias thresholds. Opinions are bindings in semantic space.
- **v3's of-course:** primitives don't need to be enumerated — they emerge from corpus structure. Composition splits into formal-verifiable (Lemma chain, audit-trail-mandatory) vs natural-auditable (HDC walk, provenance-mandatory). Mode is hormone-driven. The architecture is ONE piece of machinery; domains are infinite; the corpus + the walk handle the open universe of concepts.

The synthesis: **one shared HDC substrate, modulated by hormones, composed in two modes (formal Lemma + natural walk), feeding off a curated huge corpus whose structural patterns emerge as the primitive vocabulary.** No domain enumeration. No hardcoded `domain=X` flags. The agent's expressive range = whatever the corpus exposes + whatever lain's audit-loop refines.

---

## Honest counter-claims (cumulative across v1 + v2 + v3)

1. **Primitive emergence is empirically unproven at this scale.** Cycle 11 #7 (clustering pipeline) is the real test. If the discovered primitives are useless (just frequency rankings), the architecture needs the bootstrap escape valve.
2. **HDC walk in natural mode is the new architectural commitment.** No formal verification per step; only provenance + manual audit. For long-form prose this can drift; quality is bounded by corpus quality + audit-loop diligence. Manual audit has to actually work.
3. **Mode switching itself can be wrong.** If hormone-classification picks the wrong mode (formal for an "explain meaning of life" prompt, or natural for a "solve 3x²-14x-5=0" prompt), the output suffers. Intent classification accuracy is empirical; cycle 11 #infra-3's multi-resolution helps but doesn't guarantee.
4. **All of v2's counter-claims still apply:** won't beat GPT-N on free-form fluency; multi-region HDC complexity; audit-loop gradient underspecified; corpus capacity-vs-noise tradeoff measured-not-proven.
5. **v3 raises the cycle-11 cost ceiling.** Previously ~10-12h; v3-amended ~15-20h. If cycle 11 stays bounded to its current scope, the primitive-emergence pipeline (sub-task 7) might land in cycle 12 instead.

---

## "Use council" — disposition

This v3 amendment was written WITHOUT a separate advisor brainstorm call, following the v2 advisor pre-write critique pattern (advisor's "skip the brainstorm call, write directly when the structural decisions are already in scope" alternative). The critique that prompted v3 came directly from lain rather than from advisor — the architecture is converging through direct lain-Discord dialogue, which is a different (and arguably stronger) signal than advisor consultation.

If lain wants a v3 advisor review specifically — fresh consult on this amendment for the empirical-testability and the primitive-emergence-feasibility questions — I can fire that on his greenlight.

---

## Sources

- v1: `docs/artifacts/cycle-10-semantics-architecture.md` (commit `0cddcd6`).
- v2: `docs/artifacts/cycle-10-semantics-architecture-v2.md` (commit `6e40560`).
- HDC infrastructure roadmap: `docs/artifacts/cycle-10-hdc-infrastructure-optimization.md` (commit `acca853`).
- Lain critique: Discord msg `1503214621891493909` (2026-05-11).
- Background: classical HDC clustering work (Plate's *Holographic Reduced Representations*; Eliasmith's *Semantic Pointer Architecture*) — primitive emergence via vector clustering is established in narrower contexts; scaling to a full text-generation primitive library is what cycle 11 #7 actually tests.

— Pairs with v2 architecture doc + HDC infrastructure roadmap. Ready for lain's read on the five decision points + cycle-11 v3-amended sequence. The "no hardcoded domain solutions" ask is engaged as the load-bearing v3 amendment.
