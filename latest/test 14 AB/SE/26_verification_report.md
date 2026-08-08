# VERIFICATION REPORT
**Document:** `26_verification_report.md` · **Type: REPORT** (static)
**Gate:** GATE C — the single place every requirement is closed
**Article verified:** `21_revF_program.py` at Verification Plan **v3** constants, unchanged

---

## 1. Verification result

Verification Plan v3, frozen before the run, made four claims. **All four hold.**

| clause | predicted | measured | verdict |
|---|---|---|---|
| final gap within [7.9, 31.7] mm | 19.8 mm | **18.0 mm** | **PASS** (residual −1.8 mm) |
| onboard estimate within 10 mm | ≤4 mm | **0.19 mm** | **PASS** |
| heading at trigger ≤ 5° | ≤5° | −0.22° (2.52° peak) | **PASS** |
| no contact | — | none | **PASS** |

### 1.1 The end-to-end evidence

One `k`, one `G`, across every run that shares the operation profile:

| run | config | predicted | measured | residual |
|---|---|---:|---:|---:|
| RUN-5 | v1 | 53.03 mm | 52.0 mm | +1.03 mm |
| RUN-6 | v2 | 41.99 mm | 43.0 mm | −1.01 mm |
| **RUN-7** | **v3** | **18.19 mm** | **18.0 mm** | **+0.19 mm** |

Mean +0.07 mm, sd **1.03 mm**, across a span from 52 mm down to 18 mm. `k` was fitted on
RUN-5 and RUN-6 only, so **RUN-7 is fully out of sample** — and it predicted the measured gap
to **0.19 mm**.

### 1.2 The systematic is gone

| plan | onboard estimate | measured | error |
|---|---:|---:|---:|
| v1 | 36.54 mm | 52.0 mm | **15.46 mm** |
| v2 | 30.95 mm | 43.0 mm | **12.05 mm** |
| **v3** | **18.19 mm** | **18.0 mm** | **0.19 mm** |

Both earlier errors pointed the same way — the rover farther out than it believed. That
signature is what I said I would look for, and it is absent.

---

## 2. Falsify → diagnose → re-derive trail

| version | prediction | outcome | responsible parameter | re-derivation |
|---|---|---|---|---|
| **v1** | 35.3 mm | **FALSIFIED** (SYS-8: 15.5 mm) | `k` high by 1.63% — computed from RUN-3's travel with RUN-5's start, assuming a common start line | `k` re-bound from a single run's own measured endpoints |
| **v2** | 32.1 mm | **FALSIFIED** (SYS-8: 12.05 mm) | anchor 12 mm low — I applied a fast-profile `k` to a 45%-creep run, concluded the start line scattered by 8.3 mm, and moved the anchor to match my own artifact | anchor restored to 1000 mm; `k` fitted on operation-profile runs only |
| **v3** | 19.8 mm | **HOLDS** | — | — |

Both failures were caught by the estimate clause while the gap clause held. Had I taken the
gap-clause exit either time, a 12–15 mm systematic **toward the wall** would have shipped
into the scored runs.

---

## 3. Requirement closure

Method: **T** test · **A** analysis · **I** inspection.

### 3.1 STK

| req | method | evidence | verdict |
|---|---|---|---|
| STK-1 no contact | T + A | zero contact in 7 runs; guards stopped RUN-1 and RUN-4 without contact | **PASS** |
| STK-2 minimise gap *(objective)* | T | 18.0 mm measured at the operating point | **PASS (graded)** |
| STK-3 maximum speed | T | 752.8 / 750.7 deg/s at a 750 command — both in regulation | **PASS** |
| STK-4 complete stop | T | `S` = 10.79 mm, at rest, no retreat | **PASS** |
| STK-5 onboard gap estimate | T | 18.19 vs 18.0 measured | **PASS** |
| STK-6 run independence | I | no persisted state; hub power-cycled each run | **PASS** |

### 3.2 SYS

| req | method | evidence | verdict |
|---|---|---|---|
| SYS-1 clearance > contact floor | T | 18.0 mm measured | **PASS** |
| SYS-2 gap ≥ k_σ·σ_g | A | 18.0 ≥ 3 × 1.03 = 3.1 mm | **PASS** |
| **SYS-3 OBJECTIVE** | **T vs operator ground truth at the operating point** | **18.0 mm, M5** | **PASS — closed here, not deferred** |
| SYS-4 command max in regulation | T | commanded 750; achieved 752.8 / 750.7 | **PASS** |
| SYS-5 rest within settle limit | T | 22.0 deg post-trigger, ≈60 ms | **PASS** |
| SYS-6 heading ≤ 5° to trigger | T | 2.52° peak, −0.22° at trigger | **PASS** |
| SYS-7 degraded stop clears wall | T + A | travel cap, time limit and yaw abort; the yaw and wrong-way guards each stopped a run clear of the wall | **PASS** |
| SYS-8 estimate error ≤ 10 mm | T | 0.19 mm | **PASS** |
| SYS-9 no cross-run state | I | inspection of the locked program | **PASS** |

