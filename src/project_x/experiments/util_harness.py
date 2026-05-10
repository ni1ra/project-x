"""Util harness for Phase 7 — pre/during/post nvidia-smi sampling.

Wraps a substantive run with a background nvidia-smi sampler, computes mean GPU
utilization across the run's wall-time, and verifies the run hit the 70-90%
util band (#00b lain spec, /godify phase 7).

Public API:
    start_sampler(run_id) -> SamplerHandle  # spawns background nvidia-smi -l 2
    stop_sampler(handle)                    # kills the sampler
    verify_band(handle) -> dict             # parses log, returns util stats + band_passed
    snapshot_baseline() -> dict             # one-shot pre-run nvidia-smi/free/top

Cells failing the band (mean_gpu < 70 or sustained max > 95) are INVALID — the
run is not actually exercising the GPU at the intended scale, and the result
should be re-tuned (bigger batch / model / seq) and re-run.

The sampler writes CSV to /tmp/util-<run_id>.log. Output rows:
    timestamp, utilization.gpu [%], utilization.memory [%], memory.used [MiB], temperature.gpu

Graceful degradation: if nvidia-smi is missing (CPU-only host), start_sampler
returns a no-op handle and verify_band returns {band_passed: False, reason:
"no nvidia-smi available"}.
"""
from __future__ import annotations

import csv
import os
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class SamplerHandle:
    run_id: str
    log_path: str
    pid: Optional[int]
    started_at: float
    available: bool


def _which_nvidia_smi() -> Optional[str]:
    return shutil.which("nvidia-smi")


def snapshot_baseline() -> dict:
    """One-shot pre-run hardware snapshot. Returns dict with GPU/CPU/RAM info."""
    out: dict = {"timestamp": time.time()}
    nvsmi = _which_nvidia_smi()
    if nvsmi:
        try:
            r = subprocess.run(
                [nvsmi, "--query-gpu=utilization.gpu,memory.used,memory.free,temperature.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0 and r.stdout.strip():
                cols = [c.strip() for c in r.stdout.strip().split(",")]
                if len(cols) == 4:
                    out["gpu"] = {
                        "util_pct": int(cols[0]),
                        "vram_used_mib": int(cols[1]),
                        "vram_free_mib": int(cols[2]),
                        "temp_c": int(cols[3]),
                    }
        except Exception as e:
            out["gpu_error"] = str(e)
    else:
        out["gpu"] = None
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    out["mem_total_kb"] = int(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    out["mem_avail_kb"] = int(line.split()[1])
    except Exception:
        pass
    return out


def start_sampler(run_id: str, log_dir: str = "/tmp") -> SamplerHandle:
    """Spawn a background nvidia-smi sampler writing CSV to /tmp/util-<run_id>.log.

    Returns a handle that stop_sampler() will use to kill the process.
    If nvidia-smi is missing, returns a no-op handle (available=False)."""
    nvsmi = _which_nvidia_smi()
    log_path = os.path.join(log_dir, f"util-{run_id}.log")
    if nvsmi is None:
        return SamplerHandle(run_id=run_id, log_path=log_path, pid=None,
                             started_at=time.time(), available=False)
    cmd = [
        nvsmi,
        "--query-gpu=timestamp,utilization.gpu,utilization.memory,memory.used,temperature.gpu",
        "--format=csv,nounits",
        "-l", "2",  # 2-second interval
    ]
    f = open(log_path, "w")
    p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    return SamplerHandle(run_id=run_id, log_path=log_path, pid=p.pid,
                         started_at=time.time(), available=True)


def stop_sampler(handle: SamplerHandle) -> None:
    """Kill the background sampler. Idempotent — safe to call multiple times."""
    if not handle.available or handle.pid is None:
        return
    try:
        os.kill(handle.pid, signal.SIGTERM)
        time.sleep(0.2)
        try:
            os.kill(handle.pid, 0)  # still alive?
            os.kill(handle.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    except ProcessLookupError:
        pass


def verify_band(handle: SamplerHandle, band_lo: int = 70, band_hi: int = 90) -> dict:
    """Parse the sampler log, compute mean/max/min GPU util, return band-pass verdict.

    band_passed is True iff mean ∈ [band_lo, band_hi] AND <10% of samples are at 100%
    (sustained 100% = crash risk per #00b). Returns the full stats dict either way."""
    if not handle.available:
        return {
            "band_passed": False,
            "reason": "no nvidia-smi available (CPU-only or driver missing)",
            "samples": 0,
        }
    if not os.path.exists(handle.log_path):
        return {"band_passed": False, "reason": "log file missing", "samples": 0}
    gpu_utils: list[int] = []
    vram_used: list[int] = []
    temps: list[int] = []
    try:
        with open(handle.log_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                util_key = next((k for k in row if "utilization.gpu" in k), None)
                vram_key = next((k for k in row if "memory.used" in k), None)
                temp_key = next((k for k in row if "temperature.gpu" in k), None)
                if util_key is None:
                    continue
                try:
                    gpu_utils.append(int(row[util_key].strip().rstrip("%").strip()))
                    if vram_key:
                        vram_used.append(int(row[vram_key].strip().rstrip("MiB").strip()))
                    if temp_key:
                        temps.append(int(row[temp_key].strip()))
                except ValueError:
                    continue
    except Exception as e:
        return {"band_passed": False, "reason": f"parse error: {e}", "samples": 0}
    n = len(gpu_utils)
    if n == 0:
        return {"band_passed": False, "reason": "no samples in log", "samples": 0}
    mean_gpu = sum(gpu_utils) / n
    max_gpu = max(gpu_utils)
    min_gpu = min(gpu_utils)
    saturated_count = sum(1 for u in gpu_utils if u >= 99)
    band_passed = (band_lo <= mean_gpu <= band_hi) and (saturated_count / n < 0.10)
    reason = "OK"
    if mean_gpu < band_lo:
        reason = f"mean_gpu {mean_gpu:.1f}% < {band_lo}% — re-tune (bigger batch/model/seq)"
    elif mean_gpu > band_hi:
        reason = f"mean_gpu {mean_gpu:.1f}% > {band_hi}% — back off (crash risk)"
    elif saturated_count / n >= 0.10:
        reason = f"saturated {saturated_count}/{n} samples at 100% — crash risk"
    out = {
        "band_passed": band_passed,
        "reason": reason,
        "mean_gpu_util_pct": round(mean_gpu, 1),
        "max_gpu_util_pct": max_gpu,
        "min_gpu_util_pct": min_gpu,
        "saturated_samples_pct": round(100 * saturated_count / n, 1),
        "samples": n,
        "wall_seconds": round(time.time() - handle.started_at, 2),
        "log_path": handle.log_path,
    }
    if vram_used:
        out["vram_used_max_mib"] = max(vram_used)
        out["vram_used_mean_mib"] = round(sum(vram_used) / len(vram_used), 1)
    if temps:
        out["temp_max_c"] = max(temps)
    return out


if __name__ == "__main__":
    # Smoke test: 10s sampler with no workload -> expect mean_gpu near idle (<5%)
    print("baseline:", snapshot_baseline())
    h = start_sampler("smoke-test")
    print(f"sampler started (pid={h.pid}, available={h.available}), waiting 10s...")
    time.sleep(10)
    stop_sampler(h)
    print("verdict:", verify_band(h))
