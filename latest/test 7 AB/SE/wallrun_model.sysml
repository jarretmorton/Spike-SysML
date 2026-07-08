// ============================================================================
// wallrun_model.sysml — TAILORED system model for the wall-approach task.
//
// Realises the Requirements Specification (the source of truth) as a formal
// SysML v2 model: the design part WallRover claims the top need, the relation
// expressions from RelationTemplates are REPRODUCED against bound parameters
// (calc invocation is not in this repo's proven-valid set — see rover_generic
// VALIDATION NOTE), and WallRunRequirements carries the satisfy/require roll-up.
//
// Every attribute / relation / constraint here maps 1:1 to a named variable /
// function in wallrun_model.py (the executable view). Parameters are left free
// (uncalibrated, not zeroed); calibration binds them (TBD register, spec §5).
//
// STRUCTURAL CHECKS (grammar is verified out of band; these are the gate):
//   - reachability: every requirement reachable from WallRunNeed
//   - edge-set: nested `requirement : Child` usages == spec §7 tree edges
//   - import resolution: every referenced name resolves in-package
// Run by 03_structural_check.py against this file.
// ============================================================================

package WallRunModel {

    private import ISQ::*;
    private import SI::*;
    private import ScalarValues::*;
    private import RoverCommon::*;
    private import RoverStructure::*;
    private import RelationTemplates::*;   // single source of truth for relation expressions

    // ------------------------------------------------------------------------
    // Design part: the platform specialised to the selected effectors.
    // Effector selection (spec §6) is expressed structurally by multiplicity:
    //   motors  -> [2]  (both drive motors kept: CMP-1, CMP-2, CMP-7)
    //   rangers -> [2]  (the two FORWARD sensors kept; rear ranger dropped by
    //                    fixing the count to the two used: CMP-3, CMP-4)
    //   floor   -> [0]  (reflectance sensor dropped: no requirement traces to it)
    //   imu     -> inherited single (CMP-6)
    // ------------------------------------------------------------------------
    part def WallRover specializes Rover {
        doc /* Wall-approach rover. Claims WallRunNeed; carries the tailored
             * parameters and the reproduced relation expressions. */

        // --- selected-effector structure (absence by traceability) ---
        part :>> motors  : DriveMotor [2];
        part :>> rangers : DistanceSensor [2];      // two forward sensors
        part :>> floor   : ReflectanceSensor [0];   // DROPPED
        // imu inherited (single); latency inherited (RoverLatency, platform-wide)

        // --- calibrated / design parameters (free until calibration; spec §5) ---
        attribute kSpeed           : LengthValue;            // TBD-5  m per rad (encoder->ground)
        attribute omegaMax         : AngularVelocityValue;   // TBD-1  rad/s rated ceiling
        attribute tResponse        : DurationValue;          // TBD-4  s  sense->brake latency
        attribute tChainBound      : DurationValue;          // s  latency budget (RoverLatency.tChain)
        attribute aDecel           : AccelerationValue;      // m/s^2 (feasibility / back-solve only)
        attribute stoppingDistance : LengthValue;            // TBD-6  m  MEASURED DIRECTLY at operating point
        attribute sigmaStop        : LengthValue;            // TBD-7  m  run-to-run stopping spread
        attribute sigmaPred        : LengthValue;            // m  prediction uncertainty contributor
        attribute sigmaB           : LengthValue;            // m  offset uncertainty contributor
        attribute kMargin          : Real;                   // coverage factor (A6)
        attribute sensorOffset     : LengthValue;            // TBD-2  m  reported = scale*true + offset
        attribute sensorScale      : Real;                   // TBD-2b (~1)
        attribute minRange         : LengthValue;            // TBD-3  m  sensor min reliable range
        attribute triggerThreshold : LengthValue;            // design R_trigger (reported units)
        attribute targetGap        : LengthValue;            // design g_target
        attribute safetyMargin     : LengthValue;            // TBD-9  derived floor
        attribute headingTol       : Angle;                  // rad  straightness tolerance
        attribute restSpeedTol     : SpeedValue;             // m/s  full-stop tolerance
        attribute contactFloor     : LengthValue;            // m  = 0
        attribute residTol         : LengthValue;            // m  sensor residual tolerance
        attribute kTol             : Real;                   // ground-constant residual tolerance

        // --- measured / observed performance quantities (bound by runs) ---
        attribute maxGroundSpeed   : SpeedValue;             // reproduced RotationToSpeed
        attribute cruiseSpeed      : SpeedValue;             // achieved cruise (CMP-1 -> v_max)
        attribute omegaAchieved    : AngularVelocityValue;   // measured steady-state (CMP-1)
        attribute motorRestSpeed   : AngularVelocityValue;   // post-brake (CMP-2)
        attribute finalClearance   : LengthValue;            // reproduced clearance at rest
        attribute finalSpeed       : SpeedValue;             // rest ground speed (SYS-4)
        attribute headingDrift     : Angle;                  // measured drift (CMP-6, SYS-5)
        attribute sensorResidual   : LengthValue;            // residual after offset (CMP-3)
        attribute kResidual        : Real;                   // ground-constant fit residual (CMP-7)

        // --- REPRODUCED relation expressions (RelationTemplates), bound params ---
        // RotationToSpeed:  v = motorSpeed * k
        constraint groundSpeedRel { maxGroundSpeed == omegaMax * kSpeed }
        // achieved cruise reaches rated max ground speed (CMP-1 roll-up into SYS-2)
        constraint cruiseRel      { cruiseSpeed == maxGroundSpeed }
        // StoppingDistance (feasibility form; margin folded to 0 — the human margin
        // lives in triggerThreshold, not in D_stop). AT THE OPERATING POINT
        // stoppingDistance is the MEASURED input and aDecel the back-solved output;
        // the equation is retained only for the feasibility/back-solve cross-check.
        constraint stoppingRel    { stoppingDistance == cruiseSpeed * tResponse
                                                       + cruiseSpeed ** 2 / (2 * aDecel) }
        // safety margin = kMargin * RSS(sigmaPred, sigmaB, sigmaStop)   (tenet A6)
        constraint marginRel      { safetyMargin == kMargin
                                       * (sigmaPred ** 2 + sigmaB ** 2 + sigmaStop ** 2) ** 0.5 }
        // target gap equals the derived margin
        constraint targetRel      { targetGap == safetyMargin }
        // trigger placement:  R_trigger = sensorOffset + stoppingDistance + targetGap
        constraint triggerRel     { triggerThreshold == sensorOffset + stoppingDistance + targetGap }
        // clearance at rest (reproduced):  R_trigger - sensorOffset - stoppingDistance
        constraint clearanceRel   { finalClearance == triggerThreshold - sensorOffset - stoppingDistance }

        // --- the design claims the top stakeholder need ---
        satisfy requirement : WallRunRequirements::WallRunNeed;
    }
}

