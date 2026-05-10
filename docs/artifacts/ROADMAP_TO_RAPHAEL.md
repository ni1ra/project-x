# Roadmap To Raphael

**Date:** 2026-05-09  
**Scope:** Phase 9 through Phase 15+ strategy after Phase 8 HDC organic memory proof.  
**Hardware envelope:** RTX 5070 Ti, 13.9 GB usable VRAM hard cap, i9 CPU, tight WSL RAM, NVMe storage.  
**Thesis:** Build a hybrid local agent: local LLM speech/action surface, HDC semantic memory spine, deterministic controller, durable provenance, schema-first tools, replay consolidation, measured self-improvement, and later SNN/Neural CPU convergence.

---

## 0. Executive Verdict

Phase 8 proved a real memory primitive.

It did not prove a chattable agent.

The ideal way forward is not pure HDC, pure SNN, or pure transformer.

The ideal way forward is a layered hybrid:

```text
User
  -> Controller
  -> Encoder
  -> HDC Memory + Metadata Store
  -> Evidence Packet
  -> Local Generator
  -> Tool/Action Runtime
  -> Logs + Replay + Benchmarks
  -> Self-Improvement Harness
  -> SNN/HDC/Triton convergence
```

Each layer must become testable before the next layer depends on it.

The sequencing that maximizes learning per cycle:

1. Prove semantic memory with real text.
2. Put memory inside a minimal chat loop.
3. Add memory dynamics.
4. Add tool actions.
5. Add local generator hardening.
6. Add self-improvement under benchmark gates.
7. Add branch-and-rank cognition.
8. Bring the SNN/Neural CPU substrate back in as an optimized learned controller/encoder path.

---

## 1. What Has Been Done So Far

### Phase 1-6

Project X began as a research scaffold for novel token-prediction architectures.

Durable surfaces:

- `README.md`
- `pyproject.toml`
- `src/project_x/model.py`
- `src/project_x/smoke.py`
- `src/project_x/config.py`
- `gpt-codex/runs/`
- `docs/past_work/phases/`

The seed model in `src/project_x/model.py` is a small transformer-like architecture:

- local causal attention
- learned global memory slots
- routed expert MLPs
- smoke tests for forward shape

This was a harness, not the final architecture.

### Phase 7

Phase 7 tested compressed memory as an attention alternative.

Important files:

- `src/project_x/experiments/compressed_memory.py`
- `src/project_x/experiments/tasks.py`
- `src/project_x/experiments/hopfield_lens.py`
- `docs/artifacts/PHASE_7_HOPFIELD_LENS.md`
- `docs/past_work/phases/phase_7_hopfield_lens_bulletproof.md`

Phase 7 produced the Hopfield-lens interpretation and several synthetic retrieval tasks:

- long-range copy
- key noise
- multi-key retrieval

It also left a current test fragility:

```text
PYTHONPATH=src pytest -q
fails because compressed_memory.py imports src.project_x...
```

This should be fixed early in Phase 9 or in a preflight cleanup.

### Phase 8

Phase 8 built the HDC memory layer.

Important files:

- `src/project_x/experiments/hdc_substrate.py`
- `src/project_x/experiments/hdc_capacity.py`
- `src/project_x/experiments/hdc_compose.py`
- `src/project_x/experiments/hdc_continual.py`
- `src/project_x/experiments/hdc_conversation_demo.py`
- `src/project_x/experiments/hdc_snn_bridge.py`
- `src/project_x/experiments/hdc_vs_naive_comparison.py`
- `docs/artifacts/PHASE_8_HDC_ORGANIC_MEMORY.md`
- `docs/artifacts/PHASE_8_HOSTILE_REVIEW.md`
- `docs/artifacts/SHRINE_COUNCIL_PHASE_8.md`
- `docs/artifacts/T4_capacity_curve.png`
- `docs/artifacts/T4_dscaling_curves.png`
- `docs/artifacts/T4_cliff_vs_D.png`
- `docs/artifacts/T4_bit_accuracy_curve.png`

What Phase 8 proved:

- bipolar HDC primitives work
- bind/unbind are self-inverse for bipolar vectors
- direct binding writes fit a D-dimensional accumulator
- within-capacity cleanup can recover random values exactly
- capacity cliff appears beyond the predicted bound
- increasing D moves the cliff right
- append-only retention works within capacity
- synthetic turn-ID to utterance-symbol memory works at D=50k for 1000 turns

