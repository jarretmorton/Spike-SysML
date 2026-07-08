# Calibration Plan — Wall-Approach Rover

**Document type:** PLAN (forward-looking; revised and re-issued if a characterization run reveals something this version did not anticipate — prior versions retained).
**Version:** v1 (pre-hardware, GATE A).
**Inputs:** Requirements Specification (source of truth), tailored SysML model (`wallrun_model.sysml`, structural gate PASS), executable analysis model (`wallrun_model.py`).
**Purpose:** rank the free/uncertain parameters by leverage, decide where the one scarce operator measurement is spent, and design the minimum set of characterization runs that bind every TBD and unit-verify every CMP requirement — before any flash.

---

## Section 0 — Sensitivity analysis (justifies everything below)

Method: `wallrun_model.py` sweeps each free/uncertain parameter over its assumed prior range (others held at nominal), with the trigger threshold `R_trigger` fixed at its nominal-solved value, and reports how far the **objective** (final gap, mm) and the **no-contact margin** (required `safetyMargin`, mm) move. Priors are stated so the ranges are themselves an input to review. This ranks *where to look*; it does **not** validate the model against reality — only the operating-point ground-truth anchor and the impossible-reading rule do that (§ source-of-truth).

### 0.1 Priors (assumed ranges and knowledge tiers)

Tier: 1 = well-known · 2 = modelled / onboard-calibratable · 3 = unknown-onboard · 4 = needs external ground truth.

| Parameter (Py var) | Nominal | Lo | Hi | Tier | Basis for the prior |
|---|---|---|---|---|---|
| `k_speed_m_rad` | 0.028 | 0.020 | 0.045 | 2 | wheel-Ø×gear guess incl. slip; wide until fit |
| `omega_max_rad_s` | 18.0 | 15.7 | 19.5 | 2 | SPIKE motor rated ~900–1117 deg/s |
| `t_response_s` | 0.030 | 0.010 | 0.060 | 2 | one loop period + actuation lag |
| `a_decel_mm_s2` | 4000 | 2000 | 8000 | 3 | active hold/brake on hub, unmeasured |
| `b_mm` (offset) | 0.0 | −20 | 30 | **4** | ultrasonic face/zero offset, **no onboard absolute channel** |
| `alpha` (scale) | 1.0 | 0.97 | 1.03 | 2 | ultrasonic assumed near-linear |
| `r_min_mm` | 45 | 30 | 60 | 2 | LEGO ultrasonic near-floor |
| `sigma_stop_mm` | 8 | 3 | 20 | 3 | run-to-run stop spread, unmeasured |
| `sigma_b_mm` | 5 | 2 | 10 | 3 | offset-anchor uncertainty |
| `sigma_pred_mm` | 5 | 2 | 15 | 3 | residual model error |
| `heading_drift_deg` | 2 | 0 | 10 | 3 | drivetrain asymmetry, unmeasured |

### 0.2 REQUIRED TABLE — leverage on objective and margin

*(output of `wallrun_model.py :: sensitivity_table()`)*

| Parameter | Assumed range | Δ objective (mm) | Δ margin (mm) | Tier | Priority |
|---|---|---:|---:|:--:|:--:|
| `k_speed_m_rad` | [0.020, 0.045] | −79.3 | +0.0 | 2 | **HIGH** |
| `b_mm` | [−20, 30] | −50.0 | +0.0 | **4** | **HIGH** |
| `a_decel_mm_s2` | [2000, 8000] | +47.6 | +0.0 | 3 | **HIGH** |
| `sigma_stop_mm` | [3, 20] | +0.0 | +40.6 | 3 | **HIGH** |
| `t_response_s` | [0.010, 0.060] | −25.2 | +0.0 | 2 | MEDIUM |
| `sigma_pred_mm` | [2, 15] | +0.0 | +24.2 | 3 | MEDIUM |
| `omega_max_rad_s` | [15.7, 19.5] | −16.3 | +0.0 | 2 | MEDIUM |
| `sigma_b_mm` | [2, 10] | +0.0 | +12.3 | 3 | LOW |
| `alpha` | [0.97, 1.03] | +0.0 | +0.0 | 2 | LOW |
| `r_min_mm` | [30, 60] | +0.0 | +0.0 | 2 | LOW |
| `heading_drift_deg` | [0, 10] | +0.0 | +0.0 | 3 | LOW |

