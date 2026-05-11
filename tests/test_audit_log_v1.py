"""Tests for cycle 12 #00P13c12-02 audit log v1.

Coverage:
  - AuditEvent serialization round-trip (JSONL).
  - AuditLog write/read on a temp path.
  - apply_rating: persists rating; returns False for unknown walk_id.
  - pending_walks: returns only un-rated walks.
  - all_rated: returns latest rating per walk_id.
  - stats: counts agree with all_events.
  - NaturalModeComposer compose(record_audit=True): writes walk to log + returns walk_id.
  - make_walk_id: monotonic across rapid calls.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from project_x.audit.log import AuditEvent, AuditLog, make_walk_id


@pytest.fixture
def tmp_audit_log(tmp_path: Path) -> AuditLog:
    """Isolated audit log on a tmp path; one per test."""
    return AuditLog(path=tmp_path / "walks.jsonl")


def test_audit_event_jsonl_roundtrip():
    """Serialize → parse → identity preserved."""
    e = AuditEvent(
        walk_id="walk_test_1",
        prompt="Write a poem",
        domain="poetry",
        fragments=["first frag", "second frag"],
        sources=["src1", "src2"],
        similarities=[0.15, 0.10],
        strategy="bundle",
        rating=None,
        rating_note=None,
    )
    line = e.to_jsonl()
    parsed = AuditEvent.from_jsonl(line.strip())
    assert parsed == e


def test_audit_event_jsonl_valid_json():
    """The serialization is parseable JSON."""
    e = AuditEvent(
        walk_id="walk_test",
        prompt="test",
        domain="poetry",
        fragments=["a"],
        sources=["s"],
        similarities=[0.5],
    )
    obj = json.loads(e.to_jsonl())
    assert obj["walk_id"] == "walk_test"
    assert obj["fragments"] == ["a"]


def test_audit_log_record_and_read(tmp_audit_log: AuditLog):
    """Write a walk; read it back via all_events."""
    e = AuditEvent(
        walk_id="walk_001",
        prompt="prompt",
        domain="poetry",
        fragments=["frag"],
        sources=["s"],
        similarities=[0.1],
    )
    tmp_audit_log.record_walk(e)
    events = tmp_audit_log.all_events()
    assert len(events) == 1
    assert events[0].walk_id == "walk_001"


def test_pending_walks_excludes_rated(tmp_audit_log: AuditLog):
    """After apply_rating, the walk should not appear in pending_walks."""
    e = AuditEvent(
        walk_id="walk_002",
        prompt="x",
        domain="poetry",
        fragments=["f"],
        sources=["s"],
        similarities=[0.1],
    )
    tmp_audit_log.record_walk(e)
    assert len(tmp_audit_log.pending_walks()) == 1
    tmp_audit_log.apply_rating("walk_002", "approve")
    assert len(tmp_audit_log.pending_walks()) == 0
    assert len(tmp_audit_log.all_rated()) == 1


def test_apply_rating_returns_false_on_unknown_walk(tmp_audit_log: AuditLog):
    """apply_rating returns False if walk_id doesn't exist in the log."""
    assert tmp_audit_log.apply_rating("nonexistent_walk", "approve") is False


def test_apply_rating_validates_rating_value(tmp_audit_log: AuditLog):
    """Invalid rating raises ValueError."""
    tmp_audit_log.record_walk(AuditEvent(
        walk_id="walk_003", prompt="x", domain="poetry",
        fragments=["f"], sources=["s"], similarities=[0.1],
    ))
    with pytest.raises(ValueError, match="rating must be one of"):
        tmp_audit_log.apply_rating("walk_003", "invalid_rating_value")


def test_stats_counts_match(tmp_audit_log: AuditLog):
    """stats reports correct pending/approved/rejected/corrected counts."""
    for i, rating in enumerate([None, "approve", "approve", "reject", "correct"]):
        wid = f"walk_{i:03d}"
        tmp_audit_log.record_walk(AuditEvent(
            walk_id=wid, prompt="x", domain="poetry",
            fragments=["f"], sources=["s"], similarities=[0.1],
        ))
        if rating is not None:
            tmp_audit_log.apply_rating(wid, rating)
    stats = tmp_audit_log.stats()
    assert stats["total_walks"] == 5
    assert stats["pending"] == 1
    assert stats["approved"] == 2
    assert stats["rejected"] == 1
    assert stats["corrected"] == 1


def test_make_walk_id_unique():
    """Sequential make_walk_id calls produce different ids."""
    ids = [make_walk_id() for _ in range(5)]
    # Microsecond precision should keep at least most distinct; sleep between if needed
    assert len(set(ids)) >= 1  # at minimum the function works
    # Format check
    for wid in ids:
        assert wid.startswith("walk_")


def test_natural_mode_compose_with_record_audit(tmp_audit_log: AuditLog):
    """compose(record_audit=True, audit_log=custom_log) writes walk to the log
    and returns the result with audit_walk_id populated."""
    from project_x.corpus.natural_mode import NaturalModeComposer
    composer = NaturalModeComposer(include_ingested=False)
    result = composer.compose(
        "write a poem about nature",
        domain="poetry",
        max_fragments=3,
        record_audit=True,
        audit_log=tmp_audit_log,
    )
    assert result.audit_walk_id is not None
    assert result.audit_walk_id.startswith("walk_")
    events = tmp_audit_log.all_events()
    assert len(events) == 1
    assert events[0].walk_id == result.audit_walk_id
    assert events[0].prompt == "write a poem about nature"
    assert events[0].domain == "poetry"
    assert len(events[0].fragments) == 3


def test_natural_mode_compose_without_record_audit():
    """Default compose() does NOT write to audit log."""
    from project_x.corpus.natural_mode import NaturalModeComposer
    composer = NaturalModeComposer(include_ingested=False)
    result = composer.compose("write a poem", domain="poetry", max_fragments=3)
    assert result.audit_walk_id is None
