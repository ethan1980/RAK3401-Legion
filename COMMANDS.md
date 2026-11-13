# Legion commands

[Overview](README.md) · [Automatic features](AUTOMATIC-FEATURES.md) · [Rescue backup](RECOVERY.md) · [Energy recovery](ENERGY-RECOVERY.md) · [APC](APC.md) · [Antispam](ANTISPAM.md)

These commands are available in **Legion 0.7.0**. The requesting node and
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
Commands are lowercase. Replace `!abcdef01` with the full eight-digit hexadecimal
ID of the Legion that should act. The ID-based forms of ignore and unignore take
a second full ID for **the peer to ignore**. Only the selected Legion changes its list.

## Command reference

| Message | Result |
| --- | --- |
| `/telemetry` | Reachable Legion nodes report telemetry. |
| `/telemetry !abcdef01` | Only the selected Legion reports telemetry. |
| `/msg !abcdef01 SFNarrow Hello` | The selected Legion broadcasts text on its named channel. |
| `/reboot !abcdef01` | Schedules a normal restart 20 seconds after acceptance. |
| `/zerohop !abcdef01 [page]` | Lists direct RF peers, short names and SNR. |
| `/ignore !abcdef01 !12345678` | The selected Legion ignores the second node. |
| `/unignore !abcdef01 !12345678` | The selected Legion removes the second node from its effective ignore list. |
| `/ignorelist !abcdef01 [page]` | The selected Legion reports its own ignore list. |
| `/ignore name !abcdef01 "Long name"` | Saves an exact long-name rule on the selected Legion. |
| `/unignorename !abcdef01 "Long name"` | Removes that name rule. |
| `/ignorelist names !abcdef01 [page]` | Lists the name rules with their last seen IDs and drop counters. |
| `/trace !abcdef01 !12345678` | The selected Legion traces the second node and returns both paths. |
| `/boot !abcdef01` | Reports boot evidence and first boot voltages. |
| `/components !abcdef01` | Reports CC310 counters, radio SPI and REG1 DC/DC. |
| `/createch !abcdef01 name psk` | Creates a secondary channel in the first available slot using a Base64 PSK. |
| `/deletech !abcdef01 name` | Deletes the uniquely named secondary channel. |
| `/backup !abcdef01` | Creates a rescue point if none exists. |
| `/backup status !abcdef01` | Reports rescue validity and freshness. |
| `/backup replace !abcdef01` | Explicitly refreshes the rescue point. |
| `/backup delete !abcdef01` | Deletes the rescue point and disables its recovery. |
| `/apc observe\|shadow\|on\|off !abcdef01` | Selects an [Adaptive Power Control mode](APC.md). |
| `/arm !abcdef01` | Enables APC S1+S2 and antispam together on the selected node. |
| `/disarm !abcdef01` | Turns APC and antispam OFF together on the selected node. |
| `/guard status !abcdef01` | Reports antispam mode, quarantines and counters. |
| `/guard observe\|on\|off !abcdef01` | Selects the RAM-only antispam mode. |
| `/guard clear !abcdef01 !12345678` | Clears temporary antispam evidence; manual ignores remain. |
| `/spamlist !abcdef01 [page]` | Lists temporary quarantines; see [Antispam](ANTISPAM.md). |
| `/scramble !abcdef01` | Silences the selected Legion for 60 minutes, then restarts it. |
| `/apc status !abcdef01 [page]` | Reports APC status, pages 1–7. |

Square brackets denote optional arguments; do not type them. `/ignorelist` requires
the executor ID before its optional page. Backup details are in [RECOVERY.md](RECOVERY.md).

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

Reports over 199 bytes use `DAILY 1/2` for APC, SPAM, BACKUP and BAT, and
`DAILY 2/2` for MeshHealth. Both parts share the same cut and node ID.

## Arm and disarm

Send `/arm !abcdef01` on LegionRF to enable APC S1+S2 and antispam on one
Legion. APC requires CLIENT and follows its usual warmup. If activation
requirements fail, the request leaves both modes as they were.

Send `/disarm !abcdef01` to turn both OFF and clear temporary spam evidence.
These modes live in RAM. APC starts OFF and antispam starts OBSERVE at boot.

| Command | Confirmation |
| --- | --- |
| `/arm !abcdef01` | `!abcdef01: APC ON (S1+S2). SPAM ON.` |
| `/disarm !abcdef01` | `!abcdef01: APC OFF. SPAM OFF.` |

## Messages, restarts and ignored nodes

For `/msg`, use an enabled channel name on the executing Legion. Quote names
containing spaces, for example `/msg !abcdef01 "My channel" Hello`. The complete
command must fit the normal 199-byte text limit; channel names are limited to
11 bytes. There is no fallback to another channel or automatic command resend.

`/reboot` uses the normal save/restart path. An active settings transaction,
transfer, blocked recovery or unsafe supply can reject it as busy.

Ignore changes use persistent Meshtastic NodeDB state and include legacy ignore
entries. A reply marked **`in RAM; persistence pending`** is not yet saved.
The first ID always selects the executor; the second selects the ignored peer.
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

Send `/scramble !abcdef01` as a broadcast on **LegionRF**. The ID selects the
Legion to silence. On receipt, normal traffic stops. The node can attempt one
`Entering hibernation for Scramble.` notice on LegionRF. The notice has up to
4 seconds to transmit under the usual TX checks. The node then turns off LoRa,
Bluetooth and USB data.

After **60 minutes** from acceptance, the node restarts automatically and
reloads its saved configuration. Once ready, it attempts
`Hibernation ended. Scramble complete.` on LegionRF. APC starts OFF and
antispam starts OBSERVE. A physical reset or loss of power ends the timed
silence early. Normal low-voltage recovery still applies when the node boots.

### Secondary channels

`/createch !abcdef01 "My channel" <psk>` uses the first disabled secondary slot
(indices 1–7). The name is limited to 11 UTF-8 bytes; quote spaces as for `/msg`.
The PSK must be canonical standard Base64 decoding to **1, 16 or 32 bytes**,
including the required padding; it is not an arbitrary text password. One-byte
values are Meshtastic short-key aliases. Use your own random 16- or 32-byte key
for a private channel. Existing enabled names are not overwritten, MQTT forwarding
starts disabled, and the new channel is usable without rebooting.

`/deletech !abcdef01 "My channel"` takes no PSK. It requires one matching enabled
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
2.8.2.Legion0.6.1 !abcdef01 up:194400s
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

`/components !abcdef01` is read-only; it does not reinitialize a component or save settings.
CC310, bulk SPI and REG1 DC/DC operate automatically. See
[Automatic features](AUTOMATIC-FEATURES.md) for their purpose and the separate
flash-persistence behavior. The command reports CC310, SPI and REG1 status only.

| Field | Meaning |
| --- | --- |
| `CC310 SHA / MAC` | Successful hardware SHA-256 and ACK-proof HMAC operations since boot. |
| `SW` | Failed accelerator attempts followed by software calculation. |
| `SPI` | Radio SPI availability and configured frequency, or `NA` when unavailable. |
| `BULK` | Whether bulk radio SPI transfers are enabled in the build. |
| `DC/DC ... REG1` | Current enabled/disabled state of the MCU's REG1 DC/DC regulator. |

CC310 counts reset on reboot; a zero MAC count can be normal. The configured SPI
frequency is not a frequency measurement, and these fields do not measure energy savings.
