#!/usr/bin/env python3
"""Fast policy checks for run_organic_wrapper.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def test_default_manifest_outside_allowed_root_is_denied() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_wrapper = repo_root / "scripts" / "run_organic_wrapper.py"

    with tempfile.TemporaryDirectory(prefix="project-x-wrapper-policy-") as tmp:
        fake_project = Path(tmp) / "fake_project"
        fake_scripts = fake_project / "scripts"
        allowed_root = fake_project / "allowed"
        marker = allowed_root / "child-launched.txt"
        run_id = "temp-only-default-manifest-denial"
        default_manifest = (
            fake_project
            / "run"
            / "artifacts"
            / "organic-v0"
            / "run_manifests"
            / f"{run_id}.json"
        )

        fake_scripts.mkdir(parents=True)
        allowed_root.mkdir()
        wrapper = fake_scripts / "run_organic_wrapper.py"
        shutil.copyfile(source_wrapper, wrapper)
        wrapper.chmod(0o755)

        completed = subprocess.run(
            [
                sys.executable,
                str(wrapper),
                "--binary",
                sys.executable,
                "--run-id",
                run_id,
                "--allowed-write-root",
                str(allowed_root),
                "--",
                "-c",
                f"from pathlib import Path; Path({str(marker)!r}).write_text('launched')",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        assert completed.returncode != 0, completed.stdout + completed.stderr
        assert not marker.exists(), "wrapper launched the child despite a denied default manifest"
        assert not default_manifest.exists(), "wrapper wrote the repo default manifest outside allowed roots"


def test_explicit_manifest_inside_allowed_root_is_allowed() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_wrapper = repo_root / "scripts" / "run_organic_wrapper.py"

    with tempfile.TemporaryDirectory(prefix="project-x-wrapper-policy-") as tmp:
        fake_project = Path(tmp) / "fake_project"
        fake_scripts = fake_project / "scripts"
        allowed_root = fake_project / "allowed"
        marker = allowed_root / "child-launched.txt"
        manifest_out = allowed_root / "manifest.json"
        run_id = "temp-only-explicit-manifest"
        default_manifest = (
            fake_project
            / "run"
            / "artifacts"
            / "organic-v0"
            / "run_manifests"
            / f"{run_id}.json"
        )

        fake_scripts.mkdir(parents=True)
        allowed_root.mkdir()
        wrapper = fake_scripts / "run_organic_wrapper.py"
        shutil.copyfile(source_wrapper, wrapper)
        wrapper.chmod(0o755)

        completed = subprocess.run(
            [
                sys.executable,
                str(wrapper),
                "--binary",
                sys.executable,
                "--run-id",
                run_id,
                "--allowed-write-root",
                str(allowed_root),
                "--manifest-out",
                str(manifest_out),
                "--",
                "-c",
                f"from pathlib import Path; Path({str(marker)!r}).write_text('launched')",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        assert completed.returncode == 0, completed.stdout + completed.stderr
        assert marker.exists(), "wrapper did not launch the child for an allowed explicit manifest"
        assert manifest_out.exists(), "wrapper did not write the allowed explicit manifest"
        assert not default_manifest.exists(), "wrapper wrote the repo default manifest outside allowed roots"
        stdout = json.loads(completed.stdout)
        assert stdout["manifest"] == str(manifest_out)
        assert stdout["wrapper_denial"] is False


if __name__ == "__main__":
    test_default_manifest_outside_allowed_root_is_denied()
    test_explicit_manifest_inside_allowed_root_is_allowed()
    print("wrapper policy tests passed")
