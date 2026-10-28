# Energy recovery and resilience

[Overview](README.md) · [Commands](COMMANDS.md) · [Automatic features](AUTOMATIC-FEATURES.md) · [Rescue backup](RECOVERY.md) · [APC](APC.md)

Legion's energy policy protects startup, radio transmission and configuration
saves when the supply becomes weak. It can put the node into energy sleep and
restart it after charging restores the voltage. This policy operates automatically,
independently of APC and manual rescue backup.

It targets the **RAK3401 + battery-powered RAK13302 + RAK19007**, supplied by a
single-cell Li-Ion/LiPo pack or parallel cells at the same voltage. Four parallel
18650 cells still have a single-cell pack voltage.

## What is measured

| Measurement | Method | Normal timing |
| --- | --- | --- |
| **VBAT**, physical battery voltage | Average of 15 ADC readings through the RAK19007 battery divider, using 12-bit resolution and a **3.0 V ADC reference**. | Refreshed every **5 seconds**, during boot checks and before a TX attempt. |
| **VDD**, MCU supply voltage | Internal nRF52840 supply measurement with the **3.6 V ADC range**, separate from the battery divider. | Checked every **1 second**, during boot/TX checks and by the flash-safety guard. |
| **USB/VBUS** | Node USB power detection. | Used by the applicable boot, protection and recovery decisions. |

The battery divider has **R3 = 1 MΩ** and **R4 = 1.5 MΩ**, so its ADC input is
approximately **0.6 × VBAT**. Legion converts that physical reading independently
of the app's ADC-multiplier override. The app's estimated battery percentage can
therefore disagree with the policy voltage.

These are voltage measurements, not a fuel gauge or a measurement of solar
charging current, stored charge or battery capacity. A solar charger connected
to the battery base can charge the pack while the node still reports `USB:0`.

## Thresholds and timing

The current Legion profile uses the following defaults:

| Protection | Voltage and timing | Behavior |
| --- | --- | --- |
| **Boot reserve** | VBAT **≥ 3.60 V** and VDD **≥ 3.00 V** in four checks, **250 ms apart**; repeat after enabling IO2. | A weak supply returns to energy sleep before normal startup completes. |
| **Low battery** | Eight consecutive battery checks **below 3.50 V**, **20 seconds apart**. | Enter energy sleep. A reading **≥ 3.50 V** or USB power clears the low-battery counter. |
| **Low MCU supply** | On battery, VDD **below 2.90 V** marks the supply unsafe; **≥ 3.00 V** clears it. Six consecutive unsafe checks, normally **1 second apart**, trigger sleep. | The hysteresis avoids repeatedly clearing the warning near the lower threshold. |
| **TX reserve** | VBAT **≥ 3.50 V** and VDD **≥ 3.00 V**. | Refresh voltage readings before CAD/channel sensing; recheck the cached decision immediately before TX launch. |
| **Guarded flash saves** | Battery reserve **≥ 3.50 V**, plus the VDD guard: unsafe below **2.90 V**, safe again at **≥ 3.00 V**. | Block guarded writes on inadequate supply and once energy shutdown begins. USB bypasses the battery requirement. |
| **Hardware wake** | LPCOMP on **AIN3**, at **11/16 of VDD**, with hysteresis enabled. | Detect rising battery voltage during System OFF. The nominal battery crossing is about **3.78 V at VDD = 3.30 V**, before comparator hysteresis and component tolerances. |
| **Recovery fallback** | Four healthy checks **30 seconds apart**, with VBAT **≥ 3.80 V** and VDD **≥ 3.00 V**. | If the comparator cannot be armed or its input is already above the threshold, wait in System ON with the radio off, then reset. With USB present, healthy VDD permits reset at a recovery check without the battery-count requirement. |

Battery sampling continues every five seconds; only the low-battery **sleep
decision** uses the 20-second interval. The first and eighth low checks are
nominally **140 seconds apart**. Actual response time also depends on when the
voltage crosses the threshold and normal scheduling. TX and flash protections
do not wait for those eight checks.

The comparator wake voltage follows VDD and the analog circuit; it is not a
precisely measured 3.78 V set point. The fallback's 3.80 V requirement is a
separate software threshold. Both routes return through the boot power gate.

## Sleep and return to operation

The early boot gate runs before console, filesystem and Bluetooth startup. It
checks the supply before and after enabling the peripheral rail so a weak pack
does not proceed directly into normal operation as the load increases.

During a running-node energy shutdown, the radio receives its normal sleep
notification before SPI closes. Legion then cuts IO2 and the radio power enable
and turns off both user LEDs. It skips the TX-queue wait and final NodeDB snapshot
while the supply is falling; packets or unsaved state still in RAM can be lost.

When the wake comparator is ready, the MCU enters **System OFF**. The hardware
charger can continue charging while the firmware is asleep. If the comparator
cannot provide a future rising edge, the fallback waits for stable voltage with
the radio off rather than entering System OFF without a usable wake source.

**Reception and forwarding stop during energy sleep.** Rising battery voltage
can wake/restart the node, and the boot gate checks supply reserve again before
normal operation resumes. A deliberate app/CLI shutdown does not arm this
automatic battery-voltage wake.

## USB, APC and configuration resilience

Node USB/VBUS bypasses the battery thresholds and clears the periodic
low-battery/low-VDD sleep counters for servicing. Boot and TX still require
adequate VDD, and the VDD flash-safety guard remains active. An external solar
charger is not treated as USB power by the node.

[APC — Adaptive Power Control](APC.md), when enabled in ON, can reduce eligible
optional relay admissions before the battery reaches the energy-sleep threshold.
It does not replace these protections or initiate sleep itself.
The [manual rescue point](RECOVERY.md)
restores settings after confirmed essential preference loss; a low-voltage
shutdown alone does not authorize overwriting healthy preferences.

For normal configuration saves,
[automatic flash persistence](AUTOMATIC-FEATURES.md#flash-persistence) skips
identical content and verifies temporary writes before replacement. It works
alongside the voltage guards described above; see that section for the save
sequence and the large NodeDB file's replacement limits.

## Available readings and hardware status

`/telemetry !abcdef01` reports current physical battery voltage and its observed
minimum. `/boot !abcdef01` reports reset/shutdown evidence and the **first**
VBAT/VDD/USB samples of that boot, not live values at the instant of a fault.
[APC status](APC.md#reading-status) provides session voltage statistics when
observation is active. All use the existing private LegionRF channel.

**Hardware status:** Energy sleep and automatic return have been observed on
Legion hardware. Whole-node
sleep current, energy savings and battery-life gains have not been measured.