### 0.3 The strategy the table dictates — measure D_stop directly at the operating point

The four highest objective-leverage parameters — `k_speed`, `a_decel`, `t_response`, `omega_max` — all act **through the predicted stopping distance** `D_stop = StoppingDistance(v_max, t_response, a_decel)`. Operation runs at a **single** speed (maximum), so the StoppingDistance template's own guidance applies: *at a single operating point, measure the stopping distance directly at that point — calibration point = operating point, zero extrapolation* — and back-solve `a_decel` only if a feasibility check needs it.

Pinning `D_stop` to its measured value and re-running the sweep (`04_collapse_demo.py`) shows the leverage collapse:

| Parameter | Raw Δobjective (mm) | With D_stop measured directly | Tier | Disposition |
|---|---:|---:|:--:|---|
| `k_speed_m_rad` | 79.3 | 0.0 (mm-model) → **~5 (real)** | 2 | HIGH→**MEDIUM**: retains role in the encoder-Δ→mm conversion of the D_stop channel |
| `a_decel_mm_s2` | 47.6 | **0.0** | 3 | **collapses** — fed only the D_stop prediction; log for feasibility/CMP only |
| `t_response_s` | 25.2 | **0.0** | 2 | **collapses** — folded into the measured D_stop; log for CMP-5 |
| `omega_max_rad_s` | 16.3 | **0.0** | 2 | **collapses** — folded into the measured D_stop; log for CMP-1 |
| `b_mm` | 50.0 | **50.0** | **4** | **unchanged, unity** — no onboard absolute channel |
| `sigma_stop_mm` | 0.0 (obj) | sets **+40.6 margin** | 3 | sizes the no-contact floor |

So the plan is:
1. **Measure `D_stop` directly at the operating point** (encoder Δ from trigger-report to rest × `k_speed`). This single measurement replaces the entire top of the raw table. `a_decel`, `t_response`, `omega_max` are still **logged** every run (feasibility cross-check and CMP-1/CMP-5 unit verification) but no longer drive the gap.
2. **Spend the one costed operator measurement on `b`** (sensor offset): unity leverage, tier 4, no onboard absolute channel — exactly where external ground truth earns its price. Taken at a **reliable mid-range** rest position (not at the tiny final gap), so `b` enters the prediction where the sensor is trustworthy.
3. **Characterize `sigma_stop`** (run-to-run stopping spread) from repeated runs — it carries zero objective leverage but is the dominant term in the no-contact margin (`safetyMargin = k_margin · RSS(sigma_pred, sigma_b, sigma_stop)`, tenet A6).
4. **`k_speed`** (now medium): characterize onboard by multi-segment Δreported-distance / Δencoder-angle (the offset `b` cancels in the difference). It converts both the cruise speed and the D_stop channel.
5. **`alpha`, `r_min`, `heading_drift`** (low): quick onboard checks, one run, no dedicated runs or measurements.

**Transfer-validity note (load-bearing).** `D_stop` is characterized at a *conservative* trigger during C1/C2 but must equal `D_stop` at the *operating* trigger. Both triggers sit ≥ ~79 mm from the wall with a ~1000 mm start, so the rover reaches full cruise long before either. C1 telemetry (speed vs. distance) is checked to confirm the cruise speed is flat before the trigger; if so, the braking phase — hence `D_stop` — is identical at both triggers. This is why the conservative-trigger measurement transfers to the operating point with no re-anchor.

---

## 1. Calibration input list

Two parts: (a) model-completion parameters the model needs but no requirement names, and (b) the requirement-TBD register (spec §5). Each is bound by a specific activity below.

**(a) Model-completion parameters**

