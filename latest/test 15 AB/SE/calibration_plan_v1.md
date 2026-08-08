# Calibration Plan — Wall-Approach Rover

**Document:** calibration_plan, v1 &nbsp;|&nbsp; **Type:** PLAN (forward-looking; revised and re-issued as new versions, prior versions retained)  
**Gate:** A — issued after the requirements specification, SysML model and executable analysis model, **before any hardware is touched.**  
**Status of the rover at issue:** untouched. No program flashed, no run taken, no operator measurement consumed.

---

## 0. Sensitivity analysis

This section decides everything that follows. Each free or uncertain parameter is swept over an explicitly stated prior range with all others held at their prior mid-points, and the resulting swing is reported in two currencies: **objective sensitivity** (how far the predicted final gap moves) and **margin sensitivity** (how far the no-contact margin moves). Priority follows max(objective, margin) swing, moderated by how much of that swing calibration can actually remove.

Operating point for the sweep: trigger threshold solved to the model's target gap; r_trig = 133.6 mm, predicted gap = 27.1 mm, sigma = 9.02 mm.

### 0.1 Required sensitivity table

| # | Parameter | Assumed range (prior) | Objective swing (mm) | Margin swing (mm) | Knowledge tier | Priority |
|---|---|---|---|---|---|---|
| 1 | `v_cruise_mmps` | 250 .. 800 &nbsp; *(wheel 43-90 mm x motor 800-1050 deg/s)* | **98.9** | 121.3 | T3 — prior only | **P1** |
| 2 | `c_us_mm` | -100 .. 20 &nbsp; *(sensor face -> front-most point geometry)* | **120.0** | 120.0 | T3 — prior only | **P1** |
| 3 | `a_brake_mmps2` | 1500 .. 7000 &nbsp; *(motor brake; traction-limited below ~7000)* | **72.2** | 87.2 | T3 — prior only | **P1** |
| 4 | `tau_ms` | 5 .. 60 &nbsp; *(device reporting lag)* | **28.9** | 29.7 | T3 — prior only | **P2** |
| 5 | `t_act_ms` | 5 .. 30 &nbsp; *(brake command -> torque onset)* | **13.1** | 13.5 | T3 — prior only | **P2** |
| 6 | `t_refresh_ms` | 10 .. 60 &nbsp; *(sensor update period (staleness bound))* | **0.0** | 12.6 | T3 — prior only | **P2** |
| 7 | `psi_dev_deg` | 0 .. 8 &nbsp; *(open-loop differential drive)* | **9.1** | 12.4 | T3 — prior only | **P2** |
| 8 | `sigma_us_mm` | 1 .. 10 &nbsp; *(reading noise incl. possible crosstalk)* | **0.0** | 9.9 | T3 — prior only | **P2** |
| 9 | `k_us` | 0.97 .. 1.03 &nbsp; *(factory time-of-flight scale)* | **8.0** | 8.0 | T3 — prior only | **P3** |
| 10 | `loop_dt_ms` | 5 .. 20 &nbsp; *(achieved loop period, two sensor reads)* | **3.9** | 5.5 | T3 — prior only | **P3** |
| 11 | `half_width_mm` | 40 .. 90 &nbsp; *(SPIKE chassis half-width)* | **3.5** | 4.8 | T3 — prior only | **P3** |
| 12 | `sigma_brake_frac` | 0.04 .. 0.15 &nbsp; *(friction/thermal run-to-run)* | **0.0** | 3.6 | T3 — prior only | **P3** |
| 13 | `sigma_v_frac` | 0.01 .. 0.05 &nbsp; *(regulated drive, battery state)* | **0.0** | 3.5 | T3 — prior only | **P3** |
| 14 | `sigma_c_mm` | 1.5 .. 4 &nbsp; *(post-anchor residual (rule + noise))* | **0.0** | 2.3 | T3 — prior only | **P3** |
| 15 | `sigma_k_us` | 0.005 .. 0.03 &nbsp; *(factory scale uncertainty)* | **0.0** | 0.0 | T3 — prior only | **P3** |
| 16 | `d_start_mm` | 950 .. 1050 &nbsp; *(operator: '~1000 mm', held constant)* | **0.0** | 0.0 | T3 — prior only | **P3** |

### 0.2 What the table decides

