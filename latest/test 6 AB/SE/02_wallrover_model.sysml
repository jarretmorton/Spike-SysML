// ============================================================================
// 02_wallrover_model.sysml  —  TAILORED task model for the wall-approach rover.
//
// Formal realisation of the requirements specification
// (01_requirements_and_effectors.md). The specification is the source of truth;
// on any disagreement the specification governs. This model does NOT restate the
// requirements' prose — it carries the evaluable roll-up: one WallRover design
// part whose calibrated attributes are related by the reproduced physics
// relations, claiming the top need via `satisfy`, with the requirement tree hung
// beneath it by nested `requirement :` usages. Evaluating that satisfy/require
// roll-up against calibrated values IS the pre-run verification artifact.
//
// TAILORING (Process step 3 — instantiate only what the requirements call for):
//   Relations instantiated (from RelationTemplates, expressions REPRODUCED against
//   bound attributes per the skeleton's validation note — not calc INVOCATION):
//     • RotationToSpeed   — cruise speed from motor ceiling (sources + cross-check).
//     • StoppingDistance  — the core stop model (trigger distance in ranger frame).
//   Relation DROPPED (absence by traceability):
//     • MaxSpeedFromBudget — speed is GIVEN as "maximum"; no requirement solves for
//       a speed from a budget, so this inverse relation is not instantiated.
//   Effectors USED: 2× DriveMotor, 2× forward DistanceSensor (cross-sourced), InertialUnit.
//   Effectors DROPPED (absence by traceability): rear DistanceSensor (no rearward
//     requirement), ReflectanceSensor `floor` (senses no task quantity) — neither is
//     allocated nor referenced by any requirement below.
//
// PACKAGING NOTE: the design part and the requirements live in ONE package so the
// subject type (WallRover) and the top need (WallRunNeed) are mutually visible with
// no cross-package import cycle — the safest resolution for the out-of-band grammar
// check. Only the standard library and the rover skeleton are imported.
//
// CONSTRUCT DISCIPLINE: restricted to forms validated in rover_generic.sysml —
//   specialise a template, add `subject`, bind operands with `attribute :>> measured
//   = subject.attr` (redefinition-with-binding, NOT `redefines … :>>`), inherit the
//   require constraint; decomposition via nested `requirement :` usages; relations as
//   asserted `constraint` bodies reproducing the catalog expressions; one top-level
//   `satisfy`. No calc invocation, no invented notation.
// ============================================================================

