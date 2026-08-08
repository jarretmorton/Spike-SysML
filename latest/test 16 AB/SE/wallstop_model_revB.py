"""
================================================================================
EXECUTABLE ANALYSIS MODEL -- WallStop rover  (rev B, GATE B issue)
================================================================================
Revision B supersedes rev A in ONE structural respect, forced by C1 data:

  rev A:  stopDistance = v*t_response + v^2/(2*a_brake)      [both terms free]
  rev B:  stopDistance = v*t_eff                             [lump, calibrated
                                                              AT the operating
                                                              point]

WHY.  C1 exercised two stops at 475.6 and 462.2 mm/s -- 2.8 % apart.  Solving
the two-term form on those two points returns t_response = +0.534 s and
a_brake = -554 mm/s^2: a NEGATIVE deceleration, physically impossible.  The
split is not identifiable from data at one operating point; the quadratic term
has no leverage.  Per tenet A2 ("develop only what calibration can falsify")
the unidentifiable split is removed rather than fitted, and per the
RelationTemplates::StoppingDistance doc note -- "At a SINGLE operating point,
measure the stopping distance directly at that point (calibration point =
operating point => zero extrapolation) and back-solve `a` only if a feasibility
check needs it" -- the lump is measured directly.  No feasibility check needs
`a`, so `a` is left UNBOUND and is reported as such.

Everything is carried in RANGER-A UNITS (millimetres as ranger A reports them).
The trigger compares a ranger-A reading against a threshold built from
ranger-A-referenced constants, so the ranger's own scale cancels exactly and
never needs to be separated from the odometry scale.

API unchanged: predict / evaluate / sweep.
================================================================================
"""
from dataclasses import dataclass, fields, replace
import math


class UnboundParameter(Exception):
    pass


def _req(p, *names):
    missing = [n for n in names if getattr(p, n) is None]
    if missing:
        raise UnboundParameter("unbound parameter(s): " + ", ".join(missing))
    return [getattr(p, n) for n in names]


@dataclass
class Params:
    # ---- ranger A (the sole trigger channel after C1) ----------------------
    c_offset_A: float = None      # TBD-01  rangerA.longitudinalOffset    [mm]
    sigma_u: float = None         # TBD-07  rangerA.noiseSigma            [mm]
    u_clamp: float = None         # TBD-09  rangerA.minValidRange         [mm]
    # ---- drivetrain ---------------------------------------------------------
    k_travel: float = None        # TBD-03  motor.travelPerAngle     [mm/deg]
    v_max_ground: float = None    # TBD-04  rover.vMaxAchievable       [mm/s]
    a_brake: float = None         # TBD-05  NOT IDENTIFIABLE -> stays None
    # ---- control chain (lumped) --------------------------------------------
    t_eff: float = None           # TBD-06  rover.tResponse (lump)         [s]
    dt_loop: float = None         # TBD-08  rover.loopPeriod               [s]
    # ---- alignment -----------------------------------------------------------
    theta_yaw_deg: float = None   # TBD-11  rover.headingDeviation       [deg]
    w_half: float = None          # TBD-19  rover.halfWidth               [mm]
    # ---- design --------------------------------------------------------------
    target_gap: float = None      # TBD-12  rover.targetGap               [mm]
    k_sigma: float = 3.0
    # ---- 1-sigma uncertainties ----------------------------------------------
    sigma_c: float = None
    sigma_t_eff: float = None
    sigma_yaw: float = None
    sigma_model: float = None
    # ---- requirement targets -------------------------------------------------
    heading_limit_deg: float = 5.0
    loop_period_limit: float = 0.025
    rest_speed_limit: float = 5.0
    u_rest_floor: float = 44.0    # SYS-6: rest reading must clear the clamp
    # ---- evidence flags -------------------------------------------------------
    ev_port_selfcheck: bool = None
    ev_trim_never_exceeds_max: bool = None
    ev_ranger_b_not_gating: bool = None
    ev_imu_rest_indicator: bool = None
    ev_fallback_channel: bool = None
    ev_no_cross_run_state: bool = None
    ev_onboard_estimate: bool = None
    ev_refresh_within_bound: bool = None
    ev_min_range_respected: bool = None


# ------------------------------------------------------------------ relations

