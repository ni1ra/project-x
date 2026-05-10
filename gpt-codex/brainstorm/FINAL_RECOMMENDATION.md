# Final Recommendation

Primary implementation target: **Dual-Rate Compressed Memory Attention**.

Backup: **Surprise-Gated Writable Memory** if the primary design collapses into known sparse-attention behavior or fails to produce a memory-byte Pareto improvement.

## Why This Clears The Gate

- DeepSeek V4 has been downloaded, extracted, and summarized.
- 22 sources have been extracted and indexed.
- The idea bank ranks 30 architecture / training-signal ideas under stack discipline (PyTorch as floor, Triton as the standing target for compute-path kernels, CUDA C++ only when Triton expressivity runs out).
- The top 3 designs are named with minimum experiments and kill criteria.
- The primary target is falsifiable without building a full model.

## First Experiment (already shipped)

The smallest candidate that can fail:

- One tiny transformer control.
- One tiny model that replaces attention with local-window attention plus compressed block memory.
- Defer MoE, Muon, FP4/FP8, mHC, and serving cache engineering.
- Use identical corpus, token budget, train steps, batch, optimizer, and hardware limits.
- `--mode test` must finish in 180 seconds or less.

## Next Concrete Step (revised)

The next concrete work is **not more architecture, and not Tritonization**. The existing #1 harness needs better training signal and stronger probes before any further architectural complexity (VQ-cache, surprise-gating, kernel rewrites, vendor-SSM hybrids) is justified.

Add to the existing #1 harness, in this order:

1. **#5 Memory Distillation Head.** Generate teacher-attention labels from the dense control; train an auxiliary head that predicts which past block future tokens will need. Pure PyTorch — auxiliary head, no compute-path kernel surface, no Triton needed.
2. **#15 Memory-Byte Regularized Loss.** Add a differentiable read-budget penalty so loss-per-byte is a train-time objective, not a post-hoc score. Pure PyTorch — additional loss term.
3. **#27-style stronger long-association probes.** The current probe is underpowered. Start with longer / harder uniform-distance synthetic associations (no adversary yet) so the headline metric has a sharper signal. PyTorch + data pipeline only — no architecture change.
4. **Rerun two seeds** with the augmented harness. Confirm the kill conditions still hold and check whether the candidate's long-probe signal has moved.

Only after this loop produces evidence does Tritonization, #21 (VQ-Quantized KV), or any architectural addition become justifiable. At that point the stack doctrine kicks in: compute-path kernels go to Triton by default, and the dual-rate attention kernel for #1 is the first standing target.

## Required Metrics

- Validation cross-entropy.
- Delayed association probe loss/accuracy (now strengthened — see step 3 above).
- Estimated memory bytes per generated token (now train-time regularized — see step 2).
- Selector entropy and selected block age distribution (now distillation-trained — see step 1).
- Wall-clock time for short run.
- Two-seed variance across the augmented harness.

## Decision

The current implementation gate is **training signal, not kernel speed.** Do not write Triton kernels and do not add new architectures until #5 + #15 + stronger #27-style probes are in the harness and two seeds confirm whether #1 has earned more investment.

Once it has, kernel work resumes under the standing stack doctrine: Triton is the default for any compute-path kernel — the 50/50 tie-breaker goes to the lower level for max efficiency. CUDA C++ is reserved for kernels Triton's expressivity cannot reach, not for routine optimization.
