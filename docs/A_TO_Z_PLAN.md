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

The organism must run on the user's workstation. The local machine is the required target spec, not a convenience environment. Design from day 0 for native execution, deterministic replay, direct CPU/GPU control, and measurable efficiency.

No implementation is final. The best measured path to the manifesto wins, even if it replaces organic-v0. Preserve the artifact contract and the honesty constraints; do not preserve code shape for its own sake.

The first iteration must already produce output, but the output may be poor. It must be honest:

- no templates
- no hardcoded answer routes
- no solver-as-agent
- no persona wrapper
- no fake "all tests pass" theater
- no pretrained transformer model
- no high-level ML framework in the answer path

The first iteration should prove only this:

Given experience and reward, the brain forms internal connections and emits from those connections.

## 1.1 Runtime Target

Primary runtime direction:

- native C++20 core for organic-v0
- CUDA C++ backend once the substrate has enough parallel work to justify GPU kernels
- build flags that exploit the local CPU where valid, while preserving deterministic artifact output
- JSONL event streams and JSON artifacts kept stable across CPU/GPU backends

Current environment facts from the first native pass:

- GCC 13.3 is available
- Rust 1.93 is available, but Rust is not the chosen first brain runtime because CUDA C++ gives the most direct path to Blackwell kernels
- CUDA Toolkit 12.6 is available
- `nvidia-smi` is blocked by the operating system in this environment, so GPU execution must be probed separately before any GPU-speed claim

Python may be used for one-off analysis, but it is not the organism runtime and should not own generation, learning, evaluation, or artifacts.

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

- `native/organic_v0.cpp`
- `Makefile`
- `benchmarks/v2_ladder/`
- `scripts/train_organic_v0.sh`
- `scripts/eval_organic_v0.sh`
- `scripts/test_organic_v0.sh`

These are suggestions, not permission to add bloat. If fewer files can express the system cleanly, use fewer.

The first native version should keep data structures close to future GPU form: compact numeric feature IDs, contiguous vectors where practical, no Python object graph as brain state, no dynamic framework tensors hiding behavior.

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
- hardware/backend facts

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
- Python or a high-level ML framework becomes the organism runtime by inertia
- GPU/CPU performance is claimed without measured local artifacts

## 8. Development Philosophy

Prefer structural changes over patches.

If a path is wrong, delete it. Do not layer complexity over a broken center. The project should become smarter by changing the organism's learning machinery, not by adding cosmetic behavior.

Quality can be poor at first. Honesty cannot.

## 9. Phase Changelog (v2 — organic substrate)

Per-cycle status row. Each cycle ticks one or more architecture-target sub-points from §2 with mechanical-proof evidence linked.

