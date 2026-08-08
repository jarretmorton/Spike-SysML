# CALIBRATION PLAN — Wall-Approach Rover

**Document type: PLAN** (forward-looking; revised and re-issued as a new version whenever a characterization run reveals something this version did not anticipate; prior versions retained). **Version 1.0. GATE A. No hardware has been touched.**

Companion artifacts: `01_requirements_spec.md` (source of truth for requirements), `wall_rover.sysml` (formal model), `wallstop_model.py` (executable model), `rover_wallstop.py` (the program this plan proposes to flash).

---

## 0. Sensitivity analysis

### 0.1 Method and priors

The executable model simulates the whole approach — accelerate to the ceiling, fuse ranger and odometry, brake at the computed instant, coast to rest — at 0.5 ms resolution, with the plant on **true** parameter values and the controller on its **believed** values. Each row below varies one parameter's *true* value across its assumed range while the controller keeps believing the prior nominal. That is deliberately the *mis-calibration* sensitivity, and it is the one that matters here: this architecture measures speed and range in-run, so what hurts is not a parameter being large but a parameter being **wrong**.

Two consequences are reported per parameter: the swing in the **objective** (final clearance, mm) and the swing in the **hard-constraint margin** `m_contact = z_conf · sigma_rss`, which is what SYS-5 requires the predicted clearance to clear. Some parameters move only one of the two — `sigma_psi` for instance does not shift where the rover stops at all, it shifts how much margin we must leave, which is the same thing as the achievable gap.

Priors are engineering priors and are an input to your review. They are wide on purpose: this rover's wheel diameter, gearing, brake authority, ranger update rate and sensor mounting are all unmeasured, and stating them narrowly would smuggle in the calibration that has not happened yet (tenet A3).

| Parameter | Prior range | Basis for the prior |
|---|---|---|
| `psi_brake` | 1.8 .. 569.9 mm | DERIVED from the (v, t_chain, a_brake) priors so the prior box stays self-consistent — not an independent guess |
| `k_eff` | 0.3 .. 0.85 mm/deg | wheel diameters from 43 mm to 88 mm across the SPIKE/Technic range, direct drive, times slip |
| `b_offset` | -80 .. 15 mm | ranger recessed 0-80 mm behind the bumper, plus +-15 mm sensor bias |
| `a_brake` | 900 .. 9000 mm/s^2 | passive short-circuit braking on a light chassis; weak-brake end allows for a slick floor |
| `d_odo_drift` | -0.04 .. 0.04 1 | within-run odometric scale drift from slip variation |
| `sigma_psi` | 1 .. 20 mm | run-to-run brake scatter on a battery-powered drivetrain |
| `eps_scale` | -0.03 .. 0.03 1 | speed-of-sound and clock tolerance on a time-of-flight device |
| `sigma_ls` | 0.002 .. 0.03 s | residual after a two-pass calibration |
| `l_sensor` | 0 .. 0.12 s | ultrasonic time-of-flight plus internal processing plus UART transport |
| `t_chain` | 0 .. 0.04 s | firmware command-to-torque latency, sub-frame to a few control cycles |
| `q_range` | 1 .. 20 mm | the device may report centimetres or millimetres — a reporting artifact, not a physical resolution (tenet D1) |
| `a_accel` | 500 .. 2500 mm/s^2 | commanded acceleration limit, bounded below by torque-limited operation |
| `g_start` | 950 .. 1050 mm | operator-stated ~1000 mm, held constant |
| `psi_head` | 0 .. 6 deg | open-loop straightness of a differential drive over ~1 m |
| `omega_cruise` | 600 .. 1150 deg/s | rated no-load speeds of the SPIKE medium and large angular motors |
| `t_refresh_phase` | 0 .. 1 1 | uniform; the ranger's ping phase at boot is uncontrollable and re-drawn every run |
| `t_refresh` | 0.01 .. 0.12 s | LEGO UART sensor update rates from 8 Hz to 100 Hz |
| `sigma_b` | 1 .. 4 mm | steel-rule resolution plus static read noise |
| `d_psi_head` | 0 .. 3 deg | run-to-run variation of that veer |
| `e_trig` | 0 .. 0.004 s | 1 ms wait granularity plus loop overrun |
| `w_half` | 40 .. 80 mm | half-width of a SPIKE chassis |
| `r_min_valid` | 30 .. 60 mm | vendor near-range limit for the SPIKE distance sensor |
| `d_agree` | 0 .. 60 mm | two nominally identical sensors, different mounting depth |
| `slip_brake` | 0 .. 0.15 1 | skid fraction during braking; odometry under-reads if the wheels lock |
| `omega_left` | 600 .. 1150 deg/s | as omega_cruise, per motor |
| `omega_right` | 600 .. 1150 deg/s | as omega_cruise, per motor |
| `d_omega` | 0 .. 120 deg/s | wheel-speed asymmetry under independent PID control |
| `track` | 90 .. 180 mm | SPIKE chassis track width |
| `omega_floor` | 500 .. 900 deg/s | threshold TBD; set at GATE B from the measurement |
| `psi_travel_limit` | 20 .. 600 mm | threshold TBD; set at GATE B from the measurement |
| `sigma_psi_limit` | 2 .. 25 mm | threshold TBD; set at GATE B |
| `l_sensor_limit` | 0.02 .. 0.15 s | threshold TBD; set at GATE B |
| `t_refresh_limit` | 0.02 .. 0.15 s | threshold TBD; set at GATE B |
| `q_range_limit` | 1 .. 25 mm | threshold TBD; set at GATE B |
| `d_agree_limit` | 5 .. 80 mm | threshold TBD; set at GATE B |
| `e_trig_limit` | 0.001 .. 0.01 s | threshold TBD; set at GATE B |

### 0.2 REQUIRED TABLE — parameter sensitivity, ranked

Evaluated at the operating configuration (commanded target clearance 30 mm, backstop wide). `dG/dp` is the local coefficient; the "range for ≤2 mm" column inverts it into the **binding tolerance** each parameter must be calibrated to if its residual contribution is to stay under 2 mm — which is what actually drives the run design.

