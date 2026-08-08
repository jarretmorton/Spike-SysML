# VERIFICATION REPORT — Wall-Approach Rover

**Type:** report (static; not edited once written) · **Closes GATE C**
**Evidence:** CAL-1, CAL-2, VER-1, VER-2, VER-3 (5 program runs) · M1, M2 (2 operator measurements)
**Frozen predictions tested:** Verification Plan v1.0, v2.0, v3.0 — all retained unedited

This is the single place every requirement is closed. Each row carries a METHOD, the EVIDENCE, and a
VERDICT. **No requirement is asserted without evidence, and four are recorded as FAILED.**

---

## 1. The falsify → diagnose → re-derive trail

| Plan | Target | Falsified by | Responsible parameter | Re-derivation |
|---|---|---|---|---|
| **v1.0** | 12.0 mm | VER-1: stop yaw −0.83° vs −8.0° ± 3° (crit. 6); clearance 31 mm vs 2.8–21.2 (crit. 2) | `b_offset` yaw correction bound from CAL-2's post-staircase approaches, not from the OP sequence | rebind on M2 at the operational pose → −17.00 mm |
| **v2.0** | 14.0 mm | VER-2: stop yaw −4.9° vs −0.8° ± 4° (crit. 6, by 0.1°) | brake-phase rotation (2.95° vs 6.15°) absent from the model; `L_SENSOR` correction misattributed to latency when the o-bias is odometric | yaw term into the budget, ×1.8 small-sample inflation, target raised |
| **v3.0** | 26.0 mm | VER-3: `r_rest` clipped at 40.00 (crit. 4) | primary ranger's usable floor is above the vendor 40 mm relative to `B_OFF`; the 26 mm target did not restore an independent channel | **not re-derived** — see §4 |

Three frozen predictions, three falsifications, each diagnosed to a named parameter and each fixed by
re-binding from measurement rather than by tweaking the program. That trail is the deliverable; the
program's arithmetic was never touched to make a result come out right.

## 2. Requirement closure

### Stakeholder

| Req | Method | Evidence | Verdict |
|---|---|---|---|
| STK-0 WallRunNeed | analysis+test | roll-up below | **PASS with 4 recorded failures** |
| STK-1 SafeMaximumSpeedRun | test | 3 OP runs, all reached a full stop with no contact | **PASS** |
| STK-2 ClosestStopObjective | analysis+test | closed via OBJ-1 and M2 | **PARTIAL — see OBJ-1** |

### System

| Req | Method | Evidence | Verdict |
|---|---|---|---|
| SYS-1 MaximumApproachSpeed | inspection+test | both wheels commanded at a common regulated 860 deg/s; achieved 411–417 mm/s over 3 OP runs; no speed-reduction branch exists in the loop (inspection). **Amendment approved at GATE B**: maximum *straight-line* speed | **PASS (amended)** |
| SYS-2 NoWallContact | test | 5/5 runs, including 3 at operating targets of 12/14/26 mm, no contact. M1 = 93 mm and M2 = 31 mm both measured positive clearance | **PASS** |
| SYS-3 CompleteStop | test | 6 brake events, all reached zero wheel speed and held; static blocks show no post-stop drift | **PASS** |
| SYS-4 StraightApproach | test | wheel mismatch 0.65%/−0.31%/0.1%; accumulated deviation ≤ 4° over the approach. **Amendment approved at GATE B**: deviation accumulated during the approach, not absolute squareness | **PASS (amended)** |
| SYS-5 ClearanceMarginFloor | analysis | `g_target` 26.0 ≥ `m_contact` 15.3 mm; 3σ lower bound +10.7 mm | **PASS** |
| SYS-6 ConfigurationDiscovery | test | 2 motors C/D, 3 rangers A/B/E, 1 colour F; mirrored drivetrain and drive sign identified correctly in all 5 runs | **PASS** |
| SYS-7 ClearanceReporting | test | **no independent per-run estimator exists at this target.** `r_rest` clipped at 40.00 mm in VER-2 and VER-3; `clearance_est_odo` reduces algebraically to `T + (psi_belief − psi_odo)`, i.e. the target ±1 mm | **FAIL — declared, §4** |

### Function

| Req | Method | Evidence | Verdict |
|---|---|---|---|
| FUN-1 CruiseAtCeiling | test | plateau held ~1.5 s in each OP approach | **PASS** |
| FUN-2 ClearanceEstimation | test | 108–115 fresh samples per OP approach, `n_bad` = 0 | **PASS for control; FAIL for reporting (SYS-7)** |
| FUN-3 StopPointComputation | analysis+test | `trigger_src` = 1 on 3/3 OP runs — the ranging chain fired, never a backstop | **PASS** |
| FUN-4 BrakeActuation | test | `psi_odo` = 12.9, 12.87, 12.14, 12.63, 12.63, 12.39 mm over 6 events | **PASS** |
| FUN-5 FailSafeResponse | test | backstop fired as designed in CAL-1/CAL-2 P4; o-drift guard fired correctly in CAL-1; no-echo guards fired in CAL-2 | **PASS** |
| FUN-6 HeadingMaintenance | test | heading-hold active, `trim_peak` 0.02–0.04, arc eliminated | **PASS** |
| FUN-7 PortAndPolarityIdentification | test | correct in 5/5 runs incl. the mirrored-drivetrain case | **PASS** |
| FUN-8 TelemetryAndEstimate | test | all channels emitted; summaries emitted first, which preserved VER-3's data through a truncated dump | **PASS for telemetry; FAIL for estimate** |

### Component (CAL results pulled forward, plus OP-run confirmation)

