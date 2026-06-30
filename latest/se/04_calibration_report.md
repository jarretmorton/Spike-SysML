# CALIBRATION REPORT — Wall-Approach Rover

**Document type:** REPORT (STATIC — a record of what was measured; not revised after issue).
**Version:** 1.0 · **Phase:** GATE B (calibration complete; before the verification run).
**Realises / closes against:** Requirements Specification v1.0, `02_wall_run_model.sysml`, Calibration Plan v1.1.
**Primary data source:** Run **C1 v4** (`run-20260628-230626`), the first clean straight approach; cross-checked against C1‴ (`run-20260628-225546`) and C1′ (`run-20260628-224427`).

---

## 1. Device and drive configuration (discovered, stable across all runs)

| Item | Finding |
|---|---|
| Drive motors | ports **C** (`m0`) and **D** (`m1`) |
| Forward ultrasonics | ports **A** and **B** |
| Rear ultrasonic | port **E** (unallocated; logged opportunistically) |
| Color / reflectance | port **F** (unallocated; floor reflectance ~29–32) |
| Drive base type | **mirror-mounted** — a same-sign command to both motors *rotates* the rover in place |
| Forward command signs | **`m0` (C) = −1, `m1` (D) = +1** (these drive the rover toward the wall) |
| Yaw response `YAW_DIR` | **+1** (`m0` commanded faster than `m1` ⇒ heading increases) |
| Spin polarity `SPIN_DIR` | **−1** (used only to re-square during discovery) |

Discovery is autonomous (no operator input) and reproduced identical results on three consecutive power-cycled runs, including a run where the spin-detection distance signal collapsed to zero yet the heading-based decision still resolved correctly — confirming the discovery is robust.

---

## 2. Calibrated parameter values

| Parameter | Model attribute | Value | Uncertainty (1σ) | How measured |
|---|---|---|---|---|
| Rotation constant `k` | `kRotToSpeed` | **0.44 mm/deg** (0.0246 m/rad) | ±6 % | Δrange ÷ Δodometry over cruise; distance & odometry agree |
| Max ground speed `v_max` | `maxGroundSpeed` | **0.42 m/s** (≈420–433 mm/s) | ±5 % | cruise dR/dt; cross-checked ω·k |
| Motor max rate `ω_max` | (motor `maxSpeed`) | **≈985 deg/s** | ±3 % | cruise odometry slope (commanded 2000 saturates here) |
| **Stopping overshoot `O`** | `stopOvershoot` | **≈65 mm** (threshold-referenced; see §4) | **±16 mm** | `d_trig` − resting reading at max speed |
| Deceleration `a` | `deceleration` | **≈3.5 m/s²** | ±20 % | brake-tail slope (feasibility cross-check only) |
| Forward refresh | `forwardRefresh` | **≈16 ms** | — | repeated-value cadence in raw stream |
| Loop / response period | `responseLatency` | ~6 ms loop + ≤16 ms sensor | — | folded into `O` (not used separately) |
| Heading veer (trimmed) | (CMP-3.1 margin) | **±1.3 °** over the approach | — | IMU heading, C1 v4, steering active |
| Inter-sensor offset (A−B) | (fusion calibration) | **+160 mm** (A reads longer) | ±8 mm | A−B over cruise + at rest, stable |
| Sensor bias to true gap `b` | `sensorBias` | **OPEN — TBD at verification** | — | requires operator true-gap (OI-1) |

Numbers are deliberately quoted to 2 significant figures; the sensor's ~1 cm reading granularity does not support more.

---

## 3. Sensor characterization (forward ranging)

