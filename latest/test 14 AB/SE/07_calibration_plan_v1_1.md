# CALIBRATION PLAN — Wall-Approach Rover
**Document:** `07_calibration_plan_v1.md` · **Type: PLAN** (forward-looking; revised and
re-issued if a characterization run reveals something this version did not anticipate)
**Version:** 1.1 (see Addendum A) · **Gate:** GATE A — presented for review **before any hardware run**

**Companion artefacts:** `01_requirements_spec.md` (source of truth) ·
`02_wall_stop_model.sysml` (formal argument) · `wall_stop_model.py` (executable model) ·
`03_model_checks.py` (structural gate checks) · `04_run1_program.py` (the RUN-1 flight
program, listed for inspection) · `05_sim_harness.py`, `06_design_loop_check.py`
(free-analysis harnesses)

**Nothing in this plan has touched the rover.** All numbers below are model output at
stated priors, or results of host-side simulation. Every parameter remains **unbound**;
`EVALUATE` currently returns `INDETERMINATE` and the top-level satisfy roll-up returns
`INDETERMINATE`, which is the correct state of the argument at this gate.

---

## 0. SENSITIVITY ANALYSIS

### 0.1 Method and the priors it rests on

The executable model is swept over each free parameter's assumed range with all others
at their prior mid. **The prior ranges are an input to your review — if you think one is
wrong, that changes the plan below.** Three sensitivities are reported because they
answer different questions:

| column | question | governs |
|---|---|---|
| **d objective** | with the design **re-solved** at each value, how much does the achievable gap (`k_σ·σ_g`) move? | what to calibrate to get **closer** |
| **d nominal margin** | with `R_trig` **frozen** at the baseline design, how much does the **realised** gap move? | what must be **accurate** so as not to hit the wall |
| **d degraded margin** | the same, for the SYS-7 backstop path | so backstop parameters are ranked, not invisible |

A parameter that moves the *nominal margin* 1:1 is a **contact risk**, not a performance
nuisance: an error in it lands directly and entirely on the scored gap and shifts all
five operation runs together. A fourth, non-numeric signal is also captured — whether any
requirement **verdict flips** across the prior range. A parameter can have small numeric
leverage and still decide a pass/fail; those are promoted rather than filed under "prior
is adequate".

Knowledge tier notation: **T0** prior only · **T1** single onboard sample ·
**T2** anchored or multi-point onboard calibration · **T3** external ground truth.
Every parameter is T0 today.

### 0.2 The required table

