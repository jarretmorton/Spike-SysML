"""
wallrun_model.py  --  EXECUTABLE ANALYSIS MODEL for the wall-approach rover.

This module is the computational view of the tailored SysML model
(WallRunModel / WallRunRequirements). Every parameter, relation, and
requirement constraint in the SysML model maps 1:1 to a named variable /
function here, so the two are two views of one model:

    SysML                                Python (this file)
    -----------------------------------  ----------------------------------
    RelationTemplates::RotationToSpeed   rotation_to_speed()
    RelationTemplates::StoppingDistance  stopping_distance()
    RelationTemplates::MaxSpeedFromBudget max_speed_from_budget()
    WallRover.kSpeed                     Params.k_speed      (TBD-5)
    WallRover.omegaMax                   Params.omega_max    (TBD-1)
    WallRover.maxGroundSpeed             predict()['v_max']
    WallRover.tResponse                  Params.t_response   (TBD-4)
    WallRover.aDecel                     Params.a_decel
    WallRover.stoppingDistance           Params.D_stop       (TBD-6, measured)
    WallRover.sigmaStop                  Params.sigma_stop   (TBD-7)
    WallRover.sensorOffset               Params.b            (TBD-2)
    WallRover.sensorScale                Params.alpha        (TBD-2b, ~1)
    WallRover.minRange                   Params.r_min        (TBD-3)
    WallRover.triggerThreshold           Params.R_trigger    (design)
    WallRover.targetGap                  Params.g_target     (design)
    WallRover.safetyMargin               predict()['safety_margin']   (TBD-9)
    WallRover.finalClearance             predict()['final_clearance']
    WallRover.finalSpeed                 Params.rest_speed
    WallRover.headingDrift               Params.heading_drift
    WallRover.headingTol                 Params.heading_tol
    WallRover.restSpeedTol               Params.rest_tol
    WallRover.contactFloor               Params.contact_floor (=0)

    SYS-1 NoContact         -> evaluate()['SYS-1']   final_clearance > contact_floor
    SYS-2 MaxSpeed          -> evaluate()['SYS-2']   cruise_speed   >= v_max
    SYS-3b MinGapMargin     -> evaluate()['SYS-3b']  final_clearance >= safety_margin
    SYS-4 FullStop          -> evaluate()['SYS-4']   rest_speed     <= rest_tol
    SYS-5 StraightTravel    -> evaluate()['SYS-5']   heading_drift  <= heading_tol
    CMP-1 MotorAtMax        -> evaluate()['CMP-1']   omega_achieved >= omega_max
    CMP-2 MotorToRest       -> evaluate()['CMP-2']   motor_rest     <= rest_tol
    CMP-3 SensorResidual    -> evaluate()['CMP-3']   |resid|        <= resid_tol
    CMP-4 SensorMinRange    -> evaluate()['CMP-4']   trigger_reading>= r_min
    CMP-5 LatencyChain      -> evaluate()['CMP-5']   t_response     <= t_chain_bound
    CMP-6 HeadingBounded    -> evaluate()['CMP-6']   heading_drift  <= heading_tol
    CMP-7 GroundConstant    -> evaluate()['CMP-7']   |k_resid|      <= k_tol

Units are explicit in every name: _mm, _s, _mm_s, _mm_s2, _rad, _rad_s, _deg.
Parameters left free (None) until calibration binds them (uncalibrated, not zeroed).
"""

from dataclasses import dataclass, field, replace
from math import sqrt
from typing import Optional, Dict, Any, Tuple


# ---------------------------------------------------------------------------
# RELATION TEMPLATES  (reproduce the SysML calc-def expressions exactly)
# ---------------------------------------------------------------------------

def rotation_to_speed(omega_rad_s: float, k_m_per_rad: float) -> float:
    """RelationTemplates::RotationToSpeed :  v = motorSpeed * k   (returns m/s)."""
    return omega_rad_s * k_m_per_rad


