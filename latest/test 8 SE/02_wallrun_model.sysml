// ============================================================================
// wallrun_model.sysml — task model TAILORED from rover_generic.sysml.
//
// Realises the Requirements Specification (source of truth). Composes ONLY the
// skeleton templates the requirements call for; invents no structure and no
// notation. Parameters are declared UNCALIBRATED (no eyeballed constants, tenet
// A3) — calibration binds them; the executable Python model carries the
// arithmetic; the two are two views of one model.
//
// Instantiation rule (per rover_generic validation note): relations are applied
// by REPRODUCING their expression against bound parameters (derived-attribute
// form), not by calc INVOCATION. The RelationTemplates calc defs remain the
// single source of truth for those expressions.
// ============================================================================

package WallRunModel {
    private import ISQ::*;
    private import SI::*;
    private import ScalarValues::*;
    private import RoverCommon::*;
    private import RoverStructure::*;
    private import RelationTemplates::*;   // RotationToSpeed, StoppingDistance, MaxSpeedFromBudget

    // ------------------------------------------------------------------------
    // The task rover: specialises the platform, fixes the effector set the
    // requirements trace to, and exposes the parameters + performance quantities.
    // USED effectors carry a requirement; PRESENT-but-unused effectors are kept
    // so their disuse is visible as "no requirement traces to it" (rule 7).
    // ------------------------------------------------------------------------
    part def WallRover specializes Rover {

        // -- effectors (USED) --
        part leftMotor  : DriveMotor;   // CMP-1a, CMP-1c
        part rightMotor : DriveMotor;   // CMP-1b, CMP-1c
        part rangerFwdA : DistanceSensor;   // CMP-2a  (primary distance)
        part rangerFwdB : DistanceSensor;   // CMP-2b  (cross-source distance)
        // imu inherited from Rover : InertialUnit;   // CMP-5 (heading + accel)

        // -- effectors (PRESENT, UNUSED — absence by traceability) --
        part rangerRear : DistanceSensor;   // no requirement -> DROPS OUT
        // floor inherited from Rover : ReflectanceSensor;   // no requirement -> DROPS OUT

        // -- calibrated model parameters (UNCALIBRATED; bound at calibration) --
        attribute vMax           : SpeedValue;            // TBD-1  v_max
        attribute tResponse      : DurationValue;         // TBD-2  t_lat = latency.tChain + sampling
        attribute aBrake         : AccelerationValue;     // TBD-3  a_brake
        attribute sensorOffset   : LengthValue;           // TBD-4  c   (operator-anchored)
        attribute sampleInterval : DurationValue;         // TBD-9  Δt_s
        attribute rangeNoise     : LengthValue;           // TBD-5  σ_S (measured)
        attribute dMin           : LengthValue;           // TBD-6  valid-range floor
        attribute dMax           : LengthValue;           // TBD-6  valid-range ceiling

        // -- design / derived parameters --
        attribute dTrig            : LengthValue;         // sensor-frame trigger threshold (design)
        attribute requiredMargin   : LengthValue;         // TBD-11  M = k · σ_G  (from Python σ-rollup)
        attribute contactMargin    : LengthValue;         // definitional no-contact floor (= 0)
        attribute maxHeadingDrift  : Angle;               // TBD-8  θ_max
        attribute stopSpeedTol     : SpeedValue;          // TBD-12 v_stop_tol
        attribute rangeNoiseMax    : LengthValue;         // TBD-5  σ_S_max
        attribute abTol            : LengthValue;         // TBD-10 Δ_AB tolerance
        attribute estimateErrorTol : LengthValue;         // FUN-4 estimate-error bound

        // -- drivetrain aggregate command vs. ceiling (both motors commanded equally) --
        attribute commandedSpeed : AngularVelocityValue;  // SYS-4 measured
        attribute maxSpeed       : AngularVelocityValue;  // SYS-4 target (ceiling)

        // -- run-realised performance quantities (populated by a run / evaluation) --
        attribute finalClearance    : LengthValue;        // SYS-1  G_final
        attribute headingDrift      : Angle;              // SYS-6  |yaw drift|
        attribute finalSpeed        : SpeedValue;         // SYS-7  v_final
        attribute driveResidualSpeed: SpeedValue;         // CMP-1c residual motor speed at rest
        attribute abAgreement       : LengthValue;        // CMP-2b |A - B|
        attribute estimateError     : LengthValue;        // FUN-4  |G_est - G|

        // -- PREDICTED performance (reproduce RelationTemplates::StoppingDistance
        //    expression against bound parameters; margin term kept separate) --
        //    D_stop = v·tResponse + v²/(2a)   [reaction + braking]
        attribute dStop : LengthValue =
            vMax * tResponse + vMax ** 2 / (2 * aBrake);
        //    predicted final clearance = (sensor trigger, converted to bumper frame) − stop travel
        //    G_pred = (dTrig − c) − D_stop
        attribute predictedClearance : LengthValue =
            (dTrig - sensorOffset) - dStop;

        // The design part claims the top stakeholder need. Evaluating this
        // satisfy/require roll-up against calibrated values IS the pre-run
        // verification artifact.
        satisfy requirement : WallRunRequirements::WallRunNeed;
    }
}

