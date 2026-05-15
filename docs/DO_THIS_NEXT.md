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

- `experience/organic-v0/cycle16_corpus_sources.jsonl` — Cycle 16 multi-source descriptors (1/3 authored: Austen Pride and Prejudice #1342, 1813, sha256 `212c4047137af6855be612024988dc8fe82d4720e7ac7e2ed4311427a57eabdb`, 772,389 raw bytes)
- `experience/organic-v0/cycle16_corpus_manifest.jsonl` — Cycle 16 shard manifest (22,034 rows from 1 source)
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

Acceptance gates for godify-cycle 2:

1. Append 2 source descriptors to `experience/organic-v0/cycle16_corpus_sources.jsonl`:
   - Darwin Origin #1228 (sha256 anchor above)
   - Shakespeare Sonnets #1041 (sha256 anchor above)
2. Re-run `scripts/prepare_cycle16_corpus.sh` over all 3 sources; expect `cycle16_corpus_manifest.jsonl` to grow with new rows; existing Austen rows MUST NOT mutate (append-only rail).
3. Inspect new aggregate stats in `run/artifacts/organic-v0/cycle16_corpus_prepare.json`: per-source candidate/accepted/rejected breakdown, cross-source dedup rate (a sonnet text shared between any sources would be rejected as duplicate).
4. Author `scripts/verify_cycle16_text_scaling.sh` scaffold — verifier shape that asserts (a) cycle16_corpus_sources.jsonl schema, (b) at least 1 cycle16 source, (c) per-row schema validation against `project_x.corpus_manifest.v0`, (d) source-id known set check, (e) deterministic split-bucket reproducibility from canonicalization hash.
5. Run `scripts/verify_cycle12_corpus.sh` after every change — Cycle 12B rail must stay green.
6. Add `experience/organic-v0/cycle16_corpus_sources.jsonl`, `experience/organic-v0/cycle16_corpus_manifest.jsonl`, `scripts/prepare_cycle16_corpus.sh`, `run/artifacts/organic-v0/cycle16_corpus_prepare.json` to `docs/REPO_CONTROL.md` (REPO_CONTROL upkeep vow — co-land file + row in same commit).

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
