# Legion 0.6.0-alpha.1

**Experimental alpha for the RAK3401 1W with RAK13302. Physical validation of
this combined build is pending.** Published as a GitHub prerelease; it is not a
stable recommendation. Previous release assets remain available for rollback.

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
  selection is not implemented. See [APC.md](APC.md).
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

Use an accessible node and the UF2 for the first alpha installation. Preserve
its configuration and the previous release for rollback. The OTA ZIP is supplied
for the subsequent controlled BLE update test; its availability does not mean
physical end-to-end OTA has been verified on this base. Do not factory-reset
or erase the node as part of an ordinary update.

## Validation and next steps

Software checks cover both firmware profiles, exact patch preparation, Python
release/checkout tests, real-source host regression tests with ASan/UBSan,
compiled Cortex-M4 DFU reset/authorization checks, compiled DC/DC activation,
and matching application-only ELF/OTA/UF2 images. APC simulations cover invalid
or stale voltage evidence, USB bypass, hysteresis, budgets, exemptions,
configuration disarming, 32-bit rollover and 50 days of uptime.

**Hardware/RF validation is pending for this alpha:** command reachability,
traceroutes, real CC310 execution, boot/reset evidence, backup freshness and
restoration, DFU/OTA, migrated-base radio behavior and APC OBSERVE/SHADOW/ON.
Earlier hardware observations on 0.4.x/0.5.x do not validate this combined build.
No measured energy saving, battery-life gain or reduced-power RF reachability
is claimed. Begin with APC OFF, collect a migrated-base reference in OBSERVE,
then test SHADOW before enabling ON with known peers.

Read [COMMANDS.md](COMMANDS.md), [RECOVERY.md](RECOVERY.md), [APC.md](APC.md)
and the [alpha hardware test sequence](ALPHA-TESTING.md).
