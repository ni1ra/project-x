# Cycle 3 Mechanism — Learned Segment Generation

Date: 2026-05-13
Status: architecture lock (cycle 3 of v2_organic_substrate phase). REPO_CONTROL row co-lands at cycle close in #00f.

## Overview

Replace position-locked character emission with segment-typed emission. The brain's autoregressive generator picks, at each output position, between (a) emitting one more learned literal character, or (b) starting a copy span from a typed observation role. Mode selection is a *new dimension of the existing action space* — softmax over `(literal_char_K | start_copy_from_role_R)` — driven by the same learned context-feature → weight substrate that already drives literal emission. Once in copy mode, characters are read from the observation's filler at generate time (data-driven length, not authored). When the filler is exhausted, the generator returns to literal mode.

This is the minimum-mechanism-that-discriminates fix for the dominant cycle-2 failure pattern (12 of 16 cases are filler-copy: `unseen_filler` 10, `unseen_filler_long` 2). It honors manifesto §Builder Law because the mode-decision lives in learned softmax weights, not in authored `if role == X` branches.

## Reconnaissance Summary

- **Stack:** native C++20, single translation unit `native/organic_v0.cpp` (1856 lines), built with `g++ -std=c++20 -O3 -march=native -Wall -Wextra -pedantic`.
- **Runtime:** `make build/organic_v0`, harnessed by `scripts/{train,eval,test}_organic_v0.sh`.
- **Existing emission machinery (`OrganicBrain::generate` lines 601–662):**
  1. Encode input + observations into an HDC query vector
  2. Retrieve activated traces (similar trained events)
  3. Build feature list: `context_features(input, observations)` + trace-id features
  4. For each output position 0..`max_output_chars`:
     - Get active features = `state_features(features, previous_char, pos)`
     - For each feature: `scores[c] += feature.scale * connections_[feature.id].value[c]` for c in 0..kAscii
     - `add_slot_pass_scores(scores, slots, pos)` — existing position-locked slot bonus
     - Argmax over `scores[0..kAscii]`, emit chosen char or END
