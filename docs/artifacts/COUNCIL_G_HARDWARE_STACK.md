# Council G - Hardware Stack

**Date:** 2026-05-09  
**Mode:** SINGLE-BRAIN. advisor is not yet wired to this harness in this Codex harness. No puppet expert simulation.  
**Question:** What compute stack should Project X use on lain's RTX 5070 Ti + i9 + WSL machine so Phase 9+ can reach a chattable, tool-using Raphael without blowing the hardware envelope?

---

## 0. Ground Truth

The machine constraint is not decorative.

- GPU: RTX 5070 Ti, 16 GB GDDR7 physically present, treated as **13.9 GB usable hard cap**.
- CPU: i9 class, assume 24-32 threads.
- RAM: 7.8 GiB available in WSL context, tight enough that large data loaders and full offload buffers can dominate.
- OS: Windows + WSL Linux.
- CUDA: 12.8 target.
- Storage: NVMe, useful for logs, GGUF models, memory journals, and replay corpora.

Current Project X Phase 8 ran HDC in NumPy CPU mode. That was correct for proof, but not enough for online chat with large cleanup dictionaries or D >= 1M.

---

## 1. Evidence Pack

Fetched current sources:

- NVIDIA 5070 family page: RTX 5070 Ti has 8960 CUDA cores, Blackwell architecture, 16 GB GDDR7, 256-bit memory interface.
- PyTorch install page: current stable selector exposes CUDA 12.8 as a Linux compute platform option.
- Hugging Face llama.cpp GGUF guide: llama.cpp can run GGUF models and can be built with `-DGGML_CUDA=ON`.
- Hugging Face Qwen2.5-7B-Instruct card: 7.61B parameters, GQA, long context, JSON/structured output improvements, quantizations available for llama.cpp/Ollama/LM Studio-compatible apps.
- Mistral model card: open Mistral 7B line has 32k context and Apache 2.0 weights, but the older v0.3 card marks replacement by Ministral 3 8B.
- Project local code: Phase 8 cleanup currently casts `atom_set` to int32 per query and uses CPU matrix multiplication.

Relevant local files:

- `src/project_x/experiments/hdc_substrate.py`
- `src/project_x/experiments/hdc_capacity.py`
- `src/project_x/experiments/hdc_conversation_demo.py`
- `docs/artifacts/PHASE_8_HOSTILE_REVIEW.md`
- `/mnt/c/Users/nira/Documents/Research/Lain/TRAINING_RULES.md`
- `/mnt/c/Users/nira/Documents/Research/Lain/project_synapse/kernels.py`
- `/mnt/c/Users/nira/Documents/Research/WIRED/WIRED-BRAIN-V3/`

---

## 2. Seats

Because advisor is not yet wired to this harness, the seats are evidence lenses, not impersonated people.

| Seat | Lens | Unique concern |
|---|---|---|
| 1 | GPU kernel engineer | Can HDC/SNN cleanup be made fast enough without hand-writing all CUDA? |
| 2 | Local LLM inference engineer | What model serving path works reliably under 13.9 GB VRAM? |
| 3 | Systems reliability engineer | What stack avoids WSL RAM crashes and opaque state corruption? |
| 4 | Research velocity engineer | What gets measurable Phase 9 evidence fastest? |
| 5 | Adjacent: game-engine/runtime engineer | How should an always-on agent loop handle latency, state, hot reload, and IO? |

---

## 3. Candidate Scores

Scale: 0-420. Mean intentionally below 390. Spread >= 40. At least one defended 400+ idea.

| Candidate | Score | Verdict |
|---|---:|---|
| Mixed stack: llama.cpp for generator, PyTorch first then Triton for HDC/SNN, SQLite/JSONL for provenance | **408** | Winner |
| Pure PyTorch/NumPy | 336 | Good for research, too slow for online cleanup at scale |
| Triton everywhere | 376 | Powerful but premature before semantics are proven |
| Rust+wgpu from WIRED line | 348 | Excellent long-term runtime, slower Phase 9 velocity |
| llama.cpp only plus vector DB | 362 | Gets chat fast but abandons Project X substrate advantage |

Mean score: 366.0. Spread: 72.

---

## 4. Deliberation

The hardware stack must serve two different workloads.

First workload: local language generation. This wants stable quantized inference, streaming tokens, OpenAI-compatible server shape, and predictable VRAM. llama.cpp is the strongest default because GGUF is mature, CUDA builds are documented, model quantizations are widely available, and server mode can act like a local API.

Second workload: HDC/SNN memory. This wants fast bipolar dot products, add/bind/unbind/sign, batching, and eventually sparse spiking kernels. Phase 8 NumPy is enough for D=10k-100k offline sweeps. It is not the right long-term path for online cleanup over large vocabularies.

The theoretical best stack is not the first implementation stack. Triton kernels should be introduced after a PyTorch reference establishes semantic value. If Phase 9 uses real text and fails semantically, a perfect Triton cleanup kernel accelerates the wrong thing. If Phase 9 succeeds, the bottleneck will be obvious and Triton becomes high leverage.

Rust+wgpu should stay as a sibling runtime reference, not become Phase 9's main path. WIRED-BRAIN-V3 contributes useful operator patterns: replay logs, action policies, service boundaries, and lower-level runtime discipline. But rewriting Project X into Rust now would delay the semantic bridge.

The most dangerous hardware error is trying to run too much at once: local 13B LLM, embedder, HDC GPU buffers, SNN simulator, browser, and Python harness in a 7.8 GiB WSL RAM envelope. Phase 9 must use process-level budgets and a watchdog.