| parameter (SysML attribute) | assumed range | d objective (mm) | d nominal margin (mm) | d degraded margin (mm) | knowledge tier | priority |
|---|---|---:|---:|---:|---|---|
| `b_offset_mm`<br>`WallRover.rangeOffset` | -40 .. 80 mm | +0.0 | **-120.0** | -120.0 | T0 prior only | **P1** — bind before any fast run (decides CMP-9) |
| `a_decel_mm_s2`<br>`WallRover.decel` | 1000 .. 6000 mm/s² | -28.9 | **+111.6** | +111.6 | T0 prior only | **P1** — bind before any fast run (decides SYS-3, SYS-5) |
| `k_mm_per_deg`<br>`WallRover.speedScale` | 0.35 .. 0.8 mm/deg | +17.8 | **-80.5** | -64.3 | T0 prior only | **P1** — bind before any fast run (decides SYS-3) |
| `omega_max_deg_s`<br>`WallRover.maxWheelSpeed` | 700 .. 1100 deg/s | +10.1 | **-45.7** | -36.5 | T0 prior only | **P1** — bind before any fast run (decides SYS-3) |
| `delta_bs_mm`<br>`WallRover.backstopAllowance` | 5 .. 40 mm | +0.0 | +0.0 | **-35.0** | T0 prior only | **P1** — bind before any fast run |
| `tau_sensor_s`<br>`WallRover.rangerLag` | 0.005 .. 0.06 s | +6.0 | **-28.5** | +0.0 | T0 prior only | **P1** — bind before any fast run (decides SYS-3) |
| `e_odo_mm`<br>`WallRover.odometryError` | 2 .. 20 mm | +0.0 | +0.0 | -18.0 | T0 prior only | P2 — bind in RUN-1 (decides CMP-4) |
| `t_chain_s`<br>`WallRover.latency.tChain` | 0.002 .. 0.02 s | +2.0 | -9.3 | -9.3 | T0 prior only | P2 — bind in RUN-1 |
| `t_loop_s`<br>`WallRover.loopPeriod` | 0.005 .. 0.025 s | +1.9 | -5.2 | +0.0 | T0 prior only | P2 — bind in RUN-1 |
| `rel_sigma_S`<br>`WallRover.stopRepeatability` | 0.03 .. 0.15 | +16.4 | +0.0 | +0.0 | T0 prior only | P2 — bind in RUN-1 (decides SYS-3) |
| `u_b_mm`<br>`WallRover.offsetUncertainty` | 1 .. 10 mm | +13.4 | +0.0 | +0.0 | T0 prior only | P2 — bind in RUN-1 (decides SYS-3) |
| `k_sigma`<br>`WallRover.marginMultiplier` | 2.5 .. 3.5 | +10.4 | +0.0 | +0.0 | T0 prior only | P2 — design decision (decides SYS-3) |
| `sigma_n_mm`<br>`WallRover.rangerNoise` | 1 .. 8 mm | +8.7 | +0.0 | +0.0 | T0 prior only | P2 — bind in RUN-1 (decides FUN-2, SYS-3) |
| `n_S_samples`<br>`WallRover.stopSampleCount` | 1 .. 3 | -2.8 | +0.0 | +0.0 | T0 prior only | P3 — plan quantity |
| `sigma_theta_deg`<br>`WallRover.headingSpread` | 0 .. 3 deg | +2.2 | +0.0 | +0.0 | T0 prior only | P3 — log in RUN-1 |
| `sigma_meas_mm`<br>`WallRover.measurementSigma` | 0.5 .. 3 mm | +1.3 | +0.0 | +0.0 | T0 prior only | P3 — declared with M1 |
| `c_yaw_mm_per_deg`<br>`WallRover.yawClearanceCoeff` | 1 .. 1.6 mm/deg | +0.5 | +0.0 | +0.0 | T0 prior only | P4 — prior is adequate |
| `sym_dev_deg_s`<br>`WallRover.symmetryDeviation` | 0 .. 60 deg/s | +0.0 | +0.0 | +0.0 | T0 prior only | P2 — bind in RUN-1 (decides CMP-3) |
| `T_refresh_s`<br>`WallRover.rangerRefresh` | 0.01 .. 0.1 s | +0.0 | +0.0 | +0.0 | T0 prior only | P4 — prior is adequate |
| `r_floor_mm`<br>`WallRover.validityFloor` | 20 .. 60 mm | +0.0 | +0.0 | +0.0 | T0 prior only | P2 — bind in RUN-1 (decides CMP-9) |
| `delta_AB_mm`<br>`WallRover.rangerPairOffset` | 0 .. 30 mm | +0.0 | +0.0 | +0.0 | T0 prior only | P4 — prior is adequate |
| `theta_dev_deg`<br>`WallRover.headingDeviation` | 0 .. 8 deg | +0.0 | +0.0 | +0.0 | T0 prior only | P2 — bind in RUN-1 (decides SYS-6) |
| `R0_mm`<br>`WallRover.startRange` | 950 .. 1050 mm | +0.0 | +0.0 | +0.0 | T0 prior only | P4 — prior is adequate |

### 0.3 What the table decides

1. **`b_offset_mm` is the single most dangerous parameter and the only one with no
   onboard observer.** Its prior spans 120 mm and lands 1:1 on the realised gap. No
   channel on the rover can see it without touching the wall. This is precisely the case
   the source-of-truth hierarchy reserves a costed operator measurement for — it is why
   **M1** exists and why it is spent early rather than late.
2. **`a_decel`, `k`, `omega_max`, `tau_sensor` are P1 but are all bound by RUN-1's own
   channels.** They are dangerous only while unknown; none needs operator input. That is
   the whole justification for a single, densely-instrumented characterization run.
3. **Two parameters (`rel_sigma_S`, `sigma_n`) dominate the *objective* while having zero
   effect on the *nominal margin*.** They set how close we can get, not whether we
   crash. They are the reason RUN-1 carries static dwells at two ranges.
4. **`c_yaw_mm_per_deg` is P4 — and that is a costed measurement avoided.** Rover width
   would take an operator action to measure; the sweep shows the objective moves 0.5 mm
   across the whole plausible range. The prior is kept, deliberately. This only holds
   while heading deviation stays small, which is why `theta_dev_deg` is promoted to P2 on
   its verdict flip (it decides SYS-6).
