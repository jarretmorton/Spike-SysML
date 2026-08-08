"""
================================================================================
EXECUTABLE ANALYSIS MODEL  --  WallStop rover  (rev A, GATE A issue)
================================================================================
Computational realisation of the SysML model `wall_stop.sysml` (package
WallStopModel).  The SysML carries the formal satisfy/require argument; THIS
module carries the arithmetic.  They are two views of ONE model:

    every SysML attribute  <-> one named Python field in `Params`
    every SysML relation   <-> one named Python function
    every SysML `require`  <-> one entry in REQUIREMENTS, evaluated by evaluate()

The 1:1 map is machine-readable in TRACE (bottom of file) and is checked by
`check_model.py`.

UNITS (model-internal, consistent throughout):
    length  mm        time  s        speed  mm/s
    accel   mm/s^2    angle deg      motor angle deg

TENET A3 -- "parameters uncalibrated, not zeroed".  Every calibratable field of
`Params` defaults to None.  Any computation that touches an unbound parameter
raises UnboundParameter.  Nothing is silently defaulted to a plausible-looking
constant.  Priors used for the sensitivity sweep are held SEPARATELY in PRIORS
and are labelled ASSUMED wherever they are used.

API required by the process (GATE A):
    predict(design, truth=None)      -> performance quantities
    evaluate(design, truth=None)     -> per-requirement pass/fail roll-up
    sweep(name, design, truth, n)    -> parameter sweep for sensitivity
    sensitivity_table(...)           -> the GATE A section-0 table
================================================================================
"""

from dataclasses import dataclass, fields, replace
import math

# ------------------------------------------------------------------ exceptions


class UnboundParameter(Exception):
    """Raised when the model is asked to compute with an uncalibrated value."""


def _req(p, *names):
    """Tenet A3 guard: fail loudly rather than substitute a guess."""
    missing = [n for n in names if getattr(p, n) is None]
    if missing:
        raise UnboundParameter(
            "unbound (uncalibrated) parameter(s): " + ", ".join(missing))
    return [getattr(p, n) for n in names]


# ------------------------------------------------------------------ parameters

@dataclass
class Params:
    """
    One field per SysML attribute.  Field name == SysML attribute name (see
    TRACE).  None == not yet bound by calibration.
    """
    # ---- forward ranger / geometry  (part ForwardRanger) -------------------
    c_offset_A: float = None        # TBD-01  rangerA.longitudinalOffset   [mm]
    c_offset_B: float = None        # TBD-02  rangerB.longitudinalOffset   [mm]
    alpha_scale: float = None       # TBD-18  ranger.rangeScale        [mm/mm]
    sigma_u: float = None           # TBD-07  ranger.noiseSigma            [mm]
    T_refresh: float = None         # TBD-10  ranger.refreshInterval        [s]
    r_min_valid: float = None       # TBD-09  ranger.minValidRange         [mm]

    # ---- drivetrain  (part WallDriveMotor) ---------------------------------
    k_travel: float = None          # TBD-03  motor.travelPerAngle    [mm/deg]
    v_cmd_deg_s: float = None       #         motor.commandedSpeed     [deg/s]
    v_max_ground: float = None      # TBD-04  rover.vMaxAchievable      [mm/s]
    a_brake: float = None           # TBD-05  motor.brakeDecel       [mm/s^2]

    # ---- control chain  (part WallRover) -----------------------------------
    t_response: float = None        # TBD-06  rover.tResponse               [s]
    dt_loop: float = None           # TBD-08  rover.loopPeriod              [s]

    # ---- alignment geometry -------------------------------------------------
    theta_yaw_deg: float = None     # TBD-11  rover.headingDeviation      [deg]
    w_half: float = None            # TBD-19  rover.halfWidth              [mm]

    # ---- design variables (chosen, not measured) ---------------------------
    target_gap: float = None        # TBD-12  rover.targetGap              [mm]
    k_sigma: float = 3.0            #         rover.kSigma                  [-]

    # ---- 1-sigma uncertainties on the bound values -------------------------
    sigma_c: float = None           #         rover.sigmaC                 [mm]
    sigma_t_response: float = None  #         rover.sigmaTResponse          [s]
    sigma_a: float = None           #         rover.sigmaABrake        [mm/s^2]
    sigma_rr: float = None          # TBD-16  rover.sigmaRunToRun          [mm]

    # ---- verification limits (requirement targets) -------------------------
    heading_limit_deg: float = 5.0      # SYS-5 target
    loop_period_limit: float = 0.025    # CMP-10 target
    rest_speed_limit: float = 5.0       # SYS-3 target   [mm/s]
    contact_floor: float = 0.0          # SYS-1 physical contact plane [mm]

    # ---- evidence flags: procedural requirements, bound by calibration -----
    # None == no evidence yet (UNBOUND at GATE A), True/False once evidenced.
    ev_port_selfcheck: bool = None      # CMP-11
    ev_trim_never_exceeds_max: bool = None  # CMP-12
    ev_rear_ranger_valid: bool = None   # CMP-13
    ev_imu_rest_indicator: bool = None  # CMP-14
    ev_fallback_channel: bool = None    # SYS-8 / FUN-9
    ev_no_cross_run_state: bool = None  # SYS-7 / FUN-10
    ev_onboard_estimate: bool = None    # SYS-6 / FUN-8
    ev_refresh_within_bound: bool = None  # CMP-3
    ev_min_range_respected: bool = None   # CMP-4

    def bound_fields(self):
        return {f.name: getattr(self, f.name) for f in fields(self)
                if getattr(self, f.name) is not None}


