# Verification Plan v2 — Wall-Approach Rover

**Type:** PLAN · **Supersedes:** v1 (retained) · **Status: FROZEN.**
**Reason for re-issue:** VER-1a and VER-1b were voided by program defects (AR-004) before the
test condition was reached. No parameter was falsified.

---

## 1. What changed from v1

**The prediction has not changed.** Not one number in the table below differs from v1. That is
deliberate: nothing in the physics was tested, so there is no evidence to re-derive against.
Adjusting the prediction now would be tuning it to a run that never exercised it.

**The program has changed, in exactly two places:**

| Change | Why |
|---|---|
| Closing check is one-shot and latched, evaluated on ranger B and the encoders, never on ranger A | A single ranger-A outlier ended VER-1b while A was tracking correctly (A-12) |
| Estimator propagation limit 60 mm → 90 mm | A's behaviour at cruise below 250 mm is unobserved; a patchy channel should degrade to dead reckoning, not abort. 90 mm of odometry at ±6% is ±5.4 mm |

---

## 2. THE FROZEN PREDICTION (unchanged from v1)

| Quantity | Predicted | Acceptance band |
|---|---|---|
| **Final gap, front corner to wall** | **30.8 mm** | 0.8 … 60.8 mm |
| Final gap, chassis axis to wall | 35.8 mm | — |
| Corner lead from residual yaw | 5.2 mm | — |
| Ranger A reading at the trigger | 92 | 85 … 99 |
| Composite trigger→rest travel `d_total` | 45.0 mm | 21 … 69 mm |
| Cruise ground speed | 470 mm/s | 440 … 505 mm/s |
| Wheel rotation after brake | 30 deg | 20 … 45 deg |
| Loop period | 10.0 ms | 9 … 12 ms |
| Heading at the trigger | 0.1° | ≤ 2.0° |
| Heading at rest | 3.3° | ≤ 6.0° |
| σ of the final gap | 10.0 mm | — |
| P(contact) this run | 0.0010 | — |

Roll-up at the committed configuration: **20 PASS, 2 PENDING, 0 FAIL** (pending: STK-2 and SYS-8,
which close only against operator ground truth).

---

## 3. New predictions specific to this run

These did not exist in v1 and are added because VER-1b produced new evidence about ranger A:

| Quantity | Predicted | Meaning if violated |
|---|---|---|
| Estimator initialises (A ≤ 250 twice, within 30 mm) | yes | A is unusable below 250 at cruise — architecture must change |
| Accepted readings after initialisation | ≥ 15 | A is patchy at cruise; check `prop_max` |
| Max propagation without an accepted reading | ≤ 30 mm | approaching the 90 mm limit means A is mostly dead below 250 |
| Stale-flagged samples | 0 | the freeze mode has appeared at cruise |
| `closing_ok` latched | 1 | the corrected far-field check did not latch |

---

## 4. Acceptance criteria

VER-2 **confirms** if: no contact; `d_total` within 21–69 mm; operator-measured gap within
0.8–60.8 mm; onboard estimate within 10 mm of ground truth (SYS-8); heading, loop period and
cruise speed inside band; no plausibility bound violated.

## 5. Diagnosis tree if falsified

As Verification Plan v1 §5, plus:

| Symptom | Responsible parameter | Action |
|---|---|---|
| Estimator never initialises | ranger A unusable below 250 mm **at cruise** — the last untested assumption | fall back to the ranger-B + odometry-coast architecture; expect a larger achievable gap (~60 mm) and say so |
| `prop_max` > 60 mm | A patchy at cruise | re-bind A's cruise availability; add its propagation error to the budget; re-solve the trigger |
| Contact | — | **HALT.** No operation runs until closed. |

## 6. Operator input

**OP-MEAS-3** once VER-2 has stopped, before the rover is moved: distance from the front-most
point of the rover to the wall, perpendicular. Closes SYS-8 and the STK-2 objective at Gate C.