| # | parameter (SysML attr) | assumed range | objective swing dG | margin swing dm | dG/dp | range for <=2 mm | knowledge tier | priority |
|---|---|---|---|---|---|---|---|---|
| 1 | `psi_brake` (psiBrake) | 1.8 .. 569.9 mm | 564.4 mm | 0.0 mm | 0.994 mm per mm | +/-1.01 mm | T2-prior | 1-CRITICAL |
| 2 | `k_eff` (kEff) | 0.3 .. 0.85 mm/deg | 440.9 mm | 7.7 mm | 802 mm per mm/deg | +/-0.00125 mm/deg | T2-prior | 1-CRITICAL |
| 3 | `b_offset` (bOffset) | -80 .. 15 mm | 91.5 mm | 0.0 mm | 0.963 mm per mm | +/-1.04 mm | T2-prior | 1-CRITICAL |
| 4 | `a_brake` (aBrake) | 900 .. 9000 mm/s^2 | 78.4 mm | 0.0 mm | 0.00968 mm per mm/s^2 | +/-103 mm/s^2 | T2-prior | 1-CRITICAL |
| 5 | `d_odo_drift` (dOdoDrift) | -0.04 .. 0.04 1 | 75.7 mm | 0.0 mm | 946 mm per 1 | +/-0.00106 1 | T2-prior | 1-CRITICAL |
| 6 | `sigma_psi` (sigmaPsi) | 1 .. 20 mm | 0.0 mm | 47.1 mm | 0 mm per mm | n/a mm | T2-prior | 1-CRITICAL |
| 7 | `eps_scale` (epsScale) | -0.03 .. 0.03 1 | 36.2 mm | 0.0 mm | 604 mm per 1 | +/-0.00166 1 | T2-prior | 1-CRITICAL |
| 8 | `sigma_ls` (sigmaLs) | 0.002 .. 0.03 s | 0.0 mm | 20.9 mm | 0 mm per s | n/a s | T2-prior | 2-high |
| 9 | `l_sensor` (lSensor) | 0 .. 0.12 s | 19.8 mm | 0.0 mm | 165 mm per s | +/-0.00606 s | T2-prior | 2-high |
| 10 | `t_chain` (tChain) | 0 .. 0.04 s | 15.8 mm | 0.0 mm | 396 mm per s | +/-0.00252 s | T2-prior | 2-high |
| 11 | `q_range` (qRange) | 1 .. 20 mm | 12.5 mm | 1.1 mm | 0.657 mm per mm | +/-1.52 mm | T2-prior | 2-high |
| 12 | `a_accel` (aAccel) | 500 .. 2500 mm/s^2 | 8.7 mm | 0.0 mm | 0.00437 mm per mm/s^2 | +/-229 mm/s^2 | T2-prior | 3-moderate |
| 13 | `g_start` (gStart) | 950 .. 1050 mm | 7.5 mm | 0.0 mm | 0.075 mm per mm | +/-13.3 mm | T2-prior | 3-moderate |
| 14 | `psi_head` (psiHead) | 0 .. 6 deg | 6.3 mm | 0.0 mm | 1.05 mm per deg | +/-0.957 deg | T2-prior | 3-moderate |
| 15 | `omega_cruise` (omegaCruise) | 600 .. 1150 deg/s | 6.1 mm | 4.5 mm | 0.0111 mm per deg/s | +/-89.9 deg/s | T2-prior | 3-moderate |
| 16 | `t_refresh_phase` (tRefreshPhase) | 0 .. 1 1 | 5.9 mm | 0.0 mm | 5.94 mm per 1 | +/-0.168 1 | T2-prior | 3-moderate |
| 17 | `t_refresh` (tRefresh) | 0.01 .. 0.12 s | 4.8 mm | 0.0 mm | 43.2 mm per s | +/-0.0231 s | T2-prior | 3-moderate |
| 18 | `sigma_b` (sigmaB) | 1 .. 4 mm | 0.0 mm | 2.8 mm | 0 mm per mm | n/a mm | T2-prior | 4-low |
| 19 | `d_psi_head` (dPsiHead) | 0 .. 3 deg | 0.0 mm | 1.9 mm | 0 mm per deg | n/a deg | T2-prior | 4-low |
| 20 | `e_trig` (eTrig) | 0 .. 0.004 s | 1.6 mm | 0.5 mm | 396 mm per s | +/-0.00252 s | T2-prior | 4-low |
| 21 | `w_half` (wHalf) | 40 .. 80 mm | 1.0 mm | 0.3 mm | 0.0262 mm per mm | +/-38.2 mm | T2-prior | 4-low |
| 22 | `r_min_valid` (rMinValid) | 30 .. 60 mm | 0.0 mm | 0.0 mm | 0 mm per mm | n/a mm | T1-vendor | 4-low |
| 23 | `d_agree` (dAgree) | 0 .. 60 mm | 0.0 mm | 0.0 mm | 0 mm per mm | n/a mm | T2-prior | 4-low |
| 24 | `slip_brake` (slipBrake) | 0 .. 0.15 1 | 0.0 mm | 0.0 mm | 0 mm per 1 | n/a 1 | T2-prior | 4-low |
| 25 | `omega_left` (omegaLeft) | 600 .. 1150 deg/s | 0.0 mm | 0.0 mm | 0 mm per deg/s | n/a deg/s | T2-prior | 4-low |
| 26 | `omega_right` (omegaRight) | 600 .. 1150 deg/s | 0.0 mm | 0.0 mm | 0 mm per deg/s | n/a deg/s | T2-prior | 4-low |
| 27 | `d_omega` (dOmega) | 0 .. 120 deg/s | 0.0 mm | 0.0 mm | 0 mm per deg/s | n/a deg/s | T2-prior | 4-low |
| 28 | `track` (track) | 90 .. 180 mm | 0.0 mm | 0.0 mm | 0 mm per mm | n/a mm | T2-prior | 4-low |
| 29 | `omega_floor` (omegaFloor) | 500 .. 900 deg/s | 0.0 mm | 0.0 mm | 0 mm per deg/s | n/a deg/s | T2-prior | 4-low |
| 30 | `psi_travel_limit` (psiTravelLimit) | 20 .. 600 mm | 0.0 mm | 0.0 mm | 0 mm per mm | n/a mm | T2-prior | 4-low |
| 31 | `sigma_psi_limit` (sigmaPsiLimit) | 2 .. 25 mm | 0.0 mm | 0.0 mm | 0 mm per mm | n/a mm | T2-prior | 4-low |
| 32 | `l_sensor_limit` (lSensorLimit) | 0.02 .. 0.15 s | 0.0 mm | 0.0 mm | 0 mm per s | n/a s | T2-prior | 4-low |
| 33 | `t_refresh_limit` (tRefreshLimit) | 0.02 .. 0.15 s | 0.0 mm | 0.0 mm | 0 mm per s | n/a s | T2-prior | 4-low |
| 34 | `q_range_limit` (qRangeLimit) | 1 .. 25 mm | 0.0 mm | 0.0 mm | 0 mm per mm | n/a mm | T2-prior | 4-low |
| 35 | `d_agree_limit` (dAgreeLimit) | 5 .. 80 mm | 0.0 mm | 0.0 mm | 0 mm per mm | n/a mm | T2-prior | 4-low |
| 36 | `e_trig_limit` (eTrigLimit) | 0.001 .. 0.01 s | 0.0 mm | 0.0 mm | 0 mm per s | n/a s | T2-prior | 4-low |