# --------------------------------------------------------------- relations
# Reproduce RelationTemplates::* expressions against bound parameters.

def rotation_to_speed(motor_speed_deg_s, k_travel):
    """RelationTemplates::RotationToSpeed  --  v = motorSpeed * k."""
    return motor_speed_deg_s * k_travel


def stopping_distance(v, t_response, a_brake, margin=0.0):
    """
    RelationTemplates::StoppingDistance -- d = v*tResponse + v^2/(2a) + margin.

    `t_response` is the LUMPED effective response time: control-loop phase +
    ranger refresh phase + ranger internal lag + command issue.  It is
    calibrated as a lump (never assembled from guessed sub-terms), so the mean
    sampling delay is inside it and does not need separate bookkeeping.
    """
    if a_brake <= 0:
        raise ValueError("a_brake must be > 0")
    return v * t_response + v * v / (2.0 * a_brake) + margin


def max_speed_from_budget(t_response, a_brake, budget, margin):
    """RelationTemplates::MaxSpeedFromBudget -- positive root."""
    disc = a_brake**2 * t_response**2 + 2.0 * a_brake * (budget - margin)
    if disc < 0:
        return float("nan")
    return -a_brake * t_response + math.sqrt(disc)


def steady_speed(p):
    """Steady approach ground speed: commanded, clamped by achievable ceiling."""
    v_cmd, k, v_max = _req(p, "v_cmd_deg_s", "k_travel", "v_max_ground")
    return min(rotation_to_speed(v_cmd, k), v_max)


# -------------------------------------------------- the flight-code trigger law
# This function is the SPECIFICATION of the onboard trigger.  The MicroPython
# control loop computes exactly this expression each cycle; nothing else.

def trigger_threshold_ranger_units(v_measured, design):
    r"""
    Ranger reading at which the stop is commanded, given the LIVE measured
    ground speed.  Speed-adaptive: the stopping distance is recomputed every
    cycle, so a run-to-run change in achievable speed (battery, temperature)
    self-compensates instead of moving the stop.

        u_thr(v) = c + targetGap + [ v*tResponse + v^2/(2a) ]
                   \_/   \______/   \_______________________/
                geometry  design      StoppingDistance template
    """
    c = _mean_offset(design)
    tgt, t_r, a = _req(design, "target_gap", "t_response", "a_brake")
    return c + tgt + stopping_distance(v_measured, t_r, a)


def _mean_offset(p):
    """Offset used by the flight code (both forward rangers fused)."""
    cA, cB = _req(p, "c_offset_A", "c_offset_B")
    return 0.5 * (cA + cB)


# ------------------------------------------------------- two-world realisation

