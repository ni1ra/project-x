# Cycle 14 — Priority Decision (synthesis verdict)

**Status:** synthesis verdict over the 5 cycle-14 council angles, after the strict-strict-thesis course-correction from lain (2026-05-11 mid-synthesis). Feeds the cycle-14 #08 implementation contract.
**Date:** 2026-05-11.
**Pairs with:** the demo (`cycle-14-demo-post-thesis.md`, commit `d89b90f`), the 5 angle notes (commits `a0babad` / `d40572d` / `b691961` / `743128b` / `8ccac83`), and the cycle-14 dev reflect.
**Advisor pre-write:** 1 pre-write round (cost-math BLOCKER + A1-defers-framing + τ_satisfaction debt — all integrated). **Mid-synthesis course-correction from lain on Discord (msg 1503460740 + 1503460741 + the three follow-ups):** *"there shouldnt be a need for us to hand pick anything. it should naturally emerge as the best solution, model on its own. if you stimulate the right rewards you will get emergent behaviour. you really keep trying to hardcode everything."*

---

## §0 — The course-correction (load-bearing for everything below)

The pre-correction draft of this synthesis picked A2 (learned routing policy) + A3 (structured credit propagation) bundled at ~55-60% combined load-bearing. Lain caught that the A2 proposal was **still hardcoding**: per-primitive learned embeddings (hand-picked shape), argmax scorer (hand-picked rule), per-tool weighting (hand-picked structure). The "LEARNING MACHINERY allowed" clause was being stretched to permit hand-coded scorer architectures + curated tool lists.

The strict-strict thesis as lain named it on the synthesis call:

> *"it should naturally emerge as the best solution, model on its own."*
> *"if you stimulate the right rewards you will get emergent behaviour."*

**What this means concretely for cycle-14 scope:** the only hand-coded structure between reward signal and agent behavior is the substrate's *arithmetic* (HDC operators: bind, bundle, cosine) + the encoder (char-n-gram hash → projection) + the *substrate-wide* learning rule (Hebbian co-occurrence) + the I/O plumbing for the reward signal (read from `audit/ratings.jsonl`, write into the substrate's co-occurrence bank). Tool-use, routing, composition strategy, scorer architectures, per-primitive embeddings — all of it must EMERGE from reward shaping over the substrate. None of it gets pre-authored as scaffolding-with-learned-weights.

Two readings of how cycle-14 ships this:

- **Reading 1 (R1):** rip out the hand-coded dispatcher entirely this cycle. Cold-start agent has no built-in primitives; reward signal shapes substrate retrieval from scratch. ~15-20h work; ~600 of 639 tests break and need restructuring. Highest fidelity; longest valley.
- **Reading 2 (R2):** ship the substrate-wide reward consumer this cycle; hand-coded dispatcher persists as cold-start scaffolding because the substrate hasn't learned anything yet; subsequent cycles progressively retire the scaffolding as reward-shaped retrievals start outperforming hand-picked routes. ~4-5h work.

This synthesis commits to **R2 as the cycle-14-shippable interpretation** (lain pending confirmation; revise to R1 if lain redirects). R2 mirrors the cycle-13 "ship substrate then retire scaffolding" cadence and respects the strict-strict thesis as an end-state without the long cold-start valley.

## §1 — The verdict

**Cycle-14 #1 = A1 (substrate-wide reward-driven Hebbian update + retrieval blending) as the SINGULAR cycle-14 ship.**

A2 + A3 dropped entirely from cycle-14 (and from cycle-15 unless re-thought) — both proposals embedded hand-coded scorer/strategy structure that the strict-strict thesis rejects. The original A2 + A3 angle notes remain on disk as the deliberation record, but their proposals are NOT the cycle-14 scope and the A2 + A3 angle-note recommendations are SUPERSEDED by §0 above.

A4 + A5 defer to cycle-15 — same reasoning as the pre-correction draft (budget + sequencing).

## §2 — The 5-angle load-bearing % table (revised post-correction)