**P1 — `v_cruise`, `c_us`, `a_brake`.** These three carry the result. Two of them (`v_cruise`, `a_brake`) are directly observable onboard, to high confidence, in a single run: wheel odometry differentiated against the hub clock, cross-sourced against the ranging channel and the IMU. They are cheap to bind well.

`c_us` is different, and it is the central finding of this analysis. **It is the offset between what the ranging channel reports and where the rover's front-most point actually is** — sensor recess, chassis overhang, bumper geometry. Its objective sensitivity is exactly 1.0 mm per mm: it passes straight through to the scored quantity, undiluted. **No onboard channel observes it at all** — no sensor on the rover can see the rover's own front face, and every onboard channel measures distance *from the sensor*, so they are all biased by exactly the same unknown and cross-sourcing cannot detect it. Its prior range (-100..+20 mm) is wider than the entire gap the task is scored on. This is where the costed operator measurement is spent, and it is the reason the measurement must be taken **at the operating point** rather than anywhere convenient.

**P2 — `tau`, `t_act`, `t_refresh`, `psi_dev`, `sigma_us`.** The latency chain, the straightness deviation and the reading noise. Each is roughly 10-30 mm across its prior range, each is observable onboard, and all five are bound by the same run. Note that `t_refresh` and `sigma_us` have **zero** objective swing but 12.6 and 9.9 mm of margin swing: they do not move the nominal gap at all, they move the *dispersion* — staleness and noise are jitter terms. A single-currency sensitivity table would have ranked them at zero and the plan would have ignored two of the eight budget contributors. That is why the table reports both currencies.

**P3 and below — everything else, including `half_width`.** `half_width_mm` swings the objective by 3.5 mm across a 40..90 mm prior. That is smaller than the margin, so it is **carried at its conservative bound (90 mm) and not measured.** Spending a costed operator measurement on it would buy less than it costs. This is recorded as TBD-15 with that rationale, not silently dropped.

### 0.3 Coverage factor: an explicit trade, not a convention

SYS-4 requires predicted gap >= k x sigma. The choice of k is a decision about how many of the five scored runs are allowed to touch the wall. Computed from the model, assuming the run-to-run dispersion is the sigma the budget predicts:

| k | P(contact) per run | Expected contacts over 5 runs | Target gap at the projected sigma |
|---|---|---|---|
| 1.5 | 0.0668 | 0.334 | 11.1 mm |
| 2.0 | 0.0228 | 0.114 | 14.8 mm |
| 2.5 | 0.0062 | 0.031 | 18.5 mm |
| 3.0 | 0.0013 | 0.007 | 22.2 mm |
| 3.5 | 0.0002 | 0.001 | 25.9 mm |

**k = 3 is adopted.** The step from k=2 to k=3 costs about 7 mm of gap and removes about 0.11 expected contacts over five runs; a single contact fails a hard constraint, while 7 mm of gap is a graded loss. The step from k=3 to k=3.5 costs a further 4 mm to remove only 0.006 expected contacts, which is not worth it. This asymmetry — hard constraint against graded objective — is the whole content of the decision.

### 0.4 Projected uncertainty budget after calibration

Calibration does two different things to the eight budget terms, and the distinction matters:

- it **shrinks** the terms that are uncertain because we have not measured them (`sigma_c`, `sigma_us`, `sigma_k`, `psi_dev`);
- it only **reveals** the terms that are irreducible physics of the platform (`t_refresh`, `loop_dt`). Knowing the refresh interval exactly does not make the staleness jitter smaller — the reading is still up to one refresh period old, and the rover still travels during it.

The projection below holds the irreducible terms at their prior mid-points and moves the reducible ones to the level this plan is designed to achieve.

Projected operating point: r_trig = 126.5 mm, predicted gap = **22.2 mm**, sigma = 7.41 mm.

| Contributor | mm (1 sigma) | Share | Calibration does what to it |
|---|---|---|---|
| range staleness | 5.30 | 51% | **reveals only** — CAL-1 measures the refresh interval from staircase edge spacing; the jitter is then a known constant |
| braking variation | 3.08 | 17% | **neither** — held at its conservative prior; the 5 operation runs are the repeatability sample |
| offset anchor | 2.50 | 11% | **shrinks** — **OP-MEAS-1** (the costed measurement) + CAL-1 creep |
| loop quantisation | 1.89 | 7% | **reveals only** — hub-clock loop period; irreducible once the loop is written |
| speed variation | 1.89 | 6% | shrinks — CAL-1 within-run speed regulation |
| trigger read noise | 1.60 | 5% | shrinks — CAL-1 static bursts |
| yaw corner | 1.13 | 2% | shrinks — CAL-1 IMU heading at the stop |
| scale leverage | 0.06 | 0% | shrinks — CAL-1 linearity + anchoring near the operating point |

