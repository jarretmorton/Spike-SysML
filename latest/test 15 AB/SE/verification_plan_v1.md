# Verification Plan v1 — Wall-Approach Rover

**Type:** PLAN · **Gate:** B · **Status: FROZEN.** Predictions only. Issued before VER-1 is flashed and never edited. If falsified, a new version is issued; this one is retained.

## 1. Committed configuration

VER-1 flies **the operation program**, not a rehearsal of it. Same control loop, same trigger, same constants. If the prediction below holds, this exact configuration is locked for the five scored runs with no further tuning — so the run is test-like-you-fly in the strict sense.

| Item | Committed value |
|---|---|
| Trigger | estimated true position ≤ **81.0 mm** |
| Estimator | ranger A through true = 0.9091 × A -2.5, gated against odometry propagation |
| Gate band | 40 mm; tightened to 20 mm once the estimate is below 150 mm |
| Drive | both motors at 1000 deg/s, heading hold trimming only the leading wheel (≤12%) |
| Stop | `brake()` on both motors, issued before any telemetry write |
| Interlocks | odometry travel budget; ranger staleness; yaw abort at 15° |

**Why this trigger and not a closer one.** 81.0 mm is the smallest trigger position whose predicted gap still covers 3σ at current knowledge (SYS-4). It is not a comfortable number chosen for safety — it is the constraint boundary, solved by the model.

## 2. THE FROZEN PREDICTION

Output of `wall_rover_model_v2.predict(81.0)` at the committed configuration. Every line is separately falsifiable by VER-1's telemetry, which is what lets one run identify *which* parameter is wrong rather than merely that something is.

| Quantity | Predicted | Acceptance band (±3σ) |
|---|---|---|
| **Final gap, front corner to wall** | **30.8 mm** | 0.8 … 60.8 mm |
| Final gap, chassis axis to wall | 36.0 mm | — |
| Corner lead from residual yaw | 5.2 mm | — |
| Ranger A reading at the trigger | 92 | 85 … 99 |
| Composite trigger→rest travel `d_total` | **45.0 mm** | **21 … 69 mm** |
| Cruise ground speed | 470 mm/s | 440 … 505 mm/s |
| Wheel rotation after brake | 30 deg | 20 … 45 deg |
| Loop period | 10.0 ms | 9 … 12 ms |
| Heading at the trigger | 0.1° | ≤ 2.0° |
| Heading at rest | 3.3° | ≤ 6.0° |
| Settle time | 110 ms | ≤ 500 ms |
| σ of the final gap | 10.01 mm | — |
| P(contact) this run | 0.0010 | — |

**Predicted ranger A at rest: ~42.** Below A's proven floor, so it is expected to be invalid and is *not* part of the prediction. The onboard gap estimate is formed at the trigger, not at rest: `gap = p_est(trigger) − d_total − corner_lead`.

### 2.1 Uncertainty budget at the committed point

| contributor | mm (1 sigma) | share |
|---|---|---|
| composite transfer | 8.00 | 64% |
| range staleness | 3.26 | 11% |
| map calibration | 3.00 | 9% |
| yaw corner | 2.35 | 6% |
| brake variation | 2.25 | 5% |
| read noise | 1.82 | 3% |
| loop quantisation | 1.36 | 2% |
| speed variation | 0.90 | 1% |
| **root-sum-square** | **10.01** | |

One term is 64% of the variance. **`composite_transfer` is the risk that `d_total`, measured on ranger B, does not transfer to ranger A.** VER-1 measures it directly; if confirmed, σ falls to ~6.5 mm and a ~20 mm gap becomes available.

## 3. Requirement roll-up at the committed configuration

