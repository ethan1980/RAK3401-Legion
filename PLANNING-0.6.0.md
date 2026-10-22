# Legion 0.6.0 planning

Status: planning. APC observation is in progress; stale-backup detection is
the only additional approved feature.

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

Version policy: feature releases advance the minor version (0.5.x to 0.6.0);
small changes and fixes advance the patch version (0.5.0 to 0.5.1).
