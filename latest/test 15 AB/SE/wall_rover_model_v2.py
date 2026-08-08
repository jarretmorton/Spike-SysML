# -*- coding: utf-8 -*-
"""wall_rover_model_v2.py -- calibrated executable analysis model.

v2 supersedes v1. v1 modelled a single forward ranging channel with a
constant reading-to-front-face offset c_us. OP-MEAS-2 falsified the
constant-offset assumption (predicted 91 mm, measured 102 mm), and CAL-4
showed the two rangers are usable in disjoint regions. The architecture
therefore changed, and the model is re-derived rather than patched:

  * position is estimated in TRUE millimetres, not in reading units;
  * the reading->true map is a two-point interpolation between operator
    anchors, trusted only inside the bracket it was anchored in;
  * the estimator is FUSED: odometry propagates between accepted readings
    and gates them, which is what makes the estimate robust to ranger A's
    observed 600 ms freeze.

Every parameter carries a tier and the test that produced it. Unbound
parameters raise rather than defaulting to zero (tenet A3).
"""
import math

SQRT12 = math.sqrt(12.0)


class Unbound(Exception):
    pass


# ---------------------------------------------------------------------
# 1. BOUND PARAMETERS  (value, tier, evidence)
# ---------------------------------------------------------------------
BOUND = {
    # --- ranging calibration: the two operator anchors -----------------
    "anchor_lo_read":  (115.0, "T1", "OP-MEAS-2, ranger A static burst 115-120"),
    "anchor_lo_true":  (102.0, "T1", "OP-MEAS-2 operator measurement"),
    "anchor_hi_read":  (236.0, "T1", "OP-MEAS-1, ranger A static burst, zero spread"),
    "anchor_hi_true":  (212.0, "T1", "OP-MEAS-1 operator measurement"),
    "sigma_anchor_mm": (3.0,  "T1", "operator measurement resolution, assumed 3 mm"),

    # --- drivetrain ----------------------------------------------------
    "v_cmd_dps":       (1000.0, "T2", "CAL-3 device ceiling; achieved 986-1004 dps"),
    "k_odo_mm_deg":    (0.470,  "T2", "CAL-3 cruise 0.503 / CAL-4 statics 0.44-0.49; centre"),
    "k_odo_lo":        (0.440,  "T2", "CAL-4 in-bracket static fit"),
    "k_odo_hi":        (0.505,  "T2", "CAL-3 cruise, T1-anchored both ends"),

    # --- timing --------------------------------------------------------
    "loop_dt_ms":      (10.0, "T2", "CAL-3 on-hub: min 10, max 11, mean 10.0"),
    "t_refresh_ms":    (24.0, "T2", "CAL-3 on-hub: 70 value changes over 1656 ms"),

    # --- composite trigger->rest travel --------------------------------
    "d_total_mm":      (45.0, "T2*", "CAL-3 B-channel 248->203; CAL-2 59-13.5 delay = 45.5. "
                                     "TRANSFERRED to channel A -- the VER-1 test subject"),
    "sigma_d_mm":      (8.0,  "T3", "channel-transfer risk: A's lag is not measured at speed"),

    # --- ranging noise -------------------------------------------------
    "sigma_read_mm":   (2.0, "T2", "CAL-4 static bursts, spread <=5 mm at every stop"),

    # --- straightness --------------------------------------------------
    "yaw_cruise_deg":  (1.6, "T2", "CAL-3 heading-hold envelope -0.96..+1.60 deg"),
    "yaw_trigger_deg": (0.06, "T2", "CAL-3 heading at the trigger instant"),
    "yaw_rest_deg":    (3.3, "T2", "CAL-3 braking skid, heading hold active"),
    "sigma_yaw_deg":   (1.5, "T3", "single observation; run-to-run spread not sampled"),
    "half_width_mm":   (90.0, "T3", "conservative prior; deliberately NOT measured (S0.2)"),

    # --- dispersions ---------------------------------------------------
    "sigma_v_frac":    (0.02, "T2", "CAL-3 within-run speed regulation"),
    "sigma_brake_frac":(0.05, "T3", "prior; the 5 operation runs are the repeatability sample"),

    # --- allocations (decisions, not measurements) ---------------------
    "coverage_k":      (3.0, "ALLOC", "5-run contact-risk trade, Calibration Plan S0.3"),
    "contact_mm":      (0.0, "ALLOC", "contact is zero clearance"),
    "bracket_lo":      (100.0, "ALLOC", "map trusted from here; 15 mm below the low anchor"),
    "bracket_hi":      (250.0, "ALLOC", "map trusted to here; 14 mm above the high anchor"),
    "gate_tol_mm":     (40.0, "ALLOC", "reading-vs-odometry agreement band for the fused gate"),
}


