"""Pin checkout protection in scripts/prepare.py.

Updates must never silently compile a different base or overwrite user edits.
These tests use real Git repositories to guard that protection and the ability
to reuse an exactly patched checkout.
"""

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prepare", ROOT / "scripts/prepare.py")
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class CheckoutProtectionTests(unittest.TestCase):
    def setUp(self):
        self.sandbox = tempfile.TemporaryDirectory()
        self.dest = Path(self.sandbox.name)
        self.file = self.dest / "radio.cpp"
        self.file.write_text("original\n")
        self.git("init", "-q")
        self.git("add", "radio.cpp")
        self.git(
            "-c",
            "user.name=Legion test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "base",
        )
        self.config = {"commit": self.git("rev-parse", "HEAD").strip()}
        self.file.write_text("bulk\n")
        self.patch = self.git("diff", "HEAD", "--")
        self.file.write_text("original\n")

    def tearDown(self):
        self.sandbox.cleanup()

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.dest, text=True)

    def test_clean_and_exact_patch_are_reusable(self):
        self.assertFalse(prepare.check_checkout(self.dest, self.config, self.patch))
        self.file.write_text("bulk\n")
        self.assertTrue(prepare.check_checkout(self.dest, self.config, self.patch))

    def test_wrong_upstream_commit_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unexpected upstream HEAD"):
            prepare.check_checkout(self.dest, {"commit": "0" * 40}, self.patch)

    def test_edits_in_a_patched_file_are_preserved_and_rejected(self):
        self.file.write_text("user changes\n")
        with self.assertRaisesRegex(ValueError, "local changes"):
            prepare.check_checkout(self.dest, self.config, self.patch)
        self.assertEqual(self.file.read_text(), "user changes\n")

    def test_untracked_source_is_rejected(self):
        (self.dest / "extra.cpp").write_text("user source\n")
        with self.assertRaisesRegex(ValueError, "unexpected untracked"):
            prepare.check_checkout(self.dest, self.config, self.patch)

    def test_profile_edits_are_rejected(self):
        profile = self.dest / prepare.PROFILE_PATH
        profile.parent.mkdir(parents=True)
        profile.write_text("local profile\n")
        with self.assertRaisesRegex(ValueError, "profile has local changes"):
            prepare.check_checkout(self.dest, self.config, self.patch)


if __name__ == "__main__":
    unittest.main()
