# A To Z Plan - Project X - Phase 9 - Semantic HDC Memory Agent

**Date opened:** 2026-05-09  
**Previous phase archived:** `docs/past_work/phases/phase_8_beyond_transformer_organic_memory.md`  
**Phase theme:** real text -> **from-scratch ORGANIC encoder** (no pretrained LLM) -> HDC memory -> source-cited retrieval -> minimal evidence-cited answer loop.
**Hardware cap:** RTX 5070 Ti, 13.9 GB usable VRAM max, i9 CPU, tight WSL RAM.
**lain constraint (2026-05-09 17:53 CEST, Discord):** *"slow and methodical path... organic and real from the core and the beginning. No borrowing other LLM models, remember, we are moving past the transformer."* This **disqualifies** BGE, MiniLM, sentence-transformers, llama.cpp, Qwen, Mistral, and every pretrained transformer derivative. Encoder MUST be from-scratch (char-n-gram hashing, Hebbian co-occurrence, SNN spike-train, or equivalent). Generator slot = template-based composition from evidence text until a from-scratch generator exists in a later phase. See `docs/artifacts/PHASE_9_PICK_ONE_VERDICT.md` ADDENDUM.

---

## PHASE CHANGELOG

- `phase_number`: 9
- `active_phase_theme`: semantic_hdc_memory_agent
- `phase_entry_reason`: Phase 8 proved random-symbol HDC memory. Phase 9 must prove semantic retrieval and minimal agent use.
- `previous_phase_doc`: `docs/past_work/phases/phase_8_beyond_transformer_organic_memory.md`
- `hostile_review`: `docs/artifacts/PHASE_8_HOSTILE_REVIEW.md`
- `roadmap`: `docs/artifacts/ROADMAP_TO_RAPHAEL.md`
- `council_inputs`:
  - `docs/artifacts/COUNCIL_G_HARDWARE_STACK.md`
  - `docs/artifacts/COUNCIL_A_ENCODER.md`
  - `docs/artifacts/COUNCIL_C_CONTROLLER.md`
  - `docs/artifacts/COUNCIL_B_GENERATOR.md`
  - `docs/artifacts/COUNCIL_D_MEMORY_DYNAMICS.md`
  - `docs/artifacts/COUNCIL_E_TOOL_USE.md`
  - `docs/artifacts/COUNCIL_F_SELF_MODIFICATION.md`
  - `docs/artifacts/COUNCIL_H_BEYOND_HUMAN_CAP.md`
- `cycle_position_in_phase`: **PHASE 9 SHIPPED — all 6 cycles complete.** Layer 4 agent loop + template composer + Phase 9 verdict artifact (`docs/artifacts/PHASE_9_SEMANTIC_HDC_MEMORY.md`) + handoff staging (`docs/DO_THIS_NEXT.md`). 39 pytest pass. End-to-end demo runs: agent answers cite turn IDs via template composer with NO LLM. Critical §3 acceptance (HDC > keyword baseline on paraphrase) PASSED.

**Phase 10 ENTRY (revised after external code review 2026-05-09 evening):** PHASE NAME shifted from "Memory Dynamics" to "memory_action_organism" — reviewer's killer-milestone framing adopted as exit gate. Six P1-P6 priorities: (P1) fix dataset contradiction-label bug — was loosely-known, reviewer probed and found 29/30 contradiction queries spurious, headline contradiction metric is corrupted; (P2) strengthen tests on critical claims — current tests assert shape not semantic correctness; (P3) Fact Graph + HDC Binding Hybrid — Council Idea #1 reshapes prior "HRR-binding" plan; (P4) incremental write + replay consolidation — Council Idea #4 extends prior "incremental write"; (P5) absent-answer threshold sweep + ensemble-disagreement gating — formal sweep replaces "needs calibration" caveat; (P6) quarantine legacy transformer code in `src/project_x/model.py`. EXIT GATE: `tests/test_killer_milestone.py` passes 5-action acceptance (teach fact + resolve correction + multi-hop with citations + refuse absent + tool execution + write-back). Council Ideas #2/#3/#5 (cortical column / predictive simulation / open-ended benchmark) DEFERRED to Phase 11/12/13+. M-PROJECTX-012 logged on the defer-the-probe trap. Full plan: `docs/DO_THIS_NEXT.md`.

