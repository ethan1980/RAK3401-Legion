# Changelog

## 0.4.2 — 2026-10-16

- Correct successful DFU write authorization for the pinned S140 API: supply
  `update=1` and the original request offset, length and data. The rejected
  `NRF_ERROR_INVALID_PARAM` reply previously stopped entry before the reset.
- Handle authorization directly in the BLE task and perform flash/bond preparation
  in the main loop. Snapshot connection values before deferral; retain the safe
  full reset into the BLE bootloader with `GPREGRET=0xA8`.
- Add native DFU regression checks and execute the compiled SDK dispatch/reply
  path in ARM emulation. Check the actual write-reply contract before packaging.
- Document nRF Connect for Android as the update method. The owner reports
  0.4.2-to-0.4.2 firmware transfer; completion/restart and repeat confirmation are
  still pending at publication preparation. iPhone DFU remains unresolved.
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
