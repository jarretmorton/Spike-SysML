# Anomaly Report AR-001 — CAL-1 (run-20260806-163146)

**Type:** REPORT (static; never edited once written)
**Run:** run-20260806-163146 · duration 30.2 s (host timeout) · 752 events
**Programs consumed to date:** 1 · **Operator measurements consumed:** 0

---

## Summary

CAL-1 executed every segment and violated no physical-plausibility bound. It nonetheless
produced **no usable dynamics data**, because the rover was yawed ~36° off the wall normal
before the approach began, which blinded both forward rangers. The approach therefore
aborted on its own fail-safe after a single control cycle.

The root cause is **a defect in my discovery sequence**, not in the hardware, the sensors,
or the analysis model. The model's predictions were never tested.

---

## A-1 — Forward rangers returned the no-object sentinel · **ESCALATE → root cause found**

**Observation.** From t ≈ 1.9 s onward, ranger A (Port A) read 2000 mm (the no-object
sentinel) continuously; ranger B (Port B) alternated between ~1040–1063 mm and 2000 mm.
At the first approach cycle both were invalid, so `fuse()` returned `both == -1`, FUN-4b
fired, and the loop broke with `fault = 4` before the rover had travelled.

**Plausibility check.** No bound violated. 2000 mm is a legitimate sentinel and was
correctly interpreted as "no object", not as a distance. **The fail-safe worked exactly as
designed** — the rover refused to drive at a wall it could not see. This is the single
piece of good news in the run.

**Root cause.** Discovery nudge 1 commanded both motors "+" to test for opposition. The
motors *are* opposed, so the rover **rotated in place by −35.85°** instead of translating
(`nudge1_dhead_mdeg = −35850`). The sequence then correctly inverted the second motor's
sign and re-nudged straight (`nudge2_dhead_mdeg = +485`, i.e. 0.49° — clean translation),
**but never restored the heading.** Every subsequent segment ran at ~−37°
(`rest_head_mdeg = −37010`, `anchor_head_mdeg = −37026`).

At ~36° incidence an ultrasonic ranger sees a flat wall as a mirror: the ping reflects
away from the receiver and no echo returns.

**Corroboration — three independent channels agree:**

| Evidence | Value | What it shows |
|---|---|---|
| Static burst, squared up (t ≈ 0.65 s) | A = 1020 mm, B = 896 mm | both rangers saw the wall **before** the spin |
| Heading through the whole window | −35.4° … −37.4° | the yaw was never undone |
| B's intermittent recoveries | ~1046–1063 mm | 896 / cos(35.4°) = 1100 mm — the geometric path length at that yaw, so B recovers exactly when the chassis rocks toward normal incidence |

**Disposition: CORRECT AND RE-RUN.** The defect is in my program, so the fix is a
re-derivation of the discovery method, not an empirical tweak.

---

## A-2 — Telemetry throughput is ~30× lower than budgeted · **adapt**

752 events emitted in ~24.5 s of dumping ≈ **31 lines/s (~1.4 kB/s)**. My 1600-line budget
needs ~52 s; the run was given 30 s.

The **priority-ordered dump did its job**: the braking window was emitted first and
survived intact; the static bursts, cruise and creep were still in RAM when the host
stopped the program. Had the dump been in chronological order, the whole run would have
been lost. Retained as a design feature.

**Disposition:** cut the emitted-line budget to ~600 and raise the run timeout to 90 s.

---

## A-3 — Forward rangers disagree by 124 mm at the same position · **log, characterize**

A = 1020 mm, B = 896 mm on the same static burst, squared up. That is almost certainly real
mounting geometry (lateral offset, or a slight relative angle), not noise.

It matters twice over: it biases any fused reading, and it sits uncomfortably close to my
`DISAGREE_MM = 150` fault threshold — a **latent false-trip that would have braked the
rover mid-approach for no reason.** Raised to 300 mm for CAL-2, and the per-ranger offset
is added to the calibration targets.

---

## A-4 — The rear ranger is the best-behaved channel on the rover · **log, exploit**

Ranger E tracked 430 → 473 mm smoothly and monotonically through the return drive, ~1 mm
resolution, no dropouts, while both forward rangers were failing. It is what confirmed the
forward-direction sign independently of the (spin-contaminated) forward deltas.

This promotes CMP-13 from opportunistic to genuinely useful — **provided** its reference
surface stays in range across a 1000 mm traverse (it would run 470 → ~1470 mm, likely past
useful range). Logged on every run; the hand-off point is a CAL-2 output.

---

## A-5 — Possible straightness deficit · **log, chase in CAL-2**

~1.6° of yaw accumulated over ~380 ms of low-speed reverse. Extrapolated naively that is
~28°/m, which would be fatal to STK-4 — but the trace shows the heading *oscillating*
(−35.34° → −37.37° → −36.91°), which is chassis settling and wheel scrub after a brake, not
a steady yaw rate. The clean straight-line datum from the same run is nudge 2:
**+0.49° over ~50 mm.**

Low-speed, short-baseline, transient-contaminated data. Not chased now. CAL-2's full-speed
approach measures straightness over ~550 mm, which is the number that matters.

---

## What was and was not learned

**Bound (durable, tier T2 — cross-confirmed):**

| Finding | Value | Evidence |
|---|---|---|
| Port map | A, B = ultrasonic (forward); C, D = motors; E = ultrasonic (rear); F = none | direct probe, no operator input |
| Motor ceiling | `vmax = 1000 deg/s` | device limit read |
| Motors are physically opposed | `s(C) = −1, s(D) = +1` drives forward | nudge-2 straightness + rear-ranger trend |
| Start-line geometry | forward rangers see ~900–1020 mm | static burst, squared up |
| Telemetry throughput | ~31 lines/s | this run |

**Not bound (all P1/P2 parameters remain open):** cruise speed, odometry scale, the latency
chain, braking deceleration, stop travel, near-range floor, reading noise, straightness,
and `c_us`. **No operator measurement was spent** — OP-MEAS-1 is still available, which is
the thing worth protecting.

---

## Recommendation

**RETEST**, with a re-derived discovery method. Three changes:

1. **Delete discovery entirely.** The port map and motor signs are now known and durable;
   the operator will not rewire between runs. CAL-2 hard-codes them, which removes the
   defective sequence rather than patching it. A short straight confirmation nudge remains,
   with auto-inversion if the forward readings move the wrong way.
2. **Gate on the outcome, not the intent.** Before the approach, CAL-2 requires both
   forward rangers to return a valid reading in [600, 1500] mm from a static burst, and
   `|heading| < 3°`. If either gate fails the run aborts cleanly at the start line and
   says why, instead of driving.
3. **Fit the telemetry to the measured pipe:** ~600 lines, 90 s timeout, accelerometer
   channels emitted only inside the braking window.

Cost: one additional characterization program (2 spent, ~3 planned total). The Calibration
Plan's stated total of 2 programs is superseded; that will be recorded in the Calibration
Report rather than back-edited into the plan.
