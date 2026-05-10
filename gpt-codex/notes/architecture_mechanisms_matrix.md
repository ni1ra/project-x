# Architecture Mechanisms Matrix

| Mechanism | Sources | Bottleneck | Claim Type | Project X Transfer |
|---|---|---|---|---|
| MLA latent KV cache | DeepSeek V2/V3, MLA hardware analysis | Inference cache movement | Fact: reduces cached K/V representation; inference benefit depends on execution scheme | Implementable small: latent KV cache with identical training budget |
| CSA compressed sparse attention | DeepSeek V4, NSA | Long-context attention FLOPs and KV traffic | Fact in report; exact public reproducibility unknown | Primary candidate: block-compress KV then top-k retrieve |
| HCA heavy dense compressed attention | DeepSeek V4 | Global context access under low memory | Fact in report; quality risk from overcompression | Pair with local window and CSA to avoid lossy global-only memory |
| Hardware-aligned block sparsity | NSA, FlashAttention-2 | Sparse attention not translating to speed | Fact: blockwise access matters | Measure contiguous block reads and attention FLOPs, not just math sparsity |
| Sliding local window | DeepSeek V4, Jamba | Local syntax and causality | Established | Mandatory control branch for compressed memory designs |
| State-space recurrence | Mamba, Jamba, MemMamba | Linear-time long sequence processing | Established but weaker for arbitrary retrieval | Use as auxiliary summary memory, not replacement for content addressability |
| Test-time memory | Titans, AllMem | Updating useful memory during inference | Emerging claim | Good novelty axis: learned write/read policy under token-prediction loss |
| MoE fine-grained routing | DeepSeekMoE, V2/V3/V4, Switch, GShard | Compute allocation and parameter capacity | Established at scale | Defer until memory mechanism proves useful; small MoE can confound results |
| Auxiliary-loss-free balancing | DeepSeek V3/V4 | Routing instability | Reported | Useful only if MoE enters experiments |
| MTP | DeepSeek V3/V4 | Sample efficiency and speculative future-token signal | Reported | Secondary add-on after attention baseline |
| Muon optimizer | Muon scalable, DeepSeek V4 | Training speed/stability | Strong but optimizer confounds architecture tests | Include as later optimizer ablation, not first gate |
| FP8/FP4 precision | FP8 formats, DeepSeek V3/V4 | Memory bandwidth and training/inference cost | Hardware-dependent | Not first experiment on 16 GB VRAM; use BF16/FP16 first |
| RoPE extension | YaRN, LongRoPE | Positional extrapolation | Established for extending pretrained context | Less relevant for from-scratch tiny tests, useful for long-context controls |
| Ring/context parallelism | Ring Attention, DeepSeek V4 CP | Training memory per device | Distributed systems mechanism | Not relevant until multi-GPU or huge context experiments |

## Cross-Source Synthesis

The strongest pattern is that long-context capability is no longer one trick. Effective systems combine:

1. Representation compression: MLA, CSA/HCA, state-space summaries.
2. Access sparsity: top-k compressed blocks, hardware-aligned block reads.
3. Local exactness: sliding windows or full local attention.
4. Update discipline: warmups, constrained residuals, stabilizers, optimizer choice.
5. Evaluation discipline: measure cache bytes, selected-block recall, long-range retrieval, and normal LM loss together.
