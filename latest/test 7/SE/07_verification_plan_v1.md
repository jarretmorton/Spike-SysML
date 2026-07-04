# Verification Plan v1 — Wall-Approach Rover (FROZEN PREDICTION)

**Document type:** PLAN — the predictive argument, **frozen** at GATE B before the V1 verification run. The predictions below are the **output of the executable model at the committed configuration** (`calib_predict.py` → `calib_predict_output.txt`), nothing more. If V1 falsifies them, this version is retained unchanged and a **new** version is derived (§5).

**Committed on:** the Calibration Report (all TBDs closed, all CMPs unit-verified PASS).

---

## 1. Committed configuration (the locked operation program)

The verified/operation program is **`prog_v3.py`** (trigger on sensor A only; faulty B excluded; independent encoder crash backstop + A emergency floor; `hold()` stop) with the single calibrated change:

```
R_TRIGGER = 121.0    # reported mm on sensor A   (C2/C3 used 200; this is the only change)
```

All else identical to C2/C3 (test-like-you-fly): same crawl, same accelerate-to-max, same paced loop, same `hold()`, same `try/finally` + sentinel, same `KSPEED`, `SAFE_FLOOR_A=80`, `TRAVEL_CAP_MM=850`, `MAX_RUN_MS=2500`. Because C2/C3 confirmed full cruise is reached long before the trigger, the stopping behaviour characterized there transfers to this trigger (transfer-validity holds).

## 2. FROZEN PREDICTION (model output at the committed config)

Calibrated inputs: `k=28.2 mm/rad`, `ω=18.19 rad/s`, `b=+7 mm`, `D_stop_eff=54 mm`, `σ_stop=18`, `σ_b=6`, `σ_pred=6`, `k_margin=3`, `R_trigger=121 mm`. Predicted outputs:

| Quantity | **Predicted** |
|---|---|
| `v_max` | **513 mm/s** |
| `D_stop_eff` (used) | **54 mm** |
| `sigma_rss` | **19.9 mm** |
| **`safety_margin` = 3·RSS** | **59.7 mm** |
| `R_trigger` (committed) | **121 mm reported (A)** |
| **`final_clearance` (predicted true gap)** | **60.0 mm** |
| predicted A reading at rest | 67 mm (valid, ≥ r_min) |
| trigger reading ≥ r_min | true |

**Frozen roll-up (satisfy/require, `WallRunNeed`):**

| Req | Verdict | measured vs target |
|---|:--:|---|
| SYS-1 NoContact | **PASS** | clearance 60 > 0 |
| SYS-2 MaxSpeed | **PASS** | cruise 513 ≥ 0.98·513 |
| SYS-3 MinGap (objective) | N/A (graded) | clearance 60 (to be validated at operating point) |
| SYS-3b MinGapMargin | **PASS** | 60 ≥ 59.7 |
| SYS-4 FullStop | **PASS** | rest 7 ≤ 10 mm/s |
| SYS-5 StraightTravel | **PASS** | drift 5.5 ≤ 10 deg |
| CMP-1..7 | **PASS** | (Calibration Report §4) |
| **ROLLUP** | **PASS** | all hard PASS |

**In words:** at a 121 mm reported trigger on sensor A, the rover is predicted to stop at a true gap of **60 mm**, with no contact, at full speed, essentially straight — and the no-contact margin (3σ = 59.7 mm) is satisfied. This 60 mm is the tightest gap that keeps `final_clearance ≥ 3σ` given the measured stopping spread; the spread (from 2 samples) is the reason it is not tighter.

## 3. V1 verification procedure

1. Operator squares the rover at the start line (~1000 mm); confirms go-ahead.
2. Flash `prog_v3.py` with `R_TRIGGER = 121`; run (timeout ~12 s).
3. Read telemetry: confirm `triggered=1`, `emerg_*=0`, and the onboard rest estimate `gap_est = a_rest − 7`.
4. **Operator measurement #2:** with the rover at its V1 rest, measure the true closest gap (mm) — this is the **objective validation at the operating point**, distinct from the operation close-out. (I will state the onboard `gap_est` **before** requesting it.)

## 4. V1 pass criteria (what validates the frozen prediction)

- **No contact** (hard): operator-measured gap > 0, `emerg_*` did not fire on contact, rover fully stopped.
- **Prediction validated:** operator-measured true gap is consistent with the predicted 60 mm within the frozen uncertainty band (60 ± 3σ ≈ 60 ± 60, i.e. any positive gap that is also within a sensible ±~25 mm of 60 confirms `D_stop_eff`/`σ_stop`; a gap far below prediction, or contact, falsifies).
- **Onboard estimate check:** `gap_est` vs operator truth quantifies sensor-A near-range accuracy at the operating point (informs the operation close-out; does not gate no-contact).

If V1 passes, GATE C closes the objective (SYS-3) on this operating-point ground truth, the program locks, and the 5 operation runs proceed.

## 5. Falsification / re-derivation path (frozen-prediction discipline)

If V1 falsifies the prediction — **contact**, or true gap materially below the predicted band (indicating `σ_stop` under-estimated or `D_stop_eff` off, e.g. the real spread exceeds the 2-sample estimate):

1. **Do not tweak the program empirically.** Diagnose the responsible parameter (most likely `σ_stop` from the thin 2-sample estimate, or the `D_stop_eff` overshoot).
2. Re-derive a **new** `R_trigger` from the updated calibration (larger margin), issue **Verification Plan v2** (this v1 retained unchanged as the record), and **re-run V1**. Each verification run counts toward the program-run score.
3. Only a prediction that survives V1 at the operating point may lock for operation.

Conversely, if V1 stops much **farther** than predicted (overly conservative), that is a safe pass; I may (optionally, budget permitting) tighten `R_trigger` and re-verify to improve closeness, or accept the safe gap.
