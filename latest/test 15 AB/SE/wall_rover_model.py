#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wall_rover_model.py -- EXECUTABLE ANALYSIS MODEL for the wall-approach task.

The computational view of wall_rover.sysml. Every parameter, relation and
requirement constraint in the SysML model maps 1:1 to a named object here; the
requirement table (model_reqs.py) is the single source from which the SysML
nested-usage edge set, the Mermaid tree and this roll-up are all derived.

    SysML (SI: m, s, rad)                Python (mm, ms, deg)
    ---------------------------------    ---------------------------------
    WallRover::vCruise                   v_cruise_mmps
    WallRover::kOdo                      k_odo_mm_per_deg
    WallRover::kUs / cUs                 k_us / c_us_mm
    WallRover::tauSensor / tRefresh      tau_ms / t_refresh_ms
    WallRover::latency.tChain            t_act_ms
    WallRover::loopPeriod                loop_dt_ms
    WallRover::aBrake                    a_brake_mmps2
    WallRover::stopTravel                d_total_meas_mm
    WallRover::tResponse                 t_response_ms()
    WallRover::trueRangeAtTrigger        true_range_at_trigger()
    WallRover::stopDistanceRequired      stop_distance_required()
    WallRover::vMaxFromBudget            v_max_from_budget()
    WallRover::sigmaGap                  sigma_gap()
    WallRover::safetyMargin              safety_margin()
    WallRover::predictedGap              predicted_gap()
    WallRover::restReading               rest_reading()
    requirement <'X'>                    model_reqs.build()["X"]

TENET A3: every free parameter defaults to None and any computation touching an
unbound parameter raises Unbound. Priors live only in PRIORS, never as defaults.

