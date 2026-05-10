# Idea Bank

Scoring uses `N/F/L`: novelty, feasibility, leverage. Each dimension is 1–5. Kill conditions are deliberately harsh.

Tiers (S / A / B / C) reflect ship-priority for the tiny-scale research gate. Tier blends raw N/F/L score with definition quality, falsifiability under the 180-second test budget, and signal independence from already-prioritized ideas.

Some scores below were revised from the original bank:

- #5 Memory Distillation Head: L 4 → 5. Many selector ideas (1, 4, 14, 28) likely benefit from this signal — without it they share a circular-supervision risk.
- #15 Memory-Byte Regularized Loss: L 4 → 5. Formalizes the project's headline metric (loss per memory byte) as part of the optimizer's objective rather than a post-hoc score.
- #7 Multi-Timescale Residual Memory: N 5 → 4, L 4 → 3. Description is vague; hierarchical-RNN and Transformer-XL priors give less novelty than originally scored.
- #18 Adaptive Local Window: F 3 → 2. Hypothesis falsification can use PyTorch masks (slow but correct); the speed claim that motivates the idea cannot be honestly evaluated without a Triton kernel.

## Implementation Stack Doctrine

The architecture is research-stage. Maximum control without diminishing returns means: stay in compiled, kernel-aware Python (not C/Rust/asm), drop into Triton for the hot path, reach for CUDA C++ only when Triton's expressivity actually runs out.

**Tie-breaker rule:** when the choice between two stack levels is genuinely ~50/50, prefer the lower level. Max efficiency is the standing preference; the higher level wins only when the efficiency gap is small *and* the design is still uncertain.

| Tier | Tool | When to use | Diminishing-returns line |
|---|---|---|---|
| 0 | Python harness, dataloader, eval, run-id plumbing | always | kernel work here is wasted |
| 1 | PyTorch eager + `torch.compile` | falsification harnesses where the design is still uncertain; auxiliary heads, loss terms, ergonomic surfaces | reach for Triton as soon as the design is committed *and* the kernel cost is non-trivial |
| 2 | Triton | every compute-path kernel by default once design is committed: attention variants, MoE / depth dispatch, fused VQ, Hopfield read/write, sink-aware attention, split-cache attention | ~70% of CUDA's perf at ~10% of the engineering cost — the standing target for any compute-path kernel |
| 3 | CUDA C++ | warp-specialization, TMA on Hopper, persistent kernels, ops Triton can't express | only at scaled runs with measurable kernel-bound profile, or when Triton expressivity runs out |
| — | C / Rust / Mojo / asm | not on path for training code | ecosystem too thin and autograd unsupported |
| — | JAX/XLA | alternative to PyTorch + Triton at the same level, not lower | a horizontal swap, not a step down |

Default posture: write the *falsification harness* in PyTorch, but commit to Triton early for any kernel on a compute path that will dominate runtime once the candidate proves out — don't carry unnecessary PyTorch overhead into a design that has already earned scaling. CUDA C++ is reserved for kernels Triton's expressivity cannot reach, not for routine optimization.

The per-idea Implementation stack notes below name the *standing target* — the kernel surface the candidate will eventually need. They do not push for Tritonization before a candidate has shown signal, but they do not pretend the kernel work is optional once it has.

## Tier Ranking

**Tier S — ship targets.** Highest combined leverage and falsifiability. All four are pure-PyTorch additions to the existing #1 harness; run first.
- #1 Dual-Rate Compressed Memory Attention (primary)
- #2 Surprise-Gated Writable Memory (backup)
- #5 Memory Distillation Head
- #15 Memory-Byte Regularized Loss

