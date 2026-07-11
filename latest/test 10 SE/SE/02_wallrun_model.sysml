// ============================================================================
// wallrun_model.sysml — TAILORED task model for the Wall-Approach task.
//
// Composed by specialising the pre-validated templates in rover_generic.sysml
// (RoverStructure, RelationTemplates, RequirementTemplates). No model structure
// invented. Relations are REPRODUCED as bound attribute expressions (per the
// skeleton validation note — calc invocation is not in the proven-valid set).
// Parameters are UNCALIBRATED (no default value) until calibration binds them
// (tenet A3: not zeroed). Derived quantities carry value expressions.
//
// This model is the FORMAL view; wallrun_model.py is the COMPUTATIONAL view.
// They must agree; a mismatch between this roll-up and the Python EVALUATE is a
// defect to fix before the gate.
// ============================================================================

package WallRunModel {
    private import ISQ::*;
    private import SI::*;
    private import ScalarValues::*;
    private import RoverCommon::*;
    private import RoverStructure::*;
    private import RelationTemplates::*;
    private import RequirementTemplates::*;

    // ------------------------------------------------------------------------
    // The design subject: a Rover specialised to this task.
    // Multiplicities fixed to the USED effectors; rear ranger + floor sensor are
    // inherited from Rover but no requirement traces to them (absence by
    // traceability — see the requirements spec §6).
    // ------------------------------------------------------------------------
    part def WallRover specializes Rover {

        // --- USED effectors (arrangement fixed) ---
        part redefines motors  : DriveMotor [2];        // differential pair
        part redefines rangers : DistanceSensor [2];    // two forward-facing
        // imu, floor inherited; floor DROPPED (no requirement traces to it)

        // ==== CALIBRATED PARAMETERS (TBD until calibration) ====
        attribute omegaMax   : AngularVelocityValue;    // TBD-VMAX  motor max, rad/s
        attribute kRot       : LengthValue;             // TBD-K     m per rad (RotationToSpeed.k)
        attribute aDecel     : AccelerationValue;       // TBD-ADEC  brake decel, m/s^2
        attribute tChain     : DurationValue;           // TBD-TCHAIN latency chain (= latency.tChain)
        attribute sampLatency: DurationValue;           // sensor sampling staleness, s
        attribute refresh    : DurationValue;           // TBD-REFRESH ranger sample period (= rangers.refreshInterval)
        attribute rangerFloor: LengthValue;             // TBD-FLOOR  ranger min valid range
        attribute sensorBias : LengthValue;             // TBD-BIAS   reading = true + bias (operator-anchored)
        attribute sigmaRun   : LengthValue;             // TBD-SRUN   run-to-run stop sigma
        attribute sigmaPred  : LengthValue;             // model/calibration residual sigma
        attribute sigmaBias  : LengthValue;             // bias uncertainty (prior, then measurement)
        attribute kSigma     : Real;                    // TBD-KSIG   consequence-scaled multiplier

        // ==== COMMANDED / MEASURED (operating configuration) ====
        attribute dTrig          : LengthValue;         // TBD-DTRIG programmed threshold (reading units)
        attribute commandedSpeed : SpeedValue;          // commanded ground speed
        attribute vMaxRated      : SpeedValue;          // achievable ceiling
        attribute finalSpeed     : SpeedValue;          // ground speed at rest (target 0)
        attribute headingDrift   : Angle;               // |max yaw excursion| during approach
        attribute headingTol     : Angle;               // TBD-HEAD allowed drift
        attribute contactMargin  : LengthValue;         // 0 (strict no-contact floor)
        attribute feasGuard      : LengthValue;         // ranger-floor feasibility guard

        // ==== REPRODUCED RELATIONS (bound attribute expressions) ====

        // RelationTemplates.RotationToSpeed:  v = motorSpeed * k
        attribute vCruise : SpeedValue = omegaMax * kRot;

        // Total response latency feeding StoppingDistance.tResponse
        attribute tResponse : DurationValue = tChain + sampLatency;

        // Trigger-crossing quantisation sigma: uniform over one refresh interval
        //   sigma = v * refresh / sqrt(12),   sqrt(12) = 3.4641016
        attribute sigmaTrig : LengthValue = vCruise * refresh / 3.4641016;

        // SYS-6 derived safety margin (A6): k * RSS of independent contributors
        attribute safetyMargin : LengthValue =
            kSigma * ( sigmaTrig ** 2 + sigmaRun ** 2
                     + sigmaPred ** 2 + sigmaBias ** 2 ) ** 0.5;

        // RelationTemplates.StoppingDistance, split:
        //   dynamic part  D_dyn = v*tResponse + v^2/(2a)   (measured DIRECTLY at v_max)
        //   full stop dist       = D_dyn + margin
        attribute dDyn : LengthValue =
            vCruise * tResponse + vCruise ** 2 / (2 * aDecel);
        attribute stopDistance : LengthValue = dDyn + safetyMargin;

        // Performance quantities (what the requirements bind against):
        //   bias cancels in the reading frame: finalReading = dTrig - dDyn
        attribute finalGap       : LengthValue = dTrig - sensorBias - dDyn;
        attribute finalClearance : LengthValue = finalGap;      // SYS-1 subject attr
        attribute predictedGap   : LengthValue = finalGap;      // SYS-4/SYS-6 subject attr
        attribute finalReading   : LengthValue = dTrig - dDyn;  // onboard cross-check

        // The design claims the top stakeholder need. Evaluating THIS satisfy
        // against the require roll-up below, at the calibrated values, IS the
        // pre-run verification artifact.
        satisfy requirement : WallRunRequirements::WallRunNeed;
    }

    // ------------------------------------------------------------------------
    package WallRunRequirements {
        private import RequirementTemplates::*;

        // ===== SYS-level requirement shapes: specialise a template, add the
        //       subject, BIND the operands (:>>), inherit the constraint,
        //       nest the CMP children. =====

        // SYS-1  No contact:  finalClearance >= contactMargin
        requirement def <'SYS-1'> NoContact specializes LowerBoundRequirement {
            subject rover : WallRover;
            attribute :>> measured = rover.finalClearance;
            attribute :>> target   = rover.contactMargin;
            requirement feasible : TriggerFeasible;   // CMP-2 (leaf)
        }

        // SYS-2  Command at maximum:  commandedSpeed >= vMaxRated
        requirement def <'SYS-2'> MaxSpeedCmd specializes LowerBoundRequirement {
            subject rover : WallRover;
            attribute :>> measured = rover.commandedSpeed;
            attribute :>> target   = rover.vMaxRated;
            requirement motorMax : MotorAtMax;        // CMP-3 (leaf)
        }

        // SYS-3  Complete stop:  finalSpeed <= 0
        requirement def <'SYS-3'> CompleteStop specializes UpperBoundRequirement {
            subject rover : WallRover;
            attribute :>> measured = rover.finalSpeed;
            attribute :>> target   = rover.contactMargin;   // 0 m/s
            requirement motorZero : MotorToZero;      // CMP-4 (leaf)
        }

        // SYS-5  Straight approach (derived):  headingDrift <= headingTol
        requirement def <'SYS-5'> StraightApproach specializes UpperBoundRequirement {
            subject rover : WallRover;
            attribute :>> measured = rover.headingDrift;
            attribute :>> target   = rover.headingTol;
            requirement heading : IMUHeadingCapability;   // CMP-6 (leaf)
        }

        // SYS-6  Margin floor (derived, bridge):  predictedGap >= safetyMargin
        requirement def <'SYS-6'> MarginFloor specializes LowerBoundRequirement {
            subject rover : WallRover;
            attribute :>> measured = rover.predictedGap;
            attribute :>> target   = rover.safetyMargin;
        }

        // SYS-4  Minimise final gap — OBJECTIVE (graded, not pass/fail). Tracked
        // by SYS-6's margin and the operator-validated closeness metric; carried
        // here for traceability, not as a require constraint.
        requirement def <'SYS-4'> MinimiseGap {
            subject rover : WallRover;
            doc /* Objective: minimise rover.predictedGap subject to SYS-1..SYS-6.
                   Graded at operation against operator ground truth. */
        }

        // ===== CMP-level leaves =====

        // CMP-2  Trigger within ranger valid band:  dTrig >= rangerFloor + feasGuard
        requirement def <'CMP-2'> TriggerFeasible specializes LowerBoundRequirement {
            subject rover : WallRover;
            attribute :>> measured = rover.dTrig;
            attribute :>> target   = rover.rangerFloor + rover.feasGuard;
        }

        // CMP-3  Each motor commanded at max:  commandedSpeed >= vMaxRated
        requirement def <'CMP-3'> MotorAtMax specializes LowerBoundRequirement {
            subject rover : WallRover;
            attribute :>> measured = rover.commandedSpeed;
            attribute :>> target   = rover.vMaxRated;
        }

        // CMP-4  Each motor reaches zero on stop:  finalSpeed <= 0
        requirement def <'CMP-4'> MotorToZero specializes UpperBoundRequirement {
            subject rover : WallRover;
            attribute :>> measured = rover.finalSpeed;
            attribute :>> target   = rover.contactMargin;
        }

        // CMP-6  IMU heading capability (verified by test; capability leaf).
        requirement def <'CMP-6'> IMUHeadingCapability {
            subject rover : WallRover;
            doc /* The InertialUnit reports yaw; verified by test in CHAR-1. */
        }

        // CMP-1 / CMP-5 / CMP-7 are sensing-capability leaves verified by test
        // (ranger reading; odometry distance; IMU accel). Carried in the spec;
        // their evidence is unit verification in CHAR-1.
        requirement def <'CMP-1'> RangerReading    { subject rover : WallRover;
            doc /* fwd ranger reports range each refresh above floor. */ }
        requirement def <'CMP-5'> OdometryDistance { subject rover : WallRover;
            doc /* motor rotation -> ground distance via kRot. */ }
        requirement def <'CMP-7'> IMUAccel         { subject rover : WallRover;
            doc /* IMU forward accel, independent decel channel. */ }

        // ===== The top need: decomposition as nested requirement usages =====
        requirement def WallRunNeed {
            subject rover : WallRover;
            requirement noContact    : NoContact;         // SYS-1
            requirement maxSpeed     : MaxSpeedCmd;       // SYS-2
            requirement completeStop : CompleteStop;      // SYS-3
            requirement minGap       : MinimiseGap;       // SYS-4 (objective)
            requirement straight     : StraightApproach;  // SYS-5
            requirement margin       : MarginFloor;       // SYS-6
        }
    }
}

