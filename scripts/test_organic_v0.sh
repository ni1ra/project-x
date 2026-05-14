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
SLEEP_WAKE_LOG_TMP="$(mktemp -u /tmp/organic_v0_sleep_wake_events.XXXXXX.jsonl)"
SLEEP_WAKE_VERDICT_TMP="$(mktemp -u /tmp/organic_v0_sleep_wake.XXXXXX.json)"
trap 'rm -f "$STATE_TMP" "$LOG_TMP" "$VERDICT_TMP" "$VERDICT_TMP.child.json" "$SLEEP_WAKE_LOG_TMP" "$SLEEP_WAKE_VERDICT_TMP"' EXIT
build/organic_v0 --phase persistence-self-test \
  --save-state "$STATE_TMP" \
  --event-log "$LOG_TMP" \
  --verify-event evt_mem_test_001 \
  --out "$VERDICT_TMP"

# Phase 3: Cycle-8 short full-mode sleep/wake rail. This uses the same organism-step codepath
# as daemon-lite, but with tiny tick counts and a hard 180s wall-clock cap.
SLEEP_WAKE_CMD=(
  build/organic_v0 --phase sleep-wake
  --mode test
  --run-id cycle8-test-script
  --sleep-ticks 5
  --checkpoint-interval-ticks 5
  --internal-timeout-seconds 180
  --event-log "$SLEEP_WAKE_LOG_TMP"
  --out "$SLEEP_WAKE_VERDICT_TMP"
)
if command -v timeout >/dev/null 2>&1; then
  printf '%s\n' \
    '{"cmd":"wake","event_id":"wake_cycle8_0001","session_id":"cycle8_manual","input_text":"navi carries basalt prism","observations":[],"correction_output":"navi carries basalt prism","reward":{"task_success":1.0,"source_fidelity":1.0}}' \
    '{"cmd":"sleep","ticks":5}' \
    '{"cmd":"checkpoint"}' \
    '{"cmd":"shutdown"}' | timeout 180s "${SLEEP_WAKE_CMD[@]}"
else
  printf '%s\n' \
    '{"cmd":"wake","event_id":"wake_cycle8_0001","session_id":"cycle8_manual","input_text":"navi carries basalt prism","observations":[],"correction_output":"navi carries basalt prism","reward":{"task_success":1.0,"source_fidelity":1.0}}' \
    '{"cmd":"sleep","ticks":5}' \
    '{"cmd":"checkpoint"}' \
    '{"cmd":"shutdown"}' | "${SLEEP_WAKE_CMD[@]}"
fi
