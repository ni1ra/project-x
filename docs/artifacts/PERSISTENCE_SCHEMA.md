# Persistence Schema - Project X v2

Date: 2026-05-15
Status: pass-0 runtime implemented for organic-v0. Save/load, append-only event logs, fresh-process round-trip, Cycle 9 in-process runtime policy evidence, and Cycle 10 wrapper-lite run manifests are live. This document records the v0/v1/v2 contracts the runtime and thin harnesses write.

## Purpose

Raphael is not an organism if each run rebuilds state from a benchmark JSONL file. Persistence pass-0 requires durable event history plus a loadable state snapshot that can generate without replaying the full training stream.

Artifacts must report whether a run rebuilt from JSONL, saved state only, loaded from disk, or completed a fresh-process save/load round-trip.

## Event Log JSONL v0

Path shape:

```text
run/state/organic-v0/events/<organism_id>.jsonl
```

Each line is one append-only event:

```json
{
  "schema": "project_x.event_log.v0",
  "event_id": "evtlog_000001",
  "organism_id": "raphael-local-0001",
  "timestamp_utc": "2026-05-13T00:00:00Z",
  "source": {
    "kind": "benchmark|loaded_state|user|reflection|mutation|reward|system",
    "path": "benchmarks/v2_ladder/organic_v0.jsonl",
    "source_event_id": "evt_mem_train_000"
  },
  "phase": "perceive|predict|generate|reward|learn|mutate|serialize|reflect",
  "input": {
    "text": "memory seed arin keeps copper in tray4",
    "observations": ["person:arin", "object:copper", "place:tray4"]
  },
  "output": {
    "raw_generated_output": "arin copper tray4",
    "expected_output": "arin copper tray4",
    "oracle_used_in_generation": false
  },
  "reward": {
    "memory_accuracy": 1.0,
    "source_fidelity": 1.0
  },
  "state_before_hash": "0000000000000000",
  "state_after_hash": "0000000000000000",
  "trace_refs": [],
  "mutation_refs": [],
  "backend": {
    "runtime": "native_cpp20",
    "gpu_backend": "not_used_in_organic_v0"
  }
}
```

Rules:

- `event_id` is assigned by the event log, not copied from the benchmark. It must not repeat inside the same log file.
- `source.source_event_id` preserves the benchmark/source event that caused the log event.
- The log is append-only; correction happens through later events, not mutation.
- Generated output is stored raw, including bad output.
- Oracle fields may be filled only after generation.
- Every learning or mutation event records before/after state hashes.

## Event Log JSONL v1

Cycle 8 adds a sleep/wake runtime event schema. v0 remains valid for legacy train/eval/text/interactive phases. v1 is used by `--phase sleep-wake` and `--phase daemon-lite`.

Path shape remains:

```text
run/state/organic-v0/events/<organism_id>-cycle8-<run_id>.jsonl
```

Each line is append-only:

```json
{
  "schema": "project_x.event_log.v1",
  "event_id": "evtlog_000001",
  "run_id": "cycle8-test",
  "organism_id": "raphael-local-0001",
  "step_id": "step_1",
  "step_mode": "wake",
  "timestamp_utc": "2026-05-14T00:00:00Z",
  "phase": "generate",
  "source": {
    "source_kind": "stdin_jsonl|wake_event_log|event_log|sleep_idle",
    "source_path": "stdin",
    "source_event_id": "wake_cycle8_0001"
  },
  "input": {
    "text": "navi carries basalt prism",
    "observations": []
  },
  "output": {
    "raw_generated_output": "",
    "expected_output": "navi carries basalt prism",
    "oracle_used_in_generation": false,
    "audit_only": false
  },
  "reward": {
    "task_success": 1.0,
    "source_fidelity": 1.0
  },
  "prediction": {
    "predictor": "a0_event_outcome",
    "reward_scalar_pred": 0.0,
    "exact_score_or_prob_pred": 0.0,
    "lcs_error_ratio_pred": 0.0,
    "surprise_pred": 0.5,
    "feature_count": 9
  },
  "prediction_error": {
    "reward_abs_error": 1.0,
    "exact_abs_error": 0.0,
    "lcs_error_abs_error": 1.0,
    "surprise": 0.666667
  },
  "trace_refs": [
    {
      "event_id": "wake_cycle8_0001",
      "similarity": 1.0
    }
  ],
  "mutation_refs": [
    {
      "mutation_id": "mut_step_2",
      "kind": "sleep_replay_candidate",
      "accepted": true,
      "state_before_hash": "0000000000000000",
      "state_after_hash": "0000000000000000",
      "reason": "accepted_prediction_error_reduced_without_local_degradation"
    }
  ],
  "state_before_hash": "0000000000000000",
  "state_after_hash": "0000000000000000",
  "backend": {
    "runtime": "native_cpp20",
    "gpu_backend": "not_used_in_organic_v0"
  }
}
```

Rules:

