# Cycle 10 Semantics Architecture — Angle 4 (Multi-Agent Coordination + Scenario Simulation)

**Status:** research note, not canonical. Feeds the #05e synthesis pass that overwrites the DRAFT.
**Date:** 2026-05-11.

---

## 1. Lain quote (verbatim source anchor)

> *"we coordinate with others of same kind, on scale, and simulate scenarios, all to further our existence."*

— Msg `1503217035`, 2026-05-11 02:07 UTC.

## 2. Advisor verdict (2-3 sentences)

This is genuinely the thin angle of the four. For a single-user personal agent, three of the four sub-questions in the research plan collapse to architectural pieces already covered by angles 2 and 3 (and the forthcoming angle 1) — the temporal-multi-instance reframe lands in the consolidation/replay triple-merge; scenario simulation is K-rollout with pluggable scoring; sub-agent architecture is modular code, not a new primitive. The one genuinely new mechanism is **Sutton 1999 options as Lemma-chain-level abstraction** — addressing chains rather than primitives — but this is a cycle-12+ candidate, not cycle-11 MVP.

Net call: **~15-20% load-bearing.** Weakest angle. The note ships honestly thin (~60-70 lines) rather than padded.

## 3. Literature integration — paper by paper

### Sutton, Precup, Singh 1999 — *Between MDPs and Semi-MDPs* (options framework)

- **Core mechanism:** An option is a tuple `(I, π, β)`: initiation set, internal policy, termination condition. Options execute over multiple primitive steps, providing temporal abstraction. SMDP value-function theory generalizes Q-learning to operate at option-level.
- **HDC translation candidate:** **Lemma chains as options.** The agent's current dispatcher picks a primitive (`solve_quadratic`, `solve_pell_equation`, etc.). An option-level layer picks a CHAIN — the 4-step `identify_form → compute_search_bound → enumerate → verify` is one option; the 5-step integration-by-parts chain is another. Initiation set = chain's preconditions encoded as hypervector similarity to current prompt-binding. Termination condition = chain's expected output shape.
- **Why it's mechanism (not decoration):** chain-level dispatch IS a real abstraction layer. The current parser → dispatcher → substrate pipeline operates at primitive granularity; option-level reasoning would let chains compose into larger reasoning tasks (e.g., a "verify-then-extend" meta-chain composing `solve_pell_equation` followed by `_pell_brute_force_fundamental` cross-check).
- **Verdict: load-bearing as cycle-12+ candidate.** Cycle-11 MVP chains are short enough that option-level reasoning is overhead; load-bearing once chains exceed ~3-4 primitives composed.

### Vezhnevets et al. 2017 — *FeUdal Networks for Hierarchical RL*

- **Core mechanism:** Manager outputs goals at high temporal abstraction in a latent direction-vector space; worker executes primitives toward those goals.
- **HDC translation candidate:** Goals as hypervectors directly (HDC ships this natively). Manager-worker decomposition over agent's parse → dispatch chain.
- **Why it doesn't transfer to cycle 11 yet:** the current agent's chains are short. Manager-worker decomposition is overhead until chains grow. FeUdal is in the same family as Sutton options (both are temporal-abstraction mechanisms); they probably come in together once the agent's chains exceed ~3-4 primitives.
- **Verdict: cycle-12+ open question.** Don't oversell as mechanism now.

## 4. HDC translation (concrete mechanisms where they exist)

### 4a. The hormone-vectors interpretation of "scenario simulation"

The research plan asks: *"does scenario simulation measurably improve output quality, or is it equivalent to just running the agent with more diverse hormone vectors?"* — **The answer is the latter.** Scenario simulation in HDC = K rollouts with diverse hormone vectors, each scored by a composite of audit-approval-prediction and curiosity-signal. No new primitive; reuses v2's hormone-modulation architecture and angle 3's K-rollout loop.

```
For "simulation" of K scenarios:
  for k in 1..K:
    H_k = sample_hormone_vector_from_diverse_register_states()
    rollout_k = run_chain(prompt, with_hormone=H_k)
    score_k = audit_approval_predictor(rollout_k) + curiosity_satisfaction(rollout_k)
  emit argmax_k(score_k)
```

