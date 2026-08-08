# VERIFICATION PLAN — Rover Wall-Stop System
**Document type:** PLAN (frozen prediction; must not be edited after freezing; re-issued as new version if re-derived)  
**Version:** 1.0  **Status:** FROZEN — predictions committed before the Verification Run  
**Date frozen:** 2026-07-21  
**Gate:** B  

> **FREEZE STATEMENT:** This document is frozen at Gate B. The predictions below are the output of the executable analysis model (executable_model_v2.py) evaluated at the calibrated configuration. No integrated result may edit this version. If the Verification Run falsifies a prediction, a new version will be issued (see revision protocol at end).

---

## 1. Committed Configuration

All parameters from the Calibration Report, bound as follows:

| Parameter | Committed Value | Source |
|-----------|----------------|--------|
| vMax_mms | 465 mm/s | Cal-Run-2 USS slope fit (T2) |
| tResponse_s | 0.050 s | Cal-Run-2 hub-clock (exact, T2) |
| dStopTotal_mm | 44 mm | Cal-Run-2 ΔUSS at brake (T2) |
| dReaction_mm | 23.2 mm | Derived: 465 × 0.050 |
| dCombo_mm | **28 mm (PRE-T1 ESTIMATE)** | USS_init_A − start_nominal; ±15mm uncertainty |
| safetyMargin_mm | 50 mm | Design choice (generous for first integrated run) |
| d_trigger_verif | **122 mm** | = dStopTotal + dCombo_est + safetyMargin = 44+28+50 |
| σ_dStopTotal | 5 mm | Estimated run-to-run (single Cal-Run-2 sample) |
| σ_dCombo | 15 mm | Pre-T1 uncertainty in d_combo estimate |
| σ_dReaction | 2 mm | Propagated from v_mms uncertainty (±30mm/s) |
| σ_ussNoise | 10 mm | USS noise + stale risk margin |

**Note on dCombo:** TBD_COMBO is the only unbound T1 parameter. The 28mm estimate carries ±15mm uncertainty and will be replaced by the T1 measurement at the Verification Run stop. The predictions below are conditional on this estimate; after T1 binds dCombo, the predictions are retroactively closeable against the T1 evidence.

---

## 2. Frozen Predictions (model output at committed configuration)

Produced by: `executable_model_v2.py → evaluate(d_trigger=122.0, with_uncertainty=True)`

### 2.1 Performance quantity

| Quantity | Predicted Value | 1σ Band | 1σ Worst-Case |
|----------|----------------|---------|---------------|
| **Final gap (front face to wall)** | **50 mm** | ±19 mm | 31 mm |

The 3σ worst-case is −6 mm (contact risk at 3σ). This is expected pre-T1 because σ_dCombo = 15mm dominates the RSS. After T1 binds dCombo (σ_dCombo expected to drop to ~3mm), the RSS will fall to ~6mm, and the 3σ worst-case will rise to 50 − 3×6 = +32mm — safely clear.

### 2.2 Requirement predicted pass/fail

| Requirement | Predicted | Basis |
|-------------|-----------|-------|
| STK-1 / SYS-1 (no contact) | **PASS** | gap_mean = 50mm >> 0; 1σ worst = 31mm > 0 |
| SYS-1 1σ margin | **PASS** | 31mm > 0 |
| SYS-1 3σ margin | **FAIL** (pre-T1 only) | −6mm < 0 due to σ_dCombo = 15mm; expected to pass once T1 binds dCombo |
| SYS-2 (objective gap) | 50 mm (pre-T1 estimate; to be revised for operation) | Graded; not pass/fail |
| SYS-3 (max speed) | **PASS** | Programmatic: motor commands = MAX_CMD = 1100 deg/s |
| SYS-4 (no resume) | **PASS** | Inspection: brake() only, no run() after trigger |
| SYS-5 (heading ≤ 10°) | **PASS** | Heading correction included (KP=5); expected drift < 5° with correction |
| CMP-1 (Motor A ≥ v_max) | **PASS** | Logged via motor.speed() in Verif-Run |
| CMP-2 (Motor B ≥ v_max) | **PASS** | Symmetric |
| CMP-3 (USS-F1 ≥ 344mm valid) | **PASS** | Trigger fires at 122mm << 344mm (valid range not challenged) |
| CMP-4 (USS-F2 agreement) | **PASS** | TBD_USS_AGREE = 180mm; USS-B excluded from trigger |
| CMP-5 (d_stop ≤ dStopTotal) | **PASS** | d_trigger set from calibrated dStopTotal = 44mm |
| CMP-6 (IMU drift ≤ 10°/s) | **PASS** | Confirmed T2 at 10°/s in Cal-Run-2 |

### 2.3 Summary roll-up

- **Hard-constraint requirements (STK-1, SYS-1, SYS-3, SYS-4, SYS-5, CMP-1–6):** All predicted **PASS**.
- **SYS-1 3σ margin:** Predicted FAIL pre-T1; expected to pass once T1 reduces σ_dCombo.
- **Objective (SYS-2):** 50mm predicted gap; to be minimised in operation by reducing safetyMargin once dCombo is T1-bound.

---

## 3. Verification Programme Constants (committed before run)

```python
MAX_CMD    = 1100    # deg/s — estimated ceiling; motor.speed() will confirm
TRIGGER_MM = 122     # mm — USS-A reading at which to command brake
HEADING_KP = 5       # deg/s correction per degree of heading error
LOOP_MS    = 50      # ms (confirmed from Cal-Run-2)
SETTLE_MS  = 3000    # ms after braking

# Motor directions (calibrated):
# motor_right (Port C): run at -MAX_CMD (negative = right wheel forward)
# motor_left  (Port D): run at +MAX_CMD (positive = left wheel forward)
# Heading correction:
#   corr = HEADING_KP * hub.imu.heading()
#   motor_right.run(-MAX_CMD + corr)
#   motor_left.run( MAX_CMD + corr)
```

---

## 4. T1 Measurement Request (at Verification Run stop)

After the rover comes to a complete stop:

> **Please measure the gap between the rover's front face and the wall surface in mm (to the nearest mm) and report it.**

This single measurement closes TBD_COMBO:
`dCombo_mm = final_fwd1_reading − operator_gap_mm`

---

## 5. Revision Protocol

If the Verification Run falsifies this prediction:
1. Diagnose the responsible parameter (compare predicted vs measured gap → residual identifies which term is wrong).
2. Re-derive: bind the revised parameter in the executable model, re-run EVALUATE.
3. Issue Verification Plan v2 (this v1 remains as the frozen record of what was predicted before the first run).
4. Take another Verification Run against v2. Each re-run counts toward the programme score.

---

*End of VERIFICATION PLAN v1.0 — FROZEN*
