# 11 — VERIFICATION PLAN, Wall-Approach Rover — v1.0 (Gate B) — **FROZEN**

This document's predictions are frozen at issue. If R-VER falsifies any of
them, this plan is not edited: a new version is issued with the analysis of
the discrepancy, per the gated process.

## 0. Configuration under verification

| Item | Fingerprint |
|---|---|
| OP-WAR v1.0 (13_op_program_v1.0.py, 433 lines) | md5 `eba2d509e2d6d3800347e0a3c3be805c` |
| Gate B bindings driver (09) | md5 `2dc1be884b122f6f06f42f6b98a6d1a9` |
| Qualification (14) | 210/210 scenarios PASS; 400-seed soak: 0 contacts, 0 sentinel misses, 0 hot-path writes, worst min-gap 6.5 mm |
| Calibration basis | run-20260712-233644 + M1 = 218 mm |

R-VER = one run of the **byte-identical** OP-WAR v1.0 from the start line
(operator re-squares the rover; hub-ready confirmed before flash). Host run
timeout **45 s** (AR-002). This is characterization run 3 of the campaign.

## 1. Frozen predictions

| Quantity | Prediction |
|---|---|
| Corner-referenced final clearance C_final | **36 ± 12 mm**, 3σ window **[0, 72] mm** |
| Sensor-line rest gap (B line) | ≈ 42 ± 12 mm |
| Trigger: corrected gsig at confirm | ≈ 106 mm (thr formula at v̂ ≈ 610) |
| Trigger: raw B reading at trigger tick | ≈ 66 mm |
| Trigger speed w | 905–1010 dps (v̂ 580–650 mm/s) |
| Onset (cmd → decel) | 41 ± 10 ms |
| Heading deviation over approach | ≤ 4° (predicted ≈ −3.2°) |
| Onboard committed estimate est.c_final (= c_pred) | within ±25 mm of the true rest (nominal 1σ ≈ 10; tails to ±45 at 2σ parameter corners) |
| P(contact) per run | 0.13 % (P over 5 op runs ≈ 0.67 %) |
| Emission | ≤ 20 s (dump ~5–6 kB; ≥ 0.3 kB/s BLE), sentinel present |
| Independent sim cross-check (as-built Monte Carlo, doc 14) | median gap 44, p5–p95 [19, 67] — sits ~+8 right of the analytic center from safe-side allowance stacking; both inside the same 3σ window; the frozen prediction is the analytic one above |

## 2. R-VER pass criteria (all falsifiable; any failure ⇒ new plan version)

1. **No contact** — corner clearance > 0; witnesses: amax pattern normal
   (no wall-strike signature), min corrected gap in telemetry > 0.
2. **Clean run** — census_ok = 1, no abort/exc, run.ok = 1.
3. **Stop quality** — full rest achieved; hold_s ≥ 2.0; post-stop creep
   ≤ 4 mm equivalent (creep_deg·k̂).
4. **Prediction window** — est.c_final ∈ [0, 72]; |est.c_final − 36| ≤ 36.
5. **Trigger integrity** — trigger from a proper crossing: gsig ≤ thr with
   thr per formula; glitch_rej reported; est.disagree reported (0 expected;
   1 is a flag for analysis, not an automatic fail).
6. **Speed** — plateau w ≥ 0.95 × (v̂/k̂) equivalent (STK-2/SYS-1: full-speed,
   no slowdown before trigger).
7. **Telemetry contract** — sentinel present; emission ≤ 20 s (closes
   CMP-H2); buffer no overflow; no hot-path writes.
8. **Heading** — |dh| ≤ 4°.

## 3. Frozen mechanical roll-up (view B — prediction at R-VER)

50 PASS / 0 FAIL / 2 OPEN-by-disposition of 52. The two OPEN rows are
CMP-U3-A (dispositioned by A-demotion) and CMP-R1 (dispositioned
dropped-by-traceability); they are carried OPEN in the mechanics rather than
faked numerically, and close textually at Gate C.

```
STK-1  PASS  min_run_clearance >= contact_floor    (0.036 >= 0.001)
STK-2  PASS  speed_plateau_ratio >= 0.95           (1 >= 0.95)
STK-3  PASS  stop_target <= objective_ceiling      (0.036 <= 0.06)   [OBJ]
STK-4  PASS  rest_achieved                          (1 >= 1)
STK-5  PASS  estimates_committed                    (1 >= 1)
STK-6  PASS  operator_inputs_during_run <= 0        (0 <= 0)
STK-7  PASS  telemetry_complete                     (1 >= 1)
SYS-1  PASS  outer_duty_min >= 100                  (100 >= 100)
SYS-2  PASS  brake_cmd_delay <= T_loop              (0.01 <= 0.01)
SYS-3  PASS  final_clearance >= contact_floor       (0.036 >= 0.001)
SYS-4  PASS  final_clearance <= closeness_ceiling   (0.036 <= 0.07197) [OBJ]
SYS-5  PASS  stop_target >= margin_floor            (0.036 >= 0.03597)
SYS-6  PASS  post_stop_travel_max <= bound          (0.0026 <= 0.004)
SYS-7  PASS  estimate_channels >= 2                 (3 >= 2)
SYS-8  PASS  heading_dev_max <= bound               (0.056 <= 0.07)
SYS-9  PASS  hot_path_writes <= 0                   (0 <= 0)
SYS-10 PASS  sentinel_emitted                       (1 >= 1)
SYS-11 PASS  failsafe_latency <= 2*T_loop           (0.02 <= 0.02)
SYS-12 PASS  invalid_sample_leakage <= 0            (0 <= 0)
SYS-13 PASS  census_validated                       (1 >= 1)
FUN-1  PASS  gap_coverage >= 0.99                   (0.995 >= 0.99)
FUN-2  PASS  odo_coverage >= 0.99                   (1 >= 0.99)
FUN-3  PASS  fused_gap_at_trigger <= stop_budget    (0.09988 <= 0.09998)
FUN-4  PASS  trim_max <= 15                         (0 <= 15)
FUN-5  PASS  hold_duration >= 2                     (4 >= 2)
FUN-6  PASS  rest_sample_count >= 8                 (24 >= 8)
FUN-7  PASS  failsafe_coverage                      (1 >= 1)
CMP-M1-L/R PASS  plateau_dev <= 0.05                (0.023 / 0.022)
CMP-M2-L/R PASS  brake_dist <= ceiling              (0.019 <= 0.04167)
CMP-M3-L/R PASS  sign_valid                         (1 >= 1)
CMP-M4-L/R PASS  post_stop_travel <= 0.004          (0.0026)
CMP-M5-L/R PASS  encoder_dropouts <= 0              (0)
CMP-U1-A/B PASS  noise_sigma <= 0.004               (0.0015)
CMP-U2-A/B PASS  offset_residual <= 0.003           (0.003 / 0.002)
CMP-U3-A  OPEN   (dispositioned: A demoted)
CMP-U3-B  PASS   data_age_err <= 0.01               (0.008)
CMP-U4-A/B PASS  subfloor_leakage <= 0              (0)
CMP-U5-A/B PASS  refresh <= 0.04                    (0.032 / 0.02)
CMP-I1  PASS  imu_drift <= bound                    (0.0005 <= 0.0175)
CMP-I2  PASS  contact_witness_armed                 (1 >= 1)
CMP-H1  PASS  loop_jitter_p95 <= 0.005              (0)
CMP-H2  PASS  emission_duration <= 20               (15 predicted)
CMP-R1  OPEN   (dispositioned: dropped by traceability)
roll-up: 50 PASS / 0 FAIL / 2 OPEN of 52
```

## 4. After R-VER

Free analysis of telemetry vs §1–§2 → Verification Report (Gate C) closing
all 52 requirements with method + evidence + verdict, the objective closed on
the M1-validated chain, CMP-H2 closed on the measured emission →
**operator review** → program lock (byte-identical) → 5 operation runs →
close-out in the strict order (freeze onboard estimates in chat → request 5
measured gaps → final report with reconciliation).
