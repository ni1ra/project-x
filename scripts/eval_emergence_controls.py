#!/usr/bin/env python3
"""
Emergence confound-control checks for compute bursts (CBR).

Implements BLUEPRINT.md Section 6 "Confound controls for emergence metrics":
  - Shuffled-reward (within-episode permutation)
  - Constant-reward control (episode-mean reward)
  - Statistics: KS test on log(CBR_t) + tail-rate effect size

This script is intentionally lightweight: it replays fixed observation/action
trajectories through a checkpointed RPJBrain while varying only the reward used
for in-episode plasticity updates. Observations/actions are preserved.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.benchmarks.ccb import TorchCCBEnvironment
from src.benchmarks.multitask_ccb import TorchMultiTaskCCBEnvironment
from src.core.byte_interface import phi
from src.core.rpj_brain import RPJBrain, RPJConfig


@dataclass(frozen=True)
class Transition:
    obs: torch.Tensor  # [1, obs_dim] long
    next_obs: torch.Tensor  # [1, obs_dim] long
    action: torch.Tensor  # [1, action_bytes] long
    reward: float


def _pearson_corr(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if x.size != y.size or x.size < 2:
        return float("nan")
    x = x - x.mean()
    y = y - y.mean()
    denom = (np.sqrt((x * x).sum()) * np.sqrt((y * y).sum()))
    if denom < 1e-12:
        return 0.0
    return float((x * y).sum() / denom)


def _ks_2samp_d(x: np.ndarray, y: np.ndarray) -> float:
    """Two-sample KS D statistic (no SciPy dependency)."""
    x = np.sort(np.asarray(x, dtype=np.float64))
    y = np.sort(np.asarray(y, dtype=np.float64))
    n1 = x.size
    n2 = y.size
    if n1 == 0 or n2 == 0:
        return 0.0

    all_vals = np.sort(np.concatenate([x, y], axis=0))
    cdf1 = np.searchsorted(x, all_vals, side="right") / n1
    cdf2 = np.searchsorted(y, all_vals, side="right") / n2
    return float(np.max(np.abs(cdf1 - cdf2)))


def _ks_2samp_pvalue(d: float, n1: int, n2: int) -> float:
    """
    Approximate two-sample KS p-value via the Kolmogorov distribution.

    Uses the common asymptotic approximation with the Stephens correction.
    """
    if n1 <= 0 or n2 <= 0:
        return 1.0
    n_eff = (n1 * n2) / (n1 + n2)
    if n_eff <= 0:
        return 1.0

    en = math.sqrt(n_eff)
    lam = (en + 0.12 + 0.11 / en) * d
    if lam <= 0:
        return 1.0

    # 2 * sum_{j>=1} (-1)^{j-1} exp(-2 j^2 lam^2)
    s = 0.0
    for j in range(1, 200):
        term = math.exp(-2.0 * (j * j) * (lam * lam))
        s += term if (j % 2 == 1) else -term
        if term < 1e-12:
            break
    p = max(0.0, min(1.0, 2.0 * s))
    return float(p)


def _tail_effect_size(
    baseline_log_cbr: np.ndarray,
    control_log_cbr: np.ndarray,
    *,
    q: float,
) -> Tuple[float, float, float]:
    """
    Effect size on high-burst tail rate using Cohen's d over a binary indicator.

    Threshold is the baseline q-quantile of log(CBR).
    """
    baseline_log_cbr = np.asarray(baseline_log_cbr, dtype=np.float64)
    control_log_cbr = np.asarray(control_log_cbr, dtype=np.float64)
    if baseline_log_cbr.size == 0 or control_log_cbr.size == 0:
        return 0.0, 0.0, float("nan")

    thr = float(np.quantile(baseline_log_cbr, q))
    b = (baseline_log_cbr > thr).astype(np.float64)
    c = (control_log_cbr > thr).astype(np.float64)
    p_b = float(b.mean())
    p_c = float(c.mean())
    pooled = math.sqrt(((p_b * (1 - p_b)) + (p_c * (1 - p_c))) / 2.0)
    if pooled < 1e-12:
        d = 0.0 if abs(p_b - p_c) < 1e-12 else float("inf")
    else:
        d = (p_b - p_c) / pooled
    return p_b, p_c, float(d)


def _infer_config_from_checkpoint(checkpoint: dict, state_dict: dict) -> RPJConfig:
    ckpt_cfg = checkpoint.get("config", {}) if isinstance(checkpoint, dict) else {}
    if not isinstance(ckpt_cfg, dict):
        ckpt_cfg = {}

    latent_dim = ckpt_cfg.get("latent_dim")
    if latent_dim is None:
        for key in ("vae.encoder_online.W_mu.weight", "vae.encoder_target.W_mu.weight"):
            if key in state_dict and getattr(state_dict[key], "dim", lambda: 0)() == 2:
                latent_dim = int(state_dict[key].shape[0])
                break

    config = RPJConfig(
        obs_dim=int(ckpt_cfg.get("obs_dim", 2)),
        action_bytes=int(ckpt_cfg.get("action_bytes", 1)),
        hidden_dim=int(ckpt_cfg.get("hidden_dim", 512)),
        k_max=int(ckpt_cfg.get("k_max", 16)),
    )
    if latent_dim is not None:
        config.latent_dim = int(latent_dim)

    has_plasticity = any("plasticity." in k for k in state_dict.keys())
    has_sleep = any("sleep." in k for k in state_dict.keys())
    config.enable_plasticity = bool(has_plasticity)
    config.enable_sleep = bool(has_sleep)
    config.num_envs = 1  # evaluation/replay is single-env
    return config


def _load_checkpoint(path: str, device: str) -> Tuple[RPJBrain, dict]:
    checkpoint = torch.load(path, map_location=device)

    if isinstance(checkpoint, dict):
        if "brain_state_dict" in checkpoint:
            state_dict = checkpoint["brain_state_dict"]
        elif "model_state_dict" in checkpoint:
            state_dict = checkpoint["model_state_dict"]
        elif "state_dict" in checkpoint:
            state_dict = checkpoint["state_dict"]
        else:
            state_dict = checkpoint
    else:
        state_dict = checkpoint

    config = _infer_config_from_checkpoint(checkpoint if isinstance(checkpoint, dict) else {}, state_dict)

    brain = RPJBrain(config).to(device)

    # Skip fast-weight buffers if the checkpoint used batched plasticity.
    filtered = {}
    for k, v in state_dict.items():
        if ("adapter.A" in k or "adapter.B" in k) and getattr(v, "dim", lambda: 0)() == 3:
            continue
        filtered[k] = v
    brain.load_state_dict(filtered, strict=False)
    brain.eval()

    # Ensure fast-weight buffers are float32 (safety when loading mixed dtypes).
    if brain.plasticity is not None:
        brain.plasticity.recurrent_adapter.A = brain.plasticity.recurrent_adapter.A.float()
        brain.plasticity.recurrent_adapter.B = brain.plasticity.recurrent_adapter.B.float()
        brain.plasticity.action_adapter.A = brain.plasticity.action_adapter.A.float()
        brain.plasticity.action_adapter.B = brain.plasticity.action_adapter.B.float()

    return brain, checkpoint if isinstance(checkpoint, dict) else {}


def _make_env(ckpt_cfg: dict, device: str) -> torch.nn.Module:
    is_multitask = bool(ckpt_cfg.get("multitask", False))
    if is_multitask:
        env_num_tasks = int(ckpt_cfg.get("num_tasks", 100))
        return TorchMultiTaskCCBEnvironment(
            num_envs=1,
            num_tasks=env_num_tasks,
            device=device,
            seed=int(ckpt_cfg.get("seed", 42)),
            switch_interval=10**9,
        )
    return TorchCCBEnvironment(num_envs=1, device=device, nonlinear=True)


def _collect_episodes(
    brain: RPJBrain,
    env: torch.nn.Module,
    *,
    episodes: int,
    device: str,
) -> List[List[Transition]]:
    """
    Collect fixed trajectories (obs/actions) with in-episode plasticity enabled.

    Returns a list of episodes, each a list of Transitions.
    """
    transitions: List[List[Transition]] = []
    num_steps = int(getattr(env, "num_interventions", 5))

    for _ in range(episodes):
        obs = env.reset()
        if obs.dim() == 1:
            obs = obs.unsqueeze(0)
        obs = obs.to(device)

        h, g = brain.init_state(1, torch.device(device))
        a_prev = torch.zeros((1, brain.config.action_bytes), dtype=torch.long, device=device)

        ep: List[Transition] = []
        for _t in range(num_steps):
            with torch.no_grad():
                out = brain(obs, h, g, a_prev, training=False)
                action = out.action  # [1, action_bytes]
                env_action = action.squeeze(-1) if action.shape[-1] == 1 else action
                next_obs, reward, done, info = env.step(env_action)
                if next_obs.dim() == 1:
                    next_obs = next_obs.unsqueeze(0)
                next_obs = next_obs.to(device)

                next_out = brain(next_obs, out.h_next, out.g_t, action, training=False)

            # In-episode plasticity update (fast weights only).
            if brain.plasticity is not None:
                phi_o_next = phi(next_obs)
                brain.update_plasticity(
                    h_t=out.h_next,
                    phi_o_next=phi_o_next,
                    reward=reward,
                    value=out.value,
                    value_next=next_out.value,
                    g_t=out.g_t,
                )

            ep.append(
                Transition(
                    obs=obs.detach().cpu(),
                    next_obs=next_obs.detach().cpu(),
                    action=action.detach().cpu(),
                    reward=float(reward.item()) if hasattr(reward, "item") else float(reward),
                )
            )

            obs = next_obs
            h = out.h_next
            g = out.g_t
            a_prev = action

        transitions.append(ep)

    return transitions


def _replay_condition(
    brain: RPJBrain,
    episodes: List[List[Transition]],
    *,
    mode: str,
    rng: np.random.Generator,
    device: str,
) -> Dict[str, np.ndarray]:
    """
    Replay fixed obs/actions while varying only the reward used for plasticity.
    """
    assert mode in {"true", "shuffled", "constant"}
    log_cbr: List[float] = []
    rewards_used: List[float] = []
    td_abs: List[float] = []
    pred_loss: List[float] = []

    for ep in episodes:
        r_seq = np.array([t.reward for t in ep], dtype=np.float64)
        if mode == "true":
            r_used = r_seq
        elif mode == "shuffled":
            r_used = r_seq[rng.permutation(len(r_seq))]
        else:  # constant
            r_used = np.full_like(r_seq, float(r_seq.mean()) if r_seq.size else 0.0)

        h, g = brain.init_state(1, torch.device(device))
        a_prev = torch.zeros((1, brain.config.action_bytes), dtype=torch.long, device=device)

        for i, tr in enumerate(ep):
            obs = tr.obs.to(device)
            next_obs = tr.next_obs.to(device)
            action = tr.action.to(device)
            reward_t = torch.tensor([float(r_used[i])], device=device)

            with torch.no_grad():
                out = brain(obs, h, g, a_prev, training=False)
                next_out = brain(next_obs, out.h_next, out.g_t, action, training=False)

            cbr = float(out.cbr_t.item()) if hasattr(out.cbr_t, "item") else float(out.cbr_t)
            log_cbr.append(float(math.log(max(cbr, 1e-12))))
            rewards_used.append(float(r_used[i]))

            td = reward_t + brain.config.gamma * next_out.value - out.value
            td_abs.append(float(td.abs().item()))

            if brain.plasticity is not None:
                phi_o_next = phi(next_obs)
                pl = brain.plasticity.obs_predictor.prediction_loss(out.h_next, phi_o_next)
                pred_loss.append(float(pl.item()))
                brain.update_plasticity(
                    h_t=out.h_next,
                    phi_o_next=phi_o_next,
                    reward=reward_t,
                    value=out.value,
                    value_next=next_out.value,
                    g_t=out.g_t,
                )
            else:
                pred_loss.append(0.0)

            h = out.h_next
            g = out.g_t
            a_prev = action

    return {
        "log_cbr": np.asarray(log_cbr, dtype=np.float64),
        "reward": np.asarray(rewards_used, dtype=np.float64),
        "td_abs": np.asarray(td_abs, dtype=np.float64),
        "pred_loss": np.asarray(pred_loss, dtype=np.float64),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate emergence confound controls (CBR)")
    parser.add_argument(
        "--checkpoint",
        type=str,
        default="results/checkpoint_multitask_ccb_final_50331648.pt",
        help="Path to checkpoint .pt file",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=("cuda" if torch.cuda.is_available() else "cpu"),
        help="Device to use (cpu or cuda)",
    )
    parser.add_argument("--episodes", type=int, default=200, help="Number of episodes to sample")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (controls shuffle)")
    parser.add_argument("--alpha", type=float, default=0.01, help="KS test threshold (default: 0.01)")
    parser.add_argument("--tail-q", type=float, default=0.90, help="Tail quantile for tail-rate effect (default: 0.90)")
    parser.add_argument("--effect-min", type=float, default=0.50, help="Min |d| tail effect size (default: 0.50)")
    args = parser.parse_args()

    device = args.device
    if device.startswith("cuda") and not torch.cuda.is_available():
        device = "cpu"

    # Determinism for env sampling and replay shuffles.
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    np.random.seed(args.seed)

    brain, ckpt_cfg = _load_checkpoint(args.checkpoint, device)
    env = _make_env(ckpt_cfg.get("config", {}) if isinstance(ckpt_cfg, dict) else {}, device)

    rng = np.random.default_rng(args.seed)

    print("=" * 70)
    print("EMERGENCE CONTROLS (CBR)")
    print("=" * 70)
    print(f"Checkpoint: {args.checkpoint}")
    print(f"Device:     {device}")
    print(f"Episodes:   {args.episodes}")
    print(f"Plasticity: {'ENABLED' if brain.plasticity is not None else 'DISABLED'}")

    episodes = _collect_episodes(brain, env, episodes=args.episodes, device=device)

    base = _replay_condition(brain, episodes, mode="true", rng=rng, device=device)
    shuffled = _replay_condition(brain, episodes, mode="shuffled", rng=rng, device=device)
    constant = _replay_condition(brain, episodes, mode="constant", rng=rng, device=device)

    baseline_log_cbr = base["log_cbr"]
    results = []
    for name, ctrl in [("shuffled_reward", shuffled), ("constant_reward", constant)]:
        d = _ks_2samp_d(baseline_log_cbr, ctrl["log_cbr"])
        p = _ks_2samp_pvalue(d, baseline_log_cbr.size, ctrl["log_cbr"].size)
        p_b, p_c, tail_d = _tail_effect_size(baseline_log_cbr, ctrl["log_cbr"], q=args.tail_q)
        ok = (p < args.alpha) and (abs(tail_d) > args.effect_min)
        results.append((name, d, p, p_b, p_c, tail_d, ok))

    print("\n== KS + Tail Tests (log CBR) ==")
    overall_ok = True
    for name, d, p, p_b, p_c, tail_d, ok in results:
        overall_ok = overall_ok and ok
        print(
            f"- {name}: KS_D={d:.4f} p={p:.3g} | tail@q={args.tail_q:.2f}: "
            f"p_base={p_b:.3f} p_ctrl={p_c:.3f} d={tail_d:.3f} | {'PASS' if ok else 'FAIL'}"
        )

    print("\n== Stakes-Decoupling Diagnostics (baseline) ==")
    corr_reward = _pearson_corr(base["log_cbr"], base["reward"])
    corr_td = _pearson_corr(base["log_cbr"], base["td_abs"])
    corr_pred = _pearson_corr(base["log_cbr"], base["pred_loss"])
    print(f"- corr(log CBR, reward):    {corr_reward:.3f}")
    print(f"- corr(log CBR, |TD error|): {corr_td:.3f}")
    print(f"- corr(log CBR, pred_loss): {corr_pred:.3f}")

    print("\n== Verdict ==")
    print("PASS" if overall_ok else "FAIL")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
