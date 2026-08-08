# Anomaly Report AR-002 — CAL-2 (run-20260806-164102)

**Type:** REPORT (static; never edited once written)
**Run:** run-20260806-164102 · 90.5 s (host timeout during dump) · 846 events
**Programs consumed to date:** 2 · **Operator measurements consumed:** 0

---

## Summary

CAL-2 passed its start-line gates, confirmed the hard-coded port map and motor signs from
motion, and drove a full-speed approach. It produced the first real dynamics data of the
programme. It also exposed **three defects and one physical limitation**, one of which is
my program corrupting the measurement it exists to take.

The approach terminated early on the ranger-disagreement guard rather than on the trigger,
so the composite stop-travel figure below is valid but contaminated.

---

## A-6 — Telemetry writes on the critical path delayed the brake by 32 ms · **ESCALATE**

**Observation.** The trigger condition was met at t = 3100 ms. `brake_cmd` is stamped
**3132 ms**. Between them my program executes six `emit()` calls. Sampling then stops
entirely from 3132 to 3253 ms — a 121 ms gap with no captured samples — which is consistent
with a `stdout.write` blocking on a full BLE transmit buffer.

**Consequence.** At the measured cruise speed of 421 mm/s, **32 ms is 13.5 mm of extra
travel** before braking begins. The target final gap is of order 15–30 mm. My own logging
was about to consume half the budget, and it would have done so *silently* — the composite
trigger-to-rest measurement would have absorbed it and been applied to a flight program
that logs nothing there.

**Root cause.** At Gate A I wrote that stdout must stay off the hot path, then placed six
writes in the single most timing-critical spot in the program. The rule was right; I did
not apply it where the loop *ends*, only where it iterates.

**Corrective action (CAL-3).** `m1.brake(); m2.brake()` is now the first statement after the
loop breaks, before any assignment or write. All trigger-instant values are stashed in
variables and emitted after the settle window has completed.

---

## A-7 — The rover yaws −9° over a 208 mm approach · **ESCALATE**

| Phase | Heading change | Wheel differential | Explained? |
|---|---|---|---|
| Cruise, 123 mm | −1.1° → −3.7° (−2.6°) | 275 vs 283 deg → 3.5 mm | **yes**, at a ~77 mm track |
| Braking, ~28 mm | −3.7° → −9.2° (−5.5°) | 61 vs 66 deg → 2.2 mm | **no** — accounts for only ~1.6° |

Two distinct mechanisms. Cruise yaw is an ordinary ~3 % wheel-speed differential. Braking
yaw is not: the heading keeps changing for ~110 ms *after* the encoders have stopped
(`al` reaches 507 by t = 3253, heading is still moving at 3363). **The chassis is slewing
while the wheels are locked** — a skid, not a steering error.

**Why this matters.** At −9° a 90 mm half-width chassis presents a front corner 14 mm ahead
of its axis. That is the entire gap budget, spent on pointing the wrong way.

**Structural finding.** At a commanded 1000 deg/s the speed controller sits *at* its
ceiling, so it has no headroom left to correct heading. **STK-3 and STK-4 are in direct
tension at exactly the operating point the task demands.** This was latent in the
specification and only hardware revealed it.

**Corrective action (CAL-3).** A closed-loop heading hold that trims **only the leading
wheel downward** — the faster wheel is slowed, the other stays at `VMAX`. The drive is
still commanded at maximum and the fastest wheel still runs at maximum, so STK-3 is
preserved in the sense that matters; the trim is bounded at 12 %. Braking skid is left
alone for now: much of it may be the rover *already* carrying a yaw rate at brake time, so
heading hold is tested first before anything more invasive is attempted.

Safety on the new controller: the correction sign is derived from CAL-2 data (m2 leads,
heading goes negative), auto-inverts once if the error grows past 6°, and the approach
aborts outright past 15° where the rangers are known to fail.

---