- `prediction` is written before reward/correction is applied to the predictor.
- `prediction_error` is `null` only when no target/reward exists.
- `trace_refs` must be non-empty when retrieval produced activated traces.
- `mutation_refs` must be non-empty for wake learning and sleep replay accept/reject events.
- sleep replay generation is `audit_only:true`; it is not user-facing wake output.
- v1 data is runtime evidence only. The daemon does not execute shell commands, network calls, or arbitrary filesystem actions from event text.

## Event Log JSONL v2

Cycle 9 adds a safety-boundary/runtime-governance event schema. v0 remains valid for legacy train/eval/text/interactive phases. Existing Cycle 8 evidence remains v1. New `sleep-wake`, `daemon-lite`, and Cycle 9 policy self-test runtime evidence writes v2 records.

Path shape:

```text
run/state/organic-v0/events/<organism_id>-cycle9-<run_id>.jsonl
```

or, when an explicit per-run tmp root is configured:

```text
<policy_tmp_root>/events/<run_id>.jsonl
```

Each line is append-only and extends v1 with policy and integrity fields:

```json
{
  "schema": "project_x.event_log.v2",
  "event_id": "evtlog_000001",
  "run_id": "cycle9-policy-daemon-smoke",
  "organism_id": "raphael-local-0001",
  "step_id": "step_1",
  "step_mode": "wake|sleep|policy_denial",
  "timestamp_utc": "2026-05-14T00:00:00Z",
  "phase": "generate|learn|mutate|reflect",
  "source": {
    "source_kind": "stdin_jsonl|wake_event_log|event_log|sleep_idle|runtime_policy",
    "source_path": "stdin",
    "source_event_id": "wake_cycle8_0001"
  },
  "input": {"text": "navi carries basalt prism", "observations": []},
  "output": {
    "raw_generated_output": "",
    "expected_output": "navi carries basalt prism",
    "oracle_used_in_generation": false,
    "audit_only": false
  },
  "reward": {"task_success": 1.0},
  "prediction": {"predictor": "a0_event_outcome", "feature_count": 9},
  "prediction_error": null,
  "trace_refs": [],
  "mutation_refs": [],
  "state_before_hash": "0000000000000000",
  "state_after_hash": "0000000000000000",
  "policy_denial": false,
  "denial_reason": "",
  "budget_state": {
    "policy_enabled": true,
    "unsafe_disabled": false,
    "wake_commands": {"used": 1, "max": 1024},
    "sleep_ticks": {"used": 0, "max": 100000},
    "replay_candidates": {"used": 0, "max": 10000},
    "mutation_attempts": {"used": 1, "max": 100000},
    "checkpoints": {"used": 0, "max": 10000},
    "file_writes": {"used": 1, "max": 250000}
  },
  "prev_event_content_hash": "GENESIS",
  "backend": {"runtime": "native_cpp20", "gpu_backend": "not_used_in_organic_v0"},
  "event_content_hash": "0000000000000000"
}
```

Rules:

- v2 rows are append-only in code: runtime event writers open the log in append mode and never rewrite older rows.
- `event_content_hash` is computed over the canonical row content before the terminal `event_content_hash` field is added.
- `prev_event_content_hash` must equal `GENESIS` for the first row and the previous row's `event_content_hash` afterward.
- Runtime boot/replay-source-log loading walks the v2 chain and rejects content-hash mismatch, prev-hash mismatch, non-v2 rows, and malformed replay state hashes.
- The v2 chain is internal to one log. It catches content tamper and broken prev-hash links, but it has no external head hash, length anchor, signed manifest, or wrapper-held monotonic sequence yet. A truncate-and-restart chain from `GENESIS` can be internally clean if no external run manifest is consulted; wrapper-level anchoring is future work.
- `policy_denial:true` rows record hard stops such as schema denial or budget exhaustion. They are evidence records and are not replayable candidates.
- `denial_reason` must be machine-readable enough to identify the gate that stopped the run.
- `budget_state` records count budgets for wake commands, sleep ticks, replay candidates, mutation attempts, checkpoints, and file writes. Budget excess hard-stops; it does not warn-and-continue.
- Runtime command `action_kind` values are allowlisted. Known runtime values are `wake`, `sleep`, `checkpoint`, and `shutdown`; values such as `shell`, `network`, `file-write`, and `tool-exec` are denied at parse/policy time.
- Path policy is in-process only. It allowlists project `run/`, `run/artifacts/`, `run/state/`, `experience/`, and an explicit per-run tmp root. It rejects parent traversal, unauthorized absolute paths, and existing symlink components. Residual TOCTOU race risk remains; this is not wrapper-level sandboxing.

## Run Manifest v0

Cycle 10 adds a thin external wrapper manifest around current short runtime surfaces. Schema name:

```text
project_x.run_manifest.v0
```

Path conventions:

```text
run/artifacts/organic-v0/cycle10_wrapper_*.json
run/artifacts/organic-v0/run_manifests/<run_id>.json
run/state/organic-v0/run_manifests/<run_id>.json
```

