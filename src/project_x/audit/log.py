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

# Cycle-14 #08b — Hebbian-bank persistence path for the audit-rating consumer.
# The bank lives in `data/hebbian_bank/main.pkl` (cycle-14 v0 — single bank).
# Cycle-15+ may partition per-domain.
_DEFAULT_HEBBIAN_BANK_FILE = (
    Path(__file__).resolve().parents[3] / "data" / "hebbian_bank" / "main.pkl"
)

# Cycle-14 #08b — translate the string preference signal ("approve"/"reject"/
# "correct") into a numeric rating on the [1..5] scale the HebbianBank expects.
# The bank's RATING_MIDPOINT is 3.0; "approve" sits well above (=5), "reject"
# well below (=1), "correct" right at the midpoint (=3 — neither reinforce
# nor decay; correct-marker is feedback for cycle-15+ generation work, not
# substrate co-occurrence shaping).
_RATING_STR_TO_NUMERIC: dict[str, float] = {
    "approve": 5.0,
    "correct": 3.0,
    "reject": 1.0,
}


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

    def __init__(
        self,
        path: Path | str = _DEFAULT_AUDIT_FILE,
        hebbian_bank_path: Path | str | None = None,
    ) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()
        # Cycle-14 #08b — the substrate's HebbianBank persistence path. If
        # None, uses the default `data/hebbian_bank/main.pkl`. Tests pass
        # a tmp_path here to avoid polluting the real bank file with
        # synthetic prompts/fragments.
        self.hebbian_bank_path = (
            Path(hebbian_bank_path)
            if hebbian_bank_path is not None
            else _DEFAULT_HEBBIAN_BANK_FILE
        )

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
        trace_bank: object | None = None,
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

        # Cycle-14 #08b — close the reward → substrate loop. Feed the rating
        # into the substrate-wide HebbianBank so retrieval over the rated
        # (prompt, fragment) pairs shifts in the rated direction. Cold-start
        # safe: empty bank returns lookup=0.0, retrieval blend collapses to
        # identity (cycle-13 baseline preserved).
        self._propagate_rating_to_hebbian_bank(latest, rating)

        # v1 — wire TemporalTraceBank into audit loop so natural-mode strategy
        # ratings also shape action-selection policy. The walk's strategy
        # (bind/bundle/greedy) is treated as a discrete action.
        if trace_bank is not None and latest.strategy is not None:
            try:
                numeric = _RATING_STR_TO_NUMERIC.get(rating)
                if numeric is not None:
                    trace_bank.apply_rating_to_action(latest.strategy, numeric)
            except Exception:
                # Defensive: trace-bank update failure must not break audit
                pass
        return True

    def _propagate_rating_to_hebbian_bank(
        self,
        event: AuditEvent,
        rating_str: str,
    ) -> None:
        """Apply the rating's Hebbian update to the substrate-wide bank.

        Cycle-14 #08b: this is the I/O wire between the audit channel and
        the substrate's first write path from rated experience. Persists
        the bank to `data/hebbian_bank/main.pkl` on every update — fine at
        cycle-14 rating volume (sub-100 ratings expected); cycle-15+ may
        memoize if rating frequency grows.

        Failure modes:
          - HebbianBank import error: silently skip (test-env fallback).
          - rating not in the numeric map: silently skip (defensive guard
            already lives in `apply_rating` validating the string vocab).
          - bank load/save IO error: log + skip; we don't want to fail
            audit-rating writes because of a substrate-update error.
        """
        try:
            from project_x.hdc_infra import HebbianBank
        except ImportError:
            return  # test-environment fallback; bank wire optional
        rating_value = _RATING_STR_TO_NUMERIC.get(rating_str)
        if rating_value is None:
            return  # unknown rating string; apply_rating's validation already caught
        try:
            bank = HebbianBank.load(self.hebbian_bank_path)
            bank.update(event.prompt, event.fragments, rating_value)
            bank.save(self.hebbian_bank_path)
        except (OSError, IOError):
            # Disk-write failure shouldn't break audit-rating recording.
            # Cycle-14 v0 ignores; cycle-15+ may surface via logging.
            return

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
