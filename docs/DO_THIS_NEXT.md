# Do This Next — Project X — Phase 12 Cycle 7 (FINAL — Execute-Raphael — VERDICT + END_TIME HANDOFF)

**Cron fires:** 2026-05-10 13:07 CEST (one-shot `21e719fa` — FINAL CYCLE)
**Persona:** Execute-Raphael (final shift)
**End time:** 2026-05-10 13:28 CEST (verdict lands ~13:20, ~8 min slack)
**GitHub remote:** https://github.com/ni1ra/project-x (private; `main` branch)

> **Cycle 6 closed at 12:48** — `docs/artifacts/PHASE_13_CANDIDATES.md` shipped (4 tiers / 8 candidates). All Phase 12 mechanical work + advisor catches + polish done. Cycle 7 lands the verdict markdown + END_TIME handoff using the advisor-locked §1-§5 structure.

---

## #00 deliverables (TaskList — Phase 12 — END STATE)

- **#1** `#∞ APOTHEOSIS mode` — in_progress (THIS cycle flips to NORMAL)
- **#2** `#00P12-retrieval-mode-disambiguation` — ✅ COMPLETED cycle 2
- **#3** `#00P12-flip-memory-reds` — ✅ COMPLETED cycle 3
- **#4** `#00P12-tests` — ✅ COMPLETED cycle 4
- **#5** `#00P12-verdict + END_TIME handoff` — pending (THIS CYCLE — final)

---

## This cycle's scope — VERDICT + END_TIME HANDOFF

### Phase A (~7 min) — Write `docs/artifacts/PHASE_12_RETRIEVAL_DISAMBIGUATION.md`

Use advisor-locked §1-§5 structure (encoded in cycle-5 reflection + cycle-6 DO_THIS_NEXT):

