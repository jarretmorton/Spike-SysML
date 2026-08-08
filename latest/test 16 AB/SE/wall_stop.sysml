// ============================================================================
// wall_stop.sysml — TASK model, tailored from rover_generic.sysml.
//
// Task: approach a wall at maximum speed from a ~1000 mm start line and stop as
// close as possible without contact.
//
// TAILORING RULE (tenet A4): only the templates the requirements call for are
// instantiated.  Instantiated: RelationTemplates::RotationToSpeed,
// RelationTemplates::StoppingDistance, RequirementTemplates::LowerBound-,
// UpperBoundRequirement.  NOT instantiated: RelationTemplates::MaxSpeedFromBudget
// — no requirement asks for a speed to be derived from a distance budget; the
// approach speed is a hard constraint (STK-4 "maximum"), not a free variable.
//
// PARAMETER POLICY (tenet A3): every calibrated attribute below is declared and
// left UNBOUND.  Values arrive from the Calibration Report and are recorded in
// the Verification Plan; none is defaulted here.
//
// COMPUTATION: the arithmetic of every relation and every require constraint is
// realised 1:1 in wallstop_model.py.  Attribute name == Python field name (see
// wallstop_model.TRACE).  A disagreement between the two is a defect.
//
// VALIDATION NOTE: constructs restricted to the forms proven in
// rover_generic.sysml — part def / attribute def / specializes / redefinition-
// with-binding (:>>) / requirement def with inherited require constraint /
// nested requirement usages / satisfy.  Relations are instantiated by
// REPRODUCING the calc def expression against bound attributes, per the
// generic file's validation note.  Expressions use only + - * / ** .
// ============================================================================

