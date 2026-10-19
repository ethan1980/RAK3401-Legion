#!/usr/bin/env python3
"""Run the real control/ignore translation units under host sanitizers."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_control_tests(firmware, compiler, *, leak_check=True):
    sources = (
        "modules/LegionControlModule.cpp",
        "modules/LegionControlModule.h",
        "modules/LegionControlPolicy.h",
        "modules/LegionTelemetryPolicy.h",
        "mesh/LegionIgnore.cpp",
        "mesh/LegionIgnore.h",
        "mesh/LegionRecoveryPolicy.h",
        "mesh/Throttle.h",
        "mesh/Throttle.cpp",
        "concurrency/LockGuard.h",
        "concurrency/LockGuard.cpp",
    )
    with tempfile.TemporaryDirectory(prefix="legion-control-") as folder:
        directory = Path(folder)
        for name in sources:
            destination = directory / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(firmware) / "src" / name, destination)
        shutil.copytree(ROOT / "tests/control/stubs", directory, dirs_exist_ok=True)
        binary = directory / "control-tests"
        subprocess.run(
            [
                compiler,
                "-std=c++17",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-g",
                "-O1",
                "-fsanitize=address,undefined",
                "-fno-omit-frame-pointer",
                "-pthread",
                "-I",
                str(directory),
                "-I",
                str(directory / "mesh"),
                *[str(directory / name) for name in sources if name.endswith(".cpp")],
                str(ROOT / "tests/control/test_control.cpp"),
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


def run_dcdc_tests(firmware, compiler, *, leak_check=True):
    with tempfile.TemporaryDirectory(prefix="legion-dcdc-") as folder:
        directory = Path(folder)
        for name in ("LegionDcdc.cpp", "LegionDcdc.h"):
            destination = directory / "platform/nrf52" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(firmware) / "src/platform/nrf52" / name, destination)
        shutil.copytree(ROOT / "tests/dcdc/stubs", directory, dirs_exist_ok=True)
        binary = directory / "dcdc-tests"
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
                "-I",
                str(directory),
                str(directory / "platform/nrf52/LegionDcdc.cpp"),
                str(ROOT / "tests/dcdc/test_dcdc.cpp"),
                "-o",
                str(binary),
            ],
            check=True,
        )
        for case in (
            "success",
            "disabled",
            "query_failure",
            "api_failure",
            "readback_failure",
        ):
            subprocess.run(
                [str(binary), case],
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
    run_control_tests(
        args.firmware, shutil.which("g++"), leak_check=not args.no_leak_check
    )
    run_dcdc_tests(
        args.firmware, shutil.which("g++"), leak_check=not args.no_leak_check
    )
