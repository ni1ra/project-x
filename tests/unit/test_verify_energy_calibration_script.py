import json
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _write_manifest(path: Path, *, calibration_status: str) -> None:
    manifest = {
        "energy_constants": {
            "kappa_F": 1e-9,
            "kappa_M": 5e-11,
            "calibration_status": calibration_status,
        },
        "budgets": {
            "B_max_ep": 200,
            "B_max_day": 72000,
            "B_sleep": 100,
        },
    }
    path.write_text(json.dumps(manifest), encoding="utf-8")


def test_verify_energy_calibration_uncalibrated_ok_by_default(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, calibration_status="UNCALIBRATED")

    proc = subprocess.run(
        [sys.executable, "scripts/verify_energy_calibration.py", "--manifest", str(manifest_path)],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_verify_energy_calibration_require_calibrated_fails(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, calibration_status="UNCALIBRATED")

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/verify_energy_calibration.py",
            "--manifest",
            str(manifest_path),
            "--require-calibrated",
        ],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr


def test_verify_energy_calibration_calibrated_passes(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, calibration_status="CALIBRATED")

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/verify_energy_calibration.py",
            "--manifest",
            str(manifest_path),
            "--require-calibrated",
        ],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