- **Existing slot pass-through (`learn_slot_pass_through` / `add_slot_pass_scores` lines 929–970):** learns absolute-position char bonuses during training; copies chars from typed observations at training-time positions during generate. This is *exactly* the failure mode — position 0 weight learns "char 'm'" from training trace "milaquart arch6" and at test time emits 'm' regardless of test observation `name:lina`.
- **State machinery:** `connections_` is `std::map<uint64_t feature_id, Weights{std::array<double, kAscii> value}>`. `slot_copy_weights_` is `std::map<uint64_t key, double weight>`. `state_hash` walks both, deterministically sorted by key, contributing to the bit-exact PXSTATE_V0 hash.
- **PXSTATE_V0 sections:** `CONFIG`, `TRACES`, `CONNS`, `SLOTS`, `LEARNED`, `STATE_HASH`. Hex64-of-IEEE-bits doubles for round-trip identity. Delimiter rules enforced fail-fast at write (`require_pxstate_scalar` / `require_pxstate_observation`).
- **The Core 10 collapses to the single .cpp:** entry/routing/data-models/core-logic/state/auth are all in one file. The Core 10 here is "the 10 functions of OrganicBrain" — `learn`, `generate`, `learn_slot_pass_through`, `add_slot_pass_scores`, `state_features`, `context_features`, `serialize_state`, `load_serialized_state`, `state_hash`, `retrieve`.
- **Constraint:** persistence pass-0 is law (#00e). Any new state must survive train → save → fresh-process load → generate with bit-exact `model_state_hash` + `raw_generated_output` match. `make test` enforces this via `scripts/test_organic_v0.sh`.

## The Problem (current emission)

```
position:   0   1   2   3   4   5   6   7   8   9  10  11  12  13  14  15  16
trained:    m   i   l   a   _   q   u   a   r   t   z   _   p   i   e   r   6
                                              (target: "mila quartz pier6")

connections_[feature(pos=0, prev=START, ctx)].value['m'] = +big (learned at training)
connections_[feature(pos=5, prev=' ', ctx)].value['q'] = +big
connections_[feature(pos=12, prev=' ', ctx)].value['p'] = +big
                ...

test event: name=lina, object=onyx, place=loft3 → expected "lina onyx loft3"

generate at pos=0: feature(pos=0, prev=START, ctx_test) — ctx_test partially overlaps
                   ctx_train (same composition shape). softmax picks 'm' (trained literal).
generate at pos=1: previous='m', pos=1 → picks 'i' (trained bigram).
                   ...
output: "milaquart arch6" (training literal mash-up, ignores test observation)
```

The fault is *position-bound character learning*. Characters inside a copy span (positions 0-3, 5-10, 12-16 in the example) should not have been learned as position-conditioned literals; they should have been learned as a single mode-switch action at the span START, with the chars supplied at generate time from the observation.

## The Mechanism (segment-typed emission)

Action space expands from `kAscii` literal-char actions to `kAscii + kMaxRoles` actions, where `kMaxRoles` is a small constant (8 in initial config — covers the observed role types `name`, `object`, `place`, `signal`, `topic`, `intent`, `effect`, `parity`).

```
expanded_action_id : meaning
0..kAscii-1        : emit ASCII character C
kAscii..kAscii+kMR : start copy-span from role-token R (R = action_id - kAscii)
```

The `connections_` map's `Weights` struct extends to carry `kAscii + kMaxRoles` weights per feature_id. The softmax at generate time picks the argmax over the full expanded space.

### Learn

During training, walk the `target_output` and detect substring matches against typed observation fillers. **Match precedence: longest filler wins; ties broken by observation-list order (earlier-listed role wins).** This avoids ambiguity when, e.g., `name="lin"` and `object="lina"` both prefix-match at the same position — `object="lina"` wins because its filler is longer; if both fillers are equal length, the first-listed observation's role wins.

```
pos = 0
while pos < len(target):
    matched_role = find_observation_filler_matching_at(target, pos, observations)
    if matched_role is not None:
        # Learn: at this position+context, the action is "switch to copy-from-role:matched_role"
        for feat in state_features(features, previous, pos):
            connections_[feat.id].value[kAscii + role_id(matched_role)] += reward * feat.scale * lr
        pos += len(filler_of(matched_role))
        previous = filler_of(matched_role).back()
    else:
        # Existing per-char learning for the literal at this position
        c = target[pos]
        for feat in state_features(features, previous, pos):
            connections_[feat.id].value[c] += reward * feat.scale * lr
        pos += 1
        previous = c
# END token learned as before
```

When `use_segment_mode == true`, `learn_slot_pass_through` is bypassed (the legacy per-position-char slot bonus is replaced by the mode-switch). When `use_segment_mode == false`, code falls back to legacy emission for bit-exact reproducibility of cycle-2 results.

### Generate

```
in_copy_mode = false
copy_role = ""
copy_filler = ""
copy_pos = 0
previous = kStart
pos = 0

while pos < max_output_chars:
    if in_copy_mode:
        # Emit next char of the bound filler
        c = copy_filler[copy_pos]
        gen.output.push_back(c)
        copy_pos += 1
        previous = c
        if copy_pos == len(copy_filler):
            in_copy_mode = false
        pos += 1
        continue

    # Score all actions: literal chars + role-switches
    scores = zeros(kAscii + kMaxRoles)
    for feat in state_features(features, previous, pos):
        for action_id in 0..kAscii+kMaxRoles:
            if connections_[feat.id].value[action_id] != 0:
                scores[action_id] += feat.scale * connections_[feat.id].value[action_id]

    # GUARDRAIL: before argmax, zero out mode-switch actions whose target role has
    # no value in the current observations. This prevents a "phantom mode-switch"
    # that fires and then dead-ends. The zeroing happens BEFORE the !any check
    # so that all-zero scores (no literal + no reachable mode-switch) emits END
    # gracefully rather than break-mid-output.
    for role_idx in 0..kMaxRoles:
        role = role_token_table[role_idx]
        if observation_value_for_role(role, observations).empty():
            scores[kAscii + role_idx] = 0

    # any-score check (analog of existing line 632 `if (!any) break;`):
    # if every score in the expanded space is zero, emit END deliberately
    # instead of breaking. This is graceful degradation, not a parser-dispatcher
    # — END is a learned token in the existing action space, just one whose
    # weight happens to be the only viable one in the all-zero edge case.
    if all(scores[a] == 0 for a in 0..kAscii+kMaxRoles):
        emit END; break

    action = argmax(scores)
    if action < kAscii:
        # Literal emission (existing behavior)
        c = action
        if c == kEnd: break
        gen.output.push_back(c)
        previous = c
        pos += 1
    else:
        # Mode-switch: start copy from role R. The guardrail above guarantees
        # the role HAS a filler in the current observation, so this branch
        # never enters with an empty copy_filler.
        role = role_token_table[action - kAscii]
        copy_filler = observation_value_for_role(role, observations)
        in_copy_mode = true
        copy_role = role
        copy_pos = 0
```

The mode-switch is *learned*: which features at which positions vote for `kAscii + role_id` vs literal chars is entirely encoded in `connections_[feat.id].value[]` weights. No code anywhere reads `role:name` and decides "if role:name is present and we're at position 0, copy" — the decision emerges from softmax over learned weights.

### Builder-Law Invariant (load-bearing)

The mode-switch must live in the same softmax-over-learned-weights process that drives literal emission. The substring-match in `learn` and the empty-filler guardrail in `generate` are exempt — see "Builder-Law boundary call" below for the explicit argument. Concrete pre-commit grep:

```bash
grep -nE 'if .* role|if .* observation|if .* domain' native/organic_v0.cpp \
  | grep -vE 'learn_segment|substring|matched_role|observation_value_for_role|filler.empty'
# expected: zero matches outside the explicit allow-list
```

If this grep returns anything beyond the named exceptions, the mechanism has slid into parser-dispatcher territory and must RCT.

### Builder-Law boundary call — the load-bearing manifesto question

The cycle-3 ship hinges on whether the substring-match-against-fillers in `learn()` counts as:

- **(a) training-loop machinery / supervision-signal routing** — *allowed* under manifesto §Builder Law: "training loops, data pipelines and artifact logging" are explicitly permitted machinery. The substring-match identifies which training output spans correspond to which typed observation, then routes the supervision signal to mode-switch weights instead of per-char weights. At generate time, the brain has NO substring-match access — emission is entirely from learned softmax weights. This is the same kind of architectural choice as autoregressive emission (left-to-right) or reward-gating (skip unrewarded events): an architectural shape, baked into training, not an authored answer.

- **(b) authored inductive bias on the answer path** — *forbidden* under manifesto §Builder Law: "trigger lists that impersonate understanding" are forbidden. The substring-match encodes the bias "fillers in observations are copied verbatim into outputs", which IS an authored inductive bias. If this counts as authored-answer-machinery, the entire mechanism is manifesto-violating.

**My argument for (a):**
1. The substring-match does NOT fire at generate time. At generate time, the brain emits via softmax over `connections_[feat.id].value[action]` — pure learned weights. The substring-match is invisible at inference.
2. The substring-match in learn() does not produce an answer; it routes a supervision signal to a different weight location. Compare: a masked-language-model training loop "knows" which tokens to mask — that's training-time machinery, not an authored answer at inference.
3. The bias "fillers are copied verbatim" is empirical in the training data — the benchmark's training events have target outputs that DO contain the fillers verbatim. The training loop is recognizing structure that already exists in the data, not imposing a structure that doesn't.
4. Without this kind of training-loop machinery, the manifesto's stated component list (encoders, plasticity rules, reward mechanics, sandbox boundaries) is impossible to implement — *all* of those involve some authored decision about how supervision signals route through the substrate.

**Counter-argument for (b):**
1. The substring-match encodes domain knowledge ("typed observations have fillers; outputs use them"). A more honest approach would let the brain discover this pattern via correlation, not via authored matching.
2. The mode-switch weights are seeded by an authored decision; they're not learned from "raw data + reward" alone.
3. This is closer to a parser than I'd like — even if it only fires at training time.

**Why this question must be answered BEFORE #10 (implementation):** if advisor rules (b), I pivot to candidate B (HDC unbinding + cleanup memory) before any code lands. The HDC unbind+cleanup mechanism has no authored substring-match — characters are bound at observation-encoding time via `bind(filler:F, bind(pos:n, char:c))` (a structural encoding choice, but not a substring-match), and retrieved at generate-time via principled HDC unbind operations. The pivot is cheap NOW; expensive after.

**The advisor() call below frames this question explicitly. Verdict (a) → proceed with A. Verdict (b) → pivot to B; rewrite this doc; re-run /pick-one with the boundary ruling in hand.**

## PXSTATE_V0 Schema Extension

Add NEW SECTION MARKERS (per corpse hard-gate "extend with new sections, don't overload existing"):

```text
ROLES <n>
R <role_id_hex64> <role_string>
SEGMENT_CONNS <n>
SC <feature_id_hex64>|<role_id_hex64>:<weight_hex64>,<role_id_hex64>:<weight_hex64>,...
```

- `ROLES` section catalogs the role-token table: stable hash of role-string → role-string. Loaded into `role_token_table_`. Empty table OK; runtime grows it as new role types appear in training.
- `SEGMENT_CONNS` section: per-feature mode-switch weights, sparse format (only non-zero weights serialized). Mirrors `CONNS` shape but keyed by `(feature_id, role_id)`.
- `CONFIG` section gains `use_segment_mode=1` and `max_roles=16` and `segment_mode_gain=<hex64>` fields. Backwards-compat: missing `use_segment_mode` defaults to `0` (legacy emission).
- **`kMaxRoles` overflow behavior:** `kMaxRoles = 16` is a compile-time cap. Current tightened benchmark exposes ~6 distinct role types (`name`, `object`, `place`, `signal`, `topic`, `intent`); 16 provides ~10 slots headroom. If a 17th unique role string is encountered during training, `role_id_for_string()` THROWS `std::runtime_error("role table exhausted at kMaxRoles=16; bump constant and recompile — serialized state remains forward-compatible because role_id is a stable hash")`. Detection is fail-fast at registration, NOT silent overflow. Bumping `kMaxRoles` is a one-line constant change; serialized state survives because `role_id` is a stable `fnv1a` hash, not an index.
- **`state_hash` sort key for ROLES section:** sort by `role_id` (the uint64_t hash), not registration order, so deterministic across processes.
- Delimiter rules extend: role strings cannot contain `|` (validated via `require_pxstate_scalar("role.string", ...)` at write).
- `state_hash` extends: after the existing `slot_copy_weights_` walk, walk `role_token_table_` (sorted by role_id) and `segment_connections_` (sorted by feature_id then role_id) and combine their contributions into `h`. Bit-exact round-trip requires this.

When `use_segment_mode == 0`, the new sections may be absent (legacy save). The new `state_hash` walks are GATED behind `if (config_.use_segment_mode)` — without the gate, `combine(h, 0)` is NOT a no-op (see `combine` line 139: `mix64(a ^ mix64(b + 0x9e3779b97f4a7c15ull))` transforms `h` even when `b == 0`), so unconditionally walking empty containers would still alter the hash. With the gate, `use_segment_mode == 0` reproduces cycle-2 `state_hash` (`3536309de837d3e2`) bit-exactly. With the gate active, cycle-2 saved state loads as `use_segment_mode == 0` automatically (CONFIG section drives the flag) and the hash stays compatible.

## Integration Points in `OrganicBrain`

| Method | Change |
|---|---|
| `Config` (line 32-46) | + `bool use_segment_mode = true`, `int max_roles = 8`, `double segment_mode_gain = 5.0` |
| `Weights` (line 114-116) | `std::array<double, kAscii>` → `std::array<double, kAscii + kMaxRoles>` (compile-time constant kMaxRoles = 8); zero-initialized so legacy CONNS weights still index `[0..kAscii-1]` cleanly |
| `learn()` (line 559-599) | When `use_segment_mode`: walk target with substring-match-against-observation-fillers; emit mode-switch learning at span starts, literal char learning at separators. Else: legacy per-char learning. |
| `learn_slot_pass_through()` (line 929-945) | Add early-return `if (config_.use_segment_mode) return;` — bypassed when segment mode is active |
| `generate()` (line 601-662) | Replace per-position scoring with the segment-mode state machine described above. Existing `add_slot_pass_scores` still called when `!use_segment_mode` |
| `state_hash()` (line 664-694) | After `slot_copy_weights_` walk, append `role_token_table_` walk + `segment_connections_` walk. Sorted, deterministic. |
| `serialize_state()` (line 713-790) | + `ROLES` section, + `SEGMENT_CONNS` section. Delimiter validation on role strings. |
| `load_serialized_state()` (line 792-870) | + `ROLES` parser, + `SEGMENT_CONNS` parser. Backwards-compat: tolerate absence of these sections (sets `use_segment_mode=false`). After load, recompute `state_hash` and verify against stored. |
| `Generation` struct (line 104-112) | + `size_t segment_mode_switch_count = 0` field for evidence in artifacts |
| `GenerationStep` (line 95-102) | + `bool is_mode_switch = false`, + `std::string copy_role` (when is_mode_switch is true) — preserved in artifact for failure_cases inspection |

## Dependency Graph

Mode-decision **reads** (existing state):
- `connections_[feat.id].value[kAscii..kAscii+kMaxRoles]` — new mode-switch weights, but indexed via existing feature_id space
- `state_features(...)` — unchanged feature-extraction
- `context_features(...)` — unchanged

Mode-decision **writes** (new state):
- `role_token_table_` — registry of role strings encountered during training (grows monotonically)
- `connections_[feat.id].value[kAscii..]` — populated by `learn_segment_mode` analog

Generate-time **reads** (existing observation data):
- `parse_slots(observations)` — already exists, returns typed observation slots
- `observation_value_for_role(role, observations)` — new helper, returns filler string or empty

## Substrate Honesty Walk-Throughs

**Case 1: `mem_test_001` — name=mila, object=quartz, place=pier6 → "mila quartz pier6"** (training event)

`learn()`:
- pos=0: substring "mila" matches obs[name].value → learn mode-switch=role:name at (pos=0, prev=START, ctx). pos += 4, previous = 'a'.
- pos=4: target[4]=' ', no filler match → learn literal ' ' at (pos=4, prev='a', ctx). pos += 1, previous = ' '.
- pos=5: substring "quartz" matches obs[object].value → learn mode-switch=role:object. pos += 6, previous = 'z'.
- pos=11: literal ' '. pos += 1.
- pos=12: substring "pier6" matches obs[place].value → learn mode-switch=role:place. pos += 5.
- pos=17: END.

`generate()` on same event: mode-switch fires at pos=0,5,12; copy mode emits "mila"/"quartz"/"pier6" verbatim from observation values; literal mode emits separators ' '. Output: "mila quartz pier6". MATCH.

**Case 2: `mem_test_001` analogue — name=lina, object=onyx, place=loft3 → expected "lina onyx loft3"** (unseen-filler test)

The training-learned mode-switch weights for `(pos=0, prev=START, ctx)` are conditioned on context features that include input-shape + activated-trace similarity, NOT on the literal filler string. The test event has the same composition shape as training events; mode-switch weights transfer.

`generate()`: at pos=0, mode-switch=role:name wins. copy mode reads "lina" (4 chars) from test obs[name].value. pos advances to 4. At pos=4, literal ' ' wins. At pos=5, mode-switch=role:object wins; copy "onyx" (4 chars). pos=9, literal ' '. pos=10, mode-switch=role:place; copy "loft3". Output: "lina onyx loft3". MATCH.

**Case 3: `mem_test_004` — name=tavi, object=marble, place=lantern6 → "tavi marble lantern6"** (unseen-filler-long, length variance)

Same as Case 2. The filler lengths are read from the observations at generate time. copy mode emits *all* chars of the bound filler (4, 6, 8), independent of training filler lengths. Output: "tavi marble lantern6". MATCH.

**Case 4: `lang_test_004` — intent:farewell name:elena → expected "bye elena"** (intent_transfer)

This is the hardest case. The model must learn that the literal prefix is conditioned on intent. Training events have `intent:greeting → "hi <name>"` and `intent:farewell → "bye <name>"`. The literal-prefix-vs-intent association is in the context features (intent atom is part of `context_features(input, observations)`).

`learn()` on training `intent:greeting name:lina → "hi lina"`:
- pos=0: target[0..1]="hi", no filler match (intent:greeting has no filler-by-name lookup). Learn literal 'h' at (pos=0, prev=START, ctx_with_intent_greeting). pos += 1.
- pos=1: literal 'i'. pos += 1.
- pos=2: literal ' '. pos += 1.
- pos=3: substring "lina" matches obs[name].value → learn mode-switch=role:name. pos += 4.
- pos=7: END.

`learn()` on training `intent:farewell name:sora → "bye sora"`:
- pos=0: literal 'b' at (pos=0, prev=START, ctx_with_intent_farewell). pos += 1.
- pos=1: literal 'y'. pos += 1.
- pos=2: literal 'e'. pos += 1.
- pos=3: literal ' '. pos += 1.
- pos=4: substring "sora" matches → mode-switch=role:name. pos += 4.
- pos=8: END.

`generate()` on test `intent:farewell name:elena`:
- pos=0: scores at (pos=0, prev=START, ctx_with_intent_farewell) — connections learned 'b' as the literal that wins under ctx_with_intent_farewell. argmax → 'b'. Emit.
- pos=1: previous='b', pos=1, ctx — connections learned 'y' bigram. Emit.
- pos=2: 'e'. Emit.
- pos=3: ' '. Emit.
- pos=4: mode-switch=role:name wins (learned under similar ctx). copy "elena" (5 chars). Output: "bye elena". MATCH.

This case ALSO demonstrates the test that the mechanism is honest: nothing in the code says "if intent:farewell then prefix='bye'". The intent atom is just another feature; the literal 'b' wins because the connection weight at `(pos=0, prev=START, ctx_with_intent_farewell).value['b']` was reinforced by training events with that ctx.

## advisor() Review Checkpoint

**Before any C++ touch in #10 (#00c.3 implementation):** call `advisor()` with this document as the input artifact. The advisor sees:

- The mechanism design above
- The integration points (which methods change, which are unchanged)
- The PXSTATE_V0 schema extension shape
- The Builder-Law invariant + grep check
- The substrate honesty walk-throughs

Pass description: *"BLUEPRINT VALIDATION — cycle 3 segment-mode mechanism. Review: (1) does the action-space expansion preserve the substrate's honest learning, or does it slide into authored capability? (2) does the substring-match-in-learn count as data inspection (honest) or as authored heuristic (manifesto-violating)? (3) is the empty-filler fallback in generate a guardrail or a parser-dispatcher? (4) does the PXSTATE_V0 extension survive backwards-compat (legacy state without ROLES/SEGMENT_CONNS sections still loads)? (5) is `kMaxRoles=16` adequate or arbitrary? Score 1-420. Identify single weakest section. Be harsh."*

Files to include: this document + `native/organic_v0.cpp` + `docs/MANIFESTO.md` + `docs/artifacts/PERSISTENCE_SCHEMA.md`.

**Gate logic per design-before-build skill:**
- Score < 380 → revise this doc on disk, re-validate. Max 3 revision cycles.
- 380-399 → proceed with caution; apply advisor's targeted suggestions.
- ≥ 400 → proceed to #09 schema extension + #10 implementation.

## Implementation Plan (Phase 4 — atomic steps)

Step granularity: each step verifiable, time-boxed under ~20 min Raphael-time, with explicit Verify + Risk + Rollback.

### Phase 4.1 — Foundation
- [ ] **Step 1: Extend `Config` + `Weights`** — File: `native/organic_v0.cpp` ~lines 32-46 + 114-116. Add `use_segment_mode`, `max_roles=8`, `segment_mode_gain`. Expand `Weights::value` to `std::array<double, kAscii + kMaxRoles>`. **Verify:** `make clean && make` — zero warnings. **Risk:** LOW. **Rollback:** revert `git diff native/organic_v0.cpp`.
- [ ] **Step 2: Add role-token registry + helpers** — `role_token_table_`, `role_id_for_string(s)`, `observation_value_for_role(role, obs)`. **Verify:** unit-tested via brain self-test that exercises a fake role. **Risk:** LOW.

### Phase 4.2 — Learn
- [ ] **Step 3: Implement substring-match-and-segment-learn loop** — Extend `learn()` with the `find_observation_filler_matching_at` walk. Bypass `learn_slot_pass_through` when `use_segment_mode`. **Verify:** train on benchmark, inspect `connections_` for mode-switch weights at expected positions. **Risk:** MEDIUM (off-by-one in pos advance). **Rollback:** disable `use_segment_mode` config flag — restores legacy path bit-exactly.

### Phase 4.3 — Generate
- [ ] **Step 4: Implement segment-mode generator** — Replace inner loop of `generate()` with the in_copy/literal-mode state machine. **Verify:** generate on a training event, output bit-exactly matches target. **Risk:** MEDIUM (state-machine bugs). **Rollback:** disable `use_segment_mode`.
- [ ] **Step 5: Empty-filler graceful degradation** — When mode-switch fires for a role not in current observations, zero its score and re-argmax. **Verify:** generate on a test event missing a role; mechanism emits literal alternative without crashing. **Risk:** LOW.

### Phase 4.4 — Persistence
- [ ] **Step 6: PXSTATE_V0 `ROLES` section** — Extend `serialize_state` + `load_serialized_state`. Delimiter validation on role strings. **Verify:** save → load → state_hash match. **Risk:** MEDIUM (parse-error edge cases).
- [ ] **Step 7: PXSTATE_V0 `SEGMENT_CONNS` section** — Same shape as CONNS but keyed by (feature_id, role_id). **Verify:** save → load → state_hash match on a brain with non-zero mode-switch weights. **Risk:** MEDIUM.
- [ ] **Step 8: Extend `state_hash` to include new sections** — Sorted-key walks, deterministic. **Verify:** `make test` — persistence round-trip emits bit-exact hash + output. **Risk:** MEDIUM (hash bugs are silent — they only fire on load). **Rollback:** revert hash extension; reverts to cycle-2 hash but breaks new-state round-trip.

### Phase 4.5 — Verify
- [ ] **Step 9: Clean build + substrate self-test** — `make clean && make` zero warnings. `build/organic_v0 --phase self-test` emits "zx". **Verify:** existing self-test output unchanged. **Risk:** LOW.
- [ ] **Step 10: Persistence round-trip** — `make test` green. **Verify:** "substrate guard OK" + "persistence round-trip OK (hash <X> match, output <Y> match)". **Risk:** LOW (Step 8 already proved this).
- [ ] **Step 11: Eval on tightened benchmark** — `build/organic_v0 --phase train+eval --data benchmarks/v2_ladder/organic_v0.jsonl --save-state ... --out run/artifacts/organic-v0/eval_compositional_v2c3.json`. **Verify:** `jq '.summary_metrics + .summary_metrics.by_composition'` shows deltas vs cycle-2 baseline. **Risk:** MEDIUM (mechanism may underperform; valid outcome but requires honest report).

## Dependency Graph (Phase 5 — topological)

### Layer 0 (no dependencies)
- Step 1: Extend Config + Weights

### Layer 1 (depends on Step 1)
- Step 2: Role-token registry + helpers

### Layer 2 (depends on Step 2)
- Step 3: Learn extension

### Layer 3 (depends on Step 3) — PARALLEL with Step 5
- Step 4: Generate extension
- Step 5: Empty-filler fallback

### Layer 4 (depends on Step 4)
- Step 6: PXSTATE_V0 ROLES section
- Step 7: PXSTATE_V0 SEGMENT_CONNS section (parallel with Step 6)
- Step 8: state_hash extension (depends on Steps 6+7)

### Layer 5 (depends on Step 8)
- Step 9: Clean build + self-test
- Step 10: Persistence round-trip (depends on Step 9)

### Layer 6 (depends on Step 10)
- Step 11: Eval on tightened benchmark

**Critical path:** 1 → 2 → 3 → 4 → 6 → 8 → 9 → 10 → 11 (9 steps, ~90 min Raphael-time)
**Parallel opportunities:** Steps 4+5 within Layer 3; Steps 6+7 within Layer 4
**Orphan check:** all 11 steps accounted for; no disconnected nodes ✓

## Acceptance Criteria (Phase 6)

### Functional
- [ ] `make clean && make` succeeds with zero warnings under `-Wall -Wextra -pedantic -std=c++20 -O3 -march=native`.
- [ ] `make test` green: substrate self-test prints "organic-v0 native self-test OK" AND persistence round-trip prints "persistence round-trip OK (hash <X> match, output <Y> match)".
- [ ] Eval on tightened benchmark with `use_segment_mode=true` shows MATERIAL lift on at least one of: `unseen_filler` (currently 0/8), `unseen_filler_long` (currently 0/2), `intent_transfer` (currently 0/1). "Material" = at least 3/8 on unseen_filler, OR at least 1/2 on unseen_filler_long, OR 1/1 on intent_transfer.
- [ ] No regression on `direct_replay` (currently passing), `evidence_absence` (currently passing), `unseen_rule_transfer` (currently failing but at its honest baseline).
- [ ] Raw bad outputs preserved in `failure_cases` array of eval artifact.
- [ ] Eval-from-disk artifact diff-clean against eval-from-JSONL on `summary_metrics + by_composition + model_state_hash`.

### Non-functional
- [ ] `git diff --check` clean.
- [ ] `grep -nE 'if .* role|if .* observation|if .* domain' native/organic_v0.cpp` returns only allow-listed matches (Builder-Law invariant).
- [ ] No new dependencies; remains single-TU C++20.
- [ ] Dynamic comments density: WHAT/WHY/NEGATIVE-SPACE on each new function and on each non-trivial code path.

### Test → Step Mapping

| Test | Verifies Step(s) | AC |
|---|---|---|
| `make` zero warnings | Step 1 | "build clean under -Wall -Wextra -pedantic" |
| `build/organic_v0 --phase self-test` | Step 9 | "substrate self-test prints zx" |
| `make test` round-trip | Steps 6-8, 10 | "persistence round-trip hash + output match" |
| Eval on tightened benchmark | Step 11 | "material lift on filler-copy" |
| `grep` Builder-Law check | Steps 3, 4, 5 | "Builder-Law invariant satisfied" |
| diff-clean eval-from-disk vs eval-from-JSONL | Step 10 | "summary_metrics identical" |

## Risk Assessment (system-level)

| Risk | Likelihood | Impact | Cascade | Mitigation |
|---|---|---|---|---|
| Mode-switch weights don't generalize across train/test | Medium | High (cycle 3 ships with no measured lift) | #00d fails | Honest report; the failure case IS evidence; cycle 4 considers alternative mechanism |
| Substring-match in learn miscounts position advance | Medium | High (bit-exact hash breaks; round-trip fails silently in eval) | #00e gate fails | Step 8 hash extension catches it; explicit unit-style assertion in Step 9 self-test |
| `kMaxRoles=16` is undersized for benchmark | Low | Medium | Some mode-switches truncated | Compile-time constant; bump to 16 if benchmark trips it; preserved as the easiest knob |
| Builder-Law invariant slides during implementation | Medium | CRITICAL (manifesto violation) | Whole mechanism becomes invalid even if benchmark lifts | Pre-commit grep check (in #00f); RCT triggers immediately on first match |
| PXSTATE_V0 backwards-compat breaks cycle-2 artifacts | Low | High | Legacy artifacts orphaned | Missing ROLES/SEGMENT_CONNS sections tolerated by loader; `use_segment_mode=0` reproduces cycle-2 hash bit-exactly |
| Empty-filler fallback emits garbage instead of literal | Low | Medium | Test events with missing roles fail noisily | Empty-filler path zeros mode-switch score and re-argmaxes literal alternatives; tested in Step 5 |
| Cycle horizon spills past ~120 min | Medium | Low (lain explicitly authorized cycle 3 as the structural cycle) | None — cycle 4 absorbs spillover | Honest reporting; preserve work-in-progress on branch |

## Pre-mortem Watchlist (for #00d eval phase)

When measuring at Step 11, watch for:

1. **`unseen_filler` lift > 0/8 but `direct_replay` regression.** This means the mode-switch fires when it shouldn't (false-positive in learn's substring matcher). Mitigation: tighten substring-match to require *exact* span match, not partial.
2. **`unseen_filler` lift 0/8.** Mode-switch weights didn't generalize. Three possible causes: (a) trained mode-switch was conditioned too narrowly on training-only features (e.g., trace-id), (b) `kMaxRoles=16` truncated needed roles, (c) the substring-match miscategorized some training events. Diagnostic: inspect `connections_` for mode-switch weights at trained positions; verify mode-switch weights are non-zero in the right cells.
3. **State hash collisions across save/load.** Step 8 should catch this; if it doesn't, the new `state_hash` walks have an ordering bug. Mitigation: explicit ordering test in Step 9.
4. **`intent_transfer` lift but `evidence_present` regression.** Means the literal-prefix learner became too aggressive. Likely OK at cycle 3; cycle 4 would balance via plasticity controller.

## Retrospective (Phase 7 — to be logged at cycle 3 close)

To be appended to `Project X Session Mistakes` wiki (created on first logged curse if not yet existing) at cycle close, in dev-cycle-3.md reflection:

```
2026-05-13 — Blueprint: cycle 3 segment-mode mechanism
Assumed: [TBD at cycle close — fill in what was assumed in architecture]
Found:   [TBD — what advisor flagged + what implementation surfaced]
Delta:   [TBD]
Lesson:  [TBD — actionable for cycle 4]
```

---

**Status:** architecture lock. Awaiting advisor() validation before #00c.2 (#09) PXSTATE schema work begins.
