# CALIBRATION PLAN — Wall-Approach Rover

**Document type:** PLAN (forward-looking; **revised and re-issued** if any characterization run reveals something this version did not anticipate — prior versions retained).
**Version:** 1.0 · **Phase:** GATE A (after spec + model, before any hardware).
**Realises:** Requirements Specification v1.0 + `02_wall_run_model.sysml`.

---

## 0. Strategy in one paragraph

We operate at exactly **one** speed (maximum), so the `StoppingDistance` relation is exercised at a single point. Per the relation-template doc, at a single operating point we **measure the stopping overshoot directly there** (calibration point = operating point ⇒ zero extrapolation) rather than fitting the quadratic. The whole control law collapses to one transfer function: **final gap = d_trig − O**, where **O** is the effective overshoot at max speed and **d_trig** is the range threshold at which we brake. Calibration must bind **O** (and the speed v, constant k, latency, refresh, drift, sensor bias, and the σ-budget for the margin). We do it in **one characterization run (C1)** that is a strict superset of the operation program, plus **one operator ground-truth measurement** taken at the verification run. Target Phase-1 program count: **2** (C1 + verification). Target outside-input: **1** (verification gap) plus the mandated post-hoc 5 at close-out.

---

## 1. Calibration input list

### 1a. Model-completion parameters (the model must predict these; no requirement names them)

| Param (model attr) | Symbol | Unit | Producing activity |
|---|---|---|---|
| `kRotToSpeed` | k | m/rad | C1 — Δrange ÷ Δodometry over cruise |
| `maxGroundSpeed` | v_max | m/s | C1 — cruise dR/dt (cross: k·ω) |
| `responseLatency` | tResponse | s | C1 — loop period + sensor staleness (or absorbed in O) |
| `deceleration` | a | m/s² | C1 — back-solved from O, v, tResponse (feasibility only) |
| `stopOvershoot` | O | mm | C1 (onboard, bias-uncorrected) → Verification (bias-free) |
| `sensorBias` | b | mm | Verification — operator true gap vs static reading |
| σ_pred, σ_meas, σ_r2r | σ | mm | C1 residual/scatter + run-to-run reasoning → refine at Verification |

### 1b. Requirement-TBD register (thresholds appearing in requirement constraints)

| Threshold (model attr) | Requirement | Bound at | How set |
|---|---|---|---|
| `forwardRefresh` / `maxRefresh` | CMP-2.1 | C1 | measured cadence; bound = loop period |
| `forwardMinRange` | CMP-2.1, CMP-2.3 | C1 (if seen) + Verification | range where readings destabilise |
| `forwardMaxRange` | CMP-2.3 | C1 | reading quality at start ≈1000 mm |
| `overshootBudget` | CMP-2.2 | derived | = d_trig − m\* (feasibility envelope) |
| `maxHeadingDev` (TBD-dev) | SYS-5, CMP-3.1 | analytic | from gap-geometry + sensor beam half-width |
| `contactMargin` m\* (TBD-m\*) | SYS-6 | derived | = k_σ·RSS(σ_pred,σ_meas,σ_r2r) |
| `stopTolerance` (TBD-stop) | SYS-3 | C1 | residual speed at rest |
| `gapBudget` (TBD-gap) | SYS-4 | analytic | m\* + reporting band |
| `corr` threshold + gain | CMP-3.2 | C1 (conditional) | only if drift breaches SYS-5; gain derived |

---

## 2. Source-of-truth hierarchy (stated up front, enforced thereafter)

**Tier 1 — external ground truth:** operator-measured gap (verification + close-out). Highest trust.
**Tier 2 — anchored / multi-point onboard:** a value fit across several samples or anchored to a Tier-1 reference (e.g., k from a multi-point Δrange/Δodometry regression; v_max from a slope fit).
**Tier 3 — single onboard sample:** one reading (e.g., a lone refresh-interval timestamp).

**Enforcement.** A lower tier **never silently overwrites** a higher tier. A later sample that disagrees with a higher-confidence value is a **discrepancy to diagnose** (low battery? range-dependence? glitch?), **not** grounds to re-fit the constant. Every bound value is carried in the Calibration Report with: #samples, reference used, tier.

