# Pre-Verification Report — Wall-Approach Rover (GATE B centerpiece)

**Frozen at GATE B, before any close-range run.** Every predicted number below is committed *now* from
calibrated values. The verification run (Phase 6) tests these predictions; **no measured result may be
written back into any predicted cell.** If the verification falsifies a prediction, the responsible
calibrated parameter is diagnosed and the model re-derived — the prediction is not retroactively
edited.

---

## 1. The decision under test

The locked control law triggers a stop when `eff = min(raw, est) ≤ THRESH`, with the velocity-aided
estimate carrying through sensor plateaus. From calibration (Report §3):

> **predicted true rest gap = THRESH + 69 mm**
> (= +123 mm sensor offset − 54 mm braking distance, both measured at the anchor)

**Chosen verification = operation threshold: `THRESH = 120 mm`.**

Rationale for 120 mm: it is the **closest** stop that is no-contact-safe *even under the pessimistic
assumption that the sensor offset partly collapses at close range* (which is untested below 469 mm
true). The closeness floor here is set by the sensor (the nearer sensor reads ~123 mm short and is
untested below ~343 mm), not by the controller.

---

## 2. Margin sizing (Tenet A6) — the safety envelope

`designMargin` is the root-sum-square of independent uncertainty contributors, scaled by `k = 3`:

| Contributor | Symbol | Value (1σ) | Source |
|---|---|---|---|
| Run-to-run (jitter ⊕ braking) | σ_run | ≈ 11 mm | velocity-aided jitter ~2 mm ⊕ σ_brake ~11 mm |
| Sensor offset uncertainty | σ_offset | ≈ 15 mm | 2-point fit of the +123 mm offset |
| Model/extrapolation (offset constancy below 469 mm) | σ_model | ≈ 15 mm | offset untested at close range |
| Sensor noise | σ_meas | ≈ 3 mm | stationary window |

`designMargin = 3 · √(11² + 15² + 15² + 3²) = 3 · √580 ≈ 3 · 24.1 ≈ **72 mm**.`

**Predicted true rest gap (189 mm) comfortably exceeds the 72 mm safety envelope** — the worst-case
3σ-down gap is `189 − 72 = 117 mm > 0`. Even under the extreme assumption that the offset collapses to
zero at close range, `120 + 0 − 54 = 66 mm > 0`. **No plausible combination yields contact at THRESH =
120.**

---

## 3. Frozen prediction roll-up (the centerpiece)

Predicted at `THRESH = 120 mm`. Cells are committed; verification results go in the Post-Verification
Report only.

| Spec req | Relation / derivation | Calibrated input(s) | **Predicted** | Pass/fail (pred.) |
|---|---|---|---|---|
| **SYS‑1 / CMP‑MOT‑1** command at max | command past clamp | maxSpeed ≈ 1050 deg/s | commanded 2000 ≥ 1050 | **PASS** |
| **SYS‑3** minimise gap (objective) | = true rest gap | offset, braking | **189 mm** (sensor-limited) | n/a (graded) |
| **SYS‑2** no contact (gap > 0) | true rest = THRESH+69 | offset 123, B 54 | **189 mm > 0** | **PASS** |
| **SYS‑5** gap ≥ designMargin (bridge) | designMargin = 72 mm | σ-RSS | **189 ≥ 72** | **PASS** |
| **FUN‑4/5 / CMP‑MOT‑2** Σ within budget | B ≤ THRESH+69 | B = 54 mm | **54 ≤ 189** | **PASS** |
| **SYS‑6** complete stop | residual speed ≈ 0 | brake() | **≈ 0** | **PASS** |
| **SYS‑4 / CMP‑IMU‑1** heading | yawDrift ≤ yawMax | yawDrift ≈ 4° | **≤ 6° predicted** ≤ 15° | **PASS** |
| **CMP‑RNG‑1** refresh bounded | velocity-aid covers plateaus | refresh 16–265 ms | staleness masked by est | **PASS (mitigated)** |
| **CMP‑RNG‑2** sensors agree | A vs B | disagree ≈ 120 mm | **FAIL nominal** → handled by `min` + offset cal | **WAIVED (documented)** |

**Single headline prediction the run will test:**
> At `THRESH = 120 mm`, the rover's nearest point comes to rest at **true gap ≈ 189 mm** (expected
> range ~150–220 mm), **no contact**, heading drift **≤ ~6°**, full stop.

---

## 4. What the verification run decides

- **Confirms** (true gap in ~150–220 mm, no contact, clean heading): the offset holds at close range;
  **lock `THRESH = 120` and run the 5 operation runs.**
- **Falsifies** (true gap well outside the band, or any contact): diagnose — almost certainly the
  offset's close-range behavior (σ_model) — re-derive `THRESH` from the new offset, and re-verify. Do
  **not** empirically nudge the threshold.

One operator measurement is requested at the verification rest (the 2nd and final outside input): the
true gap, to confirm the offset at close range. During the 5 operation runs no input is taken until
close-out.

---

## 5. CMP‑RNG‑2 waiver (epistemic honesty, Tenet D)

The two forward sensors disagree by ~120 mm at equal true distance — A reads ~accurately, B reads
~123 mm short. This *fails* the nominal "sensors agree" requirement. It is **waived, not ignored**:
the control uses `min` (which selects B), B's short bias is explicitly calibrated into the +123 mm
offset, and the disagreement is itself the health signal (a sudden change in the A−B gap would flag a
fault). The consequence — a closeness floor of ~120–170 mm — is accepted as the cost of a no-contact-
first design and recorded as the binding limitation in the final report.