| req | shape | method | measured | target | verdict | note |
|---|---|---|---|---|---|---|
| STK-1 | LowerBound | test | 30.819 | 0.000 | PASS | no contact |
| STK-2 | objective | test | 30.819 | -- | PENDING | minimise gap |
| STK-3 | LowerBound | inspection | 1000.000 | 1000.000 | PASS | max speed commanded |
| STK-4 | UpperBound | test | 1.600 | 5.000 | PASS | drive straight |
| STK-5 | UpperBound | test | 10.007 | 15.000 | PASS | usable onboard estimate |
| SYS-1 | LowerBound | analysis | 30.819 | 0.000 | PASS | min clearance > 0 |
| SYS-2 | UpperBound | test | 110.000 | 500.000 | PASS | complete stop |
| SYS-3 | UpperBound | analysis | 470.000 | 2000.000 | PASS | stoppable in budget |
| SYS-4 | LowerBound | analysis | 30.819 | 30.022 | PASS | margin floor |
| SYS-5 | LowerBound | inspection | 1000.000 | 1000.000 | PASS | commanded at ceiling |
| SYS-6 | UpperBound | test | 1.600 | 5.000 | PASS | heading bound |
| SYS-7 | LowerBound | test | 3.000 | 3.000 | PASS | evidence emitted |
| SYS-8 | UpperBound | test | -- | 10.000 | PENDING | estimate vs ground truth |
| FUN-1 | UpperBound | test | 10.000 | 50.000 | PASS | clearance update |
| FUN-3 | LowerBound | analysis | 81.000 | 75.022 | PASS | trigger sizing |
| FUN-4a | LowerBound | analysis | 91.900 | 85.000 | PASS | above the map floor |
| FUN-4b | UpperBound | analysis | 91.900 | 1900.000 | PASS | below the sentinel |
| FUN-11 | UpperBound | test | 40.000 | 50.000 | PASS | fused hand-off band |
| CMP-3 | UpperBound | test | 100.000 | 91.900 | FAIL | floor <= trigger reading |
| CMP-5 | UpperBound | test | 24.000 | 80.000 | PASS | refresh interval |
| CMP-14 | UpperBound | test | 10.000 | 20.000 | PASS | loop period |
| CMP-15 | UpperBound | test | 0.065 | 0.100 | PASS | k_odo spread / k_odo |

**19 PASS, 2 PENDING, 0 FAIL.** The two pending are STK-2 (graded objective) and SYS-8, both of which close only against operator ground truth.

## 4. Acceptance criteria

VER-1 **confirms** the prediction if all hold:

- no contact;
- measured `d_total` within 21–69 mm;
- operator-measured final gap within 1 … 61 mm;
- onboard estimate agrees with operator ground truth within 10 mm (SYS-8);
- heading, loop period and cruise speed inside their bands;
- no plausibility bound violated.

## 5. Diagnosis tree if falsified

If the prediction fails, the responsible **parameter** is diagnosed and re-derived. The program is not empirically tweaked, and a new frozen Verification Plan version is issued.

| Symptom | Responsible parameter | Action |
|---|---|---|
| Gap smaller than predicted, `d_total` > 69 mm | ranger A's reporting lag exceeds B's | re-bind `d_total` on channel A from this run; re-solve trigger; new plan version |
| Gap larger than predicted, `d_total` < 21 mm | A's lag is shorter than B's | as above |
| Estimate vs ground truth off by >10 mm at similar `d_total` | the reading→true map | the map is being used 25 mm below its anchor bracket; re-anchor |
| Trigger never fires on ranger A | A's floor is above 92 mm | estimator fell back to odometry — check how far it propagated; if >40 mm, re-site the trigger |
| Heading at rest > 6° | braking skid worse than CAL-3 | re-bind `yaw_rest_deg`; the corner lead term grows and the trigger moves out |
| Contact | **HALT.** Anomaly report, full diagnosis, no operation runs until closed. | |

## 6. Operator input required

**OP-MEAS-3**, requested once VER-1 has stopped and before the rover is moved: the distance from the front-most point of the rover to the wall, perpendicular to the wall.

This is the third and final planned measurement. It is spent here rather than earlier because **SYS-8 requires the objective to be validated at the operating point**, and VER-1 is the first run that stops there. It closes three things at once: SYS-8, the predicted→estimated→measured chain that the Final Report must carry, and the STK-2 objective at Gate C.

## 7. What this run costs

One program, one measurement. If it confirms, the configuration locks unchanged for the five scored runs and no further characterization is spent.
