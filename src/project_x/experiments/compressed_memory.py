"""Phase 1-3 compressed-memory transformer-style historical-control experiment.

QUARANTINED — DO NOT IMPORT IN ORGANIC-THESIS CODE (audit-C2).

Part of the Phase 1-6 transformer-style scaffolding family (alongside
`legacy/transformer_scaffolding.py` and `experiments/tasks.py`). Preserved as
a historical control for cross-phase comparisons; lain's 2026-05-09 standing
constraint disqualifies pretrained transformer derivatives at every layer of
the live organic stack.

Torch is required for this module and is an OPTIONAL `[legacy]` extra in
pyproject.toml — install via `pip install -e .[legacy]`. The live Phase 9-10
organic stack (semantic_hdc_memory, semantic_memory_agent, encoder,
random_index_hebbian, hdc_substrate) does NOT import torch; quarantine is
enforced at install-time, not just by convention.

Phase: 1-3 (historical control)
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import time
from dataclasses import asdict, dataclass

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F


@dataclass(frozen=True)
class ExperimentConfig:
    vocab_size: int = 64
    dim: int = 48
    heads: int = 4
    depth: int = 2
    seq_len: int = 48
    batch_size: int = 8
    steps: int = 12
    eval_batches: int = 4
    local_window: int = 12
    medium_block: int = 4
    medium_top_k: int = 4
    heavy_block: int = 16
    assoc_loss_weight: float = 1.0
    distill_weight: float = 0.0
    selector_distill_weight: float = 0.0
    memory_byte_weight: float = 0.0
    block_pool: str = "mean"
    lr: float = 3e-4
    seed: int = 1337
    device: str = "auto"  # phase 7 cycle 3: explicit device override (auto|cuda|cpu)
    amp: str = "none"  # phase 7 cycle 3: autocast dtype (none|bf16|fp16); bf16 default for AMP runs
    task: str = "long-range-copy"  # phase 7 cycle 9: task variant; see tasks.TASK_REGISTRY
    task_noise_frac: float = 0.10  # phase 7 cycle 9: fraction of key-noise corruption (key-noise task)
    task_n_keys: int = 2  # phase 7 cycle 9: number of decoy keys (multi-key task; ≥2)


def causal_mask(seq: int, device: torch.device) -> torch.Tensor:
    return torch.ones(seq, seq, device=device, dtype=torch.bool).tril()


def local_mask(seq: int, window: int, device: torch.device) -> torch.Tensor:
    idx = torch.arange(seq, device=device)
    return (idx[:, None] >= idx[None, :]) & ((idx[:, None] - idx[None, :]) < window)


class FullCausalAttention(nn.Module):
    def __init__(self, cfg: ExperimentConfig) -> None:
        super().__init__()
        self.heads = cfg.heads
        self.head_dim = cfg.dim // cfg.heads
        self.qkv = nn.Linear(cfg.dim, cfg.dim * 3, bias=False)
        self.out = nn.Linear(cfg.dim, cfg.dim, bias=False)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, dict[str, float]]:
        batch, seq, dim = x.shape
        qkv = self.qkv(x).view(batch, seq, 3, self.heads, self.head_dim)
        q, k, v = [t.transpose(1, 2) for t in qkv.unbind(dim=2)]
        y = F.scaled_dot_product_attention(q, k, v, attn_mask=causal_mask(seq, x.device))
        return self.out(y.transpose(1, 2).contiguous().view(batch, seq, dim)), {
            "selector_entropy": 0.0,
            "selected_block_age": 0.0,
        }

    def forward_with_weights(
        self, x: torch.Tensor
    ) -> tuple[torch.Tensor, dict[str, float], torch.Tensor]:
        batch, seq, dim = x.shape
        qkv = self.qkv(x).view(batch, seq, 3, self.heads, self.head_dim)
        q, k, v = [t.transpose(1, 2) for t in qkv.unbind(dim=2)]
        scale = math.sqrt(self.head_dim)
        scores = torch.matmul(q, k.transpose(-2, -1)) / scale
        mask = causal_mask(seq, x.device)
        scores = scores.masked_fill(~mask, float("-inf"))
        weights = torch.softmax(scores, dim=-1)
        y = torch.matmul(weights, v)
        out = self.out(y.transpose(1, 2).contiguous().view(batch, seq, dim))
        return out, {"selector_entropy": 0.0, "selected_block_age": 0.0}, weights


class DualRateCompressedAttention(nn.Module):
    def __init__(self, cfg: ExperimentConfig) -> None:
        super().__init__()
        self.cfg = cfg
        self.heads = cfg.heads
        self.head_dim = cfg.dim // cfg.heads
        self.qkv = nn.Linear(cfg.dim, cfg.dim * 3, bias=False)
        self.out = nn.Linear(cfg.dim, cfg.dim, bias=False)
        self._last_medium_entropy: torch.Tensor | None = None
        self._last_heavy_entropy: torch.Tensor | None = None
        self._last_medium_selector_scores: torch.Tensor | None = None

    def _compressed_attention(
        self,
        q: torch.Tensor,
        k: torch.Tensor,
        v: torch.Tensor,
        block: int,
        top_k: int | None,
    ) -> tuple[torch.Tensor, dict[str, float]]:
        batch, heads, seq, head_dim = q.shape
        block_count = math.ceil(seq / block)
        pad = block_count * block - seq
        if pad:
            k_pad = F.pad(k, (0, 0, 0, pad))
            v_pad = F.pad(v, (0, 0, 0, pad))
        else:
            k_pad = k
            v_pad = v
        k_view = k_pad.view(batch, heads, block_count, block, head_dim)
        v_view = v_pad.view(batch, heads, block_count, block, head_dim)
        if self.cfg.block_pool == "max":
            k_blocks = k_view.amax(dim=3)
            v_blocks = v_view.amax(dim=3)
        elif self.cfg.block_pool == "max-keys-mean-vals":
            k_blocks = k_view.amax(dim=3)
            v_blocks = v_view.mean(dim=3)
        elif self.cfg.block_pool == "sum":
            k_blocks = k_view.sum(dim=3)
            v_blocks = v_view.sum(dim=3)
        else:
            k_blocks = k_view.mean(dim=3)
            v_blocks = v_view.mean(dim=3)

        outputs: list[torch.Tensor] = []
        entropy_values: list[torch.Tensor] = []
        age_values: list[torch.Tensor] = []
        scale = math.sqrt(head_dim)
        final_pre_topk_scores: torch.Tensor | None = None
        for t in range(seq):
            visible = max(1, t // block)
            keys = k_blocks[:, :, :visible, :]
            vals = v_blocks[:, :, :visible, :]
            scores = (q[:, :, t : t + 1, :] * keys).sum(dim=-1) / scale
            pre_topk_scores = scores
            if top_k is not None and visible > top_k:
                vals_top, idx = torch.topk(scores, top_k, dim=-1)
                gather = idx.unsqueeze(-1).expand(-1, -1, -1, head_dim)
                vals = torch.gather(vals, 2, gather)
                scores = vals_top
                selected = idx.float()
            else:
                selected = torch.arange(visible, device=q.device, dtype=torch.float32).view(1, 1, visible)
            weights = torch.softmax(scores, dim=-1)
            out = (weights.unsqueeze(-1) * vals).sum(dim=2)
            outputs.append(out)
            entropy = -(weights.clamp_min(1e-9) * weights.clamp_min(1e-9).log()).sum(dim=-1).mean()
            entropy_values.append(entropy)
            current_block = torch.tensor(float(t // block), device=q.device)
            age_values.append((current_block - selected.mean()).clamp_min(0.0))
            if t == seq - 1:
                final_pre_topk_scores = pre_topk_scores

        y = torch.stack(outputs, dim=2)
        entropy_diff = torch.stack(entropy_values).mean()
        metrics = {
            "selector_entropy": float(entropy_diff.detach()),
            "selected_block_age": float(torch.stack(age_values).mean().detach()),
        }
        return y, metrics, entropy_diff, final_pre_topk_scores

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, dict[str, float]]:
        batch, seq, dim = x.shape
        qkv = self.qkv(x).view(batch, seq, 3, self.heads, self.head_dim)
        q, k, v = [t.transpose(1, 2) for t in qkv.unbind(dim=2)]
        local = F.scaled_dot_product_attention(
            q,
            k,
            v,
            attn_mask=local_mask(seq, self.cfg.local_window, x.device),
        )
        medium, medium_metrics, medium_entropy_diff, medium_selector_scores = self._compressed_attention(
            q, k, v, self.cfg.medium_block, self.cfg.medium_top_k
        )
        heavy, heavy_metrics, heavy_entropy_diff, _ = self._compressed_attention(q, k, v, self.cfg.heavy_block, None)
        self._last_medium_entropy = medium_entropy_diff
        self._last_heavy_entropy = heavy_entropy_diff
        self._last_medium_selector_scores = medium_selector_scores
        y = (local + medium + heavy) / 3.0
        metrics = {
            "selector_entropy": medium_metrics["selector_entropy"],
            "selected_block_age": medium_metrics["selected_block_age"],
            "heavy_entropy": heavy_metrics["selector_entropy"],
        }
        return self.out(y.transpose(1, 2).contiguous().view(batch, seq, dim)), metrics


class TinyLM(nn.Module):
    def __init__(self, cfg: ExperimentConfig, attention_cls: type[nn.Module]) -> None:
        super().__init__()
        self.cfg = cfg
        self.token = nn.Embedding(cfg.vocab_size, cfg.dim)
        self.position = nn.Embedding(cfg.seq_len, cfg.dim)
        self.blocks = nn.ModuleList(
            [
                nn.ModuleDict(
                    {
                        "norm_a": nn.LayerNorm(cfg.dim),
                        "attn": attention_cls(cfg),
                        "norm_f": nn.LayerNorm(cfg.dim),
                        "ffn": nn.Sequential(
                            nn.Linear(cfg.dim, cfg.dim * 4),
                            nn.GELU(),
                            nn.Linear(cfg.dim * 4, cfg.dim),
                        ),
                    }
                )
                for _ in range(cfg.depth)
            ]
        )
        self.norm = nn.LayerNorm(cfg.dim)
        self.head = nn.Linear(cfg.dim, cfg.vocab_size, bias=False)
        n_blocks = math.ceil(cfg.seq_len / cfg.medium_block)
        self.distill_head = nn.Linear(cfg.dim, n_blocks)
        self._last_distill_logits: torch.Tensor | None = None

    def forward(self, tokens: torch.Tensor) -> tuple[torch.Tensor, list[dict[str, float]]]:
        _, seq = tokens.shape
        pos = torch.arange(seq, device=tokens.device).unsqueeze(0)
        x = self.token(tokens) + self.position(pos)
        metrics = []
        for block in self.blocks:
            delta, block_metrics = block["attn"](block["norm_a"](x))
            x = x + delta
            x = x + block["ffn"](block["norm_f"](x))
            metrics.append(block_metrics)
        x_normed = self.norm(x)
        self._last_distill_logits = self.distill_head(x_normed)
        return self.head(x_normed), metrics


def make_batch(cfg: ExperimentConfig, device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
    """Phase 7 cycle 9: dispatches to tasks.TASK_REGISTRY based on cfg.task.
    Default 'long-range-copy' preserves phase 1-7 behavior. New variants 'key-noise'
    and 'multi-key' available via --task flag."""
    from .tasks import make_batch as _dispatch
    return _dispatch(cfg, device)


def evaluate(model: TinyLM, cfg: ExperimentConfig, device: torch.device) -> dict[str, float]:
    model.eval()
    losses = []
    assoc_losses = []
    assoc_correct = 0
    assoc_total = 0
    selector_entropy = []
    selected_age = []
    # Phase 7 lain standing rule: capture sample_generations on the FINAL eval batch.
    # Top-3 logits at the probe (last) position + truth + correct-flag, ≤5 samples per cell.
    sample_generations: list[dict] = []
    with torch.no_grad():
        for batch_idx in range(cfg.eval_batches):
            x, y = make_batch(cfg, device)
            logits, metrics = model(x)
            losses.append(F.cross_entropy(logits.reshape(-1, cfg.vocab_size), y.reshape(-1)).item())
            assoc_losses.append(F.cross_entropy(logits[:, -1, :], y[:, -1]).item())
            pred = logits[:, -1, :].argmax(dim=-1)
            assoc_correct += int((pred == y[:, -1]).sum())
            assoc_total += y.shape[0]
            for item in metrics:
                selector_entropy.append(item.get("selector_entropy", 0.0))
                selected_age.append(item.get("selected_block_age", 0.0))
            # Capture from the final batch only (cheap; ≤5 samples)
            if batch_idx == cfg.eval_batches - 1:
                probe_logits = logits[:, -1, :].float().cpu()
                truth_tokens = y[:, -1].cpu()
                top3_vals, top3_idx = probe_logits.topk(3, dim=-1)
                n_samples = min(5, probe_logits.shape[0])
                for s in range(n_samples):
                    sample_generations.append({
                        "probe_pos": int(cfg.seq_len - 1),  # final position (probe)
                        "top3_token_ids": top3_idx[s].tolist(),
                        "top3_logits": [round(float(v), 3) for v in top3_vals[s].tolist()],
                        "predicted_token_id": int(top3_idx[s, 0]),
                        "truth_token_id": int(truth_tokens[s]),
                        "correct": bool(top3_idx[s, 0].item() == truth_tokens[s].item()),
                        "truth_in_top3": bool(truth_tokens[s].item() in top3_idx[s].tolist()),
                    })
    return {
        "loss": float(np.mean(losses)),
        "delayed_assoc_loss": float(np.mean(assoc_losses)),
        "delayed_assoc_acc": assoc_correct / max(1, assoc_total),
        "selector_entropy": float(np.mean(selector_entropy)),
        "selected_block_age": float(np.mean(selected_age)),
        "sample_generations": sample_generations,
    }


def _amp_context(cfg: ExperimentConfig, device: torch.device):
    """Phase 7 cycle 3 — autocast context manager based on cfg.amp.
    Returns a no-op context if amp=='none' or fp16 GradScaler is needed (deferred)."""
    if cfg.amp == "bf16" and device.type in ("cuda", "cpu"):
        return torch.autocast(device_type=device.type, dtype=torch.bfloat16)
    if cfg.amp == "fp16" and device.type == "cuda":
        return torch.autocast(device_type="cuda", dtype=torch.float16)
    # no-op
    import contextlib
    return contextlib.nullcontext()


def train_one(
    name: str,
    attention_cls: type[nn.Module],
    cfg: ExperimentConfig,
    device: torch.device,
) -> dict[str, float]:
    torch.manual_seed(cfg.seed)
    model = TinyLM(cfg, attention_cls).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr)
    teacher: TinyLM | None = None
    teacher_opt: torch.optim.Optimizer | None = None
    if (cfg.distill_weight > 0 or cfg.selector_distill_weight > 0) and attention_cls is DualRateCompressedAttention:
        teacher = TinyLM(cfg, FullCausalAttention).to(device)
        teacher_opt = torch.optim.AdamW(teacher.parameters(), lr=cfg.lr)
    n_blocks = math.ceil(cfg.seq_len / cfg.medium_block)
    train_losses = []
    start = time.time()
    for _ in range(cfg.steps):
        model.train()
        x, y = make_batch(cfg, device)
        # Phase 7 cycle 3: forward + loss under autocast (bf16/fp16); backward in fp32.
        with _amp_context(cfg, device):
            logits, _ = model(x)
            loss = F.cross_entropy(logits.reshape(-1, cfg.vocab_size), y.reshape(-1))
            loss = loss + cfg.assoc_loss_weight * F.cross_entropy(logits[:, -1, :], y[:, -1])
        if cfg.memory_byte_weight > 0:
            entropy_terms: list[torch.Tensor] = []
            for module in model.modules():
                if isinstance(module, DualRateCompressedAttention):
                    if module._last_medium_entropy is not None:
                        entropy_terms.append(module._last_medium_entropy)
                    if module._last_heavy_entropy is not None:
                        entropy_terms.append(module._last_heavy_entropy)
            if entropy_terms:
                loss = loss + cfg.memory_byte_weight * torch.stack(entropy_terms).sum()
        teacher_logits: torch.Tensor | None = None
        if teacher is not None:
            teacher.train()
            t_seq = x.shape[1]
            t_pos = torch.arange(t_seq, device=device).unsqueeze(0)
            t_x = teacher.token(x) + teacher.position(t_pos)
            teacher_weights_list: list[torch.Tensor] = []
            for t_block in teacher.blocks:
                delta, _, block_w = t_block["attn"].forward_with_weights(t_block["norm_a"](t_x))
                t_x = t_x + delta
                t_x = t_x + t_block["ffn"](t_block["norm_f"](t_x))
                teacher_weights_list.append(block_w)
            t_x_normed = teacher.norm(t_x)
            teacher_logits = teacher.head(t_x_normed)
            t_weights = teacher_weights_list[-1]
            tb, th, tq, tk = t_weights.shape
            pad_k = n_blocks * cfg.medium_block - tk
            if pad_k > 0:
                t_weights = F.pad(t_weights, (0, pad_k))
            t_weights_per_block = (
                t_weights.view(tb, th, tq, n_blocks, cfg.medium_block).sum(dim=-1).sum(dim=1)
            )
            teacher_block_idx = t_weights_per_block.argmax(dim=-1)
            if cfg.distill_weight > 0:
                student_block_logits = model._last_distill_logits
                assert student_block_logits is not None
                distill_loss = F.cross_entropy(
                    student_block_logits.reshape(-1, n_blocks),
                    teacher_block_idx.reshape(-1),
                )
                loss = loss + cfg.distill_weight * distill_loss
            if cfg.selector_distill_weight > 0:
                # Supervise the candidate's medium-attention SELECTOR directly at the
                # final query position. Teacher knows which block (per medium_block
                # partition) is most relevant; candidate's pre-top-k scores at the
                # final position should match.
                selector_scores_at_final: list[torch.Tensor] = []
                for module in model.modules():
                    if isinstance(module, DualRateCompressedAttention):
                        if module._last_medium_selector_scores is not None:
                            selector_scores_at_final.append(module._last_medium_selector_scores)
                if selector_scores_at_final:
                    teacher_idx_final = teacher_block_idx[:, -1]
                    sel_loss_terms: list[torch.Tensor] = []
                    for scores in selector_scores_at_final:
                        # scores shape: (batch, heads, visible) — pre-top-k selector logits
                        sb, sh, sv = scores.shape
                        if sv == 0:
                            continue
                        scores_pooled = scores.mean(dim=1)  # (batch, visible)
                        mask = teacher_idx_final < sv
                        if mask.any():
                            sel_loss_terms.append(
                                F.cross_entropy(
                                    scores_pooled[mask],
                                    teacher_idx_final[mask],
                                )
                            )
                    if sel_loss_terms:
                        loss = loss + cfg.selector_distill_weight * torch.stack(sel_loss_terms).mean()
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        if teacher_opt is not None and teacher_logits is not None:
            teacher_loss = F.cross_entropy(
                teacher_logits.reshape(-1, cfg.vocab_size), y.reshape(-1)
            )
            teacher_opt.zero_grad(set_to_none=True)
            teacher_loss.backward()
            teacher_opt.step()
        train_losses.append(float(loss.detach()))
    metrics = evaluate(model, cfg, device)
    # Phase 7 cycle 3 Step 4b — persist final-layer selector scores so future
    # Hopfield-lens analysis runs on saved tensors WITHOUT re-running cells.
    selector_snapshot: dict[str, list] = {}
    for module in model.modules():
        if isinstance(module, DualRateCompressedAttention):
            sc = module._last_medium_selector_scores
            if sc is not None:
                # shape: (batch, heads, visible) — last query position only.
                # Keep small: pool over batch+heads, save as list-of-lists per head.
                with torch.no_grad():
                    sc_cpu = sc.detach().to(torch.float32).cpu()
                    selector_snapshot["raw_scores_mean_over_batch"] = sc_cpu.mean(dim=0).tolist()
                    sm = torch.softmax(sc_cpu, dim=-1)
                    selector_snapshot["softmax_mean_over_batch"] = sm.mean(dim=0).tolist()
                    ent = -(sm.clamp_min(1e-9) * sm.clamp_min(1e-9).log()).sum(dim=-1).mean(dim=0)
                    selector_snapshot["entropy_per_head_mean"] = ent.tolist()
                break  # snapshot first dual-rate module only; multi-layer extension is future work
    metrics.update(
        {
            "name": name,
            "train_loss_last": train_losses[-1],
            "seconds": time.time() - start,
            "parameter_count": sum(p.numel() for p in model.parameters()),
            "selector_snapshot": selector_snapshot,
        }
    )
    return metrics


def estimated_memory_bytes(cfg: ExperimentConfig, candidate: bool) -> int:
    bytes_per_value = 4
    if not candidate:
        return cfg.depth * cfg.seq_len * cfg.dim * 2 * bytes_per_value
    local = cfg.local_window * cfg.dim * 2
    medium = math.ceil(cfg.seq_len / cfg.medium_block) * cfg.dim * 2
    heavy = math.ceil(cfg.seq_len / cfg.heavy_block) * cfg.dim * 2
    return cfg.depth * (local + medium + heavy) * bytes_per_value


def run_experiment(
    mode: str,
    run_id: str,
    seed: int | None = None,
    distill_weight: float = 0.0,
    memory_byte_weight: float = 0.0,
    selector_distill_weight: float = 0.0,
    steps: int | None = None,
    eval_batches: int | None = None,
    assoc_loss_weight: float | None = None,
    dim: int | None = None,
    depth: int | None = None,
    batch_size: int | None = None,
    heads: int | None = None,
    block_pool: str | None = None,
    seq_len: int | None = None,
    medium_top_k: int | None = None,
    heavy_block: int | None = None,
    medium_block: int | None = None,
    device: str = "auto",
    amp: str = "none",
    task: str | None = None,
    task_noise_frac: float | None = None,
    task_n_keys: int | None = None,
) -> dict[str, object]:
    cfg = ExperimentConfig()
    if mode == "test":
        cfg = ExperimentConfig(steps=20, eval_batches=3, batch_size=4, dim=32, heads=4, depth=1)
    overrides: dict[str, object] = {}
    if seed is not None:
        overrides["seed"] = seed
    if distill_weight > 0:
        overrides["distill_weight"] = distill_weight
    if memory_byte_weight > 0:
        overrides["memory_byte_weight"] = memory_byte_weight
    if selector_distill_weight > 0:
        overrides["selector_distill_weight"] = selector_distill_weight
    if steps is not None:
        overrides["steps"] = steps
    if eval_batches is not None:
        overrides["eval_batches"] = eval_batches
    if assoc_loss_weight is not None:
        overrides["assoc_loss_weight"] = assoc_loss_weight
    if dim is not None:
        overrides["dim"] = dim
    if depth is not None:
        overrides["depth"] = depth
    if batch_size is not None:
        overrides["batch_size"] = batch_size
    if heads is not None:
        overrides["heads"] = heads
    if block_pool is not None:
        overrides["block_pool"] = block_pool
    if seq_len is not None:
        overrides["seq_len"] = seq_len
    if medium_top_k is not None:
        overrides["medium_top_k"] = medium_top_k
    if heavy_block is not None:
        overrides["heavy_block"] = heavy_block
    if medium_block is not None:
        overrides["medium_block"] = medium_block
    overrides["device"] = device
    overrides["amp"] = amp
    if task is not None:
        overrides["task"] = task
    if task_noise_frac is not None:
        overrides["task_noise_frac"] = task_noise_frac
    if task_n_keys is not None:
        overrides["task_n_keys"] = task_n_keys
    if overrides:
        cfg = ExperimentConfig(**{**asdict(cfg), **overrides})
    random.seed(cfg.seed)
    np.random.seed(cfg.seed)
    torch.manual_seed(cfg.seed)
    # Phase 7 cycle 3: honor explicit --device override; fall back to auto-detect.
    if cfg.device == "cuda":
        device = torch.device("cuda")
    elif cfg.device == "cpu":
        device = torch.device("cpu")
    else:  # auto
        device = torch.device("cuda" if torch.cuda.is_available() and mode != "test" else "cpu")
    # Phase 7 cycle 3: util-harness hook (start sampler, run, stop, verify band).
    from project_x.experiments.util_harness import (
        snapshot_baseline,
        start_sampler,
        stop_sampler,
        verify_band,
    )
    util_baseline = snapshot_baseline()
    sampler = start_sampler(run_id) if device.type == "cuda" else None
    try:
        control = train_one("transformer_control", FullCausalAttention, cfg, device)
        candidate = train_one("dual_rate_compressed_memory", DualRateCompressedAttention, cfg, device)
    finally:
        if sampler is not None:
            stop_sampler(sampler)
    util_verdict = verify_band(sampler) if sampler is not None else {
        "band_passed": False, "reason": "device != cuda; util harness inactive"
    }
    control["estimated_memory_bytes"] = estimated_memory_bytes(cfg, candidate=False)
    candidate["estimated_memory_bytes"] = estimated_memory_bytes(cfg, candidate=True)
    loss_regression = (candidate["loss"] - control["loss"]) / max(control["loss"], 1e-9)
    memory_improvement = 1.0 - candidate["estimated_memory_bytes"] / control["estimated_memory_bytes"]
    passed = (
        loss_regression <= 0.03
        and memory_improvement > 0
        and candidate["selector_entropy"] > 0.05
    )
    return {
        "run_id": run_id,
        "mode": mode,
        "device": str(device),
        "amp": cfg.amp,
        "config": asdict(cfg),
        "control": control,
        "candidate": candidate,
        "comparison": {
            "loss_regression": loss_regression,
            "memory_improvement": memory_improvement,
            "passed_initial_gate": passed,
        },
        "util_baseline": util_baseline,
        "util": util_verdict,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["test", "full"], default="test")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--distill-weight", type=float, default=0.0)
    parser.add_argument("--memory-byte-weight", type=float, default=0.0)
    parser.add_argument("--selector-distill-weight", type=float, default=0.0)
    parser.add_argument("--steps", type=int)
    parser.add_argument("--eval-batches", type=int)
    parser.add_argument("--assoc-loss-weight", type=float)
    parser.add_argument("--dim", type=int)
    parser.add_argument("--depth", type=int)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--heads", type=int)
    parser.add_argument("--block-pool", type=str, choices=["mean", "max", "max-keys-mean-vals", "sum"])
    parser.add_argument("--seq-len", type=int)
    parser.add_argument("--medium-top-k", type=int)
    parser.add_argument("--heavy-block", type=int)
    parser.add_argument("--medium-block", type=int)
    parser.add_argument("--device", type=str, choices=["auto", "cuda", "cpu"], default="auto")
    parser.add_argument("--amp", type=str, choices=["none", "bf16", "fp16"], default="none")
    parser.add_argument("--task", type=str, choices=["long-range-copy", "key-noise", "multi-key"], default="long-range-copy")
    parser.add_argument("--task-noise-frac", type=float, default=None, help="key-noise task: fraction of corrupted samples (default 0.10)")
    parser.add_argument("--task-n-keys", type=int, default=None, help="multi-key task: number of keys including truth-key (default 2; ≥2)")
    args = parser.parse_args()
    result = run_experiment(
        args.mode,
        args.run_id,
        seed=args.seed,
        distill_weight=args.distill_weight,
        memory_byte_weight=args.memory_byte_weight,
        selector_distill_weight=args.selector_distill_weight,
        steps=args.steps,
        eval_batches=args.eval_batches,
        assoc_loss_weight=args.assoc_loss_weight,
        dim=args.dim,
        depth=args.depth,
        batch_size=args.batch_size,
        heads=args.heads,
        block_pool=args.block_pool,
        seq_len=args.seq_len,
        medium_top_k=args.medium_top_k,
        heavy_block=args.heavy_block,
        medium_block=args.medium_block,
        device=args.device,
        amp=args.amp,
        task=args.task,
        task_noise_frac=args.task_noise_frac,
        task_n_keys=args.task_n_keys,
    )
    out_dir = pathlib.Path("gpt-codex/runs") / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
