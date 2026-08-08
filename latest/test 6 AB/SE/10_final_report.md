# Wall-Approach Rover — Final Report

**Mission:** Drive a LEGO SPIKE Prime rover (Pybricks firmware) straight at maximum
speed from ~1000 mm and stop as close as possible to the wall **without touching it.**
**Status:** ✅ No-contact achieved **5 / 5 scored runs.** ⚠️ Closeness objective missed —
rover stopped ~135–157 mm out (operator-measured) versus an intended tight stop, due to a
ranging bias uncovered by the operator's final measurements.
**Operation artifact:** `operation_locked.py` (frozen; run **unchanged** for both
verification runs and all five scored runs).
**Authoritative record:** operator tape measurements of the true frontmost-to-wall gap,
supplied after the scored runs. These supersede all onboard gap estimates.

---

## 1. Result in one line

The rover crossed ~1000 mm at motor ceiling every run and braked cleanly on the ultrasonic
trigger with **zero contact, five for five** — but it came to rest **135–157 mm from the
wall (mean ~148 mm)**, far short of the intended tight stop, because the onboard ranger
read a near-constant **~97 mm short** of the true gap and the trigger acted on that biased
value.

---

## 2. The locked artifact

One program was frozen at Gate B and never edited again — it produced 2 verification runs
and all 5 scored runs. Its control law is deliberately minimal: **open-loop maximum speed,
raw `min(dA, dB)` trigger at T_OP = 125 mm, no heading-hold, no encoder fusion.** Rationale
at freeze: protect the two hard constraints (max speed, no contact) over the soft objective
(minimize gap). That prioritization held — but see §5 for how the `min()` trigger choice
interacted with a sensor artifact to cost closeness. Full source in `operation_locked.py`.

**Stopping is a skid.** `brake()` locks the wheels at the trigger; the rover slides a
fixed, repeatable distance (~40 mm in true terms, see §5) before resting.

---

## 3. Per-run results — onboard vs. authoritative

Operator measurements are the truth column; onboard values are shown for the reconciliation.

| phase | run_id | s_trig (mm) | onboard rest (mm) | **operator gap (mm)** | drift | stop | contact |
|---|---|---|---|---|---|---|---|
| verify-1 | run-20260701-001407 | 120 | 141 | — | −0.2° | 0 | none |
| verify-2 | run-20260701-003834 | 91 | — | — | −0.2° | 0 | none |
| **scored 1** | run-20260701-004455 | 104 | 64 | **157** | −4.3° | 0 | **none** |
| **scored 2** | run-20260701-005348 | 89 | ~40 | **135** | −4.3° | 0 | **none** |
| **scored 3** | run-20260701-005541 | 87 | ~49 | **145** | +5.9° | 0 | **none** |
| **scored 4** | run-20260701-010158 | 93 | ~40 | **147** | −2.5° | 0 | **none** |
| **scored 5** | run-20260701-010316 | 92 | 60 (rest 176 rejected) | **156** | −1.6° | 0 | **none** |

Every run braked on the sensor trigger (`stop = 0`); the 4000 ms time-cap safety net was
never reached. Contact: **0 / 5.**

---

## 4. Aggregate

- **Contact:** 0 / 5. No-contact rate **100%**, with a large true margin (135–157 mm).
- **Operator gap:** 135–157 mm, **mean ~148 mm**, σ ~9 mm — tight run-to-run, but ~100 mm
  farther from the wall than the design intended.
- **s_trig (reading at trigger):** 87–104 mm — but this reading was biased short (§5).
- **Heading drift:** −4.3° to +5.9°, |max| ~6° — small and irrelevant to contact.

---

## 5. Reconciliation — the ~97 mm ranging bias (the headline finding)

Pairing each operator measurement with the onboard rest reading:

| run | operator true gap | onboard reading | offset = reading − true |
|---|---|---|---|
| 1 | 157 | 64 | −93 |
| 2 | 135 | 40 | −95 |
| 3 | 145 | 49 | −96 |
| 4 | 147 | 40 | −107 |
| 5 | 156 | 60 | −96 |

**The ranger read a near-constant ~97 mm short of the true gap** (mean −97 mm, σ ~5 mm
excluding run 4). Formally, with `reading = true_gap + δ`, the data give **δ ≈ −97 mm**,
not the δ = 0 assumed at design time. The design was therefore triggering on a distance
that understated the true clearance by ~97 mm the entire time.

**Corroboration from previously-discarded data.** Two rest readings had been flagged as
"impossible high" and rejected — verify-1 at 141 mm and scored-5 at 176 mm — on the logic
that a rover can't rest farther out than where it braked. With the corrected picture, both
sit squarely in the true-gap band (135–157 mm): those were the sensor briefly reporting the
**real** wall distance. The low ~40–60 mm nadirs that were trusted instead were a **near
phantom echo**.

