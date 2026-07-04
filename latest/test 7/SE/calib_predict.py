"""GATE B frozen-prediction computation.

Loads wallrun_model with the values calibrated from C1-v2 / C2 / C3 + operator
measurement #1, at the committed operating trigger, and prints predict() and
evaluate() so the frozen numbers can be recorded in the Verification Plan.

Calibration provenance (see Calibration Report):
  k_speed   28.2 mm/rad  = 0.0282 m/rad   (crawl, 3 runs; cross-checked by stop segment)
  omega_max 1042 deg/s   = 18.19 rad/s    (steady cruise, 3 runs)
  b (A off) +7 mm                         (operator #1: true 196 vs A 203)
  D_stop_eff 54 mm  (reported-trigger -> true-rest overshoot 61 mm, minus b=7;
                     lumps true stopping distance + sensor/loop latency; the
                     ENCODER under-counts this via brake slip and is NOT used)
  sigma_stop 18 mm  (run-to-run spread of the final rest position for a fixed
                     trigger: C2 true-rest 125, C3 true-rest 150; SD~17, +hedge)
  heading_drift 5.5 deg (repeatable; tol set to 10 deg, corner effect folded in)
  rest_speed ~7 mm/s (held; below the 20 deg/s settle threshold)
"""
import wallrun_model as wm
from wallrun_model import Params

R_TRIGGER = 121.0   # committed operating trigger on sensor A (reported mm)

p = Params(
    # calibrated physical
    k_speed_m_rad=0.0282,
    omega_max_rad_s=18.19,
    t_response_s=0.05,          # loop+refresh; folded into measured D_stop (informational)
    a_decel_mm_s2=2000.0,       # informational only (D_stop measured directly)
    D_stop_mm=54.0,             # effective (reported-trigger->true-rest minus b)
    sigma_stop_mm=18.0,
    b_mm=7.0,
    alpha=1.0,
    r_min_mm=40.0,
    # uncertainties
    sigma_b_mm=6.0,
    sigma_pred_mm=6.0,
    # design / assurance
    R_trigger_mm=R_TRIGGER,
    k_margin=3.0,
    contact_floor_mm=0.0,
    rest_tol_mm_s=10.0,         # 20 deg/s settle threshold ~ 9.8 mm/s
    heading_tol_deg=10.0,       # budget; corner effect at 10deg ~9mm folded into sigma_pred
    resid_tol_mm=8.0,
    k_tol_frac=0.05,
    t_chain_bound_s=0.10,
    # measured-at-run (for EVALUATE)
    cruise_speed_mm_s=513.0,    # = omega*k
    omega_achieved_rad_s=18.19,
    rest_speed_mm_s=7.0,
    heading_drift_deg=5.5,
    trigger_reading_mm=R_TRIGGER,
    sensor_resid_mm=2.0,
    k_resid_frac=0.03,
)

pr = wm.predict(p)
print("=== FROZEN PREDICTION  (committed R_trigger = %.0f mm reported, sensor A) ===" % R_TRIGGER)
for k in ('v_max_mm_s', 'D_stop_used_mm', 'sigma_rss_mm', 'safety_margin_mm',
          'g_target_mm', 'R_trigger_mm', 'final_clearance_mm',
          'rest_reading_reported_mm', 'rest_reading_valid', 'trigger_above_rmin'):
    v = pr.get(k)
    if isinstance(v, float):
        print("  %-26s %.2f" % (k, v))
    else:
        print("  %-26s %s" % (k, v))

print("\n=== ROLL-UP  (satisfy/require) ===")
ev = wm.evaluate(p)
order = ['SYS-1', 'SYS-2', 'SYS-3', 'SYS-3b', 'SYS-4', 'SYS-5',
         'CMP-1', 'CMP-2', 'CMP-3', 'CMP-4', 'CMP-5', 'CMP-6', 'CMP-7', 'ROLLUP']
for rid in order:
    if rid in ev:
        r = ev[rid]
        m = r['measured']; t = r['target']
        ms = ("%.2f" % m) if isinstance(m, float) else str(m)
        ts = ("%.2f" % t) if isinstance(t, float) else str(t)
        print("  %-7s %-5s  measured=%-9s target=%-9s  %s"
              % (rid, r['verdict'], ms, ts, r.get('note', '')))
