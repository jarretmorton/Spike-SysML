# FINAL REPORT — Wall-Approach Rover

**Document type:** REPORT (STATIC, terminal deliverable).
**Version:** 1.0 · **Phase:** Operation complete.
**Closes:** Requirements Specification v1.0 and the full V&V chain.

---

## 1. Executive summary

The rover was required to drive **straight at a wall at maximum speed and stop as close as possible without contact**. Across the five scored runs it stopped at a true gap of **62–77 mm (mean 71 mm)**, **straight every time (heading ≤ ±4.6°)**, with **zero contacts (5 / 5)**. The pre-registered operation model predicted **78 mm**; the measured mean of **71 mm** validates it (the rover stopped slightly closer than predicted, and safely). Maximum speed was genuinely used on every run — the motors ran saturated at their ~985 deg/s ceiling (~0.42 m/s ground speed) the whole approach, with steering trim providing straightness without slowing.

---

## 2. Scored results — predicted → estimated → measured

| Scored run | Predicted gap (mm) | My frozen estimate, A−24 (mm) | **Operator true gap (mm)** | Contact? | Heading range |
|---|---|---|---|---|---|
| 1 | 78 | 62 | **72** | none | −2.6° … +0.5° |
| 2 | 78 | 67 | **71** | none | −4.5° … +0.4° |
| 3 | 78 | 57 | **62** | none | −4.6° … +2.6° |
| 4 | 78 | 58 | **72** | none | −2.3° … +0.3° |
| 5 | 78 | 72 | **77** | none | −3.2° … +0.2° |
| **mean** | **78** | **63** | **71** | **0 / 5** | within ±4.6° |

Measured spread: 15 mm (σ ≈ 4.9 mm) — tightly repeatable. Closest stop: **run 3, 62 mm**.

---

## 3. Outcome against the four scored quantities

- **No-contact (more is better): 5 / 5.** The hard constraint held on every scored run, confirmed by ground truth (all true gaps strictly positive, 62–77 mm).
- **Closeness (closer is better):** mean **71 mm**, best **62 mm**, all within a 15 mm band. Bounded by the sensor floor and a deliberate 3σ no-contact margin, not by control noise (the stops were highly repeatable).
- **Characterization program runs (fewer is better): 6** — four calibration runs (C1, C1′, C1‴, C1⁴), one verification run, and one operation shakedown that was reclassified to characterization when it exposed a sensor-blocking bug. Each run isolated a distinct physical fault that would otherwise have broken the scored phase (see §6); none were redundant.
- **Outside-input actions (fewer is better): 1 decision-affecting** (the verification true-gap, OI-1, which set the operation trigger), plus the **5 mandated close-out measurements** used only for this report's ground truth. No operator input was used to tune the controller mid-run.

---

## 4. Prediction validation and estimate accuracy

**The model predicted the outcome.** The GATE-C operation model `stop true gap = A_trig − 72` predicted 78 mm at `A_trig = 150`; the measured mean was 71 mm — a 7 mm difference, well inside the sized margin, on the safe side.

**My live estimates were conservative-low by ~8 mm**, and the reason is now quantified: the accurate sensor A's offset is **range-dependent**. It read **+24 mm long at the verification range (264 mm)** but only **+16 mm long at the operation range (~71 mm)** (per-run A−true: 14, 20, 19, 10, 19 mm; mean 16). Because I anchored the correction at +24 (the only true point available before operation) and applied it at close range, every live estimate under-stated the true gap by the ~8 mm difference. The error was therefore **systematic and in the safe direction** (the rover was always slightly farther from the wall than I believed) — which is exactly the behaviour a single-anchor calibration should be expected to produce, and why the 3σ margin was retained. A second true-gap anchor at close range (an extra outside input I chose not to spend) would have removed this bias and allowed a ~10 mm closer target.

---

## 5. Requirements satisfaction

| Req | Statement | Status |
|---|---|---|
| SYS-1 | Operate at maximum speed | **MET** — motors saturated at ~985 deg/s every run |
| SYS-2 | No contact with the wall | **MET** — 5 / 5, ground-truth confirmed |
| SYS-3 | Come to a full stop | **MET** — brake → hold; stable resting reads |
| SYS-4 | Minimise final gap (objective) | **ACHIEVED** — 71 mm mean, 62 mm best, tight |
| SYS-5 | Straight approach | **MET** — heading ≤ ±4.6°, gyro-trimmed |
| SYS-6 | Clearance margin = RSS of calibrated σ | **MET** — m\* sized from data (3σ), not guessed |
| CMP-1.1…3.2 | Component requirements | **MET** — see Calibration Report §5 |

---

## 6. Engineering narrative — the faults the process caught

The discipline of characterise → verify → operate earned its cost: every scored run was clean because the messy discoveries happened earlier, each diagnosed from telemetry and fixed by re-derivation rather than guesswork.

1. **Mirror-mounted drive base.** The first run spun 3¼ turns in place — same-sign motor commands rotate this rover. Distance-based sign discovery was being fooled by the rotation; the fix decides drive direction from **heading**, not distance.
2. **Telemetry truncation.** Streaming every sample over Bluetooth overran the run; fixed by buffering in RAM and emitting a downsampled curve with the **critical final readings first**.
3. **Ultrasonic crosstalk.** The two forward sensors intermittently drop their echo together; an early version mis-braked on the resulting spike. Fixed with dropout-robust fusion (hold last valid, blind-stop guard).
4. **Steering had no authority at saturation.** Trimming a wheel from an over-saturated command did nothing; the fix trims **relative to the measured real max**, which holds heading to ~±1–4°.
5. **The "primary" sensor was the faulty one.** The single operator measurement revealed sensor B reads ~98 mm short and **A is the accurate sensor** — reassigning the trigger to A is what made close, safe stops possible.
6. **Sensor-blocking near the wall.** B's no-echo call blocks; polling the accurate sensor first removed it from the scored loop.

---

## 7. Deliverable ledger

Specification → model → calibration plan (v1.0, v1.1) → calibration report → verification plan (frozen) → verification report → final report, with a chart for every hardware run. Frozen predictions were never edited after the fact; plans were revised and re-issued with prior versions retained; reports were static once written.

---

## 8. Final remarks

The rover meets every hard requirement and the objective: **maximum-speed, straight, no-contact stops at a mean of 71 mm**, fully repeatable, with the single closest at 62 mm. The result is backed by a prediction that was frozen before the runs and confirmed by independent ground truth, and by an uncertainty budget built from measured scatter rather than assumption. The one residual systematic — the range-dependent sensor offset — is identified, quantified, and was safely absorbed by the margin; it is the obvious lever for getting ~10 mm closer in a future campaign with one additional close-range calibration point.

*End of Final Report v1.0.*
