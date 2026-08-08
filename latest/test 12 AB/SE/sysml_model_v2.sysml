// ============================================================================
// wall_stop_system_v2.sysml — Tailored model for the rover wall-stop task.
// VERSION: 2.0   STATUS: BASELINE   DATE: 2026-07-21
//
// CHANGE FROM v1:  Replaced all inline template re-declarations with imports
// from rover_generic.sysml (now available). Part types corrected to canonical
// names (DistanceSensor, InertialUnit, ReflectanceSensor). Stopping-distance
// model updated to reproduce RelationTemplates::StoppingDistance expression.
// RoverLatency attribute added to WallRover. RangeRequirement removed; CMP-3
// now uses the validated LowerBoundRequirement shape only.
//
// NOTE on calc invocation: per rover_generic.sysml validation note, calc
// INVOCATION is not in the proven-valid set. The populated model reproduces
// every relation's expression in-place against bound parameters. The calc
// defs remain the single source of truth for those expressions.
//
// Structural checks (gate, out-of-band):
//   ✓ Every requirement reachable from WallRunRequirements::WallRunNeed
//   ✓ Decomposition edge-set matches requirements_spec_v2 requirement tree
//   ✓ Imports resolve to rover_generic.sysml packages
//   ✓ No invented notation; all constructs from validated template set
// ============================================================================

// ============================================================
// IMPORTS from rover_generic.sysml
// ============================================================
private import RoverCommon::*;           // Reflectance, Angle, RoverLatency
private import RoverStructure::*;        // Rover, DriveMotor, DistanceSensor,
                                         // InertialUnit, ReflectanceSensor
private import RelationTemplates::*;     // RotationToSpeed, StoppingDistance,
                                         // MaxSpeedFromBudget (calc defs;
                                         // NOT invoked — expressions reproduced)
private import RequirementTemplates::*;  // LowerBoundRequirement, UpperBoundRequirement

