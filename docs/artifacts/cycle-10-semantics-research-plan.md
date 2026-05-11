# Cycle 10 — Semantics Architecture Research Plan (deep-research phase, NOT YET CANONICAL)

**Lain directive 2026-05-11** (Discord msg `1503217035532828763`):

> *"You should use council with many experts, and deep research, before finalizing how to do the concept understanding, text generation, semantics, having opinions, non hardcoded solutions that will organically and naturally (as survival of fittest prune bad states until entropy is defied, continuing to leave offspring, which continue to evolve to optimize itself through mutation in a harsh environment, and the environment shapes what mutations are favourable.) Humans also have an image curiosity, to WANT to understand the environment better, which is an instinct to keep ones kind to continue. Therefore we have natural curiosity, we coordinate with others of same kind, on scale, and simulate scenarios, all to further our existence. Maybe some hints of how to achieve our project x structural goals lie somewhere here. But idk."*

**The catch:** the v1→v2→v3→consolidated arc shipped earlier today moved too fast. Each revision incorporated one lain critique reactively, but no DEEP RESEARCH phase happened — no multi-expert consultation, no structured exploration of the inspiration sources, no synthesis across perspectives. The consolidated doc reflects current best-thinking but is NOT canonical until the deep-research phase lands.

This research plan re-scopes the work: the existing `cycle-10-semantics-architecture.md` is DRAFT-PRELIMINARY. No cycle-11 implementation begins until the synthesis from the four research angles below produces a true canonical doc.

---

## Four research angles (lain-planted inspiration sources, ordered by concreteness)

### Angle 1 — Brain inspiration (foundational; already in DRAFT)

**Lain quote:** *"think of the human brain as inspiration for how we can make it understand semantics... It has sections to process different compartments of organs and senses, some long and big connections, some small and quiet. Also hormones are like global channels."*

**Status:** PARTIALLY incorporated. Multi-region HDC subspaces + hormone-modulation are in the DRAFT. Opinions-as-bindings (limbic-cortical anatomy) is in the DRAFT. But the brain has many more relevant subsystems we haven't modeled — working memory (prefrontal scratchpad), basal ganglia (action selection + habit formation), cerebellum (predictive modeling), hippocampus (episodic memory + replay-based consolidation). Each is a potential architectural piece.

**Research question for advisor consult:** which subsystems beyond cortex + limbic should the HDC architecture model? Specifically: is there a meaningful HDC analogue of hippocampal replay-based consolidation (rehearsing recent memories to consolidate them into long-term storage)? Of basal-ganglia action-selection (gating among competing primitives)? Of cerebellar prediction-error-based learning?

### Angle 2 — Evolutionary mechanisms (NEW; lain's latest critique)

**Lain quote:** *"as survival of fittest prune bad states until entropy is defied, continuing to leave offspring, which continue to evolve to optimize itself through mutation in a harsh environment, and the environment shapes what mutations are favourable."*

**Status:** NOT YET in DRAFT.

**Architectural questions to engage:**

