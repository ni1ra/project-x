#!/usr/bin/env python3
"""
Energy calibration visibility gate.

BLUEPRINT.md Section 3.1 requires κ constants to be declared up front and
calibration status to be explicit for any "20W-equivalent" claim.

This script prints the manifest energy constants + budgets and can optionally
hard-fail if calibration is required but missing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.energy.proxy import EnergyConfig


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify/print energy proxy calibration status")
    parser.add_argument(
        "--manifest",
        type=str,
        default="benchmarks/rpj_v5_manifest.json",
        help="Path to manifest JSON containing energy constants/budgets",
    )
    parser.add_argument(
        "--require-calibrated",
        action="store_true",
        help="Fail if manifest calibration_status != CALIBRATED",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}")
        return 2

    try:
        cfg = EnergyConfig.from_manifest(manifest_path)
    except Exception as e:
        print(f"ERROR: failed loading energy config from manifest: {e}")
        return 2

    calibration_label = "20W-EQUIVALENT" if cfg.calibrated else "UNCALIBRATED"
    print("============================================================")
    print(f"ENERGY PROXY ({calibration_label})")
    print("============================================================")
    print(f"Manifest:  {manifest_path}")
    print(f"kappa_F:   {cfg.kappa_F:.3e} J/FLOP")
    print(f"kappa_M:   {cfg.kappa_M:.3e} J/Byte")
    print(f"B_max_ep:  {cfg.B_max_ep:.3f} J")
    print(f"B_max_day: {cfg.B_max_day:.3f} J")
    print(f"B_sleep:   {cfg.B_sleep:.3f} J")
    print(f"Calibrated: {'YES' if cfg.calibrated else 'NO'}")
    if not cfg.calibrated:
        print("NOTE: BLUEPRINT.md 3.1 requires calibration logs for a strict 20W-equivalent claim.")
        print("      Current status: UNCALIBRATED ENERGY (proxy is still used internally).")

    if args.require_calibrated and not cfg.calibrated:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
