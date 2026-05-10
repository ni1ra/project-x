# Top 3 Designs

## 1. Dual-Rate Compressed Memory Attention

Why it ranks first: it attacks the main bottleneck exposed by DeepSeek V4, NSA, MLA, and hardware papers: long-context access is constrained by KV movement and attention FLOPs. It is also falsifiable in a tiny model.

Minimum experiment:

- Transformer control.
- Candidate with local window + medium compressed top-k block attention + heavy global compressed dense attention.
- Same data, tokens, steps, optimizer, batch, and approximate parameter budget.
- Metrics: validation loss, delayed association accuracy/loss, estimated KV bytes/read bytes per token, selector entropy, selected-block distance distribution.

## 2. Surprise-Gated Writable Memory

Why it ranks second: more novel and more aligned with long-horizon agents, but credit assignment is much harder. It should become the backup track if compressed memory merely reproduces known sparse-attention tradeoffs.

Minimum experiment:

- Tiny local-attention model with fixed memory slots.
- Write gate from prediction surprise and learned novelty.
- Metrics: delayed recall, write rate, write entropy, validation loss, memory-slot reuse.

## 3. Latent-KV Plus Block Retriever

Why it ranks third: feasible and cleanly grounded in MLA, but less novel. It is a strong control or fallback if Candidate 1 is too complex.

Minimum experiment:

- Full attention/GQA control.
- Latent KV cache variant with block-level retriever.
- Metrics: cache bytes, validation loss, decode-time memory proxy.
