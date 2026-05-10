#!/usr/bin/env bash
# scripts/sandbox/reset.sh — wipe sandbox/ to empty state.
# MINIMUM viable per Phase 13 cycle 1 corpse — later cycles replace with snapshot-aware reset.
# Cycle 2+ may add: --to-snapshot=<name> to restore a captured state for benchmark replay.

set -euo pipefail
SANDBOX_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/sandbox"
if [ ! -d "$SANDBOX_ROOT" ]; then
  echo "sandbox/ does not exist at $SANDBOX_ROOT — nothing to reset"
  exit 0
fi
find "$SANDBOX_ROOT" -mindepth 1 ! -name '.gitkeep' -exec rm -rf {} + 2>/dev/null || true
echo "sandbox/ reset to empty (preserved .gitkeep)"
