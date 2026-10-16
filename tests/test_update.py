"""Pin application-package integrity and reserve protection before a release.

The ELF reader is replaced with a small segment fixture; the real ZIP, init
packet and UF2 parsers are exercised against complete files. Regressions here
could publish a bootloader update, mismatched image or overwritten rescue page.
"""

import binascii
import json
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import validate_update as update


class Segment(dict):
    def data(self):
        return self["payload"]


class Symbols:
    def get_symbol_by_name(self, name):
        return [{"st_value": 1}]


class Elf:
    def __init__(self, data):
        self.data = data

    def get_section_by_name(self, name):
        return Symbols()

    def iter_segments(self):
        return [
            Segment(
                p_paddr=update.APP_START,
                p_filesz=len(self.data),
                p_type="PT_LOAD",
                payload=self.data,
            )
        ]


class UpdatePackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.elf = self.folder / "firmware.elf"
        self.ota = self.folder / "firmware.zip"
        self.uf2 = self.folder / "firmware.uf2"
        self.elf.write_bytes(b"ELF fixture")
        self.binary = bytes(range(256))
        self.extra_manifest = {}
        self.write_zip()
        self.write_uf2()
        self.reader = patch.object(
            update, "ELFFile", side_effect=lambda _: Elf(self.binary)
        )
        self.reader.start()
        self.addCleanup(self.reader.stop)

    def tearDown(self):
        self.temp.cleanup()

    def write_zip(self, bad_crc=False):
        crc = binascii.crc_hqx(self.binary, 0xFFFF) ^ int(bad_crc)
        manifest = {
            "application": {
                "bin_file": "application.bin",
                "dat_file": "application.dat",
                "init_packet_data": {
                    "firmware_crc16": crc,
                    "application_version": 0xFFFFFFFF,
                },
            },
            "dfu_version": 0.5,
            **self.extra_manifest,
        }
        with zipfile.ZipFile(self.ota, "w") as archive:
            archive.writestr("manifest.json", json.dumps({"manifest": manifest}))
            archive.writestr("application.bin", self.binary)
            archive.writestr(
                "application.dat",
                struct.pack("<HHIHHH", 82, 65535, 0xFFFFFFFF, 1, 0xB6, crc),
            )

    def write_uf2(
        self, address=update.APP_START, family=update.UF2_FAMILY, corrupt=False
    ):
        header = struct.pack(
            "<8I", 0x0A324655, 0x9E5D5157, 0x2000, address, 256, 0, 1, family
        )
        payload = bytearray(self.binary.ljust(256, b"\0"))
        if corrupt:
            payload[22] ^= 1
        self.uf2.write_bytes(
            header + payload + b"\0" * 220 + struct.pack("<I", 0x0AB16F30)
        )

    def validate(self):
        return update.validate_update(self.elf, self.ota, self.uf2)

    def test_matching_application_package_leaves_reserve_clear(self):
        report = self.validate()
        self.assertTrue(report["application_only"] and report["elf_ota_uf2_match"])
        self.assertEqual(report["image_end"], hex(update.APP_START + 256))

    def test_final_uf2_padding_matches_the_pinned_packager(self):
        self.binary = bytes(range(128))
        self.write_zip()
        self.write_uf2()
        self.assertTrue(self.validate()["elf_ota_uf2_match"])

    def test_combined_bootloader_update_is_rejected(self):
        self.extra_manifest["bootloader"] = {}
        self.write_zip()
        with self.assertRaisesRegex(ValueError, "only an application"):
            self.validate()

    def test_bad_ota_crc_is_rejected(self):
        self.write_zip(bad_crc=True)
        with self.assertRaisesRegex(ValueError, "CRC mismatch"):
            self.validate()

    def test_oversized_application_is_rejected(self):
        self.binary = b"\xff" * (update.RESCUE_START - update.APP_START + 4)
        self.write_zip()
        with self.assertRaisesRegex(ValueError, "overlaps the recovery reserve"):
            self.validate()

    def test_uf2_cannot_touch_the_rescue_page(self):
        self.write_uf2(address=update.RESCUE_START)
        with self.assertRaisesRegex(ValueError, "overlaps the recovery reserve"):
            self.validate()

    def test_wrong_uf2_family_and_different_payload_are_rejected(self):
        self.write_uf2(family=1)
        with self.assertRaisesRegex(ValueError, "family"):
            self.validate()
        self.write_uf2(corrupt=True)
        with self.assertRaisesRegex(ValueError, "payload differs"):
            self.validate()


if __name__ == "__main__":
    unittest.main()
