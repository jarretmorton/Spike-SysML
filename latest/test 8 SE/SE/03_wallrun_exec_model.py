"""
wallrun_exec_model.py — EXECUTABLE ANALYSIS MODEL for the WallRun task.

The computational view of wallrun_model.sysml. Every SysML parameter/relation/
requirement maps 1:1 to a named variable/function here (unit convention: mm, s,
mm/s, mm/s^2, deg, deg/s). The SysML carries the formal satisfy/require argument;
this module carries the arithmetic. A mismatch between the SysML roll-up and
EVALUATE() is a defect to fix before a gate.

Exposes, per the process:
  (a) predict(...)  -> performance quantities (d_stop, clearance, sigma_G, M, ...)
  (b) evaluate(...) -> pass/fail per requirement (the computational satisfy/require)
  (c) sweep(...) / sensitivity_table(...) -> parameter sensitivity

Parameters are UNCALIBRATED (None) until calibration binds them (tenet A3: never
zero/eyeball a constant). PRIORS below are the ASSUMED ranges — an INPUT to review,
used only by the sensitivity sweep, never as calibrated values.

Standard library only.
"""
from __future__ import annotations
from dataclasses import dataclass, field, replace
from math import sqrt
from typing import Optional, Dict, Tuple, List, Callable

# ---------------------------------------------------------------------------
# PRIORS — assumed ranges for the sensitivity sweep (stated for review).
# (low, nominal, high). SPIKE Prime reasoning documented in the Calibration Plan.
# These are NOT calibrated values; they seed SWEEP only.
# ---------------------------------------------------------------------------
PRIORS: Dict[str, Tuple[float, float, float]] = {
    "v_max":            (390.0, 600.0, 850.0),   # mm/s   (motor 800-1100 deg/s x wheel 56-88 mm)
    "t_lat":            (0.020, 0.060, 0.120),   # s      (loop + BLE + actuation + sampling)
    "a_brake":          (1000.0, 2000.0, 4000.0),# mm/s^2 (passive brake decel)
    "c":                (-10.0, 15.0, 40.0),     # mm     (sensor face vs frontmost point)
    "sample_interval":  (0.020, 0.040, 0.060),   # s      (ultrasonic staleness)
    "sigma_S":          (1.0, 3.0, 6.0),         # mm     (single-reading 1-sigma noise)
}

def _prior_sigma(name: str) -> float:
    """Treat the assumed range as ~+/-2 sigma -> sigma = (high-low)/4."""
    lo, _, hi = PRIORS[name]
    return (hi - lo) / 4.0


@dataclass
class Params:
    # -- calibrated model parameters (None = UNCALIBRATED) --
    v_max: Optional[float] = None            # SysML vMax           [mm/s]
    t_lat: Optional[float] = None            # SysML tResponse      [s]
    a_brake: Optional[float] = None          # SysML aBrake         [mm/s^2]
    c: Optional[float] = None                # SysML sensorOffset   [mm]
    sample_interval: Optional[float] = None  # SysML sampleInterval [s]
    sigma_S: Optional[float] = None          # SysML rangeNoise     [mm]
    d_min: Optional[float] = None            # SysML dMin           [mm]
    d_max: Optional[float] = None            # SysML dMax           [mm]

    # -- 1-sigma CALIBRATION uncertainties on the above (None = unknown) --
    sig_v: Optional[float] = None
    sig_t: Optional[float] = None
    sig_a: Optional[float] = None
    sig_c: Optional[float] = None

    # -- design / requirement parameters --
    d_trig: Optional[float] = None           # SysML dTrig            [mm] (design; often solved)
    k: float = 3.0                           # confidence factor for M = k*sigma_G
    contact_margin: float = 0.0              # SysML contactMargin   [mm] (definitional floor)
    stop_speed_tol: float = 5.0              # SysML stopSpeedTol    [mm/s] (~0)
    theta_max: Optional[float] = None        # SysML maxHeadingDrift [deg]
    sigma_S_max: Optional[float] = None      # SysML rangeNoiseMax   [mm]
    ab_tol: Optional[float] = None           # SysML abTol           [mm]
    estimate_error_tol: Optional[float] = None  # SysML estimateErrorTol [mm]

    # -- drivetrain aggregate (SYS-4) --
    commanded_speed: Optional[float] = None  # SysML commandedSpeed [deg/s]
    max_speed: Optional[float] = None        # SysML maxSpeed       [deg/s] (ceiling)

    # -- run-realised measurements (None until a run supplies them) --
    m_final_clearance: Optional[float] = None
    m_heading_drift: Optional[float] = None
    m_final_speed: Optional[float] = None
    m_drive_residual_speed: Optional[float] = None
    m_ab_agreement: Optional[float] = None
    m_estimate_error: Optional[float] = None


