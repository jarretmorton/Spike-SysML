# FINAL REPORT — Wall-Approach Rover
**Document:** `27_final_report.md` · **Type: REPORT** (static)
**Phase:** Operation close-out · **Program:** `21_revF_program.py`, locked, md5 `fb8f338f6b11e57f4c4e513db6c683ce`

---

## 1. RESULT

**Five runs, five full stops, zero contact.** Gaps 18–37 mm, mean 26.6 mm.

| run | **predicted** (frozen VP v3) | **estimated** (frozen onboard) | **measured** (operator) | delta (meas − est) |
|---:|---:|---:|---:|---:|
| 1 | 19.8 mm | 19.42 mm | 22 mm | **+2.58** |
| 2 | 19.8 mm | 20.64 mm | 34 mm | **+13.36** |
| 3 | 19.8 mm | 19.42 mm | 22 mm | **+2.58** |
| 4 | 19.8 mm | 20.40 mm | 18 mm | **−2.40** |
| 5 | 19.8 mm | 21.13 mm | 37 mm | **+15.87** |
| | | mean 20.20, sd **0.76** | mean 26.60, sd **8.35** | mean **+6.40**, sd 7.82 |

### Did the committed prediction hold?

**Partly, and the part that failed is the more interesting one.**

- **The hard constraint held.** No contact on any run. SYS-1 is satisfied in operation as it
  was at verification.
- **The prediction was biased low by 6.4 mm** and, far more importantly, **understated the
  run-to-run spread by an order of magnitude**. VP v3 predicted σ_g = 1.03 mm. The measured
  spread was **8.35 mm — 8× wider**.
- **SYS-8 failed on 2 of 5 runs** (13.36 and 15.87 mm against a 10 mm limit). It was closed
  at GATE C on a 0.19 mm verification error. That closure did not generalise.

---

## 2. RECONCILIATION — where the 6.4 mm and the 8.35 mm came from

The drivetrain did not vary. Across all five runs the odometry at rest spanned **3.5 deg =
1.72 mm**, and the onboard estimates spanned 1.71 mm. The stop distance held at
10.30–11.29 mm. **The 19 mm spread in the result is not in the rover.**

Back-solving each run's start position from its measured gap and its own odometry:

| run | implied start |
|---:|---:|
| 4 | 997.60 mm |
| 1, 3 | 1002.58 mm |
| 2 | 1013.36 mm |
| 5 | 1015.87 mm |

Mean **1006.4 mm**, sd **7.8 mm**, range **18.3 mm** — against a hard-coded anchor of
1000.0 mm. **The entire operation-phase error, bias and scatter alike, is start-line
placement**, and it maps 1:1 onto the delta column.

### 2.1 The verification sample did not span the operating condition

| phase | implied start positions | sd |
|---|---|---:|
| verification (RUN-5, 6, 7) | 1000.0, 1001.0, 999.8 | ~0.6 mm |
| operation (runs 1–5) | 997.6 … 1015.9 | **7.8 mm** |

Placement during verification was **13× tighter** than during operation. I measured the
start distance before RUN-5, and asked for a gap measurement after each verification run —
which plausibly made those resets more deliberate than the five rapid operation resets.

**This is the substantive failure of the campaign, and it is mine.** I applied
test-like-you-fly rigorously to the *program* — identical control loop, identical hot path,
byte-for-byte through seven runs — and not at all to the *operating procedure around it*. I
verified under a reset regime I had inadvertently made more careful by asking for
measurements, then flew under a different one. σ_g = 1.03 mm was a real measurement of a
condition that did not recur.

The Calibration Report flagged start-line repeatability as "the weakest number in the
budget" and assigned it 8 mm. **The true value was 7.8 mm.** That original estimate was
right; I then talked myself out of it at VP v3 on the strength of three runs that happened
to agree to ±1 mm, and adopted 1.03 mm instead. The conservative prior was correct and I
replaced it with a better-looking number from an unrepresentative sample.

### 2.2 What actually prevented contact

At GATE C I declined to tighten `TRIG_GAP` from 32 to 22 mm — an ~8 mm design that was
~17σ safe on the σ I then believed. On the σ that turned out to be real, it was 1σ. Had I
taken it, the five gaps would have been 12, 24, 12, **8**, 27 mm. Still no contact, but the
margin would have been a single sigma of a variance I had not measured, and one placement
excursion 18 mm the *other* way would have put the rover into the wall.

The reason for declining was not insight into placement. It was refusing to re-tune on a
good result after refusing to re-tune on three bad ones. **The discipline paid, not the
analysis.**

### 2.3 The architectural mistake this exposes

The forward ranger was retired at REV F because it failed in motion — 196 mm dynamic lag,
+325 mm in-motion error, crosstalk. Those failures were real and disqualifying **for the
trigger**. But the ranger's static, motors-off reading was its one good mode (12 samples,
11 mm spread, zero rejects), and that reading is the only channel on the rover that could
have **observed the start position**.

By dropping it entirely I removed the sole witness to the quantity that then dominated the
result. The right architecture was almost certainly:

> **static ranger reading as the per-run anchor, odometry for everything in motion.**

