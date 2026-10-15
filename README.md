<p align="center">
  <img src="assets/rak3401-legion-logo.png" alt="RAK3401 Legion - Unleash your demons" width="900">
</p>

# RAK3401 Legion

Experimental Meshtastic firmware for the **RAK3401 1W with RAK13302**.
Current version: **Legion 0.3.0**, based on **Meshtastic 2.8.2 develop/nightly**,
commit [`04cb888`](https://github.com/meshtastic/firmware/commit/04cb8885118b959a9f538cd5881bd7d595758911).
This pins a specific 2.8.2 source revision, not a published official nightly binary.

This repository contains a small set of patches and a build profile. The build
downloads the upstream source pinned in `upstream.json`, applies the changes,
and produces the complete firmware. This keeps Legion changes easy to review
and port to newer Meshtastic versions.

## Included changes

Legion transfers RadioLib buffers to the SX1262 in blocks through the nRF52
core's synchronous SPI API, which uses EasyDMA. The baseline transfers these
buffers one byte at a time. Legion 0.3.0 runs radio SPI at **8 MHz** for both reads
and writes; the unchanged baseline remains at **4 MHz**. The existing
bus locking and transaction boundaries are preserved. This optimization is enabled
only in `rak3401-legion`.

The goal is to reduce transfer time and CPU overhead. **Battery savings and
8 MHz hardware stability have not been measured yet.** Initial user testing of
0.2.0 reported normal operation; it does not validate the new clock or commands.
During continuous reception,
the RF front end will still account for a significant share of total power use.

The selected upstream revision's AGC and radio recovery fixes are preserved.
The profile inherits the official pin assignments and RAK3401 hardware identity.
Normal operation retains the configured TX power, channels, role and Bluetooth.

### Private telemetry on demand

Create a **SECONDARY** channel named exactly **LegionRF**, with your own random
**16-byte or 32-byte private PSK**, using the Meshtastic app. Share that channel
with the nodes that will request or read reports. There is **no common key in
the firmware**: each user can use a different PSK without recompiling.
Receiving nodes must also have matching LoRa settings and encryption mode.

Send an ordinary channel text message:

- **`/telemetry`**: reachable Legion nodes on this private channel may reply.
- **`/telemetry !abcdef01`**: only the specified node may reply; replace the
  eight hexadecimal digits with its full node ID.

The report is a normal message in the same channel, also copied to the app
connected to the responding RAK. It includes current/maximum chip temperature,
physical battery voltage/minimum, estimated charge, mean/peak sampled noise,
packet counters and uptime. Values and counters are labeled in
[COMMANDS.md](COMMANDS.md).

There are **no automatic diagnostic broadcasts**. The monitor keeps small
accumulators in RAM and adds no diagnostic-history writes to flash. It reuses
upstream's noise readings on the current frequency; it does not sweep other
frequencies or interrupt reception to retune. Chip temperature is sampled every
60 seconds while the private channel is configured, and refreshed on a reply.

A random response delay, a 60-second per-node cooldown, duplicate suppression
and one pending response limit reduce bursts. Missing, disabled, ambiguous or
public-key channels do not enable the command, and there is no fallback to the
primary channel. A pending reply is canceled if its channel/key changes or
the power reserve is insufficient. The existing radio scheduler remains in use.

**The private channel shares the same radio frequency and airtime.** Query only
as needed. A sleeping node cannot receive a request. Full setup, command syntax,
field definitions, timing and troubleshooting: **[COMMANDS.md](COMMANDS.md)**.

### Energy recovery

This policy targets the **RAK3401 + battery-powered RAK13302 + RAK19007**, with
a single-cell Li-Ion/LiPo battery or parallel cells at the same pack voltage.
Four parallel 18650 cells are still one cell in voltage terms.

| Check | Default behavior |
| --- | --- |
| Boot reserve | Require VBAT >= 3.60 V and MCU VDD >= 3.00 V in four checks, 250 ms apart; repeat after enabling IO2. |
| Battery reserve | Enter energy sleep after three consecutive VBAT readings below 3.50 V, sampled every 5 s. |
| MCU brownout | Check VDD every second; enter energy sleep after six unsafe checks, with 2.90/3.00 V hysteresis. |
| TX protection | Measure the supply before CAD; allow TX only at VBAT >= 3.50 V and VDD >= 3.00 V. Recheck the cached decision before launch. |
| Hardware wake | LPCOMP on AIN3 with 11/16 VDD reference and hysteresis: about 3.78 V nominal before comparator hysteresis and component tolerances. |
| Recovery fallback | If LPCOMP is not ready or its input is already high, keep the radio off in System ON; require four healthy checks, 30 s apart, at VBAT >= 3.80 V and VDD >= 3.00 V before resetting. |

Early checks run before console, filesystem and Bluetooth initialization. A weak
battery returns to sleep before the main firmware loads. During an energy
shutdown, the radio receives its normal sleep notification before SPI closes;
IO2 and the radio power enable are then cut, and both user LEDs are turned off.
The TX-queue wait and final NodeDB snapshot are skipped. LPCOMP readiness has a
bounded retry; the fallback avoids repeated resets or an indefinite sleep with
no working voltage wake source.

USB VBUS bypasses the battery thresholds for servicing; VDD checks still protect
flash and TX. For recovery at the bench, connect USB and press Reset. An intentional
app/CLI shutdown does not arm battery-voltage wake. Energy sleep stops reception
and forwarding until recovery; packets still queued in RAM can be lost.

The policy reads the physical battery divider independently of the app's ADC
multiplier override. The RAK19007 schematic has R3=1 MOhm and R4=1.5 MOhm, giving
AIN3=0.6*VBAT. Policy readings and the app's battery display can differ. Validate
both with a meter before changing the thresholds in `LegionPowerPolicy.h` or the
LPCOMP reference. The charger continues working while the MCU is in System OFF.
The firmware measures voltage, not stored energy or solar charging current.

### Flash persistence

- Compare the complete encoded plaintext protobuf with its existing file and
  skip the replacement when every byte and the length already match.
- Verify SafeFile temporary writes using CRC32 and exact length before rename,
  including single-byte and buffer writes. The on-disk protobuf format is unchanged.
- Require protobuf encoding to complete before committing its temporary file;
  an encoding error keeps the previous critical configuration file.
- Keep the full node database, peer keys, favorites, ignored nodes and settings.
- Extend the existing VDD save guard with the measured battery reserve, and block
  guarded saves once an energy shutdown begins.
- Report protobuf checks, unchanged saves, completed saves and failures every
  five minutes in the diagnostic log. Counters stay in RAM.

Upstream flash locking, shutdown cache coordination, retries and filesystem
readability checks remain in place. The large NodeDB file still uses upstream's
space-saving, non-atomic replacement; critical configuration files keep atomic
replacement. BLE bonding and the warm-node journal follow upstream behavior.
CRC32 readback checks do not make sudden power cuts harmless or measure physical
flash erase counts. No flash-lifetime extension or sleep-current figure has been
measured on this kit yet.

## Download a build

Download ready-to-flash firmware from
[Releases](https://github.com/ethan1980/RAK3401-Legion/releases).
After both profiles build successfully, pushes to `main` and manual workflow runs
on `main` automatically publish an **experimental prerelease** of Legion.
Each release has a tag such as `legion-v0.3.0-<commit>` and includes:

- `firmware-rak3401-legion-*.uf2` for USB/bootloader flashing.
- `firmware-rak3401-legion-*-ota.zip` for OTA/DFU updates.
- Corresponding source, build metadata, debug files, and `SHA256SUMS`.

Release assets are direct downloads and have no Actions artifact retention limit.
Published releases are preserved when the same commit is rebuilt. Pull requests
build and test the firmware without publishing a release. To build and publish
manually, open **Actions → Build RAK3401 Legion → Run workflow** and select `main`.

The comparison baseline is also available in Actions.

Open a successful run in
[Actions](https://github.com/ethan1980/RAK3401-Legion/actions/workflows/build.yml)
and download its artifacts:

| Artifact | Profile | Purpose |
| --- | --- | --- |
| `RAK3401-legion-…` | `rak3401-legion` | 8 MHz bulk SPI, energy recovery, persistence checks and private telemetry |
| `RAK3401-baseline-…` | `rak3401-1watt` | Reference with the original behavior |

Each package contains the **UF2**, **DFU ZIP**, ELF, HEX, metadata, `SHA256SUMS`,
and an archive of the source used for the build. The Actions artifact ZIP contains
another ZIP, which is the DFU package. Artifacts are retained for 30 days.

This version requires hardware testing before use on an unattended node.

### Firmware identification

The firmware identifies itself as **`2.8.2.Legion0.3.0`** in MQTT map reports,
device metadata read by the app, Bluetooth Device Information and startup logs.
The hardware model remains **RAK3401**. Regular NodeInfo broadcasts do not carry
the firmware version. Maps update after receiving the next MQTT map report.

Both version numbers and the build profile display name are generated from
`meshtastic_version` and `legion_version` in `upstream.json`. Update those fields
when changing the base or Legion version. Preparation verifies the base version
against upstream `version.properties`. The advertised string must fit the
existing **17-character** field: preparation and compilation reject an overlong
version instead of truncating it. A longer future version number will require
an explicitly shorter identification format before it can be built.

Filenames retain the upstream version and source hash (`2.8.2.04cb888`).
`legion-build.json` records `advertised_firmware_version` and both complete source
commits. Packaging verifies the advertised string is present in the compiled ELF;
release validation checks it matches the configured versions. The reference
baseline keeps the original upstream firmware identification.

## Build locally

Requirements: Git, Python 3.12 and a C++17 host compiler, with access to PlatformIO
dependencies. The build runs the Legion host regression checks with ASan/UBSan
and leak detection before compiling each firmware target.

```bash
git clone https://github.com/ethan1980/RAK3401-Legion.git
cd RAK3401-Legion
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/build.py --target legion
python scripts/build.py --target baseline
```

Packages are written to `dist/legion` and `dist/baseline`. The prepared source
is stored in `.work/firmware`. The scripts prepare and build the firmware;
they do not flash a device. Preparation can be repeated and rejects a different
upstream revision or unexpected local changes. To use another destination:
`python scripts/build.py --dest /path/to/new/directory`.

## Test on the RAK

Compare the baseline and Legion using the same battery, configuration, traffic,
and RF conditions. Check startup, Bluetooth, configuration reads, messages in
both directions, ACKs, retransmissions, and reception over several hours.
Use an external meter to measure idle RX current and energy per transmitted
and received message. Battery percentage alone does not demonstrate savings.

For energy recovery, use a current-limited supply and a connected antenna. Lower
VBAT slowly and confirm TX stops and the board sleeps. Raise it through the wake
threshold and confirm configuration, keys and peer identities survive. Repeat
with brief voltage dips, weak recovery, USB servicing and an intentional shutdown.
Measure current on the complete kit during System OFF and the recovery fallback.
Keep the previous release available for rollback until these checks pass.

The host tests exercise the actual prepared policy, protobuf comparison and
SafeFile implementation with simulated I/O. They cover low readings, USB,
recovery, CRC collisions, short writes, trailing data, failed renames and stale
temporary files. The actual private telemetry module is also compiled against
simulated channels and transports: tests cover exact commands, target IDs, local
delivery, private-key checks, duplicate suppression, cooldown/rollover, changed
keys, low-power cancellation, concurrent sample updates and report size.
They do not emulate the analog circuit or prove radio stability.

For 0.3.0, test both command forms from a second node and from the app connected
to the RAK. Check missing/wrong/public keys, other channels, repeated requests,
multiple Legion responders and a key change while a reply is pending. Compare
SPI errors, reception and consumption with 0.2.0 at 4 MHz, including low battery
and recovery. Keep 0.2.0 available for rollback.

## Update the upstream base

Update the full commit SHA and version in `upstream.json`, then prepare a new
destination. Review upstream fixes, the RadioLib and nRF52 core APIs, patch
applicability, and builds of both profiles. Repeat the hardware tests;
a patch applying successfully does not establish functional compatibility.

## Project language

English is the working language of this repository. Write documentation,
code comments, commit messages, issues, and pull requests in English.

## License and provenance

Meshtastic comes from [meshtastic/firmware](https://github.com/meshtastic/firmware).
Its **GPL-3.0** license is preserved in `LICENSE` and also applies to the Legion
changes. Dependencies retain their own licenses and source references in the
upstream PlatformIO configuration.

The implementation uses the pinned Meshtastic 2.8.2 safeguards and RAK-specific
electrical values. References:
[RAK19007 schematic](https://docs.rakwireless.com/product-categories/wisblock/rak19007/datasheet/),
[RAK13302 power control](https://docs.rakwireless.com/product-categories/wisblock/rak13302/quickstart/),
[nRF52840 LPCOMP](https://docs.nordicsemi.com/bundle/ps_nrf52840/page/lpcomp.html).

## Upstream project

Legion is based on the official Meshtastic firmware. The upstream project's
header below uses its original live badge URLs; the counters update at source.

<div align="center" markdown="1">

<img src="https://raw.githubusercontent.com/meshtastic/firmware/develop/.github/meshtastic_logo.png" alt="Meshtastic Logo" width="80"/>
<h1>Meshtastic Firmware</h1>

![GitHub release downloads](https://img.shields.io/github/downloads/meshtastic/firmware/total)
[![CI](https://img.shields.io/github/actions/workflow/status/meshtastic/firmware/main_matrix.yml?branch=master&label=actions&logo=github&color=yellow)](https://github.com/meshtastic/firmware/actions/workflows/ci.yml)
[![CLA assistant](https://cla-assistant.io/readme/badge/meshtastic/firmware)](https://cla-assistant.io/meshtastic/firmware)
[![Fiscal Contributors](https://opencollective.com/meshtastic/tiers/badge.svg?label=Fiscal%20Contributors&color=deeppink)](https://opencollective.com/meshtastic/)
[![Vercel](https://img.shields.io/static/v1?label=Powered%20by&message=Vercel&style=flat&logo=vercel&color=000000)](https://vercel.com?utm_source=meshtastic&utm_campaign=oss)
[![MemBrowse](https://membrowse.com/badge.svg)](https://membrowse.com/public/meshtastic/firmware)

<a href="https://trendshift.io/repositories/5524" target="_blank"><img src="https://trendshift.io/api/badge/repositories/5524" alt="meshtastic%2Ffirmware | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

</div>

<div align="center">
	<a href="https://meshtastic.org">Website</a>
	-
	<a href="https://meshtastic.org/docs/">Documentation</a>
</div>
