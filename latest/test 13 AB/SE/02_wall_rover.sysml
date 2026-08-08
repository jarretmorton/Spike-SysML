// ==========================================================================
// wall_rover.sysml -- the TAILORED task model for the wall-approach run.
//
// Assembled by build_sysml.py from the generic catalogs in rover_generic.sysml
// (RoverStructure / RelationTemplates / RequirementTemplates) and the authored
// requirement dataset. Model structure is instantiated from those catalogs, not
// invented: every requirement def either specialises a catalog requirement
// template and BINDS its operands against the subject's attributes, or is a
// plain decomposition node carrying nested requirement usages.
//
// TAILORING (tenet A4 -- instantiate only what the requirements call for):
//   RequirementTemplates::LowerBoundRequirement  -- instantiated (8 times)
//   RequirementTemplates::UpperBoundRequirement  -- instantiated (14 times)
//   RelationTemplates::RotationToSpeed           -- instantiated (vCruise)
//   RelationTemplates::StoppingDistance          -- instantiated (psiBelieved)
//   RelationTemplates::MaxSpeedFromBudget        -- instantiated (vBudget)
//   RoverStructure::DistanceSensor               -- 2 of 3 used; rear one drops
//   RoverStructure::ReflectanceSensor            -- drops (no requirement)
//
// PARAMETERS ARE UNCALIBRATED, NOT ZEROED (tenet A3): every attribute in the
// parameter spine below is annotated FREE or BOUND with the activity that binds
// it. Nothing carries an eyeballed number.
//
// The executable realisation is wallstop_model.py; each attribute here names
// exactly one Python variable there, checked both ways by structural_check.py.
// ==========================================================================

