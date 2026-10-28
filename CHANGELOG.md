# Changelog

## 0.6.1 — 2026-10-28

- Publish the stable `2.8.2.Legion0.6.1` release on Meshtastic `c39728e`.
- Make ignore, unignore and ignorelist individual commands with an explicit executor ID.
- Add createch/deletech for verified secondary-channel changes; protect the primary
  and LegionRF, preserve slot indices and disarm APC after a successful change.
- Add components for CC310, radio SPI and REG1; keep boot focused on startup evidence.
- Add the private daily APC/backup reminder, counted from each boot.
- Update command documentation and the illustrated friendly manual in Spanish and English.

## 0.6.0-alpha.1 — 2026-10-24

- Migrate to Meshtastic 2.8.2 develop at `e039e34`, including its BLE OTA reset fix.
- Add APC (Adaptive Power Control) S1: OBSERVE, SHADOW, ON, OFF and status pages;
  battery-based optional relay budgets, nominal RF output and boot OFF.
- Add remote `/trace` with asynchronous outbound/return paths and timeout handling.
- Add read-only `/boot` diagnostics and CC310 packet SHA/ACK-proof HMAC acceleration.
- Add read-only backup freshness with changed-block names and explicit replacement.
- Keep command/APC timing available across long uptime and clock rollover.
- Publish as an experimental alpha, identified as `2.8.2.LGN0.6.0a1`.

Current hardware status is summarized in the [README](README.md#what-legion-adds).

## 0.5.1 — 2026-10-19

- Confirm low battery with eight readings below 3.50 V, checked every 20 seconds.
- Preserve five-second sampling and independent VDD, TX and flash protection.
- Advertise `2.8.2.Legion0.5.1`.

## 0.5.0 — 2026-10-19

- Add remote text, scheduled reboot, direct-peer directory and ignored-node tools.
- Enable nRF52840 REG1 DC/DC after successful SoftDevice initialization.
- Retain bulk SPI, energy recovery, private telemetry and manual rescue.

## 0.4.2 — 2026-10-16

- Correct private telemetry formatting and consistent Legion firmware identification.
- Retain the working nRF Connect OTA path and manual rescue features.

## 0.4.0 — superseded

- Introduce explicit manual rescue backup, configuration/identity/fixed-position
  restoration and the private recovery notice.

## 0.3.5 and earlier — superseded

Earlier releases introduced radio SPI optimization, energy recovery, verified
preference writes and private telemetry. Source history remains available;
superseded download packages have been withdrawn.