Specific consequence for **O**: C1 gives a Tier-2 onboard estimate of **(O − b)** (overshoot tangled with static bias). The verification operator measurement (Tier 1) yields the **bias-free O** directly as O = d_trig,verif − gap_true. The Tier-1 value governs operation; the Tier-2 C1 value is the prediction being checked, **not** overwritten away.

---

## 3. Channel catalog & cross-sourcing (CHARACTERIZATION METHOD part 1)

For every quantity to calibrate, all independent onboard channels (derived from the rover inventory), ranked by directness/confidence, with the run that binds it. A channel serving no needed quantity drops out.

| Quantity | Rank 1 (primary) | Rank 2 | Rank 3 | Binding run |
|---|---|---|---|---|
| **Ground speed v** | Forward ultrasonic slope dR/dt (direct length/time) | Motor odometry Δangle·k (needs k) | IMU ∫forward-accel (drift-prone, weak) | C1 |
| **Constant k** | Δrange ÷ Δodometry, multi-point regression over cruise | (IMU ∫∫accel sanity) | — | C1 |
| **Forward range / gap** | Forward ultrasonic #1 | Forward ultrasonic #2 (redundant + skew) | Odometry from known start ≈1000 mm | C1; gap anchored at Verification (operator) |
| **Stop overshoot O** | R_trigger − R_final (ultrasonic) | Odometry Δangle trigger→rest · k | — | C1 (bias-tangled) → Verification (bias-free) |
| **Heading / straightness** | IMU yaw | Differential odometry (L−R wheel angle) | Two forward sensors' L/R disagreement | C1 |
| **Forward refresh** | Inter-sample Δt of distance() updates | loop wall-clock period | — | C1 |
| **Sensor static bias b** | operator true gap − static reading (Tier 1) | — | — | Verification |
| **Residual stop speed** | dR/dt after brake settles | IMU angular_velocity ≈ 0 | — | C1 |

**Fault-detector use (B1, fault-agnostic).** Every C1 sample logs *every* channel above bearing on the quantities that run touches — not just the one under test. Disagreement is the hardware-fault detector; we never assume which channel is wrong, we let the disagreement reveal it. Concretely: if forward ultrasonic #1 and #2 diverge → sensor/skew fault; if ultrasonic-slope v and odometry v diverge → wheel slip or a mis-mapped port; if IMU yaw and differential odometry diverge → gyro drift or a stuck wheel.

**Range hand-off (bounded channels).** The forward ultrasonic has a reliable floor (`forwardMinRange`, TBD). The trigger fires well above it (d_trig ≈ O + m\*, comfortably inside range), so the trigger never depends on sub-floor readings. For the *final* gap estimate at the smallest stops, if the static reading is below the reliable floor we hand off to the odometry-from-start channel and the model-predicted m\* rather than extrapolating the ultrasonic past its limit.

**Dropped channels (absence by traceability).** Rear ultrasonic and floor reflectance serve no needed quantity (no guaranteed rear reference; start position already from forward sensor). They are logged opportunistically in C1 (free fault data) but bind nothing.

---

## 4. Test-like-you-fly run construction (CHARACTERIZATION METHOD part 3)

**Principle.** The characterization program is a **strict superset** of the operation program: identical control loop, trigger, and buffer skeleton. All extra characterization logging is **off the hot path** — written to a pre-allocated buffer and dumped *after the motors stop*, never woven into the control iteration. This keeps operational timing fidelity, so what we calibrate transfers to operation with no re-anchor.

### 4.1 Shared skeleton (operation == characterization minus the dump)

