// ============================================================================
// rover_generic.sysml — the GENERIC starting point handed to the SE arm.
//
// The SPIKE Prime rover platform's structure, plus reusable relation and
// requirement templates, free of any task facts. Nothing here names a wall, a
// start distance, or which sensors get used; what gets USED is decided
// downstream by which requirements trace to it.
//
// VALIDATION NOTE. Constructs are restricted to forms validated clean against
// the OMG SysML v2 Beta-4 spec examples. Relation
// templates are kept as calc defs (the validated form). The populated model
// instantiates a relation by REPRODUCING its expression against bound parameters
// rather than by calc INVOCATION, which is not yet in this repo's proven-valid
// set; the calc defs here are the single source of truth for those expressions.
// ============================================================================

package RoverCommon {
    doc /*
     * Shared value types and the one genuinely platform-wide calibrated dynamic
     * parameter (the latency chain).
     */

    private import ISQ::*;
    private import SI::*;
    private import ScalarValues::*;

    // LEGO color/reflectance sensor reports 0..100 (dimensionless percent).
    attribute def Reflectance :> Real;

    // Plane angle carried as a dimensionless real (radians). Avoids depending on
    // an ISQ angle value-type name; sufficient for heading-drift bookkeeping.
    attribute def Angle :> Real;

    // Latency common to every stop decision: compute + BLE + actuation-command
    // issue. The lag BEFORE braking begins, so it is independent of which
    // maneuver is then commanded (the maneuver lands in the deceleration term,
    // not here). Measured hub-side. Calibrated ONCE, reused by every stop model.
    attribute def RoverLatency {
        attribute tChain : DurationValue;   // UNCALIBRATED — s; measure hub-side
    }
}

package RoverStructure {
    doc /*
     * The bare component skeleton: the rover's effectors and sensors as blocks,
     * with their commandable/measurable attributes and NO relations between them.
     * Every sensor the platform carries is here, including ones a given task may
     * never use — disuse then shows up as "no requirement traces to it" (absence
     * by traceability), not as a missing block. Both arms are handed this; only
     * the SE arm is required to develop it.
     */

    private import ISQ::*;
    private import SI::*;
    private import RoverCommon::*;

    part def DriveMotor {
        attribute commandedSpeed : AngularVelocityValue;   // rad/s, commanded
        attribute maxSpeed       : AngularVelocityValue;   // rad/s, achievable ceiling
    }

    part def DistanceSensor {
        attribute range           : LengthValue;     // reported range
        attribute refreshInterval : DurationValue;   // sample period / staleness bound
    }

    part def InertialUnit {
        attribute yaw          : Angle;               // heading estimate
        attribute forwardAccel : AccelerationValue;   // forward-axis acceleration
    }

    part def ReflectanceSensor {
        attribute reflectance : Reflectance;          // downward reflectance, 0..100
    }

    // The platform: the parts that exist. Multiplicities are left open; a task
    // model specialises this and fixes how many of each and how they are arranged.
    part def Rover {
        part motors  : DriveMotor [*];
        part rangers : DistanceSensor [*];
        part imu     : InertialUnit;
        part floor   : ReflectanceSensor;             // present on the platform
        attribute latency : RoverLatency;             // calibrated once, platform-wide
    }
}

package RelationTemplates {
    doc /*
     * The generic physics-relation catalog: engineering knowledge with free
     * parameters, not facts about any one rover. A task model selects the 
     * relations its requirements call for and binds their parameters at
     * calibration. (Mechanically, the populated model reproduces a relation's
     * expression against bound parameters; calc INVOCATION is the intended
     * alternative once confirmed valid in Syside.)
     */

    private import ISQ::*;
    private import SI::*;

    // Rotational drive -> ground speed. The constant bundles wheel radius, gear
    // ratio AND slip, which is exactly why it is calibrated, not computed.
    calc def RotationToSpeed {
        in motorSpeed : AngularVelocityValue;   // rad/s
        in k : LengthValue;                     // m per rad
        return v : SpeedValue = motorSpeed * k;
    }

    // Distance at which a stop must already be triggered: reaction + braking +
    // human margin. Quadratic in v, so the deceleration's calibration tracks the
    // speed envelope the requirements exercise. At a SINGLE operating point,
    // measure the stopping distance directly at that point (calibration point =
    // operating point => zero extrapolation) and back-solve `a` only if a
    // feasibility check needs it. Across a RANGE of speeds, sweep and inspect the
    // fit residuals for curvature (a single-speed fit would fold the quadratic
    // into the linear term and be quietly wrong at the envelope edge).
    calc def StoppingDistance {
        in v : SpeedValue;
        in tResponse : DurationValue;   // latency.tChain + sensor sampling latency
        in a : AccelerationValue;       // calibrated deceleration
        in margin : LengthValue;        // human-set / verified safety margin
        return d : LengthValue =
            v * tResponse + v ** 2 / (2 * a) + margin;
    }

    // Inverse of StoppingDistance: the largest v whose stop fits inside a distance
    // BUDGET (a sensor range, or a geometric offset). Positive root, real while
    // budget > margin.
    calc def MaxSpeedFromBudget {
        in tResponse : DurationValue;
        in a : AccelerationValue;
        in budget : LengthValue;        // sensor range or geometric offset
        in margin : LengthValue;
        return vMax : SpeedValue =
            - a * tResponse
            + ( a ** 2 * tResponse ** 2 + 2 * a * (budget - margin) ) ** 0.5;
    }
}

package RequirementTemplates {
    doc /*
     * Generic requirement SHAPES, parameterised and subject-free, in the Beta-4
     * template idiom (untyped attribute parameters + an inherited require
     * constraint). A task requirement specialises one of these, adds a subject,
     * and redefines the operands (:>>) against that subject's attributes. The
     * constraint is inherited, so the evaluable logic lives in exactly one place.
     */

    // measured >= target. Serves clearance-vs-threshold, margin floors, and
    // command-at-maximum.
    requirement def LowerBoundRequirement {
        doc /* {measured} shall be no less than {target}. */
        attribute measured;
        attribute target;
        require constraint { measured >= target }
    }

    // measured <= target. Serves bounded heading drift and speed clamps.
    requirement def UpperBoundRequirement {
        doc /* {measured} shall not exceed {target}. */
        attribute measured;
        attribute target;
        require constraint { measured <= target }
    }
}
