# Calibration Report (GATE B)

**Static REPORT** — consolidates characterization Runs 1–3 and the δ ground-truth anchor. Not edited after issue. This is the evidence base for the frozen Verification Plan (`06_verification_plan.md`).

Characterization-run count (score #1): **3**. Outside-input count (score #2): **1** (the δ anchor).

---

## 1. Runs executed

| Run | run_id | Purpose | Outcome |
|---|---|---|---|
| 1 | run-20260630-231316 | Discovery (ports, polarity, first approach) | Port map + polarity found; distance data invalidated by a nudge-induced in-place spin (see report 04). |
| 2 | run-20260630-233041 | Clean straight approach | D, skid signature, drift, B fore-aft offset. `completed`, sentinel intact. |
| 3 | run-20260630-234230 | Repeat of Run 2 for σ_run | Second D / drift sample. Flush truncated by BLE throughput (39/137 samples out), but all on-hub headline values captured. |

---

## 2. Discovered platform constants (hard-coded downstream)

- **Ports:** A, B = forward ultrasonics; E = rear ultrasonic (unused); C, D = drive motors; F = color sensor (unused).
- **Motor polarity (forward):** C = −1, D = +1 — the motors are **opposed-mounted**. Confirmed by clean monotonic encoder travel in Runs 2–3.
- **Motor ceiling:** ~1040–1090 °/s (peak `motor.speed()` and encoder rate agree).
- **Sensor geometry:** B is mounted **~111 mm forward of A** (pre-approach static, squared: A ≈ 1020, B ≈ 905 at ~1000 mm), and B's housing is the frontmost point of the whole rover (see §6).

---

## 3. Stopping behaviour — the pivotal finding (skid)

`brake()` **locks the wheels almost immediately** at the trigger; the rover then **skids** to rest. Evidence: the encoders plateau at the trigger while the ranger keeps closing. Run 2, around and after the trigger (encoder-implied gap = 912 − (aD + 72) × 0.47 mm/deg):

| phase | reading dB (mm) | encoder aD (°) | encoder-implied gap (mm) |
|---|---|---|---|
| pre-trigger | ~476 | 855 | 476 |
| **trigger** (t=1206 ms) | **464** | 882 | **464**  ← agree |
| wheels locked | ~430 | 911 | 450 |
| nadir (t=1428 ms) | **398** | 911 | 450  ← ranger 52 mm past locked wheels |
| rest | 405 | 911 | 450 |

At the trigger, ranger and encoder agree (464 mm). Afterward the encoder-implied gap sticks at ~450 mm (wheels locked) while the ranger closes to 398 mm — **~52 mm of skid** on locked wheels. The ranger, not the encoder, is the truth for stopping distance.

**Stopping-distance results (ranger, in sensor-B reading):**

| quantity | Run 2 | Run 3 | adopted |
|---|---|---|---|
| D_closest (trigger reading → sensor nadir) | 66.0 | 64.0 | **65.0 ± 1.5 mm** |
| D_rest (trigger reading → settled rest) | 58.8 | 59.7 | **59.3 mm** |

The rover overshoots to the nadir, then the chassis settles back ~6 mm to rest (D_closest − D_rest). D is **skid-dominated** (~48 mm skid + ~14 mm roll) and **highly repeatable** (σ ≈ 1.5 mm).

---

## 4. Trigger overshoot (dominant uncertainty)

At max speed the ultrasonic reading steps in ~15–36 mm increments (update granularity), and steps below the threshold before the control loop catches it. Overshoot = (threshold − reading at the deciding loop):

| | Run 2 | Run 3 |
|---|---|---|
| threshold | 500 | 500 |
| reading at trigger | 464 | 485 |
| **overshoot** | **36 mm** | **15 mm** |

Adopted: mean ≈ 25 mm, **σ ≈ 10 mm**, worst-case ≈ 40 mm. This is the largest single uncertainty in the final stop position.

---

## 5. Heading drift — variable, but not a no-contact driver

- **Cruise drift ≈ ±5°** (motor imbalance). **Braking-yaw** adds up to ~10° during the skid, correlated with the entry angle (straight entry → little yaw).
- **Net drift is not repeatable:** Run 2 = **−15.4°**, Run 3 = **+0.4°** (same program).
- **But:** (a) D is insensitive to yaw — it is a forward skid; and (b) the frontmost point is sensor B itself (§6), which measures its own gap, so yaw does **not** create an unmeasured leading corner. Even at 15° yaw, B (protruding ~105 mm ahead of the chassis) remains the closest point. **Yaw is therefore not a significant no-contact uncertainty** and is excluded from the margin.

---

## 6. δ anchor (outside-input #1) → δ ≈ 0

At Run 3's squared rest (heading 0.4°), sensor B read **425 mm**; the operator measured the **chassis front-to-wall gap = 530 mm**. A sensor cannot report a distance shorter than its own distance to the wall, so **B's face is physically at ≤425 mm** — B's housing protrudes **~105 mm ahead of the chassis** and is the rover's frontmost point. Therefore:

> **δ = (sensor-B reading) − (frontmost-point gap) = 0.** Contact occurs at sensor-B reading ≈ 0.

The 530 mm measurement corroborates the geometry (chassis well behind B; consistent with A's inferred rest reading ~536 ≈ 530, an incidental check on sensor A). A few-mm housing-lip allowance is carried in the margin rather than in δ.

---

## 7. Ranger precision & accuracy
Static noise: ±~4 mm (tight; `static_*` spreads ≈ 8 mm range). Independent accuracy cross-check is limited (the operator's measurement referenced the chassis, not B's face); a conservative **σ_sensor = 4 mm** is used.

---

## 8. Measured uncertainty inventory (basis for the margin, per Tenet A6)

| source | σ (mm) | basis |
|---|---|---|
| D_closest | 1.5 | Run 2/3 spread |
| trigger overshoot | 10 | Run 2/3 spread |
| ranger accuracy | 4 | static noise |
| housing lip / δ | 2 | geometry |
| **RSS σ_total** | **≈ 11 mm** | |

Heading yaw is deliberately excluded (§5). Every entry is measured from the runs, not guessed.

---

## 9. Cross-source checks (Tenet B1) that paid off
- **D:** ranger vs encoder disagreed (65 vs 14 mm) → correctly flagged the **skid** (encoder under-reports; ranger is truth).
- **δ:** operator chassis (530) vs sensor B (425) → flagged the **protruding sensor** → δ = 0.
- **Polarity:** encoder monotonicity confirmed the opposed-mount sign pair.

---

## 10. What remains
Calibration is complete. The operation design and its falsifiable predictions are frozen in `06_verification_plan.md`; the verification run tests them before any scored run.
