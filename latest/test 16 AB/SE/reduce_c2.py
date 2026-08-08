"""C2 verification-run reduction.  Free analysis."""
import math

U0, G0 = 817.0, 807.0
C_A, T_EFF = 10.0, 0.09661
TRIG_U, TRIG_OD, TRIG_V, TRIG_HD = 89.0, 734.327, 473.083, 1.108
REST_U, REST_OD, REST_HD = 92.0, 749.269, -7.428
SKID = 0.38          # fraction of braking travel odometry captured in C1
W_HALF = 65.0

print("=== C2 OBSERVED ===")
print("  start u_A %.0f  -> trigger u_A %.0f  -> rest u_A %.0f" % (U0, TRIG_U, REST_U))
print("  odometry  0 -> %.1f -> %.1f   (%.1f mm AFTER the brake command)"
      % (TRIG_OD, REST_OD, REST_OD - TRIG_OD))
print("  heading   +%.2f deg at trigger  ->  %.2f deg at rest  (%.1f deg of yaw)"
      % (TRIG_HD, REST_HD, TRIG_HD - REST_HD))
print("  overshoot measured on ranger A: %+.1f mm   <-- IMPOSSIBLE"
      % (TRIG_U - REST_U))

print("\n=== IMPOSSIBILITY, stated precisely ===")
print("  The rover advanced %.1f mm on odometry after the brake command," % (REST_OD-TRIG_OD))
print("  and odometry UNDER-reads braking travel (it captured %.0f%% in C1)," % (100*SKID))
print("  so true forward travel was >= %.1f mm.  Ranger A reported the wall" % (REST_OD-TRIG_OD))
print("  getting %0.f mm FARTHER.  A rest reading beyond the trigger reading is" % (REST_U-TRIG_U))
print("  on the unconditional-escalation list.")

print("\n=== WHEN did ranger A stop tracking? ===")
appr = [(1601,319),(1641,299),(1683,274),(1725,254),(1768,236),(1811,216),
        (1851,191),(1892,176),(1936,157),(1978,137),(2022,118),(2065,102),
        (2075,89)]
print("  approach steps (mm per ~42 ms sample):", end=" ")
print(", ".join("%d" % (appr[i][1]-appr[i+1][1]) for i in range(len(appr)-1)))
print("  -> tracking cleanly at ~20 mm/sample right up to the trigger.")
print("  after the trigger: 89, 89, 92, 92, 92, 92 ... 92 for ~60 consecutive")
print("     samples over 600 ms, spread = 0.0 mm.  The channel FROZE.")

print("\n=== THREE ONBOARD ESTIMATES OF THE FINAL GAP ===")
g_ranger = REST_U - C_A
g_odo_raw = G0 - REST_OD
brake_true = (REST_OD - TRIG_OD) / SKID
g_odo_skid = G0 - TRIG_OD - brake_true
g_model = TRIG_U - TRIG_V * T_EFF - C_A
print("  ranger A at rest ................ %5.1f mm   <-- REJECTED (frozen)" % g_ranger)
print("  odometry, uncorrected ........... %5.1f mm   (ignores the skid)" % g_odo_raw)
print("  odometry, C1 skid factor applied  %5.1f mm" % g_odo_skid)
print("  model back-out (C1 t_eff) ....... %5.1f mm" % g_model)
print("  -> the two channels that do NOT use the rest reading agree to %.1f mm"
      % abs(g_odo_skid - g_model))
print("     the ranger disagrees with them by %.0f mm." % (g_ranger - g_model))

centre = 0.5 * (g_odo_skid + g_model)
corner = centre - W_HALF * math.sin(math.radians(abs(REST_HD)))
print("\n=== COMMITTED ONBOARD ESTIMATE (before ground truth) ===")
print("  at the ranger centreline ........ %.1f mm" % centre)
print("  yaw correction at %.1f deg ....... -%.1f mm"
      % (abs(REST_HD), W_HALF*math.sin(math.radians(abs(REST_HD)))))
print("  AT THE FOREMOST POINT ........... %.1f mm" % corner)

print("\n=== FROZEN PREDICTION vs OUTCOME (VP v1.0) ===")
rows = [("final clearance (mm)", 37.0, "%.1f (est)" % corner, "within 3s, pending ground truth"),
        ("rest reading u_A (mm)", 47.0, "92.0", "FALSIFIED"),
        ("heading at rest (deg)", 4.91, "7.43", "FALSIFIED - SYS-5 exceeded"),
        ("valid onboard estimate", 1, "0", "FALSIFIED - SYS-6 not met")]
for n, p, a, v in rows:
    print("  %-24s predicted %-6s actual %-6s  %s" % (n, p, a, v))

print("\n=== PHYSICAL STORY LINKING THE TWO FAILURES ===")
print("  Braking yaw grew from +1.1 to -7.4 deg (one wheel locks first).")
print("  A forward ultrasonic ranger tilted 7.4 deg off the wall normal sends")
print("  its specular return away at ~14.9 deg.  At ~%.0f mm sensor-face range"
      % (centre + C_A))
print("  the returned energy collapses and the device stops updating.")
print("  SYS-5 (heading) and SYS-6 (valid estimate) are ONE root cause, not two.")
print("  In C1 the stops were at ~600 mm, where the same tilt still returns an")
print("  echo -- which is why C1 never exposed this. The failure is specific to")
print("  the OPERATING POINT, and only a run at the operating point could find it.")
