# Calibration Plan — Wall-Approach Rover
**Document type:** PLAN (revised & re-issued after any characterization run that necessitates a
re-plan) · **Version:** v1 · **Gate:** GATE A (after spec + SysML + executable model, **before
any hardware**)

This plan is produced by the executable analysis model (`03_wallrun_model.py`), run at the
stated priors. No rover has been touched. It opens with the sensitivity analysis, which
justifies everything after it.

---

## Section 0 — Sensitivity analysis (REQUIRED TABLE)

**Method.** Using `wallrun_model.sweep_parameter()`, each free/uncertain parameter was swept
over its **explicitly stated prior range** (below) with all others at nominal. Reported: the
swing in the **objective** (true final gap, at fixed `d_trig`) and in the **hard-constraint
margin** M (SYS-6). *Priors are an input to your review.*

**Stated priors (state of knowledge):**

| Parameter | Prior range | Nominal | Knowledge tier |
|-----------|-------------|---------|----------------|
| `v_cruise` (mm/s) | 250 – 500 | 380 | physics (motor + wheel geometry) |
| `a_decel` (mm/s²) | 800 – 3000 | 1600 | physics (`brake()` deceleration band) |
| `t_response` (s) | 0.030 – 0.150 | 0.070 | weak (loop period + sample staleness) |
| `refresh` (s) | 0.020 – 0.060 | 0.040 | datasheet (LEGO ultrasonic) |
| `sensor_bias` (mm) | −20 – +20 | 0 | **unknown — no onboard absolute reference** |
| `ranger_floor` (mm) | 20 – 60 | 40 | datasheet (ultrasonic min range) |
| `sigma_run` (mm) | 3 – 15 | 8 | weak (no repeats yet) |

**Sensitivity results** (ranked by leverage; nominal `d_trig` = 116 mm, `D_dyn` = 71.7 mm):

| Parameter | Assumed range | Objective sensitivity (gap swing) | Margin sensitivity (M swing) | Knowledge tier | Resulting priority |
|-----------|---------------|-----------------------------------|------------------------------|----------------|--------------------|
| `v_cruise` | 250–500 mm/s | **76.1 mm** | 2.5 mm | physics / medium | **P1** → folds into direct `D_dyn` |
| `a_decel` | 800–3000 mm/s² | **66.2 mm** | 0 | physics / medium | **P1** → folds into direct `D_dyn` |
| `t_response` | 0.03–0.15 s | **45.6 mm** (∂gap/∂t = −v) | 0 | weak | **P1** → folds into direct `D_dyn` |
| `sensor_bias` | ±20 mm | **40.0 mm** (exactly 1:1) | 0 | **unknown (no onboard channel)** | **P1-CRITICAL** → operator measurement **at the operating point** |
| `sigma_run` | 3–15 mm | 0 | **20.0 mm** | weak | **P2** → within-run channel spread + physical estimate |
| `refresh` | 0.02–0.06 s | 0 | 3.9 mm | datasheet | **P3** → free from reading timestamps |
| `ranger_floor` | 20–60 mm | 0 | 0 (feasibility only) | datasheet | **P3** → prior + free observation |

**What the table decides (this is the justification for the whole plan):**

1. **The top three objective drivers (`v_cruise`, `a_decel`, `t_response`) are coupled and all
   feed the composite `D_dyn`.** The `StoppingDistance` template's own doc says: at a **single
   operating point** (which "maximum speed" is), **measure the stopping distance directly** —
   calibration point = operating point ⇒ zero extrapolation. So these three collapse into **one
   directly-measured, cross-sourced quantity `D_dyn` at v_max**, rather than three separate
   precision fits. This is the single highest-value characterization target, and it is fully
   onboard.
2. **`sensor_bias` has exactly 1:1 leverage on the objective and is the only parameter no
   onboard channel can pin** (odometry is relative; the ultrasonic is the thing being
   calibrated). This is *exactly* where the costed operator measurement earns its price
   (tenet B4). It is spent **at the operating point**, where it simultaneously pins the bias,
   validates the objective against ground truth, and tests the frozen prediction.
3. **`sigma_run` and `refresh` move the margin, not the mean** — they are picked up for free
   from the characterization run's channel spread and reading timestamps.
4. **`ranger_floor` has zero gap/margin leverage** (feasibility only) — lowest priority, taken
   from datasheet + free observation.

