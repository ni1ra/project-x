#!/usr/bin/env python3
"""
K_eff gate for a trained checkpoint.

This is a small helper used by reproduce scripts to hard-fail if K_eff drifts
outside the BLUEPRINT/manifest target band.
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
import torch


def main() -> int:
    parser = argparse.ArgumentParser(description="Check K_eff band for a checkpoint")
    parser.add_argument(
        "--checkpoint",
        type=str,
        default="results/checkpoint_multitask_ccb_final_50331648.pt",
        help="Path to checkpoint .pt file",
    )
    parser.add_argument("--min", dest="k_min", type=float, default=2.0, help="Minimum allowed K_eff")
    parser.add_argument("--max", dest="k_max", type=float, default=6.0, help="Maximum allowed K_eff")
    parser.add_argument(
        "--window",
        type=int,
        default=5,
        help="Average of last N history points (default: 5)",
    )
    args = parser.parse_args()

    ckpt = torch.load(args.checkpoint, map_location="cpu")
    history = ckpt.get("k_eff_history")
    if not history:
        print("ERROR: checkpoint missing k_eff_history; cannot gate K_eff")
        return 2

    window = max(1, min(args.window, len(history)))
    k_eff = float(np.mean(history[-window:]))

    passed = args.k_min <= k_eff <= args.k_max
    print(f"K_eff (last {window} mean): {k_eff:.4f} | target [{args.k_min}, {args.k_max}] | {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

