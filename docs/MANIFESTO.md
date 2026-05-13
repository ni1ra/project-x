# Project X v2 Manifesto

Date: 2026-05-13
Status: canonical north star after the v1 scaffold reset.

## Prime Directive

Project X exists to build Project X Raphael: one persistent, always-running artificial organism whose intelligence grows from its own learned internal structure.

It is not a chatbot, not a RAG agent, not a wrapper around a pretrained model, not a bundle of solvers, and not a pile of impressive-looking tests. The goal is an auditable AI brain that experiences events, stores them, reflects on them, predicts consequences, acts in a bounded environment, updates itself from reward, and uses language as an output channel for internal concepts.

The first honest version may produce poor text. That is acceptable. A bad answer produced by learned internal state is progress. A polished answer assembled by templates, regex routes, hardcoded formulas, or persona wrappers is regression.

## Builder Law

The builder may write machinery. The builder may not write the agent's intelligence.

Allowed authored code:

- memory substrate
- encoders
- plasticity and consolidation rules
- training loops
- reward and audit mechanics
- sandbox and safety boundaries
- evaluators, verifiers, and benchmark oracles
- data pipelines and artifact logging

Forbidden as final capability source:

- hardcoded formulas used to answer
- parser or dispatcher chains that decide what the agent knows
- response templates
- persona prefixes or voice markers
- hardcoded humor
- hardcoded refusal strings as the source of refusal behavior
- trigger lists that impersonate understanding
- benchmark-specific branches
- self-scored subjective quality

If a future code agent wants to add a shortcut, it must ask one question first:

Does this make the brain learn, or does it make the builder answer on the brain's behalf?

If the builder is answering, do not add it.

## Organic Brain Thesis

Project X Raphael should be a single persistent instance. When no user task is active, it should not sit idle as a stateless program. It should replay past events, compare predictions to outcomes, compress experience, search for causal structure, update confidence, and prepare better future behavior.

Reflection is not daydreaming. Background cognition must stay grounded in evidence:

- replay real episodes
- preserve source event IDs
- measure prediction error
- compare against later outcomes
- reward compression that preserves behavior
- punish unsupported confabulation
- record every structural mutation

The unconscious part of the system is replay, consolidation, causal induction, concept clustering, policy update, and plasticity control. The conscious part is the active workspace: current goal, salient memories, candidate actions, uncertainty, and the final language/action output.

## Concepts Before Language

Language is not the brain. Language is the interface.

The agent should learn concepts, causal relations, procedures, and values in internal representations first. Words are how the brain reports, asks, teaches, persuades, refuses, and coordinates. The model should not be a statistical next-token engine with memory bolted on.

The language generator must eventually consume internal state and produce the full output string. No wrapper may prepend "Notice." No template may assemble the answer. If the agent develops a stable voice, it must come from training, memory, feedback, and self-consistency pressure.

## HDC Position

HDC/VSA remains a strong candidate memory spine: binding, bundling, cleanup, role-filler structure, fast associative retrieval, and graceful degradation are aligned with the project.

But HDC is not magic and not literally infinite memory. Capacity, interference, cleanup error, and semantic brittleness must be measured. Any claim about memory scale requires run IDs, dimensions, item counts, error rates, and artifact paths.

HDC should carry:

- episodic memory indices
- role-filler bindings
- concept atoms
- procedure traces
- state/action/result events
- retrieval and cleanup memory

HDC alone is probably not enough. The brain also needs learned dynamics: prediction, action policy, credit assignment, generative language, causal abstraction, and plasticity control.

## Reward System

The environment shapes the organism. Project X must not rely on one vague reward. It needs a reward vector.

Core reward axes:

- prediction error reduction
- task success
- causal explanation improvement
- memory accuracy
- source fidelity
- compression/parsimony
- novelty under control
- useful curiosity
- long-horizon consistency
- safety boundary respect
- time/energy/action cost
- external/lain approval for subjective domains

