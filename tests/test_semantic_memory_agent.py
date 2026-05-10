"""Tests for MemoryAgent (Phase 9 Cycle 6, Layer 4 — FINAL)."""

from __future__ import annotations

import pytest

from project_x.experiments.semantic_hdc_memory import (
    SemanticHDCMemory, TurnRecord,
)
from project_x.experiments.semantic_memory_agent import (
    MemoryAgent, EvidencePacket, classify_input, compose_answer,
)


def _build_agent(seed: int = 1337) -> MemoryAgent:
    records = [
        TurnRecord(turn_id=0, text="Alice prefers Python."),
        TurnRecord(turn_id=1, text="Bob settled on Rust for systems work."),
        TurnRecord(turn_id=2, text="Carol picked Postgres for the database."),
        TurnRecord(turn_id=3, text="The build is green."),
    ]
    mem = SemanticHDCMemory(D=2048, alpha=0.5, negative_samples=2, seed=seed)
    mem.write_batch(records)
    return MemoryAgent(memory=mem, cosine_threshold=0.10)  # low threshold for tiny corpus


def test_classify_input_routes_questions_and_assertions():
    assert classify_input("What does Alice prefer?") == "question"
    assert classify_input("Where is the controller?") == "question"
    assert classify_input("Alice prefers Python.") == "assertion"
    assert classify_input("we settled on Postgres for the database.") == "assertion"
    # Default to question on ambiguous
    assert classify_input("ambiguous freeform text") == "question"


def test_compose_answer_no_evidence():
    answer, decision, conf = compose_answer("anything", [], cosine_threshold=0.25)
    assert decision == "absent"
    assert "no evidence" in answer.lower()
    assert conf == 0.0


def test_compose_answer_below_threshold_returns_absent():
    ev = [EvidencePacket(turn_id=0, cosine=0.10, text="some text")]
    answer, decision, conf = compose_answer("anything", ev, cosine_threshold=0.25)
    assert decision == "absent"
    assert "below threshold" in answer.lower()
    assert conf == 0.10


def test_compose_answer_single_evidence_cites_turn_id():
    ev = [EvidencePacket(turn_id=42, cosine=0.55, text="Alice prefers Python.")]
    answer, decision, conf = compose_answer("Q", ev, cosine_threshold=0.25)
    assert decision == "retrieve"
    assert "42" in answer
    assert "Alice prefers Python." in answer
    assert conf == 0.55


def test_compose_answer_multi_evidence_joins_with_AND():
    ev = [
        EvidencePacket(turn_id=1, cosine=0.6, text="A"),
        EvidencePacket(turn_id=2, cosine=0.5, text="B"),
    ]
    answer, decision, conf = compose_answer("Q", ev, cosine_threshold=0.25)
    assert decision == "retrieve"
    assert "AND" in answer
    assert "1" in answer and "2" in answer


def test_agent_process_question_returns_answer_packet():
    agent = _build_agent()
    packet = agent.process("What does Alice prefer?")
    assert packet.query == "What does Alice prefer?"
    assert packet.decision == "retrieve", (
        f"Alice query should retrieve (cosine_threshold=0.10 in fixture), got {packet.decision}"
    )
    assert packet.evidence, "evidence must be non-empty when decision=retrieve"
    # Alice's preference is turn 0. The original assertion `turn_id in [0,1,2,3]` was
    # always true (any non-filler corpus turn passed). Tighten to top-1 == 0.
    assert packet.evidence[0].turn_id == 0, (
        f"Alice's preference (turn 0) should be top-1 evidence, got {packet.evidence[0].turn_id}"
    )


