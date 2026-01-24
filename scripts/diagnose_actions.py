#!/usr/bin/env python3
"""
Diagnostic script to understand why Phase 9 model produces 0 diff.

This script:
1. Loads the checkpoint
2. Generates a few tasks
3. Runs the model and prints FULL action bytes for each step
4. Shows what vocab_idx and offset values are being produced
"""

import os
import sys
import tempfile
import torch

from src.core.rpj_brain import create_brain
from src.harness.env import JarvisHarnessEnv, HarnessConfig, Task
from src.harness.repo_generator import RepoGenerator, BugDifficulty, generate_task_batch
from src.harness.observations import OBS_TOTAL_BYTES
from src.harness.actions import (
    ACTION_BYTES_V2, ActionType, decode_action_v2, COMBINED_VOCAB, TRIVIAL_VOCAB
)


def main():
    checkpoint_path = sys.argv[1] if len(sys.argv) > 1 else "results/jarvis_harness_v2_50000.pt"

    if not os.path.exists(checkpoint_path):
        print(f"Checkpoint not found: {checkpoint_path}")
        return

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(checkpoint_path, map_location=device)

    # Get config from checkpoint
    cfg = ckpt.get("config", {}) if isinstance(ckpt, dict) else {}
    action_bytes = cfg.get("action_bytes", 32)  # Match checkpoint
    print(f"Checkpoint action_bytes: {action_bytes}")

    # Get vocab_size from checkpoint
    state_dict = ckpt["brain_state_dict"]
    vocab_size = 5  # Default
    vocab_head_key = "action_decoder.vocab_head.classifier.5.weight"
    if vocab_head_key in state_dict:
        vocab_size = state_dict[vocab_head_key].shape[0]
    print(f"Checkpoint vocab_size: {vocab_size}")

    # Create brain with matching config
    brain = create_brain(
        obs_dim=OBS_TOTAL_BYTES,
        action_bytes=action_bytes,  # Match checkpoint!
        enable_plasticity=False,
        enable_sleep=False,
        vocab_size=vocab_size,
    ).to(device)
    brain.load_state_dict(ckpt["brain_state_dict"])
    brain.eval()

    # Generate a few tasks
    temp_base = tempfile.mkdtemp(prefix="jarvis_diag_")
    gen = RepoGenerator(seed=42)
    repos = generate_task_batch(
        num_tasks=3,
        difficulty_range=(BugDifficulty.HARD, BugDifficulty.HARD),
        seed=42,
    )

    print(f"\n=== VOCAB INFO ===")
    print(f"TRIVIAL_VOCAB ({len(TRIVIAL_VOCAB)}): {TRIVIAL_VOCAB}")
    print(f"COMBINED_VOCAB ({len(COMBINED_VOCAB)}): {COMBINED_VOCAB}")

    harness_config = HarnessConfig(
        obs_bytes=OBS_TOTAL_BYTES,
        action_bytes=action_bytes,  # Match checkpoint!
        max_steps=10,
        max_time_seconds=30,
        run_tests_on_reset=False,
        auto_focus_target=True,
    )
    env = JarvisHarnessEnv(harness_config)

    for repo_idx, repo in enumerate(repos):
        print(f"\n{'='*60}")
        print(f"=== REPO {repo_idx+1}: {repo.name} ===")
        print(f"Bug type: {repo.bugs[0].template.name if repo.bugs else 'unknown'}")
        print(f"Fix hint: {repo.fix_description}")

        repo_path = gen.write_to_disk(repo, temp_base)
        bug = repo.bugs[0] if repo.bugs else None
        task = Task(
            name=repo.name,
            description=f"Fix bugs. Hint: {repo.fix_description}",
            repo_path=repo_path,
            target_file=bug.file_path if bug else "models.py",
            bug_line=bug.line_number if bug else None,
        )
        env.set_task(task)
        obs = env.reset()

        # Show focus info
        print(f"Focus file: {env.state.focus_file}")
        print(f"Focus offset: {env.state.focus_offset}")
        print(f"Focus text (first 100 chars): {repr(env.state.focus_text[:100])}")

        h, g = brain.init_state(batch_size=1, device=device)
        a_prev = torch.zeros((1, brain.config.action_bytes), dtype=torch.long, device=device)

        for step in range(5):
            obs_b = obs.unsqueeze(0).to(device)
            with torch.no_grad():
                out = brain(obs_b, h, g, a_prev, training=False)

            action_bytes = out.action.clamp(0, 255).squeeze(0).cpu()

            # Decode action
            action = decode_action_v2(action_bytes.to(torch.uint8))

            # Extract key bytes
            action_type = action_bytes[0].item()
            offset = action_bytes[1].item()
            length = action_bytes[3].item() % 4
            vocab_idx_raw = action_bytes[25].item()
            vocab_mode = action_bytes[26].item()

            if vocab_mode == 1:
                vocab_idx = vocab_idx_raw % 219  # MICRO_VOCAB
                vocab_name = "MICRO"
            else:
                vocab_idx = vocab_idx_raw % len(COMBINED_VOCAB)
                vocab_name = "COMBINED"

            content = action.content

            print(f"\n  Step {step+1}:")
            print(f"    action_type: {action_type} ({ActionType(action_type % len(ActionType)).name})")
            print(f"    offset: {offset}")
            print(f"    length: {length}")
            print(f"    vocab_idx_raw: {vocab_idx_raw} -> {vocab_idx} ({vocab_name})")
            print(f"    content: {repr(content)}")
            print(f"    Full decoded: {action}")

            # Take the step
            obs, reward, done, info = env.step(action_bytes.to(torch.uint8))
            print(f"    Reward: {reward:.3f}, Changed: {env.state.last_edit_changed}, Done: {done}")

            if done:
                print(f"    Done reason: {info.get('done_reason', 'n/a')}")
                break

            h = out.h_next
            g = out.g_t
            a_prev = out.action

        # Check final diff
        diff_lines = 0
        for _, (orig, cur) in env.state.file_changes.items():
            from src.harness.verifiers import compute_diff_size
            changed, _ = compute_diff_size(orig, cur)
            diff_lines += changed
        print(f"\n  Final diff lines: {diff_lines}")

    env.close()
    import shutil
    shutil.rmtree(temp_base, ignore_errors=True)

    print("\n=== DIAGNOSIS COMPLETE ===")


if __name__ == "__main__":
    main()
