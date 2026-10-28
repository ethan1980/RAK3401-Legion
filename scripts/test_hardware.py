#!/usr/bin/env python3
"""Exercise real Legion CC310 dispatch and boot diagnostics at the SDK boundary.

The production Nordic headers are used. OpenSSL supplies the simulated hardware
operations and independent reference digests; this is not a physical CC310 test.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_hardware_tests(firmware, compiler, *, leak_check=True):
    sdk = Path(os.environ.get("PLATFORMIO_CORE_DIR", "~/.platformio")).expanduser()
    sdk /= "packages/framework-arduinoadafruitnrf52/libraries/Adafruit_nRFCrypto/src"
    if not (sdk / "nrf_cc310/include/crys_hash.h").exists():
        raise RuntimeError("Install the pinned nRF52 PlatformIO packages first")
    sources = (
        "platform/nrf52/LegionCrypto.cpp",
        "platform/nrf52/LegionCrypto.h",
        "platform/nrf52/NRF52CryptoSession.h",
        "platform/nrf52/NRF52CryptoEngine.cpp",
        "platform/nrf52/LegionBoot.cpp",
        "platform/nrf52/LegionBoot.h",
        "platform/nrf52/LegionComponents.cpp",
        "platform/nrf52/LegionComponents.h",
        "mesh/HardwareRNG.cpp",
        "mesh/HardwareRNG.h",
    )
    with tempfile.TemporaryDirectory(prefix="legion-hardware-") as folder:
        work = Path(folder)
        for name in sources:
            destination = work / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(firmware) / "src" / name, destination)
        shutil.copytree(ROOT / "tests/hardware/stubs", work, dirs_exist_ok=True)
        (work / "concurrency").mkdir()
        shutil.copy2(
            ROOT / "tests/control/stubs/concurrency/Lock.h", work / "concurrency/Lock.h"
        )
        binary = work / "hardware-tests"
        subprocess.run(
            [
                compiler,
                "-std=c++17",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-Wno-deprecated-declarations",
                "-Wno-unused-parameter",
                "-g",
                "-O1",
                "-fsanitize=address,undefined",
                "-fno-omit-frame-pointer",
                "-pthread",
                "-I",
                str(work),
                "-I",
                str(work / "platform/nrf52"),
                "-I",
                str(sdk),
                *[str(work / name) for name in sources if name.endswith(".cpp")],
                str(ROOT / "tests/hardware/test_hardware.cpp"),
                "-lcrypto",
                "-o",
                str(binary),
            ],
            check=True,
        )
        for case in (
            "crypto",
            "por",
            "watchdog",
            "lockup",
            "software",
            "pin",
            "wake",
            "missing",
            "foreign",
            "api_failure",
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
    run_hardware_tests(
        args.firmware, shutil.which("g++"), leak_check=not args.no_leak_check
    )