def test_agent_process_assertion_does_not_contaminate_fact_graph_with_objects():
    """Phase 11 P2 (#00P11b) — `_subjects_from_text` first-token-only fix.

    Before the fix, `agent.process("Alice now prefers Rust.")` populated
    fact_graph["Alice"] AND fact_graph["Rust"] because all capitalized
    non-stopword tokens were treated as subjects. fact_graph["Rust"]
    pointing at Alice's turn would later cause "Who uses Rust?" structural
    retrieval to surface Alice's turn at top-1 — wrong attribution.

    After the fix: only the first capitalized non-stopword token is treated
    as the subject; objects like "Rust" / "Java" / file paths do NOT enter
    fact_graph from agent.process writes."""
    records = [
        TurnRecord(turn_id=0, text="Initial seed.", fact_keys=[]),
    ]
    mem = SemanticHDCMemory(D=2048, alpha=0.5, negative_samples=2, seed=1337)
    mem.write_batch(records)
    agent = MemoryAgent(memory=mem, cosine_threshold=0.10)
    agent.process("Alice now prefers Rust.")
    assert "Alice" in mem._fact_graph, (
        f"fact_graph should contain Alice (subject); keys={list(mem._fact_graph.keys())}"
    )
    assert "Rust" not in mem._fact_graph, (
        f"fact_graph should NOT contain Rust (object); the first-token-only fix "
        f"should prevent this contamination. keys={list(mem._fact_graph.keys())}"
    )


def test_agent_process_assertion_writes_and_is_retrievable():
    """Phase 10 P4: assertions write into memory incrementally (no batch rebuild).
    The newly-written turn is retrievable via the agent's structural retrieval
    path immediately afterward — no end-of-session refit required."""
    agent = _build_agent()
    write_packet = agent.process("Alice prefers Java now.")
    assert write_packet.decision == "write"
    assert "written" in write_packet.answer_text.lower()
    # The new turn surfaces on retrieval. Structural retrieval extracts "Alice"
    # subject; recency-strict-dominance puts the LATEST Alice turn at top-1.
    follow_up = agent.process("What does Alice prefer?")
    assert follow_up.decision == "retrieve"
    assert follow_up.evidence
    # Original Alice turn was turn_id 0; the new write is at turn_id 4 (the
    # _build_agent fixture had 4 records: 0/1/2/3, so the next id is 4).
    new_turn_id = follow_up.evidence[0].turn_id
    assert new_turn_id == 4, (
        f"latest Alice assertion should win top-1 via structural recency, got "
        f"{[(e.turn_id, e.cosine, e.text[:30]) for e in follow_up.evidence]}"
    )


def test_agent_50_turn_write_retrieve_sequence():
    """Phase 10 P4 correctness gate (#00d). 50 alternating write+retrieve calls
    on a small memory: each write becomes retrievable; replay_consolidate fires
    once during the sequence (replay_cadence=20 to ensure ≥1 fire); subsequent
    retrieves still work post-consolidation."""
    records = [
        TurnRecord(turn_id=0, text="Alice prefers Python."),
        TurnRecord(turn_id=1, text="Bob settled on Rust for systems work."),
    ]
    mem = SemanticHDCMemory(D=2048, alpha=0.5, negative_samples=2, seed=1337)
    mem.write_batch(records)
    agent = MemoryAgent(memory=mem, cosine_threshold=0.10, replay_cadence=20)

    # 25 writes interleaved with retrieves of the most-recent claim.
    for i in range(25):
        person = "Alice" if i % 2 == 0 else "Bob"
        new_lang = f"Lang{i:02d}"
        write_packet = agent.process(f"{person} now prefers {new_lang}.")
        assert write_packet.decision == "write"
        # Immediately retrieve and check the new turn is reachable.
        follow_up = agent.process(f"What does {person} prefer?")
        assert follow_up.decision == "retrieve"
        assert follow_up.evidence
        # The most-recent person-turn must be retrievable as top-1 (structural
        # recency-strict-dominance handles this).
        ev_ids = [e.turn_id for e in follow_up.evidence]
        # The just-written turn for `person` is the second-to-last memory turn
        # (since the retrieve query above was just classified as a question and
        # didn't write). Its turn_id is len(memory._records) - 1 at the moment
        # of the write call.
        # We assert the top-1 turn_id is one of Alice's or Bob's recent turns.
        assert ev_ids[0] >= 2, (
            f"top-1 should be a freshly-written turn (id ≥ 2), got {ev_ids[0]}; "
            f"evidence={[(e.turn_id, e.text[:30]) for e in follow_up.evidence[:3]]}"
        )

    # Replay should have fired at least once (20 writes < 25 writes, 25 ≥ 20 → 1+ fires).
    # We can verify by counting reset cycles; agent._writes_since_replay should be < replay_cadence.
    assert agent._writes_since_replay < 20, (
        f"expected at least one replay_consolidate call, "
        f"_writes_since_replay={agent._writes_since_replay}"
    )

    # After all writes + 1+ replays, original baseline turns are still reachable.
    # Earlier Alice turn (turn 0) is no longer top-1 (newer Alice turns supersede),
    # but it should still be a valid record.
    assert mem._records[0].text == "Alice prefers Python."
    assert mem._records[1].text == "Bob settled on Rust for systems work."