Parsimony is mandatory. If 10 connections explain the same behavior as 20 without quality loss, the 10-connection structure should win. Complexity is a cost. Bloat is not intelligence.

Plasticity should be dynamic:

- high for new domains
- lower for stable verified concepts
- reopened after repeated prediction failures
- protected around safety boundaries and proven facts
- decayed for unsupported or low-value traces

## First Output Rule

The first v2 implementation must produce output from learned internal connections only.

This does not mean code has no influence. The architecture, data, reward, and plasticity rules shape the organism. It means the answer text and capability must not be authored by code. No route table should decide "this is quadratic, call solve_quadratic." No template should decide "say Negative." No wrapper should decide "sound like Raphael."

Bad organic output beats polished counterfeit output.

## Benchmark Ladder

Project X needs a granular intelligence ladder across domains. The ladder should become harder until it reaches and then exceeds current human achievement.

The ladder exists to measure growth, not to create fake wins. Each rung must name the transferable operation it measures.

Domains:

- memory and identity
- hidden-rule exploration
- causal diagnosis
- math
- physics
- coding and terminal action
- sandbox tool use
- games and ARC-style environments
- language and dialogue
- philosophy
- poetry and creative synthesis
- social modeling and theory of mind
- scientific discovery
- self-modification and meta-learning

Rung levels:

0. Organism emits: produces any response from learned state, with provenance of training and no templates.
1. Toy learned rules: small hidden-rule tasks, held-out seeds, machine-graded.
2. Schoolbook concepts: arithmetic, algebra, simple physics, memory QA, basic tool use.
3. Robust variants: randomized wording, adversarial distractors, noisy context, held-out forms.
4. Undergraduate competence: multi-step derivations, lab-style tasks, medium code/debug problems.
5. Expert competence: hard contest problems, rigorous proofs, complex systems, long-horizon projects.
6. Research frontier: open-ended tasks where success requires creating new methods or discovering structure.
7. Beyond current humanity: candidate breakthroughs only count after independent verification by domain experts, proof checkers, reproducible experiments, or external benchmark authorities.

Do not claim level 6 or 7 from self-report. For frontier and beyond-human rungs, the artifact is a candidate until independently verified.

Every benchmark result must include:

- run ID
- exact command
- seed
- model/config hash
- available tools
- training/eval split
- whether oracle access was available
- machine-readable result file
- transcript or trace file
- short interpretation of what improved and what did not

## Anti-Theater Rules

These are hard gates:

- Passing tests is not intelligence unless the tests force learned behavior.
- More code is not progress unless it increases organic learning capacity.
- A scaffold is not a capability.
- A benchmark-specific branch is contamination.
- A subjective self-score is invalid evidence.
- A handcoded oracle may grade; it may not answer for the agent.
- A retrieval result is not generation.
- A wrapper is not persona.
- A refusal regex is not moral judgment.
- A sandbox script directly invoked by the builder is not learned tool use.

The best part is no part. Prefer deletion over patches when the path is wrong.

## Safety Boundary

Learned refusal is desirable, but hard containment is non-negotiable. The agent may learn how to refuse, but it must not be trusted to enforce all safety by preference alone.

The runtime must keep:

- filesystem boundaries
- network boundaries
- action budgets
- resettable sandbox state
- raw action logs
- approval gates for external/destructive operations

Safety containment is machinery, not model knowledge. It may be hardcoded.

## v2 Reset

The v1 repo was intentionally wiped from the live tree. Its history remains in Git and `docs/past_work/`.

This reset is not loss. It is an admission that the scaffold drifted toward authored answers. v2 starts from less code so the first code has nowhere to hide.

Only three live docs define the next direction:

- `docs/MANIFESTO.md`
- `docs/A_TO_Z_PLAN.md`
- `docs/DO_THIS_NEXT.md`

Any future file must justify itself against this manifesto. If it cannot, it should not exist.
