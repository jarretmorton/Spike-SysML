#!/usr/bin/env python3
# ============================================================================
# 03_wall_rover_eam_v1.0.py — EXECUTABLE ANALYSIS MODEL (EAM)
# Wall-Approach Rover (WAR) | mirrors 02_wall_rover_model_v1.0.sysml 1:1
#
# The SysML model carries the formal satisfy/require argument; this module
# carries the arithmetic. Two views of ONE model:
#   SysML attribute  <->  named entry in PARAMS / CONSTANTS / DERIVED / OBS
#   SysML requirement def (Lower/UpperBound specialization) <-> row in REQS
#   Reproduced relation expressions (RotationToSpeed, StoppingDistance)
#       <-> functions in DERIVED (same expressions, same operands)
#
# Exposes:
#   PREDICT  - performance quantities (final gap, clearance, trigger reading,
#              stop budget) from bound parameter values
#   EVALUATE - pass/fail per requirement (computational satisfy/require
#              roll-up); unbound operands -> OPEN, never zeroed (Tenet A3)
#   SWEEP    - one-at-a-time parameter sweep over stated priors -> the
#              Calibration Plan section-0 sensitivity table
#   size_margin / mc_check - RSS margin sizing (Tenet A6) + Monte-Carlo check
#   structural_audit - reachability, edge-set-vs-spec-tree, and
#              SysML<->Python trace completeness (the by-hand checks grammar
#              cannot see, run mechanically)
#
# Units: SI base throughout (m, s, m/s, m/s^2, rad), matching the SysML
# ISQ/SI value types. Pretty-printing converts to mm / ms / deg for reading.
# Standard library only.
# ============================================================================

import math
import random

Z_MARGIN = 3.0  # SYS-5 design constant (per-run no-contact >= 99.87 %)

# ---------------------------------------------------------------------------
# Parameter registry: calibratable quantities. value=None until calibration
# binds it (uncalibrated, not zeroed). Priors are the Gate-A assumed ranges
# (inputs to operator review). tier: T0 unknown | T1 single sample |
# T2 onboard multi-point/anchored | T3 operator ground truth.
# ---------------------------------------------------------------------------

class Param:
    def __init__(self, key, lo, hi, unit, sysml, tbd, binder, role, note=""):
        self.key, self.lo, self.hi = key, lo, hi
        self.unit, self.sysml, self.tbd = unit, sysml, tbd
        self.binder, self.role, self.note = binder, role, note
        self.value = None          # bound by calibration
        self.tier = "T0-unknown"   # upgraded when bound; never silently down

    @property
    def nom(self):
        return self.value if self.value is not None else 0.5 * (self.lo + self.hi)

    def bind(self, value, tier, evidence):
        self.value, self.tier, self.evidence = value, tier, evidence


