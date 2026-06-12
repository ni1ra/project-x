# Dev Cycle 13 - Quote-Delta Diagnostics + Mechanical Repetition-Loop Suppression

Date: 2026-05-15
Branch: `phase-v3-safety-boundary`

## Claude Feedback

Classification: modify.

Claude accepted the original diagnostics/filter/no-rewrite shape but correctly flagged that the user's updated goal was text-output quality, not diagnostics alone. The final scope kept the Cycle 12B explanation gates and added one narrow quality-relevant mechanism: reduce the post-copy repetition loop without claiming semantics.

## Acceptance Gates

1. Quote-delta diagnostics explain Cycle 12B mechanically before any corpus scale-up.
2. Content-filter ablation proves the scanner is load-bearing with learning disabled.
3. Corpus manifest no-rewrite behavior is tested through a temp manifest, not by mutating and restoring the real manifest.
4. Trace/delta localization records prompt-local corpus activation and copy-boundary driver evidence.
5. Repetition-loop suppression improves raw generation mechanics on the 12 Cycle 11 prompts.
6. Negative-space and carry-forward rails remain explicit.

## Implementation

- Added `Config::repetition_penalty_weight`, persisted in PXSTATE `CONFIG` and included in `state_hash()` when nonzero.
- Added a post-copy END feature: during raw corpus exposure, copied `raw_utterance` spans that reach target end learn an END action for the copy-boundary feature.
- Added a generation-time suffix-loop penalty gated by `repetition_penalty_weight`.
- Exported `active_copy_boundary_count`, `segment_mode_switch_count`, `copy_mode_char_count`, and `copy_boundary_feature_count` in generation evidence.
- Allowed content-filter ablation with learning disabled to log rejected text that is not PXSTATE observation-safe, while retaining the observation-safe guard when learning mutates state.
- Added `CYCLE13_TEST_MANIFEST_PATH` to the corpus prepare rail for temp-manifest no-rewrite testing.
- Added `scripts/verify_cycle13_diagnostics.sh`.

## Evidence

Final verifier:

```text
run/artifacts/organic-v0/cycle13_verification.json
```

Key metrics:

- `all_required_checks_passed:true`
- `all_acceptance_gates_passed:true`
- checks: `94`
- Cycle 12 child max-cap hits: `10`
- Cycle 13 repetition child max-cap hits: `1`
- Cycle 12 child repetition-loop count: `10`
- Cycle 13 repetition child repetition-loop count: `1`
- Cycle 13 END count: `11/12`
- Cycle 13 nonrepetitive count: `11/12`
- copy-boundary driver prompt count: `9/12`

Other artifacts:

- `run/artifacts/organic-v0/cycle13_quote_delta_diagnostics.json`
- `run/artifacts/organic-v0/cycle13_repetition_fix.json`
- `run/artifacts/organic-v0/quote_per_state_cycle13_repetition_child.json`
- `run/artifacts/organic-v0/quote_per_state_cycle13_repetition_child_transcript.md`
- `run/artifacts/organic-v0/cycle13_content_filter_ablation.json`
- `run/artifacts/organic-v0/cycle13_corpus_no_rewrite_verification.json`

## Commands

```bash
make -s build/organic_v0
scripts/verify_cycle13_diagnostics.sh
```

Carry-forward commands are listed in `docs/DO_THIS_NEXT.md`; final pass status belongs to the active worktree closeout.

## Honest Boundary

Cycle 13 proves a mechanical generator-hygiene improvement. It localizes Cycle 12B quote changes to corpus trace activation and reduces a max-cap repetition pathology. It does not prove language quality, semantic understanding, fluent chat, philosophy, author imitation, alignment, safety, A0 usefulness, benchmark progress, or meaningful answers.

The remaining failure is important: most improved outputs stop immediately after copying the raw prompt. That is better than looping, but it is not a good answer. Cycle 14 should add a native locally trained neural text head and evaluate it with held-out text loss plus raw output audits.
