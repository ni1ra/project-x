# Do This Next - Project X - PHASE 10 CLOSED (awaiting lain ack)

**Updated:** 2026-05-10 (Cycle 8 close — #00c-2 HDC binding-half SHIPPED; corpse-spec hybrid complete; pytest 51/51 +12 from baseline)
**Status:** **Phase 10 mechanically closed.** All #00 deliverables from the Maki Zen'in corpse shipped + verified. Awaiting lain ack to flip phase counter and provide Phase 11 framing (Council Idea #2 cortical column ensemble per the deferred plan, or new direction).
**Active phase:** 10 — `memory_action_organism` (reshaped from earlier "Memory Dynamics" plan after external review).
**Prev verdict:** `docs/artifacts/PHASE_9_SEMANTIC_HDC_MEMORY.md` + Phase 10 P1 corrective addendum at bottom (added 2026-05-10) — contradiction headline of Phase 9 was artifact-of-bug; ensemble underperforms keyword on contradiction post-fix; critical paraphrase claim still passes.

---

## 0. What changed since Phase 9 closed

A single-brain external code review (2026-05-09 evening) probed the shipped Phase 9 stack and surfaced six concrete gaps + five council ranked ideas. Validation (this instance):

- **6 gaps — all valid; included as Phase 10 P1-P6.**
- **Council Idea #1 (Fact Graph + HDC Binding Hybrid)** — included as Phase 10 P3 (the multi-hop fix; reshapes prior "HRR-style binding" plan).
- **Council Idea #4 (Incremental Hebbian Replay)** — included as Phase 10 P4 (extends prior "incremental write" plan with replay consolidation).
- **Council Ideas #2, #3, #5 (cortical column ensemble, predictive simulation loop, open-ended benchmark ladder)** — DEFERRED to Phases 11/12/13+. Sequencing them after the current Phase 10 work is the right order; doing them in parallel risks scope explosion.
- **"Killer milestone"** (reviewer's strong opinion) — adopted as Phase 10 EXIT GATE.

Wiki entry M-PROJECTX-012 logged: I documented the contradiction-label bug only loosely; the reviewer's empirical probe found it had compromised the headline metric (29/30 spurious contradiction queries). Rule going forward: a metric whose dataset has a known issue gets either an in-cycle probe or an in-verdict caveat — never both deferred.

---

## 1. Phase 10 Priorities (reviewer-informed, in execution order)

### P1: ✅ CLOSED 2026-05-10 — Fix the dataset contradiction-label bug
**Files patched:** `src/project_x/experiments/semantic_memory_dataset.py:457` (`build_queries()`) + `:559` (`run_dataset` `n_superseded_facts` metric).
**Fix:** replaced `len(history) > 1` with a walk over `turns` collecting fact_keys for any turn whose `supersedes_turn_id is not None`, then intersect with `fact_map.items()`.
**Mechanical proof:**
- `pytest -q`: 39/39 pass (baseline preserved).
- 5-seed dataset regen (1337/2026/3001/4042/5050): pool size unanimously 5 (was 35); per-seed `n_superseded_facts` = 5.
- 5-seed benchmark sweep saved at `gpt-codex/runs/phase10_p1_contradiction_fix/run_seed{N}/result.json`; aggregate at `gpt-codex/runs/phase10_p1_contradiction_fix/result.json`.
- **Headline:** ensemble contradiction top-1 collapses 0.30 (single-seed claim) → 0.0 ± 0.0 (5-seed mean). Ensemble UNDERPERFORMS keyword by −13.3pp on contradiction post-fix. Phase 9 verdict received corrective addendum.
- **Implication:** Phase 9's HDC ensemble does NOT solve contradiction-resolution. P3 (fact-graph + HDC binding) becomes the candidate fix for both multi-hop AND contradiction (role-filler binding gives a mechanism for temporal-decay weighting on the role atom).

### P2: Strengthen tests on critical claims
**Files:** all `tests/test_*.py`.
**Bug:** several tests assert structural/shape only, not semantic correctness. Examples:
  - `test_multi_hop_decomposition_runs_and_returns_results` only checks `len(top) > 0`
  - Tests don't assert that the EXPECTED turn IDs appear in top-k for retrieve/contradiction/absent
**Fix:** for each query type, write a test that asserts the actual expected behavior:
  - retrieve: expected turn_id is top-1 OR top-5
  - multi-hop: BOTH expected turn_ids appear in top-5
  - contradiction (after P1 fix): the LATEST turn wins
  - absent_answer (after P5 fix): `decision == "absent"` and no false-positive evidence
**Why second:** catches regressions you'd otherwise ship during P3-P6.

### P3: Fact Graph + HDC Binding Hybrid (Council Idea #1)
**Files:** `src/project_x/experiments/semantic_hdc_memory.py` (Layer 3 surgery).
**Architectural lift:** on memory write, parse turn into structured fact `{subject, relation, object, time, source}` AND bind subject/relation/object atoms with the turn vec via Phase 8's `bind` primitive. On retrieval:
  - Decompose multi-hop query into per-subject sub-queries (e.g. "What do Alice and Bob prefer?" → "What does Alice prefer?" + "What does Bob prefer?")
  - Retrieve per-subject via subject-atom unbinding (Plate-style structural retrieval), then ensemble cosine for ranking
  - Union with citations
**Target:** multi-hop top-5 from 3.3% → ≥25%. Baseline preserved for non-multi-hop queries.

### P4: Incremental write + replay consolidation (Council Idea #4)
**Files:** `src/project_x/experiments/semantic_memory_agent.py:166`, `random_index_hebbian.py`.
**Bug:** `MemoryAgent.process` no-ops on assertions (returns "noted; deferred").
**Fix:**
  - Implement `MemoryAgent.process` write path: encode turn, append to memory, update fact-graph (per P3), bind into HDC accumulator. No batch rebuild.
  - Add periodic replay consolidation: every N writes (configurable), re-binarize trained word vectors against the current accumulator (a Hebbian "sleep" pass).
**Target:** 50-turn interactive sequence (alternating write + retrieve) passes a correctness test.

### P5: Absent-answer threshold sweep + ensemble-disagreement gating
**Files:** `src/project_x/experiments/semantic_memory_agent.py` (compose_answer threshold), `semantic_hdc_memory.py` (gating mechanism).
**Bug:** cosine-thresholding alone has a precision-recall pareto front (reviewer found: thr=0.25 → 53.3% FP; thr=0.32 → 0% FP but 31.2% real-answer drop).
**Fix:**
  - Formal threshold sweep on a held-out absent_answer subset (0.20 → 0.40 in 0.02 steps); pick best F1.
  - **NEW:** ensemble-disagreement gating: when CharNgram-floor top-1 turn ≠ RIHV-Hebbian top-1 turn, confidence is low → likely absent. Combine with threshold.
  - Report whether disagreement-gating + threshold combined beats threshold-alone on the F1 metric.
**Target:** absent_answer false-positive rate ≤10% AND real-answer survival ≥60% (replaces "not formally measured" from Phase 9 verdict).

### P6: Quarantine legacy transformer code
**Files:** `src/project_x/model.py:27` (legacy transformer-style scaffolding from Phase 1-6).
**Fix:** move to `src/project_x/legacy/transformer_scaffolding.py` + module-level docstring: *"LEGACY — Phase 1-6 transformer scaffolding kept as historical control. NOT part of the organic Phase 9+ stack. Do not import from this module in any organic-thesis code."* Update any imports to point at the new location. Run pytest to verify no breakage.
**Why last:** quick polish; do after architectural changes settle so nothing breaks mid-flight.

### EXIT GATE: Killer Milestone Test
**File (new):** `tests/test_killer_milestone.py`.
**Acceptance:** scripted end-to-end sequence demonstrates ALL 5 capabilities:
  1. **Teach a new fact incrementally** — `agent.process("Alice now prefers Rust.")` writes without batch rebuild.
  2. **Resolve a correction** — subsequent `agent.process("Actually Alice switched to Java.")` makes the LATEST value win on retrieval.
  3. **Multi-hop with citations** — `agent.process("What do Alice and Bob prefer?")` returns BOTH turn_ids.
  4. **Refuse an absent fact** — `agent.process("What does Ghost9999 prefer?")` returns `decision="absent"` with no false-positive evidence.
  5. **Tool execution + write-back** — agent runs a deterministic local tool (e.g., `read_file('/some/path')`), captures the result, writes it as a new memory turn.
Test passing IS the Phase 10 exit gate. Until then, Phase 10 is open.

---

## 2. Deferred (Phase 11+ bookmarks)

- **Phase 11 candidate:** Cortical Column Ensemble (Council Idea #2 — Hawkins/Numenta direction). Many sparse HDC modules with voting; do AFTER P3 fact-graph proves the structural-retrieval direction.
- **Phase 12+ candidate:** Predictive Simulation Loop (Council Idea #3 — LeCun world-model direction). Requires forward-modeling capability not yet built.
- **Phase 13+ candidate:** Open-Ended Benchmark Ladder (Council Idea #5 — Stanley/POET direction). Meta-priority on testing methodology; meaningful only after the agent can do tool execution + memory updates (i.e., after Phase 10 exit).

---

## 3. Standing constraints (carried from Phase 9)

- **NO pretrained transformers.** No BGE, MiniLM, llama.cpp, Qwen, sentence-transformers. Encoders + generators stay from-scratch organic.
- **`advisor()` is the second-mind validator.** Oracle / Six-Eyes / shrine-council all DEPRECATED 2026-05-09 (3 files deleted, ~78 swept; `commands/shrine-council.md`, `agents/oracle-runner.md`, the backup all gone).
- **Listener manual re-arm.** Auto-rearm broken in WSL bash sandbox per memory rule.
- **No git repo.** `git status` returns "not a git repository". Open question for lain at session start: `git init` for Phase 10 or stay flat?

---

## 4. Open questions for lain

1. `git init` for Phase 10? (Currently no repo. Posted to Discord cycle-open 2026-05-10; default-acting is "stay flat" until override. P1 already shipped under stay-flat assumption.)
2. Where to write the killer-milestone tool runtime — extend `MemoryAgent` or new `ToolRuntime` class? (Becomes load-bearing at #00g EXIT GATE; not yet at P4 unless replay-consolidation needs the same plumbing.)
3. Replay consolidation cadence — every N=50 writes? Every N tokens? On idle? (Becomes load-bearing at P4 / #00d.)

### P2: ✅ CLOSED 2026-05-10 — Strengthen test depth (4 sub-tasks)
**Files patched:** `tests/test_semantic_hdc_memory.py`, `tests/test_semantic_memory_agent.py`. Multi-hop assertions strengthened to BOTH turn_ids (was `len(top)>0`); retrieve + question assertions sharpened to top-1/top-5 turn_id checks (was always-true `turn_id in [0,1,2,3]`); contradiction LATEST-wins test added (xfail at P2, flipped GREEN at P3); absent_answer agent-level assertion added at threshold=0.30 (passes at unit scale). Pytest baseline 39 → 42 (+3 net new with depth, no relaxation).

### P3: ✅ CLOSED 2026-05-10 (fact-graph half #00c-1; binding-half #00c-2 awaits lain) — Fact Graph structural retrieval
**Files patched:** `src/project_x/experiments/semantic_hdc_memory.py` (write-time fact_graph + `_structural_cosines` + `retrieve_structural` + `retrieve_multi_hop` reshape + benchmark `with_structural` track), `src/project_x/experiments/semantic_memory_agent.py` (agent.process switched to structural path).
**Mechanical proof — 5-seed mean ± std on seeds 1337/2026/3001/4042/5050:**
- exact top-1: 62.0% → **94.8% ± 2.6%** (Phase 9 near-miss threshold ≥95% top-5 now CLEAN PASS at 99.6%)
- paraphrase top-1: 51.7% → **77.8% ± 5.8%** (top-5 80.8% — Phase 9 near-miss threshold ≥80% now CLEAN PASS)
- contradiction top-1: 0.0% (post-P1) → **100.0% ± 0.0%** (perfect across all 5 seeds via strict-dominance recency)
- multi-hop top-5: 3.3% → **91.3% ± 11.7%** (target ≥25% SHATTERED)
**Mechanism:** fact_graph indexes turns by subject (fact_keys + capitalized-token fallback); query-side extraction via case-insensitive substring match against fact_graph keys (catches Alice + subsystem-317 + 'the database' uniformly); strict-dominance boost (max_base_in_subject + 1.0) guarantees latest turn wins within subject regardless of cosine variance; absent queries with phantom subjects fall through to base ensemble.
**HDC binding half (#00c-2) DEFERRED:** corpse spec mandates the hybrid, but fact-graph alone shattered every metric target (no signal headroom). Surfaced to lain via Discord; Cycle 4 opens on P4 while #00c-2 awaits decision.
**Aggregate:** `gpt-codex/runs/phase10_p3_factgraph_5seed/result.json`. Verdict addendum at bottom of `docs/artifacts/PHASE_9_SEMANTIC_HDC_MEMORY.md`.

## 5. Cycle 4 provisional scope (opening immediately after this doc lands)

### P4: ✅ CLOSED 2026-05-10 — Incremental write + Hebbian replay consolidation
**Files patched:** `semantic_hdc_memory.py` added `write_one(record)` (single-record append: encodes via floor + hebbian, prepends fact_graph subject lookup with recency-desc invariant, appends Jaccard token set) + `replay_consolidate()` (re-fits Hebbian on full corpus, re-encodes turns — the "sleep pass" Council Idea #4); `semantic_memory_agent.py` agent.process write path now calls `mem.write_one`, tracks `_writes_since_replay`, fires `mem.replay_consolidate()` every `replay_cadence` writes (default 50 per default-acting on lain's open Q3).
**Mechanical proof:** new tests `test_agent_process_assertion_writes_and_is_retrievable` (write → retrieve loop, asserts top-1 == new turn_id 4) and `test_agent_50_turn_write_retrieve_sequence` (25 alternating write+retrieve cycles, replay fires at the cadence threshold, originals preserved). Pytest 42 → 43.
**Killer-milestone capabilities now demonstrated at unit scale:**
- Capability 1 (teach new fact incrementally) ✅ via `test_agent_process_assertion_writes_and_is_retrievable`
- Capability 2 (resolve correction) ✅ via `test_agent_contradiction_latest_wins`
- Capability 3 (multi-hop with citations) ✅ via `test_agent_multi_hop_recovers_both_subjects`
- Capability 4 (refuse absent) ✅ via `test_agent_absent_answer_decision`
- Capability 5 (tool execution + write-back) ⏸️ awaits lain's ToolRuntime placement decision

**Lain default-acts:** Q3 replay cadence = N=50 writes (configurable). Q1 git-init = stay flat. Q2 ToolRuntime placement still load-bearing for #00g.

## 5. Cycle 5 provisional scope (opening immediately after this doc lands)

### P5: ✅ CLOSED 2026-05-10 — Absent-answer threshold sweep + ensemble-disagreement
**Files:** new `gpt-codex/runs/phase10_p5_absent_gating/result.json` (5-seed sweep). Updated `MemoryAgent.cosine_threshold` default 0.25 → 0.32. Empirical winner: threshold-only at 0.32 (FP=9.3%, survival=93.5%, F1=0.9585). Reviewer's hypothesis (ensemble-disagreement gating) empirically NOT useful — disagreement noisy on real queries. Structural retrieval already lifted survival from 31% to 93.5%; threshold alone closes absent gate.

### P6: ✅ CLOSED 2026-05-10 — Legacy transformer quarantine
**Move:** `src/project_x/model.py` → `src/project_x/legacy/transformer_scaffolding.py`. Module-level docstring marks LEGACY status + warns against import in organic-thesis code. Imports updated in `src/project_x/smoke.py` and `tests/test_smoke.py`. Pytest still passes.

### EXIT GATE: ✅ CLOSED 2026-05-10 — Killer-milestone test
**File:** `tests/test_killer_milestone.py` — 6 tests, all PASS. ALL 5 reviewer-prescribed capabilities mechanically demonstrated end-to-end: (1) teach incrementally, (2) resolve correction LATEST-wins, (3) multi-hop with citations, (4) refuse absent, (5) tool execution + write-back. Plus full-sequence integration test. Phase 10 EXIT GATE MET.

### #00c-2: ✅ CLOSED 2026-05-10 — HDC role-filler binding
**Files patched:** `semantic_hdc_memory.py` — added `_subject_atoms` + `_subject_bound_accum` + `_subject_bound_bank` fields, `_atom_for(subject)`, `_add_to_binding_bank(subject, turn_vec)`, `_build_binding_bank(records)`, `unbind_subject_pseudo_vec(subject)`. Write-time bind: for each subject in each turn, `bind(turn_vec, atom_subject)` is added to a per-subject int32 accumulator and refreshed as a sign-cleaned bipolar bank. Unbind at read time: `bind(bank[s], atom_s)` recovers the (noisy) superposition of all turn vecs that mentioned `s` — Plate-style structural retrieval. `write_one` extends the bank incrementally so post-P4 writes contribute. Two new pytest tests verify unbinding recovers subject-specific signal: `test_hdc_binding_unbind_recovers_subject_signal` (3-record corpus: unbind(Alice) > Bob, > Carol on cosine to floor turn vecs), `test_hdc_binding_extends_on_incremental_write` (post-incremental-write the new turn contributes to the pseudo-vec).

**Empirical impact:** as predicted by advisor and verified at unit scale, the binding-half does NOT add metric lift on the Phase 9 dataset because fact-graph alone already shattered every benchmark target. Binding ships as corpse-spec compliance + future-phase infrastructure (P11+ predictive simulation may use binding for forward-modeling; Phase 12+ cortical column ensemble (council #2) may layer over it).

## 5. Phase 10 closed — what's next

**Awaiting lain:** ack of Phase 10 closure + Phase 11 framing. Council ideas #2 (cortical column ensemble), #3 (predictive simulation loop), and #5 (open-ended benchmark ladder) were DEFERRED at corpse intake; they're the candidate Phase 11/12/13+ directions. Phase 10's empirical verdict (fact-graph + structural retrieval crushed every target; binding shipped but with no measurable lift) reshapes Phase 11 priorities — the council's cortical-column-ensemble direction now has cleaner architectural surface to build on.

**Heartbeat:** disarming after this doc lands (queue empty + pytest 51/51 + checks pass per CLAUDE.md heartbeat invariant). Listener stays armed.

**Decisions still queued (no longer blocking; can answer at lain's leisure):**
1. `git init` — stayed flat throughout Phase 10. Phase 11 might benefit from git history; ask at Phase 11 entry.
2. ToolRuntime placement — default-acted "extend MemoryAgent.run_tool" for #00g; if a separate `ToolRuntime` class is preferred for Phase 11, easy refactor.
3. Replay cadence — defaulted N=50 writes; tunable.

---

## 5. If next instance resumes

Read in this order:
1. **This file** — Phase 10 priorities + killer milestone.
2. `docs/artifacts/PHASE_9_SEMANTIC_HDC_MEMORY.md` — Phase 9 verdict (what shipped + what's open).
3. `docs/artifacts/PHASE_9_PICK_ONE_VERDICT.md` ADDENDUM — lain's organic-only constraint (binding for all encoder/generator work).
4. `docs/artifacts/PHASE_9_SHRINE_COUNCIL_HEBBIAN.md` — council reasoning (Plate dossier especially relevant for P3 fact-graph).
5. `gpt-codex/runs/phase9_memory/result.json` — most recent comprehensive numbers.
6. `Project X Session Mistakes` wiki — esp. M-PROJECTX-011 (inheritance trap) and M-PROJECTX-012 (defer-the-probe trap).
7. Source modules in this order: `semantic_memory_dataset.py` → `encoder.py` → `random_index_hebbian.py` → `ensemble_encoder.py` → `semantic_hdc_memory.py` → `semantic_memory_agent.py` → `hdc_substrate.py`.

Then attack P1 first.

---

## 6. Files & paths quick-reference

```
src/project_x/experiments/
  semantic_memory_dataset.py:457   # P1 contradiction-label bug
  semantic_hdc_memory.py:159       # P3 multi-hop attack site (current decomp)
  semantic_memory_agent.py:166     # P4 incremental-write deferred line
  random_index_hebbian.py          # P4 replay consolidation extension
  encoder.py                       # P5 ensemble-disagreement gating reads from here
  hdc_substrate.py                 # P3 fact-graph binding uses bind/unbind primitives
src/project_x/model.py:27          # P6 legacy transformer to quarantine
tests/test_*.py                    # P2 strengthen all
tests/test_killer_milestone.py     # NEW — Phase 10 exit gate
```
