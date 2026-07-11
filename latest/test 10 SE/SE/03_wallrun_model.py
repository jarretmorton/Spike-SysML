"""
wallrun_model.py -- EXECUTABLE ANALYSIS MODEL for the Wall-Approach task.

This module is the computational view of the SysML `WallRun` model. Every
parameter / relation / requirement constraint in the SysML maps 1:1 to a named
Python symbol here (see the TRACE SPINE comments). The SysML carries the formal
satisfy/require argument; this Python carries the arithmetic. They must agree.

Standard library only.

Three public entry points, per the process:
  PREDICT  -> predict(params, cfg)   : performance quantities (gap, clearance,
                                        stop distance, final reading, ...).
  EVALUATE -> evaluate(params, cfg)  : pass/fail per requirement (the
                                        computational satisfy/require roll-up).
  SWEEP    -> sweep(params, ...)     : vary a parameter over a range for the
                                        sensitivity analysis.

Parameters are UNCALIBRATED (value=None) until calibration binds them. Priors
(assumed ranges) live in PRIORS and are used only by the sensitivity sweep and
for the GATE-B margin when a higher-tier value has not yet been bound.

Sign / frame conventions:
  * Distances in millimetres, speeds in mm/s, accelerations in mm/s^2,
    times in seconds, angles in degrees.
  * Wall is ahead. "gap"/"clearance" = TRUE distance from rover front face to
    wall at the full stop (>0 means no contact).
  * Ultrasonic reading model: reading = true_distance + sensorBias   (constant
    offset over the operating band; bias>0 => sensor over-reads => rover is
    CLOSER than it thinks => the dangerous sign).
"""

from __future__ import annotations
from dataclasses import dataclass, field, replace
from typing import Optional, Dict, Tuple, List
import math


# ---------------------------------------------------------------------------
# TRACE SPINE:  SysML attribute  <->  Python field
# ---------------------------------------------------------------------------
#   RoverCommon.RoverLatency.tChain        -> t_chain          (s)
#   DistanceSensor.refreshInterval         -> refresh          (s)
#   DistanceSensor.range (min valid)       -> ranger_floor     (mm)
#   DriveMotor.maxSpeed  (via RotationToSpeed: v = maxSpeed*k) -> v_cruise (mm/s)
#   RelationTemplates.RotationToSpeed.k    -> k_rot            (mm/rad)   [carried]
#   RelationTemplates.RotationToSpeed.motorSpeed -> omega_max  (rad/s)   [carried]
#   StoppingDistance.a                     -> a_decel          (mm/s^2)
#   StoppingDistance.tResponse             -> t_response       (s) = t_chain + sample latency
#   StoppingDistance.margin                -> safety_margin    (mm)  (derived, SYS-6)
#   WallRover.sensorBias                   -> sensor_bias      (mm)
#   WallRover.dTrig                        -> d_trig           (mm, reading units)
#   run-to-run stopping variability        -> sigma_run        (mm)  (model-completion)
#   confidence multiplier (A1/A6)          -> k_sigma          (-)
# ---------------------------------------------------------------------------


@dataclass
class Params:
    """Bound model parameters. None == UNCALIBRATED (A3: not zeroed)."""
    # --- kinematics / dynamics (composite operating-point quantities) ---
    v_cruise: Optional[float] = None      # mm/s   ground speed at max command
    a_decel: Optional[float] = None       # mm/s^2 deceleration under brake()
    t_response: Optional[float] = None    # s      reading-cross -> decel onset
    # --- decomposition carriers (for cross-check only) ---
    t_chain: Optional[float] = None       # s      platform latency chain
    omega_max: Optional[float] = None     # rad/s  motor max
    k_rot: Optional[float] = None         # mm/rad rotation->ground const
    # --- ranger channel ---
    refresh: Optional[float] = None       # s      ultrasonic sample period
    ranger_floor: Optional[float] = None  # mm     min valid reading
    sensor_bias: Optional[float] = None   # mm     reading = true + bias
    # --- run-to-run variability & assurance ---
    sigma_run: Optional[float] = None     # mm     run-to-run stop-distance sigma
    sigma_pred: float = 2.0               # mm     model/calibration residual (prior)
    sigma_bias_meas: float = 3.0          # mm     operator-measurement sigma
    k_sigma: float = 3.0                  # -      consequence-scaled (A1)

    def bound(self, name: str) -> float:
        v = getattr(self, name)
        if v is None:
            raise ValueError(f"parameter '{name}' is UNCALIBRATED (None)")
        return v


