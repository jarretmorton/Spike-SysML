"""Generate the GATE A / Calibration Plan section-0 sensitivity table."""
from dataclasses import replace
import wallstop_model as M

TIER = {0: "T0 none", 1: "T1 physics-bounded", 2: "T2 datasheet",
        3: "T3 onboard multi-point", 4: "T4 external ground truth"}

d = M.nominal_params()
rows = M.sensitivity_table(d)
base = M.predict(d)["final_clearance"]
sig0, _ = M.sigma_gap(d)

print("nominal design point: v=%.0f mm/s, target=%.0f mm, sigma_gap=%.2f mm, "
      "contact margin(3s)=%.1f mm\n" % (M.steady_speed(d), d.target_gap, sig0,
                                        M.contact_margin(d)))

hdr = ("| # | parameter | assumed prior range | mechanism | objective / "
       "hard-constraint-margin sensitivity | knowledge tier | priority |")
print(hdr)
print("|---|---|---|---|---|---|---|")
for r in rows:
    if r["mech"] == "mean":
        sens = ("final clearance %.0f .. %.0f mm (**span %.0f mm**)%s"
                % (r["gmin"], r["gmax"], r["span"],
                   "; **CONTACT at the low end**" if r["contact"] else ""))
    elif r["mech"] == "sigma":
        sens = ("sigma_gap %.1f -> %.1f mm; required 3s margin %.0f -> %.0f mm"
                % (r["sig_lo"], r["sig_hi"], 3 * r["sig_lo"], 3 * r["sig_hi"]))
    else:
        sens = "no effect on the mean; gates channel validity near the stop"
    rng = ("%.3g .. %.3g" % (r["lo"], r["hi"]))
    print("| %d | `%s` | %s | %s | %s | %s | %d |"
          % (r["priority"], r["param"], rng, r["mech"], sens,
             TIER[r["tier"]], r["priority"]))

# ---- adaptive vs fixed threshold: justification of the trigger law ----------
print("\n\nADAPTIVE vs FIXED trigger, true speed swept over its prior range")
print("| true steady speed (mm/s) | final clearance, ADAPTIVE law | "
      "final clearance, FIXED threshold |")
print("|---|---|---|")
u_fixed = M.trigger_threshold_ranger_units(M.steady_speed(d), d)
for v in (250, 350, 470, 600, 800):
    t = replace(d, v_max_ground=float(v))
    g_ad = M.realized_final_clearance(d, t)
    vt = M.steady_speed(t)
    g_fx = ((u_fixed - M._mean_offset(t)) / t.alpha_scale
            - M.stopping_distance(vt, t.t_response, t.a_brake))
    print("| %d | %.1f | %.1f |" % (v, g_ad, g_fx))

# ---- what one operator measurement buys ------------------------------------
print("\n\nLUMP ANCHORED BY ONE OPERATOR MEASUREMENT")
print("The flight law fires at u_thr = c + target + v*t_r + v^2/(2a).")
print("Everything except `target` enters the realised clearance ONLY through")
print("the lump  Q(v) = c + v*t_r + v^2/(2a)  (ranger units).")
for name in ("c_offset_A", "t_response", "a_brake"):
    lo, hi, nom, tier, why = M.PRIORS[name]
    rows2 = M.sweep(name, d, d, lo, hi, 3)
    print("  d(clearance)/d(%s) over prior: %.0f mm span"
          % (name, max(g for _, g in rows2) - min(g for _, g in rows2)))
qv = M._mean_offset(d) + M.stopping_distance(
    M.steady_speed(d), d.t_response, d.a_brake)
print("  nominal Q(v) = %.1f mm; a single external measurement of the final"
      " clearance at the operating point determines Q exactly:" % qv)
print("  Q = u_thr_logged - g_measured   ->  sigma_Q = sigma_measurement (~2 mm)")
