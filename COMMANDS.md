# Legion commands

The current release is **Legion 0.5.0**. Remote messaging, reboot, zero-hop reports
and ignored-node management require 0.5.0 on the executing RAK3401. Telemetry
requires 0.3.0 or later; manual rescue backup requires 0.4.0 or later.
The phone app and the requesting/receiving node can use standard Meshtastic.
Commands are ordinary text messages; no app plugin or remote-admin key is needed.

## Required private channel

1. In the Meshtastic app, create a **SECONDARY** channel named exactly **LegionRF**.
   Use a free channel slot; the slot number is not fixed by Legion.
2. Generate and assign your own random **16-byte or 32-byte PSK** using the app.
   Short key aliases, including the public default, an unset key and all-zero keys
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

All commands use **channel broadcasts**, including requests from an app connected
directly to the executing Legion. Commands are lowercase. IDs always contain
eight hexadecimal digits after `!`; either hexadecimal letter case is accepted.

## /msg - originate text from a selected Legion

~~~text
/msg !abcdef01 SFNarrow Hello from the roof
/msg !abcdef01 "My channel" Hello world
~~~

The ID selects the Legion that transmits. The named channel must be enabled on
that Legion; the requesting node only needs LegionRF. The text is broadcast on
the destination channel under the selected Legion's identity.

All three fields are required. Names use the effective Meshtastic channel name,
including the preset-derived name for an unnamed channel, with ASCII
case-insensitive matching. Quote names containing spaces. The name is limited
to the existing 11-byte field; message text is at most 199 UTF-8 bytes and the
complete command must fit a normal mesh text packet. Leading separator whitespace
is removed; remaining text, including trailing whitespace, is preserved. Oversized
or malformed text is rejected without truncation.

Queue acceptance produces `!abcdef01: Message queued to SFNarrow` on LegionRF.
This does not prove another node received or read the message. A lost status
reply never causes an automatic second publication. An explicit resend with a
new packet ID can publish the text again.

Missing, malformed or nonmatching executor IDs are silent. A valid own target
with missing fields gets usage help. Missing/disabled channels, duplicate active
names, changed settings and queue failures produce errors when a reply is
possible. No fallback channel is used. The destination identity and encryption
settings are rechecked before dispatch. Firmware-generated local messages do
not re-enter Legion's command handlers on the transmitting node.

## /reboot - scheduled normal restart

~~~text
/reboot !abcdef01
~~~

Only the matching Legion acts. It schedules the normal Meshtastic reboot for
20 seconds after acceptance and attempts `!abcdef01: Reboot scheduled in 20s`.
Repeated requests do not postpone the deadline. An earlier restart already
scheduled by Meshtastic is preserved. A failed reply does not cancel the reboot.
The normal save and notification paths run before restarting.

An active settings transaction, file transfer, blocked recovery state or low
power reserve rejects the operation with a busy response when possible. Missing,
malformed or nonmatching IDs are silent; extra fields addressed to the local node
produce usage help. Healthy preferences do not trigger emergency restoration.

## /zerohop - direct RF nodes and SNR

~~~text
/zerohop !abcdef01
/zerohop !abcdef01 2
~~~

The optional positive page defaults to 1. Pages identify the responding node,
snapshot, page count and eligible-node count. Rows show full ID, short name and
SNR in dB, sorted by descending SNR and then Node ID. Unknown names appear as `?`.

~~~text
!abcdef01 ZH#0001 1/3 n:14 SNR
!11111111 NEX1 +8.50dB
!22222222 RAK2 +0.00dB
!33333333 TEST -3.25dB
Next: /zerohop !abcdef01 2
~~~

Entries require a genuine direct RF observation during this boot, known zero-hop
metadata and existing valid SNR. Zero and negative SNR are valid. A later relayed,
unknown-hop, Internet-origin or replay-like observation removes that node's
direct-link qualification. Previous-boot records and observations from an earlier
radio configuration are insufficient. No RSSI history, probes or Neighbor Info
transmissions are added.

Results describe the latest eligible observations in the current NodeDB. They
are not an active scan, an exhaustive directory or proof of a bidirectional link.
An entry may remain until a later observation changes its qualification or the
node restarts. The existing noise RSSI in `/telemetry` is a separate diagnostic.
Missing, malformed or nonmatching executor IDs are silent; invalid pages for the
matching node get an error.

## /ignore, /unignore and /ignorelist - group-wide peer management

~~~text
/ignore !12345678
/unignore !12345678
/ignorelist
/ignorelist 2
~~~

The argument is the **peer to ignore or unignore**. Every Legion receiving the
request on the authorized LegionRF channel acts independently. These commands
have no executor selector. Each response identifies its originating Legion.

