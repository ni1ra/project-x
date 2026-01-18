#!/usr/bin/env python3
"""
Evaluate a Jarvis Harness checkpoint on generated repo-debugging tasks.

This is a verifier-grounded, end-to-end loop:
checkpoint -> actions -> env (repo) -> pytest verifier -> success rate.

OPTIMIZED VERSION: Uses vectorized environments for better GPU utilization.

Usage:
  PYTHONPATH=. ./.venv/bin/python scripts/eval_jarvis_harness.py \
    --checkpoint results/jarvis_harness_v2_100000.pt \
    --num-tasks 25 --difficulty hard --mode v2
"""

from __future__ import annotations

import argparse
import math
import os
import random
import shutil
import tempfile
import time
from dataclasses import dataclass
from typing import List, Optional

import torch

from src.core.rpj_brain import create_brain
from src.harness.env import JarvisHarnessEnv, HarnessConfig, Task, VectorizedJarvisEnv
from src.harness.repo_generator import RepoGenerator, BugDifficulty, generate_task_batch
from src.harness.verifiers import run_pytest, compute_diff_size
from src.harness.observations import OBS_TOTAL_BYTES
from src.harness.actions import ACTION_BYTES, ACTION_BYTES_V2, ActionType

# Python path with pytest installed (for running tests)
PYTEST_PYTHON = "/tmp/jarvis_venv/bin/python"


@dataclass
class EpisodeResult:
    success: bool
    steps: int
    total_reward: float
    baseline_tests_passing: int
    baseline_tests_total: int
    tests_passing: int
    tests_total: int
    delta_tests_passing: int
    diff_lines: int
    write_file_actions: int
    write_focus_actions: int
    run_tests_actions: int
    done_reason: str


def run_episode(
    brain,
    env: JarvisHarnessEnv,
    device: torch.device,
    max_steps: int,
    *,
    step_sleep_s: float = 0.0,
) -> EpisodeResult:
    obs = env.reset()

    # Baseline full-suite result for "improved vs initial" metrics.
    baseline = run_pytest(env.temp_dir, python_path=PYTEST_PYTHON) if env.temp_dir else None
    baseline_passing = baseline.tests_passing if baseline is not None else 0
    baseline_total = baseline.tests_total if baseline is not None else 0

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

        if step_sleep_s > 0:
            time.sleep(step_sleep_s)

        if done:
            done_reason = info.get("done_reason", "")
            break

    # Always evaluate final state with pytest (ground truth).
    final = run_pytest(env.temp_dir, python_path=PYTEST_PYTHON) if env.temp_dir else None
    tests_passing = final.tests_passing if final is not None else 0
    tests_total = final.tests_total if final is not None else 0
    success = bool(final.passed) if final is not None else False
    delta_tests_passing = int(tests_passing) - int(baseline_passing)

    # Diff lines (MDL proxy).
    diff_lines = 0
    if env.state is not None:
        for _, (orig, cur) in env.state.file_changes.items():
            changed, _ = compute_diff_size(orig, cur)
            diff_lines += int(changed)

    steps = env.state.step if env.state is not None else 0
    write_file_actions = env.state.write_file_actions if env.state is not None else 0
    write_focus_actions = env.state.write_focus_actions if env.state is not None else 0
    run_tests_actions = env.state.run_tests_actions if env.state is not None else 0
    return EpisodeResult(
        success=success,
        steps=steps,
        total_reward=total_reward,
        baseline_tests_passing=int(baseline_passing),
        baseline_tests_total=int(baseline_total),
        tests_passing=tests_passing,
        tests_total=tests_total,
        delta_tests_passing=int(delta_tests_passing),
        diff_lines=diff_lines,
        write_file_actions=int(write_file_actions),
        write_focus_actions=int(write_focus_actions),
        run_tests_actions=int(run_tests_actions),
        done_reason=done_reason,
    )