package WallRunDesign {
    doc /*
     * The design subject: a Rover tailored to the wall-approach task. It claims
     * the stakeholder need with satisfy, so evaluating the satisfy/require
     * roll-up over the bound attribute values IS the pre-run verification
     * artifact.
     */

    private import ISQ::*;
    private import SI::*;
    private import ScalarValues::*;
    private import RoverCommon::*;
    private import RoverStructure::*;

    // Local dimensionless value types, following the generic file's practice of
    // carrying awkward units as reals rather than depending on ISQ angle names.
    // Degrees, not radians: the IMU and the motor API both report degrees, and
    // the requirement thresholds are authored in degrees, so carrying radians
    // here would introduce a silent conversion between the model and the code.
    attribute def AngleDegrees :> Real;
    attribute def AngularRate  :> Real;   // degrees per second
    attribute def RangePerAngle :> Real;  // mm of reported range per degree
    attribute def Fraction     :> Real;   // dimensionless ratio or count

    part def WallRover specializes Rover {
        doc /*
         * Tailoring of RoverStructure::Rover. The inherited open multiplicities are
         * realised as two drive motors and two forward rangers; the third
         * (rear-facing) ranger and the floor reflectance sensor are inherited from
         * the platform but unused -- no requirement traces to them, which is the
         * recorded reason for their absence (GtWR rule 7, absence by traceability),
         * and CAL-1 logs both to VERIFY that absence rather than assume it.
         *
         * All requirement operands are bound one level deep from the subject
         * (rover.attr), which is the validated binding form; per-effector and
         * platform-nested quantities are therefore hoisted to attributes here, with
         * the source noted on each.
         */

        part motorLeft       : DriveMotor;       // CMP-1
        part motorRight      : DriveMotor;       // CMP-2
        part rangerPrimary   : DistanceSensor;   // CMP-4, CMP-5, CMP-20, CMP-21, CMP-17
        part rangerSecondary : DistanceSensor;   // CMP-7 (cross-source)
        // inherited and UNUSED: rangers[rear], floor  -- see doc above

        // ---- parameter spine: 1:1 with wallstop_model.py -------------------
        attribute omegaCmd : AngularRate;
            // [deg/s; DESIGN; design]  py:omega_cmd
            // commanded wheel speed, deliberately above the ceiling so the firmware
            // clamps to the physical maximum (SYS-1)
        attribute omegaCruise : AngularRate;
            // [deg/s; FREE; free; bound by CAL-1/P2]  py:omega_cruise
            // achieved steady wheel speed at the ceiling
        attribute kEff : RangePerAngle;
            // [mm/deg; FREE; free; bound by CAL-1/P6 (static staircase) + P2 (cruise sweep)]  py:k_eff
            // reported-range mm per degree of wheel rotation; bundles wheel radius,
            // gearing and slip (RelationTemplates::RotationToSpeed.k)
        attribute aAccel : AccelerationValue;
            // [mm/s^2; FREE; free; bound by CAL-1/P2]  py:a_accel
            // forward acceleration to cruise; upper end capped by the commanded
            // acceleration limit (design), lower end by torque
        attribute aBrake : AccelerationValue;
            // [mm/s^2; FREE; free; bound by CAL-1/P2+P4+P5 (3-speed fit)]  py:a_brake
            // effective deceleration under brake()
        attribute tChain : DurationValue;
            // [s; FREE; free; bound by CAL-1/P2 (decel onset)]  py:t_chain
            // RoverCommon::RoverLatency.tChain -- command-to-torque lag
        attribute psiBrake : LengthValue;
            // [mm; FREE; free; bound by CAL-1/P2+P4 (direct odometric+ranger measurement at cruise)]  py:psi_brake
            // post-command travel to rest AT CRUISE. Bound by direct measurement at
            // the operating point (zero extrapolation); prior range is derived from
            // the (v, t_chain, a_brake) priors so the prior box stays
            // self-consistent
        attribute sigmaPsi : LengthValue;
            // [mm; FREE; free; bound by CAL-1/P2 vs P4 (+VER run)]  py:sigma_psi
            // run-to-run scatter of psi_brake
        attribute bOffset : LengthValue;
            // [mm; FREE; free; bound by CAL-1/P7 + M1 (operator ground truth)]  py:b_offset
            // composite range->clearance offset of the PRIMARY ranger: G = r +
            // b_offset. Bundles mounting recess and sensor bias. NO onboard channel
            // observes it -- this is the parameter the one costed operator
            // measurement buys.
        attribute sigmaB : LengthValue;
            // [mm; FREE; free; bound by M1]  py:sigma_b
            // uncertainty of the b_offset anchor (ruler resolution + static read
            // noise)
        attribute lSensor : DurationValue;
            // [s; FREE; free; bound by CAL-1/P2+P4 (dynamic-vs-static offset comparison)]  py:l_sensor
            // ranger staleness: r(t) reports the range as it was at t - l_sensor
        attribute sigmaLs : DurationValue;
            // [s; FREE; free; bound by CAL-1/P2+P4]  py:sigma_ls
            // residual uncertainty of l_sensor after calibration
        attribute tRefresh : DurationValue;
            // [s; FREE; free; bound by CAL-1/P2]  py:t_refresh
            // DistanceSensor.refreshInterval -- fresh-sample period
        attribute qRange : LengthValue;
            // [mm; FREE; free; bound by CAL-1/P2+P6]  py:q_range
            // reported-range quantisation step (reporting artifact, D1)
        attribute epsScale : Fraction;
            // [1; FREE; free; bound by CAL-1/P6 (static staircase regression)]  py:eps_scale
            // ranger scale error against odometry over the working range
        attribute rMinValid : LengthValue;
            // [mm; FREE; free; bound by CAL-1/P6+P7]  py:r_min_valid
            // minimum validly reported range
        attribute rMaxValid : LengthValue;
            // [mm; BOUND; environment]  py:r_max_valid
            // no-echo / saturation value
        attribute dAgree : LengthValue;
            // [mm; FREE; free; bound by CAL-1/P0+P6+P7]  py:d_agree
            // static primary-vs-secondary ranger disagreement
        attribute dtLoop : DurationValue;
            // [s; DESIGN; design]  py:dt_loop
            // hot-path control-loop period
        attribute nLook : Fraction;
            // [1; DESIGN; design]  py:n_look
            // trigger look-ahead in loop periods; the sub-loop wait makes a generous
            // look-ahead free, which is what makes the trigger immune to loop jitter
        attribute nFuse : Fraction;
            // [1; DESIGN; design]  py:n_fuse
            // fresh ranger samples averaged by the range-offset estimator
        attribute nFuseMin : Fraction;
            // [1; DESIGN; design]  py:n_fuse_min
            // minimum fused samples before the primary trigger arms
        attribute gTarget : LengthValue;
            // [mm; DESIGN; design]  py:g_target
            // commanded target clearance. CAL-1 uses a prior-box-safe value; the
            // operating value is frozen at GATE B
        attribute gFloor : LengthValue;
            // [mm; DESIGN; design]  py:g_floor
            // dead-reckoning backstop clearance (fires only if the primary trigger
            // did not)
        attribute sBackstop : LengthValue;
            // [mm; DESIGN; design]  py:s_backstop
            // ABSOLUTE odometric travel limit: brake unconditionally at this travel.
            // In CAL-1 it is set tight (300 mm) so the first max-speed brake event
            // happens far from the wall and its safety depends only on k_eff, which
            // the static staircase binds first -- it removes the psi prior from the
            // safety argument entirely. In operation it is the fail-safe backstop of
            // CMP-10. Same code path either way.
        attribute dOdoDrift : Fraction;
            // [1; FREE; free; bound by CAL-1/P2..P7 (o_rest vs o_start consistency over the traverse)]  py:d_odo_drift
            // odometric scale drift beyond k_eff within one run (slip variation).
            // Degrades the dead-reckoning backstop but not the fused estimator,
            // which re-anchors
        attribute eTrig : DurationValue;
            // [s; FREE; free; bound by CAL-1/P2 (commanded vs achieved brake instant)]  py:e_trig
            // brake-instant timing error: 1 ms wait granularity + loop overrun
        attribute zConf : Fraction;
            // [1; DESIGN; design]  py:z_conf
            // margin coverage factor: m_contact = z_conf * sigma_rss
        attribute kObj : Fraction;
            // [1; DESIGN; design]  py:k_obj
            // objective efficiency cap: g_target <= k_obj * m_contact
        attribute wHalf : LengthValue;
            // [mm; FREE; free; bound by not scheduled -- low leverage (see sensitivity table)]  py:w_half
            // half-width of the rover's front face; converts heading error into
            // corner loss
        attribute psiHead : AngleDegrees;
            // [deg; FREE; free; bound by CAL-1/P2+P4 (IMU yaw + differential odometry)]  py:psi_head
            // heading deviation accumulated by the stop
        attribute dPsiHead : AngleDegrees;
            // [deg; FREE; free; bound by CAL-1/P2 vs P4]  py:d_psi_head
            // run-to-run variation of heading deviation
        attribute psiLimit : AngleDegrees;
            // [deg; DESIGN; design]  py:psi_limit
            // SYS-4 heading-deviation limit
        attribute gStart : LengthValue;
            // [mm; FREE; environment; bound by CAL-1/P0 (static baseline, in reported-range space)]  py:g_start
            // true clearance at the start line; the operator holds it constant
        attribute tRefreshPhase : Fraction;
            // [1; FREE; environment]  py:t_refresh_phase
            // ranger ping phase at program start as a fraction of t_refresh
            // (nuisance variable, uncontrollable, re-drawn every run)
        attribute slipBrake : Fraction;
            // [1; FREE; free; bound by CAL-1/P2+P4 (o_rest vs o_trigger consistency)]  py:slip_brake
            // fraction by which odometry UNDER-reads travel during braking (skid).
            // Detected as an inconsistency between the ranger and odometer over the
            // brake phase; a systematic that would ship a too-small psi if ignored
        attribute sigmaEstLimit : LengthValue;
            // [mm; DESIGN; design]  py:sigma_est_limit
            // SYS-7 limit on onboard clearance-estimate uncertainty
        attribute omegaLeft : AngularRate;
            // [deg/s; FREE; free; bound by CAL-1/P4 (left encoder cruise plateau)]  py:omega_left
            // CMP-1 unit quantity
        attribute omegaRight : AngularRate;
            // [deg/s; FREE; free; bound by CAL-1/P4 (right encoder cruise plateau)]  py:omega_right
            // CMP-2 unit quantity
        attribute dOmega : AngularRate;
            // [deg/s; FREE; free; bound by CAL-1/P4+P6 (per-motor speed traces)]  py:d_omega
            // worst wheel-speed asymmetry during cruise (CMP-14)
        attribute track : LengthValue;
            // [mm; FREE; free; bound by not scheduled -- low leverage; used only to derive the CMP-14 limit]  py:track
            // drive-wheel track width
        attribute contactFloor : LengthValue;
            // [mm; DESIGN; design]  py:contact_floor
            // SYS-2 floor: clearance at contact is zero by definition
        attribute omegaFloor : AngularRate;
            // [deg/s; FREE; free; bound by GATE B (TBD-1 = measured cruise speed - 3 sigma)]  py:omega_floor
            // CMP-1/CMP-2 threshold
        attribute psiTravelLimit : LengthValue;
            // [mm; FREE; free; bound by GATE B (TBD-10 = measured psi + 3 sigma)]  py:psi_travel_limit
            // CMP-11 threshold
        attribute sigmaPsiLimit : LengthValue;
            // [mm; FREE; free; bound by GATE B (TBD-11)]  py:sigma_psi_limit
            // CMP-22 threshold
        attribute lSensorLimit : DurationValue;
            // [s; FREE; free; bound by GATE B (TBD-5)]  py:l_sensor_limit
            // CMP-20 threshold
        attribute tRefreshLimit : DurationValue;
            // [s; FREE; free; bound by GATE B (TBD-4)]  py:t_refresh_limit
            // CMP-5 threshold
        attribute qRangeLimit : LengthValue;
            // [mm; FREE; free; bound by GATE B (TBD-6)]  py:q_range_limit
            // CMP-21 threshold
        attribute dAgreeLimit : LengthValue;
            // [mm; FREE; free; bound by GATE B (TBD-8)]  py:d_agree_limit
            // CMP-7 threshold
        attribute eTrigLimit : DurationValue;
            // [s; FREE; free; bound by GATE B (TBD-9)]  py:e_trig_limit
            // CMP-8 threshold
        attribute finalClearance : LengthValue;
            // [DERIVED by the analysis model]  py:g_pred
            // computed as g_pred()
        attribute clearanceLowerBound : LengthValue;
            // [DERIVED by the analysis model]  py:g_lower
            // computed as g_lower()
        attribute contactMargin : LengthValue;
            // [DERIVED by the analysis model]  py:m_contact
            // computed as m_contact()
        attribute sigmaRss : LengthValue;
            // [DERIVED by the analysis model]  py:sigma_rss
            // computed as sigma_rss()
        attribute vCruise : SpeedValue;
            // [DERIVED by the analysis model]  py:v_cruise
            // computed as v_cruise()
        attribute vBudget : SpeedValue;
            // [DERIVED by the analysis model]  py:v_budget
            // computed as v_budget()
        attribute sAccel : LengthValue;
            // [DERIVED by the analysis model]  py:s_accel
            // computed as s_accel()
        attribute sAccelBudget : LengthValue;
            // [DERIVED by the analysis model]  py:s_accel_budget
            // computed as s_accel_budget()
        attribute rRestPred : LengthValue;
            // [DERIVED by the analysis model]  py:r_rest_pred
            // computed as r_rest_pred()
        attribute sigmaEst : LengthValue;
            // [DERIVED by the analysis model]  py:sigma_est
            // computed as sigma_est()
        attribute psiBelieved : LengthValue;
            // [DERIVED by the analysis model]  py:psi_believed
            // computed as psi_believed()
        attribute dOmegaLimit : AngularRate;
            // [DERIVED by the analysis model]  py:d_omega_limit
            // computed as d_omega_limit()
        attribute tApproach : DurationValue;
            // [DERIVED by the analysis model]  py:t_approach
            // computed as t_approach()
        attribute oConsistency : LengthValue;
            // [DERIVED by the analysis model]  py:o_consistency
            // computed as o_consistency()
        attribute objectiveCap : LengthValue;
            // [DERIVED by the analysis model]  py:g_obj_cap
            // computed as g_obj_cap()
        attribute triggerFired : Fraction;
            // [DERIVED by the analysis model]  py:trigger
            // computed as trigger()
        attribute triggerFloor : Fraction;
            // [DERIVED by the analysis model]  py:trigger_floor
            // computed as trigger_floor()

        // ---- relation instances (expressions reproduced from the catalog) --
        // RelationTemplates::RotationToSpeed:   v = motorSpeed * k
        //   vCruise = omegaCruise * kEff
        // RelationTemplates::StoppingDistance:  d = v*tResponse + v^2/(2a) + margin
        //   psiBelieved = vCruise * tChain + vCruise ** 2 / (2 * aBrake) + 0
        //   NOTE psiBrake is bound by DIRECT measurement at the operating point;
        //   this relation supplies only the first-order speed correction and the
        //   3-point residual check (catalog guidance + tenet A2).
        // RelationTemplates::MaxSpeedFromBudget: feasibility of the runway
        //   vBudget = -aBrake*tChain + (aBrake^2*tChain^2
        //             + 2*aBrake*(gStart - gTarget - 0))**0.5
        // Derived margin (tenet A6, root-sum-square of independent contributors):
        //   sigmaRss = ( (qRange/(12*nFuse)**0.5)**2 + sigmaB**2 + sigmaPsi**2
        //             + (vCruise*sigmaLs)**2 + (vCruise*eTrig)**2
        //             + (wHalf*sin(dPsiHead))**2 )**0.5
        //   contactMargin = zConf * sigmaRss
        //   objectiveCap  = kObj * contactMargin

        satisfy requirement : WallRunRequirements::WallRunNeed;
    }
}