5. **`T_refresh_s` ranks P4 only because FUN-2 exists.** Without inter-sample
   extrapolation the crossing quantisation would be set by the refresh interval:

   | | crossing quantisation (1σ) | achievable gap |
   |---|---:|---:|
   | with FUN-2 | 2.24 mm | 31.1 mm |
   | without FUN-2 | 8.22 mm | 39.1 mm |

   That ~8 mm is the return on the function, computed rather than asserted.

> **A sensitivity sweep ranks where to look. It does not validate the model against
> reality.** Only the operating-point ground-truth anchor (M1/M2) and the
> impossible-reading rule do that. Nothing in §0 should be read as evidence that the
> model is correct — only as evidence about where being wrong would hurt.

### 0.4 Model state at this gate

Prior-mid working point (**for ranking only — not a calibrated model**):

| quantity | value | | quantity | value |
|---|---:|---|---|---:|
| cruise speed `v` | 517.5 mm/s | | σ loop quantisation | 2.24 mm |
| response time (pre-brake) | 43.5 ms | | σ stop repeatability | 5.47 mm |
| composite stop distance `S` | 60.8 mm | | σ ranger noise | 4.50 mm |
| time to rest | 191 ms | | σ calibrated offset | 5.77 mm |
| trigger threshold `R_trig` | 116.0 mm | | **σ_run (scatter)** | **7.68 mm** |
| required clearance `k_σ·σ_g` | 31.1 mm | | **σ_sys (common mode)** | **6.95 mm** |
| predicted gap (mean) | 31.3 mm | | **σ_g total** | **10.36 mm** |
| degraded-mode gap | 18.5 mm | | trigger reachability floor | 53.5 mm |
| expected rest reading | 51.3 mm (valid) | | admissible `v` (budget) | 2430 mm/s |

The uncertainty budget splits deliberately into two families, because they fail
differently. **σ_run** scatters the five operation runs about their own mean.
**σ_sys** shifts all five together — a calibration bias ships once and hits every run.
They are nearly equal at the prior working point, which says the plan must spend as much
care on *anchoring* `S` and `b` as on *repeating* them.

---

## 1. CALIBRATION INPUT LIST

### 1.1 Model-completion parameters (needed to predict; named by no requirement)

`tau_sensor_s`, `t_chain_s`, `t_loop_s`, `T_refresh_s`, `rel_sigma_S`, `n_S_samples`,
`u_b_mm`, `sigma_theta_deg`, `c_yaw_mm_per_deg`, `e_odo_mm`, `R0_mm`, `sigma_meas_mm`.

### 1.2 Requirement-TBD register

TBD-01 … TBD-29, reproduced in §7 of the requirements specification, each already bound
to an activity. **Closure status at this gate: 0 of 29 closed.** RUN-1 is designed to
close TBD-01…07, 09…12, 17, 18, 26, 27, 29 (17 items); M1 closes TBD-08, 16, 28;
TBD-13, 15 are set by analysis on RUN-1 data; TBD-14 is retained as a prior with a
consistency check; TBD-19 is retained as a prior by §0.3(4); TBD-20…25 are design
constants fixed here.

### 1.3 Design constants fixed at this gate (decisions, not measurements)

| constant | value | rationale |
|---|---:|---|
| `k_sigma` | 3.0 | one-sided ~99.9% on the low tail; the sweep shows ±0.5 costs ~10 mm of objective, so this is the main knob if you want a different risk posture |
| `contact_floor_mm` | 0.0 | zero gap **is** contact |
| `t_stop_max_s` | 0.5 | SYS-5 settle limit |
| `theta_max_deg` | 5.0 | at `c_yaw`≈1.3 mm/deg this caps yaw-induced corner loss at ~6.5 mm |
| `eps_est_mm` | 10.0 | SYS-8; close-out reconciliation is meaningless if looser |
| `g_goal_mm` | 30.0 | SYS-3 reporting benchmark only — **graded, never a gate** |

---

## 2. CHARACTERIZATION-RUN DESIGN

### 2.1 Channel catalog and cross-sourcing

Derived from the rover inventory, not from the obvious channel. Every run logs **every**
catalogued channel bearing on the quantities it touches; disagreement is the fault
detector and is fault-agnostic.

