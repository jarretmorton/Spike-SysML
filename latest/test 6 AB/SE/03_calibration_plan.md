# Calibration Plan — Wall-Approach Task

**Document type:** **PLAN** (forward-looking; revised and re-issued as a new version — prior versions retained — after any characterization run that reveals something this version did not anticipate).
**Version:** PLAN v1
**Standards / method:** NASA SP‑2016‑6105 (V&V framing) · tenets A–D (esp. A6 RSS margin, B1 log-every-channel, B2 trusted-reference-first, B3 batch/minimize-programs, B4 costed human measurement, C1 unit-before-integration, C2 argue-before-run) · CHARACTERIZATION METHOD (channel catalog, source-of-truth hierarchy, test-like-you-fly).
**Realises:** `01_requirements_and_effectors.md` (spec, source of truth) · `02_wallrover_model.sysml` (formal model). Symbols (δ, D, m, k, σ, θ_max, ε_acc …) are defined there and reused here.

---

## 0. Plan status & budget

| Item | Planned value |
|---|---|
| Characterization program runs (score #1) | **2** — Run 1 (calibration, all units) + Run 2 (verification). The verification run is a characterization program and is **not** one of the 5 scored operation runs. |
| Outside-input actions (score #2) | **1** — the single δ ground-truth anchor (§3), maximally batched. |
| Hardware state at this gate | **None flashed.** No `flash_program` until GATE A is reviewed **and** the readiness handshake returns an explicit go-ahead. |

**Why two programs suffice.** Every quantity the model needs is either (a) measurable in one instrumented max-speed approach that is also the operation hot loop (Run 1 — tenet B3 batching), or (b) the offset δ, which no onboard channel can observe (one operator anchor — B4). Run 2 then tests the frozen prediction on the locked program. Nothing forces a dedicated repeat run.

---

## 1. Calibration input list

Two classes feed calibration: **model-completion parameters** (free params the model must predict with, that no requirement names) and the **requirement-TBD register** (TBDs living inside requirements). Each row names the **binding activity** — the specific calibration channel/step that closes it. (Register content mirrors `01` §3; here every entry gains its producing activity and evidence tier.)

### 1a. Requirement-TBD register → binding activity

| TBD | Symbol | In req. | Binding activity | Evidence tier |
|---|---|---|---|---|
| TBD‑1 | ε (observed ranger error) | CMP‑1 | Static noise floor (precision) + operator anchor (accuracy), Run 1 Ph1/anchor | onboard multi-sample + external anchor |
| TBD‑E | ε_acc (accept limit) | CMP‑1 | **Set** from margin budget so ε_acc ≪ m (design choice recorded at GATE B) | design, frozen w/ margin |
| TBD‑2 | ω_max (motor ceiling) | CMP‑3 | `motor.speed()` read-back at max command; cross: encoder Δangle/Δt, Run 1 Ph2 | onboard, cross-sourced |
| TBD‑4 | v_max (cruise ground speed) | CMP‑3 | Ranger slope Δs/Δt (primary); cross: IMU‑accel ∫, encoder×kRot, Run 1 Ph2 | onboard multi-point, 3-channel |
| TBD‑5 | D (stopping distance) | CMP‑4 | `s_trig_cal − s_rest` (primary); cross: encoder post-command travel, IMU‑accel ∫∫, Run 1 Ph2 | onboard multi-point, 3-channel |
| TBD‑7 | headingDrift | CMP‑5 | IMU `heading()` over approach; cross: differential-encoder implied heading, Run 1 Ph2 | onboard, cross-sourced |
| TBD‑θ | θ_max (drift limit) | SYS‑4/CMP‑5 | **Set** from geometry (drift that keeps ranger normal & bumper the first-contact point at operating range) | design (geometry) |
| TBD‑m | m (contact margin) | SYS‑2/MRG‑1 | `kSafety·RSS(σ)` — **frozen in the Verification Plan** (GATE B) | derived, frozen |

### 1b. Model-completion parameters → binding activity

| Param | Symbol | Role | Binding activity | Evidence tier |
|---|---|---|---|---|
| kRot | k (m/rad) | `RotationToSpeed` v=ω·k | ranger-slope ÷ achieved ω across the Ph2 ramp (multi-point) | multi-point onboard |
| decel | a (m/s²) | `StoppingDistance` braking term | back-solve from measured D and v — **feasibility cross-check only** (D is measured directly) | derived |
| tChain | on-hub latency | reaction time | command-issue → motion-onset (first encoder Δ) timestamp gap, Run 1 | onboard timestamps |
| tSample | ranger refresh | reaction time | ranger value-change interval (consecutive distinct readings), Run 1 | onboard timestamps |
| δ | sensor offset (face→bumper) | s ↔ g conversion; **safety-critical** | **operator ground truth** at Run‑1 rest (§3) — no onboard channel observes it | **external (top tier)** |
| σ_pred | stop-prediction σ | MRG‑1 | residual of D across its 3 channels (Run 1) + the Run‑2 sample | derived |
| σ_meas | clearance-measurement σ | MRG‑1 | `== rangerError` (model `measLink`) — the CMP‑1 accuracy | onboard vs anchor |
| σ_run | run-to-run σ | MRG‑1 | D spread across Run 1 + Run 2; floored by a physical bound if only 2 samples | multi-run |
| kSafety | margin multiplier | MRG‑1 | **set** from the no-contact assurance target (want all 5 runs clean) — frozen at GATE B | design, frozen |

**Tier discipline (source-of-truth):** a value set at a higher tier is **not** silently re-fit to a later single sample. δ (external) outranks every onboard value; a later onboard reading disagreeing with δ is a discrepancy to diagnose, not grounds to move δ.

---

## 2. Characterization-run design

### 2.1 Channel catalog & cross-sourcing

For every quantity to calibrate, **all** independent onboard channels are enumerated (from the rover inventory, not just the obvious one), ranked by directness/confidence, and traced to a binding run. Every Run‑1 phase logs **every** catalogued channel bearing on the quantities it touches (B1); disagreement is the **fault detector** and is fault-agnostic (never assume which channel is wrong).

| Quantity | Channels (independent), ranked by directness | Binding run |
|---|---|---|
| **Port/device map** | ① construct-and-catch per `Port.A–F` (type identity) | Run 1 Ph0 |
| **Forward-pair identity** | ① two rangers reading ~start distance & agreeing = forward; the outlier = rear ② geometry of readings under motion (forward pair shrinks on approach) | Run 1 Ph1 → confirmed Ph2 |
| **Motor forward sign** | ① distance-feedback under a low-speed nudge (decreasing range = forward) ② IMU heading swing (opposed signs → rotation) ③ encoder sign consistency | Run 1 Ph1.5 |
| **cruiseSpeed v_max** | ① ranger slope Δs/Δt (direct ground truth of ground speed) ② encoder angular rate × kRot ③ IMU forward-accel integrated | Run 1 Ph2 |
| **motorCeiling ω_max** | ① `motor.speed()` read-back ② encoder Δangle/Δt | Run 1 Ph2 |
| **kRot (m/rad)** | ① ranger-slope ÷ achieved ω (multi-point over ramp) ② nominal wheel-radius/gear (weak, sanity only) | Run 1 Ph2 |
| **D (stopping distance)** | ① `s_trig_cal − s_rest` from the forward ranger ② encoder travel after stop command ③ IMU forward-accel double-integrated | Run 1 Ph2 |
| **headingDrift** | ① IMU `heading()` ② differential-encoder implied heading (Δθ from wheel-travel difference) ③ IMU yaw-rate integrated (secondary) | Run 1 Ph2 |
| **rangerError / noise floor** | ① static repeated reads → precision (variance) ② operator anchor → accuracy (bias) | Run 1 Ph1 + anchor |
| **tChain / tSample** | ① command-issue → first encoder motion (tChain) ② ranger value-change interval (tSample) | Run 1 Ph2 |
| **δ (sensor offset)** | *(no onboard channel — see drop-outs)* → operator anchor | §3 (outside input) |

**Channel drop-outs (absence by traceability, at the channel level):**
- **ReflectanceSensor `floor`** — observes no calibrated quantity on a uniform floor (cannot sense wall range, speed, or heading). **Dropped**; not logged.
- **Rear ranger** — observes no needed quantity (forward-only task). Read **once** in Ph1 solely to *confirm its identity* (so it is not mistaken for a forward channel); carries **no calibration** thereafter.
- **δ has no onboard observer** — this is *why* it is the one outside-input request; recorded here so the gap in onboard coverage is explicit, not silent.

### 2.2 Source-of-truth hierarchy (trust order, stated up front)

> **external ground truth (operator)  >  anchored / multi-point onboard  >  single onboard sample**

A lower tier **never** silently overwrites a value a higher tier set; a later sample disagreeing with a higher-confidence value is a **discrepancy to diagnose** (low draw? range-dependence? glitch?), not grounds to re-fit the constant. Each calibrated value is carried with its evidence basis (samples / reference / tier).

| Tier | Values landing here | Evidence basis |
|---|---|---|
| **1 — external** | δ (sensorOffset); it also anchors ranger **accuracy** | one operator measurement + concurrent onboard ranger read |
| **2 — anchored / multi-point onboard** | cruiseSpeed, kRot, D, motorCeiling, headingDrift, ranger **precision** | multiple channels × multiple time-samples within Run 1 (cross-sourced) |
| **3 — single onboard sample** | tChain, tSample (and any value only one channel yields) | single-pass onboard; **flagged**, cross-checked where possible |

### 2.3 Test-like-you-fly run construction — **Run 1 (single program)**

**Invariant (CHARACTERIZATION METHOD part 3):** the characterization program is a **strict superset** of the operation program — *identical* control loop, trigger, and buffer skeleton. All extra characterization logging is deferred **off the hot path**: written to a **pre-allocated buffer** and dumped **after the motors stop**, never woven into the loop. This keeps operational timing fidelity, so what Run 1 calibrates transfers to operation with no re-anchor. `try/finally` guarantees motors stop and the `{"event":"end"}` sentinel is always emitted.

| Phase | Motion | Purpose & measured quantities |
|---|---|---|
| **Ph0 — enumerate** | none | Construct each of the 6 devices **once**; per `Port.A–F` build the type map via construct-and-catch (expect 3 ultrasonic / 2 motor / 1 color). Devices claim ports on construction — construct once, reuse. |
| **Ph1 — static** (~1 s, motors off) | none | Read all three ultrasonics: identify the **forward pair** (~start distance, agree) vs the **rear** outlier. Capture **noise floor** (per-channel variance), initial distance, heading≈0, accel bias. |
| **Ph1.5 — polarity nudge** (low speed, brief) | tiny | Determine **forward sign per motor** by distance feedback (+heading): both `+` → range **decreasing** = forward/same-sign; range **increasing** = both reverse; heading **swings** = opposed → opposite signs. **Confirm via distance feedback before ramping.** |
| **Ph2 — logged max approach** (the operation hot loop) | **max** | Command max (`run(large)` clamps to ceiling). Hot loop appends `(t, d_primary=min(fwd pair), d_secondary, heading, encL, encR, accel)` to the preallocated buffer. **Trigger stop** when `min(forward) ≤ s_trig_cal` (**SAFE** ≈ 450 mm) with a **hard-floor failsafe** (≈ 250 mm) **and** a time cap. Coast; keep logging ~1 s to settle; then dump buffer + sentinel. |

**One pass, everything:** Ph2 yields the port map (confirmed), cruiseSpeed (3 channels), D (3 channels), headingDrift (2–3 channels), and the noise characterization — the full unit-verification data set in a single instrumented run.

**Safety of the calibration trigger:** `s_trig_cal` is deliberately **far** from the wall, so Run 1 **cannot contact**. D is measured as `s_trig_cal − s_rest` at that safe trigger (δ-independent, since D is a displacement). The **operation** trigger is computed *later* as `s_trig = D + δ + m` (never used in Run 1).

**Post-run (both phases, uncounted):** `get_telemetry` as a **downsampled/summary** view (not the raw stream), then render **forward-distance-vs-time** as a chart.

---

## 3. Outside-input request (score #2) — the single δ anchor

**Request (one action, maximally batched — B4):** at Run‑1 rest (~350 mm from the wall), ask the operator to **measure the true gap** from the rover's **front-most point to the wall**, and in the *same* request **confirm the rover is squared up**. Onboard concurrently captures the ranger reading `s_rest` at that instant.

- **Binds:** `δ = s_rest − g_measured` (Tier‑1 external). This also anchors ranger **accuracy** (bias vs the known g).
- **Batched cross-checks around the one request:** squareness confirmation; the concurrent onboard `s_rest`; the static noise floor from Ph1 (precision) combined with this anchor (accuracy) to close CMP‑1.
- **Justification (why human measurement is warranted, B4):** **no onboard channel observes δ** — the ranger measures its own face-to-wall distance, never the face-to-bumper offset. Without δ the s→g conversion is unknown, so the gap cannot be safely minimized (the design law `s_trig = D + δ + m` needs it). This is exactly the case where an onboard channel cannot close the loop.
- **Count:** **1** outside-input action. (The operator's power-cycle/reposition/square-up between runs remain free, uncounted actions.)

---

## 4. Verification support

### 4.1 Unit verification of the CMP (single-effector) requirements by calibration

Unit verification **closes in the Calibration Report (GATE B)**; the integrated requirement (STP‑1 → SYS‑2) closes later, at the Verification Report (GATE C). Each CMP is verified by a Run‑1 activity against its bound:

| CMP requirement | Bound (from model) | Calibration activity that verifies it | Closes at |
|---|---|---|---|
| **CMP‑1** RangerAccuracy | `rangerError ≤ ε_acc` | Static noise floor (precision) + operator anchor (accuracy) | GATE B |
| **CMP‑3** MotorReachesCeiling | `maxCmdSpeed ≥ motorCeiling` | `motor.speed()` read-back at max, cross-checked by encoder Δangle/Δt | GATE B |
| **CMP‑4** BrakeWithin | `stopDistance ≤ stopDistanceBudget` | D from ranger/encoder/accel during the Ph2 stop; budget from runway feasibility | GATE B |
| **CMP‑5** ImuDriftBound | `headingDrift ≤ θ_max` | IMU heading vs differential-encoder implied heading over Ph2 | GATE B |
| **STP‑1** StopWithinClearance | `finalClearance ≥ contactMargin` | **Not** unit-verified — **integrative**, closed by the verification run | GATE C |

### 4.2 Structure of the eventual verification argument (**predictions LEFT OPEN**)

The pre-run artifact is the `satisfy`/`require` roll-up of `02_wallrover_model.sysml` evaluated against calibrated values. Its **structure** is fixed now; the **numbers are filled at GATE B** in the Verification Plan and **frozen before Run 2**. Skeleton with slots (`___`):

**Step 1 — bind calibrated values (GATE B):**
```
motorCeiling = ___      kRot = ___        cruiseSpeed = motorCeiling·kRot = ___
tChain = ___            tSample = ___     tResponse = tChain + tSample = ___
decel = ___ (feasibility)                 stopDistance D = ___   (measured, 3-channel)
sensorOffset δ = ___    (operator, Tier 1)
rangerError = ___  → σ_meas = ___         σ_pred = ___      σ_run = ___     kSafety = ___
rssUncertainty = kSafety·√(σ_pred² + σ_meas² + σ_run²) = ___
contactMargin m = ___   (≥ rssUncertainty)
triggerDist s_trig = D + δ + m = ___      predicted finalClearance = m = ___
```

**Step 2 — evaluate each requirement's inherited constraint (PASS/FAIL slot):**
| Requirement | Constraint | Evaluates to |
|---|---|---|
| MRG‑1 MarginFloor | `contactMargin ≥ rssUncertainty` | ___ |
| CMP‑1 RangerAccuracy | `rangerError ≤ ε_acc` | ___ |
| CMP‑3 MotorReachesCeiling | `maxCmdSpeed ≥ motorCeiling` | ___ |
| CMP‑4 BrakeWithin | `stopDistance ≤ stopDistanceBudget` | ___ |
| CMP‑5 ImuDriftBound | `headingDrift ≤ θ_max` | ___ |
| SYS‑2 / STP‑1 (integrative) | `finalClearance ≥ contactMargin` | **predicted:** finalClearance = m > 0 → no contact at gap ≈ ___ |

**Step 3 — the frozen prediction Run 2 tests:** *"The locked operation program, run once from the full start distance, stops with **no contact** at a final gap of **≈ m** (= ___ mm)."* Every `___` is filled at GATE B and frozen before the verification run; if Run 2 falsifies it, a **new** Verification Plan version is derived (the frozen one is retained) and re-run — the frozen version is never edited.

---

## 5. Operation-program construction (forward reference)

The **operation program** is assembled after calibration and **locked** before Run 2:
- **Hard-codes** the discovered port map and motor polarity (physical wiring persists across power-cycles, so this is not re-discovered), and the computed trigger `s_trig = D + δ + m`.
- **Omits** the Ph1.5 polarity nudge (it starts from the full ~1000 mm start line).
- **Hot loop identical** to Run‑1 Ph2 (test-like-you-fly is satisfied: all discovery/logging that differs is off the hot path — Ph0/Ph1/Ph1.5 setup and the deferred buffer dump).
- **Run 2** executes this locked program **once** as the verification run (tests the frozen prediction). The **5 scored operation runs** re-flash the *same* locked program unchanged.

---

## 6. Plan-revision triggers (when this PLAN is re-issued as v2)

This PLAN is revised (new version, prior retained) if a characterization run reveals something v1 did not anticipate — e.g.: the three D-channels disagree beyond tolerance (fault to localize before trusting D); motor polarity is ambiguous after the nudge; a forward ranger drops out / saturates near the wall (hand off to the other channel; re-plan trigger); D + δ + margin does not fit the runway with clearance (re-derive the feasibility budget / trigger); heading drift exceeds θ_max (add a heading-hold correction to FUN‑4); or the δ anchor and onboard `s_rest` are mutually inconsistent (diagnose before binding δ). Each trigger → **diagnose the responsible parameter → re-plan → re-issue**, never an empirical tweak of a frozen artifact.
