#!/usr/bin/env python3
"""
Multi-seed validation runner.

BLUEPRINT.md requires emergence metrics to hold across ≥5 seeds. This script
loads the frozen seed list from the manifest (or an explicit seed list), maps
seeds to checkpoint paths, and runs validation in one of three modes:

  - reproduce: run `bash reproduce.sh <ckpt>` for each seed
  - gates:     run the individual gate scripts (no pytest)
  - smoke:     only verify checkpoints exist + load
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import torch


@dataclass(frozen=True)
class SeedRunResult:
    seed: int
    checkpoint: str
    mode: str
    ok: bool
    returncode: int
    seconds: float
    details: str = ""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_manifest_seeds(manifest_path: Path, seed_set: str) -> List[int]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    seeds = manifest.get("seeds", {}).get(seed_set)
    if not isinstance(seeds, list) or not all(isinstance(s, int) for s in seeds):
        raise ValueError(f"manifest missing seeds.{seed_set} int list")
    return list(seeds)


def _parse_seeds(text: str) -> List[int]:
    seeds: List[int] = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        seeds.append(int(part))
    return seeds


def _checkpoint_paths_from_template(template: str, seeds: Sequence[int]) -> List[str]:
    paths: List[str] = []
    for s in seeds:
        try:
            paths.append(template.format(seed=s))
        except KeyError as e:
            raise ValueError(f"checkpoint template must include {{seed}} placeholder: {e}") from e
    return paths


def _run_smoke(checkpoint: str) -> Tuple[bool, int, str]:
    path = Path(checkpoint)
    if not path.exists():
        return False, 2, "missing checkpoint"
    try:
        ckpt = torch.load(str(path), map_location="cpu")
    except Exception as e:
        return False, 2, f"load failed: {e}"

    if isinstance(ckpt, dict):
        if not any(k in ckpt for k in ("brain_state_dict", "model_state_dict", "state_dict")) and not any(
            isinstance(v, dict) for v in ckpt.values()
        ):
            return False, 2, "checkpoint dict missing recognizable state_dict keys"
    return True, 0, "ok"


def _run_cmd(cmd: List[str], cwd: Path) -> Tuple[bool, int, str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    ok = proc.returncode == 0
    # Truncate details to keep JSON small.
    out = (proc.stdout + "\n" + proc.stderr).strip()
    return ok, proc.returncode, out[-2000:]


def _run_gates(checkpoint: str, cwd: Path) -> Tuple[bool, int, str]:
    py = sys.executable
    cmds = [
        [py, "scripts/check_k_eff.py", "--checkpoint", checkpoint, "--min", "2", "--max", "6", "--window", "5"],
        [py, "scripts/compute_cbr_bimodality.py", "--checkpoint", checkpoint, "--no-save"],
        [py, "scripts/eval_doerr.py", "--checkpoint", checkpoint, "--doerr-max", "0.25", "--discrimination-min", "0.80"],
        [
            py,
            "scripts/eval_od_ndt.py",
            "--checkpoint",
            checkpoint,
            "--num-train-tasks",
            "100",
            "--num-test-tasks",
            "100",
            "--sr-novel-min",
            "0.60",
            "--transfer-min",
            "0.80",
            "--sleep-consolidation",
            "--sleep-steps",
            "50",
            "--sleep-lr",
            "1e-3",
            "--no-save",
        ],
    ]

    combined: List[str] = []
    for cmd in cmds:
        ok, code, out = _run_cmd(cmd, cwd)
        combined.append(f"$ {' '.join(cmd)}\n{out}\n")
        if not ok:
            return False, code, "\n".join(combined)[-2000:]
    return True, 0, "\n".join(combined)[-2000:]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run validation across multiple seeds")
    parser.add_argument(
        "--manifest",
        type=str,
        default="benchmarks/rpj_v5_manifest.json",
        help="Manifest path (default: benchmarks/rpj_v5_manifest.json)",
    )
    parser.add_argument(
        "--seed-set",
        type=str,
        default="development",
        choices=["development", "held_out_eval"],
        help="Which seed list to use from manifest",
    )
    parser.add_argument("--seeds", type=str, default="", help="Override seeds as comma-separated ints")
    parser.add_argument(
        "--min-seeds",
        type=int,
        default=5,
        help="Minimum number of seeds required (default: 5 per BLUEPRINT)",
    )
    parser.add_argument(
        "--checkpoint-template",
        type=str,
        default="",
        help="Checkpoint path template containing {seed} placeholder",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="reproduce",
        choices=["reproduce", "gates", "smoke"],
        help="Validation mode (default: reproduce)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="",
        help="Optional JSON output path to write results",
    )
    args = parser.parse_args()

    cwd = _repo_root()
    manifest_path = (cwd / args.manifest).resolve()
    if args.seeds.strip():
        seeds = _parse_seeds(args.seeds)
    else:
        seeds = _load_manifest_seeds(manifest_path, args.seed_set)

    if len(seeds) < args.min_seeds:
        print(f"ERROR: need at least {args.min_seeds} seeds, got {len(seeds)}", file=sys.stderr)
        return 2

    if not args.checkpoint_template:
        print("ERROR: --checkpoint-template is required (must contain {seed})", file=sys.stderr)
        return 2

    checkpoints = _checkpoint_paths_from_template(args.checkpoint_template, seeds)

    results: List[SeedRunResult] = []
    all_ok = True

    for seed, ckpt in zip(seeds, checkpoints):
        t0 = time.perf_counter()
        if args.mode == "smoke":
            ok, code, details = _run_smoke(ckpt)
        elif args.mode == "gates":
            ok, code, details = _run_gates(ckpt, cwd)
        else:
            ok, code, details = _run_cmd(["bash", "reproduce.sh", ckpt], cwd)

        dt = time.perf_counter() - t0
        results.append(
            SeedRunResult(
                seed=int(seed),
                checkpoint=str(ckpt),
                mode=args.mode,
                ok=bool(ok),
                returncode=int(code),
                seconds=float(dt),
                details=details,
            )
        )
        all_ok = all_ok and ok
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] seed={seed} ckpt={ckpt} ({dt:.1f}s)")

    payload: Dict[str, Any] = {
        "mode": args.mode,
        "manifest": str(manifest_path),
        "seed_set": args.seed_set,
        "seeds": seeds,
        "checkpoint_template": args.checkpoint_template,
        "results": [r.__dict__ for r in results],
        "all_passed": all_ok,
    }

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote: {out_path}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