```
SETUP (off hot path):
  discover ports: probe each port by trial-construct (Motor, then Ultrasonic, then Color),
                  catch exceptions; construct each device exactly ONCE, reuse it.
  determine motor polarity: brief low-speed nudge on each motor; sign chosen so that the
                  forward ultrasonic range DECREASES (= forward). [logged]
  classify the two forward rangers vs the rear by which reads ~1000 mm at the start line.
  reset clock; read R_initial (start range), heading0.

HOT PATH (control loop, paced by wait(LOOP_MS)):
  read fused forward range R = fuse(ultra_fwd_1, ultra_fwd_2)   # agree->mean; disagree->min (conservative)
  if not braking:
      drive both motors at MAX (run(big), polarity-corrected; optional heading term)
      if R <= d_trig:  begin braking  (record t_trigger, R_trigger)
  else:
      brake() both motors; when |dR/dt| ~ 0 for N samples -> hold() both; exit
  [characterization only] append {t, R1, R2, R_fused, angL, angR, yaw, accF, gyroZ, rear, refl} to BUFFER

SHUTDOWN:
  motors.hold(); read R_final (static), heading_final
  [characterization only] DUMP BUFFER as telemetry lines, then end sentinel
  emit live: R vs t (downsampled) + heading, ALWAYS end with {"event":"end"}
  wrapped in try/finally so motors stop and sentinel sends even on interruption
```

### 4.2 Run C1 — calibration + unit verification (the only planned characterization run)

- **Trigger threshold `d_char` = 400 mm** — deliberately SAFE: even with the full estimated overshoot the rover stops well short of the wall, so C1 carries **zero contact risk** while still exercising the real max-speed approach and the real brake event.
- **Speed:** command `run()` at a large target so the firmware clamps to the physical ceiling (raise `control.limits` if needed so run() is not capped below physical). Achieved speed measured, not assumed.
- **Stop method:** `brake()` (passive, repeatable) then `hold()`. (`hold()`-only alternative noted; not swept to save a program.)
- **Logging:** full channel catalog §3 to buffer at the loop rate; dump after stop.

**What C1 binds (all onboard, Tier 2/3):**

| From C1 | Extraction | Unit-verifies |
|---|---|---|
| k | regression Δrange vs Δ(mean odometry) over cruise | (supports v) |
| v_max | dR/dt steady segment (cross-checked k·ω) | **CMP-1.1** (achieved = ceiling) |
| O (bias-tangled) | R_trigger − R_final (cross: Δangle·k) | **CMP-2.2** (overshoot bounded & repeatable enough) |
| a | back-solve O = v·tResponse + v²/2a (feasibility) | CMP-2.2 sanity |
| forwardRefresh, maxRefresh | inter-sample Δt distribution | **CMP-2.1** |
| forwardMaxRange | reading quality at ~1000 mm | CMP-2.3 input |
| imuDriftRate, headingDrift | yaw over approach vs differential odometry | **CMP-3.1**; decides CMP-3.2 instantiation |
| stopTolerance | residual dR/dt at rest | **SYS-3** input |
| σ_meas | ultrasonic scatter + one-sample-period jitter v·refresh | m\* budget |
| σ_pred (partial) | brake-event consistency, accel-phase clean-up check | m\* budget |

