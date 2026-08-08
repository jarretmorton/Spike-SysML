# VERIFICATION PLAN v1.0 — WallStop

**Document** VP-WALLSTOP · **Version 1.0** · **Type: PLAN** · **Gate: B** · **PREDICTIONS ONLY**

> **THIS PREDICTION IS FROZEN.** It is the output of `wallstop_model_revB.py` evaluated at the committed configuration and the Calibration Report's bound values. No result from the C2 verification run may edit this version. If C2 falsifies it, I will diagnose the responsible parameter, re-derive, and issue **v1.1** — this version stays on the record as what was predicted.

---

## 1. Configuration under test

The **locked candidate operation program** (`operation_program.py`), unchanged. C2 runs the exact artifact that operation will run five times.

| Parameter | Value | Source |
|---|---|---|
| `c_A` ranger A offset | 10.0 mm | TBD-01, T3 |
| `G` target gap | 37.0 mm | TBD-12, set by SYS-6 |
| `t_eff` lumped response | 0.09661 s | TBD-06, T3 |
| `k_travel` | 0.482 mm/deg | TBD-03, T3 |
| `a_brake` | **UNBOUND** | not identifiable (AR-001 A-3) |
| Trigger channel | ranger A only | CMP-2 rev B |
| Validity gate | `42 < u < 1900` | CMP-4 |
| Commanded speed | 1000 deg/s (rated ceiling) | SYS-4 |

**Trigger law:** `U_thr(v) = c_A + G + v·t_eff`, recomputed every 10 ms from the live measured speed.

---

## 2. THE FROZEN PREDICTION

| Quantity | Predicted |
|---|---|
| Steady approach speed | **480.9 mm/s** |
| Stopping lump `v·t_eff` | **46.5 mm** |
| Trigger threshold `U_thr` | **93.5 mm** (ranger A reported) |
| **Final clearance** | **37.0 mm** |
| **Ranger A reading at rest** | **47.0 mm** |
| σ_gap (1σ) | **6.98 mm** |
| Contact margin (3σ) | **20.9 mm** |
| SYS-1 margin | **+16.0 mm** |
| SYS-6 headroom above the clamp | **+3.0 mm** |
| P(contact) this run | **5.9 × 10⁻⁸** |

**Predicted 1σ interval for the operator-measured gap: 30.0 – 44.0 mm. 3σ: 16.1 – 57.9 mm.**

### Falsification criteria — stated before the run

| Outcome | Reading |
|---|---|
| measured gap ∈ 30–44 mm | prediction **held** |
| measured gap ∈ 16–58 mm but outside 1σ | held at 3σ; note the residual, no re-derivation |
| measured gap **outside 16–58 mm** | **FALSIFIED** → diagnose, re-derive, issue VP v1.1, re-run |
| any contact | **FALSIFIED**, unconditionally |
| `rest_u_A` returns exactly 40.0 | clamp reached → SYS-6 not met → re-derive `G` |

### Expected direction of any error
`c_A` is biased **low** by the contact-detection lag (the stall detector fires only after the rover presses the wall), by an estimated 0–5 mm. A low `c_A` produces a gap **smaller** than predicted. I therefore expect the measured gap to fall in the **lower half** of the 1σ band if it deviates. This is stated now so that a low reading is a *confirmed prediction*, not a post-hoc rationalisation.

---

## 3. Predictive argument: requirement → model → parameters → performance

| Req | Bound quantity | Predicted | Target | Verdict |
|---|---|---|---|---|
| SYS-1 | final clearance vs contact margin | 37.0 mm | ≥ 20.9 mm | **PASS** (+16.0) |
| SYS-3 | rest ground speed | ~0 mm/s | ≤ 5 mm/s | **PASS** |
| SYS-4 | commanded / rated max | 1.0 | ≥ 1.0 | **PASS** |
| SYS-5 | heading deviation | 4.91° | ≤ 5.0° | **PASS** (marginal, +0.09°) |
| SYS-6 | rest reading vs clamp | 47.0 mm | ≥ 44.0 mm | **PASS** (+3.0) |
| SYS-2, 7, 8 | decomposition / flags | — | — | **PASS** |
| CMP-1…14 | see Calibration Report §3 | — | — | **PASS** (CMP-13 N/A) |
| **STK-1 roll-up** | | | | **PASS** |

Full roll-up reproduced by `evaluate()` — all 37 live requirements PASS, computed from the bound values, not asserted.

**Model ↔ model agreement.** The SysML satisfy/require roll-up and the Python `evaluate()` roll-up return the same verdict for every requirement; the structural checker confirms the edge sets are identical. No defect outstanding at the gate.

---

## 4. Honest weaknesses in this prediction

Stated plainly, because a frozen prediction that hides its own soft spots is worthless:

1. **`t_eff` rests on 2 samples with 1 degree of freedom.** Its σ is an estimate from a two-point spread. It is the second-largest budget term and could be materially larger.
2. **`c_A` has a known-sign, unknown-magnitude bias** (§2). It is the largest term and is the specific thing the C2 measurement exists to anchor.
3. **The back-prediction of the two C1 stops (+2.9 / −2.8 mm) is in-sample.** One parameter fitted to two points reproduces those two points by construction. It is *not* independent evidence. **C2 is the first out-of-sample test of this model.**
4. **SYS-5 passes by 0.09°.** A slightly harder skid on one wheel could push heading past the limit. If it does, SYS-5 fails on evidence and the yaw term is re-derived — it will not be waved through.

---

## 5. C2 run design

Single flash-and-run of the locked program from the standard start line, ≈3.5 s of motion plus dump. Timeout 60 s.

**Data captured for the verification argument:** trigger reading / speed / threshold / heading; the **braking transient at full 10 ms rate** (the A-4 defect fixed); rest medians and spread; three independent onboard gap estimates (ranger, model back-out, odometry); invalid-sample count; loop timing; IMU at-rest confirmation; ranger B logged as a monitor.

**Then, and only then:** the single costed operator measurement of the final gap (TBD-17). It closes the objective at the operating point and is the sole outside-input action of the entire programme.

**If the prediction holds, the same unchanged program is locked for the five operation runs.** No requirement is deferred to operation; the verification argument closes entirely at GATE C.
