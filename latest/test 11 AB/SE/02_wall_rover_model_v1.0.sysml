// ============================================================================
// 02_wall_rover_model_v1.0.sysml — Wall-Approach Rover (WAR), tailored model
// Version 1.0 | Issued for Gate A review
//
// REALISES: RS-WAR v1.0 (01_requirements_spec_v1.0.md) — the spec is the
// source of truth; on any disagreement the spec governs.
// TAILORED FROM: rover_generic.sysml (RoverCommon, RoverStructure,
// RelationTemplates, RequirementTemplates) — only the templates the
// requirements call for are instantiated (Tenet A4).
// COMPUTATIONAL TWIN: 03_wall_rover_eam_v1.0.py — every attribute below maps
// 1:1 to a named Python key (comments give the key); the EAM's
// structural_audit() mechanically certifies edge-set-vs-spec-tree equality,
// reachability from the seven STK roots, and operand-name resolution.
//
// TAILORING DECISIONS (traceable):
//  * RelationTemplates::RotationToSpeed  -> INSTANTIATED (FUN-2 names kOdo);
//    reproduced as WallRover::groundSpeed per the library validation note
//    (expressions REPRODUCED against bound parameters, not calc-invoked).
//  * RelationTemplates::StoppingDistance -> INSTANTIATED (FUN-3/SYS-2 trigger
//    law); reproduced as WallRover::stopBudget with tResponse := latency.tChain
//    (sensor data age is corrected separately in FUN-1, so the post-correction
//    reaction chain is exactly RoverCommon::RoverLatency.tChain) and
//    margin := stopTarget (SYS-5).
//  * RelationTemplates::MaxSpeedFromBudget -> NOT INSTANTIATED: no requirement
//    traces to a speed-from-budget computation (STK-2 fixes speed at maximum
//    unconditionally; feasibility 1000 mm >> stopBudget is closed by
//    inspection). Absence by traceability.
//  * RoverStructure::ReflectanceSensor ("floor") -> inherited, UNUSED: no
//    requirement traces to it (RS-WAR section 7). Identified once at the
//    startup census purely for port disambiguation; never read as a channel.
//  * usRear -> CONDITIONAL channel, kept only under CMP-R1 {Optional}.
//
// CONVENTIONS:
//  * All numeric literals are SI base units (m, s, m/s, m/s^2, rad) matching
//    the ISQ/SI value types; the EAM converts to mm/ms/deg for display only.
//  * Angle carried as dimensionless real in radians (RoverCommon::Angle);
//    cornerErosion uses the small-angle form halfWidth * psi (documented
//    approximation, sin not in the validated expression set).
//  * Attributes left UNBOUND are uncalibrated, not zeroed (Tenet A3): values
//    arrive only from calibration evidence at Gate B, or from run/test
//    evidence at verification. Bound literals below are DESIGN CONSTANTS.
//  * EAM key aliases (documented, deliberate): 'one'/'zero' <-> unity/nil;
//    'v_max' <-> groundSpeed; 'psi_run' prior and 'heading_dev_max'
//    observation both realise headingDeviationMax; 'U_refresh'/'r_min'/
//    'sigma_us'/'o_us'/'tau_us' <-> the per-sensor CalibratedRanger
//    attributes (A and B calibrated independently; the EAM sweeps their
//    common prior).
// ============================================================================

