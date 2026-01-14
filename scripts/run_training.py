#!/usr/bin/env python3
"""Wrapper script to run scripts with correct PYTHONPATH."""
import sys
import os
import argparse

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", type=str, default="train_multitask_ccb.py")
    parser.add_argument("--log", type=str, default="training_gpu_live.log")
    args, remaining = parser.parse_known_args()

    # Redirect output to log file for Windows compatibility
    log_path = os.path.join(project_root, args.log)
    log_file = open(log_path, 'w', buffering=1)
    sys.stdout = log_file
    sys.stderr = log_file

    script_path = os.path.join(project_root, "scripts", args.script)
    print(f"Running {script_path}, logging to {log_path}")
    print(f"CUDA available: {__import__('torch').cuda.is_available()}")

    # Set __file__ for the script
    __file__ = script_path
    sys.argv = [script_path] + remaining
    exec(open(script_path).read())
