"""Phase 10 EXIT GATE — killer-milestone test (#00g).

Demonstrates ALL 5 reviewer-prescribed capabilities end-to-end on a single
MemoryAgent + SemanticHDCMemory:

  1. Teach a new fact incrementally (write without batch rebuild)
  2. Resolve a correction (latest revision wins on retrieval)
  3. Multi-hop with citations (both subjects' turns surface)
  4. Refuse an absent fact (decision='absent', no FP evidence)
  5. Tool execution + write-back (run_tool result becomes a memory turn)

Until this test passes, Phase 10 is open. When it passes, Phase 10 EXIT GATE
is met. Capabilities ride on:
  - P3 #00c-1 fact-graph + structural retrieval (caps 2, 3, 4)
  - P4 #00d incremental write + replay consolidation (caps 1, 2)
  - #00g extension MemoryAgent.run_tool + read_file tool (cap 5)
"""

from __future__ import annotations

import os
import tempfile

from project_x.experiments.semantic_hdc_memory import (
    SemanticHDCMemory,
    TurnRecord,
)
from project_x.experiments.semantic_memory_agent import MemoryAgent


def _build_killer_agent() -> MemoryAgent:
    records = [
        TurnRecord(turn_id=0, text="Alice prefers Python.",
                   fact_keys=["pref:Alice"]),
        TurnRecord(turn_id=1, text="Bob settled on Rust for systems work.",
                   fact_keys=["pref:Bob"]),
        TurnRecord(turn_id=2, text="Carol picked Postgres for the database.",
                   fact_keys=["pref:Carol"]),
    ]
    mem = SemanticHDCMemory(D=2048, alpha=0.5, negative_samples=2, seed=1337)
    mem.write_batch(records)
    # Use threshold=0.32 (Phase 10 P5 empirical best); replay_cadence high so
    # the test deterministically does NOT trigger consolidation mid-flight.
    return MemoryAgent(memory=mem, cosine_threshold=0.32, replay_cadence=100)


def test_killer_milestone_capability_1_teach_new_fact():
    agent = _build_killer_agent()
    write_packet = agent.process("Alice now prefers Rust.")
    assert write_packet.decision == "write", (
        f"cap 1 (teach): expected decision=write, got {write_packet.decision}; "
        f"answer={write_packet.answer_text!r}"
    )
    # The newly-written turn must be retrievable via the structural path.
    follow_up = agent.process("What does Alice prefer?")
    assert follow_up.decision == "retrieve"
    assert follow_up.evidence
    top_text = follow_up.evidence[0].text
    assert "Rust" in top_text, (
        f"cap 1 (teach): newly-written 'Rust' assertion should win top-1, got {top_text!r}"
    )


def test_killer_milestone_capability_2_resolve_correction():
    agent = _build_killer_agent()
    agent.process("Alice now prefers Rust.")  # cap 1 setup
    correction = agent.process("Actually Alice switched to Java.")
    assert correction.decision == "write", (
        f"cap 2 (correction): expected decision=write for revision, got "
        f"{correction.decision}; answer={correction.answer_text!r}"
    )
    follow_up = agent.process("What does Alice prefer?")
    assert follow_up.decision == "retrieve"
    assert follow_up.evidence
    # LATEST-wins: 'Java' (turn 4) outranks 'Rust' (turn 3) and 'Python' (turn 0).
    top_text = follow_up.evidence[0].text
    assert "Java" in top_text, (
        f"cap 2 (correction): latest 'Java' should win, got {top_text!r}; "
        f"all evidence={[(e.turn_id, e.text) for e in follow_up.evidence]}"
    )