API: predict / evaluate / sweep / sensitivity_table / estimate_* / check_*
Standard library only.
"""

import math
from model_reqs import build as _build_reqs

FSQRT12 = math.sqrt(12.0)


class Unbound(Exception):
    """Raised when a computation needs a parameter calibration has not bound."""


# ---------------------------------------------------------------------------
# 1. PARAMETERS  (SysML: WallRover attributes; all UNCALIBRATED)
# ---------------------------------------------------------------------------

FIELDS = (
    # drivetrain
    "motor_speed_cmd_dps", "motor_speed_max_dps",
    "motor_speed_ach_left_dps", "motor_speed_ach_right_dps",
    "k_odo_mm_per_deg", "v_cruise_mmps",
    "drive_asymmetry_dps", "drive_asymmetry_limit_dps",
    "stop_angle_left_deg", "stop_angle_right_deg", "stop_angle_limit_deg",
    "brake_skew_ms", "brake_skew_limit_ms",
    # forward ranging channel (fused)
    "k_us", "c_us_mm", "tau_ms", "tau_limit_ms",
    "t_refresh_ms", "t_refresh_limit_ms", "sigma_us_mm", "sigma_k_us",
    "us_valid_min_mm", "us_valid_max_mm", "r_anchor_mm",
    "ranger_fl_residual_mm", "ranger_fr_residual_mm", "ranger_residual_tol_mm",
    # timing chain
    "loop_dt_ms", "loop_period_limit_ms", "t_act_ms", "t_response_limit_ms",
    "clearance_update_ms", "clearance_update_limit_ms",
    "heading_sample_ms", "heading_sample_limit_ms",
    # stop dynamics
    "a_brake_mmps2", "d_total_meas_mm", "t_settle_ms", "stop_time_limit_ms",
    # attitude / geometry
    "psi_dev_deg", "heading_limit_deg",
    "heading_drift_static_deg", "heading_drift_limit_deg", "half_width_mm",
    # scenario / design
    "d_start_mm", "coverage_k", "contact_threshold_mm", "r_trig_mm",
    "travel_at_stop_mm", "travel_interlock_mm",
    # dispersions
    "sigma_v_frac", "sigma_brake_frac", "sigma_c_mm",
    # estimators / evidence / cross-sources
    "estimator_error_mm", "estimator_tol_mm",
    "estimator_delta_mm", "estimator_delta_tol_mm",
    "odo_residual_mm", "odo_residual_tol_mm",
    "decel_residual_frac", "decel_residual_tol_frac",
    "rear_travel_residual_mm", "rear_travel_tol_mm",
    "speed_residual_mmps", "speed_residual_tol_mmps",
    "evidence_fields_emitted", "evidence_fields_required",
    "channels_logged", "channels_catalogued",
)


class Params(object):
    _FIELDS = FIELDS

    def __init__(self, **kw):
        for f in FIELDS:
            setattr(self, f, None)
        for k, v in kw.items():
            if k not in FIELDS:
                raise KeyError("unknown parameter %r" % k)
            setattr(self, k, v)

    def get(self, name):
        v = getattr(self, name)
        if v is None:
            raise Unbound("parameter %r is uncalibrated (tenet A3)" % name)
        return v

    def bound(self, name):
        return getattr(self, name) is not None

    def copy(self, **kw):
        q = Params()
        for f in FIELDS:
            setattr(q, f, getattr(self, f))
        for k, v in kw.items():
            if k not in FIELDS:
                raise KeyError("unknown parameter %r" % k)
            setattr(q, k, v)
        return q

    def unbound_fields(self):
        return [f for f in FIELDS if getattr(self, f) is None]


# ---------------------------------------------------------------------------
# 2. PRIORS (explicit, stated, sweep-only -- NOT defaults)
#    tier: T1 external ground truth | T2 anchored/multi-point onboard | T3 prior
# ---------------------------------------------------------------------------

PRIORS = {
    "v_cruise_mmps":    (250.0, 800.0,  "T3", "wheel 43-90 mm x motor 800-1050 deg/s"),
    "c_us_mm":          (-100.0, 20.0,  "T3", "sensor face -> front-most point geometry"),
    "a_brake_mmps2":    (1500.0, 7000.0, "T3", "motor brake; traction-limited below ~7000"),
    "tau_ms":           (5.0,   60.0,   "T3", "device reporting lag"),
    "t_act_ms":         (5.0,   30.0,   "T3", "brake command -> torque onset"),
    "t_refresh_ms":     (10.0,  60.0,   "T3", "sensor update period (staleness bound)"),
    "psi_dev_deg":      (0.0,   8.0,    "T3", "open-loop differential drive"),
    "sigma_us_mm":      (1.0,   10.0,   "T3", "reading noise incl. possible crosstalk"),
    "k_us":             (0.97,  1.03,   "T3", "factory time-of-flight scale"),
    "loop_dt_ms":       (5.0,   20.0,   "T3", "achieved loop period, two sensor reads"),
    "half_width_mm":    (40.0,  90.0,   "T3", "SPIKE chassis half-width"),
    "sigma_brake_frac": (0.04,  0.15,   "T3", "friction/thermal run-to-run"),
    "sigma_v_frac":     (0.01,  0.05,   "T3", "regulated drive, battery state"),
    "sigma_c_mm":       (1.5,   4.0,    "T3", "post-anchor residual (rule + noise)"),
    "sigma_k_us":       (0.005, 0.030,  "T3", "factory scale uncertainty"),
    "d_start_mm":       (950.0, 1050.0, "T3", "operator: '~1000 mm', held constant"),
}

# Allocated design values: set by ANALYSIS (not measurement), stated here so the
# roll-up is reproducible. These are decisions, not calibrations.
ALLOCATED = {
    "coverage_k": 3.0,             # justified by the 5-run contact-risk trade
    "contact_threshold_mm": 0.0,   # contact == zero clearance
    "heading_limit_deg": 5.0,      # yaw corner penalty <= 7.8 mm at half_width 90
    "stop_time_limit_ms": 2000.0,
    "loop_period_limit_ms": 20.0,
    "t_response_limit_ms": 120.0,
    "clearance_update_limit_ms": 60.0,
    "heading_sample_limit_ms": 60.0,
    "tau_limit_ms": 80.0,
    "t_refresh_limit_ms": 80.0,
    "stop_angle_limit_deg": 1500.0,
    "brake_skew_limit_ms": 5.0,
    "drive_asymmetry_limit_dps": 20.0,
    "heading_drift_limit_deg": 2.0,
    "ranger_residual_tol_mm": 15.0,
    "odo_residual_tol_mm": 15.0,
    "estimator_tol_mm": 8.0,
    "estimator_delta_tol_mm": 12.0,
    "decel_residual_tol_frac": 0.30,
    "rear_travel_tol_mm": 30.0,
    "speed_residual_tol_mmps": 25.0,
    "evidence_fields_required": 3.0,
    "channels_catalogued": 8.0,
    "us_valid_max_mm": 1990.0,
    "r_anchor_mm": 120.0,          # planned c-anchor reading (creep stop)
}


def nominal_from_priors():
    """Prior mid-point operating point. Ranks sensitivities ONLY; it does not
    bind anything and is never used as a calibrated value."""
    p = Params(**ALLOCATED)
    for name, (lo, hi, _t, _n) in PRIORS.items():
        setattr(p, name, 0.5 * (lo + hi))
    p.us_valid_min_mm = 50.0        # device-spec prior, replaced by calibration
    return p


# ---------------------------------------------------------------------------
# 3. RELATIONS (reproduce RelationTemplates expressions against bound params)
# ---------------------------------------------------------------------------

def rotation_to_speed(motor_speed_dps, k_odo_mm_per_deg):
    """RelationTemplates::RotationToSpeed -- v = motorSpeed * k."""
    return motor_speed_dps * k_odo_mm_per_deg


def t_response_ms(p):
    """WallRover::tResponse = tauSensor + loopPeriod/2 + latency.tChain."""
    return p.get("tau_ms") + 0.5 * p.get("loop_dt_ms") + p.get("t_act_ms")


def stop_distance_required(p):
    """RelationTemplates::StoppingDistance -- v*t + v^2/(2a) + margin."""
    v = p.get("v_cruise_mmps")
    return (v * t_response_ms(p) / 1000.0
            + v ** 2 / (2.0 * p.get("a_brake_mmps2"))
            + safety_margin(p))


def v_max_from_budget(p):
    """RelationTemplates::MaxSpeedFromBudget -- positive root (feasibility)."""
    a = p.get("a_brake_mmps2")
    t = t_response_ms(p) / 1000.0
    return (-a * t + math.sqrt(a ** 2 * t ** 2
                               + 2.0 * a * (p.get("d_start_mm") - safety_margin(p))))


def stop_travel(p):
    """Travel from the trigger-firing READING to rest, in true-gap terms.
    Preferred: the measured composite (calibration point == operating point,
    zero extrapolation). Fallback: the modelled decomposition."""
    if p.bound("d_total_meas_mm"):
        return p.get("d_total_meas_mm"), "measured"
    v = p.get("v_cruise_mmps")
    return (v * t_response_ms(p) / 1000.0
            + v ** 2 / (2.0 * p.get("a_brake_mmps2"))), "modelled"


def true_range_at_trigger(p):
    return p.get("k_us") * p.get("r_trig_mm") + p.get("c_us_mm")


def yaw_penalty(p):
    """Corner lead of a yawed chassis, small-angle form (matches the SysML;
    |error| < 0.13% at 5 deg). psi_dev is measured RELATIVE to the attitude at
    which c_us was anchored, so the mean attitude is absorbed into c_us."""
    return p.get("half_width_mm") * math.radians(p.get("psi_dev_deg"))


def predicted_gap(p):
    d, _basis = stop_travel(p)
    return true_range_at_trigger(p) - d - yaw_penalty(p)


def rest_reading(p):
    """Fused reading the rover will see at rest, i.e. what the primary estimator
    must be able to read. Drives CMP-3 (near-range floor)."""
    return (predicted_gap(p) - p.get("c_us_mm")) / p.get("k_us")


# ---------------------------------------------------------------------------
# 4. UNCERTAINTY (tenet A6: RSS of independent contributors, never guessed)
# ---------------------------------------------------------------------------

def sigma_contributors(p):
    v = p.get("v_cruise_mmps")
    a = p.get("a_brake_mmps2")
    return {
        "range_staleness":    (p.get("t_refresh_ms") / FSQRT12) * v / 1000.0,
        "loop_quantisation":  (p.get("loop_dt_ms") / FSQRT12) * v / 1000.0,
        "braking_variation":  p.get("sigma_brake_frac") * (v ** 2 / (2.0 * a)),
        "speed_variation":    (t_response_ms(p) / 1000.0 + v / a)
                              * (p.get("sigma_v_frac") * v),
        "trigger_read_noise": 0.8 * p.get("sigma_us_mm"),
        "offset_anchor":      p.get("sigma_c_mm"),
        "scale_leverage":     p.get("sigma_k_us")
                              * abs(p.get("r_trig_mm") - p.get("r_anchor_mm")),
        "yaw_corner":         0.5 * yaw_penalty(p),
    }


def sigma_gap(p):
    return math.sqrt(sum(x * x for x in sigma_contributors(p).values()))


def safety_margin(p):
    return p.get("coverage_k") * sigma_gap(p)


def no_contact_margin(p):
    return predicted_gap(p) - safety_margin(p) - p.get("contact_threshold_mm")


def solve_trigger_for_target(p, gap_target_mm=None):
    """Design inverse: r_trig such that the predicted gap equals the target
    (default: coverage_k * sigma_gap). Fixed-point; sigma depends on r_trig only
    through the small scale-leverage term."""
    d, _ = stop_travel(p)
    r = (100.0 + d - p.get("c_us_mm")) / p.get("k_us")
    for _ in range(60):
        q = p.copy(r_trig_mm=r)
        tgt = safety_margin(q) if gap_target_mm is None else gap_target_mm
        r_new = (tgt + d + yaw_penalty(p) - p.get("c_us_mm")) / p.get("k_us")
        if abs(r_new - r) < 1e-9:
            return r_new
        r = r_new
    return r


# ---------------------------------------------------------------------------
# 5. PREDICT
# ---------------------------------------------------------------------------

def predict(p):
    d, basis = stop_travel(p)
    return {
        "r_trig_mm": p.get("r_trig_mm"),
        "true_range_at_trigger_mm": true_range_at_trigger(p),
        "stop_travel_mm": d,
        "stop_travel_basis": basis,
        "yaw_penalty_mm": yaw_penalty(p),
        "predicted_gap_mm": predicted_gap(p),
        "sigma_gap_mm": sigma_gap(p),
        "safety_margin_mm": safety_margin(p),
        "no_contact_margin_mm": no_contact_margin(p),
        "rest_reading_mm": rest_reading(p),
        "v_cruise_mmps": p.get("v_cruise_mmps"),
        "v_max_from_budget_mmps": v_max_from_budget(p),
        "contributors_mm": sigma_contributors(p),
    }


# ---------------------------------------------------------------------------
# 6. EVALUATE (computational satisfy/require roll-up over the requirement table)
# ---------------------------------------------------------------------------

REQS = _build_reqs(__import__(__name__))
TOL = 1e-6


def evaluate(p, reqs=None):
    """Return {rid: {shape, measured, target, verdict}}. verdict is
    PASS / FAIL / PENDING (PENDING == an operand is still uncalibrated)."""
    reqs = REQS if reqs is None else reqs
    out = {}
    for rid, r in reqs.items():
        try:
            m = float(r.measured(p))
            t = float(r.target(p))
        except Unbound as e:
            out[rid] = {"shape": r.shape, "measured": None, "target": None,
                        "verdict": "PENDING", "why": str(e), "method": r.method}
            continue
        ok = (m >= t - TOL) if r.shape == "LowerBound" else (m <= t + TOL)
        out[rid] = {"shape": r.shape, "measured": m, "target": t,
                    "verdict": "PASS" if ok else "FAIL", "why": None,
                    "method": r.method}
    return out


def rollup(rows):
    n = {"PASS": 0, "FAIL": 0, "PENDING": 0}
    for r in rows.values():
        n[r["verdict"]] += 1
    return {"counts": n, "closed": n["FAIL"] == 0 and n["PENDING"] == 0,
            "any_fail": n["FAIL"] > 0}


# ---------------------------------------------------------------------------
# 7. ONBOARD ESTIMATORS (what the rover reports after each run)
# ---------------------------------------------------------------------------

def estimate_gap_at_rest(p, r_rest_mm):
    """PRIMARY: fused at-rest reading -> front-most-point gap. Valid only while
    r_rest lies inside the ranging channel's valid window."""
    return {"channel": "range_at_rest",
            "gap_mm": p.get("k_us") * r_rest_mm + p.get("c_us_mm"),
            "in_window": p.get("us_valid_min_mm") <= r_rest_mm <= p.get("us_valid_max_mm"),
            "sigma_mm": math.sqrt(p.get("sigma_c_mm") ** 2
                                  + (p.get("sigma_us_mm") / math.sqrt(10.0)) ** 2)}