**Range staleness dominates the projected budget, and it is the term calibration cannot reduce.** It scales as cruise speed times the refresh interval, and the task forbids reducing the first. So the achievable gap is set largely by a device property nobody has measured yet. The honest form of the prediction is therefore a band, not a number:

| If the ranging refresh interval turns out to be | sigma | Predicted gap at k=3 |
|---|---|---|
| 10 ms | 5.39 mm | **16.2 mm** |
| 20 ms | 5.99 mm | **18.0 mm** |
| 35 ms *(prior mid-point, used above)* | 7.41 mm | **22.2 mm** |
| 50 ms | 9.17 mm | **27.5 mm** |
| 60 ms | 10.46 mm | **31.4 mm** |

This band — roughly 16 to 31 mm — is the outcome this plan is buying information about. CAL-1 collapses it to a single value on its first segment. Committing to a target gap before that measurement exists would be picking a number, not predicting one.

The budget is a root-sum-square of independent contributors (tenet A6). No term is squeezed below ~1 mm, because at that level the RSS stops caring: halving a 1 mm term inside a 6 mm root-sum-square buys 0.06 mm.

---

## 1. Calibration input list

### 1.1 Model-completion parameters

Every parameter the executable model needs before it can produce a number. The model refuses to compute on an unbound parameter (it raises rather than defaulting to zero), so this list is not a matter of diligence — it is enforced.

| TBD | Parameter(s) | Bound by | Tier after binding |
|---|---|---|---|
| TBD-01 | `v_cruise_mmps` | CAL-1 (odometry + ranging, steady segment) | T2 (multi-point onboard) |
| TBD-01b | `speed_residual_mmps` | CAL-1 | T2 (multi-point onboard) |
| TBD-02 | `k_odo_mm_per_deg` | CAL-1 (ranging traverse regression) | T2 (multi-point onboard) |
| TBD-02b | `odo_residual_mm` | CAL-1 | T2 (multi-point onboard) |
| TBD-03 | `motor_speed_cmd_dps, motor_speed_max_dps, motor_speed_ach_left_dps, motor_speed_ach_right_dps` | CAL-1 (device limit read + encoder) | T2 (multi-point onboard) |
| TBD-04 | `tau_ms` | CAL-1 (lag regression, ranging vs odometry) | T2 (multi-point onboard) |
| TBD-05 | `t_refresh_ms` | CAL-1 (staircase edge spacing) | T2 (multi-point onboard) |
| TBD-06 | `loop_dt_ms` | CAL-1 (hub-clock timestamps) | T2 (multi-point onboard) |
| TBD-06b | `clearance_update_ms` | CAL-1 | T2 (multi-point onboard) |
| TBD-06c | `heading_sample_ms` | CAL-1 | T2 (multi-point onboard) |
| TBD-07 | `t_act_ms` | CAL-1 (encoder speed knee) | T2 (multi-point onboard) |
| TBD-07b | `brake_skew_ms` | CAL-1 (hub clock) + code inspection | T2 (multi-point onboard) |
| TBD-08 | `a_brake_mmps2` | CAL-1 (speed decay fit) | T2 (multi-point onboard) |
| TBD-08b | `decel_residual_frac` | CAL-1 | T2 (multi-point onboard) |
| TBD-09 | `d_total_meas_mm` | CAL-1 (r_trig - r_rest, same channel) | T2 (multi-point onboard) |
| TBD-09b | `stop_angle_left_deg, stop_angle_right_deg` | CAL-1 | T2 (multi-point onboard) |
| TBD-09c | `travel_at_stop_mm` | CAL-1 | T2 (multi-point onboard) |
| TBD-10 | `c_us_mm` | CAL-1 creep stop + OP-MEAS-1 (operator, tier 1) | **T1** (external ground truth, at the operating point) |
| TBD-10b | `sigma_c_mm` | derived from OP-MEAS-1 resolution + at-rest reading noise | T2 (derived from the T1 anchor) |
| TBD-11 | `k_us` | CAL-1 (linearity regression vs odometry); absolute scale from device spec, leverage removed by anchoring c near the operating point | T2 (multi-point onboard regression) |
| TBD-11b | `sigma_k_us` | CAL-1 residual + device spec | T3/T2 (device spec + CAL-1 residual) |
| TBD-11c | `ranger_fl_residual_mm, ranger_fr_residual_mm` | CAL-1 | T2 (multi-point onboard) |
| TBD-12 | `us_valid_min_mm` | CAL-1 creep (ranging vs odometry to the floor) | T2 (multi-point onboard) |
| TBD-13 | `sigma_us_mm` | CAL-1 (static bursts, pre-roll and post-stop) | T2 (multi-point onboard) |
| TBD-14 | `psi_dev_deg` | CAL-1 (IMU trace) | T2 (multi-point onboard) |
| TBD-14b | `drive_asymmetry_dps` | CAL-1 (per-motor encoders) | T2 (multi-point onboard) |
| TBD-14c | `heading_drift_static_deg` | CAL-1 (pre-roll and post-stop static) | T2 (multi-point onboard) |
| TBD-15 | `half_width_mm` | NOT MEASURED: carried at its conservative prior bound; sensitivity P3 (3.5 mm objective swing over the full prior range) does not justify a costed measurement | T3 (prior, deliberately not measured — see 0.2) |
| TBD-16 | `sigma_brake_frac` | prior, cross-checked by the CAL-1/VER-1 pair; the operation runs are the repeatability sample | T3 (prior; sample only from the operation runs) |
| TBD-17 | `sigma_v_frac` | CAL-1 (within-run speed regulation) | T2 (multi-point onboard) |
| TBD-19 | `t_settle_ms` | CAL-1 | T2 (multi-point onboard) |
| TBD-20 | `d_start_mm` | CAL-1 (static pre-roll reading + anchored offset) | T2 (multi-point onboard) |
| TBD-21 | `rear_travel_residual_mm` | CAL-1 (Optional; void if no rear reference) | T2 (multi-point onboard) |
| TBD-22 | `estimator_error_mm` | VER-1 close-out (uses OP-MEAS-1) | T2 (multi-point onboard) |
| TBD-23 | `estimator_delta_mm` | CAL-1 and VER-1 | T2 (multi-point onboard) |
| TBD-24 | `travel_interlock_mm` | computed onboard each run from the static start reading | T2 (multi-point onboard) |
| TBD-25 | `evidence_fields_emitted, channels_logged` | CAL-1 (inspection of the emitted stream) | T2 (multi-point onboard) |
| TBD-26 | `r_trig_mm` | solved by the executable model at GATE B from the bound parameters | T2 (multi-point onboard) |

