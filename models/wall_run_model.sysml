// ============================================================================
// wall_run_model.sysml — the POPULATED model for the wall-run task.
//
// RoverStructure::Rover specialised to this task's configuration, the consumed
// relation templates instantiated as derived attributes, and the full
// STK -> SYS -> FUN -> CMP requirement tree from Wall_run_requirements_spec.md
// expressed as SysML v2 requirement defs. Formal require constraints sit on the
// five SYS requirements that the spec states as constraints; the verification-
// floor (CMP) leaves are characterisation activities, carried as prose
// requirements whose tests BIND the parameters the constraints above depend on.
//
// The evaluable satisfy/require roll-up over the SYS layer IS the pre-run
// verification artifact: once calibration binds the UNCALIBRATED parameters,
// evaluating this hierarchy against those values yields the inspectable
// predicted-pass/fail tree. Today the parameters are unbound, so the formal
// constraints are pending — which is correct: the argument is committed before
// the numbers, then closed by calibration.
//
// Imports rover_generic.sysml. Validate in Syside alongside it.
// ============================================================================

package WallRunDesign {
    doc /*
     * The wall-run rover: the platform skeleton specialised to this task's
     * configuration, with task parameters declared UNCALIBRATED until the
     * calibration binds them, and the consumed relation templates
     * (RotationToSpeed, StoppingDistance, MaxSpeedFromBudget) instantiated as
     * derived attributes.
     */

    private import ISQ::*;
    private import SI::*;
    private import ScalarValues::*;
    private import RoverCommon::*;
    private import RoverStructure::*;

    part def WallRover specializes Rover {

        // --- configuration: how many of each effector, and their roles --------
        // Two drive motors, matched for open-loop straightness (steering finding).
        part redefines motors [2] : DriveMotor;
        // Three rangefinders: forward-left and forward-right (clearance = min of
        // the two), plus a rear channel for an independent distance estimate.
        part redefines rangers [3] : DistanceSensor;
        // imu and floor (reflectance) are inherited. floor is present but NO
        // wall-run requirement traces to it — see WallRunRequirements.

        // --- drive characterisation (RotationToSpeed instantiated) ------------
        attribute driveConstant : LengthValue;            // UNCALIBRATED — m per rad (CMP-M1)
        attribute maxMotorSpeed : AngularVelocityValue;   // UNCALIBRATED — matched straight-line max = slower motor's max (CMP-M2 + steering finding)
        attribute commandedMotorSpeed : AngularVelocityValue; // SYS-1 drives this to maxMotorSpeed
        // Achieved max straight-line ground speed = RotationToSpeed(maxMotorSpeed, driveConstant):
        attribute groundSpeed : SpeedValue = maxMotorSpeed * driveConstant;

        // --- response latency -------------------------------------------------
        attribute tSensorDistance : DurationValue;        // UNCALIBRATED — s, forward sensor sampling (CMP-U4)
        attribute tResponse : DurationValue = latency.tChain + tSensorDistance;

        // --- braking dynamics -------------------------------------------------
        attribute decelCollision : AccelerationValue;     // UNCALIBRATED — m/s^2; back-solved from the directly-measured stop distance at v_max (CMP-M3); feeds the threshold relation + feasibility ceiling

        // --- clearance budget and margin M ------------------------------------
        attribute dSenseMax : LengthValue;                // UNCALIBRATED — reliable forward sensing range (CMP-U1)
        // M = kSigma * RSS of the three uncertainty sources (the SYS-7 TBDs):
        attribute sigmaDStop : LengthValue;               // UNCALIBRATED — stopping-distance uncertainty (SYS-7a); SEM of the direct stop-distance measurement at v_max + latency (CMP-M3)
        attribute sigmaDMeas : LengthValue;               // UNCALIBRATED — clearance-measurement uncertainty (SYS-7b)
        attribute sigmaRun   : LengthValue;               // UNCALIBRATED — run-to-run variability (SYS-7c); verification-run spread, system-level (no CMP)
        attribute kSigma     : Real;                      // SET BY HUMAN — coverage factor
        attribute marginM : LengthValue =
            kSigma * ( sigmaDStop ** 2 + sigmaDMeas ** 2 + sigmaRun ** 2 ) ** 0.5;

        // --- speed-dependent braking threshold (StoppingDistance instantiated)-
        // The clearance at which the stop must already trigger, at full speed =
        // StoppingDistance(groundSpeed, tResponse, decelCollision, marginM):
        attribute brakingThreshold : LengthValue =
            groundSpeed * tResponse
            + groundSpeed ** 2 / (2 * decelCollision)
            + marginM;

        // Feasibility ceiling the task runs AGAINST but does not command toward:
        // the largest speed whose stop fits inside dSenseMax. If groundSpeed
        // exceeds this, full speed is infeasible (cannot stop within reliable
        // sensing range) and M cannot rescue it. This is the envelope check the
        // template exists for, surfaced here rather than added as a new SYS req.
        // = MaxSpeedFromBudget(tResponse, decelCollision, dSenseMax, marginM):
        attribute maxFeasibleSpeed : SpeedValue =
            - decelCollision * tResponse
            + ( decelCollision ** 2 * tResponse ** 2
                + 2 * decelCollision * (dSenseMax - marginM) ) ** 0.5;

        // --- run-time / telemetry-bound quantities ----------------------------
        attribute forwardClearance : LengthValue;   // min(L,R) during approach (FUN-S1/CMP-U2) — SYS-4 operand
        attribute finalClearance   : LengthValue;   // clearance at final stop — SYS-5/SYS-7 operand
        attribute headingDrift     : Angle;         // |yaw - normal| magnitude during approach (CMP-I1) — SYS-3 operand
        attribute thetaMax         : Angle;         // heading tolerance (SYS-3) — budget set from clearance geometry; CMP-I1 checks drift against it

        // ====================================================================
        // CALIBRATION SURFACE — the complete set of unbound quantities the
        // calibration step must resolve, consolidated from BOTH origins. This
        // is the model-side INDEX of the calibration intake (name + producing
        // test); the procedure-bearing register (units, method, value slots)
        // lives at the head of the calibration plan and pulls from this set.
        // Every entry here is one of the value-less attributes declared above,
        // so the worklist is mechanically reconcilable against this part def.
        //
        // Requirement TBDs — a requirement names them (cf. spec §2 register):
        //   thetaMax    (SYS-3)   heading tolerance. A BUDGET, set from lateral-
        //                         clearance geometry; CMP-I1 measures the achieved
        //                         drift checked against it (not itself measured).
        //   sigmaDStop  (SYS-7a)  stopping-distance uncertainty = the SEM of the
        //                         direct CMP-M3 stop-distance measurement (+ latency).
        //   sigmaDMeas  (SYS-7b)  clearance-measurement uncertainty =
        //                         CMP-U1 range bias/scale + FUN-S4 cross-check.
        //   sigmaRun    (SYS-7c)  run-to-run variability = VERIFICATION-RUN spread
        //                         (repeated identical stops); system-level, no CMP.
        //
        // Model-completion parameters — no requirement names them; the model
        // needs them to predict ("model completion", spec §2):
        //   driveConstant   (CMP-M1)    m per rad, motor rev -> linear distance.
        //   maxMotorSpeed   (CMP-M2)    matched straight-line max.
        //   tSensorDistance (CMP-U4)    forward sensor sampling latency.
        //   decelCollision  (CMP-M3)    deceleration, back-solved from the directly-
        //                               measured stop distance at v_max.
        //   dSenseMax       (CMP-U1)    reliable forward sensing range.
        //   latency.tChain  (platform)  compute+BLE+actuation lag; TIMING test,
        //                               no CMP (platform-common, inherited).
        //
        // NOT calibration targets: brakingThreshold (SYS-4) is DERIVED and
        // resolves once the above bind; kSigma is human-set; and the run-time/
        // telemetry quantities (commandedMotorSpeed, forwardClearance,
        // finalClearance, headingDrift) are produced during the run.
        // ====================================================================

        // --- the claim: this rover satisfies the wall-run need ----------------
        // Binds the subject of the whole requirement tree to this rover and
        // asserts every constraint below it must hold. Evaluating it post-
        // calibration is the pre-run verification artifact.
        satisfy requirement : WallRunRequirements::WallRunNeed;
    }
}