def main():
    parser = argparse.ArgumentParser(description="Evaluate Jarvis Harness checkpoint")
    parser.add_argument("--checkpoint", type=str, required=True, help="Path to checkpoint .pt")
    parser.add_argument("--mode", type=str, choices=["v1", "v2"], default="v2", help="Eval mode")
    parser.add_argument("--num-tasks", type=int, default=25, help="Number of tasks to evaluate")
    parser.add_argument("--difficulty", type=str, choices=["trivial", "easy", "medium", "hard"], default="hard")
    parser.add_argument("--force-write-focus", action="store_true",
                        help="Force all actions to WRITE_FOCUS (match training config)")
    parser.add_argument("--no-auto-focus", action="store_true",
                        help="Disable auto-focus on target file (for navigation eval)")
    parser.add_argument("--force-write-focus-prob", type=float, default=1.0,
                        help="Probability of forcing WRITE_FOCUS (1.0=always, 0.0=never)")
    parser.add_argument("--seed", type=int, default=123, help="RNG seed")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--max-steps", type=int, default=100, help="Max tool actions per episode")
    parser.add_argument(
        "--step-sleep-s",
        type=float,
        default=0.0,
        help="Optional per-step sleep to let async verifiers complete (useful for eval realism).",
    )
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
    brain_kwargs = dict(
        obs_dim=OBS_TOTAL_BYTES,
        action_bytes=action_bytes,
        enable_plasticity=False,
        enable_sleep=False,
    )
    if isinstance(cfg, dict):
        hidden_dim = cfg.get("hidden_dim")
        if hidden_dim is not None:
            brain_kwargs["hidden_dim"] = int(hidden_dim)

    brain = create_brain(**brain_kwargs).to(device)
    brain.load_state_dict(ckpt["brain_state_dict"])
    brain.eval()

    # Generate tasks.
    difficulty_map = {
        "trivial": BugDifficulty.TRIVIAL,
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
                bug_line=bug.line_number if bug else None,  # Pre-set focus to bug location
            )
        )

    harness_config = HarnessConfig(
        obs_bytes=OBS_TOTAL_BYTES,
        action_bytes=action_bytes,
        max_steps=args.max_steps,
        max_time_seconds=60,
        # Keep eval fast and avoid redundant pytest at env.reset(); we run full pytest ourselves.
        run_tests_on_reset=False,
        # Mirror training: fast pytest is async and can trigger auto-full when near-solved.
        run_fast_tests=True,
        async_tests=True,
        auto_tests_on_write=True,
        auto_full_tests_on_fast_pass=True,
        test_timeout_seconds=10,
        fast_test_timeout_seconds=2,
        # Match training curriculum config
        force_write_focus=args.force_write_focus,
        force_write_focus_prob=args.force_write_focus_prob,
        # Navigation eval: disable auto-focus on target file
        auto_focus_target=not getattr(args, 'no_auto_focus', False),
    )
    env = JarvisHarnessEnv(harness_config)

    results: List[EpisodeResult] = []
    try:
        for i, task in enumerate(tasks):
            env.set_task(task)
            r = run_episode(brain, env, device, max_steps=args.max_steps, step_sleep_s=float(args.step_sleep_s))
            results.append(r)
            writes = r.write_file_actions + r.write_focus_actions
            print(
                f"[{i+1:03d}/{len(tasks):03d}] "
                f"success={int(r.success)} steps={r.steps} "
                f"base={r.baseline_tests_passing}/{r.baseline_tests_total} "
                f"tests={r.tests_passing}/{r.tests_total} "
                f"delta={r.delta_tests_passing:+d} "
                f"diff={r.diff_lines} writes={writes} run_tests={r.run_tests_actions} "
                f"done={r.done_reason or 'n/a'} reward={r.total_reward:.2f}"
            )
    finally:
        env.close()
        shutil.rmtree(temp_base, ignore_errors=True)

    if not results:
        raise SystemExit("No results")

    success_rate = sum(1 for r in results if r.success) / len(results)
    improved_rate = sum(1 for r in results if r.delta_tests_passing > 0) / len(results)
    wrote_rate = sum(1 for r in results if (r.write_file_actions + r.write_focus_actions) > 0) / len(results)
    diff_rate = sum(1 for r in results if r.diff_lines > 0) / len(results)
    avg_steps = sum(r.steps for r in results) / len(results)
    avg_diff = sum(r.diff_lines for r in results) / len(results)
    avg_writes = sum((r.write_file_actions + r.write_focus_actions) for r in results) / len(results)
    print("\n=== JARVIS HARNESS EVAL ===")
    print(f"Tasks: {len(results)} | Mode: {args.mode} | Difficulty: {args.difficulty}")
    print(f"Success rate: {success_rate:.1%}")
    print(f"Improved tests: {improved_rate:.1%}")
    print(f"Wrote any: {wrote_rate:.1%} | Diff>0: {diff_rate:.1%} | Avg writes: {avg_writes:.1f}")
    print(f"Avg steps: {avg_steps:.1f}")
    print(f"Avg diff lines: {avg_diff:.1f}")


if __name__ == "__main__":
    main()
