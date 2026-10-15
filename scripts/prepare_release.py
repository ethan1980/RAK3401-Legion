#!/usr/bin/env python3
"""Validate a Legion artifact and prepare its GitHub Release metadata."""

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

from prepare import firmware_version


def prepare_release(directory, commit):
    directory = Path(directory)
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("A full build commit SHA is required")
    manifest = json.loads((directory / "legion-build.json").read_text())
    if manifest["overlay_commit"] != commit:
        raise ValueError("Artifact was built from a different commit")
    if manifest["target"] != "legion" or manifest["environment"] != "rak3401-legion":
        raise ValueError("Only the Legion firmware can be published")
    for field in ("legion_version", "meshtastic_version"):
        if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", manifest[field]):
            raise ValueError(f"Invalid version: {field}")
    advertised_version = firmware_version(manifest)
    if manifest.get("advertised_firmware_version") != advertised_version:
        raise ValueError(
            "Advertised firmware version does not match the release versions"
        )

    files = {p.name for p in directory.iterdir() if p.is_file()}
    uf2 = [
        name
        for name in files
        if name.startswith("firmware-rak3401-legion-") and name.endswith(".uf2")
    ]
    ota = [
        name
        for name in files
        if name.startswith("firmware-rak3401-legion-") and name.endswith("-ota.zip")
    ]
    if len(uf2) != 1 or len(ota) != 1 or "corresponding-source.tar.gz" not in files:
        raise ValueError("Release requires one Legion UF2, one OTA ZIP and source")
    checked = set()
    for line in (directory / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        if (
            not re.fullmatch(r"[0-9a-f]{64}", digest)
            or name not in files
            or name in checked
        ):
            raise ValueError("Invalid or duplicate checksum entry")
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Checksum mismatch: {name}")
        checked.add(name)
    if checked != files - {"SHA256SUMS"}:
        raise ValueError("Every release asset must have a checksum")

    version = manifest["legion_version"]
    upstream = manifest["meshtastic_version"]
    if version in ("0.2.0", "0.3.0") and not all(
        manifest.get(name) is True
        for name in (
            "bulk_spi",
            "energy_recovery",
            "flash_write_deduplication",
            "flash_readback_crc32",
        )
    ):
        raise ValueError(f"Legion {version} requires all declared firmware features")
    if version == "0.3.0" and not (
        manifest.get("private_telemetry") is True
        and manifest.get("spi_hz") == 8000000
        and manifest.get("telemetry_channel") == "LegionRF"
        and manifest.get("telemetry_cooldown_seconds") == 60
        and manifest.get("telemetry_automatic_reports") is False
    ):
        raise ValueError(
            "Legion 0.3.0 requires 8 MHz SPI and private on-demand telemetry"
        )
    spi_mhz = manifest.get("spi_hz", 4000000) // 1000000
    features = f"This release includes bulk SPI at **{spi_mhz} MHz**.\n\n"
    if manifest.get("private_telemetry"):
        features += (
            "Private on-demand diagnostics: create a SECONDARY channel named exactly "
            "`LegionRF` with your own random 16- or 32-byte PSK. No shared key is built "
            "into the firmware. Send `/telemetry` in that channel, or "
            "`/telemetry !xxxxxxxx` to select one node. Replies are ordinary channel "
            "text messages and are also copied to a locally connected app. "
            "There are no automatic diagnostic broadcasts. "
            "A node accepts at most one response per 60 seconds, with duplicate "
            "suppression and a random response delay. Reports include chip "
            "temperature, physical battery voltage, estimated charge, noise samples, "
            "packet counters and uptime. Diagnostics are accumulated in RAM only.\n\n"
            f"Read [COMMANDS.md](https://github.com/ethan1980/RAK3401-Legion/blob/{commit}/COMMANDS.md) "
            "for setup, fields and limits. The private channel shares the existing "
            "LoRa frequency and airtime. Requests cannot wake an energy-sleeping node.\n\n"
        )
    if manifest.get("energy_recovery"):
        features += (
            "RAK-specific battery recovery and TX reserve are enabled. Battery sleep: below "
            "3.50 V for three readings; boot reserve: 3.60 V. Hardware wake: approximately "
            "3.78 V nominal before hysteresis/tolerances. Normal TX power, region, channels "
            "and role remain configured by Meshtastic.\n\n"
        )
    if manifest.get("flash_write_deduplication"):
        features += (
            "Identical encoded protobuf files are preserved without another write.\n\n"
        )
    if manifest.get("flash_readback_crc32"):
        features += "Temporary writes are verified with CRC32 and exact length before rename.\n\n"
    return {
        "tag": f"legion-v{version}-{commit[:7]}",
        "title": f"Legion {version} - Meshtastic {upstream} ({commit[:7]})",
        "notes": (
            "Experimental firmware for the RAK3401 1W with RAK13302.\n\n"
            f"- Legion version: `{version}`\n"
            f"- Meshtastic base: `{upstream}`, commit `{manifest['commit']}`\n"
            f"- Legion build commit: `{commit}`\n"
            f"- Advertised firmware: `{advertised_version}` (MQTT, device metadata and BLE)\n"
            f"- USB/bootloader firmware: `{uf2[0]}`\n"
            f"- OTA/DFU firmware: `{ota[0]}`\n\n"
            f"{features}"
            "The advertised version is generated from `upstream.json`. Firmware filenames "
            "retain the upstream version and source hash; both complete source commits "
            "are recorded above and in `legion-build.json`.\n\n"
            "The assets include source, build metadata, debug files and `SHA256SUMS`.\n"
            "Experimental: hardware stability, voltage thresholds, sleep current and battery "
            "savings still require testing on the complete kit. Keep a previous build for rollback.\n"
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--notes", type=Path, default=Path("release-notes.md"))
    args = parser.parse_args()
    metadata = prepare_release(args.directory, args.commit)
    args.notes.write_text(metadata["notes"])
    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        output.write(f"tag={metadata['tag']}\ntitle={metadata['title']}\n")


if __name__ == "__main__":
    main()