- **Are HDC bindings units of selection?** Bindings with high audit-approval rates persist; bindings rejected by manual audit decay below a threshold and are pruned. The audit-loop IS the environment that shapes "fitness."
- **Mutation mechanism for HDC vectors.** Small perturbations of stored vectors (~1% bit-flip rate for binary-packed; or noise injection for float). Most perturbations degrade retrieval; rare ones produce serendipitous-better fits. Periodic mutation pass over the semantic subspace.
- **"Offspring" in a single-user agent.** Population-of-agents is not the natural shape for a personal Raphael. But: counterfactual binding offspring = produce K variant bindings on the same concept; let lain audit which variant performs best; the survivors propagate.
- **Environment-shaped mutation favorability.** Audit signals (lain's 👍/👎/corrections) ARE the environmental pressure. Mutations that produce 👍-approved outputs reinforce; mutations producing 👎 outputs prune.
- **Entropy defiance.** The system's resistance to confabulation as the "entropy" being fought. Audit-validated bindings carry low entropy; un-audited bindings carry high entropy and are candidates for retirement.

**Research question for advisor consult:** does evolutionary-algorithms thinking add a load-bearing mechanism to the HDC architecture, or is it metaphorical decoration? Specifically: would binding-mutation + audit-selection meaningfully improve retrieval quality vs static-binding + audit-weight-adjustment? Are there empirical analogues from the EA literature (genetic programming, neuroevolution, evolutionary strategies) that translate cleanly to HDC?

### Angle 3 — Intrinsic curiosity / instinct (NEW)

**Lain quote:** *"Humans also have an image curiosity, to WANT to understand the environment better, which is an instinct to keep ones kind to continue. Therefore we have natural curiosity..."*

**Status:** NOT YET in DRAFT.

**Architectural questions to engage:**

- **Active sampling vs passive ingestion.** Current DRAFT assumes corpus is ingested in batch. Curiosity-driven shifts this to active: the agent identifies CONCEPTS WITH HIGH UNCERTAINTY (low retrieval confidence in semantic subspace) and actively requests new corpus content covering them.
- **Counterfactual query generation.** Agent generates queries that PROBE its own gaps ("what if I encoded X with a different valence?"). Self-supervised — no lain needed per query, but lain audits the generated queries periodically.
- **Curiosity reward signal.** RL literature (Pathak et al., Random Network Distillation) gives this rigor: intrinsic reward = prediction error of a randomly-initialized network on the current observation. HDC analogue: intrinsic reward = retrieval-confidence variance across competing similar bindings (high variance = "I don't know which is right" = curiosity-triggering).
- **The "instinct to keep ones kind continuing" framing.** For a single-user personal agent, this maps to: the agent has an architectural drive to remain USEFUL to lain over time. Audit signals shape what useful means; the agent's curiosity is biased toward concepts lain has shown interest in.

**Research question for advisor consult:** does intrinsic-motivation literature (Pathak, RND, curiosity-driven exploration) give a concrete HDC analogue we can implement? Specifically: would active-curiosity-driven corpus sampling produce measurably better retrieval coverage than batch ingestion + audit? Is there a danger of curiosity-driven distraction (agent fixates on novelty at the expense of competence)?

### Angle 4 — Multi-agent coordination + scenario simulation (NEW)

**Lain quote:** *"we coordinate with others of same kind, on scale, and simulate scenarios, all to further our existence."*

**Status:** NOT YET in DRAFT.

**Architectural questions to engage:**

- **Multi-instance Raphael.** Do multiple agent instances exist and communicate? For a personal agent this seems off — there's one lain, one Raphael. But: agent instances at different time-scales could coordinate. Fast-Raphael (sub-second response, working memory) + slow-Raphael (overnight consolidation, episodic replay) might cooperate via shared HDC store.
- **Internal sub-agent architecture.** Specialized regions (cortex / limbic / hippocampus / basal-ganglia from brain inspiration) implemented as sub-agents that coordinate via the shared HDC space. Each sub-agent owns specific operations; they pass intermediate results through the shared substrate. This is closer to the brain's actual organization than monolithic-agent.
- **Scenario simulation (mental rollout).** Before producing an output, the agent generates K candidate completions internally, scores each against the audit-loop-learned criteria, emits only the highest-scoring. Counterfactual binding-trajectory generation. Analogue: MCTS-style rollouts but in HDC space, not over discrete tokens.
- **"Furthering existence" reframe.** For a personal agent: simulation is how the agent avoids costly mistakes. Before emitting a contentious opinion, simulate lain's audit response; if predicted-rejection-probability is high, refine the binding choice or honestly refuse.

**Research question for advisor consult:** is multi-instance / multi-sub-agent architecture worth the complexity overhead for a single-user agent? Specifically: does scenario simulation (mental rollout) measurably improve output quality, or is it equivalent to just running the agent with more diverse hormone vectors? What's the simplest viable simulation mechanism in HDC space?

---

## Research methodology

Per lain's "council with many experts + deep research" directive, each angle gets:

1. **Targeted advisor consult** (the "council with many experts" piece — different framings give different expert perspectives even from one model). Each consult uses the research question above + the context of the existing DRAFT architecture.
2. **Brief external-literature scan** (the "deep research" piece). For evolutionary: GP / NEAT / ES papers. For curiosity: Pathak 2017, RND, Burda+Edwards. For multi-agent: MARL literature, hierarchical RL, sub-agent architectures. For brain-subsystems: textbook references on hippocampus/basal-ganglia/cerebellum.
3. **Synthesis into a per-angle research note** in `docs/artifacts/` (small, ~50-100 line doc per angle).

After all four angles are researched + noted:

4. **Final synthesis** that produces the CANONICAL `cycle-10-semantics-architecture.md` (overwriting the current DRAFT). Decision points from each angle are integrated; architectural choices are made deliberately rather than reactively.

---

## Sequencing

This research can be done in parallel or serial. Serial is cheaper context-wise and respects "deep" over "broad":

- **Step 1 — Evolutionary angle.** Most concrete lead from lain's latest message; advisor consult + brief literature note. ~30 min Raphael-time.
- **Step 2 — Curiosity angle.** Next-most-concrete; advisor consult + brief note. ~30 min.
- **Step 3 — Multi-agent + simulation angle.** Advisor consult + brief note. ~30 min.
- **Step 4 — Brain-subsystems-beyond-cortex angle.** Advisor consult + brief note. ~30 min.
- **Step 5 — Synthesis pass.** Produce canonical doc replacing DRAFT. ~60 min.

Total deep-research phase: ~3h Raphael-time across multiple sessions. The phase explicitly precedes cycle-11 implementation, which itself was estimated at ~15-20h. So overall cycle-11 trajectory: ~3h research + ~15-20h implementation = ~20-23h, longer than v3's estimate but with much higher architectural confidence.

---

## What this means for the current DRAFT (`cycle-10-semantics-architecture.md`)

- **Status changed:** the file's current content is DRAFT-PRELIMINARY, not canonical. The 5 decision points it lists are tentative.
- **No cycle-11 implementation work begins** until the deep-research phase completes and the canonical doc replaces the DRAFT.
- **The DRAFT remains useful as the starting-point** for the synthesis pass; its multi-region + hormone + corpus + manual-audit + dual-mode + primitive-emergence pieces are likely to survive the synthesis intact, but each piece will be RE-EXAMINED through the four research lenses.

---

## "Use council" disposition (updated)

- **v1 advisor call** (the 5-candidate scaffold) — fired.
- **v2 advisor pre-write critique** — fired; surfaced the three load-bearing decisions.
- **v3 advisor call** — explicitly skipped per advisor's own "write directly" alternative.
- **Council-with-many-experts** (lain's latest directive): four targeted advisor consults across the four research angles. To be fired sequentially in subsequent turns. Each consult uses a different framing to extract a different expert perspective from the same underlying model.

---

## Sources

- Lain Discord critique 2026-05-11 (msg `1503217035532828763`).
- Existing DRAFT: `docs/artifacts/cycle-10-semantics-architecture.md` (commit `9b9aa7e`).
- HDC infra roadmap: `docs/artifacts/cycle-10-hdc-infrastructure-optimization.md` (commit `acca853`).
- Literature stubs for each angle, to be expanded as the research notes ship:
  - Evolutionary: Holland *Adaptation in Natural and Artificial Systems* (1992); Stanley *NeuroEvolution of Augmenting Topologies* (2002); Salimans et al. *Evolution Strategies as a Scalable Alternative* (2017).
  - Curiosity: Pathak et al. *Curiosity-driven Exploration by Self-supervised Prediction* (ICML 2017); Burda et al. *Exploration by Random Network Distillation* (ICLR 2019).
  - Multi-agent / hierarchical: Sutton et al. *Between MDPs and semi-MDPs* (options framework, 1999); Vezhnevets et al. *FeUdal Networks for Hierarchical RL* (ICML 2017).
  - Brain subsystems: Kandel *Principles of Neural Science* (textbook reference); for hippocampal replay: Buzsaki *The Brain from Inside Out* (2019).

— Ready for lain's read on the research-plan structure + greenlight to fire the four angles sequentially. The previous-turn consolidated doc remains DRAFT until synthesis.
