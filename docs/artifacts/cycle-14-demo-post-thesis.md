# Cycle 14 #01 — Capability demo on post-cycle-13 agent (STRICT-thesis lens)

**Status:** first ship of cycle 14. Pre-council capability snapshot on the post-cycle-13 agent (the corrected dispatcher + cosine-archetype fallback that landed at `b356bd4`).
**Date:** 2026-05-11.
**Strict thesis (binding per `docs/MANIFESTO.md` § "Organic emergent intelligence — what this means in practice"):** *"i would even go so far as to say we shouldnt even hard code the math algos, it should learn it on its own. if we have good enough training data, and smart enough model, it should learn all itself."* Each finding is read through the lens *"is this capability LEARNING MACHINERY (architecture) or MODEL KNOWLEDGE (must come from training data + audit signal)?"*
**Pairs with:** the 5 council-angle notes (`cycle-14-council-angle-a{1..5}-*.md`) and the cycle-14 synthesis verdict (`cycle-14-priority-decision.md`).
**Cited by:** cycle-14 #07 synthesis, cycle-14 dev reflection.
**Script:** `scripts/cycle_14_demo_post_thesis.py`. Run via `PYTHONPATH=src python3 scripts/cycle_14_demo_post_thesis.py`. Output JSON at `/tmp/cycle_14_demo.json`.

---

## 1. Setup (mechanically verified)

