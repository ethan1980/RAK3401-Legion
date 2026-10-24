# Legion 0.6.0-alpha.1

**Experimental alpha for the RAK3401 1W with RAK13302.** Hardware validation is
partial; this is not a stable release. Previous downloads remain available.

Published firmware build: [`979d23a`](https://github.com/ethan1980/RAK3401-Legion/commit/979d23ab6d88d540052342627b430275a6f45004).
Documentation updates do not replace its firmware assets.

## New in this release

- **Meshtastic base:** 2.8.2 develop at `e039e34171e697e36d4f1b66eedfb683ffffe4f5`,
  including the upstream BLE OTA reset fix.
- **APC — Adaptive Power Control:** `/apc observe|shadow|on|off|status !nodeid`.
  S1 adapts optional position/telemetry relay budgets to battery conditions.
  Protected traffic and reception are preserved; RF output remains nominal.
  Modes are RAM-only and every boot starts **OFF**.
- **Remote traceroute:** `/trace !nodeid !targetid` returns outbound and return
  paths asynchronously, with distinct routing-error and timeout replies.
- **CC310 hashing:** packet SHA-256 and ACK-proof HMAC-SHA256 acceleration,
  retaining compatible digests and software fallback.
- **Boot diagnostics:** `/boot !nodeid` reports reset evidence, first boot
  voltages and CC310 counters without flash writes.
- **Backup freshness:** read-only `/backup status !nodeid` identifies outdated
  saved settings. Replacement remains explicit and the rescue format is unchanged.

Existing remote tools, private telemetry, manual rescue, REG1 DC/DC, 8 MHz bulk
SPI, verified preference writes and energy recovery remain included.
The node reports **`2.8.2.LGN0.6.0a1`**.

## Download and use

- **USB:** `firmware-rak3401-legion-2.8.2.e039e34.uf2`.
- **BLE OTA:** `firmware-rak3401-legion-2.8.2.e039e34-ota.zip`.

Both packages contain the application only. They preserve the **0xE8000–0xEA000**
rescue reserve and do not update the bootloader or SoftDevice. Source, debug
files, build metadata and `SHA256SUMS` are included with the release.

OTA installation using **nRF Connect** is confirmed. The Meshtastic apps' updater
and a subsequent update initiated from the running alpha are not yet validated.
Ordinary updates do not require an erase or factory reset.

## Validation status

Core messaging/remote tools, telemetry, direct/relayed traceroute and normal
restart operation have been observed on alpha hardware. Boot diagnostics, CC310
use, backup freshness and APC OBSERVE are partially validated. **SHADOW/ON and
extended hardware validation remain pending.** Energy savings are unmeasured.

[Commands](https://github.com/ethan1980/RAK3401-Legion/blob/main/COMMANDS.md) · [Rescue backup](https://github.com/ethan1980/RAK3401-Legion/blob/main/RECOVERY.md) · [Energy recovery](https://github.com/ethan1980/RAK3401-Legion/blob/main/ENERGY-RECOVERY.md) · [APC](https://github.com/ethan1980/RAK3401-Legion/blob/main/APC.md) · [Changelog](https://github.com/ethan1980/RAK3401-Legion/blob/main/CHANGELOG.md)
