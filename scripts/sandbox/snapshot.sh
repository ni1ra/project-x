#!/usr/bin/env bash
# scripts/sandbox/snapshot.sh — capture sandbox/ state to a named snapshot dir.
# MINIMUM viable per Phase 13 cycle 1 corpse — later cycles wire restore + diff.
# Usage: scripts/sandbox/snapshot.sh <snapshot_name>
# Snapshots land at sandbox_snapshots/<name>/ (gitignored; local-only).

set -euo pipefail
SNAPSHOT_NAME="${1:-}"
if [ -z "$SNAPSHOT_NAME" ]; then
  echo "usage: $0 <snapshot_name>" >&2
  exit 1
fi
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SANDBOX_ROOT="$REPO_ROOT/sandbox"
SNAPSHOT_DIR="$REPO_ROOT/sandbox_snapshots/$SNAPSHOT_NAME"
if [ ! -d "$SANDBOX_ROOT" ]; then
  echo "sandbox/ does not exist at $SANDBOX_ROOT" >&2
  exit 1
fi
mkdir -p "$SNAPSHOT_DIR"
cp -r "$SANDBOX_ROOT/." "$SNAPSHOT_DIR/" 2>/dev/null || true
echo "snapshot captured: $SNAPSHOT_DIR"