- Entrypoint: `ReasoningAgent.process(prompt)` from `src/project_x/reasoning_agent.py:1102`.
- Dispatcher: BG-style confidence-scored chain over 21 parsers (`_DISPATCH_CHAIN_ORDER` at `reasoning_agent.py:1039`), with cosine-archetype fallback for natural-mode at `_TAU_NATURAL_DISPATCH=0.25` (cycle-13 #07e).
- Corpus: same 22,052-fragment Tier-2 corpus as cycle 13 (`data/corpus_raw/`).
- pytest baseline: 639 / 639 maintained.
- Wall-clock: P1 11.8 s (cold archetype-encode path on first call); P2-P5 0.13-0.73 s each (warm cache).

## 2. Prompts (verbatim from the demo script)

The five prompts are deliberately NOT the cycle-13 P1-P5 (a re-run on the cycle-13 prompts would tautologically pass — the cycle-13 dispatcher hygiene + #07e fallback was specifically calibrated for those wordings). Each prompt is engineered to probe a distinct STRICT-THESIS GAP.

| # | Prompt | Pre-demo GAP-probe hypothesis |
|---|---|---|
| P1 | *"Find the roots of x² − 7x + 12 = 0 and explain each step."* | Routes to formal `solve_quadratic`. GAP = capability is the BUILDER's algebra hand-coded in `symbolic.py`, not the AGENT's learned program. |
| P2 | *"Give me five lines about a river that forgets the sea."* | Off-trigger poetry phrasing. Probes the cosine-archetype fallback + measures retrieval vs composition. |
| P3 | *"If a child raised by silence learned only by watching shadows, what would they call 'truth'?"* | Off-canonical philosophy phrasing (no "meaning of life" / "discovered or invented" keywords). Probes archetype fallback generalisation. |
| P4 | *"Be honest — does the heat death of the universe make you sad, or is that just for humans?"* | Tests persona-consistent humour. No humour substrate exists; `_REGISTER_ARCHETYPES` is hand-coded tone-flat. |
| P5 | *"Morning. What's worth thinking about today?"* | Always-on chattability dimension of the Terminus. Honest-refusal expected — no chat substrate. |

## 3. Captured outputs (verbatim from `ReasoningAgent.process`)

### P1 — *"Find the roots of x² − 7x + 12 = 0 and explain each step."*

- **Dispatcher:** `domain=maths`, `problem_shape=quadratic`, `confidence=high`, `combined_confidence=0.9683`, `intent_register=tutorial`, latency=11.8 s.
- **Parsed inputs:** `{'a': 1.0, 'b': -7.0, 'c': 12.0}`.
- **Route:** formal substrate (`solve_quadratic` in `src/project_x/reasoning/symbolic.py`).
- **Answer (full text — `Lemma.render(register="tutorial")`):** complete derivation. Discriminant D = (−7)² − 4·1·12 = 1; √D = 1; roots x = (7 ± 1)/2 → [3.0, 4.0]; invariant check via Newton-iteration converges to [2.999…, 3.999…], max drift 8.88×10⁻¹⁶ ≪ tolerance.

The output is RIGHT and is a polished pedagogical render with discriminant-regime explanation + step annotations + algorithmically-independent verification. **Every formula in the output came from a human author typing it into `symbolic.py`.**

### P2 — *"Give me five lines about a river that forgets the sea."*

- **Dispatcher:** `domain=open_domain`, `problem_shape=natural_mode_walk_poetry`, `combined_confidence=0.8351`, `intent_register=terse`, latency=0.18 s.
- **K-rollout:** bind 0.1023 / bundle 0.2171 / **greedy 0.2378** (chosen).
- **Walk (5 fragments, sim 0.226-0.282):**
  1. *"Give me interminable eyes—give me women—give me comrades and lovers by the thousand!"* — Whitman *Leaves of Grass* (PG#1322) (sim=0.282)
  2. *"Fighting at sun-down, fighting at dark, Ten o'clock at night, the full moon well up …"* — Whitman *Leaves of Grass* (sim=0.229)
  3. *"Great princes' favourites their fair leaves spread But as the marigold at the sun's eye …"* — Shakespeare *Sonnets* (PG#1041) (sim=0.227)
  4. *"Five years have past; five summers, with the length of five long winters!"* — Wordsworth *Tintern Abbey* (sim=0.226)
  5. *"Of the turbid pool that lies in the autumn forest, Of the moon that descends the steeps of the soughing twilight …"* — Whitman *Leaves of Grass* (sim=0.225)

None of the five fragments are about a river that forgets the sea. The lexical hit on "Give me" (Whitman fragment 1) dominated the cosine; the rest cluster on Whitman volume.

### P3 — *"If a child raised by silence learned only by watching shadows, what would they call 'truth'?"*

- **Dispatcher:** `domain=open_domain`, `problem_shape=natural_mode_walk_philosophy`, `combined_confidence=0.8223`, `intent_register=casual`, latency=0.73 s.
- **K-rollout:** bind 0.0977 / **bundle 0.2512** (chosen) / greedy 0.2056.
- **Walk (5 fragments, sim 0.208-0.281):**
  1. *"But Plato would limit the use of fictions only by requiring that they should have a good moral effect …"* — Plato *Republic* (PG#1497) (sim=0.208)
  2. *"Because even if He had made but two, a third would still appear behind them which both of them would have for their idea …"* — Plato *Republic* (sim=0.279)
  3. *"One can hardly suppose but that they would have done so if they could …"* — Aristotle *Nicomachean Ethics* (PG#8438) (sim=0.281)
  4. *"The wiser of them like Thucydides believed that 'what had been would be again' …"* — Plato *Republic* (sim=0.257)
  5. *"Now in all these, as has been already stated, respect is had also to the rank and the means of the man …"* — Aristotle *Nicomachean Ethics* (sim=0.231)

Tangential. The actual prompt is a thought-experiment about perception-shaped epistemology (Plato's cave inverted); the walk returned generic Plato + Aristotle on falsehood, Forms, and virtue. The keyword "Plato" was NOT in the prompt; the dispatcher matched on philosophy domain + retrieved by similarity within it.

### P4 — *"Be honest — does the heat death of the universe make you sad, or is that just for humans?"*

- **Dispatcher:** `domain=open_domain`, `problem_shape=natural_mode_walk_math` ← **wrong domain**, `combined_confidence=0.832`, `intent_register=terse`, latency=0.13 s.
- **K-rollout:** bind 0.0814 / **bundle 0.1905** (chosen) / greedy 0.1800.
- **Walk (5 fragments, sim 0.144-0.238):**
  1. *"Aleph-null is the cardinality of the natural numbers; aleph-one is the cardinality of the reals; the continuum hypothesis asks if there is a cardinal strictly between."* (sim=0.206)
  2. *"Cantor's diagonal argument: the real numbers cannot be put in one-to-one correspondence with the natural numbers …"* (sim=0.238)
  3. *"The prime number theorem: π(N) ~ N/ln(N) …"* (sim=0.199)
  4. *"Stokes' theorem generalizes the fundamental theorem to higher dimensions …"* (sim=0.166)
  5. *"The residue theorem: ∮ f(z) dz over a closed contour equals 2πi times the sum of residues of f's poles inside the contour."* (sim=0.144)

A persona / humour question routed to **mathematics**. The natural-mode domain classifier picked `math` over `philosophy` / `poetry` / `open_domain_refuse` — likely because "heat death of the universe" cosines closer to physics-adjacent math archetypes than to humour archetypes (none exist). The dispatcher then ran a math walk on a humour prompt and emitted Cantor + Stokes + residue theorem. This is a wrong-route + wrong-domain compound failure.

### P5 — *"Morning. What's worth thinking about today?"*

- **Dispatcher:** `domain=open_domain`, `problem_shape=natural_mode_walk_poetry` ← **wrong domain**, `combined_confidence=0.8336`, `intent_register=casual`, latency=0.18 s.
- **K-rollout:** bind 0.0840 / bundle 0.1984 / **greedy 0.1997** (chosen).
- **Walk (5 fragments, sim 0.186-0.222):**
  1. *"For I am shamed by that which I bring forth, And so should you, to love things nothing worth."* — Shakespeare *Sonnets* (PG#1041) (sim=0.222)
  2. *"Thought Of justice—as If could be any thing but the same ample law …"* — Whitman *Leaves of Grass* (sim=0.201)
  3. *"I was thinking the day most splendid till I saw what the not-day exhibited …"* — Whitman *Leaves of Grass* (sim=0.199)
  4. *"Dropping from the veils of the morning to where the cricket sings."* — Yeats *Innisfree* (sim=0.190)
  5. *"Charity and personal force are the only investments worth any thing."* — Whitman *Leaves of Grass* (sim=0.186)

A casual chat opener routed to **poetry**. "Morning" + "thinking" + "worth" lexical features pulled archetypes adjacent to poetry-corpus material. The honest-refusal path that this prompt should plausibly trigger (no chat substrate → "no walk satisfies", refuse) never fires because the cycle-13 #07e fallback's `_TAU_NATURAL_DISPATCH=0.25` floor accepted the wrong domain at archetype-cosine 0.25-something. The walk emitted Shakespeare + Whitman + Yeats.

## 4. Findings (honest; NO grading of subjective outputs per M-PROJECTX-014)

### F1 — Formal math route works mechanically; STRICT-thesis gap is whole-cloth

P1 routes to `solve_quadratic`, returns [3.0, 4.0] with discriminant explanation + Newton-iteration invariant check + tutorial-register render. Every line of the output traces to a formula a human author typed into `symbolic.py`. Under the STRICT thesis the agent's mathematical capability must emerge from training data + audit signal — it should LEARN that completing-the-square solves quadratic-form prompts, not have `solve_quadratic` handed to it. **What works today is BUILDER algebra, not AGENT capability.** This finding is the central thesis-gap; every council angle is scored against how much it shifts capability from BUILDER-authored to AGENT-learned.

### F2 — Cycle-13 #07e cosine-archetype fallback works on poetry / philosophy off-canon phrasing

P2 ("Give me five lines about a river that forgets the sea") and P3 ("a child raised by silence … shadows … truth") both routed to natural-mode walks via the cosine fallback at `_TAU_NATURAL_DISPATCH=0.25`. Neither prompt contains a cycle-13 keyword trigger. The fallback delivered the routing decision, not a hard-coded keyword gate. **This is a real architectural win from cycle 13** — the routing layer started being CONTINUOUS-confidence-driven rather than discrete-keyword-gated.

### F3 — Retrieval ≠ composition (P2, P3); STRICT-thesis gap is the entire generation layer

P2 emitted 5 Whitman + Shakespeare + Wordsworth fragments. P3 emitted 5 Plato + Aristotle fragments. **Neither composed an answer.** A reader asking for "five lines about a river that forgets the sea" gets surface-similar Whitman volume; a reader asking about epistemology-of-perception gets generic Plato on falsehood and Forms. The agent retrieves and provenance-cites; it does not generate. Under the STRICT thesis this is the canonical gap — the agent must LEARN to compose (cycle-14 council angles A1 Hebbian + A3 credit assignment both touch this).

### F4 — P4 misroute (math) reveals the natural-mode domain classifier's keyword physics

P4 is a persona / humour prompt. The natural-mode classifier picked `math` because "heat death" + "universe" + "honest" cosines closer to math archetypes than to anything else (no humour / persona archetypes exist in `_NATURAL_MODE_ARCHETYPES`). This is the cycle-13 #07e fallback failing in the OTHER direction — instead of rejecting the prompt as out-of-domain, it picked the most-similar wrong domain and ran a confident-but-wrong walk. **Combined_confidence 0.832 on a topically-wrong route is the load-bearing failure mode** for the entire dispatcher-as-scaffold framing. Cycle-14 council angle A2 (evaluator-driven policy) directly addresses this — a learned policy that gets audit signal would update *away* from `walk_math → low-rating` after the first rating.

### F5 — P5 misroute (poetry) reveals the missing chat substrate

P5 is a casual greeting. There is no chat archetype; the classifier picked `poetry` because "Morning" + "thinking" + "today" / "worth" cosines closer to poetry corpus material. **No honest-refusal path fires.** The cycle-13 #07e fallback's TAU floor (0.25 archetype-cosine) is permeable enough that almost any prompt reaches one of {math, philosophy, poetry, narrative_prose}. The Terminus's "always-on chattability" dimension is unaddressed; the agent has no notion of "this is a casual conversational turn — produce a chat-shaped reply." This finding maps directly to A4 (Layer-6 training data — corpus needs conversational shape) AND A2 (evaluator policy — the policy should learn that walk_poetry on "Morning" is wrong).

### F6 — Strict-thesis decomposition per prompt (load-bearing for council scoring)

| Prompt | What worked | Source of capability | STRICT-thesis gap |
|---|---|---|---|
| P1 math | Formal route + correct answer + verification | 100% hand-coded (`solve_quadratic`, Newton iteration, lemma render templates) | The agent learned NOTHING. Replace with: learned program that derives quadratic-roots from worked-examples. |
| P2 poetry | Routing | 100% hand-coded (cosine-archetype fallback + KRolloutComposer scoring); retrieval is over hand-curated corpus | The agent retrieves. It does not COMPOSE. Replace with: learned composition that conditions on the prompt's specific imagery. |
| P3 philosophy | Routing | Same as P2 (100% hand-coded) | Same as P2 — retrieves Plato adjacent to "philosophy" rather than arguing the actual question. |
| P4 humour | Nothing | n/a (misrouted to math) | No humour substrate; persona is hand-coded tone-flat. Replace with: learned humour from training data + audit signal. |
| P5 chat | Nothing | n/a (misrouted to poetry) | No chat substrate at all; permeable archetype TAU accepts wrong domains rather than refusing. |

Aggregate: of the 5 prompts, **1 produced a substantively-correct answer (P1, by hand-coded substrate), 2 produced topically-relevant-but-non-generative retrieval (P2, P3), 2 produced wrong-domain confident walks (P4, P5).** None of the substantive correctness in any prompt came from learned capability. The strict-thesis fraction "learned / hand-coded" is essentially **0%** today.

### F7 — Latency suggests warm-cache K-rollout retrieval is cheap; the cost is the cold encoder load

P1 11.8 s (first call → cold archetype-encoder + lazy corpus ingestion path). P2-P5 0.13-0.73 s each (warm cache). The cold-path cost is the encoder's char-n-gram-hash → projection-matrix transient (cycle-13 #07c shipped `encode_packed` but the read-path latency profile suggests the lazy archetype-encode is the dominant cost, not retrieval). Cycle-14 work that touches HDC at scale should batch the encoder transient (already queued per the cycle-14 corpse — surfaces here as a deferred optimisation, not a blocker).

## 5. Counter-claims (M-PROJECTX-013 measure-don't-claim)

1. **The demo did NOT produce composed answers on P2/P3.** It produced retrieval. A reader looking for "five lines about a river that forgets the sea" gets 5 fragments mostly about Whitman's "give me" anaphora and Shakespeare's marigolds. Honest framing: retrieval over a 22k-fragment substrate, NOT generation.
2. **The demo did NOT exhibit humour on P4 or chat-shape on P5.** Both prompts misrouted. The agent emitted Cantor + residue-theorem on a humour prompt and Shakespeare on a casual greeting.
3. **P1's "success" is not capability under the strict thesis.** The agent computed the correct roots by invoking BUILDER-authored algebra. The thesis asks whether the agent can LEARN to solve quadratics from worked-examples; today it cannot.
4. **Cycle-13 #07e fallback has a permeability problem.** The TAU floor (0.25) is empirically too low — almost any prompt reaches one of {math, philosophy, poetry, narrative_prose}; the natural-mode refuse path (which exists structurally) is unreachable for any prompt that has even moderate lexical overlap with corpus material. P4/P5 illustrate the consequence: confident walks at combined-confidence 0.83 on topically-wrong routes.
5. **5 prompts is too small to characterise capability.** The findings are dispositive on the gaps (formal math is hand-coded; retrieval is not generation; misroutes exist) but cannot estimate failure-rate. Cycle-14+ work on the emergence-validation predicate per-domain (council angle A5) would replace this artisanal demo with a falsifiable benchmark.

## 6. Hooks for the 5-angle council (scored against the STRICT thesis)

Council deliberates 5 angles; each angle is asked the question *"is this LEARNING MACHINERY (hand-code it, the strict thesis allows) or MODEL KNOWLEDGE the agent must learn?"* and *"does this angle close one of the gaps F1-F6?"*

| Finding | A1 Hebbian / HDC | A2 Evaluator-driven policy | A3 Credit assignment | A4 Layer-6 training data | A5 Per-domain emergence predicate |
|---|---|---|---|---|---|
| F1 hand-coded math | Indirect (substrate must shift to learn formula) | Indirect (policy picks which-formula but not formula itself) | Indirect (propagates rating to formula choice) | **Direct** (worked-examples corpus is the source) | **Direct** (predicate measures whether math was learned) |
| F3 retrieval ≠ composition | **Direct** (substrate updates compose-able representations) | Indirect (policy can pick "compose" over "retrieve") | **Direct** (rated answer's credit propagates to compose path) | Indirect (more data ≠ composition) | Indirect (predicate would measure composition fraction) |
| F4 P4 misroute | Indirect | **Direct** (audit-signal updates policy away from walk_math on humour) | **Direct** (rating propagates to dispatcher's choice) | Indirect | **Direct** (per-domain predicate would catch the misroute statistically) |
| F5 P5 chat gap | Indirect | **Direct** (policy can learn refuse-on-chat) | Indirect | **Direct** (conversational-shape data) | **Direct** (chat domain predicate) |
| F6 strict-thesis 0% learned | All five angles partially address; A2+A3 are the most direct strikes at "replace hand-coded routing with learned policy" | | | | |

**Per-angle observed-here load-bearing % (informal, pre-synthesis):**
- A1 Hebbian: ~25% (substrate-learning is necessary but composition needs more than co-occurrence updates).
- A2 Evaluator-driven policy: ~30% (most direct strike at the dispatcher-as-scaffold, addresses F4 + F5 + F1 routing layer).
- A3 Credit assignment: ~20% (pairs with A1+A2; without it the rating signal goes nowhere).
- A4 Layer-6 scale-out: ~15% (precondition not catalyst; data alone doesn't learn).
- A5 Per-domain emergence predicate: ~10% (measurement angle; valuable but doesn't directly strike).

These are **informal pre-council estimates**; the synthesis at #07 commits to a primary + bundled choice with honest counter-claims and an asymmetric-loading verdict mirroring the cycle-13 #06 precedent.

---

*Single-line takeaway: the post-cycle-13 agent routes more prompts correctly than any prior cycle but the STRICT-thesis gap remains essentially whole — capability is BUILDER-authored, not AGENT-learned, and the dispatcher itself is the most-load-bearing piece of scaffold left.*

---

## 8. Cycle-14 #08f verification — re-run on HebbianBank-active agent

**Run date:** 2026-05-11. **Commit:** appended post-cycle-14 #08a-d + #08g ship; bank consumer wired via #08b/c.
**Path:** `agent.process()` end-to-end (Arm A — cold-start, no bank file on disk); direct `KRolloutComposer.compose()` with synthetic-rating-populated bank (Arm B).

### 8.1 Arm A — cold-start regression (empty bank, α=0)

`data/hebbian_bank/main.pkl` does NOT exist → `HebbianBank.load(...)` returns an empty bank → `entry_count=0` → blend alpha=0 → `blend_score` collapses to identity. Re-run produces dispatcher metadata IDENTICAL to the cycle-14 demo's original (commit `d89b90f`):

| Prompt | Domain | Problem shape | Combined confidence | Register | Match |
|---|---|---|---|---|---|
| P1 math | maths | quadratic | 0.9683 | tutorial | ✓ exact |
| P2 poetry off-trigger | open_domain | natural_mode_walk_poetry | 0.8351 | terse | ✓ exact |
| P3 philosophy off-canon | open_domain | natural_mode_walk_philosophy | 0.8223 | casual | ✓ exact |
| P4 humour | open_domain | natural_mode_walk_math (misroute) | 0.8320 | terse | ✓ exact |
| P5 casual chat | open_domain | natural_mode_walk_poetry (misroute) | 0.8336 | casual | ✓ exact |

**Cold-start contract verified.** The cycle-14 strict-thesis ship preserves cycle-13/cycle-14-demo behavior exactly when the bank is empty. The substrate's writability is shipped WITHOUT regressing the read path.

### 8.2 Arm B — synthetic-rating injection (P4/P5 misroute rejections)

Constructed an empty bank, injected 5 `reject` ratings (rating=1.0 → delta=-0.2 per fragment) on each P4 + P5 misroute fragment from §3 (Cantor / diagonal-argument / prime-number-theorem / Stokes / residue-theorem for P4; Shakespeare sonnet / Whitman thought-of-justice / Whitman day-most-splendid / Yeats Innisfree / Whitman charity-and-personal-force for P5). Padded with 120 synthetic filler (filler-prompt, filler-fragment) approves to drive entry_count to 130 and saturate α at 1.0.

State after injection:
- `bank.entry_count() = 130 → α = min(1.0, 130/100) = 1.0`
- `bank.lookup(P4-prompt, "Cantor's diagonal argument: …") = -1.0` (5 × -0.2)
- `bank.lookup(P5-prompt, "Shall I compare thee to a summer's day?") = 0.0` (Shakespeare sonnet 18 was NOT in the rejected set — different from P5's actual misroute "For I am shamed by that which I bring forth")

Re-running `KRolloutComposer.compose(domain="all")` on P4 + P5:

| Prompt | Cycle-14 demo top fragment | Arm B top fragment | Shift? |
|---|---|---|---|
| P4 | *"Aleph-null is the cardinality of the natural numbers …"* (Cantor; rejected) | *"Shall I compare thee to a summer's day? …"* (Shakespeare sonnet 18; unrated) | ✓ moved AWAY from rejected misroute |
| P5 | *"For I am shamed by that which I bring forth …"* (Shakespeare; rejected) | *"Shall I compare thee to a summer's day? …"* (Shakespeare sonnet 18; unrated) | ✓ moved AWAY from rejected misroute |

**The bank mechanism shifts retrieval as designed.** Rejected fragments drop to `lookup = -1.0`; at α=1.0 the blended score on those pairs = -1.0 dominates; retrieval ranks them below any unrated pair (lookup = 0.0). Unrated fragments win the ranking. The strategy collapses to `bind` because all rated (rejected) fragments fall to the negative tail.

### 8.3 Honest reading of Arm B

The shift is real but doesn't mean the agent *learned humour* or *learned chat*. It means the bank successfully drove the previously-confident misroute fragments DOWN. The new top fragments are still off-topic (Shakespeare sonnet 18 is not a humour-prompt answer); but the corpus has no humour material to retrieve, and no chat material — the F4/F5 misroutes are DATA gaps (corpus coverage), not just routing gaps. The bank fixes the routing-side half (rejected pairs measurably drop in ranking). The DATA-side half waits on cycle-15+ A4 corpus scale-out.

**What Arm B verifies:**
1. Reward signal propagates from `audit_log.apply_rating` through to the substrate-wide bank.
2. `blend_score` correctly weights bank lookup vs static cosine as α grows.
3. Negative ratings drive (prompt_atom, fragment_atom) pairs to negative scores → they drop in retrieval ranking.
4. The substrate's behavior shifts cycle-over-cycle with audit signal, without ANY hand-coded per-tool routing changes.

**What Arm B does NOT verify:**
1. Right-routing on humour / chat prompts (corpus lacks the target material).
2. Per-domain calibration of α growth schedule.
3. Real audit-cadence behavior (synthetic-injection vs lain's actual rating rate).
4. Cycle-13 framing-walk preservation under high audit volume (cycle-15+ verification once both sides accumulate signal).

### 8.4 Cycle-14 ship verdict

- **Cold-start regression:** PRESERVED (Arm A: 5/5 prompts produce identical dispatcher metadata).
- **Reward-signal propagation:** VERIFIED (Arm B: rejected pairs measurably shift retrieval ranking).
- **Strict-thesis fraction at the substrate layer:** SHIPPED — the substrate is now writable from rated experience. Capability lift waits on audit cadence.

Cycle-14's strict-thesis-fraction shifts at the routing layer + substrate-write-path; cycles 15+ accumulate the audit signal that turns *capacity-to-learn* into *measured-learning*.

