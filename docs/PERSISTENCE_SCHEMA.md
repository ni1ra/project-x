# Persistence Schema - Project X v2

Date: 2026-05-13
Status: pass-0 schema draft. Runtime persistence is not implemented yet.

## Purpose

Raphael is not persistent while each run rebuilds state from a benchmark JSONL file. This schema defines the minimum durable substrate required before organic-v0 can claim organism continuity.

Artifacts must distinguish schema readiness from runtime persistence. Until load/save exists, artifacts should report null state and event-log paths and explicitly say the run rebuilt from JSONL.

## Event Log JSONL v0

Path shape:

```text
run/state/organic-v0/events/<organism_id>.jsonl
```

Each line is one append-only event:

```json
{
  "schema": "project_x.event_log.v0",
  "event_id": "evt_20260513_000001",
  "organism_id": "raphael-local-0001",
  "timestamp_utc": "2026-05-13T00:00:00Z",
  "source": {
    "kind": "benchmark|user|reflection|mutation|reward|system",
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
  "trace_refs": ["evt_mem_train_000"],
  "mutation_refs": [],
  "backend": {
    "runtime": "native_cpp20",
    "gpu_backend": "not_used"
  }
}
```

Rules:

- Event IDs are stable and never reused.
- The log is append-only; correction happens through later events, not mutation.
- Generated output is stored raw, including bad output.
- Oracle fields may be filled only after generation.
- Every learning or mutation event records before/after state hashes.

## State Snapshot Binary v0

Path shape:

```text
run/state/organic-v0/snapshots/<organism_id>/<state_hash>.pxstate
```

Header:

```text
magic: PXSTATE
schema: project_x.state_snapshot.v0
endianness: little
organism_id: raphael-local-0001
created_utc: 2026-05-13T00:00:00Z
base_event_log_path: run/state/organic-v0/events/raphael-local-0001.jsonl
last_event_id: evt_20260513_000001
config_hash: <hex64>
state_hash: <hex64>
```

Sections:

```text
CONFIG
TRACE_INDEX
HDC_TRACE_VECTORS
CHAR_CONNECTION_WEIGHTS
SLOT_COPY_WEIGHTS
PLASTICITY_COUNTERS
REWARD_SUMMARIES
SOURCE_EVENT_REFS
CHECKSUM
```

Minimum contents for organic-v0:

- config values used for deterministic generation
- learned trace metadata and HDC vectors
- state-bound character connection weights
- slot-copy weights, if enabled
- learned character set
- event IDs that produced each state section
- checksum over all preceding bytes

Load contract:

1. Load a snapshot by path.
2. Verify checksum and state hash.
3. Append one new event to the event log.
4. Generate from loaded state without replaying the full benchmark JSONL.
5. Write an artifact containing `loaded_state_path`, `appended_event_log_path`, `state_before_hash`, and `state_after_hash`.

Until those five steps work, Project X has persistence schema only, not organism persistence.