def _require(p: Params, *names: str) -> None:
    missing = [n for n in names if getattr(p, n) is None]
    if missing:
        raise ValueError(f"UNCALIBRATED parameter(s): {missing} — bind at calibration before use.")


# ===========================================================================
# (a) PREDICT — reproduces RelationTemplates::StoppingDistance against bound params
# ===========================================================================
def d_stop(p: Params) -> float:
    """D_stop = v*t_lat + v^2/(2*a)  (reaction + braking travel from trigger)."""
    _require(p, "v_max", "t_lat", "a_brake")
    return p.v_max * p.t_lat + p.v_max ** 2 / (2.0 * p.a_brake)

def reaction_distance(p: Params) -> float:
    _require(p, "v_max", "t_lat"); return p.v_max * p.t_lat

def braking_distance(p: Params) -> float:
    _require(p, "v_max", "a_brake"); return p.v_max ** 2 / (2.0 * p.a_brake)

def sigma_G(p: Params) -> Dict[str, float]:
    """RSS clearance uncertainty (tenet A6): prediction + measurement + run-to-run.
    Returns the total and each contributor (mm)."""
    _require(p, "v_max", "t_lat", "a_brake",
             "sig_v", "sig_t", "sig_a", "sig_c", "sample_interval", "sigma_S")
    dGdv = -(p.t_lat + p.v_max / p.a_brake)          # d(clearance)/d(v_max)
    dGdt = -p.v_max                                  # d/d(t_lat)
    dGda = p.v_max ** 2 / (2.0 * p.a_brake ** 2)     # d/d(a_brake)
    c_v = abs(dGdv) * p.sig_v
    c_t = abs(dGdt) * p.sig_t
    c_a = abs(dGda) * p.sig_a
    c_c = p.sig_c                                    # d/d(c) = -1
    c_quant = p.v_max * p.sample_interval / sqrt(12.0)   # trigger sample quantisation
    c_noise = p.sigma_S                              # noisy reading trips trigger +/- sigma_S
    total = sqrt(c_v**2 + c_t**2 + c_a**2 + c_c**2 + c_quant**2 + c_noise**2)
    return {"total": total, "from_v": c_v, "from_t": c_t, "from_a": c_a,
            "from_c": c_c, "from_quant": c_quant, "from_noise": c_noise}

def required_margin(p: Params) -> float:
    """M = k * sigma_G  (SysML requiredMargin)."""
    return p.k * sigma_G(p)["total"]

def trigger_for_clearance(p: Params, g_target: float) -> float:
    """Sensor-frame trigger threshold to leave bumper clearance g_target:
       d_trig = g_target + c + D_stop."""
    _require(p, "c")
    return g_target + p.c + d_stop(p)

def predict(p: Params, g_target: Optional[float] = None) -> Dict[str, float]:
    """Compute performance quantities from bound parameters.
    If g_target is None, use M (the minimum-gap operating point). If p.d_trig is
    set, predicted clearance is derived from it; otherwise d_trig is solved from
    g_target."""
    sg = sigma_G(p)
    M = p.k * sg["total"]
    if g_target is None:
        g_target = M
    if p.d_trig is not None:
        d_trig = p.d_trig
        pred_clear = (d_trig - p.c) - d_stop(p)       # SysML predictedClearance
    else:
        d_trig = trigger_for_clearance(p, g_target)
        pred_clear = g_target
    final_sensor_reading = pred_clear + p.c           # S at rest
    channel_valid = (p.d_min is not None and p.d_max is not None
                     and p.d_min <= final_sensor_reading <= p.d_max)
    return {
        "reaction_distance": reaction_distance(p),
        "braking_distance": braking_distance(p),
        "d_stop": d_stop(p),
        "d_trig": d_trig,
        "g_target": g_target,
        "predicted_clearance": pred_clear,
        "final_sensor_reading": final_sensor_reading,
        "channel_valid_at_rest": channel_valid,
        "sigma_G": sg["total"],
        "required_margin_M": M,
        "sigma_contribs": sg,
    }


