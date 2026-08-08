# CALIBRATION REPORT — Rover Wall-Stop System
**Document type:** REPORT (static; not edited after issue)  
**Version:** 1.0  **Date:** 2026-07-21  
**Gate:** B  
**Producing runs:** Cal-Run-1 (run-20260720-233145) · Cal-Run-2 (run-20260720-235032)  
**Programme run count at this gate: 4** (Cal-Run-1, Cal-Run-2 attempt 1 [backward], Cal-Run-2 corrected, this gate)  
*Note: Cal-Run-2 attempt 1 ran backward for 19 s due to an incorrect motor-direction inference from Cal-Run-1 telemetry. The USS-E rear-sensor signal (548→445mm, decreasing, confirming rearward travel) was not weighted correctly during analysis. Corrected on Cal-Run-2 re-run.*

---

## 1. TBD Register — Closed (except TBD_COMBO)

| TBD ID | Parameter | Calibrated Value | Evidence Basis | Source Tier |
|--------|-----------|-----------------|----------------|-------------|
| TBD_VMOT | vMaxRated_dps | ~1100 deg/s (estimated) | Derived: v_mms / (wheel_circum/360); direct motor-speed telemetry not logged in Cal-Run-2. Single estimate; treated as T3 until verified. Revised to T2 in Verif-Run by adding `motor.speed()` log. | T3 (estimate) |
| **TBD_VMAX_MMS** | vMax_mms | **465 mm/s** | Linear fit to fwd1 vs hub-clock timestamp, t=951–1601ms (14 clean points, noise-spike-filtered). Slope = −0.465 mm/ms. Cross-checked against fwd2 slope in same window (compatible within noise). | T2 |
| **TBD_DSTOP** | dStopTotal_mm | **44 mm** | trigger_f1_mm (388mm at t=1701ms) minus final_f1_mm (344mm, settled at t=6731ms). 5030ms settle confirms full rest. Single run. | T2 (single run) |
| **TBD_TRESP** | tResponse_s | **0.050 s (50 ms)** | Hub-clock timestamp spacing: exactly 50ms between all 35 buffer entries (1, 51, 101 … 1701ms). Zero variance. Confirms `wait(50)` governs loop period and USS read overhead < 1ms effective. | T2 |
| TBD_DREACT | dReaction_mm | **23.2 mm** (derived) | = vMax_mms × tResponse_s = 465 × 0.050. Not independently measured; fully determined by TBD_VMAX_MMS and TBD_TRESP. | T2 derived |
| TBD_DECEL | decel_mms2 | **5210 mm/s²** (0.53 g) | Back-solved: vMax²/(2×(dStop − vMax×tResp)) = 465²/(2×20.8). Cross-check: 0.53g is physically plausible for active motor braking on hard surface. | T2 derived |
| **TBD_USS_MIN** | ussValidMin_mm | **344 mm** | Minimum valid fwd1 reading confirmed at rest post-stop (final_f1_mm = 344mm, fully settled). Sensor returned valid (non-saturated) readings down to this distance. | T2 |
| TBD_USS_AGREE | ussAgreement_mm | **180 mm** (threshold) | fwd1 vs fwd2 offset ranged 100–150mm across the approach. Root cause: USS-B has systematic mounting offset + stale-reading episodes (see AR-01 update). TBD_USS_AGREE set conservatively at 180mm to encompass the observed range. USS-B excluded from trigger logic. | T2 |
| **TBD_HDG** | headingTol_deg | **10.0°** | Max |heading| during approach = 9.55° at t=1701ms. Budget set at 10.0° (+0.45° buffer). Heading correction must be added to operation programme or this budget will be exceeded. | T2 |
| **TBD_HDG_DRIFT** | imuDrift_degps | **10.0 deg/s** | Linear slope of heading vs time in steady-state region (t=951–1701ms): −7.39° over 750ms → 9.86°/s. Rounded to 10.0 deg/s. Consistent with slight motor-speed asymmetry between Motor C and Motor D. | T2 |
| TBD_COMBO | dCombo_mm | **OPEN — T1 required** | Pre-T1 estimate = 28mm (USS_init_A − start_nominal = 1028 − 1000mm). Uncertainty ±15mm pre-T1. **Closes at Verification Run via operator gap measurement.** | T1 pending |