| quantity | rank 1 (most direct) | rank 2 | rank 3 | binding run | hand-off at range limits |
|---|---|---|---|---|---|
| distance to wall | ranger A | ranger B | odometry from `R0` | RUN-1 | rangers floor out below `r_floor`; **odometry covers the gap** — never extrapolate the ranger past its floor |
| travelled distance | odometry L | odometry R | ranger Δ | RUN-1 | ranger Δ invalid near the wall |
| ground speed | motor speed L | motor speed R | ranger slope | RUN-1 | — |
| heading | IMU heading | IMU yaw rate | differential odometry | RUN-1 (axis identity confirmed in Phase 0) | — |
| **composite stop `S`** | ranger `d_T − r_rest` | odometry `Δθ·k` | IMU `∫a dt` | RUN-1 | ranger channel is **slip-immune**; odometry is the **slip detector** |
| deceleration `a` | odometry differentiated | IMU forward axis | back-solved from `S` | RUN-1 | — |
| **range offset `b`** | *(no onboard channel)* | — | — | **M1** | — |

**Channels that drop out by traceability:** the rear ranger and the reflectance sensor
serve no quantity above. Both are nonetheless logged once in RUN-1 at zero marginal cost
(`rear_start/rest/creep`, `reflect_start/rest/creep`) so the drop-out is **evidenced, not
assumed** (Rule 7). The rear ranger is retained only if it shows a monotonic change
consistent with odometry — i.e. only if it turns out to observe travelled distance.

**A deliberate cross-source result already in hand from simulation:** `S_ranger` and
`S_odometry` differ by exactly the ranger lag term `v·τ`. Logging both therefore
separates transport lag from braking distance **within a single run**, with no second
speed and no extra program. The two-stage creep adds a low-speed stop point, giving a
second `(v, S)` pair — enough to check the `StoppingDistance` template's quadratic term
for curvature rather than folding it into the linear term, which is the failure mode the
template's own note warns about.

### 2.2 Source-of-truth hierarchy

> **T3 external ground truth (operator measurement) > T2 anchored or multi-point onboard
> calibration > T1 a single onboard sample.**

- A lower tier **never** silently overwrites a value a higher tier has set. A later
  sample disagreeing with a higher-confidence value is a **discrepancy to diagnose**
  (low battery? range dependence? glitch?), not grounds to re-fit the constant. This is
  enforced mechanically: `Param.bind()` raises `TierViolation` on a downgrade.
- Every bound value is carried with its evidence basis: sample count, reference, tier.
- **RULE.** A sensor value driving a scored quantity — the objective above all — is a
  **HYPOTHESIS until confirmed against an independent higher-tier source at the operating
  point.** `b_offset_mm` is exactly such a value, which is why M1 is taken at close
  range and M2 re-tests it at the operating point rather than treating M1 as final.
- On a disagreement I judge significant, or on **any physically impossible reading**,
  escalate to better data rather than arbitrating between suspect channels. Plausibility
  bounds are implemented onboard on every logged channel (`D_MIN`=20 mm, `D_MAX`=1990 mm,
  a wrong-way guard, and a staleness guard) so impossible readings surface automatically
  rather than being averaged in.

### 2.3 Test-like-you-fly run construction

`04_run1_program.py` is a **strict superset** of the operation program. The control loop,
trigger rule, stop maneuver and buffer skeleton are identical; characterization logic
runs either **before the motors are first commanded** or **after they have stopped**, and
no telemetry byte is written while the motors are commanded (FUN-10). The operation
program is derived from it by exactly three edits:

1. Phase 0 (discovery) → the constant device map RUN-1 yields, plus an assertion it still holds.
2. Phase E (two-stage creep) → deleted.
3. Five constants take calibrated values: `R_TRIG`, `K_MM_PER_DEG`, `V_NOM_MM_S`,
   `S_CAL_MM`, `FWD_AXIS`.

The travel and time backstops are **not** flashed constants: they are derived at runtime
from the rover's own static `R0` measurement, because travel-to-trigger is `(R0 − R_trig)`
in the *sensor* frame. Sizing them from an assumed start gap mis-sizes them by `b` — a
defect found in simulation (§5).

**RUN-1 phase structure**

