"""Smoke tests for semantic_memory_dataset (Phase 9 Layer 1)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from project_x.experiments.semantic_memory_dataset import (
    build_conversation,
    build_queries,
    run_dataset,
)


def test_build_conversation_smoke():
    turns, fact_map = build_conversation(n_turns=80, seed=1337)
    # 80 base turns + up to 5 contradiction revisions appended
    assert 80 <= len(turns) <= 85
    assert len(fact_map) > 0, "fact_map must contain at least one fact"
    # every substantive fact has a current_value + current_turn_id
    for fk, fm in fact_map.items():
        assert "current_value" in fm
        assert "current_turn_id" in fm
        assert fm["current_value"] != ""


def test_build_queries_all_five_types():
    turns, fact_map = build_conversation(n_turns=120, seed=42)
    queries = build_queries(turns, fact_map, n_queries=50, seed=42)
    seen_types = {q.type for q in queries}
    expected = {"exact_turn_lookup", "semantic_paraphrase", "multi_hop",
                "contradiction", "absent_answer"}
    assert seen_types == expected, f"missing query types: {expected - seen_types}"
    # absent_answer queries have no expected_turn_ids and None expected_answer
    for q in queries:
        if q.type == "absent_answer":
            assert q.expected_turn_ids == []
            assert q.expected_answer is None


def test_run_dataset_writes_files():
    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td) / "ds"
        result = run_dataset(n_turns=80, n_queries=40, seed=1337, out_dir=out_dir)
        assert (out_dir / "conversation.jsonl").exists()
        assert (out_dir / "queries.jsonl").exists()
        assert (out_dir / "result.json").exists()
        assert result["metrics"]["wall_seconds"] < 5.0
        # all 5 query types in the distribution dict
        dist = result["metrics"]["query_type_distribution"]
        assert set(dist.keys()) == {"exact_turn_lookup", "semantic_paraphrase",
                                     "multi_hop", "contradiction", "absent_answer"}


def test_contradictions_have_supersedes_link():
    turns, fact_map = build_conversation(n_turns=200, seed=1337,
                                          contradiction_count=5)
    contradictions = [t for t in turns if t.category == "contradiction"]
    assert len(contradictions) > 0
    for c in contradictions:
        assert c.supersedes_turn_id is not None
        assert c.supersedes_turn_id < c.turn_id, "contradiction must come AFTER original"