### 1.2 Requirement TBD register

The requirement-side unknowns are the allocated bounds in requirements_spec_v1.md S4.1. They are **decisions, not measurements**, and are already bound — each carries its basis in that table. None of them is an eyeballed constant: each is derived from a stated analysis (corner-lead geometry, latency-travel budget, half-the-target-gap resolution rule). They are listed there rather than duplicated here so there is one place to change them.

One requirement-side value is deliberately left open until CAL-1 returns: `r_trig_mm`, the commanded trigger threshold (TBD-26). It is **not a measurement** — it is the design variable the model solves for once the measured parameters are bound. It is frozen in the Verification Plan at Gate B, not chosen here.

---

## 2. Characterization run design

### 2.1 Channel catalog and cross-sourcing

Every independent onboard channel bearing on each quantity, ranked by directness. **All eight are logged on every run**, not only the one under test (tenet B1) — a channel that is not logged cannot later be used to diagnose a surprise, and re-running to collect it costs a program.

| # | Channel | Observes directly | Also bears on | Directness | Valid range / caveat |
|---|---|---|---|---|---|
| C1 | Forward ranger A, `distance()` | forward range | speed, travel, stop distance | high | floor ~50 mm (TBD-12); 2000 mm = no-object sentinel, **not** a distance |
| C2 | Forward ranger B, `distance()` | forward range | as C1 | high | as C1; independent device, so C1-C2 disagreement is a fault detector |
| C3 | Left motor `angle()` | wheel rotation | travel, speed, deceleration | high | no near-range floor — **this is the hand-off channel below C1/C2's floor** |
| C4 | Right motor `angle()` | wheel rotation | as C3, plus yaw via C3-C4 | high | as C3 |
| C5 | Motor `speed()` (both) | wheel angular rate | cruise speed, brake onset, settle time | high | derivative channel; noisier than differencing C3/C4 over a window |
| C6 | IMU `heading()` | yaw | straightness, corner lead | high | drifts; static drift bound by CMP-11 |
| C7 | IMU `acceleration()` | forward acceleration | deceleration, **wheel slip** | medium | noisy; its value is being independent of the wheels (Optional CMP-12) |
| C8 | Rear ranger `distance()` | rear range | travel, independent of wheels *and* forward ranging | medium | Optional CMP-13; **void if no rear reference surface exists** — the Where-precondition is evaluated from the data, not assumed |

