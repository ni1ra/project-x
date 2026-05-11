"""Audit log v1 — cycle 12 #00P13c12-02.

JSONL-based audit log for natural-mode walks. Per canonical synthesis doc
Layer 6-7 audit-as-environment + lain 2026-05-11 "dataset must be very well
curated and high quality, low noise" directive.

The audit loop is the canonical doc Layer 7 consolidation pass's required
input signal. Without real lain ratings on emitted walks, the consolidation
pass is tautological (any "improvement" measure is computed from the same
substrate that produces the walks). V1 ships the LOG-WRITING + CLI-RATING
side; Discord-reaction polling for automatic rating capture is cycle-12+.

Schema (`AuditEvent`):
  walk_id: str          — unique identifier (timestamp-derived)
  prompt: str           — user prompt that triggered the walk
  domain: str           — natural-mode domain (poetry / philosophy / etc.)
  fragments: list[str]  — emitted fragment texts
  sources: list[str]    — provenance tags per fragment
  similarities: list[float]  — cosine similarities per emitted fragment
  strategy: str | None  — K-rollout strategy that won (bind / bundle / greedy / None)
  rating: str | None    — "approve" / "reject" / "correct" / None (pending)
  rating_note: str | None  — free-text correction or comment
  ts_emitted: float     — UNIX timestamp when walk was emitted
  ts_rated: float | None  — UNIX timestamp when rated

JSONL on-disk at `data/audit_log/walks.jsonl`. Append-only; one event per line.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path


_DEFAULT_AUDIT_DIR = Path(__file__).resolve().parents[3] / "data" / "audit_log"
_DEFAULT_AUDIT_FILE = _DEFAULT_AUDIT_DIR / "walks.jsonl"


@dataclass
class AuditEvent:
    """One natural-mode walk + its audit state."""

    walk_id: str
    prompt: str
    domain: str
    fragments: list[str]
    sources: list[str]
    similarities: list[float]
    strategy: str | None = None
    rating: str | None = None  # "approve" / "reject" / "correct" / None pending
    rating_note: str | None = None
    ts_emitted: float = field(default_factory=time.time)
    ts_rated: float | None = None

    def to_jsonl(self) -> str:
        """Serialize to a single-line JSON string (newline-terminated)."""
        return json.dumps(asdict(self), ensure_ascii=False) + "\n"

    @classmethod
    def from_jsonl(cls, line: str) -> AuditEvent:
        """Parse one JSONL line back into an AuditEvent."""
        return cls(**json.loads(line))


class AuditLog:
    """Append-only JSONL audit log."""

    def __init__(self, path: Path | str = _DEFAULT_AUDIT_FILE) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def record_walk(self, event: AuditEvent) -> None:
        """Append a walk event (pending rating). Writes one JSONL line."""
        with self.path.open("a", encoding="utf-8") as f:
            f.write(event.to_jsonl())

    def all_events(self) -> list[AuditEvent]:
        """Read all events from disk. Honest about cost — file scan per call."""
        events: list[AuditEvent] = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                events.append(AuditEvent.from_jsonl(line))
        return events

    def pending_walks(self) -> list[AuditEvent]:
        """Return walks without a rating yet (LATEST rating per walk_id wins)."""
        events = self.all_events()
        latest: dict[str, AuditEvent] = {}
        for e in events:
            existing = latest.get(e.walk_id)
            if existing is None:
                latest[e.walk_id] = e
            else:
                # Prefer the most recent rating update
                if (e.ts_rated or 0) > (existing.ts_rated or 0):
                    latest[e.walk_id] = e
        return [e for e in latest.values() if e.rating is None]

    def all_rated(self) -> list[AuditEvent]:
        """Return all RATED events (latest rating per walk_id)."""
        events = self.all_events()
        latest: dict[str, AuditEvent] = {}
        for e in events:
            existing = latest.get(e.walk_id)
            if existing is None:
                latest[e.walk_id] = e
            else:
                if (e.ts_rated or 0) > (existing.ts_rated or 0):
                    latest[e.walk_id] = e
        return [e for e in latest.values() if e.rating is not None]

    def apply_rating(
        self,
        walk_id: str,
        rating: str,
        note: str | None = None,
    ) -> bool:
        """Apply a rating to a previously-recorded walk.

        Appends a NEW event with the same walk_id + the rating filled in;
        `pending_walks` / `all_rated` use latest-wins to surface the rating.

        Args:
            walk_id: the walk_id from the originally-recorded walk.
            rating: "approve" / "reject" / "correct".
            note: optional free-text comment (e.g., the corrected output).

        Returns:
            True if a matching walk was found and rated; False if walk_id not in log.
        """
        if rating not in ("approve", "reject", "correct"):
            raise ValueError(
                f"rating must be one of: approve / reject / correct (got {rating!r})"
            )
        events = self.all_events()
        latest: AuditEvent | None = None
        for e in events:
            if e.walk_id == walk_id:
                if latest is None or e.ts_emitted >= latest.ts_emitted:
                    latest = e
        if latest is None:
            return False
        # Append a rating-applied copy
        rated = AuditEvent(
            walk_id=latest.walk_id,
            prompt=latest.prompt,
            domain=latest.domain,
            fragments=latest.fragments,
            sources=latest.sources,
            similarities=latest.similarities,
            strategy=latest.strategy,
            rating=rating,
            rating_note=note,
            ts_emitted=latest.ts_emitted,
            ts_rated=time.time(),
        )
        self.record_walk(rated)
        return True

    def stats(self) -> dict[str, int]:
        """Summary counts: total / pending / approved / rejected / corrected."""
        events = self.all_events()
        all_walks = {e.walk_id for e in events}
        rated = self.all_rated()
        return {
            "total_walks": len(all_walks),
            "pending": len(all_walks) - len(rated),
            "approved": sum(1 for e in rated if e.rating == "approve"),
            "rejected": sum(1 for e in rated if e.rating == "reject"),
            "corrected": sum(1 for e in rated if e.rating == "correct"),
        }


def make_walk_id() -> str:
    """Generate a unique walk_id from current UNIX time (microsecond precision)."""
    return f"walk_{int(time.time() * 1_000_000)}"
