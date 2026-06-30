# VERIFICATION REPORT — Wall-Approach Rover

**Document type:** REPORT (STATIC).
**Version:** 1.0 · **Phase:** GATE C (verification complete; before the scored operation runs).
**Tests:** the frozen prediction in Verification Plan v1.0.
**Data:** verification run `run-20260628-232259` + operator measurement OI-1.

---

## 1. Result against the frozen prediction — **PASS**

| Quantity | Frozen prediction | Actual | Verdict |
|---|---|---|---|
| Resting B reading | 135 mm, 95 % interval **[102, 168]** | **166 mm** | **PASS** (within interval) |
| Heading through approach | within ±3° | ≤ ±2.6° (approach), 3.0° at settle | PASS |
| Contact | none | none (stopped well clear) | PASS |

The control law `final reading = d_trig − O` predicted the stop in reading-space and the result fell inside the pre-registered interval, at the high end (actual overshoot a little smaller than modelled). The approach was straight and the dropout-robust fusion absorbed a mid-approach cluster without incident. **The frozen prediction is not edited; it passed.**

---

## 2. Operator measurement OI-1 — and the finding that changes operation

At the stop, sensor **B read 166 mm**, sensor **A read 288 mm**, and the operator-measured **true gap (wall → frontmost point) = 264 mm**.

A sensor cannot physically read *less* than the distance to the nearest point of the rover, so:

- **Sensor A is the accurate forward sensor.** A = 288 vs true 264 ⇒ A reads **+24 mm** (consistent with being mounted ~24 mm behind the front edge — a fixed geometric offset).
- **Sensor B is faulty/offset.** B = 166 vs true 264 ⇒ B reads **−98 mm** (a large negative offset; impossible from geometry, so it is a sensor error).

This **reassigns the primary sensor from B to A.** B was treated as primary only because it read smaller — but it read smaller because it *under-reads*, not because it is more forward. Cross-checking against the start (the rover, placed at ~1 m, gave B ≈ 906 and A ≈ 1022) shows the same ~+24 / −98 pattern and that the distance **scale** is correct (≈738 mm of travel by both sensors and by true gap) — only B's **offset** is wrong.

**Consequence:** the rover has been stopping ~100 mm *farther* from the wall than B indicated. There is substantial room to stop closer — but only by triggering on the **accurate** sensor (A), which also reads higher and therefore stays above its minimum range at the close distances where B would read near-zero and go blind.

---

## 3. Re-derived operation model (anchored on this run's data)

Operation triggers on the accurate sensor **A** (raw reading), with B retained only as a corrected dropout backup. Anchored at the verification brake point (A_raw ≈ 335 at brake → true gap 264 at rest):

> **resting true gap = A_trig − 72 mm**
> (= [A_trig − 24, true gap at the trigger] − [≈48 mm physical overshoot])

The physical overshoot (true distance travelled from brake command to stop) is **≈48 mm** and is sensor-independent and repeatable; A's accuracy is a fixed +24 mm. For a target stop gap `T`: **`A_trig = T + 72`**.

---

## 4. Margin and proposed operation setpoint

`m* = k_σ · RSS(σ)` with the components re-estimated from the campaign:

| σ component | Value | Basis |
|---|---|---|
| σ_overshoot | 16 mm | brake-region scatter |
| σ_bias (A) | 12 mm | single true anchor; risk that A's +24 offset drifts with range |
| σ_r2r | 15 mm | provisional; the 5 runs will reveal it |
| σ_meas | 5 mm | at-rest reading + ruler |
| **RSS** | **≈26 mm** | |

**Recommended (k_σ = 3, for the no-contact hard constraint): target true gap ≈ 78 mm ⇒ `A_trig = 150 mm`.** Predicted stop ≈ 78 mm true gap on every run, with per-run contact probability ≈ 0.1 %. A more aggressive option (k_σ = 2.5 ⇒ ~65 mm gap, `A_trig = 137`) is available if you want to trade a little safety for closeness; I recommend the 3σ setting for the first runs and can tighten later if the runs prove repeatable.

At `A_trig = 150`: A reads down to ~150 at the trigger and ~102 at rest — comfortably within A's reliable range (B would be near-blind here, which is exactly why A must be primary).

---

## 5. Operation program (changes from the verified core)

The control **core** — drive at max, derived gyro heading-trim, brake at a range threshold, hold — is **unchanged** from what flew in verification. Three changes, all justified above:

1. **Trigger on A (corrected) as primary; B as corrected backup.** `true ≈ A − 24`; `B − (−98)` i.e. `B + 98` only if A drops out. Trigger threshold `A_trig = 150` (⇒ ~78 mm predicted gap). The reassignment to the accurate sensor is covered by the 3σ margin.
2. **Hardcode the proven discovery** (motors C=`m0`/D=`m1`, signs −1/+1, forward A/B, yaw +1). This removes the per-run nudges and re-squaring — which is what pushed the verification run to the 25 s timeout and added pre-run wander — making each scored run **deterministic, fast (~12 s), and started from the true ~1 m line**. (The operator squares the rover; the program resets heading at the start.)
3. **Operation run timeout raised to 35 s**, dump kept downsampled and finals-first.

This remains *test-like-you-fly*: the scored runs fly the identical control core, now reading the accurate sensor, with fixed facts hardcoded instead of re-derived.

---

## 6. Recommendation for GATE C

Proceed to the **five scored operation runs** with `A_trig = 150 mm` (predicted ~78 mm true gap, 3σ no-contact). I will: lock the program, do the flash-readiness handshake before each run, monitor each run's resting A-reading for consistency (and re-derive if any run deviates), and at close-out **first** freeze my own per-run gap estimates, **then** request the operator's true-gap for all five, **then** issue the Final Report. If you would prefer one confirmation pass of the A-primary control before the scored runs, I can do that instead — your call at this gate.

*End of Verification Report v1.0 (static).*
