// ============================================================================
// WallRunModel.sysml  --  TASK-TAILORED model for the max-speed wall-stop task.
//
// Composed from rover_generic.sysml (RoverStructure, RelationTemplates,
// RequirementTemplates, RoverCommon).  Only the templates the requirements call
// for are instantiated.  Relations are instantiated by REPRODUCING their
// calc-def expression against bound parameters (the validated form; calc
// invocation is intentionally avoided per the skeleton's VALIDATION NOTE).
// Requirements specialise a template, add the WallRover subject, and BIND the
// operands with `attribute :>> measured = subject.attr`; the require constraint
// is inherited, so the evaluable logic lives in one place.
//
// This SysML view is the FORMAL satisfy/require argument.  Its computational
// twin is model/wall_stop_model.py; the two must agree.  Parameters are FREE
// (uncalibrated) until the Calibration Plan binds them -- shown as `= TBD_*`
// placeholders, never eyeballed constants.
// ============================================================================

package WallRunModel {

    private import ISQ::*;
    private import SI::*;
    private import ScalarValues::*;
    private import RoverCommon::*;
    private import RoverStructure::*;
    private import RelationTemplates::*;       // source of truth for relation expressions
    private import RequirementTemplates::*;

    // ------------------------------------------------------------------------
    // TBD placeholders (bound at calibration; see Calibration Plan TBD register)
    //   Left as named symbols so no numeric constant is eyeballed (tenet A3).
    // ------------------------------------------------------------------------
    // TBD_vMax, TBD_omegaMax, TBD_kGain, TBD_aDecel, TBD_tChain, TBD_refresh,
    // TBD_cOffset, TBD_dStopConst, TBD_sigmaBrake, TBD_sigmaMeas, TBD_sigmaOffset,
    // TBD_headingDrift, TBD_sensorMin, TBD_sensorMax
    // Design-set (not calibrated): kZ = 3, fSamp = 0.5, qProj (>=1 raw threshold),
    //   headingBound, vStopTol, contactFloor = 0, startDistance = 1000 mm.

    // ========================================================================
    // SUBJECT: the wall-running rover, a specialisation of the generic platform.
    //   Multiplicities fixed: two drive motors, two forward rangers used (the
    //   rear ranger and the floor reflectance sensor carry NO requirement and
    //   drop out by traceability -- they are simply not referenced here).
    // ========================================================================
    part def WallRover :> Rover {

        // ---- kinematics (RotationToSpeed) ----
        attribute omegaMax  : AngularVelocityValue = TBD_omegaMax;   // motor ceiling
        attribute kGain     : LengthValue          = TBD_kGain;      // ground per motor-rad
        attribute vMax      : SpeedValue;                            // achieved ground speed
        constraint rotationToSpeed { vMax == omegaMax * kGain }      // reproduces RotationToSpeed

        // ---- stop dynamics (StoppingDistance) ----
        attribute tChain    : DurationValue     = TBD_tChain;        // = latency.tChain
        attribute refresh   : DurationValue     = TBD_refresh;       // ranger sample period
        attribute fSamp     : Real              = 0.5;               // mean sampling-lag fraction
        attribute tResponse : DurationValue;
        constraint responseChain { tResponse == tChain + fSamp * refresh }

        attribute aDecel    : AccelerationValue = TBD_aDecel;        // braking deceleration
        attribute dStopConst: LengthValue       = TBD_dStopConst;    // DIRECT-calibrated at op point
        // Cross-check form (reproduces StoppingDistance minus margin); direct value governs:
        constraint stopDistanceCrosscheck {
            dStopConst == vMax * tResponse + vMax ** 2 / (2 * aDecel)
        }

        // ---- absolute offset (operator ground truth at operating point) ----
        attribute cOffset   : LengthValue = TBD_cOffset;   // d_meas_rest - true bumper gap

        // ---- uncertainty budget (tenet A6: margin = RSS of contributors) ----
        attribute qProj      : Real       = 1.0;           // <1 if velocity-projected trigger
        attribute sigmaBrake : LengthValue = TBD_sigmaBrake;
        attribute sigmaMeas  : LengthValue = TBD_sigmaMeas;
        attribute sigmaOffset: LengthValue = TBD_sigmaOffset;
        attribute sigmaQuant : LengthValue;
        attribute sigmaTotal : LengthValue;
        constraint quantisation { sigmaQuant == qProj * vMax * refresh / (12) ** 0.5 }
        constraint rssMargin {
            sigmaTotal == ( sigmaBrake ** 2 + sigmaQuant ** 2
                          + sigmaMeas ** 2 + sigmaOffset ** 2 ) ** 0.5
        }

        // ---- design point: aim gap and trigger threshold ----
        attribute kZ        : Real        = 3.0;           // k-sigma no-contact protection
        attribute gTarget   : LengthValue;                 // aim bumper gap
        attribute dThr      : LengthValue;                 // measured-distance brake threshold
        attribute dMeasRest : LengthValue;                 // predicted rest reading
        constraint aimGap    { gTarget == kZ * sigmaTotal }
        // StoppingDistance instantiated with margin = cOffset + gTarget :
        constraint triggerThreshold { dThr == dStopConst + cOffset + gTarget }
        constraint restReading      { dMeasRest == dThr - dStopConst }

        // ---- performance outputs ----
        attribute finalClearance : LengthValue;            // bumper -> wall at rest
        attribute contactMargin  : LengthValue;            // no-contact floor (k-sigma protection)
        constraint clearance    { finalClearance == dMeasRest - cOffset }   // == gTarget
        constraint marginFloor  { contactMargin  == kZ * sigmaTotal }

        // ---- max-speed ceiling operand ----
        attribute vCeiling : SpeedValue;
        constraint ceiling { vCeiling == omegaMax * kGain }

        // ---- complete-stop operand ----
        attribute vRest    : SpeedValue = 0 [SI::'m/s'];   // achieved by brake()
        attribute vStopTol : SpeedValue;                   // stop tolerance

        // ---- straightness operands ----
        attribute headingDrift : Angle = TBD_headingDrift;
        attribute headingBound : Angle;                    // design bound

        // ---- ranger valid-range operands ----
        attribute sensorMin : LengthValue = TBD_sensorMin;
        attribute sensorMax : LengthValue = TBD_sensorMax;

        // ---- fixed task geometry ----
        attribute startDistance : LengthValue;             // = 1000 mm, operator-held

        // ---- THE CLAIM: the design satisfies the top stakeholder need ----
        satisfy requirement : WallRunRequirements::WallRunNeed;
    }

    // ========================================================================
    // REQUIREMENTS: realise the requirements spec (source of truth) as a
    //   satisfy/require roll-up.  STK is embodied by WallRunNeed; SYS are its
    //   children; FUN are thin decomposition nodes; CMP leaves bind effector-
    //   level operands.  Each bound requirement specialises a template and
    //   redefines its operands (:>>); the require constraint is inherited.
    // ========================================================================
    package WallRunRequirements {
        private import RequirementTemplates::*;

        // ---- TOP NEED (embodies STK-1..STK-5) ----
        requirement def WallRunNeed {
            doc /* STK: approach the wall at maximum speed, come to a complete
                   stop WITHOUT contact, minimising the final gap, driving
                   straight.  Decomposed into SYS-1..SYS-7 below. */
            subject rover : WallRover;

            requirement : SYS1_NoContact;
            requirement : SYS2_GapObjective;
            requirement : SYS2M_MarginBridge;
            requirement : SYS3_MaxSpeed;
            requirement : SYS4_CompleteStop;
            requirement : SYS5_Straight;
            requirement : SYS6_TriggerInRange;
            requirement : SYS7_FitsRunway;
        }

        // ---- SYS-1  No contact  (LowerBound: finalClearance >= contactMargin) ----
        requirement def <'SYS-1'> SYS1_NoContact :> LowerBoundRequirement {
            doc /* STK-1. The rover shall not contact the wall: bumper clearance
                   at rest shall be no less than the k-sigma no-contact floor. */
            subject rover : WallRover;
            attribute :>> measured = rover.finalClearance;
            attribute :>> target   = rover.contactMargin;
            requirement : FUN_Sense;
            requirement : FUN_Decide;
        }

        // ---- SYS-2  Gap objective (graded; carried, not a hard constraint) ----
        requirement def <'SYS-2'> SYS2_GapObjective {
            doc /* STK-2 (OBJECTIVE, should). Minimise finalClearance. Graded, not
                   pass/fail; bridged to the hard floor by SYS-2M. */
            subject rover : WallRover;
            attribute objective = rover.finalClearance;   // minimise
        }

        // ---- SYS-2M  Margin bridge (DERIVED; LowerBound: gTarget >= kZ*sigmaTotal) ----
        requirement def <'SYS-2M'> SYS2M_MarginBridge :> LowerBoundRequirement {
            doc /* DERIVED (rule 3, tenet A6). Bridges objective SYS-2 and hard
                   SYS-1: the aim gap shall be no less than the RSS uncertainty
                   floor, so minimising the gap never crosses the no-contact
                   constraint. Rationale: size margin from uncertainty, not guess. */
            subject rover : WallRover;
            attribute :>> measured = rover.gTarget;
            attribute :>> target   = rover.contactMargin;   // kZ*sigmaTotal
        }

        // ---- SYS-3  Max speed  (LowerBound: vMax >= vCeiling) ----
        requirement def <'SYS-3'> SYS3_MaxSpeed :> LowerBoundRequirement {
            doc /* STK-3. While approaching (pre-brake) the rover shall drive at
                   the motor ceiling; no slow-down for safety margin. */
            subject rover : WallRover;
            attribute :>> measured = rover.vMax;
            attribute :>> target   = rover.vCeiling;
            requirement : FUN_Drive;
        }

        // ---- SYS-4  Complete stop  (UpperBound: vRest <= vStopTol) ----
        requirement def <'SYS-4'> SYS4_CompleteStop :> UpperBoundRequirement {
            doc /* STK-4. When the trigger fires, the rover shall decelerate to
                   zero (within tolerance). */
            subject rover : WallRover;
            attribute :>> measured = rover.vRest;
            attribute :>> target   = rover.vStopTol;
            requirement : FUN_Brake;
        }

        // ---- SYS-5  Straight  (UpperBound: headingDrift <= headingBound) ----
        requirement def <'SYS-5'> SYS5_Straight :> UpperBoundRequirement {
            doc /* STK-5. While approaching, heading drift shall stay within the
                   bound, so the approach is perpendicular and the operating-point
                   offset (cOffset) stays valid. */
            subject rover : WallRover;
            attribute :>> measured = rover.headingDrift;
            attribute :>> target   = rover.headingBound;
            requirement : FUN_Heading;
        }

        // ---- SYS-6  Trigger in valid range (DERIVED) : two leaves ----
        requirement def <'SYS-6'> SYS6_TriggerInRange {
            doc /* DERIVED (rule 4). The measured brake threshold shall lie inside
                   the ranger's valid window, so the stop is commanded on a
                   trustworthy reading. Rationale: a channel is trusted only in
                   range (tenet D1/D2); hand off before its limit. */
            subject rover : WallRover;
            requirement : CMP_DST2_LowerRange;
            requirement : CMP_DST2_UpperRange;
        }

        // ---- SYS-7  Fits runway (DERIVED; UpperBound: dThr <= startDistance) ----
        requirement def <'SYS-7'> SYS7_FitsRunway :> UpperBoundRequirement {
            doc /* DERIVED (rule 4). The stop must initiate within the available
                   start-line budget. Rationale: feasibility of the maneuver. */
            subject rover : WallRover;
            attribute :>> measured = rover.dThr;
            attribute :>> target   = rover.startDistance;
        }

        // ====================================================================
        // FUN (function) nodes -- thin decomposition, nest the CMP leaves.
        // ====================================================================
        requirement def FUN_Sense {
            doc /* Sense forward distance to the wall. */
            subject rover : WallRover;
            requirement : CMP_DST1_Staleness;
        }
        requirement def FUN_Decide {
            doc /* Decide the brake trigger from distance (and speed). */
            subject rover : WallRover;
            requirement : CMP_LAT1_Latency;
        }
        requirement def FUN_Drive {
            doc /* Actuate forward drive at maximum. */
            subject rover : WallRover;
            requirement : CMP_DRV1_MaxSpeed;
        }
        requirement def FUN_Brake {
            doc /* Actuate braking to a complete stop. */
            subject rover : WallRover;
            requirement : CMP_DRV2_Brake;
            requirement : CMP_IMU2_Accel;
        }
        requirement def FUN_Heading {
            doc /* Sense heading for straightness. */
            subject rover : WallRover;
            requirement : CMP_IMU1_Heading;
        }

        // ====================================================================
        // CMP leaves -- single-effector, bound operands.
        // ====================================================================

        // Forward DistanceSensor: staleness bound (UpperBound: refresh <= bound)
        requirement def <'CMP-DST-1'> CMP_DST1_Staleness :> UpperBoundRequirement {
            doc /* Effector: forward DistanceSensor. While approaching, the ranger
                   shall report no less often than its refresh interval.
                   Rationale: staleness sets the trigger quantisation (sigmaQuant). */
            subject rover : WallRover;
            attribute :>> measured = rover.refresh;
            attribute :>> target   = rover.refreshBound;   // TBD staleness ceiling
            attribute refreshBound : DurationValue;
        }

        // Forward DistanceSensor: valid range, two leaves supporting SYS-6.
        requirement def <'CMP-DST-2a'> CMP_DST2_LowerRange :> LowerBoundRequirement {
            doc /* Effector: forward DistanceSensor. Threshold at/above the ranger
                   floor. */
            subject rover : WallRover;
            attribute :>> measured = rover.dThr;
            attribute :>> target   = rover.sensorMin;
        }
        requirement def <'CMP-DST-2b'> CMP_DST2_UpperRange :> UpperBoundRequirement {
            doc /* Effector: forward DistanceSensor. Threshold at/below the ranger
                   ceiling. */
            subject rover : WallRover;
            attribute :>> measured = rover.dThr;
            attribute :>> target   = rover.sensorMax;
        }

        // DriveMotor x2: command at ceiling (LowerBound: vMax >= vCeiling)
        requirement def <'CMP-DRV-1'> CMP_DRV1_MaxSpeed :> LowerBoundRequirement {
            doc /* Effector: each DriveMotor. While in approach, rotate at maximum
                   achievable speed. */
            subject rover : WallRover;
            attribute :>> measured = rover.vMax;
            attribute :>> target   = rover.vCeiling;
        }

        // DriveMotor x2: brake to zero (UpperBound: vRest <= vStopTol)
        requirement def <'CMP-DRV-2'> CMP_DRV2_Brake :> UpperBoundRequirement {
            doc /* Effector: each DriveMotor. When the trigger fires, brake to zero
                   angular velocity within the stopping-distance budget. */
            subject rover : WallRover;
            attribute :>> measured = rover.vRest;
            attribute :>> target   = rover.vStopTol;
        }

        // InertialUnit (yaw): heading drift bound (UpperBound)
        requirement def <'CMP-IMU-1'> CMP_IMU1_Heading :> UpperBoundRequirement {
            doc /* Effector: InertialUnit yaw. Report heading; drift within bound. */
            subject rover : WallRover;
            attribute :>> measured = rover.headingDrift;
            attribute :>> target   = rover.headingBound;
        }

        // InertialUnit (forwardAccel): cross-source for deceleration (DERIVED, rule 6)
        requirement def <'CMP-IMU-2'> CMP_IMU2_Accel :> LowerBoundRequirement {
            doc /* DERIVED (rule 6, cross-sourcing). Effector: InertialUnit
                   forwardAccel. Provide an independent deceleration channel so
                   `a` is cross-checked against the ultrasonic-difference estimate.
                   measured = usable accel resolution; target = min needed. */
            subject rover : WallRover;
            attribute :>> measured = rover.accelResolution;
            attribute :>> target   = rover.accelNeeded;
            attribute accelResolution : AccelerationValue;
            attribute accelNeeded     : AccelerationValue;
        }

        // Stop-decision latency (DERIVED; UpperBound: tChain <= tChainBound)
        requirement def <'CMP-LAT-1'> CMP_LAT1_Latency :> UpperBoundRequirement {
            doc /* DERIVED (rule 4). Platform latency chain. tChain shall be
                   characterised and bounded so reaction distance (vMax*tResponse)
                   stays within the stop budget. Model-completion parameter. */
            subject rover : WallRover;
            attribute :>> measured = rover.tChain;
            attribute :>> target   = rover.tChainBound;
            attribute tChainBound : DurationValue;
        }
    }
}

// ============================================================================
// EFFECTOR TRACEABILITY LEDGER (rule 7 -- disuse verified, not assumed)
//   USED   : DriveMotor x2      -> CMP-DRV-1, CMP-DRV-2
//            DistanceSensor(fwd)-> CMP-DST-1, CMP-DST-2a/b   (2 forward rangers,
//                                   cross-sourced; primary + check)
//            InertialUnit(yaw)  -> CMP-IMU-1
//            InertialUnit(accel)-> CMP-IMU-2
//   DROPPED: DistanceSensor(rear) -- no requirement traces (rearward; wall is
//                                     ahead) -> absence by traceability.
//            ReflectanceSensor(floor) -- no requirement traces (no line/scale to
//                                     read; distance handled by rangers) -> dropped.
// ============================================================================
