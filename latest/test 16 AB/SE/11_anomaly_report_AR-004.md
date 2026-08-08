# ANOMALY REPORT AR-004 — ranger A is not a usable channel

**Document** AR-WALLSTOP-004 · **Type: REPORT (static)** · Run `run-20260807-124304` (C3) · Free analysis

**Outcome: the divergence failsafe fired at 673 ms and stopped the rover at ~700 mm. `trig_reason = 2`.** VP v1.1 listed "trigger reason ≠ 1" as a falsification criterion, so **VP v1.1 is falsified** — but not by the predictive chain, which was never reached.

## 1. What happened

| t (ms) | ranger travel | odometry | divergence |
|---|---|---|---|
| 773 | 101.0 | 106.5 | −5.5 |
| 950 | 172.0 | 193.3 | −21.3 |
| 1082 | 233.0 | 257.1 | −24.1 |
| **1093** | **−158.0** | 262.9 | **−420.9 → brake** |

Ranger A read 787 mm at t = 1082 and **1178 mm eleven milliseconds later** — a +391 mm jump while the rover was closing on the wall. The failsafe did exactly what it was designed to do. It then recovered to 768, then dropped out to 2000.

**The failsafe behaved correctly and the outcome is still a failure**: a single spurious sample cost a run. A gate that aborts on one bad reading from a channel that produces bad readings is not protection, it is a second failure mode.

## 2. The channel's cumulative record

| # | Run | Failure mode |
|---|---|---|
| 1 | C1 | clamps at a constant 40 mm instead of dropping out |
| 2 | C2 | yaw-induced freeze — 92 mm held for 60 consecutive samples |
| 3 | C2 | zero wrong by ~190 mm for the entire run |
| 4 | C3 | travel scale wrong by **9.4 %** (0.906 vs 0.991 in C2) |
| 5 | C3 | single-sample spike of +391 mm in 11 ms |
| 6 | C3 | dropout to 2000 mm at rest; rest spread 49 mm |

**Six distinct failure modes across three runs. No property of this channel — zero, scale, or individual sample — survived testing.** Rev C was built on the one property that looked sound after C2, relative travel at 0.86 %; C3 broke that too.

**This also settles AR-003's open question.** C3's start reading was 1020 mm and C1's 1015 mm, both consistent with a ~1000 mm line. C2's 817 mm was the outlier. So ranger A did not suffer a permanent zero shift from the wall impact — it is **intermittently grossly wrong**, which is worse: a shifted constant can be recalibrated, an intermittent one cannot.

## 3. Disposition — rev D

**Ranger A is removed from the control path entirely.** It is logged as a monitor and gates nothing. Pure odometry dead-reckoning from the operator-measured start line.

**SYS-8 cannot be satisfied as written.** The rover carries three ultrasonic sensors and not one of them is trustworthy enough to gate a stop 23 mm from a wall. That is an architecture limitation, recorded rather than papered over. The surviving independent cross-check is the **left/right encoder pair**, which detects a wheel or encoder fault, plus a gross-heading abort. Neither is an independent *distance* channel. SYS-8 is descoped on evidence at rev D and closed as **PARTIALLY MET** in the Verification Report.

## 4. Why odometry alone is defensible

It is not a fallback of last resort; it is the best-evidenced element in the programme:

- **Validated end-to-end against ground truth.** `S − odo_trigger − Δ = 1000 − 734.3 − 43.7 = 222.0 mm` against 222 mm measured.
- **The anchor absorbs every systematic at once.** Acceleration slip, braking skid and odometry scale error all fold into the single calibrated `t_eff`, provided the profile repeats — and it does: same commanded speed, same acceleration limit, same distance, every run.
- **Deterministic mechanism.** A shaft encoder has no echo path to lose, no dead zone, and no multipath.
- **Repeatable in the data.** Odometry-measured braking travel across four stops: 13.7, 13.5, 14.9, 14.0 mm — sd 0.6 mm.

## 5. Residual risk, stated plainly

With the ranger gone there is **no independent check on the distance to the wall**. If the odometry chain is wrong, nothing on the rover will notice — exactly the situation that produced the 197 mm error in C2, except that there the faulty channel was the one being trusted. The mitigation is that the chain is T4-anchored end-to-end and the mechanism is deterministic; the exposure is that placement repeatability (σ_S = 5 mm, an assumption) is now the largest term and is unmeasured.

## 6. Recommendation

1. Issue **VERIFICATION PLAN v1.2** with rev D and a new frozen prediction.
2. Take **one** more verification run. VP v1.1's chain was never exercised, so this is the first real test of it.
3. Take the final gap measurement to close the objective at the operating point.

Cost: 4 characterisation runs and 3 outside-input actions in total. Both above the GATE A budget. The overrun is entirely attributable to a sensor that failed six different ways, and I would rather report an honest overrun than run five scored runs on an untested configuration.