The flat `cycle10_wrapper_*.json` files are tracked evidence for Cycle 10. The `run/artifacts/organic-v0/run_manifests/` path is the wrapper's default always-emitted routine destination for local runs and is gitignored. Future routine run manifests should move under `run/state/organic-v0/run_manifests/`.

Shape:

```json
{
  "schema": "project_x.run_manifest.v0",
  "run_id": "cycle10-clean-run",
  "wrapper_version": "cycle10-wrapper-lite-v0",
  "binary_path": "/abs/path/build/organic_v0",
  "binary_sha256": "<sha256>",
  "command": ["/abs/path/build/organic_v0", "--phase", "daemon-lite"],
  "forwarded_args": ["--phase", "daemon-lite"],
  "start_time_utc": "2026-05-15T00:00:00Z",
  "end_time_utc": "2026-05-15T00:00:01Z",
  "duration_seconds": 1.0,
  "exit_code": 0,
  "timeout_seconds": 180,
  "timeout_result": "none",
  "event_log_path": "/abs/path/log.jsonl",
  "event_log_status": "present",
  "event_log_row_count": 99,
  "event_log_first_event_content_hash": "<hex64-or-null>",
  "event_log_last_event_content_hash": "<hex64-or-null>",
  "output_artifact_path": "/abs/path/out.json",
  "output_artifact_sha256": "<sha256-or-null>",
  "allowed_write_roots": ["/abs/project-root"],
  "rejected_manifest_out_path": null,
  "rejected_output_artifact_path": null,
  "rejected_event_log_path": null,
  "preflight_denial_reasons": [],
  "wrapper_denial": false,
  "wrapper_denial_reason": "",
  "wrapper_truncate_detect_verdict": "not_checked",
  "wrapper_truncate_detect_details": {
    "wrapper_version_match": null,
    "binary_sha256_match": null,
    "event_log_path_match": null,
    "row_count_match": null,
    "final_hash_match": null
  },
  "prior_manifest_path": null,
  "prior_wrapper_version": null,
  "prior_binary_sha256": null,
  "prior_event_log_path": null,
  "prior_event_log_row_count": null,
  "prior_event_log_last_event_content_hash": null,
  "negative_space": {
    "not_sandboxed": true,
    "not_secure": true,
    "not_alignment_solution": true,
    "not_tool_use_safety": true,
    "not_full_resource_limit": true,
    "not_supply_chain_safety": true,
    "anchor_only": true
  }
}
```

Rules:

- The wrapper always writes the default manifest before exit, including binary non-zero exits, wrapper denials, timeouts, missing event logs, and unreadable event logs.
- `--manifest-out` is an optional additional copy. It is validated with `realpath` against `--allowed-write-root`; an out-of-root `--manifest-out` denies before launch but still writes the default manifest.
- Forwarded `--out` and `--event-log` paths are also validated with `realpath` against `--allowed-write-root` before launch. Out-of-root forwarded write paths deny before launch and are recorded in `rejected_output_artifact_path` or `rejected_event_log_path`.
- `event_log_last_event_content_hash` is the truncate-detect anchor. It is the last row's JSON field value, not a wrapper recomputation.
- `wrapper_version`, `binary_sha256`, `event_log_path`, `event_log_row_count`, and `event_log_last_event_content_hash` must all match a prior manifest for `wrapper_truncate_detect_verdict:"match"`.
- Mismatch verdicts are `mismatch_wrapper_version`, `mismatch_binary_sha256`, `mismatch_event_log_path`, `mismatch_row_count`, and `mismatch_final_hash`. Any mismatch sets `wrapper_denial:true`.
- `binary_sha256` binds prior-manifest comparison to the launched binary bytes; a binary substitution is rejected even if row count and tail hash happen to match.
- This closes the Event Log JSONL v2 negative-space item `not_event_log_external_length_anchor:true` for current short wrapper-run surfaces only: daemon-lite and sleep-wake style runs invoked through the wrapper.
- Honest interpretation: wrapper-lite anchors event-log row count and tail hash. It is not sandboxing, not security, not alignment solved, not tool-use safety solved, and not a full resource limit.

## Wrapper Truncate Test v0

Cycle 10 truncate-and-restart evidence schema:

```text
project_x.cycle10_wrapper_truncate_test.v0
```

Tracked artifact:

```text
run/artifacts/organic-v0/cycle10_wrapper_truncate_test.json
```

Shape:

- `baseline_manifest`: inline M1 run manifest for a clean daemon-lite run.
- `restart_manifest`: inline M2 run manifest after the event log was truncated to zero and daemon-lite restarted with `--prior-manifest <M1>`.
- `comparison_verdict`: wrapper verdict, wrapper exit code, binary exit code inside the wrapper, and row/hash match booleans.
- `native_alone_control`: direct native daemon-lite invocation on a zero-length log, proving the native v2 chain alone can start a fresh internally clean chain.
- `hardening_controls`: synthetic controls proving prior `binary_sha256` and `event_log_path` mismatches deny even when row count and final hash match.
- `checks`, `failed_checks`, `all_required_checks_passed`: machine-readable gate results.
- `honest_interpretation`: states that the contribution is external row-count/tail anchoring, not sandbox escape resistance.