**Root cause: `min()` of two crosstalking rangers.** Sensors A and B ping in a tight loop;
mutual crosstalk / near-field side-lobe returns an intermittent phantom echo ~97 mm short
of the wall. The trigger used `min(dA, dB)`, which systematically selected the shortest
(phantom) value and fired ~97 mm too early. The δ = 0 derivation made earlier (chassis at
530 mm while B read 425 mm) mis-attributed this short reading to sensor protrusion geometry
rather than a ranging artifact.

**True-terms geometry (corrected).** Converting via `true = reading + 97`:

| run | true gap @ trigger | operator true rest | true skid (trigger→rest) |
|---|---|---|---|
| 1 | 201 | 157 | 44 |
| 2 | 186 | 135 | 51 |
| 3 | 184 | 145 | 39 |
| 4 | 190 | 147 | 43 |
| 5 | 189 | 156 | 33 |

The true skid is a consistent **~42 mm** — the physics was sound; only the distance
reference was biased.

---

## 6. Consequence for the two goals

- **No-contact (hard constraint): met, and more robustly than believed.** True rest gaps of
  135–157 mm gave a large safety margin; the rover was never near the wall. The
  conservatism that hurt closeness is the same conservatism that guaranteed safety.
- **Closeness (soft objective): missed by ~100 mm.** The rover stopped ~148 mm out when the
  design intended a tight stop. The `min()`-phantom bias put ~97 mm of hidden standoff into
  every trigger. This is the primary lesson of the mission.

---

## 7. Scoring recap

| # | Metric | Result |
|---|---|---|
| 1 | Fewer characterization runs | **3** |
| 2 | Fewer outside-input operator measurements | **1** during engineering (the δ anchor) + 5 final gap reads supplied after scoring |
| 3 | More scored runs with no contact | **5 / 5** |
| 4 | Closest stops (operator-authoritative) | **135–157 mm, mean ~148 mm** (best run 2 at 135 mm) |

**The metrics are coupled, and that coupling is the story.** The lean path — one early
δ anchor and no near-wall operator measurement — is exactly what let the −97 mm ranging bias
survive undetected. A single operator gap measurement taken near the wall during calibration
(one more count on metric #2) would have exposed δ ≈ −97 mm and allowed the trigger to drop
~100 mm, turning ~148 mm stops into ~40–50 mm stops on metric #4. Saving one measurement
cost roughly 100 mm of closeness on five runs.

---

## 8. Corrective action (for any future attempt)

The bias is now characterized, so it is fully correctable:

1. **Fix the ranging, not just the constant.** Replace `min(dA, dB)` with a phantom-rejecting
   read: `max()` or median of A and B, a single trusted sensor, or an outlier gate that
   drops echoes inconsistent with the closing trend. Verify against an operator tape read
   that the reported distance now tracks the true wall.
2. **Recalibrate the trigger.** With true skid ~42 mm and honest ranging, set
   `T_OP ≈ desired_true_rest + 42 + margin`. To target a true ~40 mm rest with a modest
   safety margin, `T_OP` drops to roughly 30–60 mm of *true* distance — feasible only once
   the ranger reads true near the wall (step 1), since the raw reading is unreliable in the
   near field otherwise.
3. **Re-derive the no-contact margin** on the corrected distances before running; the ~97 mm
   of accidental standoff must be replaced by *deliberate* margin, not removed outright.

This would trade the current large safety margin for a much tighter stop while keeping the
no-contact guarantee explicit.

---

## 9. Closing

The system met both hard constraints — maximum speed and zero contact — on every scored
run, and did so with a comfortable, repeatable safety margin. It missed the closeness
objective: it stopped ~148 mm from the wall because the onboard ranger read ~97 mm short of
the true gap and the `min()` trigger acted on that phantom. The operator's final
measurements were what turned a plausible-but-wrong onboard story into a correct one — and
they pinpoint both the fix (reject the crosstalk phantom, recalibrate the trigger) and the
process lesson (one near-wall measurement during calibration would have caught the bias and
bought ~100 mm of closeness).

**Final tally: 3 characterization runs · 1 engineering measurement · 5/5 no contact ·
135–157 mm (mean ~148 mm) operator-measured stop · root cause identified and correctable.**

### Artifact index
- `operation_locked.py` — frozen operation program (verification + all scored runs)
- `01_requirements_and_effectors.md` — spec, EARS requirement tables, TBD register
- `02_wallrover_model.sysml` — tailored SysML v2 model
- `03_calibration_plan.md` — Calibration Plan v1
- `04_run1_report_and_plan_v2.md` — Run-1 diagnostic + Plan v2
- `05_calibration_report.md` — calibration findings (skid, overshoot, σ inventory, the
  δ = 0 derivation now superseded by §5 here)
- `06_verification_plan.md` — frozen verification plan v1
- `07_verification_report.md` — v1 verification
- `08_verification_plan_v2.md` — verification plan v2
- `09_verification_report_v2.md` — v2 re-verification (Gate C)
- `10_final_report.md` — this report (incorporates operator-authoritative measurements)
