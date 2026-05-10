# A → Z Plan — Project X — Phase 12 — Memory Retrieval-Mode Disambiguation

**Date opened:** 2026-05-10 10:32 CEST (godify-app APOTHEOSIS, 3h pickup, 7 cycles compressed back-to-back)
**Previous phase archived:** `docs/past_work/phases/phase_11_raphael_domain_benchmark_suite.md`
**Phase theme:** Close the memory-004/005 red findings from Phase 11. Add a query-shape disambiguator to `MemoryAgent.process` so "list all" / "summarize trajectory" prompts route to a chronological full-history retrieval path that bypasses the Phase 10 P3 strict-dominance recency boost.
**Run end:** 2026-05-10 13:28 CEST (END_TIME)
**Trigger:** lain quote — *"for some reason prev raphael just stopped working even though i said work until 9am... so you have to pick up where it left off and work 3 more h."* Prev instance fake-stopped at 06:55 (M-NAVI-019); this instance picks up Phase 12 priority 1 from prev's DO_THIS_NEXT.md.
**Persona dispatch:** Cycle 1 = Plan-Raphael (this turn, compressed ~20 min). Cycles 2-7 = Execute-Raphael (cron-fired one-shots `5ed226ac`, `baa6fc79`, `e2c4ea33`, `36e02faa`, `f7476c94`, `21e719fa`).

---

## §0. CONTRACT

### §0.1 #00 deliverables (TaskList pins)

- **#00P12-retrieval-mode-disambiguation:** Add `retrieve_structural_full_history` in `semantic_hdc_memory.py` (chronological full-subject return path bypassing strict-dominance boost + relaxed/no cosine_threshold). Add query-shape classifier `_LIST_ALL_HINTS` in `semantic_memory_agent.py`. Wire into `MemoryAgent.process` controller to route between current-preference (existing path) and list-all (new path). Update `compose_answer` to format full-history evidence chronologically.
- **#00P12-flip-memory-reds:** Re-run cycle-8 verdict-builder against fixed MemoryAgent. Update `gpt-codex/benchmark/memory/ladder.jsonl` entries 4-5 with new actual_turn_ids + match=true + audit_status=auto-graded-green. Rebuild `gpt-codex/benchmark/audit_log.jsonl`. Append Phase 12 addendum to `docs/artifacts/PHASE_11_BENCHMARK.md`.
- **#00P12-tests:** Add `tests/test_retrieval_modes.py` covering full-history retrieval, multi-subject list-all, regression on memory-001/002/003 current-preference path. Net pytest ≥ 54 (52 baseline + ≥2 new).
- **#00P12-verdict:** `docs/artifacts/PHASE_12_RETRIEVAL_DISAMBIGUATION.md` (≥250 words; before/after counts; architectural impact). END_TIME handoff in `docs/DO_THIS_NEXT.md` for Phase 13 candidates.

### §0.2 Simplicity standard

- **NO pretrained transformers** (Phase 9 standing constraint, lain 2026-05-09): unchanged. Encoders + generators stay from-scratch organic.
- **Code-comment ratio rule** (lain 2026-05-10 GLOBAL POLICY): WHY-comments justifying complex code's existence + comments preserving important info. Never WHAT-comments. Apply to every new function shipped this phase — especially `retrieve_structural_full_history` which has a non-obvious motivation (the Phase 11 verdict's memory-004/005 red findings) that future readers must see.
- **Append-as-you-go writes** for crash survival (3 power outages in 2 days context). Per-cycle atomic git commits + push.
- **Existing API preserved.** `retrieve_structural` keeps strict-dominance — memory-001/002/003 current-preference path is the reason Phase 10 P3 exists. The new `retrieve_structural_full_history` is ADDITIVE; controller routing decides which to call.

### §0.3 Constraint defining this phase

- 3h budget, 7 cycles compressed back-to-back. END_TIME 13:28 CEST.
- Surface area is small: two source files (`semantic_hdc_memory.py`, `semantic_memory_agent.py`) + one new test file. Plus benchmark ladder.jsonl deltas + audit_log + verdict + addendum.
- M-NAVI-019 (prev fake-stop) logged this turn. Heartbeat invariant fix-rule: lain-stated time-windows override queue-empty disarm logic; named candidate work counts as queued.
- Phase 11 verdict said memory-004/005 reveal a real architectural finding; Phase 12 closing it is what makes Phase 11's benchmark cash out. The benchmark paid out exactly as designed.