Cross-source pairs that make the argument falsifiable:

| Quantity | Primary | Independent cross-source | What disagreement would mean |
|---|---|---|---|
| forward range | C1 | C2 | one ranger faulty, or acoustic crosstalk between them |
| travel | C3+C4 | C1/C2 (and C8 if valid) | wheel slip, or a ranging scale error |
| cruise speed | C3+C4 differenced | C1/C2 slope | slip, or scale |
| deceleration | C3+C4 | C7 | wheel slip during braking (wheels stop, chassis does not) |
| yaw | C6 | C3-C4 differential | IMU drift, or a wheel-diameter mismatch |
| **front-face offset `c_us`** | *(none onboard)* | **operator, OP-MEAS-1** | this is precisely why the measurement is costed — see S0.2 |

**Bounded-range hand-off.** C1/C2 stop being valid below their near-range floor (TBD-12). The plan does not extrapolate them into that region. Instead the creep segment drives the rover slowly toward the wall while logging C1/C2 against C3/C4, and the floor is read off as the range at which C1/C2 stop tracking odometry. Below it the fallback estimator (last valid reading minus odometry travel) takes over. FUN-11 and CMP-3 exist to make this hand-off a requirement rather than an implementation detail.

### 2.2 Source-of-truth hierarchy

| Tier | Source | Examples here | Rule |
|---|---|---|---|
| **T1** | External ground truth — operator measurement | OP-MEAS-1 | Governs. Overwrites any lower tier. |
| **T2** | Anchored or multi-point onboard calibration | ranging-vs-odometry regression over ~880 mm; refresh interval from many staircase edges | May be overwritten by T1 only. |
| **T3** | Single onboard sample, or prior | one at-rest reading; `half_width_mm` | **Never silently overwrites T2 or T1.** |

Operating rules, applied for the rest of the programme:

1. Every bound value is carried with its **evidence basis and tier**, in the Calibration Report.
2. **A lower tier never silently re-fits a higher one.** If a later single sample disagrees with a T2 regression, the regression stands and the disagreement is logged as an anomaly. This is written down now, before any data exists to be tempted by.
3. **A sensor value driving a scored quantity is a hypothesis until confirmed against an independent higher-tier source at the operating point.** The final-gap estimate is exactly such a value. It is a hypothesis until OP-MEAS-1 confirms it, which is why SYS-8 exists and why the objective requirement cannot close before Gate C.
4. Disagreement beyond the allocated tolerance, or any reading outside its plausibility bound, **escalates unconditionally** — it is not filtered by sensitivity ranking.

### 2.3 Plausibility bounds (unconditional-escalation limits)

Every logged channel carries a physical bound. A value outside it is not a surprise to be weighed against sensitivity; it means the model of the situation is wrong, and it escalates.

| Quantity | Bound | Why a violation is impossible rather than merely surprising |
|---|---|---|
| `range_mm` | 0 .. 2000 | outside the device's physical range |
| `rest_minus_trig` | -inf .. 0 | at-rest range exceeds the trigger range: the rover moved backwards while braking |
| `travel_mm` | 0 .. 1200 | travel exceeds the approach corridor |
| `gap_mm` | 0 .. 1100 | negative gap is contact; beyond start is impossible |
| `heading_deg` | -30 .. 30 | yaw beyond any credible drive asymmetry |
| `loop_dt_ms` | 0 .. 100 | control loop stalled |
| `decel_mmps2` | 0 .. 12000 | deceleration beyond the traction limit |
| `v_cruise_mmps` | 0 .. 1200 | ground speed beyond the drivetrain ceiling |

### 2.4 Test-like-you-fly: one run, CAL-1

**The characterization program is a strict superset of the operation program.** Identical control loop, identical trigger evaluation, identical braking call, identical telemetry skeleton. The operation program is obtained by deleting the extra logging and the appended segments — never by editing the control path. What is characterized is therefore what flies.