| Angle | Pre-correction reading | Post-correction reading | Cycle-14 verdict |
|---|---|---|---|
| **A1 substrate-wide Hebbian** | ~25% (mid-pack on capability, ~30% on strict-thesis fraction) | **~55%+ — sole strict-strict-compatible cycle-14 ship** | **PICKED as cycle-14 #1** |
| A2 learned routing policy | ~35% (highest) | **~0% — proposal is hand-coded scorer architecture** | DROPPED |
| A3 structured credit propagation | ~25% bundled | **~0% — StrategyPolicy + per-decision-coefficients is hand-coded structure** | DROPPED |
| A4 corpus scale-out | ~15-20% | ~15-20% unchanged (data side) | DEFERRED to cycle-15 |
| A5 per-domain predicates | ~10-15% bundled | ~10-15% unchanged (measurement layer) | DEFERRED to cycle-15 |

**A1 alone = ~55%+ load-bearing on cycle-14 evidence** — not because A1 grew, but because A2 + A3 fell out. A1's original "substrate-wide Hebbian over (prompt-atom, fragment-atom) co-occurrence" framing is already strict-strict-compatible: the bank is keyed by atom-pairs, NOT by primitive-id; the update rule applies substrate-wide, not per-tool; the only hand-coded structure is the Hebbian update formula + the read-write plumbing.

## §3 — Why A1 alone (post-correction)

A1's read-path through the strict-strict lens:

- **Encoder (hand-coded substrate input):** char-n-gram-hash → projection. Per the strict thesis MANIFESTO § Standing orders, the encoder is "the architecture, not the knowledge." Pure substrate arithmetic. ✓ allowed.
- **HDC operators (hand-coded substrate algebra):** `bind`, `bundle`, `cosine`, `pack_bipolar`, `cosine_packed`. Numeric operators, not knowledge. ✓ allowed.
- **HebbianBank (hand-coded LEARNING RULE):** the *update formula* is hand-coded; the *content* of the bank (which atom-pairs co-occur, with what reward-weighted strength) is learned from experience. ✓ allowed.
- **Reward signal pipeline:** `audit/ratings.jsonl` → `HebbianBank.update(walk_metadata, rating)`. Hand-coded I/O plumbing, no scorer architecture. ✓ allowed.
- **Retrieval blend:** `final_score = (1−α) × static_cosine + α × bank_lookup(prompt_atom, fragment_atom)`. Substrate-wide formula; α grows as the bank populates. No per-primitive scorer; no per-tool weighting. ✓ allowed.