package WallApproach {

    private import ISQ::*;
    private import SI::*;
    private import ScalarValues::*;
    private import RoverCommon::*;
    private import RoverStructure::*;
    private import RequirementTemplates::*;   // LowerBoundRequirement, UpperBoundRequirement
    // RelationTemplates is the source of truth for the reproduced expressions
    // (RotationToSpeed, StoppingDistance); its expressions are reproduced below.

    // ------------------------------------------------------------------------
    // DESIGN PART — the tailored rover, its analysis attributes (uncalibrated,
    // not zeroed), the reproduced relations tying them together, and the claim.
    // ------------------------------------------------------------------------
    part def WallRover specializes Rover {
        doc /*
         * Tailored wall-approach rover. Attributes are the model-completion
         * parameters + requirement quantities; all UNCALIBRATED here and bound at
         * calibration (see 03_calibration_plan.md). Effector→attribute allocation:
         *   motors      → maxCmdSpeed, motorCeiling, cruiseSpeed (via kRot), decel, stopDistance
         *   forward rangers → rangerError (→ sigMeas), triggerDist input, finalClearance readout
         *   imu         → headingDrift (heading channel), forward-accel cross-source for cruise/stop
         *   latency     → tChain (platform-wide RoverLatency)
         */

        // ---- fixed platform allocation for this task ----
        part :>> motors  : DriveMotor [2];        // differential pair: propel, brake, differential-steer
        part :>> rangers : DistanceSensor [2];    // the two FORWARD rangers (rear ranger NOT allocated — absence by traceability)
        // imu inherited and USED. floor (ReflectanceSensor) inherited but NOT allocated
        // and referenced by no requirement below (absence by traceability).

        // ---- speed chain ----
        attribute maxCmdSpeed  : AngularVelocityValue;   // commanded angular speed (large ⇒ run() clamps to ceiling)
        attribute motorCeiling : AngularVelocityValue;   // achievable angular ceiling (read-back)
        attribute kRot         : LengthValue;            // RotationToSpeed constant, m per rad (bundles radius, gear, slip)
        attribute cruiseSpeed  : SpeedValue;             // achieved ground speed at max

        // ---- reaction latency ----
        attribute tChain    : DurationValue;   // on-hub latency (compute + command), platform-wide (RoverLatency)
        attribute tSample   : DurationValue;   // ranger refresh / staleness bound
        attribute tResponse : DurationValue;   // total reaction latency before braking begins

        // ---- braking / stop geometry ----
        attribute decel              : AccelerationValue; // calibrated deceleration (feasibility back-solve)
        attribute stopDistance       : LengthValue;       // D: displacement from trigger fire to full stop
        attribute stopDistanceBudget : LengthValue;       // D_budget: feasibility ceiling (stop must fit runway with clearance)
        attribute sensorOffset       : LengthValue;       // δ: ranger face → front-most point (operator ground truth)
        attribute contactMargin      : LengthValue;       // m: designed final gap (frozen in Verification Plan)
        attribute triggerDist        : LengthValue;       // s_trig: ranger reading at which stop is commanded
        attribute finalClearance     : LengthValue;       // g_final: true gap at full stop
        attribute runway             : LengthValue;       // available approach distance (~start distance)

        // ---- ranger accuracy ----
        attribute rangerError         : LengthValue;      // observed absolute ranger error at operating range
        attribute rangerAccuracyLimit : LengthValue;      // ε_acc: accept limit (must be ≪ contactMargin)

        // ---- heading ----
        attribute headingDrift      : Angle;              // observed yaw drift over the approach
        attribute headingDriftLimit : Angle;              // θ_max: drift limit (geometry-set)

        // ---- margin uncertainty budget (tenet A6, RSS) ----
        attribute sigPred        : LengthValue;   // stop-prediction σ
        attribute sigMeas        : LengthValue;   // clearance-measurement σ (= ranger accuracy)
        attribute sigRun         : LengthValue;   // run-to-run σ
        attribute kSafety        : Real;          // margin multiplier (set from no-contact assurance)
        attribute rssUncertainty : LengthValue;   // kSafety · RSS(σ)

        // ---- reproduced relations (RelationTemplates expressions vs bound attrs) ----
        // asserted analytical constraints; equality relations composing the model.
        assert constraint rotToSpeed { cruiseSpeed == motorCeiling * kRot }                       // RotationToSpeed: v = ω·k
        assert constraint reaction   { tResponse == tChain + tSample }                            // reaction latency chain
        assert constraint stopDist   { stopDistance == cruiseSpeed * tResponse
                                                       + cruiseSpeed ** 2 / (2 * decel) }         // StoppingDistance reaction+braking terms = D
        assert constraint stopModel  { triggerDist == stopDistance + sensorOffset + contactMargin } // D in ranger frame + margin ⇒ trigger reading
        assert constraint restClear  { finalClearance == triggerDist - stopDistance - sensorOffset } // g_final = s_trig − D − δ  (⇒ = contactMargin)
        assert constraint measLink   { sigMeas == rangerError }                                   // clearance-measurement σ is the ranger accuracy (CMP-1)
        assert constraint marginRss  { rssUncertainty == kSafety
                                        * (sigPred ** 2 + sigMeas ** 2 + sigRun ** 2) ** 0.5 }    // A6 root-sum-square

        // ---- the design claims the top need; the tree hangs beneath it ----
        satisfy requirement : WallRunNeed;
    }

    // ------------------------------------------------------------------------
    // REQUIREMENTS — realising 01_requirements_and_effectors.md §2. Each bound
    // requirement specialises a template, adds the WallRover subject, binds the
    // operands, and inherits the require constraint. Decomposition is nested
    // `requirement :` usages. Edge-set matches the Mermaid tree 1:1 (see checks).
    // ------------------------------------------------------------------------

    // STK-1 — stakeholder need (top). No single bound; carries the SYS children.
    requirement def <'STK-1'> WallRunNeed {
        subject rover : WallRover;
        doc /* Drive from the start line to the wall at maximum speed and stop as
             * close as possible without contact. Parent of all requirements. */
        requirement : ApproachAtMax;
        requirement : NoContact;
        requirement : MinimizeGap;
        requirement : DriveStraight;
        requirement : MarginFloor;
    }

    // SYS-1 — command motors at ≥ max achievable angular speed (hard, Event).
    requirement def <'SYS-1'> ApproachAtMax specializes LowerBoundRequirement {
        subject rover : WallRover;
        doc /* When executing the approach, the commanded angular speed is no less
             * than the motor ceiling (a large command clamps to the ceiling). */
        attribute :>> measured = rover.maxCmdSpeed;
        attribute :>> target   = rover.motorCeiling;
        requirement : MotorReachesCeiling;
    }

    // CMP-3 — single-motor effector reaches its ceiling. Same clamp relation as
    // SYS-1 but at the effector level: calibration binds motorCeiling (read-back)
    // and cruiseSpeed (via rotToSpeed) here. Leaf.
    requirement def <'CMP-3'> MotorReachesCeiling specializes LowerBoundRequirement {
        subject rover : WallRover;
        doc /* When commanded above its ceiling, the drive motor's commanded speed
             * reaches the achievable ceiling (read-back binds motorCeiling; cruiseSpeed
             * follows via RotationToSpeed). Single-effector leaf. */
        attribute :>> measured = rover.maxCmdSpeed;
        attribute :>> target   = rover.motorCeiling;
    }

    // SYS-2 — no contact with the wall (hard, Unwanted, integrative). The
    // clearance-vs-margin claim; realised integratively by STP-1.
    requirement def <'SYS-2'> NoContact specializes LowerBoundRequirement {
        subject rover : WallRover;
        doc /* The rover shall not make contact: final clearance ≥ contact margin. */
        attribute :>> measured = rover.finalClearance;   // true gap at full stop
        attribute :>> target   = rover.contactMargin;    // 0 + verified no-contact margin
        requirement : SenseWallRange;
        requirement : BrakeToStop;
        requirement : StopWithinClearance;
    }

    // FUN-1 — measure forward range (function). Trigger input.
    requirement def <'FUN-1'> SenseWallRange {
        subject rover : WallRover;
        doc /* Continuously measure the forward wall range during the approach. */
        requirement : RangerAccuracy;
    }

    // CMP-1 — ranger accuracy (single effector). Error bounded by ε_acc.
    requirement def <'CMP-1'> RangerAccuracy specializes UpperBoundRequirement {
        subject rover : WallRover;
        doc /* The forward distance sensor reports wall range with absolute error
             * ≤ ε_acc over the operating range. Its error is the clearance-measurement
             * σ feeding the margin (measLink: sigMeas == rangerError). */
        attribute :>> measured = rover.rangerError;
        attribute :>> target   = rover.rangerAccuracyLimit;
    }

    // FUN-3 — command stop at the trigger (function).
    requirement def <'FUN-3'> BrakeToStop {
        subject rover : WallRover;
        doc /* When the measured forward range reaches the trigger distance, command
             * all drive motors to stop. */
        requirement : BrakeWithin;
    }

    // CMP-4 — stop within the stopping-distance budget (single effector; feasibility).
    requirement def <'CMP-4'> BrakeWithin specializes UpperBoundRequirement {
        subject rover : WallRover;
        doc /* When commanded to stop from cruise, halt within stopping distance
             * D ≤ D_budget (D_budget set so the stop fits the runway with clearance). */
        attribute :>> measured = rover.stopDistance;
        attribute :>> target   = rover.stopDistanceBudget;
    }

    // STP-1 — integrative leaf that closes SYS-2. Irreducibly integrative (ranger +
    // motor + latency + heading together); decomposition stops here (Rule 2).
    // Verified by the integrated verification run.
    requirement def <'STP-1'> StopWithinClearance specializes LowerBoundRequirement {
        subject rover : WallRover;
        doc /* When the forward range reaches the trigger distance, come to a full
             * stop with final clearance ≥ contact margin. Integrative — closes SYS-2. */
        attribute :>> measured = rover.finalClearance;
        attribute :>> target   = rover.contactMargin;
    }

    // SYS-3 — minimize the final gap (objective, graded — no pass/fail constraint).
    requirement def <'SYS-3'> MinimizeGap {
        subject rover : WallRover;
        doc /* OBJECTIVE (graded, not pass/fail): minimize rover.finalClearance.
             * Bridged to the hard constraints by MarginFloor (MRG-1). Verified by the
             * measured gap in operation; carries no require constraint by design. */
    }

    // SYS-4 — hold heading within ±θ_max (derived from SYS-2/SYS-3; State-driven).
    requirement def <'SYS-4'> DriveStraight specializes UpperBoundRequirement {
        subject rover : WallRover;
        doc /* DERIVED: while approaching, keep heading drift within θ_max so the
             * ranger stays normal to the wall (range = true perpendicular gap) and the
             * front-most point is the first to reach the wall. */
        attribute :>> measured = rover.headingDrift;
        attribute :>> target   = rover.headingDriftLimit;
        requirement : HoldHeading;
    }

    // FUN-4 — balance motors to hold heading (function).
    requirement def <'FUN-4'> HoldHeading {
        subject rover : WallRover;
        doc /* While approaching, balance the drive motors to hold heading. */
        requirement : ImuDriftBound;
    }

    // CMP-5 — IMU yaw drift bounded (single effector). Straightness channel.
    requirement def <'CMP-5'> ImuDriftBound specializes UpperBoundRequirement {
        subject rover : WallRover;
        doc /* The inertial unit estimates yaw with drift ≤ θ_max over the approach
             * duration (cross-checked against differential encoders). */
        attribute :>> measured = rover.headingDrift;
        attribute :>> target   = rover.headingDriftLimit;
    }

    // MRG-1 — derived margin floor (Rule 3 bridge; tenet A6). Sizes the margin to
    // exactly the calibrated uncertainty envelope.
    requirement def <'MRG-1'> MarginFloor specializes LowerBoundRequirement {
        subject rover : WallRover;
        doc /* DERIVED (A6): contact margin ≥ kSafety·RSS(σ_pred, σ_meas, σ_run).
             * rssUncertainty is defined by the marginRss relation on WallRover. */
        attribute :>> measured = rover.contactMargin;
        attribute :>> target   = rover.rssUncertainty;
    }

    // ========================================================================
    // STRUCTURAL CHECKS  (grammar is verified out-of-band; these run as the gate)
    // ========================================================================
    // (1) REACHABILITY — every requirement reachable from WallRunNeed:
    //       WallRunNeed → ApproachAtMax → MotorReachesCeiling
    //                   → NoContact     → {SenseWallRange → RangerAccuracy,
    //                                      BrakeToStop    → BrakeWithin,
    //                                      StopWithinClearance}
    //                   → MinimizeGap
    //                   → DriveStraight → HoldHeading → ImuDriftBound
    //                   → MarginFloor
    //     14 requirement defs, all reachable, no orphans. WallRover satisfies WallRunNeed.
    //
    // (2) EDGE-SET vs the Mermaid tree in 01_requirements_and_effectors.md §5 (1:1):
    //       STK-1→SYS-1 ; STK-1→SYS-2 ; STK-1→SYS-3 ; STK-1→SYS-4 ; STK-1→MRG-1
    //       SYS-1→CMP-3
    //       SYS-2→FUN-1 ; SYS-2→FUN-3 ; SYS-2→STP-1
    //       FUN-1→CMP-1 ; FUN-3→CMP-4
    //       SYS-4→FUN-4 ; FUN-4→CMP-5
    //     Every nested `requirement :` usage above corresponds to exactly one tree
    //     edge and vice-versa. No extra edges, none missing.
    //
    // (3) IMPORT RESOLUTION (single package ⇒ no cross-package cycle):
    //       WallApproach imports ISQ, SI, ScalarValues (std library) and RoverCommon,
    //       RoverStructure, RequirementTemplates (skeleton). All external names used —
    //       Rover, DriveMotor, DistanceSensor, InertialUnit, ReflectanceSensor, Angle,
    //       LowerBoundRequirement, UpperBoundRequirement, and the ISQ/SI value types —
    //       resolve to those imports. WallRover and WallRunNeed are same-package, so the
    //       subject bindings and the `satisfy` resolve without qualification. No cycle.
    //
    // (4) EFFECTOR CLOSURE (mirrors 01 §4):
    //       USED  : motors→{CMP-3, CMP-4, FUN-4/CMP-5 via differential}, forward rangers→
    //               {CMP-1, STP-1}, imu→{CMP-5, cross-source CMP-3/CMP-4}. Each USED
    //               effector traces to ≥1 CMP.
    //       DROPPED: rear DistanceSensor, ReflectanceSensor floor — allocated to nothing,
    //               referenced by no requirement (absence by traceability).
    //
    // (5) BOUND-OPERAND CHECK — every specialised requirement binds BOTH operands to a
    //     WallRover attribute (no unbound/comment operands): SYS-1, CMP-3, SYS-2, CMP-1,
    //     CMP-4, STP-1, SYS-4, CMP-5, MRG-1 ✓.  Bare (no bound, by design): WallRunNeed,
    //     SenseWallRange, BrakeToStop, HoldHeading (structural/function nodes) and
    //     MinimizeGap (graded objective, intentionally constraint-free).
    // ========================================================================
}
