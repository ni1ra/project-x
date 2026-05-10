"""Tests for SemanticHDCMemory + KeywordBaseline (Phase 9 Cycle 5, Layer 3)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from project_x.experiments.semantic_hdc_memory import (
    KeywordBaseline,
    SemanticHDCMemory,
    TurnRecord,
)


def _build_simple_memory(seed: int = 1337) -> SemanticHDCMemory:
    records = [
        TurnRecord(turn_id=0, text="Alice prefers Python."),
        TurnRecord(turn_id=1, text="Bob settled on Rust for the systems work."),
        TurnRecord(turn_id=2, text="Carol picked Postgres for the database."),
        TurnRecord(turn_id=3, text="The build is green."),
        TurnRecord(turn_id=4, text="meeting at three."),
    ]
    mem = SemanticHDCMemory(D=2048, alpha=0.5, negative_samples=2, seed=seed)
    mem.write_batch(records)
    return mem


def test_write_batch_then_retrieve_exact():
    mem = _build_simple_memory()
    top = mem.retrieve("What does Alice prefer?", k=3)
    top_ids = [tid for tid, _, _ in top]
    assert 0 in top_ids, f"Alice's preference turn (id=0) should appear in top-3, got {top_ids}"


def test_retrieve_returns_record_with_text():
    mem = _build_simple_memory()
    top = mem.retrieve("Bob and Rust", k=2)
    for turn_id, cos, record in top:
        assert isinstance(record, TurnRecord)
        assert record.turn_id == turn_id
        assert isinstance(record.text, str) and len(record.text) > 0


def test_retrieve_before_build_raises():
    mem = SemanticHDCMemory(D=512, alpha=0.5, negative_samples=0, seed=1337)
    try:
        mem.retrieve("anything", k=3)
    except RuntimeError:
        return
    raise AssertionError("retrieve before write_batch should raise")


def test_keyword_baseline_lexical_overlap():
    bl = KeywordBaseline()
    bl.fit([
        "Alice prefers Python.",
        "the build is green.",
        "Bob picked Postgres.",
    ])
    top = bl.retrieve_top_k("What does Alice prefer?", k=2)
    top_ids = [i for i, _ in top]
    # "What does Alice prefer?" tokens: {what, does, alice, prefer}
    # vs "Alice prefers Python.": {alice, prefers, python} → intersection={alice}, union={...} ~ Jaccard 1/6
    # vs "the build is green.": no overlap → 0
    # vs "Bob picked Postgres.": no overlap → 0
    assert top_ids[0] == 0, f"Alice turn should win Jaccard, got {top_ids}"


def test_retrieve_with_baselines_returns_all_views():
    mem = _build_simple_memory()
    out = mem.retrieve_with_baselines("What does Carol prefer?", k=2)
    assert set(out.keys()) == {"ensemble", "keyword", "floor_only", "hebbian_only"}
    for view_name, items in out.items():
        assert len(items) == 2, f"{view_name}: expected 2 items, got {len(items)}"
    # Carol's preference is turn 2; ensemble top-1 should land it on this small corpus.
    ensemble_top_ids = [tid for tid, _, _ in out["ensemble"]]
    assert ensemble_top_ids[0] == 2, (
        f"Carol's preference (turn 2) should be ensemble top-1, got {ensemble_top_ids}"
    )


def test_multi_hop_decomposition_returns_both_subjects_top_k():
    mem = _build_simple_memory()
    top = mem.retrieve_multi_hop("What do Alice and Bob prefer?", k=4)
    top_ids = [tid for tid, _, _ in top]
    # Reviewer's call-out: assert BOTH expected turn_ids surface, not just len>0.
    # Alice=turn 0, Bob=turn 1.
    assert 0 in top_ids, f"Alice's preference (turn 0) missing from top-4: {top_ids}"
    assert 1 in top_ids, f"Bob's preference (turn 1) missing from top-4: {top_ids}"
    for turn_id, cos, record in top:
        assert 0 <= turn_id < 5
        assert isinstance(record, TurnRecord)


def test_multi_hop_known_subject_uses_structural_path():
    """Phase 10 P3 reshape: single-subject queries that name a known fact-graph
    subject route through `retrieve_structural` (fact-graph candidate set +
    ensemble cosine + recency boost), NOT pure `retrieve`. The structural path
    is what gives contradiction queries LATEST-wins behavior; aligning multi-hop
    with structural keeps the question-answering contract uniform.

    Expectation: `retrieve_multi_hop` of a single-subject query equals
    `retrieve_structural` of the same query, and the known subject's turn is
    top-1 (Alice = turn 0)."""
    mem = _build_simple_memory()
    top_mh = mem.retrieve_multi_hop("What does Alice prefer?", k=3)
    top_structural = mem.retrieve_structural("What does Alice prefer?", k=3)
    mh_ids = [tid for tid, _, _ in top_mh]
    structural_ids = [tid for tid, _, _ in top_structural]
    assert mh_ids == structural_ids, (
        f"known-subject multi-hop should match structural retrieve; "
        f"mh={mh_ids} structural={structural_ids}"
    )
    assert mh_ids[0] == 0, f"Alice's preference (turn 0) should be top-1, got {mh_ids}"


def test_multi_hop_unknown_subject_falls_back_to_legacy_decomposition():
    """When a query mentions no known fact-graph subjects, retrieve_multi_hop
    falls back to the Phase 9 lexical decomposition path (split on and/or/both,
    union sub-retrievals). Verifies the legacy path is still alive for queries
    that escape the structural mechanism."""
    mem = _build_simple_memory()
    # No capitalized subject; "build" / "tests" are lowercase. Should not match
    # any fact_graph entry; falls through to legacy single-subject retrieve.
    top = mem.retrieve_multi_hop("is the build green?", k=3)
    assert len(top) > 0
    # Turn 3 ("The build is green.") should surface in top-k via lexical match.
    top_ids = [tid for tid, _, _ in top]
    assert 3 in top_ids, f"build-green query should surface turn 3, got {top_ids}"


def test_alpha_extremes():
    """alpha=0.0 → pure Hebbian; alpha=1.0 → pure floor."""
    records = [
        TurnRecord(turn_id=0, text="Alice prefers Python."),
        TurnRecord(turn_id=1, text="totally unrelated text about birds."),
    ]
    mem_pure_hebbian = SemanticHDCMemory(D=1024, alpha=0.0, negative_samples=0, seed=1337)
    mem_pure_hebbian.write_batch(records)
    mem_pure_floor = SemanticHDCMemory(D=1024, alpha=1.0, negative_samples=0, seed=1337)
    mem_pure_floor.write_batch(records)
    # Both should still rank Alice-turn higher than birds-turn for an Alice query
    h = mem_pure_hebbian.retrieve("Alice", k=2)
    f = mem_pure_floor.retrieve("Alice", k=2)
    assert h[0][0] == 0
    assert f[0][0] == 0


def test_hdc_binding_unbind_recovers_subject_signal():
    """Phase 10 P3 (#00c-2) — HDC role-filler binding integrity.

    With a 3-record corpus where each record names a distinct subject (Alice/Bob/
    Carol via fact_keys), the per-subject bound bank's unbind operation should
    recover a pseudo-vec that ranks the matching subject's turn ABOVE other
    subjects' turns when measured by bipolar cosine. The binding mechanism
    preserves which subject said what, even though all turns are encoded into
    the same global vector space."""
    from project_x.experiments.encoder import cosine_bipolar
    records = [
        TurnRecord(turn_id=0, text="Alice prefers Python.", fact_keys=["pref:Alice"]),
        TurnRecord(turn_id=1, text="Bob settled on Rust for systems work.", fact_keys=["pref:Bob"]),
        TurnRecord(turn_id=2, text="Carol picked Postgres for the database.", fact_keys=["pref:Carol"]),
    ]
    mem = SemanticHDCMemory(D=2048, alpha=0.5, negative_samples=2, seed=1337)
    mem.write_batch(records)
    # Atoms + bound bank were populated in write_batch.
    assert "Alice" in mem._subject_bound_bank
    assert "Bob" in mem._subject_bound_bank
    assert "Carol" in mem._subject_bound_bank

    alice_pseudo = mem.unbind_subject_pseudo_vec("Alice")
    assert alice_pseudo is not None
    cos_alice_to_alice_turn = cosine_bipolar(alice_pseudo, mem._floor_turn_vecs[0])
    cos_alice_to_bob_turn = cosine_bipolar(alice_pseudo, mem._floor_turn_vecs[1])
    cos_alice_to_carol_turn = cosine_bipolar(alice_pseudo, mem._floor_turn_vecs[2])
    assert cos_alice_to_alice_turn > cos_alice_to_bob_turn, (
        f"unbind(Alice) should be closest to Alice's turn vec; "
        f"alice={cos_alice_to_alice_turn:.4f} bob={cos_alice_to_bob_turn:.4f}"
    )
    assert cos_alice_to_alice_turn > cos_alice_to_carol_turn, (
        f"unbind(Alice) should be closest to Alice's turn vec; "
        f"alice={cos_alice_to_alice_turn:.4f} carol={cos_alice_to_carol_turn:.4f}"
    )


def test_hdc_binding_extends_on_incremental_write():
    """Incremental writes must extend the binding bank, not just the fact_graph.
    After write_one(Alice's revision), the subject's bound bank superposes the
    new bind so the latest turn contributes to the pseudo-vec."""
    from project_x.experiments.encoder import cosine_bipolar
    records = [
        TurnRecord(turn_id=0, text="Alice prefers Python.", fact_keys=["pref:Alice"]),
    ]
    mem = SemanticHDCMemory(D=2048, alpha=0.5, negative_samples=2, seed=1337)
    mem.write_batch(records)
    # Pre-revision: Alice's pseudo-vec recovers turn 0 strongly.
    pre_pseudo = mem.unbind_subject_pseudo_vec("Alice")
    pre_cos_to_turn0 = cosine_bipolar(pre_pseudo, mem._floor_turn_vecs[0])

    # Add a second turn for Alice via write_one.
    new_record = TurnRecord(turn_id=1, text="Alice now prefers Rust.", fact_keys=["pref:Alice"])
    mem.write_one(new_record)

    # Post-revision: Alice's pseudo-vec should now have signal for both turn vecs.
    post_pseudo = mem.unbind_subject_pseudo_vec("Alice")
    post_cos_to_turn0 = cosine_bipolar(post_pseudo, mem._floor_turn_vecs[0])
    post_cos_to_turn1 = cosine_bipolar(post_pseudo, mem._floor_turn_vecs[1])
    # New turn must register above near-zero correlation noise.
    assert post_cos_to_turn1 > 0.10, (
        f"unbind(Alice) post-incremental should correlate with the new Alice turn; "
        f"cos_to_turn1={post_cos_to_turn1:.4f}"
    )
    # Original turn signal can dilute (superposition halves both contributions
    # relative to single-bind), but should still be positive.
    assert post_cos_to_turn0 > 0.0, (
        f"unbind(Alice) post-incremental should still correlate with original turn; "
        f"cos_to_turn0={post_cos_to_turn0:.4f}"
    )


def test_non_contiguous_turn_ids():
    """Audit-A1 regression guard — caller-controlled turn_ids may be sparse
    (10, 20, 30, ...) rather than contiguous (0, 1, 2, ...). The encoder arrays
    are stored densely in insertion order; the API must map turn_id ↔ row so
    callers see turn_ids in retrieval results AND no path IndexErrors when
    a turn_id exceeds len(records).

    Pre-fix: `_floor_turn_vecs[r.turn_id]` indexed row 30 of a 3-row array →
    IndexError. Even where indexing happened to land in-range, the return
    tuples leaked ROW INDICES instead of turn_ids, silently breaking the
    `record.turn_id == turn_id` invariant that `test_retrieve_returns_record_with_text`
    documents.
    """
    records = [
        TurnRecord(turn_id=10, text="Alice prefers Python.", fact_keys=["pref:Alice"]),
        TurnRecord(turn_id=20, text="Bob settled on Rust for systems work.", fact_keys=["pref:Bob"]),
        TurnRecord(turn_id=30, text="Carol picked Postgres for the database.", fact_keys=["pref:Carol"]),
    ]
    mem = SemanticHDCMemory(D=2048, alpha=0.5, negative_samples=2, seed=1337)
    mem.write_batch(records)

    # turn_id → row map populated correctly from non-contiguous IDs.
    assert mem._turn_id_to_row == {10: 0, 20: 1, 30: 2}

    # retrieve() returns turn_ids (∈ {10, 20, 30}), not row indices.
    top = mem.retrieve("What does Alice prefer?", k=3)
    top_ids = [tid for tid, _, _ in top]
    assert all(tid in {10, 20, 30} for tid in top_ids), (
        f"retrieve must return caller-facing turn_ids; got {top_ids}"
    )
    assert 10 in top_ids, f"Alice's turn (id=10) should appear in top-3, got {top_ids}"
    # tuple turn_id field must equal record.turn_id (audit-A1 invariant).
    for turn_id, _, record in top:
        assert record.turn_id == turn_id

    # retrieve_structural() — exercises the strict-dominance boost path which
    # writes into a row-indexed `out` array via fact_graph turn_ids.
    structural = mem.retrieve_structural("What does Bob prefer?", k=3)
    structural_ids = [tid for tid, _, _ in structural]
    assert 20 in structural_ids, f"Bob's turn (id=20) should appear; got {structural_ids}"
    assert structural_ids[0] == 20, (
        f"strict-dominance boost should put Bob's turn at top-1; got {structural_ids}"
    )

    # retrieve_structural_full_history() — chronological union path indexes
    # cosines + records by turn_id (must map to row pre-fix → IndexError).
    full = mem.retrieve_structural_full_history("List Carol's preferences", k=None)
    full_ids = [tid for tid, _, _ in full]
    assert 30 in full_ids, f"Carol's turn (id=30) should appear; got {full_ids}"
    for turn_id, _, record in full:
        assert record.turn_id == turn_id

    # retrieve_with_baselines() — every view must surface turn_ids.
    baselines = mem.retrieve_with_baselines("What does Alice prefer?", k=2)
    for view in ("ensemble", "keyword", "floor_only", "hebbian_only"):
        ids = [tid for tid, _, _ in baselines[view]]
        assert all(tid in {10, 20, 30} for tid in ids), (
            f"{view}: turn_ids must be caller-facing; got {ids}"
        )

    # write_one() with another non-contiguous extension — turn_id=42 jumps
    # past the existing high-water mark (30); pre-fix this would IndexError
    # on the binding-bank refresh `_floor_turn_vecs[record.turn_id]`.
    new_record = TurnRecord(turn_id=42, text="Dave chose Go for the CLI.", fact_keys=["pref:Dave"])
    mem.write_one(new_record)
    assert mem._turn_id_to_row[42] == 3
    post = mem.retrieve("What does Dave prefer?", k=2)
    post_ids = [tid for tid, _, _ in post]
    assert 42 in post_ids, f"Dave's turn (id=42) should surface post-write_one; got {post_ids}"


def test_replay_consolidate_idempotent():
    """Audit-A3 regression guard — replay_consolidate() re-fits Hebbian on the
    current corpus. Pre-fix it called `_hebbian.fit(texts)` without reset, so
    every replay tick accumulated _freq + _total_tokens on top of the prior
    fit's state. After K replay ticks, _total_tokens ≈ K × actual_corpus_tokens
    and Mikolov subsample probabilities (computed from f(w) = freq/_total_tokens)
    drifted toward zero.

    Post-fix: replay_consolidate calls fit(reset=True). _total_tokens after
    any number of replays equals the actual corpus token count, NOT a multiple
    of it.
    """
    from project_x.experiments.random_index_hebbian import tokenize
    records = [
        TurnRecord(turn_id=0, text="Alice prefers Python.", fact_keys=["pref:Alice"]),
        TurnRecord(turn_id=1, text="Bob settled on Rust.", fact_keys=["pref:Bob"]),
    ]
    mem = SemanticHDCMemory(D=1024, alpha=0.5, negative_samples=0, seed=1337)
    mem.write_batch(records)
    expected_tokens_after_batch = sum(len(tokenize(r.text)) for r in records)
    assert mem._hebbian._total_tokens == expected_tokens_after_batch

    # write_one extends the corpus; expected token count grows accordingly.
    new_record = TurnRecord(turn_id=2, text="Carol picked Postgres.", fact_keys=["pref:Carol"])
    mem.write_one(new_record)
    expected_after_write_one = expected_tokens_after_batch + len(tokenize(new_record.text))

    # Three replay ticks. Pre-fix: _total_tokens would be ~3× expected.
    for _ in range(3):
        mem.replay_consolidate()
    assert mem._hebbian._total_tokens == expected_after_write_one, (
        f"replay_consolidate must be idempotent on _total_tokens; "
        f"expected {expected_after_write_one}, got {mem._hebbian._total_tokens}"
    )
    # Vocab also stays clean (no duplicate inflation).
    expected_vocab = set()
    for r in mem._records:
        expected_vocab.update(tokenize(r.text))
    assert set(mem._hebbian._vocab.keys()) == expected_vocab


def test_save_provenance_jsonl():
    import json
    mem = _build_simple_memory()
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "provenance.jsonl"
        mem.save_provenance(path)
        assert path.exists()
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 5
        for line in lines:
            obj = json.loads(line)
            assert "turn_id" in obj and "text" in obj