def stopping_distance(v_mm_s: float, t_response_s: float,
                      a_mm_s2: float, margin_mm: float) -> float:
    """RelationTemplates::StoppingDistance : d = v*tResponse + v^2/(2a) + margin  (mm)."""
    return v_mm_s * t_response_s + v_mm_s ** 2 / (2.0 * a_mm_s2) + margin_mm


def max_speed_from_budget(t_response_s: float, a_mm_s2: float,
                          budget_mm: float, margin_mm: float) -> float:
    """RelationTemplates::MaxSpeedFromBudget : inverse of StoppingDistance (positive root)."""
    disc = a_mm_s2 ** 2 * t_response_s ** 2 + 2.0 * a_mm_s2 * (budget_mm - margin_mm)
    return -a_mm_s2 * t_response_s + sqrt(disc)


# ---------------------------------------------------------------------------
# PARAMETER SET  (1:1 with WallRover attributes;  None == free/uncalibrated)
# ---------------------------------------------------------------------------

@dataclass
class Params:
    # --- physical, calibrated (bind at calibration) ---
    k_speed_m_rad:   Optional[float] = None   # TBD-5  RotationToSpeed.k
    omega_max_rad_s: Optional[float] = None   # TBD-1  motor rated max
    t_response_s:    Optional[float] = None   # TBD-4  latency.tChain + sampling
    a_decel_mm_s2:   Optional[float] = None   # (informational; D_stop measured directly)
    D_stop_mm:       Optional[float] = None   # TBD-6  measured stopping distance @ v_max
    sigma_stop_mm:   Optional[float] = None   # TBD-7  run-to-run std of D_stop
    b_mm:            Optional[float] = None    # TBD-2  sensor offset (reported = alpha*true + b)
    alpha:           Optional[float] = None    # TBD-2b sensor scale (~1)
    r_min_mm:        Optional[float] = None    # TBD-3  sensor minimum valid range
    # --- measurement / prediction uncertainties (bind at calibration) ---
    sigma_b_mm:      Optional[float] = None    # operator-anchor uncertainty on b
    sigma_pred_mm:   Optional[float] = None    # residual model/parameter uncertainty
    # --- design / assurance choices (chosen, not calibrated) ---
    R_trigger_mm:    Optional[float] = None    # trigger threshold (reported units)
    g_target_mm:     Optional[float] = None    # desired final gap
    k_margin:        float = 3.0               # sigma multiplier for safety margin
    contact_floor_mm: float = 0.0              # SYS-1 strict no-contact floor
    rest_tol_mm_s:   float = 5.0               # SYS-4 / CMP-2 rest speed tolerance
    heading_tol_deg: float = 5.0               # SYS-5 / CMP-6 heading tolerance (budget)
    resid_tol_mm:    float = 8.0               # CMP-3 sensor residual tolerance
    k_tol_frac:      float = 0.05              # CMP-7 k residual tolerance (fractional)
    t_chain_bound_s: float = 0.060             # CMP-5 latency bound
    # --- measured-at-run quantities (filled from telemetry for EVALUATE) ---
    cruise_speed_mm_s: Optional[float] = None
    omega_achieved_rad_s: Optional[float] = None
    rest_speed_mm_s: Optional[float] = None
    heading_drift_deg: Optional[float] = None
    trigger_reading_mm: Optional[float] = None
    sensor_resid_mm: Optional[float] = None
    k_resid_frac: Optional[float] = None


# ---------------------------------------------------------------------------
# PREDICT  --  compute performance quantities from bound parameters
# ---------------------------------------------------------------------------