// ============================================================
// PACKAGE — WALL-STOP SYSTEM MODEL
// ============================================================
package WallStopSystem {

    // ----------------------------------------------------------
    // 1. WallRover Part Definition
    //    Specialises RoverStructure::Rover; fixes multiplicities
    //    and adds wall-stop attributes.
    //    All parameters marked [TBD_*] are FREE until calibration.
    // ----------------------------------------------------------
    part def WallRover specializes Rover {

        // --- Specialise inherited parts with fixed multiplicities ---
        part :>> motors  : DriveMotor[2];        // two drive motors
        part :>> rangers : DistanceSensor[3];    // fwd1, fwd2, rear
        // imu   : InertialUnit   (inherited, multiplicity 1, unchanged)
        // floor : ReflectanceSensor (inherited; present, not required by task)
        // latency : RoverLatency  (inherited; tChain = TBD_TRESP below)

        // --- Drive parameters ---
        // Reproducing RelationTemplates::RotationToSpeed in-place:
        //   v_max = motorSpeed * k     (k: m/rad, bundles radius+gear+slip)
        // Calibration note: k is NOT separately calibrated; vMax_mms is
        // measured directly from USS slope (zero-extrapolation at operating
        // point), making k implicit: k_mmrad = vMax_mms / vMaxRated_radps.
        attribute vMaxRated_dps   : Real;   // [TBD_VMOT] max motor cmd speed  deg/s
        attribute vMax_mms        : Real;   // [TBD_VMAX_MMS] = vMaxRated_radps * k_mmrad  mm/s
        attribute k_mmrad         : Real;   // implicit calibrated constant  mm/rad

        // --- Latency chain (from RoverCommon::RoverLatency) ---
        // tResponse_s = latency.tChain (hub-side: compute + BLE + command-issue)
        //             plus sensor sampling latency (one refresh interval)
        // Measured as median inter-sample interval from hub-clock timestamps.
        attribute tResponse_s : Real;       // [TBD_TRESP]  s

        // --- Stopping model ---
        // Reproducing RelationTemplates::StoppingDistance in-place:
        //   d = v * tResponse + v² / (2·a) + margin
        // At single operating point (max speed only):
        //   dStopTotal = v_max * tResponse + v_max² / (2·a)    [measured directly]
        //   a is back-solved only for feasibility checks.
        attribute dStopTotal_mm   : Real;   // [TBD_DSTOP]  measured composite  mm
        attribute decel_mms2      : Real;   // [TBD_DECEL]  back-solved: vMax²/(2*(dStop-vMax*tResp))  mm/s²

        // Design assertion: reproduces StoppingDistance at operating point
        assert constraint stoppingModel {
            dStopTotal_mm ==
                vMax_mms * tResponse_s
                + vMax_mms ** 2 / (2.0 * decel_mms2)
        }

        // --- Sensor model ---
        // dCombo = d_front_offset + uss_bias_systematic
        // Not in generic templates; task-specific composite (wall-proximity only).
        attribute dCombo_mm       : Real;   // [TBD_COMBO]  T1-anchored  mm
        attribute ussValidMin_mm  : Real;   // [TBD_USS_MIN]  mm
        attribute ussAgreement_mm : Real;   // [TBD_USS_AGREE]  mm

        // --- Trigger (design output) ---
        // Reproducing StoppingDistance + margin + sensor offset:
        attribute safetyMargin_mm : Real;   // design choice; sized from calibration RSS
        attribute dTrigger_mm     : Real;   // [TBD_TRIGGER]  mm

        assert constraint triggerDesign {
            dTrigger_mm == dStopTotal_mm + dCombo_mm + safetyMargin_mm
            // Equivalently (reproducing StoppingDistance):
            //  dTrigger = v*tResp + v²/(2a) + dCombo + margin
        }

        // --- Performance metric ---
        attribute finalClearance_mm : Real;   // front-face to wall at full stop  mm
        attribute contactMargin_mm  : Real = 0.0;  // SYS-1 lower bound

        // Gap model: what the rover's front face clears after stopping
        assert constraint gapModel {
            finalClearance_mm == dTrigger_mm - dCombo_mm - dStopTotal_mm
            // = safetyMargin_mm at design point
            // Deviates in operation by δ(dCombo) + δ(dStopTotal) from calibration residuals
        }

        // --- Heading ---
        attribute headingTol_deg   : Real;   // [TBD_HDG]  deg
        attribute imuDrift_degps   : Real;   // [TBD_HDG_DRIFT]  deg/s
    }


    // ----------------------------------------------------------
    // 2. Requirements — STK level
    // ----------------------------------------------------------
    package STK {

        requirement def <'STK-1'> NoWallContact
                specializes LowerBoundRequirement {
            subject rover : WallRover;
            attribute :>> measured = rover.finalClearance_mm;
            attribute :>> target   = rover.contactMargin_mm;    // 0.0 mm
            doc /* The rover shall not make contact with the wall
                   at any point during or after the run. */
        }

        requirement def <'STK-3'> MaxSpeedApproach
                specializes LowerBoundRequirement {
            subject rover : WallRover;
            attribute measuredSpeed_mms : Real;
            attribute :>> measured = measuredSpeed_mms;
            attribute :>> target   = rover.vMax_mms;
            doc /* The rover shall operate at maximum available motor speed
                   during the approach phase. */
        }

        requirement def <'STK-4'> CompleteStop {
            subject rover : WallRover;
            doc /* When the rover reaches zero velocity after braking, it shall
                   remain stationary. Verified by programme inspection:
                   brake() only after trigger, no run() thereafter. */
        }
    }

    // ----------------------------------------------------------
    // 3. Requirements — SYS level
    // ----------------------------------------------------------
    package SYS {

        /** SYS-1: clearance ≥ 0 mm at all times. */
        requirement def <'SYS-1'> MinimumClearance
                specializes LowerBoundRequirement {
            subject rover : WallRover;
            attribute :>> measured = rover.finalClearance_mm;
            attribute :>> target   = rover.contactMargin_mm;
        }

        /** SYS-2: minimise final gap (graded objective, not pass/fail). */
        requirement def <'SYS-2'> MinimiseGap {
            subject rover : WallRover;
            attribute measuredGap_mm : Real;
            doc /* Objective: minimise measuredGap_mm subject to SYS-1.
                   No pass/fail threshold; scored externally.
                   Predicted value set by executable model post-calibration. */
        }

        /** SYS-3: command max speed start → trigger. */
        requirement def <'SYS-3'> MaxSpeedCommand
                specializes LowerBoundRequirement {
            subject rover : WallRover;
            attribute commandedSpeed_mms : Real;
            attribute :>> measured = commandedSpeed_mms;
            attribute :>> target   = rover.vMax_mms;
        }

        /** SYS-4: no motion resumed after stop. */
        requirement def <'SYS-4'> NoResume {
            subject rover : WallRover;
            doc /* Verified by programme inspection: no run() command after
                   the brake trigger fires. */
        }

        /** SYS-5 (Derived): heading within ± headingTol_deg. */
        requirement def <'SYS-5'> HeadingBound
                specializes UpperBoundRequirement {
            subject rover : WallRover;
            attribute absHeading_deg : Real;      // |imu.yaw| in degrees
            attribute :>> measured = absHeading_deg;
            attribute :>> target   = rover.headingTol_deg;
            doc /* Derived. Heading deviation causes asymmetric approach;
                   one side closes faster, increasing contact risk. */
        }
    }

    // ----------------------------------------------------------
    // 4. Requirements — FUN level
    // ----------------------------------------------------------
    package FUN {

        requirement def <'FUN-1'> BothMotorsMaxSpeed {
            subject rover : WallRover;
            doc /* While in approach phase, the propulsion function shall
                   command both drive motors at maximum rated speed.
                   Decomposed to CMP-1 and CMP-2. */
        }

        requirement def <'FUN-2'> ContinuousForwardDistance {
            subject rover : WallRover;
            doc /* The forward sensing function shall continuously report
                   wall distance to the control loop throughout the approach.
                   Decomposed to CMP-3 and CMP-4. */
        }

        requirement def <'FUN-3'> BrakingTrigger {
            subject rover : WallRover;
            doc /* When USS-F1 reading ≤ dTrigger_mm, the braking function
                   shall issue motor stop commands within one tResponse period.
                   Decomposed to CMP-5. */
        }

        requirement def <'FUN-4'> HeadingHold {
            subject rover : WallRover;
            doc /* The heading-hold function shall maintain IMU heading within
                   ± headingTol_deg of 0° via differential motor speed.
                   Decomposed to CMP-6. */
        }
    }

    // ----------------------------------------------------------
    // 5. Requirements — CMP level (single-effector leaves)
    // ----------------------------------------------------------
    package CMP {

        /** CMP-1: Motor A commanded at ≥ vMax_mms equivalent. */
        requirement def <'CMP-1'> MotorASpeed
                specializes LowerBoundRequirement {
            subject rover : WallRover;
            attribute motorACmdSpeed_dps : Real;
            attribute :>> measured = motorACmdSpeed_dps;
            attribute :>> target   = rover.vMaxRated_dps;
        }

        /** CMP-2: Motor B commanded at ≥ vMax. */
        requirement def <'CMP-2'> MotorBSpeed
                specializes LowerBoundRequirement {
            subject rover : WallRover;
            attribute motorBCmdSpeed_dps : Real;
            attribute :>> measured = motorBCmdSpeed_dps;
            attribute :>> target   = rover.vMaxRated_dps;
        }

        /** CMP-3: USS-F1 reading ≥ ussValidMin throughout approach.
            Note: RangeRequirement is NOT in rover_generic templates.
            Upper bound (< room length) is geometrically guaranteed; only
            the lower validity bound needs a requirement. */
        requirement def <'CMP-3'> USSF1ValidMin
                specializes LowerBoundRequirement {
            subject rover : WallRover;
            attribute ussF1Reading_mm : Real;
            attribute :>> measured = ussF1Reading_mm;
            attribute :>> target   = rover.ussValidMin_mm;
        }

        /** CMP-4: USS-F2 agrees with USS-F1 within ussAgreement_mm. */
        requirement def <'CMP-4'> USSF2Agreement
                specializes UpperBoundRequirement {
            subject rover : WallRover;
            attribute ussDisagreement_mm : Real;   // |F1 − F2|
            attribute :>> measured = ussDisagreement_mm;
            attribute :>> target   = rover.ussAgreement_mm;
        }

        /** CMP-5: Final clearance ≥ 0 mm (the single-effector stopping test).
            Reproduces gapModel constraint under test conditions. */
        requirement def <'CMP-5'> StoppingClearance
                specializes LowerBoundRequirement {
            subject rover : WallRover;
            attribute :>> measured = rover.finalClearance_mm;
            attribute :>> target   = rover.contactMargin_mm;   // 0
        }

        /** CMP-6: IMU drift ≤ imuDrift_degps. */
        requirement def <'CMP-6'> IMUDriftBound
                specializes UpperBoundRequirement {
            subject rover : WallRover;
            attribute measuredDrift_degps : Real;
            attribute :>> measured = measuredDrift_degps;
            attribute :>> target   = rover.imuDrift_degps;
        }
    }

    // ----------------------------------------------------------
    // 6. Top-level need assembly + satisfy claim
    // ----------------------------------------------------------
    package WallRunRequirements {

        requirement def WallRunNeed {
            subject rover : WallRover;

            // STK
            requirement <'STK-1'> noContact    : STK::NoWallContact;
            requirement <'STK-3'> maxSpeed      : STK::MaxSpeedApproach;
            requirement <'STK-4'> completeStop  : STK::CompleteStop;

            // SYS-1: no contact chain
            requirement <'SYS-1'> clearance     : SYS::MinimumClearance {
                requirement <'FUN-2'> sensing   : FUN::ContinuousForwardDistance {
                    requirement <'CMP-3'> f1Valid : CMP::USSF1ValidMin;
                    requirement <'CMP-4'> f2Agree : CMP::USSF2Agreement;
                }
                requirement <'FUN-3'> braking   : FUN::BrakingTrigger {
                    requirement <'CMP-5'> stop  : CMP::StoppingClearance;
                }
            }

            // SYS-2: objective
            requirement <'SYS-2'> minGap        : SYS::MinimiseGap;

            // SYS-3: max speed chain
            requirement <'SYS-3'> maxSpeedSys   : SYS::MaxSpeedCommand {
                requirement <'FUN-1'> propulsion : FUN::BothMotorsMaxSpeed {
                    requirement <'CMP-1'> mA    : CMP::MotorASpeed;
                    requirement <'CMP-2'> mB    : CMP::MotorBSpeed;
                }
            }

            // SYS-4: complete stop
            requirement <'SYS-4'> noResume      : SYS::NoResume;

            // SYS-5: heading chain
            requirement <'SYS-5'> heading       : SYS::HeadingBound {
                requirement <'FUN-4'> hold      : FUN::HeadingHold {
                    requirement <'CMP-6'> imu   : CMP::IMUDriftBound;
                }
            }
        }
    }

    // ----------------------------------------------------------
    // 7. Design claim
    // ----------------------------------------------------------
    part def WallRoverDesign specializes WallRover {
        satisfy requirement WallRunRequirements::WallRunNeed;
        // All TBD_* attributes are free until calibration binds them.
        // The executable model (executable_model_v2.py) evaluates the
        // satisfy/require roll-up at the committed configuration.
    }

} // end package WallStopSystem

// ============================================================
// TRACE SPINE (CMP req → SysML attr → Python var → cal source)
//   CMP-1/2  vMaxRated_dps     <-> m.vMaxRated_dps     <- Cal-Run-2 plateau
//   CMP-1/2  vMax_mms          <-> m.vMax_mms           <- Cal-Run-2 USS slope
//   CMP-3    ussValidMin_mm    <-> m.ussValidMin_mm     <- Cal-Run-2 min observed
//   CMP-4    ussAgreement_mm   <-> m.ussAgreement_mm   <- Cal-Run-2 |F1-F2|
//   CMP-5    dStopTotal_mm     <-> m.dStopTotal_mm      <- Cal-Run-2 ΔUSS
//   CMP-5    tResponse_s       <-> m.tResponse_s        <- Cal-Run-2 timestamps
//   CMP-6    imuDrift_degps    <-> m.imuDrift_degps     <- Cal-Run-2 heading slope
//   SYS-1/2  finalClearance_mm <-> m.predict_gap()      <- Verif-Run + T1 meas.
//   SYS-5    headingTol_deg    <-> m.headingTol_deg     <- Cal-Run-2 max|heading|
// ============================================================