package WallStopStructure {
    doc /*
     * The effector complement SELECTED by the requirement trace, and the bound
     * task quantities.  Effectors present on the platform but with no
     * requirement tracing to them are absent here by traceability, not by
     * oversight — see the ABSENCE BY TRACEABILITY note at the end of the package.
     */

    private import ISQ::*;
    private import SI::*;
    private import ScalarValues::*;
    private import RoverCommon::*;
    private import RoverStructure::*;

    // ---------------------------------------------------------------- parts

    part def ForwardRanger specializes DistanceSensor {
        doc /* A forward-facing ultrasonic ranger. */

        // Longitudinal station of the sensing face BEHIND the rover's foremost
        // point.  reported range = rangeScale * trueClearance + longitudinalOffset
        attribute longitudinalOffset : LengthValue;   // UNCALIBRATED  TBD-01/02
        attribute offsetUncertainty  : LengthValue;   // UNCALIBRATED  1-sigma
        attribute rangeScale         : Real;          // UNCALIBRATED  TBD-18
        attribute noiseSigma         : LengthValue;   // UNCALIBRATED  TBD-07
        attribute minValidRange      : LengthValue;   // UNCALIBRATED  TBD-09
        attribute refreshIntervalLimit : DurationValue;  // requirement target
        attribute validityCheckCount : Real;          // evidence count, CMP-4
    }

    part def RearRanger specializes DistanceSensor {
        doc /* Rear-facing ranger.  CONDITIONAL: retained only if it returns an
             * in-range reading at the start line (CMP-13).  Otherwise it drops
             * out by traceability at GATE B. */
        attribute validAtStartCount : Real;           // evidence count, CMP-13
    }

    part def WallDriveMotor specializes DriveMotor {
        doc /* One of the two differential drive motors. */
        attribute travelPerAngle   : LengthValue;     // UNCALIBRATED  TBD-03 (k)
        attribute travelPerAngleFloor : LengthValue;  // requirement target
        attribute brakeDecel       : AccelerationValue;  // UNCALIBRATED TBD-05
        attribute brakeDecelFloor  : AccelerationValue;  // requirement target
        attribute maxCommandedSpeed : AngularVelocityValue;  // trim headroom check
    }

    // ------------------------------------------------------------ the rover

    part def WallRover specializes Rover {
        doc /* The task rover: two drive motors, two forward rangers, the IMU,
             * and (conditionally) the rear ranger. */

        part driveLeft   : WallDriveMotor;
        part driveRight  : WallDriveMotor;
        part rangerA     : ForwardRanger;
        part rangerB     : ForwardRanger;
        part rangerRear  : RearRanger;              // CONDITIONAL — see CMP-13

        // inherited from Rover: imu : InertialUnit  — ALLOCATED (CMP-9, CMP-14)
        // inherited from Rover: floor : ReflectanceSensor — UNALLOCATED, dropped
        // inherited from Rover: latency : RoverLatency — ALLOCATED into tResponse

        // ------------------------------------------------- calibrated inputs
        attribute vMaxAchievable   : SpeedValue;         // UNCALIBRATED TBD-04
        attribute vMaxFloor        : SpeedValue;         // requirement target
        attribute commandedSpeed   : AngularVelocityValue;
        attribute rangerOffset     : LengthValue;        // fused A/B offset
        attribute brakeDecel       : AccelerationValue;  // UNCALIBRATED TBD-05
        attribute tResponse        : DurationValue;      // UNCALIBRATED TBD-06
        attribute tResponseLimit   : DurationValue;      // requirement target
        attribute loopPeriod       : DurationValue;      // UNCALIBRATED TBD-08
        attribute loopPeriodLimit  : DurationValue;      // requirement target
        attribute refreshInterval  : DurationValue;      // UNCALIBRATED TBD-10
        attribute rangerNoiseSigma : LengthValue;        // UNCALIBRATED TBD-07
        attribute halfWidth        : LengthValue;        // UNCALIBRATED TBD-19
        attribute headingDeviation : Angle;              // UNCALIBRATED TBD-11
        attribute headingLimit     : Angle;              // requirement target
        attribute restSpeed        : SpeedValue;
        attribute restSpeedLimit   : SpeedValue;         // requirement target

        // ---------------------------------------------- design (chosen) inputs
        attribute targetGap        : LengthValue;        // UNBOUND until GATE B
        attribute kSigma           : Real;               // = 3

        // ---------------------------------------- 1-sigma uncertainty inputs
        attribute sigmaOffset      : LengthValue;        // UNCALIBRATED
        attribute sigmaTResponse   : DurationValue;      // UNCALIBRATED
        attribute sigmaBrakeDecel  : AccelerationValue;  // UNCALIBRATED
        attribute sigmaRunToRun    : LengthValue;        // UNCALIBRATED TBD-16

        // -------------------------------------------- evidence-count inputs
        attribute portSelfCheckCount    : Real;      // CMP-11
        attribute fallbackChannelCount  : Real;      // SYS-8 / FUN-9
        attribute persistedStateCount   : Real;      // SYS-7 / FUN-10
        attribute onboardEstimateCount  : Real;      // SYS-6 / FUN-8
        attribute restIndicatorCount    : Real;      // CMP-14
        attribute evidenceFloor         : Real;      // = 1
        attribute persistedStateLimit   : Real;      // = 0
        attribute commandedSpeedFraction : Real;     // commanded / rated max
        attribute commandedSpeedFloor    : Real;     // = 1

        // ================================================================
        // BOUND RELATIONS — RelationTemplates expressions reproduced against
        // the attributes above (calc INVOCATION not yet in the proven-valid
        // set; the calc defs remain the source of truth for the expressions).
        // ================================================================

        // RelationTemplates::RotationToSpeed( commandedSpeed, travelPerAngle )
        // clamped by the achievable ceiling: the command is deliberately larger
        // than the ceiling (STK-4 "maximum"), so vApproach == vMaxAchievable.
        attribute vApproach : SpeedValue = vMaxAchievable;

        // RelationTemplates::StoppingDistance( vApproach, tResponse, brakeDecel,
        //                                      margin = 0 )
        attribute stopDistance : LengthValue =
            vApproach * tResponse + vApproach ** 2 / (2 * brakeDecel);

        // Trigger law realised by the flight code, in TRUE-clearance terms and
        // in reported-range terms.  Recomputed every control cycle from the
        // LIVE measured speed, so a run-to-run speed change self-compensates.
        attribute triggerClearance : LengthValue = targetGap + stopDistance;
        attribute triggerRange     : LengthValue = rangerOffset + triggerClearance;

        // Predicted clearance at rest.
        attribute finalClearance : LengthValue = triggerClearance - stopDistance;

        // Tenet A6 — margin sized from uncertainty, root-sum-square of the
        // INDEPENDENT contributors.  (headingDeviation is in radians; the
        // corner-advance term uses the small-angle form, conservative by
        // +0.3 % at the requirement limit.)
        attribute sigmaGap : LengthValue =
            ( sigmaOffset ** 2
            + ( vApproach * sigmaTResponse ) ** 2
            + ( vApproach ** 2 / (2 * brakeDecel ** 2) * sigmaBrakeDecel ) ** 2
            + ( vApproach * (loopPeriod + refreshInterval) / 12 ** 0.5 ) ** 2
            + rangerNoiseSigma ** 2
            + ( halfWidth * headingDeviation ) ** 2
            + sigmaRunToRun ** 2 ) ** 0.5;

        attribute contactMargin : LengthValue = kSigma * sigmaGap;
    }

    // ---------------------------------------------------------------------
    // ABSENCE BY TRACEABILITY (GtWR rule 7, verified not assumed)
    //   Rover::floor : ReflectanceSensor — present on the platform, NOT
    //   instantiated in WallRover.  No requirement in WallRunRequirements
    //   traces to it: the quantities the task needs are clearance-to-wall,
    //   ground speed, heading and stop actuation, and downward reflectance
    //   observes none of them.  The start line's position is not needed either,
    //   because SYS-7 forbids cross-run state and the start clearance is
    //   measured directly by the forward rangers at run start.  It is
    //   identified in the port scan only so that no forward ranger can be
    //   confused with it.
    //
    //   WallRover::rangerRear : RearRanger — instantiated CONDITIONALLY, and
    //   held open by CMP-13.  It is a candidate independent channel for
    //   travelled distance (GtWR rule 6, cross-sourcing).  If the C1 static
    //   read shows it out of range at the start line it carries no quantity and
    //   drops out at GATE B on evidence.
    // ---------------------------------------------------------------------
}

