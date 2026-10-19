# Changelog

## 0.5.0 - 2026-10-19

- Add `/msg !nodeid <channel> <message>` with channel revalidation, bounded UTF-8
  text and queue-acceptance confirmation.
- Add `/reboot !nodeid` using the normal restart path with a 20-second deadline.
- Add `/zerohop !nodeid [page]` with current-boot direct RF qualification, existing
  SNR and stable manually requested pages.
- Add group-wide `/ignore !peerid`, `/unignore !peerid` and `/ignorelist [page]`.
  Reuse persistent NodeDB flags, merge legacy entries and report deferred writes.
- Enable nRF52840 REG1 DC/DC once after successful SoftDevice initialization.
  Activation was verified on the diagnostic RAK with USB and battery power;
  whole-node savings remain unmeasured.
- Advertise `2.8.2.Legion0.5.0` in MQTT, Bluetooth and device metadata, and
  `Legion0.5.0` in telemetry.
- Retain 8 MHz bulk SPI, energy recovery, persistence protections and manual
  rescue format. Extend host and compiled-binary release checks.
- New-command hardware validation, automatic emergency restoration, recovery
  announcement and physical power-cut testing remain pending.

## 0.4.2 — 2026-10-16

- Retain 8 MHz bulk SPI, energy recovery, verified preference writes, private
  telemetry and manual rescue backup.
- Advertise `2.8.2.Legion0.4.2` consistently in MQTT, Bluetooth and device
  metadata; use `Legion0.4.2` in the telemetry header.
- Verify telemetry responses, current firmware version and min/max formatting
  on hardware.
- Verify all backup commands on hardware: creation with its success confirmation,
  status, replacement and deletion. Automatic emergency restoration from a saved
  backup and its recovery announcement remain pending hardware verification.
- Verify release assets against their build hashes before withdrawing superseded
  download releases. Preserve all source tags and Git history.

## 0.4.0 — superseded

Introduced targeted manual rescue snapshots and recovery, fixed-position restore,
the recovery announcement, dynamic telemetry version and spaced min/max labels.

## 0.3.5 and earlier — superseded

The normal-operation features remain in 0.4.2. Older download releases have been
withdrawn. Source versions remain available through the repository's tags and history.
