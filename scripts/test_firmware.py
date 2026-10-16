#!/usr/bin/env python3
"""Run host tests against the actual prepared Legion firmware changes."""

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
    run_telemetry_tests(firmware, compiler, leak_check=leak_check)
    run_recovery_tests(firmware, compiler, leak_check=leak_check)
    run_engine_tests(firmware, compiler, leak_check=leak_check)
    run_dfu_tests(firmware, compiler, leak_check=leak_check)


def run_dfu_tests(firmware, compiler, *, leak_check=True):
    with tempfile.TemporaryDirectory(prefix="legion-dfu-") as folder:
        directory = Path(folder)
        for name in ("LegionDfu.cpp", "LegionDfu.h"):
            destination = directory / "platform/nrf52" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(firmware) / "src/platform/nrf52" / name, destination)
        shutil.copytree(ROOT / "tests/dfu/stubs", directory, dirs_exist_ok=True)
        binary = directory / "dfu-tests"
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
                str(directory / "platform/nrf52/LegionDfu.cpp"),
                str(ROOT / "tests/dfu/test_dfu.cpp"),
                "-o",
                str(binary),
            ],
            check=True,
        )
        for case in (
            "write_contract",
            "probes",
            "rejected",
            "busy_spi",
            "missing_bond",
            "accepted",
            "rollover",
            "unsecured",
            "concurrent",
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


def run_engine_tests(firmware, compiler, *, leak_check=True):
    runtime = next((Path(firmware) / ".pio/libdeps").glob("*/Nanopb/pb.h"), None)
    if runtime is None:
        raise RuntimeError(
            "Install the pinned PlatformIO dependencies before the recovery integration test"
        )
    runtime = runtime.parent
    sources = (
        "src/mesh/LegionRecovery.cpp",
        "src/mesh/LegionRecovery.h",
        "src/mesh/LegionRecoveryPolicy.h",
        "src/mesh/LegionRecoveryRunner.h",
        "src/mesh/LegionRecoveryStore.h",
        "src/mesh/LegionCrc32.h",
        "src/mesh/LegionPersistence.h",
        "src/mesh/LegionPersistence.cpp",
        "src/SafeFile.h",
        "src/SafeFile.cpp",
    )
    with tempfile.TemporaryDirectory(prefix="legion-engine-") as folder:
        directory = Path(folder)
        for name in sources:
            destination = directory / Path(name).relative_to("src")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(firmware) / name, destination)
        shutil.copytree(
            Path(firmware) / "src/mesh/generated", directory / "mesh/generated"
        )
        for name in ("SPILock.h", "concurrency/LockGuard.h", "FSCommon.h"):
            destination = directory / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / "tests/native/stubs" / name, destination)
        shutil.copytree(ROOT / "tests/recovery/stubs", directory, dirs_exist_ok=True)
        binary = directory / "engine-tests"
        subprocess.run(
            [
                compiler,
                "-std=c++17",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-Wno-missing-field-initializers",
                "-O1",
                "-g",
                "-fsanitize=address,undefined",
                "-fno-omit-frame-pointer",
                "-I",
                str(directory),
                "-I",
                str(directory / "mesh/generated"),
                "-I",
                str(runtime),
                str(ROOT / "tests/recovery/test_engine.cpp"),
                str(directory / "SafeFile.cpp"),
                str(directory / "mesh/LegionPersistence.cpp"),
                *map(
                    str,
                    sorted((directory / "mesh/generated/meshtastic").glob("*.pb.cpp")),
                ),
                *[
                    str(runtime / name)
                    for name in ("pb_common.c", "pb_encode.c", "pb_decode.c")
                ],
                "-lcrypto",
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


def run_recovery_tests(firmware, compiler, *, leak_check=True):
    with tempfile.TemporaryDirectory(prefix="legion-recovery-") as folder:
        binary = Path(folder) / "recovery-tests"
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
                str(ROOT / "tests/recovery/test_recovery.cpp"),
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


def run_telemetry_tests(firmware, compiler, *, leak_check=True):
    sources = (
        "src/modules/LegionTelemetryModule.cpp",
        "src/modules/LegionTelemetryModule.h",
        "src/modules/LegionTelemetryPolicy.h",
        "src/mesh/Throttle.h",
        "src/mesh/Throttle.cpp",
        "src/concurrency/LockGuard.h",
        "src/concurrency/LockGuard.cpp",
        "src/platform/nrf52/LegionTelemetryHal.h",
        "src/mesh/LegionRecoveryPolicy.h",
    )
    with tempfile.TemporaryDirectory(prefix="legion-telemetry-") as folder:
        directory = Path(folder)
        for name in sources:
            destination = directory / Path(name).relative_to("src")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(firmware) / name, destination)
        shutil.copytree(ROOT / "tests/telemetry/stubs", directory, dirs_exist_ok=True)
        binary = directory / "telemetry-tests"
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
                "-pthread",
                "-I",
                str(directory),
                str(directory / "modules/LegionTelemetryModule.cpp"),
                str(directory / "mesh/Throttle.cpp"),
                str(directory / "concurrency/LockGuard.cpp"),
                str(ROOT / "tests/telemetry/test_telemetry.cpp"),
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
