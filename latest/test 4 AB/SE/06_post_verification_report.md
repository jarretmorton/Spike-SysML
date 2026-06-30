# Post-Verification Report — Wall-Approach Rover (GATE C)

**Result: prediction CONFIRMED. Lock `THRESH = 120 mm` and proceed to the five operation runs.**

The frozen prediction (`05_pre_verification_report.md`) called the true rest gap at `THRESH = 120` to
**189 mm**, expected range ~150–220 mm. The verification run measured **173 mm**, no contact, heading
held. The prediction held inside its stated uncertainty, and the small residual has a clean physical
explanation. No predicted cell was altered.

---

## 1. Verification run — what happened

| Observable | Value | Note |
|---|---|---|
| Start reading | **897 mm** | Confirms the rover was squared at ~1000 mm (offset-consistent); run is valid |
| Trigger | `eff = 119` while raw stalled at 158 | Velocity-aided estimate fired through an ~86 ms sensor plateau |
| Rest reading | **~70 mm** (stdout 74; settled 66–67) | Sensor reads reliably at close range — closes TBD‑10 |
| Heading (min/max) | **−3° to 0°** | Straight; well within tolerance |
| Samples | 130 (buffer full) | Stall-free fast loop |
| Plateaus handled | 587 mm (~265 ms) and 158 mm (~86 ms) | Both carried by the velocity estimate |
| Post-stop glitch | one spurious 276 mm reading during settle | Harmless — stop already commanded; shows close-range noise |

Distance-vs-time chart rendered in chat.

---

## 2. Predicted vs measured roll-up

| Spec req | Predicted (frozen) | Measured | Verdict |
|---|---|---|---|
| **SYS‑2** no contact (gap > 0) | 189 mm > 0 | **173 mm > 0** | ✅ confirmed |
| **SYS‑3** minimise gap (objective) | 189 mm | **173 mm** (closer) | ✅ better than predicted |
| **SYS‑5** gap ≥ designMargin (72 mm) | 189 ≥ 72 | **173 ≥ 72** | ✅ confirmed |
| **SYS‑6** complete stop | ≈ 0 residual | rest readings flat 66–67 | ✅ stopped |
| **SYS‑4 / CMP‑IMU‑1** heading ≤ yawMax | ≤ 6° | **3° peak** | ✅ confirmed |
| **SYS‑1 / CMP‑MOT‑1** max speed | commanded 2000 | vMax ≈ 440–480 mm/s | ✅ at clamp |
| **CMP‑RNG‑1** staleness bounded | est covers plateaus | 2 plateaus carried | ✅ mitigated |
| **CMP‑RNG‑2** sensors agree | waived | A−B ≈ 120 mm (unchanged) | ✅ waiver stands |

Every requirement passes on the measured data. The objective (SYS‑3) came in 16 mm *closer* than
predicted, in the safe direction for closeness and still far from contact.

---

## 3. Reconciliation of the 16 mm residual (Tenet D — explain, don't nudge)

| Quantity | Anchor (THRESH 400) | Verification (THRESH 120) |
|---|---|---|
| Rest reading | 346 mm | ~70 mm |
| True rest gap (measured) | 469 mm | 173 mm |
| **Implied sensor offset** | **+123 mm** | **+~103 mm** |
| True distance regime | ~470 mm | ~170 mm |

The sensor offset is **mildly distance-dependent**: ~123 mm far out, ~103 mm close in (≈ 0.07 mm of
offset lost per mm of approach). The GATE B prediction used the single far-field offset (123 mm),
which slightly over-predicts the gap at close range — hence the rover stopped 16 mm nearer than the
point estimate. This was anticipated and bounded by the σ_model = 15 mm term; the 16 mm residual is
≈ 1.1 σ, i.e. squarely inside the frozen band. **No parameter is being retro-fitted to the result —
the result fell where the pre-stated uncertainty said it could.**

### Refined relationship (now two-point calibrated)
With both clean points (400 → 469, 120 → 173):

> **true rest gap ≈ 1.06 · THRESH + 46 mm** (R² = 1 on two points; slope ≈ 1 confirms the 1:1
> threshold→gap invariance; the 46 mm intercept folds in the close-range offset and braking).

At `THRESH = 120` this gives 173 mm, matching measurement.

---

## 4. Lock decision and operation forecast

**Locked: `THRESH = 120 mm`, program `operation_v5` byte-for-byte as verified.** Per process, the
verified threshold is locked — not nudged closer — because:

1. The prediction was confirmed *at this threshold*; a different threshold would be unverified.
2. Going closer means extrapolating the offset **below** the verified range (< 170 mm true), where the
   offset's continued shrinkage is unmeasured and trends in the *unsafe* (closer) direction.
3. No-contact is the paramount score; 173 mm clears the 72 mm safety envelope with ~100 mm to spare.

**Operation forecast (per run, 5×):**
- Expected true gap: **≈ 173 mm**, run-to-run spread σ_run ≈ 11 mm ⇒ ~150–195 mm window.
- Contact probability: negligible (≥ ~9σ from zero).
- **Onboard per-run gap estimate = rest_reading + 99 mm** (close-range offset anchored to this
  verification: 173 − 74). This is the number I will freeze for each operation run before requesting
  the operator's ground-truth at close-out.

---

## 5. Honest note on closeness

173 mm is the *verified* closest safe stop, not the closest the chassis could physically reach. The
binding limit is the deliberate no-contact-first design: triggering on the **nearer** of two sensors
(fail-safe against a sensor reading long), where that nearer sensor reads short. Driving closer would
require either dropping that fail-safe or extrapolating below the verified offset range, both rejected
against a hard no-contact constraint. This trade is the headline limitation carried into the final
report.

**Gate C verdict: CONFIRMED. Proceed to operation — 5 runs, `THRESH = 120`, no operator input until
close-out.**
