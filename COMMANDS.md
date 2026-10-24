# Legion commands

[Overview](README.md) · [Rescue backup](RECOVERY.md) · [Energy recovery](ENERGY-RECOVERY.md) · [APC](APC.md)

These commands are available in **Legion 0.6.0-alpha.1**. The requesting node and
phone app can use standard Meshtastic. Hardware validation is partial; see the
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
ID of the Legion that should act. For ignore commands, the ID instead selects
**the peer to ignore**, and every receiving Legion acts independently.

## Command reference

| Message | Result |
| --- | --- |
| `/telemetry` | Reachable Legion nodes report telemetry. |
| `/telemetry !abcdef01` | Only the selected Legion reports telemetry. |
| `/msg !abcdef01 SFNarrow Hello` | The selected Legion broadcasts text on its named channel. |
| `/reboot !abcdef01` | Schedules a normal restart 20 seconds after acceptance. |
| `/zerohop !abcdef01 [page]` | Lists direct RF peers, short names and SNR. |
| `/ignore !12345678` | Each receiving Legion ignores that peer. |
| `/unignore !12345678` | Each receiving Legion removes that peer from its effective ignore list. |
| `/ignorelist [page]` | Each receiving Legion reports its own ignore list. |
| `/trace !abcdef01 !12345678` | The selected Legion traces the second node and returns both paths. |
| `/boot !abcdef01` | Reports boot evidence and CC310 counters. |
| `/backup !abcdef01` | Creates a rescue point if none exists. |
| `/backup status !abcdef01` | Reports rescue validity and freshness. |
| `/backup replace !abcdef01` | Explicitly refreshes the rescue point. |
| `/backup delete !abcdef01` | Deletes the rescue point and disables its recovery. |
| `/apc observe\|shadow\|on\|off !abcdef01` | Selects an [Adaptive Power Control mode](APC.md). |
| `/apc status !abcdef01 [page]` | Reports APC status, pages 1–6. |

Square brackets denote optional arguments; do not type them. `/ignorelist` takes
an optional page, **not an executor ID**. Backup details are in [RECOVERY.md](RECOVERY.md).

## Timing and replies

| Command family | Timing |
| --- | --- |
| Remote tools and APC | Shared five-second cooldown after processing; allow at least six seconds after a reply. |
| Telemetry and backup | Shared 60-second cooldown after a response attempt. |
| Traceroute | One active trace, at least 60 seconds between starts, up to 90 seconds for a result. |

Normal radio scheduling adds delay. Requests during cooldown may receive no reply.
Replies identify the executing Legion and are copied to its connected app.
A `queued` response means local queue acceptance, not delivery to another node.
Channel/key changes or insufficient power can cancel a pending operation.

## Messages, restarts and ignored nodes

For `/msg`, use an enabled channel name on the executing Legion. Quote names
containing spaces, for example `/msg !abcdef01 "My channel" Hello`. The complete
command must fit the normal 199-byte text limit; channel names are limited to
11 bytes. There is no fallback to another channel or automatic command resend.

`/reboot` uses the normal save/restart path. An active settings transaction,
transfer, blocked recovery or unsafe supply can reject it as busy.

Ignore changes use persistent Meshtastic NodeDB state and include legacy ignore
entries. A reply marked **`in RAM; persistence pending`** is not yet saved. Nodes
that miss a group command do not catch up automatically. Ignoring filters packet
origins; it does not stop RF transmissions or silence unrelated traffic forwarded
by that peer. NodeDB ignore flags are outside the rescue snapshot.

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
2.8.2.LGN0.6.0a1 !abcdef01 up:194400s
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
the current frequency without retuning. There are no automatic diagnostic
broadcasts; normal Meshtastic telemetry settings remain separate.

## Boot fields

| Field | Meaning |
| --- | --- |
| `reset` | Cached hardware reset reason and full mask; absent evidence stays unknown. |
| `prev` | Recorded previous protective stop, such as low battery or low VDD; not a complete reset history. |
| `VBAT / VDD` | First physical voltage samples at boot, in millivolts; not live fault voltages. |
| `USB` | Node VBUS detection at that boot sample; external solar charging can still show zero. |
| `CC310 SHA / MAC` | Successful hardware SHA-256 and ACK-proof HMAC operations since boot. |
| `SW` | Failed accelerator attempts followed by software calculation. |

The report adds no flash writes. CC310 counts reset on reboot; a zero MAC count
can be normal, and counters do not measure energy savings. `NA` means unavailable.
