# Verification Plan (frozen) — Wall-Approach Rover
**Document type:** PLAN, **frozen at GATE B** (prediction values fixed *before* the verifying run,
per "argue before you run") · **Version:** v1 · **Basis:** Calibration Report v1

Freezing means: the numeric prediction below is committed now; VER-1 tests it. If VER-1
falsifies it, I diagnose and re-derive a *new* version of this plan — I do not tune the program to
pass.

---

## 1. Objective of VER-1 (one run, one operator measurement)

VER-1 does four things at once, which is why it earns its single measurement:
1. **Resolves the §3 anomaly** (brake-skid vs ultrasonic-bias) using an absolute reference.
2. **Pins the true-gap ↔ us1-reading relation** at a near-operating stop, so the objective can be
   validated against ground truth (GATE C requirement).
3. **Verifies straightness at full speed** (SYS-5), which only the low-speed move has covered.
4. **Gives a second stopping sample** (with CHAR-1b) toward run-to-run repeatability.

## 2. VER-1 design (frozen)

- **Config:** forward = (m0 −1, m1 +1); front pair us0/us1; **trigger on us1** (the forward
  sensor, reads closest to the wall).
- **Approach:** both motors at max (full-speed, as operation).
- **Trigger:** `us1 ≤ d_trig`, with **`d_trig = 128 mm`**, then `brake()`. All-sensor emergency
  backstop at ≤ 90 mm.
- **Frozen onboard prediction:** using the ultrasonic-frame `D_dyn = 48 mm`,
  **us1 at rest ≈ 80 mm** (128 − 48). Odometry-frame prediction of the true gap ≈ 113 mm. The
  gap between these two predictions (≈ 33 mm) is the anomaly VER-1 resolves.
- **Instrumentation added vs CHAR-1b:** log **heading** through the full-speed approach
  (straightness). Keep telemetry lean (downsampled) so the run completes and flushes the sentinel.
- **Safety argument:** the frozen stop is us1 ≈ 80 mm. The true gap = 80 ± (whichever error is
  real). Even if the ultrasonic *over*-reads by 40 mm (worse than the 33 mm seen, and in the
  opposite sign to CHAR-1b's evidence), the true gap ≥ 40 mm — **no contact**. This is the closest
  I will go before the anomaly is resolved.

## 3. Outside input required (the one budgeted measurement)

**After VER-1 stops, with the rover left in place:** operator measures the **true distance from
the rover's front-most face to the wall, in mm**. One number. This is the single costed
measurement from the Calibration Plan, spent here at a near-operating stop.

*(Free, uncounted: reset/square the rover to the ~1000 mm start line before the run; power-cycle;
confirm clearance.)*

## 4. Pass / fail criteria (evaluated against the frozen prediction)

| # | Criterion | Pass condition |
|---|-----------|----------------|
| C-1 | No contact (SYS-1) | operator gap > 0; rover not touching wall |
| C-2 | Onboard prediction (reading frame) | us1 at rest = 80 ± 15 mm |
| C-3 | Complete stop (SYS-3) | odometry speed → 0; body settled |
| C-4 | Straightness (SYS-5) | |heading drift| ≤ 3° through the full-speed approach |
| C-5 | Anomaly resolved | operator gap distinguishes skid (gap ≈ us1 reading) vs bias (gap ≈ odometry prediction ≈ 113 mm), or a mix, to within a few mm |
| C-6 | Repeatability sane | this stop vs CHAR-1b consistent under the resolved model |

Any FAIL → diagnose, re-issue this plan (v2), re-run. Notably, a C-2 miss with C-1 pass is still
informative (refines `D_dyn`), not a safety event.

## 5. Anomaly-resolution logic (how one number decides it)

Let `g` = operator gap, `r` = us1 at rest (≈ 80 predicted), `o` = odometry-predicted gap (≈ 113).
- `g ≈ r`  ⇒ **skid** confirmed: ultrasonic is truthful, odometry under-counts by the brake
  slide. Operating trigger uses `D_dyn ≈ 48 mm` (reading frame); the true gap equals the us1
  reading minus a small residual bias (≈ `g − r`).
- `g ≈ o`  ⇒ **ultrasonic bias** confirmed: us1 reads low by ≈ `o − r`; odometry is truthful.
  Operating gap is set from odometry with the reading-frame bias applied.
- `r < g < o` ⇒ **both**: partition the 33 mm into skid and bias by `(g − r)` and `(o − g)`; carry
  both in the margin.
In every case the **sign and size of the correction become known**, and the model's `D_dyn` /
bias terms are updated to a single self-consistent set.

## 6. Path to operation (after VER-1)

1. Update the executable model with the resolved correction; recompute the safety margin M with
   the now-pinned bias/skid uncertainty and the 2-sample repeatability.
2. **Choose the operating `d_trig`** for a target gap = M-limited closest-safe value (expected
   ~40–50 mm given present uncertainty; tighter if VER-1 shows small spread). Re-issue this plan
   (v2) with the frozen operating prediction.
3. **VER-2 (optional, no new measurement):** one run at the operating `d_trig` to confirm the
   frozen operating prediction (odometry as the onboard witness; ultrasonic where still valid)
   before the scored runs. Recommended if the operating stop would be inside the ultrasonic floor
   (can't self-check otherwise). If VER-1 already lands at an acceptable gap, lock VER-1 instead.
4. **Operation:** 5 identical locked runs at the frozen operating `d_trig`. Per run: onboard gap
   estimate recorded; motors always stop; `{"event":"end"}` sentinel. After all 5, freeze the
   onboard per-run estimates, *then* request the operator's ground-truth gaps, *then* the Final
   Report (GATE close-out order).

## 7. Abort / safety handling during VER-1

- All-sensor emergency brake at ≤ 90 mm (backstop if us1 misbehaves).
- 6 s approach-time cap → brake and stop.
- Motors stop in `finally`; sentinel always emitted.
- Any physically impossible reading (rest farther than trigger; non-monotone approach; channel
  disagreement beyond plausibility) → stop, report, escalate; do not average suspect channels.

---

*Frozen at GATE B. VER-1 will run after the rover is reset and confirmed ready; its one operator
measurement is requested immediately after it stops.*