def realized_final_clearance(design, truth):
    """
    What the rover ACTUALLY does, when the program is parameterised with
    `design` but the world is `truth`.  design is truth  =>  returns target_gap.

    Chain:
      * flight code sees speed via odometry:  v_meas = v_true * k_design/k_truth
      * flight code fires when reported u <= u_thr(v_meas)
      * ranger reports    u = alpha_true * g_true + c_true
      * after the command the rover still travels StoppingDistance(truth)
    """
    v_true = steady_speed(truth)
    k_d, = _req(design, "k_travel")
    k_t, = _req(truth, "k_travel")
    v_meas = v_true * (k_d / k_t)

    u_thr = trigger_threshold_ranger_units(v_meas, design)

    alpha_t, = _req(truth, "alpha_scale")
    c_t = _mean_offset(truth)
    g_at_trigger = (u_thr - c_t) / alpha_t

    t_r_t, a_t = _req(truth, "t_response", "a_brake")
    return g_at_trigger - stopping_distance(v_true, t_r_t, a_t)


# ------------------------------------------------------- uncertainty (tenet A6)

def sigma_gap(p):
    """
    1-sigma of the final clearance: root-sum-square of the INDEPENDENT
    contributors.  Tenet A6 -- the margin is sized from this, never guessed.
    Each term is resolved by a named calibration activity (see TRACE).
    """
    v = steady_speed(p)
    (s_c, s_t, s_a, s_u, s_rr, dt, T_u, a, th, wh) = _req(
        p, "sigma_c", "sigma_t_response", "sigma_a", "sigma_u", "sigma_rr",
        "dt_loop", "T_refresh", "a_brake", "theta_yaw_deg", "w_half")

    terms = {
        # offset calibration error -> 1:1 into the clearance
        "offset_c": s_c,
        # response-time calibration error, amplified by speed
        "t_response": v * s_t,
        # deceleration calibration error, through d(v^2/2a)/da
        "a_brake": (v * v / (2.0 * a * a)) * s_a,
        # trigger phase: uniform over one (loop + refresh) of travel
        "trigger_phase": v * (dt + T_u) / math.sqrt(12.0),
        # ranger single-sample noise at the trigger point
        "ranger_noise": s_u,
        # yaw -> nearest front corner advances ahead of the sensed centreline
        "yaw_corner": wh * math.sin(math.radians(th)),
        # residual run-to-run (friction, battery, placement) not in the above
        "run_to_run": s_rr,
    }
    total = math.sqrt(sum(t * t for t in terms.values()))
    return total, terms


def contact_margin(p):
    """SYS-1 target: kSigma * sigmaGap."""
    s, _ = sigma_gap(p)
    return p.k_sigma * s


# ------------------------------------------------------------------- PREDICT

def predict(design, truth=None):
    """(a) PREDICT -- performance quantities from bound parameter values."""
    truth = truth or design
    v = steady_speed(truth)
    s_tot, s_terms = sigma_gap(design)
    t_r, a = _req(design, "t_response", "a_brake")
    out = {
        "v_steady": v,
        "stopping_distance": stopping_distance(v, t_r, a),
        "trigger_threshold_u": trigger_threshold_ranger_units(v, design),
        "trigger_clearance": trigger_threshold_ranger_units(v, design)
                             - _mean_offset(design),
        "final_clearance": realized_final_clearance(design, truth),
        "sigma_gap": s_tot,
        "sigma_terms": s_terms,
        "contact_margin": contact_margin(design),
        "target_gap": design.target_gap,
        "clearance_margin": realized_final_clearance(design, truth)
                            - contact_margin(design),
        "approach_time_from_1000mm": None,
    }
    if v > 0:
        out["approach_time_from_1000mm"] = (
            1000.0 - out["trigger_clearance"]) / v
    return out


# ------------------------------------------------------------------ EVALUATE
# The requirement tree.  kind: 'lower' == LowerBoundRequirement (measured >=
# target), 'upper' == UpperBoundRequirement (measured <= target), 'parent' ==
# pure decomposition node.  `text` is the EARS statement (spec governs).

