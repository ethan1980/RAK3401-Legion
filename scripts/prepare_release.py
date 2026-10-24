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
    if manifest.get("source_tree_dirty") is True:
        raise ValueError("Commit the candidate sources and rebuild before publication")
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
    level = tuple(map(int, version.partition("-")[0].split(".")))
    alpha = "-alpha." in version
    if alpha != (manifest.get("release_stage") == "alpha"):
        raise ValueError("Alpha version and release_stage must agree")
    if level >= (0, 4, 2) and manifest.get("source_tree_dirty") is not False:
        raise ValueError(f"Legion {version} requires an explicitly clean source tree")
    if level >= (0, 2, 0) and not all(
        manifest.get(name) is True
        for name in (
            "bulk_spi",
            "energy_recovery",
            "flash_write_deduplication",
            "flash_readback_crc32",
        )
    ):
        raise ValueError(f"Legion {version} requires all declared firmware features")
    if level >= (0, 3, 0) and not (
        manifest.get("private_telemetry") is True
        and manifest.get("spi_hz") == 8000000
        and manifest.get("telemetry_channel") == "LegionRF"
        and manifest.get("telemetry_cooldown_seconds") == 60
        and manifest.get("telemetry_automatic_reports") is False
    ):
        raise ValueError(
            f"Legion {version} requires 8 MHz SPI and private on-demand telemetry"
        )
    if level >= (0, 3, 5):
        dfu = manifest.get("ble_dfu_validation") or {}
        if not (
            dfu.get("method") == "compiled-cortex-m4-emulation"
            and dfu.get("callback_routes_to_ota_reset") is True
            and dfu.get("reset_requested") is True
            and dfu.get("gpregret") == "0xa8"
            and dfu.get("task_stack_preserved") is True
            and dfu.get("softdevice_disable_stubbed") is True
            and dfu.get("hardware_tested") is False
        ):
            raise ValueError(
                f"Legion {version} requires verified compiled BLE DFU reset"
            )
    if level >= (0, 4, 0):
        update = manifest.get("update_validation") or {}
        if not (
            manifest.get("manual_recovery") is True
            and manifest.get("recovery_automatic_snapshot") is False
            and update.get("application_only") is True
            and update.get("elf_ota_uf2_match") is True
            and update.get("reserve_start") == "0xe8000"
            and update.get("reserve_end") == "0xea000"
            and update.get("image_margin_bytes", -1) >= 0
        ):
            raise ValueError(
                f"Legion {version} requires manual recovery and verified update boundaries"
            )
    if level >= (0, 4, 1):
        dfu = manifest.get("ble_dfu_validation") or {}
        if not (
            dfu.get("registration_emulated") is True
            and dfu.get("ada_callback_dispatch") is False
            and dfu.get("main_loop_handoff") is True
            and dfu.get("write_authorization_enabled") is True
            and dfu.get("dfu_dispatch_emulated") is True
        ):
            raise ValueError(
                f"Legion {version} requires immediate DFU registration and main-loop handoff"
            )
    if (
        level >= (0, 4, 2)
        and dfu.get("write_authorization_contract_checked") is not True
    ):
        raise ValueError(
            f"Legion {version} requires checked DFU write authorization parameters"
        )
    if level >= (0, 5, 0):
        commands = ["msg", "reboot", "zerohop", "ignore", "unignore", "ignorelist"]
        if level >= (0, 6, 0):
            commands += ["trace", "boot", "apc"]
        dcdc = manifest.get("dcdc_validation") or {}
        if not (
            manifest.get("remote_control") is True
            and manifest.get("control_commands") == commands
            and manifest.get("control_text_limit_bytes") == 199
            and manifest.get("control_cooldown_seconds") == 5
            and manifest.get("reg1_dcdc") is True
            and dcdc.get("method") == "compiled-arm-call-inspection"
            and dcdc.get("reg1_svc") == "0x3f"
            and dcdc.get("enable_argument") == 1
            and dcdc.get("bluetooth_setup_calls_enable") is True
            and dcdc.get("hardware_tested") is False
        ):
            raise ValueError(
                f"Legion {version} requires remote commands and checked REG1 DC/DC activation"
            )
    if level >= (0, 6, 0):
        if not (
            alpha
            and manifest.get("release_stage") == "alpha"
            and re.fullmatch(r"[0-9a-f]{40}", manifest.get("commit", ""))
            and manifest["commit"] != "04cb8885118b959a9f538cd5881bd7d595758911"
            and all(
                manifest.get(name) is True
                for name in (
                    "cc310_packet_sha256",
                    "cc310_ack_hmac_sha256",
                    "cc310_software_fallback",
                    "boot_diagnostics",
                    "backup_freshness_status",
                    "apc_battery_conservation",
                )
            )
            and manifest.get("apc_candidate_stage") == "S1"
            and manifest.get("apc_modes") == ["off", "observe", "shadow", "on"]
            and manifest.get("apc_boot_mode") == "off"
            and all(
                manifest.get(name) is False
                for name in (
                    "apc_persistent_settings",
                    "apc_adaptive_rf_power",
                    "apc_hardware_tested",
                    "boot_diagnostics_flash_writes",
                    "backup_freshness_flash_writes",
                    "hardware_tested",
                    "ota_hardware_tested",
                    "energy_savings_measured",
                    "trace_hardware_tested",
                    "cc310_hardware_measured",
                    "boot_diagnostics_hardware_tested",
                    "backup_freshness_hardware_tested",
                )
            )
        ):
            raise ValueError(
                "Legion 0.6.0 alpha requires the migrated base, S1 scope and explicit pending hardware validation"
            )
    spi_mhz = manifest.get("spi_hz", 4000000) // 1000000
    features = f"This release includes bulk SPI at **{spi_mhz} MHz**.\n\n"
    if level >= (0, 5, 0):
        features += (
            "### New commands\n\n"
            "| Command | Behavior |\n| --- | --- |\n"
            "| `/msg !nodeid <channel> <message>` | Originate text from the selected Legion; confirm queue acceptance. |\n"
            "| `/reboot !nodeid` | Schedule a normal restart 20 seconds after acceptance. |\n"
            "| `/zerohop !nodeid [page]` | Direct RF nodes with full IDs, short names and SNR. |\n"
            "| `/ignore !peerid` | Every receiving Legion independently ignores the peer. |\n"
            "| `/unignore !peerid` | Every receiving Legion independently unignores the peer. |\n"
            "| `/ignorelist [page]` | Each receiving Legion reports its effective ignore list. |\n\n"
            "Commands use the existing private LegionRF channel. New commands share a separate five-second cooldown "
            "and duplicate suppression. Directory snapshots preserve page order for 15 minutes and return one page "
            "per request. Ignore changes use the normal persistent NodeDB and legacy LoRa state; pending writes "
            "are identified explicitly. Queue acceptance does not confirm RF reception.\n\n"
            "### REG1 DC/DC\n\n"
            "The nRF52840 REG1 DC/DC converter is enabled automatically through the SoftDevice API after successful "
            "initialization. Activation and readback were verified on the diagnostic RAK with USB power and after "
            "a battery-powered restart. REG0 and UICR retain their existing configuration. Whole-node current "
            "reduction and battery-life improvement have not been measured.\n\n"
            "The release retains energy recovery, verified preference writes, private telemetry and manual rescue "
            "backup. Telemetry and all backup commands were verified on 0.4.2 hardware. Automated tests cover the "
            "new commands and REG1 API use. New-command hardware validation, automatic emergency restoration, "
            "recovery announcement and physical power-cut testing remain pending.\n\n"
            f"Read [COMMANDS.md](https://github.com/ethan1980/RAK3401-Legion/blob/{commit}/COMMANDS.md) "
            f"and [RECOVERY.md](https://github.com/ethan1980/RAK3401-Legion/blob/{commit}/RECOVERY.md).\n\n"
        )
    if version == "0.4.2":
        features += (
            "Legion includes manual rescue backup, radio optimizations, energy recovery, "
            "verified preference writes and private telemetry. "
            "Telemetry, current firmware version and min/max formatting are verified "
            "on hardware. All backup commands—creation with its success confirmation, "
            "status, replacement and deletion—are verified on hardware. "
            "Automatic emergency restoration from a saved backup, its recovery "
            "announcement and physical power-cut recovery remain pending hardware "
            "verification.\n\n"
            "Use `/backup !xxxxxxxx` to create a rescue point explicitly. Status, replace "
            "and delete require the same full target ID. No automatic snapshot is created. "
            "Read [RECOVERY.md](https://github.com/ethan1980/RAK3401-Legion/blob/main/RECOVERY.md) "
            "and [COMMANDS.md](https://github.com/ethan1980/RAK3401-Legion/blob/main/COMMANDS.md). "
            "The compiled version is 2.8.2.Legion0.4.2 in telemetry, MQTT, device metadata "
            "and Bluetooth.\n\n"
            "Superseded download releases are withdrawn; source tags and Git history "
            "remain available.\n\n"
        )
    if version == "0.4.1":
        features += (
            "**DFU candidate, hardware OTA unverified. Install over USB first.** "
            "Installed 0.3.5 has a confirmed ATT timeout during DFU entry; 0.4.0 "
            "retains that entry implementation. This candidate replies directly from "
            "the BLE task and prepares the safe 0xA8 reset in the main loop. "
            "Native SDK/RTOS-stub tests and compiled ARM checks are not a physical OTA test. "
            "Complete and repeat OTA on an accessible node before remounting it. "
            f"See [DFU.md](https://github.com/ethan1980/RAK3401-Legion/blob/{commit}/DFU.md).\n\n"
            "The 0.4.0 manual rescue engine, channel commands, configuration and reserved "
            "flash layout are unchanged. No bootloader or SoftDevice update is included. "
            "The compiled version is 2.8.2.Legion0.4.1, also used in telemetry, MQTT "
            "and Bluetooth. Root cause and full OTA recovery remain hardware-test pending.\n\n"
        )
    if version == "0.4.0":
        features += (
            "Manual rescue backup: `/backup !xxxxxxxx`, `/backup status !xxxxxxxx`, "
            "`/backup replace !xxxxxxxx` and `/backup delete !xxxxxxxx` on private LegionRF. "
            "Only the addressed node acts. No automatic snapshot is created. The rescue point "
            "includes names, private identity, channels, radio/module configuration and fixed position. "
            "Confirmed essential preference loss can restore it; ordinary boots, name changes and OTA "
            "with healthy preferences do not. A successful recovery queues the requested "
            "Ashes to ashes notice. Factory reset restores an armed rescue point: delete the "
            "rescue point first to deliberately remain blank.\n\n"
            f"Read [RECOVERY.md](https://github.com/ethan1980/RAK3401-Legion/blob/{commit}/RECOVERY.md) "
            "for commands, deletion, power-cut behavior and limits. Recovery/power-cut hardware "
            "testing is pending.\n\n"
            "The 0.3.5 BLE DFU correction is preserved. From installed **0.3.5**, select this "
            "release's **OTA ZIP**. From 0.2.0/0.3.0, use this release's UF2 over USB. "
            "Compiled callback and Cortex-M4 reset validation remain mandatory. The ELF, "
            "application-only OTA BIN and UF2 are cross-checked and must end before the "
            "0xE8000–0xEA000 rescue reserve. Physical end-to-end OTA remains unverified.\n\n"
            "Telemetry displays the compiled Legion version and spaces its min/max labels. "
            "MQTT, BLE and device metadata advertise 2.8.2.Legion0.4.0. "
            "The owner reports stable normal operation with 0.3.5; keep it for rollback.\n\n"
        )
    if version == "0.3.5":
        features += (
            "**USB recovery from Legion 0.2.0 or 0.3.0:** install this release's UF2 "
            "over USB. Their installed BLE DFU entry can reset into normal firmware "
            "before accepting an OTA upload; a different ZIP cannot repair that "
            "installed entry. Use the normal UF2 update and keep the existing "
            "configuration; do not run factory erase/reset.\n\n"
            "This hotfix preserves flash quiescing and Bluetooth peer/bond handoff "
            "but enters BLE OTA through the nRF52 core's full-reset path "
            "(`GPREGRET=0xA8`), avoiding the unsafe PSP-to-MSP C epilogue. "
            "The active callback and compiled reset entry are checked in Cortex-M4 "
            "emulation before packaging. SoftDevice disable is stubbed in that "
            "check; physical BLE reconnection and end-to-end OTA still need "
            "verification on a RAK3401.\n\n"
            "Legion 0.2.0 and 0.3.0 downloads are withdrawn after this release "
            "is published; their source tags and Git history are retained.\n\n"
        )
    if manifest.get("private_telemetry") and level < (0, 5, 0):
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
    if manifest.get("energy_recovery") and level < (0, 5, 0):
        features += (
            "RAK-specific battery recovery and TX reserve are enabled. Battery sleep: below "
            "3.50 V for three readings; boot reserve: 3.60 V. Hardware wake: approximately "
            "3.78 V nominal before hysteresis/tolerances. Normal TX power, region, channels "
            "and role remain configured by Meshtastic.\n\n"
        )
    if manifest.get("flash_write_deduplication") and level < (0, 5, 0):
        features += (
            "Identical encoded protobuf files are preserved without another write.\n\n"
        )
    if manifest.get("flash_readback_crc32") and level < (0, 5, 0):
        features += "Temporary writes are verified with CRC32 and exact length before rename.\n\n"
    if version == "0.5.1":
        features += (
            "Battery sleep requires eight consecutive readings below 3.50 V, checked every 20 seconds. "
            "The new timing still requires hardware validation. Manual rescue restoration was observed "
            "after erase.uf2, bootloader 0.4.4 and Legion D1 UF2 installation; recovery announcement "
            "reception was not verified. Physical interrupted-write testing remains pending.\n\n"
        )
    if alpha:
        features = (
            Path(__file__).resolve().parents[1] / "RELEASE_NOTES.md"
        ).read_text() + "\n\n"
        for name in (
            "README.md",
            "COMMANDS.md",
            "RECOVERY.md",
            "ENERGY-RECOVERY.md",
            "APC.md",
            "CHANGELOG.md",
        ):
            features = features.replace(
                f"]({name})",
                f"](https://github.com/ethan1980/RAK3401-Legion/blob/{commit}/{name})",
            )
    downloads = (
        "- Firmware packages: see the release assets.\n\n"
        if level >= (0, 4, 2)
        else f"- USB firmware: `{uf2[0]}`\n- Wireless firmware: `{ota[0]}`\n\n"
    )
    return {
        "tag": f"legion-v{version}-{commit[:7]}",
        "title": f"Legion {version} - Meshtastic {upstream} ({commit[:7]})",
        "prerelease": True,
        "notes": (
            "Experimental firmware for the RAK3401 1W with RAK13302.\n\n"
            f"- Legion version: `{version}`\n"
            f"- Meshtastic base: `{upstream}`, commit `{manifest['commit']}`\n"
            f"- Legion build commit: `{commit}`\n"
            f"- Advertised firmware: `{advertised_version}` (MQTT, device metadata and BLE)\n"
            f"{downloads}"
            f"{features}"
            "The advertised version is generated from `upstream.json`. Firmware filenames "
            "retain the upstream version and source hash; both complete source commits "
            "are recorded above and in `legion-build.json`.\n\n"
            "The assets include source, build metadata, debug files and `SHA256SUMS`.\n"
            "Experimental: controlled measurements of voltage thresholds, sleep current, "
            "battery savings and long-term radio stability remain pending on the complete kit.\n"
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