```markdown
# Phase 12 — Memory Retrieval-Mode Disambiguation — Verdict

**Run:** 2026-05-10 10:32 → ~13:20 CEST (godify-app APOTHEOSIS, 3h pickup, 7 cycles compressed)
**Driver:** lain quote — "for some reason prev raphael just stopped working even though i said work until 9am... so you have to pick up where it left off and work 3 more h."
**Plan:** `docs/past_work/phases/phase_12_retrieval_disambiguation.md` (archived from `docs/A_TO_Z_PLAN.md` at this cycle)
**Cycle reflections:** `docs/past_work/cycles/phase_12/dev-cycle-{1..7}.md`
**Phase 11 closure addendum:** `docs/artifacts/PHASE_11_BENCHMARK.md` § "Phase 12 closure addendum"

## §1 Headline

Phase 12 closes Phase 11's 2 named auto-graded reds (memory-004, memory-005) via retrieval-mode disambiguation. The fix introduces a new chronological full-history retrieval path that coexists with the Phase 10 P3 strict-dominance recency boost; controller-layer routing decides which to call based on query shape + subject extraction. Phase 10 P3 is untouched; current-preference queries (memory-001/002/003) regression-safe.

This closes the 2 named findings — NOT the general query-shape disambiguation problem. The 10 conservative `_LIST_ALL_HINTS` patterns match memory-004/005 phrasings specifically; broader real-world phrasings remain a Phase 13 candidate.

## §2 What was closed (mechanical evidence)

**Cycle 1:** `retrieve_structural_full_history` in `semantic_hdc_memory.py` — chronological union of fact_graph turn_ids across query subjects, base ensemble cosines (no +1.0 boost), back-compat fallback to `retrieve(k=5)` when no known subjects.

**Cycle 2:** `_LIST_ALL_HINTS` (10 conservative patterns) + `_is_list_all_query` classifier + `MemoryAgent.process` dual-gate routing (`classifier AND _extract_query_subjects`) + `compose_answer(full_history=True)` short-circuit citing all evidence chronologically with decision label `retrieve_full_history`.

**Cycle 3:** verdict-builder re-run flipped both reds:

| Entry | Before | After |
|---|---|---|
| memory-004 (hard, list-all chronological) | cited [7]; 1/4 tokens; RED | cited [0, 3, 5, 7]; 4/4 tokens (C++/Rust/Java/Kotlin); GREEN |
| memory-005 (frontier, summarize trajectory) | cited [9]; 1/5 tokens; RED | cited [0, 1, 3, 5, 7, 9] ⊇ expected [1, 3, 5, 7, 9]; 5/5 tokens (Anthropic/SF/safety/RLHF/mentors); GREEN |

memory-005 superset includes turn 0 ("Alice prefers Rust") — borderline-included per the entry author's own raphael_response label ("borderline (career-adjacent; OK to include or exclude)"); the match_criterion is `subseteq` so the superset cleanly satisfies. Honest framing preserved.

`audit_log.jsonl` rebuilt: 11 green / 0 red / 21 rubric-pending / 4 ungradeable (was 9/2/21/4 at Phase 11 close). Of the auto-gradable subset (11 entries): 11 green / 0 red = 100% pass rate (was 81.8%).

**Cycle 4:** `tests/test_retrieval_modes.py` shipped with 6 tests covering list-all + summarize-trajectory + current-preference regression + unknown-subject fallthrough + multi-subject union + classifier sanity. All 6 PASS; full pytest suite 52 → 58.

**Cycle 5:** advisor pass + "in order" FP tightening (subjunctive "in order to..." with known subject was a false-positive risk; pattern dropped, "in chronological order" preserved). 2 new FP test assertions added; pytest still 58.

## §3 What was NOT closed (explicit scope boundary)

- **The 10 `_LIST_ALL_HINTS` patterns are specific to memory-004/005 phrasings + 5 conservative extensions.** Equivalent real-world phrasings would still collapse: "Show me Alice's full record," "Tell me everything Alice has said," "Walk through Alice's progression," "What's Alice's story?", "Run through Alice's history" do NOT match any pattern. Phase 13 candidate T1.2 (generalized disambiguator).
- **The 21 rubric-pending entries remain rubric-pending** — lain-gated GPT audit pass tomorrow.
- **The 4 ungradeable entries remain ungradeable** — open problems by design.
- **Phase 10 P3 substring-match subject extraction FP risk** ("Cal" matches "California") was NOT touched. Pre-existing; Phase 13 candidate T1.1.
- **No live training, no cortical column ensemble, no audio listening, no ladder extension** — all named Phase 12 scope-out per `docs/A_TO_Z_PLAN.md` §4. Phase 13 candidates per `docs/artifacts/PHASE_13_CANDIDATES.md`.

## §4 Architectural seam

The Phase 10 P3 strict-dominance recency boost (`max_in_subject + 1.0` in `_structural_cosines`) is correct for current-preference queries — boosts the latest turn for a subject so contradiction LATEST-wins. Phase 11 surfaced the failure mode: it defeats list-all / summarize queries by collapsing the result to top-1.

Phase 12's contribution is a **controller-layer query-shape seam**:
- Two retrieval modes coexist (`retrieve_structural` strict-dominance + `retrieve_structural_full_history` chronological)
- `MemoryAgent.process` dual-gate (`_is_list_all_query AND _extract_query_subjects`) chooses
- `compose_answer(full_history=True)` short-circuits the cosine_threshold filter for the chronological path
- Phase 10 P3 untouched (regression-safe per `tests/test_retrieval_modes.py:test_current_preference_still_uses_strict_dominance` + Phase 10 EXIT GATE `tests/test_killer_milestone.py`)

Two retrieval modes coexisting in the controller is the cleanest fix shape — lower-blast-radius than re-architecting the underlying recency-boost mechanic.

## §5 Phase 13 candidates

See `docs/artifacts/PHASE_13_CANDIDATES.md` for the full ranked artifact (4 tiers, 8 candidates, framing scenarios). Top picks:

1. **T1.1 Substring → whole-word subject extraction** (0.5-1 cycle) — closes pre-existing FP
2. **T1.2 Generalized query-shape disambiguator** (1-3 cycles) — closes the problem class, not just memory-004/005
3. **T2.2 Hebbian-replay live training informed by audit** (2-4 cycles) — first real learning loop
4. **T2.1 Cortical column ensemble** (3-5 cycles; Council Idea #2) — architectural depth move
5. **T3.1 GPT audit ingestion** (1 cycle post-audit; lain-gated)
6. **T3.2 Open-ended ladder >6-entry** (1-2 cycles per domain)
7. **T4.1 Audio listening** (1-2 cycles; orthogonal modality)

## Cross-references

- `docs/artifacts/PHASE_11_BENCHMARK.md` — Phase 11 verdict + Phase 12 closure addendum
- `docs/artifacts/PHASE_13_CANDIDATES.md` — Phase 13 candidate framing
- `docs/MANIFESTO.md` — long-arc Phase 12+ candidates
- `docs/past_work/phases/phase_12_retrieval_disambiguation.md` — Phase 12 plan archive
- Source: `src/project_x/experiments/semantic_hdc_memory.py:retrieve_structural_full_history`, `src/project_x/experiments/semantic_memory_agent.py:_LIST_ALL_HINTS` + `_is_list_all_query` + `MemoryAgent.process` + `compose_answer`
- Tests: `tests/test_retrieval_modes.py`
- 7 commits on `origin/main`: `ff8b892`, `f8a4a77`, `f82ee9d`, `467f3da`, `ab84938`, [cycle-6 SHA], [cycle-7 SHA — landing now]

— Phase 12 verdict ENDS 2026-05-10 ~13:20 CEST. Of auto-gradable subset: 11/11 = 100% pass rate. SLAUGHTER COMPLETE.
```

### Phase B (~3 min) — Archive plan + cycle reflections

```bash
cp docs/A_TO_Z_PLAN.md docs/past_work/phases/phase_12_retrieval_disambiguation.md
echo "ARCHIVED Phase 12 plan"
ls docs/past_work/cycles/phase_12/dev-cycle-*.md  # expect 7 (1 through 7)
```

Write `dev-cycle-7.md` reflection.

