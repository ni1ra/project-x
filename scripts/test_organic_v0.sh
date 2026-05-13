#!/usr/bin/env bash
# Runs both the substrate self-test (cold-brain→learn→emit) AND the persistence round-trip
# (train→save→fresh-process load→generate→hash+output match). Either failure is `set -e` fatal.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
make -s build/organic_v0

# Phase 1: substrate guard — a cold brain emits nothing; after one rewarded event it emits the target.
build/organic_v0 --phase self-test

# Phase 2: persistence round-trip — proves a fresh process can load prior state and reproduce a
# generation bit-exactly (state_hash match + raw_output match). MANIFESTO §"Persistence Is Pass-0"
# requirement: the organism does not exist as an organism until it survives a restart.
STATE_TMP="$(mktemp -u /tmp/organic_v0_state.XXXXXX.pxstate)"
LOG_TMP="$(mktemp -u /tmp/organic_v0_events.XXXXXX.jsonl)"
VERDICT_TMP="$(mktemp -u /tmp/organic_v0_persist.XXXXXX.json)"
trap 'rm -f "$STATE_TMP" "$LOG_TMP" "$VERDICT_TMP" "$VERDICT_TMP.child.json"' EXIT
build/organic_v0 --phase persistence-self-test \
  --save-state "$STATE_TMP" \
  --event-log "$LOG_TMP" \
  --verify-event evt_mem_test_001 \
  --out "$VERDICT_TMP"
