# Legion 0.6.0-alpha.1

**Experimental alpha for the RAK3401 1W with RAK13302. Initial hardware checks
pass; extended validation is in progress.** Published as a GitHub prerelease; it is not a
stable recommendation. Previous release assets remain available for rollback.

Published firmware build: [`979d23ab6d88d540052342627b430275a6f45004`](https://github.com/ethan1980/RAK3401-Legion/commit/979d23ab6d88d540052342627b430275a6f45004).
The release assets and their build-time validation metadata belong to that build.
The hardware observations below were recorded after publication.

## Included in this alpha

- **New Meshtastic base:** 2.8.2 develop at
  `e039e34171e697e36d4f1b66eedfb683ffffe4f5`, replacing `04cb888`.
  This is a pinned source revision, not an official nightly binary. The selected
  revision adds the BLE OTA reset fix to the reviewed `0d3da2d` candidate.
  Legion retains direct ATT write authorization and its main-loop DFU handoff;
  the reference profile retains the upstream DFU implementation.
- **APC S1:** `/apc observe|shadow|on|off|status !legionid`, with six manually
  requested status pages. Battery-voltage filtering, fresh evidence,
  hysteresis and persistence govern optional position/telemetry relay budgets.
  Protected traffic, reception and nominal RF output are preserved.
  **Every boot starts OFF**, with RAM-only state. SHADOW models decisions while
  forwarding normally; ON applies the optional budget. Adaptive RF-power
  selection is not implemented. See [APC.md](https://github.com/ethan1980/RAK3401-Legion/blob/main/APC.md).
- **Remote traceroute:** `/trace !legionid !targetid` originates a standard
  Meshtastic traceroute and reports its outbound and return paths asynchronously.
- **CC310 hashing:** packet SHA-256 and ACK-proof HMAC-SHA256 use the nRF52840
  accelerator, with serialized SDK access, aligned input and software fallback.
- **Boot diagnostics:** `/boot !legionid` reports cached reset evidence, the
  previous recorded protective stop, first boot voltages and CC310 counters.
  It adds no flash writes or automatic reports.
- **Backup freshness:** `/backup status !legionid` distinguishes matching,
  OUTDATED and unavailable comparisons, naming changed blocks without exposing
  keys or values. An outdated valid rescue point remains armed. Replacement
  stays explicit; the rescue flash format is preserved.
- Command cooldowns and APC captures expire during normal polling. Completed
  APC warmup remains completed across long uptime and clock rollover.
- Existing remote commands, private telemetry, REG1 DC/DC, 8 MHz bulk SPI,
  manual rescue, verified preference writes and low-battery confirmation remain
  included. Battery sleep still requires eight readings below 3.50 V at
  20-second intervals; separate VDD, TX, flash and boot protections remain.

## Identification and packages

The full release version is **0.6.0-alpha.1**. The existing 17-character firmware
field uses **`2.8.2.LGN0.6.0a1`** in device metadata, MQTT, BLE and telemetry.
`LGN` means Legion and `a1` means alpha 1. The build profile and manifest retain
the full version. Firmware filenames use the upstream base `2.8.2.e039e34`.

- **USB:** `firmware-rak3401-legion-2.8.2.e039e34.uf2`.
- **BLE OTA:** `firmware-rak3401-legion-2.8.2.e039e34-ota.zip`.
- The OTA ZIP and UF2 contain the application only. No bootloader or SoftDevice
  update is included. Packaging checks that both match the ELF and stay below
  the `0xE8000–0xEA000` rescue reserve.
- Corresponding source, ELF/debug files, `legion-build.json` and SHA256SUMS are
  attached. Baseline comparison builds are available in GitHub Actions.

The operator confirms successful OTA installation and startup of this alpha
using **nRF Connect**. The exact client version/platform and previous firmware
version have not been recorded. This exercises the previously installed
firmware's update-entry path; a subsequent
update started from the running alpha remains pending to validate its own DFU
entry. On another accessible test node, USB UF2 remains an initial installation
option. Preserve configuration and the previous release for rollback; ordinary
updates do not require factory reset or erase.

## Validation and next steps

Software checks cover both firmware profiles, exact patch preparation, Python
release/checkout tests, real-source host regression tests with ASan/UBSan,
compiled Cortex-M4 DFU reset/authorization checks, compiled DC/DC activation,
and matching application-only ELF/OTA/UF2 images. APC simulations cover invalid
or stale voltage evidence, USB bypass, hysteresis, budgets, exemptions,
configuration disarming, 32-bit rollover and 50 days of uptime.

### Hardware observations — 2026-10-24

- Operator confirms OTA installation using nRF Connect, normal sending/receiving
  of ordinary channel and private messages, and successful remote `/msg` operation.
- Screenshots confirm firmware identity, private telemetry, `/boot`, initial
  APC OFF with nominal RF and an empty ignore list.
- A fresh `/zerohop` capture lists three neighbors, including positive and
  negative SNR. The earlier empty result was the same 15-minute frozen capture;
  the directory populated after capture renewal.
- `/trace` returns both outbound and return reports for a direct peer and a
  relayed peer. The relayed example reports two outbound intermediates and one
  return intermediate on a different path. A separate trace expires after
  90 seconds with `reachability unknown`, without claiming an unreachable target.
- CC310 counts advance from `SHA:3 MAC:3 SW:0` to `SHA:4 MAC:19 SW:0` during
  normal use. A deliberate `/reboot` acknowledges its scheduled normal restart;
  the new boot reports software reset, fresh first-voltage samples and
  `SHA:3 MAC:2 SW:0`. No software fallback is observed in these captures.
- Post-restart `/boot` and `/apc status` replies remain available; APC reports
  OFF and nominal RF. Exact reboot latency and every retained setting were not
  independently measured.
- Backup status changes from `up to date` to `OUTDATED: owner` and back to
  `up to date`, with the valid rescue point armed throughout. This demonstrates
  the owner-freshness case, not backup replacement or restoration.
- Operator reports OBSERVE activated for the migrated-base reference. The first
  six-page capture and continuous 24-hour results are awaited.

**Remaining hardware/RF validation:** explicit routing `NO_ROUTE`, other-command
responsiveness during a trace wait, ignore/unignore
mutations, protective/other reset cases, other backup-freshness blocks and rescue
operations, DFU entry from the running alpha, APC OBSERVE/SHADOW/ON and long-term
radio/energy behavior. Initial OTA with nRF Connect does not establish the
Meshtastic apps' updater path or a subsequent update from the running alpha.
Earlier 0.4.x/0.5.x hardware observations remain separate from these alpha results.

No measured energy saving, battery-life gain or reduced-power RF reachability
is claimed. The 24-hour migrated-base reference in passive OBSERVE is in progress.
Then collect 24 hours in SHADOW before a supervised 30–60-minute ON trial with known
peers. Review each stage before proceeding; no further OTA is needed to change
APC modes. Keep disruptive tests outside the continuous observation runs.

Read [COMMANDS.md](https://github.com/ethan1980/RAK3401-Legion/blob/main/COMMANDS.md), [RECOVERY.md](https://github.com/ethan1980/RAK3401-Legion/blob/main/RECOVERY.md), [APC.md](https://github.com/ethan1980/RAK3401-Legion/blob/main/APC.md)
and the [alpha hardware test sequence](https://github.com/ethan1980/RAK3401-Legion/blob/main/ALPHA-TESTING.md).
