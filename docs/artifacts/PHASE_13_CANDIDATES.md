# Phase 13 Candidate Framing — synthesized for lain's review

**Updated:** 2026-05-10 ~12:50 CEST (Phase 12 cycle 6, godify-app APOTHEOSIS pickup run).
**Author:** Execute-Raphael (informational artifact; Plan-Raphael writes the actual Phase 13 plan in Phase 13 cycle 1).
**Inputs synthesized:**
1. `docs/artifacts/PHASE_11_BENCHMARK.md` candidate Phase 12+ priorities (ranked by leverage at Phase 11 close)
2. Phase 12 cycle-5 advisor pass — closure quality gaps + remaining work areas
3. Phase 12 cycles 1-5 surface findings — what shipped, what was tightened, what was deliberately scoped out

> **Why this file exists.** Phase 12 closes 1 of Phase 11's 7 ranked candidates (priority 1: memory retrieval-mode disambiguation). Phase 13's framing decision is lain's. This file compiles the candidate set in one place so lain can pick the next phase without re-deriving the ranking from scratch — and so the AGENT in Phase 13 cycle 1 has a single canonical input to author the plan from.

---

## Closed in Phase 12 (for context)

✅ **Memory retrieval-mode disambiguation** — Phase 11 priority 1.
- New `retrieve_structural_full_history` in `semantic_hdc_memory.py` (chronological full-subject path bypassing the Phase 10 P3 strict-dominance recency boost).
- New `_LIST_ALL_HINTS` classifier + `_is_list_all_query` + dual-gate routing (`classifier AND subject-extraction`) in `MemoryAgent.process`.
- New `compose_answer(full_history=True)` short-circuit citing all evidence chronologically.
- 6 new tests in `tests/test_retrieval_modes.py` (pytest 52 → 58).
- memory-004 + memory-005 flipped auto-graded-red → auto-graded-green; audit_log counts now 11/0/21/4.
- Phase 11 verdict addendum at bottom of `docs/artifacts/PHASE_11_BENCHMARK.md`.
- Phase 12 verdict at `docs/artifacts/PHASE_12_RETRIEVAL_DISAMBIGUATION.md` (cycle 7).

The fix closes the 2 named auto-graded reds. It does NOT close the general query-shape disambiguation problem — the 10 `_LIST_ALL_HINTS` patterns match memory-004/005 phrasings specifically. Equivalent real-world phrasings ("Show me Alice's full record," "Walk through Alice's progression") would still collapse under strict-dominance. That's a Phase 13 candidate, not a Phase 12 deferral.

---

## Tier 1 — close pre-existing seams (small surface, high leverage)

### T1.1 — Substring → whole-word subject extraction

**Surface:** `src/project_x/experiments/semantic_hdc_memory.py:_extract_query_subjects` (~10 LoC change).
**Pre-existing risk:** Phase 10 P3 substring-match (`k.lower() in q_lower`) has a false-positive risk where a fact_graph key that is a substring of an unrelated word matches. Example: fact_graph key `"Cal"` (a person named Cal) matches the word `"California"` in a query like `"Who has been to California?"` — would incorrectly treat Cal as the query subject. The advisor surfaced this in Phase 12 cycle 5 as a Phase 13 candidate, not a Phase 12 issue (it predates Phase 12 + is independent of the retrieval-mode seam).
**Fix shape:** Replace `k.lower() in q_lower` with word-boundary regex `re.search(rf"\b{re.escape(k.lower())}\b", q_lower)`. Or tokenize the query and check exact-token-match.
**Tests:** 1-2 new tests in `tests/test_semantic_hdc_memory.py`:
- `test_subject_extraction_word_boundary` — fact_graph key "Cal" + query "Who has been to California?" must NOT extract "Cal"
- `test_subject_extraction_handles_punctuation` — key "Alice" + query "What does Alice's friend think?" SHOULD extract "Alice" (apostrophe is a word boundary)
**Cycle estimate:** 0.5-1 cycle.
**Leverage rationale:** Closes a known FP class without architectural change. Cheap insurance against silent miscites in Phase 13+ test ladders.

### T1.2 — Generalized query-shape disambiguator

