# CALIBRATION PLAN — Rover Wall-Stop System
**Document type:** PLAN (forward-looking; revised and re-issued if any characterisation run falsifies current content)  
**Version:** 1.0  **Status:** BASELINE  **Date:** 2026-07-21  
**Gate:** A  
**References:** requirements_spec_v1.md · sysml_model_v1.sysml · executable_model_v1.py  

---

## Section 0 — Sensitivity Analysis (REQUIRED TABLE, opens the Plan)

This section justifies everything that follows: what to measure, where to spend the one costed T1 operator measurement, and in what order.

### 0.1 Physics model (summary)

The executable model defines the final gap as:

```
final_gap_mm = d_trigger_uss - d_combo - d_stop - d_reaction

where:
  d_trigger_uss   = USS reading that triggers the brake command       [TBD_TRIGGER]
  d_combo         = d_front_offset + uss_bias   (combined sensor offset) [TBD_COMBO]
  d_stop          = distance traveled from brake command to v=0          [TBD_DSTOP]
  d_reaction      = vMaxRover_mms × loopPeriod_ms / 1000               [TBD_DREACT]
```

We set `d_trigger_uss = d_stop + d_reaction + d_combo + safety_margin` to achieve `final_gap = safety_margin`.  
If any parameter differs from its calibrated value, the gap error equals that difference (sign preserving):  
`gap_error = −δd_stop − δd_combo − δd_reaction`

The pre-calibration gap uncertainty (RSS of ±half-range for each parameter) is ≈ **138 mm** — far exceeding the ~1000 mm start distance. **Every parameter in the table below must be calibrated before the program is safe to operate.**

### 0.2 Required Sensitivity Table

Computed by `executable_model_v1.py → sensitivity_analysis()`. Nominal priors: `dStop=150mm, dCombo=50mm, loopPeriod=50ms, vMaxRover=500mm/s`.

| Parameter | Assumed Prior Range | Gap Sensitivity Over Range | Current-Knowledge Tier | Resulting Priority |
|-----------|--------------------|-----------------------------|------------------------|-------------------|
| **dStop_mm** | [50, 300] mm | **±125 mm** on objective; ±125 mm on no-contact margin | T0 — Prior only (no onboard proxy available without hardware) | **P1 CRITICAL** — highest leverage, completely unknown; must be measured on this rover on this surface |
| **dCombo_mm** | [0, 100] mm | **±50 mm** on objective; ±50 mm on margin | T0 — Prior only (geometric + bias; no onboard proxy; requires T1 ground truth to close) | **P2 HIGH** — second-highest leverage; single T1 operator measurement required |
| **loopPeriod_ms** | [20, 100] ms | **±40 mm** at v=500mm/s | T0 → T2 (measured cheaply from hub-clock timestamps in same run) | **P3 HIGH** — free to upgrade to T2 in Cal-Run-2; no cost |
| **vMaxRover_mms** | [200, 700] mm/s | **25 mm** via d_reaction only; also controls d_stop scale via v² | T0 → T2 (slope of USS vs. time during steady-state) | **P4 MEDIUM-HIGH** — secondary on d_reaction; primary driver of d_stop magnitude |
| **uss_noise_1σ** | [1, 30] mm | **run-to-run variance** only; ≤30 mm 1σ | T0 → T2 (residuals of USS linear fit) | **P5 MEDIUM** — affects margin budget, not systematic gap |

**Key conclusions driving the plan:**
1. `dStop_mm` is the dominant uncertainty by 2.5×. It can only come from hardware. It is P1.
2. `dCombo_mm` requires one operator T1 measurement (gap measurement after the verification run). This is the only costed outside input requested.
3. `loopPeriod_ms` and `vMaxRover_mms` are free T2 upgrades inside Cal-Run-2.
4. Pre-calibration RSS ≈ 138 mm → contact near-certain without calibration. Post-calibration target RSS ≈ 9 mm (assuming δd_stop=5mm, δd_combo=5mm, δd_reaction=2mm, δuss_noise=5mm).

---

## Section 1 — Calibration Input List

### 1.1 TBD Register (from requirements_spec_v1.md)

