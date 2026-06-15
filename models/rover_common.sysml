// Status: drafted, not yet validated via sysml_validate.
// Confirm ISQ/SI value-type names and the sqrt import against the installed
// standard-library version before loading into the API server.

package RoverCommon {
    doc /*
     * Shared definitions for the Spike rover unit models, plus the ONE
     * genuinely platform-wide calibrated dynamic parameter (the latency chain).
     *
     * Deliberately NOT here:
     *   - deceleration (a): differs by hazard, because the stop maneuvers
     *     differ by hazard. Lives per-model as decelCollision / decelFall.
     *   - sensor-sampling latency: differs by sensor. Lives per-model as
     *     tSensorDistance / tSensorColor.
     */

    import ISQ::*;
    import SI::*;
    import ScalarValues::*;

    // --- Value types -------------------------------------------------------

    // LEGO color/reflectance sensor reports 0..100 (dimensionless percent).
    attribute def Reflectance :> Real;

    // --- Shared calibrated parameter --------------------------------------

    // The latency common to every stop decision: compute + BLE +
    // actuation-command issue. This is the lag BEFORE braking begins, so it is
    // independent of which maneuver is then commanded (the maneuver lands in a,
    // not here). Measured hub-side (BLE arrival times are not trustworthy, per
    // the wire contract). Calibrated ONCE and reused by both stop models.
    attribute def RoverLatency {
        attribute tChain : DurationValue;   // UNCALIBRATED — seconds; measure hub-side
    }
}
