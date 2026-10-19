Experimental firmware for the **RAK3401 1W with RAK13302**.

- Legion version: **0.5.0**
- Meshtastic base: **2.8.2**, commit `04cb8885118b959a9f538cd5881bd7d595758911`
- Advertised firmware: **`2.8.2.Legion0.5.0`** in MQTT, device metadata and Bluetooth; **`Legion0.5.0`** in telemetry.
- Complete source commits and package checksums are recorded in `legion-build.json` and `SHA256SUMS`.

| New command | Behavior |
| --- | --- |
| `/msg !nodeid <channel> <message>` | Originate text from the selected Legion on an enabled channel; confirm queue acceptance. |
| `/reboot !nodeid` | Schedule a normal restart 20 seconds after acceptance. |
| `/zerohop !nodeid [page]` | Report direct RF nodes with full IDs, short names and SNR. |
| `/ignore !peerid` | Every receiving Legion independently ignores the peer. |
| `/unignore !peerid` | Every receiving Legion independently unignores the peer. |
| `/ignorelist [page]` | Each receiving Legion reports its effective ignore list. |

Commands use the existing private LegionRF channel. Directory snapshots preserve
page order for 15 minutes and return one page per request. New commands have a
separate five-second cooldown and bounded duplicate suppression. Ignore changes
use the normal persistent NodeDB and legacy LoRa state; pending writes are
identified explicitly. Queue acceptance does not confirm RF reception.

**REG1 DC/DC** is enabled automatically through the SoftDevice API after successful
initialization. Activation was verified on the diagnostic RAK with USB power and
after a battery-powered restart. REG0 and UICR retain their existing configuration.
Whole-node current reduction and battery-life improvement have not been measured.

The release retains 8 MHz bulk SPI, energy recovery, verified preference writes,
private telemetry and manual rescue backup. Telemetry and all backup commands
were verified on 0.4.2 hardware. The new commands have automated coverage; their
hardware validation, automatic emergency restoration, recovery announcement and
physical power-cut testing remain pending.

Both firmware profiles compile successfully. Automated checks cover targeting,
channel changes, queue results, SNR provenance, pagination, ignore persistence,
REG1 API use, recovery and package integrity.

See [README](https://github.com/ethan1980/RAK3401-Legion/blob/main/README.md),
[commands](https://github.com/ethan1980/RAK3401-Legion/blob/main/COMMANDS.md) and
[manual rescue backup](https://github.com/ethan1980/RAK3401-Legion/blob/main/RECOVERY.md).

Downloads include firmware packages, corresponding source, build metadata,
debug files and `SHA256SUMS`.