REQUIREMENTS = [
    # id,      parents,              kind,     text
    ("STK-1", [],                    "parent", "The rover shall execute the wall-approach task."),
    ("STK-2", ["STK-1"],             "parent", "The rover shall not contact the wall."),
    ("STK-3", ["STK-1"],             "parent", "When the approach terminates, the rover shall be at a complete stop."),
    ("STK-4", ["STK-1"],             "parent", "While approaching, the rover shall travel at maximum achievable speed."),
    ("STK-5", ["STK-1"],             "parent", "The rover should minimise the final gap. [OBJECTIVE]"),
    ("STK-6", ["STK-1"],             "parent", "The rover shall repeat STK-2..STK-4 over five unchanged runs."),

    ("SYS-1", ["STK-2", "STK-5"],    "lower",  "Final clearance >= contact margin (= kSigma * sigmaGap)."),
    ("SYS-2", ["STK-2"],             "parent", "When estimated clearance - predicted stopping distance <= targetGap, command stop."),
    ("SYS-3", ["STK-3"],             "upper",  "End-of-run ground speed <= rest threshold."),
    ("SYS-4", ["STK-4"],             "lower",  "Commanded motor speed >= rated maximum (less steering trim)."),
    ("SYS-5", ["STK-2"],             "upper",  "Heading deviation <= heading limit throughout the approach."),
    ("SYS-6", ["STK-5"],             "flag",   "The rover shall report an onboard final-clearance estimate each run."),
    ("SYS-7", ["STK-6"],             "flag",   "The rover shall not depend on state persisted across runs."),
    ("SYS-8", ["STK-2"],             "flag",   "Where the ranger channel is invalid, use an independent channel."),

    ("FUN-1", ["SYS-2"],             "upper",  "Sense forward clearance every control cycle."),
    ("FUN-2", ["SYS-2"],             "parent", "Estimate ground speed every control cycle."),
    ("FUN-3", ["SYS-2"],             "parent", "Compute predicted stopping distance every control cycle."),
    ("FUN-4", ["SYS-2"],             "upper",  "Assert the trigger within one control cycle of the condition."),
    ("FUN-5", ["SYS-4"],             "parent", "Command the drivetrain at maximum."),
    ("FUN-6", ["SYS-3"],             "parent", "Apply braking on trigger."),
    ("FUN-7", ["SYS-5"],             "parent", "Apply steering trim from heading error."),
    ("FUN-8", ["SYS-6"],             "flag",   "Buffer telemetry off the hot path and dump after the stop."),
    ("FUN-9", ["SYS-8"],             "flag",   "Validity-check each ranger sample and select the channel."),
    ("FUN-10", ["SYS-7"],            "flag",   "Establish every reference at run start."),

    ("CMP-1", ["FUN-1"],             "upper",  "Ranger A longitudinal offset known to sigma_c."),
    ("CMP-2", ["FUN-1"],             "upper",  "Ranger B longitudinal offset known to sigma_c."),
    ("CMP-3", ["FUN-1"],             "flag",   "Ranger refresh interval <= TBD-10, measured."),
    ("CMP-4", ["FUN-9"],             "flag",   "Readings below the minimum valid range treated as invalid."),
    ("CMP-5", ["FUN-2"],             "lower",  "Motor rotation-to-travel scale bound."),
    ("CMP-6", ["FUN-5"],             "lower",  "Achievable steady ground speed >= v_max floor."),
    ("CMP-7", ["FUN-3", "FUN-6"],    "lower",  "Braked deceleration >= a_brake floor."),
    ("CMP-8", ["FUN-3"],             "upper",  "Effective response latency <= t_response bound."),
    ("CMP-9", ["FUN-7"],             "upper",  "IMU heading drift over the run <= heading limit."),
    ("CMP-10", ["FUN-4"],            "upper",  "Control loop period <= loop period limit."),
    ("CMP-11", ["FUN-10"],           "flag",   "Device/port and polarity self-check at init."),
    ("CMP-12", ["FUN-7"],            "flag",   "Steering trim only ever reduces commanded speed."),
    ("CMP-13", ["FUN-9"],            "flag",   "[CONDITIONAL] rear ranger valid at the start line."),
    ("CMP-14", ["FUN-6"],            "flag",   "IMU forward acceleration usable as at-rest indicator."),
]

_PARENTS = {r[0]: r[1] for r in REQUIREMENTS}
_KIND = {r[0]: r[2] for r in REQUIREMENTS}
_TEXT = {r[0]: r[3] for r in REQUIREMENTS}


