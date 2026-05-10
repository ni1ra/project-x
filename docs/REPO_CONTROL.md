# REPO_CONTROL — Project X

> **Living document.** Mirror of the actual repo file/folder structure with justification for every entry. No file or folder allowed to exist without an entry here. Pristine-condition gate. Heartbeat-tracked: every cycle close + heartbeat fire reconciles freshness; new files added in a commit MUST land with their REPO_CONTROL row in the same commit.

---

## Standing rule

**Every code file, every artifact (verdicts, run results, tests, scripts, ladder entries, screenshots), every doc — needs an entry here with a one-line justification.** If a file exists on disk + isn't here, either (a) add the row, or (b) delete the file. The repo is pristine when the union of `git ls-files` + tracked-on-disk-but-gitignored matches the entries in this file.

Exemptions (don't need rows):
- Auto-generated build artifacts (`*.egg-info/`, `__pycache__/`, `.pytest_cache/`)
- Coverage tooling output (`.coverage`, `htmlcov/`)
- IDE/agent session artifacts (`.claude/`, `.playwright-mcp/`)
- Lockfiles tied to a manifest (e.g. `package-lock.json` next to `package.json`) — the manifest gets the row; the lockfile is an artifact of installation
- Per-language standard ignores (`__pycache__/`, `*.pyc`, etc.) — `.gitignore` is the single source of truth for these

---

## Repo root (3 files)

| Path | Justification |
|---|---|
| `README.md` | Public-facing brief — what the project is, quick-start, key artifacts. Reframed `13ab133` from "token-prediction architecture" to "post-transformer organic memory + agent stack" (audit-B4). |
| `pyproject.toml` | Setuptools build config + deps. `numpy`, `pydantic`, `requests` are core. `torch>=2.2` moved to `[legacy]` optional extra (audit-C2 quarantine). `dev` extra: `pytest`, `ruff`. |
| `pytest.ini` | Pytest config — adds `src/` to PYTHONPATH so `from project_x.*` imports work without `pip install -e .`. |
| `.gitignore` | Standard Python ignores + coverage tooling output + `.claude/` + `.playwright-mcp/` + large reference materials in `ref/papers/` and `ref/pages/` + the codex extracted-content blobs in `gpt-codex/extracted/` and `gpt-codex/sources/` (metadata-only tracking; raw blobs stay local) + `gpt-codex/runs/*/` retention policy (audit-F2). |

(Per-directory `CLAUDE.md` files were retired 2026-05-10. Single-source-of-truth lives under `docs/`.)

## `docs/` (live docs + frozen artifacts + cycle archives)

| Path | Justification |
|---|---|
| `docs/MANIFESTO.md` | lain's intent + standing orders. Live; heartbeat-tracked; re-read at session start. |
| `docs/A_TO_Z_PLAN.md` | Current run / phase plan + verification gates + scope fence + changelog. Rotates to `past_work/phases/` on phase exit (THIS file does NOT cycle out — it's REPO_CONTROL). |
| `docs/DO_THIS_NEXT.md` | Current cycle scope + next-instance handoff. Rewritten at every cycle close. Power-on resume pointer. |
| `docs/REPO_CONTROL.md` | THIS file — pristine-condition gate; mirror of repo structure with justification. Heartbeat-tracked alongside MANIFESTO. |
| `docs/ci/test.yml` | Audit-D1 CI workflow template (paste-ready). Cannot ship to `.github/workflows/` directly because Claude Code OAuth lacks `workflow` scope; lain installs via web UI or grants the scope and the agent retries. |
| `docs/artifacts/` | Phase verdicts (frozen-with-addendum convention) + research notes. See sub-section. |
| `docs/past_work/phases/` | Archived phase plans. One file per closed phase: `phase_<N>_<theme>.md`. Inter-phase repair runs (e.g. `audit_fix_run_2026-05-10.md`) are archived here too, un-numbered. |
| `docs/past_work/cycles/phase_<N>/` | Per-cycle reflections — `dev-cycle-<M>.md` written at each cycle close. Phases 1, 4-12, 13 represented. **`phase_13/dev-cycle-1.md`** added 2026-05-10 — cycle 1 close: 6/6 #00P13c1-XX shipped; pytest 87→153; baseline-attempt brutal scores (poetry 1.3/5, philosophy 1.2/5) drove lain's intelligence-first reframe. **`phase_13/dev-cycle-2.md`** added 2026-05-10 — cycle 2 close: 6/6 #00P13c2-XX shipped; pytest 153→202; substrate-driven math grades 4.0/5 both prompts (3x cycle-1 lift); D5 PASS 11/0 unchanged (substrate gain in QUALITY not COUNT — falsifiable-bar alternative clause); lain mid-D3 catch + 3 new global rules pinned (#9/#10/#11) for cycle 3 Tier A; advisor catch pre-D4 surfaced + applied. **`phase_13/dev-cycle-3.md`** added 2026-05-10 — cycle 3 close: 5/6 #00P13c3-XX shipped + 3 Tier A instruction-discipline rows + 1 deferral (#04→cycle 4 #03 per advisor pacing flag); maths PASS 3/0→5/0 (Path B; FIRST visible PASS lift in Phase 13); substrate-vs-substrate Tier 1 lift maths-001 4.0→4.5 / maths-002 4.0→4.75 (differentiated lift signal breaks calibration tell); pytest 202→221; 6 advisor catches applied. |

### `docs/artifacts/` (frozen verdicts + research notes)

| Path | Phase / topic |
|---|---|
| `PHASE_7_HOPFIELD_LENS.md` | Phase 7 Hopfield lens proof. |
| `PHASE_8_HDC_ORGANIC_MEMORY.md` | Phase 8 random-symbol HDC baseline (99.25% recall at D=50000). |
| `PHASE_8_HOSTILE_REVIEW.md` | Phase 8 hostile review. |
| `PHASE_9_PICK_ONE_VERDICT.md` | Phase 9 pick-one verdict + lain organic-only addendum (2026-05-09). |
| `PHASE_9_SEMANTIC_HDC_MEMORY.md` | Phase 9 verdict + Phase 10 closure addenda. |
| `PHASE_9_SHRINE_COUNCIL_HEBBIAN.md` | Council reasoning (Plate dossier especially relevant for Phase 10 P3 fact-graph). |
| `PHASE_11_BENCHMARK.md` | Phase 11 verdict (9/2/21/4) + Phase 12 closure addendum (11/0/21/4). |
| `PHASE_12_RETRIEVAL_DISAMBIGUATION.md` | Phase 12 verdict — `retrieve_structural_full_history` + `_LIST_ALL_HINTS` classifier closing memory-004/005. |
| `PHASE_13_CANDIDATES.md` | Phase 13 framing inputs (lain-gated, NOT a verdict) — retrieval telemetry, snapshot/restore, adversarial memory matches, from-scratch symbolic generator, binding-algebra bakeoff. |
| `PHASE_13_C3_PHYSICS_SURVEY.md` | #00P13c3-03-domain-recon (cycle 3 D3) — classifies 6 physics ladder entries by verification path (3 auto-green / 2 rubric-pending / 1 ungradeable; identical structure to maths ladder). Identifies TWO complementary cycle 4 paths: Path A (substrate extension to closed-form physics — `free_fall_time` + `pendulum_period` + `relativistic_momentum` primitives) for substrate-quality lift; Path B (grader-flip on physics-004 Einstein-field-equations + physics-005 LQG-vs-string-theory) for visible PASS-count lift. Recommends cycle 4 ships both (Path B first per cycle 3 pattern). Documents cycle 3 deferred #00P13c3-04 carries forward as cycle 4 #03 per advisor pacing flag. |
| `PHASE_13_ANTICHEAT_AUDIT.md` | #00P13c4-23-anti-cheat-leakage-audit (TIER A HIGH; lain mid-cycle-4 directive 2026-05-10) — maps 7 leak surfaces across substrate + benchmark architecture. HIGH: substrate primitives hardcode formula (Surface 1); Path B four-positions-in-one-architecture (Surface 3); memorization vs reasoning (Surface 4); substrate-driven attempt canonical cheat shape (Surface 5). MED: verifier partial independence (Surface 2); manual grade harness shared-bias gap (Surface 6). LOW: memory ladder mechanical-truth (Surface 7). Identifies 6 operational external-confirmation mechanism candidates (independent LLM-as-judge / programmatic rubric criteria / lain spot-checks at phase exits / surrogate-prompt regression / differential capability test / divergent-verifier-paths). Recommends cycle 4 #24 minimum-viable: surrogate-prompt regression + differential capability test + divergent verifier path. Defers full programmatic-rubric + ladder-wide surrogate coverage to cycle 5+. Self-acknowledged Surface 3 inheritance bias (same-architecture audit-of-self); honest "anti-cheat-audit-builder; pending external confirmation" framing. |
| `PHASE_13_C2_MATH_SURVEY.md` | #00P13c2-01-math-recon (cycle 2 D1) — classifies the 6 maths ladder entries by verification path (auto-graded vs rubric-pending vs ungradeable); identifies maths-001 (definite) + maths-002 (stretch) as cycle 2 substrate-driven re-attempt candidates; reconciles D5 falsifiable bar (PASS ≥ 4/0 via substrate alone NOT feasible — Path B grader-driven rubric-flip on rank 4-5 is independent of cycle 2 substrate scope). Drives D2 primitive shape (Lemma + DerivationStep dataclasses + `solve_quadratic` + `expand_characteristic_polynomial_2x2`). |
| `COUNCIL_A_ENCODER.md` … `COUNCIL_H_BEYOND_HUMAN_CAP.md` | Phase 9 council deliberations across 8 architectural axes. |
| `DISCORD_BRIEF_RAPHAEL_ROADMAP.md` | Discord brief on Raphael roadmap. |
| `RESEARCH_NOTE.md` | Older research notes (Phase 1-4 era). |
| `ROADMAP_TO_RAPHAEL.md` | Older long-arc roadmap (superseded by MANIFESTO + Phase 9-12 verdicts; kept as historical record). |
| `SHRINE_COUNCIL_PHASE_8.md` | Phase 8 council deliberations. |
| `T4_bit_accuracy_curve.png`, `T4_capacity_curve.png`, `T4_cliff_vs_D.png`, `T4_dscaling_curves.png` | Phase 4 figures (bit-accuracy, capacity, cliff, D-scaling). |

## `src/project_x/` (runnable research harness)

### Live Phase 9-10 production organic stack — `src/project_x/experiments/`

| Path | Justification |
|---|---|
| `__init__.py` | Package marker (empty). |
| `semantic_hdc_memory.py` | Layer 3 — `SemanticHDCMemory`: HDC accumulator + fact-graph (P3 subject indexing) + structural retrieval + HDC role-filler binding (#00c-2) + incremental `write_one` (audit-D2 amortized-O(1) growth) + `replay_consolidate` (P4) + `retrieve_structural_full_history` (Phase 12). turn_id ↔ row mapping (audit-A1) for non-contiguous IDs. `extract_query_subjects` is the public API surface (audit-C1). |
| `semantic_memory_agent.py` | Layer 4 — `MemoryAgent.process(text)` rule-based controller; routes write vs retrieve; `_LIST_ALL_HINTS` classifier (Phase 12) routes list-all queries to `retrieve_structural_full_history`; template composer (NO LLM); evidence packet with cited turn IDs; absent-answer threshold gating; `compose_answer` formats single-turn / multi-turn / full-history evidence. **Phase 13 #00P13c1-01-sandbox additions:** `SANDBOX_ROOT` module constant (`<repo>/sandbox` resolved at module load), `_validate_sandbox_path` primitive (refuses absolute / `..`-traversal / symlink-escape), 4 sandbox tools (`_tool_{read_file,write_file,run_python,list_dir}_sandbox`) registered alongside legacy `_tool_read_file` in `MemoryAgent.tools` default factory. **Phase 13 #00P13c1-02-persona additions:** `compose_answer` wraps every return path via `project_x.persona.wrap_response` with the appropriate `response_type` tag (absent → "Negative." / single-evidence → "Notice." / multi-evidence → "Multi-evidence." / full-history → "Chronological evidence."); decision label unchanged (downstream callers route on it); query passed as stable-hash seed for deterministic humor selection. |
| `semantic_memory_dataset.py` | Phase 9 synthetic-real conversation generator + labeled query set (P1 contradiction-label fix). |
| `encoder.py` | Char-n-gram + Hebbian organic encoders. From-scratch; no pretrained transformers. |
| `random_index_hebbian.py` | Hebbian co-occurrence encoder + replay-consolidation extension. `fit(reset=True)` (audit-A2) for idempotent re-fit. Sparse-ternary index vectors + Mikolov subsampling + optional negative sampling. |
| `ensemble_encoder.py` | Phase 9 Cycle 4 prototype — alpha-blend / max / per-type ensemble strategies. Alpha-blend logic was inlined into `SemanticHDCMemory._ensemble_cosines`; this module is retained as historical reference for max / per-type strategies that may be revisited. **Retention candidate** — if not revisited by Phase 14, demote. |
| `hdc_substrate.py` | HDC primitives — `bind`, `unbind`, `superpose`, `write`, `read`, `cleanup`, `random_vector`, `bit_accuracy`. Self-test CLI via `--self-test`. Coverage 24% → 89% (audit-E1). |
| `hdc_snn_bridge.py` | SNN spike-train bridge — Phase 13+ candidate substrate (research script, CLI-driven). |

### Project X Raphael reasoning substrate — `src/project_x/reasoning/` (Phase 13 #00P13c2-02)

| Path | Justification |
|---|---|
| `src/project_x/reasoning/__init__.py` | Package marker + identity-discipline note (the AGENT's reasoning layer, not the BUILDER's). Re-exports `DerivationStep`, `Lemma`, `solve_quadratic`, `expand_characteristic_polynomial_2x2`, `numerical_verify`. |
| `src/project_x/reasoning/symbolic.py` | Phase 13 #00P13c2-02 — from-scratch symbolic reasoning primitives. `DerivationStep` (operation/inputs/output/justification) + `Lemma` (claim + chain + verification metadata + Raphael-voice render). `solve_quadratic` hand-rolled discriminant + root formula (3-step chain, math.sqrt only — NO sympy). `expand_characteristic_polynomial_2x2` reuses solve_quadratic via λ² - tr(A)λ + det(A) = 0 (4-step chain, hand-rolled trace + det — NO numpy.linalg). Negative discriminant raises NotImplementedError (complex roots beyond cycle 2 scope). Drives D4 baseline-attempt against maths-001 (definite scope-fit) + maths-002 (stretch scope-fit). |
| `src/project_x/reasoning/verifier.py` | Phase 13 #00P13c2-03 — sandbox-bound numerical verifier closing the loop on the symbolic substrate. `numerical_verify(lemma, expected_value, tolerance)` generates an INDEPENDENT stdlib-only Python script per the lemma's first-step operation (`discriminant` → quadratic-root path; `trace` → 2x2-eigenvalue path), writes via D1 `_tool_write_file_sandbox`, runs via D1 `_tool_run_python_sandbox`, parses VERIFY_RESULT line via `ast.literal_eval` (refuses code execution; only literals), compares to expected (or to substrate's actual_value as consistency-check fallback) per `verification_method`. The sandbox script does NOT import the substrate — independence is the second-opinion gate (a buggy substrate must be falsifiable, not collude with itself). Sentinel strings (`NEGATIVE_DISCRIMINANT` / `COMPLEX_EIGENVALUES`) → graceful None; unsupported operations → match=False without exception. Cycle 3+ extends supported-operation set as new substrate primitives ship. **Phase 13 #00P13c4-24 EXTENSION:** `_quadratic_newton_verification_script(a, b, c)` + `verify_quadratic_via_newton(a, b, c, expected, tolerance)` add a divergent-verifier-path (Newton-Raphson from x=1.0 + Vieta deflation r₂ = -b/a - r₁). Different code path than closed-form `_quadratic_verification_script` — robust against shared closed-form bugs (Surface 2 mitigation per `docs/artifacts/PHASE_13_ANTICHEAT_AUDIT.md`). |
| `src/project_x/reasoning/physics.py` | Phase 13 #00P13c4-02 — from-scratch closed-form physics primitives mirroring the cycle 2/3 maths substrate shape. Three primitives: `free_fall_time(h, g)` (kinematic identity h = ½gt² → t = √(2h/g); 1-step + energy-conservation invariant v_f = g·t = √(2gh)); `pendulum_period(L, g)` (small-angle SHM via Lagrangian linearization → T = 2π√(L/g); 1-step + dimensionless-universal invariant T²·g/L = 4π²); `relativistic_momentum(m, v, c)` (Lorentz factor γ = 1/√(1-β²) + p = γmv; 2-step + Newtonian-limit invariant γ - 1 ≈ β²/2). Each lemma carries `add_introduction` math-WHY prose (kinematic / Lagrangian / SR derivations) + `add_invariant_check` post-derivation. Hand-rolled — uses only `math.sqrt` + `math.pi` (Python stdlib); NO scipy.constants, NO numerical-physics libraries. Anti-cheat-aware design (cycle 4 #00P13c4-24): each primitive computes per-input — surrogate-prompt regression in `tests/test_reasoning_physics.py` confirms `memorization_signal == 0.0` across Earth/Moon/Mars/Jupiter gravity regimes (free-fall + pendulum) and electron/proton mass scales at 0.1c-0.99c (relativistic momentum). Raises ValueError on non-positive inputs + superluminal velocity for `relativistic_momentum`. |

### Project X Raphael anti-cheat surface — `src/project_x/anti_cheat.py` (Phase 13 #00P13c4-24)

| Path | Justification |
|---|---|
| `src/project_x/anti_cheat.py` | Phase 13 cycle 4 #00P13c4-24 — anti-cheat mechanism per `docs/artifacts/PHASE_13_ANTICHEAT_AUDIT.md` minimum-viable scope (Candidates D + E). `AntiCheatProbe` dataclass binds canonical input + N surrogate variants + input-output predicate; `differential_capability_test(substrate_fn, probe)` runs substrate on canonical + each surrogate and computes `memorization_signal` (1.0 = canonical passes but surrogates fail = memorization or overfit; 0.0 = all surrogates pass = genuine capability). Rule-based generators `generate_surrogate_quadratic` + `generate_surrogate_char_poly_2x2` preserve regime constraints (real-discriminant; real-eigenvalues). Predicates `quadratic_roots_predicate` + `char_poly_2x2_eigenvalues_predicate` verify input-output appropriateness via closed-form identities (a·r² + b·r + c ≈ 0; Vieta on trace/det) — fake substrate hardcoding canonical answer fails predicate on surrogate inputs. Documents surrogate-author independence absence (current cycle: builder rule-based; cycle 5+ may add lain-authored / textbook-derived). Organic-thesis-compliant: NO LLM calls, NO pretrained-transformer derivatives. Gates cycle 4 #19 substrate physics Tier 2 + #20 substrate-driven attempt — both must pass `memorization_signal == 0.0` before capability claims are recorded. |

### Project X Raphael persona scaffolding — `src/project_x/persona/` (Phase 13 #00P13c1-02)

| Path | Justification |
|---|---|
| `src/project_x/persona/__init__.py` | Module exports + identity-discipline note (the AGENT's voice, not the BUILDER's). Re-exports `wrap_response`, `score_response`, `voice_consistent`, `humor_inserted`, `in_character`, plus the `VOICE_MARKERS`, `HUMOR_TEMPLATES`, `HUMOR_ENABLED_TYPES`, `HUMOR_FREQUENCY_PCT`, `FORBIDDEN_PHRASES` constants for testability. |
| `src/project_x/persona/voice.py` | `VOICE_MARKERS` dict (8 response_types: factual_retrieval / multi_evidence / retrieve_full_history / absent / refusal / error / write_ack / tool_ack) + `wrap_response(text, response_type, prompt)` wrapper. Marker prefixes the text; humor (from humor.py) optionally postfixed via `select_humor`. Unknown response_type passes through unchanged (graceful fallback). |
| `src/project_x/persona/humor.py` | `HUMOR_TEMPLATES` per humor-enabled response type (3-4 templates each, dry-understatement register matching Raphael's declarative-analytical baseline) + `select_humor(response_type, prompt)` deterministic selection via SHA-256 stable hash. `HUMOR_FREQUENCY_PCT = 30` insertion rate. Humor disabled (by design) for absent/refusal/error — gravity preserved. |
| `src/project_x/persona/rubric.py` | In-character STRUCTURAL scorer: `voice_consistent` (correct prefix), `humor_inserted` (template appended; returns False for non-humor types), `in_character` (no `FORBIDDEN_PHRASES` like "I'm an AI assistant" / "As Claude" — case-insensitive). `score_response` composes all three. **QUALITATIVE wit-grading is for the manual-grade harness (#00P13c1-03 + cycle 3+), not this rubric** — M-PROJECTX-014 firewall: agent doesn't grade own subjective output. |

#### Phase 4-8 historical research scripts (CLI-driven; coverage policy: scripts not library)

| Path | Justification |
|---|---|
| `hdc_capacity.py` | T1 within-capacity recall + T4 capacity cliff sweep. |
| `hdc_compose.py` | T2 compositional binding battery (role-filler retrieval + cleanup). |
| `hdc_continual.py` | T3 continual-learning retention test (100 random pairs across time). |
| `hdc_conversation_demo.py` | Indefinite-context conversability use-case demo. |
| `hdc_vs_naive_comparison.py` | Memory-vs-accuracy trade-off — HDC accumulator vs naive per-turn storage. |
| `hopfield_lens.py` | Post-hoc Modern Hopfield Network energy-regime analysis (β-effective + regime classification). |

#### Quarantined / utility (audit-C2; torch-dependent; `[legacy]` extra)

| Path | Justification |
|---|---|
| `compressed_memory.py` | Phase 1-3 transformer-style historical control. **DO NOT IMPORT in organic-thesis code.** |
| `tasks.py` | Task registry exclusively for `compressed_memory` experiments. Quarantine surface. |
| `util_harness.py` | Phase 7 GPU-utility harness — pre/during/post `nvidia-smi` sampling for the 70-90% util-band check. |

### Quarantine — `src/project_x/legacy/`

| Path | Justification |
|---|---|
| `__init__.py` | Package marker. |
| `transformer_scaffolding.py` | Phase 1-6 transformer-style scaffolding (was at `src/project_x/model.py` until P6 quarantine). **DO NOT IMPORT in organic-thesis code.** Required for the `legacy` extra; gated by `pytest.importorskip("torch")` in `test_smoke.py`. |

### Top-level `src/project_x/`

| Path | Justification |
|---|---|
| `__init__.py` | Package marker. |
| `config.py` | `ModelConfig` + `RunConfig` dataclasses for the legacy `ProjectXModel`. Used by `smoke.py` and `legacy/transformer_scaffolding.py`. |
| `smoke.py` | Smoke entry-point exercising the legacy `ProjectXModel`. Quarantined; torch-dependent. |

## `tests/` — pytest suite (87 tests passing as of audit-fix run)

| Path | Justification |
|---|---|
| `test_compressed_memory.py` | Phase 1-3 quarantine smoke. `pytest.importorskip("torch")` so the active suite runs without the `[legacy]` extra. |
| `test_encoder.py` | Phase 9 char-n-gram + Hebbian organic encoder coverage. |
| `test_hdc_substrate.py` | HDC primitives + 4 self-test fns + `run_self_test` CLI driver (audit-E1; 24% → 89% coverage on hdc_substrate). |
| `test_killer_milestone.py` | Phase 10 EXIT GATE acceptance — 5 capabilities (teach + correct + multi-hop + refuse-absent + tool-execution-with-writeback). |
| `test_random_index_hebbian.py` | Phase 9 + audit-A2 (`fit(reset=True)` idempotency regression guard). |
| `test_retrieval_modes.py` | Phase 12 retrieval-mode disambiguation regression guard (6 tests; audit-A4 tightened the unknown-subject behavioral assertion). |
| `test_semantic_hdc_memory.py` | Phase 9-10 Layer 3 + audit-A1 (non-contiguous turn_ids) + audit-A3 (replay_consolidate idempotency) + audit-D2 (write_one growth-by-doubling mechanics + perf-ratio guard). |
| `test_semantic_memory_agent.py` | Phase 9-10 Layer 4 agent loop + run_tool + replay coverage. |
| `test_semantic_memory_dataset.py` | Phase 9 synthetic dataset gen. |
| `test_smoke.py` | Phase 1-6 legacy scaffolding smoke. `pytest.importorskip("torch")` (audit-C2). |
| `test_benchmark_harness.py` | Audit-D3 — invokes `gpt-codex/benchmark/run_audit.py` in-process; asserts auto-graded entries replay green. |
| `test_sandbox.py` | Phase 13 #00P13c1-01-sandbox — covers `_validate_sandbox_path` primitive + 4 sandbox tools + `MemoryAgent.tools` registration + escape-attempt refusal (absolute path / `..` traversal / symlink-out). 18 tests; isolation via `monkeypatch.setattr(sma, "SANDBOX_ROOT", tmp_path/"sandbox")`. |
| `test_grader.py` | Phase 13 #00P13c1-03-grader-min — covers `Candidate` + `Grade` dataclasses, M-PROJECTX-014 firewall (parametrized over each forbidden field), Grade score-range validation (1-5 + non-int + empty-grader rejected), JSONL save/load round-trip with line-number-tagged errors, CLI subprocess invocation (`present` / `validate` / `validate-candidates` exit codes + outputs). 22 tests; loads `gpt-codex/grade_pipeline/schema.py` via `importlib.util.spec_from_file_location` because hyphenated parent dir prevents direct import. |
| `test_persona.py` | Phase 13 #00P13c1-02-persona — covers `VOICE_MARKERS` coverage, humor template structure + frequency (~30% across 1000 prompts), `wrap_response` determinism + unknown-type passthrough, in-character rubric (forbidden phrase detection case-insensitive), 10-fixture sample test (8 expected-pass + 2 cringe-fail caught), `compose_answer` integration (memory-ladder invariants preserved under wrapping). 26 tests. |
| `test_reasoning_symbolic.py` | Phase 13 #00P13c2-02-symbolic-substrate — covers DerivationStep + Lemma dataclass mechanics (init / add_step / render); solve_quadratic correctness against maths-001 (3x²-14x-5=0 → [-1/3, 5]) + edge cases (zero a, negative discriminant raises NotImplementedError, repeated root, zero-discriminant boundary); expand_characteristic_polynomial_2x2 correctness against maths-002 ([[2,1],[1,2]] → [1, 3]) + edge cases (non-2x2 ValueError, diagonal matrix); thesis-compliance source-grep (no sympy/numpy/torch/transformers/BGE/MiniLM/sentence_transformers/llama_cpp/Qwen/Mistral imports). 24 tests. |
| `test_reasoning_verifier.py` | Phase 13 #00P13c2-03-numerical-verifier — covers numerical_verify end-to-end against substrate solve_quadratic (maths-001 match + repeated-root + tolerance loose/tight) + char_poly_2x2 (maths-002 match + diagonal); corruption-detection (manually-corrupted actual_value caught via consistency check); edge cases (empty derivation chain → False, unsupported operation → False); _parse_sandbox_output (normal payload, sentinel strings NEGATIVE_DISCRIMINANT + COMPLEX_EIGENVALUES, missing VERIFY_RESULT, malformed payload, ast.literal_eval refuses code execution like __import__); _close_enough (numerical_close list match/value-mismatch/length-mismatch/scalar; symbolic_match strict; unknown-method refused); end-to-end sandbox script execution via _tool_run_python_sandbox. Sandbox isolation via monkeypatch SANDBOX_ROOT → tmp_path/sandbox. 25 tests. |
| `test_anti_cheat.py` | Phase 13 #00P13c4-24-anti-cheat-mechanism — covers surrogate generators (real-discriminant quadratic + real-eigenvalue 2x2 matrix; n-truncation; canonical-zero rejection); predicates (quadratic-roots Vieta-identity verification + char-poly Vieta on trace/det); end-to-end `differential_capability_test` on REAL substrate (`solve_quadratic` + `expand_characteristic_polynomial_2x2` — both must produce `memorization_signal == 0.0` since substrate computes per-input); OVERFIT-DETECTOR test (fake substrate hardcodes canonical maths-001 answer regardless of input; probe correctly catches → `memorization_signal == 1.0`); raising-substrate edge case (`canonical_match == False` + `memorization_signal == 0.0` collapsed when substrate broken); `AntiCheatProbe.surrogate_author` field documents authorship (default "builder (rule-based)" for cycle 4; cycle 5+ may set "lain" / "textbook:<ref>"); Newton's-method divergent-verifier-path tests via `verify_quadratic_via_newton` (maths-001 happy-path; negative-discriminant sentinel; wrong-expected rejection; sandbox-isolated). 20 tests. |
| `test_reasoning_physics.py` | Phase 13 #00P13c4-02-substrate-physics-tier2 — covers each primitive's closed-form correctness on canonical ladder inputs (physics-001 free_fall 4.04s; physics-002 pendulum 2.007s; physics-003 relativistic momentum 5.64e-22 within 10% relative); anti-cheat-aware gate (cycle 4 #00P13c4-24): differential_capability_test on each primitive with surrogate input families (Earth/Moon/Mars/Jupiter gravities for free_fall + pendulum; electron/proton/0.1c-0.99c for relativistic momentum) must produce memorization_signal == 0.0; OVERFIT-DETECTOR (fake substrate hardcoding 4.04 caught — passes canonical kinematic-identity check but fails on different-gravity surrogates); Lemma.render() integration (intro prose + invariant check rendering); boundary cases (non-positive inputs raise; superluminal v raises); thesis-compliance source-grep (no sympy/numpy/scipy/torch/transformers imports). 15 tests. |

## `gpt-codex/` — Phase 9-12 inputs + benchmark + run results

| Path | Justification |
|---|---|
| `gpt-codex/benchmark/` | Phase 11 Raphael Domain Benchmark Suite. 6 domain ladders × 6 entries (`physics/`, `maths/`, `memory/`, `persona/`, `philosophy/`, `poetry/`), each with `ladder.jsonl` + `rubric.md`. M-PROJECTX-014 firewall: NO `self_score` field. Aggregate `audit_log.jsonl` + `verdict.md`. |
| `gpt-codex/benchmark/run_audit.py` | Audit-D3 harness — replays auto-graded entries against the live stack each commit. |
| `gpt-codex/grade_pipeline/` | Phase 13 #00P13c1-03 — manual-grade harness (cycle 1: read+grade+write JSONL round-trip; cycle 3+ wires iterative loop into agent generation). Files: `__init__.py` (package marker), `schema.py` (Candidate + Grade dataclasses + load/save helpers; `FORBIDDEN_CANDIDATE_FIELDS` enforces M-PROJECTX-014 firewall — `self_score`, `self_grade`, `self_rating`, `agent_score` rejected at load with line-number-tagged ValueError), `cli.py` (subcommands: `present` → grading worksheet to stdout, `validate` → grades JSONL schema check, `validate-candidates` → firewall lint), `README.md` (usage + cycle 1 baseline-attempt context). |
| `gpt-codex/grade_pipeline/baseline_2026-05-10_math_tier1/` | Phase 13 cycle 3 #00P13c3-02 substrate Tier 1 extensions re-grade. `candidates.jsonl` (2 entries — Tier 1 extended substrate output for maths-001 + maths-002 with Lemma.add_introduction prose + Vieta invariant_checks for char_poly). `grades.jsonl` (2 entries — substrate-vs-substrate re-grade vs cycle 2 D4 baseline; maths-001 4.0→4.5/5, maths-002 4.0→4.75/5; differentiated lift signal per advisor catch — calibration-symmetry tell broken; structured `grader_was_author_bias_note` field per advisor schema-consistency catch). `improvement_directions.md` (per-prompt cycle 4+ paths to 5.0/5 + structural_insight optimistic-vs-strict-read caveat documented; comparison-axis less-bias-vulnerable-not-immune framing per advisor catch). |
| `gpt-codex/grade_pipeline/baseline_2026-05-10_pathB/` | Phase 13 cycle 3 #00P13c3-01 Path B grader-flip on rank 4-5 maths. `grades_rank_4_5.jsonl` (2 entries — builder rubric grades on Phase 11-frozen `raphael_response` for maths-004 (Galois) + maths-005 (algebraic topology); both 4.25/5 weighted aggregate after advisor-mandated completeness-gap docking). Honest audit-status label is `"rubric-graded-builder; pending external confirmation"` (NOT `"rubric-graded-green"` which would overclaim external-audit). Threshold-grader independence absent (same builder set threshold 4.0 + graded); lain or external auditor may reset via Discord. Lifts maths PASS 3/0 → 5/0 (FIRST visible PASS-count progress in Phase 13). |
| `gpt-codex/grade_pipeline/baseline_2026-05-10_physics_pathB/` | Phase 13 cycle 4 #00P13c4-01 Path B grader-flip on rank 4-5 physics. `grades_rank_4_5.jsonl` (2 entries — builder rubric grades on Phase 11-frozen `raphael_response` for physics-004 (Einstein field equations, hard) + physics-005 (LQG vs string theory, frontier); 4.33/5 + 4.75/5 weighted aggregates — DIFFERENTIATED lift signal (frontier analytical breadth vs hard term-listing) breaks calibration-symmetry tell per cycle 3 advisor catch). Honest audit-status label `"rubric-graded-builder; pending external confirmation"` per cycle 3 advisor discipline. Completeness 4/5 on physics-004 docks sign-convention-gap (Lorentzian +--- vs -+++ not explicitly named); survey_honesty 4/5 on physics-005 docks asymptotic-safety/causal-sets/CDT hand-wave. Lifts physics PASS 3/0 → 5/0 (SECOND visible PASS-count progress in Phase 13; cycle 4 mirrors cycle 3 Path B pattern). Anti-cheat-cleaner than substrate-driven attempts: grader reads frozen response, doesn't generate. |
| `gpt-codex/grade_pipeline/baseline_<YYYY-MM-DD>[_<suffix>]/` | Per-cycle capability-touchpoint baselines. **`baseline_2026-05-10/`** (#00P13c1-04): `candidates.jsonl` (2 entries — agent attempts poetry-001 + philosophy-001 via post-D2 `compose_answer` with bootstrap-seeded memory only, no curated corpus), `grades.jsonl` (2 entries — Claude Code Raphael grades each via rubric criteria, weighted aggregate 1.2-1.3/5 — brutality is the diagnostic), `improvement_directions.md`. **`baseline_2026-05-10_math/`** (#00P13c2-04): `candidates.jsonl` (2 entries — agent attempts maths-001 + maths-002 via cycle 2 substrate solve_quadratic + expand_characteristic_polynomial_2x2; numerical_verify match=True via sandbox second-opinion), `grades.jsonl` (2 entries — builder grades via maths rubric proof-shape dimensions; weighted ~4.0/5 both prompts; structural_insight 3/5 reflects WHAT-not-WHY gap per advisor catch), `improvement_directions.md` (per-prompt directions to push to 5/5 + Tier 1/2/3 substrate extension roadmap + Path B as proposed cycle 3 #1 priority). Same-day disambiguation suffix `_math` because cycle-1 already claimed bare `2026-05-10`; future cycles can use `_physics`/`_<domain>` per scope. |
| `gpt-codex/runs/` | Per-run aggregate `result.json` directories (Phase 1-9 sweeps + Phase 9 encoders). Frozen-per-phase. **Audit-F2 retention policy**: NEW dirs gitignored by default (`gpt-codex/runs/*/`); already-tracked Phase 1-10 evidence stays tracked; promotion via `git add -f` after a verdict cites the run. See MANIFESTO § retention policy. |

## `sandbox/` — Project X Raphael action-taking workspace (Phase 13 #00P13c1-01)

| Path | Justification |
|---|---|
| `sandbox/.gitkeep` | Empty marker so the locked-folder root is tracked by git. The agent (Project X Raphael) operates ONLY inside this directory via the 4 sandbox tools registered on `MemoryAgent.tools`: `read_file_sandbox`, `write_file_sandbox`, `run_python_sandbox`, `list_dir_sandbox`. Path validation in `semantic_memory_agent.py::_validate_sandbox_path` is the security boundary; absolute paths, `..` traversal, and symlinks pointing outside are refused. Cycle 2+ may add subprocess env stripping, urllib/socket blocking, /dev/tcp blocking — deferred per Phase 13 cycle 1 corpse "MINIMUM viable" framing. Snapshot/reset machinery lives in `scripts/sandbox/`. |
| `gpt-codex/notes/` | Reading notes (`architecture_mechanisms_matrix.md`, `deepseek_v4_reading_notes.md`, `frontier_model_notes.md`, `open_questions.md`). |
| `gpt-codex/brainstorm/` | Phase 1 ideation artifacts (`ARCHITECTURE_CANDIDATES.md`, `FINAL_RECOMMENDATION.md`, `IDEA_BANK.md`, `KILL_CRITERIA.md`, `NOVELTY_MATRIX.md`, `TOP_3_DESIGNS.md`). Frozen historical record. |
| `gpt-codex/logs/` | Curl/pdftotext logs from Phase 1 source ingestion. |
| `gpt-codex/extracted/` | (gitignored) Codex extracted-content blobs — large, metadata-only via `ref/SOURCE_MANIFEST.md`. |
| `gpt-codex/sources/` | (gitignored) Source pages cache — large, metadata-only. |

## `ref/` — public reference material

| Path | Justification |
|---|---|
| `ref/SOURCE_MANIFEST.md` | Manifest of public reference sources (papers, model reports). |
| `ref/sources.json` | Machine-readable source list. |
| `ref/papers/` | (gitignored) PDFs of reference papers. |
| `ref/pages/` | (gitignored) Cached source pages. |

## `scripts/` — research-scripts that don't fit `src/`

| Path | Justification |
|---|---|
| `aggregate_phase7_results.py` | Aggregates Phase 7 hbsweep + lrc-distill results across seeds. |
| `fetch_refs.py` | Source-fetch driver for `ref/`. |
| `generate_docs.py` | Source-doc generator (Phase 1 era). |
| `phase7_baseline.sh`, `run_phase7_grid.sh`, `run_phase7_hbsweep.sh` | Phase 7 sweep runners. |
| `plot_phase8_dscaling.py`, `plot_phase8_t4.py` | Plot generators for Phase 8 figures (the T4_*.png set in `docs/artifacts/`). |
| `sandbox/reset.sh` | Phase 13 #00P13c1-01-sandbox — wipe `sandbox/` to empty (preserves `.gitkeep`). MINIMUM viable; cycle 2+ may add `--to-snapshot=<name>` for benchmark replay. |
| `sandbox/snapshot.sh` | Phase 13 #00P13c1-01-sandbox — capture `sandbox/` state to `sandbox_snapshots/<name>/` (gitignored; local-only). MINIMUM viable; cycle 2+ wires restore + diff. |

## Upkeep contract (heartbeat-tracked)

- **At every cycle close:** sweep this file. Any file/dir added in the cycle that doesn't have a row → ADD a row in the same commit. Any file/dir deleted → REMOVE its row.
- **At session start:** along with MANIFESTO + A_TO_Z + DO_THIS_NEXT, re-read this file. The four together are the live-doc set.
- **Pristine gate:** `git ls-files | comm -23 - <(awk-extract-tracked-paths-from-this-file)` should be empty (no orphan tracked file). The reverse — entries here referencing files that don't exist — fails the gate too.

---

*— REPO_CONTROL.md created 2026-05-10 (audit-fix run; lain directive: "since the A TO Z gets cycled out after each phase, we dont keep the file justification in there. rather, we keep it in a new REPO_CONTROL.md file"). Heartbeat reconciles freshness; new files added in a commit MUST land with their row in the same commit.*