| TBD ID | Parameter | Calibrating Run | Source Tier |
|--------|-----------|----------------|-------------|
| TBD_VMOT | vMaxRated_dps | Cal-Run-2 | T2 |
| TBD_VMAX_MMS | vMaxRover_mms | Cal-Run-2 | T2 |
| TBD_DSTOP | dStop_mm | Cal-Run-2 | T2 |
| TBD_LOOP | loopPeriod_ms | Cal-Run-2 | T2 |
| TBD_DREACT | dReaction_mm | Cal-Run-2 (derived) | T2 |
| TBD_COMBO | dCombo_mm | Verification Run + T1 operator | T1 |
| TBD_TRIGGER | dTrigger_mm | Model (derived post-cal) | Derived |
| TBD_USS_MIN | ussValidMin_mm | Cal-Run-2 | T2 |
| TBD_USS_AGREE | ussAgreement_mm | Cal-Run-2 | T2 |
| TBD_HDG | headingTol_deg | Cal-Run-2 | T2 |
| TBD_HDG_DRIFT | imuDrift_dps_s | Cal-Run-2 | T2 |

### 1.2 Model-Completion Parameters (not named in requirements, needed for the model)

| Symbol | Description | Binding Source |
|--------|-------------|----------------|
| port_motorA | Port for Motor A | Cal-Run-1 |
| port_motorB | Port for Motor B | Cal-Run-1 |
| port_ussF1 | Port for forward USS primary | Cal-Run-1 |
| port_ussF2 | Port for forward USS secondary | Cal-Run-1 |
| motor_dir_A | Direction convention for Motor A (+1 or −1) | Cal-Run-1 |
| motor_dir_B | Direction convention for Motor B (+1 or −1) | Cal-Run-1 |
| heading_kp | Heading P-gain for correction | Cal-Run-2 (from heading residuals) |

---

## Section 2 — Channel Catalog & Cross-Sourcing

For every quantity, all independent onboard channels are enumerated. Channels with no required quantity drop out (per REQUIREMENTS METHOD Rule 7).

### 2.1 Forward Distance to Wall (primary quantity — SYS-1/2)

| Channel | Device | Directness | Confidence | Valid Range | Binding Run |
|---------|--------|-----------|-----------|------------|-------------|
| USS-F1.distance() | UltrasonicSensor (forward) | Direct | HIGH | [TBD_USS_MIN, 2000] mm | Cal-Run-2 |
| USS-F2.distance() | UltrasonicSensor (forward, 2nd) | Direct | HIGH | [TBD_USS_MIN, 2000] mm | Cal-Run-2 |
| hub.imu.heading() integrated + v_max | Hub IMU (indirect) | Indirect (dead-reckoning) | LOW (drift accumulates) | Limited by drift | Cal-Run-2 (cross-check only) |

**Cross-sourcing rule:** Both USS-F1 and USS-F2 are logged every loop. Disagreement > TBD_USS_AGREE flags a sensor fault. IMU dead-reckoning is not trusted as primary distance source (drift rate TBD_HDG_DRIFT is non-zero); it cross-checks heading only.

**Hand-off:** If USS reading falls below TBD_USS_MIN (sensor saturates at close range), the program must have already braked. Plan: trigger at ≥ 2× TBD_USS_MIN to avoid reliance on saturated range.

### 2.2 Rover Speed (v_max)

| Channel | Device | Directness | Confidence | Binding Run |
|---------|--------|-----------|-----------|------------|
| Δ(USS-F1) / Δt from hub clock | USS-F1 + hub clock | Direct (slope fit) | HIGH | Cal-Run-2 |
| Δ(USS-F2) / Δt from hub clock | USS-F2 + hub clock | Direct (slope fit, cross-check) | HIGH | Cal-Run-2 |

### 2.3 Stopping Distance (d_stop)

| Channel | Device | Directness | Confidence | Binding Run |
|---------|--------|-----------|-----------|------------|
| USS-F1_trigger − USS-F1_settled | USS-F1 + hub clock | Direct (Δ reading) | HIGH | Cal-Run-2 |
| USS-F2_trigger − USS-F2_settled | USS-F2 + hub clock | Direct (cross-check) | HIGH | Cal-Run-2 |

