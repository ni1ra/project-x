"""Audit log CLI — cycle 12 #00P13c12-02.

Lightweight CLI for reviewing + rating walks in the audit log.

Usage:
  python3 -m project_x.audit.cli list                  # show recent walks (pending first)
  python3 -m project_x.audit.cli list --rated          # show rated walks
  python3 -m project_x.audit.cli show <walk_id>        # full detail on one walk
  python3 -m project_x.audit.cli rate <walk_id> approve [--note "great"]
  python3 -m project_x.audit.cli rate <walk_id> reject --note "off-theme"
  python3 -m project_x.audit.cli rate <walk_id> correct --note "should have emitted X"
  python3 -m project_x.audit.cli stats                  # counts: pending / approved / etc.

Per canonical doc Layer 6-7 audit-as-environment + lain 2026-05-11 "dataset
must be very well curated" directive. V1 is human-rating-driven; Discord-
reaction polling for automatic capture is cycle-12+.
"""

from __future__ import annotations

import argparse
import sys

from project_x.audit.log import AuditLog


def _cmd_list(log: AuditLog, rated_only: bool, limit: int) -> int:
    events = log.all_rated() if rated_only else log.pending_walks()
    if not events:
        kind = "rated" if rated_only else "pending"
        print(f"No {kind} walks in audit log.")
        return 0
    # Sort by ts_emitted descending
    events.sort(key=lambda e: -e.ts_emitted)
    for e in events[:limit]:
        rating_str = f"[{e.rating}]" if e.rating else "[pending]"
        print(f"{e.walk_id}  {rating_str:<11}  ({e.domain})  {e.prompt[:80]}")
    return 0


def _cmd_show(log: AuditLog, walk_id: str) -> int:
    for e in log.all_events():
        if e.walk_id == walk_id:
            print(f"walk_id: {e.walk_id}")
            print(f"prompt: {e.prompt}")
            print(f"domain: {e.domain}")
            print(f"strategy: {e.strategy}")
            print(f"rating: {e.rating}")
            print(f"rating_note: {e.rating_note}")
            print(f"ts_emitted: {e.ts_emitted}")
            print(f"ts_rated: {e.ts_rated}")
            print(f"fragments + similarities:")
            for i, (frag, sim, src) in enumerate(
                zip(e.fragments, e.similarities, e.sources), 1
            ):
                print(f"  [{i}] sim={sim:.4f}  source={src}")
                print(f"      \"{frag[:140]}{'...' if len(frag) > 140 else ''}\"")
            return 0
    print(f"walk_id {walk_id} not found in audit log.")
    return 1


def _cmd_rate(log: AuditLog, walk_id: str, rating: str, note: str | None) -> int:
    if not log.apply_rating(walk_id, rating, note):
        print(f"walk_id {walk_id} not found in audit log.")
        return 1
    print(f"Rated {walk_id} as '{rating}'.")
    return 0


def _cmd_stats(log: AuditLog) -> int:
    stats = log.stats()
    for k, v in stats.items():
        print(f"{k}: {v}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_list = sub.add_parser("list", help="show recent walks")
    p_list.add_argument("--rated", action="store_true", help="show rated walks instead of pending")
    p_list.add_argument("--limit", type=int, default=20, help="max walks to show (default 20)")
    p_show = sub.add_parser("show", help="show full detail on one walk")
    p_show.add_argument("walk_id")
    p_rate = sub.add_parser("rate", help="rate a walk")
    p_rate.add_argument("walk_id")
    p_rate.add_argument("rating", choices=["approve", "reject", "correct"])
    p_rate.add_argument("--note", default=None, help="optional free-text comment")
    sub.add_parser("stats", help="summary counts")
    args = parser.parse_args()
    log = AuditLog()
    if args.cmd == "list":
        return _cmd_list(log, rated_only=args.rated, limit=args.limit)
    if args.cmd == "show":
        return _cmd_show(log, args.walk_id)
    if args.cmd == "rate":
        return _cmd_rate(log, args.walk_id, args.rating, args.note)
    if args.cmd == "stats":
        return _cmd_stats(log)
    return 1


if __name__ == "__main__":
    sys.exit(main())