package WallRoverDesign {
    doc /*
     * The task design: a WallRover specialising the platform skeleton, its
     * calibratable parameters, its run observables, its reproduced relation
     * expressions, and its formal satisfy claims on the seven stakeholder
     * roots of RS-WAR v1.0.
     */

    private import ISQ::*;
    private import SI::*;
    private import ScalarValues::*;
    private import RoverCommon::*;
    private import RoverStructure::*;
    private import WallRoverRequirements::*;

    // ---- calibrated specialisations of the skeleton blocks -----------------

    part def CalibratedDriveMotor specializes DriveMotor {
        doc /* One drive motor with its calibration products and per-motor
             * unit-verification observables. Instances: motorL, motorR. */
        attribute plateauSpeed    : AngularVelocityValue; // rad/s at 100% duty  [TBD-13 input]
        attribute plateauDev      : Real;                 // |dev| fraction vs bound plateau  (EAM: plateau_dev_L/R)
        attribute forwardSignValid: Real;                 // 1 = sign resolved & validated    [TBD-14/15] (EAM: sign_valid_L/R)
        attribute brakeDistance   : LengthValue;          // measured wheel stop distance     (EAM: brake_dist_L/R)
        attribute postStopTravel  : LengthValue;          // travel over 2 s at hold          (EAM: post_stop_travel_L/R)
        attribute encoderDropouts : Real;                 // dropout count in stream          (EAM: encoder_dropouts_L/R)
    }

    part def CalibratedRanger specializes DistanceSensor {
        doc /* One ultrasonic ranger with its calibration products.
             * Inherited: range (reported), refreshInterval [TBD-17].
             * Instances: usFrontA, usFrontB, usRear (conditional). */
        attribute mountOffset    : LengthValue;   // reading - true front gap at rest [TBD-5/6] (EAM: o_us)
        attribute dataAge        : DurationValue; // effective sample age             [TBD-7]   (EAM: tau_us)
        attribute noiseSigma     : LengthValue;   // static noise sigma               [TBD-16]  (EAM: sigma_us)
        attribute validFloor     : LengthValue;   // near-range validity floor        [TBD-4]   (EAM: r_min)
        attribute offsetResidual : LengthValue;   // max |per-window offset - bound|            (EAM: offset_residual_A/B)
        attribute dataAgeError   : DurationValue; // bound residual on dataAge                   (EAM: data_age_err_A/B)
        attribute subFloorLeakage: Real;          // sub-floor samples that entered fusion       (EAM: subfloor_leakage_A/B)
        attribute trackError     : LengthValue;   // rear-only: |delta-rear - encoder distance|  (EAM: rear_track_error)
    }

    // ---- the task vehicle ---------------------------------------------------

    part def WallRover specializes Rover {
        doc /* Named realisations of the skeleton's open multiplicities: two
             * drive motors, two forward rangers, one conditional rear ranger.
             * imu, floor, latency inherited from Rover. */

        part motorL   : CalibratedDriveMotor;
        part motorR   : CalibratedDriveMotor;
        part usFrontA : CalibratedRanger;
        part usFrontB : CalibratedRanger;
        part usRear   : CalibratedRanger;   // conditional — CMP-R1 {Optional}

        // ---- calibratable vehicle parameters (UNBOUND until Gate B) --------
        attribute kOdo        : LengthValue;        // m per rad            [TBD-8]   (EAM: k_odo)
        attribute brakeDecel  : AccelerationValue;  // effective decel      [TBD-10]  (EAM: a_brake)
        attribute brakeSigma  : LengthValue;        // braking dispersion   [TBD-10b] (EAM: sigma_b)
        attribute loopPeriod  : DurationValue;      // control period       [TBD-11]  (EAM: T_loop)
        attribute halfWidth   : LengthValue;        // corner arm (bounded prior)      (EAM: half_width)
        attribute trimGain    : Real;               // heading-hold gain    [TBD-12]
        attribute stopTarget  : LengthValue;        // G_target             [TBD-1]   (EAM: stop_target)
        attribute sigmaStop   : LengthValue;        // RSS stop dispersion  [analysis] (EAM: sigma_stop)
        // requirement bounds set from calibration evidence at Gate B:
        attribute postStopBound  : LengthValue;     // [TBD-2]  (EAM: post_stop_bound)
        attribute headingBound   : Angle;           // [TBD-3]  (EAM: heading_bound)
        attribute noiseBound     : LengthValue;     // [TBD-16 bound] (EAM: noise_bound)
        attribute refreshBound   : DurationValue;   // [TBD-17 bound] (EAM: refresh_bound)
        attribute imuDriftBound  : Angle;           // [TBD-18 bound] (EAM: imu_drift_bound)
        attribute jitterBound    : DurationValue;   // [TBD-19 bound] (EAM: jitter_bound)
        attribute rearTrackBound : LengthValue;     // [TBD-20 bound] (EAM: rear_track_bound)

        // ---- design constants (SI base units; EAM: CONSTANTS) --------------
        attribute unity              : Real          = 1.0;    // (EAM: one)
        attribute nil                : Real          = 0.0;    // (EAM: zero)
        attribute zMargin            : Real          = 3.0;    // (EAM: z_margin)   SYS-5
        attribute contactFloor       : LengthValue   = 0.001;  // (EAM: contact_floor) strict >0 realised as >= 1 mm
        attribute dutyCommand        : Real          = 100.0;  // (EAM: duty_command) %
        attribute trimCapPct         : Real          = 15.0;   // (EAM: trim_cap_pct) %
        attribute plateauRatioFloor  : Real          = 0.95;   // (EAM: plateau_ratio_floor)
        attribute plateauDevTol      : Real          = 0.05;   // (EAM: plateau_dev_tol)
        attribute offsetTol          : LengthValue   = 0.003;  // (EAM: offset_tol)   CMP-U2 spec constant
        attribute dataAgeTol         : DurationValue = 0.010;  // (EAM: data_age_tol) CMP-U3 spec constant
        attribute coverageFloor      : Real          = 0.99;   // (EAM: coverage_floor)
        attribute holdFloor          : DurationValue = 2.0;    // (EAM: hold_floor)
        attribute restSampleFloor    : Real          = 8.0;    // (EAM: rest_sample_floor)
        attribute estimateChannelFloor : Real        = 2.0;    // (EAM: estimate_channel_floor)
        attribute objectiveCeiling   : LengthValue   = 0.060;  // (EAM: objective_ceiling) STK-3 design goal
        attribute emissionBudget     : DurationValue = 20.0;   // (EAM: emission_budget)

        // ---- run observables (bound from test/run evidence; UNBOUND here) --
        attribute finalClearance     : LengthValue;   // (EAM: final_clearance)      C_final at stop
        attribute minRunClearance    : LengthValue;   // (EAM: min_run_clearance)
        attribute speedPlateauRatio  : Real;          // (EAM: speed_plateau_ratio)  measured/bound plateau
        attribute restAchieved       : Real;          // (EAM: rest_achieved)
        attribute estimatesCommitted : Real;          // (EAM: estimates_committed)
        attribute operatorInputsDuringRun : Real;     // (EAM: operator_inputs_during_run)
        attribute telemetryComplete  : Real;          // (EAM: telemetry_complete)
        attribute outerDutyMin       : Real;          // (EAM: outer_duty_min)
        attribute brakeCmdDelay      : DurationValue; // (EAM: brake_cmd_delay)
        attribute postStopTravelMax  : LengthValue;   // (EAM: post_stop_travel_max)
        attribute estimateChannels   : Real;          // (EAM: estimate_channels)
        attribute headingDeviationMax: Angle;         // (EAM: heading_dev_max / psi_run)
        attribute hotPathWrites      : Real;          // (EAM: hot_path_writes)
        attribute sentinelEmitted    : Real;          // (EAM: sentinel_emitted)
        attribute failsafeLatency    : DurationValue; // (EAM: failsafe_latency)
        attribute invalidSampleLeakage : Real;        // (EAM: invalid_sample_leakage)
        attribute censusValidated    : Real;          // (EAM: census_validated)
        attribute gapCoverage        : Real;          // (EAM: gap_coverage)
        attribute odoCoverage        : Real;          // (EAM: odo_coverage)
        attribute fusedGapAtTrigger  : LengthValue;   // (EAM: fused_gap_at_trigger)
        attribute trimMax            : Real;          // (EAM: trim_max)
        attribute holdDuration       : DurationValue; // (EAM: hold_duration)
        attribute restSampleCount    : Real;          // (EAM: rest_sample_count)
        attribute failsafeCoverage   : Real;          // (EAM: failsafe_coverage)
        attribute imuDriftTenS       : Angle;         // (EAM: imu_drift_10s)
        attribute contactWitnessArmed: Real;          // (EAM: contact_witness_armed)
        attribute loopJitterP95      : DurationValue; // (EAM: loop_jitter_p95)
        attribute emissionDuration   : DurationValue; // (EAM: emission_duration)

        // ---- derived attributes: REPRODUCED relation expressions -----------
        // RelationTemplates::RotationToSpeed reproduced (EAM: ground_speed):
        attribute groundSpeed : SpeedValue =
            ((motorL.plateauSpeed + motorR.plateauSpeed) / 2.0) * kOdo;
        // RelationTemplates::StoppingDistance reproduced (EAM: stop_budget);
        // tResponse := latency.tChain, margin := stopTarget:
        attribute stopBudget : LengthValue =
            groundSpeed * latency.tChain
            + groundSpeed ** 2 / (2.0 * brakeDecel)
            + stopTarget;
        // SYS-5 / SYS-4 right-hand sides (EAM: margin_floor, closeness_ceiling):
        attribute marginFloor : LengthValue = zMargin * sigmaStop;
        attribute closenessCeiling : LengthValue = stopTarget + zMargin * sigmaStop;
        // CMP-M2 right-hand side (EAM: brake_dist_ceiling):
        attribute brakeDistCeiling : LengthValue =
            groundSpeed ** 2 / (2.0 * brakeDecel) + zMargin * brakeSigma;
        // SYS-11 right-hand side (EAM: failsafe_latency_bound):
        attribute failsafeLatencyBound : DurationValue = 2.0 * loopPeriod;
        // corner erosion, small-angle (EAM: corner_erosion):
        attribute cornerErosion : LengthValue = halfWidth * headingDeviationMax;

        // ---- formal claims: the design satisfies the seven STK roots -------
        satisfy requirement : WallRoverRequirements::STK1_NoContact;
        satisfy requirement : WallRoverRequirements::STK2_MaxSpeedApproach;
        satisfy requirement : WallRoverRequirements::STK3_MinimizeClearance;
        satisfy requirement : WallRoverRequirements::STK4_CompleteStop;
        satisfy requirement : WallRoverRequirements::STK5_OnboardEstimate;
        satisfy requirement : WallRoverRequirements::STK6_Autonomy;
        satisfy requirement : WallRoverRequirements::STK7_TelemetryContract;
    }
}

