# Legion 0.6.0 planning

Status: **0.6.0-alpha.1**, published for controlled hardware testing on
2026-10-24. APC S1, backup freshness, remote traceroute, CC310 packet hashing
and boot diagnostics are integrated. Adaptive RF-power selection is not
implemented. Physical validation of the combined alpha is in progress. OTA using
nRF Connect, ordinary and remote `/msg` messaging, direct/relayed traceroute,
timeout reporting, live CC310 counters,
normal restart and the owner-freshness sequence are recorded in
[ALPHA-TESTING.md](ALPHA-TESTING.md#hardware-record--2026-10-24).

The operator authorized alpha publication before installing it on the node.
Hardware/RF validation follows publication and remains required before a stable
recommendation. Historical 0.4.x/0.5.x hardware results are not alpha results.
See [ALPHA-TESTING.md](ALPHA-TESTING.md) for the next test sequence.

## Upstream base migration — completed for this alpha

- Replaced `04cb8885118b959a9f538cd5881bd7d595758911` with
  `e039e34171e697e36d4f1b66eedfb683ffffe4f5` (Meshtastic 2.8.2 develop).
- Reviewed the additional commit after `0d3da2d`: upstream's BLE OTA reset fix.
  Preserve it in the reference profile. Legion retains its direct ATT
  authorization and main-loop handoff, including the attribute-update contract.
- Refresh energy/radio and DFU patch context. Exact preparation, both profiles,
  host regression and compiled update checks gate alpha publication.
- Preserve O1.1 measurements under their original base. Collect a new OBSERVE
  reference on the migrated base before attributing changes to APC decisions.

## APC — existing workstream

- Initial O1.1 observation completed: 73 h 25 min, with 20,422 completed TXs.
  Preserve the original record and its mixed charging timeline.
- Alpha S1: OFF / OBSERVE / SHADOW / ON commands, provisional filtered-voltage
  NORMAL / CONSERVE / RESERVE states, fresh-evidence checks, hysteresis and
  persistence, optional position/telemetry relay admission budgets and status.
- Keep protected and opaque traffic, normal CLIENT behavior, reception and RF
  output unchanged. OFF is the boot default; candidate mode state is RAM-only.
- Initial and controlled post-restart reports show OFF and nominal RF. Follow
  [APC.md](APC.md) and the alpha test sequence: 24 hours of passive OBSERVE,
  24 hours of SHADOW, then a supervised 30–60-minute ON trial before extending
  the run. Review each stage on the migrated base, separately from upstream effects.
- The operator reports OBSERVE activated; its initial six-page capture and
  continuous 24-hour results remain awaited. This stage is in progress.
- Adaptive RF-power selection remains pending known-receiver testing and
  implementation; S1 keeps nominal output. Thresholds, budgets and final boot
  persistence policy remain provisional. Hardware/RF tests are still required.

## Stale-backup detection — owner case observed, remaining hardware cases pending

- Extend the backup status query to distinguish a valid rescue point that
  matches current backed-up settings from a valid but outdated rescue point.
- Identify which backed-up blocks changed: owner identity, radio/configuration,
  module settings, channels, or fixed position.
- Report block names only; do not expose keys or configuration values.
- Preserve existing validity, compatibility and device-identity checks.
  A freshness difference does not itself disable an otherwise valid rescue point.
- Keep the query read-only, with no automatic replacement or flash writes.
  Updating the rescue point remains an explicit
  `/backup replace !xxxxxxxx` operation.
- Compare protobuf contents rather than structure padding, ignoring internal
  version markers and owner fields excluded from the snapshot. Compare only
  fixed-position mode/coordinates, not dynamic GPS updates or timestamps.
- Report freshness as unavailable during configuration edits, a pending reboot,
  missing fixed-position data or an invalid/unencodable current configuration.
- Host integration tests cover matching, individual/all changed blocks, absent,
  invalid and unavailable cases, read-only behavior and recovery from an older
  valid snapshot. Alpha RF captures now show `up to date` → `OUTDATED: owner`
  → `up to date`, with the valid rescue point armed throughout. Other blocks,
  unavailable comparisons and rescue write/restoration operations remain pending.

## Remote traceroute — direct, relayed and timeout cases observed

- Add `/trace !legionid !targetid` on the private LegionRF channel.
- The selected Legion originates a standard Meshtastic traceroute; the target
  does not need Legion firmware. Use its recorded channel, or the primary
  channel for an unknown target, without changing radio settings.
- Wait asynchronously for up to 90 seconds. Keep other commands available,
  allow one active trace per Legion, and leave at least 60 seconds between starts.
- Return the outbound and return paths separately, with full node IDs and `?`
  for unreported hops. Space the two result messages by at least six seconds.
- Correlate the exact request ID, target, destination and channel; reject late,
  duplicate and unrelated replies. Revalidate channel keys and radio generation.
- Distinguish routing `NO_ROUTE` from an expired wait or missing acknowledgement:
  silence alone does not establish that the destination is unreachable.
- Use standard routing reliability without adding a command retry loop or
  persistent writes. Alpha captures show both direct paths, asymmetric relayed
  paths (two outbound intermediates, one return intermediate) and a 90-second
  timeout with unknown reachability. Explicit `NO_ROUTE`, other-command
  responsiveness while waiting and extended RF cases remain pending.

## CC310 packet hashing — included in alpha, hardware measurements pending

- Use the nRF52840 CC310 for packet SHA-256 and ACK-proof HMAC-SHA256.
- Retain standard Meshtastic digests, proofs and key formats; fall back to the
  existing software calculation after any accelerator initialization/SDK error.
- Stage input through aligned RAM and respect the SDK's final-partial-block
  rule. Serialize sessions with existing AES, asymmetric crypto, RNG and optional
  encrypted-storage users; support nested sessions on the same task.
- Expose successful SHA/MAC and software-fallback attempt counts in `/boot`.
- Alpha counters advance from SHA/MAC/SW `3/3/0` to `4/19/0` during normal use;
  the deliberate restart begins new counts at `3/2/0`. Hardware activity and no
  observed fallback are established for this run, without per-operation timing.
- Compare against independent reference digests, exercise SDK failures and
  concurrent callers, and compile both Legion and the baseline profile.
- Measure real CC310 execution and energy use before claiming a performance or
  battery gain. Initialization and buffer-copy cost matter for short inputs;
  forwarding opaque packets does not inherently perform these operations.

## Boot diagnostics — normal software restart observed, other causes pending

- Add read-only `/boot !legionid` on the private LegionRF channel.
- Report the core-cached reset mask, a readable interpretation, the previous
  recorded protective shutdown, and the first battery/VDD/USB boot sample.
- Record shutdown intent in owned GPREGRET2 high-nibble values, preserving the
  low nibble and foreign markers. Keep Adafruit's GPREGRET/DFU values intact.
- Use no flash writes or automatic announcements. Missing reset/shutdown
  evidence stays unknown; a sudden battery disconnect is not diagnosed by guess.
- The alpha's `/reboot` acknowledgement is followed by a software-reset boot
  report, new first-voltage samples, reset CC310 counters and APC OFF. Exact
  latency and all retained settings were not independently measured.
- Validate watchdog, protective System OFF/wake and ordinary power cycles on
  the actual RAK after APC data collection is complete.

Version policy: feature releases advance the minor version (0.5.x to 0.6.0);
small changes and fixes advance the patch version (0.5.0 to 0.5.1).
