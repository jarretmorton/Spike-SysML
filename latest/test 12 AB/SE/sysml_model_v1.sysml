/**
 * WALL-STOP SYSTEM — Tailored SysML v2 Model
 * Version: 1.0  Status: BASELINE  Date: 2026-07-21
 *
 * Authoring note: rover_generic.sysml was listed as the template source but
 * was not recoverable from the upload.  The base templates (RoverStructure,
 * RelationTemplates, RequirementTemplates) are re-declared inline below
 * following the canonical shapes given in the process instructions and the
 * OMG SysML v2 spec.  Template declarations marked [from rover_generic.sysml].
 * Once the file is available the inline declarations below should be replaced
 * with imports.
 *
 * Verification note: No grammar checker runs in-loop.  Structural checks
 * (reachability from top need; realised decomposition edge-set; per-package
 * import resolution) are performed as the gate check, out-of-band.
 */

// ============================================================
// PACKAGE 1 — TEMPLATE CATALOG  [from rover_generic.sysml]
// ============================================================
package RequirementTemplates {

    /** Generic lower-bound requirement: measured >= target */
    requirement def LowerBoundRequirement {
        attribute measured;
        attribute target;
        require constraint { measured >= target }
    }

    /** Generic upper-bound requirement: measured <= target */
    requirement def UpperBoundRequirement {
        attribute measured;
        attribute target;
        require constraint { measured <= target }
    }

    /** Generic equality requirement: measured == target (within tolerance) */
    requirement def EqualityRequirement {
        attribute measured;
        attribute target;
        attribute tolerance;
        require constraint { (measured - target) <= tolerance
                          && (target - measured) <= tolerance }
    }

    /** Range requirement: lo <= measured <= hi */
    requirement def RangeRequirement {
        attribute measured;
        attribute lo;
        attribute hi;
        require constraint { measured >= lo && measured <= hi }
    }
}

// ============================================================
// PACKAGE 2 — ROVER STRUCTURE  [from rover_generic.sysml]
// ============================================================
package RoverStructure {

    part def SpikeHub;
    part def DriveMotor;
    part def UltrasonicSensor;
    part def IMU;
    part def ColorSensor;

    part def Rover {
        part hub        : SpikeHub;
        part motorA     : DriveMotor;
        part motorB     : DriveMotor;
        part ussForward1 : UltrasonicSensor;
        part ussForward2 : UltrasonicSensor;
        part ussRear    : UltrasonicSensor;
        part colorSensor : ColorSensor;
        part imu        : IMU;   // built into SpikeHub; modelled separately for clarity
    }
}

