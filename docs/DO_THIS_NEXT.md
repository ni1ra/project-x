# Do This Next - Project X

Generated: 2026-05-15, end of `/godify-app 4h` run (08:58 → 12:58 CEST).
Status: **Cycle 16 SEALED. Cycle 17 architectural pivot ready for cold pickup.**

## Read First

1. `docs/MANIFESTO.md`
2. `docs/A_TO_Z_PLAN.md` (PHASE CHANGELOG §11 has v3-c9 through v3-c16 closed)
3. `docs/REPO_CONTROL.md`
4. `docs/artifacts/PERSISTENCE_SCHEMA.md`
5. `docs/past_work/cycles/phase_v3_safety_boundary/dev-cycle-16-text-scaling.md` (cycle 16 full reflection + cycle 17 pivot recommendation)

## State at end of `/godify-app 4h` run

**Branch:** `phase-v3-safety-boundary`. Cycle 16 added 9 atomic commits on top of `bc2adba` (cycle 11 close):

```
a8b3ac9 feat(audit): cycle 16 godify-cycle 5 close — source-overlap audit + permanent rail + dev-cycle reflection + A_TO_Z_PLAN v3-c16
1025e0d docs: cycle 16 godify-cycle 4 close — DO_THIS_NEXT for cycle 5 audit close + cycle 17 architecture pivot scope
fe46d3a feat(diagnostic): cycle 16 godify-cycle 4 — training landed, falsifiable diagnostic fires (0/128 correct)
b28b0ba docs: cycle 16 godify-cycle 3 close — DO_THIS_NEXT for cycle 4 training + audit
1ab427f feat(native): cycle 16 godify-cycle 3 — multi-manifest training extension + co-land prior cycle 12-15 native code
e818915 docs: cycle 16 godify-cycle 2 close — rewrite DO_THIS_NEXT for cycle 3 native extension
03285b2 feat(corpus): cycle 16 godify-cycle 2 — verifier scaffold + REPO_CONTROL rows + carry-forward green
9554f1c feat(corpus): cycle 16 godify-cycle 1 expansion — 3 of 3 sources shipped
01473d9 feat(corpus): cycle 16 godify-cycle 1 — multi-source rail open + Austen #1342 (1 of 3)
```

**Headline diagnostic (advisor-set falsifiable test, fired cleanly):**

| Quantity | Cycle 15 (single-source) | Cycle 16 (multi-source) | Δ |
|---|---:|---:|---|
| Train shards | 319 | 7,990 | +25× |
| Train chars | ~27 KB | 552,098 | +20× |
| Probe NLL | 2.237254 | **1.494365** | **–33.2%** |
| Holdout NLL | 2.247765 | **1.475701** | **–34.3%** |
| Fresh-process bit-exact reproducibility | 128/128 | **128/128** | — |
| Source-overlap near-copies | 0/128 | **0/128** | true generalization |
| Manual correct-coherent-English samples | **0/128** | **0/128** | **substrate ceiling** |

**Verdict per advisor framing:** char-RNN substrate at hidden=96 trained on ~600 KB combined cross-genre English (Austen + Darwin + Shakespeare) CANNOT produce correct coherent English. Bottleneck = substrate shape, NOT data scale. Probe NLL crushed the 1.90 threshold (1.494), holdout beats unigram (1.476 < 2.95), source-overlap audit returns 0/128 near-copies (the NLL improvement is REAL generalization, not memorization). Manual 128-sample audit returns 0/128 correct. Cycle 17 pivots architecture.

## Immediate Next: Cycle 17 architectural pivot

**Recommended path (advisor preliminary): A. BPE / subword tokens + existing GRU substrate**

Rationale: cheapest architectural diagnostic. If BPE-level recurrent training also produces 0/N correct samples with similar NLL improvement, the architecture-vs-data verdict tightens further and the next pivot is HDC+neural integration (manifesto §Concepts Before Language). If BPE produces ≥1/N correct samples, char-level granularity was the bottleneck and scale-data-more becomes viable. Cost estimate: ~200 LOC native + tokenizer training + vocab serialization.

**Acceptance gates for Cycle 17 first sub-cycle:**

