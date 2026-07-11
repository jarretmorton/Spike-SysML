"""
wall_stop_model.py  --  EXECUTABLE ANALYSIS MODEL for the max-speed wall-stop task.

This module is the computational twin of the tailored SysML model
(WallRunModel.sysml).  Every SysML parameter / relation / requirement maps 1:1
to a named Python variable / function here.  The two are two views of one model:
the SysML carries the formal satisfy/require argument, this carries the arithmetic.

It exposes the three faces the process requires:
    PREDICT  -> performance quantities (gap, stop distance, clearance, ...) from
               bound parameter values.
    EVALUATE -> pass/fail for each requirement given those values (the
               computational satisfy/require roll-up).
    SWEEP    -> vary a parameter over a stated range for sensitivity analysis.

Parameters are left FREE (priors, uncalibrated) until calibration binds them.
Units: millimetre (mm), second (s), mm/s, mm/s^2, degree (deg) unless noted.

--------------------------------------------------------------------------------
SysML <-> Python trace spine  (CMP requirement -> SysML attr -> Python name)
--------------------------------------------------------------------------------
  RotationToSpeed.k                 <-> Params.k_mm_per_deg      (diagnostic)
  DriveMotor.maxSpeed  (omega_max)  <-> Params.omega_max_dps     (diagnostic)
  Rover ground speed   (v)          <-> Params.v_max_mm_s        (PRIMARY, calibrated direct)
  StoppingDistance.tResponse        <-> t_response()  = t_chain + f_samp*refresh
  RoverLatency.tChain               <-> Params.t_chain_s
  DistanceSensor.refreshInterval    <-> Params.refresh_s
  StoppingDistance.a                <-> Params.a_decel_mm_s2
  StoppingDistance.margin           <-> margin_frame() = c_offset + g_target
  (measured stop distance)          <-> d_stop_const()          (direct-cal overrides formula)
  finalClearance (bumper->wall)     <-> gap_nominal()
  contactMargin                     <-> 0 (hard floor); no-contact uses k_z*sigma protection
  combined sensor->bumper offset    <-> Params.c_offset_mm      (operator ground truth)
  run-to-run stop SD                <-> Params.sigma_brake_mm
  sample-quantisation SD            <-> sigma_quant()
  reading noise SD                  <-> Params.sigma_meas_mm
  offset-calibration SD             <-> Params.sigma_offset_mm
  total 1-sigma                     <-> sigma_total()
  safety multiplier (k-sigma)       <-> Params.k_z
  heading drift over run            <-> Params.heading_drift_deg
  heading bound                     <-> Params.heading_bound_deg
  sensor valid range [min,max]      <-> Params.sensor_min_mm / sensor_max_mm
"""

from __future__ import annotations
from dataclasses import dataclass, replace, fields
import math


# =============================================================================
# PARAMETER BLOCK  (priors; FREE until calibration binds them)
# =============================================================================
@dataclass
class Params:
    # --- kinematics --------------------------------------------------------
    v_max_mm_s: float = 450.0        # PRIMARY ground speed at full throttle (calibrate direct)
    omega_max_dps: float = 900.0     # motor ceiling, deg/s   (diagnostic, RotationToSpeed)
    k_mm_per_deg: float = 0.50       # mm of ground per deg of motor (diagnostic; = v_max/omega)

    # --- stop dynamics -----------------------------------------------------
    a_decel_mm_s2: float = 3000.0    # effective braking deceleration (brake())
    t_chain_s: float = 0.030         # compute + BLE + actuation-command latency (RoverLatency.tChain)
    refresh_s: float = 0.030         # distance-sensor sample period / staleness bound
    f_samp: float = 0.5              # mean fraction of a refresh of sampling lag folded into reaction
    d_stop_direct_mm: float | None = None  # if set, DIRECT-calibrated stop distance overrides formula

    # --- absolute offset (operator ground truth) ---------------------------
    c_offset_mm: float = 30.0        # d_meas_rest - true bumper gap (bias + geometry + typ. yaw lead)

    # --- uncertainty contributors (size the margin, tenet A6) --------------
    sigma_brake_mm: float = 6.0      # run-to-run stopping-distance SD
    sigma_meas_mm: float = 2.0       # sensor reading noise SD on d_meas_rest
    sigma_offset_mm: float = 2.0     # residual SD in c_offset after operator measurement
    q_proj: float = 1.0              # quantisation-retention factor (1.0 raw threshold; <1 if velocity-projected)

    # --- design knobs ------------------------------------------------------
    k_z: float = 3.0                 # k-sigma no-contact protection (aim gap = k_z * sigma_total)

    # --- straightness ------------------------------------------------------
    heading_drift_deg: float = 3.0   # expected |yaw| drift over the ~1 m approach
    heading_bound_deg: float = 6.0   # allowable drift bound (SYS-5)

    # --- sensor valid range ------------------------------------------------
    sensor_min_mm: float = 40.0      # below this the ranger is unreliable
    sensor_max_mm: float = 2000.0    # ranger ceiling

    # --- fixed task geometry ----------------------------------------------
    start_distance_mm: float = 1000.0  # marked start line to wall (operator-held constant)