def _registry():
    P = {}
    def add(*a, **k):
        p = Param(*a, **k); P[p.key] = p
    # role: 'mean' shifts the stop point 1:1-ish | 'disp' enters sigma_stop |
    #        'margin' erodes corner clearance | 'validity' gates a channel |
    #        'context' should show ~zero leverage (absence-by-sensitivity)
    add("o_us",     -0.010, 0.050, "m",     "WallRover::usFrontA.mountOffset (and ...B)", "TBD-5/6",
        "M1 ground-truth anchor + R-CAL rest medians", "mean",
        "reading minus true front gap at rest; only T3 observes it absolutely")
    add("tau_us",    0.010, 0.080, "s",     "WallRover::usFrontA.dataAge", "TBD-7",
        "R-CAL dynamic cross-correlation US vs odometry", "mean",
        "on approach the reading is HIGH by v*tau")
    add("t_chain",   0.009, 0.035, "s",     "WallRover::latency.tChain", "TBD-9/11",
        "R-CAL trigger-tick -> decel-onset timing", "mean",
        "loop-quantization mean + command-issue latency (RoverCommon.RoverLatency)")
    add("a_brake",   1.5,   5.0,   "m/s^2", "WallRover::brakeDecel", "TBD-10",
        "R-CAL 3 brake events, US-measured distance", "mean",
        "effective decel incl. slip; quadratic distance term")
    add("v_max",     0.25,  0.80,  "m/s",   "WallRover::groundSpeed (via motor plateaus)", "TBD-13",
        "R-CAL plateau x3 segments", "mean",
        "in-run measured -> trigger adapts (see adaptive row)")
    add("k_odo",     0.0172, 0.0573, "m/rad", "WallRover::kOdo", "TBD-8",
        "R-CAL slope fit US-vs-encoder + rest-delta cross-check", "mean",
        "RotationToSpeed constant; contaminates v_hat and DR if wrong")
    add("T_loop",    0.008, 0.030, "s",     "WallRover::loopPeriod", "TBD-11",
        "R-CAL tick log", "disp",
        "trigger quantization jitter v*T/sqrt(12); mean lives in t_chain")
    add("U_refresh", 0.010, 0.100, "s",     "WallRover::usFrontA.refreshInterval", "TBD-17",
        "R-CAL static burst sampling", "mean",
        "designed out by DR propagation between samples (see naive row)")
    add("sigma_us",  0.001, 0.005, "m",     "WallRover::usFrontA.noiseSigma", "TBD-16",
        "R-CAL static window + rest windows", "disp",
        "trigger-sample noise; 2-sample confirm divides by sqrt(2)")
    add("sigma_b",   0.003, 0.010, "m",     "WallRover::brakeSigma", "TBD-10b",
        "R-CAL 3 samples + R-VER sample", "disp",
        "run-to-run braking dispersion, largest sigma_stop contributor")
    add("psi_run",   0.0,   0.052, "rad",   "WallRover::headingDeviationMax", "TBD-3/18",
        "R-CAL heading log (trim gain decision)", "margin",
        "corner erosion = halfWidth * psi (small angle)")
    add("half_width",0.060, 0.100, "m",     "WallRover::halfWidth", "-",
        "geometry, bounded prior (no measurement planned)", "margin", "")
    add("r_min",     0.040, 0.080, "m",     "WallRover::usFrontA.validFloor", "TBD-4",
        "R-CAL creep mapping (lower bound + DR fallback)", "validity",
        "gates rest-estimate channel only, not stopping physics")
    add("G0_start",  0.90,  1.10,  "m",     "(context; not a model operand)", "-",
        "none needed - see sweep row", "context",
        "trigger is absolute in gap; start distance cancels")
    return P

PARAMS = _registry()

# ---------------------------------------------------------------------------
# Design constants (SysML: literal-bound attributes on WallRover)
# ---------------------------------------------------------------------------
CONSTANTS = {
    "zero": 0.0,
    "one": 1.0,
    "z_margin": Z_MARGIN,                # WallRover::zMargin
    "contact_floor": 0.001,              # WallRover::contactFloor (strict >0 as >=1 mm)
    "duty_command": 100.0,               # WallRover::dutyCommand (%)
    "trim_cap_pct": 15.0,                # WallRover::trimCapPct
    "plateau_ratio_floor": 0.95,         # WallRover::plateauRatioFloor
    "plateau_dev_tol": 0.05,             # WallRover::plateauDevTol (fractional)
    "offset_tol": 0.003,                 # WallRover::offsetTol (m) - CMP-U2
    "data_age_tol": 0.010,               # WallRover::dataAgeTol (s) - CMP-U3
    "coverage_floor": 0.99,              # WallRover::coverageFloor
    "hold_floor": 2.0,                   # WallRover::holdFloor (s)
    "rest_sample_floor": 8.0,            # WallRover::restSampleFloor
    "estimate_channel_floor": 2.0,       # WallRover::estimateChannelFloor
    "objective_ceiling": 0.060,          # WallRover::objectiveCeiling (m) - STK-3
    "emission_budget": 20.0,             # WallRover::emissionBudget (s)
}

# Requirement-bound values set at Gate B from calibration data (None = TBD):
GATE_B_BOUNDS = {
    "stop_target": None,       # WallRover::stopTarget      TBD-1
    "sigma_stop": None,        # WallRover::sigmaStop       (analysis RSS)
    "post_stop_bound": None,   # WallRover::postStopBound   TBD-2
    "heading_bound": None,     # WallRover::headingBound    TBD-3
    "noise_bound": None,       # WallRover::noiseBound      TBD-16 bound
    "refresh_bound": None,     # WallRover::refreshBound    TBD-17 bound
    "imu_drift_bound": None,   # WallRover::imuDriftBound   TBD-18 bound
    "jitter_bound": None,      # WallRover::jitterBound     TBD-19 bound
    "rear_track_bound": None,  # WallRover::rearTrackBound  TBD-20 bound
}

# ---------------------------------------------------------------------------
# DERIVED attributes — reproduced relation expressions (per the template
# library's validation note, expressions are REPRODUCED against bound
# parameters; RelationTemplates is the source of truth for their form).
# ---------------------------------------------------------------------------

