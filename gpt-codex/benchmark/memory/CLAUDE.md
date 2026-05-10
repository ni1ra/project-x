# gpt-codex/benchmark/memory/

## What lives here

Phase 11 Raphael Domain Benchmark Suite — memory ladder. 6 entries spanning intro→unsolved.

## Why it exists

Per Phase 11 plan §DOMAINS — memory ladder probes the Phase 9-10 HDC stack DIRECTLY: each auto-graded entry has a `setup` (list of turn-text strings) and a query, with expected cited turn_ids derived from the Phase 10 fact-graph + structural-retrieval + strict-dominance-recency mechanics. ALL 6 entries are auto-graded except rank 6 (meta-theoretical question about consolidation, ungradeable by design).

## Conventions

- `ladder.jsonl`: one entry per line, one entry per difficulty rank (1=intro through 6=unsolved). Schema per `docs/A_TO_Z_PLAN.md` §7.
- `rubric.md`: per-rank grading dimensions (already shipped cycle 2; auto-grade hooks specified).
- New entries: append to `ladder.jsonl` with next id (`memory-NNN`).
- **`self_score` MUST NOT appear** (M-PROJECTX-014 firewall).

## Auto-grade execution (cycle 8 verdict-builder runs this)

Cycle 8 verdict-builder:

```python
from project_x.experiments.semantic_memory_agent import MemoryAgent
from project_x.experiments.semantic_hdc_memory import SemanticHDCMemory

import json

with open("gpt-codex/benchmark/memory/ladder.jsonl") as f:
    entries = [json.loads(line) for line in f]

for entry in entries:
    if entry["audit_status"] != "auto-graded-pending-execution":
        continue  # rank 6 ungradeable; skip

    mem = SemanticHDCMemory()
    agent = MemoryAgent(memory=mem)

    # Write setup turns (each becomes a turn_id 0, 1, 2, ...)
    for setup_text in entry["auto_grade"]["setup"]:
        agent.process(setup_text)

    # Query
    query = entry["auto_grade"]["query"]
    response = agent.process(query)

    # Parse cited turn_ids from response.evidence
    actual_turn_ids = sorted([e.turn_id for e in response.evidence])
    expected_turn_ids = sorted(entry["auto_grade"]["expected_turn_ids"])

    # Match criterion (per entry-specific rule)
    if entry["auto_grade"]["match_criterion"].startswith("expected_turn_ids equals"):
        match = expected_turn_ids == actual_turn_ids
    elif entry["auto_grade"]["match_criterion"].startswith("expected_turn_ids subseteq"):
        match = set(expected_turn_ids).issubset(set(actual_turn_ids))
    else:
        match = False  # unknown criterion — fail closed

    # Plus: expected_response_contains check
    answer_text = response.answer_text.lower()
    contains_match = all(tok.lower() in answer_text for tok in entry["auto_grade"]["expected_response_contains"])

    entry["auto_grade"]["actual_turn_ids"] = actual_turn_ids
    entry["auto_grade"]["match"] = match and contains_match
    entry["audit_status"] = "auto-graded-green" if (match and contains_match) else "auto-graded-red"
```

## Entry summary (cycle 4 ship — cycle 8 executes)

| ID | Difficulty | Probe | Status (cycle 4 ship) |
|---|---|---|---|
| memory-001 | intro (1) | factual recall (Alice prefers Rust) | auto-graded-pending-execution |
| memory-002 | easy (2) | contradiction-LATEST-wins (Alice→Java supersedes Alice→Rust) | auto-graded-pending-execution |
| memory-003 | medium (3) | multi-hop with citations ("Alice and Bob") | auto-graded-pending-execution |
| memory-004 | hard (4) | temporal reasoning — full preference chain (4 turns) | auto-graded-pending-execution (NB: known retrieval-vs-listing tension flagged in entry's `expected_failure_mode`) |
| memory-005 | frontier (5) | episodic-semantic integration — career trajectory (5+ turns) | auto-graded-pending-execution |
| memory-006 | unsolved (6) | unified theory of memory consolidation (meta-theoretical) | ungradeable; unsolved tier |

## Cross-references

- `src/project_x/experiments/semantic_memory_agent.py` — MemoryAgent.process implementation
- `src/project_x/experiments/semantic_hdc_memory.py` — SemanticHDCMemory + fact-graph + structural retrieval + binding
- `tests/test_killer_milestone.py` — Phase 10 EXIT GATE; the 5 capabilities probed by ranks 1-5
- `docs/A_TO_Z_PLAN.md` §3 E3 — schema verification gate; §7 — entry schema
- `docs/artifacts/PHASE_9_SEMANTIC_HDC_MEMORY.md` — Phase 9 verdict + Phase 10 closure addenda

## Last reviewed

2026-05-10 by Raphael (Phase 11 cycle 4 — godify-app APOTHEOSIS).
