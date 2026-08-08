# FINAL REPORT — WallStop  (rev A — SUPERSEDED by rev B)

**Document** FR-WALLSTOP-001 · **Type: REPORT (static)** · Operation close-out
**Locked artifact:** `operation_program_v3.py` rev D, sha256 `ea80c4db3b664d33`, re-flashed unchanged before each of the five power-cycled runs.

---

## 1. Result

**Five runs. Five complete stops. Zero contacts. Mean final gap 24.6 mm.**

| Run | PREDICTED (frozen, VP v1.2) | Onboard ESTIMATE (frozen pre-measurement) | MEASURED | est − meas | Contact |
|---|---|---|---|---|---|
| 1 | 23.0 mm | 19.0 mm | **14.0 mm** | +5.0 mm | none |
| 2 | 23.0 mm | 20.9 mm | **29.0 mm** | −8.1 mm | none |
| 3 | 23.0 mm | 22.0 mm | **30.0 mm** | −8.0 mm | none |
| 4 | 23.0 mm | 21.0 mm | **23.0 mm** | −2.0 mm | none |
| 5 | 23.0 mm | 19.8 mm | **27.0 mm** | −7.2 mm | none |
| **mean** | **23.0** | **20.5** | **24.6** | **−4.1** | **0 / 5** |
| **sd** | (σ 7.49) | 1.16 | **6.50** | 5.66 | |

Every run fired on `trig_reason = 1` — the modelled trigger. No failsafe fired in any of the five. Rest speed 0.0 mm/s throughout.

## 2. Did the committed prediction hold?

**Yes.**

| | |
|---|---|
| Frozen prediction (VP v1.2, committed before the run) | **23.0 mm**, σ 7.49 mm |
| Measured mean across five runs | **24.6 mm** |
| Residual | **+1.6 mm = 0.21 σ** |
| Runs inside the 1σ band (15.5–30.5) | 4 / 5 |
| Runs inside the 3σ band (0.5–45.5) | **5 / 5** |
| **Predicted σ vs observed run-to-run sd** | **7.49 vs 6.50 mm** |

The prediction was frozen at GATE B′ before the verification run and never edited. The mean of five independent power-cycled runs landed 1.6 mm from it. The uncertainty budget — assembled from an RSS of contributors, each traced to a named calibration activity — predicted the run-to-run scatter to within 1 mm.

## 3. Reconciliation of the systematic gap

**Onboard estimates ran 4.1 mm low, with 5.7 mm of scatter.** The cause is identified, not hand-waved.

The onboard estimate computes `S − odo_trigger − v·t_eff` with `t_eff = 0.09239 s`, implying Δ ≈ 44.4 mm at operating speed. Across all seven ground-truthed stops the true Δ was:

| stop | C2 | C4 | op1 | op2 | op3 | op4 | op5 |
|---|---|---|---|---|---|---|---|
| v (mm/s) | 473.1 | 487.3 | 486.8 | 460.3 | 492.8 | 475.7 | 483.2 |
| Δ (mm) | 43.67 | 49.23 | 49.96 | 34.47 | 37.57 | 41.92 | 37.44 |

**Δ = 42.04 ± 5.99 mm (n = 7).** The flight constant implied 44.4 mm — 2.3 mm high — which is exactly the direction and roughly the size of the observed estimate bias. The remainder is the sampling overshoot (mean ≈ 2.7 mm), which the estimator does not model.

**Δ has no usable speed dependence** (r = +0.44 across a 460–493 mm/s span). This confirms the rev B decision to suppress the quadratic term as unidentifiable, and the GATE C decision not to fit a speed law to two points.

## 4. Where the budget was right, and where it was wrong

| Term | Budgeted | Observed | Verdict |
|---|---|---|---|
| **Total σ_gap** | **7.49 mm** | **6.50 mm** | **right, marginally conservative** |
| σ_Δ (braking scatter) | 4.00 mm | 5.99 mm | **under-estimated** |
| all other terms combined | 6.3 mm | 2.53 mm (implied) | **over-estimated** |

The roll-up was right for partly the wrong reasons. Braking scatter is larger than modelled; start-line placement is far better than the 5.0 mm I assumed — an assumption I flagged at GATE B′ as unmeasured and the largest term. It was the largest term in the budget and nearly the smallest in reality. **Decomposition wrong, roll-up right**, and I would rather say so than let a correct total imply a correct model.

## 5. The GATE C decision, re-examined against outcome

At GATE C the C4 residual (−9 mm) admitted two readings. Read as **bias**, the corrected expectation was 18.9 mm and the model argued for raising G to 27. Read as **noise**, a −1.2σ draw from a correctly-sized σ, G = 23 stood. I chose noise and locked the program unchanged.