## A-8 — Ranger A is not trigger-grade · **demote**

During cruise, ranger A tracked the wall at an apparent 336 mm/s against B's true
421 mm/s, then produced a single gross outlier — **1269 mm when the truth was ~820 mm** —
which tripped the 300 mm disagreement guard and ended the approach. After braking it
dropped to the 2000 mm sentinel repeatedly.

Ranger B was clean and monotonic across both runs. A's offset from B is stable at
~130–145 mm whenever both behave, independent of distance and of yaw, so it is a fixed
mounting offset and remains useful as a cross-check.

**Corrective action.** B becomes the trigger channel; A becomes cross-check only, with
fallback to A if B goes invalid. **Disagreement now degrades rather than aborts** — an
abort on the strength of the channel known to be worse is the wrong failure mode. Hard
abort is reserved for both-invalid. A wheel-odometry travel interlock is added as the
independent backstop, now that the odometry scale is bounded.

---

## A-9 — Fault latch aborted the creep · **fix**

`fault = 3` from the approach was never cleared, so the creep loop's own
`if fault != 0: break` fired after its first stage. The rover parked at a B-reading of
245 mm instead of the 130 mm anchor. Trivial defect; the creep now carries its own fault
variable.

---

## A-10 — Ranging and odometry scales disagree by 16 % · **log, resolve at OP-MEAS-1**

| Segment | Speed | Implied mm/deg |
|---|---|---|
| Confirmation nudge | ~110 mm/s | 0.46 |
| Cruise | 421 mm/s | 0.441 |
| Creep | ~88 mm/s | 0.513 |

Either the wheels slip ~14 % at cruise, or the ranging channel has a scale error, or both.
**No onboard channel can separate them** — that is exactly the trusted-reference question,
and it resolves at OP-MEAS-1 rather than by picking the answer I prefer.

**It matters less than it looks.** The final-gap estimator uses the at-rest ranging reading
plus an offset anchored at the operating point, and the trigger is sized from a composite
trigger-reading-to-rest travel **measured in range-units on the trigger channel itself**.
Neither path passes through the odometry scale. `k_odo` is carried as a T3 range, not
collapsed to a single value, and it is used only for the protective interlock — which is
sized with the *largest* credible value so it stays protective under either hypothesis.

---

## What was bound

| Quantity | Value | Tier | Evidence |
|---|---|---|---|
| Cruise wheel speed | 942 / 969 deg/s at 1000 commanded | T2 | encoders, 292 ms |
| Cruise ground speed | 421 mm/s | T2 | ranger B regression |
| Trigger → rest travel (composite) | 59 mm range-units — **includes 13.5 mm of logging delay** | T2, contaminated | B: 696 → 637 |
| Post-brake wheel rotation | 63.5 deg | T2 | encoders |
| Track width | ~77 mm | T3 | cruise yaw vs wheel differential |
| A-to-B fixed offset | ~130–145 mm | T2 | both runs, all distances |
| `k_odo` | 0.44 – 0.51 mm/deg | T3 range | three segments, unresolved |

The composite stop-travel figure is the one the design needs and it is **not yet clean**.
CAL-3 re-measures it with the logging delay removed and heading held.

---

## Recommendation

**RETEST as CAL-3.** Five changes: brake before logging; closed-loop heading hold; ranger A
demoted with degrade-not-abort; fault latch fixed; and telemetry re-architected to
**aggregate on-hub and emit scalars** rather than traces — loop-period statistics, ranging
refresh interval, A-dropout count, heading extremes, settle time and static-burst noise are
all computed on the hub, which costs ~25 lines instead of ~750 for the same information.
Trigger moved from 450 mm to 250 mm to characterize nearer the operating point while
staying safe under the worst prior on `c_us`.

Cost: a third characterization program. **OP-MEAS-1 remains unspent**, which is the asset
worth protecting — it is requested once CAL-3 leaves the rover at the anchor.
