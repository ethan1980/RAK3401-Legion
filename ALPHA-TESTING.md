# 0.6.0-alpha.1 hardware test sequence

Status: **partially validated on hardware, 2026-10-24**. Continue on an
accessible RAK3401 1W/RAK13302 with known peers.
Record firmware/build identity, power source, role, radio settings, timestamps
and full replies for each stage. Keep channel PSKs, private keys and exported
configuration private. Software simulations and compiled checks are separate
from these physical results; no energy-saving claim follows from counters alone.

## Hardware record — 2026-10-24

The following results are from the operator's alpha node. Screenshots establish
the reported command outputs; OTA completion with nRF Connect, ordinary message
exchange and successful remote `/msg` operation are also confirmed by the
operator. These observations cover the listed cases.

| Check | Observed result | Remaining scope |
| --- | --- | --- |
| OTA installation and startup | Operator confirms the alpha was installed by OTA using nRF Connect; telemetry identifies `2.8.2.LGN0.6.0a1`. | The source firmware and exact client version/platform are not recorded. Entry into DFU from the running alpha and its next OTA need a separate test; this does not validate the Meshtastic apps' updater. |
| Ordinary channel and private messages | Operator confirms normal sending and receiving of both. | Long-term reliability remains part of the continuous runs. |
| Remote `/msg` | Operator separately confirms that `/msg` works on the alpha. | The basic command case is complete; no repeat is required to start OBSERVE. |
| Private diagnostics | `/telemetry`, `/boot` and `/apc status` replies received on LegionRF. | Additional modes and long-term command reachability remain pending. |
| APC initial and post-restart state | `OFF NORMAL off`, zero decision counters and `TX:nominal`, also reported after the controlled restart. | OBSERVE is now in progress; SHADOW, ON, USB bypass, context disarming, battery-state transitions and restart from a running mode remain pending. |
| APC OBSERVE reference | Operator reports OBSERVE activated on the validation node. | Initial six-page capture, exact activation time/power context and continuous 24-hour results are awaited. Activation alone does not complete the reference. |
| Boot report and normal restart | `/reboot` acknowledges `Reboot scheduled in 20s`. The subsequent `/boot` reports `reset:software(00000004)`, `prev:unknown`, first VBAT 3,870 mV, VDD 3,336 mV and `USB:0`, with reset CC310 counters. The earlier boot samples were 3,864/3,322 mV. | Normal restart and post-restart diagnostics are observed; exact restart latency and full configuration retention were not independently measured. Protective-reset/shutdown and other reset causes remain pending. `prev:unknown` is not classified as a fault cause. |
| CC310 counters during normal use | Initial `SHA:3 MAC:3 SW:0` advances to `SHA:4 MAC:19 SW:0` before restart, after the operator-confirmed message traffic. The new boot reports `SHA:3 MAC:2 SW:0`. | Hardware SHA/MAC activity and no fallback are observed in this run. Aggregate counters do not isolate each operation. Deliberate fallback, performance and current/energy measurements remain pending. |
| Rescue status and owner freshness | A valid, armed rescue point reports `up to date`, then `OUTDATED: owner`, then `up to date` again. Both matching and stale status replies keep `recovery armed`. | The owner freshness sequence is observed. The captures do not show a backup replacement or restoration. Other changed blocks, unavailable comparisons, create/replace/delete, recovery and interrupted-write cases remain pending on the alpha. |
| Ignore-list query | Correct no-argument `/ignorelist` returns `No ignored nodes`. | This does not exercise ignore/unignore mutations. |
| Zero-hop directory | Fresh `ZH#0003` reports three neighbors with +4.50, -2.25 and -8.25 dB SNR, in descending order. | Multi-page/capacity cases are not established by this one-page result. |
| Traceroute to a direct peer | Both `1/2 out` and `2/2 back` received for the same trace ID, with zero reported relays. | This does not establish that every older peer reports every hop. |
| Traceroute with intermediates | Trace `574410f9` returns both parts: two outbound relays and one return relay on a different path. | This asymmetric relayed case passes; additional path/capacity cases and command responsiveness during the wait remain pending. |
| Traceroute timeout | Trace `72dcb0f4` reports `No traceroute response within 90s; reachability unknown`. | The timeout response is observed. Explicit routing `NO_ROUTE` and its unreachable reply remain untested; this silent target's reachability is unknown. |

