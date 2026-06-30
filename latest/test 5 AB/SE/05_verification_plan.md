# VERIFICATION PLAN — Wall-Approach Rover

**Document type:** PLAN with a **FROZEN PREDICTION**. The prediction in §2 is locked **before** the verification run. If the run falsifies it, the prediction is **not edited** — the model is diagnosed, re-derived, and re-issued as a new version; this plan stands as the record of what was predicted.
**Version:** 1.0 · **Phase:** GATE B (before the verification run).
**Realises:** Requirements Specification v1.0, `02_wall_run_model.sysml`, Calibration Report v1.0.

---

## 1. Purpose

The verification run is the first **integrated** test: it exercises the full control law (`final reading = d_trig − O`) at a **closer** trigger than any calibration run, to (a) confirm the law and the overshoot constant `O` predict the stopping point, (b) take the single operator ground-truth measurement (OI-1) that anchors sensor bias `b`, and (c) provide the second clean stop needed to estimate run-to-run scatter σ_r2r. It is **not** one of the five scored operation runs.

---

## 2. FROZEN PREDICTION

Configuration for the verification run:
- Trigger threshold **`d_trig = 200 mm`** (closer than the 400 mm calibration trigger; still a safe stop).
- Control core **identical to C1 v4** (autonomous discovery, derived steering trim, dropout-robust fusion), with two calibration-informed changes: trigger at 200 mm, and **A normalised to B's frame** (`A' = A − 160 mm`) before fusion so a B-dropout cannot under-trigger.
- Overshoot constant from calibration: **`O = 65 mm`** (threshold-referenced, max speed).

**Predicted primary outcome — resting forward reading (sensor B):**

> **final B reading = d_trig − O = 200 − 65 = `135 mm`**
> **95 % prediction interval: `135 ± 33 mm` → [102 mm, 168 mm]**
> (interval = k_σ=2 · √(σ_O² + σ_read²) = 2 · √(16² + 3²) ≈ 33 mm)

**Predicted secondary outcomes (also frozen):**
- Heading held within **±3°** through the approach (straight approach; CMP-3.1 / SYS-5).
- **No contact** (a 135 mm reading is well clear of the wall for any plausible bias).
- `A'` (normalised) agrees with B at rest to within ~±20 mm.
- Approach at full speed (~0.42 m/s) until the trigger; brake duration ~120 ms.

---

## 3. Pass / fail and falsification protocol

- **PASS** if the resting B reading falls in **[102, 168] mm** *and* heading stayed within ±3° *and* no contact.
- **FALSIFY** if the resting reading is outside the interval, or the rover contacts the wall, or heading exceeds the bound.
- On falsification: **do not edit this prediction.** Diagnose from telemetry, identify the cause (e.g., `O` speed-dependence, dropout near the wall, bias in the law), re-derive the affected calibration value, and re-issue the Calibration Report / model as a new version. Then re-plan. The five operation runs do **not** begin until a verification run passes.

---

## 4. Outside input OI-1 (the only operator interaction this phase)

After the verification rover has stopped and is holding position, the operator measures the **true gap** — the perpendicular distance from the wall to the **frontmost point of the rover** — once, and reports it. This anchors the sensor bias:

> **`b = (resting B reading) − (true gap)`**  (positive ⇒ B reads long)

This is the single Phase-1 outside input the Calibration Plan budgeted. No other operator measurement is taken until the operation close-out.

---

## 5. How the validated numbers set the operation trigger (after a passing verification)

For operation we want the smallest **true** gap that still never contacts. With the law `final reading = d_trig − O` and the anchored bias `b`:

> **true gap at rest = (d_trig − O) − b**
> Set this equal to the margin `m*` ⇒ **`d_trig(operation) = O + b + m*`**

with `m* = k_σ · RSS(σ_pred, σ_meas, σ_r2r)` and **k_σ = 3** for the no-contact hard constraint. σ_r2r will be re-estimated from the C1 v4 and verification stops before fixing `m*`. The predicted operation true gap is then `≈ m*` on every run, with contact probability driven below ~0.2 % per run by the 3σ margin.

---

## 6. Verification program (specification)

Same structure and safety guards as `c1_calibration_v4.py`, changed only where calibration dictates:

1. Autonomous discovery (device map, mirror/sign, yaw probe) — unchanged.
2. Approach at max speed with the derived steering trim — unchanged.
3. **Fusion:** compute `A' = A − 160`; treat readings ≥ 1900 mm as no-echo; use the nearer of the valid `{A', B}`; if both invalid, hold last valid; "blind too long ⇒ stop" guard — unchanged logic, now with A normalised.
4. **Trigger at `d_trig = 200 mm`.**
5. Brake → hold; emit the static final readings first, then the downsampled curve (truncation-safe), then the end sentinel — unchanged.

This is deliberately the **operation control core**: the verification run flies exactly what the scored runs will fly, only with a provisional trigger pending the bias anchor.

---

## 7. Safety

Predicted stop ~135 mm reading (true gap ~135 mm − `b`), comfortably clear of the wall; the same floor / timeout / blind-too-long guards remain. Echo quality is expected to *improve* at the closer range. If the resting reading comes in at the low end of the interval and the operator's true gap is small, the operation margin (§5) will be sized to restore a safe clearance before any scored run.

*End of Verification Plan v1.0 (prediction frozen).*
