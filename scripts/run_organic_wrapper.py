#!/usr/bin/env python3
"""Cycle 10 wrapper-lite for organic_v0.

This is an external anchor around the native runtime, not a sandbox. It records
the event-log row count and last event_content_hash so a later run can reject a
truncate-and-restart chain that is internally clean from GENESIS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any


SCHEMA = "project_x.run_manifest.v0"
WRAPPER_VERSION = "cycle10-wrapper-lite-v0"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def realpath(path: str | Path) -> Path:
    return Path(os.path.realpath(os.fspath(path)))


def sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def find_flag_value(argv: list[str], flag: str) -> str | None:
    for i, arg in enumerate(argv):
        if arg == flag and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith(flag + "="):
            return arg.split("=", 1)[1]
    return None


def is_within_or_equal(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath([str(path), str(root)]) == str(root)
    except ValueError:
        return False


def validate_inside_roots(path: Path, roots: list[Path]) -> bool:
    return any(is_within_or_equal(path, root) for root in roots)


def read_event_log(path: str | None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "event_log_path": str(realpath(path)) if path else None,
        "event_log_status": "missing",
        "event_log_row_count": 0,
        "event_log_first_event_content_hash": None,
        "event_log_last_event_content_hash": None,
        "event_log_error": "",
    }
    if not path:
        return result
    event_path = realpath(path)
    if not event_path.exists():
        return result
    try:
        first_hash: str | None = None
        last_hash: str | None = None
        row_count = 0
        with event_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                content_hash = row.get("event_content_hash")
                if first_hash is None:
                    first_hash = content_hash
                last_hash = content_hash
                row_count += 1
        result.update(
            {
                "event_log_status": "present",
                "event_log_row_count": row_count,
                "event_log_first_event_content_hash": first_hash,
                "event_log_last_event_content_hash": last_hash,
            }
        )
    except Exception as exc:  # noqa: BLE001 - manifest must survive malformed logs.
        result["event_log_status"] = "unreadable"
        result["event_log_error"] = str(exc)
    return result


def load_prior_manifest(path: str | None) -> tuple[dict[str, Any] | None, str]:
    if not path:
        return None, "not_checked"
    try:
        prior_path = realpath(path)
        with prior_path.open("r", encoding="utf-8") as f:
            return json.load(f), "loaded"
    except Exception:
        return None, "prior_missing"


def compare_prior(current: dict[str, Any], prior_path: str | None) -> dict[str, Any]:
    prior, status = load_prior_manifest(prior_path)
    verdict = "not_checked"
    wrapper_denial = False
    prior_count = None
    prior_hash = None
    prior_binary_sha256 = None
    prior_event_log_path = None
    prior_wrapper_version = None
    details = {
        "wrapper_version_match": None,
        "binary_sha256_match": None,
        "event_log_path_match": None,
        "row_count_match": None,
        "final_hash_match": None,
    }
    if prior_path:
        if prior is None:
            verdict = "prior_missing"
            wrapper_denial = True
        else:
            prior_count = prior.get("event_log_row_count")
            prior_hash = prior.get("event_log_last_event_content_hash")
            prior_binary_sha256 = prior.get("binary_sha256")
            prior_event_log_path = prior.get("event_log_path")
            prior_wrapper_version = prior.get("wrapper_version")
            wrapper_version_match = prior_wrapper_version == current.get("wrapper_version")
            binary_sha256_match = prior_binary_sha256 == current.get("binary_sha256")
            event_log_path_match = prior_event_log_path == current.get("event_log_path")
            row_count_match = prior_count == current.get("event_log_row_count")
            final_hash_match = prior_hash == current.get("event_log_last_event_content_hash")
            details = {
                "wrapper_version_match": wrapper_version_match,
                "binary_sha256_match": binary_sha256_match,
                "event_log_path_match": event_log_path_match,
                "row_count_match": row_count_match,
                "final_hash_match": final_hash_match,
            }
            if not wrapper_version_match:
                verdict = "mismatch_wrapper_version"
                wrapper_denial = True
            elif not binary_sha256_match:
                verdict = "mismatch_binary_sha256"
                wrapper_denial = True
            elif not event_log_path_match:
                verdict = "mismatch_event_log_path"
                wrapper_denial = True
            elif not row_count_match:
                verdict = "mismatch_row_count"
                wrapper_denial = True
            elif not final_hash_match:
                verdict = "mismatch_final_hash"
                wrapper_denial = True
            else:
                verdict = "match"
    return {
        "wrapper_truncate_detect_verdict": verdict,
        "wrapper_truncate_detect_details": details,
        "prior_manifest_load_status": status,
        "prior_event_log_row_count": prior_count,
        "prior_event_log_last_event_content_hash": prior_hash,
        "prior_binary_sha256": prior_binary_sha256,
        "prior_event_log_path": prior_event_log_path,
        "prior_wrapper_version": prior_wrapper_version,
        "prior_manifest_path": str(realpath(prior_path)) if prior_path else None,
        "prior_mismatch_denial": wrapper_denial,
    }


def write_manifest(manifest: dict[str, Any], manifest_paths: list[Path]) -> None:
    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    for manifest_path in manifest_paths:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(payload, encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cycle 10 wrapper-lite run manifest emitter")
    parser.add_argument("--binary", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--allowed-write-root", action="append", default=[])
    parser.add_argument("--manifest-out")
    parser.add_argument("--prior-manifest")
    parser.add_argument("forwarded_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.forwarded_args and args.forwarded_args[0] == "--":
        args.forwarded_args = args.forwarded_args[1:]
    return args


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    script_path = realpath(__file__)
    project_root = script_path.parents[1]
    binary_path = realpath(args.binary)
    event_log_arg = find_flag_value(args.forwarded_args, "--event-log")
    output_artifact_arg = find_flag_value(args.forwarded_args, "--out")
    policy_tmp_root = find_flag_value(args.forwarded_args, "--policy-tmp-root")

    if args.allowed_write_root:
        allowed_roots = [realpath(root) for root in args.allowed_write_root]
    else:
        allowed_roots = [project_root]
        if policy_tmp_root:
            allowed_roots.append(realpath(policy_tmp_root))

    default_manifest = project_root / "run" / "artifacts" / "organic-v0" / "run_manifests" / f"{args.run_id}.json"
    manifest_out = realpath(args.manifest_out) if args.manifest_out else None

    start_monotonic = time.monotonic()
    start_time = utc_now()
    exit_code: int | None = None
    timeout_result = "none"
    binary_launched = False
    stdout_tail = ""
    stderr_tail = ""
    wrapper_denial = False
    wrapper_denial_reason = ""
    preflight_denial_reasons: list[str] = []
    rejected_default_manifest_path: str | None = None
    rejected_manifest_out_path: str | None = None
    rejected_output_artifact_path: str | None = None
    rejected_event_log_path: str | None = None
    valid_manifest_out = manifest_out
    manifest_write_paths: list[Path] = []

    if manifest_out and not validate_inside_roots(manifest_out, allowed_roots):
        preflight_denial_reasons.append(f"manifest-out resolves outside allowed write roots: {manifest_out}")
        rejected_manifest_out_path = str(manifest_out)
        valid_manifest_out = None

    if not manifest_out and not validate_inside_roots(default_manifest, allowed_roots):
        preflight_denial_reasons.append(
            f"default manifest resolves outside allowed write roots: {default_manifest}"
        )
        rejected_default_manifest_path = str(default_manifest)

    if validate_inside_roots(default_manifest, allowed_roots):
        manifest_write_paths.append(default_manifest)
    if valid_manifest_out and valid_manifest_out not in manifest_write_paths:
        manifest_write_paths.append(valid_manifest_out)

    output_artifact_path = str(realpath(output_artifact_arg)) if output_artifact_arg else None
    if output_artifact_arg and not validate_inside_roots(realpath(output_artifact_arg), allowed_roots):
        preflight_denial_reasons.append(
            f"out resolves outside allowed write roots: {realpath(output_artifact_arg)}"
        )
        rejected_output_artifact_path = str(realpath(output_artifact_arg))
    if event_log_arg and not validate_inside_roots(realpath(event_log_arg), allowed_roots):
        preflight_denial_reasons.append(
            f"event-log resolves outside allowed write roots: {realpath(event_log_arg)}"
        )
        rejected_event_log_path = str(realpath(event_log_arg))

    if preflight_denial_reasons:
        wrapper_denial = True
        wrapper_denial_reason = "; ".join(preflight_denial_reasons)

    if not binary_path.is_file() and not wrapper_denial:
        wrapper_denial = True
        wrapper_denial_reason = f"binary path is not a file: {binary_path}"

    if wrapper_denial:
        exit_code = 1
    else:
        try:
            binary_launched = True
            completed = subprocess.run(
                [str(binary_path), *args.forwarded_args],
                timeout=args.timeout_seconds,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            exit_code = completed.returncode
            stdout_tail = completed.stdout[-4000:]
            stderr_tail = completed.stderr[-4000:]
        except subprocess.TimeoutExpired as exc:
            exit_code = 124
            timeout_result = "hit"
            stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            stdout_tail = stdout[-4000:]
            stderr_tail = stderr[-4000:]
        except Exception as exc:  # noqa: BLE001 - wrapper errors must still emit a manifest.
            exit_code = 1
            wrapper_denial = True
            wrapper_denial_reason = f"wrapper launch failed: {exc}"

    binary_sha256 = sha256_file(binary_path)
    event_log = read_event_log(event_log_arg)
    current_anchor = {
        **event_log,
        "binary_sha256": binary_sha256,
        "wrapper_version": WRAPPER_VERSION,
    }
    prior = compare_prior(current_anchor, args.prior_manifest)
    if prior["prior_mismatch_denial"]:
        wrapper_denial = True
        if prior["wrapper_truncate_detect_verdict"] == "prior_missing":
            wrapper_denial_reason = "prior manifest missing or unreadable"
        else:
            wrapper_denial_reason = (
                "prior manifest mismatch: "
                f"{prior['wrapper_truncate_detect_verdict']}"
            )

    output_artifact_sha256 = sha256_file(realpath(output_artifact_arg)) if output_artifact_arg else None
    duration = time.monotonic() - start_monotonic
    end_time = utc_now()

    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "run_id": args.run_id,
        "wrapper_version": WRAPPER_VERSION,
        "binary_path": str(binary_path),
        "binary_sha256": binary_sha256,
        "command": [str(binary_path), *args.forwarded_args],
        "forwarded_args": args.forwarded_args,
        "start_time_utc": start_time,
        "end_time_utc": end_time,
        "duration_seconds": round(duration, 6),
        "exit_code": exit_code,
        "timeout_seconds": args.timeout_seconds,
        "timeout_result": timeout_result,
        **event_log,
        "output_artifact_path": output_artifact_path,
        "output_artifact_sha256": output_artifact_sha256,
        "allowed_write_roots": [str(root) for root in allowed_roots],
        "default_manifest_path": str(default_manifest),
        "manifest_out_path": str(manifest_out) if manifest_out else None,
        "rejected_default_manifest_path": rejected_default_manifest_path,
        "rejected_manifest_out_path": rejected_manifest_out_path,
        "rejected_output_artifact_path": rejected_output_artifact_path,
        "rejected_event_log_path": rejected_event_log_path,
        "preflight_denial_reasons": preflight_denial_reasons,
        "binary_launched": binary_launched,
        "wrapper_denial": wrapper_denial,
        "wrapper_denial_reason": wrapper_denial_reason,
        **prior,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "negative_space": {
            "not_sandboxed": True,
            "not_secure": True,
            "not_alignment_solution": True,
            "not_tool_use_safety": True,
            "not_full_resource_limit": True,
            "not_supply_chain_safety": True,
            "anchor_only": True,
        },
        "honest_interpretation": (
            "Cycle 10 wrapper-lite anchors event-log row count and the last "
            "event_content_hash for current short runtime surfaces. It is not "
            "a sandbox, not secure, and not a broader safety solution."
        ),
    }
    if manifest_write_paths:
        write_manifest(manifest, manifest_write_paths)
    print(
        json.dumps(
            {
                "manifest": str(manifest_write_paths[0]) if manifest_write_paths else None,
                "wrapper_denial": wrapper_denial,
            },
            sort_keys=True,
        )
    )
    return 1 if wrapper_denial else int(exit_code or 0)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
