# Phase 12 Cycle 2 Reflection — Controller wiring + classifier

**When:** 2026-05-10 11:02 → ~11:08 CEST (~6 min substantive on a 25-min budget)
**Persona:** Execute-Raphael
**Status:** ✅ closed; #00P12-retrieval-mode-disambiguation FULLY shipped end-to-end (cycle 1 implemented memory.py side; cycle 2 wired the controller; both memory-004 and memory-005 confirmed GREEN through full `MemoryAgent.process` path)

## What landed

| Artifact | Surface |
|---|---|
| `_LIST_ALL_HINTS` tuple | 10 conservative patterns: `list all`, `all of`, `summarize`, `trajectory`, `history of`, `all changes`, `in chronological order`, `in order`, `every change`, `full history` |
| `_is_list_all_query(text)` classifier | lower + any-hint-match; module-level helper |
| `MemoryAgent.process` extension | dual-gate routing: `_is_list_all_query(text) AND bool(memory._extract_query_subjects(text))` → `retrieve_structural_full_history(text, k=None)`; else existing `retrieve_structural(text, k=self.k_retrieve)` |
| `compose_answer` extension | new `full_history: bool = False` kwarg; when True, short-circuits cosine_threshold filter and cites ALL evidence chronologically; decision label `retrieve_full_history` |

WHY-comments per lain GLOBAL POLICY 2026-05-10: every change carries a comment justifying its existence + Phase 11 verdict pointer + memory-004/005 architectural finding context.

## End-to-end smoke verification

**Classifier sanity (6/6 PASS):**

| Query | _is_list_all_query | Expected |
|---|---|---|
| "List all of Alice's preference changes in chronological order, with turn IDs." | True | True ✓ |
| "Summarize Alice's professional trajectory based on stated facts. Cite turn IDs." | True | True ✓ |
| "What does Alice prefer?" | False | False ✓ |
| "What do Alice and Bob prefer?" | False | False ✓ |
| "Tell me about Alice's history of changes." | True | True ✓ |
| "What is Alice's current job?" | False | False ✓ |

**memory-004 (was RED) — TARGET FLIP:**
- query: `"List all of Alice's preference changes in chronological order, with turn IDs."`
- decision: `retrieve_full_history`
- answer_text: `"Based on turns 0, 3, 5, 7: 'Alice prefers C++.' AND 'Alice switched to Rust.' AND 'Alice now prefers Java.' AND 'Alice settled on Kotlin.'"`
- cited turns: [0, 3, 5, 7] ✓ matches expected [0, 3, 5, 7]
- contains tokens: 4/4 (C++, Rust, Java, Kotlin) ✓
- **GREEN ✓**

**memory-005 (was RED) — TARGET FLIP:**
- query: `"Summarize Alice's professional trajectory based on stated facts. Cite turn IDs."`
- decision: `retrieve_full_history`
- answer_text: `"Based on turns 0, 1, 3, 5, 7, 9: 'Alice prefers Rust.' AND 'Alice joined Anthropic as a researcher.' AND 'Alice moved to San Francisco.' AND 'Alice is working on the safety team.' AND 'Alice published a paper on RLHF.' AND 'Alice mentors junior researchers.'"`
- cited turns: [0, 1, 3, 5, 7, 9] ⊇ expected [1, 3, 5, 7, 9]
- (turn 0 "Alice prefers Rust" is included; the entry's own note marks it "borderline (career-adjacent; OK to include or exclude)" — superset is fine per match_criterion `expected_turn_ids subseteq cited turn_ids`)
- contains tokens: 5/5 (Anthropic, San Francisco, safety, RLHF, mentors) ✓
- **GREEN ✓**

**Regression safety (memory-001/002/003 current-preference path, answer_text-parsed cited turns):**
- memory-001: answer "Based on turn 0: 'Alice prefers Rust.'" → cited [0] = expected [0] ✓
- memory-002: answer "Based on turn 2: 'Actually Alice switched to Java.'" → cited [2] = expected [2] ✓
- memory-003: answer "Based on turns 0, 1: 'Alice prefers Rust.' AND 'Bob prefers Go.'" → cited [0, 1] = expected [0, 1] ✓

(NB: `response.evidence` returns the full top-k retrieval set, not the threshold-filtered cited set — the `actual_turn_ids` field in ladder.jsonl is parsed from `answer_text`. Cycle 3 verdict-builder uses the answer_text-parse path, matching prev cycle-8's pattern.)

**`pytest -q`: 52 passing (no regression).**

## What cycle 3 inherits

- Both halves of #00P12-retrieval-mode-disambiguation are SHIPPED. The fix works end-to-end.
- Cycle 3's job: re-run cycle-8-style verdict-builder against the fixed agent → update `gpt-codex/benchmark/memory/ladder.jsonl` entries 4-5 with new `actual_turn_ids` + `match: true` + `audit_status: "auto-graded-green"`. Rebuild `gpt-codex/benchmark/audit_log.jsonl` with new counts (11 green / 0 red / 21 rubric-pending / 4 ungradeable). Append addendum to `docs/artifacts/PHASE_11_BENCHMARK.md` documenting the closure.
- Cycle 4 inherits the unchanged tests scope.

## Why cycle 2 finished in 6 minutes

The implementation surface for cycles 2-3 (controller wiring) was small. The hard work was in cycle 1's memory.py-side method which had the actual algorithmic content (chronological union + base cosines + safe fallbacks). Cycle 2 wired the existing pieces:
- 1 tuple constant (10 patterns)
- 1 helper function (~10 lines)
- 1 if-else routing block in `process` (~15 lines including comment)
- 1 short-circuit in `compose_answer` (~15 lines including comment)

Total LoC delta for cycle 2: ~50 lines. The bulk was WHY-comments per the global comment-ratio rule.

## Time accounting

| Stage | Duration |
|---|---|
| Bash mechanical state + edits × 3 | ~3 min |
| Smoke test (correct write_batch pattern after first run errored) | ~2 min |
| Reflection + commit + Discord (this turn) | ~1 min |
| **Total cycle 2** | ~6 min |

19 min slack rolls forward to cycle 3.

## Lesson noted (not a mistake — just an API friction)

`agent.process(setup_text)` for assertion-shape inputs calls `memory.write_one`, which requires prior `memory.write_batch` to have initialized state. The canonical fixture pattern is `mem.write_batch([TurnRecord(...) for setup])` THEN `agent.process(query)` — same pattern used in `semantic_memory_agent.py:main()` and `tests/test_killer_milestone.py`. Prev cycle 8's verdict-builder hit and resolved this same issue. Cycle 3's verdict-builder will use this pattern by default.