def estimate_gap_by_odometry(p, r_ref_mm, dtheta_deg):
    """FALLBACK: last in-window reading, less the wheel-odometry travel since
    that reading. Independent of the near-range floor."""
    travel = p.get("k_odo_mm_per_deg") * dtheta_deg
    return {"channel": "range_plus_odometry",
            "gap_mm": p.get("k_us") * r_ref_mm + p.get("c_us_mm") - travel,
            "in_window": True,
            "sigma_mm": math.sqrt(p.get("sigma_c_mm") ** 2
                                  + (0.02 * travel) ** 2)}


# Physical-plausibility bounds. A value outside its bound is model-contradicting
# and escalates UNCONDITIONALLY (ANOMALY DISPOSITION, branch 2).
PLAUSIBILITY = {
    "range_mm":         (0.0, 2000.0,  "outside the device's physical range"),
    "rest_minus_trig":  (None, 0.0,    "at-rest range exceeds the trigger range: "
                                       "the rover moved backwards while braking"),
    "travel_mm":        (0.0, 1200.0,  "travel exceeds the approach corridor"),
    "gap_mm":           (0.0, 1100.0,  "negative gap is contact; beyond start is impossible"),
    "heading_deg":      (-30.0, 30.0,  "yaw beyond any credible drive asymmetry"),
    "loop_dt_ms":       (0.0, 100.0,   "control loop stalled"),
    "decel_mmps2":      (0.0, 12000.0, "deceleration beyond the traction limit"),
    "v_cruise_mmps":    (0.0, 1200.0,  "ground speed beyond the drivetrain ceiling"),
}


