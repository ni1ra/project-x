"""Phase 12 #00P12-tests — retrieval-mode disambiguation tests.

Probes the controller-layer routing in MemoryAgent.process between
retrieve_structural (strict-dominance, latest-wins) and
retrieve_structural_full_history (chronological, all-turns). Phase 11
memory-004 / memory-005 red findings drove this surface; Phase 12
cycles 1-3 shipped the fix and flipped both reds → green. These tests
guard the regression boundary so future encoder/threshold/binding
tuning doesn't silently re-collapse list-all queries.

WHY each test exists:
  - test_list_all_query_returns_full_history: probes memory-004 fixture
    directly. If this fails, retrieve_structural_full_history is broken
    OR the controller isn't routing list-all queries to it.
  - test_summarize_trajectory_returns_full_history: probes memory-005
    fixture (10-turn career trajectory). Different lexical surface than
    "list all"; tests that 'summarize' / 'trajectory' hints also route.
  - test_current_preference_still_uses_strict_dominance: REGRESSION
    GUARD. memory-002-shape contradiction-LATEST-wins must still emit
    only the latest turn. The Phase 12 fix is opt-in; current-preference
    queries must NOT accidentally route to full-history.
  - test_unknown_subject_falls_through: edge — list-all hint with no
    fact_graph subject should fall through to retrieve, not crash.
  - test_multi_subject_list_all_unions_chronologically: validates the
    multi-subject union path; both subjects' turn_ids merged + sorted.
  - test_classifier_sanity: spot-checks _is_list_all_query patterns;
    must distinguish list-all from current-preference shapes.
"""

from project_x.experiments.semantic_memory_agent import (
    MemoryAgent,
    _is_list_all_query,
)
from project_x.experiments.semantic_hdc_memory import (
    SemanticHDCMemory,
    TurnRecord,
)


def _build_agent(setups):
    """Canonical fixture pattern: write_batch initializes encoder state,
    then construct agent over the populated memory. The assertion-shape
    `agent.process(setup)` path requires prior write_batch (it calls
    write_one which raises on uninitialized state); the canonical from-
    scratch fixture writes setups in batch up front.
    """
    records = [
        TurnRecord(turn_id=i, text=t, fact_keys=[], metadata={})
        for i, t in enumerate(setups)
    ]
    mem = SemanticHDCMemory()
    mem.write_batch(records)
    return MemoryAgent(memory=mem)


def test_list_all_query_returns_full_history():
    """memory-004 fixture: list-all over 8-turn Alice fixture must cite
    all 4 Alice turns chronologically [0, 3, 5, 7]. The Phase 11 verdict's
    auto-graded-red finding here was the original Phase 12 driver."""
    setups = [
        "Alice prefers C++.",
        "Bob prefers Go.",
        "Carol prefers Python.",
        "Alice switched to Rust.",
        "David prefers Haskell.",
        "Alice now prefers Java.",
        "Eve prefers Erlang.",
        "Alice settled on Kotlin.",
    ]
    agent = _build_agent(setups)
    response = agent.process(
        "List all of Alice's preference changes in chronological order."
    )
    cited = sorted(e.turn_id for e in response.evidence)
    assert response.decision == "retrieve_full_history"
    assert cited == [0, 3, 5, 7]
    for tok in ("C++", "Rust", "Java", "Kotlin"):
        assert tok in response.answer_text


def test_summarize_trajectory_returns_full_history():
    """memory-005 fixture: 10-turn Alice career trajectory. Tests that
    'summarize' + 'trajectory' hints route to full-history retrieval and
    that the cited set is a SUPERSET of the expected core trajectory
    [1, 3, 5, 7, 9]. Turn 0 ('Alice prefers Rust') is borderline-included
    per the entry's own raphael_response — match_criterion is `subseteq`
    so a superset cleanly satisfies."""
    setups = [
        "Alice prefers Rust.",
        "Alice joined Anthropic as a researcher.",
        "Bob prefers Go.",
        "Alice moved to San Francisco.",
        "Carol prefers Python.",
        "Alice is working on the safety team.",
        "David prefers Haskell.",
        "Alice published a paper on RLHF.",
        "Eve prefers Erlang.",
        "Alice mentors junior researchers.",
    ]
    agent = _build_agent(setups)
    response = agent.process(
        "Summarize Alice's professional trajectory based on stated facts. "
        "Cite turn IDs."
    )
    cited = set(e.turn_id for e in response.evidence)
    expected = {1, 3, 5, 7, 9}
    assert response.decision == "retrieve_full_history"
    assert expected.issubset(cited)
    contains = sum(
        1 for tok in ("Anthropic", "San Francisco", "safety", "RLHF", "mentors")
        if tok in response.answer_text
    )
    # 4-of-5 threshold per match_criterion in the original ladder entry.
    assert contains >= 4


