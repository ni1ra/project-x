# Council A - Encoder

**Date:** 2026-05-09  
**Mode:** SINGLE-BRAIN. advisor MCP absent. Evidence-backed lenses only.  
**Question:** What should encode real user text into HDC memory vectors in Phase 9 and beyond?

---

## 0. Ground Truth

Phase 8 used random bipolar atoms. That proved HDC capacity mechanics, not semantic language encoding.

The missing chain is:

```text
text -> semantic representation -> HDC-compatible vector -> bind/write/read -> cleanup -> evidence packet
```

The encoder is now the most important Phase 9 component. If it fails, the HDC memory becomes an exact-symbol trick rather than a useful agent memory.

---

## 1. Evidence Pack

Fetched sources:

- BGE docs: BGE-small-en is 33.4M parameters and 133 MB; BGE v1.5 was released to improve retrieval behavior and similarity distribution.
- BAAI/bge-small-en-v1.5 model card: sentence-transformers usage is supported and the model is MIT-licensed.
- all-MiniLM-L6-v2 model card: maps sentences and paragraphs to a 384-dimensional dense vector space for clustering/semantic search and uses sentence-transformers.
- MTEB literature establishes embedding evaluation across retrieval, clustering, classification, STS, and related tasks.
- Local Phase 8 SNN bridge: deterministic spike-derived vectors work, but cross-input cosine means around 0.36-0.42 are not near-orthogonal.

Relevant local facts:

- `hdc_snn_bridge.py` deterministic check passed.
- Orthogonality calibration deferred.
- `hdc_conversation_demo.py` does not encode text; it maps turn IDs to random vocab atoms.

---

## 2. Seats

| Seat | Lens | Unique concern |
|---|---|---|
| 1 | Retrieval engineer | Does the encoder produce useful nearest-neighbor structure? |
| 2 | HDC theorist | Does projection preserve near-orthogonality/capacity? |
| 3 | SNN substrate engineer | Can project_synapse eventually own encoding? |
| 4 | Product memory engineer | Can the agent cite provenance and handle paraphrase? |
| 5 | Adjacent: compression engineer | What information is lost when text becomes one vector? |

---

## 3. Candidate Scores

| Candidate | Score | Verdict |
|---|---:|---|
| Pretrained small embedder + random/sign projection into HDC | **404** | Winner for Phase 9 |
| Hybrid embedder + online Hebbian correction | 386 | Phase 10, after baseline |
| Learned linear projection trained on retrieval labels | 372 | Useful once dataset exists |
| project_synapse SNN encoder + spike-time hashing | 350 | Long-term substrate path, not Phase 9 default |
| Handwritten keyword/symbol encoder | 326 | Baseline only |

Mean score: 367.6. Spread: 78.

---

## 4. Deliberation

The encoder council rejects starting Phase 9 with a pure SNN encoder.

Reason: Phase 9's purpose is to close the semantic-agent gap, not to prove the substrate can eventually learn semantics. A pretrained embedder already compresses text into a semantic manifold. HDC can then test whether a high-dimensional symbolic memory can store, compose, and retrieve those semantic units.

BGE-small-en-v1.5 is the best first candidate because it is small enough for the machine, retrieval-oriented, MIT-licensed, and explicitly documented as a small model with competitive performance. MiniLM is an even lighter fallback and useful as a regression baseline. GTE/BGE-base can be later comparison arms.

The projection step must be measured, not assumed.

The simplest projection:

```text
embedding e in R^384
random matrix W in R^(D x 384)
hdc = sign(W e)
```

This gives HDC bipolar vectors while preserving approximate angular similarity. It is not biologically pure. That is acceptable for Phase 9 because it isolates the semantic question.

The SNN encoder remains a research branch. project_synapse has the right philosophical alignment: local online learning, sparsity, spike dynamics, Neural CPU. But the current bridge's cross-input cosine shows the naive spike encoder is not HDC-ready.

---

## 5. Defended 400+ Idea

**Winner: BGE-small or MiniLM + random projection + exact measurement harness.**

Phase 9 should implement:

```text
text
  -> sentence embedder
  -> normalize
  -> random Gaussian projection to D
  -> sign
  -> bind(turn_id, semantic_hdc)
  -> write to memory
```

It should also store raw text and metadata outside the HDC accumulator:

```text
turn_id -> source text
turn_id -> timestamp
turn_id -> speaker
turn_id -> tags
turn_id -> embedding checksum
```

The HDC accumulator is the associative memory, not the only memory.

---

## 6. Required Measurements

Phase 9 encoder benchmark must include:

- embedding model name and revision
- embedding dimension
- projection seed
- HDC dimension
- pairwise HDC cosine distribution
- semantic query top-k recall
- exact turn lookup recall
- false positives on absent facts
- paraphrase robustness
- contradiction cases
- cleanup dictionary size

Minimum pass line:

- Exact turn lookup: >=95% at 1000 turns.
- Semantic top-5 recall: >=80% on 200 labeled queries.
- False positive rate: <=10%.
- Every answer returns source turn IDs.

---

## 7. Phase Ordering

Phase 9:

- pretrained embedder
- random projection
- text memory harness

Phase 10:

- projection comparison
- learned projection
- online Hebbian correction

Phase 12+:

- SNN encoder calibration
- spike-time hashing
- STDP adaptation

Do not block Phase 9 on SNN purity.

---

## 8. Risks

- Sentence embeddings blur exact wording.
- One vector per turn loses internal structure.
- Projection can damage semantic neighborhoods.
- Cleanup against all turns can amplify false positives.
- Embedding benchmarks do not guarantee chat-agent usefulness.

Mitigation:

- Store raw text/provenance.
- Evaluate exact lookup and semantic lookup separately.
- Add role/fact binding, not only turn binding.
- Maintain keyword baseline and explicit vector-list baseline.

---

## 9. Verdict

Use a pretrained small sentence embedder first.

The ideal path is not "HDC replaces embeddings." The ideal path is:

```text
pretrained semantic encoder -> HDC associative memory -> local generator/controller
```

Then Project X can replace pieces with SNN-native alternatives once the behavioral target is real.

---

## 10. Implementation Pressure Test

### Encoder interface

The interface should be boring:

```python
encode_texts(texts: list[str]) -> np.ndarray
```

Return:

- shape `(n, d_embed)`
- float32
- normalized if the encoder supports it
- deterministic for the same model/revision/input

The projection interface:

```python
project_to_hdc(embeddings, D, seed) -> np.ndarray
```

Return:

- shape `(n, D)`
- int8
- values in `{-1, +1}`

### Required ablations

Run at least:

- fallback deterministic encoder
- MiniLM
- BGE-small
- D=10k
- D=50k
- D=100k if time permits

For each:

- exact lookup recall
- semantic top-5
- false positive rate
- pairwise HDC cosine mean/std
- projection wall time

### Semantic test cases

Dataset needs:

- "lain likes X" preference facts
- "project file is Y" path facts
- "decision was Z" decision facts
- "earlier bug was caused by Q" causal facts
- paraphrases
- temporal references
- absent facts
- contradictions
- corrections
- multi-hop questions

### Failure signatures

If exact lookup works but semantic recall fails:

- encoder/projection is the issue
- HDC capacity is not disproven

If semantic dense baseline works but HDC fails:

- projection or cleanup is the issue
- test learned projection or larger D

If both dense and HDC fail:

- dataset labels or encoder are likely bad

If false positives are high:

- thresholding and absent-answer detection are missing

### SNN bridge criteria

The SNN encoder branch may re-enter only when:

- deterministic output remains true
- cross-input cosine is near zero
- same-class semantic examples cluster better than random
- activity level is stable
- encoding latency is tolerable

Current Phase 8 bridge meets determinism, not orthogonality.

### Storage rule

Never store only the HDC vector.

Always store:

- raw text
- turn ID
- speaker
- timestamp
- embedding model
- projection seed
- checksum

### Acceptance interpretation

If BGE-small wins, Phase 9 moves forward.

If MiniLM wins, use it.

If dense vector list beats HDC, report it and keep HDC for compositional/fact binding until improved.

If keyword search beats HDC on semantic queries, Phase 9 fails and must reframe.
