"""Guard release validation in scripts/prepare_release.py.

Public releases must contain the Legion firmware from the current build commit,
both flashing formats, source and checksums. These cases guard publishing a
baseline artifact, an artifact from another commit, or an incomplete or damaged
download as a ready-to-flash release.
"""

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "prepare_release", ROOT / "scripts/prepare_release.py"
)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseValidationTests(unittest.TestCase):
    def setUp(self):
        self.sandbox = tempfile.TemporaryDirectory()
        self.directory = Path(self.sandbox.name)
        self.commit = "a" * 40
        self.manifest = {
            "overlay_commit": self.commit,
            "commit": "b" * 40,
            "target": "legion",
            "environment": "rak3401-legion",
            "legion_version": "0.1.0",
            "meshtastic_version": "2.8.2",
            "advertised_firmware_version": "2.8.2.Legion0.1.0",
        }
        self.uf2 = self.directory / "firmware-rak3401-legion-2.8.2.04cb888.uf2"
        self.ota = self.directory / "firmware-rak3401-legion-2.8.2.04cb888-ota.zip"
        self.uf2.write_bytes(b"firmware fixture")
        self.ota.write_bytes(b"OTA fixture")
        (self.directory / "corresponding-source.tar.gz").write_bytes(b"source fixture")
        self.write_manifest()

    def tearDown(self):
        self.sandbox.cleanup()

    def checksums(self):
        entries = sorted(p for p in self.directory.iterdir() if p.name != "SHA256SUMS")
        (self.directory / "SHA256SUMS").write_text(
            "".join(
                f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
                for p in entries
            )
        )

    def write_manifest(self):
        (self.directory / "legion-build.json").write_text(json.dumps(self.manifest))
        self.checksums()

    def test_valid_release_identifies_commit_and_flashing_files(self):
        metadata = release.prepare_release(self.directory, self.commit)
        self.assertEqual(metadata["tag"], "legion-v0.1.0-aaaaaaa")
        self.assertIn(self.uf2.name, metadata["notes"])
        self.assertIn(self.ota.name, metadata["notes"])

    def test_artifact_from_another_commit_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "different commit"):
            release.prepare_release(self.directory, "c" * 40)

    def test_baseline_artifact_is_rejected(self):
        self.manifest["target"] = "baseline"
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "Only the Legion"):
            release.prepare_release(self.directory, self.commit)

    def test_damaged_firmware_is_rejected(self):
        self.uf2.write_bytes(b"damaged firmware")
        with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
            release.prepare_release(self.directory, self.commit)

    def test_missing_ota_package_is_rejected(self):
        self.ota.unlink()
        self.checksums()
        with self.assertRaisesRegex(ValueError, "one OTA ZIP"):
            release.prepare_release(self.directory, self.commit)

    def test_extra_unchecked_asset_is_rejected(self):
        (self.directory / "unexpected.txt").write_text("not in the build manifest")
        with self.assertRaisesRegex(ValueError, "Every release asset"):
            release.prepare_release(self.directory, self.commit)

    def test_v020_requires_feature_manifest(self):
        self.manifest["legion_version"] = "0.2.0"
        self.manifest["advertised_firmware_version"] = "2.8.2.Legion0.2.0"
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "all declared firmware features"):
            release.prepare_release(self.directory, self.commit)

    def test_v020_notes_describe_enabled_features(self):
        self.manifest.update(
            legion_version="0.2.0",
            advertised_firmware_version="2.8.2.Legion0.2.0",
            bulk_spi=True,
            energy_recovery=True,
            flash_write_deduplication=True,
            flash_readback_crc32=True,
        )
        self.write_manifest()
        metadata = release.prepare_release(self.directory, self.commit)
        self.assertEqual(metadata["tag"], "legion-v0.2.0-aaaaaaa")
        self.assertIn("3.50 V", metadata["notes"])
        self.assertIn("CRC32", metadata["notes"])

    def v030_manifest(self):
        self.manifest.update(
            legion_version="0.3.0",
            advertised_firmware_version="2.8.2.Legion0.3.0",
            bulk_spi=True,
            energy_recovery=True,
            flash_write_deduplication=True,
            flash_readback_crc32=True,
            spi_hz=8000000,
            private_telemetry=True,
            telemetry_channel="LegionRF",
            telemetry_cooldown_seconds=60,
            telemetry_automatic_reports=False,
        )

    def test_v030_notes_explain_channel_commands_and_clock(self):
        self.v030_manifest()
        self.write_manifest()
        metadata = release.prepare_release(self.directory, self.commit)
        self.assertEqual(metadata["tag"], "legion-v0.3.0-aaaaaaa")
        for term in (
            "8 MHz",
            "LegionRF",
            "/telemetry",
            "SECONDARY",
            "PSK",
            "COMMANDS.md",
            "60 seconds",
            "2.8.2.Legion0.3.0",
        ):
            self.assertIn(term, metadata["notes"])

    def test_v030_rejects_wrong_spi_or_missing_private_command_feature(self):
        for field, value in (
            ("spi_hz", 4000000),
            ("private_telemetry", False),
            ("telemetry_channel", "Primary"),
            ("telemetry_cooldown_seconds", 0),
            ("telemetry_automatic_reports", True),
        ):
            with self.subTest(field=field):
                self.v030_manifest()
                self.manifest[field] = value
                self.write_manifest()
                with self.assertRaisesRegex(ValueError, "8 MHz SPI and private"):
                    release.prepare_release(self.directory, self.commit)

    def test_missing_stale_or_truncated_firmware_identification_is_rejected(self):
        for version in (None, "2.8.2.04cb888", "2.8.2.Legion0.2.0", "2.8.2.Legion0.3"):
            with self.subTest(version=version):
                self.v030_manifest()
                self.manifest["advertised_firmware_version"] = version
                self.write_manifest()
                with self.assertRaisesRegex(ValueError, "Advertised firmware version"):
                    release.prepare_release(self.directory, self.commit)

    def v035_manifest(self):
        self.v030_manifest()
        self.manifest.update(
            legion_version="0.3.5",
            advertised_firmware_version="2.8.2.Legion0.3.5",
            ble_dfu_validation={
                "method": "compiled-cortex-m4-emulation",
                "callback_routes_to_ota_reset": True,
                "reset_requested": True,
                "gpregret": "0xa8",
                "task_stack_preserved": True,
                "softdevice_disable_stubbed": True,
                "hardware_tested": False,
            },
        )

    def test_v035_requires_compiled_safe_dfu_reset(self):
        for field, value in (
            ("callback_routes_to_ota_reset", False),
            ("reset_requested", False),
            ("gpregret", "0xb1"),
            ("task_stack_preserved", False),
            ("softdevice_disable_stubbed", False),
            ("method", "source-only"),
        ):
            with self.subTest(field=field):
                self.v035_manifest()
                self.manifest["ble_dfu_validation"][field] = value
                self.write_manifest()
                with self.assertRaisesRegex(ValueError, "verified compiled BLE DFU"):
                    release.prepare_release(self.directory, self.commit)

    def v040_manifest(self):
        self.v035_manifest()
        self.manifest.update(
            legion_version="0.4.0",
            advertised_firmware_version="2.8.2.Legion0.4.0",
            manual_recovery=True,
            recovery_automatic_snapshot=False,
            update_validation={
                "application_only": True,
                "elf_ota_uf2_match": True,
                "reserve_start": "0xe8000",
                "reserve_end": "0xea000",
                "image_margin_bytes": 50000,
            },
        )

    def test_v040_requires_dfu_and_rescue_boundaries(self):
        for field in ("ble_dfu_validation", "update_validation", "manual_recovery"):
            with self.subTest(field=field):
                self.v040_manifest()
                self.manifest.pop(field)
                self.write_manifest()
                with self.assertRaises(ValueError):
                    release.prepare_release(self.directory, self.commit)

    def test_v040_notes_explain_manual_backup_and_preserved_ota(self):
        self.v040_manifest()
        self.write_manifest()
        metadata = release.prepare_release(self.directory, self.commit)
        self.assertEqual(metadata["tag"], "legion-v0.4.0-aaaaaaa")
        for term in (
            "/backup",
            "RECOVERY.md",
            "0xE8000",
            "0.3.5",
            "No automatic snapshot",
            "2.8.2.Legion0.4.0",
        ):
            self.assertIn(term, metadata["notes"])

    def test_v035_notes_require_usb_recovery_and_distinguish_hardware_validation(self):
        self.v035_manifest()
        self.write_manifest()
        metadata = release.prepare_release(self.directory, self.commit)
        self.assertEqual(metadata["tag"], "legion-v0.3.5-aaaaaaa")
        for text in (
            "USB recovery",
            "UF2",
            "0xA8",
            "physical BLE",
            "0.2.0 and 0.3.0",
            "8 MHz",
            "LegionRF",
        ):
            self.assertIn(text, metadata["notes"])

    def v041_manifest(self):
        self.v040_manifest()
        self.manifest.update(
            legion_version="0.4.1",
            advertised_firmware_version="2.8.2.Legion0.4.1",
            release_stage="dfu-candidate-hardware-unverified",
            source_tree_dirty=False,
        )
        self.manifest["ble_dfu_validation"].update(
            registration_emulated=True,
            ada_callback_dispatch=False,
            main_loop_handoff=True,
            write_authorization_enabled=True,
            dfu_dispatch_emulated=True,
        )

    def test_v041_requires_direct_registration_and_preserved_rescue_checks(self):
        for field, value in (
            ("registration_emulated", False),
            ("ada_callback_dispatch", True),
            ("main_loop_handoff", False),
            ("write_authorization_enabled", False),
            ("dfu_dispatch_emulated", False),
        ):
            with self.subTest(field=field):
                self.v041_manifest()
                self.manifest["ble_dfu_validation"][field] = value
                self.write_manifest()
                with self.assertRaisesRegex(ValueError, "immediate DFU"):
                    release.prepare_release(self.directory, self.commit)
        self.v041_manifest()
        self.manifest.pop("update_validation")
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "verified update boundaries"):
            release.prepare_release(self.directory, self.commit)

    def test_v041_notes_are_usb_first_and_do_not_claim_hardware_success(self):
        self.v041_manifest()
        self.write_manifest()
        result = release.prepare_release(self.directory, self.commit)
        for term in (
            "candidate",
            "Install over USB first",
            "hardware OTA unverified",
            "DFU.md",
            "0.4.0 manual rescue",
            "2.8.2.Legion0.4.1",
        ):
            self.assertIn(term, result["notes"])

    def test_uncommitted_candidate_cannot_be_published_as_a_clean_commit(self):
        self.v041_manifest()
        self.manifest["source_tree_dirty"] = True
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "Commit the candidate sources"):
            release.prepare_release(self.directory, self.commit)

    def test_v042_requires_the_write_parameter_contract_check(self):
        self.v041_manifest()
        self.manifest.update(
            legion_version="0.4.2", advertised_firmware_version="2.8.2.Legion0.4.2"
        )
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "checked DFU write authorization"):
            release.prepare_release(self.directory, self.commit)
        self.manifest["ble_dfu_validation"][
            "write_authorization_contract_checked"
        ] = True
        self.write_manifest()
        notes = release.prepare_release(self.directory, self.commit)["notes"]
        for term in ("manual rescue backup", "2.8.2.Legion0.4.2"):
            self.assertIn(term, notes)

    def test_v042_requires_explicit_clean_provenance(self):
        self.v041_manifest()
        self.manifest.update(
            legion_version="0.4.2", advertised_firmware_version="2.8.2.Legion0.4.2"
        )
        self.manifest.pop("source_tree_dirty")
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "explicitly clean"):
            release.prepare_release(self.directory, self.commit)

    def v050_manifest(self):
        self.v041_manifest()
        self.manifest.update(
            legion_version="0.5.0",
            advertised_firmware_version="2.8.2.Legion0.5.0",
            release_stage="experimental",
            remote_control=True,
            control_commands=[
                "msg",
                "reboot",
                "zerohop",
                "ignore",
                "unignore",
                "ignorelist",
            ],
            control_text_limit_bytes=199,
            control_cooldown_seconds=5,
            reg1_dcdc=True,
            dcdc_validation={
                "method": "compiled-arm-call-inspection",
                "reg1_svc": "0x3f",
                "enable_argument": 1,
                "bluetooth_setup_calls_enable": True,
                "hardware_tested": False,
            },
        )
        self.manifest["ble_dfu_validation"][
            "write_authorization_contract_checked"
        ] = True

    def test_v050_requires_commands_reg1_and_preserved_safeguards(self):
        for field in (
            "remote_control",
            "control_commands",
            "control_text_limit_bytes",
            "control_cooldown_seconds",
            "reg1_dcdc",
            "dcdc_validation",
        ):
            with self.subTest(field=field):
                self.v050_manifest()
                self.manifest.pop(field)
                self.write_manifest()
                with self.assertRaisesRegex(
                    ValueError, "remote commands and checked REG1"
                ):
                    release.prepare_release(self.directory, self.commit)
        for field in (
            "ble_dfu_validation",
            "update_validation",
            "manual_recovery",
            "private_telemetry",
            "bulk_spi",
            "source_tree_dirty",
        ):
            with self.subTest(field=field):
                self.v050_manifest()
                self.manifest.pop(field)
                self.write_manifest()
                with self.assertRaises(ValueError):
                    release.prepare_release(self.directory, self.commit)

    def test_v050_notes_describe_new_scope_and_unmeasured_savings(self):
        self.v050_manifest()
        self.write_manifest()
        metadata = release.prepare_release(self.directory, self.commit)
        self.assertEqual(metadata["tag"], "legion-v0.5.0-aaaaaaa")
        for term in (
            "/msg",
            "/reboot",
            "/zerohop",
            "/ignore",
            "/unignore",
            "/ignorelist",
            "REG1",
            "15 minutes",
            "have not been measured",
            "pending",
        ):
            self.assertIn(term, metadata["notes"])
        for term in ("owner reports", "bootloader", "DFU", "OTA", "Message delivered"):
            self.assertNotIn(term, metadata["notes"])

    def test_v050_rejects_wrong_regulator_api_or_enable_argument(self):
        for field, value in (
            ("reg1_svc", "0x0"),
            ("enable_argument", 0),
            ("bluetooth_setup_calls_enable", False),
        ):
            with self.subTest(field=field):
                self.v050_manifest()
                self.manifest["dcdc_validation"][field] = value
                self.write_manifest()
                with self.assertRaisesRegex(ValueError, "checked REG1"):
                    release.prepare_release(self.directory, self.commit)

    def test_v051_release_keeps_validation_and_reports_new_battery_policy(self):
        self.v050_manifest()
        self.manifest.update(legion_version="0.5.1", advertised_firmware_version="2.8.2.Legion0.5.1")
        self.write_manifest()
        metadata = release.prepare_release(self.directory, self.commit)
        self.assertEqual(metadata["tag"], "legion-v0.5.1-aaaaaaa")
        for term in ("eight consecutive", "20 seconds", "3.50 V", "erase.uf2", "not verified"):
            self.assertIn(term, metadata["notes"])
        self.manifest["reg1_dcdc"] = False
        self.write_manifest()
        with self.assertRaises(ValueError):
            release.prepare_release(self.directory, self.commit)

    def test_v042_notes_record_verified_commands_and_pending_automatic_restore(self):
        self.v041_manifest()
        self.manifest.update(
            legion_version="0.4.2", advertised_firmware_version="2.8.2.Legion0.4.2"
        )
        self.manifest["ble_dfu_validation"][
            "write_authorization_contract_checked"
        ] = True
        self.write_manifest()
        notes = release.prepare_release(self.directory, self.commit)["notes"]
        self.assertIn(
            "status, replacement and deletion—are verified on hardware", notes
        )
        self.assertIn("Automatic emergency restoration from a saved backup", notes)
        self.assertIn("remain pending hardware verification", notes)
        for term in ("dfu", "ota", "bootloader", "owner reports", "0.5.0"):
            self.assertNotIn(term, notes.lower())


if __name__ == "__main__":
    unittest.main()
