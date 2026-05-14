# Persistence Schema - Project X v2

Date: 2026-05-14
Status: pass-0 runtime implemented for organic-v0. Save/load, append-only event log, and fresh-process round-trip are live; this document records the v0 contract the runtime now writes.

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
CONFIG dimensions=256 seed=1729 learning_rate=<hex64> top_k=5 max_output_chars=48 trace_gain=<hex64> context_gain=<hex64> derived_relation_gain=<hex64> transition_gain=<hex64> position_gain=<hex64> state_binding_gain=<hex64> slot_pass_gain=<hex64> segment_mode_gain=<hex64> trace_span_position_gain=<hex64> use_trace_id_feature=1 use_slot_pass_through=1 use_segment_mode=1 use_trace_span_position_features=1 use_numeric_derived_features=1 use_threshold_derived_features=1 use_modular_derived_features=1 use_relation_projection=1 max_roles=16
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
STATE_HASH <hex64>
PXSTATE_END
```

### Cycle-3 extension: ROLES + SEGMENT_CONNS

Two new sections added in cycle 3 (v2-c3) for the learned segment-generation mechanism. See `docs/artifacts/CYCLE3_MECHANISM.md` for the mechanism design and advisor verdict (405/420).

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
