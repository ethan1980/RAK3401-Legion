Experimental firmware for the **RAK3401 1W with RAK13302**.

- Legion version: **0.4.2**
- Meshtastic base: **2.8.2**, commit `04cb8885118b959a9f538cd5881bd7d595758911`
- Firmware build commit: `aee6ab852a864ab66082eb675a8bc3941b01b6f6`
- Advertised version: **`2.8.2.Legion0.4.2`** in MQTT, device metadata and Bluetooth; **`Legion0.4.2`** in telemetry.

This maintenance release fixes BLE OTA entry and preserves 8 MHz bulk SPI,
energy recovery, verified preference writes, private telemetry and manual rescue backup.

**BLE OTA operation is verified using nRF Connect.** Use the release's
`firmware-rak3401-legion-2.8.2.04cb888-ota.zip` for BLE updates.
Migration from older Legion releases uses
`firmware-rak3401-legion-2.8.2.04cb888.uf2` over USB.
No bootloader or SoftDevice update is included.

| Hardware validation | Status |
| --- | --- |
| BLE OTA using nRF Connect | Verified. |
| `/telemetry`, current version and min/max formatting | Verified. |
| `/backup !xxxxxxxx` and success confirmation | Verified. |
| `/backup status !xxxxxxxx` | Verified. |
| `/backup delete !xxxxxxxx` | Verified. |
| Backup replacement | Pending. |
| Emergency restoration from a saved backup and recovery announcement | Pending. |
| Recovery during physical power loss | Pending. |

Backup creation is manual and requires the full target Node ID on the private
**LegionRF** channel. No automatic snapshot is created. A valid rescue point can
restore essential settings after preference loss. With a rescue point armed,
factory reset schedules restoration; deleting the rescue point first allows a
return to blank settings. Backup replies never contain private keys.

Automated checks cover the power policy, persistence, telemetry transport,
recovery engine and journal, DFU entry and application boundaries. Both firmware
profiles compile successfully. Controlled measurements of voltage thresholds,
sleep current, battery savings and long-term radio stability remain pending.

See the [README](https://github.com/ethan1980/RAK3401-Legion/blob/main/README.md),
[commands](https://github.com/ethan1980/RAK3401-Legion/blob/main/COMMANDS.md),
[backup and recovery](https://github.com/ethan1980/RAK3401-Legion/blob/main/RECOVERY.md),
and [installation instructions](https://github.com/ethan1980/RAK3401-Legion/blob/main/DFU.md).

Downloads include UF2, OTA ZIP, corresponding source, build metadata, debug files
and `SHA256SUMS`. Superseded download releases are withdrawn; source tags and Git
history remain available. This documentation update retains the existing firmware
build and download assets.