def test_killer_milestone_capability_3_multi_hop_with_citations():
    agent = _build_killer_agent()
    # Build the contradicted state from caps 1+2 first to make multi-hop interesting
    agent.process("Alice now prefers Rust.")
    agent.process("Actually Alice switched to Java.")
    multi_hop = agent.process_with_multi_hop("What do Alice and Bob prefer?")
    assert multi_hop.evidence
    evidence_ids = {e.turn_id for e in multi_hop.evidence}
    # Bob's turn is 1 (original "Bob settled on Rust for systems work.")
    assert 1 in evidence_ids, (
        f"cap 3 (multi-hop): Bob's turn (1) missing from evidence; got {evidence_ids}; "
        f"texts={[(e.turn_id, e.text[:40]) for e in multi_hop.evidence]}"
    )
    # Alice's LATEST turn is turn 4 (the Java revision).
    assert 4 in evidence_ids, (
        f"cap 3 (multi-hop): Alice's latest revision turn (4) missing; got {evidence_ids}; "
        f"texts={[(e.turn_id, e.text[:40]) for e in multi_hop.evidence]}"
    )


def test_killer_milestone_capability_4_refuse_absent():
    agent = _build_killer_agent()
    absent = agent.process("What does Ghost9999 prefer?")
    assert absent.decision == "absent", (
        f"cap 4 (absent): expected decision=absent for unknown subject, got "
        f"{absent.decision}; evidence top cosine="
        f"{absent.evidence[0].cosine if absent.evidence else 'none'}"
    )


def test_killer_milestone_capability_5_tool_execution_writeback():
    agent = _build_killer_agent()
    # Write a temp file with a unique marker so we can verify the tool wrote
    # the result back into memory and it's retrievable by content.
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tf:
        tf.write("MAGICMARKER42 lives here.")
        tf_path = tf.name
    try:
        tool_packet = agent.run_tool("read_file", path=tf_path)
        assert tool_packet.decision == "tool"
        assert "MAGICMARKER42" in tool_packet.answer_text, (
            f"cap 5 (tool exec): tool result missing marker; got {tool_packet.answer_text!r}"
        )
        # The tool turn must be in memory and retrievable. Query by the unique
        # marker — cosine retrieval will surface the tool turn (no other turn
        # contains the marker).
        retrieve = agent.process("MAGICMARKER42")
        assert retrieve.evidence, "cap 5 (tool retrieve): no evidence returned"
        marker_in_evidence = any(
            "MAGICMARKER42" in e.text for e in retrieve.evidence
        )
        assert marker_in_evidence, (
            f"cap 5 (tool retrieve): tool-written turn not in evidence; "
            f"got {[(e.turn_id, e.text[:50]) for e in retrieve.evidence]}"
        )
    finally:
        os.unlink(tf_path)


def test_killer_milestone_full_sequence():
    """All 5 capabilities exercised on the same agent in sequence — the corpse's
    'real organism seed' criterion. Until this passes, Phase 10 EXIT GATE is open."""
    agent = _build_killer_agent()

    # Cap 1: teach
    p1 = agent.process("Alice now prefers Rust.")
    assert p1.decision == "write"

    # Cap 2: correct
    p2 = agent.process("Actually Alice switched to Java.")
    assert p2.decision == "write"
    after_correction = agent.process("What does Alice prefer?")
    assert after_correction.decision == "retrieve"
    assert "Java" in after_correction.evidence[0].text

    # Cap 3: multi-hop
    multi = agent.process_with_multi_hop("What do Alice and Bob prefer?")
    ev_ids = {e.turn_id for e in multi.evidence}
    assert 1 in ev_ids and 4 in ev_ids, (
        f"multi-hop missing one of {{Bob=1, Alice-latest=4}}; got {ev_ids}"
    )

    # Cap 4: absent
    absent = agent.process("What does Ghost9999 prefer?")
    assert absent.decision == "absent"

    # Cap 5: tool + writeback
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tf:
        tf.write("PHASE10EXITTOKEN found.")
        tf_path = tf.name
    try:
        tool = agent.run_tool("read_file", path=tf_path)
        assert tool.decision == "tool"
        retrieved = agent.process("PHASE10EXITTOKEN")
        assert any("PHASE10EXITTOKEN" in e.text for e in retrieved.evidence), (
            f"tool writeback not retrievable; evidence="
            f"{[(e.turn_id, e.text[:60]) for e in retrieved.evidence]}"
        )
    finally:
        os.unlink(tf_path)
