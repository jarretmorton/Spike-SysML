# Wall‑Stop Rover — Final Engineering Report
**Task:** drive a SPIKE Prime rover straight at a wall at maximum speed and stop as close as possible **without contact**, minimizing the final gap.
**Result:** **5/5 runs stopped with no contact; mean final gap 20.0 mm (best 14 mm).**

---

## 1. Operation results (5 scored runs)

| Run | Onboard est. | Operator gap | Δ (op−est) | Contact | Stop mechanism | Heading |
|---|---|---|---|---|---|---|
| 1 | 24 mm | **19 mm** | −5 | none | dead‑reckon | ≤2.9° |
| 2† | 27 mm | **22 mm** | −5 | none | dead‑reckon | ≤3.7° |
| 3 | 27 mm | **14 mm** | −13 | none | dead‑reckon | ≤4.2° |
| 4 | 29 mm | **30 mm** | +1 | none | dead‑reckon | ≤3.9° |
| 5 | 26 mm | **15 mm** | −11 | none | dead‑reckon | ≤3.4° |

† Run 2 was re‑done on a fresh power‑cycle (the first attempt was voided for excess hub runtime); the redo is the scored run.

**Statistics (operator ground truth):** mean **20.0 mm**, min 14, max 30, σ 5.8 mm. Every run stopped on the encoder dead‑reckon (no safety backstop or failsafe triggered), straight (heading ≤ 4.2° throughout), no contact. Margin to contact ≈ **3.5σ**.

---

## 2. Reconciliation (onboard estimate vs ground truth)
Onboard estimates averaged **6.6 mm high** (rover was consistently a bit closer than reported). Cause: the onboard gap = `rest_A − c_offset` used `c_offset = 21 mm`, taken from the single verification run. The **effective `c_offset` measured across the five runs was 27.6 mm (range 20–34)** — the verification value sat at the low end of the true run‑to‑run distribution. `c_offset` is the dead‑reckon‑to‑true‑gap offset; it carries wheel‑slip and squaring effects, which vary run‑to‑run more than one verification run exposed (±7 mm). This is the report's main epistemic finding: **one operating‑point sample under‑estimated both the offset and its variance.** Because the setpoint was chosen conservatively (30 mm target, not the ~15–20 mm the point estimate would have allowed), the 6.6 mm bias and the spread were absorbed and no run contacted.

---

## 3. Validated design (locked program)
`14_operation_final_LOCKED.py` — single drive‑and‑stop:
1. **Baseline sanity gate** — reads the forward rangers; aborts without moving unless squared at ~1000 mm.
2. **Heading‑hold straight drive** at the straight‑line speed ceiling (closed‑loop trim on the IMU heading + an initial square‑up). Held heading ≤ ±4.2° on every run.
3. **Ranger‑A position fix** at ~450 mm, where A is still linear — re‑anchors the dead‑reckon origin, removing start‑distance and early‑slip error.
4. **Encoder dead‑reckon** to `D_BRAKE = 66 mm`: `dist_est = A_fix − k·Δenc`, brake when `dist_est ≤ 66`.
5. **Passive coast** ~15 mm to rest.
6. **Layered ranger‑B net** (armed only below `dist_est` 65) and encoder/time failsafes — none needed to fire.

**Why not trigger on a rangefinder directly:** ranger A saturates at a ~288 mm floor (blind in the stop region) and ranger B is noisy/nonlinear up close. The encoders (which never floor, spike, or compress) carry the trigger; the rangefinders are demoted to a position fix (A, far) and a safety net (B, close).

---

## 4. Calibration (Tier‑1 unless noted)
| Parameter | Value | Notes |
|---|---|---|
| `k_gain` | 0.516 mm/deg | encoder→ground; two methods agree |
| `v_max` | 494 mm/s | straight‑line, slower‑motor‑limited |
| `d_stop` | 15 mm | encoder‑measured coast; σ≈0 |
| `c_offset` | 21 mm (verif) → **27.6 mm (operation mean, 20–34)** | dead‑reckon→true‑gap offset; run‑to‑run variable |
| Ranger A | accurate ~1000–400 mm, **floors ~288 mm** | forbids A close‑trigger |
| Ranger B | reads to <60 mm, **noisy far, spikes** | median‑filtered safety net only |
| Heading hold | ≤ ±4.2° (operation) | straightness solved |

---

## 5. V&V chronology (gated process)
- **Gate A** — requirements spec, SysML model, executable physics model, calibration plan (sensitivity analysis first). Approved.
- **Characterization** — discovered the minimal‑MicroPython constraint (2 import‑crash loads), the port map/drive polarity, a heading veer (fixed with closed‑loop control), the BLE throughput limit (fixed with buffered/downsampled per‑cycle logging), and the **ranger‑A 288 mm floor** and **ranger‑B close/noisy** behavior. One clean 3‑cycle calibration run gave `k`, `v_max`, and the sensor models.
- **Gate B** — calibration report + frozen verification prediction. `d_stop` and `c_offset` deliberately deferred to the verification run.
- **Verification** — v1.0 prediction **falsified** (the B backstop pre‑empted the dead‑reckon); re‑derived to v1.1 (dead‑reckon primary, B net gated), which **passed** (43 mm, no contact) and closed `d_stop = 15` and `c_offset = 21`.
- **Gate C** — verification report; operation setpoint locked at `D_BRAKE = 66` (Option B, ~30 mm target).
- **Operation** — 5 runs, all no contact, mean 20 mm.

---

## 6. Scorecard
| Metric | Result |
|---|---|
| Runs with no contact (of 5) | **5 / 5** |
| Closeness (mean / best) | **20.0 mm / 14 mm** |
| Characterization/verification program runs | 7 (incl. 2 import‑crashes and 1 fail‑safe abort that were avoidable; 2 verification runs required by the falsification) |
| Outside‑input actions | 7 (2 characterization measurements + 5 mandated close‑out measurements) |

---

## 7. Lessons / what I would change
1. **Sample `c_offset` more than once before locking.** A single verification value under‑estimated the offset by ~6.6 mm and hid its ±7 mm run‑to‑run spread. Two or three dead‑reckon runs at the operating point (a superset verification) would have exposed the true distribution and let the setpoint be tuned with a correct margin.
2. **The conservative setpoint was the right call.** Given the (unbudgeted) `c_offset` variability, the ~30 mm target — rather than the ~15 mm the point estimate suggested — is why all five cleared the wall. Against a hard no‑contact constraint, budgeting for unknown‑unknowns beat squeezing the mean.
3. **Early waste was avoidable.** Two import‑crash loads and one over‑strict rear‑gate abort cost three rover runs; a dry‑run harness (adopted mid‑stream) and checking the runtime's built‑ins first would have saved them.
4. **Sensor reality dominated the design.** Neither ultrasonic could measure the stop region reliably (A floors, B is noisy/nonlinear); shifting the trigger to encoder dead‑reckon with a ranger‑A fix was the key architectural decision and the reason the stop was repeatable to a few mm within a run.

---

## 8. Artifact index (`/mnt/user-data/outputs/`)
01 Requirements · 02 SysML · 03 executable model · 04 Calibration Plan v1 · 05 calibration program · 06 Anomaly Report · 07 Calibration Plan v1.1 · 08 Calibration Report · 09 Verification Plan · 10/12 verification programs · 11 Verification Plan v1.1 · 13 Verification Report · **14 LOCKED operation program** · **this report**.
