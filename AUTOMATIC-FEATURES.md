# Automatic features

[Overview](README.md) · [Commands](COMMANDS.md) · [Rescue backup](RECOVERY.md) · [Energy recovery](ENERGY-RECOVERY.md) · [APC](APC.md)

CC310 hashing, bulk radio SPI, flash persistence and REG1 DC/DC are included in
the **Legion 0.6.1** firmware profile for the **RAK3401 1W with RAK13302**.
They work automatically in their normal firmware paths and need no separate
activation command or app setting. A private LegionRF channel is only needed
to request the component report described below.

These features operate independently of APC, which starts OFF after every boot.

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

## Bulk radio SPI at 8 MHz

**SPI** is the internal communication bus between the nRF52840 MCU and the
SX1262 LoRa radio. Legion configures this bus at **8 MHz** and transfers radio
buffers in blocks through the nRF52 **SPI/EasyDMA** path.

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

Critical configuration files use the staged replacement path. The large
**NodeDB** file retains upstream's space-saving, **non-atomic replacement**.
Unsaved RAM state can still be lost if power disappears during operation.
The [energy policy](ENERGY-RECOVERY.md#thresholds-and-timing) also guards saves
when the supply is weak.

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

## Checking component status

To query a Legion node, send this as a channel message on the private
[LegionRF channel](COMMANDS.md#private-channel), replacing the example ID:

```text
/components !abcdef01
```

Illustrative reply:

```text
!abcdef01 COMPONENTS
CC310 SHA:1357 MAC:2 SW:0
SPI:ON 8MHz BULK:ON
DC/DC:ON REG1
```

`/components` reads existing counters and component state. It does not activate
these features, reinitialize hardware or write settings to flash. Flash
persistence has no field in this report. See the
[component field reference](COMMANDS.md#component-fields) for all field meanings.

## Validation status

CC310 hardware use, 8 MHz bulk SPI operation and REG1 activation/readback have
been confirmed on hardware. Identical-save skipping and flash readback checks
have been verified in software. These observations confirm operation within the
tested conditions; current consumption and battery-life gains have not been
measured.
