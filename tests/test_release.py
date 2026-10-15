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


if __name__ == "__main__":
    unittest.main()