package WallRunRequirements {
    doc /*
     * Formal satisfy/require realisation of the Requirements Specification.
     * Each task requirement SPECIALISES a RequirementTemplates shape, adds the
     * WallRover subject, and BINDS the inherited operands with `:>> measured/target
     * = subject.attr`. The require constraint is inherited (lives in one place).
     * Decomposition is nested `requirement : Child` usages forming a single-parent
     * tree matching the requirement tree (spec §7). Objective/functional-parent
     * requirements carry doc only (graded or realised by their children), and are
     * excluded from the pass/fail roll-up by design.
     */
    private import RequirementTemplates::*;
    private import WallRunModel::*;

    // ---- STK ----------------------------------------------------------------
    requirement def <'STK-1'> WallRunNeed {
        doc /* Stop as close as possible to the wall, no contact, at max speed. */
        subject rover : WallRover;
        requirement noContact       : NoContact;
        requirement minimiseGap     : MinimiseGap;        // objective (graded)
        requirement clearanceMargin : ClearanceMargin;    // derived bridge
        requirement maxApproach     : MaxApproachSpeed;
        requirement detectBrake     : DetectAndBrake;     // functional parent
        requirement straight        : StraightApproach;
        requirement fullStop        : FullStop;
    }

    // ---- SYS ----------------------------------------------------------------
    requirement def <'SYS-1'> NoContact specializes LowerBoundRequirement {
        doc /* HARD (Unwanted): the rover shall not contact the wall. */
        subject rover : WallRover;
        attribute :>> measured = rover.finalClearance;    // G_final
        attribute :>> target   = rover.contactMargin;     // 0 (no-contact floor)
    }

    requirement def <'SYS-2'> MinimiseGap {
        doc /* OBJECTIVE (graded): minimise the final gap. Its verifiable hard
             * proxy is ClearanceMargin (SYS-3); realised by GapEstimation (FUN-4). */
        subject rover : WallRover;
    }

    requirement def <'SYS-3'> ClearanceMargin specializes LowerBoundRequirement {
        doc /* HARD, DERIVED (bridge, rule 3 / A6): predicted clearance ≥ M = k·σ_G. */
        subject rover : WallRover;
        attribute :>> measured = rover.predictedClearance;
        attribute :>> target   = rover.requiredMargin;    // M = k · σ_G  (Python σ-rollup)
        requirement gapEstimation : GapEstimation;        // FUN-4 (also supports SYS-2)
    }

    requirement def <'SYS-4'> MaxApproachSpeed specializes LowerBoundRequirement {
        doc /* HARD (State): drive at max drivetrain speed, no slow-down. */
        subject rover : WallRover;
        attribute :>> measured = rover.commandedSpeed;    // command
        attribute :>> target   = rover.maxSpeed;          // ceiling  (run() clamps)
        requirement propulsion : Propulsion;              // FUN-1
    }

    requirement def <'SYS-5'> DetectAndBrake {
        doc /* Event: at d_trig, initiate braking. Functional parent — realised by
             * ForwardRanging (FUN-2) and StopControl (FUN-3). */
        subject rover : WallRover;
        requirement forwardRanging : ForwardRanging;      // FUN-2
        requirement stopControl    : StopControl;         // FUN-3
    }

    requirement def <'SYS-6'> StraightApproach specializes UpperBoundRequirement {
        doc /* HARD, DERIVED (State): hold heading within ±θ_max. */
        subject rover : WallRover;
        attribute :>> measured = rover.headingDrift;      // |yaw drift|
        attribute :>> target   = rover.maxHeadingDrift;   // θ_max
        requirement headingSensing : HeadingSensing;      // FUN-5
    }

    requirement def <'SYS-7'> FullStop specializes UpperBoundRequirement {
        doc /* HARD (Event): full stop, v_final ≤ v_stop_tol.
             * Also satisfied by MotorBrakeToStop (CMP-1c) — cross-link, non-tree. */
        subject rover : WallRover;
        attribute :>> measured = rover.finalSpeed;        // v_final
        attribute :>> target   = rover.stopSpeedTol;      // v_stop_tol
    }

    // ---- FUN ----------------------------------------------------------------
    requirement def <'FUN-1'> Propulsion {
        doc /* Drive straight forward at max drivetrain speed. Parent of CMP-1a/1b. */
        subject rover : WallRover;
        requirement leftMax  : LeftMotorDriveMax;         // CMP-1a
        requirement rightMax : RightMotorDriveMax;        // CMP-1b
    }

    requirement def <'FUN-2'> ForwardRanging {
        doc /* Report distance to the wall throughout the approach. Parent of CMP-2a/2b. */
        subject rover : WallRover;
        requirement usA : FwdUltrasonicA;                 // CMP-2a
        requirement usB : FwdUltrasonicB;                 // CMP-2b
    }

    requirement def <'FUN-3'> StopControl {
        doc /* At d_trig, command brake to full stop. Parent of CMP-1c. */
        subject rover : WallRover;
        requirement brakeStop : MotorBrakeToStop;         // CMP-1c
    }

    requirement def <'FUN-4'> GapEstimation specializes UpperBoundRequirement {
        doc /* DERIVED: estimate final clearance at rest (range−c within window,
             * else predicted). Verifiable proxy: |G_est − G| ≤ tol. */
        subject rover : WallRover;
        attribute :>> measured = rover.estimateError;     // |G_est − G|
        attribute :>> target   = rover.estimateErrorTol;
    }

    requirement def <'FUN-5'> HeadingSensing {
        doc /* Report yaw relative to start (straightness). Parent of CMP-5. */
        subject rover : WallRover;
        requirement imuHeading : ImuHeadingAndAccel;      // CMP-5
    }

    // ---- CMP (single-effector leaves) --------------------------------------
    requirement def <'CMP-1a'> LeftMotorDriveMax specializes LowerBoundRequirement {
        doc /* [left motor] rotate forward at rated max on command. */
        subject rover : WallRover;
        attribute :>> measured = rover.leftMotor.commandedSpeed;
        attribute :>> target   = rover.leftMotor.maxSpeed;
    }

    requirement def <'CMP-1b'> RightMotorDriveMax specializes LowerBoundRequirement {
        doc /* [right motor] rotate forward at rated max on command. */
        subject rover : WallRover;
        attribute :>> measured = rover.rightMotor.commandedSpeed;
        attribute :>> target   = rover.rightMotor.maxSpeed;
    }

    requirement def <'CMP-1c'> MotorBrakeToStop specializes UpperBoundRequirement {
        doc /* [both motors] brake to zero speed (a_brake characterised).
             * Satisfies SYS-7 outcome — cross-link. */
        subject rover : WallRover;
        attribute :>> measured = rover.driveResidualSpeed;
        attribute :>> target   = rover.stopSpeedTol;
    }

    requirement def <'CMP-2a'> FwdUltrasonicA specializes UpperBoundRequirement {
        doc /* [ultrasonic A] distance over [d_min,d_max]; noise bound below.
             * Range/rate sub-claims (Δt_s ≤ Δt_s_max, valid window) verified in report. */
        subject rover : WallRover;
        attribute :>> measured = rover.rangeNoise;        // σ_S
        attribute :>> target   = rover.rangeNoiseMax;     // σ_S_max
    }

    requirement def <'CMP-2b'> FwdUltrasonicB specializes UpperBoundRequirement {
        doc /* [ultrasonic B] independent distance; agrees with A within Δ_AB
             * (cross-source, rule 6). */
        subject rover : WallRover;
        attribute :>> measured = rover.abAgreement;       // |A − B|
        attribute :>> target   = rover.abTol;             // Δ_AB
    }

    requirement def <'CMP-5'> ImuHeadingAndAccel {
        doc /* [IMU] report yaw (drift bound at SYS-6) and forward accel
             * (cross-source for a_brake / CMP-1c). Verified by inspection + test. */
        subject rover : WallRover;
    }
}

