# A_TO_Z Plan - Project X v2 Organic Brain

Date: 2026-05-13
Status: v2 skeleton after repo reset.

## 0. Current State

The live repo has been reduced to:

- `docs/MANIFESTO.md`
- `docs/A_TO_Z_PLAN.md`
- `docs/DO_THIS_NEXT.md`
- `docs/past_work/`

All v1 code, tests, data, benchmark artifacts, scripts, and scaffolds are deleted from the live tree. Historical material remains in Git history and `docs/past_work/`.

This is intentional. The next implementation must not patch the v1 scaffold.

## 1. North Star

Build one persistent Project X Raphael instance: an artificial organism with memory, plasticity, curiosity, reflection, reward, action, and language as an output channel.

The first iteration must already produce output, but the output may be poor. It must be honest:

- no templates
- no hardcoded answer routes
- no solver-as-agent
- no persona wrapper
- no fake "all tests pass" theater
- no pretrained transformer model

The first iteration should prove only this:

Given experience and reward, the brain forms internal connections and emits from those connections.

## 2. Architecture Target

Future code should grow toward these parts:

1. Event log
   - Every input, memory, action, prediction, output, reward, and mutation is an event.

2. HDC/VSA memory spine
   - Role-filler binding, episodic indexing, concept atoms, trace retrieval, cleanup.

3. Learned concept substrate
   - Concepts form from co-occurrence, prediction, compression, and reward.

4. Procedure/action memory
   - State/action/result/reward traces, learned policies, sandbox actions.

5. Predictive world model
   - Predict next observation and outcome; surprise drives learning.

6. Reflection loop
   - Background replay grounded in event evidence, not free hallucination.

7. Plasticity controller
   - Regulates learning rate, consolidation, decay, reopening, and protected memory.

8. Learned generator
   - Produces the complete output string from internal state.

9. Safety boundary
   - Hard sandbox limits, action budgets, approval gates, and logs.

10. Benchmark ladder
   - Granular multi-domain difficulty rungs through beyond-human targets.

## 3. Non-Goals

Do not rebuild:

- the v1 parser-dispatcher runtime
- handcoded math/physics answer primitives as agent capabilities
- template composers
- response prefix wrappers
- regex refusal as final behavior
- retrieval-fragment "generation"
- benchmark-specific routes

Oracles can exist later, but only outside the agent path.

## 4. First Implementation Milestone

Name: `organic-v0`.

Goal: a tiny artificial brain that learns from a small event stream and emits text from learned internal connections only.

Minimum behavior:

- train on a tiny curriculum of event/response examples
- build internal connection state
- emit a full output string without templates
- record the exact connection state used for emission
- evaluate on held-out prompts
- produce bad output honestly if that is what the learned state supports

Suggested first files for the next coding pass:

- `src/project_x_v2/events.py`
- `src/project_x_v2/hdc.py`
- `src/project_x_v2/brain.py`
- `src/project_x_v2/plasticity.py`
- `src/project_x_v2/generator.py`
- `src/project_x_v2/train.py`
- `src/project_x_v2/eval.py`
- `benchmarks/v2_ladder/`
- `scripts/train_organic_v0.py`
- `scripts/eval_organic_v0.py`

These are suggestions, not permission to add bloat. If fewer files can express the system cleanly, use fewer.

## 5. Training Data Shape

Use event-sourced JSONL, not prompt templates.

Example shape:

```json
{
  "event_id": "evt_000001",
  "episode_id": "ep_0001",
  "split": "train",
  "input": "remember: the red key opened the left door",
  "observations": ["symbol:red_key", "action:opened", "object:left_door"],
  "target_output": "stored",
  "reward": {"memory_accuracy": 1.0, "brevity": 0.5},
  "source": "seed_curriculum_v0"
}
```

The runtime may learn from `target_output`, but no code may assemble that output at inference.

## 6. Benchmark Ladder v2

Create a granular suite from the beginning. Each problem should be small, inspectable, and tied to a transferable operation.

Initial domains:

- memory
- hidden-rule learning
- causal chain prediction
- basic math concepts
- language expression
- refusal and uncertainty
- sandbox action

Later domains:

- physics
- coding/debugging
- ARC-style games
- no-engine chess/state fidelity
- philosophy
- poetry
- social modeling
- scientific discovery
- self-modification

Difficulty levels:

0. Emits from learned state.
1. Learns toy rule.
2. Generalizes held-out variants.
3. Handles noise and adversarial wording.
4. Solves multi-step textbook tasks.
5. Solves expert tasks.
6. Produces research-grade candidates.
7. Produces independently verified beyond-human results.

The suite should report granular scores, not one vanity number.

Required result fields:

- run_id
- command
- seed
- train/dev/test split
- model/config hash
- available tools
- action budget
- reward vector
- output transcript
- machine-readable scores
- failure cases
- interpretation

## 7. Success Criteria For The First Real Run

The first run succeeds if:

- output is produced by learned state, not templates
- the result artifact can point to the internal connections used
- at least one held-out task shows learning above cold/random baseline
- bad outputs are preserved, not hidden
- no legacy scaffold is reintroduced
- all claims include artifact paths

It fails if:

- code contains route tables for benchmark answers
- code hardcodes response text
- a solver generates the agent answer
- tests pass because the benchmark was made too easy
- subjective quality is self-scored as proof

## 8. Development Philosophy

Prefer structural changes over patches.

If a path is wrong, delete it. Do not layer complexity over a broken center. The project should become smarter by changing the organism's learning machinery, not by adding cosmetic behavior.

Quality can be poor at first. Honesty cannot.
