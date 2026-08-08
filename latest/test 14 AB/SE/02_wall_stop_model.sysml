// ============================================================================
// 02_wall_stop_model.sysml -- TAILORED task model for the wall-approach run.
//
// Realises 01_requirements_spec.md (the source of truth).  Composed from the
// pre-validated library in rover_generic.sysml: RoverStructure (skeleton),
// RelationTemplates (physics relations), RequirementTemplates (requirement
// shapes).  No model structure is generated from scratch.
//
// TAILORING (A4 -- instantiate only what the requirements call for):
//   RelationTemplates::RotationToSpeed    INSTANTIATED (SYS-4, CMP-1/2, CMP-4)
//   RelationTemplates::StoppingDistance   INSTANTIATED (SYS-1, SYS-2, FUN-4/5)
//   RelationTemplates::MaxSpeedFromBudget INSTANTIATED once, as the SYS-3/SYS-4
//                                         co-satisfiability (feasibility) check
//   RequirementTemplates::LowerBoundRequirement / UpperBoundRequirement -- both used
//   RoverStructure::ReflectanceSensor     NOT ALLOCATED (absence by traceability)
//   RoverStructure rear DistanceSensor    NOT ALLOCATED (candidate; see CMP-12)
//
// PARAMETERS ARE UNCALIBRATED, NOT ZEROED (A3).  Every attribute carrying a
// measured quantity is declared without a value and is marked TBD-nn against the
// register in section 7 of the specification.  Calibration binds them.
//
// Per the library's VALIDATION NOTE, relations are INSTANTIATED BY REPRODUCING
// the calc-def expression against bound parameters, not by calc invocation.
//
// UNITS: SI, per the standard library.  The executable model (wall_stop_model.py)
// works in mm / s / deg; each attribute below names its Python twin so the two
// views can be checked against each other mechanically (03_model_checks.py).
// ============================================================================

