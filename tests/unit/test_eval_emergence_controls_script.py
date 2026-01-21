import subprocess
import sys
from pathlib import Path

import torch

from src.core.rpj_brain import RPJBrain, RPJConfig


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_eval_emergence_controls_fails_without_plasticity(tmp_path: Path):
    """
    If in-episode plasticity is disabled, reward shuffling cannot affect compute
    dynamics; the control distributions should match baseline and the script
    must FAIL its KS/tail checks.
    """
    ckpt_path = tmp_path / "ckpt.pt"

    config = RPJConfig(
        obs_dim=2,
        action_bytes=1,
        enable_plasticity=False,
        enable_sleep=False,
    )
    brain = RPJBrain(config)
    torch.save(
        {
            "brain_state_dict": brain.state_dict(),
            "config": {
                "obs_dim": config.obs_dim,
                "action_bytes": config.action_bytes,
                "hidden_dim": config.hidden_dim,
                "k_max": config.k_max,
                "multitask": True,
                "num_tasks": 10,
            },
        },
        ckpt_path,
    )

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/eval_emergence_controls.py",
            "--checkpoint",
            str(ckpt_path),
            "--device",
            "cpu",
            "--episodes",
            "5",
            "--seed",
            "0",
        ],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "EMERGENCE CONTROLS" in proc.stdout