**Note on σ_r2r.** A single C1 run cannot measure run-to-run spread. We will (i) bound it by physical reasoning (battery state-of-charge droop over 5 short runs; the operator's between-run power-cycle clears thermal/gyro drift, removing that contributor), and (ii) get a second independent stopping datum at the verification run, giving a C1-vs-verification consistency check. σ_r2r is sized conservatively rather than understated; this protects the hard no-contact constraint at the cost of a slightly larger gap (acceptable trade under graded assurance, since contact is the dominant failure).

---

## 5. Outside-input requests (each one is the second score — minimised, batched)

| # | Request | When | Purpose (batched cross-checks) |
|---|---|---|---|
| **OI-1** | Operator-measured **true gap** at the rover's rest position | At the **verification run**, after it stops | (a) anchors `sensorBias` b = R_final − gap_true; (b) yields **bias-free O** = d_trig,verif − gap_true; (c) **tests the frozen verification prediction** (predicted gap vs measured); (d) validates the whole trigger chain. One measurement, four uses. |

- **C1 needs no operator input** — start range comes from the forward sensor at t=0; everything else is onboard. So Phase-1 controllable outside-input = **1** (OI-1).
- **Close-out (mandated, post-hoc):** the 5 operation-run gaps, requested only *after* all five are locked and run. Counted but unavoidable and incapable of influencing any run.

---

## 6. VERIFICATION SUPPORT

### 6.1 How calibration supports unit verification (CMP closes at GATE B)

Unit verification of the lowest-level requirements closes in the **Calibration Report** directly from C1:

- **CMP-1.1** (commanded ≥ max): C1 confirms achieved cruise speed equals the firmware ceiling ⇒ command is at/above max. ✔ from C1.
- **CMP-2.1** (refresh/range): C1 refresh-interval distribution + reading validity over the approach. ✔ from C1.
- **CMP-2.2** (overshoot bounded): C1 measures O at max speed and its scatter. ✔ from C1 (bias-tangled value; magnitude/repeatability is what CMP-2.2 needs).
- **CMP-3.1** (heading drift): C1 yaw-vs-odometry. ✔ from C1; also decides whether **CMP-3.2** must be instantiated.
- **CMP-2.3** (trigger ≤ sensor range): computed analytically once O, m\*, range are bound ⇒ closes at GATE B in the Verification Plan, not by a run.

Integrated requirements (**SYS-2/3/4/5/6**) do **not** close here — they close at the verification run (GATE C).

### 6.2 Structure of the eventual verification argument (predictions left OPEN here)

The pre-run verification artifact is the **satisfy/require roll-up evaluated against calibrated values**. Its shape is fixed now; the numbers are filled and **frozen** in the Verification Plan at GATE B, before the integrated run. Open structure:

```
WallRover satisfies WallRunNeed  ⟺  all of:
  SYS-1 MaxSpeed         : achievedSpeed  ≥ maxGroundSpeed        [pred: ____ ≥ ____]
  SYS-2 NoContact        : finalClearance ≥ 0                     [pred: ____ ≥ 0]
  SYS-3 FullStop         : finalSpeed     ≤ stopTolerance         [pred: ____ ≤ ____]
  SYS-4 MinimiseGap (obj): finalClearance ≤ gapBudget             [pred: ____ ≤ ____]
  SYS-5 StraightApproach : headingDrift   ≤ maxHeadingDev         [pred: ____ ≤ ____]
  SYS-6 ClearanceMargin  : finalClearance ≥ contactMargin (m*)    [pred: ____ ≥ ____]
    via FUN-2 StopOnTrigger:
      CMP-2.1 forwardRefresh  ≤ maxRefresh                        [pred: ____ ≤ ____]
      CMP-2.2 stopOvershoot   ≤ overshootBudget                   [pred: ____ ≤ ____]
      CMP-2.3 triggerDistance ≤ forwardMaxRange                   [pred: ____ ≤ ____]
    via FUN-1: CMP-1.1 commandedSpeed ≥ motorMaxSpeed             [pred: ____ ≥ ____]
    via FUN-3: CMP-3.1 imuDriftRate   ≤ maxHeadingDev             [pred: ____ ≤ ____]
                CMP-3.2 (only if instantiated)
  with relations bound:
    rotToSpeed : maxGroundSpeed = motorMaxSpeed · k
    triggerCalc: triggerDistance = v·tResponse + v²/(2a) + m*
    overshootId: stopOvershoot   = triggerDistance − m*
  predicted final gap  = m*  (by construction)
  predicted margin     = m* − 0  against the no-contact line, RSS-sized
```

The verification run tests the **predicted final gap = m\*** claim against OI-1 ground truth. If falsified, we diagnose the responsible parameter (most likely candidate: `sensorBias` b, or `O`), **re-derive** (not empirically tweak), issue a **new** Verification Plan version (the falsified one stays frozen), and re-run.

---

## 7. Verification sequencing (A5 / C1 ordering)

Dependency order within the analysis: **k → v_max → O → a**; **bias** anchored separately (Tier 1, verification). Components verified before integration (C1 unit-verifies CMP; the integrated run follows). The verification run is **never** one of the five scored runs.

Planned program ledger (Phase 1): **C1** (calibration + unit verification) → **Verification run** (integrated, tests frozen prediction). Re-runs only if a gate falsifies; each would count.

*End of Calibration Plan v1.0 (PLAN — subject to re-issue on new C1 information).*
