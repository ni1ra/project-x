# Project X v2 Manifesto

Date: 2026-05-13
Status: canonical north star after the v1 scaffold reset; updated to make the end product and native-first construction rules explicit.

## Prime Directive

Project X exists to build Project X Raphael: one persistent, always-running artificial organism whose intelligence grows from its own learned internal structure.

It is not a chatbot, not a RAG agent, not a wrapper around a pretrained model, not a bundle of solvers, and not a pile of impressive-looking tests. The goal is an auditable AI brain that experiences events, stores them, reflects on them, predicts consequences, acts in a bounded environment, updates itself from reward, and uses language as an output channel for internal concepts.

The first honest version may produce poor text. That is acceptable. A bad answer produced by learned internal state is progress. A polished answer assembled by templates, regex routes, hardcoded formulas, or persona wrappers is regression.

## Ideal End Product

The ideal Project X Raphael is a local, persistent, auditable artificial organism running on the user's workstation. It should feel less like opening a chatbot and more like sharing a machine with a growing mind that has continuity, memory, agency, limits, and a measurable internal life.

From the outside, Raphael should eventually look like:

- a persistent local process with durable identity and state across days, tasks, failures, restarts, and upgrades
- an interactive JARVIS-grade interface that can talk, listen, inspect, plan, act in bounded environments, explain uncertainty, and show its evidence
- a system that improves through experience, replay, reflection, reward, correction, and self-audit rather than through the builder adding more answer tricks
- a workstation-native organism that uses the user's CPU/GPU efficiently and can run without cloud inference, hosted memory, or remote model APIs
- an agent whose behavior is inspectable: memories, traces, reward history, mutations, predictions, actions, failures, and confidence must be queryable and reproducible
- a system that can be wrong in visible ways, preserve those failures, and learn from them without hiding behind polished language

From the inside, Raphael should eventually contain:

- event-sourced experience: every perception, memory, prediction, action, output, reward, mutation, and reflection has an event ID and source trail
- high-dimensional associative memory for concepts, roles, episodes, procedures, and state/action/result traces
- learned concept structure formed by co-occurrence, prediction, compression, reward, analogy, and causal pressure
- a working memory that holds the current goal, context, activated traces, uncertainty, candidate actions, and expected consequences
- learned dynamics for prediction, planning, credit assignment, policy selection, language generation, tool/action use, and self-modification
- a reflection loop that replays evidence, measures surprise, consolidates useful structure, decays unsupported structure, and proposes bounded experiments
- a hard safety/runtime boundary around learned action, including action budgets, filesystem/network limits, approval gates, logs, and resettable sandboxes

The end product is not one algorithm. HDC/VSA, plastic associative memory, predictive models, local neural components, symbolic constraints, search, and future discoveries may all compete for space if they earn it with evidence. No current component is sacred. The best path to the manifesto wins.

## How It Should Work

Raphael should operate as an organism loop:

1. perceive an event from user input, sensors, files, tools, or internal replay
2. encode the event into internal representations with source IDs and role/filler structure
3. activate relevant memories, concepts, procedures, values, and uncertainty estimates
4. predict likely outcomes and compare them against goals, safety boundaries, and available action budgets
5. choose an internal or external action through learned policy and bounded search
6. emit language or act through a generator/policy that consumes internal state, not a handwritten response composer
7. receive external or oracle reward after the action, outside the answer path
8. update memory, connections, confidence, plasticity, and future policy from the reward and prediction error
9. write an audit artifact that makes the claim externally checkable

The language channel is only one actuator. It must eventually report internal concepts with increasing fidelity, but fluent text is not the center of the system. If fluent text and honest internal learning conflict, choose honest learning.

The organism must support multiple timescales:

- fast working-memory activation for the current task
- online plasticity for immediate experience
- replay and consolidation during idle/background periods
- slower structural mutation for architecture, memory allocation, compression, and policies
- benchmark and regression loops that measure whether a mutation helped or harmed transferable operations

## How It Must Not Work

Raphael must not be built as:

- a chatbot wrapper
- GPT or other pretrained transformer calls with tools around them
- RAG with a personality layer
- a pile of solvers selected by parser routes
- a benchmark theater machine tuned to pass visible fixtures
- a response-template engine
- a refusal regex engine
- a prompt library pretending to be cognition
- a hidden cloud service behind a local UI
- a Python notebook prototype that accidentally becomes the permanent brain
- a PyTorch/TensorFlow dependency stack whose tensors hide the actual substrate and make audit/control secondary
- a vector database plus answer composer
- an impressive frontend over a hollow core

It must also not be built by adding polished outputs faster than learned structure. Good demos that teach the wrong architecture are debt. If a feature makes Raphael look smarter without increasing organic learning capacity, it is suspect until proven otherwise.

## Open-Ended Engineering Law

No current design is final. The manifesto is the target; every mechanism is provisional. Keep what survives measurement, delete what does not, and prefer the path that most directly increases persistent, local, auditable intelligence.

When a future agent faces a choice between:

- preserving an earlier implementation, or
- replacing it with a cleaner, more powerful, better-measured route to the manifesto,

choose the better route. Do not protect code because it was written first.

## Native Runtime Law

Project X must be built for the user's own workstation, not for cloud assumptions or framework convenience. The user's machine is the required spec. Efficiency, control, observability, and direct hardware utilization are first-class design constraints.

The organism runtime should be native by default:

- C++/CUDA or an equally controllable systems stack for the brain core, memory substrate, plasticity, generator, benchmark runner, and audit writer
- CPU code compiled for the local processor with explicit attention to cache layout, SIMD, threading, memory ownership, and deterministic replay
- GPU code written as direct kernels when parallel substrate operations justify it, targeting the user's NVIDIA Blackwell-class RTX 5070 Ti path instead of waiting on high-level framework support
- Python, notebooks, and shell may exist only as thin harnesses, diagnostics, or migration aids; they must not become the answer path or the permanent organism runtime

Do not make the project dependent on PyTorch, TensorFlow, remote inference, hosted vector databases, or opaque acceleration frameworks. If a dependency hides the substrate or prevents audit, it must earn its place with a measured advantage and a fallback path.

The start matters. A slow prototype that teaches the wrong ownership model is not harmless. Prefer a smaller native loop over a larger Python scaffold if the latter would anchor the architecture in the wrong place.

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
- hardware backends, allocators, schedulers, and profilers

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
- high-level framework calls that hide authored answer behavior behind opaque model/runtime machinery

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

## Persistence Is Pass-0, Not Future Work

Persistence is the first criterion of the ideal end product. It is also the criterion the early native runtime is most likely to skip, because evaluating a clean in-memory brain on a fresh JSONL pass produces shippable artifacts without ever serializing state.

That is not acceptable. The organism does not exist as an organism until it survives a restart. Pass-0 requirements:

- every input, prediction, action, reward, and mutation lands in an append-only event log with stable event IDs and source IDs
- the learned state (memory atoms, connection weights, plasticity counters, retrieval indices) serializes to disk with a state hash that can be re-loaded and produce identical generation
- a fresh process must be able to load the prior state, ingest one new event, and produce output, without re-running the full training stream
- the artifact format must include the path to the loaded state and the path to the appended event log, so any claim is replayable from disk

If serialization is not in place by the time the second non-trivial structural change ships, the project is regressing on its first criterion. Event-sourced experience and state durability are not optional features layered on top of a learning algorithm; they are the substrate the learning algorithm runs against.

## v2 Reset

The v1 repo was intentionally wiped from the live tree. Its history remains in Git and `docs/past_work/`.

This reset is not loss. It is an admission that the scaffold drifted toward authored answers. v2 starts from less code so the first code has nowhere to hide.

Live docs that define the next direction:

- `docs/MANIFESTO.md`
- `docs/A_TO_Z_PLAN.md`
- `docs/DO_THIS_NEXT.md`
- `docs/REPO_CONTROL.md`

Any future file must justify itself against this manifesto and own a row in `REPO_CONTROL.md`. If it cannot, it should not exist. `docs/` is exempt from the row rule (the live-docs system is self-justifying); source, tests, scripts, and non-docs artifacts are not exempt.