package WallStopModel {

    private import ISQ::*;
    private import SI::*;
    private import ScalarValues::*;
    private import RoverCommon::*;
    private import RoverStructure::*;
    private import RelationTemplates::*;
    private import RequirementTemplates::*;

    doc /*
     * One package, deliberately.  The design part claims the top need and the top
     * need takes the design part as its subject; splitting them across packages
     * would create a mutual import with no resolution order.  Keeping them
     * together makes per-package import resolution trivially checkable.
     */

    // ========================================================================
    // 1.  DESIGN SUBJECT
    // ========================================================================

    part def WallRover specializes Rover {
        doc /*
         * The rover as configured for this task.  Attribute names are the trace
         * spine: requirement -> attribute -> Python variable -> calibration
         * evidence.  The Python twin is named in each comment.
         */

        // ---- allocated effectors (specification section 5) ------------------
        part motorLeft   : DriveMotor;        // CMP-1, CMP-3, CMP-4, CMP-5
        part motorRight  : DriveMotor;        // CMP-2, CMP-3, CMP-4, CMP-5
        part rangerFwdA  : DistanceSensor;    // CMP-6, CMP-8, CMP-9, FUN-13
        part rangerFwdB  : DistanceSensor;    // CMP-7, CMP-8, CMP-9, FUN-13
        part imuUnit     : InertialUnit;      // CMP-10, FUN-9

        // The platform's rear DistanceSensor and its ReflectanceSensor are
        // inherited from Rover but NOT allocated here: no requirement traces to
        // them.  Absence by traceability, not a missing block.

        // ---- drivetrain parameters -----------------------------------------
        attribute maxWheelSpeed      : AngularVelocityValue;   // TBD-01  omega_max_deg_s
        attribute commandedWheelSpeed: AngularVelocityValue;   //         command target
        attribute speedScale         : LengthValue;            // TBD-02  k_mm_per_deg  [m/rad]
        attribute decel              : AccelerationValue;      // TBD-03  a_decel_mm_s2
        attribute symmetryDeviation  : AngularVelocityValue;   // TBD-04  sym_dev_deg_s
        attribute symmetryLimit      : AngularVelocityValue;   //         limit for CMP-3
        attribute decelLimit         : AccelerationValue;      //         floor for CMP-5

        // ---- forward ranging ------------------------------------------------
        attribute rangerRefresh      : DurationValue;          // TBD-05  T_refresh_s
        attribute rangerRefreshLimit : DurationValue;          //         limit for CMP-6/7
        attribute rangerLag          : DurationValue;          // TBD-06  tau_sensor_s
        attribute rangerNoise        : LengthValue;            // TBD-07  sigma_n_mm
        attribute rangerNoiseLimit   : LengthValue;            //         limit for CMP-8
        attribute rangeOffset        : LengthValue;            // TBD-08  b_offset_mm
        attribute validityFloor      : LengthValue;            // TBD-09  r_floor_mm
        attribute rangerPairOffset   : LengthValue;            // TBD-10  delta_AB_mm
        attribute pairOffsetLimit    : LengthValue;            // TBD-13  limit for FUN-13
        attribute sampleRate         : FrequencyValue;         //         = 1 / rangerRefresh
        attribute sampleRateFloor    : FrequencyValue;         //         floor for FUN-1

        // ---- timing chain ---------------------------------------------------
        attribute loopPeriod         : DurationValue;          // TBD-11  t_loop_s
        attribute loopPeriodLimit    : DurationValue;          //         limit for CMP-11/FUN-4
        // latency.tChain is inherited from Rover (RoverCommon::RoverLatency).
        //                                                     // TBD-12  t_chain_s

        // ---- composite stop --------------------------------------------------
        attribute responseTime       : DurationValue;          //         = rangerLag + latency.tChain
        attribute stopDistance       : LengthValue;            //         S  (derived)
        attribute stopRepeatability  : Real;                   // TBD-14  rel_sigma_S
        attribute stopSampleCount    : Real;                   // TBD-15  n_S_samples
        attribute timeToRest         : DurationValue;          //         derived
        attribute stopSettleLimit    : DurationValue;          // TBD-23  t_stop_max_s

        // ---- attitude --------------------------------------------------------
        attribute headingDeviation   : Angle;                  // TBD-17  theta_dev_deg
        attribute headingSpread      : Angle;                  // TBD-18  sigma_theta_deg
        attribute headingLimit       : Angle;                  // TBD-24  theta_max_deg
        attribute yawClearanceCoeff  : LengthValue;            // TBD-19  c_yaw_mm_per_deg
        attribute headingDrift       : Angle;                  //         CMP-10 measured
        attribute headingDriftLimit  : Angle;                  //         CMP-10 limit

        // ---- degraded mode ---------------------------------------------------
        attribute odometryError      : LengthValue;            // TBD-26  e_odo_mm
        attribute odometryErrorLimit : LengthValue;            //         limit for CMP-4/FUN-8
        attribute backstopAllowance  : LengthValue;            // TBD-27  delta_bs_mm
        attribute degradedClearance  : LengthValue;            //         derived

        // ---- trigger design and performance ----------------------------------
        attribute startRange         : LengthValue;            // TBD-29  R0_mm
        attribute triggerThreshold   : LengthValue;            //         R_trig (design output)
        attribute triggerFloor       : LengthValue;            //         lowest reachable threshold
        attribute loopBias           : LengthValue;            //         E[crossing undershoot]
        attribute finalGap           : LengthValue;            //         predicted mean gap
        attribute minClearance       : LengthValue;            //         low tail of finalGap
        attribute contactFloor       : LengthValue;            // TBD-20  contact_floor_mm = 0
        attribute gapGoal            : LengthValue;            // TBD-22  g_goal_mm
        attribute marginMultiplier   : Real;                   // TBD-21  k_sigma
        attribute requiredClearance  : LengthValue;            //         = k_sigma * gapSigma

        // ---- uncertainty budget (A6: RSS of independent contributors) ---------
        attribute quantisationSigma  : LengthValue;            //         sigma_q
        attribute stopSigma          : LengthValue;            //         sigma_S
        attribute yawSigma           : LengthValue;            //         c_yaw * headingSpread
        attribute offsetUncertainty  : LengthValue;            // TBD-16  u_b_mm
        attribute measurementSigma   : LengthValue;            // TBD-28  sigma_meas_mm
        attribute runSigma           : LengthValue;            //         scatter, run to run
        attribute systematicSigma    : LengthValue;            //         common mode
        attribute gapSigma           : LengthValue;            //         sigma_g (total)

        // ---- onboard estimate --------------------------------------------------
        attribute restReading        : LengthValue;            //         expected r at rest
        attribute estimateError      : LengthValue;            //         SYS-8 measured
        attribute estimateLimit      : LengthValue;            // TBD-25  eps_est_mm

        // ---- feasibility --------------------------------------------------------
        attribute speedBudget        : LengthValue;            //         startRange - rangeOffset
        attribute admissibleSpeed    : SpeedValue;             //         MaxSpeedFromBudget
        attribute cruiseSpeed        : SpeedValue;             //         RotationToSpeed

        // ====================================================================
        // 2.  RELATION INSTANTIATIONS
        //     Expressions reproduced from RelationTemplates against the bound
        //     parameters above (per the library VALIDATION NOTE).
        // ====================================================================

        // RelationTemplates::RotationToSpeed
        attribute cruiseSpeedValue : SpeedValue = maxWheelSpeed * speedScale;

        // RelationTemplates::StoppingDistance, margin := 0 -- the PHYSICAL stop
        // distance alone.  The margin term is carried separately below so that
        // the requirement roll-up and the trigger design use the same expression
        // with different margins, rather than two different expressions.
        attribute stopDistanceValue : LengthValue =
            cruiseSpeed * responseTime + cruiseSpeed ** 2 / (2 * decel);

        // RelationTemplates::StoppingDistance, margin := requiredClearance -- the
        // TRUE-gap distance at which the stop must already be triggered.
        attribute triggerGapValue : LengthValue =
            cruiseSpeed * responseTime + cruiseSpeed ** 2 / (2 * decel)
            + requiredClearance;

        // Sensor-frame trigger threshold: true-gap trigger, shifted into the
        // ranger's frame (+rangeOffset) and de-biased for the loop crossing.
        attribute triggerThresholdValue : LengthValue =
            triggerGapValue + rangeOffset + loopBias;

        // The governing performance relation (specification section 1.1).
        attribute finalGapValue : LengthValue =
            triggerThreshold - loopBias - stopDistance - rangeOffset;

        attribute minClearanceValue : LengthValue =
            finalGap - marginMultiplier * gapSigma;

        // Degraded mode: the odometric backstop fires instead of the ranger, and
        // carries no ranger lag -- so its response time is the command chain only.
        attribute degradedClearanceValue : LengthValue =
            triggerThreshold - backstopAllowance - odometryError
            - ( cruiseSpeed * latency.tChain + cruiseSpeed ** 2 / (2 * decel) )
            - rangeOffset;

        // RelationTemplates::MaxSpeedFromBudget -- feasibility of SYS-3 with SYS-4.
        attribute admissibleSpeedValue : SpeedValue =
            - decel * responseTime
            + ( decel ** 2 * responseTime ** 2
                + 2 * decel * (speedBudget - requiredClearance) ) ** 0.5;

        // Uncertainty roll-up (A6).
        attribute runSigmaValue : LengthValue =
            ( quantisationSigma ** 2 + stopSigma ** 2
              + rangerNoise ** 2 + yawSigma ** 2 ) ** 0.5;

        attribute systematicSigmaValue : LengthValue =
            ( stopSigma ** 2 / stopSampleCount
              + offsetUncertainty ** 2 + measurementSigma ** 2 ) ** 0.5;

        attribute gapSigmaValue : LengthValue =
            ( runSigma ** 2 + systematicSigma ** 2 ) ** 0.5;

        attribute requiredClearanceValue : LengthValue =
            marginMultiplier * gapSigma;

        // FUN-14 reachability floor: below this the ranger cannot report a crossing.
        attribute triggerFloorValue : LengthValue =
            validityFloor + marginMultiplier * rangerNoise;

        // ====================================================================
        // 3.  THE DESIGN CLAIMS THE TOP NEED
        // ====================================================================
        satisfy requirement : WallRunNeed;
    }

    // ========================================================================
    // 4.  REQUIREMENTS
    //     Each specialises a template, adds the subject, BINDS the operands
    //     against the subject's attributes, and inherits the require constraint.
    //     Decomposition is nested `requirement : Child` usages.
    // ========================================================================

    // ---- CMP leaves --------------------------------------------------------

    requirement def <'CMP-1'> MotorLeftMaxSpeed specializes LowerBoundRequirement {
        doc /* While commanded at maximum, motor L shall sustain >= 95% of its ceiling. */
        subject rover : WallRover;
        attribute :>> measured = rover.motorLeft.commandedSpeed;
        attribute :>> target   = rover.maxWheelSpeed;
    }

    requirement def <'CMP-2'> MotorRightMaxSpeed specializes LowerBoundRequirement {
        doc /* While commanded at maximum, motor R shall sustain >= 95% of its ceiling. */
        subject rover : WallRover;
        attribute :>> measured = rover.motorRight.commandedSpeed;
        attribute :>> target   = rover.maxWheelSpeed;
    }

    requirement def <'CMP-3'> MotorSpeedSymmetry specializes UpperBoundRequirement {
        doc /* The two drive motors' sustained speeds shall not differ by more than the limit. */
        subject rover : WallRover;
        attribute :>> measured = rover.symmetryDeviation;
        attribute :>> target   = rover.symmetryLimit;
    }

    requirement def <'CMP-4'> OdometryScaleAccuracy specializes UpperBoundRequirement {
        doc /* Rotation-to-ground scale error over the approach shall not exceed the limit. */
        subject rover : WallRover;
        attribute :>> measured = rover.odometryError;
        attribute :>> target   = rover.odometryErrorLimit;
    }

    requirement def <'CMP-5'> BrakingDecelFloor specializes LowerBoundRequirement {
        doc /* Commanded braking shall produce at least the deceleration floor. */
        subject rover : WallRover;
        attribute :>> measured = rover.decel;
        attribute :>> target   = rover.decelLimit;
    }

    requirement def <'CMP-6'> RangerARefresh specializes UpperBoundRequirement {
        doc /* Forward ranger A shall refresh at intervals no greater than the limit. */
        subject rover : WallRover;
        attribute :>> measured = rover.rangerFwdA.refreshInterval;
        attribute :>> target   = rover.rangerRefreshLimit;
    }

    requirement def <'CMP-7'> RangerBRefresh specializes UpperBoundRequirement {
        doc /* Forward ranger B shall refresh at intervals no greater than the limit. */
        subject rover : WallRover;
        attribute :>> measured = rover.rangerFwdB.refreshInterval;
        attribute :>> target   = rover.rangerRefreshLimit;
    }

    requirement def <'CMP-8'> FusedRangerNoise specializes UpperBoundRequirement {
        doc /* Fused forward-range noise shall not exceed the noise limit (1 sigma). */
        subject rover : WallRover;
        attribute :>> measured = rover.rangerNoise;
        attribute :>> target   = rover.rangerNoiseLimit;
    }

    requirement def <'CMP-9'> ValidityFloorBelowRest specializes UpperBoundRequirement {
        doc /* The ranger validity floor shall lie below the expected rest reading. */
        subject rover : WallRover;
        attribute :>> measured = rover.validityFloor;
        attribute :>> target   = rover.restReading;
    }

    requirement def <'CMP-10'> HeadingDriftBounded specializes UpperBoundRequirement {
        doc /* IMU heading drift shall not exceed the drift limit over a run. */
        subject rover : WallRover;
        attribute :>> measured = rover.headingDrift;
        attribute :>> target   = rover.headingDriftLimit;
    }

    requirement def <'CMP-11'> LoopPeriodBounded specializes UpperBoundRequirement {
        doc /* The control-loop period shall not exceed the loop-period limit. */
        subject rover : WallRover;
        attribute :>> measured = rover.loopPeriod;
        attribute :>> target   = rover.loopPeriodLimit;
    }

    // CMP-12 (rear ranger) and CMP-13 (reflectance sensor) are Optional-pattern
    // candidates in the specification.  Neither is realised here: no allocated
    // part exists for them, so no operand could be bound.  That absence IS the
    // model's statement of the drop-out (Rule 7), and RUN-1 logs both channels
    // once so the drop-out is evidenced rather than assumed.

    // ---- FUN level ---------------------------------------------------------

    requirement def <'FUN-1'> RangeSampleRate specializes LowerBoundRequirement {
        doc /* Forward range shall be sampled at no less than the sample-rate floor. */
        subject rover : WallRover;
        attribute :>> measured = rover.sampleRate;
        attribute :>> target   = rover.sampleRateFloor;
        requirement : RangerARefresh;   // CMP-6
        requirement : RangerBRefresh;   // CMP-7
    }

    requirement def <'FUN-2'> InterSampleExtrapolation specializes UpperBoundRequirement {
        doc /* Inter-sample extrapolation error shall stay below the ranger noise floor. */
        subject rover : WallRover;
        attribute :>> measured = rover.quantisationSigma;
        attribute :>> target   = rover.rangerNoise;
    }

    requirement def <'FUN-3'> RejectImplausibleSamples specializes UpperBoundRequirement {
        doc /* Range samples outside the plausibility bounds shall not enter the trigger. */
        subject rover : WallRover;
        attribute :>> measured = rover.validityFloor;
        attribute :>> target   = rover.restReading;
    }

    requirement def <'FUN-4'> TriggerWithinOneLoop specializes UpperBoundRequirement {
        doc /* The stop shall be commanded within one control-loop period of the crossing. */
        subject rover : WallRover;
        attribute :>> measured = rover.loopPeriod;
        attribute :>> target   = rover.loopPeriodLimit;
        requirement : LoopPeriodBounded;   // CMP-11
    }

    requirement def <'FUN-5'> MaximumBraking specializes LowerBoundRequirement {
        doc /* The stop shall apply the maximum available braking effort until rest. */
        subject rover : WallRover;
        attribute :>> measured = rover.decel;
        attribute :>> target   = rover.decelLimit;
        requirement : BrakingDecelFloor;   // CMP-5
    }

    requirement def <'FUN-6'> OdometricBackstop specializes LowerBoundRequirement {
        doc /* The odometric backstop shall command the stop with clearance remaining. */
        subject rover : WallRover;
        attribute :>> measured = rover.degradedClearance;
        attribute :>> target   = rover.contactFloor;
    }

    requirement def <'FUN-7'> TimeBackstop specializes LowerBoundRequirement {
        doc /* An elapsed-time limit shall command the stop independently of range. */
        subject rover : WallRover;
        attribute :>> measured = rover.degradedClearance;
        attribute :>> target   = rover.contactFloor;
    }

    requirement def <'FUN-8'> OdometryFromRotation specializes UpperBoundRequirement {
        doc /* Travelled distance shall be measured from drive-motor rotation. */
        subject rover : WallRover;
        attribute :>> measured = rover.odometryError;
        attribute :>> target   = rover.odometryErrorLimit;
        requirement : OdometryScaleAccuracy;   // CMP-4
    }

    requirement def <'FUN-9'> HeadingObserved specializes UpperBoundRequirement {
        doc /* Heading deviation shall be observed throughout the approach. */
        subject rover : WallRover;
        attribute :>> measured = rover.headingSpread;
        attribute :>> target   = rover.headingLimit;
        requirement : HeadingDriftBounded;   // CMP-10
    }

    requirement def <'FUN-10'> NoHotPathOutput specializes UpperBoundRequirement {
        doc /* Telemetry output shall not occur while the drive motors are commanded. */
        subject rover : WallRover;
        attribute :>> measured = rover.loopPeriod;
        attribute :>> target   = rover.loopPeriodLimit;
    }

    requirement def <'FUN-11'> DwellAveragedRest specializes UpperBoundRequirement {
        doc /* The rest range shall be reported as a dwell average. */
        subject rover : WallRover;
        attribute :>> measured = rover.estimateError;
        attribute :>> target   = rover.estimateLimit;
    }

    requirement def <'FUN-12'> SafeTermination specializes LowerBoundRequirement {
        doc /* Motors shall stop and the sentinel shall be emitted on every path. */
        subject rover : WallRover;
        attribute :>> measured = rover.minClearance;
        attribute :>> target   = rover.contactFloor;
    }

    requirement def <'FUN-13'> ForwardPairAgreement specializes UpperBoundRequirement {
        doc /* The two forward rangers shall agree to within the pair-offset limit. */
        subject rover : WallRover;
        attribute :>> measured = rover.rangerPairOffset;
        attribute :>> target   = rover.pairOffsetLimit;
        requirement : RangerARefresh;   // CMP-6
        requirement : RangerBRefresh;   // CMP-7
    }

    // ---- SYS level ---------------------------------------------------------

    requirement def <'FUN-14'> TriggerReachable specializes LowerBoundRequirement {
        doc /* The trigger threshold shall lie above the ranger's validity floor. */
        subject rover : WallRover;
        attribute :>> measured = rover.triggerThreshold;
        attribute :>> target   = rover.triggerFloor;
        requirement : ValidityFloorBelowRest;   // CMP-9
    }

    requirement def <'SYS-1'> NoContact specializes LowerBoundRequirement {
        doc /* Minimum clearance shall remain above the contact floor throughout the run. */
        subject rover : WallRover;
        attribute :>> measured = rover.minClearance;
        attribute :>> target   = rover.contactFloor;
        requirement : RangeSampleRate;   // FUN-1
        requirement : RejectImplausibleSamples;   // FUN-3
        requirement : TriggerWithinOneLoop;   // FUN-4
        requirement : ForwardPairAgreement;   // FUN-13
        requirement : TriggerReachable;   // FUN-14
    }

    requirement def <'SYS-2'> ClearanceMargin specializes LowerBoundRequirement {
        doc /* The predicted final gap shall be no less than k_sigma * gapSigma.
             * DERIVED margin requirement bridging the SYS-1 constraint and the
             * SYS-3 objective; sized as the RSS of independent contributors (A6). */
        subject rover : WallRover;
        attribute :>> measured = rover.finalGap;
        attribute :>> target   = rover.requiredClearance;
        requirement : InterSampleExtrapolation;   // FUN-2
        requirement : NoHotPathOutput;   // FUN-10
        requirement : FusedRangerNoise;   // CMP-8
    }

    requirement def <'SYS-3'> MinimiseGap specializes UpperBoundRequirement {
        doc /* OBJECTIVE (graded): the final gap should not exceed the gap goal. */
        subject rover : WallRover;
        attribute :>> measured = rover.finalGap;
        attribute :>> target   = rover.gapGoal;
    }

    requirement def <'SYS-4'> CommandMaximumSpeed specializes LowerBoundRequirement {
        doc /* While approaching, each drive motor shall be commanded at its maximum. */
        subject rover : WallRover;
        attribute :>> measured = rover.commandedWheelSpeed;
        attribute :>> target   = rover.maxWheelSpeed;
        requirement : MotorLeftMaxSpeed;   // CMP-1
        requirement : MotorRightMaxSpeed;   // CMP-2
    }

    requirement def <'SYS-5'> CompleteStop specializes UpperBoundRequirement {
        doc /* The rover shall reach rest within the settle limit. */
        subject rover : WallRover;
        attribute :>> measured = rover.timeToRest;
        attribute :>> target   = rover.stopSettleLimit;
        requirement : MaximumBraking;   // FUN-5
    }

    requirement def <'SYS-6'> HeadingWithinLimit specializes UpperBoundRequirement {
        doc /* Heading deviation shall not exceed the heading limit up to the trigger. */
        subject rover : WallRover;
        attribute :>> measured = rover.headingDeviation;
        attribute :>> target   = rover.headingLimit;
        requirement : HeadingObserved;   // FUN-9
        requirement : MotorSpeedSymmetry;   // CMP-3
    }

    requirement def <'SYS-7'> DegradedStopClearance specializes LowerBoundRequirement {
        doc /* With the forward-range channel unusable, the stop shall still clear the wall. */
        subject rover : WallRover;
        attribute :>> measured = rover.degradedClearance;
        attribute :>> target   = rover.contactFloor;
        requirement : OdometricBackstop;   // FUN-6
        requirement : TimeBackstop;   // FUN-7
        requirement : OdometryFromRotation;   // FUN-8
    }

    requirement def <'SYS-8'> GapEstimateAccuracy specializes UpperBoundRequirement {
        doc /* The onboard final-gap estimate error shall not exceed the estimate limit. */
        subject rover : WallRover;
        attribute :>> measured = rover.estimateError;
        attribute :>> target   = rover.estimateLimit;
        requirement : DwellAveragedRest;   // FUN-11
        requirement : ValidityFloorBelowRest;   // CMP-9
    }

    requirement def <'SYS-9'> RunIndependence specializes LowerBoundRequirement {
        doc /* No state shall be carried across runs. */
        subject rover : WallRover;
        attribute :>> measured = rover.minClearance;
        attribute :>> target   = rover.contactFloor;
        requirement : SafeTermination;   // FUN-12
    }

    // ---- STK level ---------------------------------------------------------

    requirement def <'STK-1'> StkNoContact specializes LowerBoundRequirement {
        doc /* The rover shall not make contact with the wall. */
        subject rover : WallRover;
        attribute :>> measured = rover.minClearance;
        attribute :>> target   = rover.contactFloor;
        requirement : NoContact;   // SYS-1
        requirement : ClearanceMargin;   // SYS-2
        requirement : HeadingWithinLimit;   // SYS-6
        requirement : DegradedStopClearance;   // SYS-7
    }

    requirement def <'STK-2'> StkMinimiseGap specializes UpperBoundRequirement {
        doc /* OBJECTIVE: the rover should minimise the final gap. */
        subject rover : WallRover;
        attribute :>> measured = rover.finalGap;
        attribute :>> target   = rover.gapGoal;
        requirement : MinimiseGap;   // SYS-3
        requirement : ClearanceMargin;   // SYS-2
    }

    requirement def <'STK-3'> StkMaximumSpeed specializes LowerBoundRequirement {
        doc /* The rover shall travel at maximum speed while approaching. */
        subject rover : WallRover;
        attribute :>> measured = rover.cruiseSpeed;
        attribute :>> target   = rover.admissibleSpeed;
        requirement : CommandMaximumSpeed;   // SYS-4
    }

    requirement def <'STK-4'> StkCompleteStop specializes UpperBoundRequirement {
        doc /* The rover shall come to a complete stop. */
        subject rover : WallRover;
        attribute :>> measured = rover.timeToRest;
        attribute :>> target   = rover.stopSettleLimit;
        requirement : CompleteStop;   // SYS-5
        requirement : SafeTermination;   // FUN-12
    }

    requirement def <'STK-5'> StkGapEstimate specializes UpperBoundRequirement {
        doc /* The rover shall report an onboard final-gap estimate per run. */
        subject rover : WallRover;
        attribute :>> measured = rover.estimateError;
        attribute :>> target   = rover.estimateLimit;
        requirement : GapEstimateAccuracy;   // SYS-8
    }

    requirement def <'STK-6'> StkRunIndependence specializes LowerBoundRequirement {
        doc /* Each run shall be independent of every other run. */
        subject rover : WallRover;
        attribute :>> measured = rover.minClearance;
        attribute :>> target   = rover.contactFloor;
        requirement : RunIndependence;   // SYS-9
    }

    // ---- Top need ----------------------------------------------------------

    requirement def <'NEED'> WallRunNeed specializes LowerBoundRequirement {
        doc /*
         * The stakeholder need: stop as close to the wall as possible without
         * touching it, at maximum speed.  Its own operands are the contact
         * constraint, because contact is the outcome that voids the run; the
         * objective enters through STK-2 beneath it.
         */
        subject rover : WallRover;
        attribute :>> measured = rover.minClearance;
        attribute :>> target   = rover.contactFloor;
        requirement : StkNoContact;   // STK-1
        requirement : StkMinimiseGap;   // STK-2
        requirement : StkMaximumSpeed;   // STK-3
        requirement : StkCompleteStop;   // STK-4
        requirement : StkGapEstimate;   // STK-5
        requirement : StkRunIndependence;   // STK-6
    }
}
