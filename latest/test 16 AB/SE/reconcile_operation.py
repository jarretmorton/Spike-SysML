"""Operation close-out reconciliation."""
import math

S = 1000.0
T_EFF = 0.09239
PRED = 23.0          # frozen, VP v1.2
SIG_PRED = 7.49

# run, trig_odo, v, onboard_est, measured
R = [(1, 936.044, 486.820, 19.0, 14.0),
     (2, 936.526, 460.310, 20.9, 29.0),
     (3, 932.429, 492.845, 22.0, 30.0),
     (4, 935.080, 475.734, 21.0, 23.0),
     (5, 935.562, 483.205, 19.8, 27.0)]


def stats(x):
    m = sum(x) / len(x)
    s = math.sqrt(sum((a - m) ** 2 for a in x) / (len(x) - 1))
    return m, s


meas = [r[4] for r in R]
est = [r[3] for r in R]
mm, ms = stats(meas)
em, es = stats(est)

print("=== PER-RUN RECONCILIATION ===")
print("| run | PREDICTED (frozen) | onboard ESTIMATE | MEASURED | est-meas | contact |")
print("|---|---|---|---|---|---|")
for n, tod, v, e, g in R:
    print("| %d | %.1f mm | %.1f mm | **%.1f mm** | %+.1f mm | none |"
          % (n, PRED, e, g, e - g))
print("| **mean** | **%.1f** | **%.1f** | **%.1f** | **%+.1f** | **0/5** |"
      % (PRED, em, mm, em - mm))
print("| **sd**   | (sigma %.2f) | %.2f | **%.2f** | %.2f | |"
      % (SIG_PRED, es, ms, stats([e - g for _, _, _, e, g in R])[1]))

print("\n=== DID THE COMMITTED PREDICTION HOLD? ===")
print("  frozen prediction (VP v1.2) ....... %.1f mm, sigma %.2f mm" % (PRED, SIG_PRED))
print("  measured mean over 5 runs ......... %.1f mm" % mm)
print("  residual .......................... %+.1f mm = %.2f sigma"
      % (mm - PRED, (mm - PRED) / SIG_PRED))
inside1 = sum(1 for g in meas if PRED - SIG_PRED <= g <= PRED + SIG_PRED)
inside3 = sum(1 for g in meas if PRED - 3 * SIG_PRED <= g <= PRED + 3 * SIG_PRED)
print("  runs inside 1 sigma (15.5-30.5) ... %d / 5" % inside1)
print("  runs inside 3 sigma ( 0.5-45.5) ... %d / 5" % inside3)
print("  PREDICTED sigma %.2f  vs  OBSERVED run-to-run sd %.2f" % (SIG_PRED, ms))
print("  -> the uncertainty budget was correct, marginally conservative.")

print("\n=== Delta ACROSS EVERY GROUND-TRUTHED STOP (n=7) ===")
D = []
for n, tod, v, e, g in R:
    D.append(("op%d" % n, v, S - tod - g))
D.append(("C2", 473.083, 43.673))
D.append(("C4", 487.302, 49.233))
for nm, v, d in D:
    print("  %-4s v=%.1f  Delta=%.2f mm" % (nm, v, d))
dv = [d for _, _, d in D]
dm, ds = stats(dv)
print("  mean %.2f mm, sd %.2f mm  (t_eff used in flight implied %.2f mm)"
      % (dm, ds, T_EFF * 480))
vs = [v for _, v, _ in D]
vm, _ = stats(vs)
cov = sum((v - vm) * (d - dm) for _, v, d in D) / (len(D) - 1)
r = cov / (stats(vs)[1] * ds)
print("  correlation of Delta with speed: r = %+.2f  -> %s"
      % (r, "no usable speed dependence" if abs(r) < 0.6 else "speed-dependent"))

print("\n=== WHERE THE BUDGET WAS RIGHT AND WHERE IT WAS WRONG ===")
print("  predicted total sigma  %.2f mm   observed  %.2f mm   -> RIGHT" % (SIG_PRED, ms))
print("  predicted sigma_Delta   4.00 mm   observed  %.2f mm   -> UNDER-estimated" % ds)
resid = math.sqrt(max(ms ** 2 - ds ** 2, 0.0))
print("  implied all-other-terms  %.2f mm   (budgeted 6.3 mm)   -> OVER-estimated" % resid)
print("  The total was right for partly the wrong reasons: braking scatter is")
print("  larger than modelled, start-line placement much better than the 5.0 mm")
print("  I assumed.  Decomposition wrong, roll-up right.")

print("\n=== THE GATE-C DECISION, RE-EXAMINED ===")
print("  At GATE C the C4 residual (-9 mm) could have been read as bias.")
print("  Folding it in as bias predicted E[gap] = 18.9 mm and argued for G = 27.")
print("  I judged it a -1.2 sigma NOISE draw and locked G = 23 unchanged.")
print("  Operation mean came in at %.1f mm, vs 23.0 predicted and 18.9 'corrected'."
      % mm)
print("  -> the noise reading was correct.  Had I raised G to 27 the mean would")
print("     have been ~%.1f mm, costing a 5th run, a 4th measurement, and 4 mm"
      % (mm + 4))
print("     of the objective for no gain in contacts (0/5 either way).")