# =============================================================================
# RELATION TEMPLATES  (reproduced expressions from RelationTemplates, bound here)
# =============================================================================
def rotation_to_speed(omega_dps: float, k_mm_per_deg: float) -> float:
    """RelationTemplates::RotationToSpeed :  v = motorSpeed * k   (deg/s * mm/deg)."""
    return omega_dps * k_mm_per_deg


def t_response(p: Params) -> float:
    """tResponse = latency chain + mean sampling lag (StoppingDistance.tResponse)."""
    return p.t_chain_s + p.f_samp * p.refresh_s


def stopping_distance_formula(v: float, tR: float, a: float, margin: float) -> float:
    """RelationTemplates::StoppingDistance : d = v*tR + v^2/(2a) + margin."""
    return v * tR + v * v / (2.0 * a) + margin


def max_speed_from_budget(tR: float, a: float, budget: float, margin: float) -> float:
    """RelationTemplates::MaxSpeedFromBudget : positive root; feasibility cross-check."""
    disc = a * a * tR * tR + 2.0 * a * (budget - margin)
    if disc < 0:
        return float("nan")
    return -a * tR + math.sqrt(disc)


# =============================================================================
# DERIVED QUANTITIES
# =============================================================================
def d_stop_const(p: Params) -> float:
    """Measured-frame stopping distance at v_max: reaction + braking (no margin).

    Direct-calibrated value (telemetry difference, additive-bias-free) takes
    precedence over the formula once bound; the formula is the cross-check.
    """
    if p.d_stop_direct_mm is not None:
        return p.d_stop_direct_mm
    return p.v_max_mm_s * t_response(p) + p.v_max_mm_s ** 2 / (2.0 * p.a_decel_mm_s2)


def sigma_quant(p: Params) -> float:
    """Trigger-sample quantisation SD = q_proj * v_max * refresh / sqrt(12)."""
    return p.q_proj * p.v_max_mm_s * p.refresh_s / math.sqrt(12.0)


def sigma_total(p: Params) -> float:
    """RSS of independent 1-sigma contributors (tenet A6)."""
    return math.sqrt(
        p.sigma_brake_mm ** 2
        + sigma_quant(p) ** 2
        + p.sigma_meas_mm ** 2
        + p.sigma_offset_mm ** 2
    )


def g_target(p: Params) -> float:
    """Aim-point bumper gap = k_z * sigma_total  (smallest gap meeting no-contact confidence)."""
    return p.k_z * sigma_total(p)


def margin_frame(p: Params) -> float:
    """StoppingDistance.margin operand = sensor-frame rest clearance = c_offset + g_target."""
    return p.c_offset_mm + g_target(p)


def trigger_threshold(p: Params) -> float:
    """Measured-distance threshold D_thr at which we command brake.

    D_thr = d_stop_const + c_offset + g_target  (== StoppingDistance with margin=margin_frame).
    """
    return d_stop_const(p) + p.c_offset_mm + g_target(p)


def d_meas_rest(p: Params, d_thr: float | None = None) -> float:
    """Predicted measured distance at rest = D_thr - d_stop_const."""
    if d_thr is None:
        d_thr = trigger_threshold(p)
    return d_thr - d_stop_const(p)


def gap_nominal(p: Params, d_thr: float | None = None) -> float:
    """Predicted true bumper->wall gap at rest = d_meas_rest - c_offset."""
    return d_meas_rest(p, d_thr) - p.c_offset_mm


def contact_probability(p: Params, d_thr: float | None = None) -> float:
    """P(gap < 0) under a Gaussian error of SD sigma_total about gap_nominal."""
    g = gap_nominal(p, d_thr)
    s = sigma_total(p)
    if s <= 0:
        return 0.0 if g > 0 else 1.0
    # standard normal CDF via erf
    return 0.5 * (1.0 + math.erf((0.0 - g) / (s * math.sqrt(2.0))))


