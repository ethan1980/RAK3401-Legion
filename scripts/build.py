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

from prepare import PROFILE_PATH, ROOT, firmware_version, load_config, prepare, run
from validate_dfu import validate_dfu
from validate_dcdc import validate_dcdc
from validate_update import validate_update

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
    upstream_version = f"{config['meshtastic_version']}.{config['commit'][:7]}"
    advertised_version = (
        firmware_version(config) if target == "legion" else upstream_version
    )
    elf = build / f"firmware-{environment}-{upstream_version}.elf"
    if advertised_version.encode("ascii") + b"\0" not in elf.read_bytes():
        raise RuntimeError("Compiled firmware does not contain its advertised version")
    print(f"Verified firmware identification: {advertised_version}")
    dfu_validation = validate_dfu(elf) if target == "legion" else None
    dcdc_validation = validate_dcdc(elf) if target == "legion" else None
    if dfu_validation:
        print(
            "Verified compiled immediate DFU registration, main-loop route and OTA reset (not hardware OTA)"
        )
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

    update_validation = None
    if target == "legion":
        update_validation = validate_update(
            elf,
            next(output.glob("firmware-*.zip")),
            next(output.glob("firmware-*.uf2")),
        )
        print(
            f"Verified application-only OTA/UF2 and rescue reserve: {update_validation}"
        )

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
            "README.md",
            "COMMANDS.md",
            "RECOVERY.md",
            "RELEASE_NOTES.md",
            "CHANGELOG.md",
        ):
            tar.add(ROOT / name, arcname=Path("legion") / name, filter=source_filter)
    manifest = {
        **config,
        "target": target,
        "environment": environment,
        "advertised_firmware_version": advertised_version,
        "spi_hz": 8000000 if target == "legion" else 4000000,
        "bulk_spi": target == "legion",
        "energy_recovery": target == "legion",
        "flash_write_deduplication": target == "legion",
        "flash_readback_crc32": target == "legion",
        "private_telemetry": target == "legion",
        "remote_control": target == "legion",
        "control_commands": (
            [
                "msg",
                "reboot",
                "zerohop",
                "ignore",
                "unignore",
                "ignorelist",
                "trace",
                "boot",
            ]
            if target == "legion"
            else []
        ),
        "control_text_limit_bytes": 199 if target == "legion" else None,
        "control_cooldown_seconds": 5 if target == "legion" else None,
        "trace_wait_seconds": 90 if target == "legion" else None,
        "trace_start_cooldown_seconds": 60 if target == "legion" else None,
        "trace_reply_gap_seconds": 6 if target == "legion" else None,
        "trace_hardware_tested": False,
        "cc310_packet_sha256": target == "legion",
        "cc310_ack_hmac_sha256": target == "legion",
        "cc310_software_fallback": target == "legion",
        "cc310_hardware_measured": False,
        "boot_diagnostics": target == "legion",
        "boot_diagnostics_flash_writes": False,
        "boot_diagnostics_hardware_tested": False,
        "reg1_dcdc": target == "legion",
        "dcdc_validation": dcdc_validation,
        "ble_dfu_validation": dfu_validation,
        "manual_recovery": target == "legion",
        "recovery_automatic_snapshot": False,
        "backup_freshness_status": target == "legion",
        "backup_freshness_flash_writes": False,
        "backup_freshness_hardware_tested": False,
        "update_validation": update_validation,
        "telemetry_channel": "LegionRF" if target == "legion" else None,
        "telemetry_cooldown_seconds": 60 if target == "legion" else None,
        "telemetry_automatic_reports": False,
        "hardware_tested": False,
        "ota_hardware_tested": bool(
            target == "legion"
            and config.get("ota_hardware_observation", {}).get("completion_confirmed")
        ),
        "ota_hardware_observation": (
            config.get("ota_hardware_observation") if target == "legion" else None
        ),
        "source_tree_dirty": bool(
            run("git", "status", "--porcelain", cwd=ROOT, capture=True).strip()
        ),
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
    run(
        sys.executable,
        "-m",
        "platformio",
        "pkg",
        "install",
        "-e",
        TARGETS[args.target],
        cwd=firmware,
        env=PIO_ENV,
    )
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