def predict(p: Params) -> Dict[str, Any]:
    """Compute v_max, D_stop, safety_margin, final_clearance, rest reading, ...

    Uses the measured D_stop when bound; otherwise falls back to the modelled
    StoppingDistance(v, t, a) so the model is exercisable pre-calibration.
    """
    out: Dict[str, Any] = {}

    # v_max = RotationToSpeed(omega, k) -> m/s -> mm/s
    if p.k_speed_m_rad is not None and p.omega_max_rad_s is not None:
        v_max = rotation_to_speed(p.omega_max_rad_s, p.k_speed_m_rad) * 1000.0
    else:
        v_max = None
    out['v_max_mm_s'] = v_max

    # D_stop: prefer measured (TBD-6); else model from v,t,a (cross-check / pre-cal)
    d_model = None
    if None not in (v_max, p.t_response_s, p.a_decel_mm_s2):
        d_model = stopping_distance(v_max, p.t_response_s, p.a_decel_mm_s2, 0.0)
    out['D_stop_model_mm'] = d_model
    d_used = p.D_stop_mm if p.D_stop_mm is not None else d_model
    out['D_stop_used_mm'] = d_used

    # safety margin = k_margin * RSS(sigma_stop, sigma_b, sigma_pred)   (A6)
    sig_terms = [p.sigma_stop_mm, p.sigma_b_mm, p.sigma_pred_mm]
    if all(s is not None for s in sig_terms):
        rss = sqrt(sum(s * s for s in sig_terms))
        safety_margin = p.k_margin * rss
    else:
        rss = None
        safety_margin = None
    out['sigma_rss_mm'] = rss
    out['safety_margin_mm'] = safety_margin

    # If R_trigger not chosen, solve it to place the gap at g_target (default = margin)
    g_target = p.g_target_mm if p.g_target_mm is not None else safety_margin
    out['g_target_mm'] = g_target
    R_trigger = p.R_trigger_mm
    if R_trigger is None and None not in (p.b_mm, d_used, g_target):
        R_trigger = p.b_mm + d_used + g_target
    out['R_trigger_mm'] = R_trigger

    # final clearance geometry:  clearance = R_trigger - b - D_stop
    if None not in (R_trigger, p.b_mm, d_used):
        final_clearance = R_trigger - p.b_mm - d_used
    else:
        final_clearance = None
    out['final_clearance_mm'] = final_clearance

    # rest reading (reported) = alpha*clearance + b ; valid only if >= r_min
    if None not in (final_clearance, p.alpha, p.b_mm):
        rest_reading = p.alpha * final_clearance + p.b_mm
        out['rest_reading_reported_mm'] = rest_reading
        out['rest_reading_valid'] = (p.r_min_mm is None) or (rest_reading >= p.r_min_mm)
    else:
        out['rest_reading_reported_mm'] = None
        out['rest_reading_valid'] = None

    # trigger reading vs min range (CMP-4): the reading we trigger on must be valid
    out['trigger_above_rmin'] = (
        None if (R_trigger is None or p.r_min_mm is None) else (R_trigger >= p.r_min_mm)
    )
    return out


# ---------------------------------------------------------------------------
# EVALUATE  --  pass/fail per requirement  (the satisfy/require roll-up)
# ---------------------------------------------------------------------------

def _verdict(ok: Optional[bool]) -> str:
    return "PASS" if ok is True else ("FAIL" if ok is False else "N/A")