# =============================================================================
# PREDICT
# =============================================================================
def predict(p: Params, d_thr: float | None = None) -> dict:
    """Compute the performance quantities from bound parameter values."""
    if d_thr is None:
        d_thr = trigger_threshold(p)
    v = p.v_max_mm_s
    dsc = d_stop_const(p)
    react = v * t_response(p)
    brake = v * v / (2.0 * p.a_decel_mm_s2)
    return {
        "v_max_mm_s": v,
        "t_response_s": t_response(p),
        "reaction_dist_mm": react,
        "braking_dist_mm": brake,
        "d_stop_const_mm": dsc,
        "c_offset_mm": p.c_offset_mm,
        "sigma_quant_mm": sigma_quant(p),
        "sigma_total_mm": sigma_total(p),
        "k_z": p.k_z,
        "g_target_mm": g_target(p),
        "D_thr_mm": d_thr,
        "d_meas_rest_mm": d_meas_rest(p, d_thr),
        "gap_nominal_mm": gap_nominal(p, d_thr),
        "gap_worstcase_mm": gap_nominal(p, d_thr) - p.k_z * sigma_total(p),
        "contact_prob_per_run": contact_probability(p, d_thr),
        "contact_prob_5runs": 1.0 - (1.0 - contact_probability(p, d_thr)) ** 5,
        # feasibility cross-check from the inverse relation
        "vmax_budget_check_mm_s": max_speed_from_budget(
            t_response(p), p.a_decel_mm_s2, d_thr, margin_frame(p)
        ),
    }


# =============================================================================
# EVALUATE  (computational satisfy/require roll-up; mirrors the SysML tree)
# =============================================================================
def evaluate(p: Params, d_thr: float | None = None) -> dict:
    """Return pass/fail for each requirement given the bound values.

    Keys match the requirements-spec IDs.  Each value is (ok, detail).
    """
    if d_thr is None:
        d_thr = trigger_threshold(p)
    pr = predict(p, d_thr)
    results: dict[str, tuple[bool, str]] = {}

    # SYS-1 / CMP: no contact with k_z-sigma protection  (LowerBound: gap >= k_z*sigma)
    ok = pr["gap_nominal_mm"] >= p.k_z * pr["sigma_total_mm"] - 1e-9
    results["SYS-1_NoContact"] = (
        ok, f"gap_nom {pr['gap_nominal_mm']:.1f} >= k_z*sigma {p.k_z*pr['sigma_total_mm']:.1f} mm"
    )

    # SYS-2M / OBJ margin bridge: aim gap == k_z*sigma_total (by construction)
    ok = abs(pr["g_target_mm"] - p.k_z * pr["sigma_total_mm"]) < 1e-6
    results["SYS-2M_MarginBridge"] = (
        ok, f"g_target {pr['g_target_mm']:.1f} == k_z*sigma {p.k_z*pr['sigma_total_mm']:.1f} mm"
    )

    # SYS-3 max speed: achieved ground speed == omega_max*k ceiling (LowerBound)
    v_ceiling = rotation_to_speed(p.omega_max_dps, p.k_mm_per_deg)
    ok = pr["v_max_mm_s"] >= v_ceiling - 1e-6
    results["SYS-3_MaxSpeed"] = (
        ok, f"v_max {pr['v_max_mm_s']:.0f} >= ceiling {v_ceiling:.0f} mm/s"
    )

    # SYS-4 complete stop: a finite braking distance exists (rover reaches v=0)
    ok = math.isfinite(pr["braking_dist_mm"]) and pr["braking_dist_mm"] >= 0.0
    results["SYS-4_CompleteStop"] = (ok, f"braking_dist {pr['braking_dist_mm']:.1f} mm, v_rest=0")

    # SYS-5 straight: heading drift <= bound  (UpperBound)
    ok = p.heading_drift_deg <= p.heading_bound_deg + 1e-9
    results["SYS-5_Straight"] = (
        ok, f"drift {p.heading_drift_deg:.1f} <= bound {p.heading_bound_deg:.1f} deg"
    )

    # SYS-6 feasibility: sensor_min <= D_thr <= sensor_max  (trigger inside valid range)
    ok = p.sensor_min_mm <= d_thr <= p.sensor_max_mm
    results["SYS-6_TriggerInRange"] = (
        ok, f"{p.sensor_min_mm:.0f} <= D_thr {d_thr:.1f} <= {p.sensor_max_mm:.0f} mm"
    )

    # SYS-7 feasibility: stop fits inside the start-line budget (can't need >start_distance)
    ok = d_thr <= p.start_distance_mm
    results["SYS-7_FitsRunway"] = (
        ok, f"D_thr {d_thr:.1f} <= start {p.start_distance_mm:.0f} mm"
    )

    results["_ALL_PASS"] = (all(v[0] for k, v in results.items()), "roll-up")
    return results