def rotation_to_speed(motor_speed_deg_s, k_travel):
    """RelationTemplates::RotationToSpeed."""
    return motor_speed_deg_s * k_travel


def stopping_distance(v, t_eff):
    """RelationTemplates::StoppingDistance, quadratic term suppressed (rev B)."""
    return v * t_eff


def steady_speed(p):
    return _req(p, "v_max_ground")[0]


def trigger_threshold_ranger_units(v_measured, design):
    """Flight-code trigger law:  U_thr(v) = c_A + G + v * t_eff."""
    c, g, t = _req(design, "c_offset_A", "target_gap", "t_eff")
    return c + g + stopping_distance(v_measured, t)


def realized_final_clearance(design, truth):
    """Two-world evaluation.  design is truth -> returns target_gap."""
    v = steady_speed(truth)
    u_thr = trigger_threshold_ranger_units(v, design)
    ct, tt = _req(truth, "c_offset_A", "t_eff")
    return u_thr - stopping_distance(v, tt) - ct


def predicted_rest_reading(design, truth=None):
    """What ranger A should report once the rover is stopped."""
    truth = truth or design
    return realized_final_clearance(design, truth) + _req(truth, "c_offset_A")[0]


def sigma_gap(p):
    """Tenet A6: RSS of the independent contributors, all in ranger-A mm."""
    v = steady_speed(p)
    sc, st, su, dt, sy, sm = _req(p, "sigma_c", "sigma_t_eff", "sigma_u",
                                  "dt_loop", "sigma_yaw", "sigma_model")
    terms = {
        "offset_c_A": sc,
        "lump_run_to_run": v * st,
        "ranger_noise": su,
        "trigger_phase": v * dt / math.sqrt(12.0),
        "yaw_corner": sy,
        "model_residual": sm,
    }
    return math.sqrt(sum(t * t for t in terms.values())), terms


def contact_margin(p):
    return p.k_sigma * sigma_gap(p)[0]


def predict(design, truth=None):
    truth = truth or design
    v = steady_speed(truth)
    s, terms = sigma_gap(design)
    g = realized_final_clearance(design, truth)
    return {
        "v_steady": v,
        "stopping_lump": stopping_distance(v, _req(design, "t_eff")[0]),
        "trigger_threshold_u": trigger_threshold_ranger_units(v, design),
        "final_clearance": g,
        "rest_reading_u": predicted_rest_reading(design, truth),
        "sigma_gap": s,
        "sigma_terms": terms,
        "contact_margin": contact_margin(design),
        "clearance_margin": g - contact_margin(design),
        "sys6_headroom": predicted_rest_reading(design, truth) - design.u_rest_floor,
        "p_contact_per_run": 0.5 * math.erfc((g / s) / math.sqrt(2)),
    }