// ============================================================================
// STRUCTURAL SELF-CHECKS (run in place of the out-of-band grammar checker; the
// gate per MODEL STRATEGY). Grammar conformance is verified separately, not here.
//
// (1) REACHABILITY from the top need WallRunNeed:
//     WallRunNeed -> {NoContact, MaxSpeedCmd, CompleteStop, MinimiseGap,
//                     StraightApproach, MarginFloor}
//     NoContact -> TriggerFeasible(CMP-2)
//     MaxSpeedCmd -> MotorAtMax(CMP-3)
//     CompleteStop -> MotorToZero(CMP-4)
//     StraightApproach -> IMUHeadingCapability(CMP-6)
//     => every SYS and every numeric CMP leaf is reachable. Capability leaves
//        CMP-1/5/7 are attached at spec level (test-verified), listed above.
//        NO requirement is asserted without a place in the tree.  [PASS]
//
// (2) REALIZED DECOMPOSITION EDGE-SET vs the requirement tree (spec §8):
//     Model edges: STK-1(satisfy)->WallRunNeed;
//       WallRunNeed->SYS-1..6; SYS-1->CMP-2; SYS-2->CMP-3; SYS-3->CMP-4;
//       SYS-5->CMP-6.  Spec tree edges match 1:1 (CMP-1/5/7 cross-cut FUN-1/4/5
//       and are verified by test; CMP-4 has the extra SYS-3 parent noted in the
//       spec).  [PASS — matches spec §8]
//
// (3) PER-PACKAGE IMPORT RESOLUTION:
//     WallRunModel imports ISQ, SI, ScalarValues, RoverCommon, RoverStructure,
//       RelationTemplates, RequirementTemplates — all present in the skeleton +
//       standard library.
//     WallRunRequirements imports RequirementTemplates; references WallRover in
//       the enclosing package (resolved).  [PASS]
//
// (4) SysML roll-up  <->  Python EVALUATE agreement:
//     NoContact/MaxSpeedCmd/CompleteStop/StraightApproach/MarginFloor/
//     TriggerFeasible bind the SAME operands the Python `evaluate()` checks
//     (finalClearance>=contactMargin; commandedSpeed>=vMaxRated; finalSpeed<=0;
//     headingDrift<=headingTol; predictedGap>=safetyMargin; dTrig>=floor+guard).
//     Relation expressions (vCruise, tResponse, dDyn, safetyMargin, finalGap,
//     finalReading) are reproduced identically in both views.  [PASS]
// ============================================================================
