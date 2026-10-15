#!/usr/bin/env python3
"""Check the active BLE callback and emulate the compiled OTA reset entry.

The old callback switched from the FreeRTOS PSP to MSP before a C epilogue
read beyond RAM. Publishing requires the Legion callback to reach enterOTADfu,
and that entry to request a hardware reset with GPREGRET=0xA8 on the same PSP.
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
    UC_ARM_REG_XPSR,
)

RAM_START, RAM_END = 0x20000000, 0x20040000
GPREGRET, AIRCR = 0x4000051C, 0xE000ED0C


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
        wrappers = [
            s for n, s in functions.items() if "QuiescingBLEDfu14onControlWrite" in n
        ]
        if len(wrappers) != 1 or targets(wrappers[0]) != {callback["st_value"] & ~1}:
            raise ValueError(
                "BLE DFU is not exclusively routed through the Legion callback"
            )
        if entry["st_value"] & ~1 not in targets(callback):
            raise ValueError("Legion callback does not call the safe OTA reset entry")
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
        result["callback_routes_to_ota_reset"] = True
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("elf", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(validate_dfu(arguments.elf), indent=2))
