#!/usr/bin/env python3
"""
Manifest integrity gate.

Used by reproduce.sh to enforce BLUEPRINT Rule 4.1.A pre-registration:
- the benchmark manifest is marked frozen
- the manifest content matches a pinned SHA256
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_expected_sha256(path: Path) -> str:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("sha256 file is empty")
    return text.split()[0].lower()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify benchmark manifest integrity")
    parser.add_argument(
        "--manifest",
        type=str,
        default="benchmarks/rpj_v5_manifest.json",
        help="Path to manifest JSON",
    )
    parser.add_argument(
        "--sha256-file",
        type=str,
        default="benchmarks/rpj_v5_manifest.sha256",
        help="Path to pinned manifest sha256 (first token = hex digest)",
    )
    parser.add_argument(
        "--allow-unfrozen",
        action="store_true",
        help="Do not fail if manifest['frozen'] is false (NOT recommended)",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    sha_path = Path(args.sha256_file)

    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}")
        return 2
    if not sha_path.exists():
        print(f"ERROR: pinned sha256 not found: {sha_path}")
        return 2

    try:
        expected = _read_expected_sha256(sha_path)
    except Exception as e:
        print(f"ERROR: failed reading sha256 file: {e}")
        return 2

    actual = _sha256_file(manifest_path)
    sha_ok = actual.lower() == expected

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERROR: failed parsing manifest JSON: {e}")
        return 2

    frozen = bool(manifest.get("frozen", False))
    frozen_ok = frozen or args.allow_unfrozen

    status = "PASS" if (sha_ok and frozen_ok) else "FAIL"
    print("============================================================")
    print("MANIFEST INTEGRITY")
    print("============================================================")
    print(f"Manifest: {manifest_path}")
    print(f"Pinned:   {sha_path}")
    print(f"SHA256:   {actual}")
    print(f"Expected: {expected}")
    print(f"Frozen:   {frozen}")
    print(f"Status:   {status}")

    if not sha_ok:
        return 1
    if not frozen_ok:
        print("ERROR: manifest is not marked frozen (set manifest['frozen']=true)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