def check_plausibility(name, value):
    lo, hi, why = PLAUSIBILITY[name]
    ok = ((lo is None or value >= lo) and (hi is None or value <= hi))
    return {"channel": name, "value": value, "plausible": ok,
            "escalate": not ok, "reason": None if ok else why}


# ---------------------------------------------------------------------------
# 8. SWEEP / SENSITIVITY
# ---------------------------------------------------------------------------

def sweep(p, name, lo, hi, n=21):
    out = []
    for i in range(n):
        x = lo + (hi - lo) * i / float(n - 1)
        q = p.copy(**{name: x})
        out.append((x, predicted_gap(q), no_contact_margin(q)))
    return out


def sensitivity_table(p=None, priors=None, r_trig=None, tiers=None):
    p = nominal_from_priors() if p is None else p
    priors = PRIORS if priors is None else priors
    tiers = tiers or {}
    if r_trig is None:
        r_trig = solve_trigger_for_target(p)
    p = p.copy(r_trig_mm=r_trig)
    rows = []
    for name, (lo, hi, tier, note) in priors.items():
        s = sweep(p, name, lo, hi, 21)
        gaps = [g for _x, g, _m in s]
        mars = [m for _x, _g, m in s]
        rows.append({"parameter": name, "range": (lo, hi),
                     "d_objective": max(gaps) - min(gaps),
                     "d_margin": max(mars) - min(mars),
                     "tier": tiers.get(name, tier), "note": note})
    rows.sort(key=lambda r: -max(r["d_objective"], r["d_margin"]))
    return {"r_trig_mm": r_trig, "base_gap_mm": predicted_gap(p),
            "base_margin_mm": no_contact_margin(p),
            "base_sigma_mm": sigma_gap(p), "rows": rows}


