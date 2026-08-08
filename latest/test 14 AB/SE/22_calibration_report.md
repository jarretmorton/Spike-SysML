# CALIBRATION REPORT
**Document:** `22_calibration_report.md` · **Type: REPORT** (static — not edited once written)
**Gate:** GATE B · **Covers:** RUN-1 … RUN-4 and operator measurements M1–M3

---

## 1. Bound values

Tiers: **T3** external ground truth · **T2** anchored/multi-point onboard · **T1** single sample
· **T0** prior.

| # | quantity | value | evidence | tier |
|---|---|---:|---|---|
| TBD-02 | `k` rotation→ground scale | **0.4992 mm/deg** | `(G − M1)/1646.5` = `(1000 − 178)/1646.5`. **Both endpoints operator-measured**, 1646.5 deg baseline, ranger not involved | **T3** |
| — | `G` start distance | **1000.0 mm** | M3, measured at the placement RUN-5 starts from | **T3** |
| TBD-08 | `b` ranger offset | −119.1 mm @178 mm; ≈ −90 mm @984 mm | M1 + inference. **Range-dependent — superseded, ranger retired** | T3/T1 |
| TBD-01 | commanded wheel speed | 750 deg/s | design; cruise 761.8 / 754.0 measured (RUN-3) | T2 |
| — | cruise ground speed | 374 mm/s | 750 × 0.4992 | T3 |
| TBD-03 | composite stop `S` | **11.0 mm** | RUN-3: (907.5 − 885.5) deg × k. **n = 1** | T2 |
| TBD-14 | `rel_σ_S` | 9% (prior retained) | n = 1 — not re-fit from a single sample | T0 |
| TBD-04 | motor symmetry | 7.7 deg/s = **1.0%** | RUN-3 cruise means | T2 |
| TBD-11 | control-loop period | **9.4 ms** | RUN-3: 139 samples / 1303 ms; RUN-1 gave 10.18 ms | T2 |
| TBD-17 | heading deviation | **2.54° peak** | RUN-3 under heading hold (12.58° open-loop) | T2 |
| TBD-26 | slip across the stop | 3.3 mm | RUN-3: lag-free endpoints vs odometry | T2 |
| — | start-line repeatability | **8 mm (assumed)** | conservative split of a 13.8 mm bound; **weakest number in the budget** | **T0** |
| — | `σ_k/k` | 0.75% | half the ±1.5% bound from ±12 mm start scatter on the RUN-3 leg | T2 |

**Not bound, and deliberately so:** `T_refresh`, `τ_sensor`, `r_floor`, `σ_n`, `δ_AB` — all
ranger parameters, retired with the effector.

---

## 2. Effector dispositions (Rule 7 — verified, not assumed)

| effector | disposition | evidence |
|---|---|---|
| drive motors C, D | **RETAINED** | regulate at command, 1.0% symmetry |
| IMU | **RETAINED** | heading hold 12.58° → 2.54°; yaw axis = 2, gravity 9670 mm/s² |
| forward ranger A | **DROPPED** | RUN-2: non-monotonic +92 mm while closing, 15% dropouts |
| forward ranger B | **DROPPED** | RUN-3: 196 mm dynamic lag; RUN-4: **+325 mm error in motion**, 302 mm rest spread |
| rear ranger | **DROPPED** | 2000 mm at every sample, every run |
| reflectance sensor | **DROPPED** | serves no catalogued quantity |

**Every sensor except the IMU has dropped out.** REV F is a dead-reckoning system with an
externally measured anchor. That was not the intended design and it is not a comfortable one
— §4 states what it costs.

---

## 3. CMP unit verification

| req | statement | measured | limit | verdict |
|---|---|---:|---:|---|
| CMP-1 | motor L sustains command | 761.8 deg/s | ≥712 | **PASS** |
| CMP-2 | motor R sustains command | 754.0 deg/s | ≥712 | **PASS** |
| CMP-3 | speed symmetry | 1.0% | ≤5% | **PASS** |
| CMP-4 | odometry scale accuracy | 0.75% | ≤1% | **PASS** |
| CMP-5 | braking deceleration floor | ≈7700 mm/s² | ≥1000 | **PASS** |
| CMP-10 | IMU heading drift | <1°/run | ≤1° | **PASS** |
| CMP-11 | loop period | 9.4 ms | ≤25 ms | **PASS** |
| CMP-6,7,8,9 | ranger requirements | — | — | **RETIRED** with the effector |
| CMP-12,13 | rear ranger, reflectance | — | — | **DROPPED** by traceability |
| **CMP-17** *(new)* | the start distance shall be an operator-measured setup constant | 1000.0 mm | — | **PASS** (M3) |

FUN-1, FUN-2, FUN-11, FUN-13, FUN-14 are **retired** with the ranger. FUN-3's wrong-way
operand moves to the IMU; FUN-4's trigger operand is the odometric estimate; SYS-8's
estimate channel is odometric.

---

## 4. Falsify → diagnose → re-derive trail

| run | outcome | root cause | fix |
|---|---|---|---|
| RUN-1 | rover spun at full speed | polarity test used the rangefinder to detect a spin; a spin *does* move the reading | heading-gated probe |
| RUN-2 | ranger A faulty; 12.6° yaw; 59 mm slip | crosstalk; saturation trap; plugging | drop A; regulate + heading hold; passive brake |
| RUN-3 | succeeded; ranger lags 196 mm | sensor cannot track a closing wall | invert channel roles → odometric trigger |
| RUN-4 | aborted by wrong-way guard | guard still read the ranger in motion; `k` was **2.7% wrong** | retire ranger entirely; `k` from a T3 pair |

**Two prior falsifications are on record.** `b`'s GATE A prior of [−40, +80] mm was wrong by
79 mm, and my v4 conclusion that `b` was a constant offset was wrong — it is range-dependent,
and I had tested constancy through a chain that could not detect the difference.

**RUN-4's detuning prevented a contact.** It flew `k` = 0.5030 against a true 0.4992 — a 2.7%
error worth 26 mm at the design point, against a 24 mm predicted gap. It was detuned on
`n_S = 1` grounds, with no suspicion of `k` at all.

---

## 5. What this argument does not cover

- **`S` has one sample.** `rel_σ_S` remains a prior. The verification run gives a second.
- **Start-line repeatability is assumed at 8 mm** and cannot be decomposed from ranger drift
  with the data in hand. If it is the full 13.8 mm, σ_g rises from 11.4 to ~14 mm.
- **There is no independent channel on the scored quantity.** Odometry sets the trigger,
  reports the gap, and has no witness. Wheel slip beyond the measured 3.3 mm is the one
  failure that produces contact, and nothing onboard would see it happen.