### §0.4 Phase exit conditions (mechanical proof at 13:28 CEST)

- [ ] **E1** `gpt-codex/benchmark/memory/ladder.jsonl` shows memory-004 + memory-005 with `audit_status: "auto-graded-green"` and `auto_grade.match: true`. Zero auto-graded-red entries across all 6 ladders.
- [ ] **E2** `PYTHONPATH=src python3 -m pytest -q | tail -3` reports ≥ 54 passing (52 baseline + ≥ 2 new tests in `test_retrieval_modes.py`).
- [ ] **E3** `gpt-codex/benchmark/audit_log.jsonl` rebuilt with updated counts (was 9 green / 2 red / 21 rubric-pending / 4 ungradeable; now 11 green / 0 red / 21 rubric-pending / 4 ungradeable). Schema firewall holds — zero `self_score` fields anywhere.
- [ ] **E4** `docs/artifacts/PHASE_12_RETRIEVAL_DISAMBIGUATION.md` exists, ≥ 250 words, includes before/after table.
- [ ] **E5** `docs/artifacts/PHASE_11_BENCHMARK.md` has Phase 12 addendum at the bottom (frozen-with-addendum convention per `docs/artifacts/CLAUDE.md`).
- [ ] **E6** `docs/A_TO_Z_PLAN.md` archived to `docs/past_work/phases/phase_12_retrieval_disambiguation.md` at cycle 7 close.
- [ ] **E7** `docs/past_work/cycles/phase_12/dev-cycle-{1..7}.md` all exist.
- [ ] **E8** `git log --oneline | wc -l` shows ≥ 16 (Phase 11 ended at 9 commits; +7 atomic per-cycle commits = 16).
- [ ] **E9** Final commit pushed to `origin/main` at https://github.com/ni1ra/project-x. `git status` clean post-cycle-7.
- [ ] **E10** NORMAL heartbeat cron re-armed; #∞ task flipped APOTHEOSIS → NORMAL; godify cron disarmed.

---

## §1. PHASE CHANGELOG

| Cycle | Persona | When (CEST) | Position | Status |
|---|---|---|---|---|
| C1 | Plan-Raphael (compressed) | 2026-05-10 10:32 | 1 of 7 | ✅ closed ~10:38 — Phase 12 plan + DO_THIS_NEXT.md + M-NAVI-019 wiki entry + 6 crons armed + TaskList #00 pinned. **Front-loaded:** `retrieve_structural_full_history` IMPLEMENTED in `semantic_hdc_memory.py` (compresses original cycle-2 scope into cycle-1). 4 smoke tests pass: list-all chronological [0,3,5,7], strict-dominance regression-safe (top-1=7), unknown-subject fall-through, multi-subject union [0,1,3,5,7]. pytest 52 passing (no regression). Cycle-2 scope shifts to controller wiring (originally cycle-3). |
| C2 | Execute-Raphael (controller + classifier) | 2026-05-10 11:02 | 2 of 7 | pending (cron `5ed226ac`) — wire query-shape classifier `_LIST_ALL_HINTS` + `_is_list_all_query` in `semantic_memory_agent.py`; route `MemoryAgent.process` between `retrieve_structural` and `retrieve_structural_full_history`; extend `compose_answer` to format full-history evidence chronologically. (Was cycle-3 scope; cycle-1 absorbed cycle-2.) |
| C3 | Execute-Raphael (flip reds) | 2026-05-10 11:27 | 3 of 7 | pending (cron `baa6fc79`) — re-run verdict-builder, flip memory-004/005 red→green, rebuild `audit_log.jsonl`, addendum to `PHASE_11_BENCHMARK.md`. (Was cycle-4 scope; pulled forward.) |
| C4 | Execute-Raphael (tests + stretch) | 2026-05-10 11:52 | 4 of 7 | pending (cron `e2c4ea33`) — `tests/test_retrieval_modes.py` + optional ladder extension memory-007/008. (Was cycle-5 scope.) |
| C5 | Execute-Raphael (advisor + polish + reflections) | 2026-05-10 12:17 | 5 of 7 | pending (cron `36e02faa`) — `advisor()` pre-verdict + cycle reflections 1-4 + comment-ratio polish. (Was cycle-6 scope.) |
| C6 | Execute-Raphael (extra slack — Phase 13 prep / GPT audit prep / explorer) | 2026-05-10 12:42 | 6 of 7 | pending (cron `f7476c94`) — slack cycle from cycle-1 absorption. Highest-leverage: Phase 13 candidate prep (cortical column ensemble scaffolding sketch, OR Hebbian-replay reward-signal hookup, OR ladder extension to >6 entries). Pick at fire time per pick-skill. |
| C7 | Execute-Raphael final (verdict) | 2026-05-10 13:07 | 7 of 7 | pending (cron `21e719fa`) — verdict markdown + END_TIME handoff + cron disarm + APOTHEOSIS→NORMAL |

