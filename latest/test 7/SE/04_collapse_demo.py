#!/usr/bin/env python3
"""
04_collapse_demo.py -- shows the central calibration strategy computationally.

The raw sensitivity table ranks k_speed, a_decel, t_response, omega_max HIGH/MED
on the objective. But their leverage flows through the PREDICTED stopping
distance D_stop = StoppingDistance(v_max, t_response, a_decel). Operation is at a
SINGLE speed, so (per the StoppingDistance template note) D_stop is measured
DIRECTLY at the operating point -- calibration point == operating point, zero
extrapolation. Pinning D_stop to its measured value and re-sweeping shows the
leverage of the prediction-only parameters collapse to ~0; what remains is what
we must still characterize.
"""
import wallrun_model as wm

base = wm._nominal_params()
pr0 = wm.predict(base)
Dstop_measured = pr0['D_stop_used_mm']       # 46.87 mm nominal (stand-in for the C1/C2 measurement)
Rtrig = pr0['R_trigger_mm']

def objective_swing(param, pin_dstop):
    """Max change in final clearance (mm) as `param` sweeps lo..hi, R_trigger
    fixed at nominal. pin_dstop=True holds D_stop at the measured value."""
    nom, lo, hi, tier, note = wm.PRIORS[param]
    clears = []
    for val in (lo, nom, hi):
        p = wm.replace(base, **{_field(param): val})
        p = wm.replace(p, R_trigger_mm=Rtrig)
        if pin_dstop:
            p = wm.replace(p, D_stop_mm=Dstop_measured)
        clears.append(wm.predict(p)['final_clearance_mm'])
    return max(clears) - min(clears)

def _field(prior_name):
    # PRIORS keys already match Params field names
    return prior_name

rows = []
for param in wm.PRIORS:
    raw = objective_swing(param, pin_dstop=False)
    pinned = objective_swing(param, pin_dstop=True)
    tier = wm.PRIORS[param][3]
    rows.append((param, raw, pinned, tier))

rows.sort(key=lambda r: -abs(r[1]))
print("=" * 76)
print("LEVERAGE COLLAPSE when D_stop is measured directly at the operating point")
print(f"  D_stop_measured (stand-in) = {Dstop_measured:.2f} mm ; R_trigger = {Rtrig:.2f} mm")
print("=" * 76)
print(f"{'parameter':<20}{'raw d_obj(mm)':>14}{'D_stop-pinned':>16}{'tier':>6}  note")
print("-" * 76)
for param, raw, pinned, tier in rows:
    note = ""
    if abs(raw) > 1 and abs(pinned) < 0.5:
        note = "COLLAPSES -> fed only the D_stop prediction"
    elif abs(pinned) >= 0.5:
        note = "residual leverage remains"
    print(f"{param:<20}{raw:>14.1f}{pinned:>16.1f}{tier:>6}  {note}")
print("-" * 76)
print("""Reading:
  * a_decel, t_response, omega_max -> objective leverage COLLAPSES to ~0 once
    D_stop is measured directly: they were only inputs to the D_stop prediction,
    which the direct measurement replaces. They are still LOGGED (feasibility
    cross-check; CMP-1/CMP-5 unit verification) but no longer drive the gap.
  * k_speed -> in this mm-level model it also pins out, BUT the real per-run
    D_stop is measured as encoder-delta x k_speed, so k_speed retains a RESIDUAL
    role in that conversion (~ (dk/k) x D_stop ~ 5 mm over the prior range).
    It therefore drops HIGH -> MEDIUM, not to zero: characterize onboard (tier 2).
  * b (sensor offset) -> UNITY leverage, unaffected by the collapse, tier 4, no
    onboard absolute channel. THIS is where the costed operator measurement goes.
  * sigma_stop -> zero objective leverage but sets the no-contact MARGIN (tier 3):
    characterize its spread via repeated runs (C1, C2).""")