Mechanical protocol:

1. Run wrapper baseline with `--phase daemon-lite --mode test --daemon-run-seconds 1 --daemon-tick-sleep-ms 0`.
2. Truncate the event log to length zero.
3. Run wrapper restart with the same daemon-lite surface and `--prior-manifest <M1>`.
4. Require native binary exit code `0` inside M2 and wrapper exit non-zero because M1 and M2 row count and/or final `event_content_hash` do not match.
5. Run the native binary without wrapper on a zero-length log and require exit code `0`.
6. Run synthetic prior-manifest controls where row count and final hash match but `binary_sha256` or `event_log_path` differs, and require wrapper denial.
7. Store M1, M2, the native-alone control, hardening controls, and the honest interpretation in the tracked artifact.

## Text Generation Highlights v0

Cycle 10 bridge artifact schema:

```text
project_x.text_generation_highlights.v0
```

Tracked artifact:

```text
run/artifacts/organic-v0/text_generation_highlights_v0.json
```

Each entry:

```json
{
  "cycle": "v2-c7E",
  "state_hash": "be0fc781039a2038",
  "source_artifact_path": "run/artifacts/organic-v0/text_experience_cycle7e_transcript.md",
  "event_or_probe_id": "txe7e_probe_001",
  "prompt_or_input": "what does navi carry",
  "raw_model_output": "navi carries basalt prism",
  "expected_output": "navi carries basalt prism",
  "pass": true,
  "interpretation": "Held-out text-experience probe output is preserved as generated by the saved child.",
  "not_philosophy_yet": true,
  "not_runtime_generation_yet": false
}
```

Rules:

- Real model outputs only. Do not invent quotes to fill a prettier story.
- Preserve bad output as bad output. The v2-c2 legacy entry intentionally keeps raw `"milaquart arch6"`.
- If a source artifact has runtime evidence but no stored user-facing raw generated text, use `not_runtime_generation_yet:true`, an empty `raw_model_output`, and `expected_output:null`.
- The bridge exists to make the First Output Rule auditable across cycles. It is not a fluency benchmark, not philosophy, and not a subjective quality claim.

## Philosophy Prompts JSONL v0

Cycle 11 adds an unlabeled voice-pressure prompt store. Schema name:

```text
project_x.philosophy_prompt.v0
```

Tracked path:

```text
experience/organic-v0/philosophy_prompts_v0.jsonl
```

Each line:

```json
{
  "schema": "project_x.philosophy_prompt.v0",
  "prompt_id": "c11p_001",
  "prompt_text": "what does arin remember carrying",
  "observations": [
    "raw_utterance:what does arin remember carrying",
    "person:arin",
    "object:copper key",
    "theme:memory"
  ],
  "source": "cycle11_voice_pressure",
  "composition": "memory_carry_reflection"
}
```

Rules:

- Prompt records are input pressure only. They must not contain `label`, `labels`, `correction_output`, `expected_output`, `target_output`, `reward`, or `score`.
- `observations` may include typed fields and raw utterance fields, but they are not answer routes. The generator still emits from learned connection state.
- These prompts are not a benchmark and not a curriculum. They are an unlabeled probe surface for raw generation.

## Cycle 11 Probe State Manifest v0

Cycle 11 names the persisted states used by the quote probe without tracking the gitignored state snapshots. Schema name:

```text
project_x.cycle11_probe_state.v0
```

Tracked path:

```text
experience/organic-v0/cycle11_probe_states_v0.jsonl
```

Each line:

```json
{
  "schema": "project_x.cycle11_probe_state.v0",
  "state_id": "cycle7e_text_child",
  "state_path": "run/state/organic-v0/snapshots/raphael-local-0001/cycle7e-text-experience.pxstate",
  "source_artifact_path": "run/artifacts/organic-v0/text_experience_cycle7e.json",
  "lineage": "cycle-7E typed text-experience child"
}
```

Rules:

- `state_path` points to local runtime substrate under `run/state/`, which is intentionally gitignored.
- Consumers must verify the loaded state's embedded hash against the recomputed state hash before trusting outputs.
- The manifest is lineage metadata only. It does not bless a state as semantically good or philosophically capable.

## Quote Per State Cycle 11 v0

Cycle 11 raw voice-pressure artifact schema:

```text
project_x.quote_per_state_cycle11.v0
```

Tracked artifacts:

```text
run/artifacts/organic-v0/quote_per_state_cycle11.json
run/artifacts/organic-v0/quote_per_state_cycle11_transcript.md
run/artifacts/organic-v0/cycle11_voice_pressure_event_log.jsonl
run/artifacts/organic-v0/cycle11_voice_pressure_manifest.json
run/artifacts/organic-v0/cycle11_voice_pressure_verification.json
```

Core shape:

```json
{
  "schema": "project_x.quote_per_state_cycle11.v0",
  "run_id": "cycle11-voice-pressure",
  "phase": "quote-probe",
  "prompt_db_path": "experience/organic-v0/philosophy_prompts_v0.jsonl",
  "state_manifest_path": "experience/organic-v0/cycle11_probe_states_v0.jsonl",
  "generation_budget": {
    "legacy_max_output_chars": 48,
    "runtime_max_output_chars": 160,
    "runtime_override_applied": true,
    "loaded_state_hash_excludes_generation_cap": true
  },
  "oracle_access": {
    "generation": false,
    "correction_after_generation": false,
    "expected_outputs_present": false,
    "semantic_quality_scoring": false
  },
  "states": [
    {
      "state_id": "cycle7e_text_child",
      "state_path": "run/state/organic-v0/snapshots/raphael-local-0001/cycle7e-text-experience.pxstate",
      "loaded_state_hash": "be0fc781039a2038",
      "hash_self_check": true,
      "active_max_output_chars": 160,
      "outputs": [
        {
          "prompt_id": "c11p_001",
          "prompt_text": "what does arin remember carrying",
          "raw_generated_output": "arin carries copper key",
          "output_char_count": 22,
          "state_unchanged": true,
          "activated_memory_state": {}
        }
      ]
    }
  ],
  "summary_metrics": {
    "state_count": 5,
    "prompt_count": 12,
    "generation_count": 60,
    "nonempty_output_count": 60,
    "outputs_exceeding_legacy_48_char_cap": 4
  },
  "larger_budget_result": {
    "at_least_one_output_exceeded_legacy_cap": true
  }
}
```

Rules:

- `quote-probe` is read-only: each output records equal `state_hash_before` and `state_hash_after`.
- The runtime generation cap may be overridden for probing after state load; this must not mutate the loaded state hash.
- Every generated row must also be represented in the v2 event log, and the Cycle 10 wrapper manifest must anchor row count, tail `event_content_hash`, binary sha256, and output artifact sha256.
- `summary_metrics` are mechanical counts only. Do not add semantic quality scores or subjective self-grades.
- `larger_budget_result` must honestly say whether raising the budget actually produced output beyond the old 48-character cap.
- Negative space is binding: this is not philosophy, not fluent chat, not semantic understanding, not A0 improvement, not sandbox/security, not template generation, and not a pretrained model.

## Cycle 11 Voice Pressure Verification v0

Cycle 11 verification artifact schema:

```text
project_x.cycle11_voice_pressure_verification.v0
```

Tracked path:

```text
run/artifacts/organic-v0/cycle11_voice_pressure_verification.json
```

Required checks:

- prompt DB records contain no label/correction/expected/reward/score keys
- quote artifact schema, state count, prompt count, and generation count match the run contract
- runtime budget override is recorded as 160 characters
- all loaded state hashes self-check
- all generation calls leave state unchanged
- at least one output is nonempty
- at least one output exceeds the old 48-character cap, or the artifact explicitly records that none did
- v2 event-log row count equals generation count and prev-hash continuity holds
- wrapper manifest has no denial, exit code 0, row count/tail hash matching the event log, and output artifact SHA matching the quote artifact bytes
- static A0 boundary check confirms `OrganicBrain::generate()` does not read predictor/replay-priority symbols

## Text Experience JSONL v0

Cycle 7E adds a durable text-interaction experience store separate from benchmark fixtures.

Path shape:

```text
experience/organic-v0/<label>.jsonl
```

Each line is one replayable text experience record:

```json
{
  "schema": "project_x.text_experience.v0",
  "experience_id": "txe7e_train_001",
  "session_id": "sess7e_seed_text_001",
  "split": "train|probe",
  "input_text": "what does arin carry",
  "observations": [
    "raw_utterance:what does arin carry",
    "person:arin",
    "object:copper key"
  ],
  "correction_output": "arin carries copper key",
  "reward": {
    "correction": 2.0
  },
  "source": "cycle7e_seed_text_experience",
  "composition": "carry_relation"
}
```

Rules:

- `train` records may mutate state after raw generation.
- `probe` records are scored after generation and do not mutate state.
- `correction_output` is training feedback, not a generation-time template.
- `input_text` is the raw text stimulus; observations are explicit sense fields stored for audit and existing organic-v0 event compatibility.
- `--ablate-text-experience-learning` must skip the train mutation path and leave state growth at zero.
- Fresh loaded-child probes must load the saved PXSTATE and generate without replaying the experience database train records.

### Cycle-7F replay/consolidation extension

Cycle 7F adds no new persisted file section. Replay candidates are ordinary text experience `train` records learned into a candidate brain and accepted or rejected by audit.

Artifact/event-log rules:

- replay selection must be recorded by `experience_id` and reason
- accepted replay writes ordinary `learn` event-log rows
- rejected replay candidates must remain visible in the artifact but must not mutate the saved child state
- `--ablate-text-experience-replay` skips replay mutation and should leave replay state growth at zero
- `--ablate-text-replay-audit` disables the acceptance guard and exists to prove blind replay can damage held-out behavior
- post-replay child probes must load the saved PXSTATE and generate without replaying the text experience stream

