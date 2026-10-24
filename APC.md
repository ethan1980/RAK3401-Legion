# APC S1 — Legion 0.6.0-alpha.1

Status: included in the experimental alpha on the migrated `e039e34` base.
Hardware/RF validation remains pending. This stage implements battery-state
decisions and optional relay conservation. RF output remains nominal; adaptive
RF power requires separate receiver evidence and is not implemented by S1.

## Commands

Send commands on the existing private secondary LegionRF channel. Replace the
example with the executor's complete node ID. Commands target one Legion only.

| Command | Effect |
| --- | --- |
| `/apc observe !2fcd88d4` | Collect passive voltage/TX statistics; no conservation decisions. |
| `/apc shadow !2fcd88d4` | Evaluate states and model the optional relay budget; forward normally. |
| `/apc on !2fcd88d4` | Apply the optional relay budget after fresh warmup and state persistence. |
| `/apc off !2fcd88d4` | Stop APC and observation; restore normal relay admission immediately. |
| `/apc status !2fcd88d4` | Capture and return the operational summary. |
| `/apc status !2fcd88d4 2` | Read another page of that frozen capture; pages 2-6 are optional. |

Allow at least six seconds between commands. Existing command deduplication,
private-channel checks, TX readiness and radio scheduling apply. Repeating the
current mode does not reset its evidence or counters. Changing modes resets
decision evidence; moving from SHADOW to ON requires new warmup and persistence.

Modes and all APC statistics are in RAM. Every boot starts OFF. There are no
periodic announcements, configuration writes or new backup fields. OFF retains
the stopped results; the next non-OFF mode starts a new observation session and
clears the session counters. Changes between running modes retain the session.
Counters spanning multiple modes describe that mixed session, not one mode alone.

## Provisional battery policy

Use physical battery voltage and VDD from the existing power sampler, nominally
every five seconds. The decision EMA uses a coefficient of 1/12. Collect five
minutes of fresh valid samples before starting state-persistence timers.

| Transition | Filtered battery requirement | Continuous persistence |
| --- | --- | --- |
| NORMAL to CONSERVE | At or below 3,800 mV | 15 minutes |
| NORMAL or CONSERVE to RESERVE | At or below 3,650 mV | 5 minutes |
| RESERVE to CONSERVE | At or above 3,750 mV | 15 minutes |
| CONSERVE to NORMAL | At or above 3,900 mV | 15 minutes |

RESERVE recovers through CONSERVE, even after a large voltage increase. A target
change restarts its persistence timer. The values are experimental thresholds,
not a battery-percentage or remaining-runtime calibration.

A battery reading outside 2,500-4,500 mV, VDD outside 3,000-3,600 mV, or a sampling
gap longer than 20 seconds resets decision evidence. Missing/stale evidence
permits normal relay admission. New valid measurements require warmup again.
Node USB/VBUS bypasses conservation; disconnecting it requires fresh warmup.
An external charger connected to the battery base, or a solar panel, is not
identified by the node's USB flag.

The existing battery/VDD safety policy remains independent. Its TX refusal,
protective shutdown, wake and DFU behavior take precedence over APC. APC does
not prevent or delay those protections and does not initiate sleep itself.

## Relay conservation

Only decoded, ordinary-priority or lower, non-acknowledged broadcasts carrying
POSITION_APP or TELEMETRY_APP can qualify. The packet must be received over
LoRa, be from another node, have hops remaining and be outside LegionRF.

S1 always preserves local-origin traffic, text, DMs, ACKs, routing, traceroute,
admin and other port numbers, replies, requests requiring responses, packets
requesting acknowledgements, higher-priority traffic, MQTT-sourced traffic,
opaque/undecodable traffic, and LegionRF. A packet whose calculated airtime is
unknown, zero or greater than two seconds is also preserved. Unknown content
is never classified as expendable.

The existing router decides whether a relay is otherwise eligible. APC runs
just before allocating its outgoing relay copy; suppressed packets are still
processed locally. S1 does not alter the role, hop count, channel parameters,
packet contents, receive duty or output power, and does not add retries.

| Battery state | Optional relay admission budget |
| --- | --- |
| NORMAL | Normal Meshtastic relay behavior. |
| CONSERVE | 600 ms of estimated optional-relay airtime per minute. |
| RESERVE | 120 ms of estimated optional-relay airtime per minute. |

The token bucket has a maximum credit of 2,000 ms and starts empty after a
state transition. It accumulates fractional credit without rounding each
five-second sample down. The cap allows bursts; these figures are not a
per-minute regulatory duty-cycle guarantee. Protected traffic lies outside
the optional budget, and normal regulatory/radio scheduling remains in force.

SHADOW advances the same budget model but never refuses a relay. `would` counts
budget refusals predicted at the router admission point; `skip` counts actual
refusals in ON. These are admission attempts, not proven unique losses or
successful remote deliveries. The protected-admission counter covers this
decoded relay hook; opaque relays bypass the hook and are not counted there.
A packet allowed into the normal queue can
later be cancelled by duplicate suppression, a full queue or another ordinary
radio condition. Consequently the estimated refused airtime is not measured
saved RF time, battery energy or an autonomy improvement. Shadow and active
operation also influence the surrounding mesh differently.

