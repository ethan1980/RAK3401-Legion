#!/usr/bin/env python3
"""Build and package either Legion or the unchanged RAK3401 reference."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

from prepare import PROFILE_PATH, ROOT, load_config, prepare, run

TARGETS = {"legion": "rak3401-legion", "baseline": "rak3401-1watt"}
PIO_ENV = {**os.environ, "PLATFORMIO_SETTING_ENABLE_TELEMETRY": "no"}


def source_files(firmware):
    paths = run("git", "ls-files", cwd=firmware, capture=True).splitlines()
    for name in paths + [PROFILE_PATH.as_posix()]:
        path = firmware / name
        if path.is_file():
            yield path
        elif path.is_dir():
            yield from (
                p for p in sorted(path.rglob("*")) if p.is_file() and p.name != ".git"
            )


def source_filter(info):
    if "__pycache__" in Path(info.name).parts or info.name.endswith(".pyc"):
        return None
    return info


def package(firmware, target, output):
    config = load_config()
    environment = TARGETS[target]
    output = output / target
    output.mkdir(parents=True, exist_ok=True)
    build = firmware / ".pio/build" / environment
    artifacts = []
    for suffix in ("uf2", "zip", "elf", "hex", "mt.json", "map", "ld"):
        for path in sorted(build.glob(f"firmware-*.{suffix}")):
            name = f"{path.stem}-ota.zip" if suffix == "zip" else path.name
            shutil.copy2(path, output / name)
            artifacts.append(name)
    if not any(p.endswith(".uf2") for p in artifacts) or not any(
        p.endswith(".zip") for p in artifacts
    ):
        raise RuntimeError("Build did not produce both UF2 and DFU ZIP")

    for path in output.glob("firmware-*.mt.json"):
        for entry in json.loads(path.read_text())["files"]:
            data = (output / entry["name"]).read_bytes()
            if (
                len(data) != entry["bytes"]
                or hashlib.md5(data).hexdigest() != entry["md5"]
            ):
                raise RuntimeError(f"Manifest mismatch: {entry['name']}")

    archive = output / "corresponding-source.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for path in source_files(firmware):
            tar.add(path, arcname=Path("firmware") / path.relative_to(firmware))
        for name in (
            "upstream.json",
            "requirements.txt",
            "profiles",
            "patches",
            "scripts",
            "tests",
            "LICENSE",
        ):
            tar.add(ROOT / name, arcname=Path("legion") / name, filter=source_filter)
    manifest = {
        **config,
        "target": target,
        "environment": environment,
        "spi_hz": 4000000,
        "bulk_spi": target == "legion",
        "energy_recovery": target == "legion",
        "flash_write_deduplication": target == "legion",
        "flash_readback_crc32": target == "legion",
        "hardware_tested": False,
        "energy_savings_measured": False,
        "overlay_commit": run(
            "git", "rev-parse", "HEAD", cwd=ROOT, capture=True
        ).strip(),
        "platformio_version": run(
            sys.executable, "-m", "platformio", "--version", capture=True, env=PIO_ENV
        ).strip(),
        "source_patch_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in config["patches"]
        },
        "submodules": run(
            "git", "submodule", "status", "--recursive", cwd=firmware, capture=True
        ).splitlines(),
    }
    (output / "legion-build.json").write_text(json.dumps(manifest, indent=2) + "\n")
    files = sorted(
        path
        for path in output.iterdir()
        if path.is_file() and path.name != "SHA256SUMS"
    )
    (output / "SHA256SUMS").write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
            for path in files
        )
    )
    print(f"Artifacts: {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=TARGETS, default="legion")
    parser.add_argument("--dest", type=Path, default=ROOT / ".work/firmware")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    firmware = prepare(args.dest)
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/test_firmware.py"),
            "--firmware",
            str(firmware),
        ],
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "platformio",
            "run",
            "-e",
            TARGETS[args.target],
            "-t",
            "mtjson",
        ],
        cwd=firmware,
        check=True,
        env=PIO_ENV,
    )
    package(firmware, args.target, args.output.resolve())


if __name__ == "__main__":
    main()