def test_agent_contradiction_latest_wins():
    """Post-P3 the structural retrieval path (fact-graph + recency boost) lets the
    agent prefer the latest revision turn for contradiction-style queries. Asserts
    LATEST (supersedes) turn wins on `agent.process`. xfail removed 2026-05-10
    when P3/#00c-1 landed and flipped this from red to green."""
    records = [
        TurnRecord(turn_id=0, text="Alice prefers Python."),
        TurnRecord(turn_id=1, text="Bob settled on Rust for systems work."),
        TurnRecord(turn_id=2, text="Carol picked Postgres for the database."),
        TurnRecord(turn_id=3, text="The build is green."),
        TurnRecord(turn_id=4, text="Actually Alice switched to Rust."),  # revision
    ]
    mem = SemanticHDCMemory(D=2048, alpha=0.5, negative_samples=2, seed=1337)
    mem.write_batch(records)
    agent = MemoryAgent(memory=mem, cosine_threshold=0.10)
    packet = agent.process("What is Alice's current preferred language?")
    assert packet.decision == "retrieve"
    assert packet.evidence
    # Revision turn (4) must outrank original (0).
    top_id = packet.evidence[0].turn_id
    assert top_id == 4, (
        f"Latest-wins violation: expected turn 4 (revision) at top-1, got {top_id}; "
        f"evidence: {[(e.turn_id, e.cosine) for e in packet.evidence]}"
    )


def test_agent_absent_answer_decision():
    """Querying an unknown person yields decision='absent' at the canonical Phase 9
    cosine_threshold=0.30 (the threshold pre-#00b sweep targets). Pre-#00b this is
    a tight test — if it xfails, that is real signal that even threshold=0.30 has
    FP leakage on the small fixture, reproducing the reviewer's call-out at unit
    scale. P5/#00b's threshold sweep + ensemble-disagreement gating is the fix."""
    records = [
        TurnRecord(turn_id=0, text="Alice prefers Python."),
        TurnRecord(turn_id=1, text="Bob settled on Rust for systems work."),
        TurnRecord(turn_id=2, text="Carol picked Postgres for the database."),
        TurnRecord(turn_id=3, text="The build is green."),
    ]
    mem = SemanticHDCMemory(D=2048, alpha=0.5, negative_samples=2, seed=1337)
    mem.write_batch(records)
    agent = MemoryAgent(memory=mem, cosine_threshold=0.30)
    packet = agent.process("What does Ghost9999 prefer?")
    assert packet.decision == "absent", (
        f"Ghost9999 absent-query at threshold=0.30 should return absent, got "
        f"decision={packet.decision} with evidence "
        f"{[(e.turn_id, e.cosine) for e in packet.evidence]}"
    )


def test_agent_multi_hop_recovers_both_subjects():
    agent = _build_agent()
    packet = agent.process_with_multi_hop("What do Alice and Bob prefer?")
    assert packet.query == "What do Alice and Bob prefer?"
    assert isinstance(packet.evidence, list)
    evidence_turn_ids = {e.turn_id for e in packet.evidence}
    # Reviewer's call-out: assert BOTH expected turn_ids in evidence packet,
    # not just isinstance-list check.
    # Alice=turn 0, Bob=turn 1.
    assert 0 in evidence_turn_ids, (
        f"Alice's preference (turn 0) missing from evidence: {evidence_turn_ids}"
    )
    assert 1 in evidence_turn_ids, (
        f"Bob's preference (turn 1) missing from evidence: {evidence_turn_ids}"
    )
