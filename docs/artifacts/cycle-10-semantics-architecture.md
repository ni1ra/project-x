# Cycle 10 — Semantics Architecture (current canonical)

**Status:** consolidated 2026-05-11 after iterative refinement (v1 brainstorm → v2 with lain's brain-multi-region+corpus+audit reframings → v3 amendment with lain's no-hardcode+emergence+dual-mode critique). Earlier v1, v2, v3-amendment drafts deleted per lain's no-legacy discipline; this is the single canonical reference.

**Pairs with:** `cycle-10-hdc-infrastructure-optimization.md` (the infrastructure layer underneath — operation-tier optimization, Rust port plan, dimensionality scaling).

---

## The gap (from `docs/paper.md` Chapter 9 + lain critique 2026-05-11)

The current agent has zero free-form text generation. All "natural language" output is either (a) BUILDER-authored frozen `raphael_response` in benchmark entries or (b) `Lemma.render()` structured proof shapes. Poetry baseline graded 1.2-1.3/5 in cycle 1; root cause is no generation machinery exists. Lain's directive: build it, brain-inspired, HDC-rooted, corpus-trained, manually-audited, NO hardcoded per-domain solutions.

---

## The architecture — one shared HDC substrate, hormone-modulated, dual-mode composition, corpus-emergent primitives

### Layer 1 — HDC subspaces (general-purpose, brain-inspired)

Four specialized subspaces of one shared 10k-dim hyperdimensional vector space (seed-clustered subprojections; near-orthogonal at random initialization):

- **Semantic subspace** — concept vectors. Stores facts, opinions (as `concept ⊗ valence` bindings — NOT a separate valence subspace; matches brain anatomy where limbic colors cortical memory in situ), entities, themes.
- **Syntactic subspace** — phrase-shape patterns. N-gram-typed templates.
- **Intent subspace** — planning vectors. Encodes "what the agent is trying to do this turn" (explain / argue / refuse / chat / take-action / etc).
- **Procedural subspace** — primitive/tool vectors. Maps primitive library + substrate tools to retrieval-addressable vectors.

These aren't physically separate matrices; they're subprojections of the same 10k-dim space distinguished by seed-vector clusters.

### Layer 2 — Hormone modulation (global threshold-shift)

A single `H` vector lives OUTSIDE subspaces and modulates cleanup-memory similarity thresholds across all subspaces simultaneously. Different H → different retrieval landscape → different output register.

- `H_formal` — biases toward substrate primitives + invariant cross-checks; activates Lemma chain mode.
- `H_natural` — biases toward corpus fragments + walk-style retrieval; activates HDC walk mode.

A given response can MIX modes per-Lemma-step. Mode selection is hormone-driven, NOT domain-flagged. Intent classification via HDC similarity (intent-subspace nearest-neighbor) drives hormone selection.

Brain analogue: hormones (cortisol, dopamine) are slow, broadcast, modulate excitability rather than carry content. Same role here — threshold modulation, not content production.

### Layer 3 — Dual-mode composition

**Formal mode** — `Lemma` chain unchanged from cycle-1-through-10 reasoning substrate. Structured proof; invariant cross-checks per step; audit trail per claim. Used for: math, physics-with-equations, action-taking-with-tools, anything with closed-form verifiability. Substrate primitives compose into the proof.

**Natural mode** — HDC walk through fragment-space. Each step retrieves the next fragment by HDC similarity to (current-state ⊗ intent ⊗ accumulated-context). Provenance trail per fragment (every emitted phrase points back to corpus source). Manual-audit feedback refines retrieval weights. Used for: history, humor, philosophy, poetry, casual chat, meaning-of-life questions, anything in the OPEN universe of concepts without closed-form structure.

Both modes are HONEST: formal via invariants + Lemma render; natural via provenance + manual audit. Neither confabulates.

The split is what makes the architecture handle "infinite domains" without hardcoding. Formal mode is bounded (closed-form structure required). Natural mode is open (anything in corpus + HDC walk reaches anything reachable by similarity). No `domain=X` flag anywhere.

### Layer 4 — Primitive emergence (no hand-coded per-domain libraries)

Primitives are EXTRACTED from corpus structure via unsupervised clustering, NOT hand-built. During corpus ingestion, n-gram-shell hypervectors are clustered in the procedural subspace; clusters with density above threshold become primitives.

Discovered structural shells include:
- "X is Y because Z" patterns
- "the more X, the more Y" patterns
- caesura-then-image patterns
- setup-then-punchline patterns
- when-X-then-Y temporal patterns
- claim-then-qualification patterns

