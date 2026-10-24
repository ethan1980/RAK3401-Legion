<p align="center">
  <img src="https://raw.githubusercontent.com/ethan1980/RAK3401-Legion/ce6a7ded2c675c8a0d4417828eb1246c66033afb/assets/rak3401-legion-logo.png" alt="RAK3401 Legion - Unleash your demons" width="700">
</p>

# RAK3401 Legion

<p align="center">
  <strong><a href="README.md">README</a> · <a href="COMMANDS.md">Commands</a> · <a href="RECOVERY.md">Recovery</a> · <a href="LICENSE">GPL-3.0</a></strong>
</p>

Experimental Meshtastic firmware for the **RAK3401 1W with RAK13302**.
Current prerelease: **Legion 0.6.0-alpha.1**, based on **Meshtastic 2.8.2 develop**,
commit [`e039e34`](https://github.com/meshtastic/firmware/commit/e039e34171e697e36d4f1b66eedfb683ffffe4f5).
This pins a source revision, not a published official nightly binary.

**Experimental alpha: hardware/RF validation of this combined version is pending.**
It integrates the base migration, APC S1, remote `/trace`, CC310 packet SHA/HMAC,
read-only `/boot` diagnostics and backup freshness. Existing Legion features
remain included. Earlier 0.4.x/0.5.x hardware results do not validate this build.
Previous release assets remain available for rollback.

APC starts **OFF** after every boot. `/apc observe|shadow|on|off|status !legionid`
controls the RAM-only S1 implementation. RF output remains nominal; adaptive
RF power is not implemented. Read [APC.md](APC.md), the
[release notes](RELEASE_NOTES.md) and [alpha hardware test sequence](ALPHA-TESTING.md).
See [0.6.0 planning](PLANNING-0.6.0.md) for the remaining validation.

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

### Private remote control

Send commands as channel messages on the configured private **LegionRF** channel.
The requesting node can run standard Meshtastic. Replies identify the responding
Legion and are also copied to its connected app.

| Command | Behavior |
| --- | --- |
| `/msg !nodeid <channel> <message>` | The selected Legion originates text on one of its enabled channels and confirms queue acceptance. |
| `/reboot !nodeid` | Schedule the selected Legion's normal reboot 20 seconds after request acceptance. |
| `/zerohop !nodeid [page]` | Report direct RF nodes with full IDs, short names and existing SNR. |
| `/ignore !peerid` | Every receiving Legion independently ignores that peer. |
| `/unignore !peerid` | Every receiving Legion independently removes that peer from its effective ignore list. |
| `/ignorelist [page]` | Each receiving Legion reports its own effective ignore list. |
| `/trace !legionid !targetid` | Run a standard traceroute and return both paths asynchronously. |
| `/boot !legionid` | Read boot evidence, first voltages and CC310 counters. |
| `/apc observe\|shadow\|on\|off\|status !legionid` | Control APC S1; see [APC.md](APC.md) for status pages and policy. |

Directory queries return one manually requested page at a time. Temporary
snapshots keep page order stable for 15 minutes and are bound to the requesting
node and private channel. Zero-hop reports require coherent direct RF evidence
from this boot; zero and negative SNR are valid. No RSSI history or periodic
probing is added.

Ignore management uses Meshtastic's persistent NodeDB and includes legacy ignore
entries. Replies distinguish saved changes from changes awaiting storage. A node
that misses a group command cannot apply it. Ignore state filters packet origins;
it does not remove their transmissions from the air. NodeDB ignore flags are
outside the manual rescue snapshot.

The new commands have a separate five-second cooldown, one pending request and
duplicate suppression. Queue acceptance does not confirm reception by another
node. Full syntax, errors and pagination limits are in [COMMANDS.md](COMMANDS.md).

The six commands introduced in 0.5.0 were tested on earlier hardware builds.
Regression testing of the migrated alpha is pending.

### REG1 DC/DC (new in 0.5.0)

The Legion profile enables the nRF52840's **REG1 DC/DC converter** through
`sd_power_dcdc_mode_set(NRF_POWER_DCDC_ENABLE)` after successful SoftDevice
initialization. DC/DC conversion can reduce the MCU regulator's losses under
load. Activation is automatic once per boot, with API-result and register-readback
checks. A failed activation is logged without repeated attempts.

Activation and readback were verified on the matching RAK3401 test unit with USB
power and after a battery-powered restart. REG0 and UICR retain their existing
configuration. **Whole-node current reduction and battery-life improvement have
not been measured.**

### Radio SPI

Legion transfers RadioLib buffers to the SX1262 in blocks through the nRF52
core's synchronous SPI API, which uses EasyDMA. The baseline transfers these
buffers one byte at a time. Legion runs radio SPI at **8 MHz** for both reads
and writes; the unchanged baseline remains at **4 MHz**. The existing
bus locking and transaction boundaries are preserved. This optimization is enabled
only in `rak3401-legion`.

The goal is to reduce transfer time and CPU overhead. **Battery savings and
8 MHz hardware stability have not been measured in a controlled bench test.**
During continuous reception,
the RF front end will still account for a significant share of total power use.

The selected upstream revision's AGC and radio recovery fixes are preserved.
The profile inherits the official pin assignments and RAK3401 hardware identity.
Normal operation retains the configured TX power, channels, role and Bluetooth.

### Manual rescue backup (introduced in 0.4.0)

Create a rescue point explicitly with `/backup !xxxxxxxx` on the private LegionRF
channel. Only the node matching that full Node ID acts. The rescue point stores
names, identity key, channels, device/radio and module settings, and fixed position.
No automatic backup is made. Use `status`, `replace` and `delete` with the same
destination; see [RECOVERY.md](RECOVERY.md) for the exact commands and reset behavior.

Two raw-flash generations outside LittleFS protect against a torn replacement.
At boot, confirmed essential preference loss can restore the saved configuration;
normal restart, name changes and firmware updates with healthy preferences do not.
A successful recovery queues the requested “Ashes to ashes…” notice on LegionRF.
Factory reset restores an armed rescue point; delete the rescue point first to
deliberately return to blank settings.

Manual backup restoration was observed on the test RAK after applying an erase.uf2,
installing bootloader 0.4.4 and reinstalling the D1 diagnostic Legion firmware by USB
UF2: the saved configuration returned. This validates that procedure with the file
used; it does not establish survival of a full-chip erase. Reception of the recovery
announcement was not verified because no connected receiver was available.
Physical interrupted-write/power-cut recovery testing remains pending.

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
| Battery reserve | Enter energy sleep after eight consecutive VBAT readings below 3.50 V, checked every 20 s. A reading at or above 3.50 V or USB power clears the counter. |
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

Energy hibernation and automatic return to operation have been observed on hardware:
the production node went offline overnight and resumed after sunrise. The exact
entry voltage and triggering protection were not recorded. The new 0.5.1 timing
still requires hardware validation.

Battery measurements remain refreshed every 5 seconds for existing protections;
only the sleep decision uses the 20-second interval. The first and eighth low
checks are nominally 140 seconds apart; scheduling affects actual latency.
Independent VDD protection, boot/wake thresholds and TX/flash limits are unchanged.

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
After both profiles build successfully, firmware changes pushed to `main` and manual
workflow runs on `main` publish an **experimental prerelease** of Legion. Documentation
updates preserve the existing firmware release.
Each release has a tag such as `legion-v0.5.0-<commit>` and includes firmware
packages, corresponding source, build metadata, debug files and `SHA256SUMS`.

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
| `RAK3401-legion-…` | `rak3401-legion` | Alpha with APC S1, trace, CC310, boot diagnostics, backup freshness and existing Legion features |
| `RAK3401-baseline-…` | `rak3401-1watt` | Reference with the original behavior |

Each package contains firmware files, metadata, `SHA256SUMS` and an archive of
the source used for the build. Actions artifacts are retained for 30 days.

### Firmware identification

The full version is **0.6.0-alpha.1**. The existing 17-character field uses
**`2.8.2.LGN0.6.0a1`** in MQTT map reports, device metadata, Bluetooth Device
Information and startup logs. `LGN` means Legion; `a1` means alpha 1. The
`/telemetry` header uses that same compiled string. Stable-version formatting
remains `2.8.2.Legion0.x.y`. The hardware model remains **RAK3401**. Regular
NodeInfo broadcasts do not carry the firmware version.

The advertised string, full build-profile display name and manifest version are
generated from `upstream.json`. Preparation verifies the pinned source version
and rejects invalid or overlong identifiers instead of truncating them.
Filenames retain the upstream version and source hash (`2.8.2.e039e34`).
`legion-build.json` records both complete source commits, patch hashes, the alpha
stage and explicit hardware-test flags. Packaging verifies the compiled version.
The reference baseline retains upstream firmware identification.

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

## Validation status

The following hardware observations are historical, from earlier Legion builds.
**All combined alpha hardware checks remain pending**; follow [ALPHA-TESTING.md](ALPHA-TESTING.md).
Software tests and both-profile builds cover the migrated alpha.

| Area | Validation status |
| --- | --- |
| Six commands introduced in 0.5.0 | Tested on hardware and working; automated parser, transport, pagination, SNR provenance and persistence tests pass. |
| REG1 DC/DC | Activation verified on the diagnostic RAK with USB and battery power; production implementation covered by API and compiled-binary checks. |
| `/telemetry` response, current version and min/max formatting | Verified on hardware. |
| `/backup !xxxxxxxx` | Backup creation and success confirmation verified on hardware. |
| `/backup status !xxxxxxxx` | Verified on hardware. |
| `/backup delete !xxxxxxxx` | Verified on hardware. |
| `/backup replace !xxxxxxxx` | Verified on hardware. |
| Emergency restoration and recovery announcement | Restoration observed after erase.uf2, bootloader 0.4.4 and Legion D1 UF2 installation; announcement reception remains unverified. |
| Recovery during interrupted writes or power loss | Covered by simulated storage tests; physical power-cut testing pending. |
| Energy savings, voltage thresholds and complete-kit sleep current | Controlled hardware measurements pending. |
| Long-term radio stability at 8 MHz | Controlled comparison with the 4 MHz baseline pending. |

The hardware telemetry and backup results above were obtained on 0.4.2. Automated
tests cover command targeting, queue results, channel changes, pagination, SNR
provenance, ignore persistence, REG1 activation, the prepared power policy,
protobuf comparison, verified file writes, telemetry, recovery journal and engine.
Build checks verify application boundaries and package integrity.
Both Legion and baseline profiles compile successfully. Simulated tests do not
measure the analog circuit, real flash timing, RF delivery or energy consumption.

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

## Credits

<table>
  <tr>
    <td align="center" width="120">
      <a href="https://github.com/EA2OY/NavaTastic"><img src="assets/credits/navatastic-navarra.png" alt="NavaTastic — map of Navarra" width="88"></a><br>
      <strong><a href="https://github.com/EA2OY/NavaTastic">NavaTastic</a></strong>
    </td>
    <td>The resilience system was inspired by the work of NavaTastic.</td>
  </tr>
  <tr>
    <td align="center" width="120">
      <a href="https://github.com/derpyspike/jentastic"><img src="assets/credits/jentastic-cat.png" alt="Jentastic — cat mascot" width="88"></a><br>
      <strong><a href="https://github.com/derpyspike/jentastic">Jentastic</a></strong>
    </td>
    <td>The command system was inspired by the multiplatform firmware and advanced administrative management of Nexus/Jentastic.</td>
  </tr>
</table>
