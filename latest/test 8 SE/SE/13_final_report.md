# WALLRUN — FINAL REPORT
**Task:** drive a LEGO SPIKE Prime rover straight at max speed at a wall ~1000 mm ahead and stop as close as possible **without contact**.
**Outcome:** **5 / 5 operation runs stopped with no contact**, mean gap **43.4 mm** (range 31–50 mm). The onboard gap estimate matched operator ground truth to **±2.6 mm RMS**, and the measured mean fell **1.6 mm** from the frozen pre‑run prediction.

---

## 1. Result — the 5 scored runs (reconciliation)
Frozen prediction (from Verification Plan v1, fixed before any scored run): **G = 45 mm, σ_G = 12 mm** (2σ band 21–69 mm).

| Run | Predicted (frozen) | Onboard estimate | Operator measured | Onboard − measured | Contact |
|---|---|---|---|---|---|
| 1 | 45 mm | 29 mm | 31 mm | −2 mm | none |
| 2 | 45 mm | 49 mm | 47 mm | +2 mm | none |
| 3 | 45 mm | 55 mm | 50 mm | +5 mm | none |
| 4 | 45 mm | 41 mm | 41 mm | 0 mm | none |
| 5 | 45 mm | 49 mm | 48 mm | +1 mm | none |
| **mean** | **45 mm** | **44.6 mm** | **43.4 mm** | **+1.2 mm** | **0 / 5** |

- **No contact: 5/5.** Every stop cleared the wall (closest 31 mm).
- **Onboard estimator accuracy:** onboard − measured = {−2, +2, +5, 0, +1} mm → **RMS 2.6 mm, bias +1.2 mm**. The onboard estimate `G = S_A − 15` is trustworthy to a few mm — the T0 operator anchor on c_A held.
- **Prediction accuracy:** measured mean 43.4 mm vs frozen 45 mm (Δ 1.6 mm). All five within ~1.2σ of the frozen prediction.
- **Scatter:** measured σ 7.7 mm, *below* the conservative σ_G = 12 mm budgeted — the margin was cautious, as intended for guaranteed no‑contact.

## 2. Locked program
`09_operation_program_v1.py`, run **unchanged** for the verification run and all 5 scored runs. Key locked parameters (sensor‑A frame): trigger on first valid `S_A ≤ 113 mm`; heading hold `gsign=1, MAX_CMD=1000, FF=120, KP=30, KD=4`; brake to stop; `c_A = 15 mm`; safety‑only floor `S_A ≤ 80` and `|heading| > 25°` (neither fired in any scored run). Predicted stop `G = d_trig − D_stop − c_A = 113 − 53 − 15`.

## 3. How the number was reached (calibration chain)
| Element | Value | Source |
|---|---|---|
| Forward sensor | A (Port A) | B discarded — latches/drops, physically-impossible offset |
| Sensor offset c_A | +15 mm | **operator ground truth** (gap 542 mm at S_A 557 mm) — the one costed measurement |
| Max speed | ~490 mm/s | C1d ultrasonic slope |
| D_stop | 53 mm (calib) → 62 mm at operating trigger | C1d + verification run |
| Straightness | held to ±2.6° (run), ±4° run‑to‑run | C1d + verification (feed‑forward + P + D heading hold) |
| Trigger threshold | S_A = 113 mm | designed for G_target 45 mm at ~3σ no‑contact |

The single highest‑leverage unknown — the sensor‑to‑front offset, which has **no onboard channel** — is exactly where the one operator measurement was spent; everything else was calibrated onboard.

## 4. Scores
1. **Characterization program runs: 5** — C1 (discovery), C1b + C1c + C1d (clean dynamics + heading‑control iterations forced by a drivetrain veer and a BLE‑dump limit), verification run. Two of these were driven by hardware behaviour not visible until the rover moved.
2. **Operator ground‑truth measurements (characterization): 1** — the c_A anchor. (Plus the 5 close‑out gap readings that score the runs.)
3. **No‑contact operation runs: 5 / 5.**
4. **Closeness:** mean **43.4 mm**, best **31 mm**, all 31–50 mm.

## 5. What I'd do with more hardware budget
The conservative margin (targeting 45 mm at ~3σ, on limited run‑to‑run data) traded closeness for a guaranteed clean sweep. With the now‑measured scatter (σ ≈ 7.7 mm) I could re‑lock the trigger ~15–20 mm lower (target ~25 mm at the same ~3σ) and re‑verify, likely halving the gap while keeping no‑contact — at the cost of one more verification run. Given the 5/5 no‑contact result, the delivered solution prioritised the hard constraint first.

## 6. Process trail (auditable)
Requirements spec → SysML model → executable model → **GATE A** Calibration Plan (with sensitivity analysis) → characterization runs C1–C1d (each anomaly diagnosed by free analysis, program re‑derived, never tuned‑to‑fit) → **GATE B** Calibration Report + frozen Verification Plan → verification run (frozen prediction confirmed) → **GATE C** Verification Report (all requirements closed) → 5 locked operation runs → this report. Deliverables 01–12 plus the run programs accompany this report.
