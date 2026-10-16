<p align="center">
  <img src="https://raw.githubusercontent.com/ethan1980/RAK3401-Legion/ce6a7ded2c675c8a0d4417828eb1246c66033afb/assets/rak3401-legion-logo.png" alt="RAK3401 Legion - Unleash your demons" width="700">
</p>

# RAK3401 Legion

Experimental Meshtastic firmware for the **RAK3401 1W with RAK13302**.
Current version: **Legion 0.4.0**, based on **Meshtastic 2.8.2 develop/nightly**,
commit [`04cb888`](https://github.com/meshtastic/firmware/commit/04cb8885118b959a9f538cd5881bd7d595758911).
This pins a specific 2.8.2 source revision, not a published official nightly binary.

This repository contains a small set of patches and a build profile. The build
downloads the upstream source pinned in `upstream.json`, applies the changes,
and produces the complete firmware. This keeps Legion changes easy to review
and port to newer Meshtastic versions.

## The story behind Legion

I'm Ethan (Javier). I joined the Meshtastic world a few years ago with a LILYGO
T-Beam as my first node. A lot has changed since then. After trying different
boards and configurations, and having more than a few battles with the mesh and
its gadgets, I ended up building a RAK3401 1W. It is still my current node, and
the one I have enjoyed using the most.

Even so, it has limitations I want to address. Some reflect the trade-offs of
general-purpose firmware: Meshtastic supports a wide range of boards, variants,
peripherals and use cases, so its development has to balance many different
requirements. I wanted to explore what could be gained by concentrating on one
particular kit and the way I use it.

That is how Legion began: custom firmware for my own RAK3401, built to make my
day-to-day life easier. I have no plans to expand it to other hardware models
or shape its development around every user's needs. Anyone with a RAK3401 is
welcome to try it, experiment and adapt it freely under the project's license.

### Why "Legion"?

The name comes from [Legion](https://en.wikipedia.org/wiki/Legion_%28demons%29),
the collective name given by a multitude of demons in the New Testament account
of the exorcism of the Gerasene demoniac. The image of many demons speaking with
one voice is what inspired the name and the logo. In the Gospel of Mark, Jesus
asks the possessed man his name:

> "What is thy name?"
>
> "My name is Legion: for we are many."
>
> — [Mark 5:9, King James Version](https://www.biblegateway.com/passage/?search=Mark%205%3A9&version=KJV)

To me, the mesh feels like a hive: many independent nodes forming a greater
whole. Inside my RAK3401, I picture the complexity of firmware designed for so
many different boards as a legion of demons, getting between the hardware and
what I want it to do. Legion is my attempt to untangle that complexity, release
those demons and help this particular kit work better.

**Unleash your demons.**

## Included changes

Legion transfers RadioLib buffers to the SX1262 in blocks through the nRF52
core's synchronous SPI API, which uses EasyDMA. The baseline transfers these
buffers one byte at a time. Legion runs radio SPI at **8 MHz** for both reads
and writes; the unchanged baseline remains at **4 MHz**. The existing
bus locking and transaction boundaries are preserved. This optimization is enabled
only in `rak3401-legion`.

The goal is to reduce transfer time and CPU overhead. **Battery savings and
8 MHz hardware stability have not been measured in a controlled bench test.**
The owner reports stable normal operation with 0.3.5; the observed name-change
restart was scheduled, not a confirmed spontaneous reset. This is not validation
of the new 0.4.0 recovery feature or end-to-end OTA.
During continuous reception,
the RF front end will still account for a significant share of total power use.

The selected upstream revision's AGC and radio recovery fixes are preserved.
The profile inherits the official pin assignments and RAK3401 hardware identity.
Normal operation retains the configured TX power, channels, role and Bluetooth.

### Manual rescue backup in 0.4.0

Create a rescue point explicitly with `/backup !xxxxxxxx` on the private LegionRF
channel. Only the node matching that full Node ID acts. The rescue point stores
names, identity key, channels, device/radio and module settings, and fixed position.
No automatic backup is made. Use `status`, `replace` and `delete` with the same
destination; see [RECOVERY.md](RECOVERY.md) for the exact commands and reset behavior.

Two raw-flash generations outside LittleFS protect against a torn replacement.
At boot, confirmed essential preference loss can restore the saved configuration;
normal restart, name changes and application OTA with healthy preferences do not.
A successful recovery queues the requested “Ashes to ashes…” notice on LegionRF.
Factory reset restores an armed rescue point; delete the rescue point first to
deliberately return to blank settings. Hardware recovery/power-cut tests are pending.

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
Each release has a tag such as `legion-v0.4.0-<commit>` and includes:

- `firmware-rak3401-legion-*.uf2` for USB/bootloader flashing.
- `firmware-rak3401-legion-*-ota.zip` for OTA/DFU updates.
- Corresponding source, build metadata, debug files, and `SHA256SUMS`.

Release assets are direct downloads and have no Actions artifact retention limit.
Published releases are preserved when the same commit is rebuilt. Pull requests
build and test the firmware without publishing a release. To build and publish
manually, open **Actions → Build RAK3401 Legion → Run workflow** and select `main`.

The comparison baseline is also available in Actions.

### Updating to 0.4.0 and the preserved DFU correction

**From installed 0.3.5, use this release's application OTA ZIP.** The DFU entry
correction from 0.3.5 is preserved. Physical end-to-end OTA is still a pending
hardware test; compiled callback/reset validation runs before packaging.

**If Legion 0.2.0 or 0.3.0 is installed, install 0.4.0 using its UF2 over USB.**
Those builds contain a defective BLE DFU entry that can immediately restart the
normal firmware instead of staying in the bootloader. Selecting another OTA ZIP
does not repair the entry in the installed firmware. Their releases are withdrawn
following the 0.3.5 hotfix; source tags and Git history are retained.

Connect a USB data cable, double-press Reset to expose the bootloader drive, and
copy this release's `firmware-rak3401-legion-*.uf2` onto it. Allow the node to
restart and check that the app reports **`2.8.2.Legion0.4.0`**. Use a normal UF2
update, without factory erase/reset. The firmware keeps the existing configuration
format and keeps the preference/warm-store boundaries. It reserves two previously
unused pages below the warm store. Export the configuration beforehand if possible.

The hotfix retains flash-write coordination and Bluetooth peer/bond handoff,
then uses the nRF52 core's full OTA reset (`GPREGRET=0xA8`). This avoids switching
from the FreeRTOS task stack before a compiler-generated C epilogue. Packaging
checks the active callback and emulates the compiled reset entry, including its
OTA marker and stack behavior. This software check stubs SoftDevice disable;
**physical BLE reconnection and a complete OTA transfer still need testing on
the RAK3401**. An OTA test must start from the corrected firmware.

Open a successful run in
[Actions](https://github.com/ethan1980/RAK3401-Legion/actions/workflows/build.yml)
and download its artifacts:

| Artifact | Profile | Purpose |
| --- | --- | --- |
| `RAK3401-legion-…` | `rak3401-legion` | 8 MHz bulk SPI, energy recovery, persistence checks, private telemetry and manual rescue backup |
| `RAK3401-baseline-…` | `rak3401-1watt` | Reference with the original behavior |

Each package contains the **UF2**, **DFU ZIP**, ELF, HEX, metadata, `SHA256SUMS`,
and an archive of the source used for the build. The Actions artifact ZIP contains
another ZIP, which is the DFU package. Artifacts are retained for 30 days.

This version requires hardware testing before use on an unattended node.

### Firmware identification

The firmware identifies itself as **`2.8.2.Legion0.4.0`** in MQTT map reports,
device metadata read by the app, Bluetooth Device Information and startup logs.
The `/telemetry` header derives `Legion0.4.0` from that same compiled version;
temperature maximum and battery minimum labels include readable spacing.
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

Requirements: a Linux host/container, Git, Python 3.12, a C++17 host compiler and
OpenSSL development headers/library (`libssl-dev` on Debian/Ubuntu), with access
to PlatformIO dependencies. The script installs the pinned PlatformIO dependencies,
then runs host regression checks with ASan/UBSan and leak detection before
compiling each firmware target. The recovery integration test uses the real
generated messages/nanopb runtime and OpenSSL as its X25519 test oracle.

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

For 0.4.0, test the command forms from a second node and from the app connected
to the RAK. Check missing/wrong/public keys, other channels, repeated requests,
multiple Legion responders and a key change while a reply is pending. Compare
SPI errors, reception and consumption with the reference at 4 MHz, including low
battery and recovery. Keep 0.3.5 available for rollback. Follow [RECOVERY.md](RECOVERY.md)
for manual backup and controlled restoration tests. The host runner also checks
interrupted journal writes, transaction resume, deletion and bounded retry state.

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