What Phase 8 did not prove:

- semantic text memory
- paraphrase retrieval
- contradiction handling
- autonomous relevance selection
- local generator
- tool use
- self-modification
- SNN semantic encoding

Correct framing:

```text
Phase 8 built the memory spine candidate.
Phase 9 must prove the spine carries real language evidence.
```

---

## 2. Council Integration

### G - Hardware

Verdict: mixed stack.

Use llama.cpp/GGUF for local generation. Use Python/PyTorch for reference HDC and embeddings. Add Triton only after profiling shows the semantic HDC path works and cleanup dominates.

### A - Encoder

Verdict: pretrained small embedder first.

Use BGE-small-en-v1.5 or MiniLM as the first semantic encoder, then project to bipolar HDC. SNN encoding remains a later substrate branch.

### C - Controller

Verdict: deterministic state machine with structured model proposals.

The controller owns state transitions, validation, memory write/read policy, and action gates. The LLM proposes; the controller decides.

### B - Generator

Verdict: local quantized 7B-8B LLM behind a swappable interface.

Use Qwen2.5-7B-Instruct or a locally available newer 7B/8B GGUF. Do not train generation from scratch.

### D - Memory Dynamics

Verdict: sparse writes, provenance, and replay consolidation.

Do not implement forgetting as deletion first. Implement importance, metadata, replay queues, and source-cited summaries.

### E - Tool Use

Verdict: schema-first action ledger.

Every tool call becomes a structured event with reason, args, raw output path, result summary, status, diagnosis, and memory bindings.

### F - Self-Modification

Verdict: staged sandbox-and-replace loop.

No live self-editing. Proposal, patch, benchmark, compare, accept/reject, record.

### H - Beyond Human Cap

Verdict: branch-and-verify cognition.

No-cap architecture means external memory, parallel branches, tool-augmented working memory, replay, self-benchmarking, and hardware-aware acceleration. It does not mean unmeasured claims.

---

## 3. Target Architecture

### Runtime Components

```text
raphael/
  controller.py
  generator_client.py
  encoder.py
  hdc_memory.py
  provenance_store.py
  tool_runtime.py
  replay.py
  benchmarks/
  artifacts/
```

This can initially live under `src/project_x/experiments/semantic_memory_agent.py` before graduating to a package module.

### Data Flow

```text
turn starts
  -> controller records input
  -> encoder embeds input
  -> projection maps embedding to HDC vector
  -> controller decides read/write
  -> HDC retrieves candidate memories
  -> provenance store resolves source turns
  -> generator receives evidence packet
  -> generator replies or proposes tool call
  -> controller validates
  -> tool runtime executes if allowed
  -> result stored in provenance + HDC
  -> result.json records metrics
```

### Memory Tiers

```text
Tier 0: prompt context
Tier 1: controller state
Tier 2: HDC episodic accumulator
Tier 3: SQLite/JSONL provenance store
Tier 4: consolidated summaries/facts
Tier 5: cold logs/archive
```

### Hard Invariants

- HDC accumulator is never the only source of truth.
- Every retrieved claim has source turn IDs.
- Every tool action has a structured event.
- Every benchmark writes result JSON.
- No self-improvement patch merges without before/after results.
- VRAM never exceeds 13.9 GB.
- `--mode test` completes in <=180 seconds.

---

## 4. Phase 9 - Semantic HDC Memory Agent

**Theme:** Replace random atoms with real text embeddings and put HDC retrieval inside a minimal chat loop.

**Primary question:** Can HDC memory retrieve useful evidence from real text conversations under the 5070 Ti hardware cap?

### Build

- `src/project_x/experiments/semantic_hdc_memory.py`
- `src/project_x/experiments/semantic_memory_agent.py`
- `src/project_x/experiments/semantic_memory_dataset.py`
- `src/project_x/experiments/generator_client.py`
- `tests/test_semantic_hdc_memory.py`

### Capabilities

- encode real text turns
- project embeddings to bipolar HDC
- store source text/provenance
- retrieve by exact turn ID
- retrieve by semantic query
- produce evidence-conditioned answer through mock or local generator
- record hardware metrics