@dataclass
class Config:
    """Operating configuration for a run (the thing we choose / command)."""
    d_trig: float                          # mm, reading units (programmed threshold)
    commanded_speed: float                 # mm/s commanded (should equal v_max_rated)
    v_max_rated: float                     # mm/s achievable ceiling
    heading_drift: float = 0.0             # deg, |max heading excursion| during approach
    heading_tol: float = 3.0               # deg, allowed drift (SYS-5 target, TBD)
    final_speed: float = 0.0               # mm/s at rest (SYS-3; should be 0)
    contact_margin: float = 0.0            # mm, no-contact target floor (SYS-1)
    feas_margin: float = 10.0              # mm, ranger-floor feasibility guard (CMP-2)


# Priors (assumed ranges) -- STATE OF KNOWLEDGE INPUT TO REVIEW.
# (lo, hi, nominal, knowledge_tier)   tiers: 'datasheet/physics', 'weak', 'unknown'
PRIORS: Dict[str, Tuple[float, float, float, str]] = {
    "v_cruise":     (250.0, 500.0, 380.0, "physics (motor+wheel geom)"),
    "a_decel":      (800.0, 3000.0, 1600.0, "physics (brake() range)"),
    "t_response":   (0.030, 0.150, 0.070, "weak (loop+sample staleness)"),
    "refresh":      (0.020, 0.060, 0.040, "datasheet (LEGO ultrasonic)"),
    "sensor_bias":  (-20.0, 20.0, 0.0,    "unknown (no onboard absolute ref)"),
    "ranger_floor": (20.0, 60.0, 40.0,    "datasheet (ultrasonic min range)"),
    "sigma_run":    (3.0, 15.0, 8.0,      "weak (no repeats yet)"),
}


def nominal_params() -> Params:
    return Params(
        v_cruise=PRIORS["v_cruise"][2],
        a_decel=PRIORS["a_decel"][2],
        t_response=PRIORS["t_response"][2],
        refresh=PRIORS["refresh"][2],
        sensor_bias=PRIORS["sensor_bias"][2],
        ranger_floor=PRIORS["ranger_floor"][2],
        sigma_run=PRIORS["sigma_run"][2],
    )


# ---------------------------------------------------------------------------
# Core relations (REPRODUCED from RelationTemplates against bound parameters,
# per the skeleton's validation note -- no calc invocation).
# ---------------------------------------------------------------------------

def rotation_to_speed(omega_max: float, k_rot: float) -> float:
    """RelationTemplates.RotationToSpeed:  v = motorSpeed * k."""
    return omega_max * k_rot


def dynamic_stop_distance(v: float, t_response: float, a: float) -> float:
    """StoppingDistance MINUS the human margin term:
       D_dyn = v*tResponse + v^2/(2a).  (margin added separately as SYS-6.)"""
    return v * t_response + v ** 2 / (2.0 * a)


def sigma_trigger(v: float, refresh: float) -> float:
    """Trigger-crossing quantisation: the wall is crossed somewhere inside one
       refresh interval -> uniform over [0, v*refresh], sigma = range/sqrt(12)."""
    return (v * refresh) / math.sqrt(12.0)


def safety_margin(p: Params, bias_sigma: Optional[float] = None) -> Tuple[float, Dict[str, float]]:
    """SYS-6 derived margin (A6): RSS of independent uncertainty contributors,
       scaled by k_sigma. If bias_sigma is None, use the prior half-range as the
       (unanchored) bias uncertainty; after the operating-point anchor, pass the
       measurement sigma instead."""
    v = p.bound("v_cruise")
    s_trig = sigma_trigger(v, p.bound("refresh"))
    s_run = p.bound("sigma_run")
    s_pred = p.sigma_pred
    if bias_sigma is None:
        lo, hi, _, _ = PRIORS["sensor_bias"]
        s_bias = (hi - lo) / 2.0 / math.sqrt(3.0)   # uniform prior -> sigma
    else:
        s_bias = bias_sigma
    rss = math.sqrt(s_trig ** 2 + s_run ** 2 + s_pred ** 2 + s_bias ** 2)
    M = p.k_sigma * rss
    return M, {"sigma_trig": s_trig, "sigma_run": s_run,
               "sigma_pred": s_pred, "sigma_bias": s_bias, "rss": rss}


# ---------------------------------------------------------------------------
# PREDICT
# ---------------------------------------------------------------------------