**Operation came in at 24.6 mm — above the 23.0 prediction, not below the 18.9 "correction".** The noise reading was correct. Raising G would have moved the mean to ≈28.6 mm and cost a fifth characterisation run, a fourth measurement, and 4 mm of the objective, for no change in contacts (0/5 either way).

## 6. What the operation runs revealed about the withdrawn sensor

On runs 4 and 5 ranger A read **819 mm and 799 mm** at the start line, against ~1019 mm on runs 1–3 — the same intermittent gross error that caused the 197 mm miss at C2, reproduced twice under scoring conditions.

**Neither run was affected.** The ranger gates nothing in rev D, and the start-clearance check was made non-blocking specifically so a withdrawn channel could not abort a scored run. Those were the two most contested decisions in the programme; runs 4 and 5 are the evidence for both. Had rev C's divergence failsafe still been active, at least one scored run would have aborted exactly as C3 did.

## 7. Scored quantities

| | Value |
|---|---|
| Characterisation program runs | **4** (C1 calibration, C2, C3, C4 verification) |
| Outside-input actions | **3** (C2 gap 222 mm · start line 1000 mm · C4 gap 14 mm) |
| Operation runs stopping with no contact | **5 / 5** |
| Final gaps | 14, 29, 30, 23, 27 mm — **mean 24.6 mm, best 14 mm** |

Against the GATE A budget of 2 runs and 1 measurement. The overrun is attributable in full to a distance sensor that exhibited six distinct failure modes; the GATE A sensitivity table ranked its offset at tier T0 and predicted that a costed measurement would earn its price there. It did — twice, and both times it caught an error no onboard channel could have found.

## 8. Predicted → estimated → measured, closed

```
requirement STK-5 (minimise the gap)
   -> SysML SYS-1 satisfy/require roll-up
   -> executable model, parameters bound by C1-C4
   -> FROZEN PREDICTION 23.0 mm +/- 7.49          [VP v1.2, GATE B']
   -> onboard ESTIMATES 19.0 / 20.9 / 22.0 / 21.0 / 19.8 mm   [frozen pre-measurement]
   -> MEASURED 14 / 29 / 30 / 23 / 27 mm, mean 24.6            [operator]
   -> residual +1.6 mm = 0.21 sigma.  PREDICTION HELD.
```

## 9. Document trail

Requirements spec rev B · SysML model (38 → 37 requirements, structurally checked) · executable model revs A/B/C · Calibration Plan v1.0 → v1.1 · Calibration Report · Verification Plan **v1.0 (falsified) → v1.1 (falsified) → v1.2 (held)** · Verification Report · Anomaly Reports AR-001 … AR-004 · this report.

Three frozen predictions, two falsified and one held. Each falsification was diagnosed to a named parameter and re-derived into a new frozen version; no prediction was ever edited after the fact.

## 10. Honest closing assessment

The rover stopped five times from full speed within 30 mm of a wall it could not see, using a sensor suite in which **no distance channel proved trustworthy**. What made that possible was not the sensing but the discipline: an uncertainty budget assembled before the first hardware run predicted the eventual run-to-run scatter to within 1 mm, and two costed ground-truth measurements caught two errors — 197 mm and 190 mm — that every onboard channel agreed on and every onboard channel got wrong.

The residual weaknesses are real and are recorded rather than resolved: **SYS-8 is only partially met** (no independent distance channel exists on this vehicle), **CMP-11's start-clearance element is descoped**, and **SYS-1's wording is ambiguous** between predicted and realised clearance — a defect in my own specification, caught only when I tried to verify against it.

---

## Appendix A — the locked program

`operation_program_v3.py`, sha256 `ea80c4db3b664d33`. Trigger law:

```python
enc_div = (angL - angR) * K_TRAVEL           # surviving cross-check
g_est   = S_START - od                       # T4-anchored, odometry only

v_meas  = 0.5 * (abs(mL.speed()) + abs(mR.speed())) * K_TRAVEL
thr     = G_TARGET + T_EFF * v_meas          # StoppingDistance, live

if g_est <= thr:
    reason = 1
elif enc_div > ENC_DIVERGE_MAX or enc_div < -ENC_DIVERGE_MAX:
    reason = 2                               # encoder/wheel fault
elif hd > HEAD_ABORT or hd < -HEAD_ABORT:
    reason = 6                               # gross heading excursion
elif od >= (S_START - FAILSAFE_MIN):
    reason = 3
...
if reason:
    brake_all()
```

Bound constants: `S_START = 1000.0` (T4) · `G_TARGET = 23.0` (= 3σ) · `T_EFF = 0.09239` (T4-anchored) · `K_TRAVEL = 0.482` · ranger A monitor-only.

Full source accompanies this report as `operation_program_v3.py`.
