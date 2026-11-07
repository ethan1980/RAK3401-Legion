# Legion 0.6.6 — emergency release

Legion 0.6.6 uses the same Meshtastic v2.8.2.d5f1619 base as 0.6.5 and reports
`2.8.2.Legion0.6.6`.

- **Ignore by name.** Save an exact long-name rule with
  `/ignore name !nodeid "Long name"`. Use `/unignorename !nodeid "Long name"`
  to remove it and `/ignorelist names !nodeid [page]` to review the list.
  Rules survive restarts and match new NodeIDs as they announce the same name.
- **Scramble.** Send `/scramble !nodeid` on LegionRF. The selected node silences
  LoRa, Bluetooth and USB data for 60 minutes, then restarts. It sends no reply
  and requires no additional authorization.

[Commands](COMMANDS.md) · [Manual en español](docs/Legion-Spanish-friendly-user-manual.pdf) ·
[English manual](docs/Legion-English-friendly-user-manual.pdf)

---

# Legion 0.6.5 — stable release

Pinned upstream: `v2.8.2.d5f1619`, full commit
`d5f16191ca28b01b5024f590f04a67f25d66f1b1`. Advertised version:
`2.8.2.Legion0.6.5`. The previous 4c89b69 candidate is discarded.

Includes APC S1+S2 and primary-channel broadcast-text antispam. APC starts OFF;
antispam starts OBSERVE. Use `/guard status !nodeid` to query it, `/guard on !nodeid`
to enforce blocking and `/spamlist !nodeid [page]` to inspect quarantines. The
existing 24-hour DAILY report now includes antispam mode and active or simulated
quarantine count. Scramble is reserved for 0.7.0.

The 0.6.5 OTA candidate was installed and its new control commands checked
on RAK3401 hardware. The final action-first `/guard` parser was subsequently
validated in software. S2 RF output, range and energy savings remain unmeasured.
Read [Commands](COMMANDS.md), [APC](APC.md), [Antispam](ANTISPAM.md).

---

# Legion 0.6.1

**Stable release for the RAK3401 1W with RAK13302.** Previous downloads remain available.

The node reports **`2.8.2.Legion0.6.1`**. The release assets include the exact
upstream and Legion build commits in `legion-build.json`.

## New in this release

- **Meshtastic base:** 2.8.2 develop at `c39728e3fb9304fc3b1160ebf14801b3b5f0a213`,
  including the upstream Mesh Beacon channel handling fixes.
- **Individual ignore commands:** `/ignore !nodeid !peerid`,
  `/unignore !nodeid !peerid` and `/ignorelist !nodeid [page]`. Only the selected
  Legion acts; existing ignore entries are preserved.
- **Remote channels:** `/createch !nodeid name psk` creates a secondary channel
  in the first available slot using a Base64 PSK; `/deletech !nodeid name` clears
  a secondary channel without renumbering the others. Primary and LegionRF are
  protected. A successful change sets APC OFF and leaves backup replacement explicit.
- **Component diagnostics:** `/components !nodeid` reports CC310 counters,
  configured radio SPI, bulk transfers and REG1 DC/DC. `/boot` retains reset
  evidence and first boot voltages.
- **Daily reminder:** a brief APC/backup summary on private LegionRF every
  24 hours from boot, with no accumulated backlog or automatic backup replacement.
- **APC — Adaptive Power Control:** `/apc observe|shadow|on|off|status !nodeid`.
  S1 adapts optional position/telemetry relay budgets to battery conditions.
  Protected traffic and reception are preserved; RF output remains nominal.
  Modes are RAM-only and every boot starts **OFF**.
- **Remote traceroute:** `/trace !nodeid !targetid` returns outbound and return
  paths asynchronously, with distinct routing-error and timeout replies.
- **CC310 hashing:** packet SHA-256 and ACK-proof HMAC-SHA256 acceleration,
  retaining compatible digests and software fallback.
- **Boot diagnostics:** `/boot !nodeid` reports reset evidence and first boot
  voltages without flash writes.
- **Backup freshness:** read-only `/backup status !nodeid` identifies outdated
  saved settings. Replacement remains explicit and the rescue format is unchanged.

Existing remote tools, private telemetry, manual rescue, REG1 DC/DC, 8 MHz bulk
SPI, verified preference writes and energy recovery remain included.

## Download and use

- **USB:** `firmware-rak3401-legion-2.8.2.c39728e.uf2`.
- **BLE OTA:** `firmware-rak3401-legion-2.8.2.c39728e-ota.zip`.

Both packages contain the application only. They preserve the **0xE8000–0xEA000**
rescue reserve and do not update the bootloader or SoftDevice. Source, debug
files, build metadata and `SHA256SUMS` are included with the release.

OTA installation from the previous alpha has been confirmed.
Ordinary updates do not require an erase or factory reset.

## Validation status

Command operation, including components and channel creation/deletion, has been
confirmed on hardware. APC OBSERVE, SHADOW and ON have been tested, including
CONSERVE and RESERVE operation with normal channel and private communications.
Energy savings are unmeasured.

[Commands](https://github.com/ethan1980/RAK3401-Legion/blob/main/COMMANDS.md) · [Rescue backup](https://github.com/ethan1980/RAK3401-Legion/blob/main/RECOVERY.md) · [Energy recovery](https://github.com/ethan1980/RAK3401-Legion/blob/main/ENERGY-RECOVERY.md) · [APC](https://github.com/ethan1980/RAK3401-Legion/blob/main/APC.md) · [Changelog](https://github.com/ethan1980/RAK3401-Legion/blob/main/CHANGELOG.md)
