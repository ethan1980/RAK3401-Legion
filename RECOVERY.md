# Manual rescue backup — Legion 0.4.2

Legion can save one rescue point on the configured node and restore it if a
later boot confirms missing or corrupt essential preferences. **Nothing is
backed up automatically.** Installing firmware, restarting, changing settings or
updating firmware does not create or refresh a rescue point.

## Create the rescue point

Configure and check the node first. Use the existing private **LegionRF**
secondary channel and its own 16- or 32-byte PSK as described in [COMMANDS.md](COMMANDS.md).
Possession of that configured channel authorizes these commands;
there is no additional password or administrator allowlist.

Replace `!abcdef01` with the destination node's complete eight-digit hexadecimal ID:

| Message | Result |
| --- | --- |
| `/backup !abcdef01` | Create a rescue point if none exists. |
| `/backup status !abcdef01` | Check whether a valid rescue point exists. |
| `/backup replace !abcdef01` | Explicitly replace it with the current settings. |
| `/backup delete !abcdef01` | Persistently disable recovery from that rescue point. |

The destination is mandatory. Only the matching node acts and replies, even
when several Legion nodes share the channel. Send a channel broadcast, not a
direct message. Commands are lowercase; hexadecimal IDs accept either case.
The same commands work from the app connected to the target itself.

Wait for the node's **`saved and verified; recovery armed`** response. A delivery
icon or radio ACK alone does not confirm a backup. Plain `/backup` never silently
overwrites an existing rescue point. After changes, use `replace` explicitly.
An unchanged replacement avoids another flash write.

Backup commands and telemetry share one pending request, a 60-second cooldown
and the existing duplicate-request cache. Wait at least a minute between commands.
Changing the private channel while a command waits cancels it. An open settings
transaction, pending reboot, unsupported storage mode or unsafe power prevents
creation/replacement. Normal LoRa airtime and power limits apply.

## What is saved

- Long and short names.
- Channels and their private keys, equivalent to the configuration Channel URL.
- Device/radio configuration and module configuration.
- This node's private identity key and coherent public key/Node ID.
- Fixed-position mode and configured latitude, longitude and altitude.

The licensed/Ham and “cannot be messaged” owner flags are excluded and use their
normal defaults after restoration. Peer-node databases, conversations, dynamic
GPS history, telemetry history, session counters and queued messages are excluded.
An existing peer database is retained when readable; it is not part of the backup.

Keys are captured locally after installation. Replies never contain private keys,
channel keys or backup contents. They are not compiled into release images or
uploaded to GitHub. The reserve contains sensitive data in local flash;
it is an integrity-protected rescue record, not encrypted secret storage.
Deletion commits a durable tombstone and disables recovery; it is not a forensic
secure erase of every historical flash cell. A full-device flash dump can contain it.

## When recovery runs

At boot, before normal preference loading or identity generation, Legion checks
for an explicitly saved, valid, hardware-bound snapshot. A healthy configuration
remains authoritative even when it differs from that snapshot.

Recovery requires consistent evidence of missing/corrupt essential config,
module, channel or owner files, or a committed restoration in progress.
It does not use uptime, reboot reason, silence on the mesh or default-looking
settings as evidence. Temporary read failures and unsupported preference versions
do not authorize an overwrite. Losing only peer history or position history does
not trigger a complete restoration.

Normal restart, name-change restart, battery-switch power-off/on and application
firmware updates with intact preferences do not restore the rescue point or send an announcement.
If an event actually destroys essential preferences, that damage can trigger recovery.

Restoration writes and verifies the essential files before normal boot continues.
It reconstructs identity from the saved private key, restores fixed position and
persists completion before enabling the recovery notice. A power cut during the
transaction causes a later boot to resume it rather than accept a mixed configuration.
At most three restore attempts are persisted. An incomplete/blocked restoration
holds the radio silent and prevents preference saves.
Repeated hardware/storage failure needs operator diagnosis rather than an endless
erase/reboot loop. No autonomous reboot loop is introduced.

An intentional key rotation or entering licensed mode disables the old rescue
point before the change; create a fresh compatible rescue point afterward.
This avoids restoring an intentionally retired identity.

## Factory reset

With a valid rescue point, a normal application factory-reset request schedules
restoration of that rescue point on reboot. It does not erase the rescue point.
To deliberately return to blank settings, first send `/backup delete !abcdef01`
and wait for **`deleted; recovery disabled`**, then request factory reset.
The delete confirmation must precede the reset. A normal restart is different.

## Recovery notice

After a completed recovery, the normal radio queue sends this text to the restored
private LegionRF channel:

> Ashes to ashes, dust to dust, the node [node_name] has risen again

The restored long name replaces `[node_name]`; short name and Node ID are fallbacks.
The notice is never sent for an ordinary boot, firmware update, backup creation or failed restore.
It never falls back to a public channel. If the private channel/key changes, it
does not send into that replacement channel.

Pending/attempted/sent state survives reboot independently of the manually saved
configuration. There are at most three persisted queue attempts, at least a minute
apart while running. Queue acceptance is not proof of RF reception. A power cut
between queueing and persisting its result can cause a duplicate; exactly-once
delivery across arbitrary power cuts is not promised. Notification failure does
not invalidate a successful recovery or trigger another restoration.

## Storage and updates

Two 4096-byte raw-flash pages at **0xE8000–0xEA000** hold alternate complete
generations, including integrity checks and transaction state. They are outside
LittleFS (0xED000–0xF4000) and do not take the warm-node region
(0xEA000–0xED000). The Legion linker caps the application at 0xE8000.
The two-page record keeps the previous valid generation during a torn write.

Packaging rejects application images that overlap the rescue reserve and checks
that all firmware packages describe the same application. Normal Legion firmware
updates that respect this boundary preserve the reserve. A full chip erase,
incompatible firmware or failed flash hardware can destroy it.
Encrypted-storage lockdown and event-profile builds do not create/use this rescue
format. BLE bonding is separate and is not restored by the LoRa identity snapshot.

## Validation status

Host tests exercise the actual journal/parser/recovery runner, including every
32-bit interrupted-write boundary, committed deletion, unsupported schemas,
normal boot, transient reads, partial restores and persisted retry limits.
An integration test compiles the actual recovery engine with the real generated
Meshtastic messages and nanopb, simulated storage, and an OpenSSL X25519 oracle.
It checks identity/settings/position serialization, preflight, restoration, notices,
replacement, deletion, v26 migration markers and temporary/unsupported reads.
The telemetry transport is tested against simulated channels. Build/package gates
check application boundaries and file integrity.
These checks do not substitute for physical power-cut or RF-delivery tests.

On 0.4.2, telemetry responses and formatting and all backup commands—creation
with its success confirmation, status, replacement and deletion—have been verified
on hardware. Automatic emergency restoration from a saved backup, the recovery
announcement and physical power-cut recovery remain pending hardware verification.
No rescue point is armed until an explicit backup command succeeds.