**Margin consequence (why closeness costs an anchor).** With the bias *unanchored* (prior
±20 mm ⇒ σ_bias ≈ 11.5 mm), the model gives **M ≈ 44.6 mm** (σ-RSS dominated by bias). Once the
operator measurement pins the bias (σ_bias ≈ 3 mm), **M ≈ 29.4 mm**; with run-to-run σ trimmed
to 5 mm, **M ≈ 22.7 mm**. The achievable closeness *is* the margin — so the anchor is the single
most valuable action for the closeness objective, and it is the same measurement that closes the
objective per GATE C.

---

## Section 1 — Calibration input list

### 1a. Model-completion parameters (needed to predict; named by no requirement)
`t_chain`, `sampLatency` → `t_response`; `a_decel`; **`D_dyn` (direct)**; `k_rot`; `refresh`;
`ranger_floor`; `sigma_run`; motor forward-sign convention (per motor). All bound in **CHAR-1**.

### 1b. Requirement-TBD register (from spec §7)
TBD-VMAX, TBD-K, TBD-TCHAIN, TBD-TRESP, TBD-ADEC, TBD-DDYN, TBD-REFRESH, TBD-FLOOR, TBD-SRUN,
TBD-HEAD (analysis), TBD-KSIG (choice, baseline **k=3**, tenet A1), TBD-DTRIG (GATE B), TBD-M
(computed). **TBD-BIAS** is bound by the **operator measurement at VER-1** (weak long-range
prior from the t=0 ~1000 mm reading; range-dependence is why the long-range reading is only a
prior, not the anchor).

---

## Section 2 — Characterization-run design (CHARACTERIZATION METHOD)

### 2.0 Channel catalog & cross-sourcing (quantity → channels → confidence → binding run)

| Quantity | Ch. A (rank 1) | Ch. B | Ch. C | Binding run |
|----------|----------------|-------|-------|-------------|
| Wall distance | fwd ultrasonic #1 | fwd ultrasonic #2 | odometry (relative, anchored) | CHAR-1 |
| `v_cruise` | odometry rate | ultrasonic Δreading/Δt | — | CHAR-1 |
| **`D_dyn` @ v_max** | **odometry Δ (trigger→rest), floor-immune** | ultrasonic (d_trig − final reading), valid at 300 mm brake | IMU ∬accel (noisy) | CHAR-1 |
| `a_decel`, `t_response` | odometry/IMU decel profile | — | — | CHAR-1 |
| `refresh` | ultrasonic reading-timestamp spacing | — | — | CHAR-1 |
| `ranger_floor` | ultrasonic near-range roll-off (within valid) | datasheet | — | CHAR-1 / prior |
| Heading drift | IMU yaw | odometry differential (L−R) | — | CHAR-1 |
| **`sensor_bias` @ trigger** | **operator ground truth (higher tier)** | weak US-vs-~1000 mm prior | — | **VER-1** |
| **True final gap (objective)** | **operator ground truth** | onboard odometry estimate | — | **VER-1** |
| `sigma_run` | within-run channel spread (lower bound) | physical estimate | [operation reveals, post-hoc] | CHAR-1 seed |

Every CHAR-1 reading logs **every** channel above bearing on the quantities that run touches
(tenet B1); disagreement is the fault-agnostic detector. Where the ultrasonic goes invalid
(below floor near the wall), the hand-off is to **odometry**, which covers that gap — never
extrapolate the bounded ultrasonic past its floor.

### 2.1 Source-of-truth hierarchy (stated up front)

> **external ground truth (operator)  >  anchored / multi-point onboard calibration  >  single
> onboard sample.**

- A lower tier **never** silently overwrites a higher-tier value. A later sample disagreeing
  with a higher-confidence value is a **discrepancy to diagnose** (low battery draw?
  range-dependence? glitch?), not grounds to re-fit.
- **RULE:** any sensor value driving a scored quantity — the objective above all — is a
  **hypothesis** until confirmed against an independent higher-tier source **at the operating
  point**. `sensor_bias` and the true gap are hypotheses until VER-1's operator anchor.
- **Escalation:** on a disagreement my judgment finds significant, or on any physically
  impossible reading, escalate to better data (higher tier / added channel) — do not arbitrate
  between suspect channels or explain the anomaly away. Every logged channel carries a
  physical-plausibility bound (below) so impossibilities surface automatically.

