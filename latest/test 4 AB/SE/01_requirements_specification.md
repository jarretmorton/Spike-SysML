# Requirements Specification — Wall-Approach Rover

**Project:** Maximum-speed wall approach, minimum no-contact gap
**Authority:** This specification is the **source of truth** for requirements. The SysML model
(`02_tailored_sysml_model.md`) is a formal realisation of it; on any disagreement, **this spec governs**.
**Standards:** INCOSE GtWR (4th ed.) over ISO/IEC/IEEE 29148:2018; EARS grammar; NASA SP‑2016‑6105
for decomposition and V&V framing.
**Status:** Phase 1–2 baseline, frozen for GATE A. TBD values bind in Phase 4 (calibration).

---

## 1. Scope & the core engineering tension

The task asks for three things that **pull against each other**:

| Pull | Type | Source |
|---|---|---|
| Stop as *close as possible* to the wall | Objective (graded, `should`) | task |
| *Never* touch the wall | Hard constraint (`shall not`) | task |
| Travel at *maximum* speed, no slowing for margin | Hard constraint (`shall`) | task |

At maximum speed the rover keeps moving after the stop command (latency + braking). The whole problem
is choosing a **stop-trigger distance** so that `trigger − stopping_distance` lands just above zero,
robustly, run to run. The minimum achievable gap is therefore set by how *repeatable* the stop is, not
by how aggressive we dare to be. This drives the decision to **size the standoff margin from measured
uncertainty** (Tenet A6) rather than guess it.

---

## 2. EARS pattern legend

`U` Ubiquitous · `St` State-driven (*While …*) · `Ev` Event-driven (*When …*) · `O` Optional (*Where …*) · `Un` Unwanted (*… shall not …*).
Verification method (NASA): **T** Test · **A** Analysis · **I** Inspection · **D** Demonstration.

---

## 3. Stakeholder needs (STK)

| ID | Pattern | Requirement | Rationale | Verify |
|---|---|---|---|---|
| **STK‑1** | U | The system shall come to rest as close to the wall as achievable. | Primary graded objective; defines the score being minimised. | A/T |
| **STK‑2** | Un | The system shall not contact the wall. | Hard safety constraint; any contact = run failure. | T |
| **STK‑3** | U | The system shall traverse toward the wall at its maximum achievable speed. | Hard performance constraint; explicitly no slowing for safety margin. | T |

---

## 4. System requirements (SYS) — black box

| ID | Pattern | Requirement | Parent | Derived? | Rationale | Verify |
|---|---|---|---|---|---|---|
| **SYS‑1** | St | While in the approach state, the rover shall command its drivetrain at the maximum achievable speed. | STK‑3 | — | Direct realisation of the max-speed constraint. | T |
| **SYS‑2** | Un | The rover shall not make contact with the wall (final true clearance > 0). | STK‑2 | — | Hard no-contact constraint, stated on the physical gap. | T |
| **SYS‑3** | O | Where the no-contact constraint is met, the rover should minimise the final clearance. | STK‑1 | — | The graded objective; bounded below by SYS‑5. | A/T |
| **SYS‑4** | St | While approaching, the rover shall keep heading within `yawMax` of its initial heading. | STK‑2, STK‑1 | **D** | Off-axis drift makes the sensed closing distance differ from the true bumper-to-wall gap and risks an angled clip; bounding drift keeps "closing distance ≡ gap" valid. Not literal in the task → derived. | T |
| **SYS‑5** | Ev | When the rover comes to rest, the final clearance shall be no less than the sized design margin `designMargin`. | STK‑1+STK‑2 | **D** | **Rule‑3 bridge** between the hard constraint (SYS‑2) and the objective (SYS‑3): converts "as close as possible without contact" into one verifiable floor. `designMargin` is sized from uncertainty (A6); with `designMargin > contactMargin ≈ 0`, satisfying SYS‑5 *guarantees* SYS‑2 with confidence and fixes how aggressive SYS‑3 may be. | A/T |
| **SYS‑6** | Ev | When the stop is triggered, the rover shall bring its drivetrain to a complete stop. | STK‑1 (task: "complete stop") | **D** | Task requires a full stop, not merely slowing; defines the rest condition the clearance is measured at. | T |