# ===========================================================================
# (b) EVALUATE — computational satisfy/require roll-up (mirrors the SysML)
# ===========================================================================
def _lb(measured, target):  # LowerBoundRequirement: measured >= target
    return (measured is not None and target is not None and measured >= target)
def _ub(measured, target):  # UpperBoundRequirement: measured <= target
    return (measured is not None and target is not None and measured <= target)

def evaluate(p: Params, g_target: Optional[float] = None) -> Dict[str, Dict]:
    """Return {req_id: {measured, target, op, pass}} for the evaluable HARD set,
    plus an overall roll-up. Pre-run uses predicted proxies; post-run overrides
    with any run-realised measurements present on p. Objective/functional-parent
    requirements (SYS-2,5; FUN-1,2,3,5; CMP-5) are excluded by design (graded/
    realised-by-children), exactly as the SysML notes."""
    pr = predict(p, g_target)
    # measured proxies: realised measurement if present, else prediction
    final_clear = p.m_final_clearance if p.m_final_clearance is not None else pr["predicted_clearance"]
    heading = p.m_heading_drift if p.m_heading_drift is not None else 0.0
    final_spd = p.m_final_speed if p.m_final_speed is not None else 0.0
    resid_spd = p.m_drive_residual_speed if p.m_drive_residual_speed is not None else 0.0
    ab = p.m_ab_agreement if p.m_ab_agreement is not None else 0.0
    est_err = p.m_estimate_error if p.m_estimate_error is not None else 0.0

    rows = {
        "SYS-1_NoContact":       ("LB", final_clear, p.contact_margin),
        "SYS-3_ClearanceMargin": ("LB", pr["predicted_clearance"], pr["required_margin_M"]),
        "SYS-4_MaxApproachSpeed":("LB", p.commanded_speed, p.max_speed),
        "SYS-6_StraightApproach":("UB", heading, p.theta_max),
        "SYS-7_FullStop":        ("UB", final_spd, p.stop_speed_tol),
        "FUN-4_GapEstimation":   ("UB", est_err, p.estimate_error_tol),
        "CMP-1a_LeftMotorMax":   ("LB", p.commanded_speed, p.max_speed),
        "CMP-1b_RightMotorMax":  ("LB", p.commanded_speed, p.max_speed),
        "CMP-1c_MotorBrakeStop": ("UB", resid_spd, p.stop_speed_tol),
        "CMP-2a_FwdUltrasonicA": ("UB", p.sigma_S, p.sigma_S_max),
        "CMP-2b_FwdUltrasonicB": ("UB", ab, p.ab_tol),
    }
    out: Dict[str, Dict] = {}
    all_pass = True
    for rid, (op, m, t) in rows.items():
        ok = _lb(m, t) if op == "LB" else _ub(m, t)
        out[rid] = {"measured": m, "target": t, "op": op, "pass": bool(ok)}
        all_pass = all_pass and bool(ok)
    out["ROLLUP"] = {"all_hard_pass": all_pass}
    return out


# ===========================================================================
# (c) SWEEP / sensitivity
# ===========================================================================
def sweep(param: str, base: Params, n: int = 9,
          rng: Optional[Tuple[float, float]] = None) -> List[Dict]:
    """Vary one parameter across its assumed range; recompute PREDICT."""
    lo, nom, hi = PRIORS.get(param, (None, getattr(base, param, None), None))
    if rng is not None:
        lo, hi = rng
    if lo is None or hi is None:
        raise ValueError(f"No range for '{param}'.")
    out = []
    for i in range(n):
        v = lo + (hi - lo) * i / (n - 1)
        pr = predict(replace(base, **{param: v}))
        out.append({param: v, "predicted_clearance": pr["predicted_clearance"],
                    "required_margin_M": pr["required_margin_M"],
                    "d_trig": pr["d_trig"]})
    return out

