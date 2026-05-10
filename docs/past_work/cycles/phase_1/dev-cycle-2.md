## Cycle 2 Reflection — Phase 1 — 2026-04-29 03:23–03:40 UTC (CEST 05:23–05:40)

### Persona
Execute-Navi (cycle 2 of 5 in Phase 1: Augmentation Cycle 1). Cycle 1 = prior session's lock-the-contract Plan-Navi work that produced `docs/DO_THIS_NEXT.md`.

### Skills used
- `Skill('skills:refine-todos')` (auto-invoked at session bootstrap; produced `#00a` + 10 substeps with full what/where/why/done-when structure and dep-graph blocking).
- `Skill('godify')` (fired by user with arg `6h`; loaded the cyclic protocol).

### Shipped this cycle
- **`#01`** (#5a) — `nn.Linear(cfg.dim, n_blocks)` distillation head added to `TinyLM.__init__`; `forward` captures `_last_distill_logits = self.distill_head(x_normed)` for downstream `#05`. Module-state buffer pattern → no signature change to `forward`. (`compressed_memory.py:148-184`)
- **`#02`** (#15a) — `_compressed_attention` now returns `(y, metrics, entropy_diff)` 3-tuple; `entropy_diff = torch.stack(entropy_values).mean()` un-detached. `DualRateCompressedAttention.forward` unpacks and stores `self._last_medium_entropy` / `self._last_heavy_entropy`. Outer return signature `(out, metrics)` UNCHANGED so TinyLM.forward / evaluate / train_one all still unpack 2-tuple. (`compressed_memory.py:73-145`)
- **`#03`** (#27a) — `make_batch` now samples marker position per-sample uniformly: `torch.randint(seq_len // 4, seq_len - 1, (batch_size,), device=device)`. Per-sample > per-batch — different positions within the same batch force position-invariant association learning. (`compressed_memory.py:187-195`)
- **`#06`** (#15b) — Candidate `train_one` adds entropy term gated on `cfg.memory_byte_weight > 0`: walks `model.modules()` for `DualRateCompressedAttention` instances, sums `_last_medium_entropy + _last_heavy_entropy` across all blocks, multiplies by `cfg.memory_byte_weight`. Control no-ops gracefully (no DualRate module to find). (`compressed_memory.py:240-252`)
- **`#07`** (#5d/#15c) — `distill_weight: float = 0.0` and `memory_byte_weight: float = 0.0` added to frozen `ExperimentConfig`. Defaults of 0 preserve existing test behavior; CLI/programmatic override activates the augmentation. `block_size` deferred — `cfg.medium_block` already serves the purpose for `n_blocks` calc. (`compressed_memory.py:17-35`)

### Verifications
- `pytest -q` after Layer 0 edits: `2 passed in 1.92s`.
- `pytest -q` after #06 + #07 edits: `2 passed in 1.83s`.
- Smoke test with `memory_byte_weight=5e-2` on tiny config (steps=3, batch=2, dim=16, heads=2, depth=1): `train_loss_last=8.5659` (vs baseline ~4.3), `selector_entropy=1.0691` nats. Confirms entropy term is added and backpropagating.

### Lessons
- **Cron-timing collision avoided.** Initial cron at `5-59/20` would have fired at 5:25, only 2 min after I started the in-line cycle. Caught and corrected to `2-59/20` aligned to actual cycle start. Worth memorizing: when starting an in-line cycle, the cron schedule MUST give >= 20 min before the next fire, OR delete + recreate aligned. 1 min lost; could have been 20.
- **Module-state buffer > signature change.** Tempted to extend `forward` returns to a 3-tuple with aux dict for the new tensors. Avoided because that breaks every caller (TinyLM.forward, evaluate, train_one — three different unpacking sites). Module-state buffer (`self._last_*`) is much less invasive — only the producer changes. Default pattern when adding optionally-consumed tensors to a forward path.
- **Per-sample probe distance > per-batch.** Spec said "per batch (or per sample)." Per-sample varies positions within a batch, forcing position-invariance. Stronger probe at zero compute cost.
- **Block-size handled by existing field.** Spec mentioned `cfg.block_size` but `cfg.medium_block` already drives the candidate's block partitioning, and the distillation head computes `n_blocks = math.ceil(cfg.seq_len / cfg.medium_block)` consistent with the candidate. Adding `block_size` as a separate field would have introduced configuration drift between teacher block partition and candidate. Better: one source of truth.

### 420 Score
**415** — strong execution, no rework, pytest 2-passed twice, smoke-verified entropy term backprops. Lost 5 points: (a) cron-timing collision (caught but cost a minute) and (b) cycle 1's Plan-Navi work landed in a prior session, not this /godify run, so the State Machine's 1-of-5 Plan-Navi protocol was effectively skipped — this is fine because the contract was already locked, but worth flagging.

### Next Cycle Hook
Cycle 3 = Layer 1 remainder (`#04` teacher labels via `FullCausalAttention.forward_with_weights` + `#05` distill cross-entropy term in candidate `train_one`). Full plan in `docs/DO_THIS_NEXT.md`. Smoke-test command included.
