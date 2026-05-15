# Do This Next - Project X

Generated: 2026-05-15, after Cycle 16 godify-app cycle 1 of 6 (multi-source corpus rail open).

This file is the immediate queue cut from the phase plan. It is not a cycle archive. Closed cycle evidence belongs in `docs/A_TO_Z_PLAN.md` and `docs/past_work/cycles/`; machine-readable runtime artifacts belong under `run/artifacts/`.

## Read First

1. `docs/MANIFESTO.md`
2. `docs/A_TO_Z_PLAN.md`
3. `docs/REPO_CONTROL.md`
4. `docs/artifacts/PERSISTENCE_SCHEMA.md`
5. `docs/past_work/cycles/phase_v3_safety_boundary/dev-cycle-15-recurrent-text-head.md`

## Current State

Cycle 15 shipped a native GRU-style recurrent char head trained on 27,371 bytes / 319 accepted Cycle 12B train shards (Project Gutenberg #932 only). Probe NLL `2.23725425` vs Cycle 14's `2.55547228` (12.45% relative improvement); holdout NLL `2.24776522` vs unigram `2.99608265`. Manual audit: 0/128 raw samples are correct coherent English. Substrate works; substrate IS the ceiling on tiny single-source data.

Cycle 16 is `/godify-app` 4h (started 2026-05-15 ~08:58 CEST, ends ~12:58 CEST, 6 cycles @ 20m ON / 20m OFF).

### Cycle 16 godify-cycle 1 (closed)

Diagnostic move (advisor + lain "knock socks off Demis" steer): scale from 1 source / ~27KB → multiple cross-genre sources / ~5× data to test whether data or substrate is the bottleneck. Falsifiable claim: **if probe NLL drops to ≤1.90 AND raw samples remain 0/128 correct English, the substrate is the ceiling and cycle 17 pivots architecture (BPE / multi-layer / concept-formation integration).**

Cycle-1 ship (4 new files, no edits to Cycle 12B v0 files — rail isolation):

- `experience/organic-v0/cycle16_corpus_sources.jsonl` — Cycle 16 multi-source descriptors (3 of 3 authored after cycle-1 over-ship: Austen P&P #1342, Darwin Origin #1228, Shakespeare Sonnets #1041; all sha256-anchored)
- `experience/organic-v0/cycle16_corpus_manifest.jsonl` — Cycle 16 shard manifest (48,025 rows across 3 sources)
- `scripts/prepare_cycle16_corpus.sh` — fork of prepare_cycle12 with multi-source iteration; reuses Cycle 12B filter + split + dedup + canonicalization discipline verbatim; SEPARATE manifest file preserves Cycle 12B `verify_cycle12_corpus.sh` carry-forward rail (hardcoded single-source assertion)
- `run/artifacts/organic-v0/cycle16_corpus_prepare.json` — schema `project_x.cycle16_corpus_prepare.v1`

Cycle-1 evidence:

- 22,034 candidate shards from Austen alone (13.5× Cycle 12B's 1,626)
- 3,815 accepted (9.3× Cycle 12B's 412)
- 269,086 accepted bytes (9.8× Cycle 12B's 27,371) — **already 5× the data target from one source**
- 17.31% acceptance rate; 12.15% byte acceptance
- 46 within-source duplicates; rejection breakdown: 7,580 delimiter pxstate / 5,077 non_ascii / 4,401 length min_40 / 862 length max_320 / 204 gutenberg_wrapper / 41 byline / 4 sentinel / 4 metadata_prefix
- Cycle 12B verifier still green (`all_required_checks_passed: true`, 28,536 checks); sha256 of v0 manifest / sources / patterns files unchanged from HEAD `bc2adba`
- Pre-fetched raw bytes + sha256 anchors for cycle-2 source authoring:
  - Darwin On the Origin of Species #1228: 970,615 bytes, sha256 `c8dea67f08d19467f28987d426f88bf5bf2acbf1e9a388cac4911f2154329550`, at `run/corpus/organic-v0/cycle16/cycle16_darwin_origin_pg1228/raw/pg1228.txt`
  - Shakespeare Sonnets #1041: 119,939 bytes, sha256 `9034dcbdb674f365d6e399b229f8389052e3894a0213d1caa4fa3537a554fb3f`, at `run/corpus/organic-v0/cycle16/cycle16_shakespeare_sonnets_pg1041/raw/pg1041.txt`

Honest boundary: cycle 1 ships rail infrastructure + 1 source. It does not prove language quality, semantic coverage, or generalization. The 9× shard increase from one source is mechanical (Austen's book is longer than Poe's story); the diagnostic only fires after multi-source training + sample audit completes.

## Immediate Next: Cycle 16 godify-cycle 2 (Execute-Raphael)

Cycle 2 finishes the corpus-prep half of Cycle 16. Substantive code work (native training extension to multi-source manifest) starts cycle 3.

**Cycles 1-3 closed. Commits on `phase-v3-safety-boundary`:** `01473d9` (rail open + Austen), `9554f1c` (Darwin + Shakespeare expansion), `03285b2` (verifier + REPO_CONTROL upkeep), `e818915` (cycle-2 docs handoff), `1ab427f` (cycle-3 native multi-manifest extension).

**Cycle 16 data state:** 3 sources, 9,546 accepted shards, 670,808 accepted bytes (24.5× Cycle 12B baseline). Combined train corpus 7,990 shards / 552,098 chars. ALL 10 carry-forward rails green post-extension.

**Smoke training (2 epochs hidden=64) result:**
- Probe NLL **1.95988** (Cycle 15 baseline 2.23725 → 12.4% better)
- Holdout NLL **1.95334** (Cycle 15 baseline 2.24777 → 13.1% better)
- The advisor's diagnostic threshold (probe NLL ≤ 1.90) is barely missed at 2 epochs / hidden=64. **Cycle 4 will run 48 epochs hidden=96 (Cycle 15 hyperparams)** to read the full diagnostic.

## Immediate Next: Cycle 16 godify-cycle 4 (Execute-Raphael — full training + diagnostic readout)

**A full-shape training run launched in background at the end of cycle 3 ON-shift** — `build/organic_v0 --phase neural-recurrent-text --corpus-manifest experience/organic-v0/corpus_manifest_v0.jsonl --corpus-manifest-extra experience/organic-v0/cycle16_corpus_manifest.jsonl --neural-hidden 96 --neural-epochs 48 --scenario-seed 7004 ...` → writes `run/artifacts/organic-v0/cycle16_recurrent_text_train.json` + `run/state/organic-v0/snapshots/raphael-local-0001/cycle16-recurrent-text-head.pxnn` (gitignored runtime substrate). Logs to `/tmp/cycle16_train.log`. Likely 12-25 min runtime; should complete during cycle-3 OFF-shift idle.

Acceptance gates for godify-cycle 4:

1. Verify the background training completed cleanly: `cat /tmp/cycle16_train.log | tail -10` shows `wrote run/artifacts/organic-v0/cycle16_recurrent_text_train.json` and the train.json file exists + parses + `same_process_reload_generations_match: true`.
2. **Read the diagnostic.** Extract `training.probe_nll`, `training.holdout_nll`, `training.probe_nll_relative_improvement_vs_cycle14_pct`, `training.probe_target_met`, `training.holdout_beats_unigram` from the artifact. Compare to Cycle 15's probe 2.23725 / holdout 2.24777.
3. **Fresh-process regeneration audit.** Run `build/organic_v0 --phase neural-recurrent-regenerate --load-state run/state/organic-v0/snapshots/raphael-local-0001/cycle16-recurrent-text-head.pxnn --experience-db experience/organic-v0/cycle15_generation_prompts_v0.jsonl --out /tmp/cycle16_regen.json --scenario-seed 7004` and confirm 128/128 samples match the in-process generation batch byte-for-byte.
4. **Source-overlap audit.** Char 5-gram Jaccard nearest-neighbor + longest-common-substring against the combined accepted-train corpus (Cycle 12 + Cycle 16). Near-copy threshold per Cycle 15 (Jaccard ≥ 0.82, contiguous ≥ 48 chars, or ≥90% of 32+ char output is contiguous train span).
5. **Manual 128-sample audit.** Read all 128 raw outputs. Honest count of how many are 100% correct coherent English (advisor's diagnostic). If 0/128, say 0/128. If ≥1/128, surface the sample(s) verbatim with prompt context.
6. Emit `cycle16_recurrent_text_train.json` (auto from training), draft `cycle16_recurrent_text_probe.json` + `cycle16_recurrent_text_holdout.json` + `cycle16_source_overlap_audit.json` + `cycle16_reproducibility_audit.json` + `cycle16_best_raw_output.json` (mirroring Cycle 15's artifact shape per `docs/REPO_CONTROL.md`).
7. Atomic commit cycle 4 work; if too much, split cycle 4 + 5.

**Falsifiable diagnostic (cycle 5 / advisor-set):** 
- **probe NLL ≤ 1.90 AND 0/128 correct** → substrate is the architectural ceiling; cycle 17 pivots to BPE / multi-layer / HDC+neural integration.
- **probe NLL ≤ 1.90 AND ≥1/128 correct** → data is a significant lever; scale more or pursue HDC-text integration.
- **probe NLL > 2.20 AND 0/128 correct** → either no data lift OR training bug. Investigate.
- **probe NLL between 1.90 and 2.20 AND 0/128 correct** → marginal lift. Cycle 17 considers per-character loss breakdown.

## Cycle 16 godify-cycles 4-6 (provisional scope)

- **cycle 4**: actually run the Cycle 16 recurrent training. Emit `cycle16_recurrent_text_train.json`, `cycle16_recurrent_text_probe.json`, `cycle16_recurrent_text_holdout.json`. Compare probe NLL vs Cycle 15's 2.24 and holdout NLL vs Cycle 15's 2.25. Apply 5% relative-improvement target. Honest report regardless of result.
- **cycle 5**: 128-sample regeneration via `--phase neural-recurrent-regenerate` with multi-manifest provenance. Source-overlap audit (nearest-neighbor against combined train corpus). Fresh-process reproducibility audit. `cycle16_best_raw_output.json` (honest 0/128 if 0/128). Manual sample review for 100% correct coherent English. The Hassabis-bar diagnostic FIRES at this cycle.
- **cycle 6**: docs sync (`A_TO_Z_PLAN.md` PHASE CHANGELOG v3-c16 entry + `dev-cycle-16-text-scaling.md` reflection); REPO_CONTROL rows for any new artifacts; final carry-forward rail rerun; smart-commit + push; END_TIME handoff via `/hand-off` equivalent.

Negative-space block for cycle 2:

- no template assembly
- no pretrained models
- no hosted model calls
- no semantic parsers
- no curated-corpus competence framing
- no language-quality claim from byte-count growth
- no expansion to source #4+ until existing rail proves stable
- no rewriting `corpus_sources_v0.jsonl` or `corpus_manifest_v0.jsonl` (Cycle 12B rail frozen)

Commands cycle 2 will run:

- `timeout 90s scripts/prepare_cycle16_corpus.sh`
- `timeout 60s scripts/verify_cycle12_corpus.sh`
- `timeout 60s scripts/verify_cycle16_text_scaling.sh` (after authoring)

## Cycle 16 godify-cycles 3-6 (provisional scope)

- **cycle 3**: extend `native/organic_v0.cpp` recurrent text head to accept multi-source manifest input + read both Cycle 12B and Cycle 16 accepted-train shards as combined corpus. Hyperparameters held at Cycle 15 baseline (hidden 96, 48 epochs, deterministic SGD). Begin training run.
- **cycle 4**: finish training; emit `cycle16_recurrent_text_train.json`, `cycle16_recurrent_text_probe.json`, `cycle16_recurrent_text_holdout.json`. Compare probe NLL vs Cycle 15's 2.24 and holdout NLL vs Cycle 15's 2.25. Apply 5% relative-improvement target.
- **cycle 5**: 128-sample regeneration via `--phase neural-recurrent-regenerate` with Cycle 15's prompt store. Source-overlap audit (multi-source nearest-neighbor) + fresh-process reproducibility audit + `cycle16_best_raw_output.json` (honest 0/128 if 0/128). Manual sample review for 100% correct English.
- **cycle 6**: docs sync (REPO_CONTROL rows + A_TO_Z_PLAN PHASE CHANGELOG v3-c16 entry + dev-cycle-16-text-scaling.md reflection); carry-forward rails rerun; smart-commit + push; END_TIME handoff.

## Carry-Forward Rails

Every implementation cycle must preserve these unless the artifact explicitly diagnoses and justifies a change:

- `make test`
- `timeout 180s scripts/verify_cycle9_carry_forward.sh`
- `timeout 180s scripts/verify_cycle10_wrapper.sh`
- `timeout 180s scripts/verify_cycle11_voice_pressure.sh`
- `timeout 180s scripts/verify_cycle12_corpus.sh`
- `timeout 180s scripts/verify_cycle12_exposure.sh`
- `timeout 180s scripts/verify_cycle13_diagnostics.sh`
- `timeout 180s scripts/verify_cycle14_neural_text.sh`
- `timeout 180s scripts/verify_cycle15_recurrent_text.sh`
- cycle-6 regression: 30/30, hash `29958f0880e662dc`
- clean chat rail: 1/5, hash `888b7664126b7f5f`
- legacy cycle-2 rail: 9/25, hash `3536309de837d3e2`, raw `evt_mem_test_001` output `"milaquart arch6"`
- Cycle 7B numeric interactive: seeds 7001/7002 held-out exact
- Cycle 7C symbolic interactive: seeds 7101/7102 held-out and probe exact
- Cycle 7D grid interactive: seeds 7201/7202 held-out and probe exact
- Cycle 7E text rail: all-on/from-disk exact, learning-disabled ablation degraded
- Cycle 7F replay: all-on/from-disk exact, audit-ablation degraded, replay-disabled control preserved
- Cycle 7G raw spans: all-on/from-disk exact, raw-span ablation degraded

## Cycle 16 Falsifiable Diagnostic (advisor-set)

If after cycle 16 ships:
- **probe NLL ≤ 1.90 AND 0/128 raw samples are correct English** → data was NOT the only bottleneck; substrate is the ceiling on char-RNN. Cycle 17 pivots architecture (BPE tokens, multi-layer, or HDC+neural integration per manifesto §"Concepts Before Language").
- **probe NLL ≤ 1.90 AND ≥1/128 samples are correct English** → data was a significant lever; scaling further is the path. Plan more Gutenberg sources or look at how HDC memory can co-train.
- **probe NLL > 2.20 AND 0/128 correct** → no data lift OR training-time bug. Diagnose recurrent training loop; possibly model is undertrained vs corpus size.
- **probe NLL between 1.90 and 2.20 AND 0/128 correct** → marginal lift. The next falsifiable question is whether the loss is dominated by frequent characters (article/preposition density) and the model isn't learning rare-word structure. Cycle 17 considers per-character loss breakdown.

The point: cycle 16 ships the data, cycle 17 reads the verdict the data prints.

## Process notes for next-instance Execute-Raphael (cold pickup)

- `/godify-app` APOTHEOSIS mode is active; `#∞` task tracks it.
- Working-tree state at session start had significant uncommitted Cycle 12-15 changes (REPO_CONTROL.md / native/organic_v0.cpp / multiple run/artifacts / dev-cycle docs); cycle 1 commit did NOT touch those files (blast-radius minimization). They remain in WT for prior-instance continuation or lain-authorized cleanup. The 4 cycle-1 files + this DO_THIS_NEXT.md rewrite are the only things staged.
- Heartbeat cron is DISARMED for the duration of `/godify-app` (NORMAL ⊕ APOTHEOSIS mutual exclusion).
- Listener: dual `discord-wait-for-lain.sh` armed at session start.
- Cycle-2 timer not yet armed at this writing; Execute-Raphael at cycle 2 fires `sleep 1200` BG timer at cycle open.