| phase | content | in operation? |
|---|---|---|
| **0** | settle; port scan; identify the forward ranger pair by rest agreement; discover relative motor polarity and forward direction by probe-and-undo; identify the IMU yaw axis and the forward acceleration axis | RUN-1 only |
| **A** | 12 static samples per ranger → `R0`, per-ranger spread, pair offset; rear ranger; reflectance; derive backstop limits | **both** |
| **B** | **HOT PATH** — command both motors at the controller ceiling; per-loop fused range with plausibility filter, inter-sample extrapolation, odometric and time backstops, arming and wrong-way guards; trigger; plugging stop to rest | **both, identical** |
| **C** | 400 ms settle, then 16 dwell samples per ranger → `r_rest`, spread, pair offset | **both** |
| **D** | emit primary scalars **first** (truncation-tolerant order) | **both** |
| **E** | two-stage creep to a ~55 mm reading; dwell; close-range statistics; low-speed stop point | RUN-1 only |
| **F** | downsampled buffer dump (least critical, emitted last), then the sentinel | **both** |

**Why RUN-1's trigger is 600 mm.** The worst case in the prior box gives `S` = 457 mm.
A conservative threshold is not caution for its own sake — it is what makes the run
*safe while `S` is unknown*, and `S` is measured identically wherever the trigger sits,
because the stop dynamics do not depend on where it fires. The trigger reason is logged,
so a backstop-delivered stop still yields a valid `S`.

**RUN-1 risk posture, stated plainly.** `k` is unbound, so the odometric backstop cannot
yet be correctly sized. RUN-1 protection is carried instead by the conservative `R_TRIG`,
the **ranger-staleness guard** (250 ms, entirely `k`-free — if the ranger dies at the
start line the rover stops with ~370 mm to spare), the wrong-way guard, and the time
limit. SYS-7 is verified at the verification run, with `k` bound.

**Batching (tenet B3).** RUN-1 binds 17 TBDs, unit-verifies 11 CMP requirements, tests
the discovery logic, and produces the close-range pose that M1 anchors — in one program.
Everything a later step needs is captured the first time, so no quantity forces a repeat.

### 2.4 Anticipated re-plan triggers (stated now, so a surprise is not a rationalisation)

This plan will be **revised and re-issued** rather than patched if RUN-1 shows:

- heading deviation at trigger > 5° (SYS-6 fails) → re-plan with a heading-correction
  term whose gain is bound by RUN-1 data — **not** an eyeballed gain;
- odometry-vs-ranger disagreement during the stop > 15 mm → gross wheel slip under
  plugging; re-plan the stop maneuver to passive braking and re-derive;
- ranger noise spikes that would false-trigger the single-sample rule → re-plan the
  trigger with a two-of-two confirmation and re-derive the added latency into `S`;
- `r_floor` high enough that FUN-14's reachability floor exceeds the margin-driven
  threshold → the achievable gap is floor-limited, not margin-limited, and the objective
  must be re-derived;
- forward-pair disagreement > 30 mm (FUN-13) → the two rangers are not observing the same
  target; diagnose before trusting either.

---

## 3. OUTSIDE-INPUT REQUESTS (costed)

Two, both justified by §0.

| id | when | request | binds | why it cannot be avoided |
|---|---|---|---|---|
| **M1** | immediately after RUN-1, **before the rover is moved or power-cycled** | the shortest distance from any part of the rover to the wall, at its final resting pose (~55 mm reading) | TBD-08 `b_offset_mm`, TBD-16 `u_b_mm`, TBD-28 `sigma_meas_mm` | §0.3(1) — no onboard channel observes `b`, and it lands 1:1 on the scored gap. Taken at **close range** so the anchor sits at the operating point rather than being extrapolated to it. |
| **M2** | after the verification run | the same measurement, at the verification stop | validates the **frozen predicted gap** against ground truth at the operating point | GATE C closes the objective only on this evidence. M1 binds a parameter; M2 tests a prediction. They are not interchangeable. |

I will ask for exactly one number each time, with the measurand defined precisely
(**shortest distance from any part of the rover to the wall**) so that yaw is captured
rather than ambiguous. No other measurement is requested; per §0.3(4) rover width is
deliberately *not* measured because the sweep shows it does not matter.

---

## 4. VERIFICATION SUPPORT

### 4.1 How calibration supports unit verification (CMP level)

Every CMP requirement is unit-verified by RUN-1 data, before any integrated claim
(tenet C1). Ordering respects interdependence (A5): geometry and timing first, then the
quantities that depend on them, then the composite.

