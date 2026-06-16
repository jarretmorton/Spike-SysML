// Status: drafted, not yet validated via sysml_validate.

package MotorToRoverSpeed {
    doc /*
     * Unit model 1 — CHARACTERIZATION (not a safety requirement).
     *
     * Parametric edge: commanded motor angular velocity -> rover ground speed.
     * The constant bundles wheel radius, gear ratio, AND slip — which is exactly
     * why it is calibrated rather than computed: drive a known command, read the
     * actual distance off the gyro/clock, and back out the real constant. The
     * theoretical (geometry-only) value will not match because of slip; that gap
     * is the reason the measurement exists.
     *
     * This model has no requirement wrapper. It is the parametric edge that
     * Models 2 and 3 consume (they take rover speed v as an input), not a
     * safety claim in its own right.
     */

    private import ISQ::*;
    private import SI::*;

    // Calibrated: metres of ground travel per radian of wheel rotation.
    // (Radian is dimensionless in SI, so this carries length units.)
    attribute driveConstant : LengthValue;   // UNCALIBRATED — m per rad

    calc def RoverSpeed {
        in motorSpeed : AngularVelocityValue;   // commanded, rad/s
        in k : LengthValue;                      // driveConstant (m per rad)
        return roverSpeed : SpeedValue = motorSpeed * k;
    }
}
