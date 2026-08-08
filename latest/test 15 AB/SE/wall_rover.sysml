// ============================================================================
// wall_rover.sysml — TAILORED task model for the wall-approach run.
//
// Tailored from rover_generic.sysml (RoverStructure skeleton + RelationTemplates
// + RequirementTemplates). Only the templates the requirements call for are
// instantiated:
//   RotationToSpeed     -> vCruise               (CMP-15)
//   StoppingDistance    -> stopDistanceRequired  (FUN-3)
//   MaxSpeedFromBudget  -> vMaxFromBudget        (SYS-3, feasibility)
//   LowerBoundRequirement / UpperBoundRequirement -> every requirement shape
// Relations are instantiated by REPRODUCING the template expression against
// bound parameters (per the validation note in rover_generic.sysml), not by
// calc invocation.
//
// ABSENCE BY TRACEABILITY. RoverStructure::Rover::floor (ReflectanceSensor) is
// inherited from the platform but NO requirement traces to it; it is excluded
// from the operational architecture and is not constructed by the flight
// program. The rear ranger is traced only by CMP-13 (Optional, characterization
// cross-source) and is likewise absent from the flight program.
//
// UNITS. This view carries SI (m, s, m/s, m/s^2, rad); the executable view
// (wall_rover_model.py) carries mm, ms, deg. The trace spine in the requirements
// specification states the mapping for every parameter; the two views are
// numerically identical after conversion.
//
// TENET A3. No attribute below carries a value: parameters are UNCALIBRATED,
// not zeroed. Calibration binds them; the executable model refuses to compute
// on an unbound parameter.
// ============================================================================

