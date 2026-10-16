# BLE firmware updates — Legion 0.4.2

Use **nRF Connect for Android** for this release. The owner accepts this update
method; iPhone DFU remains unresolved and is not a validated alternative.

## Hardware evidence

The test node is a RAK3401 1W / RAK4631 with bootloader **0.4.3**, dated
**May 20 2023**, board ID `WisBlock-RAK4631-Board`, and **S140 6.1.1**.

On 2026-10-16, the owner completed an OTA of the older Legion 0.4.0 image using
nRF Connect. After reinstalling 0.4.2 by USB, the owner reported that a
**0.4.2-to-0.4.2** OTA was transferring normally with nRF Connect on Android.
At publication preparation, completion, application restart and a repeated update
have not yet been reported. A transfer in progress is not recorded as a completed
OTA. The observation is also included in `legion-build.json`.

The same node's iPhone updater previously remained at "Initializing DFU".
Changing the destination ZIP does not by itself fix the firmware already running
on the node. An OTA image can be received successfully even when that image's
outgoing DFU entry is defective.

## Install or migrate over USB

1. Export the current Meshtastic configuration if available.
2. Connect a USB data cable and double-press Reset to expose the bootloader drive.
3. Copy this release's `firmware-rak3401-legion-*.uf2` to that drive.
4. Wait for restart and confirm **`2.8.2.Legion0.4.2`** in device information,
   **`Legion0.4.2`** in `/telemetry`, and the expected names, channels and settings.

Use the normal application UF2 update. Factory erase/reset is not part of this
procedure. Older Legion download releases are withdrawn; their source tags and
Git history are retained.

## Update over BLE with nRF Connect

1. Keep the node powered. Close other apps connected to it.
2. In **nRF Connect on Android**, connect to the running node's normal Legion
   Bluetooth name. Use the existing configured PIN if pairing is requested.
3. Start DFU and select the release's **`firmware-*-ota.zip`** distribution packet.
   The full Actions artifact ZIP and source archive are different files.
4. Allow the application to enter the BLE bootloader and the updater to reconnect
   and transfer the image. The bootloader may appear as **AdaDFU**.
5. Wait for the updater's completion result and application restart. Reconnect
   with Meshtastic and check version, identity, channels and normal operation.
6. Repeat an OTA from the newly installed 0.4.2 when validating future updates.
   Reflashing the same 0.4.2 OTA image exercises the outgoing entry too.

A manually selected AdaDFU session tests the bootloader transfer. Starting from
the normally running Legion node also tests authorization and the transition
into that bootloader. Record which path was used.

Keep the nRF Connect log from the normal-node connection through restart.
It distinguishes pairing, service discovery, bootloader reconnection, packet
transfer and validation failures. A browser serial monitor can close when USB
disconnects during the mode change; its lost session is not evidence of an
application crash.

## Correction in 0.4.2

The 0.4.1 serial trace showed an authenticated START reaching the handler but
`Legion DFU ATT: ... opcode=0x1 status=0x0 reply=0x7`.
The pinned S140 API identifies `0x7` as `NRF_ERROR_INVALID_PARAM`: a successful
authorized write requires an attribute update and request data. Version 0.4.2
supplies `update=1`, the incoming offset, length and data synchronously.

Authorization runs directly in the BLE task with `useAdaCallback=false`.
It performs no flash access, SPI wait, logging, allocation or reset. START copies
connection values and system attributes into a static snapshot, submits the
reply and wakes the main loop. No event-buffer or connection pointer survives
the callback. Rejected replies never arm a reset.

The main loop allows a 500 ms acknowledgement interval, acquires SPI with a
five-second timeout, loads saved peer keys, fences filesystem access and flushes
flash. Missing
bond data or unavailable SPI cancels entry. Filesystem locking, bond reads and
flash flushing remain SDK operations without a new bounded timeout.

Tasks are suspended before the peer block is copied into retained RAM.
The core then requests a full reset with **`GPREGRET=0xA8`**. The unsafe C
PSP-to-MSP epilogue is not used. PIN permissions, bootloader, SoftDevice, radio,
power policy, persistence and the 0.4.0 rescue engine/layout are preserved.

## Software verification

Native tests compile the actual DFU source against SDK/RTOS stubs and cover the
write contract, probes, rejection, SPI contention, missing bonds, accepted
handoff, time rollover, unsecured peers and overlapping requests.

Compiled ARM checks execute the real SDK callback registration and dispatch,
validate the successful write-reply fields, and inspect the deferred main-loop
route and reset marker/stack behavior. The improved verifier rejects the actual
0.4.1 ELF for its missing update flag. External SoftDevice operations are stubbed;
these checks do not replace a physical OTA.

The official RAK 0.4.3 executable was also inspected:
its dispatcher accepts the full-reset `0xA8` path, and its peer reader uses
`0x20007f80`, 60 data bytes and CRC16 at offset 60, matching Legion. Executing
that reader with synthetic RAM accepted a valid record and rejected a bad CRC.
This verifies the interface, not the real phone's bond data or RAM retention.
The official archive's version/date/board strings match the owner's
`INFO_UF2.TXT`; that text is not a full flash readback.

Packaging compares the compiled ELF, application-only OTA payload and UF2,
checks CRC and metadata, and rejects overlap with the **0xE8000–0xEA000** rescue
reserve. Release publication also checks source provenance and every uploaded
asset's size and SHA-256 before retiring older downloads.

## Bootloader fallback and diagnostics

RAK 0.4.3 can fall back to USB DFU/UF2 after an interrupted or failed BLE update.
That explains a possible final USB-only state; it does not identify the original
connection or transfer failure. RAK documents a **0.4.4** bootloader with BLE
retry after failure. It is a separate update and is **not included** in Legion.

The relevant application serial lines start with `Legion DFU`:

| Last stage | Meaning |
| --- | --- |
| `ATT: ... status=... reply=...` | The immediate handler ran. `reply=0` means SoftDevice accepted the reply, not that OTA completed. |
| `waiting for SPI` | START was accepted; the main-loop handoff began. |
| `loading bond` | SPI was acquired; peer keys are being read. |
| `waiting for filesystem` | Entry is waiting to fence filesystem operations. |
| `flushing flash` | The locks are held and the SDK cache is being flushed. |
| `resetting to BLE bootloader (0xa8)` | Reset is about to be requested; the phone log must show the subsequent connection and transfer. |

References: [pinned S140 API](https://github.com/meshtastic/Adafruit_nRF52_Arduino/blob/0fd295f13203e93df19d578073646ec32f2bf45a/cores/nRF5/nordic/softdevice/s140_nrf52_6.1.1_API/include/ble_gatts.h),
[official RAK 0.4.3 archive](https://github.com/RAKWireless/WisBlock/tree/master/bootloader/RAK4630/Old/V0.4.3),
[RAK bootloader manual](https://github.com/RAKWireless/WisBlock/blob/master/bootloader/RAK4630/README.md),
and [Adafruit fallback issue](https://github.com/adafruit/Adafruit_nRF52_Bootloader/issues/259).