---

## 5. Defended 400+ Idea

**Winner: mixed stack with explicit budget partitions.**

Recommended runtime partition:

- `llama.cpp` or compatible GGUF server for the generator/controller surface.
- `sentence-transformers`/Transformers embedder first on CPU or small GPU batches.
- PyTorch reference implementation for HDC projection and cleanup.
- Triton kernels only after a profiling artifact shows cleanup dominates.
- SQLite + JSONL for metadata/provenance/action logs.
- `nvidia-smi` sampler retained from `util_harness.py`.
- Hard per-process VRAM/RAM budget tracked in every result JSON.

This path preserves research velocity and gives a straight line to optimization.

---

## 6. Architectural Consequences

Phase 9 should not begin with Triton.

Phase 9 should begin with:

1. A real text dataset.
2. A small embedder.
3. HDC projection.
4. Retrieval benchmark.
5. Local generator interface stub or llama.cpp server adapter.
6. Exact hardware accounting.

Triton becomes Phase 10 or 11 when there is a measured CPU cleanup bottleneck against a semantic workload.

The LLM should be an interchangeable process boundary, not imported into the same Python memory space. This protects WSL RAM and makes model swaps cheap.

---

## 7. Exit Criteria For Hardware Stack

The hardware decision is considered validated when:

- A local 7B-class generator runs through an OpenAI-compatible local endpoint or equivalent CLI bridge.
- A small embedder runs with batch size tuned to avoid RAM spikes.
- HDC retrieval benchmark records wall time, RAM, and VRAM.
- GPU memory never exceeds 13.9 GB.
- Phase 9 test mode completes in <= 180 seconds.
- Full mode has a published ETA and checkpointing.

---

## 8. Risks

- Blackwell/CUDA wheel mismatch can break PyTorch/Triton installs.
- llama.cpp CUDA builds may need local compile flags.
- 13B Q4 may fit but crowd out embedder/HDC buffers and KV cache.
- Large context LLM settings can silently consume VRAM through KV cache.
- CPU RAM can become the actual bottleneck before VRAM.

Mitigation:

- Default to 7B Q4/Q5 first.
- Keep context window conservative.
- Run model, embedder, and HDC as separable processes.
- Record memory samples for every benchmark.

---

## 9. Verdict

Use a **mixed stack**.

Do not choose purity. Project X needs the local LLM ecosystem for the chat/action surface and custom kernels for the novel memory/substrate path. The winning stack is:

```text
llama.cpp / GGUF server
    + Python controller
    + small sentence embedder
    + PyTorch HDC reference
    + Triton HDC/SNN kernels after profiling
    + SQLite/JSONL durable memory metadata
```

This is the fastest route to a chattable Raphael that still preserves the no-cap substrate research line.

---

## 10. Implementation Pressure Test

### Question 1: What breaks first?

The first likely bottleneck is not raw CUDA compute.

It is memory pressure from running too many subsystems in one process.

Risk stack:

1. Local LLM loads with large context.
2. Python imports Transformers.
3. Embedder loads model weights.
4. HDC atom matrices allocate in RAM.
5. Result aggregation holds too much data.
6. WSL starts paging.
7. Benchmark latency becomes meaningless.

Mitigation:

- keep local LLM out of Python process
- run embedder in small batches
- preallocate HDC arrays
- stream result rows
- write JSONL rather than one giant in-memory object

### Question 2: What should be measured before optimization?

Measure:

- wall seconds per 100 writes
- wall seconds per 100 queries
- cleanup dictionary size
- D
- RAM before/after
- VRAM before/after
- embedder batch time
- generator latency if enabled

Do not optimize a guessed bottleneck.

### Question 3: When is Triton justified?

Triton is justified when:

- semantic retrieval is useful
- cleanup is the dominant time cost
- PyTorch batching still misses target latency
- the operation is stable enough to kernelize
- correctness can be checked against NumPy/PyTorch reference

Triton is not justified when:

- recall metrics are bad
- encoder is still changing daily
- the bottleneck is model loading
- the bottleneck is JSON serialization
- the bottleneck is the generator

### Question 4: What should stay CPU?

Keep these CPU-first:

- metadata store
- JSONL logs
- source text
- exact provenance lookup
- small test-mode benchmark
- result aggregation
- controller logic

GPU should do dense vector math, not bookkeeping.

### Question 5: What should be a separate process?

Separate:

- local LLM server
- long benchmark runner
- optional browser/tool runtime

Keep together:

- controller
- memory reference implementation
- provenance access

The process boundary protects RAM and makes failures legible.

### Question 6: What are the hardware gates per phase?

Phase 9:

- CPU-first semantic retrieval
- optional local LLM
- no Triton requirement

Phase 10:

- retrieval profiling
- no custom kernel unless bottleneck proven

Phase 11:

- tool loop latency
- generator endpoint stability

Phase 12:

- benchmark isolation
- sandbox temp dirs

Phase 15:

- Triton/SNN GPU path
- explicit VRAM watchdog

### Question 7: What is forbidden?

Forbidden:

- loading multiple large local LLMs at once
- claiming 13B support without VRAM logs
- calling CPU NumPy D=1M cleanup "online capable"
- hiding context size in generator benchmarks
- ignoring WSL RAM pressure

### Final hardware invariant

If the run cannot produce a hardware record, the run cannot support a hardware claim.
