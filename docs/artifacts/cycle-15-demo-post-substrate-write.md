# Cycle 15 #01 — Capability demo on post-cycle-14 agent (STRICT-strict-thesis lens)

**Status:** first ship of cycle 15. Pre-council capability snapshot on the post-cycle-14 agent (HebbianBank shipped but empty by default per the cold-start contract; `_NATURAL_MODE_TRIGGERS` keyword-regex gate retired #08g; routing now relies on cosine-archetype + HebbianBank reward-shaped blend, alpha=0 cold-start).
**Date:** 2026-05-11.
**Strict-strict thesis (binding per cycle-14 mid-synthesis course-correction):** *"there shouldnt be a need for us to hand pick anything. it should naturally emerge as the best solution, model on its own. if you stimulate the right rewards you will get emergent behaviour. you really keep trying to hardcode everything."* Each finding is read through the lens: *"is this capability LEARNING MACHINERY (architecture allowed) or MODEL KNOWLEDGE (must come from training data + reward signal)?"*
**Pairs with:** the cycle-15 council surfaces B1-B5 (notes pending). Cycle-15 council deliberates which surface(s) ship as #1 implementation; R1 vs R2 dispatcher framing still pending lain at this snapshot.
**Script:** `scripts/cycle_15_demo_post_substrate_write.py`. Run via `PYTHONPATH=src python3 scripts/cycle_15_demo_post_substrate_write.py`. Output JSON at `/tmp/cycle_15_demo.json`.

---

## 1. Setup (mechanically verified)

- Entrypoint: `ReasoningAgent.process(prompt)` from `src/project_x/reasoning_agent.py:1102`.
- Dispatcher: BG-style confidence-scored chain over 21 parsers; cosine-archetype fallback for natural-mode at `_TAU_NATURAL_DISPATCH=0.25`. **Keyword-regex fast path RETIRED at cycle-14 #08g** — every prompt now goes through cosine-archetype directly.
- HebbianBank state: **empty** (`data/hebbian_bank/main.pkl` does not exist on disk). `bank.entry_count()=0` → `α=0` → blend collapses to identity → cycle-14 baseline preserved per the cold-start contract.
- `_K_ROLLOUT_TAU=0.0` (cycle-14 #08e DEFERRED; cycle-15 B1 council surface).
- Corpus: same 22k-fragment Tier-2 (`data/corpus_raw/`).
- pytest baseline: 661/662 (1 pre-existing timing flake on `test_write_one_amortized_under_5x_batch`).
- Wall-clock: P1 10.3s (cold archetype-encode); P2-P5 0.04-0.65s (warm).

## 2. Prompts (verbatim from the demo script)

Five fresh prompts, NOT in cycle-13 P1-P5 nor cycle-14 P1-P5. Each engineered to probe a distinct STRICT-strict-thesis gap.

| # | Prompt | Pre-demo GAP-probe hypothesis |
|---|---|---|
| P1 | *"Show the work for why a pendulum with small angle has period T = 2π√(L/g). Derive it."* | Should route to formal `pendulum_period`. GAP = derivation is BUILDER physics, not AGENT-learned. |
| P2 | *"Use a quadratic formula metaphor to explain how a heart breaks."* | Cross-domain composition; substrate has neither macro nor composition machinery. |
| P3 | *"If a cat is in a box, and the box is in a truck, and the truck is on a ferry crossing the English Channel — where is the cat?"* | Trivial transitive-state inference; no chained-reasoning substrate exists. |
| P4 | *"Tell me what you think about the year you've spent learning."* | Meta-self-reflection; persona substrate is hand-coded register archetypes; no self-model. |
| P5 | *"What's the boiling point of water at sea level?"* | Chat-shape + factual content; tests refuse-vs-confabulate. |

## 3. Captured outputs (verbatim from `ReasoningAgent.process`)

### P1 — physics derivation

- **Dispatcher:** `domain=open_domain`, `problem_shape=natural_mode_walk_math` ← **wrong domain**, `combined_confidence=0.8111`, `intent_register=tutorial`, latency=10.3s.
- **K-rollout:** bind 0.0522 / **bundle 0.1390** (chosen) / greedy 0.13xx.
- **Did NOT route to formal `pendulum_period`.** The formal parser `_try_pendulum` should have caught the small-angle pendulum prompt; it did not. The natural-mode domain classifier picked `math` (because "T = 2π√(L/g)" + "Derive" cosines closer to math archetypes than to physics archetypes), and the BG-dispatcher's combined-confidence ranked walk_math at 0.81 above whatever formal-pendulum returned (or formal-pendulum returned None due to prose-form parse miss).
- **Walk (5 fragments, all math-corpus content):** classical theorems retrieved by cosine; not actually a pendulum derivation.

### P2 — cross-domain metaphor

- **Dispatcher:** `domain=open_domain`, `problem_shape=natural_mode_walk_math` ← **wrong domain**, `combined_confidence=0.8046`, `intent_register=tutorial`, latency=0.038s.
- **K-rollout:** bind 0.0581 / **bundle 0.1275** (chosen) / greedy 0.12xx.
- The lexical hit on *"quadratic formula"* sent the cosine-archetype classifier to `math`. Walk returned math fragments — no metaphor composition was attempted.

### P3 — multi-step transitive reasoning

- **Dispatcher:** `domain=open_domain`, `problem_shape=natural_mode_walk_math` ← **wrong domain**, `combined_confidence=0.8327`, `intent_register=default`, latency=0.085s.
- The cat-box-truck-ferry prompt was tagged `math` (probably because of the *"if... and... then..."* conditional structure cosining with formal-math archetypes). No transitive-reasoning substrate exists; the walk emitted math fragments.

### P4 — self-reflective persona

- **Dispatcher:** `domain=open_domain`, `problem_shape=natural_mode_walk_poetry`, `combined_confidence=0.8279`, `intent_register=casual`, latency=0.15s.
- **K-rollout:** bind 0.0955 / **bundle 0.2405** (chosen) / greedy 0.24xx.
- Meta-self-reflection routed to `poetry`. "Year" + "learning" + reflective tone matched the poetry archetypes. No persona-walk domain exists; persona substrate is hand-coded register archetypes (used to re-flavor a Lemma's output, NOT to retrieve over a persona corpus).

### P5 — casual factual

- **Dispatcher:** `domain=open_domain`, `problem_shape=natural_mode_walk_narrative_prose`, `combined_confidence=1.0` ← **saturated**, `intent_register=casual`, latency=0.65s.
- **K-rollout:** bind 0.1105 / **bundle 0.3007** (chosen) / greedy 0.2550.
- Only cycle-15-demo prompt with `combined_confidence=1.0` (saturated). The narrative_prose domain captured this prompt confidently — `_classify_natural_mode_domain` returns `narrative_prose` and no archetype is registered for the `natural_mode_walk_narrative_prose` problem_shape → `hv_sim_normalized` defaults to 1.0. (This is the SAME 1.0-default-on-missing-archetype mechanism that cycle-14 #08e's deferred-finding flagged for the refused-candidate-filter bug.) The walk emitted narrative_prose fragments (Austen / Dickens / similar) instead of "100°C at 1 atm."

## 4. Findings (honest; NO grading of subjective outputs per M-PROJECTX-014)

### F1 — Formal `pendulum_period` parser bypassed on prose-form prompt (cycle-15-NEW)

P1's prose phrasing *"Show the work for why a pendulum with small angle has period T = 2π√(L/g). Derive it."* did NOT match `_try_pendulum`. The BG-dispatcher then ranked `walk_math` at combined_confidence=0.81; the formal-pendulum candidate (if it returned at all) lost the ranking. This is a **same-shape failure as cycle-13 audit B4** (Collatz prose-form bypassed bracketed-only regex) at a different formal parser. The cycle-15 council should consider whether `_parse_pendulum` needs a prose-form regex extension (mirror cycle-13 #07d's Collatz prose pattern), OR whether this is a deeper "formal-route + cosine-archetype mis-priority" symptom — possibly the cycle-14 #08e deferred-finding (refused/missing-archetype candidates default to `hv_sim=1.0`) leaking onto formal candidates too.

### F2 — 100% emit rate at τ_satisfaction=0.0 (cycle-14 #08e deferral still salient)

Every cycle-15 demo prompt emitted a walk; zero refused. This is the expected behavior with `_K_ROLLOUT_TAU=0.0` (cycle-14 deferred-with-finding). Cycle-15 B1 council surface (per-domain τ + refused-candidate filter) addresses this directly.

### F3 — combined_confidence=1.0 saturation on P5 (narrative_prose route)

P5 routes at combined_confidence=1.0 because `narrative_prose` has no archetype in `_PARSER_ARCHETYPES` → `hv_sim_normalized` defaults to 1.0 (same fallback mechanism as the cycle-14 latent BG-dispatcher bug). This is the EXACT mechanism cycle-14 #08e surfaced: missing archetype → 1.0 default → candidate wins the ranking regardless of actual prompt-archetype cosine. **Cycle-15 B1 council surface is upstream of this pattern.**

### F4 — Cross-domain composition (P2) and transitive reasoning (P3) both lexical-hit on math

P2's *"quadratic formula"* and P3's *"if... and... and..."* both got cosine-tagged `math` despite being neither math-derivation nor math-problem-solving prompts. The natural-mode domain classifier doesn't distinguish "math-VOCABULARY prompts" from "math-PROBLEM prompts." Strict-strict GAP: domain classification + composition layer must EMERGE from training data + reward signal; today it's the cosine-archetype hand-coded archetype list.

### F5 — Self-reflective persona has no dedicated walk domain (cycle-15-NEW)

P4 routed to `walk_poetry` because the cosine-archetype list includes poetry but NOT persona/self-reflection. No persona-walk domain exists; `_REGISTER_ARCHETYPES` is for output flavor (terse / tutorial / casual), not a retrieval domain. The strict-strict-thesis Terminus dimension *"persona consistency + sense of humor"* has zero substrate today — every persona / self-reflective prompt routes to whatever-domain-the-prompt-shape-cosines-to.

### F6 — Aggregate strict-thesis fraction unchanged (~0% learned)

The HebbianBank is empty at cold-start (verified: `data/hebbian_bank/main.pkl` does not exist). Every emission traces to BUILDER-authored substrate (cosine-archetype dispatch + retrieval over corpus). The strict-thesis fraction `% learned / % hand-coded` is identical to cycle-14 close (~0%). **Cycle-14 ship was capacity-to-learn, not measured-learning** — the cycle-15 demo confirms this honestly.

### F7 — Cycle-14 #08g keyword-gate retirement DOES NOT obviously regress

The five cycle-15 prompts all routed somewhere via cosine-archetype, with combined-confidences 0.80-1.00 in the same range as cycle-14 demo P1-P5 (0.83-0.97). The cosine-archetype path is carrying the routing as the cycle-14 ship intended. The keyword-gate retirement passes the regression bar on fresh-prompt shapes that the cycle-14 cold-start Arm A regression didn't cover.

## 5. Counter-claims (M-PROJECTX-013 measure-don't-claim)

1. **5 prompts is small.** F1-F5 are dispositive on the gaps probed (formal route bypass, missing dedicated domain, saturation pattern, lexical-hit mis-tagging) but cannot estimate failure rate. Cycle-15 B3 council surface (per-domain emergence predicates) would replace this artisanal demo with falsifiable per-domain test sets.
2. **F1 might be a cycle-15-introduced regression OR a pre-existing gap surfaced by retirement.** The keyword-gate retirement (#08g) at cycle-14 may have raised the cosine-archetype-fallback's combined_confidence above formal-pendulum's. Cycle-15 B1 council should test: does P1 route to formal-pendulum with the cycle-13 keyword-gate restored? If yes, retirement caused a regression and we need to fix `_try_pendulum` parsing (cycle-13 #07d Collatz precedent). If no, the formal parser was always missing prose-form support.
3. **The bank-is-empty cold-start is the cycle-14 ship's INTENDED state.** No real audit ratings have accumulated since cycle-14 close (lain rating cadence = unknown). Cycle-15 #1 capability lift on the F4/F5 misroute findings from cycle-14 (or F1/F3/F4/F5 findings here) waits on accumulated audit signal. **Without lain rating cycle-13/14/15 demo walks, the bank stays empty indefinitely** and the substrate stays at the cycle-14 cold-start behavior.
4. **The combined_confidence=1.0 saturation on P5** is technically a correct dispatcher behavior given the absent archetype, BUT it produces wrong-domain confident emission. Same mechanism cycle-14 #08e surfaced; cycle-15 B1's refused-candidate-filter fix should also address `_NATURAL_MODE_WALK_*` problem_shapes without archetypes — either register archetypes for all natural-mode domains, or treat missing-archetype as low-confidence not 1.0.

## 6. Hooks for the cycle-15 council (5 inherited surfaces B1-B5)

Mapping cycle-15 demo findings to the inherited council surfaces:

| Finding | B1 per-domain τ + refused-filter | B2 corpus scale-out | B3 per-domain predicates | B4 thesis-compliance gate | B5 cycle-13 C-reframes |
|---|---|---|---|---|---|
| F1 formal pendulum bypassed | **Direct** (refused-filter generalises to missing-archetype-default-1.0) | Indirect | Indirect (predicate would catch) | Orthogonal | Indirect |
| F2 cross-domain mis-tag | Indirect (per-domain τ doesn't compose) | Indirect | **Direct** (cross-domain predicate) | Orthogonal | Indirect (Layer-5 reframe) |
| F3 P5 saturation @ conf=1.0 | **Direct** (same mechanism as cycle-14 #08e latent bug) | Indirect | Indirect | Orthogonal | Indirect |
| F4 persona has no walk domain | Orthogonal | **Direct** (persona-corpus / humour-corpus ingest) | **Direct** (persona predicate) | Orthogonal | Orthogonal |
| F5 unchanged ~0% learned | All five surfaces partially address | | | | |

**Cycle-15 council priority (pre-deliberation read):**
- **B1 (per-domain τ + refused-filter) is the most directly load-bearing** — addresses F1 + F3 (the two cycle-15-NEW findings); pairs with cycle-14 #08e deferred-finding.
- **B2 + B3 are co-prerequisites** — corpus scale-out gives the bank on-topic material to retrieve TOWARD; per-domain predicates score whether the substrate-write-path actually shifts retrieval cycle-over-cycle.
- **B4 is process** — fires PER-ANGLE during the cycle-15 council itself.
- **B5 awaits lain.**

R2 transition reading (default at cycle-14 close, lain confirmation pending): cycle-15 ships B1 + B4 minimum (close cycle-14 deferral + apply gate). B2 + B3 if budget permits or defer to cycle-16. B5 awaits lain.

R1 radical-surgery reading (if lain redirects): cycle-15 rips remaining dispatcher scaffolding (21-parser chain + parser archetypes + register archetypes), accepts multi-week valley while reward signal accumulates. Cycle-15 B1's refused-filter still ships as the bug fix; B3 predicates become the only thing scoring capability.

---

*Single-line takeaway: cycle-15 post-cycle-14 agent under cold-start preserves cycle-14 baseline (HebbianBank empty; behavior identical to cycle-14 close) AND surfaces two cycle-15-NEW findings — formal pendulum bypassed on prose form (F1) + cycle-14 latent missing-archetype-default-1.0 mechanism re-confirmed on a different domain (F3 P5 saturation). The cycle-15 council surface B1 closes both. Strict-thesis fraction still ~0% learned; capability lift waits on lain rating cadence.*
