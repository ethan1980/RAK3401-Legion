"""Pin the Cortex-M4 DFU verifier against real instruction sequences.

The valid fixture resumes Thumb execution after a stubbed SoftDevice SVC and
requests a reset with the OTA marker. The old PSP-to-MSP epilogue must instead
fault outside RAM. Wrong OTA markers and invalid AIRCR keys must not pass.
This guards both the firmware regression and an emulator PC write that loses
Thumb state while skipping the SVC.
"""

import struct
import sys
import unittest
from pathlib import Path

from unicorn import UC_ERR_READ_UNMAPPED, UcError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_dfu import (
    emulate_registration,
    emulate_reset_entry,
    validate_write_authorization,
)

ENTRY = 0x26100
# svc #0x11; movs r0,#0xa8; stores to GPREGRET and AIRCR; literal pool.
VALID_RESET = bytes.fromhex("11dfa82002490860024903480860fee71c0500400ced00e00400fa05")


def image(code):
    return [(0x26000, struct.pack("<I", 0x20040000)), (ENTRY, code)]


class DfuEmulationTests(unittest.TestCase):
    def test_successful_write_reply_requires_update_and_matching_request(self):
        payload = bytes.fromhex("0104")
        old_reply = struct.pack("<BBH", 2, 0, 0) + bytes(12)
        with self.assertRaisesRegex(ValueError, "0x7.*update=1"):
            validate_write_authorization(old_reply, payload, 0, lambda *_: payload)
        reply = bytearray(old_reply)
        reply[6] = 1
        struct.pack_into("<HHI", reply, 8, 0, 2, 0x20001000)
        self.assertEqual(
            validate_write_authorization(reply, payload, 0, lambda *_: payload), 0
        )
        for position, value in ((8, 1), (10, 1), (12, 0)):
            with self.subTest(position=position):
                bad = bytearray(reply)
                struct.pack_into("<H" if position < 12 else "<I", bad, position, value)
                with self.assertRaisesRegex(ValueError, "offset, length and data"):
                    validate_write_authorization(bad, payload, 0, lambda *_: payload)
        with self.assertRaisesRegex(ValueError, "request data"):
            validate_write_authorization(reply, payload, 0, lambda *_: b"\x02\x04")
        denied = bytearray(old_reply)
        struct.pack_into("<H", denied, 4, 0x1FD)
        self.assertEqual(
            validate_write_authorization(denied, payload, 0, lambda *_: b""), 0x1FD
        )

    def test_registration_requires_callback_pointer_and_immediate_dispatch(self):
        # Set the callback, clear the AdaCallback flag and enable write authorization.
        # movs r1,#0x71; str r1,[r0,#76]; movs r2,#68; movs r3,#0;
        # strb r3,[r0,r2]; movs r2,#49; movs r3,#16; strb r3,[r0,r2]; bx lr.
        setter = bytes.fromhex("7121c1644422002383543122102383547047")
        result = emulate_registration(image(setter), ENTRY, 0x71)
        self.assertTrue(result["registration_emulated"])
        self.assertFalse(result["ada_callback_dispatch"])
        deferred = setter[:6] + bytes.fromhex("0823") + setter[8:]
        with self.assertRaisesRegex(ValueError, "immediate callback"):
            emulate_registration(image(deferred), ENTRY, 0x71)
        with self.assertRaisesRegex(ValueError, "immediate callback"):
            emulate_registration(image(setter), ENTRY, 0x73)
        no_authorization = setter[:10] + bytes.fromhex("7047")
        with self.assertRaisesRegex(ValueError, "immediate callback"):
            emulate_registration(image(no_authorization), ENTRY, 0x71)

    def test_ota_reset_keeps_task_stack_and_thumb_state(self):
        result = emulate_reset_entry(image(VALID_RESET), ENTRY)
        self.assertTrue(result["reset_requested"])
        self.assertTrue(result["task_stack_preserved"])
        self.assertEqual(result["gpregret"], "0xa8")
        self.assertFalse(result["hardware_tested"])

    def test_old_stack_switch_epilogue_reads_outside_ram(self):
        # movs r0,#0; msr control,r0; add sp,#0x6c; pop.w {r4-r7,lr}.
        old_epilogue = bytes.fromhex("002080f314881bb0bde8f040")
        with self.assertRaises(UcError) as caught:
            emulate_reset_entry(image(old_epilogue), ENTRY)
        self.assertEqual(caught.exception.errno, UC_ERR_READ_UNMAPPED)

    def test_usb_marker_does_not_count_as_ble_ota(self):
        wrong_marker = bytearray(VALID_RESET)
        wrong_marker[2] = 0x57
        with self.assertRaisesRegex(ValueError, "BLE bootloader"):
            emulate_reset_entry(image(bytes(wrong_marker)), ENTRY)

    def test_invalid_aircr_key_does_not_count_as_reset(self):
        invalid_key = VALID_RESET[:-4] + struct.pack("<I", 4)
        with self.assertRaisesRegex(ValueError, "BLE bootloader"):
            emulate_reset_entry(image(invalid_key), ENTRY)


if __name__ == "__main__":
    unittest.main()