Extra logging is kept **off the hot path**: samples are appended to a pre-allocated list during motion and dumped to stdout only after the motors have stopped. Writing to stdout inside the control loop would inflate the loop period and change the very latency the run exists to measure.

CAL-1 segments, in order — one flash, one run:

| Seg | What happens | Binds |
|---|---|---|
| **S0** Port discovery | Probe each port, identify which are motors / rangers / IMU, and which way each motor drives forward. Emitted as telemetry, not assumed. | port map, drive polarity |
| **S1** Static pre-roll | ~1 s stationary at the start line; burst-sample every channel. | TBD-13 (reading noise), TBD-14c (IMU static drift), TBD-20 (start reading), C1-C2 offset |
| **S2** Full-speed approach | The operation sequence, verbatim, with a **deliberately conservative trigger** so the stop lands well short of the wall. | TBD-01/02/03 (speed, odometry scale), TBD-04/05/06/07 (latency chain), TBD-08 (deceleration), TBD-09 (composite stop travel), TBD-14 (heading), TBD-17 (speed regulation) |
| **S3** Post-stop static | ~1 s stationary; burst-sample every channel. | TBD-19 (settle), at-rest reading noise, IMU drift over the run |
| **S4** Creep to the anchor | Slow approach to a planned near-wall reading, then stop. **Not part of the flight program** — appended after the operational sequence has completed. | TBD-12 (near-range floor), the C1/C2-to-odometry hand-off, and the geometry for OP-MEAS-1 |
| **S5** Anchor hold | Hold position, burst-sample. Rover is left in place for the operator. | TBD-10 with OP-MEAS-1, TBD-11 (scale near the operating point) |

**Why the conservative trigger in S2.** The purpose of S2 is to measure the composite trigger-reading-to-rest travel, and that measurement is equally good from any starting trigger value. Setting an aggressive trigger before the stopping distance is known would risk contact for no information gain. The conservative trigger is a free choice; there is no reason to spend risk on it.

**Why one run and not three.** Every flash-and-run counts. The segments above are independent in what they bind and can be concatenated in a single power-on, because the only state that matters across them (hub clock, IMU heading) is continuous within a run. Splitting them would cost programs and *lose* information — the run-spanning IMU drift measurement only exists because S1 and S3 are in the same run.

**Deliberate omission.** The plan does not include a repeatability sample: run-to-run braking dispersion (`sigma_brake_frac`, TBD-16) stays at its prior. Measuring it properly would take several identical runs, and it is the largest single contributor to the budget — but its *prior* is already conservative, and spending 3-4 programs to shrink one of eight RSS terms is a poor trade against the program-count score. The consequence is accepted explicitly: the margin is sized with a conservative dispersion, and the five operation runs are themselves the repeatability sample, reported in the Final Report.

---

## 3. Outside-input requests

**One measurement is requested for the whole programme: OP-MEAS-1.** It is requested after CAL-1 has run and left the rover holding station near the wall.

> **OP-MEAS-1** — With the rover stopped where CAL-1 leaves it, measure the distance from the **front-most point of the rover** to the wall, in millimetres, in the direction perpendicular to the wall.

**Why this one and not another.** S0.1 ranks `c_us` at the top of the objective sensitivity table, at 1.0 mm per mm, and S0.2 shows no onboard channel can observe it. Every other P1 and P2 parameter is observable onboard. This is the single quantity where an operator measurement buys something no amount of free analysis or telemetry can.

**Why at the anchor point and not at the start line.** Anchoring near the operating point makes the ranging scale error irrelevant: the residual scale leverage is |1-k| times the *distance from the anchor to the operating point*, which is a few mm here rather than ~1000 mm. This is worth 0.06 mm of the budget instead of ~10.0 mm — the anchor location is doing as much work as the measurement itself.

**Maximum cross-checks batched around it (tenet B4).** The single request is surrounded by every onboard observation that can be taken at the same instant, so one costed measurement confirms several things at once:

- both forward rangers' readings at the anchor -> `c_us` **and** a check on the C1-C2 offset;
- the odometry-integrated position at the anchor -> independent check on the ranging scale;
- the creep-segment hand-off -> the near-range floor, confirmed against a T1 anchor rather than assumed from the device specification;
- the at-rest reading noise from S5 -> the residual `sigma_c_mm`;
- the difference between the S2 stop and the S5 anchor -> a second, independent path to the same offset.

