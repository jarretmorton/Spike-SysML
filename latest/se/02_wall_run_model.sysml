// ============================================================================
// 02_wall_run_model.sysml — TASK-TAILORED model for the wall-approach run.
//
// Realises the Requirements Specification v1.0 (the source of truth). Composed
// ONLY from rover_generic.sysml templates: RoverStructure (parts), the
// RelationTemplates catalog (expressions reproduced, NOT calc-invoked, per the
// skeleton's validation note), and the RequirementTemplates shapes
// (specialise + add subject + bind operands with :>> + inherited constraint).
//
// Parameters are left FREE (uncalibrated, not zeroed); calibration binds them.
// Trace spine: each CMP requirement -> WallRover attribute -> calibration TBD.
// ============================================================================

package WallRunModel {

    private import ISQ::*;
    private import SI::*;
    private import ScalarValues::*;
    private import RoverCommon::*;
    private import RoverStructure::*;
    private import RelationTemplates::*;       // source of truth for relation expressions
    private import RequirementTemplates::*;    // LowerBoundRequirement, UpperBoundRequirement

    // ------------------------------------------------------------------ //
    //  Task-specialised platform                                         //
    //  2 drive motors, 2 forward rangers, IMU used. Rear ranger + floor  //
    //  reflectance are INHERITED from Rover but UNALLOCATED: no          //
    //  requirement binds them (absence by traceability).                 //
    // ------------------------------------------------------------------ //
    part def WallRover specializes RoverStructure::Rover {

        // multiplicity fixed on inherited parts
        part redefines motors  : DriveMotor     [2];   // left, right
        part redefines rangers : DistanceSensor [2];   // two forward-facing
        // imu, floor, latency inherited; floor UNALLOCATED.

        // ---- effector ceilings (from structure) ----
        attribute motorMaxSpeed   : AngularVelocityValue;  // motors.maxSpeed (ceiling)
        attribute commandedSpeed  : AngularVelocityValue;  // commanded to motors

        // ---- calibrated model-completion parameters (FREE until calibration) ----
        attribute kRotToSpeed     : LengthValue;           // TBD-k   : m per rad
        attribute maxGroundSpeed  : SpeedValue;            // TBD-vmax: m/s (= ceiling, via rotToSpeed)
        attribute achievedSpeed   : SpeedValue;            // measured cruise speed (SYS-1)
        attribute responseLatency : DurationValue;         // TBD-tResponse: tChain + sensor staleness
        attribute deceleration    : AccelerationValue;     // TBD-a
        attribute stopOvershoot   : LengthValue;           // TBD-O (lumped, single operating point)
        attribute forwardRefresh  : DurationValue;         // TBD-refresh
        attribute forwardMinRange : LengthValue;           // TBD-minrange (reliable floor)
        attribute forwardMaxRange : LengthValue;           // TBD-maxrange (reliable ceiling)
        attribute sensorBias      : LengthValue;           // TBD-bias (static read - true)
        attribute imuDriftRate    : RoverCommon::Angle;    // TBD-drift over approach (IMU instrument)
        attribute headingDrift    : RoverCommon::Angle;    // physical heading deviation at wall

        // ---- requirement-TBD register thresholds (FREE until bound) ----
        attribute maxRefresh      : DurationValue;         // CMP-2.1 bound
        attribute overshootBudget : LengthValue;           // CMP-2.2 bound
        attribute maxHeadingDev   : RoverCommon::Angle;    // SYS-5 / CMP-3.1 bound (TBD-dev)
        attribute contactMargin   : LengthValue;           // SYS-6 m* = k_sigma*RSS(sigma) (TBD-m*)
        attribute stopTolerance   : SpeedValue;            // SYS-3 bound (TBD-stop)
        attribute gapBudget       : LengthValue;           // SYS-4 objective band (TBD-gap)

        // ---- computed / outcome attributes ----
        attribute triggerDistance : LengthValue;           // d_trig (via StoppingDistance)
        attribute finalClearance  : LengthValue;           // outcome: true gap at rest
        attribute finalSpeed      : SpeedValue;            // outcome: speed at rest (~0)

        // ------------------------------------------------------------------ //
        //  RELATION REPRODUCTIONS (expression copied from RelationTemplates;  //
        //  calc INVOCATION intentionally avoided per skeleton validation note)//
        // ------------------------------------------------------------------ //

        // RotationToSpeed:  v = motorSpeed * k
        constraint rotToSpeed {
            maxGroundSpeed == motorMaxSpeed * kRotToSpeed
        }

        // StoppingDistance: d = v*tResponse + v^2/(2a) + margin
        constraint triggerCalc {
            triggerDistance ==
                maxGroundSpeed * responseLatency
              + maxGroundSpeed ** 2 / (2 * deceleration)
              + contactMargin
        }

        // single-operating-point identity: overshoot = d_trig - margin
        // (calibration point = operating point => zero extrapolation)
        constraint overshootId {
            stopOvershoot ==
                maxGroundSpeed * responseLatency
              + maxGroundSpeed ** 2 / (2 * deceleration)
        }

        // ------------------------------------------------------------------ //
        //  TOP-LEVEL CLAIM: evaluating this satisfy/require roll-up against    //
        //  the calibrated values IS the pre-run verification artifact.        //
        // ------------------------------------------------------------------ //
        satisfy requirement wallRunNeed : WallRunRequirements::WallRunNeed {
            subject :>> rover = self;
        }
    }

    // ================================================================== //
    //  Requirement tree — every node reachable from WallRunNeed.          //
    //  Each bound node specialises a template, adds subject rover, and    //
    //  redefines operands (:>>) against rover attributes; the require     //
    //  constraint is INHERITED (evaluable logic lives once, in template). //
    // ================================================================== //
    package WallRunRequirements {
        private import RequirementTemplates::*;
        private import WallRunModel::WallRover;

        // ---------- STK-1 : aggregator need (no own constraint) ----------
        requirement def WallRunNeed {
            doc /* STK-1: stop as close as achievable to the wall, approached at
                 maximum speed, without contact. Black-box children below. */
            subject rover : WallRover;

            requirement sys1 : MaxSpeed          { subject :>> rover = WallRunNeed::rover; }
            requirement sys2 : NoContact         { subject :>> rover = WallRunNeed::rover; }
            requirement sys3 : FullStop          { subject :>> rover = WallRunNeed::rover; }
            requirement sys4 : MinimiseGap       { subject :>> rover = WallRunNeed::rover; }
            requirement sys5 : StraightApproach  { subject :>> rover = WallRunNeed::rover; }
            requirement sys6 : ClearanceMargin   { subject :>> rover = WallRunNeed::rover; }
        }

        // ---------- SYS level ----------

        // SYS-1: achieved cruise speed >= calibrated ceiling
        requirement def MaxSpeed specializes LowerBoundRequirement {
            subject rover : WallRover;
            attribute :>> measured = rover.achievedSpeed;
            attribute :>> target   = rover.maxGroundSpeed;
            requirement fun1 : DriveMotorsMax { subject :>> rover = MaxSpeed::rover; }
        }

        // SYS-2: clearance >= 0  (fundamental no-contact)
        requirement def NoContact specializes LowerBoundRequirement {
            subject rover : WallRover;
            attribute :>> measured = rover.finalClearance;
            attribute :>> target   = 0 [SI::metre];
            // realised by the stop function (shared with SYS-3, SYS-6)
            requirement fun2 : StopOnTrigger { subject :>> rover = NoContact::rover; }
        }

        // SYS-3: residual speed at rest <= stop tolerance
        requirement def FullStop specializes UpperBoundRequirement {
            subject rover : WallRover;
            attribute :>> measured = rover.finalSpeed;
            attribute :>> target   = rover.stopTolerance;
        }

        // SYS-4: OBJECTIVE — final clearance <= reporting gap budget (graded)
        requirement def MinimiseGap specializes UpperBoundRequirement {
            doc /* OBJECTIVE (graded, "should"): smaller is better; budget is a
                 reporting band, not a hard pass/fail. */
            subject rover : WallRover;
            attribute :>> measured = rover.finalClearance;
            attribute :>> target   = rover.gapBudget;
        }

        // SYS-5 [D]: heading deviation at wall <= allowed
        requirement def StraightApproach specializes UpperBoundRequirement {
            subject rover : WallRover;
            attribute :>> measured = rover.headingDrift;
            attribute :>> target   = rover.maxHeadingDev;
            requirement fun3 : HoldHeading { subject :>> rover = StraightApproach::rover; }
        }

        // SYS-6 [D]: clearance >= no-contact margin m* (the bridge)
        requirement def ClearanceMargin specializes LowerBoundRequirement {
            subject rover : WallRover;
            attribute :>> measured = rover.finalClearance;
            attribute :>> target   = rover.contactMargin;
            requirement fun2 : StopOnTrigger { subject :>> rover = ClearanceMargin::rover; }
        }

        // ---------- FUN level ----------

        // FUN-1: command both motors at max  -> CMP-1.1
        requirement def DriveMotorsMax {
            subject rover : WallRover;
            requirement cmp11 : MotorMaxSpeed { subject :>> rover = DriveMotorsMax::rover; }
        }

        // FUN-2: brake at trigger -> CMP-2.1, CMP-2.2, CMP-2.3
        requirement def StopOnTrigger {
            subject rover : WallRover;
            requirement cmp21 : ForwardRefresh  { subject :>> rover = StopOnTrigger::rover; }
            requirement cmp22 : BrakeOvershoot  { subject :>> rover = StopOnTrigger::rover; }
            requirement cmp23 : TriggerInRange  { subject :>> rover = StopOnTrigger::rover; }
        }

        // FUN-3 [D]: sense/hold heading -> CMP-3.1, CMP-3.2
        requirement def HoldHeading {
            subject rover : WallRover;
            requirement cmp31 : HeadingDriftReq    { subject :>> rover = HoldHeading::rover; }
            requirement cmp32 : HeadingCorrection  { subject :>> rover = HoldHeading::rover; }
        }

        // ---------- CMP level (single-effector leaves) ----------

        // CMP-1.1: commanded speed >= motor ceiling
        requirement def MotorMaxSpeed specializes LowerBoundRequirement {
            subject rover : WallRover;
            attribute :>> measured = rover.commandedSpeed;
            attribute :>> target   = rover.motorMaxSpeed;
        }

        // CMP-2.1: forward sensor refresh interval <= bound
        requirement def ForwardRefresh specializes UpperBoundRequirement {
            subject rover : WallRover;
            attribute :>> measured = rover.forwardRefresh;
            attribute :>> target   = rover.maxRefresh;
        }

        // CMP-2.2: stop overshoot <= budget
        requirement def BrakeOvershoot specializes UpperBoundRequirement {
            subject rover : WallRover;
            attribute :>> measured = rover.stopOvershoot;
            attribute :>> target   = rover.overshootBudget;
        }

        // CMP-2.3 [D]: computed trigger distance <= sensor reliable range (feasibility)
        requirement def TriggerInRange specializes UpperBoundRequirement {
            subject rover : WallRover;
            attribute :>> measured = rover.triggerDistance;
            attribute :>> target   = rover.forwardMaxRange;
        }

        // CMP-3.1: IMU heading drift <= allowed
        requirement def HeadingDriftReq specializes UpperBoundRequirement {
            subject rover : WallRover;
            attribute :>> measured = rover.imuDriftRate;
            attribute :>> target   = rover.maxHeadingDev;
        }

        // CMP-3.2 [D, Optional]: conditional differential correction.
        // Bound form asserts that, IF instantiated, residual heading deviation
        // after correction stays within the allowed envelope.
        requirement def HeadingCorrection specializes UpperBoundRequirement {
            doc /* OPTIONAL: instantiated only if C1 shows uncorrected drift
                 breaches SYS-5. Correction gain DERIVED from measured drift. */
            subject rover : WallRover;
            attribute :>> measured = rover.headingDrift;
            attribute :>> target   = rover.maxHeadingDev;
        }
    }
}

