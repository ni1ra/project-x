#!/usr/bin/env python3
"""
Evaluate a Jarvis Harness checkpoint on generated repo-debugging tasks.

This is a verifier-grounded, end-to-end loop:
checkpoint -> actions -> env (repo) -> pytest verifier -> success rate.

Usage:
  PYTHONPATH=. ./.venv/bin/python scripts/eval_jarvis_harness.py \
    --checkpoint results/jarvis_harness_v2_100000.pt \
    --num-tasks 25 --difficulty hard --mode v2
"""

from __future__ import annotations

import argparse
import os
import random
import shutil
import tempfile
from dataclasses import dataclass
from typing import List, Optional

import torch

from src.core.rpj_brain import create_brain
from src.harness.env import JarvisHarnessEnv, HarnessConfig, Task
from src.harness.repo_generator import RepoGenerator, BugDifficulty, generate_task_batch
from src.harness.verifiers import run_pytest, compute_diff_size
from src.harness.observations import OBS_TOTAL_BYTES
from src.harness.actions import ACTION_BYTES, ACTION_BYTES_V2, ActionType


@dataclass
class EpisodeResult:
    success: bool
    steps: int
    total_reward: float
    tests_passing: int
    tests_total: int
    diff_lines: int
    done_reason: str


def run_episode(
    brain,
    env: JarvisHarnessEnv,
    device: torch.device,
    max_steps: int,
) -> EpisodeResult:
    obs = env.reset()

    h, g = brain.init_state(batch_size=1, device=device)
    a_prev = torch.zeros((1, brain.config.action_bytes), dtype=torch.long, device=device)

    total_reward = 0.0
    done = False
    done_reason = ""

    for _ in range(max_steps):
        obs_b = obs.unsqueeze(0).to(device)
        with torch.no_grad():
            out = brain(obs_b, h, g, a_prev, training=False)

        action_bytes = out.action.clamp(0, 255).to(torch.uint8).squeeze(0).cpu()
        obs, reward, done, info = env.step(action_bytes)
        total_reward += float(reward)

        h = out.h_next
        g = out.g_t
        a_prev = out.action

        if done:
            done_reason = info.get("done_reason", "")
            break

    # Always evaluate final state with pytest (ground truth).
    final = run_pytest(env.temp_dir) if env.temp_dir else None
    tests_passing = final.tests_passing if final is not None else 0
    tests_total = final.tests_total if final is not None else 0
    success = bool(final.passed) if final is not None else False

    # Diff lines (MDL proxy).
    diff_lines = 0
    if env.state is not None:
        for _, (orig, cur) in env.state.file_changes.items():
            changed, _ = compute_diff_size(orig, cur)
            diff_lines += int(changed)

    steps = env.state.step if env.state is not None else 0
    return EpisodeResult(
        success=success,
        steps=steps,
        total_reward=total_reward,
        tests_passing=tests_passing,
        tests_total=tests_total,
        diff_lines=diff_lines,
        done_reason=done_reason,
    )


def main():
    parser = argparse.ArgumentParser(description="Evaluate Jarvis Harness checkpoint")
    parser.add_argument("--checkpoint", type=str, required=True, help="Path to checkpoint .pt")
    parser.add_argument("--mode", type=str, choices=["v1", "v2"], default="v2", help="Eval mode")
    parser.add_argument("--num-tasks", type=int, default=25, help="Number of tasks to evaluate")
    parser.add_argument("--difficulty", type=str, choices=["easy", "medium", "hard"], default="hard")
    parser.add_argument("--seed", type=int, default=123, help="RNG seed")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--max-steps", type=int, default=100, help="Max tool actions per episode")
    args = parser.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)

    device = torch.device(args.device)
    ckpt = torch.load(args.checkpoint, map_location=device)

    # Infer action bytes from checkpoint if present.
    action_bytes = None
    cfg = ckpt.get("config", {}) if isinstance(ckpt, dict) else {}
    if isinstance(cfg, dict):
        action_bytes = cfg.get("action_bytes")
    if action_bytes is None:
        action_bytes = ACTION_BYTES_V2 if args.mode == "v2" else ACTION_BYTES
    action_bytes = int(action_bytes)

    # Create brain and load weights.
    brain = create_brain(
        obs_dim=OBS_TOTAL_BYTES,
        action_bytes=action_bytes,
        enable_plasticity=False,
        enable_sleep=False,
    ).to(device)
    brain.load_state_dict(ckpt["brain_state_dict"])
    brain.eval()

    # Generate tasks.
    difficulty_map = {
        "easy": BugDifficulty.EASY,
        "medium": BugDifficulty.MEDIUM,
        "hard": BugDifficulty.HARD,
    }
    difficulty = difficulty_map[args.difficulty]

    temp_base = tempfile.mkdtemp(prefix="jarvis_eval_")
    gen = RepoGenerator(seed=args.seed)
    repos = generate_task_batch(
        num_tasks=args.num_tasks,
        difficulty_range=(difficulty, difficulty),
        seed=args.seed,
    )

    tasks: List[Task] = []
    for repo in repos:
        repo_path = gen.write_to_disk(repo, temp_base)
        bug = repo.bugs[0] if repo.bugs else None
        tasks.append(
            Task(
                name=repo.name,
                description=f"Fix the bugs and make tests pass. Hint: {repo.fix_description}",
                repo_path=repo_path,
                target_file=bug.file_path if bug else "models.py",
            )
        )

    harness_config = HarnessConfig(
        obs_bytes=OBS_TOTAL_BYTES,
        action_bytes=action_bytes,
        max_steps=args.max_steps,
        max_time_seconds=60,
    )
    env = JarvisHarnessEnv(harness_config)

    results: List[EpisodeResult] = []
    try:
        for i, task in enumerate(tasks):
            env.set_task(task)
            r = run_episode(brain, env, device, max_steps=args.max_steps)
            results.append(r)
            print(
                f"[{i+1:03d}/{len(tasks):03d}] "
                f"success={int(r.success)} steps={r.steps} "
                f"tests={r.tests_passing}/{r.tests_total} diff={r.diff_lines} "
                f"done={r.done_reason or 'n/a'} reward={r.total_reward:.2f}"
            )
    finally:
        env.close()
        shutil.rmtree(temp_base, ignore_errors=True)

    if not results:
        raise SystemExit("No results")

    success_rate = sum(1 for r in results if r.success) / len(results)
    avg_steps = sum(r.steps for r in results) / len(results)
    avg_diff = sum(r.diff_lines for r in results) / len(results)
    print("\n=== JARVIS HARNESS EVAL ===")
    print(f"Tasks: {len(results)} | Mode: {args.mode} | Difficulty: {args.difficulty}")
    print(f"Success rate: {success_rate:.1%}")
    print(f"Avg steps: {avg_steps:.1f}")
    print(f"Avg diff lines: {avg_diff:.1f}")


if __name__ == "__main__":
    main()