---

## 5. Function requirements (FUN)

| ID | Pattern | Requirement | Parent | Derived? | Rationale | Verify |
|---|---|---|---|---|---|---|
| **FUN‑1** | St | While approaching, the rover shall measure forward distance to the wall each control cycle with bounded staleness (`refreshInterval ≤ maxStaleness`). | SYS‑2/5/6 | — | The stop decision is only as good as the freshness of the distance it acts on. | T |
| **FUN‑2** | U | The rover shall derive forward distance from **two independent forward sensors** and trigger on the **nearer** of the two. | SYS‑2 | **D** | **Rule‑6 cross-sourcing.** A single sensor reading *long* would cause contact; the nearer-of-two rule is fault-agnostic and fails safe (a spuriously-long reading is ignored). Disagreement is also the hardware-fault detector (B1). | T |
| **FUN‑3** | St | While approaching, the rover shall command **both** drive motors at the maximum achievable speed. | SYS‑1 | — | Realises max speed on a differential drivetrain. | T |
| **FUN‑4** | Ev | When the nearer forward distance falls to or below the stop-trigger threshold, the rover shall command a full stop. | SYS‑2/5/6 | — | The control law. Threshold = stopping distance + `designMargin` (StoppingDistance relation). | T |
| **FUN‑5** | Ev | When a full stop is commanded, the rover shall come to rest within the calibrated stopping distance `Σ` of the trigger point. | SYS‑5/6 | — | The braking budget that the trigger threshold reserves. | T |
| **FUN‑6** | St | While approaching, the rover shall sense heading via the IMU and keep drift ≤ `yawMax`. | SYS‑4 | — | Realises SYS‑4. Irreducibly integrative (drivetrain balance, sensed by IMU) — decomposition stops here per Rule 2. | T |

---

## 6. Component requirements (CMP) — single-effector leaves

Each CMP requirement is verifiable by a test on **one effector** and instantiates a requirement
template by binding its operands (see model). TBD values bind in calibration.

| ID | Pattern | Requirement | Effector | Template | Parent | Verify |
|---|---|---|---|---|---|---|
| **CMP‑MOT‑1** | St | While approaching, each drive motor's commanded speed shall be ≥ its maximum achievable speed `maxSpeed`. | Drive motor (×2) | LowerBound | FUN‑3 | T |
| **CMP‑MOT‑2** | Ev | When a full stop is commanded at max speed, the drivetrain stopping distance `Σ` shall be ≤ the trigger budget (`triggerThreshold − designMargin`). | Drive motors (decel) | UpperBound | FUN‑4/5 | T |
| **CMP‑RNG‑1** | St | While approaching, each forward distance sensor's refresh interval shall be ≤ `maxStaleness`. | Forward distance sensor (×2) | UpperBound | FUN‑1 | T |
| **CMP‑RNG‑2** | U | The two forward sensors' readings shall agree within `agreementTol` over the operating range. | Forward distance sensors (pair) | UpperBound | FUN‑2 | T |
| **CMP‑IMU‑1** | St | While approaching, IMU-sensed heading drift shall be ≤ `yawMax`. | IMU | UpperBound | FUN‑6 | T |

---

## 7. Effector selection (Phase 2) — derived from the CMP leaves

An effector is **kept** only if a requirement traces to it; otherwise it **drops out by traceability**
(Rule 7 — verified, not assumed).

| Platform effector/sensor | Tracing requirement | Decision |
|---|---|---|
| Drive motor A | CMP‑MOT‑1, CMP‑MOT‑2 | **KEEP** |
| Drive motor B | CMP‑MOT‑1, CMP‑MOT‑2 | **KEEP** |
| Forward distance sensor #1 | CMP‑RNG‑1, CMP‑RNG‑2 | **KEEP** |
| Forward distance sensor #2 | CMP‑RNG‑1, CMP‑RNG‑2 | **KEEP** |
| IMU (yaw) | CMP‑IMU‑1 | **KEEP** |
| **Rear distance sensor** | *none* — task is a forward approach; nothing behind is constrained | **DROP** (absence by traceability) |
| **Downward reflectance/color sensor** | *none* — no floor-marking, line-following, or start-line-gating requirement | **DROP** (absence by traceability) |
| IMU forward-acceleration channel | *no requirement*, but retained as a **cross-source/health channel** (B1) — collision spike + stop-event confirmation, not a primary requirement | KEEP as monitor only |

