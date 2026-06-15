// Status: drafted, not yet validated via sysml_validate.
// Operator note: exponentiation written as ** ; confirm against grammar.

package CollisionStop {
    doc /*
     * Unit model 2 — forward collision avoidance (SAFETY REQUIREMENT).
     *
     * Stop trigger:  d_measured <= v*t_response + v**2/(2a) + margin
     *   - v*t_response       reaction distance, travelled during the
     *                        sense->decide->actuate lag (linear in v)
     *   - v**2/(2a)          braking distance, travelled after deceleration
     *                        begins (quadratic in v; a is calibrated)
     *   - margin             human-set safety margin
     *
     * The quadratic term overtakes the linear one as speed climbs, so a is
     * calibrated by a SPEED SWEEP with inspection of fit-residual curvature —
     * a single-speed fit folds the quadratic into the linear constant and is
     * quietly wrong at the envelope edges.
     */

    import ISQ::*;
    import SI::*;
    import RoverCommon::*;

    // --- Calibrated / human-set parameters (all UNCALIBRATED) --------------

    // Maneuver-specific deceleration for the collision stop maneuver (the
    // collision maneuver differs from the fall maneuver by design).
    attribute decelCollision : AccelerationValue;   // UNCALIBRATED — m/s**2; speed-sweep calibrate, check residual curvature

    // Sampling latency of the forward distance sensor only; added to tChain.
    attribute tSensorDistance : DurationValue;       // UNCALIBRATED — s

    // Human-set safety margin for the collision case.
    attribute marginCollision : LengthValue;         // SET BY HUMAN — m

    // --- Relations ---------------------------------------------------------

    // Speed-dependent distance at which the stop maneuver must already trigger.
    calc def ForwardStopThreshold {
        in v : SpeedValue;
        in tResponse : DurationValue;      // = RoverLatency::tChain + tSensorDistance
        in a : AccelerationValue;          // decelCollision
        in margin : LengthValue;           // marginCollision
        return threshold : LengthValue =
            v * tResponse + v ** 2 / (2 * a) + margin;
    }

    // Safe while measured clearance is at least the threshold.
    constraint def SafeForwardClearance {
        in measuredDistance : LengthValue;
        in threshold : LengthValue;        // from ForwardStopThreshold
        measuredDistance >= threshold
    }

    requirement def < 'R-COL-1' > NoForwardCollision {
        doc /* The rover shall maintain forward clearance no less than the
             * speed-dependent stop threshold; on reaching it, the collision
             * stop maneuver is triggered. Verified by a braking-distance test
             * across a speed sweep. */
        subject rover;
        require constraint SafeForwardClearance;
    }
}