def predict(p: Params, cfg: Config, bias_sigma: Optional[float] = None) -> Dict[str, float]:
    v = p.bound("v_cruise")
    D_dyn = dynamic_stop_distance(v, p.bound("t_response"), p.bound("a_decel"))
    M, mparts = safety_margin(p, bias_sigma=bias_sigma)
    bias = p.bound("sensor_bias")

    # StoppingDistance (full, with margin) = distance at which trigger must fire
    stop_distance = D_dyn + M

    # Where we actually end up, given the programmed threshold d_trig:
    final_gap_true = cfg.d_trig - bias - D_dyn      # TRUE gap to wall
    final_clearance = final_gap_true                # alias (SYS-1 subject attr)
    final_reading = cfg.d_trig - D_dyn              # bias cancels in reading frame
    predicted_gap = final_gap_true                  # SYS-4 objective quantity

    # d_trig that would place the stop exactly at the margin (gap == M):
    d_trig_for_margin = D_dyn + bias + M

    return {
        "D_dyn": D_dyn,
        "D_react": v * p.bound("t_response"),
        "D_brake": v ** 2 / (2.0 * p.bound("a_decel")),
        "stop_distance": stop_distance,
        "safety_margin": M,
        "final_gap_true": final_gap_true,
        "final_clearance": final_clearance,
        "final_reading": final_reading,
        "predicted_gap": predicted_gap,
        "d_trig_for_margin": d_trig_for_margin,
        **{f"m_{k}": val for k, val in mparts.items()},
    }


def recommend_d_trig(p: Params, cfg: Config, target_gap: Optional[float] = None,
                     bias_sigma: Optional[float] = None) -> float:
    """Choose d_trig. Default target_gap = the safety margin M (closest stop that
       still satisfies SYS-6). d_trig = D_dyn + bias + target_gap."""
    v = p.bound("v_cruise")
    D_dyn = dynamic_stop_distance(v, p.bound("t_response"), p.bound("a_decel"))
    M, _ = safety_margin(p, bias_sigma=bias_sigma)
    g = M if target_gap is None else target_gap
    return D_dyn + p.bound("sensor_bias") + g


# ---------------------------------------------------------------------------
# EVALUATE  (computational satisfy/require roll-up)
# ---------------------------------------------------------------------------

def evaluate(p: Params, cfg: Config, bias_sigma: Optional[float] = None) -> Dict[str, dict]:
    pr = predict(p, cfg, bias_sigma=bias_sigma)
    R: Dict[str, dict] = {}

    # SYS-1  No contact:            finalClearance >= contactMargin   (LowerBound)
    R["SYS-1"] = _lb("No contact", pr["final_clearance"], cfg.contact_margin, "mm")
    # SYS-2  Max speed:             commandedSpeed >= v_max_rated      (LowerBound)
    R["SYS-2"] = _lb("Max approach speed", cfg.commanded_speed, cfg.v_max_rated, "mm/s")
    # SYS-3  Complete stop:         finalSpeed <= 0                    (UpperBound)
    R["SYS-3"] = _ub("Complete stop", cfg.final_speed, 0.0, "mm/s")
    # SYS-5  Straight approach:     headingDrift <= headingTol         (UpperBound)
    R["SYS-5"] = _ub("Straight approach", cfg.heading_drift, cfg.heading_tol, "deg")
    # SYS-6  Margin floor:          predictedGap >= safetyMargin       (LowerBound)
    R["SYS-6"] = _lb("No-contact margin", pr["predicted_gap"], pr["safety_margin"], "mm")
    # CMP-2  Trigger feasibility:   d_trig >= rangerFloor + feasMargin (LowerBound)
    R["CMP-2"] = _lb("Trigger within ranger valid band",
                     cfg.d_trig, p.bound("ranger_floor") + cfg.feas_margin, "mm")

    R["_ALL_PASS"] = {"pass": all(v["pass"] for k, v in R.items() if k != "_ALL_PASS")}
    return R


def _lb(name, measured, target, unit):
    return {"name": name, "form": "measured >= target",
            "measured": measured, "target": target, "unit": unit,
            "pass": measured >= target, "slack": measured - target}


def _ub(name, measured, target, unit):
    return {"name": name, "form": "measured <= target",
            "measured": measured, "target": target, "unit": unit,
            "pass": measured <= target, "slack": target - measured}


# ---------------------------------------------------------------------------
# SWEEP  (sensitivity analysis)
# ---------------------------------------------------------------------------