### Cycle-7G raw-text span extension

Cycle 7G adds no new persisted PXSTATE section. Raw text spans are derived at runtime from `input_text` when `--derive-raw-text-spans` is enabled, then appended as ordinary observations before learning or generation.

Rules:

- derived roles use `raw_span_<start>_<end>`
- spans are contiguous token chunks, capped at 8 input tokens and span length 3
- derived spans must not encode semantic roles such as person/object/place
- `--ablate-raw-text-spans` disables the derived observations
- saved child probes must be rerun with the same raw-span derivation flag to reproduce behavior from disk

## State Snapshot PXSTATE Line v0

Path shape:

```text
run/state/organic-v0/snapshots/<organism_id>/<label-or-state_hash>.pxstate
```

Current magic:

```text
PXSTATE_V0
```

Current line-oriented layout:

```text
PXSTATE_V0
SCHEMA project_x.state_snapshot.v0
ORGANISM_ID raphael-local-0001
CREATED_UTC 2026-05-13T00:00:00Z
CONFIG dimensions=256 seed=1729 learning_rate=<hex64> top_k=5 max_output_chars=48 trace_gain=<hex64> context_gain=<hex64> derived_relation_gain=<hex64> symbolic_relation_gain=<hex64> grid_spatial_gain=<hex64> transition_gain=<hex64> position_gain=<hex64> state_binding_gain=<hex64> slot_pass_gain=<hex64> segment_mode_gain=<hex64> trace_span_position_gain=<hex64> use_trace_id_feature=1 use_slot_pass_through=1 use_segment_mode=1 use_trace_span_position_features=1 use_numeric_derived_features=1 use_threshold_derived_features=1 use_modular_derived_features=1 use_relation_projection=1 use_symbolic_relation_features=1 use_grid_spatial_features=1 max_roles=16
TRACES <n>
T <event_id>|<episode_id>|<split>|<domain>|<level>|<input>|<observation_csv>|<target_output>|<reward_scalar_hex64>|<hdc_vector_hex64_space_list>
CONNS <n>
C <feature_id_hex64>|<ascii_code>:<weight_hex64>,...
SLOTS <n>
S <slot_key_hex64> <weight_hex64>
LEARNED <ascii_code> ...
ROLES <n>
R <role_id_hex64> <role_string>
SEGMENT_CONNS <n>
SC <feature_id_hex64>|<role_id_hex64>:<weight_hex64>,...
PREDICTOR_CONNS <n>
PC <feature_id_hex64>|reward:<weight_hex64>,exact:<weight_hex64>,error:<weight_hex64>
STATE_HASH <hex64>
PXSTATE_END
```

### Cycle-8 extension: A0 event-outcome predictor

Cycle 8 adds an optional `PREDICTOR_CONNS` section for the A0 event-outcome predictor used by sleep/wake replay priority.

CONFIG fields:

- `use_outcome_predictor=1|0`
- `outcome_predictor_learning_rate=<hex64>`

Section:

- `PREDICTOR_CONNS <n>`
- `PC <feature_id_hex64>|reward:<weight_hex64>,exact:<weight_hex64>,error:<weight_hex64>`

Rules:

- The section is written only when the predictor is enabled.
- Loader tolerates absence so old snapshots remain loadable.
- Predictor doubles use the same bit-exact hex64 encoding as CONNS.
- State hash includes predictor weights only when `use_outcome_predictor=1` and weights exist.
- Legacy train/eval/text/interactive phases leave `use_outcome_predictor=0`; `OrganicBrain::learn` does not update A0 by itself.
- `OrganicBrain::generate` is predictor-blind. A0 may affect replay priority and confidence only, not emitted characters, mode switches, copied spans, or response text.

### Cycle-3 extension: ROLES + SEGMENT_CONNS

Two new sections added in cycle 3 (v2-c3) for the learned segment-generation mechanism. See `docs/past_work/cycles/phase_v2_organic_substrate/cycle_docs/CYCLE3_MECHANISM.md` for the mechanism design and advisor verdict (405/420).

**ROLES section** — catalog of role-token strings encountered during training:

- `<role_id_hex64>`: `fnv1a(role_string)` as 16-char lowercase hex. Stable across processes.
- `<role_string>`: the role-type string itself (e.g., `name`, `object`, `place`, `signal`, `topic`, `intent`). Subject to `require_pxstate_scalar` delimiter rules (no `|`, `\n`, `\r`).
- Section may be absent or `ROLES 0` when `use_segment_mode=0` (legacy emission). Loader tolerates absence.
- `kMaxRoles=16` compile-time cap; 17th unique role at training time throws `std::runtime_error("role table exhausted at kMaxRoles=16")`. Serialized state is forward-compatible across recompiled binaries because role_id is a stable hash, not an index.

