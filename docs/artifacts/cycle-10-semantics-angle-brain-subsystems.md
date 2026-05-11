# Cycle 10 Semantics Architecture — Angle 1 (Brain Subsystems Beyond Cortex)

**Status:** research note, not canonical. Feeds the #05e synthesis pass that overwrites the DRAFT.
**Date:** 2026-05-11. Last of the 4 sequential research angles before synthesis.

---

## 1. Lain quote (verbatim source anchor)

> *"think of the human brain as inspiration for how we can make it understand semantics... It has sections to process different compartments of organs and senses, some long and big connections, some small and quiet. Also hormones are like global channels."*

— Anchoring quote from the cycle-10 mid-cycle Discord exchange that drove DRAFT v2's brain-inspired subspace partition + hormone-modulation pieces (already in DRAFT).

The research-plan extension for this angle: which subsystems BEYOND cortex + limbic should the HDC architecture model? Specifically the hippocampus, basal ganglia, cerebellum, and prefrontal working-memory.

## 2. Advisor verdict (2-3 sentences)

This angle's role is NOT to invent new HDC primitives from neuroanatomy — that's what angles 2-4 already did from RL/EA/multi-agent literature. Instead, the brain-subsystems angle's main job is to **anchor mechanisms identified elsewhere in real neurobiology** and add 1-2 details those mechanisms missed because they came from machine-learning literature, not biological literature. The strongest single addition is **basal-ganglia-style confidence-scored parallel-bid dispatch** as the open-domain-semantics replacement for the current keyword-gated first-match-wins dispatcher; hippocampal replay's surprise-biased selection rule is the second-strongest.

Net call: **~30-40% load-bearing.** Middle weight — heavier than evolutionary (~20-25%) and multi-agent (~15-20%), lighter than curiosity (~60-70%). The asymmetric distribution across the four angles is now believable.

## 3. Literature integration — paper by paper / subsystem by subsystem

### Hippocampus — Wilson & McNaughton 1994 / Buzsaki 2019

- **Core mechanism (Wilson & McNaughton 1994, Science):** during slow-wave sleep, hippocampal place cells active during a recent waking experience reactivate in compressed sequences. Sharp-wave-ripple events drive this replay; it's not uniform across experiences — surprising / reward-modulated experiences are over-represented.
- **Additive detail for the consolidation merge:** the angle-2 ES-style perturb-audit-reweight pass + angle-3 K-rollout surprising-region tracking + angle-4 multi-temporal-Raphael all describe WHEN to consolidate (offline / overnight pass). Hippocampal replay adds the **SELECTION RULE for WHICH bindings**: bias toward surprising / high-prediction-error / high-audit-weight ones. The replay isn't uniform; consolidation shouldn't be either.
- **Bonus mechanism (cycle-12+):** forward AND reverse replay both occur. In HDC: chain executed in normal order during retrieval, in reverse order during consolidation. Reverse replay strengthens *terminal* steps disproportionately — useful for back-propagating audit-approval signals from end-of-chain to earlier steps.

### Basal ganglia — direct (Go) and indirect (NoGo) pathways + thalamic disinhibition

- **Core mechanism:** cortical primitives compete; BG implements gating. Direct pathway = Go (disinhibits thalamus → permits action); indirect pathway = NoGo (maintains inhibition → suppresses action). Parallel bidding from competing primitives with mutual inhibition until one wins.
- **HDC translation that is NOT rebranding:** the current ReasoningAgent dispatcher uses **keyword gates + first-match-wins** (`if "pell" in lower: try pell; elif "matrix" in lower: try eigenvalue; ...`). This works for cycle 7-10's bounded problem set (15 fixed shapes with distinct keywords). For open-domain semantics — where prompts are open-ended natural language and multiple primitives might have ambiguous applicability — first-match-wins breaks. A **BG-style confidence-scored parallel-bid dispatch** has each parser produce a confidence score (regex match strength, semantic-similarity-to-prompt-binding), and the dispatcher picks `argmax` with mutual-inhibition suppression of alternatives.
- **Why it's load-bearing for cycle 11 (not cycle-12+):** the open-domain-semantics dispatch problem IS what cycle 11 solves. Without this, the architecture inherits a brittle dispatcher that worked for hand-curated problem shapes but doesn't scale. This is the strongest single contribution of this angle.