def derived(vals):
    d = {}
    v   = vals.get("v_max")
    a   = vals.get("a_brake")
    tch = vals.get("t_chain")
    Gt  = vals.get("stop_target")
    ss  = vals.get("sigma_stop")
    sb  = vals.get("sigma_b")
    # RotationToSpeed (reproduced): groundSpeed = plateau * kOdo. In this
    # module v_max IS groundSpeed; the deg/s plateau lives in telemetry.
    d["ground_speed"] = v
    # StoppingDistance (reproduced): d = v*tResponse + v^2/(2a) + margin,
    # with tResponse := latency.tChain (sensor age corrected separately in
    # FUN-1) and margin := stopTarget.
    if None not in (v, tch, a, Gt):
        d["stop_budget"] = v * tch + v ** 2 / (2.0 * a) + Gt
    if None not in (Gt, ss):
        d["margin_floor"] = Z_MARGIN * ss                    # SYS-5 RHS
        d["closeness_ceiling"] = Gt + Z_MARGIN * ss          # SYS-4/STK-3 RHS
    if None not in (v, a, sb):
        d["brake_dist_ceiling"] = v ** 2 / (2.0 * a) + Z_MARGIN * sb  # CMP-M2 RHS
    if vals.get("T_loop") is not None:
        d["failsafe_latency_bound"] = 2.0 * vals["T_loop"]   # SYS-11 RHS
    if None not in (vals.get("half_width"), vals.get("psi_run")):
        d["corner_erosion"] = vals["half_width"] * vals["psi_run"]  # small angle
    return d


def base_vals(overrides=None):
    # Only CALIBRATION-BOUND values enter the evaluation namespace; priors
    # are sweep inputs, never verdict inputs (Tenet A3).
    vals = {k: p.value for k, p in PARAMS.items()}
    vals.update(CONSTANTS)
    vals.update(GATE_B_BOUNDS)
    if overrides:
        vals.update(overrides)
    vals.update(derived(vals))
    return vals

# ---------------------------------------------------------------------------
# PREDICT — closed-loop stop physics. 'real' is what the world does; the
# controller acts on BELIEFS (calibrated values). Belief error is exactly
# what the sensitivity sweep varies.
#   reading = gap + o + v*tau            (approach: reads high by v*tau)
#   trigger when corrected gap <= stop_budget  =>  reading threshold:
#   R_th = G_target + o_hat + v_hat*tau_hat + v_hat*t_chain_hat + v_hat^2/(2 a_hat)
#   gap at crossing = R_th - o - v*tau
#   advance after crossing = v*t_chain + v^2/(2a)
# ---------------------------------------------------------------------------

def predict(G_target, real_over=None, belief_over=None,
            adaptive_v=True, dr_propagation=True):
    real = {k: p.nom for k, p in PARAMS.items()}
    if real_over:
        real.update(real_over)
    bel = {k: p.nom for k, p in PARAMS.items()}
    if belief_over:
        bel.update(belief_over)

    v = real["v_max"]
    if adaptive_v:
        # v_hat = k_hat * (dtheta/dt) and dtheta/dt = v / k_real
        bel["v_max"] = v * bel["k_odo"] / real["k_odo"]
    vb = bel["v_max"]

    tau_r, tau_b = real["tau_us"], bel["tau_us"]
    if not dr_propagation:
        # naive trigger samples the raw (possibly stale) reading: extra mean
        # age U/2 on both sides (belief compensates its own believed U).
        tau_r = tau_r + real["U_refresh"] / 2.0
        tau_b = tau_b + bel["U_refresh"] / 2.0

    reading_th = (G_target + bel["o_us"] + vb * tau_b
                  + vb * bel["t_chain"] + vb ** 2 / (2.0 * bel["a_brake"]))
    gap_cross = reading_th - real["o_us"] - v * tau_r
    advance = v * real["t_chain"] + v ** 2 / (2.0 * real["a_brake"])
    final_gap = gap_cross - advance
    corner = real["half_width"] * real["psi_run"]
    return {
        "reading_trigger": reading_th,
        "gap_at_trigger": gap_cross,
        "stop_advance_real": advance,
        "final_gap": final_gap,
        "final_clearance": final_gap - corner,
        "min_run_clearance": final_gap - corner,
    }

# ---------------------------------------------------------------------------
# SWEEP — the Calibration Plan section-0 table. One-at-a-time over priors,
# beliefs pinned at nominal (except the in-run-adaptive rules), reporting how
# far the ACTUAL stop moves if reality sits at the prior edges.
# ---------------------------------------------------------------------------

