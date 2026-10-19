Experimental firmware for the **RAK3401 1W with RAK13302**.

- Legion version: **0.5.1**; advertised firmware: **`2.8.2.Legion0.5.1`**.
- Same pinned Meshtastic 2.8.2 base and existing features as 0.5.0.
- Battery sleep requires **eight consecutive readings below 3.50 V**, checked every
  **20 seconds**. A healthy reading or USB power clears the counter. First-to-eighth
  checks are nominally 140 seconds apart; this is sampled confirmation.
- Battery refresh remains every 5 seconds for existing flash/TX protection.
  Independent VDD protection, boot/wake thresholds and REG1 DC/DC are unchanged.
- New timing requires hardware validation; no measured battery-saving claim.

Energy hibernation and automatic return to operation have been observed on hardware:
the production node went offline overnight and resumed after sunrise. The exact
entry voltage and triggering protection were not recorded. The new 0.5.1 timing
still requires hardware validation.

All six commands introduced in 0.5.0 have been tested on hardware and work correctly.
Manual backup restoration was observed on the test RAK after applying an erase.uf2,
installing bootloader 0.4.4 and reinstalling the D1 diagnostic Legion firmware by USB
UF2: the saved configuration returned. This validates that procedure with the file
used; it does not establish survival of a full-chip erase. Reception of the recovery
announcement was not verified because no connected receiver was available.
Physical interrupted-write/power-cut recovery testing remains pending.

See [commands](COMMANDS.md) and [manual rescue backup](RECOVERY.md).