Priority bands: 1-CRITICAL ≥ 30 mm of swing, 2-high ≥ 10 mm, 3-moderate ≥ 3 mm, 4-low below that.

### 0.3 What the table says

**Four parameters dominate, and they are dominated for different reasons.**

1. **`psi_brake` — brake travel, 564 mm of swing.** The largest single lever, and unavoidably so: whatever the rover travels after the brake command is subtracted from the clearance one-for-one. Its prior spans 2–570 mm because it is quadratic in a speed we have not measured and inverse in a deceleration we have not measured. It is, however, **directly observable onboard** (odometry between the brake command and rest), so it is cheap to bind — and it must be bound *at cruise speed*, because extrapolating it from a slow test is exactly the structural error the template warns about.
2. **`k_eff` — odometry scale, 441 mm of swing.** Not obvious in advance: the fused estimator re-anchors on the ranger continuously, so a scale error should only act over the short lever between the fusion window and the brake point. The sweep says otherwise — the lever is long enough (fusion window plus brake travel) that a factor-of-two scale error moves the stop by hundreds of millimetres. It is also the cheapest parameter to bind well (a static staircase, zero speed, no latency), which makes it the natural first activity.
3. **`b_offset` — ranger-to-bumper offset, 91 mm of swing, unity coefficient.** The one parameter in the top four that **no onboard channel can observe**: a ranger measures from its own datum and has no way to see where the bumper is. Every onboard estimate of clearance is therefore a hypothesis offset by an unknown constant. This is precisely the case the method reserves a costed operator measurement for, and §3 spends one on it.
4. **`sigma_psi` — brake repeatability, 47 mm of margin swing.** Moves no stop, but sets the margin, and therefore sets the floor on the achievable gap. With `sigma_psi` at the pessimistic end of its prior the required margin is ~47 mm; at the optimistic end it is a few millimetres. **The single biggest determinant of our score is not where we aim but how repeatable the brake is**, which is why CAL-1 is designed to brake at cruise speed twice rather than once.

Low-leverage parameters are deliberately **not** scheduled for characterization: `w_half` (1.0 mm across a 40-80 mm prior) and `track` matter only through second-order geometry, so measuring them would spend a costed operator action on a millimetre. That is a decision the table justifies, and it is recorded rather than left implicit.

### 0.4 The uncertainty budget this implies

The no-contact margin is the root-sum-square of the independent contributors, never a guessed safety factor (tenet A6). At the priors:

| Contributor | Value at priors | Bound by |
|---|---|---|
| fused range-offset (quantisation/sqrt(12n)) | 1.18 mm | CAL-1 P2/P4 (`q_range`, `n_fuse`) |
| b_offset anchor (ruler + read noise) | 2.00 mm | M1 (operator measurement) |
| brake travel run-to-run | 6.00 mm | CAL-1 P4 vs P6, third sample at VER |
| ranger latency residual (v*sigma_ls) | 3.96 mm | CAL-1 P4/P6 dynamic-vs-static comparison |
| trigger timing (v*e_trig) | 0.59 mm | CAL-1 P4 commanded vs achieved brake instant |
| heading/corner geometry | 1.05 mm | CAL-1 P4 vs P6 IMU yaw |
| **RSS** | **7.65 mm** | |
| **m_contact = z·RSS (z=3)** | **23.0 mm** | |

So *if* the priors were the post-calibration uncertainties, the smallest defensible target clearance would be about **23 mm**. Every millimetre CAL-1 removes from these contributors — above all from `sigma_psi` and `sigma_ls` — comes straight off the scored gap. This is the quantitative link between the calibration plan and the score, and it is why the plan is built around repeatability rather than around a single well-measured stop.

### 0.5 The sensitivity analysis changed the run design (CAL-1 safety)

A sweep ranks where to look; it does not validate anything. But run through the **joint** prior box it does one more job: it tells us whether the first hardware run is safe. The answer, initially, was no.

Run through the **joint** prior box, the model answers one more question: is the first hardware run safe at all? Initially, no.

**A ranging-triggered first pass cannot be made safe by choosing the target.** The worst corner is a fast rover with a weak brake — cruise up to 978 mm/s, deceleration as low as 900 mm/s², so true stopping travel up to **570 mm on a 1000 mm runway** — while the controller, running on priors, believes ~26 mm. No target survives that: raising it far enough to cover 570 mm of error leaves no room to reach cruise, and the whole approach is then untested at the operating speed.

Two design changes follow, and they are the backbone of the run design in §2.3.

**(a) The first max-speed brake event is triggered by the odometric backstop, not by ranging.** Braking after a fixed *travel* removes `psi_brake`, `b_offset`, `l_sensor`, `eps_scale` and the entire ranging chain from the safety argument, leaving only `k_eff`. The backstop is not a special test mode: it is CMP-10, the fail-safe path the design needs anyway, with its parameter set tight for this one phase. Same file, same hot loop, same trigger arithmetic — only which of the three candidate thresholds is the minimum changes.

**(b) `k_eff` is bound *before* that pass runs, inside the same program.** A static staircase — step, stop, read ranger and odometer at rest, repeat — binds the scale at zero speed with no latency, no dynamics and no contact risk.

With ranging out of the trigger path the landing point becomes **closed-form**, so the worst case is computed exactly rather than searched for:

    x_bs = s_backstop · (k_true/k_bound) / (1 + d_odo_drift)
    v_br = min(v_cruise, √(2·a_accel·x_bs))
    psi  = v_br·t_chain + v_br²/(2·a_brake)          [StoppingDistance template]
    G    = g_start − x_bs − psi − w_half·sin(psi_head)

Every term is monotone in its parameters, so the worst case *is* a corner. Evaluated at the prior extremes with `k_eff` bound to ±2% by the staircase (`wallstop_model.backstop_worst_case`):

| Backstop | True travel | v at brake | Worst psi | **Worst-case landing** | Verdict | Cruise segment at nominal |
|---|---|---|---|---|---|---|
| 200 mm | 213 mm | 978 mm/s | 570 mm | **+159 mm** | SAFE | 122 mm / 307 ms / 6.1 fresh samples |
| 250 mm | 266 mm | 978 mm/s | 570 mm | **+106 mm** | SAFE | 172 mm / 433 ms / 8.7 fresh samples |
| 300 mm | 319 mm | 978 mm/s | 570 mm | **+53 mm** | SAFE | 222 mm / 559 ms / 11.2 fresh samples |
| 345 mm | 367 mm | 978 mm/s | 570 mm | **+5 mm** | SAFE | 267 mm / 673 ms / 13.5 fresh samples |
| 400 mm | 425 mm | 978 mm/s | 570 mm | **−53 mm** | **CONTACT POSSIBLE** | — |
| 500 mm | 531 mm | 978 mm/s | 570 mm | **−160 mm** | **CONTACT POSSIBLE** | — |

