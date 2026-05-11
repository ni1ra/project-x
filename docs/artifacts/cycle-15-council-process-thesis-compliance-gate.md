# Cycle 15 council process improvement — per-angle thesis-compliance gate

**Status:** cycle-15 process artifact (#00P13c15-05 / B4 council surface). Fires PER-ANGLE during the cycle-15 council BEFORE each angle commit. The cycle-14 council surfaced this as architectural tension #6 (commit `5dd4b64` reflect doc); cycle-15 ships the gate so the council itself uses it.

**Why this exists:** in cycle 14, the strict thesis was at the TOP of every angle doc. A2's "per-primitive learned embeddings + argmax scorer" and A3's "per-decision-coefficient credit propagation" still passed 5 angle commits + advisor pre-write + synthesis verdict's first draft before lain caught them out-of-band. The catch was correct; the question is **what about the council/synthesis discipline let hand-coded structure through despite the binding being in scope?**

The cycle-14 deliberation surface used *"is this LEARNING MACHINERY?"* as the test. That phrase is permissive enough to admit hand-coded scorer architectures with learned weights. The fix is per-angle gating with explicit *"would lain call this hardcoding?"* sanity-check — fired BEFORE the angle commits, NOT at synthesis. By synthesis time, 5 angles are already on disk and pivot cost is high.

---

## The gate (mechanical checklist — fires PER-ANGLE during cycle-15+ council)

Each cycle-15+ council angle proposal MUST pass all four tests below before the angle's atomic commit lands. The proposal's author writes the gate result inline at the end of the angle doc (or in the commit message body). Failing any test → revise or drop the proposal.

### Test 1 — "Would lain call this hardcoding?" (sanity check)

Read the proposal's core mechanism. Would lain, reading it cold, characterize the mechanism as *"hand-picking what tools to use"* / *"hard-coding the math algos"* / *"telling the agent which tools to use"* — the verbatim phrasings he used at the cycle-14 mid-synthesis catch?

**Examples that FAIL Test 1 (from cycle-14):**

- **A2 evaluator-driven policy as proposed.** Per-primitive learned embeddings `θ_i` + argmax scorer + per-tool reward-distribution coefficients. lain would say: *"you're still telling it which tools to use, just with learned weights on a hand-picked structure."*
- **A3 structured credit propagation as proposed.** `StrategyPolicy` with `weight_bind` / `weight_bundle` / `weight_greedy` scalars + per-decision-coefficient credit-distribution rule. lain would say: *"you're still hand-coding the credit assignment rule."*

**Examples that PASS Test 1 (from cycle-14):**

- **A1 substrate-wide Hebbian.** Bank keyed by `(prompt_atom, fragment_atom)` pairs; update rule applies the same delta formula regardless of which primitive matched. The bank doesn't know the difference between a math walk and a poetry walk; it only knows which atom-pairs were rewarded together.

### Test 2 — Does the proposal's hand-coded structure pass the LEARNING-MACHINERY-ONLY filter?

The strict-strict thesis allows hand-coding for exactly four categories. Anything outside these is hand-coded knowledge in disguise:

1. **The encoder** (substrate input). Char-n-gram-hash → projection. Pure substrate arithmetic.
2. **The HDC operators** (substrate algebra). `bind`, `bundle`, `cosine`, `pack`, `unpack`. Numeric operators, not knowledge.
3. **The substrate-wide learning rule.** A formula that applies the same way to any atom-pair, regardless of domain or tool-id. Hebbian co-occurrence is the cycle-14 example.
4. **The reward-signal I/O plumbing.** Reading from `audit/ratings.jsonl`, writing to the substrate's bank. No scoring logic; pure plumbing.

If a proposal's hand-coded structure falls outside (1)-(4), it FAILS Test 2.

**Examples that FAIL Test 2 (from cycle-14):**

- A2's per-primitive embeddings — outside (1)-(4); they're per-tool structure with learned weights.
- A2's argmax scorer — outside (1)-(4); the scorer architecture itself is hand-coded.
- A3's per-strategy weight scalars — outside (1)-(4); per-strategy partition is hand-coded structure.
- A3's per-decision credit-distribution coefficients — outside (1)-(4); the credit-distribution rule is hand-coded.

**Examples that PASS Test 2 (from cycle-14):**

- A1's HebbianBank dict — storage is allowed (it's substrate-wide state). Update formula is allowed (category 3 — substrate-wide learning rule). The bank's CONTENT is learned from experience.