package WallRunRequirements {
    doc /*
     * The requirements specification realised formally.  The specification
     * document governs on any disagreement.  Every requirement def specialises
     * a RequirementTemplates shape, adds the WallRover subject, and BINDS its
     * operands with `attribute :>> measured = rover.attr`; the require
     * constraint is inherited, so the evaluable logic lives in one place.
     * Decomposition is nested `requirement : Child` usages.
     */

    private import ISQ::*;
    private import SI::*;
    private import ScalarValues::*;
    private import RoverCommon::*;
    private import WallStopStructure::*;
    private import RequirementTemplates::*;

    // ===================== CMP — single-effector leaves =====================

    requirement def <'CMP-1'> RangerAOffsetKnown specializes UpperBoundRequirement {
        doc /* The forward ranger A longitudinal offset shall be known to within
             * the offset uncertainty allocated by the margin budget.
             * Rationale: the offset enters the final clearance 1:1; it is the
             * only quantity in the chain that no onboard channel observes
             * without also observing itself. */
        subject rover : WallRover;
        attribute :>> measured = rover.rangerA.offsetUncertainty;
        attribute :>> target   = rover.sigmaOffset;
    }

    requirement def <'CMP-2'> RangerBOffsetKnown specializes UpperBoundRequirement {
        doc /* As CMP-1 for ranger B.  Rationale: the two rangers need not share
             * a longitudinal station; a single fused offset would hide a real
             * per-channel difference. */
        subject rover : WallRover;
        attribute :>> measured = rover.rangerB.offsetUncertainty;
        attribute :>> target   = rover.sigmaOffset;
    }

    requirement def <'CMP-3'> RangerRefreshBounded specializes UpperBoundRequirement {
        doc /* Each forward ranger shall refresh its reported range at intervals
             * no greater than the refresh limit.  Rationale: staleness is the
             * dominant term in the trigger phase uncertainty, and a stale sample
             * moves the stop by v * refreshInterval. */
        subject rover : WallRover;
        attribute :>> measured = rover.refreshInterval;
        attribute :>> target   = rover.rangerA.refreshIntervalLimit;
    }

    requirement def <'CMP-4'> RangerValidityGated specializes LowerBoundRequirement {
        doc /* Readings below the minimum valid range shall be rejected.
             * Rationale: an ultrasonic dead-zone reading is not a small
             * distance, it is a wrong distance, and it appears exactly where the
             * rover is most committed. */
        subject rover : WallRover;
        attribute :>> measured = rover.rangerA.validityCheckCount;
        attribute :>> target   = rover.evidenceFloor;
    }

    requirement def <'CMP-5'> TravelScaleBound specializes LowerBoundRequirement {
        doc /* Each drive motor's rotation-to-travel scale shall be bound by
             * calibration.  Rationale: it converts encoder rate into the ground
             * speed the trigger law consumes. */
        subject rover : WallRover;
        attribute :>> measured = rover.driveLeft.travelPerAngle;
        attribute :>> target   = rover.driveLeft.travelPerAngleFloor;
    }

    requirement def <'CMP-6'> MaxSpeedAchieved specializes LowerBoundRequirement {
        doc /* The drivetrain shall achieve at least the calibrated maximum
             * ground speed when commanded above its ceiling.  Rationale: STK-4
             * makes maximum speed a hard constraint, so "did it actually run at
             * maximum" must be a testable claim, not an assumption. */
        subject rover : WallRover;
        attribute :>> measured = rover.vApproach;
        attribute :>> target   = rover.vMaxFloor;
    }

    requirement def <'CMP-7'> BrakeDecelSufficient specializes LowerBoundRequirement {
        doc /* When commanded to brake, the drive pair shall decelerate the rover
             * at no less than the calibrated floor.  Rationale: deceleration is
             * the highest-leverage parameter in the sensitivity table; a shortfall
             * lengthens the stop quadratically in speed. */
        subject rover : WallRover;
        attribute :>> measured = rover.brakeDecel;
        attribute :>> target   = rover.driveLeft.brakeDecelFloor;
    }

    requirement def <'CMP-8'> ResponseLatencyBounded specializes UpperBoundRequirement {
        doc /* The chain from the true clearance crossing the trigger condition
             * to the braking command shall not exceed the calibrated bound.
             * Rationale: latency converts directly into travel at 470 mm/s;
             * it is the second-ranked mean-shifting parameter. */
        subject rover : WallRover;
        attribute :>> measured = rover.tResponse;
        attribute :>> target   = rover.tResponseLimit;
    }

    requirement def <'CMP-9'> HeadingDriftBounded specializes UpperBoundRequirement {
        doc /* The inertial unit's heading error over one run shall not exceed the
             * heading limit.  Rationale: heading is the only channel steering the
             * approach; its drift is indistinguishable from a real yaw. */
        subject rover : WallRover;
        attribute :>> measured = rover.headingDeviation;
        attribute :>> target   = rover.headingLimit;
    }

    requirement def <'CMP-10'> LoopPeriodBounded specializes UpperBoundRequirement {
        doc /* The control loop shall complete each cycle within the period limit.
             * Rationale: the loop period sets the trigger quantisation, hence a
             * v*dt contribution to the clearance uncertainty. */
        subject rover : WallRover;
        attribute :>> measured = rover.loopPeriod;
        attribute :>> target   = rover.loopPeriodLimit;
    }

    requirement def <'CMP-11'> PortSelfCheck specializes LowerBoundRequirement {
        doc /* At initialisation the rover shall confirm the configured devices on
             * their configured ports and a plausible start clearance before
             * commencing the approach.  Rationale (DERIVED): the port map and the
             * drivetrain polarity are discovered facts, and a silent mis-map
             * drives the rover at the wall with an inverted control law. */
        subject rover : WallRover;
        attribute :>> measured = rover.portSelfCheckCount;
        attribute :>> target   = rover.evidenceFloor;
    }

    requirement def <'CMP-12'> TrimNeverExceedsMax specializes UpperBoundRequirement {
        doc /* The steering trim shall only ever reduce a motor's commanded speed.
             * Rationale (DERIVED): STK-4 forbids commanding below maximum for
             * safety, and the motor cannot exceed its ceiling, so a symmetric
             * trim would be a one-sided trim in disguise and would bias heading. */
        subject rover : WallRover;
        attribute :>> measured = rover.driveLeft.maxCommandedSpeed;
        attribute :>> target   = rover.driveLeft.maxSpeed;
    }

    requirement def <'CMP-13'> RearRangerConditional specializes LowerBoundRequirement {
        doc /* CONDITIONAL.  Where the rear ranger returns an in-range reading at
             * the start line, it shall serve as an independent travelled-distance
             * channel.  Rationale (DERIVED, GtWR rule 6): cross-sourcing.  If the
             * evidence is absent the requirement and the effector drop out
             * together — absence by traceability, closed on evidence. */
        subject rover : WallRover;
        attribute :>> measured = rover.rangerRear.validAtStartCount;
        attribute :>> target   = rover.evidenceFloor;
    }

    requirement def <'CMP-14'> RestIndicatorAvailable specializes LowerBoundRequirement {
        doc /* The inertial unit shall provide a forward-acceleration channel
             * usable as an independent at-rest and contact indicator.
             * Rationale (DERIVED): "came to a complete stop" and "did it touch"
             * must not both rest on the same odometry channel. */
        subject rover : WallRover;
        attribute :>> measured = rover.restIndicatorCount;
        attribute :>> target   = rover.evidenceFloor;
    }

    // ===================== FUN — functions =====================

    requirement def <'FUN-1'> SenseForwardClearance specializes UpperBoundRequirement {
        doc /* The rover shall sample forward clearance every control cycle.
             * Rationale: the trigger cannot be more current than its input. */
        subject rover : WallRover;
        attribute :>> measured = rover.loopPeriod;
        attribute :>> target   = rover.loopPeriodLimit;
        requirement : RangerAOffsetKnown;
        requirement : RangerBOffsetKnown;
        requirement : RangerRefreshBounded;
    }

    requirement def <'FUN-2'> EstimateGroundSpeed {
        doc /* The rover shall estimate its instantaneous ground speed every
             * control cycle.  Rationale: the trigger law is speed-adaptive. */
        subject rover : WallRover;
        requirement : TravelScaleBound;
    }

    requirement def <'FUN-3'> PredictStoppingDistance {
        doc /* The rover shall compute the predicted stopping distance for its
             * current ground speed every control cycle, from the calibrated
             * latency and deceleration.  Rationale: this is the instantiation of
             * RelationTemplates::StoppingDistance in the flight code. */
        subject rover : WallRover;
        requirement : ResponseLatencyBounded;
        requirement : BrakeDecelSufficient;
    }

    requirement def <'FUN-4'> AssertTrigger specializes UpperBoundRequirement {
        doc /* When the estimated clearance less the predicted stopping distance
             * falls to or below the target gap, the rover shall assert the stop
             * trigger within one control cycle.  Rationale: any additional
             * decision latency is indistinguishable from tResponse but is not in
             * its calibration. */
        subject rover : WallRover;
        attribute :>> measured = rover.loopPeriod;
        attribute :>> target   = rover.loopPeriodLimit;
        requirement : LoopPeriodBounded;
    }

    requirement def <'FUN-5'> CommandDriveAtMaximum {
        doc /* The rover shall command the drivetrain above its speed ceiling for
             * the whole approach.  Rationale: STK-4. */
        subject rover : WallRover;
        requirement : MaxSpeedAchieved;
    }

    requirement def <'FUN-6'> ApplyBraking {
        doc /* When the trigger is asserted, the rover shall brake both drive
             * motors.  Rationale: STK-3, and braking is the only actuation that
             * shortens the stop. */
        subject rover : WallRover;
        requirement : BrakeDecelSufficient;
        requirement : RestIndicatorAvailable;
    }

    requirement def <'FUN-7'> HoldHeading {
        doc /* While approaching, the rover shall trim the drive pair from the
             * heading error.  Rationale: SYS-5. */
        subject rover : WallRover;
        requirement : HeadingDriftBounded;
        requirement : TrimNeverExceedsMax;
    }

    requirement def <'FUN-8'> LogOffHotPath specializes LowerBoundRequirement {
        doc /* The rover shall buffer telemetry in memory during motion and emit
             * it only after the motors have stopped.  Rationale (DERIVED,
             * test-like-you-fly): emitting on the hot path would change the loop
             * period between characterisation and operation, invalidating every
             * latency-dependent calibration. */
        subject rover : WallRover;
        attribute :>> measured = rover.onboardEstimateCount;
        attribute :>> target   = rover.evidenceFloor;
    }

    requirement def <'FUN-9'> SelectValidChannel specializes LowerBoundRequirement {
        doc /* The rover shall validity-check each ranger sample and select an
             * in-range channel.  Rationale: SYS-8. */
        subject rover : WallRover;
        attribute :>> measured = rover.fallbackChannelCount;
        attribute :>> target   = rover.evidenceFloor;
        requirement : RangerValidityGated;
        requirement : RearRangerConditional;
    }

    requirement def <'FUN-10'> EstablishReferencesAtStart specializes UpperBoundRequirement {
        doc /* At run start the rover shall establish every reference it uses —
             * heading zero, odometry zero, start clearance, port map check.
             * Rationale: SYS-7; the hub is power-cycled between runs. */
        subject rover : WallRover;
        attribute :>> measured = rover.persistedStateCount;
        attribute :>> target   = rover.persistedStateLimit;
        requirement : PortSelfCheck;
    }

    // ===================== SYS — system black box =====================

    requirement def <'SYS-1'> ClearanceAboveMargin specializes LowerBoundRequirement {
        doc /* The final clearance shall be no less than the contact margin,
             * where the contact margin is kSigma times the root-sum-square of the
             * independent final-clearance uncertainty contributors.
             * Rationale (DERIVED, GtWR rule 3 + tenet A6): the task states a hard
             * constraint (no contact) and an objective (minimise the gap) that
             * pull against each other; the bridge between them must be an
             * uncertainty-sized margin, not a chosen number. */
        subject rover : WallRover;
        attribute :>> measured = rover.finalClearance;
        attribute :>> target   = rover.contactMargin;
    }

    requirement def <'SYS-2'> TriggerStopOnPrediction {
        doc /* When the estimated clearance less the predicted stopping distance
             * falls to or below the target gap, the rover shall command the
             * drivetrain to stop.  Rationale: this is the single decision the
             * whole task turns on. */
        subject rover : WallRover;
        requirement : SenseForwardClearance;
        requirement : EstimateGroundSpeed;
        requirement : PredictStoppingDistance;
        requirement : AssertTrigger;
    }

    requirement def <'SYS-3'> AtRestAtEnd specializes UpperBoundRequirement {
        doc /* The rover's ground speed at end of run shall not exceed the at-rest
             * threshold.  Rationale: the task requires a COMPLETE stop; a slow
             * creep is a failure that a distance-only check would pass. */
        subject rover : WallRover;
        attribute :>> measured = rover.restSpeed;
        attribute :>> target   = rover.restSpeedLimit;
        requirement : ApplyBraking;
    }

    requirement def <'SYS-4'> ApproachAtMaximum specializes LowerBoundRequirement {
        doc /* While in the approach state, each drive motor's commanded speed
             * shall be no less than its rated maximum, less only the steering
             * trim of SYS-5.  Rationale: literal task constraint — "Run at
             * maximum speed.  Do not slow down for safety margin." */
        subject rover : WallRover;
        attribute :>> measured = rover.commandedSpeedFraction;
        attribute :>> target   = rover.commandedSpeedFloor;
        requirement : CommandDriveAtMaximum;
    }

    requirement def <'SYS-5'> HeadingWithinLimit specializes UpperBoundRequirement {
        doc /* The heading deviation from the start heading shall not exceed the
             * heading limit throughout the approach.
             * Rationale (DERIVED): yaw is invisible to every distance channel yet
             * changes the answer twice — it inflates the ranger path by 1/cos and
             * it advances one front corner ahead of the sensed centreline, so an
             * uncontrolled yaw is a contact mechanism no range reading reports. */
        subject rover : WallRover;
        attribute :>> measured = rover.headingDeviation;
        attribute :>> target   = rover.headingLimit;
        requirement : HoldHeading;
    }

    requirement def <'SYS-6'> ReportOnboardEstimate specializes LowerBoundRequirement {
        doc /* The rover shall report an onboard estimate of the final clearance,
             * and the telemetry it derives from, for every run.
             * Rationale (DERIVED): the operation close-out requires a per-run
             * estimate frozen before ground truth; an estimate that cannot be
             * produced onboard cannot be frozen. */
        subject rover : WallRover;
        attribute :>> measured = rover.onboardEstimateCount;
        attribute :>> target   = rover.evidenceFloor;
        requirement : LogOffHotPath;
    }

    requirement def <'SYS-7'> NoCrossRunState specializes UpperBoundRequirement {
        doc /* The rover shall not depend on any state persisted from a previous
             * run.  Rationale (DERIVED): the hub is power-cycled between runs;
             * heading and clock reset to zero, so any carried assumption is
             * silently false on run two. */
        subject rover : WallRover;
        attribute :>> measured = rover.persistedStateCount;
        attribute :>> target   = rover.persistedStateLimit;
        requirement : EstablishReferencesAtStart;
    }

    requirement def <'SYS-8'> IndependentChannelFallback specializes LowerBoundRequirement {
        doc /* Where the primary forward-range channel returns an invalid or stale
             * value, the rover shall derive its clearance estimate from an
             * independent onboard channel.
             * Rationale (DERIVED): a dropout inside the last 200 mm has no
             * recovery path and ends in contact; cross-sourcing (GtWR rule 6). */
        subject rover : WallRover;
        attribute :>> measured = rover.fallbackChannelCount;
        attribute :>> target   = rover.evidenceFloor;
        requirement : SelectValidChannel;
    }

    // ===================== STK — stakeholder =====================

    requirement def <'STK-2'> NoContact {
        doc /* The rover shall not contact the wall.  [Unwanted]
             * Rationale: literal task hard constraint. */
        subject rover : WallRover;
        requirement : ClearanceAboveMargin;
        requirement : TriggerStopOnPrediction;
        requirement : HeadingWithinLimit;
        requirement : IndependentChannelFallback;
    }

    requirement def <'STK-3'> CompleteStop {
        doc /* When the approach terminates, the rover shall be at a complete
             * stop.  [Event-driven]  Rationale: literal task constraint. */
        subject rover : WallRover;
        requirement : AtRestAtEnd;
    }

    requirement def <'STK-4'> MaximumSpeedApproach {
        doc /* While approaching the wall, the rover shall travel at the maximum
             * speed its drivetrain can achieve.  [State-driven]
             * Rationale: literal task constraint. */
        subject rover : WallRover;
        requirement : ApproachAtMaximum;
    }

    requirement def <'STK-5'> MinimiseFinalGap {
        doc /* The rover SHOULD minimise the final gap between its foremost point
             * and the wall.  [Ubiquitous, OBJECTIVE — graded, not pass/fail]
             * Rationale: literal task objective.  Bridged to the hard constraint
             * STK-2 by the derived margin requirement SYS-1: minimising the gap
             * means minimising sigmaGap, because the gap floor IS 3*sigmaGap. */
        subject rover : WallRover;
        requirement : ClearanceAboveMargin;
        requirement : ReportOnboardEstimate;
    }

    requirement def <'STK-6'> RepeatableAcrossRuns {
        doc /* The rover shall achieve STK-2 through STK-4 on each of five
             * consecutive power-cycled runs of one unchanged program.
             * Rationale (DERIVED): three of the four scored quantities are
             * repeatability quantities, so run-to-run variance is a requirement
             * in its own right and enters the margin as sigmaRunToRun. */
        subject rover : WallRover;
        requirement : NoCrossRunState;
    }

    requirement def <'STK-1'> WallRunNeed {
        doc /* The rover shall execute the wall-approach task: a maximum-speed
             * approach from the start line terminating in a complete stop clear
             * of the wall, repeatably.  [Ubiquitous]
             * Rationale: the stakeholder need as stated in the task. */
        subject rover : WallRover;
        requirement : NoContact;
        requirement : CompleteStop;
        requirement : MaximumSpeedApproach;
        requirement : MinimiseFinalGap;
        requirement : RepeatableAcrossRuns;
    }
}

package WallStopDesign {
    doc /*
     * The design realisation.  Evaluating this satisfy/require roll-up against
     * the calibrated values IS the pre-run verification artifact (GATE B).
     */

    private import WallStopStructure::*;
    private import WallRunRequirements::*;

    part def WallRoverAsBuilt specializes WallRover {
        satisfy requirement : WallRunRequirements::WallRunNeed;
    }
}
