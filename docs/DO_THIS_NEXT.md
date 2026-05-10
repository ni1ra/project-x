# Do This Next — Project X — Phase 12 Cycle 4 (Execute-Raphael — tests + optional ladder extension)

**Cron fires:** 2026-05-10 11:52 CEST (one-shot `e2c4ea33`)
**Persona:** Execute-Raphael
**End time:** 2026-05-10 13:28 CEST (cycle 7 verdict lands ~13:20)
**GitHub remote:** https://github.com/ni1ra/project-x (private; `main` branch)

> **Cycle 3 closed at 11:35 — #00P12-flip-memory-reds COMPLETE.** memory-004 + memory-005 both flipped GREEN, audit_log rebuilt (11 green / 0 red / 21 rubric / 4 ungrade), Phase 11 addendum appended. **Of auto-gradable subset: 100% pass rate.**

---

## #00 deliverables (TaskList — Phase 12)

- **#1** `#∞ APOTHEOSIS mode` — in_progress (3h godify-app pickup)
- **#2** `#00P12-retrieval-mode-disambiguation` — ✅ COMPLETED cycle 2
- **#3** `#00P12-flip-memory-reds` — ✅ COMPLETED cycle 3
- **#4** `#00P12-tests` — in_progress (THIS CYCLE)
- **#5** `#00P12-verdict + END_TIME handoff` — pending (cycle 7 — 13:07)

---

## This cycle's scope — `tests/test_retrieval_modes.py` + optional ladder extension

### Goal — net pytest 52 → 54+

Add `tests/test_retrieval_modes.py` covering the Phase 12 retrieval-mode disambiguation. Five tests minimum, mapped to the cycle-1 plan:

