# DeepSeek V4 Reading Notes

Run ID: `run-20260428-233932-research-gate`

Source: `gpt-codex/sources/deepseek-v4-report.pdf`  
Extracted text: `gpt-codex/extracted/deepseek-v4-report.txt`  
Local SHA256: `f4cbe4fcbd2888b25b2890a98cc6ef4ce0489df7c93e140b6f853c451d3f5c52`  
Verification: Hugging Face HEAD `x-linked-etag` matched local SHA256. A web-search snippet reported a different SHA256, treated as stale or for a different object.

## Core Mechanism

DeepSeek V4 keeps a Transformer + MoE + MTP backbone and attacks the million-token bottleneck through a hybrid attention stack:

- CSA, Compressed Sparse Attention: compress token-level KV entries into block entries, then use a lightweight indexer to choose top-k compressed blocks for attention.
- HCA, Heavily Compressed Attention: compress much larger token spans into dense-attended KV entries.
- Sliding-window uncompressed KV branch: preserves local dependencies and strict causality around the current token.
- Shared-KV MQA and grouped output projection: reduce KV movement and output projection cost.
- Mixed KV precision: BF16 for RoPE dimensions, FP8 for remaining KV dimensions; FP4 for CSA indexer QK path.

The paper claims V4-Pro uses 27% of DeepSeek-V3.2 single-token inference FLOPs and 10% of its KV cache at 1M context; V4-Flash claims 10% FLOPs and 7% KV cache.

## Architecture Claims

- V4-Pro: 1.6T total parameters, 49B active per token.
- V4-Flash: 284B total parameters, 13B active per token.
- Both support 1M-token context natively after staged pretraining.
- DeepSeekMoE is retained with fine-grained routed experts and shared experts.
- Routing score activation changes from sigmoid to `sqrt(softplus)`.
- Initial dense FFN layers are replaced with MoE layers using hash routing.
- MTP modules/objectives are retained from DeepSeek V3.
- mHC expands the residual stream by a small factor and constrains residual mapping matrices to the Birkhoff polytope using Sinkhorn-Knopp, making the mapping non-expansive.

## Training And Inference Claims

- V4-Flash trained on 32T tokens; V4-Pro trained on 33T tokens.
- Sequence length curriculum: 4K to 16K to 64K to 1M.
- Sparse attention is introduced after dense warmup; CSA indexer gets a short warmup stage.
- Muon is used for most matrices; AdamW remains for embeddings, prediction heads, RMSNorm weights, and some mHC static parameters.
- Hybrid Newton-Schulz uses 8 fast-convergence iterations plus 2 stabilizing iterations.
- FP4 QAT is applied to MoE expert weights and CSA indexer QK path.
- Inference uses heterogeneous KV cache management plus on-disk KV storage for shared-prefix reuse.

## Stability Claims

- Training had loss spikes tied to MoE outliers and routing feedback.
- Anticipatory Routing decouples routing indices from the current backbone step by using historical parameters; activated only after detected spikes.
- SwiGLU clamping caps the linear component to [-10, 10] and gate upper bound to 10.
- mHC adds modeling capacity but costs 6.7% overlapped pipeline-stage wall time after fused kernels/recomputation.

## Benchmark Claims

- V4-Flash-Base beats V3.2-Base on many internal base-model benchmarks despite fewer active and total parameters.
- V4-Pro-Base dominates most base-model categories, especially knowledge and long-context.
- Post-training uses reasoning-effort modes: non-think, think high, think max.
- Mixed RL specialist training plus On-Policy Distillation replaces the older mixed RL stage.
- Public competitive claims should be treated as benchmark claims, not independent proof of architecture superiority.

## Caveats

- Many comparisons use internal evaluation frameworks.
- Exact hyperparameters for CSA/HCA compression rates and hybrid layer schedule are not fully recoverable from the prose alone.
- V4 is not a clean single mechanism result: gains confound data quality, optimizer, MoE scale, post-training, precision, cache engineering, kernels, and routing changes.
- Million-token usefulness depends on retrieval quality inside compressed/sparse attention, not only on formal context length.

## Transfer To Project X

Strong transfer candidates:

- Test small CSA/HCA-style dual-memory attention under identical token budget against a transformer control.
- Treat KV cache movement as a first-class metric, not just perplexity.
- Add local uncompressed window to any compressed memory design.
- Separate routing/indexer training warmup from full sparse use.
- Explore constrained residual mixing at small scale, but only after attention/memory experiments.

Weak transfer candidates for now:

- Full MoE scale, FP4 QAT, on-disk KV serving, and distributed Muon ZeRO are infrastructure-heavy and should not be first experiments.
