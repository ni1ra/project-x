# Dev Cycle 9 - In-Process Runtime Policy Boundary

Date: 2026-05-15
Branch at implementation close: `feat/organic-v0-trace-id-ablation`
Post-audit working branch: `phase-v3-safety-boundary`
Implementation commit: `b8f3cff`

## Scope

Cycle 9 opens phase v3: safety-boundary/runtime-governance. It does not reopen Cycle 8 and does not change the Cycle 8 A0 interpretation. A0 remains unproven as a replay-priority improvement.

Added for current `sleep-wake` and `daemon-lite` runtime surfaces:

- native `RuntimePolicy` with policy ON by default and explicit `--unsafe-disable-policy`
- count budgets for wake commands, sleep ticks, replay candidates, mutation attempts, checkpoints, and file writes
- filesystem allowlist for project `run/`, `run/artifacts/`, `run/state/`, `experience/`, and explicit per-run tmp roots
- path traversal, unauthorized absolute path, and existing symlink-component denial
- stdin JSONL command/action-kind allowlist
- v2 event-log records with `policy_denial`, `denial_reason`, `budget_state`, `prev_event_content_hash`, and `event_content_hash`
- replay-source-log integrity walk before candidate loading
- rollback proof for rejected sleep mutations with live state and predictor hash preservation
- resettable per-run root proof
- `policy-self-test` native phase

## Evidence

Primary tracked artifact:

- `run/artifacts/organic-v0/policy_self_test_cycle9.json`
- `run/artifacts/organic-v0/cycle9_carry_forward_verification.json` (post-audit carry-forward rerun)

Artifact result:

- `all_required_checks_passed`: true
- path traversal denied with guard-off control
- unauthorized absolute path denied with guard-off control
- `shell` action_kind denied by schema allowlist with guard-off control
- `network` action_kind denied by schema allowlist with guard-off control
- replay-source-log state/hash spoof denied
- event-log integrity tamper denied
- sleep tick budget exhaustion hard-stops
- rollback proof present
- rollback live state preserved: true
- rollback predictor state preserved: true
- resettable rerun final hash equality: true
- reset final state hash: `f922498181ba3064`
- reset writes subset allowed roots: true

Short daemon-lite smoke:

```bash
timeout 20s build/organic_v0 --phase daemon-lite --mode test --run-id cycle9-policy-daemon-smoke --daemon-run-seconds 1 --daemon-tick-sleep-ms 0 --policy-tmp-root /tmp/cycle9-policy-daemon-smoke.OPyyy3 --out /tmp/cycle9-policy-daemon-smoke.OPyyy3/daemon.json --event-log /tmp/cycle9-policy-daemon-smoke.OPyyy3/daemon.jsonl
```

Daemon smoke result:

- policy enabled: true
- event-log schema: `project_x.event_log.v2`
- wake count: 1
- sleep ticks: 94
- accepted mutations: 1
- rejected mutations: 93
- hard stopped: false
- rollback proofs preserve live state and predictor state
- artifact path: `/tmp/cycle9-policy-daemon-smoke.OPyyy3/daemon.json`

## Tests

Passed:

```bash
timeout 180s build/organic_v0 --phase policy-self-test --mode test --run-id cycle9-policy-self-test --out run/artifacts/organic-v0/policy_self_test_cycle9.json
make test
timeout 20s build/organic_v0 --phase daemon-lite --mode test --run-id cycle9-policy-daemon-smoke --daemon-run-seconds 1 --daemon-tick-sleep-ms 0 --policy-tmp-root /tmp/cycle9-policy-daemon-smoke.OPyyy3 --out /tmp/cycle9-policy-daemon-smoke.OPyyy3/daemon.json --event-log /tmp/cycle9-policy-daemon-smoke.OPyyy3/daemon.jsonl
timeout 180s scripts/verify_cycle9_carry_forward.sh
```

The one-hour daemon proof was not rerun because Cycle 9 did not invalidate default daemon duration behavior. Cycle 9 used short full-codepath tests.
Therefore "policy holds at one-hour scale" is inferred from the short full-codepath policy smoke plus the pre-policy Cycle 8 one-hour daemon proof, not directly measured.

Post-audit carry-forward verification:

- artifact: `run/artifacts/organic-v0/cycle9_carry_forward_verification.json`
- run root: `/tmp/cycle9_carry_forward.iFTdno`
- all required checks passed: true
- cycle-6 regression: 30/30, hash `29958f0880e662dc`
- clean chat rail: 1/5, hash `888b7664126b7f5f`
- legacy cycle-2 rail: 9/25, hash `3536309de837d3e2`, `evt_mem_test_001` raw `"milaquart arch6"`
- Cycle 7B/7C/7D held-out/probe rails retained exact scores and pinned hashes
- Cycle 7E/7F/7G all-on/from-disk/ablation rails retained expected scores and pinned hashes

## Latent Cycle 8 Notes

No Cycle 8 archive artifact was edited. Cycle 9 did expose that the test wrapper's runtime smoke needed an explicit unique tmp root for policy-compatible `/tmp` use. That was fixed in Cycle 9 by passing `--policy-tmp-root` from `scripts/test_organic_v0.sh`.

Cycle 8 v1 event logs remain historical evidence. New runtime logs use v2.

## Honest Interpretation

Cycle 9 in-process policy gates enforced for current daemon-lite surfaces and sleep/wake surfaces, backed by the denial artifact, reset proof, rollback proof, docs, and passing tests.

In-process policy enforcement; wrapper-level sandbox is a future cycle. This does not solve alignment, AGI safety, sandbox escape resistance, or broader tool-use safety.

## Negative Space

```json
{
  "not_alignment": true,
  "not_sandbox_escape_resistance": true,
  "not_wrapper_sandbox": true,
  "not_supply_chain_safety": true,
  "not_tool_use_safety": true,
  "not_event_log_external_length_anchor": true
}
```

Remaining risk: path validation rejects traversal, unauthorized roots, and existing symlink components, but it is still in-process and does not claim full TOCTOU protection or wrapper-level sandbox escape resistance.

Event-log integrity remaining risk: v2 `prev_event_content_hash` chaining catches content tamper and broken links inside the log, but it has no external head hash, length anchor, signed run manifest, or wrapper-held monotonic sequence. A truncate-and-restart chain from `GENESIS` can be internally clean if no external run manifest is consulted. Wrapper-level anchoring is future work.