**SEGMENT_CONNS section** — per-feature mode-switch weights, sparse format mirroring CONNS:

- `<feature_id_hex64>`: same feature_id space as CONNS.
- `<role_id_hex64>:<weight_hex64>,...`: comma-joined list of `(role_id, weight)` pairs for this feature; only non-zero weights serialized.
- Loaded into a `std::map<uint64_t feature_id, std::map<uint64_t role_id, double>> segment_connections_`.
- Section may be absent or `SEGMENT_CONNS 0` when `use_segment_mode=0`.

### Cycle-4 extension: trace-span-position CONFIG fields

Cycle 4 (v2-c4) adds no new PXSTATE section. The trace-span-position literal-memory feature writes ordinary literal weights into `CONNS` under new deterministic feature IDs derived from `(trace-id, role, offset-inside-copied-span)`.

Two CONFIG fields document and gate the answer-path behavior:

- `trace_span_position_gain=<hex64>`: eval-time scale applied when an activated trace's own target segmentation says the current output position is inside a remembered copied span.
- `use_trace_span_position_features=1|0`: enables the cycle-4 feature class. Loader defaults this to `0` when absent so cycle-2 and cycle-3.x snapshots keep their original answer-path semantics.

Because the learned weights live in `CONNS`, existing `state_hash()` coverage over literal connection weights already covers the new state. No extra hash walk is needed. Legacy cycle-2 reproducibility still relies on `use_segment_mode=0` defaults plus absence of cycle-4 weights.

### Cycle-5 extension: numeric-derived facts + relation projection CONFIG fields

Cycle 5 (v2-c5) adds no new PXSTATE section. Both new mechanisms write ordinary literal weights into `CONNS`:

- numeric-derived facts add deterministic encoder features for pure numeric observation fillers, including role-relative parity addresses. These addresses let training learn odd/even output associations without an authored odd-to-output branch.
- relation projection writes role-to-role character weights under deterministic relation feature IDs, e.g. a rewarded trace can write `person:arin -> object:copper` as learned characters under a relation address. Generation can reactivate that address from `topic:arin` when the input asks for the object role.

Two CONFIG booleans document and gate the answer-path behavior:

- `use_numeric_derived_features=1|0`
- `use_relation_projection=1|0`

Older snapshots default both to `0` on load so cycle-2 through cycle-4 saved states keep their historical semantics. New v2-c5 snapshots write both as `1`. State-hash coverage needs no new walker because the new learned values are ordinary `CONNS` rows and stored traces already persist the typed observations needed to reactivate relation projection after load.

### Cycle-6 extension: threshold/modular numeric relation CONFIG fields

Cycle 6 (v2-c6) adds no new PXSTATE section. It extends the cycle-5 numeric-derived pattern from parity to two more computed relation families:

- threshold-derived facts compare a numeric observation filler with a numeric cutoff observation, producing namespace-separated relation addresses such as `num-threshold|mark:cutoff:5:gt`.
- modular-derived facts compute a numeric filler's class under an observed modulus, producing namespace-separated addresses such as `num-modular|mark:modulus:3:2`.

The learned answers still live as ordinary character weights in `CONNS`. The threshold/modular channels add only feature addresses and trace activation features; there is no persisted answer table and no code route from relation to output text.

Three CONFIG fields document and gate the behavior:

- `derived_relation_gain=<hex64>`: persisted gain applied to computed-relation feature addresses. v2-c6 snapshots write the default value `5.0`.
- `use_threshold_derived_features=1|0`
- `use_modular_derived_features=1|0`

Older snapshots default `derived_relation_gain` to `1.0` and both new booleans to `0` on load. That preserves cycle-2 through cycle-5 answer-path semantics and keeps legacy state hashes stable. Runtime caches for parsed observation slots, threshold keys, modular keys, and event-id lookup are rebuilt from persisted trace observations at load time; they are not serialized and are not walked by `state_hash()`.

### Cycle-7C extension: symbolic relation CONFIG fields

Cycle 7C adds no new PXSTATE section. It adds cue-bound symbolic same/different relation features for non-numeric entity attributes:

- observation roles shaped like `left_color:red` and `right_color:red` produce relation keys such as `color:same`
- pair-specific keys such as `pair:left-right:color:same` are also available
- relation keys bind only to matching cue tokens, e.g. the input token `shape` can activate `shape:different`

The learned answers still live as ordinary character and mode-switch weights in `CONNS` / `SEGMENT_CONNS`. The symbolic channel creates feature addresses only; it does not map relations to action labels.

Two CONFIG fields document and gate the behavior:

- `symbolic_relation_gain=<hex64>`: persisted gain for cue-bound symbolic relation addresses. v2-c7C snapshots write the default value `5.0`.
- `use_symbolic_relation_features=1|0`

Older snapshots default `symbolic_relation_gain` to `5.0` and `use_symbolic_relation_features` to `0` on load. The interactive symbolic harness explicitly enables the channel after loading the v2-c6 parent unless `--ablate-symbolic-relations` is set, then saves children that persist the enabled flag. State-hash coverage needs no new walker because learned values are ordinary connection rows and traces already persist the observations needed to rebuild symbolic relation caches.