def sweep(G_target=0.035):
    base = predict(G_target)["final_gap"]
    rows = []
    for key, p in PARAMS.items():
        if p.role == "context" or key == "G0_start":
            rows.append((key, p, 0.0, 0.0, 0.0)); continue
        if p.role == "disp":
            v = PARAMS["v_max"].nom
            if key == "T_loop":
                s = v * p.hi / math.sqrt(12.0)
                rows.append((key, p, 0.0, 0.0, s)); continue
            if key == "sigma_us":
                s = p.hi / math.sqrt(2.0)
                rows.append((key, p, 0.0, 0.0, s)); continue
            if key == "sigma_b":
                rows.append((key, p, 0.0, 0.0, p.hi)); continue
        if p.role == "margin":
            lo = predict(G_target, real_over={key: p.lo})
            hi = predict(G_target, real_over={key: p.hi})
            span = abs(hi["final_clearance"] - lo["final_clearance"])
            rows.append((key, p, lo["final_clearance"] - base,
                         hi["final_clearance"] - base, span)); continue
        if p.role == "validity":
            rows.append((key, p, 0.0, 0.0, 0.0)); continue
        if key == "U_refresh":
            lo = predict(G_target, real_over={key: p.lo}, dr_propagation=False)
            hi = predict(G_target, real_over={key: p.hi}, dr_propagation=False)
            rows.append((key, p, lo["final_gap"] - base,
                         hi["final_gap"] - base,
                         abs(hi["final_gap"] - lo["final_gap"]))); continue
        lo = predict(G_target, real_over={key: p.lo})["final_gap"]
        hi = predict(G_target, real_over={key: p.hi})["final_gap"]
        rows.append((key, p, lo - base, hi - base, abs(hi - lo)))
    # special row: v_max WITHOUT in-run adaptation (design justification)
    p = PARAMS["v_max"]
    lo = predict(G_target, real_over={"v_max": p.lo}, adaptive_v=False)["final_gap"]
    hi = predict(G_target, real_over={"v_max": p.hi}, adaptive_v=False)["final_gap"]
    rows.append(("v_max (if NOT adapted)", p, lo - base, hi - base, abs(hi - lo)))
    rows.sort(key=lambda r: -r[4])
    return base, rows


def _tier_now(p):
    return p.tier if p.value is not None else "T0-unknown (prior only)"


def print_sweep(G_target=0.035):
    base, rows = sweep(G_target)
    print("SENSITIVITY TABLE (section 0) — objective = final gap; "
          "hard-constraint margin = clearance to contact")
    print("Baseline (all params at prior midpoints, beliefs correct): "
          "final gap = %.1f mm at G_target = %.0f mm" % (base * 1e3, G_target * 1e3))
    hdr = ("parameter", "assumed range", "gap shift lo/hi edge (mm)",
           "|span| (mm)", "knowledge tier", "priority / disposition")
    print("%-24s | %-22s | %-26s | %-11s | %-22s | %s" % hdr)
    print("-" * 150)
    for key, p, dlo, dhi, span in rows:
        if p.role == "disp":
            sens = "dispersion +/- %.1f (RSS)" % (span * 1e3)
        elif p.role in ("context", "validity"):
            sens = "0.0 / 0.0"
        else:
            sens = "%+.1f / %+.1f" % (dlo * 1e3, dhi * 1e3)
        rng = "%g..%g %s" % (p.lo, p.hi, p.unit)
        prio = _priority(key, span)
        print("%-24s | %-22s | %-26s | %-11.1f | %-22s | %s"
              % (key, rng, sens, span * 1e3, _tier_now(p), prio))
    print()


def _priority(key, span):
    table = {
        "k_odo":   "P1 — bind first (R-CAL slope fit, T2); contaminates v_hat & DR",
        "a_brake": "P1 — bind (R-CAL x3 brake events, T2)",
        "o_us":    "P1 — ONLY T3-able quantity: spend M1 here (operating point)",
        "v_max (if NOT adapted)": "design row — justifies in-run v adaptation (FUN-3)",
        "tau_us":  "P2 — bind (R-CAL cross-correlation, T2)",
        "U_refresh": "P2 — designed out by DR propagation (FUN-3); value still bound (T2)",
        "t_chain": "P3 — bind (R-CAL timing, T2)",
        "sigma_b": "P2 — dispersion floor of sigma_stop; 3 samples + R-VER",
        "T_loop":  "P3 — dispersion; bind (tick log)",
        "sigma_us":"P3 — dispersion; bind (static window)",
        "psi_run": "P3 — margin erosion; trim-gain decision input",
        "half_width": "P4 — bounded prior suffices (enters only via psi)",
        "r_min":   "P3 — validity floor; DR fallback removes criticality",
        "G0_start":"P4 — ZERO leverage: no operator measurement requested (absence by sensitivity)",
        "v_max":   "P2 — plateau bound for CMP-M1/STK-2; gap-insensitive once adapted",
    }
    return table.get(key, "P4")

