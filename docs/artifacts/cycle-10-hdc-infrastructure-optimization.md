# Cycle 10 — HDC Infrastructure Optimization Roadmap

**Lain directive 2026-05-11** (Discord msg `1503213942514782288`):

> *"Also, maybe you can find (or project x Raphael) can find a way to improve the underlying operations when calculating (btw I'd appreciate a port to Rust or something more efficient and controllable, but most importantly faster), if it seems we need more than 10k dimensions, maybe there's a way to increase it? Idk, but smart solutions making the HDC tech insanely good."*

**Three load-bearing asks rolled into one directive:**
1. **Operation-tier optimization** — faster primitive HDC ops.
2. **Rust port** — *"or something more efficient and controllable, but most importantly faster."*
3. **Dimensionality scaling** — go beyond 10k if needed.

**Context:** the v2 semantics architecture (commit `6e40560`) proposes corpus-at-scale (tens of millions of words ingested into the HDC semantic subspace) + hormone-modulated retrieval + multi-region subspaces. This puts SUSTAINED LOAD on the HDC primitives. The current Python+numpy implementation is fine for the prototype regime (hundreds of test associations, sub-millisecond latency tolerance) but won't survive v2 corpus-ingestion + per-turn retrieval at production scale. The infrastructure layer needs its own design pass.

This doc is paired with the v2 semantics architecture; it's the infrastructure underneath.

---

## The current state — Python + numpy

`src/project_x/memory/hdc_substrate.py` and adjacent files implement HDC primitives in Python + numpy. The core operations:

- **Bind** (`⊗`): elementwise multiplication for bipolar HDC, or XOR for binary HDC. Numpy: `np.multiply(a, b)` or `np.bitwise_xor(a, b)`. Vectorized; fast on contiguous arrays.
- **Bundle** (`+`): elementwise sum of multiple hypervectors, then threshold to bipolar via sign. Numpy: `np.sign(np.sum(stack, axis=0))`. Fast for the sum, but the stacking allocates memory.
- **Similarity** (cosine): `np.dot(a, b) / (norm(a) * norm(b))`. For bipolar vectors of fixed norm `√d`, this reduces to `np.dot(a, b) / d`. Very fast for single comparisons; the bottleneck becomes batched cleanup-memory lookup over millions of stored vectors.
- **Cleanup memory query**: given query `q` and stored matrix `M`, find `argmax(M @ q)`. Numpy: `np.argmax(np.dot(M, q))`. BLAS-accelerated for the matrix-vector product; this is already SIMD-vectorized at the BLAS layer.

