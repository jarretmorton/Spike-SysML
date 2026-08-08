# CALIBRATION PLAN — Rover Wall-Stop System
**Document type:** PLAN  
**Version:** 1.1  **Status:** BASELINE  **Date:** 2026-07-21  
**Changes from v1.0:** Parameter names aligned to rover_generic.sysml.
  - TBD_LOOP (loopPeriod_ms) → TBD_TRESP (tResponse_s); same calibration method
  - TBD_DREACT now *derived* (vMax_mms × tResponse_s); no standalone calibration row
  - TBD_DECEL added as back-solved optional
  - Section 0 sensitivity table updated to v2 parameter names
  - Section 2 channel catalog updated: DistanceSensor, InertialUnit
  - Note on RotationToSpeed: k_mmrad is implicit in the vMax_mms measurement
  - **Run design UNCHANGED: 2 cal runs + 1 verification run; operator measurement
    unchanged; sensitivity rankings unchanged**

---

## Section 0 — Sensitivity Analysis

*Identical conclusions to v1.0; parameter names updated.*

### 0.1 Model (v2 parameter names)

```
finalClearance_mm = dTrigger_mm − dCombo_mm − dStopTotal_mm

where:
  dTrigger_mm    = dStopTotal_mm + dCombo_mm + safetyMargin_mm
  dStopTotal_mm  = vMax_mms × tResponse_s + vMax_mms² / (2 × decel_mms2)
                   [measured directly at operating point — zero extrapolation]
  dCombo_mm      = d_front_offset + uss_bias_systematic
  dReaction_mm   = vMax_mms × tResponse_s   [derived; part of dStopTotal]
```

### 0.2 Sensitivity Table (v2 names)

Output of `executable_model_v2.py → sensitivity_table_v2()`.  
All parameters held at prior nominals; trigger re-computed optimally at each point.

| Parameter (v2) | Assumed Prior Range | Gap Sensitivity Over Range | Knowledge Tier | Priority |
|----------------|--------------------|-----------------------------|----------------|---------|
| **dStopTotal_mm** | [50, 300] mm | **±125 mm** on objective; ±125 mm on no-contact margin | T0 — prior only; no onboard proxy before hardware run | **P1 CRITICAL** |
| **dCombo_mm** | [0, 100] mm | **±50 mm** | T0 → T1 via one operator measurement | **P2 HIGH** |
| **tResponse_s** | [0.020, 0.100] s | **±40 mm** at v=500 mm/s | T0 → T2 via hub-clock timestamps (free) | **P3 HIGH** |
| **vMax_mms** | [200, 700] mm/s | **25 mm** via dReaction; also sets dStop scale via v² | T0 → T2 via USS slope (free) | **P4 MEDIUM-HIGH** |

**Pre-calibration RSS:** √(125²+50²+40²+15²) ≈ **138 mm** — contact near-certain without calibration.  
**Post-calibration target RSS:** √(5²+5²+2²+5²) ≈ **9 mm** after binding all parameters.

### 0.3 RotationToSpeed note (new in v1.1)

`RelationTemplates::RotationToSpeed` defines `vMax = motorSpeed × k` where  
`k` [mm/rad] bundles wheel radius + gear ratio + slip. Per the template:  
*"The constant bundles wheel radius, gear ratio AND slip, which is exactly why it  
is calibrated, not computed."*  

v1.0 incorrectly implied derivation from wheel diameter alone. Fix: `vMax_mms` is  
calibrated **directly** from the USS-F1 slope (zero-extrapolation at the single  
operating point). `k_mmrad` is then implicit: `k = vMax_mms / vMaxRated_radps`.  
`k` is a model attribute but is **not a standalone calibration target**.  
No additional calibration run or operator input is needed.

---

## Section 1 — Calibration Input List (v2)

### 1.1 TBD Register

| TBD ID | v2 Parameter | Cal Run | Source Tier |
|--------|-------------|---------|-------------|
| TBD_VMOT | vMaxRated_dps | Cal-Run-2 | T2 |
| TBD_VMAX_MMS | vMax_mms | Cal-Run-2 (USS slope) | T2 |
| TBD_DSTOP | dStopTotal_mm | Cal-Run-2 (ΔUSS trigger→settled) | T2 |
| TBD_TRESP | tResponse_s | Cal-Run-2 (median inter-sample Δt) | T2 |
| TBD_DECEL | decel_mms2 | Derived: vMax²/(2×(dStop−vMax×tResp)) | T2 derived |
| TBD_COMBO | dCombo_mm | Verification Run + T1 operator | **T1** |
| TBD_TRIGGER | dTrigger_mm | Model output | Derived |
| TBD_USS_MIN | ussValidMin_mm | Cal-Run-2 | T2 |
| TBD_USS_AGREE | ussAgreement_mm | Cal-Run-2 | T2 |
| TBD_HDG | headingTol_deg | Cal-Run-2 | T2 |
| TBD_HDG_DRIFT | imuDrift_degps | Cal-Run-2 | T2 |

*(TBD_DREACT removed: dReaction_mm is now derived from TBD_VMAX_MMS and TBD_TRESP, not a separate TBD.)*

### 1.2 Model-Completion Parameters (unchanged)