# ---------------------------------------------------------------------------
# Margin sizing (Tenet A6): G_target = z * RSS(independent contributors)
# ---------------------------------------------------------------------------

def size_margin(sigmas, z=Z_MARGIN):
    rss = math.sqrt(sum(s * s for s in sigmas.values()))
    return z * rss, rss


def illustrative_post_cal_sigmas():
    """Pre-calibration ILLUSTRATION of the post-calibration residual set,
    built from prior midpoints. Replaced wholesale by measured values at
    Gate B; printed here so the review can see the sizing machinery."""
    v = PARAMS["v_max"].nom
    return {
        "offset_anchor_residual(T3 tape + rest noise)": 0.003,
        "brake_run_to_run(3-sample, inflated)": 0.007,
        "tau_residual(+-10ms bound)*v": 0.010 / math.sqrt(3) * v,
        "k_residual(1.5%) via v_hat chain": 0.015 * (v * (PARAMS["tau_us"].nom + PARAMS["t_chain"].nom)
                                                     + v ** 2 / PARAMS["a_brake"].nom),
        "trigger_quantization(jitter)": v * PARAMS["T_loop"].nom / math.sqrt(12),
        "us_noise_at_trigger(2-sample confirm)": PARAMS["sigma_us"].nom / math.sqrt(2),
        "corner_residual(psi<=1deg)": PARAMS["half_width"].nom * math.radians(1.0),
        "unmodeled(floor/battery)": 0.003,
    }


def mc_check(G_target, sigmas, n=200000, seed=7):
    rng = random.Random(seed)
    sd = math.sqrt(sum(s * s for s in sigmas.values()))
    contacts = sum(1 for _ in range(n) if G_target + rng.gauss(0.0, sd) <= 0.0)
    p1 = contacts / n
    return p1, 1.0 - (1.0 - p1) ** 5, sd

# ---------------------------------------------------------------------------
# Requirement table — one row per SysML requirement def. kind: 'ge'|'le'.
# measured/target name keys in the merged value namespace (params +
# constants + Gate-B bounds + derived + observations/evidence).
# level + parent realize the decomposition edge-set (checked vs spec tree).
# ---------------------------------------------------------------------------

class Req:
    def __init__(self, rid, kind, measured, target, level, parent, objective=False):
        self.rid, self.kind = rid, kind
        self.measured, self.target = measured, target
        self.level, self.parent, self.objective = level, parent, objective

