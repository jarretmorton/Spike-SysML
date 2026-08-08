"""C1 pre-run safety: minimise the realised clearance over the FULL prior box."""
from dataclasses import replace
from itertools import product
import wallstop_model as M

# The C1 design as flashed (conservative priors, see c1_characterisation.py)
design = M.nominal_params(
    c_offset_A=120.0, c_offset_B=120.0,      # PRIOR UPPER
    t_response=0.150,                        # PRIOR UPPER
    a_brake=1000.0,                          # PRIOR LOWER
    k_travel=0.47,                           # PRIOR NOMINAL
    target_gap=350.0,
)

P = M.PRIORS
axes = {
    "c_offset_A": [P["c_offset_A"][0], P["c_offset_A"][1]],
    "alpha_scale": [P["alpha_scale"][0], P["alpha_scale"][1]],
    "k_travel": [P["k_travel"][0], P["k_travel"][1]],
    "t_response": [P["t_response"][0], P["t_response"][1]],
    "a_brake": [P["a_brake"][0], P["a_brake"][1]],
    "v_max_ground": [P["v_max_ground"][0], P["v_max_ground"][1]],
}
names = list(axes)

def scan(design, label):
    worst, wcfg = 1e9, None
    best = -1e9
    for combo in product(*[axes[n] for n in names]):
        kw = dict(zip(names, combo))
        kw["c_offset_B"] = kw["c_offset_A"]
        truth = replace(design, **kw)
        g = M.realized_final_clearance(design, truth)
        if g < worst:
            worst, wcfg = g, dict(kw)
        if g > best:
            best = g
    print("%s: %d corners" % (label, 2 ** len(names)))
    print("   worst-case final clearance  %+8.1f mm" % worst)
    print("   best-case  final clearance  %+8.1f mm" % best)
    print("   worst corner: " + ", ".join("%s=%g" % (k, v)
                                          for k, v in sorted(wcfg.items())
                                          if k != "c_offset_B"))
    print("   VERDICT: %s\n" % ("NO CONTACT anywhere in the prior box"
                                if worst > 0 else "*** CONTACT POSSIBLE ***"))
    return worst

print("=== C1 as designed (TARGET_C1 = 350 mm) ===")
w350 = scan(design, "full prior box")

print("=== sensitivity of the C1 stand-off choice ===")
for tg in (150.0, 200.0, 250.0, 300.0, 350.0, 400.0):
    d = replace(design, target_gap=tg)
    worst = 1e9
    for combo in product(*[axes[n] for n in names]):
        kw = dict(zip(names, combo))
        kw["c_offset_B"] = kw["c_offset_A"]
        g = M.realized_final_clearance(d, replace(d, **kw))
        worst = min(worst, g)
    print("   TARGET_C1 = %3.0f mm  ->  worst-case clearance %+7.1f mm  %s"
          % (tg, worst, "OK" if worst > 0 else "CONTACT"))

print("\n=== expected C1 outcome at the PRIOR NOMINAL truth ===")
truth = M.nominal_params()
g = M.realized_final_clearance(design, truth)
v = M.steady_speed(truth)
print("   steady speed            %.0f mm/s" % v)
print("   trigger threshold (u)   %.0f mm reported"
      % M.trigger_threshold_ranger_units(v, design))
print("   expected stop clearance %.0f mm  -> creep sweep spans 0..%.0f mm"
      % (g, g))
print("   approach travel before trigger  %.0f mm (accel needs ~%.0f mm)"
      % (1000 - (g + M.stopping_distance(v, truth.t_response, truth.a_brake)),
         v * v / (2 * 4000 * truth.k_travel)))