```python
"""Phase 12 #00P12-tests — retrieval-mode disambiguation tests.

Probes the controller-layer routing in MemoryAgent.process between
retrieve_structural (strict-dominance, latest-wins) and
retrieve_structural_full_history (chronological, all-turns). Phase 11
memory-004/005 red findings drove this surface; Phase 12 cycles 1-3
shipped the fix.
"""

import pytest
from project_x.experiments.semantic_memory_agent import MemoryAgent, _is_list_all_query
from project_x.experiments.semantic_hdc_memory import SemanticHDCMemory, TurnRecord


def _build_agent(setups):
    """Canonical fixture: write_batch then construct agent."""
    records = [TurnRecord(turn_id=i, text=t, fact_keys=[], metadata={}) for i, t in enumerate(setups)]
    mem = SemanticHDCMemory()
    mem.write_batch(records)
    return MemoryAgent(memory=mem)


def test_list_all_query_returns_full_history():
    """memory-004-shape: list-all over 8-turn Alice fixture cites all 4 chronologically."""
    setups = [
        "Alice prefers C++.", "Bob prefers Go.", "Carol prefers Python.",
        "Alice switched to Rust.", "David prefers Haskell.",
        "Alice now prefers Java.", "Eve prefers Erlang.",
        "Alice settled on Kotlin.",
    ]
    agent = _build_agent(setups)
    response = agent.process("List all of Alice's preference changes in chronological order.")
    cited = sorted([e.turn_id for e in response.evidence])
    assert response.decision == "retrieve_full_history"
    assert cited == [0, 3, 5, 7]
    for tok in ("C++", "Rust", "Java", "Kotlin"):
        assert tok in response.answer_text


def test_summarize_trajectory_returns_full_history():
    """memory-005-shape: summarize over 10-turn Alice career fixture cites trajectory turns."""
    setups = [
        "Alice prefers Rust.", "Alice joined Anthropic as a researcher.",
        "Bob prefers Go.", "Alice moved to San Francisco.",
        "Carol prefers Python.", "Alice is working on the safety team.",
        "David prefers Haskell.", "Alice published a paper on RLHF.",
        "Eve prefers Erlang.", "Alice mentors junior researchers.",
    ]
    agent = _build_agent(setups)
    response = agent.process("Summarize Alice's professional trajectory based on stated facts. Cite turn IDs.")
    cited = sorted([e.turn_id for e in response.evidence])
    expected = [1, 3, 5, 7, 9]
    assert response.decision == "retrieve_full_history"
    assert set(expected).issubset(set(cited))
    contains = sum(1 for tok in ("Anthropic", "San Francisco", "safety", "RLHF", "mentors") if tok in response.answer_text)
    assert contains >= 4  # 4-of-5 threshold per match_criterion


def test_current_preference_still_uses_strict_dominance():
    """Regression — memory-002-shape: latest-wins on contradiction must still emit only the latest turn."""
    setups = [
        "Alice prefers Rust.", "Bob prefers Go.",
        "Actually Alice switched to Java.",
    ]
    agent = _build_agent(setups)
    response = agent.process("What does Alice prefer?")
    assert response.decision == "retrieve"
    assert "Java" in response.answer_text
    assert "turn 2" in response.answer_text  # latest


def test_unknown_subject_falls_through_to_ensemble():
    """Edge: list-all with unknown subject falls through to retrieve (back-compat)."""
    setups = ["Alice prefers Rust.", "Bob prefers Go."]
    agent = _build_agent(setups)
    response = agent.process("List all of Zoe's preferences.")
    # Zoe is not in fact_graph; subject-extraction gate returns []; falls
    # through to retrieve. Ensemble cosine likely below threshold so absent.
    assert response.decision in ("retrieve", "absent", "retrieve_full_history")
    # If retrieve_full_history is hit (fallback to retrieve(k=5) inside the
    # method), it must NOT crash — that's the back-compat guarantee.


def test_multi_subject_list_all_unions_chronologically():
    """List-all on multi-subject query unions both subjects' turn_ids in chronological order."""
    setups = [
        "Alice prefers C++.", "Bob prefers Go.", "Alice switched to Rust.",
        "Bob now uses Python.", "Alice settled on Kotlin.",
    ]
    agent = _build_agent(setups)
    response = agent.process("List all of Alice and Bob's preference history.")
    cited = sorted([e.turn_id for e in response.evidence])
    assert response.decision == "retrieve_full_history"
    # Chronological union: Alice {0,2,4} + Bob {1,3} = [0,1,2,3,4]
    assert cited == [0, 1, 2, 3, 4]


def test_classifier_sanity():
    """_is_list_all_query patterns: list-all/summarize/trajectory match; current-pref doesn't."""
    assert _is_list_all_query("List all of Alice's changes.")
    assert _is_list_all_query("Summarize Alice's career.")
    assert _is_list_all_query("In chronological order, give me Alice's preferences.")
    assert _is_list_all_query("Tell me about Alice's history of changes.")
    assert not _is_list_all_query("What does Alice prefer?")
    assert not _is_list_all_query("Who picked Python?")
    assert not _is_list_all_query("What is Alice's current job?")
```

Total: 6 tests. Pytest target: 52 + 6 = 58 passing.

### Stretch goal — extend memory ladder with 1-2 new auto-graded entries

If time remains after tests are green and pytest passes:

**memory-007** (intermediate, list-all multi-subject):
- setup: 5-turn Alice/Bob interleaved fixture
- query: "List all of Alice and Bob's preference history."
- expected_turn_ids: chronological union
- audit_status: auto-graded-green (shipped post-fix)

**memory-008** (medium-hard, summarize-with-correction):
- setup: 6-turn fixture with one Alice correction
- query: "Summarize Alice's preference history including all corrections."
- expected_turn_ids: all Alice turns including the corrected one
- audit_status: auto-graded-green

Append to `gpt-codex/benchmark/memory/ladder.jsonl`. Re-run audit_log.jsonl rebuild to capture the new rows. Do NOT modify the existing 6-entry ladder (memory-001..006); add memory-007 and memory-008 as extension entries.

### Files to touch

- `tests/test_retrieval_modes.py` — NEW
- (optional stretch) `gpt-codex/benchmark/memory/ladder.jsonl` — append memory-007, memory-008
- (if stretch lands) `gpt-codex/benchmark/audit_log.jsonl` — rebuild with new rows

