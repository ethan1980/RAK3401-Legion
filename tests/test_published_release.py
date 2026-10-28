"""Require an intact experimental prerelease with exact source provenance."""

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_published_release import verify_published_release


class PublishedReleaseTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.directory = Path(self.folder.name)
        self.commit = "a" * 40
        manifest = {
            "overlay_commit": self.commit,
            "commit": "b" * 40,
            "target": "legion",
            "environment": "rak3401-legion",
            "legion_version": "0.1.0",
            "meshtastic_version": "2.8.2",
            "advertised_firmware_version": "2.8.2.Legion0.1.0",
        }
        for name in (
            "firmware-rak3401-legion-test.uf2",
            "firmware-rak3401-legion-test-ota.zip",
            "corresponding-source.tar.gz",
        ):
            (self.directory / name).write_bytes(name.encode())
        (self.directory / "legion-build.json").write_text(json.dumps(manifest))
        paths = list(self.directory.iterdir())
        (self.directory / "SHA256SUMS").write_text(
            "".join(
                f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
                for p in paths
            )
        )
        self.published = {
            "draft": False,
            "prerelease": True,
            "tag_name": "legion-v0.1.0-aaaaaaa",
            "target_commitish": self.commit,
            "assets": [
                {
                    "name": p.name,
                    "state": "uploaded",
                    "size": p.stat().st_size,
                    "digest": f"sha256:{hashlib.sha256(p.read_bytes()).hexdigest()}",
                }
                for p in self.directory.iterdir()
            ],
        }

    def test_intact_published_replacement_is_accepted(self):
        self.assertEqual(
            verify_published_release(self.directory, self.commit, self.published),
            self.published["tag_name"],
        )

    def test_draft_wrong_tag_or_wrong_commit_cannot_authorize_withdrawal(self):
        for field, value in (
            ("draft", True),
            ("prerelease", False),
            ("prerelease", None),
            ("tag_name", "legion-v0.4.2-elsewhere"),
            ("target_commitish", "c" * 40),
        ):
            with self.subTest(field=field):
                published = {**self.published, field: value}
                with self.assertRaisesRegex(ValueError, "commit and tag"):
                    verify_published_release(self.directory, self.commit, published)

    def test_incomplete_duplicate_or_extra_assets_are_rejected(self):
        for assets in (
            self.published["assets"][:-1],
            self.published["assets"] + [self.published["assets"][0]],
            self.published["assets"] + [{"name": "unexpected"}],
        ):
            with self.subTest(assets=len(assets)):
                with self.assertRaisesRegex(ValueError, "missing, extra or duplicate"):
                    verify_published_release(
                        self.directory,
                        self.commit,
                        {**self.published, "assets": assets},
                    )

    def test_stable_publication_must_not_be_marked_as_a_prerelease(self):
        expected = {"tag": self.published["tag_name"], "prerelease": False}
        with patch("verify_published_release.prepare_release", return_value=expected):
            published = {**self.published, "prerelease": False}
            self.assertEqual(
                verify_published_release(self.directory, self.commit, published),
                expected["tag"],
            )
            with self.assertRaisesRegex(ValueError, "commit and tag"):
                verify_published_release(self.directory, self.commit, self.published)

    def test_wrong_remote_hash_size_or_upload_state_is_rejected(self):
        for field, value in (
            ("digest", "sha256:" + "0" * 64),
            ("size", 0),
            ("state", "new"),
        ):
            with self.subTest(field=field):
                published = copy.deepcopy(self.published)
                published["assets"][0][field] = value
                with self.assertRaisesRegex(ValueError, "does not match the build"):
                    verify_published_release(self.directory, self.commit, published)


if __name__ == "__main__":
    unittest.main()
