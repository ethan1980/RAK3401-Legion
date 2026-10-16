#!/usr/bin/env python3
"""Check the active BLE callback and emulate the compiled OTA reset entry.

The immediate callback must be registered without AdaCallback dispatch, the
main-loop handoff must reach enterOTADfu, and the latter must request a hardware
reset with GPREGRET=0xA8 on the same PSP.
The emulator stubs successful SoftDevice disable; it is not a radio/bootloader
or physical OTA test.
"""

import argparse
import json
import struct
from pathlib import Path

from capstone import CS_ARCH_ARM, CS_MODE_MCLASS, CS_MODE_THUMB, Cs
from capstone.arm import ARM_OP_IMM
from elftools.elf.elffile import ELFFile
from unicorn import (
    UC_ARCH_ARM,
    UC_HOOK_CODE,
    UC_HOOK_MEM_WRITE,
    UC_MODE_MCLASS,
    UC_MODE_THUMB,
    Uc,
)
from unicorn.arm_const import (
    UC_ARM_REG_CONTROL,
    UC_ARM_REG_LR,
    UC_ARM_REG_MSP,
    UC_ARM_REG_PC,
    UC_ARM_REG_PSP,
    UC_ARM_REG_R0,
    UC_ARM_REG_R1,
    UC_ARM_REG_XPSR,
)

RAM_START, RAM_END = 0x20000000, 0x20040000
GPREGRET, AIRCR = 0x4000051C, 0xE000ED0C


def validate_write_authorization(reply, payload, offset, read_memory):
    """Check the pinned S140 write-reply ABI, including the mandatory data update."""
    if len(reply) != 16 or reply[0] != 2:
        raise ValueError("DFU authorization must reply to the pending write")
    status = struct.unpack_from("<H", reply, 4)[0]
    if status == 0:
        if not reply[6] & 1:
            raise ValueError(
                "NRF_ERROR_INVALID_PARAM (0x7): successful write requires update=1"
            )
        supplied_offset, length, pointer = struct.unpack_from("<HHI", reply, 8)
        if supplied_offset != offset or length != len(payload) or not pointer:
            raise ValueError(
                "Successful DFU write must supply its offset, length and data"
            )
        if bytes(read_memory(pointer, length)) != payload:
            raise ValueError(
                "Successful DFU write must supply the pending request data"
            )
    return status