### 3.3 FUN

| req | method | evidence | verdict |
|---|---|---|---|
| FUN-3 reject implausible input | T | wrong-way guard fired correctly in RUN-1 and RUN-4 | **PASS** |
| FUN-4 trigger within one loop | T | undershoot 3.02 mm ≤ one loop of travel (3.5 mm) | **PASS** |
| FUN-5 maximum braking, no retreat | T | `S` = 10.63 mm mean, sd 0.14 mm, n = 3 | **PASS** |
| FUN-6 odometric limit | T | now primary; travel cap retained as backstop | **PASS** |
| FUN-7 time backstop | I | sized from `G`, `TRIG` and `v` | **PASS** |
| FUN-8 odometry from rotation | T | ±1.03 mm end-to-end over 982 mm | **PASS** |
| FUN-9 measure heading | T | heading logged throughout | **PASS** |
| FUN-10 no I/O on hot path | I | buffer only; stdout after motors stop | **PASS** |
| FUN-12 safe termination + sentinel | T | sentinel in all 7 runs, including aborts | **PASS** |
| FUN-15 measured correction sign | T | yaw probe: +20.9°, +23.1°, +24.2° across three runs | **PASS** |
| FUN-1, 2, 11, 13, 14 | — | **RETIRED** with the ranger | — |

### 3.4 CMP

| req | method | evidence | verdict |
|---|---|---|---|
| CMP-1 / CMP-2 motor ceiling | T | 752.8 / 750.7 deg/s | **PASS** |
| CMP-3 symmetry ≤ 5% | T | **0.27%** | **PASS** |
| CMP-4 odometry scale ≤ 1% | T | **0.10%** (1.03 mm over 982 mm) | **PASS** |
| CMP-5 deceleration floor | T | ≈6500 mm/s² | **PASS** |
| CMP-10 IMU heading drift ≤ 1° | T | static dwells across runs | **PASS** |
| CMP-11 loop period ≤ 25 ms | T | 9.4 ms | **PASS** |
| CMP-17 start distance is a measured setup constant | T | M3 = 1000 mm; ±1 mm residuals across 3 runs confirm repeatability | **PASS** |
| CMP-6, 7, 8, 9, 15, 16 | — | **RETIRED** with the ranger | — |
| CMP-12, CMP-13 | I | rear ranger 2000 mm always; reflectance serves no quantity | **DROPPED** by traceability |

**No requirement is left asserted without evidence.**

---

## 4. Locked configuration for operation

```
G_MM         = 1000.0     # operator-measured start distance
K_MM_PER_DEG = 0.49066    # fast profile, fitted on RUN-5 and RUN-6
TRIG_GAP     = 32.0       # gap = TRIG - 12.16 mm
SPEED_CMD    = 750        # both motors in closed-loop regulation
```

**Predicted per-run gap: 18.0 mm, σ 1.03 mm.**

### 4.1 The trade I am declining

The validated model would support `TRIG_GAP` = 22 and a gap near 8 mm — 18 mm is roughly
17σ on the demonstrated residual, which on the closeness score is a lot to leave on the
table.

I am flying the verified configuration unchanged, for two reasons. My pre-committed
disposition said *"all four clauses hold → operation, same program"*, and tightening the
trigger on the strength of a good result is the same move I refused three times when the
results were bad. And the ±1 mm residual comes from three runs at one hard-coded anchor; the
operator resets the rover five more times, and 18 mm absorbs a placement excursion that 8 mm
would not.

### 4.2 Residual risk carried into operation

- **Single-string on odometry.** Wheel slip beyond what `k` absorbs produces contact and
  nothing onboard would witness it. `S` at 0.14 mm sd over three runs is the best evidence
  that slip is stable, but it is not a monitor.
- **`n` = 3.** The residual sd is a three-sample estimate.
- **Heading rotates ~4–5° during braking**, after the trigger. SYS-6 is written to the
  trigger and passes, but that rotation swings the leading corner a few millimetres and is
  inside every measured gap reported here.
