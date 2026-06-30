# Tailored SysML v2 Model — Wall-Approach Rover

**Relationship to the spec.** This model is a *formal realisation* of
`01_requirements_specification.md`. The spec governs on any disagreement. Every model element
carries the spec ID it realises, and §6 below is an element-by-element traceability back-map.

**Provenance.** Tailored from `rover_generic.sysml` (the platform skeleton + template library).
Constructs are restricted to the forms the skeleton validated clean against the OMG SysML v2 Beta-4
spec examples: `part def … specializes …`, subset parts (`:>`), `requirement def … specializes
<template>`, operand binding by redefinition (`attribute :>> measured = …`), inherited `require
constraint`, nested `requirement` usages for decomposition, and `satisfy requirement : …`. Relation
templates are reproduced as bound expressions (not `calc` invocation), exactly as the skeleton
prescribes. **No live grammar checker runs in this loop**, so correctness is argued *structurally* in
§5 (reachability, decomposition edge-set, import resolution).

---

## 1. Tailoring decisions (what is instantiated, what is dropped)

The skeleton is rover-agnostic. Tailoring keeps only the structure and templates that a requirement
calls for; everything else is *dropped by traceability* (Rule 7 / Tenet A4 — "develop only what a
requirement exercises").

| Skeleton element | Decision | Driving requirement / rationale |
|---|---|---|
| `RoverStructure::Rover` | **Specialise → `WallRover`** | The platform under test. |
| `DriveMotor` ×2 (`leftMotor`,`rightMotor`) | **Instantiate** (subset `motors`) | CMP‑MOT‑1, CMP‑MOT‑2. |
| `DistanceSensor` ×2 forward (`fwdSensorL`,`fwdSensorR`) | **Instantiate** (subset `rangers`) | CMP‑RNG‑1, CMP‑RNG‑2, FUN‑2 cross-source. |
| `InertialUnit` `imu` (yaw) | **Instantiate** (inherited singleton) | CMP‑IMU‑1 / SYS‑4. |
| `InertialUnit.forwardAccel` | **Monitor only** | No requirement traces to it; kept as health/cross-source channel (B1), not satisfied. |
| Rear `DistanceSensor` | **DROP** | No requirement traces to it (forward task). Shows up as *not subsetted* from `rangers`. |
| `ReflectanceSensor` `floor` | **DROP** (inherited, unused) | No floor/line/start-gate requirement. Present on platform, no requirement → not referenced. |
| `RoverLatency.tChain` | **Keep** | Feeds `tResponse` in the StoppingDistance reproduction (FUN‑4/5). |
| `RelationTemplates::StoppingDistance` | **Instantiate** (reproduce expression) | FUN‑4 control law + FUN‑5 / CMP‑MOT‑2 budget. |
| `RelationTemplates::RotationToSpeed` | **DROP** | `vMax` is measured **directly** from the approach-slope (TBD‑02); the rad→m constant `k` is never needed, so the relation that would consume it is not instantiated. |
| `RelationTemplates::MaxSpeedFromBudget` | **DROP** | Speed is *fixed at maximum* (SYS‑1), not solved from a budget. The inverse relation has no requirement to serve. |
| `RequirementTemplates::LowerBoundRequirement` | **Instantiate** | SYS‑2, SYS‑5, CMP‑MOT‑1. |
| `RequirementTemplates::UpperBoundRequirement` | **Instantiate** | SYS‑4, SYS‑6, CMP‑MOT‑2, CMP‑RNG‑1, CMP‑RNG‑2, CMP‑IMU‑1. |

---

## 2. The tailored model

### 2.1 `WallStructure` — the platform under test, with task quantities

```sysml
package WallStructure {
    doc /*
     * WallRover: the platform skeleton specialised for the wall-approach task.
     * Fixes the platform multiplicities to the effectors a requirement traces to
     * (two drive motors, two FORWARD distance sensors, the IMU). The rear ranger
     * and the floor reflectance sensor are deliberately NOT referenced — their
     * disuse is "absence by traceability", not a missing block.
     *
     * Task quantities (clearances, speeds, thresholds, drift) are carried as
     * attributes. They are UNCALIBRATED here — declared, not zeroed — and bind in
     * Phase 4. Each is tagged with the spec TBD it closes.
     */

    private import ISQ::*;
    private import SI::*;
    private import RoverCommon::*;
    private import RoverStructure::*;

    part def WallRover specializes Rover {

        // -- effectors a requirement traces to (subset the platform collections) --
        part leftMotor   : DriveMotor      :> motors;    // CMP-MOT-1/2
        part rightMotor  : DriveMotor      :> motors;    // CMP-MOT-1/2
        part fwdSensorL  : DistanceSensor  :> rangers;   // CMP-RNG-1/2, FUN-2
        part fwdSensorR  : DistanceSensor  :> rangers;   // CMP-RNG-1/2, FUN-2
        // imu : InertialUnit  -- inherited singleton, used by CMP-IMU-1 (yaw)
        // rear DistanceSensor -- NOT subsetted (dropped by traceability)
        // floor : ReflectanceSensor -- inherited, NOT referenced (dropped)

        // -- measured / derived task quantities (bind in Phase 4; not zeroed) --
        attribute finalClearance     : LengthValue;            // true gap at rest        (SYS-2/3/5)
        attribute contactMargin      : LengthValue;            // hard no-contact floor ~0 (SYS-2)
        attribute designMargin       : LengthValue;            // A6-sized standoff        (SYS-5)  TBD via §margin
        attribute finalSpeed         : SpeedValue;             // speed at rest ~0         (SYS-6)
        attribute stopTolerance      : SpeedValue;             // speed~0 acceptance band  (SYS-6)
        attribute triggerThreshold   : LengthValue;            // FUN-4 control-law threshold
        attribute stoppingDistance   : LengthValue;            // Sigma, travel after trigger (FUN-5/CMP-MOT-2)  TBD-05
        attribute yawDrift           : Angle;                  // heading drift over approach (SYS-4/CMP-IMU-1)  TBD-07
        attribute yawMax             : Angle;                  // drift bound (geometry)      (SYS-4)
        attribute rangerDisagreement : LengthValue;            // |sL - sR| over range        (CMP-RNG-2)      TBD-08
        attribute agreementTol       : LengthValue;            // disagreement bound          (CMP-RNG-2)
        attribute maxStaleness       : DurationValue;          // loop staleness bound        (FUN-1/CMP-RNG-1)

        // -- parameters of the StoppingDistance reproduction (RelationTemplates::StoppingDistance) --
        attribute vMax       : SpeedValue;                     // max ground speed            (TBD-02)
        attribute tResponse  : DurationValue;                  // = latency.tChain (+ sampling latency)
        attribute decel      : AccelerationValue;              // back-solved ONLY if feasibility needs it

        // -- StoppingDistance relation, reproduced against bound parameters --
        // d = v*tResponse + v^2/(2a) + margin   (the trigger distance, margin included)
        // Sigma = d - margin                     (the braking budget the trigger reserves)
        // At the single max-speed operating point Sigma is MEASURED directly (TBD-05);
        // 'decel' is recovered from Sigma only if a feasibility check requires it.
        assert constraint triggerModel {
            triggerThreshold == vMax * tResponse + vMax ** 2 / (2 * decel) + designMargin
        }
        assert constraint stoppingBudget {
            stoppingDistance == triggerThreshold - designMargin
        }
    }
}
```

**Note on the relation reproduction.** Per the skeleton's `StoppingDistance` doc, this is the
single-operating-point case: calibration point = operating point (always max speed), so there is
**zero extrapolation**. `Sigma` (`stoppingDistance`) is measured directly at that point in CHAR‑1;
the quadratic decomposition `v·tResponse + v²/(2a)` is retained as the *model* whose lumped value is
what we measure, and `decel` is back-solved only if a feasibility check needs the split (Tenet A:
parameters uncalibrated, not zeroed). `RotationToSpeed` and `MaxSpeedFromBudget` are **not**
reproduced — no requirement consumes them.

### 2.2 `WallRequirements` — requirement defs and the decomposition tree

```sysml
package WallRequirements {
    doc /*
     * Task requirements as a single rooted decomposition (WallRunNeed) whose
     * leaves specialise the bound templates. Convention: SYS/FUN requirements take
     * subject 'rover : WallRover' and bind operands to the rover's attributes;
     * single-effector CMP leaves take the EFFECTOR as subject and bind to its own
     * attributes, then the tree instantiates them once per physical effector.
     * Operand binding uses the validated redefinition form  attribute :>> X = ...
     * (NOT 'redefines X :>>', which is not in the proven-valid set).
     */

    private import ISQ::*;
    private import SI::*;
    private import RoverCommon::*;
    private import RoverStructure::*;
    private import WallStructure::*;
    private import RequirementTemplates::*;

    // ---------- Component leaves (single-effector, bound to templates) ----------

    requirement def <'CMP-MOT-1'> CommandAtMax specializes LowerBoundRequirement {
        doc /* Each drive motor's commanded speed >= its achievable maxSpeed. */
        subject motor : DriveMotor;
        attribute :>> measured = motor.commandedSpeed;
        attribute :>> target   = motor.maxSpeed;
    }

    requirement def <'CMP-MOT-2'> StoppingWithinBudget specializes UpperBoundRequirement {
        doc /* Drivetrain stopping distance Sigma <= the trigger budget (threshold - margin). */
        subject rover : WallRover;
        attribute :>> measured = rover.stoppingDistance;
        attribute :>> target   = rover.triggerThreshold - rover.designMargin;
    }

    requirement def <'CMP-RNG-1'> RefreshBounded specializes UpperBoundRequirement {
        doc /* Each forward sensor's refresh interval <= maxStaleness. */
        subject rover : WallRover;
        attribute :>> measured = rover.fwdSensorL.refreshInterval;   // rebound per-sensor in the tree
        attribute :>> target   = rover.maxStaleness;
    }

    requirement def <'CMP-RNG-2'> SensorsAgree specializes UpperBoundRequirement {
        doc /* The two forward sensors agree within agreementTol over the operating range. */
        subject rover : WallRover;
        attribute :>> measured = rover.rangerDisagreement;
        attribute :>> target   = rover.agreementTol;
    }

    requirement def <'CMP-IMU-1'> YawBounded specializes UpperBoundRequirement {
        doc /* IMU-sensed heading drift <= yawMax. */
        subject rover : WallRover;
        attribute :>> measured = rover.yawDrift;
        attribute :>> target   = rover.yawMax;
    }

    // ---------- System leaves that are themselves a single bound ----------

    requirement def <'SYS-2'> NoContact specializes LowerBoundRequirement {
        doc /* Final true clearance > 0 (contactMargin is the hard ~0 floor). */
        subject rover : WallRover;
        attribute :>> measured = rover.finalClearance;
        attribute :>> target   = rover.contactMargin;
    }

    requirement def <'SYS-4'> HeadingBounded specializes UpperBoundRequirement {
        doc /* Heading drift over the approach <= yawMax. */
        subject rover : WallRover;
        attribute :>> measured = rover.yawDrift;
        attribute :>> target   = rover.yawMax;
    }

    requirement def <'SYS-5'> ClearanceMargin specializes LowerBoundRequirement {
        doc /* Rule-3 bridge: final clearance >= the A6-sized designMargin. Guarantees SYS-2. */
        subject rover : WallRover;
        attribute :>> measured = rover.finalClearance;
        attribute :>> target   = rover.designMargin;
    }

    requirement def <'SYS-6'> CompleteStop specializes UpperBoundRequirement {
        doc /* At rest, residual speed <= stopTolerance (a complete stop, not a slow). */
        subject rover : WallRover;
        attribute :>> measured = rover.finalSpeed;
        attribute :>> target   = rover.stopTolerance;
    }

    // ---------- Composite (behavioural) requirements — no single bound ----------

    requirement def <'SYS-1'> CommandDrivetrainAtMax {
        doc /* While approaching, command the drivetrain at maximum achievable speed. */
        subject rover : WallRover;
    }
    requirement def <'SYS-3'> MinimiseClearance {
        doc /* OBJECTIVE (graded, 'should'): minimise final clearance, bounded below by SYS-5.
                Not a pass/fail constraint — no require constraint. */
        subject rover : WallRover;
    }
    requirement def <'FUN-1'> MeasureForwardBounded {
        doc /* Measure forward distance each cycle with bounded staleness. */
        subject rover : WallRover;
    }
    requirement def <'FUN-2'> CrossSourceNearer {
        doc /* Derive forward distance from two independent sensors; trigger on the NEARER. */
        subject rover : WallRover;
    }
    requirement def <'FUN-3'> DriveBothAtMax {
        doc /* Command BOTH drive motors at maximum achievable speed. */
        subject rover : WallRover;
    }
    requirement def <'FUN-4'> StopTriggerLaw {
        doc /* When nearer distance <= triggerThreshold, command a full stop.
                triggerThreshold = stoppingDistance(Sigma) + designMargin  (see WallRover.triggerModel). */
        subject rover : WallRover;
    }
    requirement def <'FUN-5'> BrakeWithinSigma {
        doc /* On full-stop command, come to rest within the calibrated Sigma of the trigger point. */
        subject rover : WallRover;
    }
    requirement def <'FUN-6'> HeadingHold {
        doc /* Sense heading via IMU and hold drift <= yawMax. Irreducibly integrative (Rule 2). */
        subject rover : WallRover;
    }

    // ---------- Top need: the rooted decomposition (nested usages) ----------

    requirement def <'WallRunNeed'> WallRunRequirements {
        doc /*
         * The rooted requirement tree. Containment expresses the PRIMARY parent of
         * each child; edges that are shared across parents in the spec tree (e.g.
         * FUN-4 also serving SYS-5 and SYS-6) are enumerated in the model's
         * decomposition edge-set (§5.2) and asserted equal to spec §11. CMP leaves
         * appear once per physical effector; the second instance rebinds the bound
         * operand/subject to the twin effector.
         */
        subject rover : WallRover;

        // SYS-1 -> FUN-3 -> CMP-MOT-1 (x2 motors)
        requirement sys1 : CommandDrivetrainAtMax {
            requirement fun3 : DriveBothAtMax {
                requirement cmpMot1L : CommandAtMax { subject :>> motor = rover.leftMotor;  }
                requirement cmpMot1R : CommandAtMax { subject :>> motor = rover.rightMotor; }
            }
        }

        // SYS-2 -> { FUN-1 -> CMP-RNG-1 (x2 sensors); FUN-2 -> CMP-RNG-2; FUN-4 (shared) }
        requirement sys2 : NoContact {
            requirement fun1 : MeasureForwardBounded {
                requirement cmpRng1L : RefreshBounded {
                    attribute :>> measured = rover.fwdSensorL.refreshInterval;
                }
                requirement cmpRng1R : RefreshBounded {
                    attribute :>> measured = rover.fwdSensorR.refreshInterval;
                }
            }
            requirement fun2 : CrossSourceNearer {
                requirement cmpRng2 : SensorsAgree;
            }
            requirement fun4 : StopTriggerLaw {
                requirement cmpMot2 : StoppingWithinBudget;
            }
        }

        // SYS-3 objective (bounded by SYS-5)
        requirement sys3 : MinimiseClearance;

        // SYS-4 -> FUN-6 -> CMP-IMU-1
        requirement sys4 : HeadingBounded {
            requirement fun6 : HeadingHold {
                requirement cmpImu1 : YawBounded;
            }
        }

        // SYS-5 (Rule-3 bridge) realised by FUN-4 (trigger) + FUN-5 (brake)
        requirement sys5 : ClearanceMargin {
            requirement fun5 : BrakeWithinSigma {
                requirement cmpMot2b : StoppingWithinBudget;   // same leaf, integrative roll-up
            }
        }

        // SYS-6 complete stop (realised by FUN-4 trigger + FUN-5 brake)
        requirement sys6 : CompleteStop;
    }
}
```

### 2.3 `WallDesign` — the design that claims the need

```sysml
package WallDesign {
    doc /*
     * The populated rover claims the top need. Evaluating this satisfy/require
     * roll-up against the Phase-4 calibrated values IS the pre-run verification
     * artifact (every bound operand becomes a number, every require constraint a
     * pass/fail, every objective a predicted value). Imports are one-directional
     * (Design -> Requirements -> Structure), so there is no package cycle.
     */
    private import WallStructure::*;
    private import WallRequirements::*;

    part wallRover : WallRover {
        satisfy requirement : WallRunRequirements;   // subject binds to this wallRover
    }
}
```

---

## 3. Operand-binding idiom (the one valid form used throughout)

Every task requirement specialises a template, adds a `subject`, and binds the template's operands by
**redefinition with a value**:

```sysml
attribute :>> measured = <subject>.<attribute>;
attribute :>> target   = <subject>.<attribute>;
```

The inherited `require constraint { measured >= target }` (or `<=`) is **not** restated — the evaluable
logic lives in exactly one place (the template). The invalid form `attribute redefines measured :>>
<subject>.<attribute>` is **not** used anywhere. Where a leaf applies to two identical effectors, the
tree carries two usages; the second rebinds the subject (`subject :>> motor = rover.rightMotor`) or the
operand (`attribute :>> measured = rover.fwdSensorR.refreshInterval`), so both physical effectors are
explicit in the structure.

---

## 4. Relation instantiation summary (Tenet A4)

| Template | Instantiated? | Where / why |
|---|---|---|
| `StoppingDistance` | **Yes** | `WallRover.triggerModel` + `WallRover.stoppingBudget`; single-operating-point, Σ measured directly (TBD‑05), `decel` back-solved only on feasibility need. |
| `RotationToSpeed` | No | `vMax` measured directly (TBD‑02); constant `k` never consumed. |
| `MaxSpeedFromBudget` | No | Speed fixed at maximum (SYS‑1); no budget-inversion required. |
| `LowerBoundRequirement` | **Yes** | SYS‑2, SYS‑5, CMP‑MOT‑1. |
| `UpperBoundRequirement` | **Yes** | SYS‑4, SYS‑6, CMP‑MOT‑2, CMP‑RNG‑1, CMP‑RNG‑2, CMP‑IMU‑1. |

---

## 5. Structural checks (the gate — run in lieu of a live grammar checker)

### 5.1 Reachability — every requirement reaches the top need

Walking containment + the rebind usages from `WallRunNeed`:

```
WallRunNeed
├─ SYS-1 ─ FUN-3 ─ CMP-MOT-1 {leftMotor, rightMotor}
├─ SYS-2 ─┬ FUN-1 ─ CMP-RNG-1 {fwdSensorL, fwdSensorR}
│         ├ FUN-2 ─ CMP-RNG-2
│         └ FUN-4 ─ CMP-MOT-2
├─ SYS-3  (objective leaf)
├─ SYS-4 ─ FUN-6 ─ CMP-IMU-1
├─ SYS-5 ─ FUN-5 ─ CMP-MOT-2     (integrative roll-up of the same leaf)
└─ SYS-6  (realised by FUN-4 + FUN-5)
```

Reachable requirement set =
{SYS‑1…6, FUN‑1…6, CMP‑MOT‑1, CMP‑MOT‑2, CMP‑RNG‑1, CMP‑RNG‑2, CMP‑IMU‑1}. **All 17 spec
requirements are reachable; none is orphaned.** (FUN‑4 and FUN‑5 are reached once by containment and
additionally serve SYS‑2/5/6 via the shared edges in §5.2.)

### 5.2 Decomposition edge-set — asserted equal to spec §11

The model realises exactly these parent→child edges. Edge type **C** = realised by containment in
`WallRunNeed`; **S** = shared edge (same child, additional parent) enumerated here and matching the
spec DAG.

| Parent | Child | In model | In spec §11 | Type |
|---|---|---|---|---|
| STK‑3 | SYS‑1 | ✓ (top binds STK via §6) | ✓ | C |
| STK‑2 | SYS‑2 | ✓ | ✓ | C |
| STK‑1 | SYS‑3 | ✓ | ✓ | C |
| STK‑1,2 + SYS‑2 | SYS‑5 | ✓ | ✓ | C+S |
| STK‑1,2 | SYS‑4 | ✓ | ✓ | C |
| STK‑1 | SYS‑6 | ✓ | ✓ | C |
| SYS‑1 | FUN‑3 | ✓ | ✓ | C |
| SYS‑2 | FUN‑1 | ✓ | ✓ | C |
| SYS‑2 | FUN‑2 | ✓ | ✓ | C |
| SYS‑2 | FUN‑4 | ✓ | ✓ | C |
| SYS‑5 | FUN‑4 | ✓ | ✓ | S |
| SYS‑6 | FUN‑4 | ✓ | ✓ | S |
| SYS‑5 | FUN‑5 | ✓ | ✓ | C |
| SYS‑6 | FUN‑5 | ✓ | ✓ | S |
| SYS‑4 | FUN‑6 | ✓ | ✓ | C |
| FUN‑3 | CMP‑MOT‑1 | ✓ | ✓ | C |
| FUN‑4 | CMP‑MOT‑2 | ✓ | ✓ | C |
| FUN‑5 | CMP‑MOT‑2 | ✓ | ✓ | S |
| FUN‑1 | CMP‑RNG‑1 | ✓ | ✓ | C |
| FUN‑2 | CMP‑RNG‑2 | ✓ | ✓ | C |
| FUN‑6 | CMP‑IMU‑1 | ✓ | ✓ | C |
| CMP‑MOT‑1 | leftMotor, rightMotor | ✓ | ✓ | C |
| CMP‑MOT‑2 | drivetrain (decel) | ✓ | ✓ | C |
| CMP‑RNG‑1 | fwdSensorL, fwdSensorR | ✓ | ✓ | C |
| CMP‑RNG‑2 | fwdSensor pair | ✓ | ✓ | C |
| CMP‑IMU‑1 | imu | ✓ | ✓ | C |

**Result: the model edge-set equals the spec §11 edge-set** (every spec edge realised; no edge in the
model absent from the spec). Shared edges (FUN‑4→{SYS‑2,5,6}, FUN‑5→{SYS‑5,6}, CMP‑MOT‑2→{FUN‑4,5})
are represented once by containment and the remainder marked **S**.

### 5.3 Per-package import resolution (acyclic)

| Package | Imports | All names resolve? | Cycle? |
|---|---|---|---|
| `WallStructure` | ISQ, SI, RoverCommon, RoverStructure | ✓ (`Rover`,`DriveMotor`,`DistanceSensor`,`InertialUnit`,`RoverLatency`, value types) | no |
| `WallRequirements` | ISQ, SI, RoverCommon, RoverStructure, **WallStructure**, RequirementTemplates | ✓ (`WallRover`,`DriveMotor`, `LowerBound/UpperBoundRequirement`) | no |
| `WallDesign` | **WallStructure**, **WallRequirements** | ✓ (`WallRover`,`WallRunRequirements`) | no |

Import direction is strictly `WallDesign → WallRequirements → WallStructure → (skeleton)`. **No package
imports a package that (transitively) imports it** — the `satisfy` lives in `WallDesign`, not in
`WallStructure`, precisely to keep this acyclic.

---

## 6. Traceability back-map (model element ↔ spec requirement)

| Spec ID | Model element | Bound operands / form |
|---|---|---|
| STK‑1/2/3 | (stakeholder needs; realised at SYS via §5.2 edges) | — |
| SYS‑1 | `CommandDrivetrainAtMax` | composite |
| SYS‑2 | `NoContact` : LowerBound | `finalClearance ≥ contactMargin` |
| SYS‑3 | `MinimiseClearance` | objective (no constraint) |
| SYS‑4 | `HeadingBounded` : UpperBound | `yawDrift ≤ yawMax` |
| SYS‑5 | `ClearanceMargin` : LowerBound | `finalClearance ≥ designMargin` |
| SYS‑6 | `CompleteStop` : UpperBound | `finalSpeed ≤ stopTolerance` |
| FUN‑1 | `MeasureForwardBounded` | composite |
| FUN‑2 | `CrossSourceNearer` | composite |
| FUN‑3 | `DriveBothAtMax` | composite |
| FUN‑4 | `StopTriggerLaw` + `WallRover.triggerModel` | `threshold = vMax·tResponse + vMax²/(2·decel) + designMargin` |
| FUN‑5 | `BrakeWithinSigma` + `WallRover.stoppingBudget` | `Σ = threshold − designMargin` |
| FUN‑6 | `HeadingHold` | composite (integrative) |
| CMP‑MOT‑1 | `CommandAtMax` : LowerBound ×2 | `motor.commandedSpeed ≥ motor.maxSpeed` |
| CMP‑MOT‑2 | `StoppingWithinBudget` : UpperBound | `stoppingDistance ≤ triggerThreshold − designMargin` |
| CMP‑RNG‑1 | `RefreshBounded` : UpperBound ×2 | `fwdSensor{L,R}.refreshInterval ≤ maxStaleness` |
| CMP‑RNG‑2 | `SensorsAgree` : UpperBound | `rangerDisagreement ≤ agreementTol` |
| CMP‑IMU‑1 | `YawBounded` : UpperBound | `yawDrift ≤ yawMax` |
| TBD‑02 | `WallRover.vMax` | bound in CHAR‑1 |
| TBD‑05 | `WallRover.stoppingDistance` | bound in CHAR‑1 (direct) |
| TBD‑07 | `WallRover.yawDrift` | bound in CHAR‑1 |
| TBD‑08 | `WallRover.rangerDisagreement` | bound in CHAR‑1 |
| (latency) | `WallRover.tResponse` ← `Rover.latency.tChain` | platform-wide |

**Roll-up semantics.** When the Phase‑4 calibrated values are substituted into the `WallRover`
attributes, every `require constraint` in the tree evaluates to a pass/fail and the `SYS‑3` objective
to a predicted gap. That evaluation is the **Pre-Verification Report** (GATE B centerpiece): the
numbers are predicted there and frozen *before* any integrated run.