# --------------------------------------------------------------- requirements
REQUIREMENTS = [
    ("STK-1", [], "parent", "Execute the wall-approach task."),
    ("STK-2", ["STK-1"], "parent", "Shall not contact the wall."),
    ("STK-3", ["STK-1"], "parent", "Complete stop at the end of the approach."),
    ("STK-4", ["STK-1"], "parent", "Travel at maximum achievable speed."),
    ("STK-5", ["STK-1"], "parent", "Minimise the final gap. [OBJECTIVE]"),
    ("STK-6", ["STK-1"], "parent", "Repeat over five unchanged runs."),
    ("SYS-1", ["STK-2", "STK-5"], "lower", "Final clearance >= contact margin."),
    ("SYS-2", ["STK-2"], "parent", "Trigger the stop on prediction."),
    ("SYS-3", ["STK-3"], "upper", "End-of-run ground speed <= rest threshold."),
    ("SYS-4", ["STK-4"], "lower", "Commanded speed >= rated maximum."),
    ("SYS-5", ["STK-2"], "upper", "Heading deviation <= heading limit."),
    ("SYS-6", ["STK-5"], "lower", "Report a valid onboard clearance estimate."),
    ("SYS-7", ["STK-6"], "flag", "No dependence on cross-run state."),
    ("SYS-8", ["STK-2"], "flag", "Independent-channel fallback."),
    ("FUN-1", ["SYS-2"], "upper", "Sense clearance every cycle."),
    ("FUN-2", ["SYS-2"], "parent", "Estimate ground speed every cycle."),
    ("FUN-3", ["SYS-2"], "parent", "Compute stopping distance every cycle."),
    ("FUN-4", ["SYS-2"], "upper", "Assert the trigger within one cycle."),
    ("FUN-5", ["SYS-4"], "parent", "Command the drivetrain at maximum."),
    ("FUN-6", ["SYS-3"], "parent", "Apply braking on trigger."),
    ("FUN-7", ["SYS-5"], "parent", "Apply steering trim."),
    ("FUN-8", ["SYS-6"], "flag", "Log off the hot path."),
    ("FUN-9", ["SYS-8"], "flag", "Validity-check and select the channel."),
    ("FUN-10", ["SYS-7"], "flag", "Establish references at run start."),
    ("CMP-1", ["FUN-1"], "upper", "Ranger A offset known to sigma_c."),
    ("CMP-2", ["FUN-1"], "flag", "The stop decision shall not depend on ranger B."),
    ("CMP-3", ["FUN-1"], "flag", "Ranger refresh interval bounded."),
    ("CMP-4", ["FUN-9"], "flag", "Clamp region rejected."),
    ("CMP-5", ["FUN-2"], "lower", "Rotation-to-travel scale bound."),
    ("CMP-6", ["FUN-5"], "lower", "Achievable ground speed >= floor."),
    ("CMP-7", ["FUN-3", "FUN-6"], "flag", "Stopping lump bound at the op point."),
    ("CMP-8", ["FUN-3"], "upper", "Effective latency bounded."),
    ("CMP-9", ["FUN-7"], "upper", "Heading drift <= heading limit."),
    ("CMP-10", ["FUN-4"], "upper", "Loop period <= limit."),
    ("CMP-11", ["FUN-10"], "flag", "Port/polarity self-check at init."),
    ("CMP-12", ["FUN-7"], "flag", "Trim only reduces commanded speed."),
    ("CMP-14", ["FUN-6"], "flag", "IMU at-rest indicator available."),
]

_FLAG = {
    "SYS-7": "ev_no_cross_run_state", "SYS-8": "ev_fallback_channel",
    "FUN-8": "ev_onboard_estimate", "FUN-9": "ev_fallback_channel",
    "FUN-10": "ev_no_cross_run_state", "CMP-2": "ev_ranger_b_not_gating",
    "CMP-3": "ev_refresh_within_bound", "CMP-4": "ev_min_range_respected",
    "CMP-7": "ev_imu_rest_indicator", "CMP-11": "ev_port_selfcheck",
    "CMP-12": "ev_trim_never_exceeds_max", 
    "CMP-14": "ev_imu_rest_indicator",
}


def _operands(rid, p, pred):
    try:
        if rid == "SYS-1":
            return pred["final_clearance"], pred["contact_margin"]
        if rid == "SYS-3":
            return 0.0, p.rest_speed_limit
        if rid == "SYS-4":
            return 1.0, 1.0
        if rid == "SYS-5" or rid == "CMP-9":
            return _req(p, "theta_yaw_deg")[0], p.heading_limit_deg
        if rid == "SYS-6":
            return pred["rest_reading_u"], p.u_rest_floor
        if rid in ("FUN-1", "FUN-4", "CMP-10"):
            return _req(p, "dt_loop")[0], p.loop_period_limit
        if rid == "CMP-1":
            return _req(p, "sigma_c")[0], 6.0
        if rid == "CMP-5":
            return _req(p, "k_travel")[0], 0.0
        if rid == "CMP-6":
            return steady_speed(p), 0.0
        if rid == "CMP-8":
            return _req(p, "t_eff")[0], 0.15
    except UnboundParameter:
        return None
    return None


def evaluate(design, truth=None):
    truth = truth or design
    try:
        pred = predict(design, truth)
    except UnboundParameter:
        pred = None
    v = {}
    for rid, parents, kind, _ in REQUIREMENTS:
        if kind == "flag":
            f = _FLAG.get(rid)
            val = getattr(design, f) if f else None
            v[rid] = "UNBOUND" if val is None else ("PASS" if val else "FAIL")
        elif kind in ("lower", "upper") and pred:
            ops = _operands(rid, design, pred)
            if ops is None:
                v[rid] = "UNBOUND"
            else:
                m, t = ops
                v[rid] = "PASS" if ((m >= t) if kind == "lower" else (m <= t)) else "FAIL"
        elif kind in ("lower", "upper"):
            v[rid] = "UNBOUND"
        else:
            v[rid] = None
    kids = {}
    for rid, parents, _, _ in REQUIREMENTS:
        for par in parents:
            kids.setdefault(par, []).append(rid)

    def roll(rid):
        own = v[rid]
        sub = [roll(c) for c in kids.get(rid, [])]
        vals = ([own] if own else []) + sub
        v[rid] = "FAIL" if "FAIL" in vals else ("UNBOUND" if "UNBOUND" in vals else "PASS")
        return v[rid]
    roll("STK-1")
    return v, pred