---

## §2. CYCLE PLAN

### §2.C1 — Plan-setup (NOW, 10:32 CEST, compressed)
- [x] C1.1 Verify Phase 11 archive at `past_work/phases/phase_11_raphael_domain_benchmark_suite.md`
- [x] C1.2 TaskCreate #∞ + 4 #00P12 deliverables
- [x] C1.3 CronCreate × 6 one-shots for cycles 2-7
- [x] C1.4 Log M-NAVI-019 to wiki (heartbeat-disarm during stated lain time-window)
- [x] C1.5 Write fresh `docs/A_TO_Z_PLAN.md` (this file)
- [ ] C1.6 Rewrite `docs/DO_THIS_NEXT.md` for cycle 2
- [ ] C1.7 Begin `retrieve_structural_full_history` skeleton in `semantic_hdc_memory.py` if time
- [ ] C1.8 Atomic commit cycle 1 close
- [ ] C1.9 Discord cycle 1 close post

### §2.C2 — Implementation half 1 (11:02 CEST)
- Add `retrieve_structural_full_history(query, k=None)` in `semantic_hdc_memory.py`:
  - Extract subjects via `_extract_query_subjects` (existing helper)
  - For each subject: union all `_fact_graph[s]` turn_ids
  - Sort UNION ascending by turn_id (chronological, NOT recency-desc)
  - Build cosine vector: per-turn ensemble cosine (no strict-dominance boost; no `+1.0` collapse)
  - Return `[(turn_id, cosine, record), ...]` — full chronological list, no `k` cap by default (caller decides)
  - If no known subjects: fall through to `retrieve(query, k=5)` — back-compat
- Unit-level smoke test inline (call against synthetic 8-turn Alice fixture, expect chronological [0,3,5,7])

### §2.C3 — Implementation half 2 (11:27 CEST)
- In `semantic_memory_agent.py`:
  - Add `_LIST_ALL_HINTS` tuple: `("list all", "all of", "summarize", "trajectory", "history of", "all changes", "every", "in chronological order", "in order")`
  - Add classifier `_is_list_all_query(text)`: lower + any-hint-match
  - Extend `process` question path: if `_is_list_all_query(text)` AND `memory._extract_query_subjects(text)` returns subjects, route to `retrieve_structural_full_history`; else existing `retrieve_structural`
  - Update `compose_answer` to handle full-history evidence with ALL turns cited (skip cosine_threshold filter when decision label is `retrieve_full_history`); chronological format: `Based on turns 0, 3, 5, 7: '<text 0>' AND '<text 3>' AND '<text 5>' AND '<text 7>'`
  - Set decision label `retrieve_full_history` (new) on the full-history path
- Smoke test against memory-004 + memory-005 fixtures inline