| Parameter | Role | Bound by | Tier |
|---|---|---|---|
| `a_decel_mm_s2` | feasibility back-solve only (not on objective path once D_stop measured) | back-solved from D_stop at C1 if needed | 3 |
| `alpha` | sensor scale (assumed ≈1) | C1 multi-segment slope check | 2 |
| `sigma_pred_mm` | prediction-error contributor to margin | residual of model vs C1/C2 D_stop + V1 | 3 |
| `sigma_b_mm` | offset-anchor uncertainty contributor to margin | operator-measurement repeatability / read resolution | 3 |
| `k_margin` | coverage factor on the RSS margin | design choice = 3 (see §4.4) | 1 |

**(b) Requirement-TBD register** — reproduced from spec §5, with the binding activity made concrete:

| TBD | Quantity | Requirement | Binding activity | Tier |
|---|---|---|---|:--:|
| TBD-1 | `omega_max` | CMP-1 | C1 steady-state encoder rate during cruise | 2 |
| TBD-2 | `b` sensor offset | CMP-3 | C1 rest + **operator measurement #1** (true dist at reliable range) | **4** |
| TBD-2b | `alpha` sensor scale | CMP-3 | C1 multi-segment Δreport/Δencoder slope | 2 |
| TBD-3 | `r_min` | CMP-4 | C1 near-wall reading curve (both fwd sensors) | 2 |
| TBD-4 | `t_response`/`tChainBound` | CMP-5 | C1 loop period + actuation lag (hub clock) | 2 |
| TBD-5 | `k_speed` | CMP-7 | C1 multi-segment Δreport/Δencoder (offset cancels) | 2 |
| TBD-6 | `D_stop` | FUN-4 | C1 + C2 encoder Δ trigger→rest (**direct at operating point**) | 3 |
| TBD-7 | `sigma_stop` | FUN-4 / SYS-3b | spread across C1, C2 + within-run jitter floor | 3 |
| TBD-8 | `heading_drift` | CMP-6 | C1 IMU heading trace (+ encoder differential) | 3 |
| TBD-9 | `safetyMargin` | SYS-3b | computed once σ's bound: `k_margin·RSS` | derived |
| TBD-10 | `R_trigger`,`g_target` | SYS-1/FUN-2 | set from model after TBD-2/5/6/7/9 | design |
| TBD-11 | `contactFloor`=0; `restSpeedTol` | SYS-1/SYS-4 | fixed / from encoder noise floor at C1 | 1 |

---

## 2. Characterization-run design

### 2.1 Channel catalog & cross-sourcing

For every quantity, all independent onboard channels that observe it (derived from the kept-effector inventory), ranked by directness/confidence, with the run that binds it. A channel serving no needed quantity drops out (absence by traceability). **Every run logs every channel bearing on the quantities it touches** — disagreement is the fault-agnostic detector; never assume which channel is wrong.

| Quantity | Channel (ranked) | Conf. | Binding run |
|---|---|:--:|:--:|
| `k_speed` (encoder→mm) | ①Δreported-fwd-dist / Δencoder-angle, mid-range (b cancels) · ②nominal wheel-Ø×gear (sanity bound only) | ①hi ②lo | C1 |
| `b` (sensor offset) | ①**operator true-dist at rest** (tier 4) · ②none onboard (no absolute ref) | ①highest | C1 + meas #1 |
| `omega_max` | ①steady-state encoder rate in cruise · ②commanded-vs-achieved | ①hi | C1 |
| `v_max` (=ω·k) | ①ω_max×k_speed · ②Δreport/Δt in cruise · ③IMU fwd-accel integral | ①hi ②med ③lo | C1 |
| `D_stop` (trigger→rest) | ①**encoder Δangle×k_speed** (range-independent) · ②sensor report-drop R_trig−rest_report (valid iff rest≥r_min) · ③IMU fwd-accel double-integral over braking | ①hi ②med ③lo | C1, C2 |
| `sigma_stop` | ①spread of ① across C1,C2 · ②within-run encoder jitter (floor) | ①med ②lo | C1, C2 |
| `r_min` | ①near-wall report curve, sensor #1 · ②sensor #2 agreement near range | ①med ②med | C1 |
| `t_response` | ①consecutive telemetry Δt (hub clock) · ②command→speed-drop onset in encoder rate | ①hi ②med | C1 |
| `heading_drift` | ①IMU heading trace · ②left/right encoder-angle differential | ①hi ②med | C1 |
| `alpha` | ①multi-segment Δreport/Δencoder slope | ①med | C1 |
| `rest_speed` (SYS-4) | ①post-brake encoder rate · ②IMU settling | ①hi ②med | C1, C2 |

