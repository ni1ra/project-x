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

## Cycles 1-4 CLOSED — DIAGNOSTIC RESOLVED

7 commits on `phase-v3-safety-boundary`: `01473d9` `9554f1c` `03285b2` `e818915` `1ab427f` `b28b0ba` `fe46d3a`.

**The falsifiable diagnostic FIRED cleanly.** Probe NLL **1.494365** (advisor threshold ≤ 1.90; –33.2% relative vs Cycle 15's 2.237254). Holdout NLL **1.475701** (–34.3%). Fresh-process reproducibility 128/128 bit-exact match. **Manual 128-sample audit: 0/128 correct coherent English.** Outputs markedly more coherent than Cycle 15 (real word fragments, short correct phrases visible) but no full sample is grammatical English with a meaningful claim.

**Verdict per advisor framing:** char-RNN substrate (hidden=96, single-layer GRU, char-level) IS the architectural ceiling at this corpus scale (~600 KB combined Austen + Darwin + Shakespeare). The bottleneck is substrate shape, NOT data scale. Cycle 17+ pivots architecture.

## Immediate Next: Cycle 16 godify-cycle 5 (Execute-Raphael — close cycle 16 + open cycle 17 plan)

Acceptance gates:

1. **Source-overlap audit** (`cycle16_source_overlap_audit.json`): char 5-gram Jaccard nearest-neighbor over the combined 7990 accepted train shards × 128 generation samples; longest-common-substring guard; ≥90% of 32+ char span check. Cycle 15 thresholds (Jaccard ≥0.82 / contiguous ≥48 / span ≥90%). Expected near-copy count: 0 (small NLL improvement + diverse cross-source corpus makes memorization unlikely; if non-zero, surface samples).
2. **`scripts/verify_cycle16_recurrent_train.sh`** — permanent carry-forward rail that drives the Cycle 16 recurrent training reproducibly and validates outcomes. Same shape as `verify_cycle15_recurrent_text.sh` but with `--corpus-manifest-extra` + diagnostic gate (probe NLL ≤ 1.90 expected; if regresses above, rail fails). Add this rail to the carry-forward list in this file.
3. **`docs/past_work/cycles/phase_v3_safety_boundary/dev-cycle-16-text-scaling.md`** — full reflection: hypothesis, implementation, evidence, manual audit, honest boundary, audit questions answered, cycle-17 pivot recommendation.
4. **`docs/A_TO_Z_PLAN.md`** PHASE CHANGELOG: add v3-c16 row with full evidence path list + verdict.
5. Re-run the full 10-rail carry-forward set including the new `verify_cycle16_recurrent_train.sh` rail. All green.
6. Atomic commit.

## Cycle 17 architecture pivot — candidate paths (for godify-cycle 6 handoff / next-instance scope)

Three candidate architectures to consider for the cycle-17 manifesto-aligned ship:

**A. BPE / subword tokens + same GRU**
- Pivot the substrate from char-level to byte-pair-encoding tokens (~256-2048 vocabulary).
- Existing RecurrentCharNeuralHead becomes RecurrentTokenNeuralHead.
- Reuses the entire corpus rail; only the tokenizer + vocab + neural head shape change.
- Cost: tokenizer training + native vocab serialization. ~200 LOC.
- Hassabis-bar question it answers: is char-level the granularity that's hurting, or is it model capacity?

**B. Multi-layer recurrent / stacked GRU + hidden width scaling**
- Stack 2-3 GRU layers, scale hidden width to 256-512.
- Same corpus, same tokenization (chars).
- Cost: ~50-100 LOC of native, but proportionally more training time.
- Hassabis-bar question: is single-layer the bottleneck, given the data lift is unambiguous?

**C. HDC + neural integration (manifesto §Concepts Before Language)**
- Use the existing HDC substrate (cycle 1-7) to encode concept atoms; train a neural head that maps HDC concept activations to text continuations rather than raw char→char.
- The HDC substrate already supports rule learning (cycle 7B/C/D show 14/14, 16/16 held-out transfer). Coupling concepts to language is the manifesto's actual ask.
- Cost: significant — needs HDC concept encoder + integration layer + redesigned training loop. ~400-800 LOC + new artifact schemas.
- Hassabis-bar question: does concept learning before language produce more coherent output than character-level next-prediction?

**Recommendation (preliminary, subject to advisor review at cycle 6):** start with **A (BPE)** in cycle 17 — lowest-cost pivot, fastest diagnostic answer (BPE-RNN producing pseudo-English in 3-7 word units instead of pseudo-character word units is a clear architectural-vs-data signal). If A fires the same 0/N correct sample gate, move to **C (HDC+neural)** as the structural pivot manifesto pushes toward. **B** is the weakest move — same architecture style with more parameters typically just produces longer pseudo-text.

## Cycle 16 godify-cycle 6 (Execute-Raphael — END_TIME handoff)

- Final docs sync if cycle 5 missed anything.
- Final carry-forward rail rerun for green-state seal.
- `/hand-off` style next-instance briefing: state of branch, remaining work, recommended cycle-17 architecture, expected next session's first 2 hours of work.
- Discord END_TIME post with self-impression score for the 4h run, cycle count, commit count, files changed, headlines.

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
- `timeout 180s scripts/verify_cycle16_text_scaling.sh` (Cycle 16 corpus rail; 837k+ checks)
- `timeout 180s scripts/verify_cycle16_recurrent_train.sh` (Cycle 16 recurrent training pipeline; 22 checks)
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
