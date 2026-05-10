# Novelty Matrix

| Candidate | Existing Evidence | What Is New For Project X | Novelty Risk | Measurable Axis |
|---|---|---|---|---|
| Dual-Rate Compressed Memory Attention | DeepSeek V4 CSA/HCA, NSA | Tiny-scale, open experiment around dual-rate memory bytes vs loss | Medium: inspired by V4 but not a clone if designed independently | Loss per memory byte; delayed association |
| Surprise-Gated Writable Memory | Titans, AllMem | Combine surprise writes with token-prediction memory budget | High | Recall per write; write entropy |
| Latent-KV Plus Block Retriever | MLA, MLA hardware | Add explicit block retrieval to latent KV | Medium | Cache bytes vs validation loss |
| Recurrent Summary-Guided Sparse Retrieval | Mamba/Jamba/MemMamba + sparse attention | Use recurrence only as retrieval prior | Medium-high | Selector recall and long-probe loss |
| Memory Distillation Head | Sparse warmup, dense attention teachers | Future-utility labels for sparse selector | Medium | Sparse warmup speed |

Winner on novelty: Surprise-Gated Writable Memory.  
Winner on feasibility: Latent-KV Plus Block Retriever.  
Winner on leverage: Dual-Rate Compressed Memory Attention.
