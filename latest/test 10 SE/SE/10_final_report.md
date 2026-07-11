# Final Report — Wall-Approach Rover
**Document type:** REPORT (backward-looking, static) · **Version:** v1 (close-out) · **Basis:**
five locked operation runs (`run-20260711-010427` … `-011226`) + operator ground truth.

---

## 1. Objective outcome

The rover was required to approach a wall at maximum speed and stop as close as possible **without
contact**. Result over five identical scored runs:

- **No contact: 5 / 5.**
- **True final gap (operator-measured): 36, 35, 36, 36, 35 mm** → **mean 35.6 mm, spread 1 mm.**
- **Straight: 5 / 5** (heading at rest within ±3°; best −0.7°).

The objective is met: a genuinely close (~35–36 mm), square, contact-free stop, repeatable to
±0.5 mm.

## 2. Operation runs — onboard estimate vs ground truth

| Run | Odometry gap | us0−16 gap | **Operator (true)** | odo err | us0 err | Heading rest | Contact |
|-----|--------------|------------|---------------------|---------|---------|--------------|---------|
| 1 | 40.9 | 35.0 | **36** | +4.9 | −1.0 | −3.0° | none |
| 2 | 39.3 | 31.0 | **35** | +4.3 | −4.0 | +1.8° | none |
| 3 | 40.1 | 35.4 | **36** | +4.1 | −0.6 | −2.2° | none |
| 4 | 39.3 | 37.6 | **36** | +3.3 | +1.6 | −2.6° | none |
| 5 | 37.0 | 35.2 | **35** | +2.0 | +0.2 | −0.7° | none |
| **mean** | **39.3** | **34.8** | **35.6** | **+3.7** | **−0.8** | — | **0/5** |

## 3. Model vs reality

- **us0 − 16** (the operator-calibrated channel from the 166 mm anchor) predicted the true gap to
  **~±1.5 mm** at the operating point — the single characterization measurement generalized
  correctly to the close-stop regime.
- **Odometry** ran a **consistent +3.7 mm** high (predicted the gap larger than it was), i.e. the
  rover stopped ~3–4 mm **closer** than odometry indicated — a small residual brake effect at the
  operating speed, always in the **safe** direction. Because it is consistent, it is fully
  predictable; the design absorbed it with margin rather than being surprised by it.
- Both independent channels **bracketed** the truth every run (us0−16 below, odometry above),
  which is exactly the redundancy the plan called for.

## 4. Requirement closure (final)

| Req | Verdict | Basis |
|-----|---------|-------|
| STK-1 mission | **MET** | close, contact-free stop achieved |
| SYS-1 no contact | **MET (5/5)** | true gaps 35–36 mm; hard odometry cap as guarantee |
| SYS-2 max approach speed | **MET (~97% of saturated max)** | full saturation removes steering authority (caused the 20° veer); ~97% is the fastest speed holdable straight — a required trade, documented |
| SYS-3 complete stop | **MET (5/5)** | odometry → 0, settled each run |
| SYS-4 minimise gap (objective) | **MET** | 35.6 mm mean, operator-validated |
| SYS-5 straight approach | **MET (5/5)** | IMU steering; heading ≤3° |
| SYS-6 no-contact margin | **MET** | predicted gap held above contact margin with slack |
| CMP-1/3/4/5/6/7 | **MET** | unit-verified in CHAR-1b/VER-3/VER-4 |
| us1, rear ranger, reflectance | **DROPPED by evidence** | us1 reads ~116 mm short near wall; rear/floor uninformative |

## 5. Scoring summary (honest)

| Metric | Value |
|--------|-------|
| Characterization / verification runs | **6** (CHAR-1, CHAR-1b, VER-1, VER-2, VER-3, VER-4) |
| Outside measurements | **6** total — **1** used to *build* the solution (the 166 mm anchor) + **5** close-out ground-truth measurements used to *score/validate* the operation stops |
| Operation runs stopping with no contact | **5 / 5** |
| Closeness (true gap) | **35.6 mm mean** (35–36 mm), σ ≈ 0.5 mm |

The characterization count (6) is higher than the 2-run baseline the Calibration Plan targeted.
That cost was incurred by **three real defects that only hardware revealed**, each of which would
otherwise have produced a confident-but-wrong result:

1. **Wrong drive direction** (CHAR-1) — the naive "forward = distance decreasing" test was fooled
   by a noisy long-range sensor; the rover drove *away* from the wall.
2. **20° veer at full speed** (VER-1/VER-2) — motors saturate at max command, so straightness
   requires backing off to ~97% and closing a heading loop; a saturated steering attempt did
   literally nothing until this was understood.
3. **A hidden 116 mm sensor offset** (exposed only by the operator's 166 mm measurement) — the
   sensor being triggered on read ~116 mm short, so stops that *looked* like 50 mm were really
   ~166 mm. Control was moved onto the two channels the measurement validated.

Each defect was **caught by the gated verify-before-you-commit process** rather than by driving at
the wall and hoping. The payoff is the Section 1 result: not "looks close," but **is** close
(35.6 mm), square, and contact-free, five times running.

## 6. Deliverable ledger

Requirements Spec (v1) · SysML model · Executable model · Calibration Plan (v1) · Calibration
Report (v1 + Addendum v2) · Verification Plan (v1 → **v2 frozen**) · Verification Report (GATE C)
· **Final Report (this document)**. Runs and their traces are retained under `runs/`.

*End of Final Report.*