### Exit Criteria

- exact turn lookup >=95% at 1000 turns
- semantic top-5 recall >=80% on >=200 labeled queries
- false positive rate <=10% on absent-answer queries
- 100% of answered retrievals include source turn IDs
- result JSONs under `gpt-codex/runs/phase9_*`
- test mode <=180 seconds
- `PYTHONPATH=src pytest -q` passes

### Hardware Budget

- Embedder: BGE-small or MiniLM, CPU or small GPU batches.
- HDC: CPU/PyTorch reference, D in {10k, 50k, 100k}.
- Generator: mock for tests; optional local GGUF for full demo.
- VRAM: <13.9 GB.
- RAM: avoid loading large datasets; generate synthetic-real conversations on the fly.

---

## 5. Phase 10 - Memory Dynamics

**Theme:** Make memory selective, durable, and less noisy.

### Build

- importance gating
- write policy
- namespace accumulators
- retrieval confidence calibration
- absent-answer classifier
- contradiction records

### Exit Criteria

- sparse-write policy reduces false positives vs write-all baseline
- no more than 2 pp drop in exact recall
- contradiction benchmark preserves both sides and marks supersession
- metadata store exports audit trail
- result JSON includes write counts, retrieval counts, and source coverage

### Hardware Budget

CPU-first. GPU not required except optional batched embedding.

---

## 6. Phase 11 - Tool-Using Raphael Loop

**Theme:** Add schema-first tool calls and durable action ledger.

### Build

- tool registry
- tool schema validator
- action ledger
- read/search/file/test tools
- tool output memory binding
- tool-failure diagnosis policy

### Exit Criteria

- agent can answer memory questions
- agent can run a harmless local command
- agent can read a file and cite path
- agent can run tests and store result
- failed command triggers diagnosis before retry
- all actions recorded as structured events

### Hardware Budget

Minimal. Keep generator local 7B optional.

---

## 7. Phase 12 - Sandbox Self-Improvement Harness

**Theme:** Let the system propose improvements only under benchmark gates.

### Build

- proposal schema
- patch sandbox
- benchmark runner
- accept/reject rule evaluator
- rollback record
- self-improvement result JSON

### Exit Criteria

- at least 3 proposed patches
- at least 1 accepted improvement
- accepted improvement beats baseline on predeclared metric
- rejected proposals explain failure
- no mutation of evaluator during candidate run

### Hardware Budget

CPU-first. GPU only if benchmark requires it.

---

## 8. Phase 13 - Branch-And-Rank Cognition

**Theme:** Make "council technique" an internal runtime primitive.

### Build

- K-plan generator
- evidence retrieval per branch
- critic branch
- ranker
- consensus summary
- branch logs

### Exit Criteria

- best-of-K improves benchmark success over single plan
- branch logs are inspectable
- critic catches at least 50% of seeded plan errors
- no unbounded branch explosion

### Hardware Budget

Sequential by default. Parallel optional within RAM/VRAM budgets.

---

## 9. Phase 14 - Hard General Benchmarks

**Theme:** Stop self-evaluating on easy internal tests.

### Build

- no-engine chess state/tactic pack
- hidden-rule local games
- Terminal-Bench-style reduced tasks
- browser/research source-discipline tasks
- local SWE-style issue set

### Exit Criteria

- each benchmark has machine-readable result file
- state fidelity measured
- no internet/tools mode separated from tool-agent mode
- failures produce next-action queue

### Hardware Budget

Mostly CPU. Local LLM optional for tool-agent mode.

---

## 10. Phase 15 - SNN/HDC/Triton Convergence

**Theme:** Bring Project Lain substrate back into the agent stack.

### Build

- SNN encoder calibration
- spike-to-HDC projection
- Triton HDC cleanup kernels
- Neural CPU controller experiments
- kernel profiling and correctness tests

### Exit Criteria

- SNN encoder cross-input cosine near zero on benchmark set
- Triton cleanup beats CPU/PyTorch baseline by predeclared factor
- Neural CPU opcode demo can read a controlled file/memory surface
- no VRAM cap violations

### Hardware Budget

GPU-heavy. Use watchdog and small-first scaling.

---

## 11. Phase 16+ - Raphael Proper

**Theme:** Always-on local chattable agent with actions, memory, replay, and measured improvement.

