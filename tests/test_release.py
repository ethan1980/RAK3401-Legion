"""Guard release validation in scripts/prepare_release.py.

Public releases must contain the Legion firmware from the current build commit,
both flashing formats, source and checksums. These cases guard publishing a
baseline artifact, an artifact from another commit, or an incomplete or damaged
download as a ready-to-flash release.
"""

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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


if __name__ == "__main__":
    unittest.main()
