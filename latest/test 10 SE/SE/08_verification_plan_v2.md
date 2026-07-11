# Verification Plan v2 (frozen) — Wall-Approach Rover
**Document type:** PLAN, **frozen before the run** · **Version:** v2 (supersedes v1; v1 retained
in the record) · **Basis:** Calibration Report v1 + Addendum v2

**Why v2 exists:** v1 verified against **us1** with a full-speed open-loop `brake()`. Both
premises are now known bad — us1 reads ~116 mm short of the true front gap, and the open-loop
approach veers 20°. VER-1/2/3 falsified v1; per the discipline of re-deriving rather than tuning,
this is a fresh frozen plan for a new control strategy. The single operator measurement is
**already spent** (the 166 mm anchor); v2 requires **no further measurement**.

---

## 1. Control strategy (new)

Stop the rover using the two **lag-free, operator-validated** channels:
- **Anchor:** at standstill, average us0 → `true_start = us0_avg − 16 mm`.
- **Propagate:** reset odometry at launch; `distance = mean(|Δmotor0|,|Δmotor1|) × 0.50 mm/deg`;
  `pred_gap = true_start − distance`. (Both channels lag-free; the in-motion ultrasonic is not
  used for control.)
- **Straightness:** IMU proportional steering, cruise command 850 (below saturation), Kp=25,
  clamp ±250, ramped launch — the VER-3 configuration that held heading to ≤3°.
- **Stop:** `brake()` when `pred_gap ≤ target + brake_roll`, with `brake_roll ≈ 13 mm` (VER-3),
  so the rover rolls to rest at ≈ `target`.
- **us1 is dropped** from control *and* from the emergency logic (its low reading would false-trip
  a proximity stop).

## 2. VER-4 design (frozen)

- Steered straight approach as above; **target true gap = 40 mm**.
- Brake when `pred_gap ≤ 40 + 13 = 53 mm`.
- **Frozen prediction:** true final gap ≈ **40 mm**; `us0` at rest ≈ **56 mm** (40 + 16);
  odometry-final ≈ **40 mm**; heading at rest within **±3°**.
- Telemetry lean (downsampled), so the run completes and flushes the sentinel.

## 3. Safety (no operator, genuinely close target)

- **Hard odometry cap (lag-free):** brake immediately if `pred_gap ≤ 25 mm` — the rover never
  drives past a 25 mm prediction regardless of the target logic.
- **us0 close backstop:** if `us0 − 16 ≤ 20 mm`, brake (secondary; us0 lags at speed so this is a
  backstop, not the primary).
- Approach-time cap 6 s → brake. Motors stop in `finally`; `{"event":"end"}` always emitted.
- Margin check: with odometry accurate to ~1 mm (VER-3) and a 40 mm target, the predicted stop
  clears the wall with a wide margin; the hard cap guarantees no closer than ~25 mm even if a term
  is mis-estimated.

## 4. Pass / fail criteria (against the frozen prediction; no measurement)

| # | Criterion | Pass condition |
|---|-----------|----------------|
| P-1 | No contact (SYS-1) | rover not touching wall; `us0` at rest > offset floor |
| P-2 | Objective — close (SYS-4) | true final (from `us0 − 16` **and** odometry) ≈ 40 ± 12 mm |
| P-3 | Two-channel agreement | `us0_rest − 16` and odometry-final agree within ~10 mm (both track true) |
| P-4 | Straightness (SYS-5) | |heading| ≤ 3° through the approach; rest skew ≤ 3° |
| P-5 | Complete stop (SYS-3) | odometry speed → 0; settled |

A FAIL → diagnose, re-issue (v3), re-run. A near-miss on P-2 with P-1/P-3/P-4 pass is a refinement
(adjust `brake_roll`/target), not a safety event.

## 5. Path to operation (after VER-4)

1. If VER-4 passes: the program is the operating program. Optionally nudge the target for the five
   runs based on VER-4's realized accuracy (tighter only if P-2/P-3 show small spread; otherwise
   hold 40 mm — reliability first, since a contact fails a scored run).
2. **Lock** the exact program. Run the **five identical scored runs**, each: record the onboard
   final estimate (odometry gap and `us0 − 16`); motors always stop; sentinel each run.
3. Close-out order: freeze the five onboard estimates, **then** (if offered) request operator
   ground-truth gaps, **then** the Final Report.

## 6. Objective-validation note

The objective (true final gap) is anchored to ground truth at the operating configuration by the
166 mm measurement, which calibrated `us0` and confirmed odometry to 1 mm. VER-4 and the operation
runs are therefore read on **operator-validated** channels — the objective is not closed on an
unvalidated sensor.

---

*Frozen. VER-4 runs after the rover is reset to the ~1000 mm start line and confirmed ready; no
further operator measurement is required by this plan.*