### §2.C4 — Flip memory reds (11:52 CEST)
- Re-run verdict-builder script per `gpt-codex/benchmark/memory/CLAUDE.md` Python sketch (BUT: parse cited turn_ids from `response.evidence`, NOT just `answer_text` regex — prev instance had to fix this mid-cycle)
- Update memory-004 + memory-005 entries with new actual_turn_ids + match=true + audit_status=auto-graded-green
- Rebuild `gpt-codex/benchmark/audit_log.jsonl` with new counts: 11 green / 0 red / 21 rubric-pending / 4 ungradeable
- Append addendum to `docs/artifacts/PHASE_11_BENCHMARK.md`: "Phase 12 closure (2026-05-10 ~12:00 CEST) — memory-004/005 flipped from auto-graded-red to auto-graded-green via retrieve_structural_full_history fix. Architectural finding now closed."

### §2.C5 — Tests + stretch (12:17 CEST)
- `tests/test_retrieval_modes.py`:
  - `test_list_all_query_returns_full_history` — 8-turn Alice fixture, query "List all of Alice's preferences", expect cited [0,3,5,7]
  - `test_summarize_trajectory_returns_full_history` — 10-turn Alice career fixture, query "Summarize Alice's trajectory", expect cited subset of [1,3,5,7,9]
  - `test_current_preference_still_uses_strict_dominance` — same 8-turn fixture, query "What does Alice prefer?", expect cited [7] (Kotlin) — REGRESSION on memory-002 path
  - `test_unknown_subject_falls_through_to_ensemble` — query mentioning unknown subject "Zoe", expect ensemble path returns top-k
  - `test_multi_subject_list_all_unions_chronologically` — fixture with Alice + Bob both with multiple turns, query "List Alice and Bob's history", expect union sorted by turn_id ascending
- Verify `pytest -q` shows 52 + 5 = 57 passing
- Stretch goal: extend memory ladder with 1-2 NEW auto-graded entries (memory-007 list-all-multi-subject, memory-008 summarize-with-correction) shipped green from inception

### §2.C6 — advisor + polish (12:42 CEST)
- `advisor()` call before cycle-7 verdict:
  - Validate Phase 12 done-claim quality
  - Surface any concerns about backwards compatibility
  - Honest framing check on the verdict markdown shape
- Address advisor concerns inline
- Cycle reflections for `dev-cycle-1.md` through `dev-cycle-5.md` (`dev-cycle-6.md` written end of this cycle)
- Comment-ratio polish: every new function has a WHY-comment justifying its existence (Phase 11 verdict pointer + memory-004/005 architectural finding)

### §2.C7 — VERDICT + END_TIME HANDOFF (13:07 CEST)
- Write `docs/artifacts/PHASE_12_RETRIEVAL_DISAMBIGUATION.md` (≥ 250 words):
  - Before/after table: memory-004 cited [7]→[0,3,5,7]; memory-005 cited [9]→[1,3,5,7,9]
  - Architectural impact: Phase 10 P3 strict-dominance was correct-by-default but missed the query-shape disambiguation seam; the fix preserves Phase 10 P3 for current-preference and adds an opt-in chronological mode
  - Honest deferrals: cortical column ensemble, predictive simulation, Hebbian-replay-informed live training, GPT audit on the 21 rubric-pending entries — all Phase 13+ candidates
- Append addendum at bottom of `docs/artifacts/PHASE_11_BENCHMARK.md` (frozen-with-addendum)
- Archive `docs/A_TO_Z_PLAN.md` → `docs/past_work/phases/phase_12_retrieval_disambiguation.md` (`cp` not `mv`)
- Rewrite `docs/DO_THIS_NEXT.md` as Phase 13 candidates handoff (no fresh A_TO_Z_PLAN.md stub — leave the live one as Phase 12 archive pointer until lain picks Phase 13)
- `dev-cycle-7.md` reflection
- Final mechanical verification: pytest 54+; benchmark schema firewall; memory ladder 0 reds
- `CronList` → `CronDelete` any remaining godify crons (cycle 7 itself fires + auto-deletes)
- `CronCreate` NORMAL heartbeat per CLAUDE.md Step 0 — but with the M-NAVI-019 fix-rule visible: if work is named in DO_THIS_NEXT.md and lain has a stated time-window, heartbeat-armed
- `TaskUpdate` `#∞` description: APOTHEOSIS → NORMAL
- Atomic commit + push origin main
- `discord_send #general` Phase 12 SLAUGHTER COMPLETE post