**Surface:** `src/project_x/experiments/semantic_memory_agent.py` `_LIST_ALL_HINTS` + classifier (~30-50 LoC change).
**Phase 12 limitation:** The 10 `_LIST_ALL_HINTS` patterns are specific to memory-004/005 phrasings + 5-6 conservative extensions. Real-world phrasings that don't match: "Show me Alice's full record," "Tell me everything Alice has said," "Walk through Alice's progression," "What's Alice's story?", "Run through Alice's history." Each phrasing variant the user reaches for collapses unless added to the pattern list — which doesn't scale.
**Fix shape options:**
- (a) Richer pattern grammar — verb-prefix patterns (`tell|show|walk|run|give` + `me` + possessive + `record|story|history|progression`) with 20-30 patterns covering common verb-noun list-all phrasings
- (b) Learned classifier — small from-scratch organic classifier (MUST honor lain's no-pretrained-transformers rule) trained on a labeled dataset of ~50 list-all vs ~50 current-preference queries; could use Hebbian co-occurrence vectors or char-n-gram + simple linear classifier
- (c) Hybrid — pattern grammar as fast path, classifier as fallback
**Cycle estimate:** 1-2 cycles for (a); 2-3 cycles for (b) including labeled dataset; (c) bundles them.
**Leverage rationale:** Phase 12's conservative approach closes the 2 named findings. A generalized disambiguator closes the problem class — would mean any reasonable list-all phrasing routes correctly, not just memory-004/005 fixture phrasings. Net effect on benchmark: would let Phase 11 ladder authors write more natural list-all probes without having to match the agent's exact pattern set.

---

## Tier 2 — architectural extensions (medium surface, multi-cycle)

### T2.1 — Cortical column ensemble

**Council Idea #2** (Hawkins/Numenta direction; `docs/artifacts/PHASE_9_SHRINE_COUNCIL_HEBBIAN.md` — see Plate dossier especially).
**Concept:** Many sparse HDC modules (e.g. 8-32 columns) each storing a different view of the corpus, voting at retrieve time over the Phase 10 fact-graph + binding substrate. Adds robustness to encoder noise + improves disambiguation across subject-similar facts.
**Predicted impact:** Lift on memory ranks 4-5 (and Phase 13 ladder extensions) even WITHOUT T1.2 — ensemble voting may surface chronologically-distant turns by aggregating across columns that each saw a slightly different cosine landscape.
**Cycle estimate:** 3-5 cycles. Requires:
1. Architecture sketch (column factory; voting mechanism; how cosines combine across columns)
2. Implementation (refactor `SemanticHDCMemory` to support N parallel columns OR new `EnsembleHDCMemory` class)
3. Hyperparameter sweep (column count, voting rule, encoder seeding strategy)
4. Benchmark re-run (memory ladder + new tests + per-column diagnostic)
5. Verdict
**Leverage rationale:** This is a proper organic-stack architectural step — multi-module, voting-based, biologically-inspired. Predicted to be the highest-leverage Phase 13 move IF lain wants depth. Predicted to be the longest cycle path IF lain wants breadth (T1.1 + T1.2 + T1.x ladder ext is faster shipping).

### T2.2 — Hebbian-replay live training informed by audit

**MANIFESTO long-arc:** "Live-training algo the agent uses where its rubric-pending domains scored weakest. Phase 11's verdict markdown is the input." (`docs/MANIFESTO.md` Phase 12+ candidates §3.)
**Concept:** Use Phase 11 + Phase 12 auto-graded results (and tomorrow's GPT-audited rubric scores) as the reward signal. Where the agent scored red, replay-consolidate emphasizes those failure-mode patterns; where green, reinforce. Closes the benchmark→training loop the MANIFESTO names as the "learning loop."
**Surface:**
- `src/project_x/experiments/semantic_hdc_memory.py:replay_consolidate` already exists (Phase 10 P4); needs an audit-informed weighting pass
- New `BenchmarkRewardSignal` class loading audit_log.jsonl + per-entry green/red/score
- Replay schedule changes — currently every N writes; would change to weighted-by-failure-mode
**Cycle estimate:** 2-4 cycles. Requires honest before/after benchmark re-run to measure if the replay actually moves any rubric-pending entries from low-graded to higher-graded post-training.
**Leverage rationale:** This is the FIRST real "learning" loop in the Project X stack. Phase 9-10 was static encoder + static fact-graph. Phase 12 was a controller change. T2.2 is the agent improving itself based on benchmark feedback. Predicted to be the highest-leverage Phase 13 move IF lain wants closure on the static-vs-learning gap. Risk: replay may not move much without architectural depth (T2.1) underneath.

---

## Tier 3 — methodology / scope expansion

### T3.1 — GPT audit on the 21 rubric-pending entries

**Lain-gated.** Tomorrow's pass per Phase 11 verdict GPT audit prep instructions. lain runs external GPT against `gpt-codex/benchmark/audit_log.jsonl` filtered on `needs_audit: true`. GPT outputs per-entry rubric scores using `gpt-codex/benchmark/<domain>/rubric.md`. Audit produces:
- Per-domain average score (informs which rubrics to re-weight)
- Lowest-graded entries flagged as Phase 13+ candidate work areas
- Cross-checks on auto-graded subset (verify Phase 12 closure honesty)
**Cycle estimate:** 0 from agent (lain runs GPT); 1 cycle to ingest + write up rubric re-weighting if needed.
**Leverage rationale:** Until the audit runs, the 21 rubric-pending entries have no honest grade. This is the REAL Phase 11 scoreboard.

### T3.2 — Open-ended benchmark ladder

**Council Idea #5** (Stanley/POET direction).
**Concept:** Ladder >6-entry-per-domain. Phase 11 close named this as a future candidate; Phase 12 scope-fenced it cycle 4. Adds depth to test methodology — not just intro→unsolved per domain, but each rank tier with multiple distinct probes.
**Cycle estimate:** 1-2 cycles per domain (6 domains = 6-12 cycles total if extending all). Probably do 2-3 high-leverage domains first (memory, philosophy, persona) and revisit.
**Leverage rationale:** Meta-priority on testing methodology. Meaningful ONLY after T1.x + T2.x close real architectural seams. Otherwise just adds entries that probe the same fixed agent capability.

### T3.3 — Predictive simulation loop

**Council Idea #3** (LeCun world-model direction).
**Concept:** Forward-modeling capability the agent doesn't yet have. Given a state + an action, predict the next state. Can use HDC binding for forward-modeling (subject + verb + object → predicted next-turn pseudo-vec).
**Cycle estimate:** 4-6 cycles — this is properly novel and would need its own Plan-navi cycle to architect.
**Leverage rationale:** Big jump in capability surface. Predicted to be Phase 14+, not Phase 13 — Phase 13 should close gaps before adding novel capabilities.

---

## Tier 4 — orthogonal capability

### T4.1 — Audio listening (Whisper integration)

**Deferred from Phase 11 brief.** Whisper installed at `/home/nira/.local/bin/whisper`. Discord-REST polling + voice-attachment download + transcription pipeline is its own scope.
**Cycle estimate:** 1-2 cycles.
**Leverage rationale:** Orthogonal — doesn't improve memory or retrieval; opens a new input modality. Worth landing eventually; not the leverage move for Phase 13.

---

## Recommended Phase 13 framing (advisory only — Plan-Raphael writes the actual plan)

**If lain wants depth:** T2.1 (cortical column ensemble) is the architectural step that makes T1.2 + T2.2 cleaner downstream. ~3-5 cycles, godify-app 6h fits comfortably.

**If lain wants breadth:** Bundle T1.1 (whole-word subject extraction) + T1.2 (generalized classifier) + T3.1 (GPT audit ingestion) into a 3-4 cycle Phase 13. Closes 3 named gaps cleanly.

**If lain wants the learning loop:** T2.2 (Hebbian-replay informed by audit) is the first real learning step. Highest-leverage from a long-arc MANIFESTO perspective. ~2-4 cycles + needs T3.1 audit data first or in parallel.

**If lain wants methodology:** T3.2 (ladder >6-entry extension) + T3.1 (GPT audit) ingestion. Better Phase 14+ priority once architectural seams close.

**Most-likely lain pick (anti-realist Plan-Raphael's read):** Bundle T1.1 + T2.2 + T3.1. Small architectural surface (T1.1 closes a real FP), real learning step (T2.2 informed by audit data), and the audit ingestion (T3.1) as the input. 3-4 cycles. Aligned with MANIFESTO's "learning loop" framing while honoring the slow-and-methodical organic-thesis discipline.

But the framing is lain's. This artifact compiles the inputs.

---

## Cross-references

- `docs/artifacts/PHASE_11_BENCHMARK.md` — Phase 11 verdict + Phase 12 closure addendum
- `docs/artifacts/PHASE_12_RETRIEVAL_DISAMBIGUATION.md` — Phase 12 verdict (cycle 7)
- `docs/MANIFESTO.md` — long-arc Phase 12+ candidates (§ "Phase 12+ candidates")
- `docs/artifacts/PHASE_9_SHRINE_COUNCIL_HEBBIAN.md` — Council Ideas #2 (cortical) + #3 (predictive) + #5 (open-ended)
- `docs/artifacts/PHASE_9_PICK_ONE_VERDICT.md` — original Phase 9 council ranking + ADDENDUM (lain organic-only constraint)
- Phase 12 cycle reflections: `docs/past_work/cycles/phase_12/dev-cycle-{1..7}.md`

## What this file is NOT

- Not a Phase 13 plan. Plan-Raphael writes that in Phase 13 cycle 1.
- Not a recommendation lain must follow. Compiles inputs; lain frames.
- Not exhaustive. There may be Phase 13 candidates lain has in mind that this file doesn't list.