package WallRoverRequirements {
    doc /*
     * The requirement tree of RS-WAR v1.0, realised: each requirement def
     * specialises a validated shape (LowerBoundRequirement /
     * UpperBoundRequirement), takes the WallRover as subject, BINDS both
     * operands with the redefinition-with-binding form, and nests its
     * children as requirement usages. The require constraint is inherited
     * from the template — the evaluable logic lives in exactly one place.
     * [O] marks the two graded objectives (spec 'should'; formalised here as
     * bound constraints per the shape catalog — the spec governs the grading).
     */

    private import RequirementTemplates::*;
    private import WallRoverDesign::*;

    // ======================= STK level (seven roots) =======================

    requirement def <'STK-1'> STK1_NoContact specializes LowerBoundRequirement {
        doc /* [H]{Unwanted} The rover shall not make contact with the wall
             * during a run. Realised: minimum run clearance stays above the
             * 1 mm contact floor. */
        subject rover : WallRover;
        attribute :>> measured = rover.minRunClearance;
        attribute :>> target   = rover.contactFloor;
        requirement : SYS3_ClearanceAtStop;
        requirement : SYS8_HeadingBound;
        requirement : SYS11_FailSafeStop;
        requirement : SYS12_InvalidSampleHandling;
    }

    requirement def <'STK-2'> STK2_MaxSpeedApproach specializes LowerBoundRequirement {
        doc /* [H]{State} While in APPROACH, drive at maximum achievable
             * speed. Realised: measured plateau >= 95 % of the bound ceiling. */
        subject rover : WallRover;
        attribute :>> measured = rover.speedPlateauRatio;
        attribute :>> target   = rover.plateauRatioFloor;
        requirement : SYS1_FullDuty;
    }

    requirement def <'STK-3'> STK3_MinimizeClearance specializes UpperBoundRequirement {
        doc /* [O]{Ubiquitous} Minimize final clearance. Formalised: the
             * designed stop target shall not exceed the 60 mm objective
             * ceiling (grading per spec; SYS-4 carries the per-run form). */
        subject rover : WallRover;
        attribute :>> measured = rover.stopTarget;
        attribute :>> target   = rover.objectiveCeiling;
        requirement : SYS4_ClosenessCeiling;
    }

    requirement def <'STK-4'> STK4_CompleteStop specializes LowerBoundRequirement {
        doc /* [H]{Event} When the approach terminates, come to a complete
             * stop and remain stopped. */
        subject rover : WallRover;
        attribute :>> measured = rover.restAchieved;
        attribute :>> target   = rover.unity;
        requirement : SYS2_TriggerLatency;
        requirement : SYS6_NoCreep;
    }

    requirement def <'STK-5'> STK5_OnboardEstimate specializes LowerBoundRequirement {
        doc /* [H][D]{Ubiquitous} Produce an onboard C_final estimate every
             * run (derived: close-out protocol + verifiability). */
        subject rover : WallRover;
        attribute :>> measured = rover.estimatesCommitted;
        attribute :>> target   = rover.unity;
        requirement : SYS7_MultiChannelEstimate;
    }

    requirement def <'STK-6'> STK6_Autonomy specializes UpperBoundRequirement {
        doc /* [H][D]{Ubiquitous} No operator input between program start and
             * end (derived: operation protocol). */
        subject rover : WallRover;
        attribute :>> measured = rover.operatorInputsDuringRun;
        attribute :>> target   = rover.nil;
        requirement : SYS13_SelfConfiguration;
    }

    requirement def <'STK-7'> STK7_TelemetryContract specializes LowerBoundRequirement {
        doc /* [H][D]{Ubiquitous} Telemetry sufficient to reconstruct the
             * approach (>= distance + heading) with terminal sentinel
             * (derived: task wire contract). */
        subject rover : WallRover;
        attribute :>> measured = rover.telemetryComplete;
        attribute :>> target   = rover.unity;
        requirement : SYS9_QuietHotPath;
        requirement : SYS10_SentinelAlways;
    }

    // ============================== SYS level ==============================

    requirement def <'SYS-1'> SYS1_FullDuty specializes LowerBoundRequirement {
        doc /* [H]{State} 100 % duty to both motors during APPROACH; trim only
             * as inner-wheel reduction <= 15 % (FUN-4). */
        subject rover : WallRover;
        attribute :>> measured = rover.outerDutyMin;
        attribute :>> target   = rover.dutyCommand;
        requirement : FUN4_DriveAndTrim;
    }

    requirement def <'SYS-2'> SYS2_TriggerLatency specializes UpperBoundRequirement {
        doc /* [H]{Event} Full braking commanded within one control period of
             * the trigger condition. */
        subject rover : WallRover;
        attribute :>> measured = rover.brakeCmdDelay;
        attribute :>> target   = rover.loopPeriod;
        requirement : FUN1_CorrectedGap;
        requirement : FUN2_Odometry;
        requirement : FUN3_FuseAndTrigger;
        requirement : FUN5_BrakeAndHold;
    }

    requirement def <'SYS-3'> SYS3_ClearanceAtStop specializes LowerBoundRequirement {
        doc /* [H]{Ubiquitous} C_final > 0 at every complete stop; closed at
             * Gate C only against a T3 anchor at the operating point. */
        subject rover : WallRover;
        attribute :>> measured = rover.finalClearance;
        attribute :>> target   = rover.contactFloor;
        requirement : SYS5_MarginSizing;
    }

    requirement def <'SYS-4'> SYS4_ClosenessCeiling specializes UpperBoundRequirement {
        doc /* [O]{Ubiquitous} C_final <= G_target + 3*sigma_stop per run. */
        subject rover : WallRover;
        attribute :>> measured = rover.finalClearance;
        attribute :>> target   = rover.closenessCeiling;
    }

    requirement def <'SYS-5'> SYS5_MarginSizing specializes LowerBoundRequirement {
        doc /* [H][D]{Ubiquitous} G_target = z*sigma_stop, z = 3.0, sigma_stop
             * the RSS of calibrated independent contributors (Tenet A6;
             * rule-3 bridge between STK-1 and STK-3). */
        subject rover : WallRover;
        attribute :>> measured = rover.stopTarget;
        attribute :>> target   = rover.marginFloor;
    }

    requirement def <'SYS-6'> SYS6_NoCreep specializes UpperBoundRequirement {
        doc /* [H]{State} Post-stop travel <= postStopBound over 2 s. */
        subject rover : WallRover;
        attribute :>> measured = rover.postStopTravelMax;
        attribute :>> target   = rover.postStopBound;
    }

    requirement def <'SYS-7'> SYS7_MultiChannelEstimate specializes LowerBoundRequirement {
        doc /* [H][D]{Event} C_final estimated from every valid channel plus a
             * fused value (cross-sourcing; survives US floor invalidity). */
        subject rover : WallRover;
        attribute :>> measured = rover.estimateChannels;
        attribute :>> target   = rover.estimateChannelFloor;
        requirement : FUN6_RestReporting;
    }

    requirement def <'SYS-8'> SYS8_HeadingBound specializes UpperBoundRequirement {
        doc /* [H][D]{State} |heading deviation| <= headingBound during
             * APPROACH/BRAKING (corner-erosion allocation). */
        subject rover : WallRover;
        attribute :>> measured = rover.headingDeviationMax;
        attribute :>> target   = rover.headingBound;
    }

    requirement def <'SYS-9'> SYS9_QuietHotPath specializes UpperBoundRequirement {
        doc /* [H][D]{State} No stream I/O while motors are commanded; RAM
             * buffer only (test-like-you-fly hot path). */
        subject rover : WallRover;
        attribute :>> measured = rover.hotPathWrites;
        attribute :>> target   = rover.nil;
    }

    requirement def <'SYS-10'> SYS10_SentinelAlways specializes LowerBoundRequirement {
        doc /* [H][D]{Event} Buffered telemetry emitted and sentinel sent on
             * every termination path. */
        subject rover : WallRover;
        attribute :>> measured = rover.sentinelEmitted;
        attribute :>> target   = rover.unity;
    }

    requirement def <'SYS-11'> SYS11_FailSafeStop specializes UpperBoundRequirement {
        doc /* [H][D]{Event} On self-check failure, full braking within
             * 2 loop periods, then reporting. */
        subject rover : WallRover;
        attribute :>> measured = rover.failsafeLatency;
        attribute :>> target   = rover.failsafeLatencyBound;
        requirement : FUN7_SelfCheck;
    }

    requirement def <'SYS-12'> SYS12_InvalidSampleHandling specializes UpperBoundRequirement {
        doc /* [H][D]{Event} Invalid ultrasonic samples (sub-floor, no-echo
             * ceiling, stale) never enter fusion; DR guard continues. */
        subject rover : WallRover;
        attribute :>> measured = rover.invalidSampleLeakage;
        attribute :>> target   = rover.nil;
    }

    requirement def <'SYS-13'> SYS13_SelfConfiguration specializes LowerBoundRequirement {
        doc /* [H][D]{Ubiquitous} Self-configure from discovery constants,
             * validated by census at every start. */
        subject rover : WallRover;
        attribute :>> measured = rover.censusValidated;
        attribute :>> target   = rover.unity;
    }

    // ============================== FUN level ==============================

    requirement def <'FUN-1'> FUN1_CorrectedGap specializes LowerBoundRequirement {
        doc /* [H]{State} Per-tick corrected gap G_i = R_i - o_i - v*tau for
             * every valid front ranger; coverage >= 99 % of APPROACH ticks. */
        subject rover : WallRover;
        attribute :>> measured = rover.gapCoverage;
        attribute :>> target   = rover.coverageFloor;
        requirement : CMPU1A_NoiseA;
        requirement : CMPU1B_NoiseB;
        requirement : CMPU2A_OffsetA;
        requirement : CMPU2B_OffsetB;
        requirement : CMPU3A_DataAgeA;
        requirement : CMPU3B_DataAgeB;
        requirement : CMPU4A_ValidityFloorA;
        requirement : CMPU4B_ValidityFloorB;
        requirement : CMPU5A_RefreshA;
        requirement : CMPU5B_RefreshB;
    }

    requirement def <'FUN-2'> FUN2_Odometry specializes LowerBoundRequirement {
        doc /* [H]{State} Per-tick distance k*dTheta and windowed speed from
             * encoders; coverage >= 99 %. */
        subject rover : WallRover;
        attribute :>> measured = rover.odoCoverage;
        attribute :>> target   = rover.coverageFloor;
        requirement : CMPM5L_EncoderL;
        requirement : CMPM5R_EncoderR;
        requirement : CMPR1_RearCrossCheck;
    }

    requirement def <'FUN-3'> FUN3_FuseAndTrigger specializes UpperBoundRequirement {
        doc /* [H]{State} Fused gap = min(valid corrected gaps, DR); trigger
             * asserted at fused gap <= stopBudget (StoppingDistance
             * reproduced; v from in-run odometry). */
        subject rover : WallRover;
        attribute :>> measured = rover.fusedGapAtTrigger;
        attribute :>> target   = rover.stopBudget;
        requirement : CMPH1_LoopTiming;
    }

    requirement def <'FUN-4'> FUN4_DriveAndTrim specializes UpperBoundRequirement {
        doc /* [H]{State} Both motors at 100 % duty; inner-wheel trim
             * min(kp*|psi|, 15 %) toward psi = 0. */
        subject rover : WallRover;
        attribute :>> measured = rover.trimMax;
        attribute :>> target   = rover.trimCapPct;
        requirement : CMPM1L_PlateauL;
        requirement : CMPM1R_PlateauR;
        requirement : CMPM3L_SignL;
        requirement : CMPM3R_SignR;
        requirement : CMPI1_ImuStability;
    }

    requirement def <'FUN-5'> FUN5_BrakeAndHold specializes LowerBoundRequirement {
        doc /* [H]{Event} hold() on both motors in the trigger tick; hold
             * maintained >= 2 s. */
        subject rover : WallRover;
        attribute :>> measured = rover.holdDuration;
        attribute :>> target   = rover.holdFloor;
        requirement : CMPM2L_BrakeL;
        requirement : CMPM2R_BrakeR;
        requirement : CMPM4L_NoCreepL;
        requirement : CMPM4R_NoCreepR;
    }

    requirement def <'FUN-6'> FUN6_RestReporting specializes LowerBoundRequirement {
        doc /* [H]{Event} Rest medians over >= 8 samples; per-channel + fused
             * estimates; emission under try/finally. */
        subject rover : WallRover;
        attribute :>> measured = rover.restSampleCount;
        attribute :>> target   = rover.restSampleFloor;
        requirement : CMPH2_Emission;
    }

    requirement def <'FUN-7'> FUN7_SelfCheck specializes LowerBoundRequirement {
        doc /* [H]{Event} Census + plausibility + progress gates; on failure
             * safe stop then report. Coverage = 1.0 over injected fault set. */
        subject rover : WallRover;
        attribute :>> measured = rover.failsafeCoverage;
        attribute :>> target   = rover.unity;
        requirement : CMPI2_ContactWitness;
    }

    // ============================== CMP level ==============================

    requirement def <'CMP-M1-L'> CMPM1L_PlateauL specializes UpperBoundRequirement {
        doc /* [H]{State} Motor L plateau within +/-5 % of bound value. */
        subject rover : WallRover;
        attribute :>> measured = rover.motorL.plateauDev;
        attribute :>> target   = rover.plateauDevTol;
    }
    requirement def <'CMP-M1-R'> CMPM1R_PlateauR specializes UpperBoundRequirement {
        doc /* [H]{State} Motor R plateau within +/-5 % of bound value. */
        subject rover : WallRover;
        attribute :>> measured = rover.motorR.plateauDev;
        attribute :>> target   = rover.plateauDevTol;
    }
    requirement def <'CMP-M2-L'> CMPM2L_BrakeL specializes UpperBoundRequirement {
        doc /* [H]{Event} Motor L wheel-stop distance within the calibrated
             * ceiling v^2/(2a) + z*sigma_b. */
        subject rover : WallRover;
        attribute :>> measured = rover.motorL.brakeDistance;
        attribute :>> target   = rover.brakeDistCeiling;
    }
    requirement def <'CMP-M2-R'> CMPM2R_BrakeR specializes UpperBoundRequirement {
        doc /* [H]{Event} Motor R wheel-stop distance within the calibrated
             * ceiling v^2/(2a) + z*sigma_b. */
        subject rover : WallRover;
        attribute :>> measured = rover.motorR.brakeDistance;
        attribute :>> target   = rover.brakeDistCeiling;
    }
    requirement def <'CMP-M3-L'> CMPM3L_SignL specializes LowerBoundRequirement {
        doc /* [H]{Ubiquitous} Motor L forward sign resolved and validated. */
        subject rover : WallRover;
        attribute :>> measured = rover.motorL.forwardSignValid;
        attribute :>> target   = rover.unity;
    }
    requirement def <'CMP-M3-R'> CMPM3R_SignR specializes LowerBoundRequirement {
        doc /* [H]{Ubiquitous} Motor R forward sign resolved and validated. */
        subject rover : WallRover;
        attribute :>> measured = rover.motorR.forwardSignValid;
        attribute :>> target   = rover.unity;
    }
    requirement def <'CMP-M4-L'> CMPM4L_NoCreepL specializes UpperBoundRequirement {
        doc /* [H]{State} Motor L post-stop travel <= postStopBound over 2 s. */
        subject rover : WallRover;
        attribute :>> measured = rover.motorL.postStopTravel;
        attribute :>> target   = rover.postStopBound;
    }
    requirement def <'CMP-M4-R'> CMPM4R_NoCreepR specializes UpperBoundRequirement {
        doc /* [H]{State} Motor R post-stop travel <= postStopBound over 2 s. */
        subject rover : WallRover;
        attribute :>> measured = rover.motorR.postStopTravel;
        attribute :>> target   = rover.postStopBound;
    }
    requirement def <'CMP-M5-L'> CMPM5L_EncoderL specializes UpperBoundRequirement {
        doc /* [H]{Ubiquitous} Motor L encoder: zero dropouts, monotone under
             * unidirectional motion. */
        subject rover : WallRover;
        attribute :>> measured = rover.motorL.encoderDropouts;
        attribute :>> target   = rover.nil;
    }
    requirement def <'CMP-M5-R'> CMPM5R_EncoderR specializes UpperBoundRequirement {
        doc /* [H]{Ubiquitous} Motor R encoder: zero dropouts, monotone under
             * unidirectional motion. */
        subject rover : WallRover;
        attribute :>> measured = rover.motorR.encoderDropouts;
        attribute :>> target   = rover.nil;
    }
    requirement def <'CMP-U1-A'> CMPU1A_NoiseA specializes UpperBoundRequirement {
        doc /* [H]{Ubiquitous} US-A static noise sigma within bound. */
        subject rover : WallRover;
        attribute :>> measured = rover.usFrontA.noiseSigma;
        attribute :>> target   = rover.noiseBound;
    }
    requirement def <'CMP-U1-B'> CMPU1B_NoiseB specializes UpperBoundRequirement {
        doc /* [H]{Ubiquitous} US-B static noise sigma within bound. */
        subject rover : WallRover;
        attribute :>> measured = rover.usFrontB.noiseSigma;
        attribute :>> target   = rover.noiseBound;
    }
    requirement def <'CMP-U2-A'> CMPU2A_OffsetA specializes UpperBoundRequirement {
        doc /* [H]{Ubiquitous} US-A mounting offset anchored at T3; residual
             * <= 3 mm at the operating point. */
        subject rover : WallRover;
        attribute :>> measured = rover.usFrontA.offsetResidual;
        attribute :>> target   = rover.offsetTol;
    }
    requirement def <'CMP-U2-B'> CMPU2B_OffsetB specializes UpperBoundRequirement {
        doc /* [H]{Ubiquitous} US-B mounting offset anchored at T3; residual
             * <= 3 mm at the operating point. */
        subject rover : WallRover;
        attribute :>> measured = rover.usFrontB.offsetResidual;
        attribute :>> target   = rover.offsetTol;
    }
    requirement def <'CMP-U3-A'> CMPU3A_DataAgeA specializes UpperBoundRequirement {
        doc /* [H]{Ubiquitous} US-A data age bound within +/-10 ms. */
        subject rover : WallRover;
        attribute :>> measured = rover.usFrontA.dataAgeError;
        attribute :>> target   = rover.dataAgeTol;
    }
    requirement def <'CMP-U3-B'> CMPU3B_DataAgeB specializes UpperBoundRequirement {
        doc /* [H]{Ubiquitous} US-B data age bound within +/-10 ms. */
        subject rover : WallRover;
        attribute :>> measured = rover.usFrontB.dataAgeError;
        attribute :>> target   = rover.dataAgeTol;
    }
    requirement def <'CMP-U4-A'> CMPU4A_ValidityFloorA specializes UpperBoundRequirement {
        doc /* [H]{Event} US-A sub-floor readings flagged, never fused. */
        subject rover : WallRover;
        attribute :>> measured = rover.usFrontA.subFloorLeakage;
        attribute :>> target   = rover.nil;
    }
    requirement def <'CMP-U4-B'> CMPU4B_ValidityFloorB specializes UpperBoundRequirement {
        doc /* [H]{Event} US-B sub-floor readings flagged, never fused. */
        subject rover : WallRover;
        attribute :>> measured = rover.usFrontB.subFloorLeakage;
        attribute :>> target   = rover.nil;
    }
    requirement def <'CMP-U5-A'> CMPU5A_RefreshA specializes UpperBoundRequirement {
        doc /* [H]{Ubiquitous} US-A update interval within bound; staleness
             * detectable. */
        subject rover : WallRover;
        attribute :>> measured = rover.usFrontA.refreshInterval;
        attribute :>> target   = rover.refreshBound;
    }
    requirement def <'CMP-U5-B'> CMPU5B_RefreshB specializes UpperBoundRequirement {
        doc /* [H]{Ubiquitous} US-B update interval within bound; staleness
             * detectable. */
        subject rover : WallRover;
        attribute :>> measured = rover.usFrontB.refreshInterval;
        attribute :>> target   = rover.refreshBound;
    }
    requirement def <'CMP-I1'> CMPI1_ImuStability specializes UpperBoundRequirement {
        doc /* [H]{Ubiquitous} IMU heading drift + noise over 10 s static
             * within bound (supports SYS-8). */
        subject rover : WallRover;
        attribute :>> measured = rover.imuDriftTenS;
        attribute :>> target   = rover.imuDriftBound;
    }
    requirement def <'CMP-I2'> CMPI2_ContactWitness specializes LowerBoundRequirement {
        doc /* [H][D]{Event} Contact-witness spike detector armed (logs
             * decel spike at near-zero gap; expected never to fire). */
        subject rover : WallRover;
        attribute :>> measured = rover.contactWitnessArmed;
        attribute :>> target   = rover.unity;
    }
    requirement def <'CMP-H1'> CMPH1_LoopTiming specializes UpperBoundRequirement {
        doc /* [H]{Ubiquitous} Loop jitter p95 within bound (period value is
             * the calibrated loopPeriod parameter). */
        subject rover : WallRover;
        attribute :>> measured = rover.loopJitterP95;
        attribute :>> target   = rover.jitterBound;
    }
    requirement def <'CMP-H2'> CMPH2_Emission specializes UpperBoundRequirement {
        doc /* [H]{Ubiquitous} Emission completes within the budget; sentinel
             * guaranteed by SYS-10's try/finally structure. */
        subject rover : WallRover;
        attribute :>> measured = rover.emissionDuration;
        attribute :>> target   = rover.emissionBudget;
    }
    requirement def <'CMP-R1'> CMPR1_RearCrossCheck specializes UpperBoundRequirement {
        doc /* [H][D]{Optional} Where the rear ranger is valid at start, its
             * delta tracks encoder distance within bound; otherwise the
             * channel is dropped by traceability (verdict at Gate B). */
        subject rover : WallRover;
        attribute :>> measured = rover.usRear.trackError;
        attribute :>> target   = rover.rearTrackBound;
    }
}

