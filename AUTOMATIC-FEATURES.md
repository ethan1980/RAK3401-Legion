# Automatic features

[Overview](README.md) · [Commands](COMMANDS.md) · [Rescue backup](RECOVERY.md) · [Energy recovery](ENERGY-RECOVERY.md) · [APC](APC.md)

CC310 hashing, bulk radio SPI, flash persistence and REG1 DC/DC are included in
the **Legion 0.7.2** firmware profile for the **RAK3401 1W with RAK13302**.
They work automatically in their normal firmware paths and need no separate
activation command or app setting. A private LegionRF channel is only needed
to request the component report described below.

These features operate independently of APC. APC defaults to OFF at boot unless
the user has saved [permanent arming](COMMANDS.md#arm-and-disarm).

## CC310 hashing

The nRF52840 contains a **CC310 cryptographic accelerator**. Legion uses it for
packet **SHA-256** hashing and **HMAC-SHA256** calculations for ACK proofs,
offloading those calculations from the CPU to dedicated hardware.

The firmware selects the hardware path when a calculation is needed. If an
accelerator attempt fails or the accelerator is unavailable, it completes the
calculation in software. This keeps the normal Meshtastic result and packet
compatibility.

The component report's `SHA` and `MAC` counters record successful hardware
operations since boot. `SW` counts attempts that fell back to software.
A zero `MAC` count can be normal when no ACK-proof HMAC operation has occurred.

The 0.7.2 nightly base also accelerates the Ed25519 base-point multiplication
used by XEdDSA signing on CC310 and avoids repeating expensive RNG setup.
Legion preserves its accelerator-session locking and the upstream self-test
and software fallback. `SHA`/`MAC` do not count signing operations. This new
upstream path is pending HW verification; no battery gain has been measured.

## Bulk radio SPI at 8 MHz

**SPI** is the internal communication bus between the nRF52840 MCU and the
SX1262 LoRa radio. Legion configures this bus at **8 MHz** and transfers radio
buffers in blocks through the nRF52 **SPI/EasyDMA** path.
The pinned Meshtastic base supplies `RADIO_SPI_BULK`; Legion sets the bus clock.

Block transfers avoid handling an entire buffer as individual byte transfers.
The 8 MHz value is the internal bus clock; LoRa modulation and channel settings
are configured separately in Meshtastic.

The component report shows SPI availability, the configured clock and whether
the build enables `BULK`. The clock shown is the configured value, rather than
a live frequency measurement.

## Flash persistence

Flash stores the node's saved configuration. Legion automatically checks normal
preference saves to avoid unnecessary writes and verifies staged data before
replacing a saved file:

1. Compare the encoded settings with the existing file byte for byte. If they
   are identical, keep the existing file and skip the write.
2. When content changes, encode it into a temporary file. Encoding must finish
   successfully before the save can be committed.
3. Read the temporary file back and check its **CRC32 and exact byte length**
   before proceeding with replacement.
4. If encoding, writing, verification or renaming fails, close the staging file
   and remove that attempt's `.tmp` when the supply is safe for flash operations.
   An unsafe supply or failed removal leaves cleanup for the next opening.

Critical configuration files use the staged replacement path. The large
**NodeDB** file retains upstream's space-saving, **non-atomic replacement**.
Unsaved RAM state can still be lost if power disappears during operation.
The [energy policy](ENERGY-RECOVERY.md#thresholds-and-timing) also guards saves
when the supply is weak.

`/components` now includes `SAVE C:n U:n S:n F:n`: preference saves checked,
identical saves skipped, completed saves and failed attempts since boot.
Reading the counters does not save settings. These counts cover the protobuf
preference-save path; they are not a count of every filesystem write.

For an explicit restorable configuration snapshot, use the
[manual rescue backup](RECOVERY.md). Flash persistence applies to ordinary
saves independently of whether a rescue point exists.

## REG1 DC/DC

**REG1** is the nRF52840's main internal supply regulator. Its **DC/DC** mode
uses the board's switching-regulator circuit for more efficient MCU power
conversion.

Legion requests REG1 DC/DC enablement after successful Bluetooth SoftDevice
initialization and checks the hardware register to confirm activation.
The component report reads the regulator's current enabled/disabled state.

## CPU thermal hibernation

Legion samples the nRF52840's internal temperature every 30 seconds. At
70 °C or higher for 3 minutes, it stops the radio and peripherals and waits
in System ON. A reading below 70 °C, an invalid reading or a missed sample
resets the three-minute timer. While suspended, two consecutive valid readings at
60 °C or lower trigger a restart. An overlapping Scramble deadline also
has to elapse.

When normal TX checks allow it, LegionRF receives one attempt at
`Entering hibernation due to high CPU temperature.` before sleep and
`Hibernation ended. CPU cooled down.` once the node is operational again.
The entry notice has up to 4 seconds to transmit. The restart is recorded
as `prev:cpu-thermal` in [boot diagnostics](COMMANDS.md#boot-fields).

## Fixed-position warning

With **Fixed position** enabled, Legion checks its local coordinates. If both
latitude and longitude are `0`, it waits **5 minutes** and sends this on the
private **LegionRF** channel, using the node's own ID.

```text
!abcdef01: Fixed position is invalid. Set valid coordinates in Position settings.
```

The warning repeats every **12 hours** while the coordinates remain empty.
Correcting the coordinates or disabling fixed position cancels the pending
warning silently. A new occurrence starts another five-minute delay. A restart
also starts the delay again.

The warning uses the existing TX and private-channel checks. A deferred attempt
checks the position again before sending. The feature runs automatically and
its state stays in RAM.

## Checking component status

To query a Legion node, send this as a channel message on the private
[LegionRF channel](COMMANDS.md#private-channel), replacing the example ID:

```text
/components !abcdef01
/components PSVR
```

Illustrative reply:

```text
!abcdef01 COMPONENTS
CC310 SHA:1357 MAC:2 SW:0
SPI:ON 8MHz BULK:ON
DC/DC:ON REG1
SAVE C:20 U:14 S:6 F:0
```

`/components` reads existing counters and component state. It does not activate
these features, reinitialize hardware or write settings to flash. See the
[component field reference](COMMANDS.md#component-fields) for all field meanings.

## Validation status

The owner confirmed all Legion 0.7.1 functions tested on HW on 23 November 2026.
This includes failed-save temporary cleanup and the fixed-position warning,
alongside the commands, DAILY score and previously verified components.
Automated tests cover the save failure paths and voltage guards.
The 0.7.2 base migration, signing path and new SAVE report fields are pending HW.
Current consumption and battery-life gains have not been measured.