### Cerebellum — climbing-fiber error signals → parallel-fiber weight updates

- **Core mechanism:** the cerebellum implements supervised motor learning. Climbing fibers from the inferior olive deliver error signals; these modulate parallel-fiber synapses onto Purkinje cells. The forward-model + prediction-error pattern is exactly the cerebellar computation.
- **NOT a new HDC primitive:** this is **angle 3's curiosity mechanism in different vocabulary.** Pathak 2017's ICM is the computational instantiation of what the cerebellum does biologically. The HDC `1 - cos(hv_pred, hv_actual)` curiosity signal that angle 3 identified has direct neurobiological substrate.
- **Synthesis use:** legitimization. The prediction-error-as-signal mechanism isn't a hopeful translation from RL theory; the brain implements it natively in the cerebellum. Cross-ref to angle 3 in synthesis; do not write a separate cerebellar mechanism.

### Prefrontal cortex / working memory — REJECT as rebranding

- **Core mechanism:** PFC sustains recurrent activity to hold task-relevant information across multiple seconds. Implements working memory through persistent firing of task-coding neurons.
- **HDC analogue candidate:** transient hypervector buffer holding intermediate Lemma-chain step outputs.
- **Why this is rebranding:** the Lemma chain **already implements working memory mechanically**. Each step's output IS the next step's input; the chain's intermediate state IS the scratchpad. Adding "prefrontal" vocabulary doesn't add a primitive. The 4-step `identify_form → compute_search_bound → enumerate → verify` chain already has the working-memory property built in.
- **Verdict: explicit reject** in section 6.

### Thalamus / superior colliculus — orienting attention (cycle-12+ at most)

- **Core mechanism:** thalamic relay + colliculus orienting drive attention shifts.
- **HDC translation:** attention as a hormone-vector that biases retrieval toward specific subspaces.
- **Why deferred:** the v2 DRAFT's hormone-modulation already handles this — attention shifts are a use case of the existing hormone-vector mechanism, not a new primitive. Cycle-12+ at most.

## 4. HDC translation (concrete mechanisms where they exist)

### 4a. Basal-ganglia-style confidence-scored parallel-bid dispatch (LOAD-BEARING for cycle 11)

```
For each prompt:
  1. Each parser produces a confidence score in [0, 1]:
       - regex match strength (full match = 1.0; partial = 0.5; no match = 0.0)
       - hypervector-similarity to prompt-binding (cos similarity, scaled)
       - combined: weighted average (tunable weights)
  2. Parallel bid: collect (parser_id, confidence) pairs for all parsers
  3. Apply mutual inhibition: top-1 confidence dominates; alternatives suppressed
  4. If top-1 confidence > tau_dispatch threshold: route to that parser's substrate
  5. If top-1 < threshold: honest-refusal path (no parser confident enough)
```

This replaces the current `if A: try A; elif B: try B; ...` chain. Specifically required when prompts are open-ended natural language and multiple primitives have ambiguous applicability — which is exactly cycle-11's open-domain semantics scope.

### 4b. Hippocampal-replay surprise-biased consolidation (additive to the merge)

```
At consolidation-pass time (offline / overnight):
  1. Pull the set of bindings_touched_by_surprising_rollouts (from angle 3 tracking)
     ∪ bindings_with_recent_audit_revision (from angle 2 ES pass)
     — this is the "recent + surprising/reward-modulated" set, biased like
     hippocampal sharp-wave-ripple replay.
  2. Apply the ES-style perturb-audit-reweight pass from angle 2 ON THESE
     BINDINGS ONLY, not uniformly across the substrate.
  3. (Cycle-12+) Some bindings get reverse-chain replay: chain executed in
     reverse, strengthening terminal-step weights.
```

## 5. Load-bearing vs decoration verdict (single sentence + percentage)