The earlier empty `ZH#0001` was a frozen directory capture. A new capture after
its 15-minute lifetime included the neighbors; this case does not establish a
zero-hop detection regression. Repeated page 1 requests reuse a live capture.

Installing the alpha by OTA exercises the entry path of the previously installed
firmware. Testing the alpha's own DFU entry requires starting a subsequent update
while the alpha is running. The first installation is complete; record that next
entry test separately. USB power, external battery/solar charging context and
full configuration-retention confirmation should accompany later observations.

The later captures close the relayed-trace, timeout-reporting, CC310 follow-up,
normal-restart and owner-freshness cases listed above. They do not establish
backup replacement/restoration or all reset causes. CC310 counters are RAM-only;
their lower values after the deliberate restart are expected for a new boot.

Current stage: the operator has started the 24-hour passive OBSERVE reference
on the migrated base; the first capture is awaited. SHADOW and controlled ON
follow after review. Keep the completed cases closed unless
new evidence exposes a regression. Defer configuration edits, deliberate reboots,
DFU and recovery tests until the continuous APC capture is complete.

## 1. Install and establish the migrated-base reference

- First installation is complete by OTA using nRF Connect on the validation
  node. For another accessible node, keep the earlier working firmware and export/check its
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

## 2. Feature checks with APC OFF

The hardware record above determines which cases still need evidence. Do not
repeat its completed direct/relayed trace, timeout, normal-restart, owner-freshness
or ordinary-message checks merely to start APC observation. Remaining disruptive
checks can follow the continuous OBSERVE/SHADOW runs.

| Check | Evidence to collect |
| --- | --- |
| Existing remote commands | Remote `/msg` is now operator-confirmed. Test ignore/unignore mutations only with deliberate test peers. The no-argument ignore-list query and zero-hop directory already reply on the alpha. |
| Traceroute | Still collect an explicit routing `NO_ROUTE` if reproducible and a diagnostic reply while another trace is waiting. Direct, asymmetric relayed and timeout replies are already observed. |
| CC310 | The live SHA/MAC counts and zero observed fallback are recorded. Isolate operation/fallback behavior and measure performance/energy separately if needed; a zero MAC count alone is inconclusive. |
| Boot evidence | Compare USB/battery boot samples and protective/wake or other reset causes in controlled later runs. Normal software restart is already observed. Record unknown causes as unknown. |
| Backup freshness | Owner stale/matching replies are observed. Later exercise other captured blocks and unavailable comparisons; status must add no writes. Keep explicit replacement and restoration separate from a freshness query. |
| Backup and DFU | Initial OTA installation using nRF Connect is confirmed. Test a subsequent DFU/OTA entry from the running alpha, and record the exact updater/client version/platform, source/target versions, reconnection, preferences and rescue status. Use an agreed procedure for restoration. |

After any reboot, APC must again be OFF. Prioritize command/reception failures,
watchdog resets, unexpected configuration changes or flash/DFU failures before
proceeding to APC. Preserve logs and the installed artifact hash.

## 3. Observe, then shadow

- Use `/apc observe !legionid` for a **24-hour migrated-base reference**. Record
  the activation time, power/charging arrangement and normal operating context.
  OBSERVE collects passive statistics without imposing APC relay limits.
- After 5–10 minutes, request page 1 once, then pages 2–6 in order, at least
  six seconds apart, from the same requesting node. Complete the set within
  15 minutes and retain matching session/report IDs. Do not repeat page 1 in
  the middle: it replaces the frozen capture. For example:

  ```text
  /apc status !legionid
  /apc status !legionid 2
  /apc status !legionid 3
  /apc status !legionid 4
  /apc status !legionid 5
  /apc status !legionid 6
  ```

- Send that initial set with the activation time and power context. Keep normal
  traffic and the same node location/settings; avoid planned restarts, updates
  and configuration edits during the run. Report unexpected disarming, resets
  or message/command failures immediately, preserving the replies and time.
- At 24 hours from activation, collect another complete six-page set the same
  way, plus `/boot` and `/telemetry`, respecting their existing cooldowns.
  Include charging/USB changes and any interruptions. Review the reference
  before switching modes; an interrupted run is not a continuous 24-hour record.
- Then use `/apc shadow !legionid` for **24 hours across a day/night transition**,
  with initial/final six-page captures and the same context record. Switching modes
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
- Start with 30–60 minutes of supervised operation and review the reports before
  extending ON to 24 hours. Do not infer low-voltage refusal coverage from a run
  that remains in NORMAL or has no eligible relay workload.
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