**Tier A — supporting / fallback.** Strong on their own; several are infra dependencies for Tier S. #27 sits at the Tier S/A boundary because the current long-association probe is underpowered and stronger probes likely unblock the existing harness; #21 is high Tier A pending Tier-S long-context signal.
- #27 Adversarial Long-Probe Curriculum (S/A boundary — probe upgrade likely on-path before more architecture)
- #21 VQ-Quantized KV Codebook (high A — promote to S only after #1 produces meaningful long-probe signal)
- #3 Latent-KV Plus Block Retriever
- #4 Recurrent Summary As Query Prior (vendor `mamba-ssm` dependency — verify reproducibility on this box before committing)
- #13 Two-Phase Sparse Warmup
- #16 Segment-Level MTP
- #22 Mixture-of-Depth Token Skipper
- #23 Fast-Weights Hopfield Memory Head
- #25 Learned Attention Sinks With Eviction
- #26 Key-Only Retrieval Bypass
- #28 Self-Distilled Cache Pruning
- #30 Skip-Stream Bidirectional Summary (vendor `mamba-ssm` dependency — same caveat as #4)

**Tier B — situational.** Run only if a Tier S/A idea exposes them as on-path.
- #6 Causal Block Autoencoder KV (overlaps #1)
- #14 Top-k With Diversity Penalty
- #17 Persistent Scratchpad Tokens
- #24 Drafter-Coupled Cache Co-Train (inference / serving optimization, not a base-architecture gate)
- #29 Codebook-Anchored Persistent Memory

**Tier C — skip unless re-scoped.** Wrong scale, kernel-hostile, synthetic-only, or non-architectural.
- #7 Multi-Timescale Residual Memory
- #8 Birkhoff Residual Mixer
- #9 Budgeted Reasoning Cache
- #10 Contradiction Sentinel Memory
- #11 Hash-Routed Early Experts
- #12 Learned RoPE Dimension Split
- #18 Adaptive Local Window
- #19 Expert-As-Memory Slots
- #20 On-Disk Prefix Memory Simulator

## Quick Ranking

