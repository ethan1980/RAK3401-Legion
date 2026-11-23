# Legion commands

[Overview](README.md) · [Automatic features](AUTOMATIC-FEATURES.md) · [Rescue backup](RECOVERY.md) · [Energy recovery](ENERGY-RECOVERY.md) · [APC](APC.md) · [Antispam](ANTISPAM.md)

These commands are available in **Legion 0.7.2**. The requesting node and
phone app can use standard Meshtastic. See the
[feature summary](README.md#what-legion-adds).

## Private channel

1. Configure one enabled **SECONDARY** channel named exactly **LegionRF**.
2. Assign your own random **16-byte or 32-byte private PSK**. Public/default keys,
   short key aliases, unset keys and all-zero keys do not enable the commands.
3. Share that channel with trusted requesting nodes using compatible LoRa settings.
4. Send the command as a **channel broadcast on LegionRF**, not a direct message.
   This also applies to the app connected directly to the executing Legion.

Access to this channel authorizes control; there is no extra command password.
Commands are lowercase. All targeted commands accept either the full eight-digit
hexadecimal node ID or the node's own short name, as described below.

## Node selection

The general selector is **`!nodeid | shortname`**: choose either the full
`!` plus eight-digit hexadecimal node ID or the executing Legion's actual short
name. These are placeholders, not words to send. `|` means **or**; parentheses
group alternatives, square brackets mark an optional argument, and angle
brackets mark a value to replace. Do not type this notation literally.

```text
/telemetry !nodeid | shortname
/trace (!nodeid | shortname) (!peerid | shortname)
/backup status !nodeid | shortname
```

**Examples - PSVR and AZTH are sample short names, not part of any command:**

```text
/telemetry PSVR
/telemetry AZTH
/telemetry !2fcd88d4
```

Substitute the name or ID of your own target. The rule applies to **every targeted
command**, including APC/guard actions, backup subcommands and pagination.
`/telemetry` without a selector still asks all reachable Legion nodes on the
channel to report.

Short names match the entire name without ASCII case differences. Quote a name
containing spaces, for example `/boot "AB C"`. Commands and channel names retain
their existing rules. Each Legion matches its own name: if two Legions on the
same LegionRF channel share that short name, both can execute the command.
Use the full ID to select one uniquely.

The second node in `/trace`, `/ignore`, `/unignore` and `/guard clear` also accepts
a short name. Syntax: `/trace (!nodeid | shortname) (!peerid | shortname)`.
It must resolve to exactly one named entry in the executing Legion's NodeDB.
Missing or ambiguous names produce an error asking for the full ID. A queued
operation rechecks the name before acting and cancels if its identity changed.
The quoted **long name** in `/ignore name` remains the literal filtering rule;
it is separate from these node selectors.

## Command reference

| General syntax | Result |
| --- | --- |
| `/telemetry` | Reachable Legion nodes report telemetry. |
| `/telemetry !nodeid \| shortname` | Only the selected Legion reports telemetry. |
| `/msg (!nodeid \| shortname) <channel> <message>` | The selected Legion broadcasts text on its named channel. |
| [`/drakarys (!nodeid \| shortname) <channel> <message>`](#drakarys) | Sends the message on the selected channel at maximum available power and 7 hops. Use is under the user's responsibility; the user must assess legality in their region. |
| `/reboot !nodeid \| shortname` | Schedules a normal restart 20 seconds after acceptance. |
| `/zerohop (!nodeid \| shortname) [page]` | Lists direct RF peers, short names and SNR. |
| `/ignore (!nodeid \| shortname) (!peerid \| shortname)` | The selected Legion ignores the second node. |
| `/unignore (!nodeid \| shortname) (!peerid \| shortname)` | The selected Legion removes the second node from its effective ignore list. |
| `/ignorelist (!nodeid \| shortname) [page]` | The selected Legion reports its own ignore list. |
| `/ignore name (!nodeid \| shortname) "<long_name>"` | Saves an exact long-name rule on the selected Legion. |
| `/unignorename (!nodeid \| shortname) "<long_name>"` | Removes that name rule. |
| `/ignorelist names (!nodeid \| shortname) [page]` | Lists the name rules with their last seen IDs and drop counters. |
| `/trace (!nodeid \| shortname) (!peerid \| shortname)` | The selected Legion traces the second node and returns both paths. |
| `/boot !nodeid \| shortname` | Reports boot evidence and first boot voltages. |
| `/components !nodeid \| shortname` | Reports CC310 counters, radio SPI, REG1 DC/DC and preference-save counters. |
| `/daily !nodeid \| shortname` | Reports the last closed 24-hour MeshHealth cut and its age. |
| `/position !nodeid \| shortname` | Reports local position, validity, precision and configured LoRa/MQTT publication. |
| `/listchannels !nodeid \| shortname` | Lists enabled configured channels and their one-based positions. |
| `/createch (!nodeid \| shortname) <channel> <psk>` | Creates a secondary channel in the first available slot using a Base64 PSK. |
| `/deletech (!nodeid \| shortname) <channel>` | Deletes the uniquely named secondary channel. |
| `/backup !nodeid \| shortname` | Creates a rescue point if none exists. |
| `/backup status !nodeid \| shortname` | Reports rescue validity and freshness. |
| `/backup replace !nodeid \| shortname` | Explicitly refreshes the rescue point. |
| `/backup delete !nodeid \| shortname` | Deletes the rescue point and disables its recovery. |
| `/apc (observe \| shadow \| on \| off) (!nodeid \| shortname)` | Selects an [Adaptive Power Control mode](APC.md). |
| `/arm !nodeid \| shortname` | Enables APC S1+S2 and antispam for this run; clears saved permanent arming. |
| `/arm permanent !nodeid \| shortname` | Enables both and saves automatic arming across restarts. |
| `/disarm !nodeid \| shortname` | Turns both OFF and clears saved permanent arming. |
| `/guard status !nodeid \| shortname` | Reports antispam mode, quarantines and counters. |
| `/guard (observe \| on \| off) (!nodeid \| shortname)` | Selects the RAM-only antispam mode. |
| `/guard clear (!nodeid \| shortname) (!peerid \| shortname)` | Clears temporary antispam evidence; manual ignores remain. |
| `/spamlist (!nodeid \| shortname) [page]` | Lists temporary quarantines; see [Antispam](ANTISPAM.md). |
| `/scramble !nodeid \| shortname` | Silences the selected Legion for 60 minutes, then restarts it. |
| `/apc status (!nodeid \| shortname) [page]` | Reports APC status, pages 1–7. |

Square brackets denote optional arguments; do not type them. `/ignorelist` requires
the executor selector before its optional page. Every targeted syntax shows both choices. Backup details are in [RECOVERY.md](RECOVERY.md).

## Timing and replies

| Command family | Timing |
| --- | --- |
| Remote tools, APC and antispam | Shared five-second cooldown after processing; allow at least six seconds after a reply. |
| Telemetry and backup | Shared 60-second cooldown after a response attempt. |
| Traceroute | One active trace, at least 60 seconds between starts, up to 90 seconds for a result. |
| Scramble | Blocks normal traffic on receipt. An entry notice has up to 4 seconds to transmit. |

Normal radio scheduling adds delay. Requests during cooldown may receive no reply.
Replies identify the executing Legion and are copied to its connected app.
A `queued` response means local queue acceptance, not delivery to another node.
Channel/key changes or insufficient power can cancel a pending operation.

## DAILY

Every **24 hours from boot**, Legion queues a status report on the private
LegionRF channel, even when APC is OFF. The first is due at 24 hours,
then 48, 72 and so on; rebooting restarts the count. The summary uses background
priority, requests no ACK and does not replace a backup or reset APC captures.
If busy or unable to queue it, the node has a 15-minute window with at most one
attempt per minute. Each part queues once and missed windows expire.
Backup labels are `UP TO DATE`, `NOT PRESENT`, `OUTDATED`, `INVALID` and `UNKNOWN`.
Antispam reports `SPAM:ON Q:n`, `SPAM:OFF Q:0` or `SPAM:OBSERVE simQ:n`.
The OBSERVE count is for simulated quarantines.

```text
!abcdef01 DAILY
APC:ON NORMAL
SPAM:ON Q:0
BACKUP:UP TO DATE
BAT:78% (-5pp) 4.01V (-60mV)
MeshHealth 60/100
Heard:258 Direct:18 2+ hops:59
Relayed:120 Sources:54
DM targets:5 Confirmed:3
```

- **BAT** shows the estimated charge, measured voltage and the change since
  the previous 24-hour cut in percentage points and millivolts. `24h:NA`
  indicates a missing reference. The two samples are kept in RAM.
- **MeshHealth** compares the node with the median of up to seven prior full
  cuts on the same LoRa configuration and role. `Heard` contributes 40 points,
  `Direct` 25 and `Sources` 35. Each contribution is capped at its weight.
  A zero reference leaves that metric out and scales the remaining weights.
  A score of 100 means the node met its reference in every scored metric.
- **Heard** counts distinct LoRa origins. **Direct** counts origins heard
  with zero relay hops. **2+ hops** counts origins whose shortest known
  observed path used two or more relays. The report uses the node's committed
  LoRa slot and excludes MQTT-origin traffic.
- **Relayed** counts completed LoRa re-transmissions. **Sources** counts
  distinct origins in those relays. **DM targets** and **Confirmed** count
  destinations of locally transmitted direct texts and destinations whose
  explicit ACK arrived during the same cut. Relayed records local TX.
- **MeshHealth NA** appears while a comparable reference is unavailable.
  **MeshHealth PARTIAL** marks an incomplete cut or a configuration change.
  History starts again after reboot. The report uses existing traffic.
- Tracking is exact for up to **768 distinct nodes** per cut. Above that, the
  unique counts use bounded-memory estimates marked `~`; the cut can still
  contribute a score and a reference. A score marked `~` uses estimated data
  in the current cut or its reference. `Relayed` remains a packet count.
  The first complete comparable cut normally shows `NA`; a score can appear
  from the next complete cut.

Reports over 199 bytes use `DAILY 1/2` for APC, SPAM, BACKUP and BAT, and
`DAILY 2/2` for MeshHealth. Both parts share the same cut and node ID.

### Manual DAILY query

Send `/daily !nodeid | shortname` to read the **last closed** 24-hour
MeshHealth cut. It returns the MeshHealth score or `NA`/`PARTIAL`, the cut's
activity fields, any `~` estimate markers and `age:...s` since that cut closed.
Before the first 24-hour period closes, it replies that DAILY is unavailable.
The query does not create a fresh cut, reset history or move the automatic DAILY
schedule. Its response is the MeshHealth portion, not a fresh battery reading.

## Position query

Send `/position !nodeid | shortname`. The read-only reply includes
`FIXED` or `LIVE`, coordinate validity, latitude/longitude, effective position
precision in bits, selected sharing channel (one-based), the configured broadcast
interval and smart-position flag. It also reports LoRa TX/sharing configuration
and MQTT enable, channel uplink and map-reporting flags.

These are the node's local coordinates and configured publication settings,
not confirmation of a new GPS fix or of LoRa/MQTT delivery. No position request,
radio reconfiguration or flash save is made.

## Arm and disarm

Send `/arm !nodeid | shortname` on LegionRF to enable APC S1+S2 and antispam
for this run. APC requires CLIENT and follows its usual warmup. If activation
requirements fail, the request leaves both modes and the saved preference as they were.

Use `/arm permanent !nodeid | shortname` to enable both and **save automatic arming across
restarts**. The saved preference is read back before confirmation. On the next
boot it restores both after configuration and activation checks are ready;
APC starts a fresh session and warmup. Statistics, samples and spam quarantines
are still RAM-only. Missing or invalid saved state uses APC OFF and spam OBSERVE.

Ordinary `/arm !nodeid | shortname` clears a previous permanent preference while arming the
current run. `/disarm !nodeid | shortname` turns both OFF, clears temporary spam evidence and
clears the permanent preference. A save failure reports an error and leaves
both modes as they were. Individual `/apc` and `/guard` mode changes affect the
current run; the saved preference remains until ordinary `/arm` or `/disarm`.
APC status page 1 and mode replies expose `AUTOARM:saved` or `AUTOARM:OFF`.

| Command | Confirmation |
| --- | --- |
| `/arm !nodeid \| shortname` | `!abcdef01: APC ON (S1+S2). SPAM ON.` |
| `/arm permanent !nodeid \| shortname` | `!abcdef01: APC ON (S1+S2). SPAM ON. AUTOARM saved.` |
| `/disarm !nodeid \| shortname` | `!abcdef01: APC OFF. SPAM OFF.` |

## Messages, restarts and ignored nodes

For `/msg`, use an enabled channel name on the executing Legion. Quote names
containing spaces, for example `/msg (!nodeid | shortname) "My channel" Hello`. The complete
command must fit the normal 199-byte text limit; channel names are limited to
11 bytes. There is no fallback to another channel or automatic command resend.

### Drakarys

Send `/drakarys (!nodeid | shortname) <channel> <message>`
in LegionRF. The syntax, channel selection and text limits are the same as
for `/msg`.

**Sends at the maximum available power.** The node sends the message on the
selected channel at the maximum available power and **7 hops**. These temporary
transmission settings apply to this message; subsequent traffic uses its normal
settings, without saving a different radio configuration.

Use this command under the user's responsibility. The user must assess whether
the maximum available power is legal in their region and whether they may use
the command.

After the radio completes transmission, the node responds on LegionRF:

```text
Dracarys! Pōntes valar! - Dracarys!, flame them all!
```

`/reboot` uses the normal save/restart path. An active settings transaction,
transfer, blocked recovery or unsafe supply can reject it as busy.

Ignore changes use persistent Meshtastic NodeDB state and include legacy ignore
entries. A reply marked **`in RAM; persistence pending`** is not yet saved.
The first node selector chooses the executor; the second chooses the ignored peer.
The old group forms are not accepted. Ignoring filters packet
origins; it does not stop RF transmissions or silence unrelated traffic forwarded
by that peer. NodeDB ignore flags are outside the rescue snapshot.

### Ignore by name

Use the exact advertised **long name**, including case, regardless of hardware
model. Quote the name if it contains spaces. A Legion can store eight rules of
up to 39 UTF-8 bytes each. The confirmation means the rule was saved to flash.
Use `/unignorename` or its alias `/unignore name` to remove it.

When a decodable NodeInfo announces a matching name, Legion drops the announcement
before it can answer or relay it. It remembers up to 24 matching NodeIDs in RAM
and filters subsequent packets from those origins. A learned ID expires after
one hour of inactivity. After a restart, the saved rules match new announcements
and learn the IDs again. Traffic from a new ID can arrive before its name is known.
Name rules are local to the executing Legion and are outside the rescue snapshot.

### Scramble

Send `/scramble !nodeid | shortname` as a broadcast on **LegionRF**. The node selector chooses the
Legion to silence. On receipt, normal traffic stops. The node can attempt one
`Entering hibernation for Scramble.` notice on LegionRF. The notice has up to
4 seconds to transmit under the usual TX checks. The node then turns off LoRa,
Bluetooth and USB data.

After **60 minutes** from acceptance, the node restarts automatically and
reloads its saved configuration. Once ready, it attempts
`Hibernation ended. Scramble complete.` on LegionRF. Saved permanent arming can restore APC and antispam after startup checks;
otherwise APC starts OFF and antispam starts OBSERVE. A physical reset or loss of power ends the timed
silence early. Normal low-voltage recovery still applies when the node boots.

## Secondary channels

Send `/listchannels !nodeid | shortname` to list the executing
node's enabled configured channels, including the primary and LegionRF:

```text
!abcdef01: 1:SFNarrow, 2:Iberia, 3:Madrid, 4:LegionRF
```

Display positions start at **1** and preserve actual slot positions. Disabled
slots leave gaps; deleting a channel does not renumber the rest. No PSKs are
reported and the query does not change the channels.


`/createch (!nodeid | shortname) <channel> <psk>` uses the first disabled secondary slot
(indices 1–7). The name is limited to 11 UTF-8 bytes; quote spaces as for `/msg`.
The PSK must be canonical standard Base64 decoding to **1, 16 or 32 bytes**,
including the required padding; it is not an arbitrary text password. One-byte
values are Meshtastic short-key aliases. Use your own random 16- or 32-byte key
for a private channel. Existing enabled names are not overwritten, MQTT forwarding
starts disabled, and the new channel is usable without rebooting.

`/deletech (!nodeid | shortname) <channel>` takes no PSK. It requires one matching enabled
secondary channel and clears its slot without renumbering the others. Primary
and LegionRF channels are protected. Names match without ASCII case differences;
ambiguous matches are rejected. A slot used by Mesh Beacon, an active broadcast
or a queued Beacon transmission also prevents a channel edit.

Wait for the saved confirmation. A successful creation/deletion sets **APC OFF**
and can make the manual backup OUTDATED; it never refreshes that backup. Re-enable
APC explicitly and use `/backup replace` only when you want to save the new settings.

## Direct-peer and traceroute reports

`/zerohop` lists current-boot direct RF observations, sorted by descending SNR.
Zero and negative SNR are valid. It is a passive directory, not an active scan or
a guarantee of bidirectional reachability.

Zero-hop and ignore-list pages use a **15-minute frozen snapshot** tied to the
requesting node and channel. Repeating page 1 reuses that snapshot, including an
empty one. Follow the reply's `Next:` command for more pages; a new capture is
created after expiry. Radio changes invalidate the zero-hop capture. Reports
hold up to 128 rows and explicitly mark overflow as `partial`.

`/trace` uses the target's recorded channel, or the primary channel for an unknown
target. A successful result contains `1/2 out` and `2/2 back`; paths can differ.
Results use full IDs and `?` for unreported hops. `0 reported relays` describes
reported metadata. Routing `NO_ROUTE` is reported as unreachable; no response
within 90 seconds is **`reachability unknown`**. Radio/channel changes cancel
stale results. Other commands remain available while a trace waits.

## Telemetry fields

Illustrative reply:

```text
2.8.3.Legion0.7.2 !abcdef01 up:194400s
CPU:29.25 / max 34.50C BAT:82% 4.01 / min 3.96V
N:-116 peak:-88dBm n:600
RX:450 BAD:7 TX:32 REL:24 DROP:2
```

| Field | Meaning |
| --- | --- |
| `up` | Seconds since boot. |
| `CPU / max` | Current and maximum sampled chip temperature, not ambient temperature. |
| `BAT` | Estimated percentage, physical battery voltage and observed minimum. |
| `N / peak / n` | Mean/peak sampled RF noise RSSI and sample count. |
| `RX / BAD` | Successful and bad-reception counters; BAD is not exclusively CRC failures. |
| `TX / REL` | Transmissions and relays; REL is a subset of TX. |
| `DROP` | Dropped-transmission counter. |

Values accumulate in RAM and reset on reboot. Battery voltage uses the physical
RAK19007 divider independently of the app's ADC multiplier. Noise sampling uses
the current frequency without retuning. This detailed report is on demand;
the [DAILY](#daily) and normal Meshtastic telemetry settings
remain separate.

## Boot fields

| Field | Meaning |
| --- | --- |
| `reset` | Cached hardware reset reason and full mask; absent evidence stays unknown. |
| `prev` | Recorded previous protective stop, including low battery, low VDD, `cpu-thermal` and `scramble`. |
| `VBAT / VDD` | First physical voltage samples at boot, in millivolts; not live fault voltages. |
| `USB` | Node VBUS detection at that boot sample; external solar charging can still show zero. |

The report adds no flash writes. `NA` means unavailable.

## Component fields

`/components !nodeid | shortname` is read-only; it does not reinitialize a component or save settings.
CC310, bulk SPI and REG1 DC/DC operate automatically. See
[Automatic features](AUTOMATIC-FEATURES.md) for their purpose and the separate
flash-persistence behavior. The command also reports preference-save counters.

| Field | Meaning |
| --- | --- |
| `CC310 SHA / MAC` | Successful hardware SHA-256 and ACK-proof HMAC operations since boot. |
| `SW` | Failed accelerator attempts followed by software calculation. |
| `SPI` | Radio SPI availability and configured frequency, or `NA` when unavailable. |
| `BULK` | Whether bulk radio SPI transfers are enabled in the build. |
| `DC/DC ... REG1` | Current enabled/disabled state of the MCU's REG1 DC/DC regulator. |
| `SAVE C / U / S / F` | Preference saves checked / identical saves skipped / completed saves / failed attempts, since boot. |

CC310 and SAVE counts reset on reboot; a zero MAC count can be normal. The configured SPI
frequency is not a frequency measurement, and these fields do not measure energy savings.
