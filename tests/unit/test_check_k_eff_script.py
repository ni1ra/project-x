import subprocess
import sys
from pathlib import Path

import torch


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_check_k_eff_pass(tmp_path: Path):
    ckpt_path = tmp_path / "ckpt.pt"
    torch.save({"k_eff_history": [3.0, 4.0, 5.0, 4.5, 4.7]}, ckpt_path)

    proc = subprocess.run(
        [sys.executable, "scripts/check_k_eff.py", "--checkpoint", str(ckpt_path), "--min", "2", "--max", "6", "--window", "5"],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_check_k_eff_fail(tmp_path: Path):
    ckpt_path = tmp_path / "ckpt.pt"
    torch.save({"k_eff_history": [7.0, 7.1, 7.2]}, ckpt_path)

    proc = subprocess.run(
        [sys.executable, "scripts/check_k_eff.py", "--checkpoint", str(ckpt_path), "--min", "2", "--max", "6", "--window", "3"],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr


def test_check_k_eff_missing_history(tmp_path: Path):
    ckpt_path = tmp_path / "ckpt.pt"
    torch.save({"not_k_eff_history": []}, ckpt_path)

    proc = subprocess.run(
        [sys.executable, "scripts/check_k_eff.py", "--checkpoint", str(ckpt_path)],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr

