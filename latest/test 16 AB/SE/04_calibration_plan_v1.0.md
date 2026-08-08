# CALIBRATION PLAN — Wall-Approach Stop

**Document** CP-WALLSTOP · **Version 1.0** · **Type: PLAN** (forward-looking; revised and re-issued if a characterisation run reveals something this version did not anticipate — prior versions retained) · **Gate:** A · **Status:** issued for review, **no hardware touched**

Companions: RS-WALLSTOP-001 rev A (requirements), `wall_stop.sysml`, `wallstop_model.py`.

---

## 0. Sensitivity analysis — where to look, and why

Produced by `wallstop_model.sensitivity_table()`. Method: parameterise the flight program at the **prior nominal**, then let the parameter's **true** value range over its stated prior and compute the clearance the rover actually reaches (`realized_final_clearance`, the two-world evaluation). This answers the operative question — *if this parameter is as wrong as I currently allow it to be, where does the rover actually stop?*

**Priors are an input to your review.** They are assumptions, stated so you can challenge them, not measurements. Knowledge tiers: **T0** none · **T1** physics-bounded · **T2** datasheet · **T3** onboard multi-point · **T4** external ground truth.

Nominal design point: v = 470 mm/s, target gap = 30 mm, σ_gap = 15.0 mm, 3σ margin = 45 mm.

| # | Parameter | Assumed prior range | Prior rationale | Objective / hard-constraint-margin sensitivity | Tier | Priority |
|---|---|---|---|---|---|---|
| 1 | `a_brake` (mm/s²) | 1000 … 8000 | coast+rolling at the low end; tyre friction limit μ≈0.6 at the high end | final clearance **−49 … +48 mm** (span **97 mm**) — **CONTACT at the low end** | T1 | **1** |
| 2 | `k_travel` (mm/deg) | 0.30 … 0.65 | wheel Ø 40–70 mm, direct drive ⇒ πD/360 | final clearance +5 … +97 mm (span **93 mm**) | T1 | **2** |
| 3 | `t_response` (s) | 0.015 … 0.150 | loop phase + ranger refresh phase + ranger internal lag + command issue | final clearance **−3 … +61 mm** (span **63 mm**) — **CONTACT at the low end** | T1 | **3** |
| 4 | `c_offset_A` (mm) | 0 … 120 | ranger may be flush with the front face or set back behind a bumper/frame | final clearance **−0 … +60 mm** (span **60 mm**) — **CONTACT at the low end** | **T0** | **4** |
| 5 | `c_offset_B` (mm) | 0 … 120 | as A; the two need not share a longitudinal station | final clearance −0 … +60 mm (span 60 mm) — **CONTACT at the low end** | **T0** | **5** |
| 6 | `alpha_scale` (–) | 0.93 … 1.07 | time-of-flight scale; speed of sound varies with temperature | final clearance +24 … +37 mm (span 14 mm) | T1 | 6 |
| 7 | `v_max_ground` (mm/s) | 250 … 800 | rated motor speed × `k_travel`, plus battery spread | final clearance +30 … +30 mm (span **0 mm**) — *see §0.2* | T1 | 7 |
| 8 | `sigma_u` (mm) | 1 … 10 | 1 mm reporting quantisation up to multi-mm echo jitter | σ_gap 14.5 → 17.6 mm; required 3σ margin 44 → 53 mm | T1 | 8 |
| 9 | `theta_yaw_deg` (°) | 0 … 8 | open-loop drift over 1 m if the drive pair mismatches | σ_gap 14.8 → 17.4 mm; required 3σ margin 45 → 52 mm | **T0** | 9 |
| 10 | `T_refresh` (s) | 0.010 … 0.050 | LEGO UART sensor refresh 20–100 Hz | σ_gap 14.5 → 16.5 mm; required 3σ margin 43 → 49 mm | T2 | 10 |
| 11 | `dt_loop` (s) | 0.005 … 0.025 | MicroPython loop with four device reads | σ_gap 14.7 → 15.7 mm; required 3σ margin 44 → 47 mm | T1 | 11 |
| 12 | `w_half` (mm) | 50 … 80 | SPIKE chassis half-width | σ_gap 14.9 → 15.1 mm; margin unchanged | T1 | 12 |
| 13 | `r_min_valid` (mm) | 20 … 90 | ultrasonic ring-down / dead zone | no effect on the mean; **gates channel validity exactly where the rover is most committed** | T1 | 13 |

### 0.1 What the table justifies

1. **Four parameters can each, alone, drive the rover into the wall** (`a_brake`, `t_response`, `c_offset_A/B`). All four must be bound before any run at the operating point. They are bound in **C1**.
2. **Two of them sit at tier T0** — `c_offset_A/B`. Highest leverage *and* least known. Characterise first (tenet B2, trusted-reference-first).
3. **`k_travel` ranks 2nd, but its listed span is deliberately pessimistic.** The sweep treats parameters as independent; in reality `k_travel`, `t_response` and `a_brake` are co-fitted from one C1 dataset against one ranger baseline, so a pure scale error in `k_travel` propagates consistently through all three and largely cancels. It is ranked high anyway because *ranking is cheap and being wrong is not*; the C1 run binds it as a by-product of the same regression.
4. **`sigma_u`, `theta_yaw_deg`, `T_refresh`, `dt_loop` do not move the mean — they set the margin,** and therefore the objective. Because SYS-1 makes the achievable gap exactly 3σ_gap, *every millimetre of σ is three millimetres of score.* These are cheap to bind (they fall out of the same C1 run) and there is no reason not to.
5. **`r_min_valid` never moves the mean but can invalidate the primary channel at the stop.** It is bound by the C1 creep sweep, which walks the ranger through its own near field to contact.

### 0.2 Why the trigger law is speed-adaptive

Row 7 shows **zero** sensitivity to the achievable speed. That is a design result, not luck. With a fixed distance threshold the same sweep gives:

| True steady speed (mm/s) | Adaptive law | Fixed threshold |
|---|---|---|
| 250 | 30.0 mm | 70.2 mm |
| 350 | 30.0 mm | 53.7 mm |
| 470 | 30.0 mm | 30.0 mm |
| 600 | 30.0 mm | **−0.3 mm (contact)** |
| 800 | 30.0 mm | **−56.3 mm (contact)** |

Battery voltage, temperature and floor friction all move the achievable speed between the five power-cycled operation runs, and STK-4 forbids buying that back with speed. Recomputing `StoppingDistance` from the **live measured** speed every control cycle converts a run-to-run hazard into a null. This is the single most valuable design decision in the plan and it costs nothing.

### 0.3 Where the costed operator measurement earns its price

The flight law fires at `u_thr = c + target + v·t_response + v²/(2a)`. Everything except `target` enters the realised clearance **only** through the lump

> **Q(v) = c + v·t_response + v²/(2a)**  (nominal ≈ 129 mm, ranger units)

so the top four rows of the table are four ways of being wrong about **one** number. And that one number is the one thing no onboard channel can settle: every onboard estimate of `c` is derived from odometry that is itself scaled against the ranger, so the pair is self-referential — internally consistent and jointly wrong is a reachable state. **Nothing on the rover observes the rover's own foremost point.**

One external measurement of the final clearance after a full-speed stop determines Q exactly:

> **Q = u_thr(logged) − g(measured)**, hence σ_Q = σ_measurement ≈ 2 mm

collapsing four T0/T1 parameters to a single T4-anchored quantity **at the operating point**, which is precisely the condition the source-of-truth rule requires. That is the one outside-input action this plan requests (§4).

---

## 1. Calibration input list

### 1.1 Model-completion parameters (needed to predict; no requirement names them)
`alpha_scale` (TBD-18) · `w_half` (TBD-19) · `sigma_c`, `sigma_t_response`, `sigma_a` (the 1σ's feeding `sigmaGap`) · `yaw_sign` and the port map (TBD-13/14) · the ranger refresh/near-field structure feeding `sigma_u`.

### 1.2 Requirement-TBD register
TBD-01 … TBD-19, as tabulated in RS-WALLSTOP-001 §8. Every entry is bound by C1 except **TBD-12** (analysis only) and **TBD-17** (the operator measurement).

### 1.3 Deliberately left free until GATE B
`target_gap`. It is *computed*, not chosen: `target_gap = kSigma · sigmaGap` at the values C1 binds. Setting it now would be eyeballing a constant (tenet A3).

---

## 2. Characterisation method

### 2.1 Channel catalog and cross-sourcing

Every channel the platform can produce, traced to the quantity it serves. **A channel serving no needed quantity drops out** — same rule as effectors.

| Quantity | Channel | Directness | Confidence | Bound in | Notes |
|---|---|---|---|---|---|
| Clearance to wall | ranger A `distance()` | direct | high (in range) | C1 | bounded below by `r_min_valid` |
| | ranger B `distance()` | direct | high (in range) | C1 | independent echo path |
| | odometry from start clearance | indirect | medium | C1 | **covers the ranger's near-field gap** |
| | rear ranger | indirect | conditional | C1 | drops out if out of range (CMP-13) |
| Travelled distance | `motor.angle()` left | direct | high | C1 | slip-sensitive under hard braking |
| | `motor.angle()` right | direct | high | C1 | |
| | ranger decrement | indirect | high | C1 | slip-immune; the anchor for `k_travel` |
| Ground speed | `motor.speed()` | direct | high | C1 | filtered; feeds the live trigger |
| | Δodometry/Δt | direct | medium | C1 | noisier, unfiltered |
| | Δranger/Δt | indirect | medium | C1 | independent of the drivetrain entirely |
| Deceleration | odometry speed profile in the brake window | direct | high | C1 | |
| | IMU forward acceleration | direct | medium | C1 | axis identity unknown until C1 |
| At rest | odometry rate | direct | high | C1 | a locked wheel reads the same as a stopped rover |
| | IMU forward accel | direct | medium | C1 | breaks that ambiguity |
| | ranger stationarity | indirect | medium | C1 | |
| Heading | IMU yaw | direct | high | C1 | drift bounded by CMP-9 |
| | odometry differential L−R | indirect | medium | C1 | independent of the IMU |
| Ranger offset `c` | creep-to-contact zero | direct | medium | C1 | physical zero, but biased by contact-detection lag |
| | accel-phase lag-fit intercept | indirect | medium | C1 | independent estimator, different failure mode |
| | **operator measurement** | direct | **highest** | **C2** | **T4** |
| Ranger refresh | repeated-value run length in the 10 ms brake window | direct | high | C1 | |
| Loop period | hub-clock Δt statistics | direct | high | C1 | |
| Floor reflectance | colour sensor | — | — | — | **serves no needed quantity — DROPPED** |

**Cross-sourcing rule in force (tenet B1):** every characterisation run logs *every* catalogued channel bearing on the quantities that run touches, not only the one under test. Disagreement is the fault detector and is fault-agnostic — no channel is assumed correct in advance.

**Bounded-range hand-off (planned, not improvised):** the forward rangers are invalid below `r_min_valid`. Rather than extrapolate them past their limit, the odometry clearance estimate (anchored to the start clearance) covers that region, and the C1 creep sweep measures exactly where the hand-off must occur.

### 2.2 Source-of-truth hierarchy

> **T4 external ground truth (operator measurement) > T3 anchored or multi-point onboard calibration > T2 datasheet > T1 physics bound > T0 prior.**

Rules in force:
1. A lower tier **never** silently overwrites a value a higher tier has set. A later single sample disagreeing with a multi-point fit is a **discrepancy to diagnose** (low battery? range-dependence? glitch?), not grounds to re-fit the constant.
2. Every calibrated value is carried with its **evidence basis**: how many samples, against what reference, at what tier. The Calibration Report tabulates this.
3. **A sensor value that drives a scored quantity is a HYPOTHESIS until confirmed against an independent higher-tier source at the operating point.** The objective is the scored quantity here, so the final clearance is a hypothesis until TBD-17 is in hand.
4. On a disagreement judged significant, or on **any physically impossible reading**, escalate to better data rather than arbitrating between suspect channels.

**Physical-plausibility bounds** (a violation is an unconditional escalation, per ANOMALY DISPOSITION):

| Channel | Bound | Why a violation is impossible, not merely odd |
|---|---|---|
| ranger during approach | monotone non-increasing beyond noise | the rover only moves toward the wall |
| rest reading vs trigger reading | rest ≤ trigger | the rover cannot end farther out than where it braked |
| ranger reading | 0 ≤ u ≤ 2000 mm | outside the device's stated range |
| odometry travel vs ranger decrement | agree within 15 % over the approach | a larger gap means gross slip or a wrong `k_travel` |
| `a_brake` back-solved | 0 < a < 12 000 mm/s² | exceeds the tyre friction limit at μ≈1.2 |
| heading during a straight approach | \|Δ\| < 30° | the rover would be visibly turning |
| creep travel to contact | ≤ ranger reading at creep start + 60 mm | it cannot travel farther than it was away |
| loop period | 3 ms ≤ dt ≤ 60 ms | outside this, the trigger is not what was calibrated |

### 2.3 Test-like-you-fly run construction

**The characterisation program is a strict superset of the operation program.**

```
C1:  [port discovery] [polarity discovery]  CORE  [reverse]  CORE  [creep to contact]  [dump]
OP:  [port self-check]                      CORE                                       [dump]
                                            ^^^^
                                  byte-identical function
```

`CORE()` is the operation control loop: same 10 ms cadence, same channel reads in the same order, same validity gating, same speed-adaptive trigger expression, same brake call, same failsafes, same buffer writes. Only its **bound parameter values** differ between C1 (conservative priors) and operation (calibrated values) — which is the definition of a parameter rather than a structure.

**All characterisation logging is off the hot path.** During motion, samples go to five pre-allocated arrays; nothing is written to stdout until the wheels have stopped. Emitting on the hot path would change the loop period between characterisation and operation and silently invalidate every latency-dependent calibration — the exact failure this construction exists to prevent (FUN-8).

**Batching (tenet B3).** C1 carries: the port map, the polarity and yaw sign, two full-speed stops (giving a within-run repeatability sample for TBD-16 at no extra run cost), the approach regression, the brake-window profile, the loop-timing statistics, the static and in-motion noise samples, the rear-ranger disposition, and the creep sweep through the ranger's entire near field to a physical zero. **Every quantity later steps need is captured the first time**, so no quantity forces a dedicated repeat run.

---

## 3. Characterisation run design

### 3.1 C1 — calibration + unit verification (1 program run)

Full listing in **Appendix A**; it is syntax-checked and hot-path-checked. Phases:

| # | Phase | Duration | Binds |
|---|---|---|---|
| 0 | Port scan: try Motor → UltrasonicSensor → ColorSensor on each of A–F | ~1 s | TBD-13 |
| 1 | Static read ×15: all three rangers, IMU heading, IMU accel ×3 axes, colour | 0.5 s | TBD-07, TBD-15, forward-pair identity |
| 2 | Polarity probes: (+,+) pulse ⇒ translate or spin; then (+,−) if mirrored; then single-motor pulse for the yaw sign. Every probe is undone by an equal reverse pulse. | ~4 s | TBD-14 |
| 3 | **CORE #1** — full-speed approach, adaptive trigger at conservative priors, brake, 900 ms of rest logging, rest medians | ~3 s | TBD-03…06, TBD-08, TBD-10, TBD-11 |
| 4 | Reverse toward the start line under ranger + odometry limits | ~2 s | — |
| 5 | **CORE #2** — identical | ~3 s | **TBD-16** (within-run repeat) |
| 6 | Creep sweep: 200 mm/s to 220 mm reported, then 60 mm/s to contact (stall-detected), logging the entire near field | ~4 s | TBD-01, TBD-02, TBD-09, TBD-18 |
| 7 | Dump: scalars already emitted; series with a stride budget; sentinel | — | — |

**Forward-pair identification** is static (the two in-range rangers whose readings agree most closely are looking at the same wall) and is then cross-checked dynamically (they must both decrease as the rover advances, while the rear increases or stays out of range). Two independent discriminators, per B1.

**C1 design parameters — conservative priors, not guesses:**
`c_off` = 120 mm (prior **upper**) · `t_response` = 0.150 s (prior **upper**) · `a_brake` = 1000 mm/s² (prior **lower**) · `k_travel` = 0.47 mm/deg (prior nominal) · `target_gap` = **350 mm**.

**Pre-run safety analysis (Appendix B).** The realised clearance was minimised over the **full 64-corner prior box**:

| C1 stand-off | Worst-case clearance over the prior box | |
|---|---|---|
| 150 mm | −62 mm | CONTACT |
| 200 mm | −16 mm | CONTACT |
| 250 mm | +31 mm | OK |
| 300 mm | +78 mm | OK |
| **350 mm** | **+125 mm** | **OK — selected** |

Worst corner: `a_brake`=1000, `alpha`=1.07, `c`=120, `k_travel`=0.65, `t_response`=0.15, `v`=800. At the prior nominal, C1 is expected to stop ≈520 mm out, leaving a 0–520 mm creep sweep — which is a *feature*: it maps the ranger across the whole span that matters.

**Layered failsafes inside CORE** (identical in operation, different values): raw-ranger floor · odometry floor referenced to the measured start clearance · watchdog timer · a no-motion abort if 15 mm of travel is not seen within 400 ms (catches an inverted polarity before it matters).

### 3.2 C2 — verification run (1 program run)

The **locked candidate operation program**, unchanged, at the calibrated values, with `target_gap = 3·σ_gap` computed at GATE B. Its frozen prediction is the output of `wallstop_model.predict()` at the committed configuration, presented in the Verification Plan **before** the run.

### 3.3 Planned budget

| | Programs | Outside-input actions |
|---|---|---|
| C1 | 1 | 0 |
| C2 (verification) | 1 | **1** (TBD-17) |
| **Planned total** | **2** | **1** |
| Reserve if C2 falsifies the frozen prediction | +1 | +1 |

---

## 4. Outside-input request (costed) — exactly one

**Requested:** after the C2 verification run comes to rest, **one** measurement — the distance from the rover's foremost point to the wall, along the direction of travel, in millimetres.

**Requested at that point and not another** because §0.3 shows the objective's whole error budget collapses into one lump Q(v) that is only observable at the operating point, and the source-of-truth rule requires the scored quantity to be confirmed against a higher-tier source **at the operating point** before it may be closed. Taken earlier (e.g. a static tape measurement of the ranger offset) it would anchor `c` alone and leave `t_response` and `a_brake` unanchored; taken here it anchors all four at once.

**Batched cross-checks around the same request (tenet B4)** — all read from the *same* rest state, no additional operator action: ranger A and B rest medians, odometry-derived clearance, IMU at-rest confirmation, final heading, and the trigger-time values already logged. One measurement, six cross-checks.

**Not requested, deliberately:** the start-line distance (measured onboard at ~1000 mm where the ranger is most reliable, and cross-checked by odometry); wheel diameter (regressed from the approach); track width (only enters the small yaw-corner term).

---

## 5. Verification support

### 5.1 Unit verification of the CMP leaves by C1 (tenet C1: components before integration)

| Requirement | Evidence C1 produces | Method |
|---|---|---|
| CMP-1 / CMP-2 | creep-sweep fit residuals ⇒ offset ± uncertainty, per ranger | T |
| CMP-3 | repeated-value run length at 10 ms in the brake window | T |
| CMP-4 | near-field behaviour below `r_min_valid` + validity gate in the locked source | T + I |
| CMP-5 | odometry vs ranger regression slope, per motor | T |
| CMP-6 | steady-segment ground speed vs rated max read from `control.limits()` | T |
| CMP-7 | brake-window deceleration, two independent stops | T |
| CMP-8 | accel-phase lag fit + overshoot back-solve, two stops | T |
| CMP-9 | heading over the static segments and the straight approach | T |
| CMP-10 | loop Δt min/max/count per core | T |
| CMP-11 | port scan result + start-clearance plausibility gate exercised | T + I |
| CMP-12 | reduce-only trim arithmetic in the locked source | I |
| CMP-13 | rear-ranger static reading — **retain or drop on evidence** | T |
| CMP-14 | IMU accel at rest and at contact vs in motion | T |

### 5.2 Structure of the verification argument (predictions left open)

To be instantiated numerically in the Verification Plan at GATE B and closed in the Verification Report at GATE C:

```
STK-1  requirement → wall_stop.sysml requirement def
   ↓   satisfy (WallRoverAsBuilt)
SYS/FUN/CMP roll-up → evaluate() over bound values
   ↓
each CMP  → calibrated parameter (Calibration Report, with tier + sample count)
   ↓
predict() → final clearance, σ_gap, contact margin, per-requirement verdict   ← FROZEN before C2
   ↓
C2 run    → measured onboard clearance  +  operator ground truth (TBD-17)
   ↓
verdict per requirement, method + evidence + result                          ← GATE C
```

**Verification order (tenet A5).** CMP leaves first (C1). Then SYS-4/SYS-5/SYS-3 — independent of the trigger and confirmable from C1's own approach. Then SYS-2, which depends on all of FUN-1…4. **SYS-1 last**, because it is the only requirement that depends on both the calibrated σ's and the T4 anchor. The objective closes at GATE C on that anchored evidence, never on an unvalidated onboard channel — that is how a systematic bias would ship.

### 5.3 Falsification protocol

If C2 falsifies the frozen prediction: diagnose the responsible parameter from the cross-sourced channels, **re-derive — do not empirically tweak the program**, re-run the model, issue a **new** Verification Plan version (the prior stays frozen as the record of what was predicted), and take another verification run against it. The trail is recorded in the Verification Report.

---

## 6. Revision policy

This is a **PLAN**. It is re-issued as v1.1, v1.2 … if a characterisation run reveals something this version did not anticipate — a channel behaving outside its plausibility bound, an effector disposition that changes, or a parameter the sensitivity ranking mis-ordered. Prior versions are retained. Reports (Calibration, Verification, Final, Anomaly) are static once written.

---

## Appendix A — C1 program listing

The exact source to be flashed, offered for review **before** it costs a run. Syntax-checked; verified to contain no stdout write inside `CORE`; verified to construct each device exactly once (ports are claimed, not released).

*(Listing accompanies this plan as `c1_characterisation.py`.)*

Key excerpt — the trigger law, identical in the operation program:

```python
v_meas = 0.5 * (abs(mL.speed()) + abs(mR.speed())) * k_travel
thr    = target + t_resp * v_meas + v_meas * v_meas / (2.0 * a_brk)
if g_est <= thr:
    reason = 1                      # RelationTemplates::StoppingDistance, live
```

Key excerpt — reduce-only steering trim (CMP-12):

```python
red = KP_HEAD * hd * yaw_sign
cl  = VCMD - (red if red > 0 else 0.0)      # never exceeds VCMD
cr  = VCMD - (-red if red < 0 else 0.0)
```

## Appendix B — C1 worst-case corner analysis

`gen_c1_safety.py`, 2⁶ = 64 corners of the prior box on
{`c_offset`, `alpha_scale`, `k_travel`, `t_response`, `a_brake`, `v_max_ground`}:

```
C1 as designed (TARGET_C1 = 350 mm)
   worst-case final clearance    +124.6 mm
   best-case  final clearance   +1100.5 mm
   worst corner: a_brake=1000, alpha=1.07, c=120, k_travel=0.65,
                 t_response=0.15, v_max_ground=800
   VERDICT: NO CONTACT anywhere in the prior box
```

## Appendix C — structural check of the model pair

```
wall_stop.sysml structural check
  packages ...................... 3 (WallRunRequirements, WallStopDesign, WallStopStructure)
  requirement defs .............. 38
  decomposition edges ........... 39
  operand bindings resolved ..... 52
  reachable from STK-1 .......... 38 / 38
  edge-set == spec tree ......... YES
RESULT: all structural checks pass
```
