# Changelog

## 0.4.2 — 2026-10-16

- Fix BLE OTA entry. Correct operation is verified using nRF Connect.
- Add native DFU regression tests and compiled ARM checks for update entry.
- Verify telemetry responses, current firmware version and min/max formatting
  on hardware.
- Verify manual backup creation with a success confirmation, status and deletion
  on hardware. Emergency restoration from the saved backup, its announcement,
  backup replacement and physical power-cut recovery remain pending hardware tests.
- Preserve the 0.4.0 manual rescue engine, flash layout, radio, power policy,
  persistence and private telemetry. Advertise `2.8.2.Legion0.4.2` consistently
  in MQTT, Bluetooth, device metadata and the telemetry header.
- Verify uploaded release assets against their build hashes before withdrawing
  superseded download releases. Preserve all source tags and Git history.

## 0.4.0 — superseded

Introduced targeted manual rescue snapshots and recovery, fixed-position restore,
the recovery announcement, dynamic telemetry version and spaced min/max labels.
Its outgoing DFU entry is superseded; being able to receive its OTA image does
not verify that it can initiate the next update.

## 0.3.5 and earlier — superseded

The normal-operation features remain in 0.4.2. Older download releases have been
withdrawn in favor of the corrected DFU entry. Use 0.4.2 UF2 for USB migration.
Source versions remain available through the repository's tags and history.