// ============================================================================
// STRUCTURAL CHECKS (the gate that stands in for the absent grammar checker).
// Grammar conformance is verified out of band, after the run — NOT here.
// ----------------------------------------------------------------------------
// (1) REACHABILITY from the top need WallRunNeed (STK-1). Every requirement is
//     reachable via nested `requirement : Child` usages:
//       STK-1 → SYS-1,2,3,4,5,6,7
//       SYS-3 → FUN-4
//       SYS-4 → FUN-1 → CMP-1a, CMP-1b
//       SYS-5 → FUN-2 → CMP-2a, CMP-2b ; FUN-3 → CMP-1c
//       SYS-6 → FUN-5 → CMP-5
//     Reachable set = {STK-1, SYS-1..7, FUN-1..5, CMP-1a,1b,1c,2a,2b,5} = all 19. PASS.
//
// (2) EDGE-SET matches the requirement tree (spec §7 primary/single-parent edges).
//     Realised nesting edges (parent→child):
//       STK-1→{SYS-1,SYS-2,SYS-3,SYS-4,SYS-5,SYS-6,SYS-7}
//       SYS-3→FUN-4 ; SYS-4→FUN-1 ; SYS-5→{FUN-2,FUN-3} ; SYS-6→FUN-5
//       FUN-1→{CMP-1a,CMP-1b} ; FUN-2→{CMP-2a,CMP-2b} ; FUN-3→CMP-1c ; FUN-5→CMP-5
//     == spec §7 primary edges. PASS.
//     Non-tree links (documented, not nesting edges): FUN-4⇢SYS-2 (support);
//       CMP-1c⇢SYS-7 (satisfy); CMP-5.accel⇢CMP-1c (cross-source).
//
// (3) IMPORT resolution per package:
//       WallRunModel imports ISQ, SI, ScalarValues, RoverCommon, RoverStructure,
//         RelationTemplates — all present in rover_generic.sysml. PASS.
//       WallRunRequirements imports RequirementTemplates, WallRunModel — present. PASS.
//
// (4) SATISFY roll-up: WallRover satisfies WallRunNeed; the HARD leaves carrying
//     inherited require constraints (SYS-1,3,4,6,7; FUN-4; CMP-1a,1b,1c,2a,2b)
//     are the evaluable set. Objective/functional-parent defs (SYS-2,5; FUN-1,2,3,5;
//     CMP-5) carry doc only and are excluded from pass/fail by design. The Python
//     EVALUATE() reproduces exactly this evaluable set — a mismatch is a defect to
//     fix before the gate.
// ============================================================================
