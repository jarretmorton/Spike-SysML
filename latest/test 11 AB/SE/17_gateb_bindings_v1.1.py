#!/usr/bin/env python3
# ============================================================================
# 17_gateb_bindings_v1.1.py - Gate B binding driver, v1.1 (AR-003 rebind).
# Loads 03_wall_rover_eam_v1.0.py UNCHANGED, binds parameters from R-CAL
# run-20260712-233644 + M1 (218 mm), sets Gate-B requirement bounds, computes
# sigma_stop (RSS, Tenet A6) and G_target, and prints:
#   [1] binding table (value | tier | evidence)
#   [2] margin computation
#   [3] EVALUATE view A - closed by calibration now (run rows OPEN)
#   [4] EVALUATE view B - FROZEN PREDICTION at R-VER (all rows)
#   [5] PREDICT stop numbers + operation-program constants
# ============================================================================
import math

eam = {}
exec(open('/home/claude/eam.py').read(), eam)
PARAMS = eam['PARAMS']
GATE_B_BOUNDS = eam['GATE_B_BOUNDS']
evaluate = eam['evaluate']
print_evaluate = eam['print_evaluate']
predict = eam['predict']

MM = 1e-3

# ---- [1] parameter bindings (SI) -------------------------------------------
B = [
    ("o_us",     -46*MM, "T3", "M1 218 mm vs 38-sample rest median B=172 (primary channel B; A=+68 documented separately)"),
    ("tau_us",    10*MM, "T2", "advance decomposition seg2/seg3 (fresh-trigger vs rest) bounds data age 2-18 ms; carry 10 +/- 8"),
    ("t_chain",   71*MM, "T2", "onset 41 ms measured x3 (identical) + 20 ms median-of-3 lag + 10 ms confirm tick (designed)"),
    ("a_brake",   9.0,   "T2", "post-onset brake distance ~19 mm from 610 mm/s (seg2/seg3 series); amax 0.9-1.16 g corroborates"),
    ("v_max",     0.604, "T2", "trimmed plateau ~= slower ceiling ~944 dps x k_hat (v1.1: outer full duty, inner matched)"),
    ("k_odo",     0.03667, "T2", "cruise fits: B-slope/encoder seg2 0.656 mm/deg, B fresh-interval seg3 ~0.66-0.69, A 0.47 (A anomalous, demoted); carry 0.64 mm/deg +/- 0.04"),
    ("T_loop",    0.010, "T2", "tick log: jit_max 0 all segments"),
    ("U_refresh", 0.020, "T2", "S0 change-interval stats: B 20 ms (A 32 ms)"),
    ("sigma_us",  0.0015,"T2", "static MAD 0-1 mm both sensors; rest windows consistent"),
    ("sigma_b",   0.007, "T2", "2 clean advance samples (~46, ~41 mm), small-sample inflated"),
    ("psi_run",   0.087, "T2", "AR-003 corrected decode: un-trimmed arc ~-11 deg/seg, R-VER -39 deg; v1.1 trim holds cruise <=~1.5 deg, brake-skid swing adds <=8: at-wall mean ~5 deg"),
    ("half_width",0.100, "T0-prior-ceiling", "geometry unmeasured by design (absence by sensitivity); ceiling used - conservative"),
    ("r_min",     0.040, "T1", "hardware floor; readings validated clean down to 172 mm; below untested - op uses plausibility gate + DR fallback"),
]
print("=== [1] GATE B PARAMETER BINDINGS ===")
for k, v, tier, ev in B:
    PARAMS[k].bind(v, tier, ev)
    print("  %-10s = %-9.4g %-5s %-18s %s" % (k, v, PARAMS[k].unit, tier, ev[:96]))
print("  %-10s   %-9s %-5s %-18s %s" % ("G0_start", "unbound", "m", "T0", "context row - zero leverage, deliberately unmeasured"))

# ---- [2] margin: sigma_stop RSS -> G_target --------------------------------
sig = {
    "offset anchor residual (o_B, M1 + yaw de-confound)": 6.0,
    "braking/advance run-to-run (2 samples, infl)": 7.0,
    "data-age residual v*d(tau) (+/-8 ms)":        4.9,
    "k residual -> advance belief + DR-fallback span": 5.5,
    "trigger crossing quantization v*U/sqrt(12)":  3.5,
    "US noise at trigger (2-sample confirm)":      2.0,
    "corner-erosion variability (at-wall yaw +/-4 deg)": 4.0,
    "unmodeled floor/battery":                     3.0,
}
rss = math.sqrt(sum(v*v for v in sig.values()))
G_target = 0.041           # 3*sigma rounded (40.3 -> 41 mm), corner-referenced
corner_mean = 0.100*0.087  # half_width * sin(at-wall mean ~5 deg) = 8.7 mm
G_aim = 0.050              # sensor-line aim = G_target + corner_mean (rounded)
print("\n=== [2] MARGIN (RSS, Tenet A6) ===")
for k, v in sig.items():
    print("  %-46s %4.1f mm" % (k, v))
print("  RSS sigma_stop = %.2f mm -> 3*sigma = %.1f mm" % (rss, 3*rss))
print("  G_target (corner-referenced, SYS-5) = %.0f mm  >=  3*sigma %.1f mm" % (G_target/MM, 3*rss))
print("  corner mean erosion %.1f mm folded into sensor-line aim G_aim = %.0f mm" % (corner_mean/MM, G_aim/MM))

GATE_B_BOUNDS.update({
    "stop_target": G_target, "sigma_stop": rss*MM,
    "post_stop_bound": 0.004, "heading_bound": 0.175,
    "noise_bound": 0.004, "refresh_bound": 0.040,
    "imu_drift_bound": 0.0175, "jitter_bound": 0.005,
    # rear_track_bound left None: CMP-R1 dispositioned DROPPED-BY-TRACEABILITY
})

# ---- [3] view A: closed by calibration today --------------------------------
OBS_UNIT = {
    "plateau_dev_L": 0.015, "plateau_dev_R": 0.015,
    "sign_valid_L": 1.0, "sign_valid_R": 1.0,
    "brake_dist_L": 0.019, "brake_dist_R": 0.019,
    "post_stop_travel_L": 0.0026, "post_stop_travel_R": 0.0026,
    "encoder_dropouts_L": 0.0, "encoder_dropouts_R": 0.0,
    "noise_sigma_A": 0.0015, "noise_sigma_B": 0.0015,
    "offset_residual_A": 0.003, "offset_residual_B": 0.002,
    "data_age_err_B": 0.008,
    # data_age_err_A intentionally ABSENT: A demoted to validity-only;
    # CMP-U3-A dispositioned by channel decision (Calibration Report sec 3)
    "subfloor_leakage_A": 0.0, "subfloor_leakage_B": 0.0,
    "refresh_A": 0.032, "refresh_B": 0.020,
    "imu_drift_10s": 0.0005, "contact_witness_armed": 1.0,
    "loop_jitter_p95": 0.000,
    "heading_dev_max": 0.020,   # v1.1 trim-held cruise (sim); skid adds at brake
    "hot_path_writes": 0.0, "invalid_sample_leakage": 0.0,
    "census_validated": 1.0,
    "failsafe_coverage": 1.0,   # mock fault-injection suite (169+400 clean)
}
print("\n=== [3] EVALUATE view A - closed by calibration (run-level rows OPEN until R-VER) ===")
print_evaluate(evaluate(observations=OBS_UNIT), "")

# ---- [4] view B: FROZEN PREDICTION at R-VER ---------------------------------
vals = eam['base_vals']()
stop_budget = vals["stop_budget"]
OBS_PRED = dict(OBS_UNIT)
OBS_PRED.update({
    "final_clearance": G_target,            # corner-referenced center
    "min_run_clearance": G_target,
    "speed_plateau_ratio": 1.00,
    "rest_achieved": 1.0, "estimates_committed": 1.0,
    "operator_inputs_during_run": 0.0, "telemetry_complete": 1.0,
    "outer_duty_min": 100.0,                # cmd 2000 dps >> ceiling: saturated
    "brake_cmd_delay": 0.010,
    "post_stop_travel_max": 0.0026,
    "estimate_channels": 3.0,               # B, DR, A-rest
    "heading_dev_max": 0.140,               # predicted whole-run max incl. skid swing
    "sentinel_emitted": 1.0,
    "failsafe_latency": 0.020,
    "gap_coverage": 0.995, "odo_coverage": 1.0,
    "fused_gap_at_trigger": stop_budget - 0.0001,
    "trim_max": 0.0, "hold_duration": 4.0, "rest_sample_count": 24.0,
    "emission_duration": 15.0,              # op dump ~5 kB at >=0.35 kB/s
})
print("=== [4] EVALUATE view B - FROZEN PREDICTION at R-VER (per-run prediction center) ===")
print_evaluate(evaluate(observations=OBS_PRED), "")

# ---- [5] PREDICT + operation constants --------------------------------------
p = predict(G_aim)  # aim at sensor line; corner lands at G_target
print("=== [5] STOP PREDICTION (center values; dispersion sigma_stop=%.1f mm) ===" % rss)
print("  trigger reading threshold (B, corrected frame): %.1f mm" % ((G_aim + PARAMS['o_us'].value + 0.604*(0.010+0.071) + 0.604**2/18.0)/MM))
for k in ("reading_trigger", "gap_at_trigger", "stop_advance_real", "final_gap", "final_clearance"):
    print("  %-20s %7.1f mm" % (k, p[k]/MM))
print("  predicted C_final (corner) ~ %.0f +/- %.1f mm; 3-sigma window [%.0f, %.0f]"
      % (G_target/MM, rss, G_target/MM-3*rss, G_target/MM+3*rss))
print("  P(contact per run) ~ %.2f %% | P(any contact in 5) ~ %.2f %%"
      % (100*0.5*math.erfc((G_target/MM)/(rss*math.sqrt(2))),
         100*(1-(1-0.5*math.erfc((G_target/MM)/(rss*math.sqrt(2))))**5)))
print("\n=== OPERATION PROGRAM CONSTANTS (mm / ms integer domain) ===")
print("  K_CAL=0.64 mm/deg | O_B=-46 | O_A=+68 | TAU=10 ms | TCH_EFF=71 ms")
print("  A_BR=9000 mm/s^2 | G_AIM=50 mm | trigger: Ghat<=G_AIM+v*71/1000+v*v/18000")
print("  median-of-3-fresh + 2-tick confirm (TCH_EFF = 41 chain + 20 median + 10 confirm)")
print("  DR with K_CAL between fixes | staleness 120 ms | valid [25,1600]")
