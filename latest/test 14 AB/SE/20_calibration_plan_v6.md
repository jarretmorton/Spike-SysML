# CALIBRATION PLAN — Wall-Approach Rover — **v6**
**Document:** `20_calibration_plan_v6.md` · **Type: PLAN** · **Supersedes:** v5
**Decision:** Option A taken — one further operator measurement, on my call

---

## 0. THE DECISION, AND WHY MY OWN FRAMING WAS WRONG

I presented Option A in v5 as buying down the **anchor** uncertainty. Working the numbers
properly, that is not where its value is. Its value is in **`k`**.

`k` is currently obtained from a joint fit that assumes the start line is constant, so
start-line scatter feeds straight into it: 13.8 mm of scatter shifts `k` by 2.3%, which over
a 940 mm approach is **21.6 mm of position error**. That is the dominant term in the whole
budget by a wide margin.

A directly-measured start distance `G`, paired with M1, gives `k` from a **long-baseline T3
pair with no ranger anywhere in it**:

```
k = (G − 178) / 1646.5        σ_k/k = 0.35%  →  1.6 mm over the approach
```

| | σ_g | 3σ target gap |
|---|---:|---:|
| **Option B** — no measurement | 23.4 mm | **70.1 mm** |
| **Option A** — measure `G` | 9.0 mm | **27.1 mm** |

The measurement is worth about **43 mm of closeness**, not the ~20 mm I estimated in v5. I
had the right recommendation for a substantially wrong reason, and the corrected reason is
stronger: `k` being 2.7% wrong is what would have driven the rover into the wall on RUN-4
had it not been detuned.

**Decision: take Option A.**

---

## 1. ARCHITECTURE REV F — the ranger leaves the control path entirely

With `G` measured and `k` from a ranger-free T3 pair, the ranger has no remaining job in the
trigger chain. It has been the proximate cause of three of the four anomalies (A crosstalk,
196 mm dynamic lag, +325 mm in-motion error). It is retired.

| element | source |
|---|---|
| start anchor | **`G`, hard-coded from measurement** — the setup is stated to be fixed across attempts |
| scale `k` | **hard-coded**, from M1 + `G` (T3, 1646.5 deg baseline) |
| trigger | odometric: fire when `G − travel·k ≤ target + S` |
| direction witness | **forward-axis IMU acceleration** (restored; its removal is what made AR-04 unresolvable) |
| attitude | IMU heading hold, verified at 2.5° peak |
| guards | heading abort, time limit, absolute travel cap |
| forward ranger | **not constructed** — removes it as a failure mode *and* as a crosstalk source |

**Uncertainty budget (σ_g = 9.0 mm, target 27 mm):**

| term | value | basis |
|---|---:|---|
| start-line repeatability | **8.0 mm** | *the weakest number here* — see §1.1 |
| slip variability | 3.0 mm | RUN-3 measured 3.3 mm across the stop |
| `k` × travel | 1.6 mm | T3 pair |
| stop repeatability | 1.3 mm | n = 1, 9% prior on S ≈ 14 mm |
| yaw | 1.3 mm | heading hold at 2.5° peak |
| loop quantisation | 1.0 mm | 9.4 ms at 381 mm/s |

### 1.1 The one number I cannot justify from data

RUN-3 and RUN-4 read `R0` = 887.08 and 900.83 — a 13.8 mm spread. That spread is the **sum**
of start-line scatter and ranger static instability, and **two runs cannot separate them.**
I have assigned 8 mm to start-line repeatability as a deliberately conservative split of a
13.8 mm upper bound.

If the true split is worse — say all 13.8 mm is placement — then σ_g rises to about 14 mm and
a 27 mm target sits at 1.9σ rather than 3σ. **That is the residual risk of REV F and I am not
going to hide it inside an RSS.** It is also why the verification run must be validated
against ground truth before any scored run, which the process requires anyway.

---

## 2. THE REQUEST

One measurement, with a protocol that matters:

1. **Reset the rover to the start line** and square it up, exactly as for a normal run.
2. **Measure the distance from the front-most point of the rover to the wall** — the same
   measurand as M1: shortest distance from any part of the rover to the wall.
3. **Do not move it afterwards.** RUN-5 must start from that identical placement, or the
   measurement anchors a position the rover is not in.

The flash does not move the rover, so measure first, tell me the number, and I will flash
against it.

---

## 3. WHAT FOLLOWS

With `G` in hand: **GATE B** — the Calibration Report closing the TBD register with evidence,
and the Verification Plan with a frozen numeric prediction. Then **RUN-5 as the verification
run** at the operating configuration, then the ground-truth measurement that closes the
objective at **GATE C**, then the five scored operation runs.

| | consumed | projected |
|---|---:|---:|
| characterization runs | 4 | 5 |
| operator measurements | 2 | 4 |

That is over the two measurements I planned at GATE A. The overrun is honest: the prior on
`b` was wrong by 79 mm, the ranger turned out to be unfit for the control path, and `k` was
entangled with a setup quantity I had assumed away. Each measurement bought a parameter that
no onboard channel could reach.