def emulate_registration(
    segments, entry, callback, *, handler=None, notify=None, ada=None
):
    """Execute the real setter; offsets belong to the pinned 0fd295f1 SDK ABI."""
    cpu = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
    cpu.mem_map(0, 0x100000)
    cpu.mem_map(RAM_START, RAM_END - RAM_START)
    for address, data in segments:
        cpu.mem_write(address, data)
    characteristic = 0x20030000
    cpu.mem_write(characteristic, b"\xff" * 88)
    cpu.mem_write(characteristic + 49, b"\0")
    cpu.reg_write(UC_ARM_REG_XPSR, 0x01000000)
    cpu.reg_write(UC_ARM_REG_MSP, RAM_END - 0x100)
    cpu.reg_write(UC_ARM_REG_R0, characteristic)
    cpu.reg_write(UC_ARM_REG_LR, 0x1001)
    returned = []
    probe = {"notifications": True, "replies": [], "payload": b""}

    def stop(machine, address, _size, _):
        if address == 0x1000:
            returned.append(True)
            machine.emu_stop()
        elif handler is not None and address == (ada & ~1):
            raise ValueError("Compiled DFU authorization tried to use AdaCallback")
        elif handler is not None and address == (notify & ~1):
            machine.reg_write(UC_ARM_REG_R0, int(probe["notifications"]))
            machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))
        elif handler is not None and bytes(machine.mem_read(address, 2)) == b"\xb0\xdf":
            reply = bytes(machine.mem_read(machine.reg_read(UC_ARM_REG_R1), 16))
            probe["replies"].append(
                validate_write_authorization(
                    reply, probe["payload"], 0, machine.mem_read
                )
            )
            machine.reg_write(UC_ARM_REG_R0, 0)
            machine.reg_write(UC_ARM_REG_PC, (address + 2) | 1)

    cpu.hook_add(UC_HOOK_CODE, stop)
    cpu.emu_start(entry | 1, 0, count=200)
    pointer = struct.unpack("<I", cpu.mem_read(characteristic + 76, 4))[0]
    deferred = cpu.mem_read(characteristic + 68, 1)[0] & 8
    authorization = cpu.mem_read(characteristic + 49, 1)[0] & 16
    if not returned or pointer != callback or deferred or not authorization:
        raise ValueError(
            "Compiled DFU registration must install the immediate callback"
        )
    result = {
        "registration_emulated": True,
        "ada_callback_dispatch": False,
        "write_authorization_enabled": True,
    }
    if handler is not None:
        # Run the actual SDK dispatcher and compiled probe handler, with notify/SVC stubs.
        event = characteristic + 0x200
        cpu.mem_write(characteristic + 50, struct.pack("<H", 0x12))
        for payload, notifications, expected in (
            (b"\x02", True, 0),
            (b"\x02\x01", True, 0),
            (b"\x02" + bytes(range(1, 23)), True, 0),
            (b"\x02", False, 0x1FD),
            (b"", True, 0x10D),
            (b"\x01\x04", False, 0x1FD),
        ):
            request = bytearray(14)
            struct.pack_into("<H", request, 0, 0x12)
            request[6] = 1
            struct.pack_into("<H", request, 10, len(payload))
            request[12 : 12 + len(payload)] = payload
            cpu.mem_write(
                event, struct.pack("<HHHBB", 0x51, 22, 0, 2, 0) + bytes(request)
            )
            probe["notifications"] = notifications
            probe["payload"] = payload
            probe["replies"] = []
            returned.clear()
            cpu.reg_write(UC_ARM_REG_R0, characteristic)
            cpu.reg_write(UC_ARM_REG_R1, event)
            cpu.reg_write(UC_ARM_REG_LR, 0x1001)
            cpu.emu_start(handler | 1, 0, count=2000)
            if not returned or probe["replies"] != [expected]:
                raise ValueError(
                    "Compiled DFU event did not produce one immediate ATT reply"
                )
        result["dfu_dispatch_emulated"] = True
        result["compiled_probe_cases"] = 6
        result["write_authorization_contract_checked"] = True
        result["write_authorization_service_stubbed"] = True
    return result


def emulate_reset_entry(segments, entry, expected_magic=0xA8):
    decoder = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
    decoder.detail = True
    cpu = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
    cpu.mem_map(0, 0x100000)
    cpu.mem_map(RAM_START, RAM_END - RAM_START)
    cpu.mem_map(0x40000000, 0x1000)
    cpu.mem_map(0xE000E000, 0x1000)
    for address, data in segments:
        cpu.mem_write(address, data)
    initial_msp = struct.unpack("<I", cpu.mem_read(0x26000, 4))[0]
    cpu.reg_write(UC_ARM_REG_XPSR, 0x01000000)
    cpu.reg_write(UC_ARM_REG_MSP, initial_msp)
    cpu.reg_write(UC_ARM_REG_PSP, 0x20020000)
    cpu.reg_write(UC_ARM_REG_CONTROL, 2)
    cpu.reg_write(UC_ARM_REG_LR, 0xFFFFFFFF)
    state = {
        "reset_requested": False,
        "softdevice_disable_calls": 0,
        "gpregret": None,
    }

    def instruction_hook(machine, address, size, _):
        instruction = next(
            decoder.disasm(bytes(machine.mem_read(address, size)), address)
        )
        if instruction.mnemonic == "svc":
            if instruction.operands[0].imm != 0x11:
                raise ValueError("Unexpected SVC in OTA reset")
            state["softdevice_disable_calls"] += 1
            machine.reg_write(UC_ARM_REG_R0, 0)
            machine.reg_write(UC_ARM_REG_PC, (address + size) | 1)

    def write_hook(machine, _access, address, _size, value, _):
        if address == GPREGRET:
            state["gpregret"] = value
        if address == AIRCR and value & 4 and value >> 16 == 0x05FA:
            state["reset_requested"] = True
            machine.emu_stop()

    cpu.hook_add(UC_HOOK_CODE, instruction_hook)
    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    cpu.emu_start(entry | 1, 0, count=200)
    if not state["reset_requested"] or state["gpregret"] != expected_magic:
        raise ValueError(
            "OTA reset did not request the BLE bootloader with GPREGRET=0xA8"
        )
    if state["softdevice_disable_calls"] != 1:
        raise ValueError("OTA reset must disable the SoftDevice exactly once")
    if (
        cpu.reg_read(UC_ARM_REG_CONTROL) != 2
        or cpu.reg_read(UC_ARM_REG_MSP) != initial_msp
    ):
        raise ValueError("OTA reset switched away from the FreeRTOS task stack")
    return {
        "method": "compiled-cortex-m4-emulation",
        "reset_requested": True,
        "gpregret": hex(expected_magic),
        "task_stack_preserved": True,
        "softdevice_disable_stubbed": True,
        "hardware_tested": False,
    }