# ---------------------------------------------------------------------------
# 9. REPORTING HELPERS
# ---------------------------------------------------------------------------

def fmt_sensitivity(t, binding=None):
    binding = binding or {}
    out = ["| # | parameter | assumed range | objective swing (mm) | "
           "margin swing (mm) | knowledge tier | priority | bound by |",
           "|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(t["rows"], 1):
        pri = "P1" if i <= 3 else ("P2" if i <= 7 else "P3")
        out.append("| %d | `%s` | %g .. %g | %.1f | %.1f | %s | %s | %s |"
                   % (i, r["parameter"], r["range"][0], r["range"][1],
                      r["d_objective"], r["d_margin"], r["tier"], pri,
                      binding.get(r["parameter"], "CAL-1")))
    return "\n".join(out)


def fmt_budget(p):
    c = sigma_contributors(p)
    tot = math.sqrt(sum(x * x for x in c.values()))
    out = ["| contributor | 1-sigma (mm) | share of variance |", "|---|---|---|"]
    for k in sorted(c, key=lambda k: -c[k]):
        out.append("| %s | %.2f | %.0f%% |" % (k, c[k], 100.0 * c[k] ** 2 / tot ** 2))
    out.append("| **RSS total** | **%.2f** | 100%% |" % tot)
    return "\n".join(out)


def fmt_rollup(rows, reqs=None):
    reqs = REQS if reqs is None else reqs
    order = sorted(rows, key=lambda r: (["STK", "SYS", "FUN", "CMP"].index(reqs[r].level),
                                        r))
    out = ["| req | level | shape | method | measured | target | verdict |",
           "|---|---|---|---|---|---|---|"]
    for rid in order:
        r = rows[rid]
        m = "--" if r["measured"] is None else "%.3f" % r["measured"]
        t = "--" if r["target"] is None else "%.3f" % r["target"]
        out.append("| %s | %s | %s | %s | %s | %s | %s |"
                   % (rid, reqs[rid].level, r["shape"], r["method"], m, t,
                      r["verdict"]))
    return "\n".join(out)


def mermaid_tree(reqs=None):
    reqs = REQS if reqs is None else reqs
    lines = ["graph TD", '  NEED["<b>NEED</b><br/>stop as close as achievable,<br/>'
             'no contact, max speed"]']
    style = {"STK": ":::stk", "SYS": ":::sys", "FUN": ":::fun", "CMP": ":::cmp"}
    for rid in sorted(reqs, key=lambda r: (["STK", "SYS", "FUN", "CMP"].index(reqs[r].level), r)):
        r = reqs[rid]
        label = r.text.split(".")[0]
        if len(label) > 68:
            label = label[:65] + "..."
        tag = " (D)" if r.derived else ""
        lines.append('  %s["<b>%s</b>%s<br/>%s"]%s'
                     % (rid.replace("-", "_"), rid, tag, label,
                        style[r.level]))
    for rid in sorted(reqs):
        for par in reqs[rid].parents:
            lines.append("  %s --> %s" % (par.replace("-", "_"),
                                          rid.replace("-", "_")))
    lines += ["  classDef stk fill:#e8f0fe,stroke:#1a73e8;",
              "  classDef sys fill:#e6f4ea,stroke:#137333;",
              "  classDef fun fill:#fef7e0,stroke:#b06000;",
              "  classDef cmp fill:#fce8e6,stroke:#c5221f;"]
    return "\n".join(lines)


if __name__ == "__main__":
    p = nominal_from_priors()
    t = sensitivity_table(p)
    print("SENSITIVITY at the prior mid-point: r_trig=%.1f gap=%.1f sigma=%.2f "
          "margin=%.2f" % (t["r_trig_mm"], t["base_gap_mm"], t["base_sigma_mm"],
                           t["base_margin_mm"]))
    print(fmt_sensitivity(t))
    print()
    print(fmt_budget(p.copy(r_trig_mm=t["r_trig_mm"])))
    print()
    rows = evaluate(p.copy(r_trig_mm=t["r_trig_mm"]))
    print(fmt_rollup(rows))
    print(rollup(rows))