# =============================================================================
# SWEEP  (sensitivity analysis engine)
# =============================================================================
def sweep(base: Params, field_name: str, lo: float, hi: float, n: int = 21):
    """Vary one parameter lo..hi, holding the DESIGN threshold at the base value.

    Returns list of (value, gap_true, margin_to_contact, contact_prob).
      gap_true       = realised bumper gap if the parameter's TRUE value is `value`
                       while the trigger threshold was set from the base priors.
      margin         = gap_true - k_z*sigma_total(perturbed)
    This isolates leverage x prior-uncertainty for each parameter.
    """
    d_thr_design = trigger_threshold(base)   # threshold locked from base priors
    out = []
    for i in range(n):
        val = lo + (hi - lo) * i / (n - 1)
        p = replace(base, **{field_name: val})
        g = gap_nominal(p, d_thr_design)          # true gap with design threshold
        m = g - p.k_z * sigma_total(p)
        cp = contact_probability(p, d_thr_design)
        out.append((val, g, m, cp))
    return out


def sensitivity_row(base: Params, field_name: str, lo: float, hi: float):
    """One row of the GATE-A sensitivity table."""
    s = sweep(base, field_name, lo, hi, n=21)
    gaps = [r[1] for r in s]
    margins = [r[2] for r in s]
    gap_swing = max(gaps) - min(gaps)
    margin_swing = max(margins) - min(margins)
    return {
        "param": field_name,
        "range": (lo, hi),
        "gap_swing_mm": gap_swing,
        "margin_swing_mm": margin_swing,
    }


# =============================================================================
# __main__  : print nominal prediction, requirement roll-up, sensitivity table
# =============================================================================
if __name__ == "__main__":
    base = Params()

    print("=" * 78)
    print("NOMINAL PREDICTION  (central priors, uncalibrated)")
    print("=" * 78)
    pr = predict(base)
    for k, v in pr.items():
        print(f"  {k:24s} = {v:10.3f}")

    print()
    print("=" * 78)
    print("REQUIREMENT ROLL-UP  (EVALUATE at nominal)")
    print("=" * 78)
    ev = evaluate(base)
    for k, (ok, detail) in ev.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {k:22s} {detail}")

    print()
    print("=" * 78)
    print("SENSITIVITY TABLE  (SWEEP each prior; threshold locked at base)")
    print("=" * 78)
    # (param, lo, hi, tier, note)  -- priors stated here as the review input
    plan = [
        ("c_offset_mm",     -20.0,   80.0, "none-onboard (needs operator)", "absolute bumper offset"),
        ("sigma_brake_mm",    2.0,   15.0, "onboard multi-stop",           "braking repeatability"),
        ("refresh_s",         0.010,  0.060,"onboard (detect step timing)", "sensor staleness -> sigma_quant"),
        ("v_max_mm_s",      300.0,  600.0, "onboard direct (US slope)",    "ground speed"),
        ("a_decel_mm_s2",  1500.0, 5000.0, "onboard (US diff + IMU accel)","deceleration"),
        ("t_chain_s",         0.010,  0.050,"onboard (trigger->decel lag)", "command latency"),
        ("sigma_offset_mm",   1.0,    5.0,  "set by operator precision",    "offset cal SD"),
        ("sigma_meas_mm",     1.0,    5.0,  "onboard (rest reading spread)","reading noise"),
        ("heading_drift_deg", 0.0,    8.0,  "onboard (IMU yaw)",            "straightness"),
    ]
    print(f"  {'parameter':16s} {'assumed range':>20s} {'gap swing':>11s} {'margin swing':>13s}  tier")
    print("  " + "-" * 92)
    rows = []
    for name, lo, hi, tier, note in plan:
        r = sensitivity_row(base, name, lo, hi)
        rows.append((r, tier, note))
        rng = f"[{lo:g}, {hi:g}]"
        print(f"  {name:16s} {rng:>20s} {r['gap_swing_mm']:>9.1f}mm {r['margin_swing_mm']:>11.1f}mm  {tier}")

    print()
    print("  Ranked by max(|gap swing|, |margin swing|):")
    rank = sorted(rows, key=lambda t: max(t[0]["gap_swing_mm"], abs(t[0]["margin_swing_mm"])), reverse=True)
    for i, (r, tier, note) in enumerate(rank, 1):
        lev = max(r["gap_swing_mm"], abs(r["margin_swing_mm"]))
        print(f"    {i}. {r['param']:16s} leverage {lev:6.1f} mm   [{tier}]  {note}")
