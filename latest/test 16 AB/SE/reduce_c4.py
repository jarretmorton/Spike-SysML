"""C4 ground truth = 14 mm.  Two T4 anchors now exist."""
import math

S = 1000.0
# (label, odo_at_trigger, v_at_trigger, measured_gap)
A = [("C2", 734.327, 473.083, 222.0),
     ("C4", 936.767, 487.302, 14.0)]

print("=== 1. FROZEN PREDICTION vs GROUND TRUTH (VP v1.2) ===")
pred, sig, meas = 23.0, 7.49, 14.0
print("  predicted %.1f mm   measured %.1f mm   residual %+.1f mm = %.2f sigma"
      % (pred, meas, meas - pred, (meas - pred) / sig))
print("  1-sigma band 15.5-30.5 : OUTSIDE")
print("  3-sigma band  0.5-45.5 : INSIDE     -> HELD AT 3 SIGMA")
print("  trigger reason 1, no contact, no failsafe -> NOT FALSIFIED")

print("\n=== 2. Delta, from both anchors ===")
D = []
for nm, od, v, g in A:
    d = S - od - g
    D.append((nm, v, d))
    print("  %s: Delta = 1000 - %.1f - %.0f = %.2f mm at v = %.1f mm/s"
          % (nm, od, g, d, v))
n = len(D)
dm = sum(d for _, _, d in D) / n
sd = math.sqrt(sum((d - dm) ** 2 for _, _, d in D) / (n - 1))
print("  mean %.2f mm, sd %.2f mm  (n=2)" % (dm, sd))
print("  budgeted sigma_delta at GATE B' was 4.00 mm -> the budget was RIGHT")

r = D[1][2] / D[0][2]
vr = D[1][1] / D[0][1]
print("\n  speed exponent implied: Delta ~ v^%.1f" % (math.log(r) / math.log(vr)))
print("  v^4 is unphysical -> a 3 %% speed change cannot explain a 13 %% Delta")
print("  change.  The difference is RUN-TO-RUN SCATTER, not speed dependence.")
print("  Do NOT fit a speed law to it (tenet A2).  Delta is a constant + noise.")

print("\n=== 3. Updated expectation at the LOCKED configuration (G = 23) ===")
G, dt, v = 23.0, 0.011, 487.3
t_eff = 0.09239
eps = v * dt / 2.0
E = G + t_eff * v - eps - dm
print("  realised gap = G + t_eff*v - sampling_overshoot - Delta")
print("               = %.1f + %.1f - %.1f - %.2f = %.2f mm" % (G, t_eff*v, eps, dm, E))
print("  (C4 drew eps = 4.79 and Delta = 49.23, giving 14.0 -- consistent)")

terms = {"start_line_placement": 5.0, "Delta_run_to_run": sd,
         "odometry_dead_reckoning": 2.0, "yaw_corner": 3.0,
         "sampling_phase": v * dt / math.sqrt(12)}
s = math.sqrt(sum(x * x for x in terms.values()))
for k, x in sorted(terms.items(), key=lambda kv: -kv[1]):
    print("      %-26s %5.2f" % (k, x))
print("  sigma_gap %.2f mm   3 sigma %.2f mm" % (s, 3 * s))
p = 0.5 * math.erfc((E / s) / math.sqrt(2))
print("  P(contact) per run %.4f   over 5 runs %.4f" % (p, 1 - (1 - p) ** 5))

print("\n=== 4. Would raising G be worth it? ===")
for Gn in (23.0, 27.0, 31.0):
    En = Gn + t_eff * v - eps - dm
    pn = 0.5 * math.erfc((En / s) / math.sqrt(2))
    print("  G=%2.0f -> E[gap] %5.1f mm, P(>=1 contact in 5) %.4f, "
          "needs re-verification: %s" % (Gn, En, 1 - (1 - pn) ** 5,
                                         "no" if Gn == 23 else "YES"))
print("  Raising G costs a 5th characterisation run and a 4th measurement to")
print("  buy ~2 %% contact probability and lose ~4-8 mm of closeness, AND would")
print("  mean operating an artifact different from the verified one.")
print("  DECISION: lock rev D UNCHANGED at G = 23.")