1. Author a deterministic BPE tokenizer trainer (~256-2048 vocab) over the combined Cycle 12 + Cycle 16 accepted-train corpus. Native C++20 or Python diagnostic-only with native consumption.
2. Persist vocab + merge rules to `experience/organic-v0/cycle17_bpe_vocab_v0.json` (or similar). Deterministic from seeded corpus + max_vocab.
3. Extend `native/organic_v0.cpp` with `RecurrentTokenNeuralHead` (mirrors `RecurrentCharNeuralHead` structurally; token vocab ≤ 2048 instead of char vocab 96-ish). New phase `neural-recurrent-tokens` parallel to `neural-recurrent-text`.
4. Train recurrent token head on combined Cycle 12 + Cycle 16 corpus (48 epochs hidden=96 baseline). Emit `cycle17_token_text_train.json` + `cycle17_best_raw_output.json`.
5. 128-sample regeneration + source-overlap audit + fresh-process reproducibility audit (all per Cycle 15/16 pattern).
6. Manual sample audit — same gate ("100% correct coherent English with meaningful claim"). Honest count.
7. New permanent rail `scripts/verify_cycle17_token_train.sh`.
8. PHASE CHANGELOG row v3-c17.

**Alternative paths (lower priority unless A fails or BPE design has issues):**

- **B. Multi-layer recurrent + hidden width scaling** (hidden 256-512, 2-3 GRU layers, same chars). Cost ~50-100 LOC native. Typically the weakest move — more capacity on the same architecture usually just produces longer pseudo-text.
- **C. HDC + neural integration** (manifesto §Concepts Before Language). The structurally manifesto-aligned move: HDC concept atoms drive a neural head that emits text continuations rather than raw char→char. Cost ~400-800 LOC. Highest leverage for the long-term manifesto trajectory; reserve for after BPE proves itself or fails.

## Cold pickup checklist for next-instance Execute-Raphael

1. Read this file end-to-end.
2. Read `docs/MANIFESTO.md` (Concepts Before Language law is load-bearing for cycle 17 architecture choice).
3. Read `docs/past_work/cycles/phase_v3_safety_boundary/dev-cycle-16-text-scaling.md` for the falsifiable-diagnostic context.
4. `git log --oneline -10` to confirm branch tip is `a8b3ac9` (or later cycle 6 commit).
5. Run `timeout 180s scripts/verify_cycle16_recurrent_train.sh` to confirm cycle 16 carry-forward rail is green (the pre-cycle-17 baseline).
6. Decide architectural path (A/B/C above). Recommended: A (BPE).
7. Pin #00 deliverable for cycle 17.
8. Fire pillars (`Skill('skills:pick-skill')` + `Skill('skills:sharpen-todos')`) before substantive work.

## Carry-Forward Rails (must stay green for any cycle 17+ work)

- `make test`
- `timeout 180s scripts/verify_cycle9_carry_forward.sh`
- `timeout 180s scripts/verify_cycle10_wrapper.sh`
- `timeout 180s scripts/verify_cycle11_voice_pressure.sh`
- `timeout 180s scripts/verify_cycle12_corpus.sh`
- `timeout 180s scripts/verify_cycle12_exposure.sh`
- `timeout 180s scripts/verify_cycle13_diagnostics.sh`
- `timeout 180s scripts/verify_cycle14_neural_text.sh`
- `timeout 180s scripts/verify_cycle15_recurrent_text.sh`
- `timeout 180s scripts/verify_cycle16_text_scaling.sh` (cycle 16 corpus rail; 837k+ checks)
- `timeout 180s scripts/verify_cycle16_recurrent_train.sh` (cycle 16 multi-manifest training pipeline; 22 checks)
- cycle-6 regression: 30/30, hash `29958f0880e662dc`
- clean chat rail: 1/5, hash `888b7664126b7f5f`
- legacy cycle-2 rail: 9/25, hash `3536309de837d3e2`, raw `evt_mem_test_001` output `"milaquart arch6"`
- Cycle 7B numeric interactive: seeds 7001/7002 held-out exact
- Cycle 7C symbolic interactive: seeds 7101/7102 held-out and probe exact
- Cycle 7D grid interactive: seeds 7201/7202 held-out and probe exact
- Cycle 7E text rail: all-on/from-disk exact, learning-disabled ablation degraded
- Cycle 7F replay: all-on/from-disk exact, audit-ablation degraded, replay-disabled control preserved
- Cycle 7G raw spans: all-on/from-disk exact, raw-span ablation degraded