**Physical plausibility bound:** d_stop must be in (1, 800) mm. Any reading outside this range is impossible → escalate unconditionally.

### 2.4 Heading (for SYS-5)

| Channel | Device | Directness | Confidence | Binding Run |
|---------|--------|-----------|-----------|------------|
| hub.imu.heading() | Built-in IMU (yaw) | Direct | MEDIUM (temp/drift) | Cal-Run-2 |

No independent cross-source for heading available on this rover. Heading is logged for anomaly detection only; the model uses it for P-control, not distance.

### 2.5 Combined Sensor Offset (d_combo)

| Channel | Source | Directness | Confidence | Binding Run |
|---------|--------|-----------|-----------|------------|
| Operator measurement: gap after stop | Physical ruler | Direct (T1) | HIGHEST | Verification Run |
| USS_final_reading − operator_gap | USS-F1 + T1 | Cross-check | T1-anchored | Verification Run |

**This is the sole T1 measurement requested.** The formula `d_combo = USS_F1_final_reading − operator_gap_measured` directly binds TBD_COMBO from the verification run.

---

## Section 3 — Source-of-Truth Hierarchy

```
T1 (HIGHEST): Operator measurement with physical instrument
              → Used for: dCombo_mm (gap after verification run)

T2:           Multi-sample onboard calibration anchored to T1 reference
              → Used for: dStop_mm (ΔUSS over ≥3 runs), vMaxRover_mms,
                loopPeriod_ms, heading drift

T3:           Single onboard sample
              → Used for: initial readings in Cal-Run-1 (exploratory only)
              → Never used to set a safety-critical parameter alone
```

**Rules:**
- A T2 value is NEVER silently re-fit by a later T3 sample. If a T3 sample disagrees with T2 by more than 2× uss_noise_1σ, it is an anomaly to diagnose.
- `dCombo_mm` (T1-anchored) cannot be overridden by any USS reading alone.
- Any re-calibration of a T1-anchored parameter requires another T1 measurement. No exceptions.

---

## Section 4 — Characterisation Run Design

### Overview

| Run | Label | Purpose | Safety trigger distance | Duration |
|-----|-------|---------|------------------------|---------|
| Cal-Run-1 | Port Discovery | Port map, motor direction, initial USS readings | N/A (no full approach) | ~20 s |
| Cal-Run-2 | Speed + Stop Cal | Bind: dStop, vMax, loopPeriod, USS valid range, heading drift | 400 mm (conservative) | ~15 s |
| *Verification* | Verif-Run | Integrated test + T1 operator measurement → dCombo | d_trigger (calibrated) | ~10 s |

**Total hardware runs: 2 calibration + 1 verification = 3 runs.** (Plus 5 scored operation runs.)

---

### Cal-Run-1: Port Discovery

**Objectives:**
- Identify device at each of ports A–F (Motor / USS / ColorSensor / unknown).
- For each motor found: run briefly, measure IMU heading response to determine turning direction.
- For each USS found: read initial distance to identify forward-facing sensors (should read ~1000 mm at start).
- Determine motor polarity: which combination of signs drives the rover toward the wall (forward USS distance decreases).

**Test-like-you-fly compliance:** This is a discovery run, not a speed run. No full-speed approach. Nonetheless the hub-clock and emit() infrastructure is identical to what will be used in operation.

**Program sketch:**
```python
# Probe each port in order: try Motor → USS → ColorSensor
# For motors found: pulse 200 deg/s for 0.5 s, log heading delta
# For USS found: log distance reading (identifies forward sensors by ~1000mm reading)
# Goal: emit port_type, uss_reading, heading_delta for each port
```

**Data logged:**
- `device_<port>`: 1=Motor, 2=USS, 3=Color, 0=none
- `uss_reading_<port>`: USS distance at each USS port
- `heading_post_motor_<port>`: heading after brief motor test
- `color_reflection_<port>`: if color sensor found

**Analysis:**
- Forward USS = ports reading ~900–1100 mm (at start line ~1000 mm from wall).
- Rear USS = port reading a different distance (varies).
- Motor direction = from sign of heading change after pulsing each motor.

**Expected outcome:** Full port map, motor sign convention, forward USS identification.