| Rank | # | Idea | N/F/L | Tier | Standing-target stack |
|---:|---:|---|---:|:---:|---|
| 1 | 1 | Dual-Rate Compressed Memory Attention | 4/4/5 | S | PyTorch harness now; **Triton** dual-rate attention kernel is the standing target |
| 2 | 2 | Surprise-Gated Writable Memory | 5/3/5 | S | PyTorch gating now; **Triton** Hopfield-style read kernel is the standing target |
| 3 | 5 | Memory Distillation Head | 4/3/5 | S | PyTorch only — auxiliary head, no compute-path kernel surface |
| 4 | 15 | Memory-Byte Regularized Loss | 4/3/5 | S | PyTorch only — loss term, no compute-path kernel surface |
| 5 | 27 | Adversarial Long-Probe Curriculum | 5/2/4 | A (S/A boundary) | PyTorch + data pipeline only |
| 6 | 21 | VQ-Quantized KV Codebook | 4/3/5 | A (high) | PyTorch falsification; **Triton** fused VQ-attention is the standing target |
| 7 | 3 | Latent-KV Plus Block Retriever | 3/4/4 | A | PyTorch + **Triton** MLA kernel (DeepSeek's reference is Triton-based) |
| 8 | 4 | Recurrent Summary As Query Prior | 4/3/4 | A | PyTorch + vendor `mamba-ssm` CUDA kernel (verify reproducibility on this box) |
| 9 | 13 | Two-Phase Sparse Warmup | 2/5/4 | A | PyTorch only — training-schedule infra |
| 10 | 22 | Mixture-of-Depth Token Skipper | 3/4/4 | A | PyTorch falsification; **Triton** dispatch kernel once router proves out |
| 11 | 23 | Fast-Weights Hopfield Memory Head | 4/3/4 | A | PyTorch falsification; **Triton** fused write/read kernel above ~1k tokens |
| 12 | 25 | Learned Attention Sinks With Eviction | 4/4/3 | A | PyTorch falsification; **Triton** sink-aware attention is the standing target |
| 13 | 26 | Key-Only Retrieval Bypass | 3/4/4 | A | PyTorch falsification; **Triton** split-cache attention is the standing target |
| 14 | 28 | Self-Distilled Cache Pruning | 4/3/4 | A | PyTorch only — utility head + top-k mask |
| 15 | 30 | Skip-Stream Bidirectional Summary | 4/3/4 | A | PyTorch + vendor bidirectional `mamba-ssm` (same vendor caveat as #4) |
| 16 | 16 | Segment-Level MTP | 3/4/3 | A | PyTorch only — auxiliary head |
| 17 | 6 | Causal Block Autoencoder KV | 4/2/4 | B | PyTorch + **Triton** compressor (only if #1 fails) |
| 18 | 14 | Top-k With Diversity Penalty | 3/4/3 | B | PyTorch only — selector regularizer |
| 19 | 17 | Persistent Scratchpad Tokens | 3/4/3 | B | PyTorch only — token-stream modification |
| 20 | 24 | Drafter-Coupled Cache Co-Train | 4/3/4 | B | PyTorch (training); inference-side Triton handled by serving stack — not a base-arch gate |
| 21 | 29 | Codebook-Anchored Persistent Memory | 4/2/3 | B | PyTorch only — single embedding-gather |
| 22 | 7 | Multi-Timescale Residual Memory | 4/2/3 | C | PyTorch only |
| 23 | 8 | Birkhoff Residual Mixer | 3/4/3 | C | PyTorch only |
| 24 | 9 | Budgeted Reasoning Cache | 4/2/4 | C | PyTorch + Python serving harness |
| 25 | 10 | Contradiction Sentinel Memory | 5/2/3 | C | PyTorch + synthetic data generator |
| 26 | 11 | Hash-Routed Early Experts | 2/4/2 | C | PyTorch + **Triton** group-gemm (off-path for memory) |
| 27 | 12 | Learned RoPE Dimension Split | 3/4/3 | C | PyTorch only — single rotation op |
| 28 | 18 | Adaptive Local Window | 3/2/3 | C | PyTorch masks falsify the loss hypothesis; **Triton** required for any honest speed claim |
| 29 | 19 | Expert-As-Memory Slots | 4/2/2 | C | PyTorch + **Triton** group-gemm (confounded with routing) |
| 30 | 20 | On-Disk Prefix Memory Simulator | 2/5/2 | C | Python only — pure simulator |

## 1. Dual-Rate Compressed Memory Attention  [Tier S]

**Core mechanism:** Local window + medium compressed top-k blocks + heavy global dense compressed blocks.

**Why it might work:** Combines exact local syntax, content retrieval, and cheap global summary.

**Why it might fail:** Compressor may lose token identity; indexer may train poorly.

**Minimum experiment:** Tiny LM vs transformer on the same tokens.

**Metric signal:** Lower long-association loss at less than or equal validation loss.

**Kill condition:** More than 3% worse validation loss and no long-task gain.

**Implementation stack:** PyTorch model code today — design is still being shaped. **Triton** dual-rate attention kernel (FlashAttention-style with separate local-window and compressed-block masks fused) is the standing target the moment the candidate shows long-probe signal; do not carry PyTorch overhead into a scaled run. CUDA C++ only at scaled runs after Triton profiling shows memory-bandwidth saturation.

## 2. Surprise-Gated Writable Memory  [Tier S]

**Core mechanism:** Write to memory only when prediction surprise or representation novelty is high.

**Why it might work:** Memory budget tracks information value.

**Why it might fail:** Surprise may overfit noise.

**Minimum experiment:** Add memory slots updated by a learned gate.

**Metric signal:** Better delayed recall per memory byte.

**Kill condition:** Writes saturate or collapse to none.

**Implementation stack:** PyTorch for the gating logic; **Triton** Hopfield-style memory read kernel (softmax-attention over slot bank fused with gating mask) is the standing target. Per-token write op is sequential but small — PyTorch suffices indefinitely for that surface.

## 3. Latent-KV Plus Block Retriever  [Tier A]

**Core mechanism:** MLA-like latent KV cache plus block-level retrieval over latent summaries.

**Why it might work:** Directly targets cache bytes with content access.

**Why it might fail:** Low-rank cache may hurt small models.

**Minimum experiment:** Latent KV attention layer control.

**Metric signal:** KV bytes down with no loss hit.

**Kill condition:** Loss worse at same params.

**Implementation stack:** PyTorch + **Triton** MLA kernel — DeepSeek's published reference is already Triton-based, so the lower-level path is the path-of-least-resistance. Top-k retriever is a single PyTorch op.

## 4. Recurrent Summary As Query Prior  [Tier A]

**Core mechanism:** Mamba-like state biases attention block selection.

**Why it might work:** Recurrent state can guide where sparse attention looks.

**Why it might fail:** State may encode shallow recency only.

**Minimum experiment:** Add state-conditioned top-k logits.

**Metric signal:** Retriever recall improves.

**Kill condition:** No recall gain vs learned query only.

**Implementation stack:** PyTorch + vendor `mamba-ssm` CUDA kernel for the SSM scan. **Vendor caveat:** `mamba-ssm` is an external CUDA dependency — verify build and reproducibility on this box before committing, and have a PyTorch fallback path in case the vendor kernel breaks under our toolchain. Selector is small; no custom kernel needed.

## 5. Memory Distillation Head  [Tier S — L revised 4 → 5]

**Core mechanism:** Auxiliary head predicts which past block future tokens will need.

**Why it might work:** Gives credit assignment to memory/indexer. Many selector ideas (1, 4, 14, 28) likely benefit from this signal — without it they share a circular-supervision risk.

**Why it might fail:** Auxiliary labels are heuristic.

**Minimum experiment:** Generate labels from dense attention in a teacher.

**Metric signal:** Faster sparse warmup.

**Kill condition:** No selector improvement after warmup.

**Implementation stack:** PyTorch only. Teacher-attention labels can be precomputed once and cached as targets; auxiliary head is a thin MLP. No compute-path kernel surface — Triton would be premature.

## 6. Causal Block Autoencoder KV  [Tier B]

**Core mechanism:** Compress each block with a causal autoencoder trained by future-token utility.

**Why it might work:** Learns useful summaries, not averages.

**Why it might fail:** Extra loss may dominate.

**Minimum experiment:** Block compressor plus reconstruction/prediction loss.

**Metric signal:** Better long retrieval at fixed cache.

**Kill condition:** Reconstruction good but LM bad.

**Implementation stack:** PyTorch for the autoencoder; **Triton** compressor + attention-over-codes when the design proves out. Heavy overlap with #1 — run only if #1's compressor design fails to learn useful summaries.

## 7. Multi-Timescale Residual Memory  [Tier C — N 5 → 4, L 4 → 3]

**Core mechanism:** Separate residual streams for token, segment, document, task.

**Why it might work:** Mirrors hierarchy of context usefulness.

**Why it might fail:** Complexity and instability. Hierarchical-RNN and Transformer-XL priors give this less novelty than originally scored.

**Minimum experiment:** Two-stream residual tiny model.

**Metric signal:** Improved long consistency.

**Kill condition:** No gain over window attention.

**Implementation stack:** PyTorch only. No specialized kernel until the design is concrete enough to profile.

## 8. Birkhoff Residual Mixer  [Tier C]

**Core mechanism:** mHC-style constrained residual mixing without MoE.

**Why it might work:** Stable depth/capacity axis.

**Why it might fail:** Too small to matter at tiny scale.

**Minimum experiment:** Swap residual blocks in baseline.

**Metric signal:** Lower gradient spikes or deeper training.

**Kill condition:** More cost without loss gain.

**Implementation stack:** PyTorch only — pure linear-algebra primitives.

## 9. Budgeted Reasoning Cache  [Tier C]

**Core mechanism:** Allocate inference cache dynamically based on uncertainty.

**Why it might work:** Test-time compute follows difficulty.

**Why it might fail:** Hard to train from next-token loss.

**Minimum experiment:** Evict/retain KV by uncertainty.

**Metric signal:** Better perplexity per cache byte.

**Kill condition:** Same as simple recency.

**Implementation stack:** PyTorch model + Python serving harness. Eviction logic doesn't need a custom kernel.

## 10. Contradiction Sentinel Memory  [Tier C]

**Core mechanism:** Memory slots specialize in facts likely to conflict later.

**Why it might work:** Targets long-horizon consistency.

**Why it might fail:** Requires data/tasks with contradictions.

**Minimum experiment:** Synthetic contradiction corpus.

**Metric signal:** Better contradiction resolution.

**Kill condition:** Only helps synthetic task.

**Implementation stack:** PyTorch + synthetic data generator. No kernel work.

## 11. Hash-Routed Early Experts  [Tier C]

**Core mechanism:** Hash-routed shallow MoE for token-type specialization.

**Why it might work:** Cheap stable specialization.

**Why it might fail:** Not core memory bottleneck.

**Minimum experiment:** Replace first FFN with hash experts.

**Metric signal:** Lower train loss per FLOP.

**Kill condition:** Routing confounds memory tests.

**Implementation stack:** PyTorch + **Triton** group-gemm if expert dispatch becomes the bottleneck. Off-path for memory work — kernel investment not warranted at this depth in the priority queue.

## 12. Learned RoPE Dimension Split  [Tier C]

**Core mechanism:** Different positional treatment for local vs compressed memory dims.

**Why it might work:** Avoids absolute-position contamination in values.

**Why it might fail:** May be implementation fiddly.

**Minimum experiment:** Partial RoPE ablation in compressed attention.

**Metric signal:** Better long extrapolation.

**Kill condition:** No effect vs normal RoPE.

**Implementation stack:** PyTorch only — RoPE is a single rotation op. No efficiency case for Triton at this scope.

## 13. Two-Phase Sparse Warmup  [Tier A]

**Core mechanism:** Dense train, selector imitation, then sparse train.

**Why it might work:** Avoids cold selector collapse.

**Why it might fail:** Teacher attention may be a bad target.

**Minimum experiment:** Dense control creates labels.

**Metric signal:** Faster stable sparse convergence.

**Kill condition:** Sparse never catches dense.

**Implementation stack:** PyTorch only — pure training-schedule infra. Infra dependency for Tier S #1 and #5.

## 14. Top-k With Diversity Penalty  [Tier B]

**Core mechanism:** Select blocks by relevance plus temporal/diversity spread.

**Why it might work:** Reduces redundant retrieved blocks.

**Why it might fail:** Can omit key local evidence.

**Minimum experiment:** Add diversity regularizer.

**Metric signal:** Higher selected-block coverage.

**Kill condition:** Worse LM loss, no recall.

**Implementation stack:** PyTorch only — selector regularizer.

## 15. Memory-Byte Regularized Loss  [Tier S — L revised 4 → 5]

**Core mechanism:** Penalize memory reads/writes directly during training.

**Why it might work:** Creates new measurable axis. Formalizes the project's headline metric (loss per memory byte) as part of the optimizer's objective rather than a post-hoc score.

**Why it might fail:** Model may underuse memory.

**Minimum experiment:** Add differentiable read budget.

**Metric signal:** Better loss/byte Pareto.

**Kill condition:** Degenerate low-read high-loss.

**Implementation stack:** PyTorch only — additional loss term, no compute-path kernel surface.

## 16. Segment-Level MTP  [Tier A]

**Core mechanism:** Predict future tokens at segment boundaries to train summaries.

**Why it might work:** Summary learns forward utility.

**Why it might fail:** May duplicate normal LM loss.

**Minimum experiment:** Auxiliary segment future head.

**Metric signal:** Better long-term probes.

**Kill condition:** No gain after equal tokens.

**Implementation stack:** PyTorch only — auxiliary head.

## 17. Persistent Scratchpad Tokens  [Tier B]

**Core mechanism:** Dedicated internal tokens carry compressed state between chunks.

**Why it might work:** Simple and compatible.

**Why it might fail:** Scratch tokens may become junk.

**Minimum experiment:** Insert memory tokens per block.

**Metric signal:** Better chunked LM loss.

**Kill condition:** No improvement over CLS token.

**Implementation stack:** PyTorch only — token-stream modification.

## 18. Adaptive Local Window  [Tier C — F revised 3 → 2]

**Core mechanism:** Window grows/shrinks by entropy.

**Why it might work:** Saves cache on easy regions.

**Why it might fail:** Dynamic shapes complicate kernels — variable per-token attention shape is the canonical PyTorch-hostile pattern.

**Minimum experiment:** Simulated mask in tiny model.

**Metric signal:** Same loss with fewer local reads.

**Kill condition:** Always chooses max window.

**Implementation stack:** **Two-path stack.** (a) Hypothesis falsification — does entropy-controlled masking help loss? — uses PyTorch masks, slow but correct. (b) Speed claim — does adaptive window save FLOPs/cache vs fixed window? — requires **Triton**, since PyTorch eager and `torch.compile` cannot express variable-shape attention efficiently. Both paths must show signal before this graduates from Tier C.

## 19. Expert-As-Memory Slots  [Tier C]

**Core mechanism:** MoE experts act as persistent memory transforms.

**Why it might work:** Merges routing and memory.

**Why it might fail:** Too confounded and scale-hungry.

**Minimum experiment:** Tiny routed memory FFN.

**Metric signal:** Improved repeated pattern learning.

**Kill condition:** No gain vs FFN.

**Implementation stack:** PyTorch + **Triton** group-gemm. Confounded with routing — kernel investment not warranted at tiny scale.

## 20. On-Disk Prefix Memory Simulator  [Tier C]

**Core mechanism:** Simulate prefix cache reuse and eviction policies.

**Why it might work:** Useful for agents with long sessions.

**Why it might fail:** Serving problem, not base model.

**Minimum experiment:** No model change; cache benchmark.

**Metric signal:** Better cost model.

**Kill condition:** No architecture insight.

**Implementation stack:** Python only — pure simulator, no kernel surface.

## 21. VQ-Quantized KV Codebook  [Tier A — high; promotion to S waits for #1 long-probe signal]

**Core mechanism:** Quantize K and V via learned discrete codebooks; cache stores small indices, not vectors.

**Why it might work:** Bytes-per-token drops 4×–16× on the same axis as #1, but orthogonally to compression — both can stack.

**Why it might fail:** Codebook collapse; rounding noise propagates through attention.

**Minimum experiment:** VQ bottleneck on K and V before cache write; same control/candidate harness as #1.

**Metric signal:** KV bytes/token at matched validation loss; codebook utilization entropy.

**Kill condition:** More than 1.5% loss penalty at 4× compression or codebook usage below 25%.

**Implementation stack:** PyTorch falsification harness today. **Triton** fused VQ-attention kernel (lookup + dot-product fused so the dequantized K never materializes) is the standing target — VQ's whole point is bytes-per-token, and a non-fused PyTorch path forfeits the byte-axis win at scale. CUDA C++ only if Triton can't hit memory-bandwidth target on Hopper TMA.

## 22. Mixture-of-Depth Token Skipper  [Tier A]

**Core mechanism:** Per-layer router lets some tokens skip the layer transform; depth becomes adaptive per token.

**Why it might work:** Frees compute for hard tokens; cousin of MoE on the depth axis (Raposo 2024).

**Why it might fail:** Router collapses to all-skip or all-transform; depth-conditional bias destabilizes training.

**Minimum experiment:** Router-gated transform on 50% of blocks; control runs same blocks unconditionally.

**Metric signal:** Loss-per-FLOP at matched validation loss.

**Kill condition:** Router collapses, or loss-per-FLOP no better than a smaller dense baseline.

**Implementation stack:** PyTorch falsification while routing behavior is being shaped; **Triton** dispatch kernel for scatter-gather under the router (same primitive as MoE expert dispatch) is the standing target once router proves out. CUDA unnecessary — Triton's scatter ops are mature.

## 23. Fast-Weights Hopfield Memory Head  [Tier A]

**Core mechanism:** Memory head with delta-rule writes (`W += outer(k, v)`) read via softmax-Hopfield retrieval.

**Why it might work:** Differentiable Hebbian writes provide a non-surprise alternative covering #2's credit-assignment gap.

**Why it might fail:** Capacity ceiling at tiny scale; numerical drift on long sequences.

**Minimum experiment:** One fast-weights head alongside attention at matched parameter count.

**Metric signal:** Delayed-association recall; per-step write magnitude.

**Kill condition:** Recall not above local-attention floor.

**Implementation stack:** PyTorch for the per-token write loop at tiny scale (~<1k tokens, eager-mode wins on overhead); **Triton** fused Hopfield kernel (write + softmax-read in one pass) is the standing target above the eager-mode break-even.

## 24. Drafter-Coupled Cache Co-Train  [Tier B — inference / serving optimization, not base-arch gate]

**Core mechanism:** Train a small drafter that shares the main model's KV cache; co-loss on speculative acceptance rate.

**Why it might work:** Inference-time speedup with zero extra cache; serving teams hand-tune this — rarely attacked at training time.

**Why it might fail:** Drafter diverges in distribution; acceptance rate floors at random.

**Minimum experiment:** Tiny model + 1/8-size drafter sharing K-cache; jointly trained.

**Metric signal:** Speculative acceptance rate vs drafter FLOPs.

**Kill condition:** Acceptance rate below 25%, or main-model loss regression above 1%.

**Implementation stack:** PyTorch for both models and the co-loss. Inference-time speculative decoding stack (vLLM / Triton kernels) is downstream. Tier B because base-architecture decisions are not gated by drafter acceptance — run after the base research questions resolve.

## 25. Learned Attention Sinks With Eviction  [Tier A]

**Core mechanism:** Replace StreamingLLM's fixed sinks with a small set of learned slots; surprise-gated writes; bounded count.

**Why it might work:** Combines streaming stability with the writable-memory line of #2 without needing slot-eviction heuristics.

**Why it might fail:** Sinks become redundant scratchpad (#17 failure mode).

**Minimum experiment:** Replace fixed sink with k learned slots; gate writes by prediction surprise.

**Metric signal:** Loss under truncation pressure; sink-slot reuse rate.

**Kill condition:** No improvement over fixed sinks at the same truncation budget.

**Implementation stack:** PyTorch falsification; **Triton** sink-aware attention kernel (FlashAttention with anchored slot positions exempt from causal mask) is the standing target.

## 26. Key-Only Retrieval Bypass  [Tier A]

**Core mechanism:** Split the KV cache so the block selector reads only K embeddings; V is loaded only on top-k hit.

**Why it might work:** Selector bandwidth dominates retriever cost; V is redundant during selection.

**Why it might fail:** K alone may be too coarse to discriminate.

**Minimum experiment:** Block-retrieval over K-only summaries; V loaded post-select.

**Metric signal:** Selector recall vs search FLOPs.

**Kill condition:** Recall drops more than 5% at the same top-k vs full-vector retrieval.

**Implementation stack:** PyTorch model for falsification; **Triton** split-cache attention kernel (two-stage: K-only top-k pass, then conditional V gather + attention) is the standing target — the bandwidth win this idea claims requires the fused two-stage kernel.

## 27. Adversarial Long-Probe Curriculum  [Tier A — S/A boundary]

**Core mechanism:** Generator network synthesizes long-association probes targeting the model's currently weakest distance band; co-trained.

**Why it might work:** Long-context training is signal-starved on natural data; targeted probes are the missing curriculum. The current harness's long-association probe is underpowered, so stronger probes are likely on-path before further architectural work — which raises this idea's near-term priority above some Tier-S architecture choices.

**Why it might fail:** Generator collapses; probes drift off-distribution.

**Minimum experiment:** Generator emits (key, query, distance) triples; mix with normal LM batches. Start with uniform-distance probes (no adversary) before adding the adversarial curriculum.

**Metric signal:** Long-association loss as a function of distance.

**Kill condition:** Generator collapse, or no gain over uniform-distance synthetic probes.

**Implementation stack:** PyTorch + data pipeline only. No model-architecture kernel surface — work is in the training loop.

## 28. Self-Distilled Cache Pruning  [Tier A]

**Core mechanism:** Per-block "utility head" predicts future attention weight on that block; eviction policy uses head outputs.

**Why it might work:** Closes the loop between selector and eviction; reuses #5's distillation signal at decode time.

**Why it might fail:** Utility head correlates only with recency.

**Minimum experiment:** Add utility head; evict bottom-k blocks under fixed cache size.

**Metric signal:** Loss-per-byte after eviction; correlation between head output and recency baseline.

**Kill condition:** Head's eviction matches pure-recency eviction within noise.

**Implementation stack:** PyTorch only — utility head and top-k mask op.

## 29. Codebook-Anchored Persistent Memory  [Tier B]

**Core mechanism:** Fixed pre-trained memory pages as a parametric retrieval index baked into weights; common facts read from anchors instead of cache.

**Why it might work:** Common facts should not occupy per-session cache; anchors generalize across sessions.

**Why it might fail:** Tiny scale will not learn useful anchors.

**Minimum experiment:** Retrievable codebook trained on a synthetic facts corpus; integrate as fixed read-only memory.

**Metric signal:** Cache bytes vs factual recall on held-out sequences.

**Kill condition:** No fact-recall transfer beyond training corpus.

**Implementation stack:** PyTorch only — codebook lookup is a single embedding-gather. No kernel work.

## 30. Skip-Stream Bidirectional Summary  [Tier A]

**Core mechanism:** Two parallel streams: causal attention over the current chunk; bidirectional SSM over already-finalized chunks.

**Why it might work:** Finalized past has no causal constraint during training; a bidirectional summary is strictly more informative than a causal one.

**Why it might fail:** Boundary handling is fiddly; train/eval mismatch on the rolling chunk.

**Minimum experiment:** Tiny model with chunked bidirectional summarizer feeding into local-attention head.

**Metric signal:** Long-probe loss; chunk-boundary perplexity gap.

**Kill condition:** Same loss as a causal-summary baseline.

**Implementation stack:** PyTorch + vendor bidirectional `mamba-ssm` kernel. **Vendor caveat:** same external CUDA dependency as #4 — verify reproducibility on this box first, and have a PyTorch fallback for the bidirectional scan in case the vendor kernel breaks under our toolchain. Chunk-boundary plumbing is pure Python.

## Bottleneck Decomposition

Original-bank decomposition retained, expanded to include 21–30:

- **Context access:** ideas 1, 3, 4, 10, 14, 21, 22, 25, 26, 28.
- **Compression:** ideas 1, 3, 6, 15, 17, 21.
- **Memory update:** ideas 2, 6, 9, 17, 23, 25.
- **Routing:** ideas 4, 5, 11, 14, 19, 22, 26.
- **Credit assignment:** ideas 5, 6, 13, 16, 27, 28.
- **Inference cache movement:** ideas 1, 3, 9, 15, 20, 21, 24, 26, 28.
- **Long-horizon consistency:** ideas 2, 7, 10, 16, 23, 30.
- **Reasoning-time compute allocation:** ideas 2, 9, 18, 22.
- **Data efficiency:** ideas 5, 13, 16, 27, 29.
- **Training stability:** ideas 8, 12, 13, 22, 25.

## Stack Discipline (Closing Rule)

**PyTorch is the floor for ergonomics; Triton is the standing target for any compute-path kernel once the candidate has shown signal.** When the choice between two stack levels is genuinely 50/50 — comparable engineering cost, comparable design risk — go lower. Max efficiency is the standing preference.

**CUDA C++** only at scaled runs after Triton hits a measurable wall (memory-bandwidth saturation, launch-bound kernels, ops Triton cannot express). Rust / C / Mojo / asm are not on the path for training code: ecosystem too thin and autograd unsupported. JAX/XLA is a horizontal swap, not a step down.

The current research bottleneck is learning signal, not kernel speed — but the doctrine here protects against the inverse failure mode of staying in PyTorch out of habit once a candidate has earned scaling. The implementation-stack notes per idea above name the *standing target* — what the kernel surface will eventually look like once the candidate proves out — so there is no ambiguity about where the optimization debt lives.

For the locked-in primary (#1), the next concrete step is **better training signal, not kernel work** — add #5 (Memory Distillation Head) and #15 (Memory-Byte Regularized Loss) to the existing harness, strengthen the #27-style long-association probe, then rerun two seeds. Tritonization waits until the candidate has earned the optimization. After that point, the dual-rate attention kernel and the surprise-gated Hopfield read are the standing Triton targets, with #21's fused VQ-attention queued behind whichever shows long-probe signal first.