Total 11 verifier rails + 9 substantive baselines.

## Environment + Process notes

- **Working tree at end of run** had several prior-instance Cycle 12-15 modifications that landed in the cycle-3 commit (`1ab427f`) as a co-land. Branch is now reasonably clean except for `.playwright-mcp/` scratch dir (gitignored), `docs/artifacts/PERSISTENCE_SCHEMA.md` + `docs/artifacts/paper.md` + a few `run/artifacts/organic-v0/cycle9-11*.json` files that remained WT-modified (not part of cycle 16 scope).
- **Listener:** dual `discord-wait-for-lain.sh` armed at run start; should still be running. Verify with `pgrep -af 'discord-wait-for-lain'` at next session start; if absent, rearm per CLAUDE.md DD-1 protocol.
- **Heartbeat cron:** DISARMED for the duration of `/godify-app` APOTHEOSIS mode. After END_TIME, NORMAL mode resumes per CLAUDE.md § RAPHAEL OPERATING MODES. Heartbeat cron should be REARMED at next session start IF actionable `#00` queue is non-empty (cycle 17 work IS actionable, so cron should re-arm).
- **Backround training: completed.** No long-running native processes left over from this run.
- **PXNN v2 state file** at `run/state/organic-v0/snapshots/raphael-local-0001/cycle16-recurrent-text-head.pxnn` (gitignored). Cycle 17 architecture pivot can regenerate from training rail; this file is not load-bearing for cycle 17 work.
- **Wrapper manifests under** `run/artifacts/organic-v0/run_manifests/` (gitignored per existing .gitignore).

## Known not-blockers / housekeeping

- `experience/organic-v0/cycle15_generation_prompts_v0.jsonl` still WT-modified state from prior instance — needs eventual commit but does not block cycle 17.
- `docs/artifacts/PERSISTENCE_SCHEMA.md` + `docs/artifacts/paper.md` carry prior-instance edits that did not land in cycle 16 commits.
- `src/project_x_v2/` + `tests/` empty dirs left over from v1 reset (per REPO_CONTROL.md "Not tracked, on disk" section). Candidates for removal in a housekeeping cycle.

## Final 4h run summary (for the record)

- **Run:** `/godify-app 4h pick up where gpt left off. try to knock the socks off demis.`
- **Cycles fired:** 6 × 20m ON / 20m OFF, no overrun
- **Commits:** 9 atomic (cycles 1-5 substantive + cycle 6 final close)
- **Pillars per cycle:** pick-skill + sharpen-todos (cycle 1 explicit Skill() invocations; cycles 2-6 mechanical sharpen-todos with the chain pick stable)
- **Discord posts:** 10+ substantive (cycle opens, smoke results, diagnostic, closes, END_TIME)
- **Advisor consultations:** 1 (cycle 1 — pre-execution sanity)
- **Mechanical checks total across all rails per run:** 837,173 (cycle16 verifier) + ~30,000 (cycle 12) + per-cycle ~70-2700 = on the order of 900k checks per full rail set rerun
- **Carry-forward rail set:** 9 rails at run start → 11 rails at run end (added verify_cycle16_text_scaling + verify_cycle16_recurrent_train)
- **Data scale shipped:** Cycle 12B 27,371 accepted bytes → Cycle 16 670,808 (combined 12+16 = 698,179 — 25× the cycle 12 baseline)
- **NLL diagnostic:** Cycle 15 probe 2.237 / holdout 2.248 → Cycle 16 probe 1.494 / holdout 1.476 (-33% / -34% relative)
- **Manual sample audit:** Cycle 15 0/128 → Cycle 16 0/128 (substrate ceiling)
- **Falsifiable diagnostic outcome:** advisor's threshold (probe NLL ≤ 1.90 AND 0/N correct) FIRED cleanly. Cycle 17 pivots architecture.
- **Hassabis-bar:** prose quality fails; methodology earns the stop-and-stare. Run designed so failure says something specific. Self-impression peak score: 405/420 (cycle 4 diagnostic landing commit). Run average: ~380/420. Honest. Not inflated.