package WallRunStructure {
    doc /*
     * The tailored design part: the generic Rover specialised to the effector
     * complement the requirements select, carrying every quantity the
     * requirement operands bind against.
     */

    private import ISQ::*;
    private import SI::*;
    private import ScalarValues::*;
    private import RoverCommon::*;
    private import RoverStructure::*;

    part def WallRover specializes Rover {

        // ---- selected effector complement (absence by traceability) --------
        part :>> motors  : DriveMotor [2];       // CMP-6..CMP-9, CMP-15
        part :>> rangers : DistanceSensor [3];   // 2 forward: CMP-1..CMP-5
                                                 // 1 rear:    CMP-13 (Optional)
        part :>> imu     : InertialUnit;         // CMP-11 (yaw), CMP-12 (accel)
        // inherited: part floor : ReflectanceSensor — UNTRACED, excluded.

        // ---- drivetrain -----------------------------------------------------
        attribute motorSpeedCmd      : AngularVelocityValue;   // TBD-03
        attribute motorSpeedMax      : AngularVelocityValue;   // TBD-03
        attribute motorSpeedAchLeft  : AngularVelocityValue;   // TBD-03
        attribute motorSpeedAchRight : AngularVelocityValue;   // TBD-03
        attribute kOdo               : LengthValue;            // TBD-02 (m/rad)
        attribute driveAsymmetry      : AngularVelocityValue;  // TBD-14b
        attribute driveAsymmetryLimit : AngularVelocityValue;  // allocated
        attribute stopAngleLeft   : Angle;                     // TBD-09b
        attribute stopAngleRight  : Angle;                     // TBD-09b
        attribute stopAngleLimit  : Angle;                     // allocated
        attribute brakeCommandSkew      : DurationValue;       // TBD-07b
        attribute brakeCommandSkewLimit : DurationValue;       // allocated
        // RelationTemplates::RotationToSpeed reproduced:
        attribute vCruise : SpeedValue = motorSpeedCmd * kOdo;  // TBD-01

        // ---- fused forward ranging channel ---------------------------------
        attribute kUs           : Real;          // TBD-11  scale
        attribute cUs           : LengthValue;   // TBD-10  reading -> front face
        attribute tauSensor     : DurationValue; // TBD-04  reporting lag
        attribute tauLimit      : DurationValue; // allocated
        attribute tRefresh      : DurationValue; // TBD-05  refresh interval
        attribute tRefreshLimit : DurationValue; // allocated
        attribute sigmaUs       : LengthValue;   // TBD-13  reading noise 1-sigma
        attribute sigmaKUs      : Real;          // TBD-11b scale uncertainty
        attribute rangeValidMin : LengthValue;   // TBD-12  near-range floor
        attribute rangeValidMax : LengthValue;   // allocated (no-object sentinel)
        attribute rAnchor       : LengthValue;   // reading at which cUs anchored
        attribute rangerFLResidual        : LengthValue;  // TBD-11c
        attribute rangerFRResidual        : LengthValue;  // TBD-11c
        attribute rangerResidualTolerance : LengthValue;  // allocated

        // ---- timing chain ---------------------------------------------------
        attribute loopPeriod        : DurationValue;   // TBD-06
        attribute loopPeriodLimit   : DurationValue;   // allocated
        attribute tResponseLimit    : DurationValue;   // allocated
        attribute clearanceUpdateInterval : DurationValue;  // TBD-06b
        attribute clearanceUpdateLimit    : DurationValue;  // allocated
        attribute headingSampleInterval   : DurationValue;  // TBD-06c
        attribute headingSampleLimit      : DurationValue;  // allocated
        // latency : RoverLatency is inherited; latency.tChain = TBD-07
        attribute tResponse : DurationValue =
            tauSensor + loopPeriod / 2 + latency.tChain;

        // ---- stop dynamics ---------------------------------------------------
        attribute aBrake         : AccelerationValue;  // TBD-08
        attribute stopTravel     : LengthValue;        // TBD-09 measured composite
        attribute stopSettleTime : DurationValue;      // TBD-19
        attribute stopTimeLimit  : DurationValue;      // allocated

        // ---- attitude / geometry ---------------------------------------------
        attribute headingDeviation    : Angle;        // TBD-14 (vs anchor attitude)
        attribute headingLimit        : Angle;        // allocated
        attribute headingDriftStatic  : Angle;        // TBD-14c
        attribute headingDriftLimit   : Angle;        // allocated
        attribute halfWidth           : LengthValue;  // TBD-15 (prior-bounded)
        // small-angle form; |error| < 0.13 % at headingDeviation = 5 deg
        attribute yawPenalty : LengthValue = halfWidth * headingDeviation;

        // ---- scenario ---------------------------------------------------------
        attribute dStart           : LengthValue;   // TBD-20 start-line gap
        attribute contactThreshold : LengthValue;   // allocated (0)
        attribute coverageFactor   : Real;          // allocated (3)
        attribute travelAtStop     : LengthValue;   // TBD-09c
        attribute travelInterlock  : LengthValue;   // derived fail-safe limit

        // ---- dispersions (tenet A6: RSS of independent contributors) ----------
        attribute sigmaVFrac     : Real;          // TBD-17
        attribute sigmaBrakeFrac : Real;          // TBD-16
        attribute sigmaCUs       : LengthValue;   // TBD-10b anchor residual
        attribute sStale  : LengthValue = tRefresh   / 12 ** 0.5 * vCruise;
        attribute sLoop   : LengthValue = loopPeriod / 12 ** 0.5 * vCruise;
        attribute sBrake  : LengthValue = sigmaBrakeFrac * (vCruise ** 2 / (2 * aBrake));
        attribute sSpeed  : LengthValue = (tResponse + vCruise / aBrake)
                                          * sigmaVFrac * vCruise;
        attribute sRead   : LengthValue = 0.8 * sigmaUs;
        attribute sOffset : LengthValue = sigmaCUs;
        attribute sScale  : LengthValue = sigmaKUs * (rTrigger - rAnchor);
        attribute sYaw    : LengthValue = 0.5 * yawPenalty;
        attribute sigmaGap : LengthValue =
            ( sStale ** 2 + sLoop ** 2 + sBrake ** 2 + sSpeed ** 2
            + sRead ** 2 + sOffset ** 2 + sScale ** 2 + sYaw ** 2 ) ** 0.5;

        // ---- design variable and predicted performance ------------------------
        attribute rTrigger : LengthValue;         // DESIGN: trigger threshold
        attribute trueRangeAtTrigger : LengthValue = kUs * rTrigger + cUs;
        attribute safetyMargin : LengthValue = coverageFactor * sigmaGap;

        // RelationTemplates::StoppingDistance reproduced:
        attribute stopDistanceRequired : LengthValue =
            vCruise * tResponse + vCruise ** 2 / (2 * aBrake) + safetyMargin;

        // RelationTemplates::MaxSpeedFromBudget reproduced (feasibility):
        attribute vMaxFromBudget : SpeedValue =
            - aBrake * tResponse
            + ( aBrake ** 2 * tResponse ** 2
              + 2 * aBrake * (dStart - safetyMargin) ) ** 0.5;

        attribute predictedGap : LengthValue =
            trueRangeAtTrigger - stopTravel - yawPenalty;
        // Braking-only deceleration => a monotonic approach => the minimum
        // clearance over the run IS the final clearance.
        attribute finalClearance : LengthValue = predictedGap;
        attribute minClearance   : LengthValue = predictedGap;

        // ---- onboard estimators (FUN-11 / SYS-8) -------------------------------
        attribute restReading      : LengthValue = (predictedGap - cUs) / kUs;
        attribute gapEstimate      : LengthValue;   // primary: at-rest ranging
        attribute gapEstimateOdo   : LengthValue;   // fallback: ranging + odometry
        attribute estimatorDelta   : LengthValue;   // |primary - fallback|
        attribute estimatorDeltaTolerance : LengthValue;  // allocated
        attribute estimatorError     : LengthValue; // |estimate - ground truth|
        attribute estimatorTolerance : LengthValue; // TBD-18

        // ---- cross-source residuals -------------------------------------------
        attribute odoResidual            : LengthValue;  // TBD-02b
        attribute odoResidualTolerance   : LengthValue;  // allocated
        attribute decelResidual          : Real;         // TBD-08b
        attribute decelResidualTolerance : Real;         // allocated
        attribute rearTravelResidual     : LengthValue;  // TBD-21
        attribute rearTravelTolerance    : LengthValue;  // allocated
        attribute speedResidual          : SpeedValue;   // TBD-01b
        attribute speedResidualTolerance : SpeedValue;   // allocated

        // ---- evidence ----------------------------------------------------------
        attribute evidenceFieldsEmitted  : Real;
        attribute evidenceFieldsRequired : Real;
        attribute channelsLogged         : Real;
        attribute channelsCatalogued     : Real;

        satisfy requirement : WallRunRequirements::WallRunNeed;
    }
}

