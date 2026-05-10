# Do This Next — Project X — Phase 12 Cycle 6 (Execute-Raphael — Phase 13 candidate framing)

**Cron fires:** 2026-05-10 12:42 CEST (one-shot `f7476c94`)
**Persona:** Execute-Raphael
**End time:** 2026-05-10 13:28 CEST (cycle 7 verdict lands ~13:20)
**GitHub remote:** https://github.com/ni1ra/project-x (private; `main` branch)

> **Phase 12 mechanical fix is FULLY CLOSED + advisor-cleared.** Cycle 5 advisor pass surfaced 1 actionable code fix (shipped) + 4 verdict-framing concerns (encoded in cycle-7 verdict §1-§5 structure below). Cycle 6 is true slack — the highest-leverage move is **Phase 13 candidate framing** (informational artifact, no new code).

---

## #00 deliverables (TaskList — Phase 12)

- **#1** `#∞ APOTHEOSIS mode` — in_progress (3h godify-app pickup)
- **#2** `#00P12-retrieval-mode-disambiguation` — ✅ COMPLETED cycle 2
- **#3** `#00P12-flip-memory-reds` — ✅ COMPLETED cycle 3
- **#4** `#00P12-tests` — ✅ COMPLETED cycle 4
- **#5** `#00P12-verdict + END_TIME handoff` — pending (cycle 7 — 13:07)

---

## This cycle's scope — write `docs/artifacts/PHASE_13_CANDIDATES.md`

### Goal

Synthesize a single ranked artifact for lain's Phase 13 framing decision. Inputs:

1. **Advisor's Phase 13 candidate list** (cycle-5 pass):
   - Classifier expansion (general query-shape disambiguation; current 10 patterns match memory-004/005 specifically, not the general problem)
   - Cortical column ensemble (Council Idea #2 — Hawkins/Numenta direction)
   - Hebbian-replay live training informed by audit (closes the loop benchmark→training)
   - GPT audit of 21 rubric-pending (lain-gated; tomorrow's pass)
   - Substring → whole-word subject extraction (Phase 10 P3 pre-existing FP: fact_graph key "Cal" matches "California")
   - Ladder >6-entry-per-domain extension (Phase 11 close named this)
   - Audio listening (Whisper integration; deferred from Phase 11 brief)

2. **Phase 11 verdict's #2-#7** (`docs/artifacts/PHASE_11_BENCHMARK.md` candidate Phase 12+ priorities, ranked by leverage):
   - Memory retrieval-mode disambiguation (CLOSED in Phase 12)
   - Cortical column ensemble
   - Hebbian-replay-informed live training
   - GPT audit on 21 rubric-pending entries
   - Predictive simulation loop (Council Idea #3)
   - Open-ended benchmark ladder (Council Idea #5)
   - Audio listening (Whisper integration)

3. **This run's surface findings** (Phase 12 cycles 1-5):
   - Subjunctive "in order to..." subjunctive was FP risk; tightened cycle 5 — but the broader "classifier-as-narrow-pattern-matching" approach is itself a Phase 13 leverage point (the conservative approach scales poorly)
   - Phase 12 controller dual-gate (`_is_list_all_query AND _extract_query_subjects`) is conservative-by-design; closing the seam more broadly needs a learned classifier or a richer pattern grammar

### Artifact structure (recommended)

```markdown
# Phase 13 Candidate Framing — synthesized for lain's review

**Updated:** 2026-05-10 ~12:50 CEST (Phase 12 cycle 6, godify-app APOTHEOSIS pickup run)
**Inputs synthesized:**
- Phase 11 verdict's candidate Phase 12+ list (`docs/artifacts/PHASE_11_BENCHMARK.md`)
- Phase 12 cycle-5 advisor pass on closure quality + remaining gaps
- Phase 12 surface findings (cycles 1-5): "in order" FP, classifier-as-narrow-pattern, dual-gate conservatism

## Ranked candidates

### Tier 1 — close pre-existing seams (small surface, high leverage)
1. **Substring → whole-word subject extraction** (~0.5 cycle scope)
   - Pre-existing Phase 10 P3 FP: fact_graph key "Cal" matches "California"
   - Fix: word-boundary regex in `_extract_query_subjects`
   - Tests: regression on memory-001..005, plus FP test "California vs Cal"

2. **Generalized query-shape disambiguator** (~1-2 cycles scope)
   - Replace 10-pattern `_LIST_ALL_HINTS` with a richer pattern grammar OR a learned classifier
   - Phase 12's conservative approach closes specific findings; a general approach closes a problem class

### Tier 2 — architectural extensions (medium surface, multi-cycle)
3. **Cortical column ensemble** (Council Idea #2)
   - Many sparse HDC modules + voting over Phase 10 fact-graph + binding substrate
   - Predicted lift on memory ranks 4-5 even without (1) — ensemble robustness to encoder noise

4. **Hebbian-replay live training informed by audit**
   - Use Phase 11 + Phase 12 auto-graded results as reward signal
   - Replay-consolidate emphasizes failure-mode patterns where agent scored red
   - Closes the benchmark→training loop the MANIFESTO names as Phase 12+ "learning loop"

### Tier 3 — methodology / scope expansion
5. **GPT audit of 21 rubric-pending entries** (lain-gated; tomorrow)
6. **Open-ended benchmark ladder** (Council Idea #5; >6-entry-per-domain extension)
7. **Predictive simulation loop** (Council Idea #3 — LeCun world-model direction)

### Tier 4 — orthogonal capability
8. **Audio listening** (Whisper integration; deferred from Phase 11 brief)

## Recommended Phase 13 framing

(Plan-Raphael writes this in Phase 13 cycle 1; Phase 12 cycle 6 just compiles the input set.)

## Cross-references

- `docs/artifacts/PHASE_11_BENCHMARK.md` (Phase 11 verdict + Phase 12 closure addendum)
- `docs/artifacts/PHASE_12_RETRIEVAL_DISAMBIGUATION.md` (Phase 12 verdict, cycle 7)
- `docs/MANIFESTO.md` (long-arc Phase 12+ candidates)
- Phase 11 PICK_ONE addendum / Council Idea #2-5 references
```

### Files to touch

- `docs/artifacts/PHASE_13_CANDIDATES.md` — NEW
- (do NOT touch source code; advisor: "Don't expand scope")

### Time budget

22 min substantive + 3 min close. Sub-budget:
- 15 min: write `PHASE_13_CANDIDATES.md` synthesizing all 3 input sources
- 3 min: cross-link verification (paths, addendum reference)
- 7 min: PHASE CHANGELOG cycle-6 + dev-cycle-6 + DO_THIS_NEXT cycle-7 + atomic commit + push + Discord

### Cycle 6 close checklist

- [ ] `docs/artifacts/PHASE_13_CANDIDATES.md` exists with ≥ 4 ranked tiers
- [ ] Each candidate has scope estimate + leverage rationale + cross-reference
- [ ] No new code shipped (advisor scope-fence honored)
- [ ] PHASE CHANGELOG cycle-6 row → ✅ closed
- [ ] Cycle reflection at `docs/past_work/cycles/phase_12/dev-cycle-6.md`
- [ ] DO_THIS_NEXT.md rewritten for cycle 7 (verdict + END_TIME handoff with §1-§5 structure)
- [ ] Atomic commit `docs(phase12): cycle 6 — Phase 13 candidate framing artifact`
- [ ] `git push origin main`
- [ ] `discord_send #general` cycle 6 close
- [ ] Clock out by minute 22; cycle 7 cron fires 13:07

---

## Cycle 7 verdict §1-§5 structure (advisor-locked, for cycle 7 reference)

**§1 Headline:** *"Phase 12 closes Phase 11's 2 named auto-graded reds via retrieval-mode disambiguation."* (Specific. NOT "closes the benchmark.")

**§2 What was closed:**
- memory-004 cited [7] → [0, 3, 5, 7]; 1/4 → 4/4 tokens; auto-graded-red → auto-graded-green
- memory-005 cited [9] → [0, 1, 3, 5, 7, 9] (superset, turn 0 borderline-included per entry author's labeling); 1/5 → 5/5 tokens; auto-graded-red → auto-graded-green
- Mechanical evidence: cycle-3 verdict-builder re-run, cited turn_ids parsed from answer_text, ladder.jsonl rewritten, audit_log rebuilt
- Of auto-gradable subset (11 entries): 11 green / 0 red = **100% pass rate** (was 81.8%)

**§3 What was NOT closed (scope boundary — must be explicit):**
- The 10 `_LIST_ALL_HINTS` patterns match memory-004/005 fixture phrasings specifically, not the general query-shape disambiguation problem
- Equivalent real-world phrasings would still collapse: "Show me Alice's full record" / "Tell me everything Alice has said" / "Walk through Alice's progression" don't match any pattern
- The 21 rubric-pending entries remain rubric-pending (lain-gated GPT audit)
- The 4 ungradeable entries remain ungradeable (open problems by design)
- Phase 10 P3 substring-match subject extraction FP risk ("Cal" matches "California") was NOT touched (pre-existing, Phase 13 candidate)

**§4 Architectural seam:**
- Controller-layer routing in `MemoryAgent.process` via `_is_list_all_query AND _extract_query_subjects` dual-gate
- Two retrieval modes coexist: `retrieve_structural` (strict-dominance, latest-wins) for current-preference; `retrieve_structural_full_history` (chronological, all-turns) for list-all
- Phase 10 P3 strict-dominance untouched (regression-safe per cycle 4 tests)
- `compose_answer(full_history=True)` short-circuits cosine_threshold filter; decision label `retrieve_full_history` for downstream provenance
- WHY-comments per lain GLOBAL POLICY 2026-05-10 on every change

**§5 Phase 13 candidates ranked** (cross-link `docs/artifacts/PHASE_13_CANDIDATES.md`)

---

## Battlefield

- **Working dir:** `/mnt/c/Users/nira/Documents/Research/projext-x`
- **Branch:** `main` tracking `origin/main`
- **Cycle-5 commit:** to land at end of cycle 5 turn (this turn)
- **Cron state:** 2 godify one-shots remain (`f7476c94` cycle 6 12:42 → `21e719fa` cycle 7 verdict 13:07)
- **Listener:** PID 13941 alive — pgrep + atomic re-arm if dead per M-NAVI-018
- **Tests:** 58 passing
- **Memory ladder:** 5 green / 0 red / 0 rubric-pending / 1 ungradeable

---

## When lain returns mid-run

Atomic ack protocol per CLAUDE.md DD-2 + M-NAVI-018:
1. Read msg from listener output file
2. `discord_send` ack BEFORE substantive work
3. Atomic re-arm: single Bash + run_in_background:true
4. Act

---

## M-NAVI-019 standing rule (for all 7 cycles)

Heartbeat-armed while `now < 13:28 CEST` AND named work exists. Premature disarm is fake-stop. Cycle 7 verdict cron is the only legitimate disarm signal.

---

## Phase 12 status at cycle 5 close

- ✅ retrieve_structural_full_history (cycle 1)
- ✅ _LIST_ALL_HINTS + classifier + controller routing + compose_answer extension (cycle 2)
- ✅ memory-004/005 flipped red→green; audit_log rebuilt 11/0/21/4; PHASE_11 addendum (cycle 3)
- ✅ test_retrieval_modes.py — 6 tests, full suite 58 passing (cycle 4)
- ✅ advisor pass + "in order" FP fix + tests/CLAUDE.md refresh + reflection sanity (cycle 5)
- ⏳ Phase 13 candidate framing (cycle 6, THIS CYCLE)
- ⏳ Phase 12 verdict + END_TIME handoff (cycle 7)

The mechanical fix + tests + benchmark JSON updates are all DONE. Cycle 6 is informational artifact for lain. Cycle 7 lands the verdict using the advisor-locked §1-§5 structure.