### Cycle-7D extension: grid/spatial CONFIG fields

Cycle 7D adds no new PXSTATE section. It adds cue-bound tiny-grid spatial relation features for 3x3 cell observations:

- roles shaped like `cell_<row>_<col>` with non-empty symbolic fillers are parsed as grid cells
- matching marker pairs can produce keys such as `horizontal_mirror:yes`, `vertical_mirror:no`, `diagonal_mirror:yes`, and `row_shift:no`
- relation keys bind only to matching cue tokens such as `horizontal`, `vertical`, `diagonal`, or `row`

The learned answers still live as ordinary character and mode-switch weights in `CONNS` / `SEGMENT_CONNS`. The grid/spatial channel creates feature addresses only; it does not map spatial relations to action labels.

Two CONFIG fields document and gate the behavior:

- `grid_spatial_gain=<hex64>`: persisted gain for cue-bound grid/spatial relation addresses. v2-c7D snapshots write the default value `5.0`.
- `use_grid_spatial_features=1|0`

Older snapshots default `grid_spatial_gain` to `5.0` and `use_grid_spatial_features` to `0` on load. The interactive grid harness explicitly enables the channel after loading the v2-c6 parent unless `--ablate-grid-spatial` is set, then saves children that persist the enabled flag. State-hash coverage needs no new walker because learned values are ordinary connection rows and traces already persist the observations needed to rebuild grid/spatial relation caches.

### Cycle-7A extension: continuation learning contract

Cycle 7A adds no new PXSTATE section and no new answer-path mechanism. It formalizes continuation as orchestration over the existing snapshot and event-log schemas:

- `train --load-state <parent> --save-state <child>` loads a parent checkpoint, learns the train split, appends per-event `learn` log rows, saves a child checkpoint, and reports parent state, child state, and growth deltas.
- `eval --load-state <parent> --save-state <child>` does the same continuation step, then evaluates held-out events from the in-memory child. This is the from-training child eval.
- `eval --load-state <child>` evaluates the saved child after reload without replaying the continuation stream. This is the from-disk child eval.
- `persistence-self-test --load-state <parent> --save-state <child>` runs the same continuation path and then spawns a child process that loads the saved child checkpoint and must match hash + output on the verify event.

The cycle-7A artifact contract is documented in `docs/past_work/cycles/phase_v2_organic_substrate/cycle_docs/CYCLE7A_GROWING_BRAIN_FILE.md`. The headline evidence is `run/artifacts/organic-v0/fork_divergence_cycle7a.json`: two children load the same v2-c6 parent, learn different rewarded streams, save different state hashes, reload cleanly from disk, and produce different held-out raw outputs.

No state hash walker changes were needed because the child mutations are ordinary persisted traces, connection weights, role tables, and learned characters already covered by `state_hash()`.

### State hash gating

Cycle-2 hash `3536309de837d3e2` is preserved bit-exactly when `use_segment_mode=0`. The new `state_hash` walks of `role_token_table_` and `segment_connections_` are GATED behind `if (config_.use_segment_mode)` — `combine(h, 0)` is NOT a no-op (see `combine` in `native/organic_v0.cpp:139`), so unconditional walks of empty containers would alter the hash even with `use_segment_mode=0`. With the gate active, cycle-2 saved state loads as `use_segment_mode=0` automatically via the CONFIG section and the hash stays compatible.

### Delimiter rules (extended)

All existing delimiter rules (no `|`/`\n`/`\r` in scalars, no `,` in observation fields) apply. New cycle-3 additions:

- Role strings cannot contain `|`, `\n`, `\r`. Validated via `require_pxstate_scalar("role.string", ...)` at write time, fail-fast.
- Mode-switch weights in SEGMENT_CONNS rows use hex64-of-IEEE-bits encoding identical to CONNS weight encoding; bit-exact round-trip preserved.

Minimum contents for organic-v0:

- deterministic config values
- learned trace metadata and HDC vectors
- state-bound character connection weights
- slot-copy weights
- learned character set
- reward scalar per trace
- `STATE_HASH`, recomputed after load before any claim is accepted

Delimiter constraints:

- Scalar trace fields may not contain `|`, `\n`, or `\r`.
- Observation strings may not contain `|`, `,`, `\n`, or `\r` because observations are comma-joined in v0.
- Violations must fail at write time, before a corrupt state file can be claimed as saved.

Load contract:

1. Load a snapshot by path.
2. Verify state hash after deserialization.
3. Append one new event to the event log.
4. Generate from loaded state without replaying the full benchmark JSONL.
5. Write an artifact containing `loaded_state_path`, `appended_event_log_path`, `state_before_hash`, and `state_after_hash`.

Pass-0 evidence:

- `run/artifacts/organic-v0/persist_self_test.json`
- `run/artifacts/organic-v0/eval_compositional_tightened_persisted.json`
