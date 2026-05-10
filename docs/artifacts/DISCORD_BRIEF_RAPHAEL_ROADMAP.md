# Discord Brief - Project X Roadmap To Raphael

lain - Phase 8 is now reviewed with hostile eyes and the Phase 9+ roadmap is written.

The clean verdict: Phase 8 is real, but it must be framed precisely. It proved a bipolar HDC associative memory layer. It did not prove semantic chat memory or a full agent. The best evidence is the capacity cliff: D=10k gives perfect recall at N=200, collapses past capacity, then D=50k/D=100k push the cliff right exactly as theory predicts. The D=50k synthetic conversation demo hit 99.25% recall at 1000 turns with a 195 KB accumulator, but those "utterances" were random vocab atoms, not natural language semantics.

What that means: the memory spine candidate is legitimate. The next proof must be semantic.

Eight councils were written as SINGLE-BRAIN councils because advisor/Discord tools are not available in this Codex harness and I will not fake separate expert agents. They are still evidence-backed and scored:

1. **Hardware:** mixed stack wins. llama.cpp/GGUF for local generator, Python/PyTorch for reference memory, Triton only after profiling proves semantic HDC works.
2. **Encoder:** BGE-small/MiniLM + projection wins. Do not block Phase 9 on a pure SNN encoder; project_synapse comes back after the semantic bridge exists.
3. **Controller:** deterministic state machine wins. The LLM proposes, the controller validates and owns state.
4. **Generator:** local Q4/Q5 7B-8B LLM wins. Use it as speech/action surface, not as the whole mind.
5. **Memory dynamics:** sparse writes + provenance + replay wins. Do not implement forgetting as deletion first.
6. **Tool use:** schema-first action ledger wins. Every tool call becomes structured evidence.
7. **Self-modification:** sandbox-and-replace wins. No live self-editing; proposal, patch, benchmark, accept/reject.
8. **Beyond-human cap:** branch-and-verify cognition wins. No-cap means external memory, tools, parallel futures, replay, and measured self-improvement, not hype.

The roadmap says Phase 9 should be **Semantic HDC Memory Agent**.

Do not do Triton first. Do not do pure SNN encoder first. Do not do self-modification first. Do not just wrap a local LLM and call it Raphael.

Phase 9 target:

```text
real text turns
  -> small sentence embedder
  -> random/sign projection into HDC
  -> HDC write/read
  -> provenance store
  -> evidence packet
  -> mock or local generator
  -> source-cited answer
```

Mechanical Phase 9 pass lines:

- `PYTHONPATH=src pytest -q` green.
- HDC self-test green.
- exact turn lookup >=95% at 1000 turns.
- semantic top-5 recall >=80% on >=200 labeled queries.
- false-positive rate <=10% on absent-answer queries.
- 100% of answered retrievals cite source turn IDs.
- HDC beats keyword baseline on semantic paraphrase queries.
- dense vector list baseline is reported honestly, even if it wins.
- test mode completes in <=180 seconds.
- VRAM stays below 13.9 GB if GPU is used.

Important files now:

- `docs/artifacts/PHASE_8_HOSTILE_REVIEW.md`
- `docs/artifacts/COUNCIL_G_HARDWARE_STACK.md`
- `docs/artifacts/COUNCIL_A_ENCODER.md`
- `docs/artifacts/COUNCIL_C_CONTROLLER.md`
- `docs/artifacts/COUNCIL_B_GENERATOR.md`
- `docs/artifacts/COUNCIL_D_MEMORY_DYNAMICS.md`
- `docs/artifacts/COUNCIL_E_TOOL_USE.md`
- `docs/artifacts/COUNCIL_F_SELF_MODIFICATION.md`
- `docs/artifacts/COUNCIL_H_BEYOND_HUMAN_CAP.md`
- `docs/artifacts/ROADMAP_TO_RAPHAEL.md`
- `docs/A_TO_Z_PLAN.md`
- `docs/DO_THIS_NEXT.md`

The shortest path to Raphael:

```text
Phase 9  - semantic HDC memory agent
Phase 10 - memory dynamics
Phase 11 - tool-using Raphael loop
Phase 12 - sandbox self-improvement harness
Phase 13 - branch-and-rank cognition
Phase 14 - hard general benchmarks
Phase 15 - SNN/HDC/Triton convergence
Phase 16 - Raphael proper
```

The architecture is hybrid by necessity:

```text
local quantized generator
+ pretrained semantic encoder
+ HDC associative memory
+ deterministic controller
+ provenance store
+ schema-first tools
+ replay consolidation
+ benchmarked self-improvement
+ later SNN/Triton substrate convergence
```

This preserves the no-cap direction without pretending Phase 8 already solved the whole stack.

Decision points for you:

1. Do we use BGE-small-en-v1.5 as the first full-mode encoder, with MiniLM as fallback, or do you want MiniLM first for speed?
2. Do we keep Phase 9 generator mocked until retrieval passes, or wire llama.cpp immediately for a demo loop?
3. Do you want Phase 9 to include a small visible CLI chat demo, or keep it benchmark-only until the metrics are green?

My recommendation:

Use BGE-small first, mock generator first, then add llama.cpp after semantic retrieval passes. Build the memory spine before dressing it in a voice.