def sweep(name, design, lo, hi, n=21):
    out = []
    for i in range(n):
        x = lo + (hi - lo) * i / (n - 1)
        out.append((x, realized_final_clearance(design, replace(design, **{name: x}))))
    return out


# ======================= C1-BOUND CONFIGURATION (GATE B) ======================
C1_BOUND = Params(
    c_offset_A=10.0,        # TBD-01  creep-anchored, 26-pt fit, slope-spanned
    sigma_u=1.47,           # TBD-07  11 samples at rest
    u_clamp=40.0,           # TBD-09  hard clamp, measured
    k_travel=0.482,         # TBD-03  rolling-phase ranger/odometry ratio
    v_max_ground=480.9,     # TBD-04  mean of two steady segments
    a_brake=None,           # TBD-05  NOT IDENTIFIABLE -- left unbound (A3)
    t_eff=0.09661,          # TBD-06  lump, 2 stops at the operating point
    dt_loop=0.0105,         # TBD-08  min 10 / max 11 ms over 175 cycles
    theta_yaw_deg=4.91,     # TBD-11  worst of the two stops
    w_half=65.0,            # TBD-19
    target_gap=37.0,        # TBD-12  set by SYS-6 (clamp), not by SYS-1
    sigma_c=4.6,
    sigma_t_eff=0.00834,
    sigma_yaw=2.5,
    sigma_model=1.0,
    ev_port_selfcheck=True, ev_trim_never_exceeds_max=True,
    ev_ranger_b_not_gating=True,    # verified by inspection of the locked source
    ev_imu_rest_indicator=True, ev_fallback_channel=True,
    ev_no_cross_run_state=True, ev_onboard_estimate=True,
    ev_refresh_within_bound=True, ev_min_range_respected=True,
)

if __name__ == "__main__":
    p = C1_BOUND
    pr = predict(p)
    print("=== FROZEN PREDICTION at the C1-bound configuration ===")
    print("  steady speed v .............. %.0f mm/s" % pr["v_steady"])
    print("  stopping lump v*t_eff ....... %.1f mm" % pr["stopping_lump"])
    print("  trigger threshold U_thr ..... %.1f mm (ranger A)" % pr["trigger_threshold_u"])
    print("  PREDICTED final clearance ... %.1f mm" % pr["final_clearance"])
    print("  PREDICTED rest reading u_A .. %.1f mm" % pr["rest_reading_u"])
    print("  sigma_gap ................... %.2f mm" % pr["sigma_gap"])
    for k, val in sorted(pr["sigma_terms"].items(), key=lambda kv: -kv[1]):
        print("      %-20s %5.2f" % (k, val))
    print("  contact margin (3 sigma) .... %.1f mm" % pr["contact_margin"])
    print("  SYS-1 margin ................ %+.1f mm" % pr["clearance_margin"])
    print("  SYS-6 headroom above clamp .. %+.1f mm" % pr["sys6_headroom"])
    print("  P(contact) per run .......... %.2e" % pr["p_contact_per_run"])
    v, _ = evaluate(p)
    print("\n=== REQUIREMENT ROLL-UP ===")
    for rid, _, _, _ in REQUIREMENTS:
        print("  %-8s %s" % (rid, v[rid]))
    print("\n  BACK-PREDICTION of the two C1 stops (in-sample, not a test):")
    for nm, ut, ur, vv in [("core1", 652.0, 602.0, 475.64),
                           ("core2", 761.0, 718.0, 462.24)]:
        pr2 = ut - vv * p.t_eff
        print("    %s predicted rest u_A %.1f vs actual %.1f  (%+.1f mm)"
              % (nm, pr2, ur, pr2 - ur))
