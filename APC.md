# APC — Adaptive Power Control

[Overview](README.md) · [Commands](COMMANDS.md) · [Rescue backup](RECOVERY.md) · [Energy recovery](ENERGY-RECOVERY.md)

**APC means Adaptive Power Control.** Legion 0.6.5 combines the existing **S1**
optional-relay budget with **S2** per-packet RF selection. Reception remains active.

**Hardware status:** The 0.6.5 candidate was installed and the new commands
were checked on hardware. S2 radio-power targets have not been measured with RF
test equipment; savings, range and autonomy remain unmeasured.

## Modes and commands

Send channel messages on the private secondary **LegionRF** channel. Replace
`!abcdef01` with the full ID of the Legion to control. S1/S2 require **CLIENT** role.

| Command | Effect |
| --- | --- |
| `/apc observe !abcdef01` | Collects passive voltage/TX statistics; normal forwarding continues. |
| `/apc shadow !abcdef01` | Models battery states and relay budgets while forwarding normally. |
| `/apc on !abcdef01` | Applies S1 relay budgets and S2 RF selection after warmup and state persistence. |
| `/apc off !abcdef01` | Stops APC and restores normal optional-relay admission immediately. |
| `/arm !abcdef01` / `/disarm !abcdef01` | Switches APC and antispam together with one reply. |
| `/apc status !abcdef01` | Returns page 1 and freezes a fresh seven-page report. |
| `/apc status !abcdef01 2` | Returns page 2 of that report; pages 2–7 are available. |

Allow at least six seconds after a reply before another control command.
**Every boot starts OFF.** Modes and statistics are RAM-only, without automatic
settings writes. Detailed reports are on demand; Legion separately sends the
[DAILY](COMMANDS.md#daily) with its current APC mode and state.
Repeating a mode keeps its current session. OFF
retains stopped results; the next activation starts a new session. Switching
between running modes retains session counters but resets decision warmup.

## Battery policy

APC uses the existing physical battery/VDD samples, nominally every five seconds.
Decisions use a filtered battery voltage and require five minutes of fresh valid
samples before transition persistence begins.

| Transition | Filtered VBAT | Continuous persistence |
| --- | --- | --- |
| NORMAL → CONSERVE | At or below 3,800 mV | 15 minutes |
| NORMAL/CONSERVE → RESERVE | At or below 3,650 mV | 5 minutes |
| RESERVE → CONSERVE | At or above 3,750 mV | 15 minutes |
| CONSERVE → NORMAL | At or above 3,900 mV | 15 minutes |

RESERVE recovers through CONSERVE. Thresholds are experimental voltage settings,
not calibrated remaining battery percentages.

Invalid/stale readings permit normal relay admission and reset decision evidence.
That includes a sample gap over 20 seconds, VBAT outside 2,500–4,500 mV or VDD
outside 3,000–3,600 mV. Node USB power bypasses conservation; an external solar
charger may leave `USB:0`. Existing boot, TX and low-voltage safety takes priority;
APC does not itself initiate sleep. See [Energy recovery](ENERGY-RECOVERY.md)
for the independent protection thresholds and automatic wake behavior.

## S1 relay admission

Only otherwise eligible, decoded **position and telemetry broadcast relays**
from other LoRa nodes can qualify. They must have hops remaining, ordinary or
lower priority, no acknowledgement/response request, and be outside LegionRF.

Text, DMs, ACKs, routing, traceroute, admin, local-origin traffic, LegionRF,
higher-priority traffic, MQTT-origin traffic and opaque/undecodable traffic are
preserved. Unknown or oversized airtime estimates are also admitted normally.

| Battery state | Optional-relay admission budget |
| --- | --- |
| NORMAL | Normal Meshtastic behavior. |
| CONSERVE | 600 ms of estimated airtime per minute. |
| RESERVE | 120 ms of estimated airtime per minute. |

Credit accumulates up to a 2,000 ms burst cap and starts empty on a state change.
SHADOW only models refusals; ON applies them. APC leaves the normal router,
regulatory limits and radio queue in charge of admitted traffic.

A relevant settings/channel change, restart/shutdown request, transfer or recovery
disarms APC. Reactivation is explicit. It does not change the configured role,
frequency, modem settings, hop count or configured RF power. S2 selects a temporary
RF target for each eligible transmission; it does not save a new power setting.
Creating or deleting a channel with `/createch` or `/deletech` also sets APC OFF;
the daily reminder does not change its mode, counters or current report capture.

## S2 RF selection

| Relay class | CONSERVE | RESERVE |
| --- | --- | --- |
| Position/telemetry and previously completed identical NodeInfo | P0 minus 3 dB | P0 minus 6 dB |
| Relayed text and opaque PKI direct messages | P0 minus 3 dB | P0 minus 3 dB |
| Own traffic, LegionRF, routing/admin and other protected traffic | P0 | P0 |

P0 is configured nominal power. Targets never rise above it and are clamped at
21 dBm when P0 is higher. For P0=27 dBm, routine targets are 24/21 dBm, text and
opaque PKI use 24 dBm. P0 at or below 21 dBm stays unchanged. NORMAL, USB, warmup,
stale samples and OFF/OBSERVE use nominal power. SHADOW models reductions with
nominal output. `/apc on` enables both stages; there is no separate S2 switch.

First/changed NodeInfo goes nominal; only a completed local TX establishes its
payload for later reduction. A locally transmitted packet repeated within the
bounded history goes nominal. Selection occurs in standby before CAD, using the
existing RAK13302 gain conversion. A failed PA setting attempts nominal restore,
latches S2 to nominal and defers TX if restore also fails. `/apc off` clears the
fault latch. A mode change during CAD forces a new scan before TX.

## Reading status

Page 1 creates a **15-minute frozen capture** tied to the requesting node,
channel and radio generation. Pages 2–7 read that capture; another page 1 replaces
it. Session/report IDs identify which replies belong together.

| Page | Contents |
| --- | --- |
| 1 | Mode/state, inhibition reason, raw/decision-filtered VBAT and decision counters. |
| 2 | Uptime, session duration, samples, USB samples, VBAT raw/min/max/mean/EMA, sum and VDD current/minimum. |
| 3 | Own/relay TX starts, completions, aborts and estimated airtime. |
| 4 | IRQ timing, bounded repeat-ID evidence, start failures, open TXs, sample gaps and configuration changes. |
| 5 | Radio settings, configured power and compensated chip-drive setting. |
| 6 | Budgets, protected admissions, state changes and estimated refused airtime. |
| 7 | S2 configured/last/chip target, validity, fault latch, reduced/nominal/shadow counts and metadata pressure. |

`eligible` counts optional admission attempts; `would` counts modeled refusals;
`skip` counts actual refusals in ON. OBSERVE bypasses these decisions, so its
counters stay zero even when traffic is forwarded. `observe`, `warmup`, `USB`,
`sample` and `context` explain the current inhibition; `?` means unavailable.

TX completion is local evidence, not proof of remote delivery. `evict` counts
replacement of entries in the 32-ID repeat tracker, not packet drops. Counters
spanning several modes describe a mixed session; airtime estimates are not
measured battery savings.
