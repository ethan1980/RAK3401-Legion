# 0.6.0-alpha.1 hardware test sequence

Status: pending. Run on an accessible RAK3401 1W/RAK13302 with known peers.
Record firmware/build identity, power source, role, radio settings, timestamps
and full replies for each stage. Keep channel PSKs, private keys and exported
configuration private. Software simulations and compiled checks are separate
from these physical results; no energy-saving claim follows from counters alone.

## 1. Install and establish the migrated-base reference

- Keep the earlier working firmware available and export/check the current
  configuration. Install the alpha UF2 by the normal USB procedure, preserving
  preferences. Ordinary updates do not require erase or factory reset.
- Verify `2.8.2.LGN0.6.0a1`, node ID, owner, region, channels, keys, role and
  fixed position. Check app/BLE connection and ordinary receive/transmit behavior.
- APC must be OFF after boot. On private LegionRF, send `/apc status !legionid`,
  `/boot !legionid` and `/telemetry !legionid`. Replace IDs with the full executor
  ID. Allow at least six seconds between control commands; telemetry and backup
  share a separate 60-second cooldown.
- Record reset mask, first VBAT/VDD/USB, firmware identity, packet behavior and
  any unexpected restarts before attributing a change to APC.

## 2. Check pending features with APC OFF

| Check | Evidence to collect |
| --- | --- |
| Existing remote commands | `/msg`, `/zerohop`, ignore-list queries and a scheduled reboot still work. Use deliberate test peers for ignore changes. |
| Traceroute | Trace known direct and relayed peers. Check both paths, pacing, timeout/unreachable distinction and command responsiveness while waiting. |
| CC310 | Compare `/boot` counters before/after local packet SHA and PKI/ACK-proof operations with a compatible peer. Confirm successful text/DM/ACK exchange; a zero MAC count alone is inconclusive. |
| Boot evidence | Compare USB/battery boot samples and recorded reset causes after a deliberate normal restart. Record unknown causes as unknown. |
| Backup freshness | Query a known valid rescue point, compare after a reversible backed-up setting change, then restore that setting or explicitly replace the rescue point. Status must add no writes. |
| Backup and DFU | Verify create/status/replace and restoration only with an agreed recovery procedure. Perform BLE OTA after the first USB installation; verify reconnect, version, preferences and backup status. |

After any reboot, APC must again be OFF. Prioritize command/reception failures,
watchdog resets, unexpected configuration changes or flash/DFU failures before
proceeding to APC. Preserve logs and the installed artifact hash.

## 3. Observe, then shadow

- Use `/apc observe !legionid` for a migrated-base reference. Read page 1 and
  then pages 2–6 of the frozen capture; retain matching session/report IDs.
- Use `/apc shadow !legionid` across a day/night transition. Switching modes
  requires fresh decision warmup. Check VBAT/raw/decision EMA, sample gaps,
  inhibition reason, persistence and state transitions against [APC.md](APC.md).
- Check USB bypass and fresh warmup after unplugging. An external battery/solar
  charger may remain `USB:0`; record its charging timeline separately.
- `would` can increase in SHADOW; actual `skip` must stay zero for a fresh
  SHADOW-only session. Mixed-session counters retain previous running modes.
- Confirm text, DMs, ACKs, traceroute and LegionRF remain reachable. Compare
  eligible admissions and modeled refusals without treating them as deliveries
  or measured battery savings.

## 4. Controlled ON and immediate OFF

- Enable ON only after the reference and SHADOW checks, with known peers and
  normal CLIENT role. Changing SHADOW to ON restarts warmup/persistence.
- At known low-voltage conditions, check optional position/telemetry relay
  admissions, protected traffic and text/DM/ACK/command delivery at known peers.
  Use a controlled supply or observed natural voltage; avoid an uncontrolled
  brownout. Existing low-power safeguards take priority over APC.
- `/apc off !legionid` restores normal optional-relay admission immediately.
  Check that mode state is not saved and the next boot remains OFF.
- Check context disarming after an intentional relevant configuration change;
  reactivation must be explicit. Keep normal RF output and continuous reception.

## 5. Longer follow-up

Validate battery safety/hibernation/wake thresholds, reset/shutdown evidence,
recovery announcement delivery, interrupted-write recovery and long-term radio
stability in separate controlled runs. Measure current/charge with suitable
hardware before claiming energy or autonomy gains. Adaptive RF-power selection
requires a separate implementation and known-receiver calibration; it is outside
this S1 alpha.