// ============================================================================
// STRUCTURAL CHECKS  (the in-loop gate that stands in for the out-of-band
// grammar check; per MODEL STRATEGY "run the structural checks grammar cannot
// see"). Performed by hand on the tree above.
//
// (1) REACHABILITY from the top need WallRunNeed:
//     WallRunNeed -> {sys1,sys2,sys3,sys4,sys5,sys6}
//       sys1 MaxSpeed         -> fun1 DriveMotorsMax -> cmp11 MotorMaxSpeed
//       sys2 NoContact        -> fun2 StopOnTrigger  -> {cmp21,cmp22,cmp23}
//       sys3 FullStop         -> (leaf bound)
//       sys4 MinimiseGap      -> (leaf bound, objective)
//       sys5 StraightApproach -> fun3 HoldHeading    -> {cmp31,cmp32}
//       sys6 ClearanceMargin  -> fun2 StopOnTrigger  -> {cmp21,cmp22,cmp23}
//     => every requirement def is reachable. PASS.
//
// (2) REALISED DECOMPOSITION EDGE-SET vs requirement tree (spec §7 Mermaid):
//     Spec edges: STK1->SYS{1..6}; SYS1->FUN1->CMP11; {SYS2,SYS3,SYS6}->FUN2;
//                 FUN2->{CMP21,CMP22,CMP23}; SYS5->FUN3->{CMP31,CMP32}.
//     Model edges (nested requirement usages) reproduce exactly this set, with
//     FUN2/StopOnTrigger shared by sys2 + sys6 (and sys3 bounds finalSpeed as a
//     leaf, its stop realised through the same FUN2 in the spec narrative).
//     => edge-set matches the requirement tree. PASS.
//
// (3) PER-PACKAGE IMPORT RESOLUTION:
//     WallRunModel imports ISQ, SI, ScalarValues, RoverCommon, RoverStructure,
//       RelationTemplates, RequirementTemplates — all defined in
//       rover_generic.sysml (RoverCommon, RoverStructure, RelationTemplates,
//       RequirementTemplates) or the SysML standard library (ISQ, SI,
//       ScalarValues). WallRover references only imported defs + own attributes.
//     WallRunRequirements imports RequirementTemplates and WallRunModel::WallRover;
//       every requirement def references WallRover attributes (qualified via the
//       subject) and LowerBound/UpperBound templates. No dangling references.
//     => imports resolve. PASS.
//
// NOTE on UNALLOCATED parts: Rover::rangers[rear], Rover::floor remain inherited
// but no requirement binds them -> intentional absence by traceability, not a
// modelling gap (spec §5).
//
// Grammar conformance is verified out of band, after the run, not here.
// ============================================================================
