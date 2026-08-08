# VERIFICATION PLAN — v1 · **FROZEN**
**Document:** `23_verification_plan_v1.md` · **Type: PLAN** · **Gate:** GATE B
**Status: FROZEN before the verification run. Predictions only. No result may edit this
version.** If the run falsifies it, I diagnose the responsible parameter, re-derive, and
issue **v2** — this version stays as the record of what was predicted.

**Article under test:** `21_revF_program.py` (REV F), unchanged, which is also the operation
candidate.

---

## 1. Configuration

| item | value |
|---|---|
| anchor `G` | 1000.0 mm (M3, hard-coded) |
| scale `k` | 0.4992 mm/deg (M1 + M3 pair, 1646.5 deg baseline) |
| `TRIG_GAP` | **48 mm** true gap |
| commanded speed | 750 deg/s → 374 mm/s |
| stop | passive `brake()` |
| forward ranger | **not constructed** |

---

## 2. FROZEN PREDICTION — output of the executable model at the committed values

| quantity | predicted |
|---|---:|
| cruise speed | 374 mm/s |
| composite stop distance `S` | 11.0 mm |
| loop-crossing bias | 1.8 mm |
| **final gap, mean** | **35.3 mm** |
| σ_g, verification run (anchor exact) | 8.3 mm |
| σ_g, operation (start-line scatter) | 11.4 mm |
| onboard estimate `g_est_final` | 35.3 mm, error ≤ 2 mm |
| travel to trigger | 1907 motor deg |
| time to trigger | ≈ 2.5 s |

### 2.1 The falsifiable statement

> **The verification run will stop with a measured gap of 35.3 mm, and the measured value
> will lie within [10.3, 60.2] mm (±3σ). The onboard estimate will agree with the measured
> gap to within 10 mm. Heading will not exceed 5°. There will be no contact.**

If the measured gap falls outside that interval, the model is falsified and I re-derive
rather than adjust.

### 2.2 Uncertainty budget

| term | σ (mm) | basis |
|---|---:|---|
| start-line repeatability | 8.0 *(operation only; 2.0 for this run)* | assumed split of a 13.8 mm bound |
| `k` × travel | 7.2 | 0.75% over 965 mm |
| slip variability | 3.0 | RUN-3 measured 3.3 mm |
| yaw | 1.3 | 2.54° peak × 1.3 mm/deg |
| stop repeatability | 1.0 | 9% prior on S = 11.0, n = 1 |
| loop quantisation | 1.0 | 9.4 ms at 374 mm/s |

---

## 3. Predicted requirement roll-up

| req | operand | predicted | target | verdict |
|---|---|---:|---:|---|
| SYS-1 | minimum clearance, low tail | 10.3 mm | > 0 | **PASS** |
| SYS-2 | gap ≥ k_σ·σ_g (operation) | 35.3 | 34.1 | **PASS** — margin 1.2 mm |
| SYS-3 | gap ≤ goal (objective, graded) | 35.3 | 30 | **graded** — reported, not gating |
| SYS-4 | commanded speed = max in regulation | 750 | 750 | **PASS** |
| SYS-5 | time to rest | 59 ms | ≤500 | **PASS** |
| SYS-6 | heading deviation | 2.54° | ≤5° | **PASS** |
| SYS-7 | degraded stop clears the wall | travel cap at 88 mm | > 0 | **PASS** |
| SYS-8 | estimate error | ≤2 mm | ≤10 mm | **PASS** |
| SYS-9 | no cross-run state | — | — | **PASS** (inspection) |

**SYS-2 passes by 1.2 mm.** The design sits essentially exactly on its margin requirement,
which is what the optimum looks like when the objective pushes down and the margin pushes
back — but it means any adverse surprise in σ_g breaks it, and the honest reading is that
this design has no slack, not that it has been proven safe.

---

## 4. Pre-committed disposition rules

Decided **before** the run, so the result cannot select the rule:

| outcome | disposition |
|---|---|
| gap in [10.3, 60.2] mm, no contact | prediction **holds** → GATE C → operation with this same program |
| gap outside the interval, no contact | **falsified** → diagnose the responsible parameter, re-derive, issue Verification Plan **v2**, re-run |
| contact | **falsified**, and `TRIG_GAP` re-derived upward from the observed error before any further run |
| `trigger_reason` ≠ 1 | a guard fired → treat as an anomaly report, not a verification result |

---

## 5. Residual risks carried into the run

1. **`S` has one sample**, so `rel_σ_S` is a prior. Contributes 1.0 mm — small, but unverified.
2. **Start-line repeatability is assumed.** It does not affect *this* run (the anchor was
   measured at this placement) but it dominates the operation budget.
3. **Single-string on odometry.** Slip beyond the measured 3.3 mm produces contact and
   nothing onboard would witness it. This is the residual the simulation cannot retire:
   REV F survives a ±1.5% scale error with 18.9 mm to spare, and even +3% without contact
   (4.2 mm), but simulated slip is not measured slip.
4. **Direction is hard-coded.** Confirmed across three runs; a change would waste a run, not
   cause contact. `accel_x_mean` / `accel_y_mean` are logged as the witness.