**A second measurement is anticipated but not yet requested:** the ground-truth gap at the verification run's stop, which closes SYS-8 and the objective requirement at Gate C. Whether that is a genuinely new request or is satisfied by the VER-1 close-out depends on how well OP-MEAS-1's anchor generalises; the decision is deferred to the Verification Plan, where the prediction it tests will already be frozen.

---

## 4. Verification support

### 4.1 How calibration supports unit verification of the CMP requirements

The CMP requirements are the single-effector leaves, and **they are verified by CAL-1 itself** — before anything is integrated (tenet C1). Each is a bound on a quantity the run already logs, so unit verification is a roll-up over the same telemetry that binds the parameters, not a separate activity.

| CMP | Verified by | Segment | Method |
|---|---|---|---|
| CMP-1 | ranger A vs odometry residual over the traverse | S2 | test |
| CMP-2 | ranger B vs odometry residual over the traverse | S2 | test |
| CMP-3 | near-range floor vs the at-rest reading | S4/S5 | test |
| CMP-4 | lag regression, ranging vs odometry | S2 | test |
| CMP-5 | refresh interval from staircase edge spacing | S2 | test |
| CMP-6 | left encoder speed during cruise | S2 | test |
| CMP-7 | right encoder speed during cruise | S2 | test |
| CMP-8 | left rotation after the brake command | S2 | test |
| CMP-9 | right rotation after the brake command | S2 | test |
| CMP-10 | odometry vs ranging residual | S2 | test |
| CMP-11 | IMU heading drift, static | S1+S3 | test |
| CMP-12 | IMU deceleration vs odometry deceleration | S2 | test (Optional) |
| CMP-13 | rear-ranging travel vs odometry | S2 | test (Optional, void if no reference) |
| CMP-14 | loop period from hub-clock timestamps | S2 | test |
| CMP-15 | rotation-to-speed regression | S2 | test |

If a CMP requirement fails, the failure is localised to one effector before any integrated claim rests on it — which is the point of ordering verification by interdependence (tenet A5).

### 4.2 Structure of the verification argument (predictions left open)

The Verification Plan at Gate B will have exactly this shape. It is stated now, empty, so that the argument cannot be reshaped after the data arrives.

```
  CAL-1 telemetry
      |
      +--> binds TBD-01..TBD-25          [Calibration Report, with tier + evidence]
      +--> unit-verifies CMP-1..CMP-15   [Calibration Report]
      |
  OP-MEAS-1 (T1) --> anchors c_us
      |
      v
  executable model at the committed configuration
      |
      +--> solves r_trig                  [the design variable]
      +--> emits predicted gap, sigma, and the per-requirement roll-up
      |
      v
  FROZEN PREDICTION  =  model output, committed before VER-1 is flashed
      |
      v
  VER-1 integrated run --> compared against the frozen prediction
      |
      +-- consistent --> Gate C: Verification Report closes every requirement
      +-- falsified  --> diagnose the responsible PARAMETER, re-bind, re-run the model,
                         issue a NEW frozen Verification Plan version, take another VER run.
                         The program is NOT empirically tweaked.
```

The frozen prediction will be the **output of the executable model**, not a narrative: predicted final gap, predicted sigma, predicted at-rest reading, predicted trigger-to-rest travel, and the PASS/FAIL roll-up per requirement. Each of those is separately falsifiable by VER-1's telemetry, which means a single run can discriminate *which* parameter is wrong rather than merely that something is.

### 4.3 What closes where

| Requirement group | Closes at | On what evidence |
|---|---|---|
| CMP-1..CMP-15 | Gate B (Calibration Report) | CAL-1 unit tests, pulled forward into the Verification Report at Gate C |
| FUN-1..FUN-11 | Gate C | CAL-1 + VER-1 telemetry; several by inspection of the frozen program |
| SYS-1..SYS-7 | Gate C | VER-1 against the frozen prediction |
| **SYS-8, STK-2 (objective)** | **Gate C only** | **Only on evidence that the predicted final gap was validated against operator ground truth at the operating point.** Not closable from onboard data alone — that is the entire content of SYS-8. |
| STK-1, STK-3, STK-4, STK-5 | Gate C | roll-up over the above |

---

## 5. Current model roll-up (pre-calibration)

Run at the prior mid-points, to show the requirement set is not internally contradictory before any data exists. `PENDING` means an operand is still unbound — the model reports it as pending rather than assuming a value.

