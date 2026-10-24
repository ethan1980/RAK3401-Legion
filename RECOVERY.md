# Manual rescue backup

[Overview](README.md) · [Commands](COMMANDS.md) · [APC](APC.md)

Legion can save one rescue point and restore it after confirmed loss or corruption
of essential preferences. **Backup creation and replacement are always explicit.**
Installing firmware, restarting or changing settings never refreshes it.

## Commands

Send these channel messages on the configured private **LegionRF** channel.
Replace the example with the destination's full node ID; only that Legion acts.

| Message | Result |
| --- | --- |
| `/backup !abcdef01` | Creates a rescue point if absent. |
| `/backup status !abcdef01` | Reports validity and whether the saved settings are current. |
| `/backup replace !abcdef01` | Replaces the rescue point with current settings. |
| `/backup delete !abcdef01` | Persistently disables recovery from that rescue point. |

Telemetry and backup share a **60-second cooldown**. Wait for **`saved and
verified; recovery armed`** or **`deleted; recovery disabled`**: a delivery icon
alone does not confirm persistence. Creation never silently overwrites a rescue
point; replacement is explicit and avoids a new write if unchanged.

## Saved settings

The rescue point contains names, this node's private identity and coherent public
key/Node ID, channel keys, device/radio settings, module settings and fixed-position
configuration. It excludes peer databases, conversations, dynamic GPS history,
session counters, queued messages and BLE bonding. Licensed/Ham and “cannot be
messaged” owner flags are excluded and use their normal defaults on restoration.

Keys remain on the device and are never included in status replies. The rescue
record is integrity-protected local flash, **not encrypted secret storage**.
Deletion disables recovery; it is not a forensic secure erase.

## Backup freshness

`/backup status` is read-only. It compares the settings captured by a valid rescue
point with the current configuration without replacing it.

| Status | Meaning |
| --- | --- |
| `up to date; recovery armed` | Captured settings match. |
| `OUTDATED: owner,channels; recovery armed` | Named blocks differ; the saved rescue point remains usable. |
| `freshness unavailable` | A reliable comparison is currently unavailable. |
| `no rescue point; recovery disabled` | No active rescue point exists. |
| `rescue point invalid or incompatible` | The record cannot be used. |

Changed blocks are `owner`, `config`, `modules`, `channels` and `position`.
Replies contain block names, not settings or keys. Runtime fields and dynamic
GPS updates do not make the snapshot stale. An active settings edit, pending
restart or unavailable fixed-position data can prevent comparison. To save
intentional changes, use `/backup replace` explicitly.

## Restoration behavior

At boot, a valid, device-bound rescue point can restore consistently missing or
corrupt essential owner, channel, configuration or module files. Healthy current
preferences remain authoritative, even when different from the saved snapshot.
Normal restarts, name changes and application updates do not trigger restoration.

Restoration verifies the saved settings before normal operation resumes. An
incomplete recovery holds the radio silent and has a bounded retry limit.
Intentional identity-key rotation or licensed mode disables the old rescue point.

**Factory reset restores an armed rescue point.** To deliberately return to blank
settings, send `/backup delete !abcdef01`, wait for its deletion confirmation,
then request factory reset.

After successful recovery, Legion queues this notice on the restored private
LegionRF channel:

> Ashes to ashes, dust to dust, the node [node_name] has risen again

It is not sent for ordinary boots or firmware updates. Notification failure does
not undo recovery; queue acceptance does not guarantee another node received it.

Two alternate flash generations at **0xE8000–0xEA000**, outside LittleFS, hold the
rescue record. Compatible application-only Legion updates preserve that reserve.
A full-chip erase, incompatible firmware or flash failure can destroy it.

## Low-energy sleep and wake

Separate from rescue backup, Legion's power policy protects the battery and MCU
supply automatically. Eight battery readings below **3.50 V**, spaced 20 seconds
apart, trigger energy sleep; VDD and TX protections remain independent. Reception
and forwarding stop during sleep and resume after voltage recovery. Node USB
power bypasses the battery threshold for servicing. A deliberate app shutdown
does not arm automatic battery-voltage wake. APC does not replace this policy.

## Hardware status

Backup commands and manual restoration were tested on earlier Legion builds.
The alpha's freshness feature is partially tested. Recovery-notice reception
and physical interrupted-write recovery are not yet hardware-validated.