// ============================================================
// PACKAGE 3 — WALL-STOP SYSTEM MODEL
// ============================================================
package WallStopSystem {

    // -----------------------------------------------------------
    // 3.1  Part Definition — WallRover
    // Extends the generic Rover with wall-stop specific quantities.
    // Parameters left free (None / 0.0) until calibration binds them.
    // -----------------------------------------------------------
    part def WallRover specializes RoverStructure::Rover {

        // === Performance quantities (bound by calibration) ===
        attribute finalClearance_mm   : Real;    // front-face to wall at full stop [TBD_OBJ]
        attribute contactMargin_mm    : Real = 0.0;  // hard lower bound on finalClearance

        // === Drive parameters ===
        attribute vMaxRated_dps       : Real;    // max motor shaft speed [TBD_VMOT]
        attribute vMaxRover_mms       : Real;    // max rover translation speed [TBD_VMAX_MMS]

        // === Stopping model ===
        attribute dStop_mm            : Real;    // stopping distance at v_max [TBD_DSTOP]
        attribute loopPeriod_ms       : Real;    // control loop period [TBD_LOOP]
        attribute dReaction_mm        : Real;    // = vMaxRover_mms * loopPeriod_ms / 1000 [TBD_DREACT]

        // === Sensor model ===
        attribute dCombo_mm           : Real;    // d_front_offset + uss_bias [TBD_COMBO]
        attribute ussValidMin_mm      : Real;    // minimum valid USS reading [TBD_USS_MIN]
        attribute ussAgreement_mm     : Real;    // F1 vs F2 max disagreement [TBD_USS_AGREE]

        // === Trigger ===
        attribute dTrigger_mm         : Real;    // USS reading at brake trigger [TBD_TRIGGER]
                                                 // design eqn: dStop + dReaction + dCombo + margin

        // === Heading ===
        attribute headingTol_deg      : Real;    // max heading deviation [TBD_HDG]
        attribute imuDrift_dps_s      : Real;    // IMU drift rate [TBD_HDG_DRIFT]

        // === Derived relation (inline assertion) ===
        // dTrigger must be set so that finalClearance >= contactMargin
        assert constraint dTriggerSufficiency {
            dTrigger_mm >= dStop_mm + dReaction_mm + dCombo_mm + contactMargin_mm
        }
    }

    // -----------------------------------------------------------
    // 3.2  STK Requirements
    // -----------------------------------------------------------
    package STK {

        requirement def <'STK-1'> NoWallContact specializes
                RequirementTemplates::LowerBoundRequirement {
            subject rover : WallRover;
            attribute :>> measured = rover.finalClearance_mm;
            attribute :>> target   = rover.contactMargin_mm;      // 0 mm
            doc /* The rover shall not make contact with the wall at any point
                   during or after the run. */
        }

        requirement def <'STK-3'> MaxSpeed {
            subject rover : WallRover;
            attribute measured_dps : Real;           // actual commanded speed
            attribute :>> measured = measured_dps;
            attribute target_dps   : Real;
            attribute :>> target   = rover.vMaxRated_dps;
            require constraint { measured_dps >= target_dps }
            doc /* The rover shall operate at maximum available motor speed
                   during the approach phase. */
        }

        requirement def <'STK-4'> CompleteStop {
            subject rover : WallRover;
            doc /* When the rover reaches zero velocity after braking,
                   the rover shall remain stationary. Verified by programme
                   inspection (brake command, no subsequent run command). */
        }
    }

    // -----------------------------------------------------------
    // 3.3  SYS Requirements
    // -----------------------------------------------------------
    package SYS {

        /** SYS-1 — Clearance ≥ 0 mm at all times.  Inherits constraint from LowerBound. */
        requirement def <'SYS-1'> MinimumClearance specializes
                RequirementTemplates::LowerBoundRequirement {
            subject rover : WallRover;
            attribute :>> measured = rover.finalClearance_mm;
            attribute :>> target   = rover.contactMargin_mm;
        }

        /** SYS-2 — Minimise final gap (objective; not a pass/fail). */
        requirement def <'SYS-2'> MinimiseGap {
            subject rover : WallRover;
            attribute measuredGap_mm : Real;
            doc /* Objective: minimise measuredGap_mm subject to SYS-1.
                   Graded; no pass/fail threshold.  Scored externally. */
        }

        /** SYS-3 — Max speed start → trigger. */
        requirement def <'SYS-3'> MaxSpeedApproach specializes
                RequirementTemplates::LowerBoundRequirement {
            subject rover : WallRover;
            attribute :>> measured = rover.vMaxRover_mms;   // commanded speed
            attribute :>> target   = rover.vMaxRated_dps;   // (normalised units TBD)
            doc /* The rover shall command maximum rated motor speed from
                   first motion until the braking trigger fires. */
        }

        /** SYS-4 — No resume after stop. */
        requirement def <'SYS-4'> NoResume {
            subject rover : WallRover;
            doc /* When the rover has stopped, it shall not resume motion.
                   Verified by programme inspection: no run() after brake(). */
        }

        /** SYS-5 (Derived) — Heading within ± headingTol. */
        requirement def <'SYS-5'> HeadingBound specializes
                RequirementTemplates::UpperBoundRequirement {
            subject rover : WallRover;
            attribute headingDeviation_deg : Real;   // absolute value of heading reading
            attribute :>> measured = headingDeviation_deg;
            attribute :>> target   = rover.headingTol_deg;
            doc /* Derived.  The rover shall maintain heading within
                   ± headingTol_deg throughout the run. */
        }
    }

    // -----------------------------------------------------------
    // 3.4  FUN Requirements
    // -----------------------------------------------------------
    package FUN {

        requirement def <'FUN-1'> BothMotorsMaxSpeed {
            subject rover : WallRover;
            requirement <'CMP-1'> motorASpeed : SYS::MaxSpeedApproach;
            requirement <'CMP-2'> motorBSpeed : SYS::MaxSpeedApproach;
            doc /* While in approach phase, propulsion shall command both
                   drive motors at maximum rated speed. */
        }

        requirement def <'FUN-2'> ContinuousForwardDistance {
            subject rover : WallRover;
            requirement <'CMP-3'> ussF1Valid;
            requirement <'CMP-4'> ussF2Valid;
            doc /* The forward sensing function shall continuously report
                   wall distance throughout the approach. */
        }

        requirement def <'FUN-3'> BrakingTrigger {
            subject rover : WallRover;
            requirement <'CMP-5'> stopWithinDistance;
            doc /* When USS-F1 reading <= dTrigger_mm, issue brake commands
                   within one loop period and travel <= dStop + dReaction. */
        }

        requirement def <'FUN-4'> HeadingHold {
            subject rover : WallRover;
            requirement <'CMP-6'> imuDriftBound;
            doc /* The heading-hold function shall maintain IMU heading
                   within ± headingTol_deg of 0 using differential motor speed. */
        }
    }

    // -----------------------------------------------------------
    // 3.5  CMP Requirements (leaf level)
    // -----------------------------------------------------------
    package CMP {

        requirement def <'CMP-1'> MotorASpeed specializes
                RequirementTemplates::LowerBoundRequirement {
            subject rover : WallRover;
            attribute motorAActual_dps : Real;
            attribute :>> measured = motorAActual_dps;
            attribute :>> target   = rover.vMaxRated_dps;
        }

        requirement def <'CMP-2'> MotorBSpeed specializes
                RequirementTemplates::LowerBoundRequirement {
            subject rover : WallRover;
            attribute motorBActual_dps : Real;
            attribute :>> measured = motorBActual_dps;
            attribute :>> target   = rover.vMaxRated_dps;
        }

        requirement def <'CMP-3'> USSF1ValidReading specializes
                RequirementTemplates::RangeRequirement {
            subject rover : WallRover;
            attribute ussF1Reading_mm : Real;
            attribute :>> measured = ussF1Reading_mm;
            attribute :>> lo       = rover.ussValidMin_mm;
            attribute :>> hi       = 2000.0;
        }

        requirement def <'CMP-4'> USSF2Agreement specializes
                RequirementTemplates::UpperBoundRequirement {
            subject rover : WallRover;
            attribute f1Reading : Real;
            attribute f2Reading : Real;
            attribute disagreement : Real;
            attribute :>> measured = disagreement;   // |F1 - F2|
            attribute :>> target   = rover.ussAgreement_mm;
        }

        requirement def <'CMP-5'> StoppingDistance specializes
                RequirementTemplates::UpperBoundRequirement {
            subject rover : WallRover;
            attribute distanceTraveled_mm : Real;    // trigger USS - final settled USS
            attribute :>> measured = distanceTraveled_mm;
            attribute :>> target   = rover.dStop_mm + rover.dReaction_mm;
        }

        requirement def <'CMP-6'> IMUDriftBound specializes
                RequirementTemplates::UpperBoundRequirement {
            subject rover : WallRover;
            attribute measuredDrift_dps : Real;
            attribute :>> measured = measuredDrift_dps;
            attribute :>> target   = rover.imuDrift_dps_s;
        }
    }

    // -----------------------------------------------------------
    // 3.6  Top-level need assembly + satisfy claim
    // -----------------------------------------------------------
    package WallRunRequirements {

        requirement def WallRunNeed {
            subject rover : WallRover;

            requirement <'STK-1'> noContact     : STK::NoWallContact;
            requirement <'STK-3'> maxSpeed      : STK::MaxSpeed;
            requirement <'STK-4'> completeStop  : STK::CompleteStop;

            requirement <'SYS-1'> clearance     : SYS::MinimumClearance {
                requirement <'FUN-2'> sensing   : FUN::ContinuousForwardDistance {
                    requirement <'CMP-3'> f1    : CMP::USSF1ValidReading;
                    requirement <'CMP-4'> f2    : CMP::USSF2Agreement;
                }
                requirement <'FUN-3'> braking   : FUN::BrakingTrigger {
                    requirement <'CMP-5'> stop  : CMP::StoppingDistance;
                }
            }

            requirement <'SYS-2'> minGap        : SYS::MinimiseGap;

            requirement <'SYS-3'> maxSpeedSys   : SYS::MaxSpeedApproach {
                requirement <'FUN-1'> propulsion : FUN::BothMotorsMaxSpeed {
                    requirement <'CMP-1'> mA    : CMP::MotorASpeed;
                    requirement <'CMP-2'> mB    : CMP::MotorBSpeed;
                }
            }

            requirement <'SYS-4'> noResume      : SYS::NoResume;

            requirement <'SYS-5'> heading       : SYS::HeadingBound {
                requirement <'FUN-4'> hold      : FUN::HeadingHold {
                    requirement <'CMP-6'> imu   : CMP::IMUDriftBound;
                }
            }
        }
    }

    // -----------------------------------------------------------
    // 3.7  Design satisfy claim
    // -----------------------------------------------------------
    part def WallRoverDesign specializes WallRover {
        satisfy requirement WallRunRequirements::WallRunNeed;
        // Parameters are free until calibration binds them.
        // The executable model (executable_model_v1.py) evaluates this
        // satisfy/require roll-up at the committed configuration.
    }
}

// ============================================================
// END OF MODEL
// Trace spine (CMP req -> SysML attribute -> Python variable -> calibration):
//   CMP-1/2  vMaxRated_dps      <->  m.vMaxRated_dps      <- Cal-Run-2 motor speed plateau
//   CMP-3/4  ussValidMin_mm     <->  m.ussValidMin_mm      <- Cal-Run-2 min observed
//   CMP-5    dStop_mm           <->  m.dStop_mm            <- Cal-Run-2 ΔUSS post-trigger
//   CMP-5    dReaction_mm       <->  m.dReaction_mm        <- derived (vMax * loopPeriod)
//   CMP-6    imuDrift_dps_s     <->  m.imuDrift_dps_s      <- Cal-Run-2 heading slope
//   SYS-5    headingTol_deg     <->  m.headingTol_deg      <- Cal-Run-2 max |heading|
//   SYS-1    finalClearance_mm  <->  m.predict_gap()       <- Verification-Run + T1 operator
//   SYS-2    minGap (obj.)      <->  m.predict_gap()       <- Verification-Run + T1 operator
// ============================================================
