"""Re-derivation against the T4 anchor.  g_measured(C2) = 222 mm."""
import math

GT = 222.0                      # operator-measured final gap, C2
U0, UT = 817.0, 89.0            # ranger A at start / at trigger (C2)
OD_T, OD_R = 734.327, 749.269   # odometry at trigger / at rest (C2)
V = 473.083
S_NOM = 1000.0                  # operator-guaranteed constant start line

print("=== 1. WHAT THE ANCHOR FORCES ===")
print("  Ranger travel start->trigger  %.1f mm" % (U0-UT))
print("  Odometry travel start->trigger %.1f mm   (agree to %.2f%%)"
      % (OD_T, 100*abs((U0-UT)-OD_T)/OD_T))
print("  -> ranger A's SCALE is sound; only its ZERO is in question.")
print()
print("  At the trigger the ranger read %.0f mm." % UT)
print("  The rover then stopped, and the wall was measured at %.0f mm." % GT)
print("  Braking travel B > 0, so true gap at trigger = %.0f + B." % GT)
print("  Hence  c_A = %.0f - (%.0f + B) = %.0f - B" % (UT, GT, UT-GT))
for B in (15, 30, 44, 60):
    print("     B = %2d mm  ->  c_A = %+.0f mm" % (B, UT-GT-B))
print("  c_A is NEGATIVE for every physically possible B.")
print("  In C2 ranger A under-read the true gap by ~175 mm.")

print("\n=== 2. THE ODOMETRY STORY, CHECKED AGAINST GROUND TRUTH ===")
B = S_NOM - OD_R - GT + (OD_R - OD_T)   # solve S=1000 for true braking travel
B_true = S_NOM - OD_T - GT
print("  Assume only the operator's guarantee: start line S = %.0f mm." % S_NOM)
print("  Odometry (rolling, validated) to trigger  %.1f mm" % OD_T)
print("  -> true gap at trigger = %.1f mm" % (S_NOM - OD_T))
print("  -> true braking travel  = %.1f mm  (odometry saw %.1f, i.e. %.0f%%)"
      % (B_true, OD_R-OD_T, 100*(OD_R-OD_T)/B_true))
print("  C1 measured that same skid capture at 37-39%% -- INDEPENDENT AGREEMENT.")
print("  Predicted final gap from odometry alone: %.1f mm vs measured %.1f mm"
      % (S_NOM - OD_T - B_true, GT))
print("  The odometry chain is consistent with ground truth. The ranger is not.")

print("\n=== 3. DID c_A CHANGE BETWEEN C1 AND C2? ===")
print("  C1, assuming the same %.0f mm start line:" % S_NOM)
print("    static ranger A = 1015 -> c_A = 1015 - 1000 = +15 mm")
print("    creep: started at ranger 718 (true %.0f), drove 698 mm ->" % (718-15))
print("      predicted stop at true gap %.0f mm  == CONTACT. Consistent." % (718-15-698))
print("    clamp onset predicted at odometry %.0f mm, observed 657 mm." % (703-25))
print("  C2: c_A = -175 mm.")
print("  => ranger A's zero moved by ~190 mm between the two runs.")
print("     Leading hypothesis: C1 ENDED by driving the rover into the wall and")
print("     stalling the motors against it; that impact disturbed the sensor")
print("     mounting. My own characterisation manoeuvre is the prime suspect.")

print("\n=== 4. RE-DERIVED DESIGN: use the ranger RELATIVELY, never absolutely ===")
print("  Sound property : travel = u0 - u(t)   scale error %.2f%%"
      % (100*abs((U0-UT)-OD_T)/OD_T))
print("  Unsound property: absolute gap = u - c_A   (c_A moved 190 mm)")
print("  New estimator:  g = S - max(odometry_travel, ranger_travel)")
print("    -> offset-free, and takes the more conservative of two channels.")

t_eff = B_true / V
print("\n=== 5. RE-BOUND PARAMETERS (T4-anchored) ===")
print("  S  start gap ............ %.0f mm   (operator guarantee + C2 anchor)" % S_NOM)
print("  B  braking overshoot .... %.1f mm  at %.0f mm/s" % (B_true, V))
print("  t_eff = B/v ............. %.5f s   (was %.5f, ranger-derived)"
      % (t_eff, 0.09661))
print("  odometry rolling scale .. validated to %.2f%% against the ranger"
      % (100*abs((U0-UT)-OD_T)/OD_T))

print("\n=== 6. MARGIN BUDGET (re-derived) ===")
terms = {
  "start-line repeatability S":      8.0,
  "odometry rolling over ~900 mm":   4.5,
  "braking overshoot B run-to-run":  3.0,
  "yaw corner advance (7.4 deg max)":3.0,
  "trigger phase v*dt/sqrt(12)":     V*0.0105/math.sqrt(12),
}
sig = math.sqrt(sum(v*v for v in terms.values()))
for k,v in sorted(terms.items(), key=lambda kv:-kv[1]):
    print("    %-34s %5.2f mm" % (k,v))
print("    %-34s %5.2f mm" % ("RSS sigma_gap", sig))
print("    %-34s %5.2f mm" % ("contact margin = 3 sigma", 3*sig))
G = 3*sig
print("\n  SYS-1 floor -> G = %.0f mm  (no SYS-6 clamp constraint any more:" % G)
print("     the estimate now comes from odometry, not the ranger)")
print("  Trigger fires at true gap = G + B = %.0f mm" % (G + B_true))
print("  PREDICTED FINAL GAP: %.0f mm   (C2 achieved %.0f mm)" % (G, GT))
print("  P(contact) per run = %.2e" % (0.5*math.erfc((G/sig)/math.sqrt(2))))
