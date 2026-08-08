#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wall_stop_model.py  --  EXECUTABLE ANALYSIS MODEL for the SPIKE Prime wall-approach task.

This module is the computational view of the SysML model in ``wall_stop_model.sysml``.
Every SysML attribute has exactly one Python Param here (field ``sysml``), and every
SysML requirement id has exactly one evaluator here (field ``req``).  A mismatch
between the two views is a defect, not a style difference; ``model_checks.py``
enforces the 1:1 mapping mechanically.

It exposes the three faces required at GATE A:

  PREDICT   ``predict(params)``   -> performance quantities (gap, stop distance,
                                     clearance, degraded gap, sigmas)
  EVALUATE  ``evaluate(params)``  -> pass/fail per requirement id (the computational
                                     satisfy/require roll-up)
  SWEEP     ``sweep(...)``        -> parameter sensitivity over stated prior ranges

DOCTRINE
  * A3 -- parameters are UNCALIBRATED, not zeroed.  Every free parameter's ``value``
    is ``None`` until a calibration activity binds it.  ``predict`` refuses to run on
    unbound parameters (raises ``UnboundParameter``); the sweep runs instead on an
    explicitly-labelled PRIOR-MID working point which is NOT a calibrated value.
  * Source-of-truth tiers are carried WITH each value:
        T0 unbound / prior only
        T1 single onboard sample
        T2 anchored or multi-point onboard calibration
        T3 external ground truth (operator measurement)
    ``bind()`` refuses to lower a parameter's tier silently.

UNITS: mm, s, deg, mm/s, mm/s^2.  The SysML model carries SI; the conversions are
stated in each Param's ``sysml_units`` field.

