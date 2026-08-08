# Anomaly Report AR-004 — VER-1 (runs 173032 and 172922)

**Type:** REPORT (static) · **Programs consumed to date: 6** (CAL-1…4, VER-1a, VER-1b) ·
**Operator measurements: 2**

---

## Summary

Neither verification attempt tested the frozen prediction. Both were ended by defects in my
program before the rover reached the test condition.

**The Verification Plan v1 prediction is therefore UNTESTED, not falsified.** I want to be exact
about that distinction rather than let a void run read as a pass: the estimator never
initialised, the trigger condition was never evaluated, and no number in the frozen prediction
table was exercised. The plan's physics stands unexamined. It does not get to claim a success it
did not earn.

---

## A-11 — VER-1a: `math` module absent on the hub · **my defect**

`ImportError: no module named 'math'`, 0.47 s, no data. The corner-lead term used
`math.sin(math.radians(...))`. This Pybricks build has no `math`.

Replaced with a two-term series: for |yaw| ≤ 8° the error is under 0.0001 mm, so nothing is lost.
Verified against the exact value across 0–15° before re-flashing.

**Cost: one program.** Avoidable — I used a module I had never exercised on this hub, and there
was no reason to need it.

---

## A-12 — VER-1b: a single outlier ended the run · **my defect**

**Symptom.** Aborted at t = 1021 ms with fault 17 (closing check), ~660 mm from the wall.

**What actually happened.** Ranger A was tracking correctly. Over t = 831–1011 ms it fell
smoothly and monotonically: 960, 952, 944, 942, 929, 920, 915, 901, 891 — no dropouts, no
reversals. Odometry (354°) and ranger B (877 → 716, a 161 mm closure) both confirm the rover
travelled ~166 mm. Then at t = 1021 ms A returned a single reading of **1033**, and the run died.

**Root cause.** My closing check —

```
if t - t0 > CLOSING_MS and a < 1900 and a > a0 - CLOSING_MIN_MM:
    fault = 17
```

— was intended as a one-time "is the rover actually driving toward the wall" sanity test. I wrote
it as a **condition re-evaluated on every loop, with no debounce, on the noisiest channel on the
rover.** After 400 ms, any single spurious high reading from ranger A ends the run, regardless of
how well it had been tracking a millisecond earlier. A had already closed 134 mm; the check
should have latched satisfied long before.

This is the same class of error as AR-002: a guard written without asking what a single bad
sample does to it.

**Correction.** The check is now **one-shot and latched**, and evaluated on **ranger B and the
encoders — never on ranger A**. It latches when the wheels have turned ≥150° *and* B has closed
≥40 mm, and only faults if the wheels have not turned or nothing has latched within 1.5 s.
Replayed against VER-1b's own B and odometry data, it latches correctly.

---

## A-13 — Ranger A has a bad zone around 840–990 mm · **characteristic, log**

Not a defect, a property, and it is why the check must never have been on A:

| Evidence | Behaviour |
|---|---|
| CAL-4 creep (20 ms loop, 140 mm/s) | one sentinel dropout at A ≈ 840 |
| VER-1b approach (10 ms loop, ~470 mm/s) | clean 960 → 891, then one outlier at 1033 |
| VER-1b after braking, stationary at ~834 mm | periodic ~30 ms valid / ~50 ms sentinel, plus spurious 1272–1274 |
| CAL-4 static bursts at 1024, 387, 225, 161, 116 | spread ≤ 5 mm — clean |

A is clean at ~1000 mm and clean at ≤ 400 mm, and unreliable in between. **This does not touch
the frozen prediction**, because the fused estimator initialises at A ≤ 250 — below the bad zone
— and the far field is now guarded by B, which has been reliable at cruise in every run.

**Still unobserved:** ranger A's behaviour at cruise speed below 250 mm. CAL-4 characterised that
region at 40–140 mm/s only. This is the residual risk VER-2 carries, and the fused estimator,
the 90 mm propagation limit and the odometry budget are the three independent things standing
between it and the wall.

---

## Disposition

**RETEST as VER-2.** The frozen prediction is re-issued **unchanged** in Verification Plan v2 —
no parameter was falsified, so re-deriving one would be fabricating a response to evidence that
does not exist. What changes is the program: the closing check is corrected, and the estimator's
propagation limit rises from 60 mm to 90 mm so that a patchy ranger below 250 mm degrades into
dead reckoning rather than an abort. 90 mm of odometry at ±6% is ±5.4 mm, which the margin
absorbs.

Two programs spent on two defects of mine, no contact, no damage, and the interlocks stopped the
rover safely both times.
