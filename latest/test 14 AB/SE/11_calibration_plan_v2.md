# CALIBRATION PLAN — Wall-Approach Rover — **v2**
**Document:** `11_calibration_plan_v2.md` · **Type: PLAN** (forward-looking; revised and re-issued)
**Supersedes:** v1.0/v1.1 (`07_calibration_plan_v1_1.md`, retained unedited as the record of
what was planned before RUN-1) · **Trigger for re-issue:** AR-01

**What changed and why.** RUN-1 revealed a discovery-logic defect its predecessor did not
anticipate (AR-01), and bound five parameters. Both change the plan: the sensitivity
ranking shifts when parameters become known, and the run design must close the defect. This
is a re-plan, not a patch — v1.1 stands as the record of the prior reasoning.

---

## 0. SENSITIVITY ANALYSIS (re-run with RUN-1 bindings applied)

Priors and method are unchanged from v1 §0.1. The table is re-computed with the five
parameters RUN-1 bound now held at their measured values.

| parameter (SysML attribute) | assumed range | d objective (mm) | d nominal margin (mm) | d degraded margin (mm) | knowledge tier | priority |
|---|---|---:|---:|---:|---|---|
| `a_decel_mm_s2`<br>`WallRover.decel` | 1000 .. 6000 mm/s² | -38.7 | **+137.8** | +137.8 | T0 prior only | **P1** |
| `b_offset_mm`<br>`WallRover.rangeOffset` | -40 .. 80 mm | +0.0 | **-120.0** | -120.0 | T0 prior only | **P1** |
| `k_mm_per_deg`<br>`WallRover.speedScale` | 0.35 .. 0.8 mm/deg | +23.3 | **-95.8** | -78.9 | T0 prior only | **P1** |
| `omega_max_deg_s`<br>`WallRover.maxWheelSpeed` | 700 .. 1100 deg/s | +10.2 | -45.2 | -36.5 | **T2 bound** | **P1** → residual only |
| `delta_bs_mm`<br>`WallRover.backstopAllowance` | 5 .. 40 mm | +0.0 | +0.0 | -35.0 | T0 prior only | **P1** |
| `tau_sensor_s`<br>`WallRover.rangerLag` | 0.005 .. 0.06 s | +7.7 | -31.6 | +0.0 | T0 prior only | **P1** |
| `e_odo_mm`<br>`WallRover.odometryError` | 2 .. 20 mm | +0.0 | +0.0 | -18.0 | T0 prior only | P2 |
| `t_chain_s`<br>`WallRover.latency.tChain` | 0.002 .. 0.02 s | +2.5 | -10.4 | -10.4 | T0 prior only | P2 |
| `t_loop_s`<br>`WallRover.loopPeriod` | 0.005 .. 0.025 s | +2.2 | -5.8 | +0.0 | **T2 bound** | closed |
| `rel_sigma_S`<br>`WallRover.stopRepeatability` | 0.03 .. 0.15 | **+22.1** | +0.0 | +0.0 | T0 prior only | P2 |
| `u_b_mm`<br>`WallRover.offsetUncertainty` | 1 .. 10 mm | +12.9 | +0.0 | +0.0 | T0 prior only | P2 |
| `k_sigma`<br>`WallRover.marginMultiplier` | 2.5 .. 3.5 | +10.8 | +0.0 | +0.0 | design decision | P2 |
| `sigma_n_mm`<br>`WallRover.rangerNoise` | 1 .. 8 mm | +8.7 | +0.0 | +0.0 | **T2 bound (one range)** | P3 residual |
| remaining rows | — | ≤ +2.5 | 0.0 | 0.0 | T0 | P3/P4 as v1 |

### 0.1 What changed in the ranking

1. **`a_decel` overtakes `b_offset` as the top nominal-margin risk** (137.8 mm vs 120.0 mm).
   Binding `omega_max` at its true ceiling of 1000 deg/s (rather than a 700–1100 prior)
   *raised* the leverage of the remaining kinematic unknowns, because the speed is now known
   to sit at the top of the assumed band. Knowing one parameter made another more dangerous —
   which is exactly why the sweep is re-run rather than carried forward.