```
| req | level | shape | method | measured | target | verdict |
|---|---|---|---|---|---|---|
| STK-1 | STK | LowerBound | test | 27.060 | 0.000 | PASS |
| STK-2 | STK | UpperBound | analysis | 27.060 | 27.060 | PASS |
| STK-3 | STK | LowerBound | inspection | -- | -- | PENDING |
| STK-4 | STK | UpperBound | test | 4.000 | 5.000 | PASS |
| STK-5 | STK | UpperBound | test | -- | -- | PENDING |
| SYS-1 | SYS | LowerBound | analysis | 27.060 | 0.000 | PASS |
| SYS-2 | SYS | UpperBound | test | -- | -- | PENDING |
| SYS-3 | SYS | UpperBound | analysis | 525.000 | 2646.616 | PASS |
| SYS-4 | SYS | LowerBound | analysis | 27.060 | 27.060 | PASS |
| SYS-5 | SYS | LowerBound | inspection | -- | -- | PENDING |
| SYS-6 | SYS | UpperBound | test | 4.000 | 5.000 | PASS |
| SYS-7 | SYS | LowerBound | test | -- | -- | PENDING |
| SYS-8 | SYS | UpperBound | test | -- | -- | PENDING |
| FUN-1 | FUN | UpperBound | test | -- | -- | PENDING |
| FUN-10 | FUN | LowerBound | inspection | -- | -- | PENDING |
| FUN-11 | FUN | UpperBound | test | -- | -- | PENDING |
| FUN-2 | FUN | UpperBound | analysis | 56.250 | 120.000 | PASS |
| FUN-3 | FUN | LowerBound | analysis | 93.555 | 89.018 | PASS |
| FUN-4a | FUN | LowerBound | analysis | 133.555 | 50.000 | PASS |
| FUN-4b | FUN | UpperBound | analysis | 133.555 | 1990.000 | PASS |
| FUN-5 | FUN | UpperBound | test | -- | -- | PENDING |
| FUN-6 | FUN | UpperBound | test | -- | -- | PENDING |
| FUN-7 | FUN | UpperBound | inspection | -- | -- | PENDING |
| FUN-8 | FUN | UpperBound | test | -- | -- | PENDING |
| FUN-9 | FUN | LowerBound | inspection | -- | -- | PENDING |
| CMP-1 | CMP | UpperBound | test | -- | -- | PENDING |
| CMP-10 | CMP | UpperBound | test | -- | -- | PENDING |
| CMP-11 | CMP | UpperBound | test | -- | -- | PENDING |
| CMP-12 | CMP | UpperBound | test | -- | -- | PENDING |
| CMP-13 | CMP | UpperBound | test | -- | -- | PENDING |
| CMP-14 | CMP | UpperBound | test | 12.500 | 20.000 | PASS |
| CMP-15 | CMP | UpperBound | test | -- | -- | PENDING |
| CMP-2 | CMP | UpperBound | test | -- | -- | PENDING |
| CMP-3 | CMP | UpperBound | test | 50.000 | 67.060 | PASS |
| CMP-4 | CMP | UpperBound | test | 32.500 | 80.000 | PASS |
| CMP-5 | CMP | UpperBound | test | 35.000 | 80.000 | PASS |
| CMP-6 | CMP | LowerBound | test | -- | -- | PENDING |
| CMP-7 | CMP | LowerBound | test | -- | -- | PENDING |
| CMP-8 | CMP | UpperBound | test | -- | -- | PENDING |
| CMP-9 | CMP | UpperBound | test | -- | -- | PENDING |
```

---

## 6. What happens next, and what it costs

| Step | Rover cost | Operator cost |
|---|---|---|
| Gate A review | 0 | review only |
| CAL-1 flash + run | **1 program** | readiness confirmation (free), reset to start line (free) |
| OP-MEAS-1 | 0 | **1 measurement** |
| Gate B: Calibration Report + frozen Verification Plan | 0 | review only |
| VER-1 flash + run | **1 program** | readiness confirmation (free) |
| Gate C: Verification Report | 0 | possibly 1 further measurement (S3) |
| Operation: 5 scored runs of the locked program | 5 scored runs | power-cycle + reset only |

**Planned totals: 2 characterization programs, 1-2 operator measurements.**

---

*Gate A deliverables: requirements_spec_v1.md, wall_rover.sysml, wall_rover_model.py, model_reqs.py, calibration_plan_v1.md. Awaiting operator review. No hardware will be touched until this gate clears and the hub is confirmed ready.*
