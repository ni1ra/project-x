import json
import subprocess
import sys
from pathlib import Path

import torch


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_run_multiseed_validation_smoke(tmp_path: Path):
    for seed in (1, 2):
        torch.save({"brain_state_dict": {}}, tmp_path / f"ckpt_{seed}.pt")

    out_path = tmp_path / "multiseed.json"
    template = str(tmp_path / "ckpt_{seed}.pt")

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_multiseed_validation.py",
            "--seeds",
            "1,2",
            "--min-seeds",
            "2",
            "--checkpoint-template",
            template,
            "--mode",
            "smoke",
            "--out",
            str(out_path),
        ],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["all_passed"] is True
    assert payload["seeds"] == [1, 2]

