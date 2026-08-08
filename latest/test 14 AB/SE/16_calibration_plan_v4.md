# CALIBRATION PLAN — Wall-Approach Rover — **v4**
**Document:** `16_calibration_plan_v4.md` · **Type: PLAN** (revised and re-issued)
**Supersedes:** v3 · **Trigger:** AR-03 + operator measurement **M1**

---

## 0. M1 AND WHAT IT DECIDED

**M1 = 178 mm** at a pose reading 58.875 mm, heading −0.34°.

```
b = r − g = 58.875 − 178 = −119.1 mm
```

**The prior was wrong.** GATE A stated `b ∈ [−40, +80] mm`. The truth is 79 mm outside it.
The sensitivity table ranked `b` P1 on a 120 mm assumed range; the real range needed to be
wider still. That is not a failure of the ranking — it is the reason the ranking put a
costed measurement here, and it is the clearest possible vindication of the rule that **a
sensor value driving a scored quantity is a hypothesis until an independent higher-tier
source confirms it at the operating point.** Three runs of onboard data would never have
found this; every onboard channel is self-consistent with a wrong `b`.

**Independent corroboration.** `b` = −119.1 puts the true start gap at
`887.08 + 119.1 = 1006.2 mm`, against the task's stated *"~1000 mm out"*. That check uses
nothing from the derivation. A constant-offset model fits both ends of an 828 mm baseline; a
scale-error model does not (it would predict 333 mm at the start, against 887 observed).

**M1 also bought `k`**, anchored at T3 over 828 mm:

| estimate | value | independent of `b`? |
|---|---:|---|
| creep segment only | 0.4986 mm/deg | yes |
| fast approach, static endpoints | 0.5066 mm/deg | yes |
| **M1-anchored, 828 mm baseline** | **0.5030 mm/deg** | no — uses M1 |

The two `b`-independent estimates bracket the anchored one. One measurement, two parameters,
cross-validated.

### 0.1 The consequence that reshapes the design

The ranger reads **119 mm short**. So the reading corresponding to a small true gap is
negative — a value the sensor can never produce:

| true gap | ranger would report |
|---:|---:|
| 25 mm | **−94 mm** |
| 100 mm | **−19 mm** |
| 159 mm | +40 mm (its floor) |

**The smallest true gap the ranger can observe at all is ≈159 mm.** It therefore cannot
trigger the stop at the operating point, and cannot measure the final gap there either.
This is not a tuning problem and no calibration fixes it.

Evaluating both architectures on the now-calibrated model:

| | ranger trigger | **odometric trigger** |
|---|---:|---:|
| trigger threshold | 48 mm *(reading, floor-clamped)* | **46 mm** *(true gap)* |
| composite stop `S` | 20.1 mm | 20.1 mm |
| σ_g | 7.84 mm | 7.84 mm |
| **predicted final gap** | **145.2 mm** | **24.1 mm** |
| low tail | 121.7 mm | 0.6 mm |
| onboard estimate error | 2.9 mm *(but unreachable)* | 6.7 mm |

The 145 mm figure is FUN-14's reachability clamp doing exactly the job it was added for at
GATE A — it prices the ranger architecture rather than letting it fail silently.

---

## 1. ARCHITECTURE REV D — odometric trigger, ranger as validator

`distance_to_go = R0_true − odo × k`, with `R0_true = R0_reading − b` from a static,
lag-free pre-run dwell. Trigger when `distance_to_go ≤ 46 mm`.

Each channel now does what it is good at: the ranger is accurate at rest (σ ≈ 2.6 mm) and
hopeless in motion (196 mm lag, AR-03); odometry is fast and lag-free but incremental, so it
needs an anchor. The ranger supplies the anchor; odometry supplies the tracking.

### 1.1 Uncertainty budget, calibrated

| term | value | note |
|---|---:|---|
| offset `b` anchor | 4.47 mm | M1 resolution + dwell mean + `b`-constancy over 828 mm |
| **scale `k` × travel** | **5.03 mm** | 0.5% of 1006 mm — *created by* the hand-off |
| stop repeatability | 1.81 mm | n = 1, prior `rel_σ_S` = 9% retained |
| loop quantisation | 1.03 mm | |
| **σ_run 3.58 ⊕ σ_sys 6.97 → σ_g 7.84 mm** | | required clearance 23.5 mm |

The two systematic terms dominate and are now comparable. **The scale term is the price of
the hand-off**: under a ranger trigger the sensor re-anchors every sample, so scale error
cannot accumulate; under an odometric trigger it acts over the whole approach. It did not
exist in v3's budget and is added to the model as `u_k_rel`.

### 1.2 What this costs in defence-in-depth — stated plainly

Under REV D the no-contact case rests primarily on **one** channel. The dangerous failure is
wheel slip, which makes odometry under-read travel so the rover goes *further* than it
believes. Measured slip across RUN-3's stop was 3.3 mm, well inside the 23.5 mm clearance,
but that is one sample.

The ranger retains a genuine one-sided check: because its lag biases the reading *high*
during motion, a reading *below* the odometric prediction can only mean the rover is closer
than it thinks. That direction is trustworthy; the reverse is not. It is a real backstop but
a coarse one, since the lag envelope is ~200 mm. **This is a reduction in redundancy
compared with the original two-ranger concept, and it is a consequence of the hardware, not
a choice I would otherwise make.**

### 1.3 Requirement deltas (specification to be re-issued on approval)

| requirement | change |
|---|---|
| **FUN-4** | trigger operand moves from the ranger estimate to the odometric estimate |
| **FUN-2** (extrapolation) | **RETIRED** — under an odometric trigger it is unnecessary; it was also silently disabled by sensor noise resetting its timer (AR-03) |
| **CMP-4** (odometry scale, 2%) | promoted from cross-check to **load-bearing**; limit tightened to **1%** |
| **CMP-9** (validity floor below operating gap) | **FAILS and is retired** — the operating gap is unobservable by the ranger; SYS-8 re-allocated |
| **SYS-8** (gap estimate) | operand moves to the odometric channel; predicted error 6.7 mm against a 10 mm limit |
| **SYS-7** (degraded stop) | re-derived onto the ranger one-sided check + time limit, per §1.2 |
| **new CMP-15** | *The static pre-run anchor shall be measured over ≥12 valid samples with the rover stationary.* Rationale: the anchor is now the single most load-bearing measurement in the run |

---

## 2. RUN-4 DESIGN

Same test-like-you-fly structure; REV C's verified fixes are retained unchanged (single
ranger, regulated speed + heading hold, passive braking, tight telemetry).

1. **Odometric trigger** at a true gap of 46 mm, computed from `R0_reading + 119.1`.
2. **Ranger one-sided cross-check** armed throughout: stop if the reading falls more than
   200 mm below the odometric prediction.
3. **Ranger-dynamics scalars** (4 lines, per AR-03): longest unchanged-value hold, largest
   single-step jump, number of changes, and mean hold. These close AR-03's open question
   cheaply and confirm the decision to retire the ranger from the trigger path.
4. **No creep phase.** The fast stop now lands at ~24 mm, which *is* the close pose. This
   shortens the run and removes a phase.
5. `k` re-measured from static endpoints for a second sample, shrinking `u_k_rel`.

**RUN-4 is a calibration run, not the verification run.** It confirms REV D at the operating
point and gives a second `S` and `k` sample. GATE B follows it.

### 2.1 Risk posture

This is the first run that will stop *near* the wall — predicted 24.1 mm, low tail 0.6 mm.
That low tail is thin, and it is thin because `n_S_samples` = 1. I therefore propose running
RUN-4 at a **deliberately detuned trigger: true gap 100 mm instead of 46 mm.** It exercises
the full REV D architecture, yields the second `S` and `k` samples, and validates the
odometric chain against the ranger at a range where the ranger still works (100 mm true gap
→ reading ≈ −19 mm… *below the floor*, so the ranger cannot confirm even there — the
confirmation must come from M2 or from odometry alone).

That last parenthesis matters: **there is no range at which the ranger can independently
confirm a small gap.** Validation of the objective at the operating point therefore depends
entirely on **M2**, exactly as GATE C requires.

---

## 3. MEASUREMENTS

**M1: SPENT**, and it changed the architecture. **M2** remains, for the verification run,
where it closes SYS-3 at the operating point.

| | planned | consumed |
|---|---:|---:|
| characterization runs | 5 | 3 |
| operator measurements | 2 | **1** |

---

## 4. WHAT I AM ASKING YOU TO REVIEW

1. **The architecture inversion** — trigger on odometry, ranger as anchor and coarse
   backstop — and the §1.2 acknowledgement that this is single-string on the dangerous
   failure mode.
2. **Retiring FUN-2 and CMP-9**, and tightening CMP-4 to 1%.
3. **RUN-4 detuned to a 100 mm trigger** rather than going straight to 46 mm on a single
   `S` sample.
4. Whether you want a **third measurement** spent at RUN-4 to confirm the odometric chain at
   close range. My recommendation is **no** — M2 at the verification run tests the same
   chain where it counts, and a mid-calibration measurement would tempt me to re-fit `b`
   from a single later sample, which the source-of-truth hierarchy forbids.

**I will not flash RUN-4 until you review this, and I will ask again immediately before the
flash.**