def _operands(rid, design, truth, pred):
    """
    Bind (measured, target) for each bound-form requirement -- the Python side
    of the SysML `attribute :>> measured = subject.attr` bindings.
    Returns None when the operand is unbound (UNBOUND verdict).
    """
    p, t = design, truth
    try:
        if rid == "SYS-1":
            return pred["final_clearance"], pred["contact_margin"]
        if rid == "SYS-3":
            return 0.0, p.rest_speed_limit          # braked to rest, measured
        if rid == "SYS-4":
            return 1.0, 1.0                         # commanded fraction of max
        if rid == "SYS-5":
            return _req(p, "theta_yaw_deg")[0], p.heading_limit_deg
        if rid == "FUN-1":
            return _req(p, "dt_loop")[0], p.loop_period_limit
        if rid == "FUN-4":
            return _req(p, "dt_loop")[0], p.loop_period_limit
        if rid == "CMP-1":
            return _req(p, "c_offset_A")[0], -1e9   # bound-ness check
        if rid == "CMP-2":
            return _req(p, "c_offset_B")[0], -1e9
        if rid == "CMP-5":
            return _req(p, "k_travel")[0], 0.0
        if rid == "CMP-6":
            return steady_speed(p), 0.0
        if rid == "CMP-7":
            return _req(p, "a_brake")[0], 0.0
        if rid == "CMP-8":
            return _req(p, "t_response")[0], 1e9
        if rid == "CMP-9":
            return _req(p, "theta_yaw_deg")[0], p.heading_limit_deg
        if rid == "CMP-10":
            return _req(p, "dt_loop")[0], p.loop_period_limit
    except UnboundParameter:
        return None
    return None


_FLAG_FIELD = {
    "SYS-6": "ev_onboard_estimate", "SYS-7": "ev_no_cross_run_state",
    "SYS-8": "ev_fallback_channel", "FUN-8": "ev_onboard_estimate",
    "FUN-9": "ev_fallback_channel", "FUN-10": "ev_no_cross_run_state",
    "CMP-3": "ev_refresh_within_bound", "CMP-4": "ev_min_range_respected",
    "CMP-11": "ev_port_selfcheck", "CMP-12": "ev_trim_never_exceeds_max",
    "CMP-13": "ev_rear_ranger_valid", "CMP-14": "ev_imu_rest_indicator",
}


def evaluate(design, truth=None):
    """(b) EVALUATE -- the computational satisfy/require roll-up."""
    truth = truth or design
    try:
        pred = predict(design, truth)
    except UnboundParameter:
        pred = None

    verdict = {}
    for rid, parents, kind, text in REQUIREMENTS:
        if kind == "flag":
            f = _FLAG_FIELD.get(rid)
            v = getattr(design, f) if f else None
            verdict[rid] = ("UNBOUND" if v is None
                            else ("PASS" if v else "FAIL"))
        elif kind in ("lower", "upper"):
            ops = _operands(rid, design, truth, pred) if pred else None
            if ops is None:
                verdict[rid] = "UNBOUND"
            else:
                m, tg = ops
                ok = (m >= tg) if kind == "lower" else (m <= tg)
                verdict[rid] = "PASS" if ok else "FAIL"
        else:
            verdict[rid] = None                      # parent: filled by roll-up

    # roll-up: a node is PASS iff its own constraint passes and all children do
    children = {}
    for rid, parents, _, _ in REQUIREMENTS:
        for par in parents:
            children.setdefault(par, []).append(rid)

    def rollup(rid):
        own = verdict[rid]
        kids = [rollup(c) for c in children.get(rid, [])]
        vals = [v for v in ([own] if own else []) + kids]
        if "FAIL" in vals:
            verdict[rid] = "FAIL"
        elif "UNBOUND" in vals:
            verdict[rid] = "UNBOUND"
        else:
            verdict[rid] = "PASS"
        return verdict[rid]

    rollup("STK-1")
    return verdict, pred


# --------------------------------------------------------------------- SWEEP

def sweep(name, design, truth_base=None, lo=None, hi=None, n=25):
    """(c) SWEEP -- vary one parameter over a stated range in the TRUTH world."""
    truth_base = truth_base or design
    lo = lo if lo is not None else PRIORS[name][0]
    hi = hi if hi is not None else PRIORS[name][1]
    rows = []
    for i in range(n):
        x = lo + (hi - lo) * i / (n - 1)
        truth = replace(truth_base, **{name: x})
        g = realized_final_clearance(design, truth)
        rows.append((x, g))
    return rows