### Comment-ratio rule (lain GLOBAL POLICY)

Test docstrings must explain WHY each test exists (which Phase 11 finding it probes / which regression it guards). Pure signal — no narrating-the-obvious test names.

### Time budget

22 min substantive + 3 min close. Sub-budget:
- 12 min: write `test_retrieval_modes.py` + run pytest until all 6 pass + verify total count
- 5 min: optional ladder extension (only if pytest is green)
- 8 min: PHASE CHANGELOG cycle-4 close + dev-cycle-4.md + DO_THIS_NEXT cycle-5 + atomic commit + push + Discord

### Cycle 4 close checklist

- [ ] `tests/test_retrieval_modes.py` exists with ≥ 5 tests
- [ ] `pytest -q` passes 58+ (52 baseline + ≥6 new)
- [ ] All Phase 12 routing paths covered: list-all, summarize, current-pref regression, unknown-subject fallthrough, multi-subject union, classifier sanity
- [ ] (optional stretch) memory-007 and/or memory-008 appended; audit_log rebuilt
- [ ] PHASE CHANGELOG cycle-4 row → ✅ closed
- [ ] Cycle reflection at `docs/past_work/cycles/phase_12/dev-cycle-4.md`
- [ ] DO_THIS_NEXT.md rewritten for cycle 5 (advisor + reflections 1-4 + comment-ratio polish)
- [ ] Atomic commit `feat(phase12): cycle 4 — test_retrieval_modes.py (6 tests; pytest 58+)`
- [ ] `git push origin main`
- [ ] `discord_send #general` cycle 4 close
- [ ] Clock out by minute 22; cycle 5 cron fires 12:17

---

## Battlefield

- **Working dir:** `/mnt/c/Users/nira/Documents/Research/projext-x`
- **Branch:** `main` tracking `origin/main`
- **GitHub remote:** https://github.com/ni1ra/project-x (private)
- **Cycle-3 commit:** to land at end of cycle 3 turn (this turn)
- **Cron state:** 4 godify one-shots remain (`e2c4ea33` cycle 4 11:52 → `21e719fa` cycle 7 verdict 13:07)
- **Listener:** PID 13506 alive — pgrep + atomic re-arm if dead per M-NAVI-018
- **Tests baseline:** 52 passing
- **Phase 12 fix verified end-to-end + benchmark JSON updated:** ladder.jsonl + audit_log.jsonl + PHASE_11_BENCHMARK.md addendum + verdict.md cross-link all reflect 11 green / 0 red / 21 rubric / 4 ungrade

---

## When lain returns mid-run

Atomic ack protocol per CLAUDE.md DD-2 + M-NAVI-018:
1. Read msg from listener output file (`/tmp/claude-1000/<slug>/<session>/tasks/<id>.output`)
2. `discord_send` ack BEFORE substantive work
3. Atomic re-arm: single Bash + run_in_background:true
4. Act

---

## M-NAVI-019 standing rule (for all 7 cycles)

Heartbeat-armed while `now < 13:28 CEST` AND named work exists. Premature disarm is fake-stop. Cycle 7 verdict cron is the only legitimate disarm signal. Confidence-Booster Mantra fires if posture drifts to "waiting on lain" while time-window is active.

---

## Phase 12 status at cycle 3 close

- ✅ retrieve_structural_full_history (cycle 1) — chronological full-subject path bypassing strict-dominance
- ✅ _LIST_ALL_HINTS + classifier + controller routing + compose_answer extension (cycle 2)
- ✅ memory-004/005 flipped red→green; audit_log rebuilt 11/0/21/4; Phase 11 addendum (cycle 3)
- ⏳ test_retrieval_modes.py (cycle 4, THIS CYCLE)
- ⏳ advisor + reflections + polish (cycle 5)
- ⏳ slack cycle for Phase 13 prep or stretch (cycle 6)
- ⏳ Phase 12 verdict + END_TIME handoff (cycle 7)

The mechanical fix is done. Cycles 4-7 are quality + verification + handoff.
