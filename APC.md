# APC — Adaptive Power Control

[Overview](README.md) · [Commands](COMMANDS.md) · [Rescue backup](RECOVERY.md) · [Energy recovery](ENERGY-RECOVERY.md)

**APC means Adaptive Power Control.** Legion's **S1** implementation
adapts optional relay activity to battery conditions. It keeps reception and RF
output nominal; adaptive RF-power selection is not implemented in this stage.

**Hardware status:** OBSERVE, SHADOW and ON have been tested on hardware, including
CONSERVE and RESERVE operation with channel messages and private messages working.
Energy savings and autonomy gains have not been measured.

## Modes and commands

Send channel messages on the private secondary **LegionRF** channel. Replace
`!abcdef01` with the full ID of the Legion to control. S1 requires **CLIENT** role.

| Command | Effect |
| --- | --- |
| `/apc observe !abcdef01` | Collects passive voltage/TX statistics; normal forwarding continues. |
| `/apc shadow !abcdef01` | Models battery states and relay budgets while forwarding normally. |
| `/apc on !abcdef01` | Applies the optional relay budget after warmup and state persistence. |
| `/apc off !abcdef01` | Stops APC and restores normal optional-relay admission immediately. |
| `/apc status !abcdef01` | Returns page 1 and freezes a fresh six-page report. |
| `/apc status !abcdef01 2` | Returns page 2 of that report; pages 2–6 are available. |

Allow at least six seconds after a reply before another control command.
**Every boot starts OFF.** Modes and statistics are RAM-only, without automatic
settings writes. Detailed reports are on demand; Legion separately sends the
brief daily APC/backup reminder described in [Commands](COMMANDS.md#timing-and-replies).
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

## What APC can limit

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
frequency, modem settings, hop count or RF power.
Creating or deleting a channel with `/createch` or `/deletech` also sets APC OFF;
the daily reminder does not change its mode, counters or current report capture.

## Reading status

Page 1 creates a **15-minute frozen capture** tied to the requesting node,
channel and radio generation. Pages 2–6 read that capture; another page 1 replaces
it. Session/report IDs identify which replies belong together.

| Page | Contents |
| --- | --- |
| 1 | Mode/state, inhibition reason, raw/decision-filtered VBAT and decision counters. |
| 2 | Uptime, session duration, samples, USB samples, VBAT raw/min/max/mean/EMA, sum and VDD current/minimum. |
| 3 | Own/relay TX starts, completions, aborts and estimated airtime. |
| 4 | IRQ timing, bounded repeat-ID evidence, start failures, open TXs, sample gaps and configuration changes. |
| 5 | Radio settings, configured power and compensated chip-drive setting. |
| 6 | Budgets, protected admissions, state changes and estimated refused airtime. |

`eligible` counts optional admission attempts; `would` counts modeled refusals;
`skip` counts actual refusals in ON. OBSERVE bypasses these decisions, so its
counters stay zero even when traffic is forwarded. `observe`, `warmup`, `USB`,
`sample` and `context` explain the current inhibition; `?` means unavailable.

TX completion is local evidence, not proof of remote delivery. `evict` counts
replacement of entries in the 32-ID repeat tracker, not packet drops. Counters
spanning several modes describe a mixed session; airtime estimates are not
measured battery savings.
