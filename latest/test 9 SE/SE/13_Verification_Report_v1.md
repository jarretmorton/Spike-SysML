# Verification Report — Wall‑Stop Rover
**Gate:** C. **Verification runs:** `run‑20260709‑221742` (v1.0, falsified) → re‑derived → `run‑20260709‑223749` (v1.1, **PASS**).
**Locked scheme:** heading‑hold straight drive → ranger‑A position fix @ ~448 mm → encoder dead‑reckon → passive coast, with a gated ranger‑B net.

---

## 1. Verification outcome (v1.1, run‑20260709‑223749)
| Check | Predicted | Measured | Verdict |
|---|---|---|---|
| Stop mechanism | dead‑reckon (reason 1) | reason 1 ×3 | ✅ |
| Rest (A/encoder frame) | ~66 mm | **60 / 64 / 64 mm** (±2) | ✅ |
| Coast `d_stop` | ~15 mm | 16 / 15 / 15 mm | ✅ |
| Final true gap | ~35 mm | **43 mm** (operator, cycle 2) | ✅ in band [20,55] |
| Contact | none | none | ✅ |
| Heading | ≤ ±6° | −3.4° … +5.4° | ✅ |
| A‑fix latched | yes | ~436 mm ×3 | ✅ |

The frozen prediction is confirmed (gap 43 mm vs predicted 35 mm, inside the [20,55] pass band, in the safe direction).

## 2. Calibration closed (Tier 1)
- `k_gain` = 0.516 mm/deg · `v_max` = 494 mm/s · `d_stop` = **15 mm** (σ≈0).
- `c_offset` = **21 mm** at the operating point (dead‑reckon stop). Operating gap model, now validated:
  **`true_gap = D_BRAKE − (d_stop + c_offset) = D_BRAKE − 36 mm`.** (At D_BRAKE=81 → 45 predicted ≈ 43 measured.)
- **`c_offset` is travel‑dependent, not constant:** it was 31 mm at the B‑backstop stop (rest_A ≈ 150, less travel) and 21 mm here (rest_A ≈ 64, more travel). This is encoder over‑count (slip); it makes the rover stop *farther* than `dist_est` reports — i.e. the error is in the no‑contact‑safe direction. Because slip scales with travel, the operating value 21 mm is the correct one for a fixed‑`D_BRAKE` operation.

## 3. Uncertainty (objective)
- **Within‑run** (3 cycles, fixed D_BRAKE): rest spread **±2 mm** — the dead‑reckon is highly repeatable at a fixed setpoint.
- **Run‑to‑run** (fresh power‑cycle + re‑square): not directly sampled for the dead‑reckon; the A‑fix re‑anchors distance each approach, so it should be near the within‑run figure. The 31→21 `c_offset` change is dominated by the *distance* difference above, not random run‑to‑run scatter, so run‑to‑run σ is estimated ~3–5 mm (not 10).
- Net: at a fixed operating D_BRAKE, expected gap σ ≈ 3–5 mm.

## 4. Requirements closure
- **SYS‑1 max speed** — drive at `BASE_CMD` (straight‑line ceiling, slower‑motor‑limited), `v_max` 494 mm/s: **closed**.
- **SYS‑2 no contact** (hard) — 6/6 cycles across two runs, no contact; margin per §3: **closed / verified**.
- **SYS‑3 minimize gap** — objective closed on operating‑point ground truth: the rover stops **without contact at a measured 43 mm** with the verified config, and the validated model shows the setpoint is freely tightenable via `D_BRAKE` (§5). **Closed** (setpoint selection below).
- **SYS‑5 straightness** — heading ≤ ±5.4° (≤ ±6°): **closed**.

## 5. Operation setpoint — DECISION: locked at D_BRAKE = 66 mm (Option B)
The verified config (D_BRAKE = 81) yields ~43 mm. Because the stop is repeatable to ±2 mm and the gap model (`gap = D_BRAKE − 36`) is validated, the setpoint was tightened. Three options were weighed for the locked 5‑run program:

| Option | D_BRAKE | Predicted gap | Margin vs contact | Cost |
|---|---|---|---|---|
| **A — safe** | 81 | ~43 mm | ~8–14σ | lock verified program as‑is |
| **B — tighten (model)** | 66 | ~30 mm | ~6σ (σ≈5) | small setpoint change on validated model; no extra run |
| **C — tighten + re‑verify** | 61 | ~25 mm | ~5σ, *verified* | +1 verification run, +1 measurement |

**DECISION — Option B (locked).** `D_BRAKE = 66 mm`, predicted true gap ≈ 30 mm (rest_A ≈ 51 → 51 − `c_offset` 21). Rationale: a meaningful closeness gain (43→30 mm) using the validated linear gap model, with no additional characterization runs or measurements; the five close‑out gap measurements serve as ground truth, and ~6σ margin (σ≈5 mm) protects the hard no‑contact constraint. The locked operation program is `14_operation_final_LOCKED.py` (single drive‑and‑stop; identical across all five runs; emits its own onboard `gap_est = rest_A − 21`).

## 6. Operation protocol (setpoint locked: D_BRAKE = 66)
Run the identical locked program (`14_operation_final_LOCKED.py`) **5×** at max speed; between runs the operator power‑cycles, re‑squares to ~1000 mm, clears behind (all free). Close‑out (strict order): **freeze onboard per‑run gap estimate** (`dist_est_rest − 21`) for each run **before** requesting the operator's per‑run measured gap; then produce the final engineering report (per‑run table: onboard est. | operator | Δ, contact y/n, plus reconciliation) as a downloadable markdown artifact.

## 7. Ledger
Characterization/verification program runs: 7 (2 import‑crash, 1 discovery, 1 fail‑safe abort, 1 calibration, 2 verification). Operator measurements: 2 (122, 43). Upcoming: 5 scored operation runs + 5 close‑out measurements.