REQS = [
    # ---- STK ----
    Req("STK-1", "ge", "min_run_clearance", "contact_floor", "STK", None),
    Req("STK-2", "ge", "speed_plateau_ratio", "plateau_ratio_floor", "STK", None),
    Req("STK-3", "le", "stop_target", "objective_ceiling", "STK", None, objective=True),
    Req("STK-4", "ge", "rest_achieved", "one", "STK", None),
    Req("STK-5", "ge", "estimates_committed", "one", "STK", None),
    Req("STK-6", "le", "operator_inputs_during_run", "zero", "STK", None),
    Req("STK-7", "ge", "telemetry_complete", "one", "STK", None),
    # ---- SYS ----
    Req("SYS-1", "ge", "outer_duty_min", "duty_command", "SYS", "STK-2"),
    Req("SYS-2", "le", "brake_cmd_delay", "T_loop", "SYS", "STK-4"),
    Req("SYS-3", "ge", "final_clearance", "contact_floor", "SYS", "STK-1"),
    Req("SYS-4", "le", "final_clearance", "closeness_ceiling", "SYS", "STK-3", objective=True),
    Req("SYS-5", "ge", "stop_target", "margin_floor", "SYS", "SYS-3"),
    Req("SYS-6", "le", "post_stop_travel_max", "post_stop_bound", "SYS", "STK-4"),
    Req("SYS-7", "ge", "estimate_channels", "estimate_channel_floor", "SYS", "STK-5"),
    Req("SYS-8", "le", "heading_dev_max", "heading_bound", "SYS", "STK-1"),
    Req("SYS-9", "le", "hot_path_writes", "zero", "SYS", "STK-7"),
    Req("SYS-10", "ge", "sentinel_emitted", "one", "SYS", "STK-7"),
    Req("SYS-11", "le", "failsafe_latency", "failsafe_latency_bound", "SYS", "STK-1"),
    Req("SYS-12", "le", "invalid_sample_leakage", "zero", "SYS", "STK-1"),
    Req("SYS-13", "ge", "census_validated", "one", "SYS", "STK-6"),
    # ---- FUN ----
    Req("FUN-1", "ge", "gap_coverage", "coverage_floor", "FUN", "SYS-2"),
    Req("FUN-2", "ge", "odo_coverage", "coverage_floor", "FUN", "SYS-2"),
    Req("FUN-3", "le", "fused_gap_at_trigger", "stop_budget", "FUN", "SYS-2"),
    Req("FUN-4", "le", "trim_max", "trim_cap_pct", "FUN", "SYS-1"),
    Req("FUN-5", "ge", "hold_duration", "hold_floor", "FUN", "SYS-2"),
    Req("FUN-6", "ge", "rest_sample_count", "rest_sample_floor", "FUN", "SYS-7"),
    Req("FUN-7", "ge", "failsafe_coverage", "one", "FUN", "SYS-11"),
    # ---- CMP ----
    Req("CMP-M1-L", "le", "plateau_dev_L", "plateau_dev_tol", "CMP", "FUN-4"),
    Req("CMP-M1-R", "le", "plateau_dev_R", "plateau_dev_tol", "CMP", "FUN-4"),
    Req("CMP-M2-L", "le", "brake_dist_L", "brake_dist_ceiling", "CMP", "FUN-5"),
    Req("CMP-M2-R", "le", "brake_dist_R", "brake_dist_ceiling", "CMP", "FUN-5"),
    Req("CMP-M3-L", "ge", "sign_valid_L", "one", "CMP", "FUN-4"),
    Req("CMP-M3-R", "ge", "sign_valid_R", "one", "CMP", "FUN-4"),
    Req("CMP-M4-L", "le", "post_stop_travel_L", "post_stop_bound", "CMP", "FUN-5"),
    Req("CMP-M4-R", "le", "post_stop_travel_R", "post_stop_bound", "CMP", "FUN-5"),
    Req("CMP-M5-L", "le", "encoder_dropouts_L", "zero", "CMP", "FUN-2"),
    Req("CMP-M5-R", "le", "encoder_dropouts_R", "zero", "CMP", "FUN-2"),
    Req("CMP-U1-A", "le", "noise_sigma_A", "noise_bound", "CMP", "FUN-1"),
    Req("CMP-U1-B", "le", "noise_sigma_B", "noise_bound", "CMP", "FUN-1"),
    Req("CMP-U2-A", "le", "offset_residual_A", "offset_tol", "CMP", "FUN-1"),
    Req("CMP-U2-B", "le", "offset_residual_B", "offset_tol", "CMP", "FUN-1"),
    Req("CMP-U3-A", "le", "data_age_err_A", "data_age_tol", "CMP", "FUN-1"),
    Req("CMP-U3-B", "le", "data_age_err_B", "data_age_tol", "CMP", "FUN-1"),
    Req("CMP-U4-A", "le", "subfloor_leakage_A", "zero", "CMP", "FUN-1"),
    Req("CMP-U4-B", "le", "subfloor_leakage_B", "zero", "CMP", "FUN-1"),
    Req("CMP-U5-A", "le", "refresh_A", "refresh_bound", "CMP", "FUN-1"),
    Req("CMP-U5-B", "le", "refresh_B", "refresh_bound", "CMP", "FUN-1"),
    Req("CMP-I1", "le", "imu_drift_10s", "imu_drift_bound", "CMP", "FUN-4"),
    Req("CMP-I2", "ge", "contact_witness_armed", "one", "CMP", "FUN-7"),
    Req("CMP-H1", "le", "loop_jitter_p95", "jitter_bound", "CMP", "FUN-3"),
    Req("CMP-H2", "le", "emission_duration", "emission_budget", "CMP", "FUN-6"),
    Req("CMP-R1", "le", "rear_track_error", "rear_track_bound", "CMP", "FUN-2"),
]