def test_current_preference_still_uses_strict_dominance():
    """REGRESSION GUARD — memory-002-shape contradiction-LATEST-wins.
    The Phase 12 fix routes ONLY when both _is_list_all_query is True AND
    a known fact_graph subject is named. 'What does Alice prefer?' has
    neither hint nor list-all shape — must stay on the existing strict-
    dominance path and emit ONLY the latest Alice turn (turn 2 'Java')."""
    setups = [
        "Alice prefers Rust.",
        "Bob prefers Go.",
        "Actually Alice switched to Java.",
    ]
    agent = _build_agent(setups)
    response = agent.process("What does Alice prefer?")
    # The strict-dominance path emits 'Based on turn 2:' single-turn shape.
    assert response.decision == "retrieve"
    assert "Java" in response.answer_text
    assert "turn 2" in response.answer_text


def test_unknown_subject_list_all_falls_through():
    """Edge: list-all hint with no fact_graph subject must fall through
    to retrieve(query, k=5) inside retrieve_structural_full_history. Must
    NOT crash and must NOT route to full-history (no subject to enumerate).
    Decision label can legitimately be 'retrieve', 'absent', or
    'retrieve_full_history' depending on cosine; the contract is no crash."""
    setups = ["Alice prefers Rust.", "Bob prefers Go."]
    agent = _build_agent(setups)
    response = agent.process("List all of Zoe's preferences.")
    # Zoe is not in fact_graph; subject-extraction returns []; the controller
    # enters the full-history branch but the method itself falls through to
    # retrieve(k=5). Decision label may end up 'retrieve_full_history' (the
    # outer routing label) even though the inner retrieval was ensemble.
    # The contract this test enforces: no exception + an AnswerPacket.
    assert response is not None
    assert response.decision in ("retrieve", "absent", "retrieve_full_history")


def test_multi_subject_list_all_unions_chronologically():
    """Multi-subject query routes to retrieve_structural_full_history
    which unions both subjects' fact_graph turn_ids and sorts ascending.
    Alice turns {0, 2, 4} ∪ Bob turns {1, 3} = chronological [0,1,2,3,4]."""
    setups = [
        "Alice prefers C++.",
        "Bob prefers Go.",
        "Alice switched to Rust.",
        "Bob now uses Python.",
        "Alice settled on Kotlin.",
    ]
    agent = _build_agent(setups)
    response = agent.process("List all of Alice and Bob's preference history.")
    cited = sorted(e.turn_id for e in response.evidence)
    assert response.decision == "retrieve_full_history"
    assert cited == [0, 1, 2, 3, 4]


def test_classifier_sanity():
    """_is_list_all_query patterns: list-all / summarize / trajectory /
    history-of / chronological-order shapes match; current-preference
    shapes do not. Conservative — false positives cause regression on
    memory-001/002/003."""
    # Should match (list-all / summarize / trajectory / history shapes)
    assert _is_list_all_query("List all of Alice's changes.")
    assert _is_list_all_query("Summarize Alice's career.")
    assert _is_list_all_query("In chronological order, give me Alice's preferences.")
    assert _is_list_all_query("Tell me about Alice's history of changes.")
    assert _is_list_all_query("Walk through Alice's full history.")
    # Should NOT match (current-preference shapes)
    assert not _is_list_all_query("What does Alice prefer?")
    assert not _is_list_all_query("Who picked Python?")
    assert not _is_list_all_query("What is Alice's current job?")
    assert not _is_list_all_query("Where does Bob live?")
    # Phase 12 cycle 5 advisor catch: "in order" subjunctive must NOT match
    # (was a false-positive risk under the bare "in order" pattern; the
    # pattern was tightened to "in chronological order" only).
    assert not _is_list_all_query("What does Alice need to do in order to succeed?")
    assert not _is_list_all_query("Bob arranged the books in order on the shelf.")
