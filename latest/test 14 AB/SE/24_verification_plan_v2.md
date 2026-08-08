# VERIFICATION PLAN — v2 · **FROZEN**
**Document:** `24_verification_plan_v2.md` · **Type: PLAN**
**Supersedes:** v1 (`23_verification_plan_v1.md`, retained **unedited** as the record of what
was predicted and falsified)

---

## 1. v1 WAS FALSIFIED

Measured gap: **52 mm**. Four frozen clauses:

| clause | predicted | measured | verdict |
|---|---|---|---|
| gap within [10.3, 60.2] mm | 35.3 mm | 52.0 mm | **holds** |
| onboard estimate agrees to within 10 mm | ≤2 mm error | **15.5 mm error** | **FAILS — SYS-8** |
| heading ≤ 5° | 2.54° | 3.23° | holds |
| no contact | — | none | holds |

**The statement as a whole is falsified.** The gap clause held, and my pre-committed rule
said "gap in interval → prediction holds → GATE C". I am not taking that exit. The frozen
statement had four clauses and one failed; treating the run as a pass because the widest
clause survived would be reading the rules to suit the result, which is the exact failure
mode the freeze exists to prevent. **SYS-8 fails, so the argument does not close.**

### 1.1 Diagnosis — one parameter, cleanly identified

`k` was **1.63% too high**: 0.4992 against a true 0.4912. Over 963 mm of travel that is
15.5 mm — the entire estimate error, to the millimetre. Nothing else is implicated:

| quantity | v1 predicted | measured | Δ |
|---|---:|---:|---:|
| travel to trigger | 1907 deg | 1908.5 deg | +1.5 |
| stop distance `S` | 11.0 mm | 10.73 mm | −0.27 |
| crossing undershoot | 1.8 mm | 0.72 mm | −1.1 |
| motor symmetry | ≤5% | **0.06%** | — |

**The structure of the model is right; one number in it was wrong.** That is the good case:
it is re-bindable rather than re-derivable.

### 1.2 Why v1's `k` was wrong, and why v2's cannot be wrong the same way

v1 computed `k = (G − M1)/1646.5` using **RUN-3's travel** with **RUN-5's start distance** —
it assumed the two runs started from the same place. They did not.

RUN-5 gives `k` from **one run's own endpoints**, both operator-measured, with no
start-line assumption anywhere:

```
k = (1000 − 52) / 1930 = 0.491192 mm/deg      σ_k/k = 0.30%
```

Re-scaling the earlier runs on this `k` exposes what v1 had assumed away:

| run | start distance |
|---|---:|
| RUN-3 | 986.7 mm |
| RUN-4 | 984.7 mm |
| RUN-5 | 1000.0 mm *(measured)* |

**Mean 990.5 mm, sample sd 8.3 mm.** The start line is *not* constant to the millimetre. My
GATE B report assumed 8 mm as "the weakest number in the budget" — that guess was right, and
it is now a measurement rather than an assumption.

`S` also improves: two samples, 10.81 and 10.56 mm — a spread of 0.25 mm against the 9%
prior I had been carrying. `rel_σ_S` drops to **1.1%**.

---

## 2. RE-DERIVED CONFIGURATION

| item | v1 | **v2** |
|---|---|---|
| `k` | 0.4992 (assumed common start) | **0.491192** (same-run T3 pair) |
| anchor `G` | 1000.0 (one placement) | **990.0** (mean of three, hard-coded) |
| `TRIG_GAP` | 48 mm | **44 mm** |
| `S` | 11.0 mm, n=1, 9% prior | **10.68 mm, n=2, 1.1%** |

The anchor moves to the *mean* placement, not the measured one. Hard-coding 1000 would bias
every operation run 9.5 mm closer than designed, because the operator resets by eye and two
of three resets landed near 985.

**No empirical tweaking.** `TRIG_GAP` is not tuned to hit a target; it is solved from
`E[gap] = TRIG − loop bias − S` against the margin requirement `E[gap] ≥ 3σ_g`.

---

## 3. FROZEN PREDICTION — v2

| quantity | predicted |
|---|---:|
| cruise speed | 368.4 mm/s |
| stop distance `S` | 10.68 mm |
| crossing undershoot | 1.73 mm |
| **final gap, mean** | **32.1 mm** |
| σ_g | 9.4 mm |
| 3σ low tail | +3.8 mm |
| onboard estimate `g_est_final` | 32.1 mm, error ≤ 5 mm |

σ budget: start-line scatter **8.3** (now measured, n=3) ⊕ slip 3.0 ⊕ `k`×travel 2.8 ⊕ yaw
1.3 ⊕ quantisation 1.0 ⊕ `S` 0.18.

**Start-line scatter is now 78% of the variance.** Everything I control is down at the
1–3 mm level; the dominant term is where the operator sets the rover down, which I cannot
reduce from onboard.

### 3.1 The falsifiable statement

> **The verification run will stop with a measured gap of 32.1 mm, within [3.8, 60.4] mm
> (±3σ). The onboard estimate will agree with the measured gap to within 10 mm. Heading will
> not exceed 5°. There will be no contact.**

The estimate clause is the one that failed last time and is the real test: it is now a
direct check on the re-bound `k`, independent of the data that bound it only if the rover
starts somewhere other than 1000 mm — which, given 8.3 mm of scatter, it will.

---

## 4. Pre-committed disposition — unchanged in form, and I will hold to it

| outcome | disposition |
|---|---|
| all four clauses hold | GATE C → operation, same program |
| any clause fails | falsified → diagnose → **v3** → re-run |
| contact | falsified; `TRIG_GAP` re-derived upward before any further run |
| `trigger_reason` ≠ 1 | anomaly report, not a verification result |

---

## 5. Cost of holding the line

This re-run costs one program run and one measurement. I could have declared v1 a pass on
the gap clause and gone straight to operation. I am not doing that, because the failed clause
was a **15.5 mm systematic error in the direction of the wall** — had the operation trigger
been set at the design point rather than detuned, that same error would have been a contact.
The one thing this whole process is for is not shipping a known systematic.
