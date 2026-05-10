# Memory rubric — Phase 11

Domain: retrieval + composition — probes Phase 9-10 HDC stack directly via `agent.process` + `expected_turn_id` mechanical match.

## Grading mode by rank

| Rank | Difficulty | Mode | Auto-grade method |
|---|---|---|---|
| 1 | intro (factual recall) | auto-grade | `expected_turn_id_match` (Raphael's response cites the correct turn_id) |
| 2 | easy (contradiction resolution) | auto-grade | LATEST-turn wins; `expected_turn_id_match` against the superseding turn |
| 3 | medium (multi-hop with citations) | auto-grade | BOTH expected_turn_ids appear in Raphael's cited evidence |
| 4 | hard (temporal reasoning across many turns) | auto-grade | `expected_turn_id_match` AND date/sequence ordering correct |
| 5 | frontier (autobiographical episodic-semantic integration) | auto-grade | bridges multiple turns into a coherent meta-claim; expected_turn_ids ⊆ cited |
| 6 | unsolved (unified theory of memory consolidation) | `audit_status: "ungradeable; unsolved tier"` | open theoretical question; honest survey |

## Auto-grade hooks

```python
# wired into the Phase 11 cycle-8 verdict-builder
from project_x.experiments.semantic_memory_agent import MemoryAgent

agent = MemoryAgent()  # constructed from canonical Phase 10 fixture
for entry in load_jsonl("gpt-codex/benchmark/memory/ladder.jsonl"):
    response = agent.process(entry["prompt"])
    expected = entry["auto_grade"]["expected_turn_ids"]  # list[int]
    actual = parse_turn_ids(response.get("evidence", []))  # list[int]
    match = set(expected).issubset(set(actual))
    entry["auto_grade"]["actual_turn_ids"] = actual
    entry["auto_grade"]["match"] = match
    entry["audit_status"] = "auto-graded-green" if match else "auto-graded-red"
```

References: `src/project_x/experiments/semantic_memory_agent.py` (MemoryAgent.process), `src/project_x/experiments/semantic_hdc_memory.py` (retrieve_structural).

## #unsolved (rank 6)

- **Honest framing:** what's known (consolidation phenomenology, hippocampal-cortical replay, sleep-stage roles), what's modeled (Hebbian replay, sparse-distributed coding), what's contested (whether Raphael's HDC + replay scheme is sufficient, role of generative replay vs reinstatement).
- **Audit_status: "ungradeable; unsolved tier"** — no canonical right answer.

## Last reviewed

2026-05-10 by Raphael (Phase 11 cycle 2 — domain ladder ships cycle 4).