package WallRunRequirements {
    doc /*
     * Formal realisation of requirements_spec.md (the source of truth).
     * Each task requirement SPECIALISES a catalog shape, adds the subject,
     * and BINDS the inherited operands; the require constraint is inherited,
     * so the evaluable logic lives once, in RequirementTemplates.
     * GENERATED from model_reqs.py by build_model.py -- do not hand-edit.
     */

    private import RequirementTemplates::*;
    private import WallRunStructure::*;

    // ---------------- CMP ----------------
    requirement def <'CMP-1'> RangerFLResidual specializes UpperBoundRequirement {
        // The forward-left ranger shall report range with a residual against
        // wheel odometry of no more than the allocated bound over 120..1000
        // mm.
        subject rover : WallRover;
        attribute :>> measured = rover.rangerFLResidual;
        attribute :>> target   = rover.rangerResidualTolerance;
    }

    requirement def <'CMP-2'> RangerFRResidual specializes UpperBoundRequirement {
        // The forward-right ranger shall report range with a residual
        // against wheel odometry of no more than the allocated bound over
        // 120..1000 mm.
        subject rover : WallRover;
        attribute :>> measured = rover.rangerFRResidual;
        attribute :>> target   = rover.rangerResidualTolerance;
    }

    requirement def <'CMP-3'> NearRangeFloor specializes UpperBoundRequirement {
        // The fused ranging channel's near-range validity floor shall be no
        // greater than the at-rest reading used by the primary estimator.
        subject rover : WallRover;
        attribute :>> measured = rover.rangeValidMin;
        attribute :>> target   = rover.restReading;
    }

    requirement def <'CMP-4'> ReportingLagBound specializes UpperBoundRequirement {
        // The fused ranging channel's reporting lag shall not exceed the
        // allocated bound.
        subject rover : WallRover;
        attribute :>> measured = rover.tauSensor;
        attribute :>> target   = rover.tauLimit;
    }

    requirement def <'CMP-5'> RefreshBound specializes UpperBoundRequirement {
        // The fused ranging channel's refresh interval shall not exceed the
        // allocated bound.
        subject rover : WallRover;
        attribute :>> measured = rover.tRefresh;
        attribute :>> target   = rover.tRefreshLimit;
    }

    requirement def <'CMP-6'> LeftMotorCruise specializes LowerBoundRequirement {
        // While cruising, the left drive motor shall sustain at least 98% of
        // its commanded speed.
        subject rover : WallRover;
        attribute :>> measured = rover.motorSpeedAchLeft;
        attribute :>> target   = rover.motorSpeedCmd * 0.98;
    }

    requirement def <'CMP-7'> RightMotorCruise specializes LowerBoundRequirement {
        // While cruising, the right drive motor shall sustain at least 98%
        // of its commanded speed.
        subject rover : WallRover;
        attribute :>> measured = rover.motorSpeedAchRight;
        attribute :>> target   = rover.motorSpeedCmd * 0.98;
    }

    requirement def <'CMP-8'> LeftMotorBrakes specializes UpperBoundRequirement {
        // When braking is commanded, the left drive motor shall come to rest
        // within the allocated bound of further rotation.
        subject rover : WallRover;
        attribute :>> measured = rover.stopAngleLeft;
        attribute :>> target   = rover.stopAngleLimit;
    }

    requirement def <'CMP-9'> RightMotorBrakes specializes UpperBoundRequirement {
        // When braking is commanded, the right drive motor shall come to
        // rest within the allocated bound of further rotation.
        subject rover : WallRover;
        attribute :>> measured = rover.stopAngleRight;
        attribute :>> target   = rover.stopAngleLimit;
    }

    requirement def <'CMP-10'> OdometryScale specializes UpperBoundRequirement {
        // The wheel-odometry channel shall track the ranging channel over
        // the calibrated traverse with a residual of no more than the
        // allocated bound.
        subject rover : WallRover;
        attribute :>> measured = rover.odoResidual;
        attribute :>> target   = rover.odoResidualTolerance;
    }

    requirement def <'CMP-11'> HeadingDrift specializes UpperBoundRequirement {
        // While the rover is at rest, the IMU heading channel shall drift by
        // no more than the allocated bound over the run duration.
        subject rover : WallRover;
        attribute :>> measured = rover.headingDriftStatic;
        attribute :>> target   = rover.headingDriftLimit;
    }

    requirement def <'CMP-12'> DecelCrossSource specializes UpperBoundRequirement {
        // Where the IMU forward-acceleration channel is available, the rover
        // shall record it during braking, agreeing with the odometry-derived
        // deceleration to within the allocated bound.
        subject rover : WallRover;
        attribute :>> measured = rover.decelResidual;
        attribute :>> target   = rover.decelResidualTolerance;
    }

    requirement def <'CMP-13'> RearRangeCrossSource specializes UpperBoundRequirement {
        // Where a valid rear reference surface is present, the rover shall
        // record rear range before motion and after the stop, agreeing with
        // wheel odometry to within the allocated bound.
        subject rover : WallRover;
        attribute :>> measured = rover.rearTravelResidual;
        attribute :>> target   = rover.rearTravelTolerance;
    }

    requirement def <'CMP-14'> LoopPeriodBound specializes UpperBoundRequirement {
        // The control-loop period shall not exceed the allocated bound,
        // hub-clock measured.
        subject rover : WallRover;
        attribute :>> measured = rover.loopPeriod;
        attribute :>> target   = rover.loopPeriodLimit;
    }

    requirement def <'CMP-15'> GroundSpeedRelation specializes UpperBoundRequirement {
        // The rotation-to-speed constant shall reproduce the ranging-derived
        // ground speed to within the allocated bound.
        subject rover : WallRover;
        attribute :>> measured = rover.speedResidual;
        attribute :>> target   = rover.speedResidualTolerance;
    }

    // ---------------- FUN ----------------
    requirement def <'FUN-1'> ClearanceUpdateRate specializes UpperBoundRequirement {
        // While driving, the rover shall refresh its fused forward-clearance
        // estimate at intervals not exceeding the allocated bound.
        subject rover : WallRover;
        attribute :>> measured = rover.clearanceUpdateInterval;
        attribute :>> target   = rover.clearanceUpdateLimit;
        requirement : RangerFLResidual;
        requirement : RangerFRResidual;
        requirement : LoopPeriodBound;
    }

    requirement def <'FUN-2'> TriggerLatency specializes UpperBoundRequirement {
        // When the fused forward clearance falls to or below the trigger
        // threshold, the rover shall command braking within the allocated
        // bound.
        subject rover : WallRover;
        attribute :>> measured = rover.tResponse;
        attribute :>> target   = rover.tResponseLimit;
        requirement : ReportingLagBound;
        requirement : RefreshBound;
    }

    requirement def <'FUN-3'> TriggerSizing specializes LowerBoundRequirement {
        // The rover's true range at the trigger instant shall be no less
        // than its stopping distance plus the derived safety margin.
        subject rover : WallRover;
        attribute :>> measured = rover.trueRangeAtTrigger;
        attribute :>> target   = rover.stopDistanceRequired;
        requirement : GroundSpeedRelation;
    }

    requirement def <'FUN-4a'> TriggerAboveFloor specializes LowerBoundRequirement {
        // The rover shall not base a trigger decision on a range reading
        // below the ranging channel's near-range validity floor.
        subject rover : WallRover;
        attribute :>> measured = rover.rTrigger;
        attribute :>> target   = rover.rangeValidMin;
        requirement : NearRangeFloor;
    }

    requirement def <'FUN-4b'> TriggerBelowCeiling specializes UpperBoundRequirement {
        // The rover shall not base a trigger decision on a range reading
        // above the ranging channel's far-range validity ceiling.
        subject rover : WallRover;
        attribute :>> measured = rover.rTrigger;
        attribute :>> target   = rover.rangeValidMax;
    }

    requirement def <'FUN-5'> TravelInterlock specializes UpperBoundRequirement {
        // When wheel-odometry travel exceeds the interlock limit, the rover
        // shall command braking independently of the ranging channel.
        subject rover : WallRover;
        attribute :>> measured = rover.travelAtStop;
        attribute :>> target   = rover.travelInterlock;
        requirement : OdometryScale;
    }

    requirement def <'FUN-6'> SymmetricDrive specializes UpperBoundRequirement {
        // While cruising, the rover shall command both drive motors at equal
        // magnitude in the forward sense.
        subject rover : WallRover;
        attribute :>> measured = rover.driveAsymmetry;
        attribute :>> target   = rover.driveAsymmetryLimit;
        requirement : LeftMotorCruise;
        requirement : RightMotorCruise;
    }

    requirement def <'FUN-7'> BrakingMode specializes UpperBoundRequirement {
        // When braking is commanded, the rover shall apply the drivetrain
        // braking mode to both motors within the allocated bound.
        subject rover : WallRover;
        attribute :>> measured = rover.brakeCommandSkew;
        attribute :>> target   = rover.brakeCommandSkewLimit;
        requirement : LeftMotorBrakes;
        requirement : RightMotorBrakes;
    }

    requirement def <'FUN-8'> HeadingMeasurement specializes UpperBoundRequirement {
        // While driving, the rover shall sample heading at intervals not
        // exceeding the allocated bound.
        subject rover : WallRover;
        attribute :>> measured = rover.headingSampleInterval;
        attribute :>> target   = rover.headingSampleLimit;
        requirement : HeadingDrift;
    }

    requirement def <'FUN-9'> StopEvidence specializes LowerBoundRequirement {
        // When motion has ceased, the rover shall emit the trigger-instant
        // fused range, the at-rest fused range and the trigger-to-rest
        // travel.
        subject rover : WallRover;
        attribute :>> measured = rover.evidenceFieldsEmitted;
        attribute :>> target   = rover.evidenceFieldsRequired;
    }

    requirement def <'FUN-10'> ChannelLogging specializes LowerBoundRequirement {
        // The rover shall log every catalogued channel bearing on the
        // quantities a run touches, off the timing-critical path.
        subject rover : WallRover;
        attribute :>> measured = rover.channelsLogged;
        attribute :>> target   = rover.channelsCatalogued;
        requirement : DecelCrossSource;
        requirement : RearRangeCrossSource;
    }

    requirement def <'FUN-11'> DualEstimator specializes UpperBoundRequirement {
        // The rover shall compute the final gap on two independent channels
        // and emit both, agreeing to within the allocated bound.
        subject rover : WallRover;
        attribute :>> measured = rover.estimatorDelta;
        attribute :>> target   = rover.estimatorDeltaTolerance;
        requirement : RangerFLResidual;
        requirement : RangerFRResidual;
        requirement : NearRangeFloor;
        requirement : OdometryScale;
    }

    // ---------------- SYS ----------------
    requirement def <'SYS-1'> NoContact specializes LowerBoundRequirement {
        // The rover shall not reduce its clearance to the wall to the
        // contact threshold at any point during a run.
        subject rover : WallRover;
        attribute :>> measured = rover.predictedGap;
        attribute :>> target   = rover.contactThreshold;
        requirement : ClearanceUpdateRate;
        requirement : TriggerLatency;
        requirement : TriggerSizing;
        requirement : TriggerAboveFloor;
        requirement : TriggerBelowCeiling;
        requirement : TravelInterlock;
    }

    requirement def <'SYS-2'> CompleteStop specializes UpperBoundRequirement {
        // When braking is commanded, the rover shall reach a complete stop
        // within the allocated bound.
        subject rover : WallRover;
        attribute :>> measured = rover.stopSettleTime;
        attribute :>> target   = rover.stopTimeLimit;
        requirement : BrakingMode;
    }

    requirement def <'SYS-3'> SpeedFeasibility specializes UpperBoundRequirement {
        // The rover's commanded cruise speed shall not exceed the maximum
        // speed stoppable within the approach budget.
        subject rover : WallRover;
        attribute :>> measured = rover.vCruise;
        attribute :>> target   = rover.vMaxFromBudget;
    }

    requirement def <'SYS-4'> MarginFloor specializes LowerBoundRequirement {
        // The rover's predicted final gap shall be no less than the coverage
        // factor times the root-sum-square dispersion of the final gap.
        subject rover : WallRover;
        attribute :>> measured = rover.predictedGap;
        attribute :>> target   = rover.safetyMargin;
        requirement : TriggerSizing;
    }

    requirement def <'SYS-5'> MaximumSpeed specializes LowerBoundRequirement {
        // While cruising, the rover shall command each drive motor at no
        // less than its achievable maximum speed.
        subject rover : WallRover;
        attribute :>> measured = rover.motorSpeedCmd;
        attribute :>> target   = rover.motorSpeedMax;
        requirement : SymmetricDrive;
    }

    requirement def <'SYS-6'> Straightness specializes UpperBoundRequirement {
        // The rover's heading deviation from its start heading shall not
        // exceed the allocated bound throughout the approach.
        subject rover : WallRover;
        attribute :>> measured = rover.headingDeviation;
        attribute :>> target   = rover.headingLimit;
        requirement : HeadingMeasurement;
    }

    requirement def <'SYS-7'> RunEvidence specializes LowerBoundRequirement {
        // After each run the rover shall emit the quantities from which its
        // final gap is computed.
        subject rover : WallRover;
        attribute :>> measured = rover.evidenceFieldsEmitted;
        attribute :>> target   = rover.evidenceFieldsRequired;
        requirement : StopEvidence;
        requirement : ChannelLogging;
    }

    requirement def <'SYS-8'> EstimatorValidated specializes UpperBoundRequirement {
        // The rover's onboard final-gap estimate shall agree with operator
        // ground truth at the operating point to within the allocated bound.
        subject rover : WallRover;
        attribute :>> measured = rover.estimatorError;
        attribute :>> target   = rover.estimatorTolerance;
        requirement : DualEstimator;
    }

    // ---------------- STK ----------------
    requirement def <'STK-1'> StopWithoutContact specializes LowerBoundRequirement {
        // The rover shall come to a complete stop ahead of the wall without
        // contacting it.
        subject rover : WallRover;
        attribute :>> measured = rover.predictedGap;
        attribute :>> target   = rover.contactThreshold;
        requirement : NoContact;
        requirement : CompleteStop;
        requirement : SpeedFeasibility;
    }

    requirement def <'STK-2'> MinimiseGap specializes UpperBoundRequirement {
        // The rover should minimise the final gap between its front-most
        // point and the wall. [OBJECTIVE - graded]
        subject rover : WallRover;
        attribute :>> measured = rover.predictedGap;
        attribute :>> target   = rover.safetyMargin;
        requirement : MarginFloor;
        requirement : EstimatorValidated;
    }

    requirement def <'STK-3'> ApproachAtMaximumSpeed specializes LowerBoundRequirement {
        // While approaching the wall, the rover shall drive at maximum
        // speed.
        subject rover : WallRover;
        attribute :>> measured = rover.motorSpeedCmd;
        attribute :>> target   = rover.motorSpeedMax;
        requirement : MaximumSpeed;
    }

    requirement def <'STK-4'> DriveStraight specializes UpperBoundRequirement {
        // The rover shall drive straight at the wall.
        subject rover : WallRover;
        attribute :>> measured = rover.headingDeviation;
        attribute :>> target   = rover.headingLimit;
        requirement : Straightness;
    }

    requirement def <'STK-5'> RunEvidenceNeed specializes UpperBoundRequirement {
        // The rover shall produce, for each run, onboard evidence of its
        // final gap sufficient for the close-out reconciliation.
        subject rover : WallRover;
        attribute :>> measured = rover.estimatorError;
        attribute :>> target   = rover.estimatorTolerance;
        requirement : RunEvidence;
        requirement : EstimatorValidated;
    }

    // ---------------- top need ----------------
    requirement def WallRunNeed {
        // The rover comes to a complete stop as close to the wall as
        // achievable without contacting it, having approached at maximum
        // speed, with per-run evidence of where it stopped.
        subject rover : WallRover;
        requirement : StopWithoutContact;
        requirement : MinimiseGap;
        requirement : ApproachAtMaximumSpeed;
        requirement : DriveStraight;
        requirement : RunEvidenceNeed;
    }
}