// ============================================================================
package WallRunRequirements {
    doc /* Formal realisation of the requirements spec. Each task requirement
         * specialises a bound template (RequirementTemplates), adds a subject,
         * BINDS operands against WallRover attributes via `:>> measured = ...`
         * (inherited require constraint), and nests `requirement : Child`
         * usages for its decomposition. Graded / aggregator requirements carry
         * no bound (no constraint to evaluate) but remain in the tree. */

    private import RequirementTemplates::*;
    private import WallRunModel::*;

    // ---- STK ----------------------------------------------------------------
    // Top need: aggregator (no own bound); its satisfaction is its children's.
    requirement def WallRunNeed {
        doc /* STK-1. Drive to the wall at max speed and stop as close as
             * possible without contact. Decomposed into the SYS children. */
        subject rover : WallRover;
        requirement : NoContact;
        requirement : MaxSpeed;
        requirement : MinGap;
        requirement : FullStop;
        requirement : StraightTravel;
    }

    // ---- SYS ----------------------------------------------------------------
    requirement def NoContact specializes LowerBoundRequirement {
        doc /* SYS-1 (Unwanted, HARD). finalClearance >= contactFloor (=0). */
        subject rover : WallRover;
        attribute :>> measured = rover.finalClearance;
        attribute :>> target   = rover.contactFloor;
        requirement : MinGapMargin;      // SYS-3b (derived bridge lives under SYS-1)
        requirement : SenseDistance;     // FUN-1
        requirement : DecideStop;        // FUN-2
    }

    requirement def MaxSpeed specializes LowerBoundRequirement {
        doc /* SYS-2 (State-driven, HARD). cruiseSpeed >= maxGroundSpeed (reach ceiling). */
        subject rover : WallRover;
        attribute :>> measured = rover.cruiseSpeed;
        attribute :>> target   = rover.maxGroundSpeed;
        requirement : DriveMax;          // FUN-3
    }

    // SYS-3 objective: graded, no hard constraint => no bound template, no child.
    requirement def MinGap {
        doc /* SYS-3 (Objective, graded). Minimize final gap. Bridged to a hard
             * floor by MinGapMargin (SYS-3b). Closed at GATE C only on
             * operating-point ground-truth validation of the predicted gap. */
        subject rover : WallRover;
    }

    requirement def MinGapMargin specializes LowerBoundRequirement {
        doc /* SYS-3b (Event-driven, HARD, DERIVED). finalClearance >= safetyMargin.
             * Bridges SYS-1 <-> SYS-3. safetyMargin sized by RSS (A6). */
        subject rover : WallRover;
        attribute :>> measured = rover.finalClearance;
        attribute :>> target   = rover.safetyMargin;
        requirement : StoppingCharacterized;   // FUN-4
        requirement : EstimateGap;             // FUN-6
    }

    requirement def FullStop specializes UpperBoundRequirement {
        doc /* SYS-4 (Event-driven, HARD). finalSpeed <= restSpeedTol. */
        subject rover : WallRover;
        attribute :>> measured = rover.finalSpeed;
        attribute :>> target   = rover.restSpeedTol;
        requirement : MotorToRest;       // CMP-2 (single-effector realization)
    }

    requirement def StraightTravel specializes UpperBoundRequirement {
        doc /* SYS-5 (State-driven, HARD, DERIVED). headingDrift <= headingTol. */
        subject rover : WallRover;
        attribute :>> measured = rover.headingDrift;
        attribute :>> target   = rover.headingTol;
        requirement : MaintainHeading;   // FUN-5
    }

    // ---- FUN (aggregators; content in the CMP leaves) -----------------------
    requirement def SenseDistance {
        doc /* FUN-1 (Ubiquitous). Continuously measure forward distance. */
        subject rover : WallRover;
        requirement : SensorResidual;    // CMP-3
        requirement : SensorMinRange;    // CMP-4
    }

    requirement def DecideStop {
        doc /* FUN-2 (Event-driven). Brake when distance <= triggerThreshold. */
        subject rover : WallRover;
        requirement : LatencyChain;      // CMP-5
    }

    requirement def DriveMax {
        doc /* FUN-3 (State-driven). Drive both motors at rated max before trigger. */
        subject rover : WallRover;
        requirement : MotorAtMax;        // CMP-1
    }

    requirement def StoppingCharacterized {
        doc /* FUN-4 (Ubiquitous, DERIVED). Repeatable stopping distance with
             * characterized central value and spread; measured directly at
             * the operating point. */
        subject rover : WallRover;
        requirement : GroundConstant;    // CMP-7
    }

    requirement def MaintainHeading {
        doc /* FUN-5 (State-driven). Limit heading deviation about start heading. */
        subject rover : WallRover;
        requirement : HeadingBounded;    // CMP-6
    }

    // FUN-6 EstimateGap: derived helper realized by onboard computation over
    // CMP-3/CMP-7 channels; no additional effector, no bound. Leaf in the tree.
    requirement def EstimateGap {
        doc /* FUN-6 (Event-driven, DERIVED). Compute onboard gap estimate at
             * rest: (triggerThreshold - sensorOffset) - stoppingDistance_this_run.
             * Offset enters at the trigger range (reliable), not the tiny gap. */
        subject rover : WallRover;
    }

    // ---- CMP (single-effector leaves; bound constraints) --------------------
    requirement def MotorAtMax specializes LowerBoundRequirement {
        doc /* CMP-1 (Ubiquitous) — DriveMotor. omegaAchieved >= omegaMax. */
        subject rover : WallRover;
        attribute :>> measured = rover.omegaAchieved;
        attribute :>> target   = rover.omegaMax;
    }

    requirement def MotorToRest specializes UpperBoundRequirement {
        doc /* CMP-2 (Event-driven) — DriveMotor. motorRestSpeed <= restSpeedTol. */
        subject rover : WallRover;
        attribute :>> measured = rover.motorRestSpeed;
        attribute :>> target   = rover.restSpeedTol;
    }

    requirement def SensorResidual specializes UpperBoundRequirement {
        doc /* CMP-3 (Ubiquitous) — DistanceSensor. sensorResidual <= residTol
             * after offset correction. sensorOffset anchored by operator (tier 4). */
        subject rover : WallRover;
        attribute :>> measured = rover.sensorResidual;
        attribute :>> target   = rover.residTol;
    }

    requirement def SensorMinRange specializes LowerBoundRequirement {
        doc /* CMP-4 (State-driven) — DistanceSensor. triggerThreshold >= minRange
             * (trigger placed where the sensor is reliable). */
        subject rover : WallRover;
        attribute :>> measured = rover.triggerThreshold;
        attribute :>> target   = rover.minRange;
    }

    requirement def LatencyChain specializes UpperBoundRequirement {
        doc /* CMP-5 (Ubiquitous) — platform latency. tResponse <= tChainBound. */
        subject rover : WallRover;
        attribute :>> measured = rover.tResponse;
        attribute :>> target   = rover.tChainBound;
    }

    requirement def HeadingBounded specializes UpperBoundRequirement {
        doc /* CMP-6 (State-driven) — InertialUnit. headingDrift <= headingTol
             * (cross-sourced vs left/right encoder differential). */
        subject rover : WallRover;
        attribute :>> measured = rover.headingDrift;
        attribute :>> target   = rover.headingTol;
    }

    requirement def GroundConstant specializes UpperBoundRequirement {
        doc /* CMP-7 (Ubiquitous) — DriveMotor encoder. kResidual <= kTol
             * (multi-segment fit; offset cancels in the difference). */
        subject rover : WallRover;
        attribute :>> measured = rover.kResidual;
        attribute :>> target   = rover.kTol;
    }
}
