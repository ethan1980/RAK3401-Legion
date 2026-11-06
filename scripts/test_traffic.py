#!/usr/bin/env python3
"""Run the actual traffic policies with host ASan/UBSan and deterministic clocks."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_traffic_tests(firmware, compiler, *, leak_check=True):
    with tempfile.TemporaryDirectory(prefix="legion-traffic-") as folder:
        binary = Path(folder) / "traffic-tests"
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
                "-I", str(Path(firmware) / "src/mesh"),
                str(ROOT / "tests/traffic/test_traffic.cpp"),
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
    run_traffic_tests(args.firmware, shutil.which("g++"), leak_check=not args.no_leak_check)