def validate_dfu(path):
    with Path(path).open("rb") as stream:
        elf = ELFFile(stream)
        if elf.header["e_machine"] != "EM_ARM":
            raise ValueError("DFU validation requires an ARM ELF")
        symbols = list(elf.get_section_by_name(".symtab").iter_symbols())
        functions = {
            symbol.name: symbol
            for symbol in symbols
            if symbol["st_info"]["type"] == "STT_FUNC" and symbol["st_size"]
        }
        decoder = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
        decoder.detail = True

        def function(name):
            matches = [
                s for n, s in functions.items() if n == name or n.startswith(name + ".")
            ]
            if len(matches) != 1:
                raise ValueError(f"Expected one compiled DFU function: {name}")
            return matches[0]

        def instructions(symbol):
            start = symbol["st_value"] & ~1
            section = elf.get_section(symbol["st_shndx"])
            offset = start - section["sh_addr"]
            return list(
                decoder.disasm(
                    section.data()[offset : offset + symbol["st_size"]], start
                )
            )

        def targets(symbol):
            return {
                instruction.operands[0].imm & ~1
                for instruction in instructions(symbol)
                if instruction.mnemonic in ("b", "b.w", "bl")
                and instruction.operands
                and instruction.operands[0].type == ARM_OP_IMM
            }

        callback = function("legionDfuControlWrite")
        entry = function("enterOTADfu")
        install = function("legionDfuInstall")
        process = function("legionDfuProcess")
        begins = [s for n, s in functions.items() if "QuiescingBLEDfu5begin" in n]
        if len(begins) != 1 or install["st_value"] & ~1 not in targets(begins[0]):
            raise ValueError(
                "Active BLE DFU service does not install the immediate callback"
            )
        # LTO inlines nrf52Loop into Arduino's C-linkage loop in this pinned build.
        loop = function("loop")
        if process["st_value"] & ~1 not in targets(loop):
            raise ValueError("Main loop does not service the deferred DFU handoff")
        if entry["st_value"] & ~1 not in targets(process):
            raise ValueError(
                "Deferred DFU handoff does not reach the safe OTA reset entry"
            )
        if {entry["st_value"] & ~1, process["st_value"] & ~1} & targets(callback):
            raise ValueError("Immediate authorization must not run the reset handoff")
        if any(
            i.mnemonic == "msr" and i.op_str.startswith(("control", "msp"))
            for i in instructions(callback)
        ):
            raise ValueError("The C callback must not switch the active stack")

        segments = [
            (segment["p_vaddr"], segment.data())
            for segment in elf.iter_segments()
            if segment["p_type"] == "PT_LOAD" and segment["p_filesz"]
        ]
        result = emulate_reset_entry(segments, entry["st_value"])
        result.update(
            emulate_registration(
                segments,
                install["st_value"],
                callback["st_value"],
                handler=function("_ZN17BLECharacteristic13_eventHandlerEP9ble_evt_t")[
                    "st_value"
                ],
                notify=function("_ZN17BLECharacteristic13notifyEnabledEt")["st_value"],
                ada=function("ada_callback_invoke")["st_value"],
            )
        )
        result["callback_routes_to_ota_reset"] = True
        result["main_loop_handoff"] = True
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("elf", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(validate_dfu(arguments.elf), indent=2))