| order | CMP | verified from | depends on |
|---|---|---|---|
| 1 | CMP-11 loop period | hot-path timestamp deltas | — |
| 2 | CMP-6, CMP-7 ranger refresh | value-change timestamps | CMP-11 |
| 3 | CMP-8 fused noise | static dwells at ~1000 mm, ~520 mm, ~55 mm | CMP-6/7 |
| 4 | CMP-9 validity floor | creep stage 2 approach to 55 mm | CMP-8 |
| 5 | CMP-1, CMP-2 motor ceiling | cruise plateau, per motor | CMP-11 |
| 6 | CMP-3 symmetry | per-motor cruise speeds | CMP-1/2 |
| 7 | CMP-4 odometry scale | regression of fused range on motor angle over the whole approach | CMP-1/2, CMP-8 |
| 8 | CMP-5 deceleration floor | stop window, odometry differentiated, cross-checked against IMU | CMP-4 |
| 9 | CMP-10 IMU heading drift | static dwells before and after motion | — |

The scale regression uses the **whole approach including the acceleration ramp**, not
just the cruise. At constant velocity the ranger's transport lag is a constant offset and
is unidentifiable; during acceleration it produces curvature, so fitting
`r = R0 − k·θ + k·τ·ω` over the ramp separates `k` from `τ`. The acceleration phase is an
asset, not a nuisance to be trimmed away.

### 4.2 Structure of the eventual verification argument (predictions left open)

The argument closes at GATE C in exactly this shape, one row per requirement:

```
requirement → SysML operand binding → calibrated parameter(s) + evidence tier
            → executable-model prediction → margin → verification method → verdict
```

with the roll-up `WallRover satisfies WallRunNeed` evaluating to SATISFIED only if every
hard requirement's operand pair passes. Predictions are **not** filled in here — that is
GATE B's frozen artefact. What is fixed now is the *shape*, the method allocation
(§9 of the specification), and this commitment:

- **SYS-3, the objective, closes at GATE C on M2**, not on the operation runs. Operation
  is a scored demonstration and a repeatability sample; it first-verifies nothing.
- Any requirement lacking a verdict makes the Verification Report incomplete, and it is
  reissued rather than shipped with an assertion.

---

## 5. APPENDIX — free analysis already performed, and what it changed

Per the tenet that free analysis is preferred to a hardware run wherever it can answer the
question, the flight program was executed against a host-side simulated rover before any
flash. Two harnesses: `05_sim_harness.py` (a stand-in Pybricks runtime with physics) and
`06_design_loop_check.py` (draws a rover from the prior box, gives the model perfect
knowledge of it, lets the model choose `R_trig`, then runs the **real program** against
that rover). This validates the **procedure**, not the rover; it binds nothing.

**It found four defects that would otherwise have cost hardware runs — or worse, shipped:**

| # | defect | how it would have presented | fix |
|---|---|---|---|
| 1 | the design solve drove `R_trig` **below the ranger's validity floor** on 4 of 12 draws | primary trigger silently never fires; a backstop delivers the run and it *looks like success* | **FUN-14** added to the specification, SysML and model: a reachability clamp `R_trig ≥ r_floor + k_σ·σ_n` |
| 2 | the SYS-8 fallback estimate `d_T − S_ranger − b` was **circular** — `S_ranger` is computed from `r_rest`, so it collapses back to the floored value | onboard gap estimate wrong by up to +90 mm, undetectable without ground truth | fallback must use the **calibrated** `S` constant; the program now emits both channels plus its selection |
| 3 | travel/time backstops sized from an assumed start gap rather than measured `R0` | backstops **pre-empt** the primary trigger by `b`, on 4 of 12 draws | limits derived at runtime from the rover's own `R0` |
| 4 | time backstop too tight for a slow rover | run terminated before reaching the trigger | derived from `R0`, `R_trig` and calibrated `v` |

Outcome after the fixes, over 12 draws spanning the full prior box:

| metric | before | after |
|---|---:|---:|
| contacts | 0 / 12 | **0 / 12** |
| minimum true gap | 1.2 mm | 9.6 mm |
| max abs prediction residual | 218.3 mm | **12.4 mm** |
| max abs onboard-estimate error | 90.2 mm | **10.1 mm** |

**Two residual concerns carried into RUN-1**, both to be resolved with real data rather
than argued away here:

- The travel backstop still co-triggers with the ranger on some draws, because
  `delta_bs_mm` = 25 mm is a prior, not a measurement. RUN-1 measures the actual
  odometry-vs-ranger residual; `delta_bs` will be set to ≥3× it so the backstop is a true
  backstop rather than a co-trigger, and the model re-checked to confirm the degraded gap
  stays positive.