This is `angle 3 K-rollout` with `pluggable scoring`. The synthesis pass should MERGE these into one mechanism, not double-count.

### 4b. Options-as-Lemma-chain (cycle-12+ candidate)

For when cycle-11 implementation grows the chain library: a meta-dispatcher addressable at chain level. Each chain registered with `(initiation_hv, internal_chain, termination_hv)` tuple. The agent's outer loop selects chains by hypervector similarity to current prompt; the chain's internal substrate-call sequence runs as a unit.

Not load-bearing for cycle-11 MVP (chains are short, primitives are addressed directly via existing dispatcher).

## 5. Load-bearing vs decoration verdict (single sentence + percentage)

**~15-20% load-bearing** — only Sutton-options-as-Lemma-chain-abstraction is a genuinely new mechanism, and it's a cycle-12+ candidate rather than cycle-11 MVP; the rest of the multi-agent framing either rebrands existing primitives (sub-agent = modular code; scenario simulation = K-rollout with pluggable scoring) or doesn't apply to a single-user agent (multi-instance Raphael).

## 6. Decision points for #05e synthesis (numbered for copy-paste)

1. **Reject multi-instance Raphael for single-user agent.** Multi-process is overkill; multi-temporal (fast/slow/overnight Raphael) collapses to the consolidation/replay triple-merge already flagged in angles 2/3 + forthcoming angle 1.

2. **Reject "scenario simulation" as a separate mechanism.** It IS angle 3's K-rollout with pluggable scoring (audit-approval prediction in addition to curiosity-signal). Synthesis pass should describe ONE K-rollout primitive with multiple scoring functions plugged in, not two parallel rollout mechanisms.

3. **Reject "sub-agent architecture" as a new primitive.** Specialized HDC subspaces (cortex/limbic/hippocampus/basal-ganglia analogues) are already in v2 DRAFT. Implementing them as separate Python modules is normal code organization, not new architectural primitive — `[no new mechanism here; modular code is in v2 already]`.

4. **Reject pre-emit audit-prediction as rebranding.** "Simulate lain's audit response before emitting" = audit-weight-adjustment applied speculatively at emit-time = same learned-judgment function, different application moment. Not a new mechanism.

5. **Adopt Sutton-options-as-Lemma-chain-abstraction as a CYCLE-12+ candidate.** Once cycle-11 implementation grows the chain library beyond ~3-4 primitives composed, options-level dispatch becomes load-bearing. State explicitly in synthesis as deferred; do NOT include in cycle-11 MVP scope.

6. **Defer FeUdal manager-worker to cycle-12+.** Same family as Sutton options (temporal abstraction). Comes in together when chains grow.

7. **MERGE flag for synthesis pass — the consolidation triple.** Angle 2's ES-style perturb-audit-reweight + angle 3's K-rollout-with-surprising-region-tracking + angle 1's (forthcoming) hippocampal replay + this angle's multi-temporal-instance reframe = ONE architectural piece (offline / overnight consolidation pass), viewed through four lenses. The synthesis must produce ONE decision point, not four — quadruple-counting would imply mechanism-density that doesn't exist.

---

## Sources

- Sutton, R. S., Precup, D., Singh, S. *Between MDPs and Semi-MDPs: A Framework for Temporal Abstraction in Reinforcement Learning*. Artificial Intelligence 112, 1999.
- Vezhnevets, A. S. et al. *FeUdal Networks for Hierarchical Reinforcement Learning*. ICML 2017 (arXiv:1703.01161).
- Advisor consult, cycle 10 #05c turn (auto-forwarded transcript).
- Lain Discord msg `1503217035`, 2026-05-11 02:07 UTC.
- DRAFT: `docs/artifacts/cycle-10-semantics-architecture.md` (status: DRAFT-PRELIMINARY).
- Research plan: `docs/artifacts/cycle-10-semantics-research-plan.md`, § Angle 4.
- Cross-references: `cycle-10-semantics-angle-evolutionary.md` (commit `4133eaa`) + `cycle-10-semantics-angle-curiosity.md` (commit `9f93ea2`).
