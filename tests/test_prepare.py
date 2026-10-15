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
        self.config = {
            **prepare.load_config(),
            "commit": self.git("rev-parse", "HEAD").strip(),
        }
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

    def test_generated_profile_is_reusable_but_stale_version_is_rejected(self):
        profile = self.dest / prepare.PROFILE_PATH
        profile.parent.mkdir(parents=True)
        profile.write_bytes(prepare.render_profile(self.config))
        self.assertFalse(prepare.check_checkout(self.dest, self.config, self.patch))
        changed = {**self.config, "legion_version": "0.3.1"}
        with self.assertRaisesRegex(ValueError, "profile has local changes"):
            prepare.check_checkout(self.dest, changed, self.patch)
        self.assertEqual(profile.read_bytes(), prepare.render_profile(self.config))

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


class FirmwareIdentificationTests(unittest.TestCase):
    def test_versions_and_display_name_follow_the_configuration(self):
        for upstream, legion in (("2.8.2", "0.3.0"), ("2.8.3", "0.4.0")):
            with self.subTest(upstream=upstream, legion=legion):
                config = {"meshtastic_version": upstream, "legion_version": legion}
                version = f"{upstream}.Legion{legion}"
                self.assertEqual(prepare.firmware_version(config), version)
                profile = prepare.render_profile(config).decode()
                self.assertIn(f"-DRAK3401_LEGION_FIRMWARE_VERSION={version}", profile)
                self.assertIn(f"RAK3401 Legion {legion} (experimental)", profile)
                self.assertNotIn("@", profile)

    def test_overlong_or_invalid_versions_fail_before_truncation(self):
        config = {"meshtastic_version": "2.8.2", "legion_version": "0.3.0"}
        self.assertEqual(len(prepare.firmware_version(config)), 17)
        for upstream, legion in (
            ("2.8.12", "0.3.0"),
            ("2.8.2", "0.10.0"),
            ("2.8.2\n", "0.3.0"),
            ("2.8.2", "0.3.0 -DOTHER=1"),
            ("2.8.2", "０.3.0"),
        ):
            with self.subTest(upstream=upstream, legion=legion):
                with self.assertRaises(ValueError):
                    prepare.firmware_version(
                        {"meshtastic_version": upstream, "legion_version": legion}
                    )

    def test_base_version_must_match_the_source(self):
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder)
            (dest / "version.properties").write_text(
                "[VERSION]\nmajor = 2\nminor = 8\nbuild = 2\n"
            )
            prepare.check_base_version(dest, {"meshtastic_version": "2.8.2"})
            with self.assertRaisesRegex(ValueError, "does not match upstream source"):
                prepare.check_base_version(dest, {"meshtastic_version": "2.8.3"})


if __name__ == "__main__":
    unittest.main()