---

## 8. Cross-sourcing allocation (Rule 6 / Tenet B1)

Independent channels deliberately allocated to the same quantity, so disagreement reveals a fault
(fault-agnostic — we never assume which channel is bad):

| Quantity | Primary channel | Independent cross-source(s) |
|---|---|---|
| Forward distance / closing speed | Forward sensor #1 (nearer-of-two) | Forward sensor #2; speed also cross-checked vs. IMU forward-accel integral (sign/onset only) |
| Stop event (motion → rest) | Forward distance flattening | IMU forward-acceleration deceleration pulse |
| Straight-line travel | IMU yaw | Symmetry of the two forward-sensor traces during approach |
| Contact (must never happen) | True clearance (operator measure, once) | Forward distance floor + IMU acceleration spike |

---

## 9. Hard constraints vs. objectives, and the margin bridge (Rule 3)

- **Hard (pass/fail):** SYS‑1, SYS‑2, SYS‑4, SYS‑5, SYS‑6 and their CMP leaves.
- **Objective (graded):** SYS‑3 (minimise gap).
- **Bridge:** **SYS‑5** ties them together. We minimise the gap *down to* `designMargin`, and
  `designMargin` is **sized from uncertainty** (Tenet A6):

  `designMargin = k · sqrt( σ_pred² + σ_meas² + σ_run² )`

  with `k` the assurance factor and the three σ-contributors each resolved by calibration (§10). The
  predicted nominal final gap equals `designMargin`; no-contact holds because the worst-case downside
  (`designMargin − k·σ_run`) stays > 0 by construction.

---

## 10. TBD register

Every unknown is marked TBD and bound to a specific calibration activity. This register is part of the
input list to calibration (the remainder being model-completion parameters — see the C&V Plan).

| TBD | Quantity (symbol) | Units | Used by | Bound by (calibration activity) | Channel |
|---|---|---|---|---|---|
| **TBD‑01** | True clearance at CHAR‑1 rest, `g_char` | mm | Σ-reference, sensor bias `b` | **Outside-input measurement** (1×) after CHAR‑1 | Operator ruler |
| **TBD‑02** | Max ground speed, `vMax` | mm/s | SYS‑1 confirm, σ_run sampling term, reporting | CHAR‑1 approach-slope of distance(t) | Forward sensor |
| **TBD‑03** | Sensor refresh interval, `refreshInterval` | s | CMP‑RNG‑1, σ_run sampling term | CHAR‑1 reading-step cadence | Forward sensor |
| **TBD‑04** | Sensor noise std, `σ_meas` | mm | designMargin | CHAR‑1 stationary window (motors off) | Forward sensor |
| **TBD‑05** | Stopping distance @ vMax, `Σ` | mm | FUN‑5, CMP‑MOT‑2, threshold | CHAR‑1: `d_trigger_char − reported_final` (reported ref); true ref via TBD‑01 | Forward sensor (+IMU accel) |
| **TBD‑06** | Braking variability, `σ_brake` | mm | designMargin (σ_run) | CHAR‑1 decel-profile cleanliness (bounded), tested at verification run | Forward sensor / IMU accel |
| **TBD‑07** | Heading drift over approach, `yawDrift` | rad | SYS‑4 / CMP‑IMU‑1 | CHAR‑1 IMU yaw at trigger | IMU |
| **TBD‑08** | Forward-sensor disagreement | mm | CMP‑RNG‑2 | CHAR‑1 (both sensors logged) | Forward sensors |
| **TBD‑09** | Motor `maxSpeed` (rad/s) | rad/s | CMP‑MOT‑1 | CHAR‑1 (commanded vs. clamped speed) | Motor |
| **TBD‑10** | Min reliable sensor range, `d_min` | mm | Feasibility floor on threshold | CHAR‑1 (lowest clean reading) | Forward sensor |

