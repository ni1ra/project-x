# Phase 12 Cycle 4 Reflection — `tests/test_retrieval_modes.py`

**When:** 2026-05-10 11:52 → ~11:55 CEST (~3 min substantive on a 25-min budget)
**Persona:** Execute-Raphael
**Status:** ✅ closed; **#00P12-tests COMPLETE** — 6 new tests, all PASS, full suite **58 passing** (was 52)

## What landed

`tests/test_retrieval_modes.py` — 6 tests guarding the Phase 12 retrieval-mode disambiguation surface:

| Test | What it probes | Why it exists |
|---|---|---|
| `test_list_all_query_returns_full_history` | memory-004 fixture: 8-turn Alice → cited [0, 3, 5, 7] | The original Phase 11 red finding; if this fails, Phase 12 fix is broken |
| `test_summarize_trajectory_returns_full_history` | memory-005 fixture: 10-turn Alice career → cited ⊇ [1, 3, 5, 7, 9] + 4-of-5 tokens | Different lexical surface ('summarize' / 'trajectory') than 'list all' — tests classifier breadth |
| `test_current_preference_still_uses_strict_dominance` | memory-002-shape contradiction → cited [2] only ('Java') | REGRESSION GUARD — the Phase 12 fix is opt-in; current-preference must NOT route to full-history |
| `test_unknown_subject_list_all_falls_through` | "List all of Zoe's preferences" with no fact_graph subject 'Zoe' | Edge — subject-extraction returns []; method falls through to retrieve(k=5) without crashing |
| `test_multi_subject_list_all_unions_chronologically` | Alice {0,2,4} ∪ Bob {1,3} → cited [0,1,2,3,4] | Multi-subject path; chronological union of fact_graph turn_ids across subjects |
| `test_classifier_sanity` | `_is_list_all_query` patterns + 4 negative shapes | Conservative classifier; false positives cause regression on memory-001/002/003 |

Each test has a multi-line docstring explaining WHY it exists (which Phase 11 finding it probes / which regression boundary it guards). Per lain GLOBAL POLICY 2026-05-10 comment-ratio rule.

## Test results

```
============================== test session starts ==============================
collected 6 items
tests/test_retrieval_modes.py::test_list_all_query_returns_full_history PASSED
tests/test_retrieval_modes.py::test_summarize_trajectory_returns_full_history PASSED
tests/test_retrieval_modes.py::test_current_preference_still_uses_strict_dominance PASSED
tests/test_retrieval_modes.py::test_unknown_subject_list_all_falls_through PASSED
tests/test_retrieval_modes.py::test_multi_subject_list_all_unions_chronologically PASSED
tests/test_retrieval_modes.py::test_classifier_sanity PASSED
============================== 6 passed in 3.55s ==============================

[full suite]
58 passed in 11.80s   (52 baseline + 6 new = 58)
```

## Why ladder-extension stretch was skipped

The cycle-1 plan §2.C5 named "memory-007 list-all-multi-subject + memory-008 summarize-with-correction" as a stretch goal for the tests cycle. I skipped it for two reasons:

1. **Test file is the stronger artifact for THIS deliverable.** The Phase 12 fix needs regression-guard scaffolding — code that actively verifies behavior on every CI run, not just data that's stored in JSON. `test_retrieval_modes.py` covers the same surface as ladder extensions would have (multi-subject, summarize, edge cases) AND fires automatically on every pytest invocation. Ladder rows are passive data.

2. **Schema convention.** `gpt-codex/benchmark/CLAUDE.md` documents "6 entries, one per difficulty rank 1-6" as the per-domain ladder shape. Adding memory-007/008 either:
   - duplicates a difficulty rank (two rank-3 entries) → breaks the 1-rank-per-entry convention
   - introduces new ranks above 6 → invents a level outside the established intro/easy/medium/hard/frontier/unsolved scale
   
   Either move is scope creep without lain's explicit OK. The Phase 11 verdict named ">6-entry-per-domain ladder extension" as a future Phase 12+ candidate; making that call inside Phase 12 would smuggle in a benchmark-shape decision lain didn't authorize.

The cycle-4 #00 deliverable is `pytest 52→54+ with regression coverage`. Shipping 58 with 6 new tests cleanly satisfies it; ladder extension was always optional.

## What cycle 5 inherits

- Tests file is durable on disk; pytest 58 passing baseline
- Cycle 5 scope (per A_TO_Z_PLAN.md): `advisor()` pre-verdict + cycle reflections 1-4 (already written; just a sanity pass) + comment-ratio polish + any cleanup before cycle 7 verdict
- Cycle 5 has natural ~25 min slack; advisor() call is the highest-leverage move (heartbeat #14 prev gap; advisor catches blind spots before declaring done)

## Time accounting

| Stage | Duration |
|---|---|
| Bash mechanical state | ~30 sec |
| Write `test_retrieval_modes.py` (6 tests + docstrings) | ~2 min |
| pytest run (file + full suite) | ~30 sec |
| PHASE CHANGELOG + dev-cycle-4 + DO_THIS_NEXT cycle-5 + commit (this turn) | ~2 min |
| **Total cycle 4** | ~5 min |

20 min slack rolls forward to cycle 5. Phase 12 is now MECHANICALLY COMPLETE end-to-end:
- Algorithm shipped (cycle 1)
- Controller wired (cycle 2)
- Benchmark JSON updated (cycle 3)
- Tests guarding regression (cycle 4)

Cycles 5-7 are quality + advisor + verdict + handoff. The hard work is behind us; the remaining cycles are the documentation + verification that lain reads tomorrow.