| Cycle | Date closed | Scope | Status | Evidence |
|---|---|---|---|---|
| v2-c1 | 2026-05-13 | Native HDC organism + trace-id ablation | ✅ | commit `dab6e41`; `run/artifacts/organic-v0/eval_{with,no}_trace.json`; proved trace-id feature is redundant, position-bound bigram chain is load-bearing |
| v2-c2 | 2026-05-13 | Benchmark honesty (parity-cheat removal + abstention contrastive + length variance) + persistence pass-0 (save/load + event log + round-trip self-test) | ✅ | `run/artifacts/organic-v0/eval_compositional_tightened_persisted.json` (overall 0.36 with persistence active); `run/artifacts/organic-v0/persist_self_test.json` (`load_status: save_and_load_verified`); manifesto §"Persistence Is Pass-0" materialized |
| v2-c3 | 2026-05-13 | Learned segment generation (picked over HDC-unbind via /pick-one 405/420; advisor concurred after escalated Builder-Law boundary call). Action space expanded from kAscii to kAscii+kMaxRoles; mode-switch weights in same connection substrate; copy-mode emission reads chars from test-time observation. Persistence pass-0 survives (state_hash gate preserves cycle-2 reproducibility) | ✅ | `run/artifacts/organic-v0/eval_compositional_v2c3.json` (overall 0.680 vs cycle-2 0.360; unseen_filler 8/8 was 0/8; unseen_filler_long 2/2 was 0/2); `run/artifacts/organic-v0/persist_self_test_v2c3.json` (hash + output bit-exact); honest direct_replay regression 5/5→3/5 documented in `docs/past_work/cycles/phase_v2_organic_substrate/dev-cycle-3-4a0260f.md` |
| v2-c3.5 | 2026-05-13 | GPT audit follow-up: dual-learning of filler spans (trace-id-anchored literal channel) + legacy loader default + config_hash extension + segment-mode evidence export + empty-role guardrail explicit END. Five audit defects fixed, cycle-3 direct_replay regression recovered, all cycle-3 gains held | ✅ | `run/artifacts/organic-v0/eval_compositional_v2c3.json` (overall 0.720 vs cycle-3 0.680; direct_replay 4/5 vs cycle-3 3/5; unseen_filler 8/8 + unseen_filler_long 2/2 held); cycle-2 snapshot loads cleanly under cycle-3.5 binary (exact_rate 0.360, `"milaquart arch6"` on evt_mem_test_001); `docs/past_work/cycles/phase_v2_organic_substrate/dev-cycle-3-5-5c69d51.md` |
| v2-c4 | 2026-05-13 | Trace-span-position literal memory: picked candidate A2 (407/420) and added trace-local span-offset features for copied spans, closing the residual `evt_mem_dev_000` deep-span replay failure while keeping role-copy transfer intact | ✅ | `run/artifacts/organic-v0/eval_compositional_v2c4.json` (overall 0.760 vs 0.720; direct_replay 5/5 vs 4/5; unseen_filler 8/8, long 2/2, short 1/1 held; state hash `23d5362d7c8b8ea7`; config hash `490e66afe575275c`); `run/artifacts/organic-v0/eval_compositional_v2c4_from_disk.json` diff-clean on summary_metrics + model_state_hash; `run/artifacts/organic-v0/persist_self_test_v2c4.json`; `docs/past_work/cycles/phase_v2_organic_substrate/dev-cycle-4-422ed12.md` |
| v2-c5 | 2026-05-14 | Numeric-derived trace activation + relation projection + intent curriculum repair. Original old fixture reaches 24/25 (0.960) before data repair; repaired benchmark reaches 25/25 (1.000). Numeric ablation falls to 22/25, relation ablation to 23/25. | ✅ | `run/artifacts/organic-v0/eval_compositional_v2c5.json` (overall 1.000; state hash `ccd7a48ec4614703`; config hash `de2ad1690588249d`); `run/artifacts/organic-v0/eval_compositional_v2c5_from_disk.json` diff-clean on summary_metrics + model_state_hash; `run/artifacts/organic-v0/persist_self_test_v2c5.json`; `run/artifacts/organic-v0/eval_cycle5_substrate_only_old_fixture.json` old-fixture 0.960; `run/artifacts/organic-v0/eval_cycle5_ablate_numeric.json`; `run/artifacts/organic-v0/eval_cycle5_ablate_relation.json` |
| v2-c6 | 2026-05-14 | Numeric relation substrate generalization beyond parity. Added threshold (`mark > cutoff`) and modular (`mark mod 3`) hidden-rule mini-suites with two train values per class, held-out unseen marks, isolated ablation flags, and transient cache/index speed cleanup. | ✅ | `run/artifacts/organic-v0/eval_cycle6_relations_all_on.json` (overall 1.000, 30/30; state hash `29958f0880e662dc`; config hash `99032d46527a795b`); `run/artifacts/organic-v0/eval_cycle6_relations_from_disk.json` diff-clean on summary_metrics + model_state_hash; `run/artifacts/organic-v0/persist_self_test_v2c6.json`; `run/artifacts/organic-v0/eval_cycle6_ablate_numeric.json`; `run/artifacts/organic-v0/eval_cycle6_ablate_threshold.json`; `run/artifacts/organic-v0/eval_cycle6_ablate_modular.json`; `docs/artifacts/CYCLE6_NUMERIC_RELATION_GENERALIZATION.md` |
| v2-c7A | 2026-05-14 | Continuation learning as a first-class substrate primitive. Eval can now load parent -> learn train split -> save child -> evaluate same-process child; persistence self-test can verify loaded-parent child checkpoints; fork A/B prove same parent diverges under different experience. | ✅ | `run/artifacts/organic-v0/fork_divergence_cycle7a.json` (parent hash `29958f0880e662dc`; child A hash `fab9c2c0367ed2b5`; child B hash `c0f016285e735e14`; child hashes and held-out outputs diverge); `run/artifacts/organic-v0/eval_cycle7a_child_a_from_training.json` + `_from_disk.json` diff-clean on summary_metrics + model_state_hash; same for child B; `run/artifacts/organic-v0/persist_self_test_cycle7a_child.json`; `docs/artifacts/CYCLE7A_GROWING_BRAIN_FILE.md` |
| v2-c7B | 2026-05-14 | Native interactive hidden-rule micro-harness. Loaded v2-c6 parent acts before oracle feedback, learns correction into state, then transfers to held-out parity/threshold/modular marks across two seeds. Feedback-strength ablation shows correction pressure is load-bearing. | ✅ | `run/artifacts/organic-v0/interactive_hidden_rule_cycle7b_summary.json` (aggregate held-out 14/14, total pre-feedback 26/42; parent hash `29958f0880e662dc`); `run/artifacts/organic-v0/interactive_hidden_rule_cycle7b_feedback_ablation.json` (strength 2.0 -> 14/14 held-out, strength 1.0 -> 13/14); seed artifacts `interactive_hidden_rule_cycle7b_seed7001.json` and `interactive_hidden_rule_cycle7b_seed7002.json`; `docs/artifacts/CYCLE7B_INTERACTIVE_HIDDEN_RULE.md` |
