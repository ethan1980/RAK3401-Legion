# Legion antispam

[Commands](COMMANDS.md) · [APC](APC.md)

Boot mode is **OBSERVE**. This models decisions and simulated quarantines while
allowing traffic. **ON** must be selected explicitly and enforces the same
policy. **OFF** bypasses detection. Mode changes clear evidence, not counters;
selecting the current mode again preserves evidence. Everything is RAM-only.

Send these commands as broadcasts on your existing private secondary **LegionRF**
channel, replacing `!abcdef01` with the full ID of the executing Legion:

| Command | Result |
| --- | --- |
| `/guard status !abcdef01` | Mode, active or simulated quarantines, and counters. Read-only. |
| `/guard observe !abcdef01` | Model the detector without blocking. |
| `/guard on !abcdef01` | Enforce detection and quarantine. |
| `/guard off !abcdef01` | Stop detection and clear temporary evidence. |
| `/arm !abcdef01` / `/disarm !abcdef01` | Enable or disable antispam together with APC. |
| `/guard clear !abcdef01 !12345678` | Clear temporary evidence for that peer in both identity domains. Manual ignore remains unchanged. |
| `/spamlist !abcdef01 [page]` | Snapshot of quarantines, signed/unsigned identity, cause and seconds remaining. Request page 1 first. |

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
removed on release. No persistent settings, NodeDB ignore flag or backup is
written by this feature.

[DAILY](COMMANDS.md#daily) reports antispam alongside the other 24-hour fields. For example:

```text
!abcdef01 DAILY
APC:ON CONSERVE
SPAM:ON Q:1
BACKUP:UP TO DATE
```

OBSERVE uses `SPAM:OBSERVE simQ:1` so a modeled quarantine is never presented as
an enforced block. Status and DAILY do not reset evidence or APC report captures.

The 0.6.5 candidate was installed and new control commands tested on hardware.
The final action-first `/guard` syntax was checked by software tests after the field test.
RF range, consumption and measured energy savings remain unverified.