Dropped channels (absence by traceability): rear ultrasonic (no rearward quantity), downward reflectance (no line/marking), IMU lateral/vertical axes beyond forward-accel + yaw.

### 2.2 Source-of-truth hierarchy (stated up front)

**Tier 4 (highest): external operator ground truth** — the `b` anchor at the C1 rest, and the objective gap at V1. **Tier 2–3 (middle): anchored / multi-point onboard calibration** — `k_speed` multi-segment, `omega_max` steady-state, `D_stop` encoder Δ, latency from hub-clock timestamps. **Tier 1 (lowest): a single onboard sample** — one raw reading, a nominal geometry constant.

Rules:
- A lower tier **never silently overwrites** a higher-tier value. A later sample disagreeing with a higher-confidence value is a **discrepancy to diagnose** (low battery? range-dependence? glitch?), not grounds to re-fit.
- A sensor value driving a **scored** quantity — the objective, via `b` and `D_stop` — is a **HYPOTHESIS until confirmed against a higher-tier source at the operating point** (that confirmation is the V1 operator measurement). This is exactly how the objective is closed at GATE C, and why it is never closed on an unvalidated sensor.
- **Impossible readings escalate unconditionally** (physical-plausibility bounds, §2.5): rest report > trigger report, negative distance, `D_stop` < 0, rest speed increasing. These falsify a load-bearing assumption; the model does not get to adjudicate its own falsification.

### 2.3 Test-like-you-fly run construction

The characterization program is a **strict superset of the operation program**: identical port/direction detection, identical acceleration-to-max, identical paced control loop, identical trigger *mechanism* (`break when primary_forward ≤ R_trigger`), identical `hold()`-both-motors stop, identical `try/finally` guaranteeing motors stop + sentinel. The **only** differences:
- the trigger **threshold value** (the one calibrated parameter): conservative in C1/C2, the computed operating value in V1 and in operation — the mechanism is unchanged, and V1 exercises the exact operating value so what is verified transfers with no re-anchor;
- **extra characterization logging** written to a **pre-allocated buffer and dumped after the motors stop**, never on the hot path — so hot-path timing (hence `t_response` and `D_stop`) matches operation exactly.

Port/direction **detection is baked into the locked program** (deterministic, runs identically every run; 0 extra runs): probe each port once in order UltrasonicSensor→Motor→ColorSensor keeping the first successful construction (a failed wrong-device construction does not claim the port; avoids EBUSY double-claim). Forward vs. rear sensors are classified by which readings **decrease** on a small forward nudge; the forward-motor sign convention is set from the same nudge. Contingency (this is a plan): if detection proves flaky at C1, hard-code the map discovered at C1 into the locked program.

### 2.4 D_stop channel definition (the objective-critical measurement)

At the telemetry instant the primary forward reading first satisfies `≤ R_trigger` (the trigger-report instant): latch `encoder_angle_trigger`, `heading_trigger`, hub-clock `t_trigger`, and both forward reports. Command `hold()` on both motors. At rest: latch `encoder_angle_rest`, both forward reports, rest speed. Then
`D_stop = (encoder_angle_rest − encoder_angle_trigger) × k_speed` (averaged over the two drive motors). This captures latency-coast + braking travel — exactly the trigger-to-rest distance the geometry needs. Cross-checks logged: report-drop `R_trigger − rest_report` (only if `rest_report ≥ r_min`), and IMU forward-accel double-integral over `[t_trigger, t_rest]`. Per-run **onboard gap estimate** (FUN-6): `gap_est = (R_trigger − b) − D_stop_thisrun`.

### 2.5 Physical-plausibility bounds (auto-surface anomalies)