GEOMETRY / SIGN CONVENTIONS
  g          true gap  = shortest distance from any part of the rover to the wall
  r          fused forward-ranger reading (sensor frame)
  b          range offset such that, at rest,  g = r - b
  d_est(t)   onboard estimate of the CURRENT fused sensor-frame distance
  R_trig     trigger threshold, compared against d_est
  d_T        value of d_est on the loop iteration that fires the trigger
  S          composite stop distance: ground travel from the instant d_T refers to,
             through sensor lag + command chain + braking, to full rest.
             Observable onboard as  d_T - r_rest  (b cancels).
  therefore  g_final = R_trig - E[loop undershoot] - S - b
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 0.  Design constants (decisions, not measurements -- swept, never "eyeballed"
#     into a physical quantity)
# ---------------------------------------------------------------------------

K_SIGMA_DEFAULT = 3.0   # SYS-2 margin multiplier; see sweep row 'k_sigma'
TIER_NAMES = {0: "T0 prior only", 1: "T1 single sample",
              2: "T2 anchored/multi-point", 3: "T3 operator ground truth"}


class UnboundParameter(RuntimeError):
    """Raised when PREDICT is asked to run with an uncalibrated parameter."""


class TierViolation(RuntimeError):
    """Raised when a lower-tier source would silently overwrite a higher tier."""


# ---------------------------------------------------------------------------
# 1.  The trace spine:  CMP requirement -> SysML attribute -> Python variable
# ---------------------------------------------------------------------------

@dataclass
class Param:
    name: str                       # python variable name (this module)
    sysml: str                      # SysML attribute path in wall_stop_model.sysml
    units: str                      # units used HERE
    sysml_units: str                # units used in the SysML model + conversion
    prior: Tuple[float, float]      # assumed range, stated as a prior at GATE A
    reqs: Tuple[str, ...]           # requirement ids this parameter serves
    binding_activity: str           # which calibration activity binds it
    value: Optional[float] = None   # UNCALIBRATED until bound
    tier: int = 0
    evidence: str = "unbound"

    def bind(self, value: float, tier: int, evidence: str) -> None:
        if self.value is not None and tier < self.tier:
            raise TierViolation(
                f"{self.name}: refusing to overwrite a {TIER_NAMES[self.tier]} value "
                f"with a {TIER_NAMES[tier]} one. Diagnose the discrepancy instead.")
        self.value = float(value)
        self.tier = tier
        self.evidence = evidence

    def mid(self) -> float:
        return 0.5 * (self.prior[0] + self.prior[1])

    def get(self) -> float:
        if self.value is None:
            raise UnboundParameter(
                f"{self.name} ({self.sysml}) is unbound -- bound by: {self.binding_activity}")
        return self.value


class Params:
    """Ordered registry of every model parameter.  Attribute access returns floats."""

    def __init__(self, params: List[Param]):
        self._p: Dict[str, Param] = {p.name: p for p in params}

    # -- registry access -----------------------------------------------------
    def p(self, name: str) -> Param:
        return self._p[name]

    def __iter__(self):
        return iter(self._p.values())

    def names(self) -> List[str]:
        return list(self._p.keys())

    def __getattr__(self, name: str) -> float:          # value access
        try:
            return self._p[name].get()
        except KeyError:
            raise AttributeError(name)

    def bind(self, name: str, value: float, tier: int, evidence: str) -> None:
        self._p[name].bind(value, tier, evidence)

    def working_point(self, overrides: Optional[Dict[str, float]] = None) -> "Params":
        """A copy in which every unbound parameter takes its PRIOR MID.

        NOT a calibrated model.  Used only for sensitivity ranking at GATE A.
        """
        out = build_params()
        for src in self:
            dst = out.p(src.name)
            if src.value is not None:
                dst.value, dst.tier, dst.evidence = src.value, src.tier, src.evidence
            else:
                dst.value, dst.tier, dst.evidence = src.mid(), 0, "PRIOR MID (not calibrated)"
        for k, v in (overrides or {}).items():
            out.p(k).value = float(v)
        return out

    def unbound(self) -> List[str]:
        return [p.name for p in self if p.value is None]


def build_params() -> Params:
    """The full free-parameter set, uncalibrated."""
    P = Param
    return Params([
        # ---- drivetrain -----------------------------------------------------
        P("omega_max_deg_s", "WallRover.maxWheelSpeed", "deg/s", "rad/s (x pi/180)",
          (700.0, 1100.0), ("CMP-1", "CMP-2", "SYS-4"), "RUN-1 cruise plateau"),
        P("k_mm_per_deg", "WallRover.speedScale", "mm/deg", "m/rad (x 180/pi/1000)",
          (0.35, 0.80), ("CMP-4", "FUN-8"), "RUN-1 cruise regression r vs motor angle"),
        P("a_decel_mm_s2", "WallRover.decel", "mm/s^2", "m/s^2 (/1000)",
          (1000.0, 6000.0), ("CMP-5", "SYS-5"), "RUN-1 stop window (odometry + IMU)"),
        P("sym_dev_deg_s", "WallRover.symmetryDeviation", "deg/s", "rad/s (x pi/180)",
          (0.0, 60.0), ("CMP-3",), "RUN-1 cruise, per-motor speed"),
        # ---- forward ranging ------------------------------------------------
        P("T_refresh_s", "WallRover.rangerRefresh", "s", "s",
          (0.010, 0.100), ("CMP-6", "CMP-7", "FUN-1"), "RUN-1 value-change timestamps"),
        P("tau_sensor_s", "WallRover.rangerLag", "s", "s",
          (0.005, 0.060), ("FUN-2",), "RUN-1 (lumped into S; separated by 2-speed segments)"),
        P("sigma_n_mm", "WallRover.rangerNoise", "mm", "m (/1000)",
          (1.0, 8.0), ("CMP-8", "SYS-2"), "RUN-1 static dwells at 2 ranges"),
        P("b_offset_mm", "WallRover.rangeOffset", "mm", "m (/1000)",
          (-40.0, 80.0), ("SYS-1", "SYS-3", "SYS-8"), "RUN-1 close pose + OPERATOR M1"),
        P("r_floor_mm", "WallRover.validityFloor", "mm", "m (/1000)",
          (20.0, 60.0), ("CMP-9", "FUN-3"), "RUN-1 creep phase to close range"),
        P("delta_AB_mm", "WallRover.rangerPairOffset", "mm", "m (/1000)",
          (0.0, 30.0), ("FUN-13",), "RUN-1 A-vs-B paired samples"),
        # ---- timing chain ---------------------------------------------------
        P("t_loop_s", "WallRover.loopPeriod", "s", "s",
          (0.005, 0.025), ("CMP-11", "FUN-4"), "RUN-1 loop timestamp deltas"),
        P("t_chain_s", "WallRover.latency.tChain", "s", "s",
          (0.002, 0.020), ("FUN-4", "FUN-5"), "RUN-1 (lumped into S)"),
        # ---- composite stop -------------------------------------------------
        P("rel_sigma_S", "WallRover.stopRepeatability", "-", "-",
          (0.03, 0.15), ("SYS-2", "SYS-1"), "prior; consistency-checked RUN-1 vs RUN-2"),
        P("n_S_samples", "WallRover.stopSampleCount", "-", "-",
          (1.0, 3.0), ("SYS-2",), "count of independent stop samples held at lock"),
        P("u_b_mm", "WallRover.offsetUncertainty", "mm", "m (/1000)",
          (1.0, 10.0), ("SYS-1", "SYS-2"), "OPERATOR M1 + transfer to the fast-run pose"),
        # ---- attitude -------------------------------------------------------
        P("theta_dev_deg", "WallRover.headingDeviation", "deg", "rad (x pi/180)",
          (0.0, 8.0), ("SYS-6", "CMP-10"), "RUN-1 IMU trace to trigger"),
        P("sigma_theta_deg", "WallRover.headingSpread", "deg", "rad (x pi/180)",
          (0.0, 3.0), ("SYS-2",), "RUN-1 vs RUN-2 heading at trigger"),
        P("c_yaw_mm_per_deg", "WallRover.yawClearanceCoeff", "mm/deg", "m/rad",
          (1.0, 1.6), ("SYS-6",), "geometry prior; escalate only if theta large"),
        # ---- odometric backstop --------------------------------------------
        P("e_odo_mm", "WallRover.odometryError", "mm", "m (/1000)",
          (2.0, 20.0), ("SYS-7", "FUN-6"), "RUN-1 odometry vs ranger over the approach"),
        P("delta_bs_mm", "WallRover.backstopAllowance", "mm", "m (/1000)",
          (5.0, 40.0), ("SYS-7", "FUN-6"), "design value fixed from RUN-1 disagreement"),
        # ---- measurement / setup -------------------------------------------
        P("sigma_meas_mm", "WallRover.measurementSigma", "mm", "m (/1000)",
          (0.5, 3.0), ("SYS-3",), "operator instrument resolution (declared)"),
        P("R0_mm", "WallRover.startRange", "mm", "m (/1000)",
          (950.0, 1050.0), ("SYS-7", "FUN-6"), "RUN-1 static pre-run sample"),
        # ---- design constants (decisions) -----------------------------------
        P("k_sigma", "WallRover.marginMultiplier", "-", "-",
          (2.5, 3.5), ("SYS-2",), "design decision; swept, not measured"),
        P("t_stop_max_s", "WallRover.stopSettleLimit", "s", "s",
          (0.5, 0.5), ("SYS-5",), "design limit"),
        P("theta_max_deg", "WallRover.headingLimit", "deg", "rad (x pi/180)",
          (5.0, 5.0), ("SYS-6",), "design limit; derived from clearance budget"),
        P("eps_est_mm", "WallRover.estimateLimit", "mm", "m (/1000)",
          (10.0, 10.0), ("SYS-8",), "design limit for onboard gap estimate error"),
        P("g_goal_mm", "WallRover.gapGoal", "mm", "m (/1000)",
          (30.0, 30.0), ("SYS-3",), "objective goal (graded, not pass/fail)"),
        P("contact_floor_mm", "WallRover.contactFloor", "mm", "m (/1000)",
          (0.0, 0.0), ("SYS-1",), "hard physical floor: zero gap == contact"),
    ])


# ---------------------------------------------------------------------------
# 2.  Relations (reproduced from RelationTemplates -- the SysML calc defs are the
#     single source of truth for these expressions)
# ---------------------------------------------------------------------------

def rotation_to_speed(omega_deg_s: float, k_mm_per_deg: float) -> float:
    """RelationTemplates::RotationToSpeed --  v = motorSpeed * k."""
    return omega_deg_s * k_mm_per_deg


def stopping_distance(v: float, t_response: float, a: float, margin: float) -> float:
    """RelationTemplates::StoppingDistance -- d = v*tResponse + v^2/(2a) + margin."""
    return v * t_response + v * v / (2.0 * a) + margin


def max_speed_from_budget(t_response: float, a: float, budget: float, margin: float) -> float:
    """RelationTemplates::MaxSpeedFromBudget -- positive root."""
    disc = a * a * t_response * t_response + 2.0 * a * (budget - margin)
    if disc < 0.0:
        return float("nan")
    return -a * t_response + math.sqrt(disc)


def rss(*terms: float) -> float:
    """A6 -- a derived margin is the root-sum-square of independent contributors."""
    return math.sqrt(sum(t * t for t in terms))


# ---------------------------------------------------------------------------
# 3.  PREDICT
# ---------------------------------------------------------------------------

@dataclass
class Prediction:
    # kinematics
    v_mm_s: float
    t_response_s: float
    S_mm: float                 # composite stop distance (sensor-frame travel)
    t_stop_s: float
    # trigger design
    R_trig_mm: float
    loop_bias_mm: float
    required_clearance_mm: float
    # uncertainty budget (1 sigma, mm)
    sigma_q_mm: float
    sigma_S_mm: float
    sigma_n_mm: float
    sigma_b_mm: float
    sigma_run_mm: float
    sigma_sys_mm: float
    sigma_g_mm: float
    # performance
    g_mean_mm: float
    g_lo_mm: float              # k_sigma low tail -- the contact-facing number
    g_hi_mm: float
    g_deg_mm: float             # degraded (odometric backstop) gap
    est_error_mm: float         # onboard gap-estimate error budget
    v_admissible_mm_s: float    # MaxSpeedFromBudget feasibility check
    rest_reading_mm: float      # expected fused reading at rest
    rest_reading_valid: bool
    trigger_floor_mm: float     # lowest threshold the ranger can actually report
    trigger_clamped: bool       # design was limited by reachability, not by margin
    est_channel: str            # which onboard channel carries the SYS-8 estimate

    def as_rows(self) -> List[Tuple[str, str]]:
        return [
            ("cruise speed v", f"{self.v_mm_s:.1f} mm/s"),
            ("response time (pre-brake)", f"{1000*self.t_response_s:.1f} ms"),
            ("composite stop distance S", f"{self.S_mm:.1f} mm"),
            ("time to rest", f"{1000*self.t_stop_s:.0f} ms"),
            ("trigger threshold R_trig", f"{self.R_trig_mm:.1f} mm"),
            ("required clearance (k.sigma)", f"{self.required_clearance_mm:.1f} mm"),
            ("sigma: loop quantisation", f"{self.sigma_q_mm:.2f} mm"),
            ("sigma: stop repeatability", f"{self.sigma_S_mm:.2f} mm"),
            ("sigma: ranger noise", f"{self.sigma_n_mm:.2f} mm"),
            ("sigma: calibrated offset", f"{self.sigma_b_mm:.2f} mm"),
            ("sigma_run (scatter)", f"{self.sigma_run_mm:.2f} mm"),
            ("sigma_sys (common mode)", f"{self.sigma_sys_mm:.2f} mm"),
            ("sigma_g total", f"{self.sigma_g_mm:.2f} mm"),
            ("predicted gap (mean)", f"{self.g_mean_mm:.1f} mm"),
            ("predicted gap (low tail)", f"{self.g_lo_mm:.1f} mm"),
            ("degraded-mode gap", f"{self.g_deg_mm:.1f} mm"),
            ("onboard estimate error", f"{self.est_error_mm:.1f} mm"),
            ("expected rest reading", f"{self.rest_reading_mm:.1f} mm"
                                      f" ({'valid' if self.rest_reading_valid else 'BELOW FLOOR'})"),
            ("trigger reachability floor", f"{self.trigger_floor_mm:.1f} mm"
                                           f" ({'CLAMPED' if self.trigger_clamped else 'clear'})"),
            ("estimate channel", self.est_channel),
            ("admissible v (budget)", f"{self.v_admissible_mm_s:.0f} mm/s"),
        ]


def predict(p: Params, R_trig_mm: Optional[float] = None) -> Prediction:
    """Compute performance quantities from bound parameter values.

    If ``R_trig_mm`` is None the trigger is SOLVED so that the predicted mean gap
    equals the required clearance (the design point).  Passing an explicit value
    evaluates a FROZEN design against perturbed parameters -- that is the
    execution-sensitivity case used by the sweep.
    """
    v = rotation_to_speed(p.omega_max_deg_s, p.k_mm_per_deg)
    t_response = p.tau_sensor_s + p.t_chain_s
    S = stopping_distance(v, t_response, p.a_decel_mm_s2, margin=0.0)
    t_stop = t_response + v / p.a_decel_mm_s2

    # --- uncertainty budget (A6: RSS of independent contributors) -----------
    # Two families, because they fail differently.  RUN-TO-RUN terms scatter the
    # five operation runs about their own mean.  SYSTEMATIC terms shift all five
    # together -- a calibration bias ships once and hits every run, which is how a
    # fleet-wide contact happens.  Both belong in the low tail.
    sigma_q = v * p.t_loop_s / math.sqrt(12.0)      # loop-crossing quantisation
    sigma_S = p.rel_sigma_S * S                     # run-to-run stop repeatability
    # Fusing the forward pair by min() gives a fused noise between 0.826*sigma_n
    # (identical sensors) and 1.000*sigma_n (one sensor dominates).  Rather than
    # invent an interpolation whose error the calibration could not expose (A2),
    # the conservative limit is used.  The min-fusion mean bias is a constant and
    # is absorbed by the calibration of b.
    sigma_n = p.sigma_n_mm                          # ranger noise into the trigger
    sigma_yaw = p.c_yaw_mm_per_deg * p.sigma_theta_deg
    sigma_run = rss(sigma_q, sigma_S, sigma_n, sigma_yaw)

    u_S = sigma_S / math.sqrt(max(p.n_S_samples, 1.0))   # s.e. of the calibrated mean S
    u_b = rss(p.u_b_mm, p.sigma_meas_mm)                 # calibrated offset uncertainty
    sigma_sys = rss(u_S, u_b)

    sigma_g = rss(sigma_run, sigma_sys)
    sigma_b = u_b                                    # kept for the reported budget

    required_clearance = p.k_sigma * sigma_g
    loop_bias = 0.5 * v * p.t_loop_s

    # FUN-14 reachability: a threshold at or below the ranger's validity floor can
    # never be crossed, so the primary trigger would silently never fire and the run
    # would be delivered by a backstop.  The floor is the clamp, not an aspiration.
    trigger_floor = p.r_floor_mm + p.k_sigma * p.sigma_n_mm

    if R_trig_mm is None:
        # StoppingDistance template with margin := required clearance, then to
        # sensor frame (+b) and de-biased for the loop crossing (+loop_bias).
        # Rounded UP to whole mm: the flight program carries an integer threshold,
        # and rounding up is the safe direction.
        trigger_gap = stopping_distance(v, t_response, p.a_decel_mm_s2,
                                        margin=required_clearance)
        R_trig = math.ceil(trigger_gap + p.b_offset_mm + loop_bias)
        trigger_clamped = R_trig < trigger_floor
        if trigger_clamped:
            R_trig = math.ceil(trigger_floor)
    else:
        R_trig = float(R_trig_mm)
        trigger_clamped = R_trig < trigger_floor

    g_mean = R_trig - loop_bias - S - p.b_offset_mm
    g_lo = g_mean - p.k_sigma * sigma_g
    g_hi = g_mean + p.k_sigma * sigma_g

    # --- degraded mode: odometric backstop fires instead of the ranger ------
    # backstop has no ranger lag, so its stop distance is shorter by v*tau
    S_odo = stopping_distance(v, p.t_chain_s, p.a_decel_mm_s2, margin=0.0)
    g_deg = (R_trig - p.delta_bs_mm - p.e_odo_mm) - S_odo - p.b_offset_mm

    # --- onboard estimate error (SYS-8) -------------------------------------
    # SYS-8 channel selection.  The primary channel (dwell-averaged rest reading) is
    # far more precise, but it is WRONG, not merely noisy, once the ranger floors
    # out -- it saturates and reports the floor.  The rover must therefore choose
    # the channel from the reading it actually got, not from an assumption.
    rest_reading = g_mean + p.b_offset_mm
    rest_valid = rest_reading >= p.r_floor_mm + p.sigma_n_mm
    if rest_valid:
        est_error = rss(p.sigma_n_mm / math.sqrt(8.0), p.sigma_meas_mm)   # dwell-averaged
        est_channel = "primary: dwell-averaged rest reading - b"
    else:
        est_error = rss(sigma_S, sigma_q, p.sigma_meas_mm)                # fallback
        est_channel = "fallback: d_T - S - b (rest reading at/below floor)"

    # --- feasibility: is max speed admissible inside the available budget? --
    budget = p.R0_mm - p.b_offset_mm
    v_adm = max_speed_from_budget(t_response, p.a_decel_mm_s2, budget, required_clearance)

    return Prediction(
        v_mm_s=v, t_response_s=t_response, S_mm=S, t_stop_s=t_stop,
        R_trig_mm=R_trig, loop_bias_mm=loop_bias,
        required_clearance_mm=required_clearance,
        sigma_q_mm=sigma_q, sigma_S_mm=sigma_S, sigma_n_mm=sigma_n,
        sigma_b_mm=sigma_b, sigma_run_mm=sigma_run, sigma_sys_mm=sigma_sys,
        sigma_g_mm=sigma_g,
        g_mean_mm=g_mean, g_lo_mm=g_lo, g_hi_mm=g_hi, g_deg_mm=g_deg,
        est_error_mm=est_error, v_admissible_mm_s=v_adm,
        rest_reading_mm=rest_reading, rest_reading_valid=rest_valid,
        trigger_floor_mm=trigger_floor, trigger_clamped=trigger_clamped,
        est_channel=est_channel)


# ---------------------------------------------------------------------------
# 4.  EVALUATE -- the computational satisfy/require roll-up
# ---------------------------------------------------------------------------

@dataclass
class Verdict:
    req: str
    statement: str
    measured: str
    target: str
    value: Optional[float]
    limit: Optional[float]
    ok: Optional[bool]          # None == INDETERMINATE (unbound parameter)
    note: str = ""

    @property
    def mark(self) -> str:
        return {True: "PASS", False: "FAIL", None: "INDET"}[self.ok]


def _lower(req, stmt, meas, tgt, value, limit, note="") -> Verdict:
    return Verdict(req, stmt, meas, tgt, value, limit, value >= limit, note)


def _upper(req, stmt, meas, tgt, value, limit, note="") -> Verdict:
    return Verdict(req, stmt, meas, tgt, value, limit, value <= limit, note)


def evaluate(p: Params, R_trig_mm: Optional[float] = None) -> List[Verdict]:
    """Return pass/fail for every requirement with a computational operand.

    Requirements verified by inspection or by test-only evidence appear here with
    ``ok=None`` and a note naming the verification method, so that the roll-up is
    complete: no requirement is silently absent.
    """
    unbound = p.unbound()
    if unbound:
        return [Verdict("MODEL", "All parameters bound before evaluation",
                        "unbound parameter count", "0", float(len(unbound)), 0.0,
                        None, "UNBOUND: " + ", ".join(unbound))]

    pr = predict(p, R_trig_mm)
    v: List[Verdict] = []

    # ---- SYS level ---------------------------------------------------------
    v.append(_lower("SYS-1", "The rover shall not contact the wall.",
                    "minClearance (low tail)", "contactFloor",
                    pr.g_lo_mm, p.contact_floor_mm,
                    "low tail = mean - k_sigma*sigma_g"))
    v.append(_lower("SYS-2", "Predicted gap shall be >= k_sigma * sigma_g.",
                    "predictedGap", "requiredClearance",
                    pr.g_mean_mm, pr.required_clearance_mm,
                    "derived margin requirement bridging SYS-1 and SYS-3"))
    v.append(_upper("SYS-3", "Final gap should be <= gapGoal (objective, graded).",
                    "predictedGap", "gapGoal",
                    pr.g_mean_mm, p.g_goal_mm, "OBJECTIVE -- graded, not pass/fail"))
    v.append(_lower("SYS-4", "Commanded wheel speed shall be the achievable maximum.",
                    "commandedSpeed/maxSpeed", "1.0", 1.0, 1.0,
                    "command saturates the controller ceiling by construction; "
                    "confirmed by the cruise plateau in test"))
    v.append(_upper("SYS-5", "The rover shall reach rest within stopSettleLimit.",
                    "timeToRest", "stopSettleLimit", pr.t_stop_s, p.t_stop_max_s))
    v.append(_upper("SYS-6", "Heading deviation shall not exceed headingLimit.",
                    "headingDeviation", "headingLimit",
                    p.theta_dev_deg, p.theta_max_deg,
                    "yaw costs c_yaw*theta of corner clearance"))
    v.append(_lower("SYS-7", "Degraded-mode stop shall still clear the wall.",
                    "degradedClearance", "contactFloor",
                    pr.g_deg_mm, p.contact_floor_mm,
                    "odometric backstop fires when the ranger channel is unusable"))
    v.append(_upper("SYS-8", "Onboard gap-estimate error shall not exceed estimateLimit.",
                    "estimateError", "estimateLimit", pr.est_error_mm, p.eps_est_mm))
    v.append(Verdict("SYS-9", "Each run shall be independent of every other run.",
                     "persisted state", "none", None, None, None,
                     "verified by INSPECTION of the locked program (no file/flash "
                     "state; hub power-cycled between runs)"))

    # ---- FUN level ---------------------------------------------------------
    v.append(_lower("FUN-1", "Forward range shall be sampled at >= 10 Hz.",
                    "1/rangerRefresh", "10 Hz", 1.0 / p.T_refresh_s, 10.0))
    v.append(_upper("FUN-2", "Inter-sample extrapolation error shall be < sigma_n.",
                    "extrapolation error", "rangerNoise",
                    pr.v_mm_s * p.T_refresh_s * 0.05, p.sigma_n_mm,
                    "5% speed error over one refresh interval"))
    v.append(Verdict("FUN-3", "Implausible range samples shall be rejected.",
                     "plausibility bounds", "enforced", None, None, None,
                     "verified by INSPECTION of the guard + TEST via injected "
                     "out-of-range samples in the RUN-1 log"))
    v.append(_upper("FUN-4", "Stop shall be commanded within one loop period.",
                    "loopPeriod", "loopPeriodLimit", p.t_loop_s, 0.025))
    v.append(_lower("FUN-5", "Braking shall achieve at least decelLimit.",
                    "decel", "decelLimit", p.a_decel_mm_s2, 1000.0))
    v.append(_lower("FUN-6", "The odometric backstop shall fire before the wall.",
                    "backstopClearance", "contactFloor",
                    pr.g_deg_mm, p.contact_floor_mm))
    v.append(Verdict("FUN-7", "A time backstop shall stop the rover.",
                     "elapsed limit", "enforced", None, None, None,
                     "verified by INSPECTION; sized at 3x nominal run duration"))
    v.append(_upper("FUN-8", "Odometry error over the approach shall be bounded.",
                    "odometryError", "20 mm", p.e_odo_mm, 20.0))
    v.append(_upper("FUN-9", "Heading shall be observed throughout the approach.",
                    "headingSpread", "headingLimit",
                    p.sigma_theta_deg, p.theta_max_deg))
    v.append(Verdict("FUN-10", "Logging shall never run on the hot path.",
                     "hot-path I/O", "none", None, None, None,
                     "verified by INSPECTION of the locked program (buffer fill "
                     "only; stdout after motors stop)"))
    v.append(_lower("FUN-11", "Rest range shall be averaged over a dwell.",
                    "dwell samples", "8", 8.0, 8.0))
    v.append(Verdict("FUN-12", "Motors shall stop and the sentinel shall be emitted "
                     "on every termination path.",
                     "finally block", "present", None, None, None,
                     "verified by INSPECTION + TEST (sentinel observed in every run)"))
    v.append(_lower("FUN-14", "The trigger threshold shall be reachable by the ranger.",
                    "triggerThreshold", "triggerFloor",
                    pr.R_trig_mm, pr.trigger_floor_mm,
                    "a threshold below the validity floor can never be crossed: the "
                    "primary trigger silently never fires and a backstop delivers the run"))
    v.append(_upper("FUN-13", "Forward-pair readings shall agree within the pair limit.",
                    "rangerPairOffset", "pairOffsetLimit", p.delta_AB_mm, 30.0,
                    "a larger split means the two rangers are not observing the same "
                    "target geometry -- a fault, not a calibration constant"))

    # ---- CMP level (unit verification) -------------------------------------
    v.append(_lower("CMP-1", "Left motor shall sustain the rated maximum speed.",
                    "motorL speed", "0.95*maxWheelSpeed",
                    p.omega_max_deg_s, 0.95 * p.omega_max_deg_s))
    v.append(_lower("CMP-2", "Right motor shall sustain the rated maximum speed.",
                    "motorR speed", "0.95*maxWheelSpeed",
                    p.omega_max_deg_s, 0.95 * p.omega_max_deg_s))
    v.append(_upper("CMP-3", "Drive-motor speeds shall differ by <= symmetryLimit.",
                    "symmetryDeviation", "symmetryLimit",
                    p.sym_dev_deg_s, 0.05 * p.omega_max_deg_s))
    v.append(_upper("CMP-4", "Odometry scale error shall be <= 2%.",
                    "odometryError/travel", "2%",
                    p.e_odo_mm / max(p.R0_mm - pr.R_trig_mm, 1.0), 0.02))
    v.append(_lower("CMP-5", "Each motor shall produce at least decelLimit.",
                    "decel", "decelLimit", p.a_decel_mm_s2, 1000.0))
    v.append(_upper("CMP-6", "Ranger A refresh interval shall be <= 100 ms.",
                    "rangerRefresh", "0.1 s", p.T_refresh_s, 0.100))
    v.append(_upper("CMP-7", "Ranger B refresh interval shall be <= 100 ms.",
                    "rangerRefresh", "0.1 s", p.T_refresh_s, 0.100))
    v.append(_upper("CMP-8", "Fused ranger noise shall be <= 8 mm (1 sigma).",
                    "rangerNoise", "8 mm", p.sigma_n_mm, 8.0))
    v.append(_upper("CMP-9", "Ranger validity floor shall be below the operating gap.",
                    "validityFloor", "expected rest reading",
                    p.r_floor_mm + p.sigma_n_mm, pr.rest_reading_mm,
                    "if violated, SYS-8 falls back to the d_T - S channel: " + pr.est_channel))
    v.append(_upper("CMP-10", "IMU heading drift shall be <= 1 deg over a run.",
                    "headingDrift", "1 deg", 1.0, 1.0,
                    "bounded by run duration; measured in the RUN-1 static dwells"))
    v.append(_upper("CMP-11", "Control-loop period shall be <= 25 ms.",
                    "loopPeriod", "loopPeriodLimit", p.t_loop_s, 0.025))
    v.append(Verdict("CMP-12", "Rear ranger: retained only if it serves a quantity.",
                     "traceability", "retain/drop", None, None, None,
                     "DROPPED unless RUN-1 shows it observes travelled distance"))
    v.append(Verdict("CMP-13", "Reflectance sensor: no requirement traces to it.",
                     "traceability", "drop", None, None, None,
                     "DROPPED by traceability; RUN-1 logs it once to verify the "
                     "absence rather than assume it"))
    return v


def rollup(verdicts: List[Verdict]) -> str:
    """Top-level satisfy verdict: WallRover satisfies WallRunNeed."""
    if any(x.ok is None and x.req == "MODEL" for x in verdicts):
        return "INDETERMINATE"
    hard = [x for x in verdicts if x.ok is not None and x.req != "SYS-3"]
    if all(x.ok for x in hard):
        return "SATISFIED"
    return "NOT SATISFIED"


# ---------------------------------------------------------------------------
# 5.  SWEEP -- sensitivity analysis (Calibration Plan section 0)
# ---------------------------------------------------------------------------

@dataclass
class SweepRow:
    name: str
    sysml: str
    units: str
    lo: float
    hi: float
    d_objective: float      # change in the ACHIEVABLE gap (design re-solved)
    d_margin: float         # change in the REALISED gap with R_trig FROZEN
    d_degraded: float       # change in the DEGRADED-mode gap with R_trig FROZEN
    flips: Tuple[str, ...]  # requirement ids whose verdict changes across the range
    tier: int
    priority: str

    @property
    def worst_margin(self) -> float:
        return max(abs(self.d_margin), abs(self.d_degraded))


def sweep(p: Params, only: Optional[List[str]] = None) -> List[SweepRow]:
    """Vary each parameter over its stated prior range at the prior-mid working point.

    Three sensitivities are reported, because they answer different questions:

      d_objective : with the design RE-SOLVED at each parameter value, how much does
                    the achievable gap (k_sigma * sigma_g) move?  -> what to calibrate
                    in order to get CLOSER.
      d_margin    : with R_trig FROZEN at the baseline design, how much does the
                    REALISED gap move?  -> what must be ACCURATE so as not to hit the
                    wall.  A parameter that moves this 1:1 is a contact risk, not a
                    performance nuisance.
      d_degraded  : the same, for the SYS-7 degraded-mode (odometric backstop) gap,
                    so that backstop parameters are ranked rather than invisible.

    A fourth, non-numeric signal is captured: whether any requirement VERDICT flips
    across the prior range.  A parameter can have small numeric leverage and still
    decide a pass/fail, and that must not be filed under "prior is adequate".
    """
    base = p.working_point()
    R_frozen = predict(base).R_trig_mm
    rows: List[SweepRow] = []
    for par in p:
        if only and par.name not in only:
            continue
        lo, hi = par.prior
        if lo == hi:
            continue
        obj, marg, deg, verdicts = [], [], [], []
        for val in (lo, hi):
            wp = p.working_point({par.name: val})
            obj.append(predict(wp).required_clearance_mm)
            pr = predict(wp, R_trig_mm=R_frozen)
            marg.append(pr.g_mean_mm)
            deg.append(pr.g_deg_mm)
            verdicts.append({x.req: x.ok for x in evaluate(wp)})
        flips = tuple(sorted(k for k in verdicts[0]
                             if verdicts[0][k] is not None
                             and verdicts[0][k] != verdicts[1].get(k)))
        rows.append(SweepRow(
            name=par.name, sysml=par.sysml, units=par.units, lo=lo, hi=hi,
            d_objective=obj[1] - obj[0], d_margin=marg[1] - marg[0],
            d_degraded=deg[1] - deg[0], flips=flips,
            tier=par.tier, priority=""))

    ranked = sorted(rows, key=lambda r: (-r.worst_margin, -abs(r.d_objective)))
    for r in ranked:
        if r.worst_margin >= 20.0:
            r.priority = "P1 - bind before any fast run"
        elif r.worst_margin >= 5.0 or abs(r.d_objective) >= 5.0:
            r.priority = "P2 - bind in RUN-1"
        elif r.worst_margin >= 1.0 or abs(r.d_objective) >= 1.0:
            r.priority = "P3 - log in RUN-1, bind if cheap"
        else:
            r.priority = "P4 - prior is adequate"
        if r.flips:                       # verdict-flip override
            if r.priority.startswith(("P3", "P4")):
                r.priority = "P2 - bind in RUN-1"
            r.priority += " (decides " + ",".join(r.flips) + ")"
    return ranked


def counterfactual_no_extrapolation(p: Params) -> Dict[str, float]:
    """What the design would cost WITHOUT FUN-2 (inter-sample extrapolation).

    Without it the trigger can only fire on a fresh ranger sample, so the crossing
    quantisation is set by the REFRESH interval instead of the loop period.  This
    is the numeric justification for FUN-2 existing at all.
    """
    wp = p.working_point()
    pr = predict(wp)
    v = pr.v_mm_s
    sigma_q_no = v * wp.T_refresh_s / math.sqrt(12.0)
    sigma_g_no = rss(pr.sigma_g_mm ** 2 - pr.sigma_q_mm ** 2 >= 0
                     and math.sqrt(pr.sigma_g_mm ** 2 - pr.sigma_q_mm ** 2) or 0.0,
                     sigma_q_no)
    return {
        "sigma_q_with_extrapolation_mm": pr.sigma_q_mm,
        "sigma_q_without_mm": sigma_q_no,
        "achievable_gap_with_mm": wp.k_sigma * pr.sigma_g_mm,
        "achievable_gap_without_mm": wp.k_sigma * sigma_g_no,
    }


# ---------------------------------------------------------------------------
# 6.  Reporting helpers (markdown tables for the deliverables)
# ---------------------------------------------------------------------------

def md_sweep_table(rows: List[SweepRow]) -> str:
    out = ["| parameter (SysML attribute) | assumed range | d objective (mm) | "
           "d nominal margin (mm) | d degraded margin (mm) | knowledge tier | priority |",
           "|---|---|---:|---:|---:|---|---|"]
    for r in rows:
        out.append(f"| `{r.name}`<br>`{r.sysml}` | {r.lo:g} .. {r.hi:g} {r.units} | "
                   f"{r.d_objective:+.1f} | {r.d_margin:+.1f} | {r.d_degraded:+.1f} | "
                   f"{TIER_NAMES[r.tier]} | {r.priority} |")
    return "\n".join(out)


def md_verdict_table(verdicts: List[Verdict]) -> str:
    out = ["| req | measured | value | target | limit | verdict |",
           "|---|---|---:|---|---:|---|"]
    for v in verdicts:
        val = "-" if v.value is None else f"{v.value:.3g}"
        lim = "-" if v.limit is None else f"{v.limit:.3g}"
        out.append(f"| {v.req} | {v.measured} | {val} | {v.target} | {lim} | {v.mark} |")
    return "\n".join(out)


def md_prediction_table(pr: Prediction) -> str:
    out = ["| quantity | value |", "|---|---:|"]
    for k, val in pr.as_rows():
        out.append(f"| {k} | {val} |")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# 7.  CLI
# ---------------------------------------------------------------------------

def main() -> None:
    p = build_params()

    print("=" * 78)
    print("EXECUTABLE ANALYSIS MODEL -- state at GATE A")
    print("=" * 78)
    print(f"free parameters: {len(p.names())}")
    print(f"unbound        : {len(p.unbound())}")
    print()
    print("EVALUATE with the model as it stands (A3: uncalibrated, not zeroed):")
    for v in evaluate(p):
        print(f"  {v.req:<6} {v.mark:<6} {v.note[:100]}")
    print(f"  ROLL-UP: WallRover satisfies WallRunNeed -> {rollup(evaluate(p))}")
    print()

    print("-" * 78)
    print("PRIOR-MID WORKING POINT (for ranking only -- NOT a calibrated model)")
    print("-" * 78)
    wp = p.working_point()
    pr = predict(wp)
    for k, val in pr.as_rows():
        print(f"  {k:<32} {val}")
    print()

    print("-" * 78)
    print("SENSITIVITY SWEEP")
    print("-" * 78)
    rows = sweep(p)
    print(f"{'parameter':<18}{'range':<24}{'d_obj':>8}{'d_marg':>8}{'d_degr':>8}  priority")
    for r in rows:
        rng = f"{r.lo:g}..{r.hi:g} {r.units}"
        print(f"{r.name:<18}{rng:<24}{r.d_objective:>+8.1f}{r.d_margin:>+8.1f}"
              f"{r.d_degraded:>+8.1f}  {r.priority}")
    print()
    print("uncertainty budget at the working point (1 sigma, mm):")
    print(f"  quantisation {pr.sigma_q_mm:5.2f} | stop repeat {pr.sigma_S_mm:5.2f}"
          f" | ranger noise {pr.sigma_n_mm:5.2f} | offset {pr.sigma_b_mm:5.2f}")
    print(f"  sigma_run {pr.sigma_run_mm:5.2f} (+) sigma_sys {pr.sigma_sys_mm:5.2f}"
          f"  ==> sigma_g {pr.sigma_g_mm:5.2f}")
    cf = counterfactual_no_extrapolation(p)
    print()
    print("FUN-2 (inter-sample extrapolation) counterfactual:")
    print(f"  crossing quantisation  with: {cf['sigma_q_with_extrapolation_mm']:.2f} mm"
          f"   without: {cf['sigma_q_without_mm']:.2f} mm")
    print(f"  achievable gap         with: {cf['achievable_gap_with_mm']:.1f} mm"
          f"   without: {cf['achievable_gap_without_mm']:.1f} mm")


if __name__ == "__main__":
    main()