**Design constants** (set with rationale, not "unknowns," but listed for completeness):
`contactMargin ≈ 0` (hard no-contact floor); `stopTolerance` ≈ small speed≈0 band; `maxStaleness`
from loop design; `yawMax` from geometry (lateral error over 1000 mm tolerable); `agreementTol`
from sensor spec; `k` assurance factor (target **k = 3**, justified in the plan, revisited once σ's are known).

---

## 11. Requirement tree (Mermaid)

```mermaid
flowchart TD
    %% Stakeholder
    STK1["STK-1\nstop as close as possible\n(objective)"]
    STK2["STK-2\nnever contact wall\n(constraint)"]
    STK3["STK-3\nmaximum speed\n(constraint)"]

    %% System
    SYS1["SYS-1\ncommand drivetrain at max"]
    SYS2["SYS-2\nno wall contact (gap>0)"]
    SYS3["SYS-3\nminimise final clearance"]
    SYS4["SYS-4 (derived)\nbounded heading drift"]
    SYS5["SYS-5 (derived bridge)\nclearance >= designMargin"]
    SYS6["SYS-6\ncomplete stop"]

    %% Function
    FUN1["FUN-1\nmeasure fwd distance,\nbounded staleness"]
    FUN2["FUN-2 (derived)\ncross-source 2 sensors,\nnearer-of-two"]
    FUN3["FUN-3\nboth motors at max"]
    FUN4["FUN-4\nstop-trigger control law"]
    FUN5["FUN-5\nbrake within Sigma"]
    FUN6["FUN-6\nheading hold via IMU"]

    %% Component (single-effector leaves)
    CM1["CMP-MOT-1\ncommanded >= maxSpeed"]
    CM2["CMP-MOT-2\nstopping dist <= budget"]
    CR1["CMP-RNG-1\nrefresh <= maxStaleness"]
    CR2["CMP-RNG-2\nsensors agree <= tol"]
    CI1["CMP-IMU-1\nyaw drift <= yawMax"]

    %% Effectors
    M1(["Drive motor A"])
    M2(["Drive motor B"])
    R1(["Fwd sensor #1"])
    R2(["Fwd sensor #2"])
    IMU(["IMU yaw"])
    DROP1{{"Rear sensor — DROP\n(no requirement)"}}
    DROP2{{"Color sensor — DROP\n(no requirement)"}}

    STK3 --> SYS1
    STK2 --> SYS2
    STK1 --> SYS3
    STK1 --> SYS5
    STK2 --> SYS5
    SYS2 --> SYS5
    STK1 --> SYS4
    STK2 --> SYS4
    STK1 --> SYS6

    SYS1 --> FUN3
    SYS2 --> FUN1
    SYS2 --> FUN2
    SYS2 --> FUN4
    SYS5 --> FUN4
    SYS6 --> FUN4
    SYS5 --> FUN5
    SYS6 --> FUN5
    SYS4 --> FUN6

    FUN3 --> CM1
    FUN4 --> CM2
    FUN5 --> CM2
    FUN1 --> CR1
    FUN2 --> CR2
    FUN6 --> CI1

    CM1 --> M1
    CM1 --> M2
    CM2 --> M1
    CM2 --> M2
    CR1 --> R1
    CR1 --> R2
    CR2 --> R1
    CR2 --> R2
    CI1 --> IMU

    DROP1 -.x.- R2
    DROP2 -.x.- IMU
```

---

## 12. Verification sequencing note (Tenet A5/C1)

Requirements are verified **most-directly-observable first**, components before integration:

1. **Forward distance channel** (CMP‑RNG‑1/2) — most directly observable, least coupled (B2 trusted-reference-first).
2. **Speed `vMax`** (SYS‑1/CMP‑MOT‑1) — read off the same distance trace's slope.
3. **Heading** (CMP‑IMU‑1) — independent IMU channel, logged on the same run.
4. **Stopping distance `Σ`** (CMP‑MOT‑2/FUN‑5) — depends on (1) and (2); measured at the single max-speed operating point.
5. **Sensor bias `b`** — needs the one outside-input anchor; bootstrapped off (1).
6. **Integrated clearance** (SYS‑2/5) — composed analytically from 1–5 **before** any integrated run (the Pre-Verification artifact), then tested once at the verification run.

All of 1–4, 7, 8 are batched into **one** characterization program (CHAR‑1) per Tenet B3.
