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

    def test_added_source_remains_protected_on_reuse(self):
        source = self.dest / "energy.h"
        source.write_text("battery policy\n")
        self.git("add", "--intent-to-add", "energy.h")
        self.file.write_text("bulk\n")
        expected = self.git("diff", "HEAD", "--")
        self.assertTrue(prepare.check_checkout(self.dest, self.config, expected))
        source.write_text("user policy\n")
        with self.assertRaisesRegex(ValueError, "local changes"):
            prepare.check_checkout(self.dest, self.config, expected)

    def test_expected_patch_includes_new_files(self):
        source = self.dest / "energy.h"
        source.write_text("battery policy\n")
        self.git("add", "--intent-to-add", "energy.h")
        addition = self.git("diff", "HEAD", "--")
        self.git("reset", "--", "energy.h")
        source.unlink()
        with tempfile.TemporaryDirectory() as folder:
            patch = Path(folder) / "addition.patch"
            patch.write_text(addition)
            expected = prepare.expected_diff(self.dest, [patch])
            self.assertFalse(prepare.check_checkout(self.dest, self.config, expected))
            self.git("apply", "--intent-to-add", str(patch))
            self.assertTrue(prepare.check_checkout(self.dest, self.config, expected))

    def test_patch_can_follow_an_upstream_change_outside_its_context(self):
        original = "".join(f"line {n}\n" for n in range(20))
        self.file.write_text(original)
        self.git("add", "radio.cpp")
        self.git(
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "larger base",
        )
        self.file.write_text(original.replace("line 10\n", "bulk\n"))
        old_patch = self.git("diff", "HEAD", "--")
        new_base = original.replace("line 0\n", "new upstream line\n")
        self.file.write_text(new_base)
        self.git("add", "radio.cpp")
        self.git(
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "upstream update",
        )
        config = {"commit": self.git("rev-parse", "HEAD").strip()}
        with tempfile.TemporaryDirectory() as folder:
            patch = Path(folder) / "change.patch"
            patch.write_text(old_patch)
            expected = prepare.expected_diff(self.dest, [patch])
            self.assertEqual(self.file.read_text(), new_base)
            self.assertEqual(self.git("diff", "--cached", "HEAD"), "")
            self.assertNotEqual(expected, old_patch)
            self.git("apply", str(patch))
            self.assertTrue(prepare.check_checkout(self.dest, config, expected))


if __name__ == "__main__":
    unittest.main()
