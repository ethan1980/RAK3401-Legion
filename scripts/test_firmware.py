#!/usr/bin/env python3
"""Run host tests against the actual prepared Legion policy and persistence code."""

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "src/power/LegionPowerPolicy.h",
    "src/mesh/LegionCrc32.h",
    "src/mesh/LegionPersistence.h",
    "src/mesh/LegionPersistence.cpp",
    "src/SafeFile.h",
    "src/SafeFile.cpp",
)


def run_tests(firmware, *, leak_check=True):
    compiler = shutil.which("g++") or shutil.which("clang++")
    if not compiler:
        raise RuntimeError("A C++17 host compiler is required for the firmware checks")
    with tempfile.TemporaryDirectory(prefix="legion-native-") as folder:
        directory = Path(folder)
        for name in SOURCES:
            source = Path(firmware) / name
            destination = directory / Path(name).relative_to("src")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        shutil.copytree(ROOT / "tests/native/stubs", directory, dirs_exist_ok=True)
        binary = directory / "legion-tests"
        subprocess.run(
            [
                compiler,
                "-std=c++17",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-g",
                "-fsanitize=address,undefined",
                "-fno-omit-frame-pointer",
                "-DRAK3401_LEGION_FLASH=1",
                "-I",
                str(directory),
                str(directory / "SafeFile.cpp"),
                str(directory / "mesh/LegionPersistence.cpp"),
                str(ROOT / "tests/native/test_legion.cpp"),
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--firmware", type=Path, required=True)
    parser.add_argument(
        "--no-leak-check",
        action="store_true",
        help="Keep ASan/UBSan but disable leak tracing on hosts without /proc access",
    )
    args = parser.parse_args()
    run_tests(args.firmware.resolve(), leak_check=not args.no_leak_check)


if __name__ == "__main__":
    main()