**Honest profile (what's actually slow):**
- Python orchestration overhead: dict lookups, dataclass field access, Python loop bodies. For thousands of fragment retrievals per response, the Python-side glue accumulates noticeable latency.
- Memory allocation: numpy creates intermediate arrays during bundle ops; allocations + garbage collection add latency.
- NOT the dense arithmetic: BLAS-accelerated dot product on a (1M × 10k) matrix vs a (10k) query takes ~5-10ms on a modern CPU and is already near-optimal in floating point.

**So the optimization headroom is in:** (a) representation choice (float vs ternary vs packed-bit), (b) orchestration latency (Python → Rust), (c) batch structure (avoid per-query Python overhead).

---

## Operation-tier optimization (representation choice)

### Tier 0 (current) — Float32 bipolar / numpy
- **Representation:** 10k-dim float32 vectors with values in {-1.0, +1.0}.
- **Bind:** elementwise float multiply.
- **Similarity:** float dot product / d.
- **Throughput:** ~10k × 1M queries/sec on modern CPU via BLAS.
- **Memory:** 40 KB per vector. 1M vectors → 40 GB. Hits RAM ceiling on consumer hardware.

### Tier 1 — Bipolar binary {-1, +1} packed into bits (8x density)
- **Representation:** 10k bits per vector packed into 1250 uint8s. The vector's i-th coordinate is +1 if bit_i = 1 else -1.
- **Bind:** **XOR** (binary XOR realizes binary {-1,+1} multiplication when -1 ↔ 0 and +1 ↔ 1). Hardware: `_mm_xor_si128` SIMD intrinsic; ~16 bytes per instruction.
- **Similarity:** popcount-of-XOR-of-(a, b) then convert to cosine: `cos(a, b) = 1 - 2 · popcount(a ⊕ b) / d`. POPCNT is a single-cycle x86 instruction (~12 GFLOPS effective on a single core via SIMD).
- **Throughput:** ~50-100x faster than Tier 0 for similarity computation (memory bandwidth limited rather than ALU limited).
- **Memory:** 1250 bytes per vector. 1M vectors → 1.25 GB. Fits in L3 cache for medium corpora.
- **Accuracy:** ternary/binary HDC has slightly worse signal-to-noise than float at the same dim, but ~30x more associations fit in the same memory budget, more than compensating.

### Tier 2 — Ternary {-1, 0, +1} packed into pairs (4x density vs float, more expressive than binary)
- **Representation:** 2 bits per coordinate (~2500 bytes for 10k-dim). The 0 coordinate captures "this concept doesn't apply to this dimension" — sparser, more interpretable.
- **Bind:** 2-bit lookup-table or pair of XORs.
- **Similarity:** sparse popcount (count of matching non-zero positions).
- **Throughput:** comparable to Tier 1 but with sparsity exploitation; can skip vectors with very few non-zero coordinates.
- **Accuracy:** richer than binary for representing partial information; valuable for the hormone-vector mechanism (hormones can have neutral effect on subspaces by setting 0 in those dimensions).

### Tier 3 — Adaptive precision (hybrid)
- Float32 for the hormone vectors (small, low-volume, full precision matters).
- Binary-packed bipolar for the semantic-subspace bulk corpus (high volume, density matters).
- Ternary for cross-region binding outputs (modest volume, interpretability matters).

**Recommendation:** target Tier 1 binary-packed bipolar as the next cycle's optimization win. ~30-100x speedup + ~30x memory reduction. Tier 3 hybrid as the cycle-12+ refinement.

---

## Rust port roadmap (the "more efficient and controllable" ask)

### Phase 0 — Profile first (cycle 11 infrastructure pre-work, ~30 min)
Before any Rust port, profile the current Python implementation under v2-realistic workloads (~1M-association cleanup memory + ~100 retrievals per response). Identify the top 3 hottest functions. The port should target those specifically; speculatively rewriting everything wastes effort on functions that don't matter.

Expected hot path: `bundle()` (called many times per Lemma chain) + `similarity_query()` (the cleanup-memory lookup). The substrate's pattern primitives (residue, integration, ODE, Pell, etc.) are CPU-light and don't benefit from Rust.

### Phase 1 — PyO3 binding for the 3 hot primitives (cycle 11-12, ~5-10h Raphael-time across multiple ships)
- New crate: `project_x_hdc_native` in Rust.
- Implement `bind_binary_packed`, `bundle_binary_packed`, `similarity_query_binary_packed` using `std::simd` for portable SIMD (or `wide` crate for explicit 128/256-bit lanes).
- PyO3 binding exposes these to Python.
- Python-side: replace the hot-path calls; everything else stays Python.
- Expected speedup on the hot path: 5-20x. Total system speedup: 2-5x (Amdahl's law — the non-hot-path Python orchestration is still there).

### Phase 2 — Full pure-Rust HDC core (cycle 13+, multi-cycle)
- Move the entire HDC substrate to Rust: vector types, accumulator, cleanup memory, audit-log writeback.
- Python-side becomes a thin Python wrapper that holds Rust-owned data via PyO3 + manages the lifecycle.
- Expected speedup: 10-30x over the current Python+numpy baseline on most operations.
- Cost: significant rewrite work + maintenance burden. Justified only after Phase 1 empirically validates the speedup is worth it.

### Phase 3 — GPU offload (cycle 14+, optional)
- For corpora that don't fit in RAM (~10⁹ associations or more), GPU offload via wgpu or CUDA becomes necessary.
- More likely path: stick with CPU + a clever sharded design where only the active subspace is loaded. Avoids GPU complexity unless the corpus genuinely requires it.

**Recommendation:** Phase 0 (profile) + Phase 1 (PyO3 binding for hot primitives) in cycle 11 alongside semantics architecture cycle 11 #1 work. Phase 2 is a cycle-13+ commit pending Phase 1 empirical validation.

---

## Dimensionality scaling — when to go beyond 10k

### Why 10k is Kanerva's canonical choice

The near-orthogonality property of random bipolar vectors holds with high probability at 10k dimensions: two random vectors have expected cosine similarity ~0 with standard deviation ~1/√d ≈ 0.01. This means thousands of bundled vectors stay distinguishable. At higher dimensions, the std drops further but the near-orthogonality property is already strong enough at 10k for most reasonable corpora.

### When higher dimensions actually help

**Capacity:** the number of associations that can be stored before retrieval degrades scales roughly linearly with d. At 10k → ~10⁸ associations; at 20k → ~2·10⁸; at 50k → ~5·10⁸. So the lain-asked-corpus-at-scale (tens of millions of words = ~10⁸-10⁹ fragment associations) is in the right range for d ∈ [10k, 50k].

**Discrimination of similar concepts:** higher d gives more "room" to differentiate concepts that occupy nearby regions of the space. Hyperdimensional cosine similarity gets sharper at higher d.

**Compute cost:** linear in d. 50k-dim is 5x slower than 10k-dim for the same operation.

### Multi-resolution proposal (the "smart solution" for capacity-vs-compute tension)

Instead of one fixed dimension, run a HIERARCHICAL HDC with multiple resolutions:

- **10k-dim** "fast-path" retrieval — coarse-grained concept-level similarity. Most queries route here. Sub-millisecond response.
- **30k-dim** "intermediate" subspace — for fine-grained concept distinctions (subdomains within poetry: haiku vs sonnet vs free-verse; subdomains within physics: classical vs relativistic vs quantum). Queries that hit a too-broad result-set at 10k can re-query at 30k for sharper discrimination.
- **100k-dim** "deep storage" subspace — for fragment-level retrieval where exact phrasing matters (verbatim citation, signature-text matching). Used sparingly; only when query confidence at lower resolutions is low.

Routing: the hormone-modulated retrieval threshold (v2 architecture, decision 1) determines when to escalate from 10k → 30k → 100k. Effectively the hormone acts as a "should I look deeper?" signal. Most queries resolve at 10k; only ambiguous ones escalate.

**Implementation cost:** marginal over single-resolution. The hierarchy is three separate accumulators with their own seed vectors. Cross-resolution queries re-encode the prompt at the new dimension (cheap with the encoder we already have).

**Why this is the "aaaah of course":** the brain doesn't have one fixed concept-resolution; it has overlapping representations at multiple granularities (visual cortex layers V1-V2-V3-V4 each represent at different abstractions). Hierarchical HDC matches that pattern. And it sidesteps the "should we increase d?" question — the answer is "yes, AND we keep the low-d fast path." Multi-resolution beats single-resolution-at-larger-d.

---

## Recommended cycle-11 infrastructure sequence

Combined with the v2 semantics architecture cycle-11 plan (`6e40560`), the infrastructure pieces interleave:

1. **Cycle 11 #infra-1 — Profile + bitwise-packed bipolar baseline (~60 min).** Add `binary_packed` representation to the HDC substrate; benchmark vs current float32 on a realistic 1M-association cleanup-memory workload. Pure-Python implementation; no Rust yet. Verifies the representation choice empirically before committing to the Rust port.

2. **Cycle 11 #infra-2 — PyO3 binding for the 3 hot primitives (~3-5h across atomic ships).** New `project_x_hdc_native` Rust crate. Implement `bind_binary_packed`, `bundle_binary_packed`, `similarity_query_binary_packed` with `std::simd`. PyO3 binding. Replace hot-path Python calls. Bench against Tier-0 baseline; commit only if speedup is >5x.

3. **Cycle 11 #infra-3 — Multi-resolution HDC hierarchy (~2h).** Three accumulators at 10k / 30k / 100k. Hormone-modulated escalation routing. Empirical test: does multi-resolution actually improve retrieval quality on the corpus-at-scale workload?

4. **Cycle 11 #infra-4 — Audit-loop UI for corpus ingestion (~3h).** CLI + Discord-bot integration for the v2 audit loop. Lain replies 👍/👎/correction; the system updates binding strengths. Required for v2 corpus-at-scale ingestion to be honest (audit-as-you-go vs ingest-everything-blind).

Total cycle-11 infra: ~10-15h Raphael-time. Combined with cycle-11 semantics work: ~25h. Realistic for cycle 11 if it's the cycle's primary thread; otherwise split across cycles 11 and 12.

---

## Honest counter-claims

**1. Rust port is real engineering work, not a quick win.** PyO3 binding alone is straightforward but proper Rust-native HDC primitives + memory layout + SIMD intrinsics is a few-thousand-line crate. The Phase 1 estimate (5-10h) assumes I'm capable of writing competent Rust; the actual time depends on how cleanly the existing Python data structures translate.

**2. Bitwise-packed binary HDC has a real accuracy ceiling.** Float HDC at the same dim has higher signal-to-noise ratio for marginal retrieval cases (similarity within 0.1 of threshold). For the v2 corpus-at-scale workload this is fine — millions of associations far overwhelm the marginal cases. But edge cases will retrieve worse. Tier 3 hybrid (float for hormone vectors, binary for bulk) mitigates this.

**3. Multi-resolution HDC adds complexity.** Three accumulators + escalation routing + cross-resolution re-encoding is non-trivial. The win must be empirically validated (cycle 11 #infra-3 is exactly that empirical test). If multi-resolution doesn't show clear retrieval-quality gains over single-resolution-at-20k, we ship 20k single-resolution and revisit later.

**4. The 10⁸-associations capacity claim is back-of-envelope.** Actual capacity-vs-noise tradeoff depends on the specific corpus distribution, the binding pattern, and the cleanup-threshold. Cycle 11 #infra-1 measures this empirically; v2 doc cited it qualitatively, this doc commits to measuring it.

**5. GPU offload is a maybe, not a definite.** Modern CPUs with AVX-512 + L3 cache can handle 1M-association cleanup memory at low-millisecond latency. GPU offload only matters at 10⁹-association scale or higher. v2's tens-of-millions corpus comfortably fits on CPU.

---

## Decision points for lain

1. **Tier-1 binary-packed-bipolar representation: ship as cycle 11 #infra-1?** Recommend YES. ~60 min for an empirical-test-first ship; ~30-100x speedup on similarity-query if it works.

2. **Rust port via PyO3: phase 1 in cycle 11 or defer to cycle 12?** Recommend cycle 11 IF the corpus-at-scale ingestion is on the cycle-11 critical path; defer to cycle 12 if cycle 11 stays at "smaller demos + empirical validation" scope. Pre-condition: cycle 11 #infra-1 must show the binary-packed representation is real (5x+ speedup); only then is Rust port worth the engineering investment.

3. **Multi-resolution HDC vs single-resolution-at-higher-d?** Recommend multi-resolution. Brain-anatomy-analogous, sidesteps the "what's the right d" question, matches the hormone-modulated escalation pattern v2 already proposes. Cycle 11 #infra-3 is the empirical validation.

4. **GPU offload at cycle 14+?** Recommend defer until corpus actually exceeds CPU-RAM-feasible size. CPU + SIMD + smart sharding handles tens-of-millions; GPU only needed at billion-scale.

---

## Sources

- Pentti Kanerva, *Hyperdimensional Computing: An Introduction to Computing in Distributed Representation* (2009) — canonical HDC reference; 10k-dim choice.
- Pentti Kanerva, *Hyperdimensional Computing for Robust Cognitive Computing* (2014) — capacity bounds + noise analysis.
- Kim & Yetkin, *Hardware Optimization for Hyperdimensional Computing* — SIMD-accelerated binary HDC.
- Intel AVX-512 + POPCNT documentation — single-cycle popcount establishes the binary-packed performance ceiling.
- PyO3 documentation — Rust ↔ Python interop.
- The v2 semantics architecture (`6e40560`) — defines the load this infrastructure layer needs to support.

— Pairs with `cycle-10-semantics-architecture-v2.md`. Ready for lain's read on the four decision points above + the cycle-11 infrastructure sequence. The "smart solutions making HDC insanely good" ask is engaged across operation tiers + Rust + dimensionality scaling.