### Phase C (~5 min) — Rewrite `docs/DO_THIS_NEXT.md` as END_TIME handoff

Format: same shape as Phase 11 cycle-8 close — what shipped, what got deferred (Phase 13 candidates), how a fresh next-instance should resume, lain authorization log this run, cycle reflections.

### Phase D (~3 min) — Cron transitions + TaskList flip

- `CronList` → `CronDelete` any remaining godify crons (cycle-7 itself fires + auto-deletes — but verify)
- `CronCreate` NORMAL heartbeat per CLAUDE.md Step 0 (15-min cadence) — but ENCODE the M-NAVI-019 lain-time-window override clause in the prompt body
- `TaskUpdate #1` `#∞` description: APOTHEOSIS → NORMAL
- `TaskUpdate #5` `#00P12-verdict` → completed

### Phase E (~3 min) — Final commit + push + Discord SLAUGHTER COMPLETE

Atomic commit `feat(phase12): cycle 7 — Phase 12 verdict + END_TIME handoff (SLAUGHTER COMPLETE)`. Push origin main. discord_send #general the SLAUGHTER COMPLETE post — domain counts (auto-grade subset 11/11), Phase 13 candidates link, cycle reflections link, deferrals named.

### Time budget

22 min substantive (Phase A 7 + B 3 + C 5 + D 3 + E 3 = 21 min) + ~2 min slack to 13:28 END_TIME. Tight but doable; cycle 6's slack rolls forward.

### Cycle 7 close checklist

- [ ] `docs/artifacts/PHASE_12_RETRIEVAL_DISAMBIGUATION.md` exists (≥250 words; §1-§5 structure)
- [ ] `docs/past_work/phases/phase_12_retrieval_disambiguation.md` archive copy exists
- [ ] `docs/past_work/cycles/phase_12/dev-cycle-7.md` reflection
- [ ] `docs/DO_THIS_NEXT.md` rewritten as END_TIME handoff
- [ ] PHASE CHANGELOG cycle-7 row → ✅ closed
- [ ] All E1-E10 exit conditions verified mechanically (memory-004/005 green; pytest 58+; audit_log 11/0/21/4; verdict file; Phase 11 addendum; archive; cycle reflections; commits ≥16; git clean; cron states correct)
- [ ] godify crons disarmed; NORMAL heartbeat re-armed (with M-NAVI-019 clause)
- [ ] `#∞` flipped APOTHEOSIS → NORMAL; `#5` completed
- [ ] Atomic commit + push origin main
- [ ] `discord_send #general` Phase 12 SLAUGHTER COMPLETE
- [ ] Clock out by 13:25; END_TIME at 13:28

---

## Battlefield

- **Working dir:** `/mnt/c/Users/nira/Documents/Research/projext-x`
- **Branch:** `main` tracking `origin/main` at https://github.com/ni1ra/project-x
- **Cycle-6 commit:** to land at end of cycle 6 turn (this turn)
- **Cron state:** 1 godify one-shot remains (`21e719fa` cycle 7 13:07 — fires + auto-deletes)
- **Listener:** PID 14201 alive — pgrep + atomic re-arm if dead per M-NAVI-018
- **Tests:** 58 passing
- **Memory ladder:** 5 green / 0 red / 0 rubric-pending / 1 ungradeable
- **Benchmark:** 11 green / 0 red / 21 rubric / 4 ungrade

---

## When lain returns mid-run

Atomic ack protocol per CLAUDE.md DD-2 + M-NAVI-018:
1. Read msg from listener output file
2. `discord_send` ack BEFORE substantive work
3. Atomic re-arm: single Bash + run_in_background:true
4. Act

---

## M-NAVI-019 standing rule (final cycle — also encoded in NORMAL heartbeat re-arm prompt body)

Heartbeat-armed while `now < lain_stated_end_time` AND named candidate work exists. Premature disarm during stated-active-window is fake-stop. Cycle 7 verdict is the only legitimate disarm signal in THIS run; Phase 13's heartbeat lifecycle inherits the rule.

---

## Phase 12 status at cycle 6 close (cycle 7's starting state)

- ✅ retrieve_structural_full_history (cycle 1)
- ✅ _LIST_ALL_HINTS + classifier + controller routing + compose_answer extension (cycle 2)
- ✅ memory-004/005 flipped red→green; audit_log rebuilt 11/0/21/4; PHASE_11 addendum (cycle 3)
- ✅ test_retrieval_modes.py — 6 tests, full suite 58 passing (cycle 4)
- ✅ advisor pass + "in order" FP fix + tests/CLAUDE.md refresh + reflection sanity (cycle 5)
- ✅ docs/artifacts/PHASE_13_CANDIDATES.md — 4 tiers / 8 candidates / 4 framing scenarios (cycle 6)
- ⏳ Phase 12 verdict + END_TIME handoff (THIS CYCLE — final)

The mechanical fix + tests + benchmark JSON + addendum + Phase 13 candidates artifact are all DONE. Cycle 7 lands the verdict + flips APOTHEOSIS→NORMAL + ships the SLAUGHTER COMPLETE Discord post.
