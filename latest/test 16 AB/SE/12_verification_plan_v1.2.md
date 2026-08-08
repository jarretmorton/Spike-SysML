# VERIFICATION PLAN v1.2 — WallStop

**Document** VP-WALLSTOP · **Version 1.2** · **Type: PLAN** · **PREDICTIONS ONLY**
**Supersedes v1.1 by re-derivation. v1.0 and v1.1 remain frozen on the record.**

> **FROZEN.** Output of `wallstop_model_revC.py` at the T4-anchored configuration. No result may edit this version.

## 1. Version trail

| | v1.0 | v1.1 | v1.2 |
|---|---|---|---|
| Absolute channel | ranger A zero | ranger A travel + odometry | **odometry only** |
| Predicted gap | 37.0 mm | 23.0 mm | **23.0 mm** |
| Outcome | FALSIFIED — measured 222 mm | FALSIFIED — failsafe fired at 700 mm | — |
| Root cause | unstable ranger zero (AR-003) | spurious ranger sample tripping the cross-check (AR-004) | — |

The predictive chain is **unchanged** from v1.1 — it has never been tested, because C3 aborted before reaching it. What changed is that the ranger no longer participates in, or can abort, the control path.

## 2. Configuration

`operation_program_v3.py`, sha256 `d5583d2c03d5219f`.

| Parameter | Value | Tier |
|---|---|---|
| `S` start-line gap | 1000.0 mm | **T4 operator-measured** |
| `t_eff` | 0.09239 s (Δ = 43.7 mm at 473 mm/s) | **T4-anchored** |
| `G` target gap | 23.0 mm (= 3σ, SYS-1) | analysis |
| `k_travel` | 0.482 mm/deg | T3 |
| Ranger A | **monitor only — gates nothing** | withdrawn |

**Trigger:** `g_est = S − odometry_travel`; brake when `g_est ≤ G + v·t_eff`.
**Failsafes:** encoder L/R divergence >60 mm · heading >15° · odometry floor at S−15 · watchdog 6 s · no-motion abort. **No ranger-based gate.**

## 3. THE FROZEN PREDICTION

| Quantity | Predicted |
|---|---|
| Approach speed | 473–498 mm/s (adaptive) |
| Δ, post-trigger travel | 43.7 mm at 473 mm/s |
| Trigger at odometry | **933.3 mm** |
| **FINAL GAP** | **23.0 mm** |
| σ_gap | **7.49 mm** |
| Contact margin (3σ) | 22.5 mm · SYS-1 margin **+0.5 mm** |
| P(contact) per run | 1.1 × 10⁻³ |

**1σ: 15.5 – 30.5 mm. 3σ: 0.5 – 45.5 mm.**

### Falsification criteria
| Outcome | Reading |
|---|---|
| gap ∈ 15.5–30.5 mm **and** `trig_reason = 1` | **held** |
| ∈ 0.5–45.5 mm, reason 1 | held at 3σ |
| outside 0.5–45.5 mm, or any contact, or reason ≠ 1 | **FALSIFIED** |

## 4. Requirement changes

**SYS-8 descoped to PARTIALLY MET (rev D).** No independent *distance* channel exists — three ultrasonic sensors, none trustworthy. Retained cross-checks: left/right encoder divergence and gross-heading abort. Recorded as an architecture limitation, closed on evidence in the Verification Report, not asserted away.

**CMP-1…4** (ranger offset, refresh, clamp gate) become **N/A at rev D** — the effector they trace to no longer carries a requirement. Absence by traceability, applied to a sensor that failed its way out of the design.

## 5. Honest weaknesses

1. **No independent distance check.** If odometry is wrong, nothing notices. Mitigated by the T4 end-to-end anchor and a deterministic mechanism; not eliminated.
2. **σ_S = 5 mm is an assumption.** Now the largest term, and unmeasured.
3. **SYS-1 margin +0.5 mm** — at the floor, deliberately, because STK-5 asks for the minimum gap.
4. **The chain is being tested for the first time.** v1.1's prediction was never exercised.