What A1 does NOT introduce:
- ✗ No per-primitive embeddings (that's A2's hand-coded structure — dropped).
- ✗ No argmax-over-tools scorer (that's A2 — dropped).
- ✗ No per-decision credit-distribution coefficients (that's A3 — dropped).
- ✗ No StrategyPolicy with weight_bind / weight_bundle / weight_greedy (that's A3 — dropped).
- ✗ No new hand-coded knowledge of any kind.

A1 is the *minimum viable strict-strict ship*: the substrate gets a write path from experience; nothing else.

## §4 — Cold-start scaffolding RETIREMENT — concrete + measurable, not vibe-based

The strict-strict thesis is the END-STATE. Cycle 14 is one cycle of a multi-cycle path. The cold-start substrate has accumulated 0 ratings; with 0 ratings the HebbianBank is empty, retrieval blending collapses to the static encoder (α=0), and the agent has no learned routing at all. Without SOME cold-start scaffolding, the cold-start agent has no capability for any prompt the substrate hasn't yet learned.

**But "cold-start scaffolding stays as fallback" without a retirement schedule IS the failure pattern lain just caught.** The pre-correction draft said *"cycle-15+ progressively retires it as substrate accumulates."* Future tense + vague threshold = the same hand-coded-stays trap. So §4 commits to BOTH halves of the retirement:

### §4.a — Cycle-14 pre-retires the keyword-trigger gate (proof-of-direction, NOW, not future)

`_NATURAL_MODE_TRIGGERS` is the keyword-regex gate at `corpus/natural_mode.py` that decides if a prompt is "natural-mode-shaped" before the BG-dispatcher confidence-scored chain even sees it. It's the most-keyword-shaped, most-hand-picked piece of scaffolding in the dispatcher. Cycle-13 #07e shipped the cosine-archetype fallback `_classify_natural_mode_domain` at `_TAU_NATURAL_DISPATCH=0.25` that fires when the keyword gate misses — meaning the cosine fallback already covers everything the keyword gate covered, plus the off-trigger prompts the cycle-13 demo and cycle-14 demo both flagged.

**Cycle-14 #08 disables `_NATURAL_MODE_TRIGGERS` entirely.** Natural-mode routing relies ON: (a) the cosine-archetype fallback + (b) the new HebbianBank's reward-shaped retrieval scores. One concrete piece of scaffolding goes away this cycle, not next cycle.

This is the proof-of-direction sub-task #08g: cycle-14 ships LESS hand-coded scaffolding at close than at open. The retirement schedule for the rest of the dispatcher (the 21-parser chain, the parser archetypes, the register archetypes) lives in §4.b.

### §4.b — Cycle-15+ retirement criterion (measurable, not "progressively")

A dispatcher entry (parser archetype, register archetype, individual parser in the chain) retires when one of three measurable conditions holds:

1. **Bank-coverage threshold:** the HebbianBank has accumulated ≥ N ratings whose retrieval-blend wins over the scaffolding entry's confidence-scored win on ≥ 80% of rated prompts in that entry's domain (where N is calibrated cycle-15 over the rated audit log; starting estimate N=50).
2. **Cosine-archetype absorption:** if a parser's archetype lives within `_PARSER_ARCHETYPES` and the cycle-13 #07e cosine-archetype fallback has the same archetype already cached, the parser's keyword-gated path is redundant — retire as in §4.a's #08g.
3. **Demo regression:** if the cycle-14 demo (or the per-domain predicate from cycle-15 A5) shows the retrieval-blend outperforms the scaffolding entry on the held-out test set, retire the entry.

These conditions are testable cycle-over-cycle. The cycle-15+ A5 work (deferred from cycle-14) ships the predicate scaffolding that scores conditions (1) and (3) automatically; until then, cycle-15 manually applies the criteria on whatever audit volume accumulates.

**R1 alternative:** rip the dispatcher entirely this cycle. Honest fidelity to strict-strict + a multi-week valley with no rateable output. Lain to confirm if this is the cycle-14 ask; default R2 with #08g pre-retirement unless he says R1.

## §5 — Permeability asterisk: cycle-14 ships a substrate that CAN learn, not an agent that has learned

Same honest framing as the pre-correction draft, unchanged by the strict-strict reframe:

A1 ships LEARNING MACHINERY. The machinery does not produce a measurably-smarter agent at cycle-14 close. Capability lift on the demo's misroute findings requires accumulated rating cadence (~20-50 ratings on misroute-shaped prompts) via the cycle-12 audit UI, consumed by the HebbianBank's reward-driven update. If lain rates 20+ walks in the cycle-14 window, A1 produces measurable retrieval shifts. If rating cadence is lower, cycle-14 ships a substrate that *can* learn but hasn't yet — and rateable evidence accumulates over cycles 15-N.

**Cycle-14 close framing: "substrate writability shipped + reward-signal-pipeline online + audit cadence pending."** NOT "the agent learned tool-use this cycle."

## §6 — Why A2, A3 drop, A4, A5 defer

- **A2 drops** because its proposal embedded hand-coded scorer architecture + per-primitive embeddings + argmax routing rule. The strict-strict thesis rejects these as "still telling the agent which tools to use, just with learned weights on a hand-picked structure." A2 in its current form is the failure mode lain caught on the synthesis call.
- **A3 drops** because its proposal embedded hand-coded credit-distribution coefficients + StrategyPolicy with per-strategy scalar weights. Same failure mode at a smaller scale. A3's "structured rating signal" framing IS the right intuition — but it can be achieved by Hebbian co-occurrence having strong-rating-weighted updates over the walk's atoms, without ANY per-decision-coefficient scaffolding.
- **A4 defers** because more corpus without consuming machinery is bytes on disk. Cycle-15 picks up A4 once the substrate's reward-driven update path (cycle-14's A1) has demonstrated retrieval shifts on rated prompts. The order is: machinery cycle-14 → data cycle-15 → more capacity cycle-16+.
- **A5 defers** because per-domain predicate templates are 6-8h alone and don't advance capability this cycle. The cycle-14 close DOES include a re-run of the cycle-14 demo as a verification artifact — that's the lightweight measurement-this-cycle path without the full predicate-templates ship.

## §7 — Cycle-14 #08 implementation contract (handoff to next task)

Per the simplified scope, the sub-task split is smaller than the pre-correction A2+A3 contract.

### Sub-task split (read by re-fired `Skill('skills:sharpen-todos')` at #07→#08 boundary)

| Sub-task | Scope | Files | Est. Raphael-time | Atomic commit message |
|---|---|---|---|---|
| #08a | HebbianBank class + substrate-wide co-occurrence storage | `src/project_x/hdc_infra/hebbian.py` (new) + `__init__.py` export | 1-1.5h | `feat(P13c14-08a-hebbian-bank): substrate-wide reward-driven co-occurrence bank` |
| #08b | Reward consumer wiring — `AuditLog.apply_rating` triggers `HebbianBank.update(walk_metadata, rating)` | `src/project_x/audit/log.py` modify (add post-rating hook) | 0.5h | `feat(P13c14-08b-audit-hebbian-wire): rating-write triggers HebbianBank update` |
| #08c | Retrieval blend in `NaturalModeComposer` / `KRolloutComposer` — `final = (1-α) * static_cos + α * bank_lookup` | `src/project_x/corpus/natural_mode.py` + `src/project_x/corpus/k_rollout.py` modify | 1h | `feat(P13c14-08c-retrieval-blend): blend static-encoder cosine with HebbianBank lookup` |
| #08d | HebbianBank tests + cycle-13 regression (empty-bank → α=0 → cycle-13 baseline preserved) | `tests/test_hebbian_bank.py` (new, ~200 lines, 12-18 tests) | 1h | `test(P13c14-08d-hebbian-tests): empty-bank regression + synthetic rating sweep` |
| #08e | τ_satisfaction calibration (cycle-13 audit B5 debt) — raise `_K_ROLLOUT_TAU` from 0.0 to ~0.3 + tests | `src/project_x/reasoning_agent.py:1231` modify | 0.5h | `feat(P13c14-08e-tau-satisfaction-calibration): raise refuse floor from 0.0` |
| #08f | Cycle-14 demo re-run with HebbianBank active — verification artifact (cold-start + synthetic-rating-injection arms) | `scripts/cycle_14_demo_post_thesis.py` re-run + append §8 to demo doc | 0.5h | `docs(P13c14-08f-demo-rerun): cycle-14 demo on Hebbian-active agent` |
| #08g | **Pre-retire `_NATURAL_MODE_TRIGGERS` keyword-regex gate** — disable entirely, rely on cycle-13 #07e cosine-archetype fallback + HebbianBank for natural-mode routing. Proof-of-direction: cycle-14 ships with LESS hand-coded scaffolding than cycle-14 opened with. | `src/project_x/corpus/natural_mode.py` (gate-removal) + `src/project_x/reasoning_agent.py` (caller flow) + cycle-13 test regression | 0.5-1h | `feat(P13c14-08g-retire-natural-mode-triggers): disable keyword-regex gate; cosine-archetype fallback + HebbianBank carry natural-mode routing` |

**Total: 5-6h Raphael-time across 7 atomic feat/test/docs commits.** Still smaller than the pre-correction A2+A3+τ contract (which was 6-7h across 8 commits). Includes the #08g pre-retirement that turns the "retire scaffolding cycle-15+" promise into a "retired one piece cycle-14" fact.

### Acceptance criteria for cycle-14 #08

- All 6 sub-tasks ship as atomic feat/test/docs commits with conventional messages + WHY in the body.
- pytest baseline 639/639 preserved on cold-start path (α=0 collapses retrieval blend to identity); new tests bring total to ~660+ passing.
- Cycle-13 bench-replay agent-runtime 48/0 preserved.
- REPO_CONTROL row co-landed for `hebbian.py`.
- `Skill('skills:consult-advisor')` invoked BEFORE declaring #08 done (M-PROJECTX-013 lock).
- Cycle-14 demo re-run (#08f) provides the verification artifact: cold-start preserves baseline; synthetic 20-rating audit log on humour/chat-shaped prompts → measurable retrieval shift demonstrating the substrate IS now reward-shaped.
- NO new hand-coded scorer architectures introduced. NO new hand-coded per-tool weights. NO new hand-coded routing logic. The Hebbian update formula is the only new hand-coded structure.

### Spillover policy

If #08c (retrieval blend) reveals deeper integration issues than expected (cycle-13 `_DISPATCH_CHAIN_ORDER`'s BG-style confidence calculation may conflict with the blend in non-obvious ways), ship #08a-b + #08d + #08e + #08f as cycle-14 close + push #08c retrieval-blend to cycle-15 as continuation. The HebbianBank ships independently of the retrieval-blend wire; both halves are valuable but the bank is the load-bearing piece.

## §8 — Honest counter-claims (M-PROJECTX-013 measure-don't-claim)

1. **R2 is a transition reading, not the end-state.** Cycle-14 keeps the hand-coded dispatcher as cold-start scaffolding. Lain may prefer R1 (rip the dispatcher this cycle); this synthesis defaults to R2 as cycle-shippable and awaits redirect.
2. **The "Hebbian alone IS strict-strict-compatible" claim depends on the substrate-wide formulation.** A1's original write-up's HebbianBank IS substrate-wide (keyed by atom-pairs, not primitive-id); if the implementation drifts toward per-primitive embeddings during cycle-14 #08 work, the strict-strict-fit erodes. The cycle-14 implementation must hold this discipline.
3. **Cycle-14 ships a substrate that CAN learn, not an agent that has learned.** The audit-volume floor remains — without ~20-50 ratings on misroute-shaped prompts, the bank stays empty and the agent behaves identically to cycle-13.
4. **Dropping A2 + A3 means cycle-14 ships less hand-coded structure than the pre-correction synthesis intended, AND less learned-routing-policy capability.** The trade-off is honest: lower scaffolding-mass + thinner cycle-14 capability advance + cleaner strict-strict-fit. Cycle-15+ progressively retires more of the cold-start dispatcher as the substrate accumulates retrievals.
5. **τ_satisfaction calibration at ~0.3 is empirical, not principled.** Cycle-14 #08e ships a coarse calibration; cycle-15+ work needs per-domain τ.
6. **The "% capability from learned retrieval / % capability from hand-coded dispatcher" measurement is missing in cycle-14.** Cycle-15 picks up A5 (per-domain predicates) to make this fraction falsifiable. Cycle-14 ships the machinery without the measurement; cycle-15 ships the measurement.
7. **The demo re-run in #08f is a weak verification.** It's cold-start + synthetic-rating-injection, not real audit-cadence evidence. Cycle-15+ runs the demo against the agent after real audit accumulation as the falsifiability test.
8. **α growth schedule + τ_satisfaction threshold are hand-tuned coefficients.** α=0 cold-start, growth rate-per-rating uncalibrated; τ_satisfaction=0.3 is a coarse first pass. These are substrate-arithmetic-tuning (parallel to learning-rate + decay in any learning system), not knowledge or strategy — defensible per the strict-strict reading. Cycle-15+ calibration sweep over the accumulating rated audit log will tune both per-domain.
9. **#08g retires ONE piece of scaffolding cycle-14; the rest waits on the §4.b retirement criterion.** Honest framing: cycle-14 doesn't gut the dispatcher; it pre-retires the most-keyword-shaped piece + commits to a measurable retirement schedule for the rest. Cycle-15 must apply the criterion to at least 2-3 more entries to keep direction credible.

## §9 — Single-paragraph verdict (for cycle-14 reflect citation)

Cycle 14 commits to **A1 (substrate-wide reward-driven Hebbian update + retrieval blending) as primary ship + pre-retirement of `_NATURAL_MODE_TRIGGERS` keyword-regex gate as proof-of-direction**, after lain's mid-synthesis course-correction caught that the pre-correction A2 + A3 verdict was still embedding hand-coded scorer architectures + per-tool weighted structure. A2 + A3 drop entirely from cycle-14 (and from cycle-15 in current form); A4 + A5 defer to cycle-15. The cycle-14 ship is the substrate's first write path from rated experience: HebbianBank reads `audit/ratings.jsonl`, updates substrate-wide atom-pair co-occurrence, and retrieval scores blend static-cosine with bank-lookup as α grows from 0 (cold-start) toward learned-weight as ratings accumulate. Crucially: cycle-14 retires ONE piece of dispatcher scaffolding (the keyword gate) THIS CYCLE, not "cycle-15+ progressively." Remaining scaffolding waits on §4.b's measurable retirement criterion. R1 (rip dispatcher entirely this cycle) is the strict-strict-end-state read; default R2 with #08g pre-retirement unless lain redirects. ~5-6h Raphael-time across 7 atomic sub-task commits. Cycle-14 close framing: substrate writability shipped + reward-signal pipeline online + ONE scaffolding piece retired + audit cadence pending.

---

*Single-line takeaway: A1 alone, substrate-wide Hebbian + reward consumer + retrieval blend, dispatcher as cold-start scaffolding under R2. Smaller ship, cleaner strict-strict-fit, gradual end-state path.*