Every logged channel carries a bound; a violation is an unconditional escalate (Anomaly Report):
`0 ≤ forward_report ≤ ~2000 mm`; `rest_report ≤ R_trigger` (rest cannot be farther than trigger); `D_stop ≥ 0` and `D_stop ≤ ~300 mm` (else runaway); `0 ≤ omega_achieved ≤ ~20 rad/s`; `|heading_drift| ≤ ~30°`; rest speed must be **decreasing** into rest. Surprising-but-possible deviations are filtered by the §0 ranking (chase only if high-leverage); impossible ones escalate regardless.

### 2.6 Run schedule and operator-measurement requests

| # | Run | Trigger | Binds / verifies | Operator input |
|:--:|---|---|---|---|
| 1 | **C1** | conservative (~180 mm reported, ≥ r_min, comfortable reliable-range rest) | omega_max, k_speed, r_min, t_response, alpha, heading_drift, D_stop #1, rest_speed, all cross-checks; CMP-1/3/4/5/6/7 unit data | **Measurement #1:** true distance rover-front→wall at the C1 rest (anchors `b`, tier 4) |
| 2 | **C2** | conservative (identical program) | D_stop #2 → `sigma_stop` (spread) + repeatability of rest_speed/heading | none |
| — | *compute operating `R_trigger` = b + D_stop + g_target; **freeze Verification Plan (GATE B)*** | | | |
| 3 | **V1** | **operating** (~79 mm reported, computed) | tests the frozen prediction; confirms D_stop at the true operating point | **Measurement #2:** true gap rover-front→wall at V1 rest (**objective validation at operating point**, tier 4; GATE C) |
| — | *operation (5 scored runs), locked operating program* | operating | scored demonstration + repeatability | close-out only (post-hoc) |

**Totals, Phase 1: 3 program runs (C1, C2, V1) + 2 operator measurements.** Then 5 operation runs.

Batching (tenet B3/B4): C1 carries the maximum cross-checks around measurement #1 (every onboard channel logged that run); C2 adds only the second D_stop sample the σ needs; V1 doubles as verification run and objective-validation anchor.

**Leaner alternative (considered, not chosen):** drop C2 → 2 program runs + 2 measurements, sizing `sigma_stop` from within-run jitter × a factor instead of a 2-sample spread. Rejected for v1: the no-contact constraint is hard, `sigma_stop` is the dominant margin term (§0.2), and a single sample cannot separate run-to-run spread from within-run jitter. Re-plan to this option only if C1 shows `sigma_stop` is negligibly small relative to the margin already.

---

## 3. Outside-input requests (the costed measurements)

Exactly two, both tier-4 ground truth, placed by the §0 ranking:

1. **Measurement #1 — `b` anchor (at C1).** "With the rover stopped at its C1 rest, measure the true distance from the front face of the rover (the sensor face) to the wall, in mm." Anchors the sensor offset `b` at a reliable range. Front-loaded because `b` is unity-leverage and has no onboard absolute channel.
2. **Measurement #2 — objective validation (at V1).** "With the rover stopped at its V1 rest, measure the true gap from the front of the rover to the wall, in mm." Confirms the scored objective against ground truth **at the operating point** and tests the frozen prediction. This is the measurement that lets GATE C close the objective on validated data, not an unvalidated sensor.

Each is one distinct measurement (counts as such even though maximum cross-checks are batched around it onboard). No other operator input is requested in Phase 1; none during the 5 operation runs.

---

## 4. Verification support

How the calibration activities support verification, and the structure of the eventual argument (predictions left open, to be frozen at GATE B).

### 4.1 CMP unit verification (produced in the Calibration Report, GATE B)

| CMP | Unit-verification method | Evidence from | Bound/target |
|---|---|---|---|
| CMP-1 MotorAtMax | test | C1 steady-state encoder rate | `omega_achieved ≥ omega_max` |
| CMP-2 MotorToRest | test | C1/C2 post-brake encoder rate | `motorRestSpeed ≤ restSpeedTol` |
| CMP-3 SensorResidual | test/analysis | C1 report vs operator-anchored true + 2-sensor agreement | `|resid| ≤ residTol` after offset |
| CMP-4 SensorMinRange | test + inspection | C1 near-wall curve → r_min; operating R_trigger | `R_trigger ≥ r_min` |
| CMP-5 LatencyChain | analysis | C1 loop Δt + actuation lag (hub clock) | `t_response ≤ tChainBound` |
| CMP-6 HeadingBounded | test | C1 heading trace + encoder differential | `heading_drift ≤ headingTol` |
| CMP-7 GroundConstant | test/analysis | C1 multi-segment fit residual | `|k_resid| ≤ kTol` |

