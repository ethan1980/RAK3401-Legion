<p align="center">
  <img src="https://raw.githubusercontent.com/ethan1980/RAK3401-Legion/ce6a7ded2c675c8a0d4417828eb1246c66033afb/assets/rak3401-legion-logo.png" alt="RAK3401 Legion - Unleash your demons" width="700">
</p>

# RAK3401 Legion

<p align="center">
  <strong><a href="README.md">Overview</a> · <a href="COMMANDS.md">Commands</a> · <a href="RECOVERY.md">Rescue backup</a> · <a href="ENERGY-RECOVERY.md">Energy recovery</a> · <a href="APC.md">APC</a> · <a href="RELEASE_NOTES.md">Release notes</a> · <a href="CHANGELOG.md">Changelog</a> · <a href="https://github.com/ethan1980/RAK3401-Legion/releases">Downloads</a> · <a href="LICENSE">License</a></strong>
</p>

Experimental Meshtastic firmware for the **RAK3401 1W with RAK13302**.
Current release: **Legion 0.6.0-alpha.1**, based on Meshtastic **2.8.2 develop**
at [`e039e34`](https://github.com/meshtastic/firmware/commit/e039e34171e697e36d4f1b66eedfb683ffffe4f5).
The node reports **`2.8.2.LGN0.6.0a1`**.

Legion focuses on this kit's radio operation, energy resilience and private
remote tools. This release is an **experimental alpha**, with partial hardware
validation. Current consumption and battery-life gains have not been measured.

## What Legion adds

| Feature | What it does | Hardware status |
| --- | --- | --- |
| [Private telemetry](COMMANDS.md#telemetry-fields) | Reports battery, CPU temperature, sampled RF noise and packet counters on demand. | Tested in this alpha. |
| [Remote node tools](COMMANDS.md#command-reference) | Sends text from a selected node, schedules restarts, lists direct RF peers and manages ignored nodes. | Tested in earlier releases; core operation confirmed in this alpha. |
| [Remote traceroute](COMMANDS.md#direct-peer-and-traceroute-reports) | Returns outbound and return mesh paths on LegionRF. | Direct, relayed and timeout replies tested in this alpha. |
| [Boot diagnostics](COMMANDS.md#boot-fields) | Reports reset evidence, first boot voltages and accelerator counters. | Partially tested in this alpha. |
| [CC310 hashing](COMMANDS.md#boot-fields) | Accelerates packet SHA-256 and ACK-proof HMAC-SHA256, with software fallback. | Hardware use confirmed; performance and energy gains unmeasured. |
| [Manual rescue backup](RECOVERY.md) | Saves configuration explicitly and restores it after confirmed essential preference loss; reports whether the backup is current. | Backup/restoration tested on earlier builds; freshness partially tested in this alpha. |
| [APC — Adaptive Power Control](APC.md) | Adapts optional relay activity to battery conditions; RF output stays nominal. | OBSERVE basic operation tested; SHADOW/ON not yet hardware-validated. |
| [Energy recovery and resilience](ENERGY-RECOVERY.md) | Protects boot, TX and saves at low supply voltage; sleeps and wakes as energy returns. | Partially tested; sleep/wake observed on earlier builds. |
| [Flash persistence](ENERGY-RECOVERY.md#usb-apc-and-configuration-resilience) | Skips identical saves and verifies temporary writes before replacement. | Software-tested; physical power-loss tolerance unverified. |
| Bulk radio SPI at 8 MHz | Transfers SX1262 buffers in blocks through the nRF52 SPI/EasyDMA path. | In use; controlled long-term comparison unverified. |
| REG1 DC/DC | Enables the MCU's efficient regulator after SoftDevice initialization. | Activation tested on earlier builds; whole-node savings unmeasured. |

“Tested” describes observed operation, not complete validation of every condition.
Earlier-release results remain distinct from results for this alpha.

## Use Legion

Download the firmware from [Releases](https://github.com/ethan1980/RAK3401-Legion/releases):
use **UF2 over USB** or the **OTA ZIP with nRF Connect**. Installation of this
alpha with nRF Connect is confirmed; the Meshtastic apps' updater and a subsequent
update initiated from this alpha are not yet validated. Ordinary application
updates preserve preferences and do not require an erase or factory reset.
Previous releases remain available for rollback.

For remote tools, configure one private **SECONDARY** channel named exactly
**LegionRF**, with your own random **16- or 32-byte PSK**, and share it with trusted
requesting nodes. Send commands as channel messages, including when connected
directly to the Legion node. Replace the example ID with the target's full ID:

```text
/telemetry !abcdef01
/boot !abcdef01
/apc status !abcdef01
```

- [Commands](COMMANDS.md): channel setup, command syntax and report fields.
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

[Meshtastic website](https://meshtastic.org) · [Meshtastic documentation](https://meshtastic.org/docs/)

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