These emerge naturally from a poetry corpus exposing caesura/volta structures, a physics corpus exposing law/analogy/regime patterns, a history corpus exposing temporal-causal patterns, a humor corpus exposing setup/payoff patterns. Add a new corpus domain → its patterns get clustered in → agent composes with them. No code change. No `domain=X` flag.

**Optional bootstrap** (mitigation if pure-unsupervised clustering insufficient): hand-seed ~10-20 STRUCTURAL UNIVERSALS (X-is-Y, X-causes-Y, X-but-Y, X-then-Y) — these are domain-agnostic structural patterns, not domain-specific primitives. The clustering builds on top. Honest about the bootstrap.

### Layer 5 — Curated corpus-at-scale + manual-audit feedback

**Corpus shape** (tier-balanced, ~tens of millions of words total, source-provenance metadata per fragment):

- **Tier 1 — Lain-authored (~100k words; voice anchor):** Discord messages, code, paper.md, MANIFESTO, dev-cycle reflections. Tagged `voice=lain`. Retrieval prioritizes lain-tagged fragments when hormone is `H_chat` or `H_default` so Raphael's phrasing aligns to lain's.
- **Tier 2 — Domain-canonical curated (~1M-10M words per domain):** Public-domain poetry (Project Gutenberg); physics textbooks (Feynman, Griffiths) + curated arxiv abstracts; math (Hardy+Wright + Davenport + Lang); curated dialogue corpora (NOT GPT-generated; that would distill a transformer through the back door); scripting examples + tool documentation for action-taking. Sources tagged + citable.
- **Tier 3 — Lain's curated reading (optional growth):** Essays / blogs / papers lain explicitly flags.
- **Tier 4 — Synthetic from substrate (small, ongoing):** Agent's own Lemma-render outputs after lain audit.

**HDC capacity at 10k-dim:** ~10⁸ associations before noise dominates retrieval. Tens of millions of fragments × ~10 tokens each = ~10⁸-10⁹ tokens total. Fits. Memory IS the model; no learned weights, no gradient descent.

**Provenance is the honesty layer.** Every retrieved fragment carries source metadata. The agent never generates "beyond what it has stored + composed." Out-of-scope → honest refusal (same shape as math primitives refusing on indefinite forms).

**Manual-audit feedback loop (the load-bearing training signal):**

- Agent generates output; reports per-slot retrieval-confidence + per-primitive selection-confidence + aggregated chain confidence.
- Lain audits LOW-CONFIDENCE generations preferentially via Discord (👍 approve / 👎 reject / ✏️ correct).
- Audit signals propagate back as binding-strength adjustments. For opinion corrections, adjust the specific `(concept ⊗ valence)` binding directly.
- CLI + Discord as v0 audit UI; no web app required.

---

## "Aaaah of course" reframing (cumulative)

- The brain's compartmentalization isn't separate STORAGE; it's modulated RETRIEVAL from one shared substrate. HDC is that substrate. Regions are seed-clustered subspaces.
- Hormones bias retrieval thresholds. They're how mode-switching works without separate circuits.
- Opinions are bindings IN semantic space (not a separate valence space) — matches limbic-cortical anatomy.
- Composition splits into formal-Lemma (audit-trail) + natural-HDC-walk (provenance-trail). Domains are infinite; the corpus + walk handle them; no enumeration.
- Primitives emerge from corpus structure; not hand-built per domain.
- `Lemma.render()` IS the surface assembler for formal mode; HDC walk IS the surface assembler for natural mode.
- Curated huge corpus + manual audit IS the training mechanism. HDC's perfect-memory property is what makes scale viable.

Synthesis: **one shared HDC substrate, hormone-modulated, dual-mode composition (formal Lemma + natural walk), feeding off a curated huge corpus whose structural patterns emerge as primitives, refined by lain's manual audit loop.**

---

## Decision tree for lain (5 branches)

1. **Hormone modulation in or out?** RECOMMEND IN — load-bearing for mode-switching; empirically testable cheaply in cycle 11 #1.
2. **Valence-as-binding or separate subspace?** RECOMMEND BINDING (in semantic space) — matches brain anatomy; simpler audit-loop.
3. **Corpus shape?** RECOMMEND tier-balanced-at-scale (Tier 1 voice anchor + Tier 2 domain canonical at 1-10M words each + Tier 3-4 optional).
4. **Primitive emergence vs hand-built libraries?** RECOMMEND EMERGENCE via corpus clustering, with optional STRUCTURAL-UNIVERSAL bootstrap. No per-domain primitive lists.
5. **Dual-mode composition vs unified?** RECOMMEND DUAL-MODE (formal Lemma + natural HDC walk). Hormone switches; mixes per-Lemma-step OK. Handles infinite domains without hardcoding.