### Required Properties

- local chat loop
- persistent memory
- source-cited recall
- tool actions
- project-aware coding assistance
- replay consolidation
- benchmarked self-improvement
- branch-and-rank planning
- SNN/HDC acceleration path

### Exit Criteria

- 10k-turn memory demo with source-cited recall
- tool-use task suite green
- local code-edit benchmark green
- memory replay improves held-out recall
- self-improvement loop accepts at least one patch per cycle without regression
- hardware budgets stable for long run

---

## 12. Immediate Phase 9 Decision

Pick this:

```text
Phase 9 = Semantic HDC Memory Agent
```

Not Triton first.

Not SNN encoder first.

Not self-modification first.

Not pure local LLM wrapper.

The first missing proof is semantic memory in a chat loop. Everything else depends on it.

---

## 13. Important Instruction Files

Project X:

- `docs/A_TO_Z_PLAN.md`
- `docs/DO_THIS_NEXT.md`
- `docs/artifacts/PHASE_8_HDC_ORGANIC_MEMORY.md`
- `docs/artifacts/PHASE_8_HOSTILE_REVIEW.md`
- `docs/artifacts/ROADMAP_TO_RAPHAEL.md`
- `src/project_x/experiments/hdc_substrate.py`

Codex/global:

- `/home/nira/.codex/AGENTS.md`
- `/home/nira/.codex/memories/`
- `/home/nira/.codex/skills/`

Claude/Raphael surfaces:

- `/home/nira/.claude/CLAUDE.md`
- `/home/nira/.claude/commands/shrine-council.md` (DELETED 2026-05-09)

Project Lain:

- `/mnt/c/Users/nira/Documents/Research/Lain/MANIFESTO.md`
- `/mnt/c/Users/nira/Documents/Research/Lain/TRAINING_RULES.md`
- `/mnt/c/Users/nira/Documents/Research/Lain/CLAUDE.md`
- `/mnt/c/Users/nira/Documents/Research/Lain/project_synapse/kernels.py`
- `/mnt/c/Users/nira/Documents/Research/Lain/project_synapse/cpu.py`
- `/mnt/c/Users/nira/Documents/Research/Lain/project_synapse/isa.py`
- `/mnt/c/Users/nira/Documents/Research/Lain/project_synapse/test_turing_controller.py`

WIRED reference:

- `/mnt/c/Users/nira/Documents/Research/WIRED/WIRED-BRAIN-V3/`

---

## 14. Source Links Used

- NVIDIA RTX 5070 family: https://www.nvidia.com/en-au/geforce/graphics-cards/50-series/rtx-5070-family/
- PyTorch local install/CUDA selector: https://pytorch.org/get-started/locally/
- llama.cpp GGUF usage: https://huggingface.co/docs/hub/gguf-llamacpp
- BGE docs: https://bge-model.com/bge/bge_v1_v1.5.html
- MiniLM model card: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
- Qwen2.5-7B-Instruct: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct
- Mistral 7B model card: https://docs.mistral.ai/models/model-cards/mistral-7b-0-3
- ReAct: https://arxiv.org/abs/2210.03629
- Toolformer: https://arxiv.org/abs/2302.04761
- MCP tools spec: https://modelcontextprotocol.io/specification/2024-11-05/server/tools
- OpenAI function calling help: https://help.openai.com/en/articles/8555517
- OpenAI Structured Outputs: https://openai.com/index/introducing-structured-outputs-in-the-api/
- CLS update preprint: https://web.stanford.edu/~jlmcc/papers/KumaranHassabisMcClelland16FinalMS.pdf
- Terminal-Bench: https://www.tbench.ai/
- Codex system-card addendum: https://openai.com/index/o3-o4-mini-codex-system-card-addendum/

---

## 15. Final Roadmap Verdict

The main system starts now.

Phase 9 should build a real semantic memory-agent loop, not another isolated memory plot.

The strongest design is:

```text
local quantized generator
+ pretrained semantic encoder
+ HDC associative memory
+ deterministic controller
+ provenance store
+ schema-first tools
+ replay consolidation
+ benchmarked self-improvement
+ later SNN/Triton convergence
```

This is the shortest path to a local Raphael that can chat, remember, act, and eventually improve itself without faking progress.