def evaluate(p: Params) -> Dict[str, Dict[str, Any]]:
    """Return {req_id: {measured, target, op, verdict}} plus a roll-up.

    Hard requirements gate the roll-up; SYS-3 (objective) is graded, not pass/fail.
    """
    pr = predict(p)
    R: Dict[str, Dict[str, Any]] = {}

    def add(rid, measured, target, op, ok, note=""):
        R[rid] = dict(measured=measured, target=target, op=op,
                      verdict=_verdict(ok), note=note)

    fc = pr['final_clearance_mm']
    sm = pr['safety_margin_mm']

    # SYS-1  NoContact : final_clearance > contact_floor
    add('SYS-1', fc, p.contact_floor_mm, '>',
        None if fc is None else fc > p.contact_floor_mm, "hard: no contact")
    # SYS-2  MaxSpeed : cruise_speed >= v_max  (achieves the ceiling; tol 2%)
    v = pr['v_max_mm_s']
    cs = p.cruise_speed_mm_s
    add('SYS-2', cs, v, '>=',
        None if (cs is None or v is None) else cs >= 0.98 * v, "hard: command at max")
    # SYS-3  MinGap (objective, graded) -- reported, never pass/fail
    add('SYS-3', fc, None, 'min', None, "objective: minimize (graded, not pass/fail)")
    # SYS-3b MinGapMargin : final_clearance >= safety_margin
    add('SYS-3b', fc, sm, '>=',
        None if (fc is None or sm is None) else fc >= sm, "derived margin bridge")
    # SYS-4  FullStop : rest_speed <= rest_tol
    add('SYS-4', p.rest_speed_mm_s, p.rest_tol_mm_s, '<=',
        None if p.rest_speed_mm_s is None else p.rest_speed_mm_s <= p.rest_tol_mm_s,
        "hard: complete stop")
    # SYS-5  StraightTravel : heading_drift <= heading_tol
    add('SYS-5', p.heading_drift_deg, p.heading_tol_deg, '<=',
        None if p.heading_drift_deg is None else p.heading_drift_deg <= p.heading_tol_deg,
        "derived: straight")
    # CMP-1  MotorAtMax : omega_achieved >= omega_max (rated)
    add('CMP-1', p.omega_achieved_rad_s, p.omega_max_rad_s, '>=',
        None if (p.omega_achieved_rad_s is None or p.omega_max_rad_s is None)
        else p.omega_achieved_rad_s >= 0.98 * p.omega_max_rad_s, "motor reaches rated max")
    # CMP-2  MotorToRest : rest_speed <= rest_tol
    add('CMP-2', p.rest_speed_mm_s, p.rest_tol_mm_s, '<=',
        None if p.rest_speed_mm_s is None else p.rest_speed_mm_s <= p.rest_tol_mm_s,
        "motor decelerates to rest")
    # CMP-3  SensorResidual : |resid| <= resid_tol
    add('CMP-3', p.sensor_resid_mm, p.resid_tol_mm, '<=',
        None if p.sensor_resid_mm is None else abs(p.sensor_resid_mm) <= p.resid_tol_mm,
        "sensor tracks true within offset")
    # CMP-4  SensorMinRange : trigger reading >= r_min
    tr = p.trigger_reading_mm if p.trigger_reading_mm is not None else pr['R_trigger_mm']
    add('CMP-4', tr, p.r_min_mm, '>=',
        None if (tr is None or p.r_min_mm is None) else tr >= p.r_min_mm,
        "trigger in valid sensor range")
    # CMP-5  LatencyChain : t_response <= bound
    add('CMP-5', p.t_response_s, p.t_chain_bound_s, '<=',
        None if p.t_response_s is None else p.t_response_s <= p.t_chain_bound_s,
        "sense->brake latency bounded")
    # CMP-6  HeadingBounded : heading_drift <= heading_tol
    add('CMP-6', p.heading_drift_deg, p.heading_tol_deg, '<=',
        None if p.heading_drift_deg is None else p.heading_drift_deg <= p.heading_tol_deg,
        "IMU heading drift bounded")
    # CMP-7  GroundConstant : |k_resid| <= k_tol
    add('CMP-7', p.k_resid_frac, p.k_tol_frac, '<=',
        None if p.k_resid_frac is None else abs(p.k_resid_frac) <= p.k_tol_frac,
        "encoder->ground constant calibrated")

    hard = ['SYS-1', 'SYS-2', 'SYS-3b', 'SYS-4', 'SYS-5',
            'CMP-1', 'CMP-2', 'CMP-3', 'CMP-4', 'CMP-5', 'CMP-6', 'CMP-7']
    verdicts = [R[h]['verdict'] for h in hard]
    if 'FAIL' in verdicts:
        roll = 'FAIL'
    elif 'N/A' in verdicts:
        roll = 'INCOMPLETE'
    else:
        roll = 'PASS'
    R['ROLLUP'] = dict(measured=roll, target='all hard PASS', op='satisfy',
                       verdict=roll, note="WallRunNeed satisfy/require roll-up")
    return R