- One draw showed an onboard-estimate error of 10.1 mm, marginally outside SYS-8's limit,
  on the *fallback* channel. If RUN-1 shows `r_floor` low enough that the primary channel
  is available at the operating point, this is moot; if not, SYS-8's limit is re-examined
  at GATE B on evidence, not relaxed for convenience.

**Structural gate checks** (`03_model_checks.py`) — all pass, and the checker was
negative-tested by injecting an orphaned requirement, a broken edge and a dangling
operand, each of which it caught:

```
PASS  C0 nested requirement references resolve to a declared requirement
PASS  C1 every requirement reachable from the top need (NEED)
PASS  C2 realized decomposition edge-set == specification requirement tree
PASS  C3 per-package import resolution
PASS  C4 SysML requirement ids == executable-model requirement ids
PASS  C5 every requirement binds both operands to existing attributes
PASS  C6 no dead parameters; every Python parameter has a SysML attribute
requirements declared : 41 | decomposition edges : 45 | reachable from NEED : 41
```

---

## 6. WHAT I AM ASKING YOU TO REVIEW

1. **The prior ranges in §0.2** — they are an input to the analysis, and if one is wrong
   the priority ordering changes.
2. **`k_sigma` = 3.0** (§1.3) — the risk posture. Lower buys a closer stop and raises
   contact probability; this is the one dial that trades the two scored quantities
   directly against each other.
3. **The two costed measurements in §3**, and my decision *not* to measure rover width.
4. **The RUN-1 program** (`04_run1_program.py`) — in particular the plugging stop
   (rationale: it minimises `S`, hence `σ_S = rel_σ_S · S`, and unlike a position hold it
   does not retreat, so minimum clearance and final gap are the same point) and RUN-1's
   `k`-free risk posture (§2.3).
5. **Run budget:** I intend **one** characterization run (RUN-1) plus **one** verification
   run, and two operator measurements. If RUN-1 fires a re-plan trigger from §2.4, that
   becomes two characterization runs and I will re-issue this plan first.

**I will not flash anything until you have reviewed this and given an explicit
go-ahead — and I will ask again immediately before the flash itself.**

---

## ADDENDUM A — pre-flight change, issued before RUN-1 (plan v1.1)

*Recorded rather than silently applied: the RUN-1 program was presented for review in
v1.0, so a change to it is a change to a reviewed artefact.*

**Finding.** The final pre-flight dry run terminated on `trigger_reason = 3` (odometric
backstop) rather than `1` (ranger trigger). The backstop pre-empted the primary trigger by
~5 mm. This is the residual concern already stated in §5 — `delta_bs_mm` is a prior, not a
measurement — arriving earlier than expected.

**Diagnosis (analysis, no hardware).** In RUN-1 the backstop must satisfy two conditions
simultaneously, and with `k` spanning 0.35–0.80 mm/deg they are **incompatible**:

- non-pre-empting: `travel_lim_deg ≥ (R0 − R_trig)/k_min = 425/0.35 ≈ 1214 deg`
- protective:      `travel_lim_deg ≤ (R0 − S_worst)/k_max = 543/0.80 ≈ 679 deg`

No value satisfies both. This is not a tuning problem; it is a direct consequence of `k`
being unbound, which is *why RUN-1 exists*.

**Disposition.** Make the backstop deliberately **non-pre-empting** in RUN-1, so that the
FUN-4 primary-trigger path is genuinely exercised and unit-verified. RUN-1 protection is
carried, as §2.3 already states, by the **`k`-free staleness guard**, the conservative
`R_TRIG`, and the wrong-way guard. Implemented as one new constant:

```
K_BACK_MM_PER_DEG = 0.35   # LOWER bound of k, used ONLY for the backstop conversion
```

Using the lower bound of `k` makes the conversion conservative in the non-pre-empting
direction by construction, rather than by a tuned number. In the operation program this
constant takes the single calibrated value of `k`, at which point the two conditions above
are no longer in tension and the backstop becomes a true backstop.

**Verification of the change:** dry run now terminates on `trigger_reason = 1`, no contact,
sentinel present, 95 of 260 buffer slots used, 134 telemetry lines, 10.7 s simulated.

**No other change.** `R_TRIG`, the trigger rule, the stop maneuver, the guards and the
phase structure are as reviewed. SYS-7 remains scheduled for verification at the
verification run, with `k` bound.
