// Status: drafted, not yet validated via sysml_validate.
// Operator note: exponentiation written as ** ; sqrt assumed available from the
// standard math library — confirm the import against the installed version.

package FallStop {
    doc /*
     * Unit model 3 — fall (edge/cliff) avoidance (SAFETY REQUIREMENT).
     *
     * The downward reflectance sensor is treated as a STEP detector, not a
     * graded range proxy: the trip level is a FIXED, calibrated reflectance
     * value, independent of speed. Speed enters only as a MAXIMUM SAFE SPEED
     * set by geometry.
     *
     * Geometry: the sensor sits a fixed offset ahead of the stopping reference
     * (wheel contact). When the edge trips the detector, the rover has at most
     * `sensorOffset` of surface left and must stop within it:
     *
     *     sensorOffset >= v*t_response + v**2/(2a) + margin
     *
     * The calibration activity sets vMax = the largest v satisfying this with
     * equality (closed form below); the controller clamps commanded speed to it.
     *
     * Maneuver note: the fall stop maneuver (e.g. slam-reverse) differs from the
     * collision maneuver, so decelFall is its own calibrated parameter.
     */

    import ISQ::*;
    import SI::*;
    import RoverCommon::*;

    // --- Calibrated / human-set parameters (all UNCALIBRATED) --------------

    attribute surfaceReflectance : Reflectance;   // UNCALIBRATED — R on solid floor
    attribute voidReflectance    : Reflectance;   // UNCALIBRATED — R over the void

    // Fixed detection level, biased toward an early trip: set above
    // voidReflectance by a noise band. Trip the fall maneuver when measured
    // reflectance falls to or below this. Speed-independent.
    attribute detectThreshold    : Reflectance;   // CALIBRATED from the two levels + noise

    // Fixed geometry: sensor spot to stopping reference (wheel contact).
    attribute sensorOffset : LengthValue;         // MEASURED — m

    // Maneuver-specific deceleration for the fall stop maneuver.
    attribute decelFall : AccelerationValue;      // UNCALIBRATED — m/s**2

    // Sampling latency of the color/reflectance sensor only; added to tChain.
    attribute tSensorColor : DurationValue;       // UNCALIBRATED — s

    // Human-set safety margin for the edge case.
    attribute marginFall : LengthValue;           // SET BY HUMAN — m

    // --- Relations ---------------------------------------------------------

    // Fixed, speed-independent edge detection.
    constraint def EdgeDetected {
        in measuredReflectance : Reflectance;
        in threshold : Reflectance;        // detectThreshold
        measuredReflectance <= threshold
    }

    // Maximum safe speed: positive root of
    //   sensorOffset = v*tResponse + v**2/(2a) + margin
    // Real and positive while sensorOffset > margin.
    calc def MaxSafeSpeed {
        in tResponse : DurationValue;      // = RoverLatency::tChain + tSensorColor
        in a : AccelerationValue;          // decelFall
        in offset : LengthValue;           // sensorOffset
        in margin : LengthValue;           // marginFall
        return vMax : SpeedValue =
            - a * tResponse
            + sqrt( a ** 2 * tResponse ** 2 + 2 * a * (offset - margin) );
    }

    // Commanded speed must not exceed the geometry-limited maximum.
    constraint def FallSafeSpeed {
        in v : SpeedValue;
        in vMax : SpeedValue;              // from MaxSafeSpeed
        v <= vMax
    }

    requirement def < 'R-FALL-1' > NoFallOverEdge {
        doc /* The rover shall (a) trigger the fall stop maneuver when downward
             * reflectance drops to the calibrated detection threshold, and
             * (b) operate at or below the maximum safe speed set by the fixed
             * sensor offset and the calibrated fall-stop dynamics. Calibration
             * sets vMax. Verified by an edge-trip test at, and just above, vMax. */
        subject rover;
        require constraint EdgeDetected;
        require constraint FallSafeSpeed;
    }
}