# ---------------------------------------------------------------------------
# SWEEP  --  sensitivity of objective & margin to each parameter over a range
# ---------------------------------------------------------------------------

# Priors: (nominal, lo, hi, knowledge-tier, note).  Tiers: 1=well known,
# 2=modelled/inferred, 3=unknown-onboard, 4=needs external ground truth.
PRIORS = {
    'k_speed_m_rad':   (0.028, 0.020, 0.045, 2, "wheel radius x gearing; onboard-calibratable"),
    'omega_max_rad_s': (18.0, 15.7, 19.5,   2, "motor rated max; datasheet/onboard"),
    't_response_s':    (0.030, 0.010, 0.060, 2, "loop period + sampling + actuation"),
    'a_decel_mm_s2':   (4000., 2000., 8000., 3, "braking decel; not directly known"),
    'b_mm':            (0.0, -20.0, 30.0,    4, "sensor offset; NO onboard absolute channel"),
    'alpha':           (1.0, 0.97, 1.03,     2, "sensor scale; near unity"),
    'r_min_mm':        (45.0, 30.0, 60.0,    2, "sensor min valid range"),
    'sigma_stop_mm':   (8.0, 3.0, 20.0,      3, "run-to-run stop std; sets margin"),
    'sigma_b_mm':      (5.0, 2.0, 10.0,      3, "operator-anchor uncertainty"),
    'sigma_pred_mm':   (5.0, 2.0, 15.0,      3, "residual model uncertainty"),
    'heading_drift_deg': (2.0, 0.0, 10.0,    3, "approach heading drift"),
}


def _nominal_params() -> Params:
    p = Params()
    for name, (nom, lo, hi, tier, note) in PRIORS.items():
        setattr(p, name, nom)
    # fill measured-at-run stand-ins at nominal so EVALUATE is exercisable
    p.cruise_speed_mm_s = rotation_to_speed(p.omega_max_rad_s, p.k_speed_m_rad) * 1000.0
    p.omega_achieved_rad_s = p.omega_max_rad_s
    p.rest_speed_mm_s = 0.0
    p.sensor_resid_mm = 0.0
    p.k_resid_frac = 0.0
    return p


def sweep(param: str, at_fixed_trigger: bool = True) -> Dict[str, Any]:
    """Vary one parameter lo..hi (others nominal). Report how the objective
    (final clearance) and the no-contact margin move.

    at_fixed_trigger=True: R_trigger is fixed at its nominal-solved value, so we
    see how an ERROR in the parameter's TRUE value shifts the achieved gap --
    this is the leverage that matters for shipping a systematic bias.
    """
    nom, lo, hi, tier, note = PRIORS[param]
    base = _nominal_params()

    # establish the nominal operating point and fix R_trigger there
    base_pred = predict(base)
    R_fixed = base_pred['R_trigger_mm']
    if at_fixed_trigger:
        base = replace(base, R_trigger_mm=R_fixed)

    def eval_at(val):
        q = replace(base, **{param: val})
        # keep cruise_speed consistent if we move k or omega
        if param in ('k_speed_m_rad', 'omega_max_rad_s'):
            q.cruise_speed_mm_s = rotation_to_speed(q.omega_max_rad_s, q.k_speed_m_rad) * 1000.0
            q.omega_achieved_rad_s = q.omega_max_rad_s
        pr = predict(q)
        return pr['final_clearance_mm'], pr['safety_margin_mm']

    fc_lo, sm_lo = eval_at(lo)
    fc_hi, sm_hi = eval_at(hi)
    fc_nom, sm_nom = eval_at(nom)

    d_obj = None if (fc_lo is None or fc_hi is None) else (fc_hi - fc_lo)
    d_margin = None if (sm_lo is None or sm_hi is None) else (sm_hi - sm_lo)
    return dict(param=param, nominal=nom, lo=lo, hi=hi, tier=tier, note=note,
                fc_lo=fc_lo, fc_hi=fc_hi, fc_nom=fc_nom,
                sm_lo=sm_lo, sm_hi=sm_hi, sm_nom=sm_nom,
                d_objective_mm=d_obj, d_margin_mm=d_margin)