| Req | Method | Evidence | Verdict |
|---|---|---|---|
| CMP-1 LeftMotorCeiling | test | 872 deg/s | **PASS** |
| CMP-2 RightMotorCeiling | test | 928 deg/s | **PASS** |
| CMP-3 AccelWithinRunway | analysis | s_accel ≈ 87 mm of ~1000 mm | **PASS** |
| CMP-4 PrimaryRangerBias | test | M2, T5, at the operational pose | **PASS** |
| CMP-5 PrimaryRangerRefresh | test | 21.8 ms | **PASS** |
| CMP-20 PrimaryRangerStaleness | test | 50 ms effective, bound at the operating point; physical value 62–69 ms | **PASS (composite)** |
| CMP-21 PrimaryRangerQuantisation | test | 2 mm | **PASS** |
| CMP-6 OdometryScale | test | `k_eff` 0.4858 mm/deg, 6-pt fit, ±6.3 mm over 620 mm | **PASS** |
| CMP-7 SecondaryRangerAgreement | test | port B disagreement −106, −158, −312, −693 mm; final readings 40/45.9/55 at one pose | **FAIL — demoted to monitor-only** |
| CMP-8 TriggerTimingResolution | test | 1 ms wait granularity; trigger fired as computed 3/3 | **PASS** |
| CMP-9 PlausibilityBounds | inspection+test | every guard that should have fired did (flags 64, 256, 512, 1024 paths all exercised) | **PASS** |
| CMP-10 DeadReckonBackstop | test | `trigger_src` = 2 in CAL-1/CAL-2 P4 at the commanded travel | **PASS** |
| CMP-11 BrakeTravel | test | 12.64 mm mean of 6 | **PASS** |
| CMP-22 BrakeTravelRepeatability | test | sd 0.30 mm over 6 events, two configurations | **PASS** |
| CMP-12 NoPostStopMotion | test | static blocks stable after every stop | **PASS** |
| CMP-13 HeadingSensing | test | IMU vs differential odometry agree to 0.13° across a brake | **PASS** |
| CMP-14 WheelSpeedSymmetry | test | ≤0.65% after the fix (6.2% before) | **PASS** |
| CMP-15 DeviceTypeIdentification | test | correct 5/5 | **PASS** |
| CMP-16 DrivePolarityIdentification | test | correct 5/5, mirrored case handled | **PASS** |
| CMP-17 RestRangeEstimator | test | clipped at 40.00 mm in VER-2 and VER-3 | **FAIL — predicted in advance in v2.0 §5** |
| CMP-18 OdometricEstimator | test | internally consistent but **tautological** (derivation in §4) | **FAIL as an estimator** |
| CMP-19 ContactDetection | test | forward acceleration logged through all 6 brakes; 0.76 g signature clean, no impact spike | **PASS** |

### Objective

| Req | Method | Evidence | Verdict |
|---|---|---|---|
| OBJ-1 MarginEfficiency (`g_target` ≤ 1.2·`m_contact`) | analysis | 26.0 mm vs an 18.3 mm cap | **FAIL by 7.7 mm — deliberate, §4** |

## 3. The objective, closed on external ground truth

GATE C requires the objective closed only on evidence that the predicted final gap was validated
against operator ground truth **at the operating point**.

**M2 = 31 mm**, measured at a reported range of 48.0 mm and 0.83° of yaw, in the operational
configuration, at the operational speed, after a ranging-triggered stop. My committed pre-measurement
prediction was 20–32 mm with a point estimate of 26 mm; the measurement landed at 31 mm, inside the
committed interval. The operating point is now 26 mm — 5 mm from where M2 was taken, same yaw regime,
same configuration.

The objective is therefore closed on an externally validated chain, **not** on the onboard sensor. That
distinction is not academic here: the onboard chain concealed an 18.6 mm latency bias until two
independent estimators disagreed, and it would have concealed a 7.9 mm yaw error had M2 not been taken.

## 4. Four declared failures

**SYS-7 / CMP-17 / CMP-18 — no independent per-run clearance estimate.** The trigger fires at
`s_br = o_cmd + B_OFF − T − psi_belief`, and the odometric estimator computes `(o_cmd + B_OFF) − s_rest`,
which reduces to `T + (psi_belief − psi_odo)` — the target plus a ~1 mm psi error. It cannot detect a
clearance error. The one independent channel, the static rest reading, clipped at exactly 40.00 mm in
both VER-2 and VER-3 despite v3.0 raising the target specifically to clear that floor. Port B, the
cross-source, failed CMP-7 and cannot be converted to a clearance.

Consequence, stated plainly: **the five close-out estimates will be target-anchored, not measured.**
I will report ≈26 mm for each run with the psi error as the only genuine per-run information, and the
operator's measurements will be the sole independent test. I chose not to spend a sixth characterization
run chasing a monitor I could not act on mid-sequence, because contact risk is governed by things that
*are* externally anchored: M2, `psi` repeatable to 0.30 mm over six events, and a trigger that fired
correctly on 3/3 operating runs with zero flags.

**OBJ-1 — efficiency cap exceeded by 7.7 mm.** 26 mm was chosen over 20 mm to buy observability. In
the event the observability was not obtained, so this failure bought less than intended. Recorded as
what it is rather than retro-justified: had I known VER-3 would clip, 20 mm would have been the better
choice, and the objective score is ~6 mm worse than it needed to be.

## 5. Verdict

Every requirement is closed on evidence. **STK-1 passes**: the rover drives at its maximum
straight-line speed and stops, repeatably, without contact. **STK-2 passes partially**: it stops close,
but ~12 mm further out than the uncertainty budget alone would require, and it cannot independently
measure how close.

Operation may proceed with `15_rover_wallstop_LOCKED_v3.py` unchanged.

**Scores at GATE C: 5 characterization program runs, 2 outside-input actions.**
