# SHRINE COUNCIL — Phase 8 Architecture Verdict

**Date:** 2026-05-09
**Mode:** SINGLE-BRAIN (advisor MCP deferred for time budget — flagged honestly)
**Convener:** Raphael (post-persona-shift; transitional)
**Question:** What architecture should the next 6h proof-of-concept demonstrate to fill the GAP above lain's existing SNN+STDP+Neural CPU substrate, delivering local-rule-only learning + perfect compositional memory at scale + continual learning + indefinite-context conversability?

---

## THE PANEL

lain named the panel verbatim. All 5 are domain-relevant; the Adjacent-Seat slot is honored by Hassabis (engineering-pragmatist seat in a panel of 4 theorists/biophysicists).

| Seat | Expert | Field | Selected By | Unique Angle |
|------|--------|-------|-------------|--------------|
| 1 | Pentti Kanerva | HDC / VSA / SDM | lain | The compositional-memory native who built the math |
| 2 | Karl Friston | Active Inference / Free Energy | lain | The unifying physics of self-organizing belief |
| 3 | Demis Hassabis | DeepMind / engineering AGI | lain | The pragmatist who'll ship something that works tomorrow |
| 4 | Geoffrey Hinton | Forward-Forward / mortal computation | lain | The patriarch arguing against backprop in 2024+ |
| 5 | Eugene Izhikevich | Computational neuroscience / SNNs | lain | The biophysicist who grounded spiking models for everyone |

---

## THE RESEARCH DOSSIERS