def sensitivity_table(base: Params) -> List[Dict]:
    """For each swept parameter: local dObjective/dparam at nominal, the objective
    swing over the assumed range (linearised), the prior-sigma contribution to the
    margin M, and the prior sigma. Feeds Calibration-Plan section 0."""
    _require(base, "v_max", "t_lat", "a_brake", "c", "sample_interval", "sigma_S")
    v, t, a = base.v_max, base.t_lat, base.a_brake
    partials: Dict[str, float] = {
        "v_max": -(t + v / a),
        "t_lat": -v,
        "a_brake": v ** 2 / (2.0 * a ** 2),
        "c": -1.0,
        "sample_interval": -v / sqrt(12.0),   # via quantisation term
        "sigma_S": -1.0,                       # via noise term (approx unit on clearance)
    }
    rows = []
    for name, (lo, nom, hi) in PRIORS.items():
        dpar = partials[name]
        obj_swing = abs(dpar) * (hi - lo)                 # ΔG across assumed range
        psig = _prior_sigma(name)
        margin_contrib_k = base.k * abs(dpar) * psig      # k * sigma-contribution to M
        rows.append({
            "parameter": name,
            "assumed_range": (lo, hi),
            "nominal": nom,
            "prior_sigma": psig,
            "dObjective_dparam": dpar,
            "objective_swing_over_range_mm": obj_swing,
            "margin_M_contribution_mm": margin_contrib_k,
        })
    rows.sort(key=lambda r: r["objective_swing_over_range_mm"], reverse=True)
    return rows


# ---------------------------------------------------------------------------
# Self-demo with PRIORS at nominal (free analysis; produces section-0 numbers).
# ---------------------------------------------------------------------------
def _nominal_params() -> Params:
    return Params(
        v_max=PRIORS["v_max"][1], t_lat=PRIORS["t_lat"][1], a_brake=PRIORS["a_brake"][1],
        c=PRIORS["c"][1], sample_interval=PRIORS["sample_interval"][1], sigma_S=PRIORS["sigma_S"][1],
        d_min=40.0, d_max=2000.0,
        sig_v=_prior_sigma("v_max"), sig_t=_prior_sigma("t_lat"),
        sig_a=_prior_sigma("a_brake"), sig_c=_prior_sigma("c"),
        k=3.0, theta_max=3.0, sigma_S_max=6.0, ab_tol=15.0, estimate_error_tol=10.0,
        commanded_speed=2000.0, max_speed=1000.0,   # commanded > ceiling (run() clamps)
    )

if __name__ == "__main__":
    p = _nominal_params()
    pr = predict(p)
    print("=== PREDICT @ priors-nominal (min-gap operating point) ===")
    for kk in ("reaction_distance", "braking_distance", "d_stop", "d_trig",
               "predicted_clearance", "final_sensor_reading", "channel_valid_at_rest",
               "sigma_G", "required_margin_M"):
        print(f"  {kk:26s} = {pr[kk]}")
    print("  sigma_G contributors (mm):")
    for kk, vv in pr["sigma_contribs"].items():
        print(f"    {kk:12s} {vv:8.2f}")
    print("\n=== SENSITIVITY TABLE (section 0 feed) ===")
    hdr = f"{'param':16s}{'range':22s}{'prior_sig':10s}{'dG/dp':10s}{'ΔG/range':10s}{'M-contrib(k)':12s}"
    print(hdr)
    for r in sensitivity_table(p):
        print(f"{r['parameter']:16s}{str(r['assumed_range']):22s}"
              f"{r['prior_sigma']:<10.3f}{r['dObjective_dparam']:<10.3f}"
              f"{r['objective_swing_over_range_mm']:<10.1f}{r['margin_M_contribution_mm']:<12.1f}")
    print("\n=== EVALUATE (pre-run, predicted proxies) ===")
    for rid, d in evaluate(p).items():
        print(f"  {rid:26s} {d}")