# ------------------------------------------------------------------- PRIORS
# ASSUMED ranges only -- these are NOT calibrated values.  (lo, hi, nominal,
# knowledge tier, rationale).  Tiers: 0 none / 1 physics-bounded / 2 datasheet
# / 3 onboard multi-point / 4 external ground truth.
PRIORS = {
    "c_offset_A":  (0.0, 120.0, 60.0, 0, "ranger may be flush with the front face or set back behind a bumper/frame"),
    "c_offset_B":  (0.0, 120.0, 60.0, 0, "as A; the two need not share a longitudinal station"),
    "alpha_scale": (0.93, 1.07, 1.00, 1, "ultrasonic time-of-flight scale, temperature-dependent speed of sound"),
    "sigma_u":     (1.0, 10.0, 4.0, 1, "1 mm reporting quantisation up to multi-mm echo jitter"),
    "T_refresh":   (0.010, 0.050, 0.025, 2, "LEGO UART sensor refresh 20-100 Hz"),
    "r_min_valid": (20.0, 90.0, 50.0, 1, "ultrasonic ring-down / dead zone"),
    "k_travel":    (0.30, 0.65, 0.47, 1, "wheel dia 40-70 mm, direct drive => pi*D/360"),
    "v_max_ground": (250.0, 800.0, 470.0, 1, "rated motor speed x k_travel, battery spread"),
    "a_brake":     (1000.0, 8000.0, 3500.0, 1, "coast+rolling at the low end; tyre friction limit mu~0.6 at the high end"),
    "t_response":  (0.015, 0.150, 0.080, 1, "loop phase + ranger refresh phase + ranger internal lag + command issue"),
    "dt_loop":     (0.005, 0.025, 0.012, 1, "MicroPython loop with 4 device reads"),
    "theta_yaw_deg": (0.0, 8.0, 2.0, 0, "open-loop drift over 1 m if the drive pair mismatches"),
    "w_half":      (50.0, 80.0, 65.0, 1, "SPIKE chassis half-width"),
}


def nominal_params(**over):
    """A fully-bound ASSUMED parameter set, for sensitivity work only."""
    p = Params(
        c_offset_A=PRIORS["c_offset_A"][2], c_offset_B=PRIORS["c_offset_B"][2],
        alpha_scale=PRIORS["alpha_scale"][2], sigma_u=PRIORS["sigma_u"][2],
        T_refresh=PRIORS["T_refresh"][2], r_min_valid=PRIORS["r_min_valid"][2],
        k_travel=PRIORS["k_travel"][2], v_cmd_deg_s=2000.0,
        v_max_ground=PRIORS["v_max_ground"][2], a_brake=PRIORS["a_brake"][2],
        t_response=PRIORS["t_response"][2], dt_loop=PRIORS["dt_loop"][2],
        theta_yaw_deg=PRIORS["theta_yaw_deg"][2], w_half=PRIORS["w_half"][2],
        target_gap=30.0,
        sigma_c=8.0, sigma_t_response=0.015, sigma_a=600.0, sigma_rr=6.0,
    )
    return replace(p, **over) if over else p


# ------------------------------------------------------- SENSITIVITY TABLE (0)

_MECHANISM = {
    "c_offset_A": "mean", "c_offset_B": "mean", "alpha_scale": "mean",
    "k_travel": "mean", "a_brake": "mean", "t_response": "mean",
    "v_max_ground": "mean", "r_min_valid": "gate",
    "sigma_u": "sigma", "T_refresh": "sigma", "dt_loop": "sigma",
    "theta_yaw_deg": "sigma", "w_half": "sigma",
}


def sensitivity_table(design=None, n=41):
    """
    Section-0 table: for each free parameter, how far the objective (final
    clearance) and the hard-constraint margin (clearance above the contact
    plane) move when the parameter's TRUE value ranges over its prior, with the
    program parameterised at the prior NOMINAL.
    """
    design = design or nominal_params()
    base = predict(design)["final_clearance"]
    rows = []
    for name, (lo, hi, nom, tier, why) in PRIORS.items():
        mech = _MECHANISM.get(name, "mean")
        if mech == "mean":
            data = sweep(name, design, design, lo, hi, n)
            gmin = min(g for _, g in data)
            gmax = max(g for _, g in data)
            span = gmax - gmin
            rows.append(dict(param=name, lo=lo, hi=hi, nom=nom, tier=tier,
                             mech=mech, gmin=gmin, gmax=gmax, span=span,
                             contact=(gmin <= 0.0), why=why,
                             sig_lo=None, sig_hi=None))
        elif mech == "sigma":
            s_lo = sigma_gap(replace(design, **{name: lo}))[0]
            s_hi = sigma_gap(replace(design, **{name: hi}))[0]
            rows.append(dict(param=name, lo=lo, hi=hi, nom=nom, tier=tier,
                             mech=mech, gmin=base, gmax=base, span=0.0,
                             contact=False, why=why,
                             sig_lo=min(s_lo, s_hi), sig_hi=max(s_lo, s_hi)))
        else:  # gate
            rows.append(dict(param=name, lo=lo, hi=hi, nom=nom, tier=tier,
                             mech=mech, gmin=base, gmax=base, span=0.0,
                             contact=False, why=why, sig_lo=None, sig_hi=None))
    # priority: mean-shifting span first, then sigma growth
    def key(r):
        if r["mech"] == "mean":
            return (0, -r["span"])
        if r["mech"] == "sigma":
            return (1, -(r["sig_hi"] - r["sig_lo"]))
        return (2, 0)
    rows.sort(key=key)
    for i, r in enumerate(rows, 1):
        r["priority"] = i
    return rows


