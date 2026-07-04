# Verification Plan v2 — Wall-Approach Rover (FROZEN PREDICTION, re-derived)

**Document type:** PLAN — re-derived predictive argument, frozen at the GATE-B re-derivation after V1 falsified v1. **Verification Plan v1 is retained unchanged** as the record. Predictions below are the output of the executable model at the new committed configuration (`calib_predict_v2.py` → `calib_predict_v2_output.txt`).

---

## 0. Why v1 was falsified (the V1 result)

V1 ran `prog_v3` at `R_TRIGGER = 121` (on sensor A). Frozen v1 prediction: 60 mm gap. **Actual (operator #2): 28 mm — no contact, but 32 mm closer than predicted.**

Root cause (diagnosed, not tweaked): the control loop **stalled** near the trigger — the ultrasonic read hit a no-echo timeout and BLE was slow (~240 ms/line), producing a ~471 ms loop iteration during which the rover travelled ~223 mm. The ultrasonic-based trigger therefore fired **late** (at A = 100 rather than 121), driving the rover 21 mm closer in reported terms and ~32 mm closer in true gap. **The structural model held** (overshoot from the *actual* trigger reading to rest was 65 mm at V1, consistent with C2/C3's 73/49), but the **threshold→actual-trigger overshoot is loop-timing-dependent and unbounded** when the ultrasonic can block the loop. No contact occurred, but it was luck: a slower loop could have contacted. That is not acceptable for five operation runs.

Also learned: sensor A **over-reads by ~14 mm at ~40 mm range** (read 42, true 28) — A is unreliable below ~45 mm, confirming the encoder/geometry (not A) must carry the near-range gap.

## 1. The fix and the new committed configuration

**Program `prog_v4.py`** — the fast-approach trigger is now on **encoder travel**, not the ultrasonic:

- The hot loop reads only `.angle()`/`.speed()` (fast, non-blocking) and **no ultrasonic and no telemetry** → the loop period is bounded (~5 ms) regardless of ultrasonic echo or BLE. The stall that caused V1 cannot recur.
- Sensor A is read **once** at the fast-approach start (reliable ~930 mm range) to fix `true_start = A_start − 7`; the crawl still confirms A faces the wall and provides a sanity-checked `k`.
- Trigger fires when wheel travel reaches `target_travel = true_start − TARGET_TRUE_TRIGGER` (computed per run, so it adapts to squaring), with `TARGET_TRUE_TRIGGER = TARGET_GAP + D_stop_eff = 55 + 58 = 113 mm`. `target_travel` is **clamped** (≤ 830 mm) to bound an A-start over-read, and aborts on out-of-range `A_start` or `k`.
- Travel uses a **fixed long-baseline `k = 27.5 mm/rad`** (from the ~800 mm rolling approach across C2/C3/V1, spread ±0.8%) — far more precise than the ~89 mm crawl estimate. The encoder tracks *rolling* travel to ±0.8%; slip is only in the post-trigger brake (captured in `D_stop_eff`).

Net effect: the trigger position is now precise (±~6 mm from `A_start` + `k`), so the final-gap spread is dominated by the **braking spread alone** (`σ_stop`), which is what the margin covers.

## 2. FROZEN PREDICTION v2 (model output at the committed config)

Calibrated inputs: `k=27.5`, `ω=18.19 rad/s`, `b=+7`, `D_stop_eff=58`, `σ_stop=15`, `σ_b=6`, `σ_pred=6`, `k_margin=3`, effective reported trigger `=120 mm` (= 113 true + b).

| Quantity | **Predicted** |
|---|---|
| `v_max` | 500 mm/s |
| `D_stop_eff` | 58 mm |
| `sigma_rss` | 17.2 mm |
| **`safety_margin` = 3·RSS** | **51.7 mm** |
| **`final_clearance` (predicted true gap)** | **55.0 mm** |
| onboard geometry gap estimate | `true_start − travel_rest` |

**Frozen roll-up:** SYS-1 PASS (55 > 0) · SYS-2 PASS · SYS-3b PASS (55 ≥ 51.7) · SYS-4 PASS · SYS-5 PASS · CMP-1..7 PASS · **ROLLUP PASS**.

**In words:** the rover is predicted to stop at a true gap of **55 mm**, no contact, full speed, straight — and now this is **robust to loop timing** (the failure mode from V1 is removed). 55 mm is the tightest that keeps clearance ≥ 3σ given the braking spread; getting tighter would require a more repeatable (gentler) brake plus re-characterization, which I judged not worth the extra runs.

## 3. V1′ verification procedure

1. Operator squares the rover (~1000 mm); go-ahead.
2. Flash `prog_v4.py`; run (timeout ~15 s — telemetry is minimized so it completes even under slow BLE).
3. Confirm `triggered=1`, `emerg=0`; read the onboard geometry estimate `gap_est_geom = true_start − travel_rest` (stated **before** the measurement).
4. **Operator measurement #3:** true closest gap (mm) at the V1′ rest — objective validation at the operating point.

## 4. Pass criteria

- **No contact** (hard): measured gap > 0, `emerg=0`, fully stopped.
- **Prediction validated:** measured gap consistent with 55 mm within the frozen band (≈ 55 ± 3σ). A gap far below prediction, or contact, falsifies (→ §5).
- The onboard geometry estimate vs truth quantifies residual `D_stop`/`k` error (informs the operation close-out; does not gate no-contact).

If V1′ passes, GATE C closes the objective on this ground truth, `prog_v4` locks, and the 5 operation runs proceed.

## 5. Falsification / re-derivation path

If V1′ contacts or the gap is materially below the predicted band (e.g. `σ_stop` still under-estimated, or `D_stop_eff` off): **diagnose, do not tweak.** Re-derive `TARGET_GAP`/`D_stop_eff` from the updated data, issue **Verification Plan v3** (v1, v2 retained), and re-run. If V1′ is much **farther** than 55 mm (safe but loose), optionally tighten `TARGET_GAP` and re-verify, budget permitting.

**Budget note:** program runs after V1′ = 6 (C1-fail, C1-v2, C2, C3, V1, V1′); operator measurements = 3 (#1 196, #2 28, #3 pending). The extra V1′ + measurement are the cost of V1's falsification — unavoidable given the loop-timing safety risk it exposed.