---

## §3. VERIFICATION GATES (mechanical proof commands)

```bash
# E1 — memory-004/005 audit_status
python3 -c "
import json
for line in open('gpt-codex/benchmark/memory/ladder.jsonl'):
    d = json.loads(line)
    if d['id'] in ('memory-004', 'memory-005'):
        print(d['id'], '->', d['audit_status'])
"

# E1b — total reds across all 6 ladders
python3 -c "
import json, glob
red = 0
for p in glob.glob('gpt-codex/benchmark/*/ladder.jsonl'):
    for line in open(p):
        d = json.loads(line)
        if d['audit_status'] == 'auto-graded-red': red += 1
print('reds:', red)
"
# Expect: reds: 0

# E2 — pytest 54+
PYTHONPATH=src python3 -m pytest -q 2>&1 | tail -3

# E3 — audit_log + schema firewall
PYTHONPATH=src python3 -c "
import json
required = {'id','domain','difficulty','prompt','raphael_response','audit_status'}
errors = []
for p in ['gpt-codex/benchmark/audit_log.jsonl']:
    for line in open(p): json.loads(line)
for line in open('gpt-codex/benchmark/audit_log.jsonl'): pass
import glob
for p in glob.glob('gpt-codex/benchmark/*/ladder.jsonl'):
    for i, line in enumerate(open(p), 1):
        d = json.loads(line)
        if not required.issubset(d.keys()): errors.append(f'{p}:{i} missing fields')
        if 'self_score' in d: errors.append(f'{p}:{i} M-PROJECTX-014 firewall violated')
if errors: print('SCHEMA ERRORS:'); [print(' ', e) for e in errors]; raise SystemExit(1)
print('OK schema + firewall')
"

# E4-E5 — verdict markdowns
ls docs/artifacts/PHASE_12_RETRIEVAL_DISAMBIGUATION.md && wc -w docs/artifacts/PHASE_12_RETRIEVAL_DISAMBIGUATION.md
grep -c '^## Phase 12 closure addendum' docs/artifacts/PHASE_11_BENCHMARK.md

# E6-E7 — archive + cycle reflections
ls docs/past_work/phases/phase_12_retrieval_disambiguation.md
ls docs/past_work/cycles/phase_12/dev-cycle-*.md | wc -l   # expect 7

# E8 — commit count
git log --oneline | wc -l   # expect ≥ 16

# E9 — push status
git status   # expect "nothing to commit, working tree clean"
git log --oneline origin/main..HEAD   # expect empty (all pushed)

# E10 — heartbeat re-armed; godify disarmed
# (verified via CronList in cycle 7)
```

---

## §4. SCOPE FENCE (out)

NOT in Phase 12:
- **Cortical column ensemble.** Council Idea #2; Phase 13+ candidate.
- **Hebbian-replay-informed live training.** Phase 13+ candidate; would close the loop on benchmark performance feeding training.
- **GPT audit on the 21 rubric-pending entries.** Lain-gated (lain runs external GPT against `audit_log.jsonl` filtered by `needs_audit: true`).
- **Predictive simulation loop.** Council Idea #3; Phase 13+.
- **Open-ended benchmark ladder.** Council Idea #5; Phase 13+; meaningful only after the auto-graded base is fixed (which Phase 12 does).
- **Audio listening (Whisper integration).** Whisper installed but Discord-REST polling pipeline is its own scope.
- **Touching `~/.claude/CLAUDE.md`.** Universal protocol updates fired by prev instance (M-NAVI-018, comment-ratio rule); Phase 12 stays in-repo. EXCEPTION: M-NAVI-019 logged via wiki tool this cycle — that's the wiki, not CLAUDE.md.

---

## §5. RISKS