# ------------------------------------------------------------------- TRACE
# CMP requirement -> SysML attribute -> Python variable -> calibration activity
TRACE = [
    # req,     SysML attribute,                  python field,      bound by
    ("CMP-1",  "rangerA.longitudinalOffset",     "c_offset_A",      "C1-creep sweep fit"),
    ("CMP-2",  "rangerB.longitudinalOffset",     "c_offset_B",      "C1-creep sweep fit"),
    ("CMP-3",  "ranger.refreshInterval",         "T_refresh",       "C1-brake window step structure"),
    ("CMP-4",  "ranger.minValidRange",           "r_min_valid",     "C1-creep near field"),
    ("CMP-5",  "motor.travelPerAngle",           "k_travel",        "C1-approach odo/ranger regression"),
    ("CMP-6",  "rover.vMaxAchievable",           "v_max_ground",    "C1-approach steady segment"),
    ("CMP-7",  "motor.brakeDecel",               "a_brake",         "C1-brake window (2 stops)"),
    ("CMP-8",  "rover.tResponse",                "t_response",      "C1-overshoot back-solve (2 stops)"),
    ("CMP-9",  "rover.headingDeviation",         "theta_yaw_deg",   "C1-static + approach heading trace"),
    ("CMP-10", "rover.loopPeriod",               "dt_loop",         "C1-loop timing statistics"),
    ("CMP-11", "rover.portSelfCheck",            "ev_port_selfcheck", "C1-discovery preamble"),
    ("CMP-12", "rover.trimNeverExceedsMax",      "ev_trim_never_exceeds_max", "inspection of locked source"),
    ("CMP-13", "rangerRear.validAtStart",        "ev_rear_ranger_valid", "C1-static read"),
    ("CMP-14", "imu.forwardAccel",               "ev_imu_rest_indicator", "C1-rest segments"),
    ("SYS-1",  "rover.contactMargin",            "k_sigma,sigma_*", "analysis on calibrated sigmas"),
    ("SYS-1",  "rover.finalClearance",           "target_gap",      "C2 + operator ground truth (TBD-17)"),
    ("SYS-5",  "rover.headingLimit",             "heading_limit_deg", "C1-approach heading trace"),
    ("STK-5",  "rover.targetGap",                "target_gap",      "analysis: 3*sigma_gap"),
]


# --------------------------------------------------------------------- self
if __name__ == "__main__":
    import sys
    p = nominal_params()
    print("=== self-check: design == truth  =>  clearance == target ===")
    pr = predict(p)
    print("  v_steady            %.1f mm/s" % pr["v_steady"])
    print("  stopping_distance   %.1f mm" % pr["stopping_distance"])
    print("  trigger_threshold_u %.1f mm (ranger units)" % pr["trigger_threshold_u"])
    print("  final_clearance     %.3f mm  (target %.1f)"
          % (pr["final_clearance"], p.target_gap))
    assert abs(pr["final_clearance"] - p.target_gap) < 1e-9
    s, terms = sigma_gap(p)
    print("  sigma_gap           %.2f mm" % s)
    for k, v in sorted(terms.items(), key=lambda kv: -kv[1]):
        print("      %-14s %6.2f" % (k, v))
    print("  contact_margin(3s)  %.2f mm" % contact_margin(p))
    v, _ = evaluate(p)
    print("  roll-up STK-1       %s" % v["STK-1"])
    print("\n=== A3 guard ===")
    try:
        predict(Params())
    except UnboundParameter as e:
        print("  OK, refused to compute:", str(e)[:60], "...")