# Spec requirement tree (RS-WAR v1.0 section 5, PRIMARY edges only) — the
# reference the model's realized edge-set must match. CMP families expand to
# per-device instances (spec section 4.4 header).
SPEC_TREE_EDGES = {
    ("STK-2", "SYS-1"), ("STK-4", "SYS-2"), ("STK-1", "SYS-3"),
    ("STK-3", "SYS-4"), ("SYS-3", "SYS-5"), ("STK-4", "SYS-6"),
    ("STK-5", "SYS-7"), ("STK-1", "SYS-8"), ("STK-7", "SYS-9"),
    ("STK-7", "SYS-10"), ("STK-1", "SYS-11"), ("STK-1", "SYS-12"),
    ("STK-6", "SYS-13"),
    ("SYS-2", "FUN-1"), ("SYS-2", "FUN-2"), ("SYS-2", "FUN-3"),
    ("SYS-1", "FUN-4"), ("SYS-2", "FUN-5"), ("SYS-7", "FUN-6"),
    ("SYS-11", "FUN-7"),
    ("FUN-4", "CMP-M1-L"), ("FUN-4", "CMP-M1-R"),
    ("FUN-5", "CMP-M2-L"), ("FUN-5", "CMP-M2-R"),
    ("FUN-4", "CMP-M3-L"), ("FUN-4", "CMP-M3-R"),
    ("FUN-5", "CMP-M4-L"), ("FUN-5", "CMP-M4-R"),
    ("FUN-2", "CMP-M5-L"), ("FUN-2", "CMP-M5-R"),
    ("FUN-1", "CMP-U1-A"), ("FUN-1", "CMP-U1-B"),
    ("FUN-1", "CMP-U2-A"), ("FUN-1", "CMP-U2-B"),
    ("FUN-1", "CMP-U3-A"), ("FUN-1", "CMP-U3-B"),
    ("FUN-1", "CMP-U4-A"), ("FUN-1", "CMP-U4-B"),
    ("FUN-1", "CMP-U5-A"), ("FUN-1", "CMP-U5-B"),
    ("FUN-4", "CMP-I1"), ("FUN-7", "CMP-I2"),
    ("FUN-3", "CMP-H1"), ("FUN-6", "CMP-H2"),
    ("FUN-2", "CMP-R1"),
}

# ---------------------------------------------------------------------------
# EVALUATE — the computational satisfy/require roll-up. OPEN when an operand
# is unbound (uncalibrated, not zeroed).
# ---------------------------------------------------------------------------

def evaluate(observations=None, overrides=None):
    vals = base_vals(overrides)
    if observations:
        vals.update(observations)
        vals.update(derived(vals))  # derived may now resolve further
    out = []
    for r in REQS:
        m, t = vals.get(r.measured), vals.get(r.target)
        if m is None or t is None:
            out.append((r, "OPEN", m, t))
            continue
        ok = (m >= t) if r.kind == "ge" else (m <= t)
        out.append((r, "PASS" if ok else "FAIL", m, t))
    return out


def print_evaluate(results, title):
    print(title)
    npass = sum(1 for _, s, _, _ in results if s == "PASS")
    nfail = sum(1 for _, s, _, _ in results if s == "FAIL")
    nopen = sum(1 for _, s, _, _ in results if s == "OPEN")
    for r, s, m, t in results:
        rel = ">=" if r.kind == "ge" else "<="
        tag = " [OBJ]" if r.objective else ""
        mm = "unbound" if m is None else "%.4g" % m
        tt = "unbound" if t is None else "%.4g" % t
        print("  %-9s %-4s  %s %s %s  (%s %s %s)%s"
              % (r.rid, s, r.measured, rel, r.target, mm, rel, tt, tag))
    print("  roll-up: %d PASS / %d FAIL / %d OPEN of %d\n"
          % (npass, nfail, nopen, len(results)))

# ---------------------------------------------------------------------------
# STRUCTURAL AUDIT — the checks grammar cannot see, run mechanically:
#  (1) edge-set realized by REQS == spec tree edge-set
#  (2) every requirement reachable from the STK roots
#  (3) trace completeness: every Param names a SysML attribute & binder;
#      every Req operand resolves to a namespace key
# ---------------------------------------------------------------------------