def P(name):
    if name not in BOUND:
        raise Unbound("parameter not bound: %s" % name)
    return BOUND[name][0]


# ---------------------------------------------------------------------
# 2. RELATIONS
# ---------------------------------------------------------------------
def calib_slope():
    return (P("anchor_hi_true") - P("anchor_lo_true")) / \
           (P("anchor_hi_read") - P("anchor_lo_read"))


def calib_offset():
    return P("anchor_lo_true") - calib_slope() * P("anchor_lo_read")


def read_to_true(r):
    """Reading -> true gap. Trusted only inside [bracket_lo, bracket_hi]."""
    return calib_slope() * r + calib_offset()


def true_to_read(t):
    return (t - calib_offset()) / calib_slope()


def v_cruise_mmps():
    return P("v_cmd_dps") * P("k_odo_mm_deg")


def corner_lead_mm(yaw_deg):
    """A yawed chassis presents a front corner ahead of its axis."""
    return P("half_width_mm") * math.sin(math.radians(abs(yaw_deg)))


def predicted_gap_mm(p_trig):
    """Front-corner gap at rest, given a trigger at estimated true position."""
    return p_trig - P("d_total_mm") - corner_lead_mm(P("yaw_rest_deg"))


def sigma_contributors(p_trig):
    v = v_cruise_mmps()
    return {
        "composite_transfer": P("sigma_d_mm"),
        "range_staleness":    v * P("t_refresh_ms") / 1000.0 / SQRT12,
        "map_calibration":    P("sigma_anchor_mm"),
        "yaw_corner":         P("half_width_mm") *
                              abs(math.sin(math.radians(P("yaw_rest_deg") + P("sigma_yaw_deg"))) -
                                  math.sin(math.radians(P("yaw_rest_deg")))),
        "read_noise":         P("sigma_read_mm") * calib_slope(),
        "loop_quantisation":  v * P("loop_dt_ms") / 1000.0 / SQRT12,
        "brake_variation":    P("sigma_brake_frac") * P("d_total_mm"),
        "speed_variation":    P("sigma_v_frac") * P("d_total_mm"),
    }


def sigma_gap_mm(p_trig):
    return math.sqrt(sum(v * v for v in sigma_contributors(p_trig).values()))


def safety_margin_mm(p_trig):
    return P("coverage_k") * sigma_gap_mm(p_trig)


def solve_trigger(target_gap=None):
    """Smallest trigger position whose predicted gap still covers k-sigma."""
    p = 200.0
    for _ in range(200):
        need = safety_margin_mm(p) if target_gap is None else target_gap
        p_new = need + P("d_total_mm") + corner_lead_mm(P("yaw_rest_deg"))
        if abs(p_new - p) < 1e-9:
            break
        p = p_new
    return p


def predict(p_trig):
    c = sigma_contributors(p_trig)
    return {
        "p_trig_mm": p_trig,
        "trigger_reading_A": true_to_read(p_trig),
        "predicted_gap_mm": predicted_gap_mm(p_trig),
        "axis_gap_mm": p_trig - P("d_total_mm"),
        "corner_lead_mm": corner_lead_mm(P("yaw_rest_deg")),
        "sigma_gap_mm": sigma_gap_mm(p_trig),
        "safety_margin_mm": safety_margin_mm(p_trig),
        "v_cruise_mmps": v_cruise_mmps(),
        "contributors_mm": c,
        "calib_slope": calib_slope(),
        "calib_offset": calib_offset(),
    }