### 2.2 Test-like-you-fly run construction

The characterization program is a **strict superset of the operation program**: identical
control-loop / trigger / buffer skeleton, with all extra logging **off the hot path**
(pre-allocated buffer, dumped after the motors stop).

**Operation program skeleton (the locked core, shared by CHAR-1 and VER-1):**
1. Construct each device **once** (avoid EBUSY); zero clock/heading.
2. **Guarded direction prelude** (low speed): nudge the drivetrain forward using the sign
   convention; confirm the forward ultrasonic distance *decreases* and odometry sign agrees; if
   not, flip both motor signs. Establishes the forward convention deterministically each run
   (the platform's port→direction mapping is unknown — spec requires we determine it). Low speed
   ⇒ no effect on the full-speed braking calibration that follows.
3. **Full-speed approach:** command both motors forward at max; each loop read
   `min(fwd US #1, #2)` (conservative — nearest wins, protects no-contact), heading, odometry.
4. **Trigger:** when `min(fwd US) ≤ d_trig`, `brake()` both motors; mark trigger event
   (timestamp, readings, odometer).
5. **Rest:** hold until speed ≈ 0; mark rest event. `try/finally` guarantees motors stop and
   the `{"event":"end"}` sentinel is sent even on interruption.

**CHAR-1 (characterization run):** the skeleton above with **`d_trig` = 300 mm (conservative,
far from wall — safe)** and extra **buffered high-rate logging** (IMU accel, both raw
ultrasonics, both odometers, reflectance, rear ranger) dumped after rest. Binds: forward signs,
`k_rot`, `v_cruise`, **`D_dyn` (direct, 3-way cross-sourced)**, `a_decel`/`t_response` (profile),
`refresh` (timestamps), `ranger_floor` (near-range roll-off), heading drift at speed,
`sigma_run` seed (channel spread). Verifies the dropped effectors carry no wall info (rear
ranger, reflectance logged and confirmed uninformative — rule 7).

**Plausibility bounds (auto-surface impossibilities):** ultrasonic ∈ [floor−ε, ~2500 mm] and
monotone-non-increasing during a straight approach; rest reading **not farther** than trigger
reading (a farther rest reading is physically impossible → unconditional escalate); odometry
distance ≥ 0 and monotone; |heading| < 45°; `D_dyn` ∈ [10, 250] mm; the three `D_dyn` channels
agree within a few mm.

---

## Section 3 — Outside-input requests (a SECOND score — minimised)

- **ONE costed operator measurement**, at **VER-1**: the **true final gap (mm)** from the rover's
  front face to the wall at the full stop, at the operating point. This single measurement pins
  `sensor_bias` at the trigger distance (via onboard `D_dyn`), **validates the objective against
  ground truth at the operating point** (GATE C requirement), and tests the frozen prediction —
  three purposes, one measurement. Front-loaded here because Section 0 ranks bias as the 1:1,
  onboard-unpinnable objective driver.
- **Free (uncounted) actions**, requested as needed: power-cycle between runs (given),
  reset/square the rover to the start line, wake the hub. These are hardware operation, not help.
- **No** operator input during the five operation runs (only power-cycle + reset), per task.

---

## Section 4 — Verification support

### 4a. Unit verification delivered by CHAR-1 (CMP leaves, tenet C1: units gate integration)

| CMP | Unit-verification evidence from CHAR-1 |
|-----|----------------------------------------|
| CMP-1 (ranger reads; refresh; floor) | valid readings each refresh; timestamp spacing → `refresh`; near-range roll-off → `floor` |
| CMP-3 (motor at max) | commanded == rated; achieved cruise from odometry (SYS-2/CMP-3) |
| CMP-4 (motor → 0) | odometry & IMU show speed → 0 at rest |
| CMP-5 (odometry → distance via k) | odometry Δ vs ultrasonic Δ over the approach → `k_rot`, agreement |
| CMP-6 (IMU yaw) | yaw logged; heading drift vs odometry differential |
| CMP-7 (IMU accel) | forward accel logged; ∬accel vs odometry/ultrasonic `D_dyn` |
| Motor forward-sign | prelude establishes and logs it |
| Dropped effectors | rear ranger + reflectance logged, confirmed uninformative |

### 4b. Structure of the eventual verification argument (predictions left OPEN here)

The verification artifact is the SysML **satisfy/require roll-up** (`WallRover satisfy
WallRunNeed`) evaluated at the calibrated values — computed by `wallrun_model.evaluate()`. Its
shape, to be filled at GATE B and frozen before VER-1:

```
WallRunNeed  (rover : WallRover)
├─ SYS-1 NoContact        finalClearance ≥ contactMargin      [pred: OPEN]
│    └─ CMP-2 TriggerFeasible  dTrig ≥ rangerFloor + feasGuard [pred: OPEN]
├─ SYS-2 MaxSpeedCmd      commandedSpeed ≥ vMaxRated           [pred: OPEN]
│    └─ CMP-3 MotorAtMax
├─ SYS-3 CompleteStop     finalSpeed ≤ 0                       [pred: OPEN]
│    └─ CMP-4 MotorToZero
├─ SYS-4 MinimiseGap      (objective, graded)                 [pred: OPEN]
├─ SYS-5 StraightApproach headingDrift ≤ headingTol           [pred: OPEN]
│    └─ CMP-6 IMUHeadingCapability
└─ SYS-6 MarginFloor      predictedGap ≥ safetyMargin          [pred: OPEN]
```

At GATE B this becomes numeric (predictions only) from `predict()`/`evaluate()` at the committed
`d_trig` and bound values, **frozen** before VER-1. VER-1 tests it; the operator anchor validates
SYS-4/SYS-1 at the operating point.

---

## Section 5 — Run-count strategy & the closeness/program-count trade (for your decision)

Two hardware runs are the **floor** to reach operation with a *verified* prediction: one to
calibrate the integrative dynamics (CHAR-1), one to verify the frozen prediction (VER-1) — you
cannot fit and verify on the same data ("argue before you run"). `D_dyn` depends on speed, not on
the trigger value, so calibrating it at `d_trig`=300 mm and applying it at the operating trigger
is a genuine out-of-sample test at VER-1.

**A fundamental constraint on closeness:** `sensor_bias` is first observable only when the rover
first reaches the operating point — which is the very run (VER-1) whose `d_trig` had to be chosen
*before* bias was known. So VER-1's `d_trig` is set with the (prior) bias uncertainty, giving a
realized gap ≈ **M(prior) ≈ 35–45 mm**.

| Plan | Runs (Phase 1) | Operator meas. | Expected closeness | Note |
|------|----------------|----------------|--------------------|------|
| **Baseline** | 2 (CHAR-1, VER-1) | 1 | ~35–45 mm | Lock VER-1 if it passes. Minimal program count. |
| **Recommended** | 3 (CHAR-1, VER-1, **VER-2**) | 1 (same, at VER-1) | ~25–30 mm | VER-1's anchor collapses σ_bias (11.5→3 mm); **re-derive** the tightened `d_trig` from the model and **verify it** at VER-2 before locking. Model-driven re-derivation, not empirical tweaking. Extra run also demonstrates the tightened prediction holds before the scored runs. |

I recommend the **3-run plan**: closeness is an explicit scored objective, contact is
catastrophic, and VER-2 buys a demonstrated-safe tighter margin for the cost of one run and **no
extra measurement**. But this trades program-count (score 1) against closeness (score 4), whose
weights I don't know — so I surface it for your call at this gate rather than assuming.

---

## Section 6 — What I will bind, in order (B2: trusted-reference-first)

1. Motor forward-signs → `k_rot` → `v_cruise` (odometry, most direct, least coupled). CHAR-1.
2. **`D_dyn` @ v_max, directly, 3-way cross-sourced** (the P1 objective driver). CHAR-1.
3. `refresh`, `ranger_floor`, heading drift, `sigma_run` seed (free, same run). CHAR-1.
4. Freeze prediction (GATE B) with bias-prior margin.
5. **`sensor_bias` + true-gap objective anchor** (the P1-critical operator measurement). VER-1.
6. (Recommended) re-derive tightened `d_trig`, freeze new prediction, verify. VER-2.

---

*End of Calibration Plan v1. Presented for review at GATE A. I will not flash any program until
you confirm this plan and the rover is ready. This plan will be re-issued as a new version if a
characterization run reveals something it did not anticipate.*