**~30-40% load-bearing** — the BG-style confidence-scored parallel-bid dispatch is genuinely new and load-bearing specifically for cycle-11 open-domain semantics dispatch (~25-30% of the angle on its own); hippocampal replay adds the surprise-biased selection rule that the consolidation merge was missing (~5-10%); cerebellum legitimizes angle 3 in neurobiology but adds no new mechanism (~0%); prefrontal/working-memory is rebranding (0%); thalamus / superior colliculus is at most cycle-12+ (0%).

## 6. Decision points for #05e synthesis (numbered for copy-paste)

1. **Adopt BG-style confidence-scored parallel-bid dispatch for cycle 11.** Replaces the current keyword-gated first-match-wins dispatcher. Each parser produces a `[0, 1]` confidence; argmax + threshold-gating + honest-refusal path when threshold not met. Specifically motivated by the open-domain-semantics dispatch problem cycle-11 is solving — required mechanism, not optional.

2. **Hippocampal replay adds the SURPRISE-BIASED SELECTION RULE to the consolidation merge.** The merge already specified when to consolidate (offline / overnight); replay specifies WHICH bindings (recent + surprising / high-prediction-error / high-audit-weight). Apply ES-style perturb-audit-reweight ON THIS SUBSET, not uniformly across the substrate.

3. **Cerebellum grounds angle 3 curiosity neurobiologically — not a separate mechanism.** Synthesis should cite cerebellum + climbing-fiber-error in angle 3's section, not as a parallel mechanism. Legitimizes the prediction-error-as-intrinsic-reward pattern as having direct biological substrate (not just a hopeful translation from RL theory).

4. **Reject prefrontal / working-memory framing as rebranding.** The Lemma chain already implements working-memory mechanically (each step's output IS next step's input). Adding "prefrontal" vocabulary doesn't add a primitive.

5. **Forward-AND-reverse-replay as a cycle-12+ candidate.** Reverse-order chain execution during consolidation strengthens terminal-step weights — useful for back-propagating audit-approval signals. Not load-bearing for cycle-11 MVP; flag for later.

6. **LOCK the consolidation quadruple-merge as ONE synthesis decision point.** Four angles cite it: angle 2 ES-style perturb-audit-reweight + angle 3 K-rollout surprising-region tracking + angle 4 multi-temporal-Raphael + this angle's hippocampal replay (with surprise-biased selection rule). The synthesis pass's most important single reduction is merging these into ONE consolidation primitive, not four. Quadruple-counting would imply mechanism-density that doesn't exist.

7. **Defer thalamus / superior-colliculus orienting attention to cycle-12+ at most.** Existing v2 hormone-modulation absorbs this. Don't introduce as a separate mechanism.

---

## Sources

- Wilson, M. A. and McNaughton, B. L. *Reactivation of Hippocampal Ensemble Memories During Sleep*. Science 265, 1994.
- Buzsaki, G. *The Brain from Inside Out*. Oxford University Press, 2019.
- Kandel et al. *Principles of Neural Science*, 6th ed., McGraw-Hill, 2021 (general anatomy reference for BG / cerebellum / PFC).
- Mink, J. W. *The Basal Ganglia: Focused Selection and Inhibition of Competing Motor Programs*. Progress in Neurobiology 50, 1996 (canonical BG-as-selection paper).
- Ito, M. *Cerebellar circuitry as a neuronal machine*. Progress in Neurobiology 78, 2006 (forward-model + error-correction in cerebellum).
- Advisor consult, cycle 10 #05d turn (auto-forwarded transcript).
- Lain Discord mid-cycle brain-inspiration exchange (msg `1503212043` and surrounding).
- DRAFT: `docs/artifacts/cycle-10-semantics-architecture.md` (status: DRAFT-PRELIMINARY).
- Research plan: `docs/artifacts/cycle-10-semantics-research-plan.md`, § Angle 1.
- Cross-references: `cycle-10-semantics-angle-evolutionary.md` (commit `4133eaa`) + `cycle-10-semantics-angle-curiosity.md` (`9f93ea2`) + `cycle-10-semantics-angle-multi-agent.md` (`4781366`).
