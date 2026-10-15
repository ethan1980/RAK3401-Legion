# Legion commands

These commands require **Legion 0.3.0 or later on the responding RAK3401**.
The phone app and the requesting/receiving node can use standard Meshtastic.
Commands are ordinary text messages; no app plugin or remote-admin key is needed.

## Required private channel

1. In the Meshtastic app, create a **SECONDARY** channel named exactly **LegionRF**.
   Use a free channel slot; the slot number is not fixed by Legion.
2. Generate and assign your own random **16-byte or 32-byte PSK** using the app.
   The public default key, single-byte key aliases, an unset key and all-zero keys
   do not enable the command.
3. Share that channel with the nodes from which you want to request or read reports.
   Their channel name, PSK and encryption mode must match. Their frequency,
   bandwidth and spreading factor must also match the Legion node.
4. Open the **LegionRF** conversation and send one of the commands below.

Each installation chooses its own PSK. Another user can run the identical firmware
with a different key and the same channel name. Changing the channel key does not
require recompiling or reflashing. Keys are read from the normal node configuration
and are never included in reports or the repository.

The feature requires one unambiguous, enabled secondary channel with that name.
If it is missing, disabled, duplicated or uses a public/invalid key, Legion does
not respond. It never falls back to the primary channel or creates a channel.
Licensed/Ham mode, which disables channel encryption, does not enable this feature.

## /telemetry

| Message | Behavior |
| --- | --- |
| `/telemetry` | Every reachable Legion node on this private channel may reply. |
| `/telemetry !abcdef01` | Only the node whose full ID is `!abcdef01` may reply. |

Replace the example ID with the eight hexadecimal digits shown for your node.
Hexadecimal letters in the ID can be upper- or lowercase. The command itself
is lowercase. Leading/trailing spaces and line breaks are accepted; extra words,
partial IDs and embedded NUL bytes are rejected.

Requests must be channel broadcasts on **LegionRF**, not direct messages or
messages on another channel. This applies to both remote requests and requests
sent from the app connected to the responding RAK itself.

Replies are ordinary text messages in the same channel, encrypted with its
currently configured PSK. A copy is explicitly delivered to the connected local
app, so the RAK does not need another node to echo its own report.

Example report; values are illustrative:

~~~text
Legion0.3.0 !abcdef01 up:194400s
CPU:29.25/max34.50C BAT:82% 4.01/min3.96V
N:-116 peak:-88dBm n:600
RX:450 BAD:7 TX:32 REL:24 DROP:2
~~~

| Field | Meaning |
| --- | --- |
| up | Monotonic seconds since boot. |
| CPU / max | Current chip temperature / highest sampled chip temperature, in degrees Celsius. This is not ambient temperature. |
| BAT | Charge estimated by Meshtastic, followed by the physical battery voltage and its lowest observed value. |
| N / peak / n | Arithmetic mean of valid sampled RSSI values in dBm, highest sampled RSSI and number of samples. |
| RX / BAD | Upstream successful-reception and bad-reception counters. BAD is not exclusively a CRC-error count. |
| TX / REL | Upstream successful-transmission and relay counters. REL is a subset of TX, not an extra total. |
| DROP | Upstream dropped-transmission counter. |

Packet counters are since boot and retain upstream's counter widths. RF and
battery extrema accumulate from monitor initialization until reboot. Temperature
sampling begins once the private channel is configured. Queries do not reset
the counters or extrema. `NA` means there is no valid reading; it is not zero.

Battery voltage uses Legion's physical RAK19007 divider, independently of the
app's ADC multiplier override. The voltage and the app's estimated percentage
can therefore disagree. This is a voltage monitor, not a fuel gauge or charging
current measurement.

## Sampling and response limits

- Reuse upstream's current-channel noise samples: no more than one valid sample
  every five seconds, only while the radio is receiving and has no detected
  packet or pending interrupt. Some intervals will have no sample.
- Observe the physical battery readings already taken by Legion's power policy,
  including checks before transmission.
- Sample chip temperature every 60 seconds while the private channel is enabled,
  and refresh temperature and cached battery voltage before answering.
- No frequency sweep, retuning, CAD replacement or AGC change is performed.
  Sampled RSSI peaks are not a complete record of short interference bursts.
- There are **no automatic diagnostic reports**, including no four-hour broadcast.
- One pending response per node and a **60-second cooldown** after the response
  attempt. Extra requests during that time are silently ignored.
- Broadcast queries wait a random 1–10 seconds before response processing;
  targeted queries wait 0.25–1 second. The one-second scheduler and normal radio
  queue may add delay.
- Recently accepted sender/packet-ID pairs are suppressed for ten minutes.
  The cache is bounded to 16 entries. Relaying the same request must not trigger
  additional reports.
- Changing/removing the private channel, its key or its encryption mode cancels
  a pending reply. Low supply reserve or allocation failure cancels the attempt
  without creating a retry loop.
- Reports fit one text packet of fewer than 200 bytes. Normal radio scheduling,
  airtime restrictions and energy recovery still apply; delivery is not guaranteed.
- The counters, extrema and request cache stay in RAM. No diagnostic history is
  written to flash. Reboot and energy-recovery restart reset them.

A private messaging channel shares the existing radio frequency and airtime.
Other nodes may relay its encrypted packets even when they cannot read them.
Limit queries and hop count to what your installation needs.

An energy-sleeping node cannot receive `/telemetry`; wait for power recovery.
The feature does not alter the existing Meshtastic telemetry settings or its
standard periodic telemetry packets.

## If no report arrives

Check the exact channel name, SECONDARY role, private PSK, matching modem settings
and that the target runs Legion 0.3.0. Wait at least a minute after a previous
attempt, and allow for the response delay and a busy channel. A muted channel may
hide notifications. Keep a receiver/app connected if you need a continuous record:
ordinary nodes do not provide a guaranteed archive of earlier reports.