**Phase 10 CLOSED (live):** Cycles 1-8 closed 2026-05-10. **51/51 pytest (+12 net new from Phase 9 baseline 39).** Every #00 deliverable from the corpse mechanically shipped + verified. P1 ✅ (#00a contradiction-label fix); P2 ✅ (#00e test depth strengthened); P3 fact-graph half ✅ (#00c-1 structural retrieval — 5-seed: exact top-5 99.6%, paraphrase top-5 80.8%, multi-hop top-5 91.3%, contradiction top-1 100%; Phase 9 near-miss thresholds CLEAN PASS); P3 binding half ✅ (#00c-2 HDC role-filler binding — write-time `bind(turn_vec, atom_subject)` superposed into per-subject bank; `unbind_subject_pseudo_vec` provides Plate-style structural retrieval; 2 new tests verify unbinding recovers subject-specific signal at unit scale; corpse-spec hybrid now complete); P4 ✅ (#00d incremental write + Hebbian replay consolidation; binding bank also extends on `write_one`); P5 ✅ (#00b absent-answer threshold sweep — empirical best thr=0.32 fp=9.3% survival=93.5% F1=0.9585 targets MET; reviewer's ensemble-disagreement empirically not useful at this scale); P6 ✅ (#00f legacy transformer quarantined to `src/project_x/legacy/`); EXIT GATE ✅ (#00g killer-milestone — `tests/test_killer_milestone.py` 6 tests passing — teach + correct + multi-hop + refuse-absent + tool-exec-writeback + full integration). **Phase 10 work complete; awaiting lain ack to flip phase counter and open Phase 11.**
- `test_mode_requirement`: `--mode test` completes in <=180 seconds
- `minimum_evidence`: scripts + result JSON + short interpretation

---

## 0. Phase 9 Thesis

The next proof is semantic, not larger.

Phase 8's killer demo:

```text
D=50000
1000 synthetic turns
vocab=200 random utterance atoms
99.25% recall
195 KB accumulator
```

That is a real HDC capacity result. It is not yet a real conversation-memory result.

Phase 9 must answer:

```text
Can HDC retrieve useful evidence from real text conversations, cite source turns,
and feed a generator/controller loop under the RTX 5070 Ti hardware cap?
```

If yes, Project X has a viable memory spine for Raphael.

If no, HDC remains a strong symbolic associative memory but needs another semantic grounding mechanism.

---

## 1. Architecture

### Phase 9 Components

```text
src/project_x/experiments/
  semantic_memory_dataset.py     # synthetic-real conversation generator + labels
  semantic_hdc_memory.py         # embed -> project -> write/read/retrieve
  semantic_memory_agent.py       # minimal controller + generator stub
  generator_client.py            # mock/local-LLM boundary
  phase9_report.py               # aggregation/report helper
```

Tests:

```text
tests/test_semantic_hdc_memory.py
tests/test_semantic_memory_agent.py
```

Artifacts:

```text
gpt-codex/runs/phase9_*/result.json
docs/artifacts/PHASE_9_SEMANTIC_HDC_MEMORY.md
```

### Data Flow

```text
conversation turn
  -> from-scratch ORGANIC encoder
       (char-n-gram + hash + projection  OR  Hebbian co-occurrence
        OR  SNN spike-train  — never a pretrained transformer)
  -> bipolar HDC vector (D-dim)
  -> bind turn_id / fact_key / speaker_key
  -> write HDC accumulator
  -> store raw text + metadata in JSONL/SQLite
```

Query:

```text
question
  -> SAME organic encoder
  -> retrieve candidate HDC memories
  -> resolve source text
  -> build evidence packet
  -> template-based composition cites source turn IDs
     ("Based on turn {ids}: '{evidence text}'.")
     NO pretrained LLM generator
```

---

## 2. Dependency Graph

### Layer 0 - Preflight

1. Fix existing import-path regression in `compressed_memory.py`.
2. Verify `PYTHONPATH=src pytest -q` passes.
3. Verify HDC self-test still passes.
4. Record baseline hardware snapshot.

### Layer 1 - Dataset

1. Build synthetic-real conversation generator.
2. Include named facts, preferences, decisions, file paths, contradictions, and absent-answer queries.
3. Produce labeled query set:
   - exact turn lookup
   - semantic paraphrase
   - multi-hop
   - contradiction
   - absent-answer

### Layer 2 - Organic Encoder (NO pretrained LLM — lain 2026-05-09)

1. Implement `OrganicEncoder` protocol.
2. **Floor:** `CharNgramHashEncoder` — character n-grams → hash bucket → multi-hot → random Gaussian projection → sign → bipolar HDC. No learning. Deterministic.
3. **Semantic step:** `HebbianCooccurrenceEncoder` — words as random HDC atoms; sentence-co-occurrence superposition pass; sentence encoding = bound superposition of (now-correlated) word atoms.
4. **Substrate path (later cycles):** extend `hdc_snn_bridge.py` LIF encoding to take char-level / byte-level driven input; calibrate cross-input cosine to near-zero; that becomes the SNN organic encoder.
5. Measure orthogonality and semantic neighborhood preservation per encoder variant.

### Layer 3 - Memory

1. Implement semantic write.
2. Implement exact turn lookup.
3. Implement semantic top-k retrieval.
4. Store provenance metadata.
5. Add baselines:
   - keyword/metadata search
   - explicit dense vector list
   - HDC accumulator

### Layer 4 - Agent Loop (NO pretrained LLM)

1. Minimal controller decides read/write.
2. Evidence packet constructed from retrieval.
3. **Template composer** answers from evidence (no LLM): format = `"Based on turn {ids}: '{evidence text}'."` for found facts; `"No evidence found in conversation memory."` for absent_answer queries.
4. Generator interface (`AnswerComposer`) is left in place as a swap-point for a future from-scratch generator phase. NOT a llama.cpp/Qwen wrapper.
5. Every answer cites turn IDs.

