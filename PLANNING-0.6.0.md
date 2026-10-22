# Legion 0.6.0 planning

Status: in development. APC observation is in progress; stale-backup detection
and remote traceroute are approved additions. The released firmware remains 0.5.1.

Previous documentation and battery-confirmation items moved to 0.5.1.

## APC — existing workstream

- Continue passive observation with the local experimental firmware.
- Use the observations to develop and validate battery conservation
  (NORMAL / CONSERVE / RESERVE) and adaptive transmit-power behavior.
- Select thresholds and actions after reviewing the measurements and the
  required reception tests. Observation builds remain separate from a release.

## Stale-backup detection — approved, pending implementation

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
- Validate matching, changed, absent and invalid rescue-point cases before release.

## Remote traceroute — implemented on the development branch, RF validation pending

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
  persistent writes. Validate RF paths, direct and unreachable targets on hardware
  before releasing 0.6.0. Leave the running APC observation firmware undisturbed.

Version policy: feature releases advance the minor version (0.5.x to 0.6.0);
small changes and fixes advance the patch version (0.5.0 to 0.5.1).