package WallRunRequirements {
    doc /*
     * Formal realisation of the requirements specification, which remains the
     * source of truth: on any disagreement the specification governs. Each task
     * requirement specialises a catalog template, adds the subject, and binds
     * the template's operands with attribute :>> measured = rover.attr, so the
     * require constraint is inherited and the evaluable logic lives in exactly
     * one place. Decomposition is carried by nested requirement usages.
     */

    private import RequirementTemplates::*;
    private import WallRunDesign::*;

    requirement def <'STK-0'> WallRunNeed {
        doc /*
         * Ubiquitous | STK | The rover shall perform a wall-approach run that ends
         * in a full stop as close to the wall as achievable without contact, driving
         * at maximum speed.
         *
         * RATIONALE: The stakeholder need, taken verbatim from the task. It is a
         * compound need and is therefore not verified directly: it is closed by the
         * roll-up of STK-1 (the hard constraints) and STK-2 (the objective).
         *
         * VERIFICATION: analysis+test, closed at GATE-C. Allocated to: WallRover.
         */
        subject rover : WallRover;
        requirement : SafeMaximumSpeedRun;
        requirement : ClosestStopObjective;
    }

    requirement def <'STK-1'> SafeMaximumSpeedRun {
        doc /*
         * Ubiquitous | STK | The rover shall traverse from the start line to a
         * complete stop at maximum drivetrain speed without contacting the wall.
         *
         * RATIONALE: Separates the pass/fail part of the need from the graded part
         * (GtWR rule 3). Verified by the conjunction of SYS-1..SYS-7.
         *
         * VERIFICATION: test, closed at GATE-C. Allocated to: WallRover.
         */
        subject rover : WallRover;
        requirement : MaximumApproachSpeed;
        requirement : NoWallContact;
        requirement : CompleteStop;
        requirement : StraightApproach;
        requirement : ConfigurationDiscovery;
        requirement : ClearanceReporting;
    }

    requirement def <'STK-2'> ClosestStopObjective {
        doc /*
         * Objective | STK | The rover should minimise the clearance between its
         * front-most point and the wall at the full stop.
         *
         * RATIONALE: The scored objective. Stated with 'should' and graded, never as
         * a pass/fail constraint (GtWR rule 3); bridged to the hard constraint SYS-2
         * by the derived margin requirement SYS-5.
         *
         * VERIFICATION: analysis+test, closed at GATE-C. Allocated to: WallRover.
         */
        subject rover : WallRover;
        requirement : MarginEfficiency;
    }

    requirement def <'SYS-1'> MaximumApproachSpeed specializes LowerBoundRequirement {
        doc /*
         * State-driven | SYS | While in the APPROACH state, the rover shall command
         * both drive motors at a speed no less than the drivetrain's maximum
         * achievable speed.
         *
         * RATIONALE: The task forbids slowing down for safety margin. Stated as a
         * command-side lower bound so that 'maximum speed' is a construction
         * property of the program (verifiable by inspection) as well as a measured
         * one.
         *
         * VERIFICATION: inspection+test, closed at CAL-1. Allocated to: WallRover.
         */
        subject rover : WallRover;
        attribute :>> measured = rover.omegaCmd;
        attribute :>> target   = rover.omegaCruise;
        requirement : CruiseAtCeiling;
    }

    requirement def <'SYS-2'> NoWallContact specializes LowerBoundRequirement {
        doc /*
         * Unwanted | SYS | The rover shall not contact the wall.
         *
         * RATIONALE: The task's hard constraint. Contact is a pass/fail event, so it
         * is stated as an Unwanted-behaviour requirement over the clearance channel
         * with a zero floor, and cross-checked by an independent contact channel
         * (CMP-19).
         *
         * VERIFICATION: test, closed at GATE-C. Allocated to: WallRover.
         */
        subject rover : WallRover;
        attribute :>> measured = rover.finalClearance;
        attribute :>> target   = rover.contactFloor;
        requirement : ClearanceMarginFloor;
        requirement : ClearanceEstimation;
        requirement : StopPointComputation;
        requirement : FailSafeResponse;
    }

    requirement def <'SYS-3'> CompleteStop {
        doc /*
         * Event-driven | SYS | When the brake command is issued, the rover shall
         * reach zero ground speed.
         *
         * RATIONALE: The task requires a complete stop, not merely a slow-down; a
         * run that rolls to a halt outside the observed window would not be a stop.
         *
         * VERIFICATION: test, closed at CAL-1. Allocated to: WallRover.
         */
        subject rover : WallRover;
        requirement : BrakeActuation;
    }

    requirement def <'SYS-4'> StraightApproach specializes UpperBoundRequirement {
        doc /*
         * Ubiquitous | SYS | DERIVED. The rover shall not deviate from its initial
         * heading by more than TBD-12 degrees during the approach.
         *
         * RATIONALE: DERIVED. The task says drive straight at the wall;
         * quantitatively, heading deviation converts a centre-line clearance into a
         * smaller corner clearance and tilts the ranger's line of sight, so it must
         * be bounded, not just observed.
         *
         * VERIFICATION: test, closed at CAL-1. TBDs: TBD-12. Allocated to:
         * WallRover.
         */
        subject rover : WallRover;
        attribute :>> measured = rover.psiHead;
        attribute :>> target   = rover.psiLimit;
        requirement : HeadingMaintenance;
    }

    requirement def <'SYS-5'> ClearanceMarginFloor specializes LowerBoundRequirement {
        doc /*
         * Ubiquitous | SYS | DERIVED. The rover's predicted final clearance shall be
         * no less than the derived no-contact margin m_contact.
         *
         * RATIONALE: DERIVED margin requirement bridging the hard constraint SYS-2
         * and the objective STK-2 (GtWR rule 3). m_contact = z_conf * sigma_rss, the
         * RSS of the independent uncertainty contributors (tenet A6) -- it is
         * computed, never guessed, and it is what makes 'as close as possible'
         * decidable.
         *
         * VERIFICATION: analysis, closed at GATE-B. TBDs: TBD-16. Allocated to:
         * WallRover.
         */
        subject rover : WallRover;
        attribute :>> measured = rover.clearanceLowerBound;
        attribute :>> target   = rover.contactFloor;
    }

    requirement def <'SYS-6'> ConfigurationDiscovery {
        doc /*
         * Event-driven | SYS | DERIVED. When the program starts, the rover shall
         * determine the device type on every port it uses and the drivetrain sign
         * convention before commanding motion.
         *
         * RATIONALE: DERIVED. The task states the port map and direction conventions
         * are unknown and must be determined; a wrong polarity would drive the rover
         * backwards or spin it, so this gates all motion.
         *
         * VERIFICATION: test, closed at CAL-1. Allocated to: WallRover.
         */
        subject rover : WallRover;
        requirement : PortAndPolarityIdentification;
    }

    requirement def <'SYS-7'> ClearanceReporting specializes UpperBoundRequirement {
        doc /*
         * Ubiquitous | SYS | DERIVED. The rover shall report, for each run, an
         * estimate of its final clearance with an uncertainty not exceeding TBD-14
         * millimetres.
         *
         * RATIONALE: DERIVED. The operation close-out requires a per-run onboard
         * estimate frozen before ground truth is disclosed, and the objective may
         * only be closed on a channel whose accuracy has been validated -- both need
         * a stated uncertainty.
         *
         * VERIFICATION: test, closed at GATE-C. TBDs: TBD-14. Allocated to:
         * WallRover.
         */
        subject rover : WallRover;
        attribute :>> measured = rover.sigmaEst;
        attribute :>> target   = rover.sigmaEstLimit;
        requirement : TelemetryAndEstimate;
    }

    requirement def <'FUN-1'> CruiseAtCeiling specializes LowerBoundRequirement {
        doc /*
         * Event-driven | FUN | When the APPROACH state is entered, the rover shall
         * accelerate to the commanded ceiling speed and hold it until the brake
         * command.
         *
         * RATIONALE: Allocates SYS-1 to the propulsion function and makes the cruise
         * phase long enough that the stopping travel is calibrated at the speed it
         * is used at.
         *
         * VERIFICATION: test, closed at CAL-1. Allocated to: WallRover.
         */
        subject rover : WallRover;
        attribute :>> measured = rover.omegaCruise;
        attribute :>> target   = rover.omegaFloor;
        requirement : LeftMotorCeiling;
        requirement : RightMotorCeiling;
        requirement : AccelWithinRunway;
    }

    requirement def <'FUN-2'> ClearanceEstimation specializes UpperBoundRequirement {
        doc /*
         * Ubiquitous | FUN | The rover shall estimate the clearance from its
         * front-most point to the wall continuously throughout the approach.
         *
         * RATIONALE: The stop decision needs clearance, not raw range: the two
         * differ by the ranger's mounting offset and bias, which is a separate
         * calibrated quantity.
         *
         * VERIFICATION: test, closed at CAL-1. Allocated to: WallRover.
         */
        subject rover : WallRover;
        attribute :>> measured = rover.sigmaEst;
        attribute :>> target   = rover.sigmaEstLimit;
        requirement : PrimaryRangerBias;
        requirement : PrimaryRangerRefresh;
        requirement : PrimaryRangerStaleness;
        requirement : PrimaryRangerQuantisation;
        requirement : OdometryScale;
        requirement : SecondaryRangerAgreement;
    }

    requirement def <'FUN-3'> StopPointComputation specializes LowerBoundRequirement {
        doc /*
         * Ubiquitous | FUN | The rover shall compute the brake-command instant at
         * which the predicted rest clearance equals the commanded target clearance.
         *
         * RATIONALE: Makes the stop criterion an explicit prediction rather than a
         * tuned threshold, so it can be verified against the model before the run
         * and transfers unchanged from calibration to operation.
         *
         * VERIFICATION: analysis+test, closed at CAL-1. Allocated to: WallRover.
         */
        subject rover : WallRover;
        attribute :>> measured = rover.triggerFired;
        attribute :>> target   = rover.triggerFloor;
        requirement : TriggerTimingResolution;
    }

    requirement def <'FUN-4'> BrakeActuation {
        doc /*
         * Event-driven | FUN | When the brake instant is reached, the rover shall
         * apply maximum braking to both drive wheels.
         *
         * RATIONALE: Allocates SYS-3 to the actuation function. Passive braking is
         * chosen so the approach to rest is monotone: the final position equals the
         * closest position, so the scored gap and the contact risk refer to the same
         * point.
         *
         * VERIFICATION: test, closed at CAL-1. Allocated to: WallRover.
         */
        subject rover : WallRover;
        requirement : BrakeTravel;
        requirement : BrakeTravelRepeatability;
        requirement : NoPostStopMotion;
    }

    requirement def <'FUN-5'> FailSafeResponse {
        doc /*
         * Event-driven | FUN | DERIVED. When any monitored channel violates its
         * stated plausibility bound, the rover shall brake immediately.
         *
         * RATIONALE: DERIVED. Graded assurance (tenet A1): contact is the
         * high-consequence outcome, so the primary range channel must not be
         * single-string. Every fail-safe path errs toward braking early.
         *
         * VERIFICATION: test, closed at CAL-1. Allocated to: WallRover.
         */
        subject rover : WallRover;
        requirement : PlausibilityBounds;
        requirement : DeadReckonBackstop;
    }

    requirement def <'FUN-6'> HeadingMaintenance {
        doc /*
         * Ubiquitous | FUN | DERIVED. The rover shall command both drive wheels at
         * equal speed throughout the approach.
         *
         * RATIONALE: DERIVED. Equal commanded wheel speed is the open-loop means of
         * meeting SYS-4 without introducing an uncalibrated steering gain (tenet
         * A3); any residual veer is measured and carried as an uncertainty
         * contributor.
         *
         * VERIFICATION: test, closed at CAL-1. Allocated to: WallRover.
         */
        subject rover : WallRover;
        requirement : HeadingSensing;
        requirement : WheelSpeedSymmetry;
    }

    requirement def <'FUN-7'> PortAndPolarityIdentification {
        doc /*
         * Event-driven | FUN | DERIVED. When the program starts, the rover shall
         * identify the device type on each port and the motor sign pair that
         * produces forward motion.
         *
         * RATIONALE: Allocates SYS-6. Identification is done from onboard evidence
         * so no operator input is consumed for it.
         *
         * VERIFICATION: test, closed at CAL-1. Allocated to: WallRover.
         */
        subject rover : WallRover;
        requirement : DeviceTypeIdentification;
        requirement : DrivePolarityIdentification;
    }

    requirement def <'FUN-8'> TelemetryAndEstimate {
        doc /*
         * Ubiquitous | FUN | DERIVED. The rover shall report two independent
         * estimates of its final clearance at each rest position.
         *
         * RATIONALE: DERIVED from SYS-7 and cross-sourcing (GtWR rule 6 / tenet B1):
         * two independent estimates make a disagreement visible, which is the only
         * way an estimate error is detectable without spending operator
         * measurements.
         *
         * VERIFICATION: test, closed at CAL-1. Allocated to: WallRover.
         */
        subject rover : WallRover;
        requirement : RestRangeEstimator;
        requirement : OdometricEstimator;
        requirement : ContactDetection;
    }

    requirement def <'CMP-1'> LeftMotorCeiling specializes LowerBoundRequirement {
        doc /*
         * Ubiquitous | CMP | The left drive motor shall sustain an angular speed of
         * at least TBD-1 degrees per second when commanded above its ceiling.
         *
         * RATIONALE: Single-effector leaf of FUN-1: fixes what 'maximum' numerically
         * is for this motor, and makes a weak or dragging motor visible as a unit
         * failure.
         *
         * VERIFICATION: test, closed at CAL-1. TBDs: TBD-1. Allocated to: MotorLeft.
         */
        subject rover : WallRover;
        attribute :>> measured = rover.omegaLeft;
        attribute :>> target   = rover.omegaFloor;
    }

    requirement def <'CMP-2'> RightMotorCeiling specializes LowerBoundRequirement {
        doc /*
         * Ubiquitous | CMP | The right drive motor shall sustain an angular speed of
         * at least TBD-1 degrees per second when commanded above its ceiling.
         *
         * RATIONALE: Single-effector leaf of FUN-1, mirror of CMP-1. Verified
         * separately so a one-sided fault cannot hide inside an average.
         *
         * VERIFICATION: test, closed at CAL-1. TBDs: TBD-1. Allocated to:
         * MotorRight.
         */
        subject rover : WallRover;
        attribute :>> measured = rover.omegaRight;
        attribute :>> target   = rover.omegaFloor;
    }

    requirement def <'CMP-3'> AccelWithinRunway specializes UpperBoundRequirement {
        doc /*
         * Ubiquitous | CMP | DERIVED. The drivetrain shall reach its ceiling speed
         * within TBD-2 millimetres of travel from the start line.
         *
         * RATIONALE: DERIVED feasibility leaf: if the ceiling is not reached before
         * the brake point, the run is not at maximum speed and the stopping travel
         * is calibrated at the wrong speed. Instantiates MaxSpeedFromBudget.
         *
         * VERIFICATION: analysis, closed at CAL-1. TBDs: TBD-2. Allocated to:
         * Drivetrain.
         */
        subject rover : WallRover;
        attribute :>> measured = rover.sAccel;
        attribute :>> target   = rover.sAccelBudget;
    }

    requirement def <'CMP-4'> PrimaryRangerBias {
        doc /*
         * Ubiquitous | CMP | DERIVED. The primary forward ranger shall report the
         * wall range with a fixed offset of TBD-3 millimetres relative to the
         * rover's front-most point over the interval 40 mm to 1000 mm.
         *
         * RATIONALE: Single-effector leaf of FUN-2 and the highest-leverage
         * unobservable: no onboard channel can see where the bumper is relative to
         * the sensor datum, so this TBD is bound by the one costed operator
         * measurement.
         *
         * VERIFICATION: test, closed at CAL-1. TBDs: TBD-3. Allocated to:
         * RangerPrimary.
         */
        subject rover : WallRover;
    }

    requirement def <'CMP-5'> PrimaryRangerRefresh specializes UpperBoundRequirement {
        doc /*
         * Ubiquitous | CMP | DERIVED. The primary forward ranger shall deliver a
         * fresh sample at intervals not exceeding TBD-4 milliseconds.
         *
         * RATIONALE: Bounds how stale the newest sample can be, which sets how far
         * the rover moves between absolute updates. Split from staleness and
         * quantisation so each is one verifiable claim (GtWR rule 1).
         *
         * VERIFICATION: test, closed at CAL-1. TBDs: TBD-4. Allocated to:
         * RangerPrimary.
         */
        subject rover : WallRover;
        attribute :>> measured = rover.tRefresh;
        attribute :>> target   = rover.tRefreshLimit;
    }

    requirement def <'CMP-20'> PrimaryRangerStaleness specializes UpperBoundRequirement {
        doc /*
         * Ubiquitous | CMP | DERIVED. The primary forward ranger shall report a
         * range whose age does not exceed TBD-5 milliseconds at the instant it
         * becomes readable.
         *
         * RATIONALE: DERIVED. Staleness is a bias, not noise: at cruise it converts
         * directly into millimetres of unseen travel, so it must be characterised
         * and compensated rather than idealised away (tenet D2).
         *
         * VERIFICATION: test, closed at CAL-1. TBDs: TBD-5. Allocated to:
         * RangerPrimary.
         */
        subject rover : WallRover;
        attribute :>> measured = rover.lSensor;
        attribute :>> target   = rover.lSensorLimit;
    }

    requirement def <'CMP-21'> PrimaryRangerQuantisation specializes UpperBoundRequirement {
        doc /*
         * Ubiquitous | CMP | DERIVED. The primary forward ranger shall report range
         * in steps not exceeding TBD-6 millimetres.
         *
         * RATIONALE: DERIVED. A reporting artifact (tenet D1): the quantisation
         * step, not the physical resolution, is what the estimator sees, and it sets
         * the noise floor of the fused offset.
         *
         * VERIFICATION: test, closed at CAL-1. TBDs: TBD-6. Allocated to:
         * RangerPrimary.
         */
        subject rover : WallRover;
        attribute :>> measured = rover.qRange;
        attribute :>> target   = rover.qRangeLimit;
    }

    requirement def <'CMP-6'> OdometryScale {
        doc /*
         * Ubiquitous | CMP | DERIVED. The drive odometry shall report travel with a
         * scale factor of TBD-7 millimetres of wall range per degree of wheel
         * rotation.
         *
         * RATIONALE: Single-effector leaf of FUN-2. The scale bundles wheel radius,
         * gearing and slip, which is exactly why it is calibrated against the ranger
         * rather than computed from nominal wheel geometry (tenet A3).
         *
         * VERIFICATION: test, closed at CAL-1. TBDs: TBD-7. Allocated to:
         * Drivetrain.
         */
        subject rover : WallRover;
    }

    requirement def <'CMP-7'> SecondaryRangerAgreement specializes UpperBoundRequirement {
        doc /*
         * Ubiquitous | CMP | DERIVED. The secondary forward ranger shall agree with
         * the primary ranger within TBD-8 millimetres, after removal of their fixed
         * mounting difference, over the interval 40 mm to 1000 mm.
         *
         * RATIONALE: DERIVED cross-source (GtWR rule 6). An independent ranger
         * observing the same quantity is the fault-agnostic detector: a disagreement
         * localises a fault without assuming which channel is wrong.
         *
         * VERIFICATION: test, closed at CAL-1. TBDs: TBD-8. Allocated to:
         * RangerSecondary.
         */
        subject rover : WallRover;
        attribute :>> measured = rover.dAgree;
        attribute :>> target   = rover.dAgreeLimit;
    }

    requirement def <'CMP-8'> TriggerTimingResolution specializes UpperBoundRequirement {
        doc /*
         * Ubiquitous | CMP | DERIVED. The controller shall issue the brake command
         * within TBD-9 milliseconds of the computed brake instant.
         *
         * RATIONALE: DERIVED. Timing error converts to millimetres at cruise speed;
         * a sub-loop wait is what keeps the trigger from inheriting the loop period
         * as error.
         *
         * VERIFICATION: test, closed at CAL-1. TBDs: TBD-9. Allocated to:
         * Controller.
         */
        subject rover : WallRover;
        attribute :>> measured = rover.eTrig;
        attribute :>> target   = rover.eTrigLimit;
    }

    requirement def <'CMP-9'> PlausibilityBounds {
        doc /*
         * Ubiquitous | CMP | DERIVED. The controller shall bound every logged
         * channel by a stated physical range and shall flag any sample outside it.
         *
         * RATIONALE: DERIVED. Makes physically impossible readings surface
         * automatically, which is the trigger for unconditional escalation under
         * ANOMALY DISPOSITION.
         *
         * VERIFICATION: inspection+test, closed at CAL-1. Allocated to: Controller.
         */
        subject rover : WallRover;
    }

    requirement def <'CMP-10'> DeadReckonBackstop {
        doc /*
         * Ubiquitous | CMP | DERIVED. The controller shall brake unconditionally
         * when odometric travel reaches the configured backstop distance.
         *
         * RATIONALE: DERIVED. An independent, ranger-free stop path: it covers loss
         * of echo and, set tight, it is what makes the first max-speed brake event
         * safe before any stopping-travel calibration exists.
         *
         * VERIFICATION: test, closed at CAL-1. Allocated to: Controller.
         */
        subject rover : WallRover;
    }

    requirement def <'CMP-11'> BrakeTravel specializes UpperBoundRequirement {
        doc /*
         * Ubiquitous | CMP | DERIVED. Each drive motor shall arrest wheel rotation
         * within TBD-10 millimetres of travel from the brake command at cruise
         * speed.
         *
         * RATIONALE: Single-effector leaf of FUN-4 and the second-highest-leverage
         * parameter: it is measured directly at the operating point so no
         * extrapolation enters the stop prediction
         * (RelationTemplates::StoppingDistance guidance).
         *
         * VERIFICATION: test, closed at CAL-1. TBDs: TBD-10. Allocated to:
         * Drivetrain.
         */
        subject rover : WallRover;
        attribute :>> measured = rover.psiBrake;
        attribute :>> target   = rover.psiTravelLimit;
    }

    requirement def <'CMP-22'> BrakeTravelRepeatability specializes UpperBoundRequirement {
        doc /*
         * Ubiquitous | CMP | DERIVED. The travel from brake command to rest shall
         * not vary by more than TBD-11 millimetres between runs at cruise speed.
         *
         * RATIONALE: DERIVED. Run-to-run scatter, not the mean, is what the
         * no-contact margin is made of (tenet A6); split from CMP-11 so each is one
         * verifiable claim.
         *
         * VERIFICATION: test, closed at CAL-1. TBDs: TBD-11. Allocated to:
         * Drivetrain.
         */
        subject rover : WallRover;
        attribute :>> measured = rover.sigmaPsi;
        attribute :>> target   = rover.sigmaPsiLimit;
    }

    requirement def <'CMP-12'> NoPostStopMotion {
        doc /*
         * Unwanted | CMP | DERIVED. The rover shall not move after reaching the full
         * stop.
         *
         * RATIONALE: DERIVED. The scored gap is measured by the operator some
         * seconds after the run ends; creep or rollback between the stop and the
         * measurement would make the onboard estimate and the ground truth refer to
         * different positions.
         *
         * VERIFICATION: test, closed at CAL-1. Allocated to: Drivetrain.
         */
        subject rover : WallRover;
    }

    requirement def <'CMP-13'> HeadingSensing specializes UpperBoundRequirement {
        doc /*
         * Ubiquitous | CMP | DERIVED. The inertial unit shall report heading with a
         * drift not exceeding TBD-12 degrees over the duration of one run.
         *
         * RATIONALE: Single-effector leaf of FUN-6. The hub is power-cycled between
         * runs so heading is always relative to the start pose; only within-run
         * drift matters.
         *
         * VERIFICATION: test, closed at CAL-1. TBDs: TBD-12. Allocated to: Imu.
         */
        subject rover : WallRover;
        attribute :>> measured = rover.psiHead;
        attribute :>> target   = rover.psiLimit;
    }

    requirement def <'CMP-14'> WheelSpeedSymmetry specializes UpperBoundRequirement {
        doc /*
         * Ubiquitous | CMP | DERIVED. The two drive motors shall maintain speeds
         * within TBD-13 degrees per second of each other during cruise.
         *
         * RATIONALE: DERIVED. Differential wheel speed is the mechanism behind
         * heading deviation; measuring it separately from the IMU gives a second,
         * independent view of straightness (cross-sourcing).
         *
         * VERIFICATION: test, closed at CAL-1. TBDs: TBD-13. Allocated to:
         * Drivetrain.
         */
        subject rover : WallRover;
        attribute :>> measured = rover.dOmega;
        attribute :>> target   = rover.dOmegaLimit;
    }

    requirement def <'CMP-15'> DeviceTypeIdentification {
        doc /*
         * Event-driven | CMP | DERIVED. When the program starts, the controller
         * shall determine the device type present on each of the hub's six ports.
         *
         * RATIONALE: Single-effector leaf of FUN-7: the port map is unknown a priori
         * and every later channel depends on it.
         *
         * VERIFICATION: test, closed at CAL-1. Allocated to: Controller.
         */
        subject rover : WallRover;
    }

    requirement def <'CMP-16'> DrivePolarityIdentification {
        doc /*
         * Event-driven | CMP | DERIVED. When the port map is known, the controller
         * shall determine the pair of motor speed signs that moves the rover toward
         * the wall.
         *
         * RATIONALE: Single-effector leaf of FUN-7. Determined from the sign of the
         * range change and the heading change under a short, low-speed probe, so no
         * assumption about drivetrain mirroring is needed.
         *
         * VERIFICATION: test, closed at CAL-1. Allocated to: Controller.
         */
        subject rover : WallRover;
    }

    requirement def <'CMP-17'> RestRangeEstimator specializes LowerBoundRequirement {
        doc /*
         * Ubiquitous | CMP | DERIVED. The rover shall report a static-range
         * clearance estimate at rest whenever the reported range is not less than
         * TBD-15 millimetres.
         *
         * RATIONALE: DERIVED. The static estimate is latency-free and therefore the
         * most trusted onboard clearance channel, but it has a validity floor -- the
         * condition is stated so the hand-off to the odometric estimate is planned,
         * not improvised (CHARACTERIZATION METHOD 1).
         *
         * VERIFICATION: test, closed at CAL-1. TBDs: TBD-15. Allocated to:
         * RangerPrimary.
         */
        subject rover : WallRover;
        attribute :>> measured = rover.rRestPred;
        attribute :>> target   = rover.rMinValid;
    }

    requirement def <'CMP-18'> OdometricEstimator {
        doc /*
         * Ubiquitous | CMP | DERIVED. The rover shall report an odometric clearance
         * estimate at every rest position, independent of the reported range at
         * rest.
         *
         * RATIONALE: DERIVED. Covers the range below the ranger's validity floor and
         * provides the independent second estimate FUN-8 requires.
         *
         * VERIFICATION: test, closed at CAL-1. Allocated to: Drivetrain.
         */
        subject rover : WallRover;
    }

    requirement def <'CMP-19'> ContactDetection {
        doc /*
         * Ubiquitous | CMP | DERIVED. The inertial unit shall report forward-axis
         * acceleration throughout the brake phase at a rate sufficient to
         * distinguish braking from an impact.
         *
         * RATIONALE: DERIVED. Gives SYS-2 an onboard witness independent of the
         * ranger and of the operator's observation: an impact is a distinctive
         * acceleration transient, so 'no contact' is evidenced rather than assumed.
         *
         * VERIFICATION: test, closed at CAL-1. Allocated to: Imu.
         */
        subject rover : WallRover;
    }

    requirement def <'OBJ-1'> MarginEfficiency specializes UpperBoundRequirement {
        doc /*
         * Objective | OBJ | DERIVED. The commanded target clearance should not
         * exceed the derived no-contact margin by more than a factor of TBD-17.
         *
         * RATIONALE: DERIVED. Operationalises 'as close as possible': the smallest
         * defensible target is the uncertainty-derived margin itself, so the
         * objective is to leave no clearance beyond that margin. Below it we would
         * be buying score with contact risk; above it we are giving away score for
         * nothing.
         *
         * VERIFICATION: analysis, closed at GATE-B. TBDs: TBD-16, TBD-17. Allocated
         * to: WallRover.
         */
        subject rover : WallRover;
        attribute :>> measured = rover.gTarget;
        attribute :>> target   = rover.objectiveCap;
    }

}
