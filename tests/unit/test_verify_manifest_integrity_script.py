import hashlib
import json
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_verify_manifest_integrity_pass(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"frozen": True}), encoding="utf-8")

    sha_path = tmp_path / "manifest.sha256"
    sha_path.write_text(_sha256_bytes(manifest_path.read_bytes()), encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/verify_manifest_integrity.py",
            "--manifest",
            str(manifest_path),
            "--sha256-file",
            str(sha_path),
        ],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_verify_manifest_integrity_sha_mismatch(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"frozen": True}), encoding="utf-8")

    sha_path = tmp_path / "manifest.sha256"
    sha_path.write_text("0" * 64, encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/verify_manifest_integrity.py",
            "--manifest",
            str(manifest_path),
            "--sha256-file",
            str(sha_path),
        ],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr


def test_verify_manifest_integrity_unfrozen_fails(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"frozen": False}), encoding="utf-8")

    sha_path = tmp_path / "manifest.sha256"
    sha_path.write_text(_sha256_bytes(manifest_path.read_bytes()), encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/verify_manifest_integrity.py",
            "--manifest",
            str(manifest_path),
            "--sha256-file",
            str(sha_path),
        ],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr

