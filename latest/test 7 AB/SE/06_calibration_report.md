# Calibration Report — Wall-Approach Rover

**Document type:** REPORT (backward-looking, static; not edited after issue).
**Basis:** runs C1 (failed), C1-v2, C2, C3 + operator measurement #1 (196 mm). Programs `c1_program.py` (v1, failed), `c1_program_v2.py`, `prog_v3.py`.
**Purpose:** close the TBD register with evidence, unit-verify the CMP requirements, and record the dispositions that the frozen Verification Plan rests on.

---

## 1. Calibration runs (what produced the data)

| Run | Program | Result | Produced |
|---|---|---|---|
| C1 | v1 | **FAILED — wall contact** (Anomaly Report); counts as a program run | port map, motor signs, first ω/k; exposed detection + backstop defects |
| C1-v2 | v2 | clean, no contact, stopped 196 mm (operator) | crawl confirms A/B forward, E rear; k; ω; **exposed sensor-B fault** |
| C2 | v3 | clean, no contact, A-rest 132 (true ~125) | A-only trigger safe; **exposed encoder brake-slip**; stop sample #1 |
| C3 | v3 | clean, no contact, A-rest 157 (true ~150) | stop sample #2 → **run-to-run spread** |
| meas #1 | — | operator: true closest gap = **196 mm** | anchored A offset; confirmed front flush (B is faulty) |

Program-run cost so far: **4**. Operator measurements so far: **1** (of the planned 2).

## 2. TBD register — closed

Evidence tier: 1 well-known · 2 anchored/multi-point onboard · 3 unknown-onboard/thin-sample · 4 external ground truth.

| TBD | Quantity | **Value** | Producing test | Tier |
|---|---|---|---|:--:|
| TBD-1 | `omega_max` | **1042 deg/s (18.19 rad/s)** | steady cruise, 3 runs (1044/1044/1041) | 2 |
| TBD-5 | `k_speed` | **28.2 mm/rad** | crawl Δreport/Δθ, 3 runs (27.79/29.04/27.87); cross-checked by C1-v2 stop segment | 2 |
| — | `v_max` | **513 mm/s** | `omega_max × k_speed` | 2 |
| TBD-2 | `b` (sensor **A** offset) | **+7 mm** (reports true + 7) | operator #1 (196) vs A rest (203) | **4** |
| TBD-2b | `alpha` (A scale) | **≈ 1.0** | A tracks linearly over 200–1000 mm | 2 |
| TBD-6 | `D_stop_eff` | **54 mm** | reported-trigger→true-rest overshoot (C2 73, C3 49; mean 61) − `b` 7. **Sensor-based (A).** Encoder gives 6–30 mm and is NOT used (§3b). | 3 |
| TBD-7 | `sigma_stop` | **18 mm** | run-to-run spread of true rest: C2 125, C3 150 (SD ≈ 17, hedged). **Thin (2 samples) — dominant margin term.** | 3 |
| TBD-3 | `r_min` (A) | **≈ 40 mm** floor; no-echo = 2000; A reliable ≥ ~100 mm | near-range readings across runs | 2 |
| TBD-4 | `t_response` | **≈ 0.05 s** (loop ~28 ms + refresh) | loop period; **folded into measured `D_stop`** (informational) | 2 |
| TBD-8 | `heading_drift` | **≈ 5.5 deg** (repeatable) | IMU, 2 runs (5.67/5.33) | 2 |
| TBD-11 | `rest_speed`; `contact_floor` | **≈ 7 mm/s** held; 0 mm | post-`hold()` speed (< 20 deg/s settle); fixed | 1 |
| TBD-9 | `safetyMargin` | **59.7 mm** = `3 · RSS(18,6,6)` | computed (below) | derived |
| TBD-10 | `R_trigger`, `g_target` | **121 mm reported / 60 mm** | set in Verification Plan | design |

`sigma_b` = 6 mm (A-anchor read resolution + near-range drift allowance), `sigma_pred` = 6 mm (unmodeled, incl. the ~5–9 mm yaw corner effect). Both tier 3.

## 3. Dispositions (load-bearing)

**3a. Sensor B is faulty — excluded.** B read ~130 mm low throughout (C1-v2: 888 vs A 1025; 80 vs A 203); the operator confirmed the front is flush with nothing protruding, so B is not seeing a real surface. **B is excluded from triggering and gap estimation, logged only for monitoring** (a change in its bias would escalate). Sensor **A is the trusted forward channel**.

**3b. The encoder under-counts the stopping distance (brake slip) — sensor used instead.** With A trusted, C2/C3 show the encoder logs 6–30 mm of trigger→rest travel while sensor A shows 42–66 mm (whole-approach cross-check: encoder ~40 mm short of A-travel, concentrated in the brake). The aggressive `hold()` brake slips/locks the wheels, so **the encoder is not a valid `D_stop` channel** and is not used for the stop/gap. It remains valid for the **rolling** travel used by the crash backstop (the cap is checked during cruise, where slip is negligible). My prior "sharp 6 mm stop" reading (C1-v2) was an encoder artifact and is withdrawn; true `D_stop` is ~55–66 mm.

**3c. Stopping variability sizes the margin.** For an identical trigger (~199 reported), the rover stopped 25 mm apart (true 125 vs 150 mm). This run-to-run spread (`sigma_stop` ≈ 18 mm) is the dominant no-contact-margin term. It is estimated from only **two** samples, so it is the **key residual uncertainty** the verification run must probe; the frozen prediction is sized conservatively because of it.

## 4. CMP unit-verification (gates the integrated V1 test)

Computed by `wallrun_model.evaluate()` at the calibrated config (`calib_predict_output.txt`).

| CMP | Claim | Value vs bound | Verdict | Evidence |
|---|---|---|:--:|---|
| CMP-1 MotorAtMax | ω_achieved ≥ rated | 18.19 ≥ 18.19 | **PASS** | cruise, 3 runs |
| CMP-2 MotorToRest | rest speed ≤ tol | 7 ≤ 10 mm/s | **PASS** | post-`hold()`, 3 runs |
| CMP-3 SensorResidual (A) | |resid| ≤ tol | 2 ≤ 8 mm | **PASS** | A 203 vs true 196; linear track |
| CMP-4 SensorMinRange | trigger reading ≥ r_min | 121 ≥ 40 mm | **PASS** | operating trigger well above floor |
| CMP-5 LatencyChain | t_response ≤ bound | 0.05 ≤ 0.10 s | **PASS** | deterministic loop; folded into `D_stop` |
| CMP-6 HeadingBounded | drift ≤ tol | 5.5 ≤ 10 deg | **PASS** | IMU, 2 runs |
| CMP-7 GroundConstant | |k resid| ≤ tol | 0.03 ≤ 0.05 | **PASS** | crawl k spread across runs |

All component-level requirements are unit-verified → the integrated verification (V1) is cleared to run (tenet C1).

## 5. Residual uncertainties → what V1 must validate

1. **`sigma_stop` (18 mm) rests on 2 samples.** V1 is an independent third sample at the operating trigger; a large departure from the predicted 60 mm gap means `sigma_stop`/`D_stop_eff` are off → re-derive.
2. **Sensor A near-range reliability at the operating rest (~60 mm true).** Below ~100 mm the ultrasonic can be jumpy; operator measurement #2 validates the true gap against A's reading at the operating point. (This does not affect no-contact — the trigger stops the rover regardless — only the accuracy of the onboard gap estimate.)
3. **The lumped `(b + latency + D_stop)` = 61 mm overshoot** is validated as a whole at the operating point by V1 + operator #2.

These are exactly what the frozen Verification Plan predicts and V1 tests.
