"""GATE B frozen-prediction computation -- v2 (re-derivation after V1).

For prog_v4 (encoder-travel trigger). V1 falsified v1 because the ultrasonic
trigger fired late under a stalled loop. The encoder trigger removes trigger
jitter, so the final-gap spread is now dominated by the braking spread alone.

Calibration update (Calibration Report + V1):
  D_stop_eff 58 mm  (true trigger->rest; C2 66, C3 42, V1 65 -- V1 anchored by
                     operator 28 mm ground truth)
  sigma_stop 15 mm  (braking spread; 3 samples 66/42/65, SD~14, +hedge; the
                     encoder trigger removes the loop-timing term)
  k 27.5 mm/rad     (long-baseline rolling, C2/C3/V1 27.47 +-0.8%)
  b +7 mm ; trigger reference = A_start read at ~930 mm (reliable range)

Committed design: TARGET_GAP 55 mm, TARGET_TRUE_TRIGGER = 55+58 = 113 mm true,
i.e. effective reported trigger = 113 + b(7) = 120 mm in the model's framing.
"""
import wallrun_model as wm
from wallrun_model import Params

R_TRIGGER_EQUIV = 120.0   # = TARGET_TRUE_TRIGGER(113) + b(7), model's reported framing

p = Params(
    k_speed_m_rad=0.0275,
    omega_max_rad_s=18.19,
    t_response_s=0.03,          # encoder trigger; loop now ~5 ms (informational)
    a_decel_mm_s2=2200.0,       # informational
    D_stop_mm=58.0,
    sigma_stop_mm=15.0,
    b_mm=7.0,
    alpha=1.0,
    r_min_mm=40.0,
    sigma_b_mm=6.0,
    sigma_pred_mm=6.0,
    R_trigger_mm=R_TRIGGER_EQUIV,
    k_margin=3.0,
    contact_floor_mm=0.0,
    rest_tol_mm_s=10.0,
    heading_tol_deg=10.0,
    resid_tol_mm=8.0,
    k_tol_frac=0.05,
    t_chain_bound_s=0.10,
    cruise_speed_mm_s=500.0,    # = omega*k (18.19*27.5)
    omega_achieved_rad_s=18.19,
    rest_speed_mm_s=7.0,
    heading_drift_deg=5.7,
    trigger_reading_mm=930.0,   # A_start reference actually read (reliable range)
    sensor_resid_mm=2.0,
    k_resid_frac=0.008,         # long-baseline k spread 0.8%
)

pr = wm.predict(p)
print("=== FROZEN PREDICTION v2 (prog_v4 encoder-travel; TARGET_GAP=55, D_stop=58) ===")
for k in ('v_max_mm_s', 'D_stop_used_mm', 'sigma_rss_mm', 'safety_margin_mm',
          'g_target_mm', 'R_trigger_mm', 'final_clearance_mm',
          'rest_reading_reported_mm', 'trigger_above_rmin'):
    v = pr.get(k)
    print("  %-26s %s" % (k, ("%.2f" % v) if isinstance(v, float) else v))

print("\n=== ROLL-UP ===")
ev = wm.evaluate(p)
for rid in ['SYS-1','SYS-2','SYS-3','SYS-3b','SYS-4','SYS-5',
            'CMP-1','CMP-2','CMP-3','CMP-4','CMP-5','CMP-6','CMP-7','ROLLUP']:
    if rid in ev:
        r = ev[rid]; m=r['measured']; t=r['target']
        ms = ("%.2f"%m) if isinstance(m,float) else str(m)
        ts = ("%.2f"%t) if isinstance(t,float) else str(t)
        print("  %-7s %-5s measured=%-9s target=%-9s %s" % (rid,r['verdict'],ms,ts,r.get('note','')))