### Layer 5 - Report

1. Aggregate results.
2. Write `PHASE_9_SEMANTIC_HDC_MEMORY.md`.
3. Update `docs/DO_THIS_NEXT.md`.

---

## 3. Acceptance Criteria

Phase 9 passes only if all are true:

- `PYTHONPATH=src pytest -q` passes.
- `PYTHONPATH=src python3 -m project_x.experiments.hdc_substrate --self-test` passes.
- Exact turn lookup >=95% at 1000 turns.
- Semantic top-5 recall >=80% on >=200 labeled queries.
- False-positive rate <=10% on absent-answer queries.
- Evidence citation rate = 100% for answered retrievals.
- HDC beats keyword baseline on semantic paraphrase queries.
- Dense vector list baseline is reported, even if it wins.
- Result JSONs include wall time, memory bytes, model names, seeds, D, query counts.
- VRAM stays under 13.9 GB if GPU used.
- Test mode completes in <=180 seconds.

Breakthrough claims require >=1000 evaluated queries.

---

## 4. Kill Criteria

Stop or reframe if:

- semantic top-5 recall <50% after two encoder/projection variants
- false-positive rate >25% after threshold calibration
- provenance citation cannot be made reliable
- full mode OOMs WSL repeatedly
- HDC performs no better than keyword search on semantic paraphrase

If killed, fallback is not "abandon memory." Fallback is:

```text
dense vector DB / explicit vector list + HDC as compositional/fact memory adjunct
```

---

## 5. Cycle Plan

### Cycle 1 - Preflight + Dataset

- Fix import-path bug.
- Add dataset generator.
- Add labels for >=200 test queries.
- Run smoke benchmark in test mode.

Exit:

- pytest green
- dataset result JSON written

### Cycle 2 - Encoder + Projection

- Add embedder interface.
- Add deterministic fallback encoder.
- Add BGE/MiniLM full-mode option.
- Add projection stats.

Exit:

- pairwise HDC cosine distribution reported
- semantic nearest-neighbor sanity green

### Cycle 3 - HDC Retrieval

- Write semantic HDC memory class.
- Implement exact and semantic retrieval.
- Add dense vector and keyword baselines.

Exit:

- exact lookup and semantic retrieval metrics in result JSON

### Cycle 4 - Minimal Agent Loop

- Add controller.
- Add evidence packet.
- Add mock generator.
- Optional local LLM adapter.

Exit:

- agent answers memory questions with source turn IDs

### Cycle 5 - Full Sweep

- Run 1000-turn benchmark.
- Run >=200 query labels.
- Run ablations over D and encoder.
- Record hardware metrics.

Exit:

- pass/fail verdict known

### Cycle 6 - Report + Handoff

- Write Phase 9 artifact.
- Update roadmap if council assumptions changed.
- Rewrite `DO_THIS_NEXT.md`.

Exit:

- docs synced
- next phase decision written

---

## 6. Hardware Budget

Default test mode:

- `CharNgramHashEncoder` (organic, deterministic, no models)
- D=10k
- 100-200 turns
- <=50 queries
- CPU only
- <=180 seconds

Default full mode:

- `CharNgramHashEncoder` baseline + `HebbianCooccurrenceEncoder` semantic
- D in {10k, 50k, 100k}
- 1000 turns
- >=200 queries
- CPU only (no GPU needed for these encoders)
- **NO** local LLM. **NO** pretrained transformer. Both disqualified by lain 2026-05-09.

Optional substrate mode (Phase 10+):

- SNN spike-train encoder via `hdc_snn_bridge` calibration
- project_synapse SNN integration (Phase 12+)
- Triton kernels for HDC cleanup (Phase 15)

---

## 7. Result Schema

```json
{
  "run_id": "phase9_semantic_hdc_seed1337",
  "mode": "test|full",
  "config": {
    "encoder": "char_ngram_hash|hebbian_cooccurrence|snn_spike_train",
    "D": 50000,
    "n_turns": 1000,
    "n_queries": 200,
    "seed": 1337
  },
  "metrics": {
    "exact_turn_recall": 0.0,
    "semantic_top1": 0.0,
    "semantic_top5": 0.0,
    "false_positive_rate": 0.0,
    "citation_rate": 1.0,
    "wall_seconds": 0.0
  },
  "baselines": {
    "keyword": {},
    "dense_vector_list": {},
    "hdc": {}
  },
  "hardware": {
    "ram": {},
    "vram": {}
  },
  "samples": []
}
```

---

## 8. Non-Goals

Phase 9 does not:

- train a new LLM
- build full JARVIS UI
- implement self-modification
- port HDC to Triton
- replace sentence embeddings with SNN
- claim AGI

Those are later phases.

---

## 9. Definition Of Done

Phase 9 is done when the repo contains:

- runnable semantic memory code
- green tests
- result JSONs
- comparison baselines
- hardware metrics
- source-cited demo answers
- written verdict artifact
- updated handoff

The final question to answer:

```text
Did HDC become useful for real conversation memory, or only for random symbolic memory?
```

