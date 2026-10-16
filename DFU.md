# Firmware installation and updates — Legion 0.4.2

BLE OTA updates have been verified using **nRF Connect**.
The firmware identifies itself as **`2.8.2.Legion0.4.2`**.

## BLE OTA with nRF Connect

1. Download `firmware-rak3401-legion-*-ota.zip` from the
   [0.4.2 release](https://github.com/ethan1980/RAK3401-Legion/releases/tag/legion-v0.4.2-aee6ab8).
   Keep this OTA ZIP intact; the complete Actions artifact ZIP is a different file.
2. Disconnect other apps from the node and connect to it in nRF Connect.
   Complete Bluetooth pairing with the configured PIN if requested.
3. Start the app's DFU update and select the OTA ZIP as the distribution package.
4. Allow the transfer to complete and the node to restart.

## USB installation

Migration from older Legion releases uses the 0.4.2 UF2 over USB.
Connect a USB data cable, double-press Reset to expose the bootloader drive,
and copy `firmware-rak3401-legion-*.uf2` onto that drive.
The node restarts automatically after installation.

A normal application update preserves the existing configuration and Legion's
rescue reserve. The release does not include a bootloader or SoftDevice update.
A factory reset or full-device erase is not part of the update procedure.
See [RECOVERY.md](RECOVERY.md) for backup storage and reset behavior.
