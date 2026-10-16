#!/usr/bin/env python3
"""Check that ELF, application-only DFU and UF2 agree and avoid rescue storage."""

import binascii
import json
import struct
import zipfile
from pathlib import Path

from elftools.elf.elffile import ELFFile

APP_START = 0x26000
RESCUE_START = 0xE8000
RESCUE_END = 0xEA000
UF2_FAMILY = 0xADA52840


def validate_update(elf_path, ota_path, uf2_path):
    with zipfile.ZipFile(ota_path) as archive:
        if archive.testzip():
            raise ValueError("Corrupt OTA ZIP")
        manifest = json.loads(archive.read("manifest.json"))["manifest"]
        if set(manifest) != {"application", "dfu_version"}:
            raise ValueError("OTA must contain only an application update")
        app = manifest["application"]
        binary = archive.read(app["bin_file"])
        init = archive.read(app["dat_file"])
        if not binary or len(binary) % 4 or APP_START + len(binary) > RESCUE_START:
            raise ValueError("OTA image overlaps the recovery reserve")
        if len(init) < 12:
            raise ValueError("Invalid DFU init packet")
        device, revision, version, count = struct.unpack_from("<HHIH", init)
        if len(init) != 12 + 2 * count:
            raise ValueError("Invalid DFU init packet length")
        softdevices = list(struct.unpack_from(f"<{count}H", init, 10))
        crc = struct.unpack_from("<H", init, len(init) - 2)[0]
        if device != 82 or revision != 65535 or softdevices != [0xB6]:
            raise ValueError("OTA targets a different device or SoftDevice")
        if crc != binascii.crc_hqx(binary, 0xFFFF):
            raise ValueError("OTA application CRC mismatch")
        metadata = app["init_packet_data"]
        if (metadata["firmware_crc16"], metadata["application_version"]) != (
            crc,
            version,
        ):
            raise ValueError("OTA metadata differs from init packet")

    flash_end = APP_START
    with open(elf_path, "rb") as source:
        elf = ELFFile(source)
        symbols = elf.get_section_by_name(".symtab")
        marker = symbols.get_symbol_by_name("__legion_recovery")
        if not marker or marker[0]["st_value"] != 1:
            raise ValueError("ELF lacks the recovery linker boundary")
        for segment in elf.iter_segments():
            address = segment["p_paddr"]
            if (
                segment["p_type"] != "PT_LOAD"
                or not segment["p_filesz"]
                or address >= 0x20000000
            ):
                continue
            end = address + segment["p_filesz"]
            if address < APP_START or end > RESCUE_START:
                raise ValueError("ELF overlaps protected flash")
            data = segment.data()
            if binary[address - APP_START : end - APP_START] != data:
                raise ValueError("OTA image differs from compiled ELF")
            flash_end = max(flash_end, end)

    uf2 = Path(uf2_path).read_bytes()
    if not uf2 or len(uf2) % 512:
        raise ValueError("Invalid UF2 length")
    addresses = set()
    numbers = set()
    block_count = len(uf2) // 512
    for offset in range(0, len(uf2), 512):
        block = uf2[offset : offset + 512]
        magic0, magic1, flags, address, size, number, count, family = (
            struct.unpack_from("<8I", block)
        )
        if (magic0, magic1, struct.unpack_from("<I", block, 508)[0]) != (
            0x0A324655,
            0x9E5D5157,
            0x0AB16F30,
        ):
            raise ValueError("Invalid UF2 magic")
        if flags != 0x2000 or family != UF2_FAMILY or size != 256 or address % 256:
            raise ValueError("Invalid UF2 family, flags or payload")
        if address < APP_START or address + size > RESCUE_START:
            raise ValueError("UF2 overlaps the recovery reserve")
        if (
            count != block_count
            or number >= count
            or number in numbers
            or address in addresses
        ):
            raise ValueError("Duplicate or inconsistent UF2 blocks")
        numbers.add(number)
        addresses.add(address)
        expected = binary[address - APP_START : address - APP_START + size].ljust(
            size, b"\0"
        )
        if block[32 : 32 + size] != expected:
            raise ValueError("UF2 payload differs from OTA")
    expected_addresses = set(range(APP_START, APP_START + len(binary), 256))
    if addresses != expected_addresses:
        raise ValueError("UF2 does not cover the complete application")
    return {
        "application_only": True,
        "elf_ota_uf2_match": True,
        "reserve_start": hex(RESCUE_START),
        "reserve_end": hex(RESCUE_END),
        "image_end": hex(flash_end),
        "image_margin_bytes": RESCUE_START - flash_end,
        "ota_crc16": crc,
        "hardware_tested": False,
    }