def sweep_parameter(name: str, p: Params, cfg: Config, n: int = 9) -> Dict[str, float]:
    """Vary one parameter over its prior [lo,hi] with all others at nominal;
       report the resulting swing in the objective (final_gap_true) at FIXED
       d_trig, and the swing in the safety margin M. Also report local
       d(gap)/d(param)."""
    lo, hi, nom, tier = PRIORS[name]
    gaps: List[float] = []
    Ms: List[float] = []
    xs = [lo + (hi - lo) * i / (n - 1) for i in range(n)]
    for x in xs:
        pp = replace(p, **{name: x})
        pr = predict(pp, cfg)
        gaps.append(pr["final_gap_true"])
        Ms.append(pr["safety_margin"])
    gap_swing = max(gaps) - min(gaps)
    M_swing = max(Ms) - min(Ms)
    # local slope at nominal
    eps = (hi - lo) * 1e-3
    p_hi = predict(replace(p, **{name: nom + eps}), cfg)["final_gap_true"]
    p_lo = predict(replace(p, **{name: nom - eps}), cfg)["final_gap_true"]
    dgap = (p_hi - p_lo) / (2 * eps)
    return {"lo": lo, "hi": hi, "nominal": nom, "tier": tier,
            "gap_swing_mm": gap_swing, "margin_swing_mm": M_swing,
            "dgap_dparam": dgap}


def sensitivity_table(p: Params, cfg: Config) -> List[Tuple[str, Dict[str, float]]]:
    rows = [(name, sweep_parameter(name, p, cfg)) for name in PRIORS]
    # rank by the larger of the two leverage measures
    rows.sort(key=lambda r: max(r[1]["gap_swing_mm"], r[1]["margin_swing_mm"]),
              reverse=True)
    return rows


# ---------------------------------------------------------------------------
# Self-demonstration when run directly (free analysis, no hardware).
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    p = nominal_params()
    # reference operating config: d_trig at the nominal margin point
    Mnom, _ = safety_margin(p)
    D_dyn_nom = dynamic_stop_distance(p.v_cruise, p.t_response, p.a_decel)
    d_trig_ref = D_dyn_nom + p.sensor_bias + Mnom
    cfg = Config(d_trig=d_trig_ref, commanded_speed=p.v_cruise,
                 v_max_rated=p.v_cruise, heading_drift=1.0)

    print("=" * 74)
    print("PREDICT @ nominal priors, d_trig = %.1f mm" % d_trig_ref)
    print("=" * 74)
    pr = predict(p, cfg)
    for k in ["v_cruise->", "D_react", "D_brake", "D_dyn", "safety_margin",
              "stop_distance", "final_gap_true", "final_reading",
              "d_trig_for_margin"]:
        if k == "v_cruise->":
            print(f"  {'v_cruise':<20s} = {p.v_cruise:8.2f} mm/s")
            continue
        print(f"  {k:<20s} = {pr[k]:8.2f}")
    print("  margin parts (sigmas, mm):")
    for k in ["m_sigma_trig", "m_sigma_run", "m_sigma_pred", "m_sigma_bias", "m_rss"]:
        print(f"      {k:<16s} = {pr[k]:7.2f}")

    print()
    print("=" * 74)
    print("EVALUATE @ nominal (commanded == rated, heading 1 deg)")
    print("=" * 74)
    for rid, r in evaluate(p, cfg).items():
        if rid == "_ALL_PASS":
            print(f"  ALL PASS: {r['pass']}")
            continue
        print(f"  {rid}  {r['name']:<32s} {r['form']:<18s} "
              f"{r['measured']:8.2f} vs {r['target']:8.2f} {r['unit']:<4s} "
              f"-> {'PASS' if r['pass'] else 'FAIL'} (slack {r['slack']:+.2f})")

    print()
    print("=" * 74)
    print("SWEEP / SENSITIVITY  (ranked by leverage on gap or margin)")
    print("=" * 74)
    print(f"  {'param':<13s} {'range':<20s} {'gapSwing':>9s} {'Mswing':>8s} "
          f"{'dgap/dp':>10s}  tier")
    for name, s in sensitivity_table(p, cfg):
        rng = f"[{s['lo']:g}, {s['hi']:g}]"
        print(f"  {name:<13s} {rng:<20s} {s['gap_swing_mm']:9.1f} "
              f"{s['margin_swing_mm']:8.1f} {s['dgap_dparam']:10.3f}  {s['tier']}")