---

## Cycle 11 implementation sequence (~15-20h Raphael-time)

Combined with cycle-11-infrastructure work from `cycle-10-hdc-infrastructure-optimization.md`:

1. **#1 hormone-modulation primitive on existing math substrate (~45 min).** No corpus required. Add `register: str = "default"` to `Lemma.render()` with `terse / default / tutorial / casual` registers. Demonstrates mode-switching mechanism empirically — qualitatively-different output flavors from the same chain. If hormone modulation produces real flavor differences, the architecture's foundation holds; if it doesn't, rethink before corpus investment.
2. **#2 opinion bindings (~60 min).** Hand-seed ~50-100 concept-vectors with valence bindings on philosophy/persona domain. Demonstrate "what do you think of X" routing.
3. **#3 Tier-1 corpus ingestion + audit UI (~3h).** Build encoding pipeline + provenance-tagging + the audit UI. Ingest lain-authored corpus (~100k words). One-time pipeline work that unlocks all later tiers.
4. **#4 Primitive emergence clustering pipeline (~3h).** Unsupervised clustering of n-gram-shell hypervectors in the procedural subspace. Empirical-test-first: does it produce useful primitives or just frequency-rankings? Bootstrap fallback ready (~45 min) if clustering insufficient.
5. **#5 Tier-2 per-domain corpus ingestion (~30-60 min per domain × 5 domains).** Run pipeline on poetry / physics / math / chat / action corpora. Atomic per-domain ships.
6. **#6 Dual-mode composer (~2h).** Build the natural-mode HDC walk alongside Lemma chain. Hormone selects mode.
7. **#7 End-to-end demo on two domains: formal + natural (~90 min).** Formal: existing math substrate with hormone-modulated rendering. Natural: HDC walk on a single prompt over the Tier-1 ingested corpus.

Total ~12-18h. Cycle 11 primary thread if greenlit; otherwise split across cycles 11-12.

---

## Honest counter-claims

1. **Primitive emergence clustering is empirically unproven at this scale.** Cycle 11 #4 IS the test. If discovered primitives are useless, bootstrap escape valve kicks in.
2. **HDC walk in natural mode has no formal verification per step.** Only provenance + manual audit. For long-form prose this can drift; quality bounded by corpus + audit diligence.
3. **Mode switching can be wrong.** Intent-classification accuracy is empirical.
4. **Won't beat GPT-N on free-form fluency.** Thesis: competence + honesty + auditability + provenance, not fluency match.
5. **Cycle-11 cost ceiling is real.** ~15-20h is a lot for one cycle; primitive-emergence pipeline may slip to cycle 12.
6. **Corpus provenance is the honesty layer; provenance has to actually work** — every retrieved fragment must trace back to source even when fragments get composed across retrieval steps.
7. **HDC at 10⁸ associations starts degrading non-linearly.** The capacity claim is back-of-envelope; cycle 11 #1 of the HDC-infra plan measures it empirically with bitwise-packed representation.

---

## "Use council" disposition

This canonical doc consolidates v1 (advisor 5-candidate scaffold), v2 (incorporates lain's brain+corpus+audit reframings; advisor pre-write surfaced opinion-as-binding correction), v3 amendment (lain's no-hardcode + emergence + dual-mode critique). Two advisor calls fired in the design path; lain's three Discord critiques drove the more substantive reframings. The v1-v2-v3 iteration files have been removed per lain's no-legacy discipline. Available to fire a fresh advisor consult on this canonical doc on lain greenlight if needed.

---

## Sources

- `docs/artifacts/cycle-10-hdc-infrastructure-optimization.md` (commit `acca853`) — paired infrastructure roadmap.
- Pentti Kanerva, *Hyperdimensional Computing* (2009) — HDC fundamentals; 10k-dim canonical choice; capacity bounds.
- Plate, *Holographic Reduced Representations* — binding + cleanup memory.
- Eliasmith, *Semantic Pointer Architecture* — neural-architecture-inspired HDC composition.
- Lain Discord critiques 2026-05-11 (msgs `1503208357`, `1503208951`, `1503212043`, `1503212366`, `1503213942`, `1503214621`, `1503215121`) — the iterative refinement that produced this canonical doc.
- The cycle 10 #1 predicate-strength uniformity pass — establishes the rigor pattern formal-mode primitives must honor.

— Ready for lain's read on the 5 decision points + cycle-11 sequence. Architecture is one shared HDC substrate with hormone-modulated dual-mode composition over a corpus-emergent primitive vocabulary; no domain enumeration; honest at every layer.