**Chosen: backstop at 250 mm** — worst-case landing +106 mm of clearance over the entire remaining prior box, while still leaving ~430 ms at cruise before the brake, enough for the speed to plateau and for ~9 fresh ranger samples at cruise. `psi_brake` is therefore measured *at the speed it will be used at* (zero extrapolation, per the `StoppingDistance` template's own guidance). P4 does not need a long cruise segment: P6 supplies the long ranging-triggered rehearsal, once `psi_brake` is no longer a prior.

**Why the ordering is load-bearing.** The same closed form, with `k_eff` left at its raw prior spread instead of bound:

| Residual uncertainty on `k_eff` when P4 runs | Worst-case landing |
|---|---|
| ±2% (staircase P2 ran first) | **+106 mm** — safe |
| ±20% | +46 mm — safe |
| ±74% (raw prior, no staircase) | **−630 mm** — contact |

So the staircase is not merely economical batching; it is what makes the max-speed pass admissible at all (tenets A5, B2 — verify in dependency order, least-coupled quantity first).

> **Correction recorded at gate review.** An earlier draft of this section sized the backstop with a *directed corner search* over the simulation: each parameter's worst direction fixed one-at-a-time at the nominal. That heuristic reported a **500 mm** backstop as safe with a worst case of +212 mm. It is wrong: it misses corners where one parameter's worst direction depends on another (`a_accel` only matters once the rover can reach cruise, and only then does the worst `psi` apply). The exact closed form shows a 500 mm backstop permits **−160 mm**, i.e. contact. The value was changed to 250 mm, the flight program's `S_BACKSTOP` with it, and the heuristic is retained in the model only as a cross-check, explicitly labelled as unsound for worst-case use. This is the first entry in this plan's revision record.

---

## 1. Calibration input list

### 1.1 Model-completion parameters (free, but named by no requirement)

These the model needs in order to predict at all; they are not requirement TBDs.

| Parameter | SysML attribute | Unit | Bound by | Why the model needs it |
|---|---|---|---|---|
| `k_eff` | `kEff` | mm/deg | CAL-1/P6 (static staircase) + P2 (cruise sweep) | converts encoder degrees into millimetres everywhere |
| `omega_cruise` | `omegaCruise` | deg/s | CAL-1/P2 | sets cruise speed, hence brake travel and every latency-to-mm conversion |
| `a_accel` | `aAccel` | mm/s^2 | CAL-1/P2 | sets how much runway is spent reaching cruise (CMP-3 feasibility) |
| `a_brake` | `aBrake` | mm/s^2 | CAL-1/P2+P4+P5 (3-speed fit) | supplies the first-order speed correction to brake travel |
| `t_chain` | `tChain` | s | CAL-1/P2 (decel onset) | the platform latency term of the same correction |
| `l_sensor` | `lSensor` | s | CAL-1/P2+P4 (dynamic-vs-static offset comparison) | how stale the newest range sample is, in millimetres of unseen travel |
| `t_refresh` | `tRefresh` | s | CAL-1/P2 | how far the rover moves between absolute updates |
| `q_range` | `qRange` | mm | CAL-1/P2+P6 | noise floor of the fused range offset |
| `eps_scale` | `epsScale` | 1 | CAL-1/P6 (static staircase regression) | range-dependence of the ranger against odometry |
| `d_odo_drift` | `dOdoDrift` | 1 | CAL-1/P2..P7 (o_rest vs o_start consistency over the traverse) | degrades the dead-reckoning backstop; must not fire before the primary |
| `slip_brake` | `slipBrake` | 1 | CAL-1/P2+P4 (o_rest vs o_trigger consistency) | if the wheels skid, odometry under-reads brake travel — a systematic that would ship a too-small psi |
| `sigma_ls` | `sigmaLs` | s | CAL-1/P2+P4 | residual latency error, an uncertainty contributor |
| `sigma_b` | `sigmaB` | mm | M1 | anchor uncertainty, an uncertainty contributor |
| `d_psi_head` | `dPsiHead` | deg | CAL-1/P2 vs P4 | run-to-run heading variation, an uncertainty contributor |
| `g_start` | `gStart` | mm | CAL-1/P0 (static baseline, in reported-range space) | runway available; also the dead-reckoning anchor |
| `w_half` | `wHalf` | mm | not scheduled -- low leverage (see sensitivity table) | converts heading error to corner clearance loss (low leverage) |
| `track` | `track` | mm | not scheduled -- low leverage; used only to derive the CMP-14 limit | derives the wheel-symmetry limit from the heading limit (low leverage) |
| `t_refresh_phase` | `tRefreshPhase` | 1 |  | uncontrollable nuisance; quantifies irreducible run-to-run spread |

### 1.2 Requirement-TBD register (from the specification §6)

| TBD | Quantity | Parameter | Bound by | Planned tier |
|---|---|---|---|---|
| TBD-1 | minimum sustained wheel speed at the ceiling | `omega_cruise` | CAL-1 P4/P6 cruise plateau, per motor | T4-onboard-multi |
| TBD-2 | travel needed to reach ceiling speed | `a_accel` | CAL-1 P4 speed ramp | T4-onboard-multi |
| TBD-3 | primary ranger offset to the front-most point | `b_offset` | CAL-1 P8 static block + M1 operator measurement | T5-external |
| TBD-4 | ranger fresh-sample interval | `t_refresh` | CAL-1 P4 value-change interval histogram | T4-onboard-multi |
| TBD-5 | ranger sample staleness | `l_sensor` | CAL-1 P4/P6 dynamic-vs-static offset comparison | T4-onboard-multi |
| TBD-6 | ranger reported quantisation step | `q_range` | CAL-1 P2 static staircase + P4 trace | T4-onboard-multi |
| TBD-7 | odometry-to-range scale factor | `k_eff` | CAL-1 P2 static staircase regression | T4-onboard-multi |
| TBD-8 | primary-secondary ranger agreement | `d_agree` | CAL-1 P0/P2/P8 static blocks | T4-onboard-multi |
| TBD-9 | brake-command timing error | `e_trig` | CAL-1 P4 commanded vs achieved brake instant | T4-onboard-multi |
| TBD-10 | brake travel from command to rest at cruise | `psi_brake` | CAL-1 P4 and P6, odometry and ranger | T4-onboard-multi |
| TBD-11 | run-to-run scatter of brake travel | `sigma_psi` | CAL-1 P4 vs P6 (+ VER as a third sample) | T4-onboard-multi |
| TBD-12 | heading deviation limit and IMU drift | `psi_head / d_psi_head` | CAL-1 P4/P6 IMU yaw and differential odometry | T4-onboard-multi |
| TBD-13 | wheel-speed symmetry during cruise | `-- (encoder pair)` | CAL-1 P4/P6 per-motor speed traces | T4-onboard-multi |
| TBD-14 | allowed uncertainty of the reported clearance estimate | `sigma_est_limit` | design decision at GATE B, verified at GATE C | T0-design |
| TBD-15 | ranger validity floor | `r_min_valid` | CAL-1 P7 fine staircase into the near field | T4-onboard-multi |
| TBD-16 | no-contact margin | `m_contact` | computed at GATE B from the bound sigma contributors | T4-onboard-multi |
| TBD-17 | margin-efficiency factor | `k_obj` | design decision at GATE B | T0-design |

Note the two classes. Most TBDs are **values to be measured** (`k_eff`, `psi_brake`, `l_sensor`...). A few are **requirement thresholds** (`omega_floor`, `psi_travel_limit`, `sigma_psi_limit`, ...) which are set at GATE B from the measured value plus a tolerance, and then verified against a *later, independent sample* — the verification run. A threshold set from a measurement and then "verified" against that same measurement would be circular; the VER run is what makes those CMP verdicts mean something.

### 1.3 Deliberately not characterized

`w_half`, `track`, `r_max_valid` and the design constants. The sensitivity table shows their combined leverage is under 2 mm; carrying their priors into the margin costs less than measuring them would. Recorded here so the omission is a decision with evidence, not an oversight.

---

## 2. Characterization method

### 2.1 Channel catalog and cross-sourcing

Every quantity to be calibrated, with **all** independent onboard channels that observe it — derived from the platform inventory, not just the obvious one — ranked by directness and confidence. Every characterization phase logs every catalogued channel bearing on the quantities it touches, not only the channel under test (tenet B1). Disagreement is the fault detector, and it is fault-agnostic: we never assume in advance which channel is wrong.

| Quantity | Channels, ranked by directness | Hand-off / notes | Bound in |
|---|---|---|---|
| **Clearance to wall** | 1 primary ranger at rest (static, latency-free) · 2 primary ranger in motion (stale by `l_sensor`) · 3 secondary ranger · 4 odometry from a static anchor · 5 IMU double integration (rejected: drift) | Channel 1 has a validity floor (`r_min_valid` ≈ 40 mm). Below it the hand-off is to channel 4, which is valid at any range — planned, not improvised. All four are offset by the unobservable `b_offset`. | P2, P4, P6, P7, P8 + M1 |
| **Travel** | 1 odometry, both motors averaged · 2 change in reported range · 3 IMU integration (rejected) | 1 and 2 are compared over every phase; their disagreement over a brake event is the skid detector (`slip_brake`). | P2 (static), P4/P6 (dynamic) |
| **Cruise speed** | 1 `motor.speed()` per motor · 2 differentiated odometry · 3 differentiated range | Per-motor speeds also give wheel symmetry (CMP-14) — one channel, two requirements. | P4, P6 |
| **Brake travel `psi_brake`** | 1 odometry between brake command and rest · 2 (fused range offset at command) minus (reported range at rest) · 3 IMU deceleration integrated | Channels 1 and 2 are independent in exactly the way that matters: if the wheels skid, 1 under-reads and 2 does not. | P4, P6 |
| **Ranger staleness `l_sensor`** | 1 dynamic range offset minus static range offset, divided by speed · 2 phase of the value-change events against odometry | This is the one quantity with no static analogue — it only exists in motion, so it is bootstrapped off the static offset, which is the trusted reference (B2). | P4, P6 |
| **Ranger refresh and quantisation** | 1 intervals between value changes at known speed · 2 histogram of consecutive differences · 3 static repeat reads | Reporting artifacts, not physics (D1): what the estimator sees is the step size, whatever the device's internal resolution. | P2, P4 |
| **Heading / straightness** | 1 IMU yaw · 2 differential odometry · 3 difference between the two forward rangers (the only channel sensitive to ABSOLUTE squareness to the wall, since IMU yaw is relative to boot) | Channel 3 is coarse (quantisation over an unknown lateral separation) so it is used as a plausibility check on the operator's squaring, not as a measurement. | P0, P4, P6, P8 |
| **Contact** | 1 IMU forward-axis acceleration transient · 2 discontinuity in the clearance channel · 3 odometry stall against commanded speed | Gives SYS-2 an onboard witness independent of both the ranger and the operator's eye. | P4, P6 (and every operation run) |
| **`b_offset` (ranger datum to bumper)** | **no onboard channel** — the sensor cannot observe its own mounting relative to the chassis front | Hence the single costed operator measurement, §3. | M1 |
| **Rear ranger** | serves no needed quantity | DROPPED by traceability. Logged at low rate in P0/P8 to VERIFY the drop: its range must increase while the forward ranges decrease. | P0, P8 (verification of drop-out only) |
| **Floor reflectance** | serves no needed quantity | DROPPED by traceability. Logged in P0/P8 to verify it carries no usable position information. | P0, P8 (verification of drop-out only) |

### 2.2 Source-of-truth hierarchy

Stated up front, before any data exists, so it cannot be rationalised afterwards:

| Tier | Source | Example here |
|---|---|---|
| **T5** | external ground truth (operator measurement) | the one gap measurement, M1 |
| **T4** | anchored or multi-point onboard calibration | `k_eff` from a 5-point static staircase; `psi_brake` from two cruise brake events |
| **T3** | single onboard sample | a lone reading at rest |
| **T1** | vendor / firmware datasheet | ranger near-range limit, motor rated speed |
| **T2** | engineering prior | everything in §0.1 today |

Rules, applied without exception:

1. **A lower tier never silently overwrites a higher one.** The executable model enforces this in code: `bind()` refuses a write that would lower a parameter's tier and raises instead. A later sample that disagrees with a higher-tier value is a **discrepancy to diagnose** — low battery? range dependence? glitch? — not grounds to re-fit the constant.
2. **Every bound value carries its evidence basis**: how many samples, against what reference, at what tier. The Calibration Report tabulates all three per parameter.
3. **A sensor value driving a scored quantity is a HYPOTHESIS until confirmed against an independent higher-tier source at the operating point.** The final gap is the scored quantity, so the clearance channel may not close the objective on its own authority, however self-consistent it looks. That is what M1 is for.
4. **On a significant disagreement, or on any physically impossible reading, escalate to better data** rather than arbitrating between suspect channels. Asking the model whether its own falsification is worth chasing is asking the wrong model.

### 2.3 Test-like-you-fly run construction

**One program, two modes.** `rover_wallstop.py` contains a single `approach()` function: the hot loop, the trigger arithmetic, the sub-loop wait, the brake call and the buffer skeleton. `MODE = "CAL"` runs it inside a scaffold of extra phases; `MODE = "OP"` runs it alone. The characterization program is therefore a strict superset of the operation program **by construction, not by discipline** — there is no second copy of the control loop to drift.

**All characterization logging is off the hot path.** The loop appends integers to pre-allocated lists. Nothing is written to stdout until the motors have stopped. Hub-computed summaries are emitted *first* and raw traces second, decimated, so that if BLE throughput truncates the dump we lose audit detail rather than the values that bind parameters.

**Phase design.** One run, eight phases, ordered so that each phase's safety depends only on parameters already bound by an earlier phase:

| Phase | What it does | Binds / verifies | Safety basis |
|---|---|---|---|
| **P0** | static baseline at the start line: 12 samples of both forward rangers, rear ranger, reflectance, IMU yaw and acceleration | `g_start`, `d_agree`, `q_range` (static repeat), IMU rest vector (identifies the forward axis), drop-out verification for the rear ranger and reflectance | stationary |
| **P1** | port discovery on all six ports; **two-stage probe**: stage A (120 deg/s, 150 ms) asks only whether the drivetrain is mirrored, from IMU yaw; stage B (300 deg/s, 400 ms) is a pure translation that (i) classifies the three rangers by **2-vs-1 majority of the sign of range change** — the two that agree are the forward pair, the odd one out is the rear — and (ii) fixes the drive sign; then a bang-bang IMU yaw-null back to square | CMP-15, CMP-16; the forward/rear ranger assignment; a first low-speed `k_eff` sanity check | stage A moves 5–20 mm and rotates ≤13° if mirrored; stage B translates 36–102 mm, 900+ mm from the wall |
| **P2** | **static staircase, coarse**: 5 steps of 120 mm at 220 deg/s, full stop and static block at each | **`k_eff` to ±1-2%**, `eps_scale` (linearity over 1000→400 mm), `q_range`, `d_agree` vs range; CMP-6, CMP-21 | steps are odometric but gated by a 200 mm reported-range floor checked every 5 ms; worst case stops ≈170 mm reported |
| **P3** | reverse to the start line, closed-loop on the ranger | `d_odo_drift` (reverse-direction odometry vs ranger) | low speed, moving away from the wall |
| **P4** | **max-speed pass 1**, brake triggered by the odometric backstop at 250 mm | **`psi_brake` at cruise**, `omega_left`, `omega_right`, `d_omega`, `a_accel`, `a_brake`, `t_chain`, `l_sensor`, `e_trig`, `slip_brake`, `psi_head`; CMP-1, CMP-2, CMP-3, CMP-5, CMP-8, CMP-10, CMP-11, CMP-13, CMP-14, CMP-19, CMP-20 | backstop + `k_eff` bound in P2 → exact worst-case landing **+106 mm**, nominal ≈720 mm |
| **P5** | reverse to the start line | second `d_odo_drift` sample | as P3 |
| **P6** | **max-speed pass 2**, brake triggered by the *fused ranging chain* with a 220 mm target — the first end-to-end rehearsal of the operational algorithm | **`sigma_psi`** (second cruise brake event), second `l_sensor` sample, FUN-2/FUN-3 as an integrated function, `d_psi_head` | `psi_brake` now measured in P4, so the ranging trigger is no longer running on a prior; backstop still armed at 2000 mm as a net |
| **P7** | **static staircase, fine**: up to 8 steps of 18 mm until the reported range reaches 130 mm | `r_min_valid` (CMP-17), near-range linearity, near-range `d_agree`; and it parks the rover at the operating range for M1 | low speed, 112 mm reported floor; worst case ≈28 mm true clearance if `b_offset` is at its most negative |
| **P8** | final static block, 20 samples of every channel; then dump | `b_offset` (with M1), CMP-12 (no post-stop motion), drop-out verification | stationary |

**Why one run and not three.** Every phase above is a different measurement on the same traverse; splitting them into separate programs would multiply the program-count score without adding information, and would re-introduce the very cross-run drift the operator's power-cycling is there to control out. The cost is that a bug wastes more; that is why the program is being presented for review before it is flashed, and why every phase carries its own timeout, range floor and watchdog and falls through to the dump rather than hanging.

Run parameters requested: `timeout_seconds = 75` (motion budget ≈ 25 s, global watchdog at 30 s, remainder for the BLE dump of ~450 lines).

### 2.4 Plausibility bounds (the impossible-reading rule)

Every logged channel carries a physical bound, checked in-loop, with a flag bitmask emitted first in the dump. These make model-contradicting readings surface automatically instead of waiting to be noticed:

| Channel | Bound | Escalation if violated |
|---|---|---|
| reported range | 25 .. 2000 mm; must not increase while driving forward | unconditional escalation: a rest reading farther than the trigger reading is physically impossible and falsifies a load-bearing assumption |
| cruise speed | within 0.4–1.3 × the P4 plateau | anomaly report, sensitivity-ranked |
| heading | |Δψ| ≤ 12° (abort), ≤ 5° (SYS-4) | brake immediately, then diagnose |
| odometry vs ranger over a phase (`o_consistency`) | |Δ| ≤ 15 mm | skid or scale error: diagnose, do not re-fit |
| brake travel | 0 < psi < 600 mm, monotone approach to rest | non-monotone rest implies rollback: escalate |
| IMU acceleration | |a| ≤ 4 g | impact or drop: escalate |

---

## 3. Outside-input request

**One measurement, M1.** After CAL-1 completes, with the rover parked where P7 left it (reported range ≈ 130 mm, i.e. within a few tens of millimetres of the operating point):

> **M1 — measure the distance from the rover's front-most point to the wall, in millimetres.**

Why this measurement and why here:

- It binds **TBD-3 / `b_offset`**, the only top-four parameter with no onboard channel and unity leverage on the score (§0.3).
- It is taken **at rest**, so it is free of every dynamic effect, and **at the operating range**, so extrapolating it to the operation configuration involves only the ranger's residual scale error over a few tens of millimetres (≈1 mm).
- It converts the whole clearance chain from a self-consistent hypothesis into an anchored measurement — the T5 confirmation that §2.2 rule 3 requires before the scored quantity may be closed.

**Cross-checks batched around it (tenet B4).** The same rest pose is observed simultaneously by: the primary ranger (20 static samples), the secondary ranger, the odometric estimate accumulated from P0's anchor, and the fine staircase's step-by-step ranger-vs-odometer record leading into it. One operator action therefore anchors four channels at once and calibrates their mutual offsets, rather than just one number.

**A second measurement is planned but not requested yet.** GATE C requires the objective to be closed on ground truth *at the operating point*. M1 anchors the chain at the operating range but with the rover parked by a staircase, not by a max-speed stop. The Verification Plan will therefore request **M2**, the measured gap after the verification run, which is the operating point in full. That request belongs to GATE B, not here — and if the review prefers a different split, this is the moment to say so, because the plan is cheap to change now and expensive to change after CAL-1.

Nothing else is requested. Free operator actions used: power-cycle before the flash, reset to the start line and re-square after CAL-1 and M1.

---

## 4. Verification support

### 4.1 Unit verification carried by the calibration activities

Calibration and unit verification are combined in one program (tenet B3). Each CMP requirement below is closed by the phase that binds its parameter, with the verdict recorded in the Calibration Report at GATE B:

| CMP requirement | Phase | Evidence it produces |
|---|---|---|
| CMP-1 LeftMotorCeiling | P4 | left-motor speed plateau at commanded ceiling, ≥ threshold |
| CMP-2 RightMotorCeiling | P4 | right-motor speed plateau at commanded ceiling, ≥ threshold |
| CMP-3 AccelWithinRunway | P4 | travel to reach plateau, against the runway budget |
| CMP-4 PrimaryRangerBias | P7/P8 + M1 | offset from ground truth to reported range at rest |
| CMP-5 PrimaryRangerRefresh | P4 | distribution of intervals between reported-value changes |
| CMP-20 PrimaryRangerStaleness | P4/P6 | dynamic minus static range offset, divided by cruise speed |
| CMP-21 PrimaryRangerQuantisation | P2/P4 | histogram of consecutive reported-range differences |
| CMP-6 OdometryScale | P2 | 5-point regression of reported range against wheel angle at rest |
| CMP-7 SecondaryRangerAgreement | P0/P2/P7/P8 | primary-secondary difference across the whole range |
| CMP-8 TriggerTimingResolution | P4 | commanded brake instant vs achieved, from the hub clock |
| CMP-9 PlausibilityBounds | all | flag bitmask emitted; bounds listed in §2.4 |
| CMP-10 DeadReckonBackstop | P4 | backstop fires and is the recorded trigger source |
| CMP-11 BrakeTravel | P4/P6 | odometric and ranger-space brake travel at cruise |
| CMP-22 BrakeTravelRepeatability | P4 vs P6 | difference between two cruise brake events |
| CMP-12 NoPostStopMotion | P8 | 20 static samples over ~1 s show no drift in range or angle |
| CMP-13 HeadingSensing | P4/P6 | IMU yaw trace over the approach |
| CMP-14 WheelSpeedSymmetry | P4/P6 | per-motor speed traces during cruise |
| CMP-15 DeviceTypeIdentification | P1 | device type resolved on each of six ports |
| CMP-16 DrivePolarityIdentification | P1 | sign pair chosen, confirmed by range decreasing |
| CMP-17 RestRangeEstimator | P7 | lowest range still reported sensibly on the fine staircase |
| CMP-18 OdometricEstimator | P4/P6/P7 | odometric clearance estimate at each rest pose |
| CMP-19 ContactDetection | P4/P6 | forward-axis acceleration through the brake transient |

### 4.2 Structure of the verification argument (predictions left open)

The Verification Plan at GATE B will be this same roll-up with the right-hand column filled by the executable model evaluated at the bound values, and frozen before the verification run. Its shape is fixed now so that the prediction cannot be shaped to fit the result:

```
requirement -> model relation -> calibrated parameters -> predicted value | margin | verdict

STK-0  WallRunNeed              roll-up of children [—]
       predicted: <open>    margin: <open>    verdict: <open>
STK-1  SafeMaximumSpeedRun      roll-up of children [—]
       predicted: <open>    margin: <open>    verdict: <open>
SYS-1  MaximumApproachSpeed     LowerBound       [omega_cruise]
       predicted: <open>    margin: <open>    verdict: <open>
SYS-2  NoWallContact            LowerBound       [b_offset, psi_brake]
       predicted: <open>    margin: <open>    verdict: <open>
SYS-5  ClearanceMarginFloor     LowerBound       [sigma_psi, sigma_b, sigma_ls, b_offset, psi_brake]
       predicted: <open>    margin: <open>    verdict: <open>
SYS-3  CompleteStop             roll-up of children [—]
       predicted: <open>    margin: <open>    verdict: <open>
SYS-4  StraightApproach         UpperBound       [psi_head]
       predicted: <open>    margin: <open>    verdict: <open>
SYS-7  ClearanceReporting       UpperBound       [sigma_b, q_range, sigma_psi]
       predicted: <open>    margin: <open>    verdict: <open>
STK-2  ClosestStopObjective     roll-up of children [—]
       predicted: <open>    margin: <open>    verdict: <open>
OBJ-1  MarginEfficiency         UpperBound       [sigma_psi, sigma_b, sigma_ls]
       predicted: <open>    margin: <open>    verdict: <open>
```

Today that roll-up evaluates to **0/41 UNRESOLVED**, which is the correct state: not one parameter is bound, so not one requirement may claim a verdict. The executable model is three-valued for exactly this reason — a requirement whose parameters are unbound returns UNRESOLVED, never PASS.

### 4.3 Order of verification (tenet A5)

Verification order follows the dependency graph, not the requirement numbering:

1. **CMP-15, CMP-16** (port map, polarity) — everything else is meaningless if the wrong device is being read or the rover drives backwards.
2. **CMP-6, CMP-21** (odometry scale, quantisation) — the units in which every later quantity is expressed; and the safety of P4 rests on CMP-6.
3. **CMP-1, CMP-2, CMP-5, CMP-20, CMP-8** (per-effector speed, ranger timing, trigger timing) — single-effector properties, independent of each other.
4. **CMP-11, CMP-22, CMP-13, CMP-14, CMP-19** — brake and straightness behaviour at cruise, which depend on 2 and 3.
5. **CMP-4, CMP-17** — the ranging chain's absolute anchor, requiring M1.
6. **FUN-2, FUN-3** as integrated functions (P6), then **SYS-2, SYS-3, SYS-4, SYS-5, SYS-7** at the verification run.
7. **STK-0, STK-1, STK-2, OBJ-1** by roll-up at GATE C.

SYS-2 (no contact) is verified **last among the system requirements and never by operation**: the five scored runs are a demonstration and a repeatability sample, not the evidence that the rover will not hit the wall. That evidence has to exist before they are run.

---

## 5. Risks and re-plan triggers

This plan is a PLAN: any of the following observations in CAL-1 obliges a new version before GATE B, rather than a quiet adjustment.

| Observation | Interpretation | Re-plan action |
|---|---|---|
| `sigma_psi` (P4 vs P6) > 15 mm | brake repeatability alone forces a ~45 mm margin; the objective is bounded by physics, not by aim | re-issue with a third brake event or a different brake mode evaluated in the model first |
| `o_consistency` > 15 mm | wheels skid under braking, or the ranger's scale is wrong | diagnose which, using the static staircase (immune to skid) as arbiter; re-bind, do not re-fit |
| ranger reports in 10 mm steps AND `t_refresh` > 80 ms | the absolute channel is coarse and slow; the fused estimator's noise floor rises | re-derive `n_fuse` in the model and re-issue |
| heading deviation > 5° | SYS-4 fails as designed; open-loop symmetry is insufficient | add a *calibrated feedforward* trim fitted from the CAL-1 yaw trace — never an eyeballed steering gain |
| `psi_head` differs between P4 and P6 by > 2° | the veer is not repeatable, so it cannot be trimmed out, only budgeted | enlarge the geometry contributor and re-derive the margin |
| P4 speed plateau not reached before the backstop | 250 mm of runway insufficient; `psi_brake` was measured below cruise | re-issue with a longer backstop, justified by a new staged corner search |
| discovery finds fewer than 2 motors or 2 forward rangers | platform assumption wrong | halt, report, request operator confirmation of the build |

---

## 6. What is being asked of the reviewer

1. Are the **priors in §0.1** acceptable? They are the input to everything else; if any is badly placed, the run design should change now.
2. Is the **odometric-backstop-first ordering** (§0.5) accepted as the safety basis for the first max-speed brake event?
3. Is spending **one operator measurement now (M1)** and **one later (M2, at GATE B)** the split you want, given that GATE C requires the objective closed on ground truth at the operating point?
4. Any objection to the **CAL-1 program** (`rover_wallstop.py`) as written? It is presented before flashing precisely so that defects cost nothing.

On your go-ahead I will ask the readiness question, and only then flash.

---

## 7. Revision record

This is a **plan**: it is revised and re-issued whenever something invalidates its current version, with prior versions retained.

| Version | Change | Cause |
|---|---|---|
| v1.0 | initial issue | — |
| **v1.1** | CAL-1 backstop 500 → **250 mm**; §0.5 heuristic corner search replaced by an exact closed-form worst case | pre-flash verification of the plan's own safety claim: the heuristic understated the worst case and would have permitted contact on the first hardware run |
| **v1.1** | P1 rewritten as a two-stage probe with 2-vs-1 majority ranger classification | the flight program identified rangers by port order; if the rear ranger enumerated first, every range-based decision — including the polarity decision itself — would have inverted |
| **v1.1** | OP mode given its own slack backstop `S_BACKSTOP_OP` | OP reused the tight CAL backstop, which would have braked after 250 mm and stopped ~700 mm short on every scored run |
| **v1.1** | monotone-approach guard added to the hot loop (`o` rise > 50 mm → abort) | §2.4 promised this plausibility bound; the program did not implement it |
| **v1.1** | reverse leg given a 600 mm odometric cap; fine-staircase floor 100 → 112 mm, target 115 → 130 mm | unbounded reverse on a stuck ranger; worst-case fine-staircase clearance was ~11 mm |

No hardware has been run. Every change above is free analysis, made before the first flash.