**Anomaly checks (physically impossible → escalate unconditionally):**
- Any USS reading < 10 mm at start line: sensor backwards or broken.
- Heading > 45° from motor pulse at 200 dps for 0.5 s: likely not a motor port.

---

### Cal-Run-2: Speed + Stopping Characterisation (test-like-you-fly)

**Objectives:**
- Bind: dStop_mm, vMaxRover_mms, loopPeriod_ms, dReaction_mm.
- Characterise: USS-F1 vs. USS-F2 spread (→ TBD_USS_AGREE), USS valid min (→ TBD_USS_MIN).
- Characterise: heading drift and max deviation (→ TBD_HDG, TBD_HDG_DRIFT).
- Unit-verify CMP-1/2 (motor speed ≥ v_max_rated), CMP-3/4 (USS valid range), CMP-6 (IMU drift).

**Architecture (test-like-you-fly):**  
Identical skeleton to the operation program. All logging deferred OFF the hot path — buffer all readings to a list in memory, flush to `emit()` AFTER motors stop. This ensures calibration timing fidelity = operation timing fidelity.

**Safety trigger:** 400 mm (well above the nominal d_stop prior of 50–300 mm). Chosen to be conservative for the first full-speed characterisation run.

**Hot path (inside the loop, no I/O):**
```python
buf = []
while True:
    t = clock.time()
    d1 = ussF1.distance()
    d2 = ussF2.distance()
    h  = hub.imu.heading()
    buf.append((t, d1, d2, h))           # buffered — NOT emitted here
    
    # Heading correction (P-control; kp from Cal-Run-1)
    corr = HEADING_KP * h
    motorA.run(MOTOR_A_DIR * MAX_SPEED + corr)
    motorB.run(MOTOR_B_DIR * MAX_SPEED - corr)
    
    if d1 <= TRIGGER_400MM:
        motorA.brake()
        motorB.brake()
        break
    wait(LOOP_MS)
```

**Post-stop (dump, no timing constraint):**
```python
wait(3000)              # let rover settle fully
d1_final = ussF1.distance()
d2_final = ussF2.distance()
for (t, d1, d2, h) in buf:
    emit('fwd1', d1); emit('fwd2', d2); emit('heading', h)
# Also emit final settled readings + timestamps for dStop derivation:
emit('trigger_reading_f1', trigger_d1)
emit('trigger_t_ms', trigger_t)
emit('final_f1', d1_final)
emit('final_f2', d2_final)
```

**Derived calibration quantities (computed from telemetry post-run):**

| Quantity | Derivation | Unit-req verified |
|----------|-----------|-------------------|
| v_max_mms | Linear fit slope of USS-F1 vs. t (steady-state phase, last 300mm before trigger) | CMP-1/2 (motor at rated speed) |
| d_stop_mm | trigger_reading_f1 − final_f1 | CMP-5 |
| loop_period_ms | Median Δt between consecutive buffer entries | — |
| d_reaction_mm | v_max_mms × loop_period_ms / 1000 | CMP-5 |
| uss_agree_mm | Max |F1-F2| across the approach | CMP-4 |
| uss_valid_min | Min of min(F1, F2) observed | CMP-3 |
| heading_max | Max |heading| during approach | SYS-5 |
| imu_drift_dps | Slope of heading vs. t during straight approach | CMP-6 |

**Anomaly checks:**
- d_stop_mm < 1 or > 800: physically impossible → escalate.
- USS-F1 and USS-F2 disagree by > 50 mm at the same timestamp: one sensor faulty.
- Heading > 30° during straight approach: motor direction or polarity problem.
- v_max_mms < 50 or > 1500: out of physical bounds → escalate.

---

## Section 5 — Outside-Input Requests

**One T1 measurement requested, timed to the Verification Run:**

> After the Verification Run, when the rover has come to a complete stop, please measure the physical gap between the rover's front face and the wall surface (in mm). Report to the nearest mm.

**Justification (from sensitivity table):**  
`dCombo_mm` has ±50 mm leverage on the final gap — second-highest of all parameters. No onboard channel can resolve it independently because `d_front_offset` (a geometric constant) and `uss_bias` (a systematic sensor error) enter identically into the final-gap equation, making them unobservable separately. Their sum `d_combo = d_front_offset + uss_bias` is observable only by comparing the USS reading when stopped with the true gap from an independent source (the ruler).

