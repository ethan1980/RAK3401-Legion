# RAK3401 Legion

Experimental Meshtastic firmware for the **RAK3401 1W with RAK13302**.
First version: **Legion 0.1.0**, based on **Meshtastic 2.8.2 develop/nightly**,
commit [`04cb888`](https://github.com/meshtastic/firmware/commit/04cb8885118b959a9f538cd5881bd7d595758911).
This pins a specific 2.8.2 source revision, not a published official nightly binary.

This repository contains a small set of patches and a build profile. The build
downloads the upstream source pinned in `upstream.json`, applies the changes,
and produces the complete firmware. This keeps Legion changes easy to review
and port to newer Meshtastic versions.

## Included change

Legion transfers RadioLib buffers to the SX1262 in blocks through the nRF52
core's synchronous SPI API, which uses EasyDMA. The baseline transfers these
buffers one byte at a time. The SPI frequency remains **4 MHz**, with the existing
bus locking and transaction boundaries preserved. This optimization is enabled
only in `rak3401-legion`.

The goal is to reduce CPU overhead during transfers. **Battery savings and
hardware stability have not been measured yet.** During continuous reception,
the RF front end will still account for a significant share of total power use.

The selected upstream revision's AGC and radio recovery fixes are preserved.
TX power, region, channels, role, Bluetooth, listening periods, and configuration
defaults remain unchanged. LNA bypass is not implemented. The profile inherits
the official firmware's pin assignments and RAK3401 hardware identity.

## Download a build

Open a successful run in
[Actions](https://github.com/ethan1980/RAK3401-Legion/actions/workflows/build.yml)
and download its artifacts:

| Artifact | Profile | Purpose |
| --- | --- | --- |
| `RAK3401-legion-…` | `rak3401-legion` | Bulk SPI enabled |
| `RAK3401-baseline-…` | `rak3401-1watt` | Reference with the original behavior |

Each package contains the **UF2**, **DFU ZIP**, ELF, HEX, metadata, `SHA256SUMS`,
and an archive of the source used for the build. The Actions artifact ZIP contains
another ZIP, which is the DFU package. Artifacts are retained for 30 days.

This version requires hardware testing before use on an unattended node.
The filename and profile identify Legion; the version shown in the app retains
the Meshtastic version and commit (`2.8.2.04cb888`).

## Build locally

Requirements: Git and Python 3.12, with access to PlatformIO dependencies.

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