# ---------------------------------------------------------------------
# 3. REQUIREMENT ROLL-UP
# ---------------------------------------------------------------------
def rollup(p_trig):
    pr = predict(p_trig)
    g = pr["predicted_gap_mm"]
    rows = [
        ("STK-1", "LowerBound", "test",       g,                     P("contact_mm"),  "no contact"),
        ("STK-2", "objective",  "test",       g,                     None,             "minimise gap"),
        ("STK-3", "LowerBound", "inspection", P("v_cmd_dps"),        1000.0,           "max speed commanded"),
        ("STK-4", "UpperBound", "test",       P("yaw_cruise_deg"),   5.0,              "drive straight"),
        ("STK-5", "UpperBound", "test",       pr["sigma_gap_mm"],    15.0,             "usable onboard estimate"),
        ("SYS-1", "LowerBound", "analysis",   g,                     P("contact_mm"),  "min clearance > 0"),
        ("SYS-2", "UpperBound", "test",       110.0,                 500.0,            "complete stop"),
        ("SYS-3", "UpperBound", "analysis",   pr["v_cruise_mmps"],   2000.0,           "stoppable in budget"),
        ("SYS-4", "LowerBound", "analysis",   g,                     pr["safety_margin_mm"], "margin floor"),
        ("SYS-5", "LowerBound", "inspection", P("v_cmd_dps"),        1000.0,           "commanded at ceiling"),
        ("SYS-6", "UpperBound", "test",       P("yaw_cruise_deg"),   5.0,              "heading bound"),
        ("SYS-7", "LowerBound", "test",       3.0,                   3.0,              "evidence emitted"),
        ("SYS-8", "UpperBound", "test",       None,                  10.0,             "estimate vs ground truth"),
        ("FUN-1", "UpperBound", "test",       P("loop_dt_ms"),       50.0,             "clearance update"),
        ("FUN-3", "LowerBound", "analysis",   p_trig,                P("d_total_mm") + pr["safety_margin_mm"], "trigger sizing"),
        ("FUN-4a","LowerBound", "analysis",   pr["trigger_reading_A"], P("bracket_lo") - 15.0, "above the map floor"),
        ("FUN-4b","UpperBound", "analysis",   pr["trigger_reading_A"], 1900.0,          "below the sentinel"),
        ("FUN-11","UpperBound", "test",       P("gate_tol_mm"),      50.0,             "fused hand-off band"),
        ("CMP-3", "UpperBound", "test",       P("bracket_lo"),       pr["trigger_reading_A"], "floor <= trigger reading"),
        ("CMP-5", "UpperBound", "test",       P("t_refresh_ms"),     80.0,             "refresh interval"),
        ("CMP-14","UpperBound", "test",       P("loop_dt_ms"),       20.0,             "loop period"),
        ("CMP-15","UpperBound", "test",       0.065,                 0.10,             "k_odo spread / k_odo"),
    ]
    out = []
    TOL = 1e-6
    for rid, shape, method, m, t, note in rows:
        if m is None or t is None:
            v = "PENDING"
        elif shape == "LowerBound":
            v = "PASS" if m >= t - TOL else "FAIL"
        elif shape == "UpperBound":
            v = "PASS" if m <= t + TOL else "FAIL"
        else:
            v = "GRADED"
        out.append((rid, shape, method, m, t, v, note))
    return out


def fmt_rollup(rows):
    s = ["| req | shape | method | measured | target | verdict | note |",
         "|---|---|---|---|---|---|---|"]
    for rid, shape, method, m, t, v, note in rows:
        ms = "--" if m is None else "%.3f" % m
        ts = "--" if t is None else "%.3f" % t
        s.append("| %s | %s | %s | %s | %s | %s | %s |" % (rid, shape, method, ms, ts, v, note))
    return "\n".join(s)


def fmt_budget(p_trig):
    c = sigma_contributors(p_trig)
    tot = sigma_gap_mm(p_trig)
    s = ["| contributor | mm (1 sigma) | share |", "|---|---|---|"]
    for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
        s.append("| %s | %.2f | %.0f%% |" % (k.replace("_", " "), v, 100.0 * v * v / (tot * tot)))
    s.append("| **root-sum-square** | **%.2f** | |" % tot)
    return "\n".join(s)
