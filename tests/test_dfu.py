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
from validate_dfu import emulate_reset_entry

ENTRY = 0x26100
# svc #0x11; movs r0,#0xa8; stores to GPREGRET and AIRCR; literal pool.
VALID_RESET = bytes.fromhex("11dfa82002490860024903480860fee71c0500400ced00e00400fa05")


def image(code):
    return [(0x26000, struct.pack("<I", 0x20040000)), (ENTRY, code)]


class DfuEmulationTests(unittest.TestCase):
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