- `/ignore` uses Meshtastic's normal protected NodeDB ignored flag. A valid unseen
  ID can be added when database and protected-node capacity permit.
- `/unignore` removes both the NodeDB flag and matching legacy LoRa ignore entries.
- `/ignorelist [page]` reports the deduplicated union, sorted by full ID, with
  available short names. Each Legion reports its own effective list.

Typical replies include `!abcdef01: Ignored !12345678`, `Already ignored`,
`Unignored` and `Not ignored`. Malformed, reserved and self IDs are rejected.
Capacity and storage failures are explicit.

Saved changes survive a normal reboot and use standard app-visible state. A
deferred or failed write is reported as **`in RAM; persistence pending`**. Retries
use a minute cadence and the graceful reboot save path. Sudden power loss before
a successful save can lose that change. Already-applied requests avoid redundant
writes.

Nodes that miss the command do not catch up automatically; their lists may differ.
Staggered responses describe individual results, not a fleet-wide atomic change.
Ignoring filters packets by originating `from` ID. It does not silence a radio,
free already-used airtime or block unrelated origins forwarded by that physical
relay. An ignored sender is filtered before command dispatch and cannot rely on
unignoring itself through the same path; use another authorized node or a local
app. NodeDB ignore flags are outside the manual rescue snapshot.

## Pagination and limits for new commands

- Directory queries return one page per request, at most five rows and 199 UTF-8
  bytes. Names are not split and long lists are not silently truncated. Follow
  the `Next:` command to retrieve another page.
- Snapshots last **15 minutes**, retain sort order and bind to the requesting
  node and private channel/key. Repeating a page with a new request packet ID
  retrieves identical content while valid. Page 1 reuses an active snapshot;
  after expiry it creates a fresh one.
- Each report type has one active snapshot. Another requester receives a busy
  result. Expiry or a changed key requires page 1 again. Zero-hop reports also
  invalidate after a radio configuration change.
- Capacity is 128 rows; overflow is explicitly labeled `partial`. An empty list
  uses one short response. Ignore/unignore commands invalidate the local ignore
  snapshot. Changes through other paths may wait until snapshot expiry to appear.
- The six new commands share one pending request and a **five-second cooldown
  after processing** per Legion. Requests while pending/cooling down are silent.
  This gate is separate from telemetry/backup's 60 seconds.
- Targeted requests wait 0.25-1 second; group requests wait 1-10 seconds, followed
  by normal scheduler/queue delays. The duplicate cache holds 16 sender/packet-ID
  pairs for 15 minutes in RAM.
- Channel/key changes and insufficient power cancel pending operations. Normal
  scheduling, airtime limits and energy recovery apply. Sleeping nodes cannot
  receive commands. No persistent command log or automatic retry is added.

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
Legion0.5.0 !abcdef01 up:194400s
CPU:29.25 / max 34.50C BAT:82% 4.01 / min 3.96V
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

## /backup — manual rescue point (0.4.0)

| Message | Behavior |
| --- | --- |
| `/backup !abcdef01` | Create if absent; never silently overwrite. |
| `/backup status !abcdef01` | Report whether a valid rescue point exists. |
| `/backup replace !abcdef01` | Explicitly replace with current settings. |
| `/backup delete !abcdef01` | Disable recovery with a durable deletion marker. |

All four commands require the full destination ID. Other nodes remain silent.
They use the same channel validation, cooldown and duplicate cache as telemetry.
No key or backup contents are sent in the reply. Wait for the explicit saved or
deleted response; a delivery icon is not proof of persistence.

Installing firmware, rebooting or changing settings never creates a rescue point.
Names, keys, radio/module/channel settings and fixed position are captured only
after an explicit backup command. Read [RECOVERY.md](RECOVERY.md) before using factory
reset: an armed rescue point is restored; delete it first to deliberately remain blank.
The successful-recovery notice is separate from routine telemetry and is emitted
only after a completed recovery.

## Telemetry/backup sampling and response limits

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
and that the target runs a compatible Legion version. Wait at least a minute after a previous
attempt, and allow for the response delay and a busy channel. A muted channel may
hide notifications. Keep a receiver/app connected if you need a continuous record:
ordinary nodes do not provide a guaranteed archive of earlier reports.

## Validation status

Telemetry responses, current firmware version and min/max formatting were verified
on 0.4.2 hardware. All backup commands—creation with its success confirmation, status,
replacement and deletion—are also verified on hardware. Automatic emergency
restoration from the saved copy and the recovery announcement remain pending
hardware verification.
The six commands introduced in 0.5.0 have automated parser, transport, pagination,
SNR provenance, duplicate and persistence coverage. End-to-end hardware validation
of these additions is pending.