That would have tracked placement run by run and collapsed most of the 8.35 mm scatter,
leaving only the ranger's static noise (~3 mm) plus a systematic offset. I retired an
effector for failing in a role it should never have held, and lost its good role with it.
Supporting evidence: RUN-3 and RUN-4's static readings differed by 13.75 mm, which I
attributed to a mix of placement and sensor drift — on the operation data, placement alone
accounts for it.

---

## 3. Requirement outcomes in operation

| req | GATE C verdict | operation outcome |
|---|---|---|
| SYS-1 no contact | PASS | **PASS — 5 of 5** |
| SYS-3 objective (gap) | PASS, 18.0 mm | mean 26.6 mm, min 18 mm |
| SYS-4 max speed in regulation | PASS | PASS — 750–754 deg/s every run |
| SYS-5 complete stop | PASS | PASS — `S` 10.30–11.29 mm |
| SYS-6 heading ≤ 5° | PASS | PASS — peak 4.23 mm on run 2, rest ≤ 2.4° |
| SYS-7 degraded stop | PASS | not exercised — no guard fired in any run |
| **SYS-8 estimate error ≤ 10 mm** | **PASS (0.19 mm)** | **FAIL on runs 2 and 5** |

SYS-8 is the requirement to carry forward. It was verified honestly, on ground truth, at the
operating point — and still failed in service, because the verification sample did not span
the operating variance. Verification at a point is not verification over a distribution.

---

## 4. Scores

| metric | value |
|---|---|
| characterization program runs | **7** (RUN-1…4 calibration, RUN-5/6/7 verification) |
| outside-input actions | **6** (M1 178, M2 775, M3 1000, M4 52, M5 43, M6 18) |
| operation runs with no contact | **5 of 5** |
| closeness | mean **26.6 mm**, min 18 mm, max 37 mm |

The run and measurement counts overran the two-and-two I planned at GATE A. The overrun is
traceable and, with one exception, bought something: RUN-1 a discovery defect, RUN-2 a faulty
ranger and the saturation trap, RUN-3 the dynamic-lag finding, RUN-4 the `k` error that would
have caused contact, RUN-5/6 two falsified predictions each carrying a systematic toward the
wall. The exception is **VP v2**, which spent a run and a measurement testing an anchor I had
derived by mixing motion profiles — an error I could have found for free in data I already
held.

---

## 5. Falsification trail

| artifact | prediction | outcome | responsible parameter |
|---|---|---|---|
| VP v1 | 35.3 mm | falsified — 15.46 mm estimate error | `k` high 1.63% (mixed-run start assumption) |
| VP v2 | 32.1 mm | falsified — 12.05 mm estimate error | anchor 12 mm low (my profile-mixing artifact) |
| VP v3 | 19.8 mm | **held** at verification, 0.19 mm | — |
| VP v3 in operation | 19.8 mm ± 1.03 | **spread falsified** — σ 8.35 mm | start-line placement, unobserved by design |

Two priors were falsified outright: `b` ∈ [−40, +80] mm was wrong by 79 mm, and my v4
conclusion that `b` was a constant offset was wrong. Both were caught only by operator
ground truth, and neither was reachable from onboard data — every onboard channel was
self-consistent with the wrong value.

---

## 6. What I would do differently

1. **Keep the ranger as the static anchor.** Retire it from the trigger, not from the rover.
2. **Treat the operating procedure as part of the article under test.** My verification
   changed the operator's behaviour by asking for measurements, so it measured a condition
   that operation did not reproduce.
3. **Do not replace a conservative prior with a tighter number from a small unrepresentative
   sample.** The 8 mm placement prior in the Calibration Report was right; three agreeing
   runs talked me out of it, and the truth was 7.8 mm.
4. **Distrust a σ estimated from n = 3** when the dominant term is something the system
   cannot observe.

---

## 7. Locked program

```python
# LOCKED OPERATION PROGRAM -- REV F / Verification Plan v3
# md5 fb8f338f6b11e57f4c4e513db6c683ce, 241 lines, unchanged across all five runs

G_MM          = 1000.0    # operator-measured start distance (M3)
K_MM_PER_DEG  = 0.49066   # fast profile, fitted on RUN-5 and RUN-6
TRIG_GAP      = 32.0      # gap = TRIG - 12.16 mm, solved against 3*sigma_g
P_ML, P_MR    = Port.C, Port.D
SGN_L, SGN_R  = -1, 1     # translating configuration, confirmed over three runs
SPEED_CMD     = 750       # below saturation so both controllers regulate
HEAD_GAIN     = 7.0       # deg/s per deg, from a 0.3 s closed-loop time constant
CORR_MAX      = 120.0
HEAD_ABORT    = 15.0      # gross-yaw guard
TRAVEL_MARGIN = 40.0      # absolute travel cap beyond the trigger
LOOP_MS       = 10
```

Control law, in full: reference odometry before any motion; measure the heading-correction
sign with a yaw probe and undo it; drive both motors at 750 deg/s with proportional heading
hold `cmd = 750 ∓ 7·θ` clamped to ±120; each loop compute `d_go = 1000 − travel·k` and stop
when `d_go ≤ 32`; brake passively; report `g_est = 1000 − odo_rest·k`. Guards: gross yaw,
travel cap, time limit. No forward ranger is constructed. The full source is
`21_revF_program.py`.
