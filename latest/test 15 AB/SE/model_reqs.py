# -*- coding: utf-8 -*-
"""
model_reqs.py -- the REQUIREMENT TABLE: the single source of the trace spine.

Each entry carries the requirement's id, level, parents (decomposition edges),
catalog shape, the two operands as callables over the bound parameter set, its
verification method, and its text. The SysML nested-usage edge set, the Mermaid
requirement tree and the computational satisfy/require roll-up are all derived
from THIS table, so the three views cannot silently disagree.

Imported by wall_rover_model.py.
"""


class Req(object):
    __slots__ = ("rid", "level", "parents", "shape", "measured", "target",
                 "method", "text", "sysml_name", "derived")

    def __init__(self, rid, level, parents, shape, measured, target,
                 method, text, sysml_name, derived=False):
        self.rid = rid
        self.level = level
        self.parents = parents
        self.shape = shape          # "LowerBound" | "UpperBound"
        self.measured = measured    # callable(p) -> float
        self.target = target        # callable(p) -> float
        self.method = method        # "test" | "analysis" | "inspection"
        self.text = text
        self.sysml_name = sysml_name
        self.derived = derived


def build(M):
    """M is the wall_rover_model module (for its relation functions)."""
    g = lambda n: (lambda p: p.get(n))                      # noqa: E731
    L, U = "LowerBound", "UpperBound"
    R = []
    add = R.append

    # ---------------- CMP ---------------------------------------------------
    add(Req("CMP-1", "CMP", ["FUN-1", "FUN-11"], U,
            g("ranger_fl_residual_mm"), g("ranger_residual_tol_mm"), "test",
            "The forward-left ranger shall report range with a residual against "
            "wheel odometry of no more than {target} over 120..1000 mm.",
            "RangerFLResidual"))
    add(Req("CMP-2", "CMP", ["FUN-1", "FUN-11"], U,
            g("ranger_fr_residual_mm"), g("ranger_residual_tol_mm"), "test",
            "The forward-right ranger shall report range with a residual against "
            "wheel odometry of no more than {target} over 120..1000 mm.",
            "RangerFRResidual"))
    add(Req("CMP-3", "CMP", ["FUN-4a", "FUN-11"], U,
            g("us_valid_min_mm"), lambda p: M.rest_reading(p), "test",
            "The fused ranging channel's near-range validity floor shall be no "
            "greater than the at-rest reading used by the primary estimator.",
            "NearRangeFloor", derived=True))
    add(Req("CMP-4", "CMP", ["FUN-2"], U,
            g("tau_ms"), g("tau_limit_ms"), "test",
            "The fused ranging channel's reporting lag shall not exceed {target}.",
            "ReportingLagBound", derived=True))
    add(Req("CMP-5", "CMP", ["FUN-2"], U,
            g("t_refresh_ms"), g("t_refresh_limit_ms"), "test",
            "The fused ranging channel's refresh interval shall not exceed {target}.",
            "RefreshBound", derived=True))
    add(Req("CMP-6", "CMP", ["FUN-6"], L,
            g("motor_speed_ach_left_dps"),
            lambda p: 0.98 * p.get("motor_speed_cmd_dps"), "test",
            "While cruising, the left drive motor shall sustain at least 98% of "
            "its commanded speed.", "LeftMotorCruise"))
    add(Req("CMP-7", "CMP", ["FUN-6"], L,
            g("motor_speed_ach_right_dps"),
            lambda p: 0.98 * p.get("motor_speed_cmd_dps"), "test",
            "While cruising, the right drive motor shall sustain at least 98% of "
            "its commanded speed.", "RightMotorCruise"))
    add(Req("CMP-8", "CMP", ["FUN-7"], U,
            g("stop_angle_left_deg"), g("stop_angle_limit_deg"), "test",
            "When braking is commanded, the left drive motor shall come to rest "
            "within {target} of further rotation.", "LeftMotorBrakes", derived=True))
    add(Req("CMP-9", "CMP", ["FUN-7"], U,
            g("stop_angle_right_deg"), g("stop_angle_limit_deg"), "test",
            "When braking is commanded, the right drive motor shall come to rest "
            "within {target} of further rotation.", "RightMotorBrakes", derived=True))
    add(Req("CMP-10", "CMP", ["FUN-5", "FUN-11"], U,
            g("odo_residual_mm"), g("odo_residual_tol_mm"), "test",
            "The wheel-odometry channel shall track the ranging channel over the "
            "calibrated traverse with a residual of no more than {target}.",
            "OdometryScale", derived=True))
    add(Req("CMP-11", "CMP", ["FUN-8"], U,
            g("heading_drift_static_deg"), g("heading_drift_limit_deg"), "test",
            "While the rover is at rest, the IMU heading channel shall drift by "
            "no more than {target} over the run duration.", "HeadingDrift",
            derived=True))
    add(Req("CMP-12", "CMP", ["FUN-10"], U,
            g("decel_residual_frac"), g("decel_residual_tol_frac"), "test",
            "Where the IMU forward-acceleration channel is available, the rover "
            "shall record it during braking, agreeing with the odometry-derived "
            "deceleration to within {target}.", "DecelCrossSource", derived=True))
    add(Req("CMP-13", "CMP", ["FUN-10"], U,
            g("rear_travel_residual_mm"), g("rear_travel_tol_mm"), "test",
            "Where a valid rear reference surface is present, the rover shall "
            "record rear range before motion and after the stop, agreeing with "
            "wheel odometry to within {target}.", "RearRangeCrossSource",
            derived=True))
    add(Req("CMP-14", "CMP", ["FUN-1"], U,
            g("loop_dt_ms"), g("loop_period_limit_ms"), "test",
            "The control-loop period shall not exceed {target}, hub-clock measured.",
            "LoopPeriodBound", derived=True))
    add(Req("CMP-15", "CMP", ["FUN-3"], U,
            g("speed_residual_mmps"), g("speed_residual_tol_mmps"), "test",
            "The rotation-to-speed constant shall reproduce the ranging-derived "
            "ground speed to within {target}.", "GroundSpeedRelation", derived=True))

    # ---------------- FUN ---------------------------------------------------
    add(Req("FUN-1", "FUN", ["SYS-1"], U,
            g("clearance_update_ms"), g("clearance_update_limit_ms"), "test",
            "While driving, the rover shall refresh its fused forward-clearance "
            "estimate at intervals not exceeding {target}.", "ClearanceUpdateRate"))
    add(Req("FUN-2", "FUN", ["SYS-1"], U,
            lambda p: M.t_response_ms(p), g("t_response_limit_ms"), "analysis",
            "When the fused forward clearance falls to or below the trigger "
            "threshold, the rover shall command braking within {target}.",
            "TriggerLatency"))
    add(Req("FUN-3", "FUN", ["SYS-1", "SYS-4"], L,
            lambda p: M.true_range_at_trigger(p),
            lambda p: M.stop_distance_required(p), "analysis",
            "The rover's true range at the trigger instant shall be no less than "
            "its stopping distance plus the derived safety margin.", "TriggerSizing"))
    add(Req("FUN-4a", "FUN", ["SYS-1"], L,
            g("r_trig_mm"), g("us_valid_min_mm"), "analysis",
            "The rover shall not base a trigger decision on a range reading below "
            "the ranging channel's near-range validity floor.", "TriggerAboveFloor",
            derived=True))
    add(Req("FUN-4b", "FUN", ["SYS-1"], U,
            g("r_trig_mm"), g("us_valid_max_mm"), "analysis",
            "The rover shall not base a trigger decision on a range reading above "
            "the ranging channel's far-range validity ceiling.", "TriggerBelowCeiling",
            derived=True))
    add(Req("FUN-5", "FUN", ["SYS-1"], U,
            g("travel_at_stop_mm"), g("travel_interlock_mm"), "test",
            "When wheel-odometry travel exceeds the interlock limit, the rover "
            "shall command braking independently of the ranging channel.",
            "TravelInterlock", derived=True))
    add(Req("FUN-6", "FUN", ["SYS-5"], U,
            g("drive_asymmetry_dps"), g("drive_asymmetry_limit_dps"), "test",
            "While cruising, the rover shall command both drive motors at equal "
            "magnitude in the forward sense.", "SymmetricDrive"))
    add(Req("FUN-7", "FUN", ["SYS-2"], U,
            g("brake_skew_ms"), g("brake_skew_limit_ms"), "inspection",
            "When braking is commanded, the rover shall apply the drivetrain "
            "braking mode to both motors within {target}.", "BrakingMode",
            derived=True))
    add(Req("FUN-8", "FUN", ["SYS-6"], U,
            g("heading_sample_ms"), g("heading_sample_limit_ms"), "test",
            "While driving, the rover shall sample heading at intervals not "
            "exceeding {target}.", "HeadingMeasurement"))
    add(Req("FUN-9", "FUN", ["SYS-7"], L,
            g("evidence_fields_emitted"), g("evidence_fields_required"), "inspection",
            "When motion has ceased, the rover shall emit the trigger-instant "
            "fused range, the at-rest fused range and the trigger-to-rest travel.",
            "StopEvidence"))
    add(Req("FUN-10", "FUN", ["SYS-7"], L,
            g("channels_logged"), g("channels_catalogued"), "inspection",
            "The rover shall log every catalogued channel bearing on the "
            "quantities a run touches, off the timing-critical path.",
            "ChannelLogging", derived=True))
    add(Req("FUN-11", "FUN", ["SYS-8"], U,
            g("estimator_delta_mm"), g("estimator_delta_tol_mm"), "test",
            "The rover shall compute the final gap on two independent channels "
            "and emit both, agreeing to within {target}.", "DualEstimator",
            derived=True))

    # ---------------- SYS ---------------------------------------------------
    add(Req("SYS-1", "SYS", ["STK-1"], L,
            lambda p: M.predicted_gap(p), g("contact_threshold_mm"), "analysis",
            "The rover shall not reduce its clearance to the wall to the contact "
            "threshold at any point during a run.", "NoContact"))
    add(Req("SYS-2", "SYS", ["STK-1"], U,
            g("t_settle_ms"), g("stop_time_limit_ms"), "test",
            "When braking is commanded, the rover shall reach a complete stop "
            "within {target}.", "CompleteStop"))
    add(Req("SYS-3", "SYS", ["STK-1"], U,
            g("v_cruise_mmps"), lambda p: M.v_max_from_budget(p), "analysis",
            "The rover's commanded cruise speed shall not exceed the maximum "
            "speed stoppable within the approach budget.", "SpeedFeasibility",
            derived=True))
    add(Req("SYS-4", "SYS", ["STK-2"], L,
            lambda p: M.predicted_gap(p), lambda p: M.safety_margin(p), "analysis",
            "The rover's predicted final gap shall be no less than the coverage "
            "factor times the root-sum-square dispersion of the final gap.",
            "MarginFloor", derived=True))
    add(Req("SYS-5", "SYS", ["STK-3"], L,
            g("motor_speed_cmd_dps"), g("motor_speed_max_dps"), "inspection",
            "While cruising, the rover shall command each drive motor at no less "
            "than its achievable maximum speed.", "MaximumSpeed"))
    add(Req("SYS-6", "SYS", ["STK-4"], U,
            g("psi_dev_deg"), g("heading_limit_deg"), "test",
            "The rover's heading deviation from its start heading shall not "
            "exceed {target} throughout the approach.", "Straightness"))
    add(Req("SYS-7", "SYS", ["STK-5"], L,
            g("evidence_fields_emitted"), g("evidence_fields_required"), "test",
            "After each run the rover shall emit the quantities from which its "
            "final gap is computed.", "RunEvidence"))
    add(Req("SYS-8", "SYS", ["STK-2", "STK-5"], U,
            g("estimator_error_mm"), g("estimator_tol_mm"), "test",
            "The rover's onboard final-gap estimate shall agree with operator "
            "ground truth at the operating point to within {target}.",
            "EstimatorValidated", derived=True))

    # ---------------- STK ---------------------------------------------------
    add(Req("STK-1", "STK", ["NEED"], L,
            lambda p: M.predicted_gap(p), g("contact_threshold_mm"), "test",
            "The rover shall come to a complete stop ahead of the wall without "
            "contacting it.", "StopWithoutContact"))
    add(Req("STK-2", "STK", ["NEED"], U,
            lambda p: M.predicted_gap(p), lambda p: M.safety_margin(p), "analysis",
            "The rover should minimise the final gap between its front-most point "
            "and the wall. [OBJECTIVE - graded]", "MinimiseGap"))
    add(Req("STK-3", "STK", ["NEED"], L,
            g("motor_speed_cmd_dps"), g("motor_speed_max_dps"), "inspection",
            "While approaching the wall, the rover shall drive at maximum speed.",
            "ApproachAtMaximumSpeed"))
    add(Req("STK-4", "STK", ["NEED"], U,
            g("psi_dev_deg"), g("heading_limit_deg"), "test",
            "The rover shall drive straight at the wall.", "DriveStraight"))
    add(Req("STK-5", "STK", ["NEED"], U,
            g("estimator_error_mm"), g("estimator_tol_mm"), "test",
            "The rover shall produce, for each run, onboard evidence of its final "
            "gap sufficient for the close-out reconciliation.", "RunEvidenceNeed",
            derived=True))

    return {r.rid: r for r in R}