def sensitivity_table():
    rows = [sweep(name) for name in PRIORS]

    # rank by combined absolute leverage on objective + margin
    def lever(r):
        return max(abs(r['d_objective_mm'] or 0.0), abs(r['d_margin_mm'] or 0.0))
    rows.sort(key=lever, reverse=True)
    return rows


# ---------------------------------------------------------------------------
# demo / self-check
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 92)
    print("NOMINAL PREDICT (priors, pre-calibration)")
    print("=" * 92)
    base = _nominal_params()
    pr = predict(base)
    for k in ('v_max_mm_s', 'D_stop_model_mm', 'D_stop_used_mm', 'sigma_rss_mm',
              'safety_margin_mm', 'g_target_mm', 'R_trigger_mm',
              'final_clearance_mm', 'rest_reading_reported_mm',
              'rest_reading_valid', 'trigger_above_rmin'):
        v = pr[k]
        print(f"  {k:26s} = {v:.3f}" if isinstance(v, float) else f"  {k:26s} = {v}")

    print()
    print("=" * 92)
    print("SENSITIVITY TABLE  (R_trigger fixed at nominal; ranges = assumed priors)")
    print("  d_objective = change in final gap (mm) as the TRUE value sweeps lo..hi")
    print("  d_margin    = change in required no-contact margin (mm) over the same range")
    print("=" * 92)
    hdr = f"{'parameter':18s} {'range':>16s} {'d_obj(mm)':>10s} {'d_margin(mm)':>12s} {'tier':>4s}  priority"
    print(hdr)
    print("-" * 92)
    rows = sensitivity_table()
    n = len(rows)
    for i, r in enumerate(rows):
        rng = f"[{r['lo']:g}, {r['hi']:g}]"
        do = r['d_objective_mm']; dm = r['d_margin_mm']
        do_s = f"{do:+.1f}" if do is not None else "  n/a"
        dm_s = f"{dm:+.1f}" if dm is not None else "  n/a"
        lever = max(abs(do or 0), abs(dm or 0))
        if lever >= 40:  prio = "HIGH"
        elif lever >= 15: prio = "MEDIUM"
        else:            prio = "LOW"
        print(f"{r['param']:18s} {rng:>16s} {do_s:>10s} {dm_s:>12s} {r['tier']:>4d}  {prio}")
    print("-" * 92)
    print("tiers: 1=well-known  2=modelled/onboard-calibratable  "
          "3=unknown-onboard  4=needs external ground truth")

    print()
    print("=" * 92)
    print("EVALUATE at nominal operating point (all measured stand-ins nominal)")
    print("=" * 92)
    # bind a measured D_stop = model value for the nominal roll-up demo
    base2 = replace(base, D_stop_mm=pr['D_stop_model_mm'],
                    R_trigger_mm=pr['R_trigger_mm'],
                    trigger_reading_mm=pr['R_trigger_mm'],
                    heading_drift_deg=2.0)
    ev = evaluate(base2)
    for rid in ['SYS-1', 'SYS-2', 'SYS-3', 'SYS-3b', 'SYS-4', 'SYS-5',
                'CMP-1', 'CMP-2', 'CMP-3', 'CMP-4', 'CMP-5', 'CMP-6', 'CMP-7', 'ROLLUP']:
        e = ev[rid]
        m = e['measured']; t = e['target']
        ms = f"{m:.2f}" if isinstance(m, float) else str(m)
        ts = f"{t:.2f}" if isinstance(t, float) else str(t)
        print(f"  {rid:7s} {e['verdict']:11s} measured={ms:>10s} {e['op']:>4s} target={ts:>10s}  {e['note']}")
