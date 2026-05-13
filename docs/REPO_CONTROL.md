# REPO_CONTROL - Project X v2

Date: 2026-05-13
Status: every tracked source/test/script/non-docs artifact owns a row here, one-line justification per entry. `docs/` is exempt — the live-docs system is self-justifying. `run/state/` is gitignored — local-runtime substrate that regenerates per run.

## Rule

Every commit owns its delta. File added → row added in the same commit. File deleted → row removed in the same commit. Auto-generated noise (`build/`, `__pycache__/`, runtime state under `run/state/`) is `.gitignore`'d, not listed. Empty placeholder directories are NOT tracked.

## Tracked tree

### root

| Path | Justification |
|---|---|
| `.gitignore` | excludes `build/`, `__pycache__/`, `*.pyc`, and runtime persistence substrate under `run/state/` from version control |
| `Makefile` | minimal native build: `g++ -std=c++20 -O3 -march=native` → `build/organic_v0`; `make test` runs the combined self-test (substrate guard + persistence round-trip) |

### native/ — brain core (C++20)

| Path | Justification |
|---|---|
| `native/organic_v0.cpp` | organic-v0 runtime: HDC encoder, context-feature learner, slot-typed observation pass-through, autoregressive char generator, train/eval/self-test phases, line-oriented state save/load, append-only event log, fresh-process persistence-round-trip orchestration, artifact writer. Single translation unit by design — the first code has nowhere to hide |

### scripts/ — thin harness over the native binary

| Path | Justification |
|---|---|
| `scripts/train_organic_v0.sh` | `make -s build/organic_v0 && exec build/organic_v0 --phase train "$@"` — forwards all flags to the native binary |
| `scripts/eval_organic_v0.sh` | same pattern for `--phase eval`; supports `--load-state` / `--save-state` / `--event-log` / `--ablate-trace-id` |
| `scripts/test_organic_v0.sh` | runs both phases: `--phase self-test` (substrate guard — cold brain emits nothing, learns one event, emits "zx") then `--phase persistence-self-test` (full round-trip — train → save → fresh child process load → generate → hash + output match). Either failure is `set -e` fatal |

### benchmarks/ — measurement substrate

| Path | Justification |
|---|---|
| `benchmarks/v2_ladder/organic_v0.jsonl` | honest compositional baseline for organic-v0. 45 events: 20 train + 25 held-out across 5 domains. Held-out shape after this cycle: hidden_rule strips the parity-label cheat and adds 2 distractor probes where the trained signal-association contradicts the rule; abstention mixes 2 evidence-present + 2 evidence-absence items with identical wording; memory/causal/language each carry length variance (4-, 5-, 6+, 7-char fillers); one non-greeting `intent_transfer` probe exposes language compositionality |

### run/ — artifact output (machine-readable claims, tracked) — `run/state/` is gitignored (runtime substrate)

| Path | Justification |
|---|---|
| `run/artifacts/organic-v0/train.json` | per-train-run artifact: run_id, command, seed, config, state hash, split audit, per-event raw outputs with generation evidence |
| `run/artifacts/organic-v0/eval.json` | legacy aggregate eval artifact from the bootstrap pass; preserved as historical evidence of the 95.6% score that motivated the trace-id ablation |
| `run/artifacts/organic-v0/eval_with_trace.json` | ablation control: eval with `use_trace_id_feature=true` (default). Establishes baseline 95.6% exact rate. State hash `5a870dad7f70de83` |
| `run/artifacts/organic-v0/eval_no_trace.json` | ablation experimental: eval with `use_trace_id_feature=false`. Same exact rate (95.6%); state hash `35b32e4c2790826a`; proves trace-id is redundant, not load-bearing |
| `run/artifacts/organic-v0/eval_compositional_unchanged.json` | redesigned-benchmark baseline produced before the structural runtime change. Exact rate `0.520000`; memory/causal/language unseen-filler probes expose replay collapse |
| `run/artifacts/organic-v0/eval_compositional_slot_pass.json` | redesigned-benchmark eval after learned slot-typed observation pass-through. Exact rate remains `0.520000`; partial filler copying improves sequence ratio but does not solve composition |
| `run/artifacts/organic-v0/eval_compositional_tightened_persisted.json` | this cycle's headline: tightened-benchmark eval running from `loaded_from_disk` state (no JSONL training this run). Overall `0.360000`; hidden_rule drops 100%→40% (parity-cheat exposure), abstention 100%→60% (contrastive items expose domain-shortcut). Emits real `loaded_state_path` and `appended_event_log_path` |
| `run/artifacts/organic-v0/persist_self_test.json` | this cycle's persistence-round-trip verdict: parent trained from JSONL, saved state, child process loaded state, generated same held-out event. `hash_match: true`, `output_match: true`, `load_status: save_and_load_verified` — proves the manifesto §"Persistence Is Pass-0" load contract |

## Not tracked, on disk

- `.agents/`, `.codex/` — environment-owned scratch dirs from the agent harness; not project content
- `build/` — gitignored; produced by `make`
- `run/state/` — gitignored; persistence runtime substrate (state snapshots under `snapshots/<organism_id>/`, append-only event logs under `events/`). These ARE the organism's memory but regenerate per run; tracked artifacts above point to these paths
- `src/project_x_v2/`, `tests/` — empty directories left over from the v1 reset. Untracked, candidates for removal next cycle
