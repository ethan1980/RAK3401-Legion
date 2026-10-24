# 0.6.0-alpha.1 hardware test sequence

Status: **partially validated on hardware, 2026-10-24**. Continue on an
accessible RAK3401 1W/RAK13302 with known peers.
Record firmware/build identity, power source, role, radio settings, timestamps
and full replies for each stage. Keep channel PSKs, private keys and exported
configuration private. Software simulations and compiled checks are separate
from these physical results; no energy-saving claim follows from counters alone.

## Hardware record — 2026-10-24

The following results are from the operator's alpha node. Screenshots establish
the reported command outputs; OTA completion and ordinary message exchange are
also confirmed by the operator. These observations cover the listed cases.

| Check | Observed result | Remaining scope |
| --- | --- | --- |
| OTA installation and startup | Operator confirms the alpha was installed by OTA; telemetry identifies `2.8.2.LGN0.6.0a1`. | Updater/client and source version are not recorded. Entry into DFU from the running alpha and its next OTA need a separate test. |
| Ordinary channel and private messages | Operator confirms normal sending and receiving of both. | Successful delivery specifically through the remote `/msg` command has not been stated separately. |
| Private diagnostics | `/telemetry`, `/boot` and `/apc status` replies received on LegionRF. | Additional modes and long-term command reachability remain pending. |
| APC initial state | `OFF NORMAL off`, zero decision counters and `TX:nominal`. | OBSERVE, SHADOW, ON, USB bypass, context disarming and battery-state transitions remain pending. |
| Boot report | `reset:software(00000004)`, `prev:unknown`, first VBAT 3,864 mV, VDD 3,322 mV and `USB:0`. | Controlled normal restart and protective-reset/shutdown cases remain pending. `prev:unknown` is not classified as a fault cause. |
| CC310 counters | Initial live report shows `SHA:3 MAC:3 SW:0`. | Follow-up `/boot` after the confirmed message traffic is still awaited. Performance and current/energy measurements remain pending. |
| Rescue status | `valid rescue point; up to date; recovery armed`. | OUTDATED after a reversible change, replacement, recovery and interrupted-write cases remain pending on the alpha. |
| Ignore-list query | Correct no-argument `/ignorelist` returns `No ignored nodes`. | This does not exercise ignore/unignore mutations. |
| Zero-hop directory | Fresh `ZH#0003` reports three neighbors with +4.50, -2.25 and -8.25 dB SNR, in descending order. | Multi-page/capacity cases are not established by this one-page result. |
| Traceroute to a direct peer | Both `1/2 out` and `2/2 back` received for the same trace ID, with zero reported relays. | Routes with intermediates, timeout/unreachable distinction and other-command responsiveness while waiting remain pending. |

The earlier empty `ZH#0001` was a frozen directory capture. A new capture after
its 15-minute lifetime included the neighbors; this case does not establish a
zero-hop detection regression. Repeated page 1 requests reuse a live capture.

Installing the alpha by OTA exercises the entry path of the previously installed
firmware. Testing the alpha's own DFU entry requires starting a subsequent update
while the alpha is running. The first installation is complete; record that next
entry test separately. USB power, external battery/solar charging context and
full configuration-retention confirmation should accompany later observations.

Next: traceroute through known intermediates and the pending `/boot` capture,
then a controlled normal restart, reversible backup-freshness test and APC
OBSERVE → SHADOW → ON. Save the CC310 report before restarting: counters are RAM-only.

## 1. Install and establish the migrated-base reference

- First installation is complete by OTA on the validation node. For another
  accessible node, keep the earlier working firmware and export/check its
  configuration; USB UF2 remains the initial test option. Ordinary updates
  preserve preferences and do not require erase or factory reset.
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
| Backup and DFU | Initial OTA installation is confirmed. Test a subsequent DFU/OTA entry from the running alpha, and record the updater/client, source/target versions, reconnection, preferences and rescue status. Use an agreed procedure for restoration. |

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
