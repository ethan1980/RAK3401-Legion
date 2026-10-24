#!/usr/bin/env python3
"""Run the actual APC policy with host ASan/UBSan and deterministic clocks."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_apc_tests(firmware, compiler, *, leak_check=True):
    with tempfile.TemporaryDirectory(prefix="legion-apc-") as folder:
        binary = Path(folder) / "apc-tests"
        subprocess.run(
            [
                compiler,
                "-std=c++17",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-O1",
                "-g",
                "-fsanitize=address,undefined",
                "-fno-omit-frame-pointer",
                "-I",
                str(Path(firmware) / "src"),
                str(ROOT / "tests/apc/test_apc.cpp"),
                "-o",
                str(binary),
            ],
            check=True,
        )
        subprocess.run(
            [str(binary)],
            check=True,
            env={
                **os.environ,
                "ASAN_OPTIONS": f"detect_leaks={int(leak_check)}",
                "UBSAN_OPTIONS": "halt_on_error=1",
            },
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--firmware", type=Path, required=True)
    parser.add_argument("--no-leak-check", action="store_true")
    args = parser.parse_args()
    run_apc_tests(args.firmware, shutil.which("g++"), leak_check=not args.no_leak_check)