| Symbol | Description | Source |
|--------|-------------|--------|
| port_motorA | Port for DriveMotor A | Cal-Run-1 |
| port_motorB | Port for DriveMotor B | Cal-Run-1 |
| port_ussF1 | Port for DistanceSensor forward primary | Cal-Run-1 |
| port_ussF2 | Port for DistanceSensor forward secondary | Cal-Run-1 |
| motor_dir_A | Sign convention for Motor A | Cal-Run-1 |
| motor_dir_B | Sign convention for Motor B | Cal-Run-1 |
| heading_kp | Heading P-gain | Cal-Run-2 (from heading residuals) |

---

## Section 2 — Channel Catalog & Cross-Sourcing (v2 type names)

### Forward Distance (primary — SYS-1/2)

| Channel | rover_generic Type | Confidence | Valid Range | Binding Run |
|---------|-------------------|-----------|------------|------------|
| ranger[fwd1].range (USS-F1) | DistanceSensor | HIGH | [TBD_USS_MIN, 2000] mm | Cal-Run-2 |
| ranger[fwd2].range (USS-F2) | DistanceSensor | HIGH | [TBD_USS_MIN, 2000] mm | Cal-Run-2 |
| imu.forwardAccel integrated | InertialUnit | LOW (dead-reckoning only) | Cross-check | Cal-Run-2 |

### Rover Speed (vMax_mms — RotationToSpeed binding)

| Channel | Derivation | Tier |
|---------|-----------|------|
| Δ(USS-F1) / Δt (hub-clock) | Linear slope fit during steady-state approach | T2 |
| Δ(USS-F2) / Δt (cross-check) | Must agree within ussAgreement_mm | T2 |

### Stopping Distance (dStopTotal — StoppingDistance binding)

| Channel | Derivation | Tier |
|---------|-----------|------|
| USS-F1_trigger_reading − USS-F1_settled_reading | Direct ΔUSS measurement | T2 |
| USS-F2 cross-check | Must agree within ussAgreement_mm | T2 |

### Response Time (tResponse_s — RoverLatency.tChain)

| Channel | Derivation | Tier |
|---------|-----------|------|
| Median(Δt between consecutive buffer entries) | Hub-clock timestamps; no BLE jitter | T2 |

### Combined Sensor Offset (dCombo — T1 anchor)

| Channel | Source | Tier |
|---------|--------|------|
| Operator gap measurement after verification run | Physical ruler | T1 |
| dCombo = USS-F1_settled − operator_gap | T1-anchored computation | T1 |

### Heading (SYS-5)

| Channel | rover_generic Type | Tier |
|---------|-------------------|------|
| imu.yaw | InertialUnit | T2 (no independent cross-source) |

---

## Section 3 — Source-of-Truth Hierarchy (unchanged)

```
T1:  Operator physical measurement  →  dCombo_mm (verification run)
T2:  Multi-sample onboard, hub-clock →  all other TBDs
T3:  Single onboard sample           →  exploratory only (Cal-Run-1)
```

Rules from v1.0 unchanged.

---

## Section 4 — Characterisation Run Design (UNCHANGED)

### Run schedule

| Run | Label | Purpose | Trigger dist. | Est. duration |
|-----|-------|---------|--------------|--------------|
| Cal-Run-1 | Port Discovery | Port map, directions, initial USS readings | N/A | ~20 s |
| Cal-Run-2 | Speed + Stop Cal | Bind all T2 TBDs; unit-verify CMP-1–4, 6 | 400 mm | ~15 s |
| Verification | Verif-Run | Integrated test + T1 dCombo binding; close SYS-1/2 | Calibrated dTrigger | ~10 s |

**Total hardware runs: 3 (2 cal + 1 verification).** Run design per v1.0 Section 4 in full.
See v1.0 for full program sketches and per-run anomaly checks.

---

## Section 5 — Outside-Input Requests (unchanged)

**One T1 measurement, timed to the Verification Run:**  
> After the Verification Run, with the rover fully stopped, please measure the gap
> between the rover's front face and the wall surface in mm (to the nearest mm).

Formula: `dCombo_mm = USS_F1_settled_reading − operator_gap_mm`

Justification: dCombo_mm has ±50 mm leverage (P2 in sensitivity table). No onboard
channel resolves d_front_offset and uss_bias independently — their sum is
unobservable without a T1 reference. One operator measurement closes TBD_COMBO completely.

---

## Section 6 — Verification Support (unchanged from v1.0)

Calibration-to-verification traces identical to v1.0.  
Gate conditions before Verification Run (updated parameter names):

1. All T2 TBDs bound: TBD_VMOT, TBD_VMAX_MMS, TBD_DSTOP, TBD_TRESP, TBD_USS_MIN, TBD_USS_AGREE, TBD_HDG, TBD_HDG_DRIFT.  
2. Predicted `dTrigger = dStopTotal + dCombo_prior + safetyMargin` with `safetyMargin ≥ 3 × RSS_uncertainty`.  
3. `executable_model_v2.py → evaluate()` returns `SYS-1_clearance_PASS: True` at the planned trigger.  
4. No open anomalies from Cal-Run-1 or Cal-Run-2.  
5. CMP-1 through CMP-4 and CMP-6 unit-verified (CMP-5 closes at Verif-Run via T1).

---

*End of CALIBRATION PLAN v1.1*