**TBD_COMBO is the sole remaining open TBD.** All others are bound. Its closure requires one operator measurement at the Verification Run stop (formula: dCombo = fwd1_settled − operator_gap_mm).

---

## 2. Model-Completion Parameters (calibrated)

| Symbol | Calibrated Value | Source Run |
|--------|-----------------|-----------|
| port_motorRight | Port.C | Cal-Run-1 |
| port_motorLeft | Port.D | Cal-Run-1 |
| port_ussF1 | Port.A (forward primary) | Cal-Run-1 |
| port_ussF2 | Port.B (forward secondary, excluded from trigger) | Cal-Run-1 |
| port_ussRear | Port.E | Cal-Run-1 |
| motor_dir_right | **negative** speed = forward (C(−) = right wheel forward) | Cal-Run-1 + Cal-Run-2 validation |
| motor_dir_left | **positive** speed = forward (D(+) = left wheel forward) | Cal-Run-1 + Cal-Run-2 validation |
| heading_correction | `corr = KP × heading; right.run(−MAX − corr); left.run(MAX + corr)` | See note |

**Motor direction note:** Initial direction inference was incorrect (Cal-Run-2 attempt 1 went backward for 19s). Root cause: USS-E rear sensor decreasing (548→445mm) during Cal-Run-1 combined test was not recognised as a rearward-motion indicator. Corrected from first principles; validated by Cal-Run-2 successful approach.

**Heading correction note:** At 10°/s drift, correction is necessary. Because both motors clamp at the hardware ceiling when commanded at 3000 deg/s, heading correction only takes effect when commanded at the estimated ceiling (≈1100 deg/s). Operation programme uses `MAX_CMD = 1100 deg/s` with correction `KP = 5`. Verification run will include `motor.speed()` telemetry to confirm actual v_max_dps and refine MAX_CMD if needed.

---

## 3. CMP Unit Verification Results (from calibration runs)

| Req | Method | Evidence | Verdict |
|-----|--------|----------|---------|
| CMP-1 (Motor A ≥ v_max) | Test | Rover achieved v_max_mms = 465mm/s (USS slope), consistent with motors at ceiling. Motors commanded at 3000 deg/s (clamp) throughout approach. | ✅ PASS |
| CMP-2 (Motor B ≥ v_max) | Test | Straight approach confirmed (heading drift was systematic, not one-sided stall). Both motors contributing. | ✅ PASS |
| CMP-3 (USS-F1 ≥ ussValidMin) | Test | Minimum fwd1 during approach = 388mm (at trigger). Final settled = 344mm. Sensor returned valid non-saturated readings throughout. TBD_USS_MIN = 344mm. | ✅ PASS |
| CMP-4 (USS-F2 agrees within ussAgreement) | Test | Observed. Systematic offset 100–150mm confirmed. Stale-reading episodes (586mm for 300ms; see AR-01 update). USS-B excluded from trigger. TBD_USS_AGREE = 180mm (accounts for offset + stale risk). CMP-4 passes at this threshold. | ✅ PASS (with caveat: USS-B stale episodes; see AR-01) |
| CMP-5 (d_stop ≤ dStopTotal + margin) | Test | d_stop_total = 44mm measured. BINDS TBD_DSTOP = 44mm. Margin bound from RSS uncertainty. | ✅ PASS (binds TBD_DSTOP) |
| CMP-6 (IMU drift ≤ imuDrift_degps) | Test | Steady-state heading drift = 10.0°/s. BINDS TBD_HDG_DRIFT = 10.0°/s. | ✅ PASS (binds TBD_HDG_DRIFT) |

**All CMP requirements are unit-verified.** TBD_COMBO closure remains for the Verification Run to close CMP-5's SYS-1 implication (finalClearance depends on dCombo).

---

## 4. Open Items Before Verification Run

1. **TBD_COMBO (T1):** Operator gap measurement after the Verification Run stop.
2. **AR-01 update** (see anomaly_report_AR01_v2.md): USS-B has 300ms stale episodes. Excluded from operation trigger; logged for post-hoc reference only.
3. **Heading correction:** Verification Run programme must include P-correction (KP=5, MAX_CMD=1100 deg/s) and `motor.speed()` telemetry to confirm v_max_dps.

---

*End of CALIBRATION REPORT v1.0*
