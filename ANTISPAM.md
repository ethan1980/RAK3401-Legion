# Legion antispam

[Commands](COMMANDS.md) · [APC](APC.md)

Boot defaults to **OBSERVE** unless saved permanent arming restores ON after startup checks. This models decisions and simulated quarantines while
allowing traffic. **ON** enforces the same
policy. **OFF** bypasses detection. Mode changes clear evidence, not counters;
selecting the current mode again preserves evidence. Evidence, counters and quarantines are RAM-only. The separate permanent-arm preference persists.

Send these commands as broadcasts on your existing private secondary **LegionRF**
channel, replacing `!abcdef01` with the full ID or short name of the executing Legion:

| Command | Result |
| --- | --- |
| `/guard status !nodeid \| shortname` | Mode, active or simulated quarantines, and counters. Read-only. |
| `/guard observe !nodeid \| shortname` | Model the detector without blocking. |
| `/guard on !nodeid \| shortname` | Enforce detection and quarantine. |
| `/guard off !nodeid \| shortname` | Stop detection and clear temporary evidence. |
| `/arm !nodeid \| shortname` / `/disarm !nodeid \| shortname` | Enable or disable both and clear saved permanent arming. |
| `/arm permanent !nodeid \| shortname` | Enable both and save automatic arming across restarts. |
| `/guard clear (!nodeid \| shortname) (!peerid \| shortname)` | Clear temporary evidence for that peer in both identity domains. Manual ignore remains unchanged. |
| `/spamlist (!nodeid \| shortname) [page]` | Snapshot of quarantines, signed/unsigned identity, cause and seconds remaining. Request page 1 first. |

These commands share the existing five-second remote-control cooldown and channel
validation. They do not create a second control key or modify `/ignore` lists.

Only **PRIMARY broadcast text** received over LoRa is eligible, including
compressed text. Local-origin messages, direct messages, secondary-channel text,
LegionRF, telemetry, NodeInfo, routing and admin are outside this detector.

Each origin has eight initial tokens and recovers one every five seconds. A new
packet without a token is suppressed in ON. Four such excesses in twenty seconds,
or six identical texts with different packet IDs in twenty seconds, produce a
**ten-minute fixed quarantine**. Copies of an already seen ID do not add tokens,
excesses or repetition evidence. Spam during quarantine does not extend expiry.
After expiry, the origin starts with two tokens. Explicit clear restores eight.

Verified signed identity is bound to the full authoritative public key. Unsigned
traffic with the same node ID has separate evidence; it cannot quarantine that
signed identity. Unsigned node IDs still have the normal channel-PSK spoofing
limits. A fresh sender is admitted when detector storage is full; existing
quarantines are not evicted. Limits: twelve detector origins, twelve recent IDs
per origin and eight quarantines. A primary-channel, radio-generation or role
change clears evidence and disarms the detector to OFF.

The receive gate precedes chat/module/MQTT dispatch. Duplicate forwarding and
already encrypted queued packets also check quarantine; queued metadata is
removed on release. The detector writes no NodeDB ignore flag or backup. Only explicit permanent
arming writes the separate startup preference; see [arming](COMMANDS.md#arm-and-disarm).

[DAILY](COMMANDS.md#daily) reports antispam alongside the other 24-hour fields. For example:

```text
!abcdef01 DAILY
APC:ON CONSERVE
SPAM:ON Q:1
BACKUP:UP TO DATE
```

OBSERVE uses `SPAM:OBSERVE simQ:1` so a modeled quarantine is never presented as
an enforced block. Status and DAILY do not reset evidence or APC report captures.

The owner confirmed commands and modes tested on HW with Legion 0.7.1,
including the action-first `/guard` syntax.
Permanent arming and short-name selectors in 0.7.2 are tested on HW.
RF range, consumption and measured energy savings remain unverified.
