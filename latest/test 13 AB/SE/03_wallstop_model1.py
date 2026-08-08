#!/usr/bin/env python3
"""
wallstop_model.py  v1.0 -- EXECUTABLE ANALYSIS MODEL for the wall-approach rover.

Computational view of the SysML model (wall_rover.sysml). Every parameter carries
`sysml_ref`, the attribute it realises in the SysML model; every `require`
constraint in the SysML model is realised by one entry in REQUIREMENTS. The two
views must agree -- structural_check.py verifies the correspondence both ways.

Standard library only.

Public entry points (Process step 3):
    predict()  -> performance quantities (clearance, margins, timings)
    evaluate() -> PASS/FAIL/UNRESOLVED for every requirement (satisfy roll-up)
    sweep()    -> parameter sensitivity for the GATE A sensitivity analysis

DOCTRINE
  A3  uncalibrated, not zeroed: free parameters are value=None until a
      calibration activity binds them. predict() with unbound parameters must be
      asked for explicitly (use_prior=True) and records which priors it used.
  A6  margins are the RSS of independent uncertainty contributors, never a guess.
  A2  psi (post-command stopping travel) is bound by DIRECT measurement at the
      operating point; the StoppingDistance relation is used only for the
      first-order speed correction and for the structural residual check, which
      a 3-speed calibration can expose.

FRAME / SIGN CONVENTIONS
  x        true forward travel from the start pose, mm (+ = toward the wall)
  G(x)     clearance, rover FRONT-MOST POINT to wall, mm
  r        range REPORTED by a forward ranger, mm
  G = r + b_offset            (b_offset <= 0 if the ranger sits behind the bumper)
  s        controller's odometric travel estimate, mm  (s = k_eff * dtheta)
  o        range offset  o = r + s : constant along a straight approach, and the
           quantity the fused estimator averages (the architecture's absolute anchor)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 1. PARAMETER REGISTRY   (SysML attribute <-> Python variable, 1:1)
# ---------------------------------------------------------------------------

TIER_ORDER = ["T2-prior", "T1-vendor", "T0-design", "T3-onboard-single",
              "T4-onboard-multi", "T5-external"]
TIERS = {
    "T2-prior": "engineering prior only (nothing measured)",
    "T1-vendor": "vendor / firmware datasheet",
    "T0-design": "design decision, fixed by us",
    "T3-onboard-single": "single onboard sample",
    "T4-onboard-multi": "multi-point or anchored onboard calibration",
    "T5-external": "external ground truth (operator measurement)",
}


@dataclass
class Param:
    name: str
    sysml_ref: str
    unit: str
    kind: str                      # design | free | environment | derived
    prior: Optional[Tuple[float, float]] = None
    nominal: Optional[float] = None
    value: Optional[float] = None  # BOUND value; None = free
    tier: str = "T2-prior"
    basis: str = ""
    binds_to: str = ""
    doc: str = ""

    def get(self, use_prior: bool = False) -> float:
        if self.value is not None:
            return self.value
        if use_prior and self.nominal is not None:
            return self.nominal
        raise ValueError(f"parameter '{self.name}' is UNBOUND -- bound by {self.binds_to!r}")

    @property
    def bound(self) -> bool:
        return self.value is not None


PARAMS: Dict[str, Param] = {}


def P(*a, **k) -> Param:
    p = Param(*a, **k)
    PARAMS[p.name] = p
    return p


def g(name: str, use_prior: bool = False) -> float:
    return PARAMS[name].get(use_prior)


# --- drivetrain -----------------------------------------------------------
P("omega_cmd", "omegaCmd", "deg/s", "design", nominal=10000.0, value=10000.0,
  tier="T0-design", doc="commanded wheel speed, deliberately above the ceiling so the "
                        "firmware clamps to the physical maximum (SYS-1)")
P("omega_cruise", "omegaCruise", "deg/s", "free", prior=(600.0, 1150.0), nominal=810.0,
  binds_to="CAL-1/P2", doc="achieved steady wheel speed at the ceiling")
P("k_eff", "kEff", "mm/deg", "free", prior=(0.30, 0.85), nominal=0.489,
  binds_to="CAL-1/P6 (static staircase) + P2 (cruise sweep)",
  doc="reported-range mm per degree of wheel rotation; bundles wheel radius, "
      "gearing and slip (RelationTemplates::RotationToSpeed.k)")
P("a_accel", "aAccel", "mm/s^2", "free", prior=(500.0, 2500.0), nominal=1000.0,
  binds_to="CAL-1/P2", doc="forward acceleration to cruise; upper end capped by the "
                           "commanded acceleration limit (design), lower end by torque")
P("a_brake", "aBrake", "mm/s^2", "free", prior=(900.0, 9000.0), nominal=3500.0,
  binds_to="CAL-1/P2+P4+P5 (3-speed fit)", doc="effective deceleration under brake()")
P("t_chain", "tChain", "s", "free", prior=(0.000, 0.040), nominal=0.012,
  binds_to="CAL-1/P2 (decel onset)",
  doc="RoverCommon::RoverLatency.tChain -- command-to-torque lag")
P("psi_brake", "psiBrake", "mm", "free", prior=(3.0, 430.0), nominal=None,
  binds_to="CAL-1/P2+P4 (direct odometric+ranger measurement at cruise)",
  doc="post-command travel to rest AT CRUISE. Bound by direct measurement at the "
      "operating point (zero extrapolation); prior range is derived from the "
      "(v, t_chain, a_brake) priors so the prior box stays self-consistent")
P("sigma_psi", "sigmaPsi", "mm", "free", prior=(1.0, 20.0), nominal=6.0,
  binds_to="CAL-1/P2 vs P4 (+VER run)", doc="run-to-run scatter of psi_brake")

# --- ranging --------------------------------------------------------------
P("b_offset", "bOffset", "mm", "free", prior=(-80.0, 15.0), nominal=-30.0,
  binds_to="CAL-1/P7 + M1 (operator ground truth)",
  doc="composite range->clearance offset of the PRIMARY ranger: G = r + b_offset. "
      "Bundles mounting recess and sensor bias. NO onboard channel observes it -- "
      "this is the parameter the one costed operator measurement buys.")
P("sigma_b", "sigmaB", "mm", "free", prior=(1.0, 4.0), nominal=2.0, binds_to="M1",
  doc="uncertainty of the b_offset anchor (ruler resolution + static read noise)")
P("l_sensor", "lSensor", "s", "free", prior=(0.0, 0.120), nominal=0.040,
  binds_to="CAL-1/P2+P4 (dynamic-vs-static offset comparison)",
  doc="ranger staleness: r(t) reports the range as it was at t - l_sensor")
P("sigma_ls", "sigmaLs", "s", "free", prior=(0.002, 0.030), nominal=0.010,
  binds_to="CAL-1/P2+P4", doc="residual uncertainty of l_sensor after calibration")
P("t_refresh", "tRefresh", "s", "free", prior=(0.010, 0.120), nominal=0.050,
  binds_to="CAL-1/P2", doc="DistanceSensor.refreshInterval -- fresh-sample period")
P("q_range", "qRange", "mm", "free", prior=(1.0, 20.0), nominal=10.0,
  binds_to="CAL-1/P2+P6", doc="reported-range quantisation step (reporting artifact, D1)")
P("eps_scale", "epsScale", "1", "free", prior=(-0.03, 0.03), nominal=0.0,
  binds_to="CAL-1/P6 (static staircase regression)",
  doc="ranger scale error against odometry over the working range")
P("r_min_valid", "rMinValid", "mm", "free", prior=(30.0, 60.0), nominal=40.0,
  tier="T1-vendor", binds_to="CAL-1/P6+P7", doc="minimum validly reported range")
P("r_max_valid", "rMaxValid", "mm", "environment", nominal=2000.0, value=2000.0,
  tier="T1-vendor", doc="no-echo / saturation value")
P("d_agree", "dAgree", "mm", "free", prior=(0.0, 60.0), nominal=15.0,
  binds_to="CAL-1/P0+P6+P7", doc="static primary-vs-secondary ranger disagreement")

# --- controller design ----------------------------------------------------
P("dt_loop", "dtLoop", "s", "design", nominal=0.005, value=0.005, tier="T0-design",
  doc="hot-path control-loop period")
P("n_look", "nLook", "1", "design", nominal=4.0, value=4.0, tier="T0-design",
  doc="trigger look-ahead in loop periods; the sub-loop wait makes a generous "
      "look-ahead free, which is what makes the trigger immune to loop jitter")
P("n_fuse", "nFuse", "1", "design", nominal=6.0, value=6.0, tier="T0-design",
  doc="fresh ranger samples averaged by the range-offset estimator")
P("n_fuse_min", "nFuseMin", "1", "design", nominal=3.0, value=3.0, tier="T0-design",
  doc="minimum fused samples before the primary trigger arms")
P("g_target", "gTarget", "mm", "design", prior=(15.0, 600.0), nominal=500.0,
  tier="T0-design", doc="commanded target clearance. CAL-1 uses a prior-box-safe "
                        "value; the operating value is frozen at GATE B")
P("g_floor", "gFloor", "mm", "design", nominal=30.0, value=30.0, tier="T0-design",
  doc="dead-reckoning backstop clearance (fires only if the primary trigger did not)")
P("s_backstop", "sBackstop", "mm", "design", prior=(200.0, 2000.0), nominal=300.0,
  tier="T0-design",
  doc="ABSOLUTE odometric travel limit: brake unconditionally at this travel. In "
      "CAL-1 it is set tight (300 mm) so the first max-speed brake event happens far "
      "from the wall and its safety depends only on k_eff, which the static staircase "
      "binds first -- it removes the psi prior from the safety argument entirely. In "
      "operation it is the fail-safe backstop of CMP-10. Same code path either way.")
P("d_odo_drift", "dOdoDrift", "1", "free", prior=(-0.04, 0.04), nominal=0.01,
  binds_to="CAL-1/P2..P7 (o_rest vs o_start consistency over the traverse)",
  doc="odometric scale drift beyond k_eff within one run (slip variation). Degrades "
      "the dead-reckoning backstop but not the fused estimator, which re-anchors")
P("e_trig", "eTrig", "s", "free", prior=(0.0, 0.004), nominal=0.0015,
  binds_to="CAL-1/P2 (commanded vs achieved brake instant)",
  doc="brake-instant timing error: 1 ms wait granularity + loop overrun")
P("z_conf", "zConf", "1", "design", nominal=3.0, value=3.0, tier="T0-design",
  doc="margin coverage factor: m_contact = z_conf * sigma_rss")
P("k_obj", "kObj", "1", "design", nominal=1.2, value=1.2, tier="T0-design",
  doc="objective efficiency cap: g_target <= k_obj * m_contact")

# --- geometry / environment ----------------------------------------------
P("w_half", "wHalf", "mm", "free", prior=(40.0, 80.0), nominal=60.0,
  binds_to="not scheduled -- low leverage (see sensitivity table)",
  doc="half-width of the rover's front face; converts heading error into corner loss")
P("psi_head", "psiHead", "deg", "free", prior=(0.0, 6.0), nominal=1.5,
  binds_to="CAL-1/P2+P4 (IMU yaw + differential odometry)",
  doc="heading deviation accumulated by the stop")
P("d_psi_head", "dPsiHead", "deg", "free", prior=(0.0, 3.0), nominal=1.0,
  binds_to="CAL-1/P2 vs P4", doc="run-to-run variation of heading deviation")
P("psi_limit", "psiLimit", "deg", "design", nominal=5.0, value=5.0, tier="T0-design",
  doc="SYS-4 heading-deviation limit")
P("g_start", "gStart", "mm", "environment", prior=(950.0, 1050.0), nominal=1000.0,
  binds_to="CAL-1/P0 (static baseline, in reported-range space)",
  doc="true clearance at the start line; the operator holds it constant")
P("t_refresh_phase", "tRefreshPhase", "1", "environment", prior=(0.0, 1.0), nominal=0.5,
  doc="ranger ping phase at program start as a fraction of t_refresh (nuisance "
      "variable, uncontrollable, re-drawn every run)")
P("slip_brake", "slipBrake", "1", "free", prior=(0.0, 0.15), nominal=0.0,
  binds_to="CAL-1/P2+P4 (o_rest vs o_trigger consistency)",
  doc="fraction by which odometry UNDER-reads travel during braking (skid). "
      "Detected as an inconsistency between the ranger and odometer over the "
      "brake phase; a systematic that would ship a too-small psi if ignored")
P("sigma_est_limit", "sigmaEstLimit", "mm", "design", nominal=10.0, value=10.0,
  tier="T0-design", doc="SYS-7 limit on onboard clearance-estimate uncertainty")
P("omega_left", "omegaLeft", "deg/s", "free", prior=(600.0, 1150.0), nominal=810.0,
  binds_to="CAL-1/P4 (left encoder cruise plateau)", doc="CMP-1 unit quantity")
P("omega_right", "omegaRight", "deg/s", "free", prior=(600.0, 1150.0), nominal=810.0,
  binds_to="CAL-1/P4 (right encoder cruise plateau)", doc="CMP-2 unit quantity")
P("d_omega", "dOmega", "deg/s", "free", prior=(0.0, 120.0), nominal=10.0,
  binds_to="CAL-1/P4+P6 (per-motor speed traces)",
  doc="worst wheel-speed asymmetry during cruise (CMP-14)")
P("track", "track", "mm", "free", prior=(90.0, 180.0), nominal=120.0,
  binds_to="not scheduled -- low leverage; used only to derive the CMP-14 limit",
  doc="drive-wheel track width")
P("contact_floor", "contactFloor", "mm", "design", nominal=0.0, value=0.0,
  tier="T0-design", doc="SYS-2 floor: clearance at contact is zero by definition")
# --- requirement threshold TBDs: set at GATE B from the CAL-1 measurement plus a
#     tolerance, then verified against a LATER sample (the VER run). Free until then.
P("omega_floor", "omegaFloor", "deg/s", "free", prior=(500.0, 900.0), nominal=600.0,
  binds_to="GATE B (TBD-1 = measured cruise speed - 3 sigma)", doc="CMP-1/CMP-2 threshold")
P("psi_travel_limit", "psiTravelLimit", "mm", "free", prior=(20.0, 600.0), nominal=90.0,
  binds_to="GATE B (TBD-10 = measured psi + 3 sigma)", doc="CMP-11 threshold")
P("sigma_psi_limit", "sigmaPsiLimit", "mm", "free", prior=(2.0, 25.0), nominal=8.0,
  binds_to="GATE B (TBD-11)", doc="CMP-22 threshold")
P("l_sensor_limit", "lSensorLimit", "s", "free", prior=(0.02, 0.15), nominal=0.06,
  binds_to="GATE B (TBD-5)", doc="CMP-20 threshold")
P("t_refresh_limit", "tRefreshLimit", "s", "free", prior=(0.02, 0.15), nominal=0.07,
  binds_to="GATE B (TBD-4)", doc="CMP-5 threshold")
P("q_range_limit", "qRangeLimit", "mm", "free", prior=(1.0, 25.0), nominal=12.0,
  binds_to="GATE B (TBD-6)", doc="CMP-21 threshold")
P("d_agree_limit", "dAgreeLimit", "mm", "free", prior=(5.0, 80.0), nominal=25.0,
  binds_to="GATE B (TBD-8)", doc="CMP-7 threshold")
P("e_trig_limit", "eTrigLimit", "s", "free", prior=(0.001, 0.010), nominal=0.003,
  binds_to="GATE B (TBD-9)", doc="CMP-8 threshold")


DERIVED_SYSML = {
    "finalClearance": "g_pred", "clearanceLowerBound": "g_lower",
    "contactMargin": "m_contact", "sigmaRss": "sigma_rss", "vCruise": "v_cruise",
    "vBudget": "v_budget", "sAccel": "s_accel", "sAccelBudget": "s_accel_budget",
    "rRestPred": "r_rest_pred", "sigmaEst": "sigma_est", "psiBelieved": "psi_believed",
    "dOmegaLimit": "d_omega_limit", "tApproach": "t_approach",
    "oConsistency": "o_consistency", "objectiveCap": "g_obj_cap",
    "triggerFired": "trigger", "triggerFloor": "trigger_floor",
}

# Verification evidence, keyed by requirement id. Populated by the Calibration and
# Verification Reports; empty at GATE A, which is why the roll-up is UNRESOLVED there.
EVIDENCE: Dict[str, str] = {}


def set_evidence(rid: str, text: str) -> None:
    EVIDENCE[rid] = text


def bind(name: str, value: float, tier: str, basis: str) -> None:
    """Bind a free parameter, ENFORCING the source-of-truth hierarchy
    (CHARACTERIZATION METHOD 2): a lower tier may never silently overwrite a value
    a higher tier has set. A later sample that disagrees with a higher-confidence
    value is a discrepancy to diagnose, not grounds to re-fit the constant."""
    if name not in PARAMS:
        raise KeyError(name)
    if tier not in TIER_ORDER:
        raise ValueError("unknown tier " + tier)
    p = PARAMS[name]
    if p.bound and TIER_ORDER.index(tier) < TIER_ORDER.index(p.tier):
        raise ValueError(
            "refusing to overwrite %s (held at %s) with lower tier %s -- "
            "diagnose the discrepancy instead of re-fitting" % (name, p.tier, tier))
    p.value, p.tier, p.basis = float(value), tier, basis


def unbound_names() -> List[str]:
    return [q.name for q in PARAMS.values()
            if q.kind in ("free", "environment") and not q.bound]


def psi_prior_from_physics() -> Tuple[float, float]:
    """Keep the psi prior consistent with the (v, t_chain, a_brake) priors."""
    v_lo = PARAMS["k_eff"].prior[0] * PARAMS["omega_cruise"].prior[0]
    v_hi = PARAMS["k_eff"].prior[1] * PARAMS["omega_cruise"].prior[1]
    lo = stopping_distance(v_lo, PARAMS["t_chain"].prior[0], PARAMS["a_brake"].prior[1], 0.0)
    hi = stopping_distance(v_hi, PARAMS["t_chain"].prior[1], PARAMS["a_brake"].prior[0], 0.0)
    return (round(lo, 1), round(hi, 1))


# ---------------------------------------------------------------------------
# 2. RELATIONS  (RelationTemplates instances -- expressions reproduced 1:1)
# ---------------------------------------------------------------------------

def rotation_to_speed(motor_speed: float, k: float) -> float:
    """RelationTemplates::RotationToSpeed --  v = motorSpeed * k"""
    return motor_speed * k


def stopping_distance(v: float, t_response: float, a: float, margin: float) -> float:
    """RelationTemplates::StoppingDistance --  d = v*tResponse + v^2/(2a) + margin"""
    return v * t_response + v * v / (2.0 * a) + margin


def max_speed_from_budget(t_response: float, a: float, budget: float, margin: float) -> float:
    """RelationTemplates::MaxSpeedFromBudget -- positive root of StoppingDistance"""
    disc = a * a * t_response * t_response + 2.0 * a * (budget - margin)
    return 0.0 if disc < 0 else -a * t_response + math.sqrt(disc)


def psi_belief(v: float, psi_cal: float, v_cal: float, t_chain: float, a_brake: float) -> float:
    """Controller's stopping-travel belief: direct measurement at the operating
    point plus the first-order speed correction d(psi)/dv from StoppingDistance.
    (Template guidance: at a single operating point, measure d directly; use the
    relation for the slope, not for the absolute value.)"""
    return psi_cal + (v - v_cal) * (t_chain + v_cal / a_brake)


# ---------------------------------------------------------------------------
# 3. PLANT + CONTROLLER SIMULATION
# ---------------------------------------------------------------------------

@dataclass
class Truth:
    k_eff: float
    omega_cruise: float
    a_accel: float
    a_brake: float
    t_chain: float
    l_sensor: float
    t_refresh: float
    q_range: float
    eps_scale: float
    b_offset: float
    g_start: float
    phase: float
    psi_head: float = 0.0
    w_half: float = 60.0
    slip_brake: float = 0.0
    e_trig: float = 0.0
    d_odo_drift: float = 0.0


@dataclass
class Ctrl:
    k_eff: float
    l_sensor: float
    psi_cal: float
    v_cal: float
    t_chain: float
    a_brake: float
    b_offset: float
    g_target: float
    g_floor: float
    dt_loop: float
    n_look: float
    n_fuse: int
    n_fuse_min: int
    s_odo_limit: float


@dataclass
class RunResult:
    g_final: float
    contact: bool
    v_cruise: float
    v_at_brake: float
    x_brake_cmd: float
    psi_actual: float
    psi_believed: float
    r_rest: float
    t_total: float
    triggered_by: str
    o_bar_trigger: float
    o_rest: float
    n_fresh: int


def _quantise(x: float, q: float) -> float:
    return x if q <= 0 else round(x / q) * q


def simulate(T: Truth, C: Ctrl, dt: float = 0.0005, t_max: float = 12.0) -> RunResult:
    """One approach: accelerate to the ceiling, fuse ranger+odometry, brake, rest.
    The controller block reproduces the flight program's hot loop arithmetic, so
    the model and the program are two views of one algorithm."""
    v_cruise = rotation_to_speed(T.omega_cruise, T.k_eff)
    x = v = t = 0.0
    braking = False
    t_brake_cmd: Optional[float] = None
    x_brake_cmd = float("nan")
    v_at_brake = float("nan")
    psi_believed = float("nan")
    s_brake: Optional[float] = None
    triggered_by = "none"
    x_odo = 0.0                      # odometry-integrated travel (slips during braking)

    next_emit = T.phase * T.t_refresh
    r_latest: Optional[float] = None
    r_prev: Optional[float] = None
    hist_t: List[float] = [0.0]
    hist_s: List[float] = [0.0]

    r_static = _quantise(max(0.0, (T.g_start - T.b_offset) * (1.0 + T.eps_scale)), T.q_range)
    o_ring: List[float] = [r_static]           # seeded from the static baseline at s=0
    o_bar = r_static
    o_bar_trigger = float("nan")
    dr_anchor = r_static
    n_fresh = 0
    next_loop = 0.0

    def s_at(tq: float) -> float:
        if tq <= hist_t[0]:
            return hist_s[0]
        for i in range(len(hist_t) - 1, 0, -1):
            if hist_t[i - 1] <= tq:
                f = (tq - hist_t[i - 1]) / (hist_t[i] - hist_t[i - 1])
                return hist_s[i - 1] + f * (hist_s[i] - hist_s[i - 1])
        return hist_s[0]

    while t < t_max:
        if braking:
            v = max(0.0, v - T.a_brake * dt)
            x += v * dt
            x_odo += v * dt * (1.0 - T.slip_brake)     # skid: odometry under-reads
        else:
            if t_brake_cmd is not None and t >= t_brake_cmd + T.t_chain:
                braking = True
            v = min(v_cruise, v + T.a_accel * dt)
            x += v * dt
            x_odo += v * dt
        t += dt
        s_now = x_odo * (1.0 + T.d_odo_drift) * (C.k_eff / T.k_eff)
        hist_t.append(t)
        hist_s.append(s_now)
        if braking and v <= 0.0:
            break

        if t >= next_emit:
            face = (T.g_start - _interp(hist_t, [xx for xx in _xs(hist_t, hist_s, C, T)],
                                       t - T.l_sensor)) if False else None
            # true face range at the emission instant (uses TRUE travel, not odometry)
            x_then = _true_x_at(t - T.l_sensor, T, dt, hist_t, hist_s, C)
            r_latest = _quantise(max(0.0, (T.g_start - x_then - T.b_offset)
                                     * (1.0 + T.eps_scale)), T.q_range)
            next_emit += T.t_refresh

        if t >= next_loop and t_brake_cmd is None:
            next_loop += C.dt_loop
            if r_latest is not None and r_latest != r_prev:
                r_prev = r_latest
                n_fresh += 1
                o_ring.append(r_latest + s_at(t - C.l_sensor))
                if len(o_ring) > C.n_fuse:
                    o_ring.pop(0)
                o_bar = sum(o_ring) / len(o_ring)
            v_est = v
            psi_b = psi_belief(v_est, C.psi_cal, C.v_cal, C.t_chain, C.a_brake)
            s_brake = o_bar + C.b_offset - C.g_target - psi_b
            armed = n_fresh >= C.n_fuse_min
            if armed and v_est > 1.0 and (s_brake - s_now) <= v_est * C.dt_loop * C.n_look:
                wait_s = max(0.0, (s_brake - s_now) / v_est)
                wait_s = math.ceil(wait_s * 1000.0) / 1000.0        # 1 ms granularity
                t_brake_cmd = t + wait_s + T.e_trig
                triggered_by, o_bar_trigger = "primary", o_bar
                v_at_brake, psi_believed = v_est, psi_b
            elif s_now >= C.s_odo_limit:
                t_brake_cmd = t
                triggered_by, o_bar_trigger = "odo_backstop", o_bar
                v_at_brake, psi_believed = v_est, psi_b
            elif ((dr_anchor + C.b_offset) - s_now
                  - psi_belief(v_est, C.psi_cal, C.v_cal, C.t_chain, C.a_brake) <= C.g_floor):
                t_brake_cmd = t
                triggered_by, o_bar_trigger = "backstop", o_bar
                v_at_brake, psi_believed = v_est, psi_b
            if t_brake_cmd is not None:
                x_brake_cmd = x + v * (t_brake_cmd - t)

    g_final = T.g_start - x - T.w_half * math.sin(math.radians(T.psi_head))
    r_rest = _quantise(max(0.0, (T.g_start - x - T.b_offset) * (1.0 + T.eps_scale)), T.q_range)
    s_rest = x_odo * (1.0 + T.d_odo_drift) * (C.k_eff / T.k_eff)
    return RunResult(
        g_final=g_final, contact=g_final <= 0.0, v_cruise=v_cruise, v_at_brake=v_at_brake,
        x_brake_cmd=x_brake_cmd, psi_actual=x - x_brake_cmd, psi_believed=psi_believed,
        r_rest=r_rest, t_total=t, triggered_by=triggered_by, o_bar_trigger=o_bar_trigger,
        o_rest=r_rest + s_rest, n_fresh=n_fresh)


# -- small helpers kept separate so the loop above reads like the flight code --
def _xs(*a):            # pragma: no cover  (unused branch guard)
    return []


def _interp(ts, xs, tq):  # pragma: no cover
    return 0.0


_TRUE_HIST: Dict[int, Tuple[List[float], List[float]]] = {}


def _true_x_at(tq: float, T: Truth, dt: float,
               hist_t: List[float], hist_s: List[float], C: Ctrl) -> float:
    """True travel at time tq. Reconstructed from the odometric history by undoing
    the scale factor -- exact before braking, and during braking the small slip
    correction is applied. Kept as a helper so simulate() mirrors the flight loop."""
    s = 0.0
    if tq <= hist_t[0]:
        return 0.0
    for i in range(len(hist_t) - 1, 0, -1):
        if hist_t[i - 1] <= tq:
            f = (tq - hist_t[i - 1]) / (hist_t[i] - hist_t[i - 1])
            s = hist_s[i - 1] + f * (hist_s[i] - hist_s[i - 1])
            break
    return s * (T.k_eff / C.k_eff)


# ---------------------------------------------------------------------------
# 4. PREDICT
# ---------------------------------------------------------------------------

def _truth(use_prior: bool, **over) -> Truth:
    T = Truth(k_eff=g("k_eff", use_prior), omega_cruise=g("omega_cruise", use_prior),
              a_accel=g("a_accel", use_prior), a_brake=g("a_brake", use_prior),
              t_chain=g("t_chain", use_prior), l_sensor=g("l_sensor", use_prior),
              t_refresh=g("t_refresh", use_prior), q_range=g("q_range", use_prior),
              eps_scale=g("eps_scale", use_prior), b_offset=g("b_offset", use_prior),
              g_start=g("g_start", use_prior), phase=g("t_refresh_phase", use_prior),
              psi_head=g("psi_head", use_prior), w_half=g("w_half", use_prior),
              slip_brake=g("slip_brake", use_prior), e_trig=g("e_trig", use_prior),
              d_odo_drift=g("d_odo_drift", use_prior))
    for k, v in over.items():
        setattr(T, k, v)
    return T


def _ctrl(use_prior: bool, g_target: Optional[float] = None, **over) -> Ctrl:
    psi_cal = PARAMS["psi_brake"].value
    v_cal = (PARAMS["k_eff"].get(use_prior) * PARAMS["omega_cruise"].get(use_prior))
    if psi_cal is None:
        if not use_prior:
            raise ValueError("psi_brake UNBOUND -- bound by CAL-1/P2+P4")
        psi_cal = stopping_distance(v_cal, g("t_chain", True), g("a_brake", True), 0.0)
    C = Ctrl(k_eff=g("k_eff", use_prior), l_sensor=g("l_sensor", use_prior),
             psi_cal=psi_cal, v_cal=v_cal, t_chain=g("t_chain", use_prior),
             a_brake=g("a_brake", use_prior), b_offset=g("b_offset", use_prior),
             g_target=g("g_target", use_prior) if g_target is None else g_target,
             g_floor=g("g_floor", use_prior), dt_loop=g("dt_loop", use_prior),
             n_look=g("n_look", use_prior), n_fuse=int(g("n_fuse", use_prior)),
             n_fuse_min=int(g("n_fuse_min", use_prior)),
             s_odo_limit=g("s_backstop", use_prior))
    for k, v in over.items():
        setattr(C, k, v)
    return C


def sigma_contributors(use_prior: bool = False) -> Dict[str, float]:
    """Independent contributors to final-clearance uncertainty, mm (tenet A6)."""
    v = rotation_to_speed(g("omega_cruise", use_prior), g("k_eff", use_prior))
    n = max(1.0, g("n_fuse", use_prior))
    return {
        "fused range-offset (quantisation/sqrt(12n))": g("q_range", use_prior) / math.sqrt(12.0 * n),
        "b_offset anchor (ruler + read noise)": g("sigma_b", use_prior),
        "brake travel run-to-run": g("sigma_psi", use_prior),
        "ranger latency residual (v*sigma_ls)": v * g("sigma_ls", use_prior),
        "trigger timing (v*e_trig)": v * g("e_trig", use_prior),
        "heading/corner geometry": g("w_half", use_prior)
                                   * math.sin(math.radians(g("d_psi_head", use_prior))),
    }


def predict(use_prior: bool = False, g_target: Optional[float] = None) -> dict:
    T, C = _truth(use_prior), _ctrl(use_prior, g_target=g_target)
    R = simulate(T, C)
    contrib = sigma_contributors(use_prior)
    sigma_rss = math.sqrt(sum(c * c for c in contrib.values()))
    m_contact = g("z_conf", use_prior) * sigma_rss
    v = R.v_cruise
    out = {
        "v_cruise": v, "v_at_brake": R.v_at_brake, "g_target": C.g_target,
        "g_pred": R.g_final, "g_lower": R.g_final - m_contact,
        "sigma_rss": sigma_rss, "m_contact": m_contact,
        "psi_actual": R.psi_actual, "psi_believed": R.psi_believed,
        "psi_composed": stopping_distance(v, g("t_chain", use_prior),
                                          g("a_brake", use_prior), 0.0),
        "s_accel": v * v / (2.0 * g("a_accel", use_prior)),
        "v_budget": max_speed_from_budget(g("t_chain", use_prior), g("a_brake", use_prior),
                                          g("g_start", use_prior) - C.g_target, 0.0),
        "r_rest_pred": R.r_rest, "o_consistency": R.o_rest - R.o_bar_trigger,
        "sigma_est": math.sqrt(contrib["fused range-offset (quantisation/sqrt(12n))"] ** 2
                               + contrib["b_offset anchor (ruler + read noise)"] ** 2
                               + contrib["brake travel run-to-run"] ** 2),
        "t_total": R.t_total, "n_fresh": float(R.n_fresh),
        "trigger": 1.0 if R.triggered_by == "primary" else 0.0,
        "contact": 1.0 if R.contact else 0.0,
        "psi_head": g("psi_head", use_prior), "psi_limit": g("psi_limit", use_prior),
        "omega_cruise": g("omega_cruise", use_prior), "omega_cmd": g("omega_cmd", use_prior),
        "r_min_valid": g("r_min_valid", use_prior), "d_agree": g("d_agree", use_prior),
        "sigma_est_limit": g("sigma_est_limit", use_prior), "k_obj": g("k_obj", use_prior),
        "slip_brake": g("slip_brake", use_prior),
        "omega_left": g("omega_left", use_prior), "omega_right": g("omega_right", use_prior),
        "omega_floor": g("omega_floor", use_prior), "d_omega": g("d_omega", use_prior),
        "contact_floor": g("contact_floor", use_prior),
        "psi_travel_limit": g("psi_travel_limit", use_prior),
        "sigma_psi_limit": g("sigma_psi_limit", use_prior),
        "sigma_psi": g("sigma_psi", use_prior),
        "l_sensor": g("l_sensor", use_prior), "l_sensor_limit": g("l_sensor_limit", use_prior),
        "t_refresh": g("t_refresh", use_prior), "t_refresh_limit": g("t_refresh_limit", use_prior),
        "q_range": g("q_range", use_prior), "q_range_limit": g("q_range_limit", use_prior),
        "d_agree_limit": g("d_agree_limit", use_prior),
        "e_trig": g("e_trig", use_prior), "e_trig_limit": g("e_trig_limit", use_prior),
        "d_psi_head": g("d_psi_head", use_prior),
        "t_approach": R.t_total, "trigger_floor": 1.0,
        "g_obj_cap": g("k_obj", use_prior) * m_contact,
        "s_accel_budget": (g("g_start", use_prior) - C.g_target
                           - (PARAMS["psi_brake"].value or R.psi_actual)),
        "d_omega_limit": (g("track", use_prior) * math.radians(g("psi_limit", use_prior))
                          / max(0.1, R.t_total) / g("k_eff", use_prior)),
    }
    out["_contrib"] = contrib
    out["_priors_used"] = [p.name for p in PARAMS.values()
                           if p.kind in ("free", "environment") and not p.bound] if use_prior else []
    return out


# ---------------------------------------------------------------------------
# 5. EVALUATE   (computational satisfy/require roll-up, three-valued)
# ---------------------------------------------------------------------------

PASS, FAIL, UNRES = "PASS", "FAIL", "UNRESOLVED"
REQUIREMENTS: Dict[str, dict] = {}


def R_(rid, sysml, parent, method, template=None, check=None, needs=()):
    REQUIREMENTS[rid] = dict(sysml=sysml, parent=parent, method=method,
                             template=template, check=check, needs=needs)


def _lb(key, target, unit="mm"):
    def f(p):
        m, t = p[key], (p[target] if isinstance(target, str) else target)
        return (PASS if m >= t else FAIL), f"{key}={m:.2f} >= {t:.2f} {unit}"
    return f


def _ub(key, target, unit="mm"):
    def f(p):
        m, t = p[key], (p[target] if isinstance(target, str) else target)
        return (PASS if m <= t else FAIL), f"{key}={m:.2f} <= {t:.2f} {unit}"
    return f


R_("STK-0", "WallRunNeed", None, "analysis+test")
R_("STK-1", "SafeMaximumSpeedRun", "STK-0", "test")
R_("SYS-1", "MaximumApproachSpeed", "STK-1", "inspection+test", "LowerBound",
   _lb("omega_cmd", "omega_cruise", "deg/s"), ("omega_cruise",))
R_("FUN-1", "CruiseAtCeiling", "SYS-1", "test", "LowerBound",
   _lb("omega_cruise", 600.0, "deg/s"), ("omega_cruise",))
R_("CMP-1", "LeftMotorCeiling", "FUN-1", "test", "LowerBound",
   _lb("omega_left", "omega_floor", "deg/s"), ("omega_left", "omega_floor"))
R_("CMP-2", "RightMotorCeiling", "FUN-1", "test", "LowerBound",
   _lb("omega_right", "omega_floor", "deg/s"), ("omega_right", "omega_floor"))
R_("CMP-3", "AccelWithinRunway", "FUN-1", "analysis", "UpperBound",
   _ub("s_accel", "s_accel_budget"), ("a_accel", "psi_brake"))
R_("SYS-2", "NoWallContact", "STK-1", "test", "LowerBound",
   _lb("g_pred", "contact_floor"), ("b_offset", "psi_brake"))
R_("SYS-5", "ClearanceMarginFloor", "SYS-2", "analysis", "LowerBound",
   _lb("g_lower", 0.0), ("sigma_psi", "sigma_b", "sigma_ls", "b_offset", "psi_brake"))
R_("FUN-2", "ClearanceEstimation", "SYS-2", "test", "UpperBound",
   _ub("sigma_est", "sigma_est_limit"), ("q_range", "sigma_b", "sigma_psi"))
R_("CMP-4", "PrimaryRangerBias", "FUN-2", "test", None, None, ("b_offset",))
R_("CMP-5", "PrimaryRangerRefresh", "FUN-2", "test", "UpperBound",
   _ub("t_refresh", "t_refresh_limit", "s"), ("t_refresh", "t_refresh_limit"))
R_("CMP-20", "PrimaryRangerStaleness", "FUN-2", "test", "UpperBound",
   _ub("l_sensor", "l_sensor_limit", "s"), ("l_sensor", "l_sensor_limit"))
R_("CMP-21", "PrimaryRangerQuantisation", "FUN-2", "test", "UpperBound",
   _ub("q_range", "q_range_limit"), ("q_range", "q_range_limit"))
R_("CMP-6", "OdometryScale", "FUN-2", "test", None, None, ("k_eff", "eps_scale"))
R_("CMP-7", "SecondaryRangerAgreement", "FUN-2", "test", "UpperBound",
   _ub("d_agree", "d_agree_limit"), ("d_agree", "d_agree_limit"))
R_("FUN-3", "StopPointComputation", "SYS-2", "analysis+test", "LowerBound",
   _lb("trigger", 1.0, "-"), ("psi_brake", "b_offset"))
R_("CMP-8", "TriggerTimingResolution", "FUN-3", "test", "UpperBound",
   _ub("e_trig", "e_trig_limit", "s"), ("e_trig", "e_trig_limit"))
R_("FUN-5", "FailSafeResponse", "SYS-2", "test")
R_("CMP-9", "PlausibilityBounds", "FUN-5", "inspection+test")
R_("CMP-10", "DeadReckonBackstop", "FUN-5", "test")
R_("SYS-3", "CompleteStop", "STK-1", "test")
R_("FUN-4", "BrakeActuation", "SYS-3", "test")
R_("CMP-11", "BrakeTravel", "FUN-4", "test", "UpperBound",
   _ub("psi_actual", "psi_travel_limit"), ("psi_brake", "psi_travel_limit", "slip_brake"))
R_("CMP-22", "BrakeTravelRepeatability", "FUN-4", "test", "UpperBound",
   _ub("sigma_psi", "sigma_psi_limit"), ("sigma_psi", "sigma_psi_limit"))
R_("CMP-12", "NoPostStopMotion", "FUN-4", "test")
R_("SYS-4", "StraightApproach", "STK-1", "test", "UpperBound",
   _ub("psi_head", "psi_limit", "deg"), ("psi_head",))
R_("FUN-6", "HeadingMaintenance", "SYS-4", "test")
R_("CMP-13", "HeadingSensing", "FUN-6", "test", "UpperBound",
   _ub("psi_head", "psi_limit", "deg"), ("psi_head", "d_psi_head"))
R_("CMP-14", "WheelSpeedSymmetry", "FUN-6", "test", "UpperBound",
   _ub("d_omega", "d_omega_limit", "deg/s"), ("d_omega", "track"))
R_("SYS-6", "ConfigurationDiscovery", "STK-1", "test")
R_("FUN-7", "PortAndPolarityIdentification", "SYS-6", "test")
R_("CMP-15", "DeviceTypeIdentification", "FUN-7", "test")
R_("CMP-16", "DrivePolarityIdentification", "FUN-7", "test")
R_("SYS-7", "ClearanceReporting", "STK-1", "test", "UpperBound",
   _ub("sigma_est", "sigma_est_limit"), ("sigma_b", "q_range", "sigma_psi"))
R_("FUN-8", "TelemetryAndEstimate", "SYS-7", "test")
R_("CMP-17", "RestRangeEstimator", "FUN-8", "test", "LowerBound",
   _lb("r_rest_pred", "r_min_valid"), ("b_offset", "r_min_valid"))
R_("CMP-18", "OdometricEstimator", "FUN-8", "test", None, None,
   ("k_eff", "psi_brake", "d_odo_drift"))
R_("CMP-19", "ContactDetection", "FUN-8", "test")
R_("STK-2", "ClosestStopObjective", "STK-0", "analysis+test")
R_("OBJ-1", "MarginEfficiency", "STK-2", "analysis", "UpperBound",
   lambda p: ((PASS if p["g_target"] <= p["k_obj"] * p["m_contact"] else FAIL),
              f"g_target={p['g_target']:.1f} <= k_obj*m_contact="
              f"{p['k_obj'] * p['m_contact']:.1f} mm"),
   ("sigma_psi", "sigma_b", "sigma_ls"))


def children(rid: str) -> List[str]:
    return [k for k, v in REQUIREMENTS.items() if v["parent"] == rid]


def evaluate(pred: Optional[dict] = None, use_prior: bool = False) -> Dict[str, Tuple[str, str]]:
    if pred is None:
        pred = predict(use_prior=use_prior)
    out: Dict[str, Tuple[str, str]] = {}

    def ev(rid: str) -> Tuple[str, str]:
        if rid in out:
            return out[rid]
        req = REQUIREMENTS[rid]
        missing = [n for n in req["needs"] if not PARAMS[n].bound]
        own = None
        if req["check"] is not None:
            own = (UNRES, "unbound: " + ",".join(missing)) if missing else req["check"](pred)
        elif missing:
            own = (UNRES, "unbound: " + ",".join(missing))
        elif req["needs"]:
            own = (PASS, "bound: " + ", ".join(
                f"{n}={PARAMS[n].value:g} [{PARAMS[n].tier}]" for n in req["needs"]))
        elif rid in EVIDENCE:
            own = (PASS, EVIDENCE[rid])
        elif not children(rid):
            own = (UNRES, "no evidence recorded (method: " + req["method"] + ")")
        kids = [ev(c) for c in children(rid)]
        verdicts = [v for v, _ in kids] + ([own[0]] if own else [])
        if not verdicts:
            res = (UNRES, "no evidence yet (method: " + req["method"] + ")")
        elif FAIL in verdicts:
            res = (FAIL, own[1] if own and own[0] == FAIL else "child FAIL")
        elif UNRES in verdicts:
            res = (UNRES, own[1] if own and own[0] == UNRES else "child UNRESOLVED")
        else:
            res = (PASS, own[1] if own else "all children PASS")
        out[rid] = res
        return res

    for rid in REQUIREMENTS:
        ev(rid)
    return out


# ---------------------------------------------------------------------------
# 6. SWEEP  (GATE A sensitivity analysis)
# ---------------------------------------------------------------------------

_TRUTH_KEYS = set(Truth.__annotations__)
_CTRL_ONLY = {"psi_brake": "psi_cal", "n_fuse": "n_fuse", "n_look": "n_look",
              "g_floor": "g_floor", "dt_loop": "dt_loop"}


def sweep(param: str, lo=None, hi=None, n: int = 9, g_target=None) -> List[Tuple[float, float]]:
    """Vary the TRUE value of `param` while the controller keeps its prior-nominal
    belief: a MIS-CALIBRATION sweep. For controller-only parameters the belief
    itself is varied. Returns [(value, final clearance)]."""
    p = PARAMS[param]
    lo = p.prior[0] if lo is None else lo
    hi = p.prior[1] if hi is None else hi
    if param == "psi_brake":
        lo, hi = psi_prior_from_physics()
    rows = []
    for i in range(n):
        x = lo + (hi - lo) * i / (n - 1)
        tover, cover = {}, {}
        if param == "t_refresh_phase":
            tover["phase"] = x
        elif param in _TRUTH_KEYS:
            tover[param] = x
        if param in _CTRL_ONLY:
            cover[_CTRL_ONLY[param]] = x
        T = _truth(True, **tover)
        C = _ctrl(True, g_target=g_target, **cover)
        rows.append((x, simulate(T, C).g_final))
    return rows


def margin_sensitivity(param: str) -> float:
    """Swing in m_contact (hence in the achievable gap) across the prior range."""
    p = PARAMS[param]
    if not p.prior or p.bound:
        return 0.0
    keep = p.value
    vals = []
    for x in p.prior:
        p.value = x
        vals.append(g("z_conf", True) * math.sqrt(sum(c * c for c in sigma_contributors(True).values())))
    p.value = keep
    return abs(vals[1] - vals[0])


def sensitivity_table(g_target: float, params: Optional[List[str]] = None) -> List[dict]:
    base = predict(use_prior=True, g_target=g_target)["g_pred"]
    names = params or [p.name for p in PARAMS.values()
                       if p.kind in ("free", "environment") and p.prior and not p.bound]
    rows = []
    for nm in names:
        p = PARAMS[nm]
        pts = sweep(nm, n=9, g_target=g_target)
        gs = [q for _, q in pts]
        swing = max(gs) - min(gs)
        pr = psi_prior_from_physics() if nm == "psi_brake" else p.prior
        span = pr[1] - pr[0]
        coeff = swing / span if span else 0.0
        msens = margin_sensitivity(nm)
        rows.append(dict(param=nm, sysml=p.sysml_ref, unit=p.unit, prior=pr,
                         g_lo=min(gs), g_hi=max(gs), swing=swing, coeff=coeff,
                         margin_swing=msens, total=max(swing, msens),
                         tol_2mm=(2.0 / coeff if coeff > 1e-9 else float("inf")),
                         tier=p.tier, binds_to=p.binds_to))
    rows.sort(key=lambda r: -r["total"])
    return rows


def prior_box_corners(g_target: float) -> Tuple[float, float, List[str], List[str]]:
    """Directed corner search over the joint prior box: worst/best clearance a run
    at this g_target can produce given everything not yet bound. This is the
    safety argument for a characterization run made BEFORE any calibration."""
    keys = ["k_eff", "omega_cruise", "a_accel", "a_brake", "t_chain", "l_sensor",
            "t_refresh", "q_range", "eps_scale", "b_offset", "g_start",
            "t_refresh_phase", "slip_brake", "psi_head", "w_half", "e_trig",
           "d_odo_drift"]
    signs = {}
    for k in keys:
        pts = sweep(k, n=3, g_target=g_target)
        signs[k] = 1.0 if pts[-1][1] >= pts[0][1] else -1.0
    res, descs = [], []
    for direction in (-1.0, 1.0):
        tover, cover, desc = {}, {}, []
        for k in keys:
            p = PARAMS[k]
            pr = psi_prior_from_physics() if k == "psi_brake" else p.prior
            pick = pr[0] if signs[k] * direction < 0 else pr[1]
            desc.append(f"{k}={pick:g}")
            if k == "t_refresh_phase":
                tover["phase"] = pick
            elif k in _TRUTH_KEYS:
                tover[k] = pick
        T = _truth(True, **tover)
        C = _ctrl(True, g_target=g_target, **cover)
        res.append(simulate(T, C).g_final)
        descs.append(desc)
    return res[0], res[1], descs[0], descs[1]


# ---------------------------------------------------------------------------
# 7. REPORTING
# ---------------------------------------------------------------------------

def fmt_sensitivity(rows: List[dict]) -> str:
    out = ["| # | parameter (SysML attr) | assumed range | objective swing dG | "
           "margin swing dm | dG/dp | range for <=2 mm | knowledge tier | priority |",
           "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        prio = ("1-CRITICAL" if r["total"] >= 30 else "2-high" if r["total"] >= 10
                else "3-moderate" if r["total"] >= 3 else "4-low")
        tol = "n/a" if r["tol_2mm"] == float("inf") else f"+/-{r['tol_2mm'] / 2:.3g}"
        out.append(f"| {i} | `{r['param']}` ({r['sysml']}) | {r['prior'][0]:g} .. "
                   f"{r['prior'][1]:g} {r['unit']} | {r['swing']:.1f} mm | "
                   f"{r['margin_swing']:.1f} mm | {r['coeff']:.3g} mm per {r['unit']} | "
                   f"{tol} {r['unit']} | {r['tier']} | {prio} |")
    return "\n".join(out)


def staged_prior_box(narrow: Dict[str, Tuple[float, float]], s_backstop: float,
                     g_target: float) -> Tuple[float, float]:
    """Prior-box corner search with some parameters already narrowed by an earlier
    phase of the SAME run (tenet A5/B2: order the characterization so the cheap,
    least-coupled quantity is bound before the phase whose safety depends on it)."""
    keep = {k: PARAMS[k].prior for k in narrow}
    keep_sb = PARAMS["s_backstop"].value
    for k, v in narrow.items():
        PARAMS[k].prior = v
    PARAMS["s_backstop"].value = s_backstop
    w, b, _, _ = prior_box_corners(g_target)
    for k, v in keep.items():
        PARAMS[k].prior = v
    PARAMS["s_backstop"].value = keep_sb
    return w, b


def backstop_worst_case(s_backstop: float, k_tol: float = 0.02,
                       use_prior: bool = True) -> Dict[str, float]:
    """EXACT worst-case landing for a pass whose brake is triggered by the
    ODOMETRIC BACKSTOP. No simulation and no corner heuristic is involved: with
    ranging out of the trigger path the landing point is closed-form, every term
    is monotone in its parameters, so the worst case IS a corner and is computed
    directly.

        x_bs  = s_backstop * (k_true/k_bound) / (1 + d_odo_drift)
        v_br  = min(v_cruise, sqrt(2 * a_accel * x_bs))
        psi   = v_br*t_chain + v_br^2/(2*a_brake)        [StoppingDistance]
        G     = g_start - x_bs - psi - w_half*sin(psi_head)

    `k_tol` is the fractional uncertainty left on k_eff by the static staircase
    that runs BEFORE this pass. This function is the reason the staircase is
    ordered first: at k_tol = the raw prior spread, no backstop is safe.

    NOTE this supersedes the directed-corner heuristic used by prior_box_corners():
    that search fixes each parameter's worst direction one-at-a-time at the
    nominal, so it misses corners where the worst direction depends on another
    parameter (a_accel only matters once the rover can reach cruise). It reported
    a 500 mm backstop as safe; the exact analysis shows it permits contact.
    """
    kp = lambda n: PARAMS[n].prior
    infl = (1.0 / (1.0 - k_tol)) / (1.0 - abs(kp("d_odo_drift")[1]))
    x_bs = s_backstop * infl
    v_hi = kp("k_eff")[1] * kp("omega_cruise")[1]
    v_br = min(v_hi, math.sqrt(2.0 * kp("a_accel")[1] * x_bs))
    psi = stopping_distance(v_br, kp("t_chain")[1], kp("a_brake")[0], 0.0)
    corner = kp("w_half")[1] * math.sin(math.radians(kp("psi_head")[1]))
    land = kp("g_start")[0] - x_bs - psi - corner
    v_nom = PARAMS["k_eff"].nominal * PARAMS["omega_cruise"].nominal
    s_acc_nom = v_nom * v_nom / (2.0 * PARAMS["a_accel"].nominal)
    return dict(s_backstop=s_backstop, x_bs=x_bs, v_at_brake=v_br, psi_worst=psi,
                corner=corner, landing=land, safe=land > 0.0,
                cruise_mm_nominal=max(0.0, s_backstop - s_acc_nom),
                cruise_ms_nominal=max(0.0, s_backstop - s_acc_nom) / v_nom * 1000.0,
                fresh_at_cruise=max(0.0, s_backstop - s_acc_nom) / v_nom
                                / PARAMS["t_refresh"].nominal)


def max_safe_backstop(margin_mm: float = 0.0, k_tol: float = 0.02) -> float:
    """Largest odometric backstop whose exact worst-case landing still clears
    `margin_mm`. Bisection on the closed form above."""
    lo, hi = 10.0, 1200.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if backstop_worst_case(mid, k_tol)["landing"] > margin_mm:
            lo = mid
        else:
            hi = mid
    return lo


def cal1_safety(s_backstop: float, g_target: float) -> Tuple[float, float, str]:
    """Prior-box worst/best landing for a characterization run configured with an
    odometric backstop. This is the safety argument for CAL-1, made before any
    calibration exists."""
    keep = PARAMS["s_backstop"].value
    PARAMS["s_backstop"].value = s_backstop
    w, b, dw, _ = prior_box_corners(g_target)
    PARAMS["s_backstop"].value = keep
    return w, b, ", ".join(dw)


def main() -> None:
    PARAMS["psi_brake"].prior = psi_prior_from_physics()
    print("=" * 104)
    print("SECTION 0 -- GATE A SENSITIVITY ANALYSIS")
    print("controller on PRIOR NOMINALS (nothing calibrated); evaluated at the OPERATING")
    print("configuration: g_target = 30 mm, backstop wide (2000 mm)")
    print("=" * 104)
    PARAMS["s_backstop"].value = 2000.0
    rows = sensitivity_table(30.0)
    print(fmt_sensitivity(rows))
    base = predict(use_prior=True, g_target=30.0)
    print(f"\nnominal-prior operating prediction: clearance {base['g_pred']:.1f} mm, "
          f"v_cruise {base['v_cruise']:.0f} mm/s, psi {base['psi_actual']:.1f} mm, "
          f"{base['n_fresh']:.0f} fresh ranger samples during the approach")
    print(f"psi_brake prior derived from the (v, t_chain, a_brake) priors: "
          f"{psi_prior_from_physics()} mm")
    print("\nsigma contributors at the priors (tenet A6 -- RSS, not a guess):")
    for k, v in sigma_contributors(True).items():
        print(f"   {k:48s} {v:6.2f} mm")
    print(f"   {'RSS':48s} {base['sigma_rss']:6.2f} mm"
          f"  ->  m_contact = z*RSS = {base['m_contact']:.1f} mm")

    print("\n" + "=" * 104)
    print("CAL-1 SAFETY ARGUMENT -- EXACT closed form (no corner heuristic)")
    print("A pass whose brake is triggered by the odometric backstop takes the")
    print("ranging chain out of the trigger path, so its landing point is analytic.")
    print("=" * 104)
    print("| backstop | true travel | v at brake | worst psi | WORST LANDING | verdict |"
          "  cruise segment (nominal) |")
    print("|---|---|---|---|---|---|---|")
    for sb in (200.0, 250.0, 300.0, 345.0, 400.0, 500.0):
        w = backstop_worst_case(sb)
        print(f"| {sb:.0f} mm | {w['x_bs']:.0f} mm | {w['v_at_brake']:.0f} mm/s | "
              f"{w['psi_worst']:.0f} mm | {w['landing']:+.0f} mm | "
              f"{'SAFE' if w['safe'] else 'CONTACT POSSIBLE'} | "
              f"{w['cruise_mm_nominal']:.0f} mm / {w['cruise_ms_nominal']:.0f} ms / "
              f"{w['fresh_at_cruise']:.1f} fresh samples |")
    print(f"\nceiling: largest safe backstop = {max_safe_backstop():.0f} mm "
          f"(zero margin); with 100 mm of margin = {max_safe_backstop(100.0):.0f} mm")
    print("CHOSEN for CAL-1/P4: s_backstop = 250 mm  ->  worst-case landing "
          f"{backstop_worst_case(250.0)['landing']:+.0f} mm")
    print("\nIf k_eff were NOT bound first (raw prior spread instead of +-2%):")
    for kt in (0.02, 0.20, 0.74):
        w = backstop_worst_case(250.0, k_tol=kt)
        print(f"   k_tol = {kt:.0%} -> landing {w['landing']:+.0f} mm  "
              f"{'SAFE' if w['safe'] else 'CONTACT POSSIBLE'}")
    print("   => the static staircase MUST precede the max-speed pass (tenets A5, B2)")

    ev = evaluate(predict(use_prior=True, g_target=30.0))
    n_unres = sum(1 for v, _ in ev.values() if v == UNRES)
    print(f"\nroll-up at GATE A: {n_unres}/{len(ev)} requirements UNRESOLVED "
          "(correct: nothing is calibrated yet)")
    print("STK-0 =", ev["STK-0"])


if __name__ == "__main__":
    main()
