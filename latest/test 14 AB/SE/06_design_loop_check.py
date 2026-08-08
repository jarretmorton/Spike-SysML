#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
06_design_loop_check.py -- does the DESIGN PROCEDURE close?

The question is not "will the rover stop 25 mm from the wall" -- no simulation can
answer that.  The question is whether the procedure itself is sound:

    calibrated parameters  ->  executable model  ->  trigger threshold
                           ->  flight program    ->  no contact

If the arithmetic that converts bound parameters into R_TRIG is wrong, that error
is invisible in the SysML roll-up (which would happily evaluate a wrong number as
PASS) and would only appear on the wall.  Running the real program against a rover
whose truth we KNOW exposes it for free.

Method: draw a rover from the prior ranges, hand the model perfect knowledge of it
(the best case a calibration could achieve), let the model choose R_TRIG, run the
actual flight program against that rover, and record the outcome.  Repeated over
draws this also shows how much of the predicted sigma_g is real.

This validates the PROCEDURE, not the rover.  No parameter is bound from it.
"""

from __future__ import annotations

import importlib
import io
import json
import random
import re
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import wall_stop_model as M


def make_operation_source(run1_src: str, r_trig: float, k: float,
                          v_nom: float, s_cal: float, fwd_axis: int = 2) -> str:
    """Derive the operation program from the RUN-1 program, as the plan specifies:
    replace discovery with the constant map, delete the creep, set four constants."""
    s = run1_src
    s = re.sub(r"^R_TRIG\s*=\s*\d+", "R_TRIG        = %d" % round(r_trig), s, flags=re.M)
    s = re.sub(r"^K_MM_PER_DEG\s*=\s*[\d.]+", "K_MM_PER_DEG  = %.4f" % k, s, flags=re.M)
    s = re.sub(r"^V_NOM_MM_S\s*=\s*\d+", "V_NOM_MM_S    = %d" % round(v_nom), s, flags=re.M)
    s = re.sub(r"^S_CAL_MM\s*=\s*\d+", "S_CAL_MM      = %d" % round(s_cal), s, flags=re.M)
    # delete PHASE E (creep) -- everything between the PHASE E banner and PHASE F
    i = s.index("    # PHASE E")
    j = s.index("    # PHASE F")
    s = s[:i - 78] + s[j - 78:]
    return s


def draw_truth(rng: random.Random) -> dict:
    p = M.build_params()

    def u(name):
        lo, hi = p.p(name).prior
        return rng.uniform(lo, hi)

    return dict(
        omega_ceiling=u("omega_max_deg_s"),
        k=u("k_mm_per_deg"),
        a_brake_mm=u("a_decel_mm_s2"),
        a_coast_mm=1400.0,
        tau=u("tau_sensor_s"),
        refresh=u("T_refresh_s"),
        noise=u("sigma_n_mm"),
        bA=rng.uniform(-40.0, 80.0),
        floor=u("r_floor_mm"),
        g0=1000.0,
        accel_limit=3000.0,
        yaw_rate_bias=rng.uniform(-1.0, 1.0),
        mirrored=rng.random() < 0.5,
    )


def bind_model_to_truth(truth: dict, t_loop: float, n_stop: float) -> M.Params:
    """The best case a calibration could achieve: perfect knowledge of this rover.

    Note what is NOT perfect: the run-to-run and systematic uncertainty terms are
    still carried at plausible calibrated magnitudes, because a calibration never
    removes them -- it only measures them.
    """
    p = M.build_params()
    b = dict(
        omega_max_deg_s=truth["omega_ceiling"], k_mm_per_deg=truth["k"],
        a_decel_mm_s2=truth["a_brake_mm"], sym_dev_deg_s=5.0,
        T_refresh_s=truth["refresh"], tau_sensor_s=truth["tau"],
        sigma_n_mm=truth["noise"], b_offset_mm=truth["bA"],
        r_floor_mm=truth["floor"], delta_AB_mm=10.0,
        t_loop_s=t_loop, t_chain_s=0.002,
        rel_sigma_S=0.09, n_S_samples=n_stop, u_b_mm=2.0,
        theta_dev_deg=1.0, sigma_theta_deg=0.5, c_yaw_mm_per_deg=1.3,
        e_odo_mm=8.0, delta_bs_mm=15.0, sigma_meas_mm=1.0, R0_mm=1000.0,
        k_sigma=3.0, t_stop_max_s=0.5, theta_max_deg=5.0, eps_est_mm=10.0,
        g_goal_mm=30.0, contact_floor_mm=0.0,
    )
    for kk, vv in b.items():
        p.bind(kk, vv, 2, "simulated calibration")
    return p


def one_trial(seed: int, run1_src: str, verbose: bool = False):
    rng = random.Random(seed)
    truth = draw_truth(rng)

    p = bind_model_to_truth(truth, t_loop=0.014, n_stop=2.0)
    pred = M.predict(p)
    src = make_operation_source(run1_src, pred.R_trig_mm, truth["k"],
                                v_nom=pred.v_mm_s, s_cal=pred.S_mm)

    # fresh simulator per trial
    for mod in list(sys.modules):
        if mod.startswith("pybricks") or mod == "usys" or mod.endswith("sim_harness"):
            del sys.modules[mod]
    sim = importlib.import_module("05_sim_harness".replace("05_", "sim_")) \
        if False else None
    spec = importlib.util.spec_from_file_location("simh", HERE / "05_sim_harness.py")
    simh = importlib.util.module_from_spec(spec)
    sys.modules["simh"] = simh
    spec.loader.exec_module(simh)
    simh.TRUTH.update(truth)
    simh.TRUTH["bB"] = truth["bA"] + 10.0
    simh.random.seed(seed)
    simh.W = simh.World()

    us = simh.install()
    g = {"__name__": "__main__"}
    exc = None
    try:
        exec(compile(src, "operation_program.py", "exec"), g)
    except Exception as e:                        # noqa: BLE001
        exc = e
    out = us.stdout.getvalue()

    vals = {}
    for line in out.splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        if "sensor" in d:
            vals.setdefault(d["sensor"], d["value"])

    # SYS-8 channel selection, as the rover will implement it
    r_rest = vals.get("r_rest_fused", float("nan"))
    if r_rest > truth["floor"] + truth["noise"]:
        est = r_rest - truth["bA"]
        chan = "P"
    else:
        est = vals.get("gap_est_fallback_raw", float("nan")) - truth["bA"]
        chan = "F"
    return dict(
        seed=seed, contact=simh.W.contact, true_gap=simh.W.g,
        predicted=pred.g_mean_mm, R_trig=pred.R_trig_mm,
        onboard_est=est, chan=chan, reason=vals.get("trigger_reason"),
        S_ranger=vals.get("S_ranger"), wall_time=simh.W.t, exc=exc,
        v=truth["omega_ceiling"] * truth["k"],
    )


def main():
    run1_src = (HERE / "04_run1_program.py").read_text()
    print("=" * 92)
    print("DESIGN-LOOP CHECK -- model picks R_TRIG, the real program drives it")
    print("=" * 92)
    print(f"{'seed':>4} {'v mm/s':>7} {'R_trig':>7} {'pred gap':>9} {'true gap':>9}"
          f" {'onboard est':>12} {'err':>7} {'why':>4} {'ch':>3} {'contact':>8}")
    rows = []
    for seed in range(1, 13):
        r = one_trial(seed, run1_src)
        rows.append(r)
        if r["exc"]:
            print(f"{seed:>4}  EXCEPTION: {type(r['exc']).__name__}: {r['exc']}")
            continue
        err = r["onboard_est"] - r["true_gap"]
        print(f"{seed:>4} {r['v']:>7.0f} {r['R_trig']:>7.0f} {r['predicted']:>9.1f}"
              f" {r['true_gap']:>9.1f} {r['onboard_est']:>12.1f} {err:>7.1f}"
              f" {int(r['reason'] or 0):>4} {r['chan']:>3} {str(r['contact']):>8}")

    ok = [r for r in rows if not r["exc"]]
    contacts = sum(1 for r in ok if r["contact"])
    gaps = [r["true_gap"] for r in ok]
    errs = [r["onboard_est"] - r["true_gap"] for r in ok if r["onboard_est"] == r["onboard_est"]]
    resid = [r["true_gap"] - r["predicted"] for r in ok]
    print()
    print(f"trials {len(ok)} | CONTACTS {contacts} | true gap "
          f"min {min(gaps):.1f} mean {sum(gaps)/len(gaps):.1f} max {max(gaps):.1f} mm")
    print(f"onboard estimate error: mean {sum(errs)/len(errs):+.2f} mm, "
          f"max |err| {max(abs(e) for e in errs):.2f} mm")
    print(f"prediction residual (true - predicted): mean {sum(resid)/len(resid):+.2f} mm, "
          f"max |resid| {max(abs(x) for x in resid):.2f} mm")
    print()
    print("Interpretation: contacts must be ZERO and the onboard estimate error must sit")
    print("inside SYS-8's limit, or the design PROCEDURE is defective independently of")
    print("any calibration. This says nothing about the physical rover.")


if __name__ == "__main__":
    import importlib.util  # noqa: F401
    main()