2. **`rel_sigma_S` rises to +22.1 mm on the objective**, the largest single objective term.
   Stop repeatability is now the dominant limit on how close we can get.
3. **`t_loop_s` is closed.** 10.18 ms measured; CMP-11 PASS.
4. **`sigma_n_mm` is bound at one range only** (3.68 mm at ~900 mm). CMP-8 requires the
   trigger and rest ranges too, so it stays open at reduced priority.
5. **`delta_AB_mm` is bound at 107.1 mm and FAILS FUN-13.** It has near-zero numeric
   leverage but a failing verdict, and a failing verdict is not a low priority. See §2.5.

**Unchanged conclusion:** `b_offset` remains the only load-bearing parameter with no onboard
observer, and M1 remains justified and unspent.

---

## 1. CALIBRATION INPUT LIST

**TBD closure: 5 of 29 closed** (TBD-01 partial, TBD-07 partial, TBD-10, TBD-11, TBD-29).
RUN-2 is designed to close TBD-02…06, 09, 12, 17, 18, 26, 27 and complete TBD-01/07;
M1 closes TBD-08, 16, 28.

| TBD | parameter | status after RUN-1 |
|---|---|---|
| TBD-01 | `omega_max_deg_s` = 1000 deg/s | **bound T2** (controller ceiling); cruise-plateau confirmation outstanding |
| TBD-07 | `sigma_n_mm` = 3.68 mm | **bound T2 at ~900 mm only** |
| TBD-10 | `delta_AB_mm` = 107.1 mm | **bound T2** — and **FUN-13 FAIL**, open per §2.5 |
| TBD-11 | `t_loop_s` = 10.18 ms | **CLOSED**, CMP-11 PASS |
| TBD-29 | `R0_mm` = 903.4 mm | **bound T2** |
| all others | — | unbound; no valid translation occurred |

Design constants (v1 §1.3) are unchanged, including `k_sigma` = 3.0.

---

## 2. CHARACTERIZATION-RUN DESIGN — RUN-2 (REV B)

### 2.1 Configuration, now evidence-based

| item | value | source |
|---|---|---|
| forward rangers | Port **A**, Port **B** | RUN-1 `port_kind` |
| rear ranger | Port **E** (reads 2000 throughout) | RUN-1 — **dropped by traceability** |
| drive motors | Port **C**, Port **D** | RUN-1 `port_kind` |
| reflectance | Port **F** | RUN-1 — **dropped by traceability** |
| vertical axis | index 2 (gravity 9670 mm/s²) | RUN-1 `accel_rest_axis` |
| yaw channel | `hub.imu.heading()`, responds correctly | RUN-1 (tracked 0→95°) |
| relative polarity | **opposite signs translate** (same sign spins) | RUN-1 `probe1_dheading` |

The map is hard-coded and **asserted** at startup, which removes discovery risk from RUN-2
and from every operation run.

### 2.2 The four corrections (detail in AR-01 §8)

**A.** hard-coded, asserted device map · **B.** polarity fixed to the translating pair, with
the direction probe **gated on heading** rather than on range · **C.** in-loop gross-yaw
guard at 15° (`reason 6`) · **D.** both rangers logged separately through the approach.

**On C — why 15° and not SYS-6's 5°.** The guard exists to catch *gross* failure, not to
enforce the requirement. Tripping the approach at 5° would convert marginal, acceptable
drift into an aborted run and a poor gap. SYS-6 stays a verification criterion evaluated
after the fact; the guard catches the spin.

### 2.3 Test-like-you-fly — unchanged, and now cheaper

REV B remains a strict superset of the operation program: identical control loop, trigger
rule, stop maneuver and buffer skeleton, with characterization work confined to before the
motors are first commanded and after they stop. Because discovery is replaced by a map plus
one probe, the pre-hot-path phase drops from ~3.6 s to ~1.8 s. The operation program is
derived from REV B by deleting Phase E, removing the direction probe (direction is then a
constant too), and setting five calibrated constants.

### 2.4 Risk posture for RUN-2

Unchanged in kind from v1 §2.3: `R_TRIG` = 600 mm against a worst-case prior `S` of 384 mm;
the odometric backstop deliberately non-pre-emptive while `k` is unbound; protection carried
by the **`k`-free** staleness guard, the wrong-way guard, and now the gross-yaw guard.
RUN-1 provided direct evidence that this posture works: the wrong-way guard stopped a
full-speed spin without the rover approaching the wall.

### 2.5 FUN-13 disposition plan (open item)

The 107.1 mm pair split is a **FAIL** carried open into the Calibration Report. It will be
dispositioned from RUN-2's per-ranger traces, not by assertion:

- Regress each ranger's reading against odometry over the approach. A ranger tracking the
  wall gives slope −`k` with small residuals; one that is angled or seeing something else
  gives a different slope, curvature, or a poor fit.
- **If both track with the same slope** → the split is a mounting offset, `min()` is correct
  (it tracks the closest point, which is the contact-relevant one), the offset is absorbed
  into `b`, and FUN-13's limit is re-derived from evidence rather than the assumed 30 mm.
- **If only one tracks** → the fusion rule is changed to that ranger alone before GATE B.
  Because both channels are logged in full, `d_T`, `r_rest` and hence `S` can be
  reconstructed for either channel post hoc, so this does **not** cost a re-run.
- **If neither tracks** → escalate; the trigger has no valid primary channel.

No operator measurement is requested for this. Asking for a ruler here would arbitrate
between two suspect channels; the approach regression lets the disagreement reveal which is
wrong, which is what cross-sourcing is for.

---

## 3. OUTSIDE-INPUT REQUESTS — unchanged, still two, still unspent

**M1** after RUN-2, *conditional on the run reaching its close pose*; **M2** after the
verification run. Both as specified in v1 §3. **M1 was deliberately not spent on RUN-1**,
because the rover finished rotated and reading 2000 mm — a measurement there would have
bound nothing. Preserving it cost nothing and is the reason the run budget, not the
measurement budget, absorbed AR-01.

---

## 4. VERIFICATION SUPPORT

Unit-verification ordering is unchanged from v1 §4.1, with these already closed by RUN-1
and pulled forward to the Calibration Report:

| req | verdict | evidence |
|---|---|---|
| CMP-11 loop period ≤ 25 ms | **PASS** | 10.18 ms, 34 samples over 346 ms |
| CMP-12 rear ranger | **DROP** by traceability | 2000 mm at start, rest, creep |
| CMP-13 reflectance | **DROP** by traceability | serves no catalogued quantity |
| FUN-3 implausible-sample / wrong-way guard | **PASS** | fired at 155 deg; runaway prevented |
| FUN-12 safe termination + sentinel | **PASS** | sentinel emitted on the abort path |
| FUN-13 forward-pair agreement | **FAIL — open** | 107.1 mm > 30 mm; disposition per §2.5 |

The eventual verification argument's structure (v1 §4.2) is unchanged, including that
**SYS-3, the objective, closes at GATE C on M2** and never on the operation runs.

---

## 5. RUN BUDGET — revised

| | v1 plan | v2 plan | actual so far |
|---|---:|---:|---:|
| characterization runs | 2 | **3** | 1 used |
| operator measurements | 2 | **2** | 0 used |

RUN-1 is spent and bought five bound parameters, five requirement verdicts and one root
cause. The run budget absorbed AR-01; the measurement budget did not.

**If RUN-2 succeeds**, the remaining plan is: RUN-2 → M1 → GATE B (Calibration Report +
frozen Verification Plan) → verification run → M2 → GATE C → operation.

---

## 6. WHAT I AM ASKING YOU TO REVIEW

1. **AR-01's recommendation** — retest with REV B, at a cost of one program run.
2. **The four corrections** in §2.2, in particular the 15° in-loop yaw guard and the
   decision to keep SYS-6's 5° as a post-hoc verification criterion.
3. **The FUN-13 disposition plan** in §2.5 — specifically that it is answered from RUN-2's
   own data rather than by spending a measurement.
4. **Holding `R_TRIG` at 600 mm** for RUN-2 rather than tightening it. Nothing about `S`
   has been learned, so tightening would spend safety margin to buy nothing.

**I will not flash RUN-2 until you have reviewed this and given an explicit go-ahead — and
I will ask again immediately before the flash.**