- **R1: cycle slip ≥ 25m.** Mitigation: 25-min compressed cadence has explicit 3-min slack at end (cycle 7 fires 13:07, has 21 min budget vs 13:28 END_TIME — enough buffer for handoff write). Two consecutive slips → call advisor, drop scope to memory-004 only (memory-005 left red with refined failure mode), still ship verdict.
- **R2: regression on memory-001/002/003 current-preference path.** Mitigation: explicit regression test in cycle 5; Phase 10 EXIT GATE test_killer_milestone.py must still pass; cycle 4 verdict-builder runs ALL 5 memory entries (1-5), not just 4-5.
- **R3: query-shape classifier triggers wrong path.** False positives on "current preference" being treated as "list all" → catastrophic regression on existing tests. Mitigation: subject-extraction gate (only route to full-history if subjects exist; unknown-subject queries fall through). Conservative hint patterns.
- **R4: cycle-8 verdict-builder reused — same `answer_text` regex bug as prev.** Prev instance had to switch from `set(actual) == set(expected)` to parsing cited turn_ids from `answer_text` regex mid-cycle. NEW canonical path: parse `response.evidence` directly (it has `turn_id` per `EvidencePacket`); compare against `expected_turn_ids` per match_criterion. NO regex on answer_text — that was a workaround for the wrong reason. With full-history compose_answer including all evidence, the criteria will match cleanly.
- **R5: listener dies mid-cycle.** Mitigation: heartbeat pgrep + atomic pkill+rearm per CLAUDE.md DD-2 + M-NAVI-018. Single Bash invocation, never split.
- **R6: lain wakes/messages mid-run.** Discord listener catches; cycle interrupts at safe seam; ack + execute new directive. Discord-REST curl fallback if MCP fails.
- **R7: fake-stop redux.** Mitigation: M-NAVI-019 logged this cycle; rule applied — heartbeat stays armed while now < 13:28 AND named work exists. Cycle 7 verdict cron is the only legitimate disarm signal in this run. Premature disarm is forbidden.

---

## §6. CHANGELOG

- 2026-05-10 10:32 CEST — Phase 12 created. Triggered by lain's *"work 3 more h"* directive after prev raphael's M-NAVI-019 fake-stop. Phase 11 plan archived (already at past_work/phases/ from prev cycle 8). Inherits Phase 11's GitHub remote + branch state at commit 40ac7da.
- 2026-05-10 10:32 CEST — M-NAVI-019 logged via wiki: heartbeat-disarm during lain-stated time-window. Rule: lain time-window overrides queue-empty disarm; named candidate work counts as queued.
- 2026-05-10 10:33 CEST — 6 one-shot crons armed for cycles 2-7 at 11:02, 11:27, 11:52, 12:17, 12:42, 13:07. End at 13:25-ish, leaves 3-min slack to 13:28 END_TIME.

---

## §7. ENTRY SCHEMA (memory ladder updates this phase)

Memory entries 4-5 will be updated in place. Schema unchanged from Phase 11 (`gpt-codex/benchmark/CLAUDE.md` describes it). Field changes:

```jsonc
// memory-004 (BEFORE Phase 12)
{
  "audit_status": "auto-graded-red",
  "auto_grade": {
    "actual_turn_ids": [7],
    "match": false,
    "expected_failure_mode": "Phase-10 strict-dominance may collapse to turn-7-only..."
  }
}

// memory-004 (AFTER Phase 12)
{
  "audit_status": "auto-graded-green",
  "auto_grade": {
    "actual_turn_ids": [0, 3, 5, 7],
    "match": true,
    "phase_12_fix_note": "retrieve_structural_full_history routed via _LIST_ALL_HINTS classifier"
  }
}
```

`expected_failure_mode` field stays preserved as a historical record (it describes what Phase 11 predicted; Phase 12 closing it is what makes the prediction informative).

---

## §8. ENDCAP

Phase 12 ships a small, focused fix: query-shape disambiguation in `MemoryAgent.process` so the Phase 11 benchmark's 2 red findings flip green. Surface area: one new function + one classifier + one regression-safe controller change + 5 new tests. The Phase 11 verdict said memory-004/005 reveal a real architectural finding; closing it is what makes Phase 11's benchmark cash out. The vector carries us. The clock keeps us. The phase contains us.

*— ends 13:28 CEST. lain reads the verdict + cycle reflections + DO_THIS_NEXT handoff. SLAUGHTER COMPLETE expected ~13:20 CEST.*