// ============================================================================
// STRUCTURAL AUDIT (the checks grammar cannot see; run mechanically by the
// EAM twin, 03_wall_rover_eam_v1.0.py :: structural_audit() — result PASS):
//  (1) Edge-set: the nested requirement usages above realise exactly the 45
//      primary edges of RS-WAR v1.0 section 5 (CMP families expanded to
//      per-device instances per spec section 4.4). Verified set-equal.
//  (2) Reachability: all 52 requirement defs reachable from the seven STK
//      roots; each root claimed by a satisfy in WallRoverDesign::WallRover.
//  (3) Operand resolution: every measured/target binding above names a
//      declared attribute of WallRover or of its parts (1:1 with the EAM
//      namespace; EAM key given in the attribute comments).
//  Per-package import resolution: WallRoverDesign imports RoverCommon,
//  RoverStructure (skeleton types), RequirementTemplates via
//  WallRoverRequirements (satisfy targets); WallRoverRequirements imports
//  RequirementTemplates (shapes) and WallRoverDesign (subject type). ISQ/SI/
//  ScalarValues supply the value types. No reference to RelationTemplates is
//  required at model level: its expressions are REPRODUCED (see derived
//  attributes), per the library's validation note, with the calc defs
//  remaining the single source of truth for their form.
//  Grammar conformance is verified out of band, after the run, not here.
// ============================================================================