The initial 73 h 25 min observation shows 98.829% of completed TX time in
relays. It does not identify how much qualifies for this protected policy, so
that percentage must not be advertised as attainable battery savings.

## Context changes and reporting

CLIENT is required for the S1 candidate. A pending reboot/shutdown, settings
edit, transfer, recovery operation, change of LegionRF or the primary channel,
or relevant LoRa settings disarms APC. Fresh activation is explicit. The
controller also rejects evidence from a different radio generation. No
automatic announcement is transmitted when disarming.

Page 1 reports mode, battery state, inhibition reason, last observed raw
battery/decision EMA, pending transition and dwell seconds, eligible admission
attempts, predicted refusals and actual refusals. `sample` means fresh valid
evidence is missing; `warmup` means the initial five-minute period; `USB` means
node VBUS is present; `context` with OFF means automatic disarming. `?` means
the decision EMA is unavailable, rather than a zero-volt measurement.

Page 1 freezes all six pages for 15 minutes, bound to the requester, private
channel and radio generation. Another page 1 replaces the capture. Later
pages are not live updates. All replies fit the existing 199-byte payload
limit or return an explicit size error.

| Page | Contents |
| --- | --- |
| 1 | Operational state and controller counters. |
| 2 | Observation elapsed time, sample counts, raw/min/max/mean/EMA VBAT, exact sum and VDD. |
| 3 | Own/relay TX start, completion and interruption counts, and estimated airtime. |
| 4 | Completed IRQ timing, repeated-ID evidence, start failures, unresolved starts, sample gaps and generation changes. |
| 5 | Radio configuration and compensated chip-drive setting. |
| 6 | Optional budget, burst cap, protected admissions, state transitions and estimated refused airtime. |

Pages 2-5 retain the O1.1 measurement meanings, under a new A2 header and page
numbers. The observation EMA covers its session, while the decision EMA
restarts after mode/evidence changes. TX_DONE still establishes local
completion only. Statistics are not current or charge measurements.

## Hardware validation after alpha installation

1. Preserve the completed O1.1 record under its original base. Install the alpha
   on an accessible node; every boot starts APC OFF. Record firmware identity,
   configuration and `/boot` evidence before activating a mode.
2. The upstream base is pinned to `e039e34`, including the BLE OTA reset fix
   added after the reviewed `0d3da2d` revision. Compare the migrated firmware
   before enabling relay conservation; see [ALPHA-TESTING.md](ALPHA-TESTING.md).
3. Test the combined development additions: `/trace`, CC310, `/boot`, backup
   freshness, backup restoration and the verified DFU path.
4. On the migrated candidate, collect a short reference in OBSERVE, then run
   SHADOW across a day/night transition. Check state stability, eligible
   workload, modeled refusals and command reachability.
5. Validate ON with known peers, checking both intended optional-refusal
   behavior and preservation of text, DMs, ACKs, traceroutes and control replies.
   Test low-voltage states with a controlled supply or naturally occurring
   conditions; host-injected voltage traces are not hardware validation.
6. Design/calibrate the adaptive RF-power component separately with known
   receivers and delivery evidence. An inbound SNR or TX_DONE alone cannot
   establish reduced-power outbound reachability. S1 keeps nominal power.

The command surface can continue through these stages; no additional OTA is
needed solely to change OBSERVE/SHADOW/ON/OFF. Final thresholds, budget values,
boot/persistence policy remain subject to physical validation results. The alpha
source pin is fixed; any subsequent change requires a new build/version.

## Software validation record

For the 2026-10-24 alpha, the prepared S1 tree passes the overlay Python test suite and
the firmware host regression runner, including the actual control/APC
translation units, CC310/boot, recovery and DFU boundary tests. APC-specific
tests exercise persistence, hysteresis, initial low-voltage warmup, isolated
transients, USB, invalid/stale measurements, mode idempotency, fractional
budgets, burst caps, 32-bit rollover, traffic exemptions and context disarming.
Long-uptime simulations cover 50 days of controller operation and command
availability after 25 days without requests. Completed warmup and expired
command/traceroute cooldowns do not reappear at the clock's half-range.
Host checks use AddressSanitizer and UndefinedBehaviorSanitizer; exit-time
LeakSanitizer is disabled for this restricted runtime.

Both `rak3401-legion` and `rak3401-1watt` compile on the migrated pinned base.
The Legion ELF passes compiled DFU/DC-DC checks and the application-only
ELF/OTA/UF2 comparison, with the rescue reserve outside the application image.
Exact patch preparation and whitespace checks pass. Code formatting uses local
clang-format 20.1.0 and Black 26.5.1.

These are software/build checks. No physical node has been flashed during
preparation; RF delivery, current consumption and battery savings remain
unverified. The alpha advertises `2.8.2.LGN0.6.0a1`; APC reports use A2.