Unit verification **gates** the integrated test (tenet C1): V1 is not run until the CMP leaves it depends on are verified at GATE B.

### 4.2 Verification-argument structure (the roll-up, predictions open)

The formal satisfy/require roll-up (`WallRunNeed`) is realized in the SysML model and computed by `wallrun_model.py :: evaluate()`. The two views are certified to evaluate the **same 12 constraint-bearing requirements** (structural check #4, PASS). At GATE B the model is evaluated at the committed configuration → the **frozen prediction**: each requirement's predicted verdict + the `ROLLUP`. Shape (verdicts open until GATE B):

```
ROLLUP  WallRunNeed  [open]
├─ SYS-1 NoContact        finalClearance ≥ contactFloor      [open]
│  ├─ SYS-3b MinGapMargin finalClearance ≥ safetyMargin      [open]
│  │  ├─ FUN-4 (D_stop, sigmaStop characterized) → CMP-7     [CMP: GATE B]
│  │  └─ FUN-6 (onboard gap estimate)                        [—]
│  ├─ FUN-1 SenseDistance → CMP-3, CMP-4                     [CMP: GATE B]
│  └─ FUN-2 DecideStop    → CMP-5                            [CMP: GATE B]
├─ SYS-2 MaxSpeed         cruiseSpeed ≥ maxGroundSpeed  → CMP-1  [open]
├─ SYS-3 MinGap (objective, graded)  validated at V1 operating point [open]
├─ SYS-4 FullStop         finalSpeed ≤ restSpeedTol     → CMP-2  [open]
└─ SYS-5 StraightTravel   headingDrift ≤ headingTol     → CMP-5/6 [open]
```

### 4.3 Verification sequence (tenet A5, dependency order)

CMP leaves (unit-verified at GATE B from C1/C2) → SYS integrative claims that compose them: `D_stop`/clearance (SYS-1, SYS-3b) and straightness (SYS-5) tested at **V1** → objective (SYS-3) validated at the **V1 operating point**. No requirement needs the scored operation runs; the entire verification argument closes at **GATE C**. Operation is a scored demonstration and a repeatability sample only.

### 4.4 Margin and the falsification path

`safetyMargin = k_margin · RSS(sigma_pred, sigma_b, sigma_stop)` (tenet A6), `k_margin = 3` (per-run P(contact) ≈ 0.13 % Gaussian; ≈ 0.67 % over 5 runs). The margin covers **random run-to-run** spread only. A **systematic** offset in `b` or `D_stop` is caught by the V1 operating-point validation (measurement #2): if V1's true gap departs from the frozen prediction beyond the margin, **diagnose the responsible parameter, re-derive `R_trigger`, issue a new Verification Plan version, and re-run V1** — never tweak the program empirically, and the prior frozen prediction stays as the record. This is the only mechanism by which the operating trigger moves before the 5 runs are locked.

---

## 5. What this plan commits to before any flash

- The one dominant objective-critical quantity (`D_stop`) is **measured directly at the operating point**, collapsing the top of the sensitivity table (§0.3, demonstrated in `04_collapse_demo.py`).
- The single scarce measurement is **front-loaded on `b`** (unity leverage, tier 4, no onboard channel); a second validates the objective at the operating point.
- **3 program runs, 2 operator measurements** in Phase 1 (C1, C2, V1), with a documented leaner fallback.
- Every TBD is bound to a run; every CMP has a unit-verification method; the roll-up structure is fixed with predictions left open to be **frozen at GATE B**.

*Revision triggers for this plan:* C1 shows cruise not reached before the trigger (transfer-validity breaks) · `r_min` forces `R_trigger` near the sensor floor (CMP-4 tight) · `sigma_stop` negligible (drop C2) · detection flaky (hard-code map) · any impossible reading (Anomaly Report).