- **B is the primary control sensor.** The two forward sensors sit at different fore/aft positions: B is ~160 mm *more forward* (closer to the wall) than A. The rover triggers on the **nearer valid reading**, which is normally B — conservative by construction.
- **A is secondary**, offset +160 mm and noticeably more prone to dropout. For verification/operation it will be **normalised** (`A' = A − 160 mm`) so that if B drops out the fallback (`A'`) is in B's frame and does **not** under-trigger.
- **Crosstalk dropouts.** Both forward sensors occasionally return 2000 mm (no echo) simultaneously — interference between the two continuously-pinging sensors. In C1 v4 a ~240 ms cluster appeared mid-approach (~590 mm). The **dropout-robust fusion** (treat ≥1900 mm as invalid; use the valid sensor; if both invalid, *hold the last valid value*; a "blind too long ⇒ stop" guard bounds blind travel) absorbed it with no spurious behaviour and the run completed normally. Echoes are expected to be *stronger* (fewer dropouts) at the closer operation ranges, but this remains a tracked risk and a contributor to the margin.
- **Static reading stability at rest is excellent:** B held 331–338 mm across six post-stop reads (±~3 mm), so the *gap* measurement itself is precise; the uncertainty lives in overshoot and bias, not in the static read.

---

## 4. Uncertainty budget (inputs to the SYS-6 margin)

The clearance margin is `m* = k_σ · RSS(σ_pred, σ_meas, σ_r2r)` (spec SYS-6; sized from data, not guessed).

| Component | Value (1σ) | Basis |
|---|---|---|
| σ_pred (model/overshoot) | **≈16 mm** | scatter in `O` from reading noise at trigger (±15 mm) ⊕ speed-driven variation of `O` (±~5 mm) |
| σ_meas (static gap read) | **≈5 mm** | at-rest reading spread (±3 mm) ⊕ residual bias-anchor uncertainty |
| σ_r2r (run-to-run) | **PROVISIONAL ≈10 mm** | only one clean stop so far; **to be re-estimated** from the verification stop + the operation runs |

`O` is **threshold-referenced**: `O ≡ d_trig − (resting reading)`, so the control law is simply **`final reading = d_trig − O`**. From C1 v4: `400 − 334 = 66 mm` ⇒ `O ≈ 65 mm`. Because the rover is at full speed at the trigger for any `d_trig ≤ ~700 mm` (start ≈ 1000 mm), `O` is a single constant at the operating speed — no extrapolation, exactly as the strategy intends.

Provisional `m*` (k_σ = 3 for the no-contact hard constraint): `3 · RSS(16, 5, 10) = 3 · 19.5 ≈ 59 mm`. This will tighten once σ_r2r is measured at verification.

---

## 5. Component unit-verification status (against the spec's CMP requirements)

| Requirement | Closes on | Status from C1 v4 |
|---|---|---|
| CMP-1.1 commanded speed ≥ max | reaching saturation | **MET** — commanded 1100+ saturates the motor at ~985 deg/s |
| CMP-2.1 forward refresh / range | refresh + start-range reading | **MET** — refresh ≈16 ms; clean reads from ~1000 mm down |
| CMP-2.2 brake overshoot `O` | measured stop | **MET** — `O ≈ 65 mm` at max speed |
| CMP-2.3 `d_trig` ≤ sensor range | trigger within range | **MET** — trigger 400 mm well inside range |
| CMP-3.1 heading drift bound | measured veer | **MET** — ±1.3° with steering (well within a squared-approach budget) |
| CMP-3.2 differential correction | instantiated & effective | **MET** — derived steering trim (gain/sign from yaw probe) holds heading; necessity confirmed by data |
| SYS-2 / SYS-4 closure (true gap & bias) | operator true-gap | **OPEN** — anchored at the verification run (OI-1) |

---

## 6. Calibration-run ledger

| Run | Outcome | Value delivered |
|---|---|---|
| C1 (spin) | mirror-mount diagnosed | drove sign-discovery redesign |
| C1′ | forward + straight confirmed; BLE dump truncated | proved discovery/translation; drove the dense-logging fix |
| C1‴ | clean cruise; crosstalk + trim-authority exposed | `v_max`, `k`, `ω_max`, refresh; drove fusion + steering fixes |
| **C1 v4** | **clean straight approach to trigger + brake** | **`O`, confirmed straightness, offset, full uncertainty inputs** |

*End of Calibration Report v1.0 (static).*
