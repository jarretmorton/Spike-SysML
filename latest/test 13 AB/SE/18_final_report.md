# FINAL REPORT — Wall-Approach Rover

**Type:** report (static) · Closes the operation phase
**Locked program:** `15_rover_wallstop_LOCKED_v3.py`, flashed unchanged before each of the five runs
**Frozen prediction under test:** Verification Plan v3.0 — 26.0 mm, 3σ band 10.7–41.3 mm

---

## 1. Result

**5 of 5 runs stopped with no contact.** Measured gaps: **24, 27, 21, 21, 19 mm** — mean 22.4 mm,
sd 3.13 mm, all five inside the frozen band. The committed prediction held.

| Scored quantity | Result |
|---|---|
| Characterization program runs | **5** (CAL-1, CAL-2, VER-1, VER-2, VER-3) |
| Outside-input actions | **2** (M1, M2) |
| Runs with no contact | **5 / 5** |
| Closeness | mean **22.4 mm**, range 19–27 mm |

## 2. The chain: predicted → estimated → measured

| Run | Predicted (v3.0, frozen) | My estimate (frozen pre-measurement) | Measured | Δ (est − meas) | `r_rest` |
|---|---|---|---|---|---|
| 1 | 26.0 mm | 25.97 mm | **24 mm** | +1.97 | 40.00 *(clipped)* |
| 2 | 26.0 mm | 27.26 mm | **27 mm** | **+0.26** | 44.00 *(valid)* |
| 3 | 26.0 mm | 23.84 mm | **21 mm** | +2.84 | 40.86 |
| 4 | 26.0 mm | 24.34 mm | **21 mm** | +3.34 | 41.00 |
| 5 | 26.0 mm | 24.40 mm | **19 mm** | +5.40 | 41.00 |

Mean Δ = **+2.76 mm, sd 1.88, and positive on every single run.**

## 3. Reconciliation of the systematic

Two systematics, and they point in the same direction.

**(a) The rover stopped 3.6 mm closer than commanded** (22.4 mm measured against a 26.0 mm target).
Well inside `m_contact` = 15.3 mm, so the no-contact case was never threatened, but it is a real bias
and it is *toward* the wall.

**(b) My estimates were high on all five runs**, which is the more interesting failure because I
predicted its sign before seeing the data. At close-out I wrote that the static readings sitting
~1 mm above the clip floor "may be floor-limited and biased upward… if so, the true clearances are
smaller than I've committed — and the errors would be one-directional, not scattered." They were.

The mechanism is confirmed by the data rather than asserted:

| `r_rest` above the 40 mm floor | Δ (est − meas) |
|---|---|
| **+4.00 mm** (run 2, comfortably valid) | **+0.26 mm** |
| +1.00, +1.00, +0.86 mm (runs 5, 4, 3) | +5.40, +3.34, +2.84 mm |
| 0.00 mm (run 1, clipped, odometric only) | +1.97 mm |

The single run whose static reading was genuinely clear of the floor was accurate to **0.26 mm**. The
four sitting on the floor averaged **+3.39 mm** of error. The estimator was not noisy — it was
saturating, and a saturating sensor reports a floor, which reads as "further away than I am."

**So the sensor's usable floor is effectively ~44 mm of reported range, not the 40 mm vendor figure.**
Translated through `B_OFF` = −17 mm, an independent onboard estimate requires a clearance of **≥27 mm**
— above the 26 mm target chosen to obtain it. The v3.0 target choice therefore failed on its own
terms, by about 1 mm.

## 4. What this says about the three declared failures

**SYS-7 — correctly declared FAILED at GATE C.** The declaration was not defensive paperwork: the
estimator did exactly what the report said it would, and the operator's measurements were the only
thing that could reveal it. Closing SYS-7 as passed on the odometric channel would have shipped a
tautology, and the +2.76 mm bias would have gone unrecorded.

**OBJ-1 — the 7.7 mm violation bought less than intended.** 26 mm over 20 mm was chosen to buy
observability. It bought it on one run in five. Had I known the effective floor was 44 mm, the honest
options were ~28 mm (observable, worse score) or ~20 mm (unobservable, better score) — and 26 mm was
the one choice that got neither cleanly. That is a genuine error of judgement, not a trade-off, and
it cost roughly 3 mm of closeness for nothing.

**CMP-17 — failed as predicted, and now quantified.** v2.0 predicted the clipping; this report
supplies the number the prediction lacked: the floor bites 4 mm higher than the datasheet says.

## 5. Two predictions that held precisely

- **`psi_odo`** averaged 12.49 mm (sd 0.58) across the five runs against a frozen 12.64 ± 0.90 mm.
  Eleven brake events across five hardware runs and two configurations, sd ≈ 0.5 mm throughout.
- **`o_consistency`** averaged −0.99 mm against a frozen 0 ± 6 mm. The latency/drift correction —
  the thing that caused v2.0's falsification — transferred to all five scored runs.
- **`trigger_src` = 1 on all five.** The ranging chain fired every time; no backstop, no guard, no
  no-echo dropout (`n_bad` = 0 throughout).

## 6. What I would do differently

1. **Characterize the sensor's floor directly.** I inherited 40 mm from the vendor and never measured
   it, because CAL-2's fine staircase stopped at 130 mm reported. One extra staircase decade would
   have cost nothing and would have set the target correctly the first time.
2. **Derive the estimator's algebra before choosing the target.** `clearance_est_odo` was tautological
   from the moment it was written; I discovered that after three frozen plans, by inspection, not by
   measurement. An hour of free analysis at GATE A would have found it.
3. **Bind parameters in the configuration that will fly.** v1.0 was falsified because I took the stop
   yaw from CAL-2's post-staircase approaches. I enforced test-like-you-fly on the control loop and
   then broke it in the parameter binding — the harder half to see, and the one that cost a run.

## 7. Record

Three frozen predictions, two falsified and each diagnosed to a named parameter; four requirements
closed as failed on evidence; two systematics found by cross-channel disagreement that no single
channel showed (an 18.6 mm latency bias and a 7.9 mm yaw mis-binding), both of which would have
produced contact at the targets originally planned. The program's arithmetic was never adjusted to
make a result come out right — only constants, and only from measurement.

**5/5 no contact, mean gap 22.4 mm, 5 characterization runs, 2 operator measurements.**