def structural_audit(verbose=True):
    ok = True
    realized = {(r.parent, r.rid) for r in REQS if r.parent is not None}
    missing = SPEC_TREE_EDGES - realized
    extra = realized - SPEC_TREE_EDGES
    if missing or extra:
        ok = False
        if verbose:
            print("EDGE-SET MISMATCH: missing=%s extra=%s" % (missing, extra))
    ids = {r.rid for r in REQS}
    roots = {r.rid for r in REQS if r.parent is None}
    reach, frontier = set(roots), set(roots)
    children = {}
    for r in REQS:
        if r.parent:
            children.setdefault(r.parent, set()).add(r.rid)
    while frontier:
        nxt = set()
        for p in frontier:
            nxt |= children.get(p, set())
        nxt -= reach
        reach |= nxt
        frontier = nxt
    unreachable = ids - reach
    if unreachable:
        ok = False
        if verbose:
            print("UNREACHABLE FROM ROOTS:", unreachable)
    ns = set(base_vals().keys()) | {
        # evidence/observation keys supplied by test data (enumerated so a
        # typo in a Req row is caught here, not silently OPEN forever):
        "min_run_clearance", "speed_plateau_ratio", "rest_achieved",
        "estimates_committed", "operator_inputs_during_run",
        "telemetry_complete", "outer_duty_min", "brake_cmd_delay",
        "final_clearance", "post_stop_travel_max", "estimate_channels",
        "heading_dev_max", "hot_path_writes", "sentinel_emitted",
        "failsafe_latency", "invalid_sample_leakage", "census_validated",
        "gap_coverage", "odo_coverage", "fused_gap_at_trigger", "trim_max",
        "hold_duration", "rest_sample_count", "failsafe_coverage",
        "plateau_dev_L", "plateau_dev_R", "brake_dist_L", "brake_dist_R",
        "sign_valid_L", "sign_valid_R", "post_stop_travel_L",
        "post_stop_travel_R", "encoder_dropouts_L", "encoder_dropouts_R",
        "noise_sigma_A", "noise_sigma_B", "offset_residual_A",
        "offset_residual_B", "data_age_err_A", "data_age_err_B",
        "subfloor_leakage_A", "subfloor_leakage_B", "refresh_A", "refresh_B",
        "imu_drift_10s", "contact_witness_armed", "loop_jitter_p95",
        "emission_duration", "rear_track_error",
        "margin_floor", "closeness_ceiling", "stop_budget",
        "brake_dist_ceiling", "failsafe_latency_bound",
    }
    for r in REQS:
        for opn in (r.measured, r.target):
            if opn not in ns:
                ok = False
                if verbose:
                    print("UNRESOLVED OPERAND %s in %s" % (opn, r.rid))
    for k, p in PARAMS.items():
        if not p.sysml or not p.binder:
            ok = False
            if verbose:
                print("TRACE GAP on param", k)
    if verbose:
        print("STRUCTURAL AUDIT: %s  (%d requirements, %d edges, %d roots; "
              "edge-set == spec tree: %s; all reachable: %s)"
              % ("PASS" if ok else "FAIL", len(REQS), len(realized),
                 len(roots), not (missing or extra), not unreachable))
    return ok

# ---------------------------------------------------------------------------

def print_trace():
    print("TRACE SPINE (CMP/SYS parameter -> SysML attribute -> Python key -> "
          "TBD -> binding activity)")
    for k, p in PARAMS.items():
        print("  %-10s -> %-46s tbd=%-8s binder=%s"
              % (k, p.sysml, p.tbd, p.binder))
    print()


if __name__ == "__main__":
    print("=" * 150)
    print("EAM v1.0 — Wall-Approach Rover — pre-calibration snapshot "
          "(all parameters at priors; nothing bound; Tenet A3 in force)")
    print("=" * 150)
    structural_audit()
    print()
    print_trace()
    print_sweep(G_target=0.035)
    sig = illustrative_post_cal_sigmas()
    gt, rss = size_margin(sig)
    print("MARGIN SIZING PREVIEW (illustrative; real values at Gate B):")
    for k, s in sig.items():
        print("  %-46s %.1f mm" % (k, s * 1e3))
    print("  RSS sigma_stop = %.1f mm -> G_target = z*RSS = %.1f mm (z=%.1f)"
          % (rss * 1e3, gt * 1e3, Z_MARGIN))
    p1, p5, sd = mc_check(gt, sig)
    print("  Monte-Carlo check (n=2e5): P(contact per run)=%.4f%%, "
          "P(any contact in 5)=%.3f%% at sigma=%.1f mm\n"
          % (p1 * 100, p5 * 100, sd * 1e3))
    print_evaluate(evaluate(), "REQUIREMENT ROLL-UP (pre-calibration; "
                   "OPEN = operand unbound, awaiting calibration):")
