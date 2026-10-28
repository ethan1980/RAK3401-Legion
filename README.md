<p align="center">
  <img src="https://raw.githubusercontent.com/ethan1980/RAK3401-Legion/ce6a7ded2c675c8a0d4417828eb1246c66033afb/assets/rak3401-legion-logo.png" alt="RAK3401 Legion - Unleash your demons" width="700">
</p>

# RAK3401 Legion

<p align="center">
  <strong><a href="README.md">Overview</a> · <a href="COMMANDS.md">Commands</a> · <a href="AUTOMATIC-FEATURES.md">Automatic features</a> · <a href="RECOVERY.md">Rescue backup</a> · <a href="ENERGY-RECOVERY.md">Energy recovery</a> · <a href="APC.md">APC</a> · <a href="RELEASE_NOTES.md">Release notes</a> · <a href="CHANGELOG.md">Changelog</a> · <a href="https://github.com/ethan1980/RAK3401-Legion/releases">Downloads</a> · <a href="LICENSE">License</a></strong>
</p>

Meshtastic firmware for the **RAK3401 1W with RAK13302**.
Current release: **Legion 0.6.1**, based on Meshtastic **2.8.2 develop**
at [`c39728e`](https://github.com/meshtastic/firmware/commit/c39728e3fb9304fc3b1160ebf14801b3b5f0a213).
The node reports **`2.8.2.Legion0.6.1`**.

Legion focuses on this kit's radio operation, energy resilience and private
remote tools. Current consumption and battery-life gains have not been measured.

## What Legion adds

| Feature | What it does | Hardware status |
| --- | --- | --- |
| [Private telemetry](COMMANDS.md#telemetry-fields) | Reports battery, CPU temperature, sampled RF noise and packet counters on demand. | Operation confirmed on hardware. |
| [Remote node tools](COMMANDS.md#command-reference) | Sends text, schedules restarts, lists direct RF peers, manages each node's ignore list and creates or deletes secondary channels. | Command operation confirmed on hardware. |
| [Remote traceroute](COMMANDS.md#direct-peer-and-traceroute-reports) | Returns outbound and return mesh paths on LegionRF. | Direct, relayed and timeout replies observed. |
| [Boot diagnostics](COMMANDS.md#boot-fields) | Reports reset evidence and first boot voltages. | Boot queries confirmed on hardware. |
| [Manual rescue backup](RECOVERY.md) | Saves configuration explicitly and restores it after confirmed essential preference loss; reports whether the backup is current. | Backup commands and manual restoration observed. |
| [APC — Adaptive Power Control](APC.md) | Adapts optional relay activity to battery conditions; RF output stays nominal. | OBSERVE, SHADOW and ON tested; CONSERVE and RESERVE observed. |
| [Energy recovery and resilience](ENERGY-RECOVERY.md) | Protects boot, TX and saves at low supply voltage; sleeps and wakes as energy returns. | Energy sleep and automatic return observed. |
| [CC310 hashing](AUTOMATIC-FEATURES.md#cc310-hashing) | Accelerates packet SHA-256 and ACK-proof HMAC-SHA256, with software fallback. | Hardware use and component queries confirmed. |
| [Bulk radio SPI at 8 MHz](AUTOMATIC-FEATURES.md#bulk-radio-spi-at-8-mhz) | Transfers SX1262 buffers in blocks through the nRF52 SPI/EasyDMA path. | Active with 8 MHz bulk transfers. |
| [Flash persistence](AUTOMATIC-FEATURES.md#flash-persistence) | Skips identical saves and verifies temporary writes before replacement. | Identical-save and readback checks verified in software. |
| [REG1 DC/DC](AUTOMATIC-FEATURES.md#reg1-dcdc) | Enables the MCU's efficient regulator after SoftDevice initialization. | Activation and readback confirmed on hardware. |

“Tested” describes observed operation, not complete validation of every condition.
The summary reflects observed operation across Legion builds.

CC310, bulk SPI, flash persistence and REG1 DC/DC are
[automatic features](AUTOMATIC-FEATURES.md): no activation command or app setting
is required.

## Use Legion

[Spanish friendly user manual](docs/Legion-Spanish-friendly-user-manual.pdf) ·
[English friendly user manual](docs/Legion-English-friendly-user-manual.pdf) (PDF).

Download the firmware from [Releases](https://github.com/ethan1980/RAK3401-Legion/releases):
use **UF2 over USB** or the **OTA ZIP with nRF Connect**. OTA installation from
the previous alpha has been confirmed. Ordinary application
updates preserve preferences and do not require an erase or factory reset.
Previous releases remain available for rollback.

For remote tools, configure one private **SECONDARY** channel named exactly
**LegionRF**, with your own random **16- or 32-byte PSK**, and share it with trusted
requesting nodes. Send commands as channel messages, including when connected
directly to the Legion node. Replace the example ID with the target's full ID:

```text
/telemetry !abcdef01
/boot !abcdef01
/components !abcdef01
/apc status !abcdef01
```

- [Commands](COMMANDS.md): channel setup, command syntax and report fields.
- [Automatic features](AUTOMATIC-FEATURES.md): what CC310, bulk SPI, flash persistence and REG1 DC/DC do, and how to check their status.
- [Rescue backup](RECOVERY.md): backup, freshness and restoration behavior.
- [Energy recovery](ENERGY-RECOVERY.md): voltage measurements, protection thresholds, sleep and automatic wake.
- [APC](APC.md): Adaptive Power Control modes and battery policy.

**APC starts OFF after every boot.** Its settings and counters remain in RAM.
The current S1 implementation conserves eligible position/telemetry relays;
RF-power adaptation is not implemented.

## Build from source

The repository contains the Legion patches and profile; `upstream.json` pins the
Meshtastic source. Requires Git, Python 3.12, a C++17 compiler and OpenSSL development
headers, plus access to PlatformIO dependencies.

```bash
git clone https://github.com/ethan1980/RAK3401-Legion.git
cd RAK3401-Legion
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/build.py --target legion
```

Packages appear in `dist/legion`. `--target baseline` builds the unchanged
`rak3401-1watt` reference. The scripts build and package; they do not flash a node.

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

## License and upstream

Legion is based on [Meshtastic firmware](https://github.com/meshtastic/firmware)
and preserves its [GPL-3.0 license](LICENSE). Dependencies retain their licenses.
English is the working language of this repository.

<div align="center" markdown="1">

<img src="https://raw.githubusercontent.com/meshtastic/firmware/develop/.github/meshtastic_logo.png" alt="Meshtastic Logo" width="80"/>
<h1>Meshtastic Firmware</h1>

![Legion release downloads](https://img.shields.io/github/downloads/ethan1980/RAK3401-Legion/total)
[![Legion CI](https://img.shields.io/github/actions/workflow/status/ethan1980/RAK3401-Legion/build.yml?branch=main&label=Legion%20CI&logo=github)](https://github.com/ethan1980/RAK3401-Legion/actions/workflows/build.yml)
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