### Test 3 — Is the atom-shape of any new bank/memory substrate-wide, NOT per-tool partitioned?

If the proposal introduces new substrate state, look at the storage shape. The keys should be substrate-wide (any prompt-shape × any fragment-shape pair), NOT partitioned by primitive-id / domain-tag / strategy-id / role.

**Anti-pattern (FAIL Test 3):**

- `embeddings: dict[primitive_id, hypervector]` — per-tool partition. Hand-coded shape.
- `strategy_weights: dict[strategy_name, float]` — per-strategy partition. Hand-coded shape.
- `domain_thetas: dict[domain, hypervector]` — per-domain partition. Hand-coded shape.

**Pass shape:**

- `bank: dict[(prompt_atom, fragment_atom), float]` — substrate-wide. The bank doesn't know about tools, strategies, or domains. Atoms are derived uniformly across all prompt-shapes + fragment-shapes.

### Test 4 — Does the gate fire PER-ANGLE BEFORE the angle commits, NOT at synthesis?

This is the load-bearing process test. Synthesis fires AFTER 5 angle commits are on disk; pivot cost there is high (cycle-14 had to rewrite the entire synthesis verdict mid-flight). PER-ANGLE gating catches the failure at the earliest point.

**Mechanical contract:**

- Each angle author writes the four-test result inline at the END of the angle doc (a new §"Thesis-compliance gate" section), OR in the commit message body.
- Format: *"Test 1: PASS — [1-sentence why]. Test 2: PASS — [LEARNING-MACHINERY category cited]. Test 3: PASS — [storage shape described]. Test 4: PASS — gate fired before commit."*
- If any test FAILS: the angle is revised or dropped BEFORE commit. The author cites the failure mode + the alternative proposal that would pass.
- Synthesis pass then knows all 5 angles already passed the gate; no surprise hand-coded structure surfaces at synthesis.

---

## How the gate would have caught cycle-14's failure (concrete retrospective)

If this gate had existed at cycle 14:

**Angle A2 (cycle-14 #03) would have failed Test 1 + Test 2 + Test 3:**

- Test 1: lain would have called the per-primitive embeddings + argmax scorer "hand-picking what tools to use, just with learned weights." FAIL.
- Test 2: per-primitive embeddings fall outside categories (1)-(4). FAIL.
- Test 3: storage shape is `dict[primitive_id, embedding]` — per-tool partition. FAIL.

Result: A2's commit `d40572d` would not have landed in its current form. The author would have revised the proposal to substrate-wide structure (e.g., a learned reward predictor over the existing `(prompt_atom, fragment_atom)` bank, NOT new per-primitive state), or dropped A2 entirely.

**Angle A3 (cycle-14 #04) would have failed Test 2 + Test 3:**

- Test 2: per-strategy weight scalars + per-decision credit-distribution coefficients fall outside categories (1)-(4). FAIL.
- Test 3: storage shape includes `dict[strategy_name, float]` — per-strategy partition. FAIL.

Result: A3's commit `b691961` would not have landed in its current form. The author would have revised the credit propagation to act on the existing substrate-wide bank directly (the bank already accumulates per-fragment credit; per-strategy and per-decision coefficients were the redundant + hand-coded layer).

The synthesis verdict at #07 would then have inherited 3 thesis-compliance-passing angles (A1, A4, A5) + 2 revised or dropped (A2, A3) — instead of the actual cycle-14 sequence where lain caught the failure mid-synthesis and the synthesis pivoted in flight.

---

## Application to cycle-15 council surfaces B1-B5

This gate fires at each cycle-15 council angle commit:

| Cycle-15 surface | Pre-gate prediction |
|---|---|
| B1 per-domain τ_satisfaction + BG-dispatcher refused-candidate filter | **Likely PASS.** Per-domain τ values are scalars, not per-tool structure (they're calibration constants, like learning_rate). The refused-candidate filter is plumbing (category 4) — a missing-archetype-default-1.0 check that doesn't add knowledge. **Caveat:** per-domain τ is borderline — if "domain" means "math vs poetry," it's hand-coded partition; if "domain" means "what the cosine-archetype classifier outputs at runtime," it's emergent. Cycle-15 council should be explicit. |
| B2 A4 corpus scale-out | **PASS.** Adding training data is the data side of "good enough training data + smart enough model." Corpus is INPUT to the substrate, not structure inside it. Category 1 (encoder substrate) consumes corpus uniformly. |
| B3 A5 per-domain emergence predicate templates | **PASS.** Predicates are SCORING machinery (category 4 plumbing — measurement, not knowledge), pre-registered before runs, falsifiability scaffolding. They don't add hand-coded structure to the agent's behavior; they measure whether learning happened. Per-domain partition is OK because it's measurement-side, not agent-side. |
| B4 thesis-compliance gate | **PASS.** This is the gate itself; meta-process artifact; doesn't touch the substrate. |
| B5 cycle-13 audit C-reframes | **PASS.** Doc-only work; canonical-doc wording corrections. No substrate changes. |

The cycle-15 council deliberates priority among these, with the gate fired at each commit.

---

## Counter-claims (M-PROJECTX-013 measure-don't-claim)

1. **The gate is itself hand-coded process scaffolding.** The four tests are author-written. Future cycles may critique this as "you authored the rules for what counts as authored." The response: the gate is METADATA, not knowledge. It's a verification artifact for the meta-question "is this proposal compatible with the strict-strict thesis," not a substrate component. The thesis allows hand-coded process discipline; what it rejects is hand-coded agent knowledge.
2. **The "would lain call this hardcoding?" test is subjective.** Different angle authors may interpret it differently. The mitigation: the test is paired with Test 2's mechanical filter (4 allowed categories) which is objective. Test 1 is the qualitative pre-screen; Test 2 is the mechanical check.
3. **The gate fires per-angle, but lain's catch was at synthesis.** True; the gate's per-angle-firing is the proposed improvement over cycle-14's de-facto "synthesis time" gating. It hasn't been validated empirically. Cycle-15 council is the first empirical test of whether per-angle gating catches more failures earlier.
4. **The 4 allowed categories may be too restrictive.** If a cycle-15+ proposal needs hand-coded structure outside (1)-(4) that IS strict-thesis-compatible, the gate would block it incorrectly. Mitigation: the gate is a guideline, not absolute. If an author argues their proposal falls outside (1)-(4) but is still strict-strict-compatible, the synthesis pass adjudicates. The gate's job is to surface the dispute pre-commit, not to make the final call.
5. **The retrospective application to A2/A3 is post-hoc.** It's easy to say the gate would have caught A2/A3 because lain already caught them; the real test is whether the gate catches a cycle-15 failure the author + advisor would have missed. Cycle-15 is the test bed.

---

*Single-line takeaway: per-angle thesis-compliance gate fires at each council angle commit; four tests (qualitative "would lain call this hardcoding," mechanical "LEARNING-MACHINERY-ONLY filter," structural "substrate-wide atom shape," procedural "fires before commit not at synthesis"). Cycle-15 council uses this gate; cycle-14 retrospective shows it would have caught A2 + A3 at angle-commit time instead of synthesis time.*
