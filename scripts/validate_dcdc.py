#!/usr/bin/env python3
"""Inspect the compiled REG1 API, enable argument and Bluetooth startup call."""

from pathlib import Path

from capstone import CS_ARCH_ARM, CS_MODE_MCLASS, CS_MODE_THUMB, Cs
from capstone.arm import ARM_REG_R0
from elftools.elf.elffile import ELFFile


def validate_dcdc(path):
    with Path(path).open("rb") as stream:
        image = ELFFile(stream)
        symbols = list(image.get_section_by_name(".symtab").iter_symbols())
        functions = [
            s
            for s in symbols
            if s["st_info"]["type"] == "STT_FUNC"
            and isinstance(s["st_shndx"], int)
            and s["st_size"]
        ]
        decoder = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
        decoder.detail = True

        def instructions(symbol):
            section = image.get_section(symbol["st_shndx"])
            address = symbol["st_value"] & ~1
            end = address + symbol["st_size"]
            mappings = sorted(
                (s["st_value"], s.name[:2])
                for s in symbols
                if s["st_shndx"] == symbol["st_shndx"]
                and s.name.startswith(("$t", "$d"))
            )
            boundaries = sorted(
                {address, end} | {a for a, _ in mappings if address < a < end}
            )
            result = []
            for begin, stop in zip(boundaries, boundaries[1:]):
                kind = next((k for a, k in reversed(mappings) if a <= begin), "$t")
                if kind == "$t":
                    start = begin - section["sh_addr"]
                    result.extend(
                        decoder.disasm(
                            section.data()[start : start + stop - begin], begin
                        )
                    )
            return result

        wrappers = [s for s in functions if s.name == "sd_power_dcdc_mode_set"]
        if not wrappers or not all(
            any(i.mnemonic == "svc" and i.op_str == "#0x3f" for i in instructions(s))
            for s in wrappers
        ):
            raise ValueError("Missing or incorrect compiled REG1 S140 API")
        addresses = {s["st_value"] & ~1 for s in wrappers}
        enables = [s for s in functions if s.name == "legionEnableDcdcReg1"]
        if len(enables) != 1:
            raise ValueError("Missing compiled Legion REG1 enable function")
        code = instructions(enables[0])
        calls = [
            i
            for i, instruction in enumerate(code)
            if instruction.mnemonic == "bl"
            and int(instruction.op_str.lstrip("#"), 0) in addresses
        ]
        if len(calls) != 1:
            raise ValueError("REG1 must have one compiled API call site")
        index = calls[0]
        argument_one = bool(
            index
            and code[index - 1].mnemonic.startswith("mov")
            and code[index - 1].op_str == "r0, #1"
        )
        # GCC can reuse the enabled status byte on the r0 == 1 branch.
        for guard_index, guard in enumerate(code):
            if guard.mnemonic not in ("beq", "beq.w") or not guard_index:
                continue
            if (
                code[guard_index - 1].mnemonic != "cmp"
                or code[guard_index - 1].op_str != "r0, #1"
            ):
                continue
            target = int(guard.op_str.lstrip("#"), 0)
            block = [i for i in code if target <= i.address < code[index].address]
            if target == code[index].address:
                argument_one = True
            elif (
                block
                and block[0].address == target
                and block[-1].address + block[-1].size == code[index].address
            ):
                if all(
                    ARM_REG_R0 not in i.regs_access()[1]
                    and not i.mnemonic.startswith("b")
                    for i in block
                ):
                    argument_one = True
        if not argument_one:
            raise ValueError("Compiled REG1 enable argument is not proven to be 1")
        setup = [s for s in functions if "NRF52Bluetooth5setup" in s.name]
        entry = enables[0]["st_value"] & ~1
        if not any(
            i.mnemonic == "bl" and int(i.op_str.lstrip("#"), 0) == entry
            for s in setup
            for i in instructions(s)
        ):
            raise ValueError(
                "Bluetooth setup does not call the compiled REG1 initializer"
            )
        return {
            "method": "compiled-arm-call-inspection",
            "reg1_svc": "0x3f",
            "enable_argument": 1,
            "bluetooth_setup_calls_enable": True,
            "hardware_tested": False,
        }