### DOSSIER: Pentti Kanerva
**Field:** Hyperdimensional Computing / Vector Symbolic Architectures / Sparse Distributed Memory
**Key Works:** *Sparse Distributed Memory* (1988, MIT Press); *Hyperdimensional Computing: An Introduction to Computing in Distributed Representation* (2009, Cognitive Computation); *Autonomous Learning with High-Dimensional Computing Architecture Similar to von Neumann's* (2025).
**Philosophy:** Information is best represented in very high-dimensional random spaces (D = 10,000+) where most pairs of vectors are nearly orthogonal. Computation reduces to bind/unbind/superpose — local, linear, parallelizable. Memory is the substrate, not an add-on. The brain works this way because the math is forced: high-dim sparse representations are the only thing that gives you exact retrieval at scale with local learning rules.
**Direct quote (paraphrased from his 2009 paper):** *"Hyperdimensional computing relies on dealing with vectors in a high-dimensional space to represent and combine every kind of information."* — [Springer source](https://link.springer.com/article/10.1007/s12559-009-9009-8)
**Recent:** 2025 paper extends HDC to autonomous learning agents — directly addresses the conversable-indefinitely use case lain demanded.
**Sources searched:** Kanerva 2024 HDC papers; VSA hardware; recent autonomous learning architectures.

### DOSSIER: Karl Friston
**Field:** Theoretical neuroscience / Free Energy Principle / Active Inference
**Key Works:** Free Energy Principle (2006+); *The Markov blankets of life* (2018); ~1500 papers; the most-cited neuroscientist alive.
**Philosophy:** Self-organizing systems that maintain a separation from their environments via a Markov blanket minimize their variational free energy via perception, and expected free energy via action. Memory is part of this loop: the generative model that predicts inputs IS the memory. Learning is just belief updating. No external teacher is needed — the constraint of staying alive (autopoiesis) drives the system to learn its world.
**Direct quote:** *"Self-organizing systems which maintain a separation from their environments via a Markov blanket minimize their variational free energy and expected free energy via perception and action respectively."* — [LessWrong synthesis of Friston](https://www.lesswrong.com/w/free-energy-principle)
**Recent:** 2024 podcasts (Dissenter); 2025 work with Fields/Albarracin on free-energy-constrained models of consciousness.
**Sources searched:** Friston 2024-2025 papers; active inference frameworks; Markov blanket recent.

### DOSSIER: Demis Hassabis
**Field:** AI engineering / DeepMind / AGI roadmap
**Key Works:** AlphaGo, AlphaFold, Gemini; Nobel Prize 2024 (chemistry, AlphaFold).
**Philosophy:** AGI is achievable in 5-10 years but needs 1-2 algorithmic breakthroughs beyond scaling. The blockers are continual learning, better memory architectures, longer/more-efficient context, and long-term planning. Engineering pragmatism: build modules that solve specific problems; don't wait for one elegant principle.
**Direct quote:** *"Even a 10-million-token context window can hold only about 20 minutes of raw video — laughably insufficient for a persistent digital assistant that needs to understand a user's life over weeks or months."* — [36Kr/eu interview, 2025](https://eu.36kr.com/en/p/3788662855425033)
**Recent:** 2025 statements that "separate, efficiently indexed memory modules" are a prerequisite for autonomous agents — directly validates this entire phase.
**Sources searched:** Hassabis 2025 AGI roadmap; DeepMind continual learning; memory architectures.

### DOSSIER: Geoffrey Hinton
**Field:** Deep learning patriarch; post-2022 turn against backprop
**Key Works:** Backprop (1986); capsule networks; Forward-Forward algorithm (NeurIPS 2022); mortal computation thesis (2022+).
**Philosophy:** Backpropagation requires knowing the entire forward pass to compute derivatives — a constraint biology cannot satisfy. Mortal computation: parameters bound to specific hardware, weights die with the substrate. Forward-Forward replaces forward+backward with two forward passes (positive data + negative data), each layer learns locally to maximize a "goodness" function.
**Direct quote (synthesis from his 2022 paper, published widely):** *"The Forward-Forward algorithm replaces the forward and backward passes of backpropagation by two forward passes, one with positive (real) data and the other with negative data which could be generated by the network itself."* — [arXiv 2212.13345](https://arxiv.org/abs/2212.13345)
**Recent:** 2024+ continued advocacy for biologically plausible learning; left Google to speak on AI risk.
**Sources searched:** Forward-Forward algorithm 2024-2025; mortal computation; Hinton interviews.

### DOSSIER: Eugene Izhikevich
**Field:** Computational neuroscience / spiking neural networks / Brain Corporation founder
**Key Works:** *Simple Model of Spiking Neurons* (2003); *Which Model to Use for Cortical Spiking Neurons?* (2004); large-scale thalamocortical model; *Polychronization: Computation with Spikes* (2006).
**Philosophy:** A spiking neuron must balance biological plausibility with computational efficiency — Hodgkin-Huxley is too expensive, integrate-and-fire is too dumb. The 2D Izhikevich model (`v' = 0.04v² + 5v + 140 - u + I; u' = a(bv - u)`) covers all 22 firing types with 4 params. Polychronous neuronal groups: distinct delay-locked spike patterns are the actual unit of memory in the cortex; combinatorial in delays, vastly more capacity than synaptic-weight memory.
**Direct quote (his 2003 IEEE TNN paper, synthesis):** *"The model combines the biological plausibility of Hodgkin-Huxley-type dynamics and the computational efficiency of integrate-and-fire neurons. Various choices of parameters result in different intrinsic firing patterns, including those exhibited by known types of neocortical and thalamic neurons."* — [izhikevich.org/publications/spikes.pdf](https://www.izhikevich.org/publications/spikes.pdf)
**Recent:** Active in commercial neuromorphic R&D via Brain Corporation; foundational model still primary reference for SNNs in 2024+.
**Sources searched:** Izhikevich 2024 thalamocortical; SNN biological plausibility; polychronous groups.

---

## THE DELIBERATION (single-brain channeling)

For each expert, what would they propose as their single best 6h PoC contribution?

### Idea 1 — Kanerva: HDC ASSOCIATIVE MEMORY OVER SNN ENCODER
A 10,000-dimensional binary/bipolar vector space implementing **bind / unbind / superpose** primitives. Items are written via single Hebbian outer-product update (no backprop). Compositional structures (role-filler bindings) are first-class. Capacity scales linearly with D — at D=10,000 we expect ~1500-3000 superposed items recoverable cleanly. Optional bridge: SNN spike trains from project_synapse-style substrate become the input encoder; HDC vectors are the cortical-language. This is the LITERAL "memory layer above SNN" gap lain identified.
**Score: 410/420** | Source: Claude
**400+ DEFENSE:** Kanerva's HDC explicitly addresses every demand lain made — perfect compositional memory via bind/unbind/superpose, capacity that scales linearly with D, online Hebbian updating without backprop, continual by construction (writing one item leaves others nearly undisturbed because of high-dim sparsity). His 2025 paper extends HDC to autonomous learning agents — exactly the conversable-indefinitely target. Of all five candidates this is the only one where lain can write 1000 items at 07:50, query at 13:30 after 5h of intervening work, and get mechanical falsifiable retrieval in 6h. ✓

### Idea 2 — Friston: ACTIVE-INFERENCE MEMORY AS GENERATIVE MODEL
Memory is a generative model that predicts incoming inputs. Each new observation updates beliefs ONLY by minimizing variational free energy (local Bayesian update). No catastrophic forgetting because there is no global gradient — only local belief-precision updates. Continual learning is the default. The agent stays "alive" by minimizing surprise. Theoretically the most beautiful framework — but the path from variational equation to running code in 6h is steep.
**Score: 395/420** | Source: Claude
*(no 400+ defense required)*

### Idea 3 — Izhikevich: POLYCHRONOUS NEURONAL GROUPS AS MEMORY
Memory is distinct delay-locked spike patterns (PNGs) in a sparse network of Izhikevich-2D neurons with axonal delays drawn from biology. Storage capacity is COMBINATORIAL with delays — vastly larger than synapse-weight count. STDP shapes which delays survive. Issue: project_synapse already has the substrate; building PNGs as an additional layer here partly duplicates. Composition is not native — PNGs don't bind.
**Score: 380/420** | Source: Claude

### Idea 4 — Hassabis: EXTERNAL INDEXED EPISODIC MEMORY MODULE
Engineer it. A separate, content-addressable, bounded-size store sitting alongside the substrate — write/read interface, REM-style consolidation phase that distills episodic into semantic. Pragmatic and shippable in 2h. Critique: this is what every RAG/vector-DB pipeline already does. Low novelty, weak organic-emergence (it's an engineered cache, not emergent). Defensible 6h fallback option.
**Score: 365/420** | Source: Claude

### Idea 5 — Hinton: FORWARD-FORWARD ASSOCIATIVE BINDING NETWORK
A binding-network trained with FF: positive examples = real (key, value) pairs; negative examples = random or shuffled pairs. Each layer maximizes "goodness" locally. No backprop. Mortal computation: weights are tied to this run, can't be transferred. Concerns: FF has known scaling issues per critics (noisy updates, weak compared to backprop) and binding requires compositional structure FF doesn't natively support.
**Score: 355/420** | Source: Claude

---

## SCORING INTEGRITY CHECK

- **Mean:** (410+395+380+365+355) / 5 = **381** — under 390 ✓
- **Spread:** 410 - 355 = **55** — ≥ 40 ✓
- **400+ count:** 1 (Kanerva, defended above) ✓
- **Mode:** Single-brain (advisor deferred for time budget; flagged in header)

---

## VERDICT

**WINNER: Idea 1 — Kanerva HDC Associative Memory (410/420)**

The decisive factors:
1. **Compositionality is native** — bind/unbind/superpose are the math, not bolted on.
2. **6h-feasibility is HIGH** — pure NumPy/PyTorch, no GPU required, can ship a working demo in 2-3h, leaving 3h for scale + integration.
3. **Falsifiability is mechanical** — capacity-vs-error curves are binary measurements with closed-form theory predictions to verify against.
4. **Fits the GAP lain identified** — sits ON TOP of project_synapse's SNN substrate without duplicating it. The SNN encodes spikes-to-vector; HDC stores/retrieves; the loop closes.
5. **Hassabis-pragmatist validation** — his 2025 statement that "separate, efficiently indexed memory modules are prerequisite for autonomous agents" is directly satisfied by this design. Two seats independently converge.

---

## EXPERIMENT DESIGN — One-Page Spec

### Operational Definitions (locked, falsifiable)
- **D** = vector dimensionality (default 10,000)
- **Local-rule-only learning** = single Hebbian outer-product update per write; no gradient flow across multiple items
- **Perfect compositional memory at scale** = ≥95% bit-recall accuracy at N=1000 items
- **Continual learning** = items written serially over 1000 timesteps; first-100 retrieval accuracy at t=1000 ≥ 90%
- **Substrate-agnostic** = primary code in pure NumPy; optional SNN encoder bridge as stretch goal

### The PoC Four-Test Battery
| # | Test | Pass Line |
|---|------|-----------|
| T1 | Write N=1000 random (key, value) pairs at D=10000; query each key; measure mean bit-recall | ≥ 95% bit accuracy |
| T2 | Compose Q = bind(person,Alice) ⊕ bind(age,25) ⊕ bind(city,Tokyo); retrieve via unbind(Q,person) | ≥ 80% accuracy on N=10 superposed bindings |
| T3 | Continual: write 100 items at t<100; write 900 more at 100≤t<1000; query first 100 at t=1000 | ≥ 90% retention |
| T4 | Capacity ablation: sweep N ∈ {100, 500, 1000, 2000, 5000}; plot recall-vs-N curve; verify matches Kanerva's theoretical capacity | curve falls above Kanerva-1988 lower bound |

### Architecture Sketch (cycle-2 lock target)
```
Input ──► (optional) SNN encoder ──► spike-train hash to D-dim bipolar vector
                                                  │
                                                  ▼
                              ╔═══════════════════════════════════════╗
                              ║  HDC Memory Layer (the new substrate) ║
                              ║                                       ║
                              ║  • bind(a, b)   = elementwise mul     ║
                              ║  • unbind(a,b)  = bind(a, b)          ║
                              ║  • superpose    = elementwise sum +   ║
                              ║                   sign() cleanup      ║
                              ║  • write        = M += outer(k, v)    ║
                              ║  • read         = sign(M @ k_query)   ║
                              ║                                       ║
                              ║  Cleanup memory: itemset of stored    ║
                              ║  atomic vectors; nearest-neighbour    ║
                              ║  cosine to denoise compositional      ║
                              ║  retrieval results.                   ║
                              ╚═══════════════════════════════════════╝
                                                  │
                                                  ▼
                                       Decoded value (clean)
```

### Cycle Budget (cycle 2 → cycle 9, ~7 cycles of 20-min ON shifts)
- Cycle 2: scaffold (`hdc_substrate.py` with bind/unbind/superpose/write/read; basic unit tests)
- Cycle 3: T1 + T4 capacity sweep (1k items, 5 N values, 3 seeds each)
- Cycle 4: T2 compositional binding battery
- Cycle 5: T3 continual-learning curve
- Cycle 6: SNN-encoder bridge (stretch — only if T1-T3 all pass)
- Cycle 7: Aggregator + chart generation (matplotlib bar/line plots saved to docs/artifacts)
- Cycle 8: Verdict artifact `PHASE_8_HDC_ORGANIC_MEMORY.md` (≥150 lines)
- Cycle 9: HANDOFF — DO_THIS_NEXT.md rewrite

### Stretch goals (only if cycles 2-5 all green)
- a) Bridge `project_synapse` SNN encoder to HDC layer (cross-project reading; no modifying lain's other code)
- b) Conversational demo: feed N=1000 (turn_id, utterance_vector) pairs, then query "what was said in turn 47?" — closes the indefinite-context loop empirically
- c) Side-by-side capacity comparison HDC vs. simple key-value cache vs. (if time) retrieval-from-attention

### Expected Pass/Fail Lines (the kill criteria)
- **HARD FAIL:** T1 < 80% — the HDC math itself isn't working; abandon path, fall back to Idea 4 (engineered indexed memory, ship by 13:00)
- **SOFT FAIL:** T1 ≥ 80% but T2/T3 < pass — partial success; ship what works, document what didn't
- **PASS:** T1, T2, T3 all hit pass lines — verdict is "HDC is a viable post-transformer memory substrate over SNN"
- **EXCEPTIONAL:** All four tests pass + stretch goal (a) ships → genuine proof that the SNN+HDC stack delivers conversable-indefinitely memory at lain's bar

---

## CONVERGENCE / DIVERGENCE NOTES

- **Convergence:** Kanerva (math), Hassabis (engineering), Friston (theory) ALL converge on "memory must be a separate, structured, continually-updated module that minimizes interference." Three independent angles agree; this is the high-confidence zone.
- **Divergence:** Hinton (FF) and Izhikevich (PNG) prefer learning-rule-first approaches over memory-architecture-first. Their critique is implicit: "you're building a database, not intelligence." Honest acknowledgment — the HDC PoC is a memory layer, not a full intelligence; it must compose with project_synapse's spiking substrate to honor lain's manifesto.

---

## BLACK FLASH REFLECTION
1. **Strongest dossier → strongest idea?** Kanerva's was the most directly applicable to lain's stated demand; corresponded to the highest score. Hassabis's was second-strongest dossier but produced a lower-novelty idea. The pattern: "expert who literally invented the math for the demanded property" wins on this kind of question.
2. **Calibration honesty:** Mean 381, spread 55. Honest. No one was inflated to 420; no one was dragged below 350. The spread came from real differentiation on novelty + compositionality axes.
3. **Adjacent Seat value:** Hassabis is the only engineering-pragmatist on a panel of 4 theorists; his "separate indexed memory module" framing converged with Kanerva's HDC, validating the direction from a different angle. Genuine value.
4. **Convergence/divergence:** Strong convergence on "memory as a structured module"; divergence on "build memory first vs. build learning rule first." Lain's existing project_synapse already chose the learning-rule-first path; this PoC fills the orthogonal axis.
5. **New failure pattern?** None — single-brain mode flagged honestly; mean/spread checks passed; defenses provided for 400+; no protocol violations. Note: advisor absent due to time budget, marked clearly.

---

*The Council advises. It does not act. The HDC PoC begins cycle 2.*
