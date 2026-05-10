# Architecture Candidates

## Candidate A: Dual-Rate Compressed Memory Attention

Core mechanism: each layer has local exact attention over a short window, CSA-style compressed block attention over medium chunks with learned top-k selection, and HCA-style heavily compressed dense global attention.

Why it might work: it creates a new Pareto axis, validation loss per memory byte, while preserving local exactness. It cross-breeds DeepSeek V4 CSA/HCA, NSA hardware-aligned block selection, and Jamba-style hybrid locality/globality.

Why it might fail: the compressor/indexer may not receive clean credit from next-token loss and may learn a recency shortcut.

Minimum experiment: replace one or more attention layers in the tiny Project X model; compare with transformer control under identical tokens, params or FLOPs, optimizer, batch, and steps.

Expected signal: lower delayed-association loss or equal validation loss with lower KV/memory bytes.

Kill condition: more than 3% worse validation loss and less than 10% improvement on long-association probes after matched training.

## Candidate B: Surprise-Gated Writable Memory

Core mechanism: a fixed memory bank receives writes only when a learned gate, prediction surprise, or novelty score crosses threshold. Reads are content-addressed and combined with local attention.

Why it might work: it creates an explicit memory update axis and could transfer to agents with long-horizon state.

Why it might fail: learned writes may saturate, never fire, or memorize noise. Credit assignment is harder than compressed attention.

Minimum experiment: tiny LM with 16-64 memory slots on delayed-copy and small text data.

Expected signal: better delayed recall per memory slot without large normal LM loss regression.

Kill condition: write entropy collapses or memory reads do not beat a recency cache.

## Candidate C: Latent-KV Plus Block Retriever

Core mechanism: cache low-rank latent K/V states and select blocks through a lightweight retriever before up-projection/recompute.

Why it might work: it directly addresses the memory-bound decode bottleneck identified by MLA sources while staying simpler than full CSA/HCA.

Why it might fail: tiny models may not benefit from low-rank compression; recomputation can erase speed gains.

Minimum experiment: latent-KV attention layer vs GQA/full attention control.

Expected signal: lower cache bytes at equal validation loss.

Kill condition: no loss/byte Pareto improvement.

## Candidate D: Recurrent Summary-Guided Sparse Retrieval

Core mechanism: a Mamba-like recurrent state summarizes prefix and biases top-k block selection for attention.

Why it might work: recurrence offers cheap global context while sparse attention preserves exact retrieval.

Why it might fail: recurrent state may only learn recency and add instability.

Minimum experiment: add recurrent selector prior to Candidate A’s medium compressed blocks.

Expected signal: higher selected-block recall and lower long-context probe loss.

Kill condition: selector prior is ignored or hurts normal LM loss.

## Candidate E: Memory Distillation Head

Core mechanism: train a sparse/compressed selector using auxiliary labels from dense attention or future-token utility, then anneal into normal sparse training.

Why it might work: it directly attacks the selector credit-assignment problem.

Why it might fail: dense attention labels are not necessarily causally useful and can bake in teacher biases.

Minimum experiment: dense teacher logs block salience; sparse student learns selector.

Expected signal: faster sparse convergence and less early collapse.

Kill condition: imitation improves selector metrics but not LM or long-task metrics.