package WallRunRequirements {
    doc /*
     * SOURCE OF TRUTH. The requirements document — experiments/Wall_run_requirements_spec.md
     * — is the source of truth for the wall-run requirements. This package is a
     * formal SysML realisation of it, not a replacement: on any disagreement the
     * spec governs and the model has a bug to reconcile (requirement IDs and the
     * decomposition edge-set must match the spec's tree).
     *
     * Leveled requirements STK -> SYS -> FUN -> CMP (Wall_run_requirements_spec.md):
     * INCOSE GtWR over ISO/IEC/IEEE 29148, EARS grammar, NASA SP-2016-6105 framing.
     * Decomposition is expressed by nested requirement usages (requirement : Child).
     * Shared leaves (e.g. CMP-M1, CMP-U1, CMP-U5) appear under more than one parent
     * — the DAG of the spec, realised as multiple usages of one definition.
     *
     * Texture: the five SYS requirements the spec states AS constraints carry
     * formal require constraints (four by specialising a template from
     * RequirementTemplates; SYS-5 inline, to keep its strict inequality). SYS-2,
     * SYS-6, and all FUN/CMP requirements are prose — SYS-6 is an objective with
     * deliberately no constraint, and the CMP leaves are single-effector
     * characterisation tests whose results BIND the parameters the SYS constraints
     * consume (noted per leaf).
     */

    private import ISQ::*;
    private import RequirementTemplates::*;
    private import WallRunDesign::*;

    // ===== Level 0 — Need ====================================================
    requirement def <'STK-1'> WallRunNeed {
        doc /* From a fixed ~1000 mm start squared to the wall, the rover shall
             * approach at the drive motors' maximum speed and come to a complete
             * stop without contact, minimising the residual gap. Source: task
             * statement. Compound; decomposed into SYS-1..7. */
        subject rover : WallRover;

        requirement : CommandMaxSpeed;
        requirement : TranslateAlongNormal;
        requirement : HoldHeading;
        requirement : StopBeforeWall;
        requirement : NoContact;
        requirement : MinimizeResidualGap;
        requirement : ClearanceMargin;
    }

    // ===== Level 1 — System (rover black-box) ================================

    // SYS-1 [state-driven · HARD CONSTRAINT] <- STK-1
    requirement def <'SYS-1'> CommandMaxSpeed specializes LowerBoundRequirement {
        doc /* While approaching, the rover shall command both drive motors at
             * maximum angular velocity. Speed may not be traded for margin.
             * commanded >= max forces commanded = max (max is the ceiling). */
        subject rover : WallRover;
        attribute :>> measured = rover.commandedMotorSpeed;
        attribute :>> target = rover.maxMotorSpeed;

        requirement : ReachMaxSpeed;
    }

    // SYS-2 [state-driven] <- STK-1
    requirement def <'SYS-2'> TranslateAlongNormal {
        doc /* While approaching, the rover shall translate along the start-line
             * normal toward the wall. */
        subject rover : WallRover;
        requirement : ForwardTranslation;
    }

    // SYS-3 [state-driven · DERIVED] <- STK-1
    requirement def <'SYS-3'> HoldHeading specializes UpperBoundRequirement {
        doc /* While approaching, the rover shall hold heading within thetaMax of
             * the normal. DERIVED: lateral drift changes effective closing distance
             * and risks glancing contact. Held OPEN-LOOP via matched-drive trim
             * (steering finding); headingDrift is the absolute drift magnitude,
             * verified from the IMU trace, not corrected at run time. */
        subject rover : WallRover;
        attribute :>> measured = rover.headingDrift;
        attribute :>> target = rover.thetaMax;

        requirement : MonitorHeading;
        requirement : EqualizeDrive;
    }

    // SYS-4 [event-driven] <- STK-1
    requirement def <'SYS-4'> StopBeforeWall specializes LowerBoundRequirement {
        doc /* When forward clearance reaches the braking threshold, the rover
             * shall decelerate to a complete stop. The invariant "clearance >=
             * threshold while at speed" is the collision-avoidance mechanism;
             * threshold instantiates StoppingDistance against the rover's bound
             * parameters. Verified by direct measurement of the stop distance at v_max (multi-cycle). */
        subject rover : WallRover;
        attribute :>> measured = rover.forwardClearance;
        attribute :>> target = rover.brakingThreshold;

        requirement : ControlledDeceleration;
        requirement : EstimateForwardClearance;
        requirement : EstimateDeceleration;
        requirement : TriggerStopAtThreshold;
    }

    // SYS-5 [unwanted · HARD CONSTRAINT] <- STK-1   (inline; strict inequality)
    requirement def <'SYS-5'> NoContact {
        doc /* The rover shall not contact the wall. Binary pass/fail; dominant
             * success criterion. Strict: final clearance must be positive. */
        subject rover : WallRover;
        attribute measured : LengthValue = rover.finalClearance;
        require constraint { measured > 0 }

        requirement : TriggerStopAtThreshold;
    }

    // SYS-6 [objective — "should"] <- STK-1   (deliberately no constraint)
    requirement def <'SYS-6'> MinimizeResidualGap {
        doc /* The rover should minimize the residual gap at final stop. OBJECTIVE,
             * not a shall-threshold: graded and traded against SYS-5. Carries no
             * require constraint — it is the optimisation target, verified by the
             * performance measure, not a pass/fail gate. */
        subject rover : WallRover;
    }

    // SYS-7 [ubiquitous · DERIVED · HARD CONSTRAINT] <- SYS-5/6
    requirement def <'SYS-7'> ClearanceMargin specializes LowerBoundRequirement {
        doc /* The rover shall stop with a clearance margin M sized to cover
             * (a) stopping-distance prediction uncertainty, (b) clearance-
             * measurement uncertainty, and (c) run-to-run variability. The
             * verifiable proxy for "as close as possible without contact"; the
             * operation tests that M covers the spread. M = rover.marginM, three TBDs:
             * sigmaDStop, sigmaDMeas, sigmaRun. */
        subject rover : WallRover;
        attribute :>> measured = rover.finalClearance;
        attribute :>> target = rover.marginM;

        requirement : EstimateForwardClearance;
        requirement : IndependentDistanceEstimate;
        requirement : CrossValidateDistance;
        requirement : HoldFinalClearance;
    }

    // ===== Level 2 — Function ================================================
    // Prose decomposition layer; each allocates downward to single-effector leaves.

    // Drive
    requirement def <'FUN-D1'> ForwardTranslation {
        doc /* Forward translation at commanded ground speed. <- SYS-2 */
        subject rover : WallRover;
        requirement : GroundDistancePerRev;
        requirement : DriveSignConvention;
    }
    requirement def <'FUN-D2'> ReachMaxSpeed {
        doc /* Reach maximum ground speed at maximum commanded angular velocity. <- SYS-1 */
        subject rover : WallRover;
        requirement : CharacterizeMaxAngularVelocity;
    }
    requirement def <'FUN-D3'> ControlledDeceleration {
        doc /* Controlled deceleration to zero on stop command. <- SYS-4 */
        subject rover : WallRover;
        requirement : DecelerationProfile;
    }

    // Guidance (open-loop — steering finding)
    requirement def <'FUN-G1'> MonitorHeading {
        doc /* Monitor heading vs the normal — verification, not feedback. <- SYS-3 */
        subject rover : WallRover;
        requirement : YawDrift;
    }
    requirement def <'FUN-G2'> EqualizeDrive {
        doc /* Equalise drive so open-loop heading drift stays <= thetaMax
             * (matched-drive trim, not a run-time controller). <- SYS-3, SYS-1 */
        subject rover : WallRover;
        requirement : CharacterizeMaxAngularVelocity;
        requirement : DriveSignConvention;
    }

    // Sensing
    requirement def <'FUN-S1'> EstimateForwardClearance {
        doc /* Estimate forward clearance. <- SYS-4, SYS-7 */
        subject rover : WallRover;
        requirement : ForwardRangeCharacterization;
        requirement : ClearanceFusion;
        requirement : ForwardRefreshLatency;
    }
    requirement def <'FUN-S2'> IndependentDistanceEstimate {
        doc /* Estimate distance travelled / speed independently of the drive
             * command. <- SYS-7 */
        subject rover : WallRover;
        requirement : RearRangeChannel;
    }
    requirement def <'FUN-S3'> EstimateDeceleration {
        doc /* Estimate deceleration during braking. <- SYS-4 */
        subject rover : WallRover;
        requirement : ForwardAccelCharacterization;
    }
    requirement def <'FUN-S4'> CrossValidateDistance {
        doc /* Cross-validate the distance estimate across independent channels;
             * flag and exclude any channel discrepant beyond tolerance. DERIVED,
             * fault-agnostic — the hardware-error detector. <- SYS-7 */
        subject rover : WallRover;
        requirement : ForwardRangeCharacterization;
        requirement : RearRangeChannel;
        requirement : GroundDistancePerRev;
    }

    // Stop-control
    requirement def <'FUN-C1'> TriggerStopAtThreshold {
        doc /* Command stop when estimated clearance hits the braking threshold.
             * <- SYS-4, SYS-5 */
        subject rover : WallRover;
        requirement : ForwardRefreshLatency;
    }
    requirement def <'FUN-C2'> HoldFinalClearance {
        doc /* Hold final clearance >= M. Integrative — verified by composition in
             * the integrated test, no single-effector leaf. <- SYS-7 */
        subject rover : WallRover;
    }

    // ===== Level 3 — Single-effector leaves (verification floor) =============
    // Each checkable by a test on one effector; method class in brackets. The
    // result of each test BINDS a model parameter named below.

    requirement def <'CMP-M1'> GroundDistancePerRev {
        doc /* Each drive motor shall hold a repeatable ground-distance-per-
             * revolution over the speed range used. [motor: commanded displacement
             * vs ground-truth distance] Binds driveConstant. */
        subject rover : WallRover;
    }
    requirement def <'CMP-M2'> CharacterizeMaxAngularVelocity {
        doc /* Each motor shall report achieved angular velocity; its maximum shall
             * be characterised (sets the matched straight-line max). [motor: command
             * max, read achieved] Binds maxMotorSpeed. */
        subject rover : WallRover;
    }
    requirement def <'CMP-M3'> DecelerationProfile {
        doc /* Each motor shall produce a repeatable stop from max speed; the stop
             * distance is measured DIRECTLY at v_max. [motor: stop from v_max,
             * measure stop distance, multi-cycle -> mean + run spread] Binds the
             * stop distance at v_max (which back-solves decelCollision) and
             * sigmaRun; sigmaDStop (SYS-7a) is the measurement SEM. Operating point
             * = calibration point, so no speed sweep is needed (zero extrapolation). */
        subject rover : WallRover;
    }
    requirement def <'CMP-M4'> DriveSignConvention {
        doc /* Forward drive-sign convention per motor. [motor: command +, observe
             * direction] Interface requirement. */
        subject rover : WallRover;
    }
    requirement def <'CMP-U1'> ForwardRangeCharacterization {
        doc /* Each forward ultrasonic shall report range with characterised
             * bias/scale over the approach range (~50–1000 mm), per sensor.
             * [ultrasonic vs ground truth] Binds dSenseMax and sigmaDMeas. */
        subject rover : WallRover;
    }
    requirement def <'CMP-U2'> ClearanceFusion {
        doc /* Forward clearance shall be defined as min(L,R) and validated.
             * [two-sensor fusion] Binds forwardClearance. */
        subject rover : WallRover;
    }
    requirement def <'CMP-U4'> ForwardRefreshLatency {
        doc /* Forward ultrasonic refresh interval / latency shall be characterised.
             * [ultrasonic: sample timing vs motion] Bounds distance per stale
             * reading at max speed. Binds tSensorDistance. */
        subject rover : WallRover;
    }
    requirement def <'CMP-U5'> RearRangeChannel {
        doc /* Rear ultrasonic shall report range-from-start with characterised
             * bias/scale (independent distance channel). [ultrasonic vs ground
             * truth] Feeds FUN-S2 / FUN-S4 cross-validation. */
        subject rover : WallRover;
    }
    requirement def <'CMP-I1'> YawDrift {
        doc /* The IMU shall report yaw with characterised drift over a run.
             * [IMU: known rotation / static-hold drift] Measures the achieved drift
             * checked against the thetaMax budget (SYS-3). */
        subject rover : WallRover;
    }
    requirement def <'CMP-I2'> ForwardAccelCharacterization {
        doc /* The IMU shall report forward-axis acceleration with characterised
             * bias/noise sufficient to corroborate deceleration. [IMU: known decel,
             * integrate, compare] Corroborates decelCollision (FUN-S4 channel). */
        subject rover : WallRover;
    }

    // ------------------------------------------------------------------------
    // Absence by traceability. Nothing in STK-1 traces to the downward
    // reflectance sensor (WallRover::floor). No CMP leaf subjects it, so the
    // FallStop step-detector relation and any NoFallOverEdge requirement are
    // never instantiated. The sensor sits in the structure, unused and visibly
    // so — dropped because no requirement reaches it, not deleted.
    // ------------------------------------------------------------------------
}