**Formula:** `dCombo_mm = USS_F1_settled_reading − operator_gap_mm`

No other T1 measurements are requested. All other TBDs are bound from onboard T2 telemetry.

---

## Section 6 — Verification Support

### 6.1 How Calibration Supports Verification

| Calibration output | Supports | Verification method |
|-------------------|---------|---------------------|
| Cal-Run-1: port map | All CMPs (port-specific tests) | Inspection (program uses correct ports) |
| Cal-Run-2: d_stop | CMP-5 (stopping distance), SYS-1 (no contact) | Test (CMP-5 unit-verified in Cal-Run-2; SYS-1 in Verif-Run) |
| Cal-Run-2: v_max_mms | CMP-1/2 (motor speed), SYS-3 | Test (speed telemetry during approach) |
| Cal-Run-2: loop_period | CMP-5 (d_reaction) | Analysis (derived) |
| Cal-Run-2: heading | CMP-6, SYS-5 | Test (heading telemetry) |
| Verif-Run + T1: d_combo | SYS-1, SYS-2 (objective) | Test + T1 measurement (closes objective at operating point) |

### 6.2 Verification Argument Structure (pre-run skeleton)

The Verification Plan (GATE B deliverable) will populate the following with calibrated values:

```
STK-1 (no contact)
  └─ SYS-1 (clearance ≥ 0mm)
       ├─ FUN-2 / CMP-3/4 (USS valid readings)     → unit-verified Cal-Run-2 [OPEN]
       └─ FUN-3 / CMP-5 (stopping distance)         → unit-verified Cal-Run-2 [OPEN]
            MODEL: gap = d_trigger - d_combo - d_stop - d_reaction
                       = [TBD_TRIGGER] - [TBD_COMBO] - [TBD_DSTOP] - [TBD_DREACT]
                       = [TBD] mm    (must be ≥ 0)
STK-3 (max speed)
  └─ SYS-3 / FUN-1 / CMP-1/2                       → unit-verified Cal-Run-2 [OPEN]
STK-2 (minimise gap)
  └─ SYS-2 (objective gap)
            OBJECTIVE: predicted gap = [TBD] mm      → validated vs. T1 at Verif-Run [OPEN]
```

All `[OPEN]` fields close at GATE B with calibrated values. No requirement may be asserted-without-evidence.

### 6.3 CMP Unit-Verification Plan (in Cal-Run-2)

| CMP | Claim | Evidence from Cal-Run-2 | Pass criterion |
|-----|-------|------------------------|----------------|
| CMP-1 | Motor A ≥ v_max_rated | v_max from USS slope | slope ≥ (nominal − 10%) |
| CMP-2 | Motor B ≥ v_max_rated | Same (straight-line confirms both running) | idem |
| CMP-3 | USS-F1 valid [uss_min, 2000] | Min USS reading during approach | No saturation above min |
| CMP-4 | USS-F2 agrees F1 within uss_agree | Max |F1−F2| | < TBD_USS_AGREE |
| CMP-5 | d_stop ≤ d_stop_nominal + margin | trigger_reading − final_reading | BINDS TBD_DSTOP |
| CMP-6 | IMU drift ≤ TBD_HDG_DRIFT | heading slope during approach | BINDS TBD_HDG_DRIFT |

---

## Section 7 — Safety and Go/No-Go Gate

Before the Verification Run, the following conditions must all be met:

1. All T2 TBDs bound from Cal-Run-2 telemetry (no None values remaining except TBD_COMBO).
2. Predicted d_trigger = d_stop + d_reaction + d_combo_prior + safety_margin_mm (where safety_margin ≥ 3× RSS uncertainty at this point).
3. No open anomalies from Cal-Run-1 or Cal-Run-2.
4. CMP-1 through CMP-6 unit-verified (except CMP-5 which carries TBD_COMBO — closes at Verif-Run).
5. Executable model EVALUATE returns `SYS-1_no_contact_PASS: True` at the planned d_trigger.

---

*End of CALIBRATION PLAN v1.0*
