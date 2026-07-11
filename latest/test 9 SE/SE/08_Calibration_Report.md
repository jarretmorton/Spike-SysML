# Calibration Report — Wall‑Stop Rover
**Gate:** B (static calibration closed; verification plan frozen separately)
**Run of record:** `run-20260709-214225` — clean, 3 cycles, completed with sentinel, no contact, straight.
**Supersedes priors in:** Calibration Plan v1.1 (03/04/07). Program of record: `05_run1_calibration.py`.

---

## 1. Calibrated parameters

| Symbol | Meaning | Value | Method | Evidence tier | Use |
|---|---|---|---|---|---|
| `v_max` | straight‑line max ground speed | **494 mm/s** (≈500) | ranger‑A slope; cross‑checked by encoder slope | **1 — measured, 2 methods agree** | speed/phase timing |
| `wheel_max` | wheel speed at `BASE_CMD=1000` | **957 deg/s** | encoder slope | 1 | actuator model |
| `k_gain` | ground travel per wheel degree | **0.516 mm/deg** | Δdistance/Δencoder (least‑squares); equals `v_max/wheel_max` | **1 — measured, 2 methods agree** | encoder dead‑reckoning |
| `A_floor` | ranger‑A minimum readable distance | **≈288 mm** (reads 288–298 regardless of true) | direct, all 3 cycles | 1 | forbids A close‑trigger |
| `A_linear` | ranger‑A trustworthy band | **~1000 → ~400 mm** | direct (smooth, tracks true) | 1 | A position‑fix window |
| `B_min` | ranger‑B minimum readable distance | **≤114 mm** | direct | 1 | close‑range backstop |
| `heading_hold` | worst‑case heading excursion, whole run | **[−4.5°, +3.2°]** | IMU, closed‑loop control | 1 | straightness (SYS‑5) |
| `a_decel` | passive‑brake deceleration | **~4200–5800 mm/s²** (axis‑ambiguous) | IMU accel (forward axis split X/Y) | 3 — modeled | d_stop sanity only (P3) |
| `d_stop` | coast distance, brake→rest (physical) | **OPEN; best est. 25–50 mm** | ultrasonic inflated/inconsistent; physics 21–29 | **3 → closes to 1 at verification (encoder)** | brake‑point placement |
| `c_offset` | (sensor rest reading) − (true bumper gap) | **OPEN — no onboard channel** | requires 1 operator measurement | 0 → closes at verification | absolute gap |

Two parameters remain open by design; both are closed in a single verification run (§6).

---

## 2. Sensor characterization and design impact

**Ranger A (forward primary).** Accurate far (baseline 1036 ≈ true ~1000), smooth and monotonic down to ~400 mm, then **saturates at a ~288 mm floor** — it reads 288–298 no matter how much closer the rover is. Proof: across three cycles with descending triggers (350/300/250 mm), the three rest readings were 298/288/294 — flat, not tracking the trigger — and the 250 mm trigger was **never reachable on A** (that cycle fell to the `min(A,B)` backstop). **A cannot be used to trigger or confirm a stop closer than ~300 mm.**

**Ranger B (forward secondary).** Reads much closer — down to ~114 mm — so it *can* see the operation's stopping region. But it is **noisy far** (±150 mm scatter at 600–900 mm, including an 8‑sample freeze at 709 while ~700 mm out) and throws **single‑sample high spikes** (e.g. 247/270 while truly ~120). At close range (<~450 mm) it is smooth and monotonic. High spikes are the dangerous failure mode (they make the wall look farther → could delay a brake), so B is used only as a filtered emergency backstop, never as the sole trigger.

**Close‑range nonlinearity (both).** Measured on ranger B alone, the brake→rest reading‑difference shrank across cycles: 50 → 41 → 34 mm as the brake happened nearer the wall. Same sensor, so this is not cross‑sensor scale — it is **compression near the floor**: reading change understates true motion by more the closer you are. Consequence: **ultrasonic reading‑differences do not give a trustworthy physical stopping distance**, which is exactly why `d_stop` is deferred to an encoder measurement.

**Heading / straightness.** The closed‑loop heading hold plus per‑cycle square‑up held heading within [−4.5°, +3.2°] for the entire run (vs a −26° veer before), and equalized wheel travel to 0.6% (ml −1377 vs mr +1385). Straightness is a solved problem and is reused unchanged.

---

## 3. Stopping distance `d_stop` — status

`d_stop` is the single most objective‑sensitive parameter (per Plan §0) and is deliberately **not** claimed from this run:

- **Ultrasonic estimate:** 34–52 mm, but inflated and cycle‑inconsistent due to §2 nonlinearity → rejected as a point value.
- **Physics bracket:** `v²/(2·a)` = 21–29 mm over the plausible `a` range → lower bound.
- **Held value for planning:** 25–50 mm (wide), used only to place a *conservative* verification brake point.
- **Closure:** the verification run logs **encoder angle throughout the settle window**; `d_stop = k_gain · (enc_rest − enc_brake)` is sensor‑independent and floor‑free → Tier 1. `σ_brake` comes from its cycle‑to‑cycle spread there.

---

## 4. Uncertainty budget (objective)

`σ_total = RSS(σ_brake, σ_quant, σ_slip, σ_meas, σ_offset)`

| Term | Est. (mm) | Source | Status |
|---|---|---|---|
| σ_brake | 8 | coast variability | tighten at verification (encoder) |
| σ_quant | 3 | encoder + A‑fix quantization (NOT ultrasonic, by design) | firm |
| σ_slip | 6 | wheel slip in dead‑reckoned final leg | measure at verification |
| σ_meas | 4 | operator gap measurement | firm |
| σ_offset | 4 | single‑measurement `c_offset` | firm |
| **σ_total** | **≈12** | RSS | preliminary |
| **g_target = 3·σ_total** | **≈36 mm** | k_z = 3 | preliminary |

Interpretation: aim the *nominal* operating gap near ~36 mm to retain 3σ no‑contact margin; revise once σ_brake/σ_slip are measured. Tightening the gap below this is only justified after those two terms shrink.

---

## 5. Operation‑control decision (committed)

**Rejected:** triggering the stop on either ultrasonic. A is blind < 300 mm; B is noisy/spiky and nonlinear close. Neither supports a *repeatable, contact‑safe, small* gap.

**Committed scheme — "A‑fix → encoder dead‑reckon → coast, B‑backstop":**
1. **Straight drive** at `BASE_CMD` with the proven heading hold + initial square‑up.
2. **A position‑fix:** while A is linear, take a fix at `A ≈ 450 mm` (accurate there); set the encoder origin at that instant. This removes start‑distance and early‑slip error from the final leg.
3. **Dead‑reckon final leg** on encoders: `dist_to_go = 450 − k_gain·Δenc`; command **brake** when `dist_to_go ≤ (g_nominal + d_stop)`. Encoders don't floor, spike, or compress.
4. **Coast** `d_stop` (passive brake, monotonic) to rest ≈ `g_nominal` in the A/encoder frame.
5. **Emergency backstop:** filtered ranger B (median of last 3, ignore lone high spikes) — if `B ≤ B_stop`, brake immediately. Independent of k and of the dead‑reckon; prevents contact if slip/`d_stop` is worse than modeled.
6. **Absolute gap** = (A/encoder‑frame rest) − `c_offset`; `c_offset` from the one operator measurement.

Rationale: the reliable channels (A far, encoders throughout) carry the trigger; the unreliable channels (ultrasonic close) are demoted to a safety net. This is the minimal‑risk way to reach a small gap the sensors can't directly measure.

---

## 6. Items closed at the verification run (one run, triple duty)

The verification run is required by the process anyway; it is instrumented to close everything at once:
- **Validate** the frozen predictive argument (Verification Plan) at the true operating point.
- **Measure `d_stop`** (Tier 1) via settle‑window encoder logging → also fixes σ_brake, σ_slip.
- **Bind `c_offset`** via the single costed operator gap measurement → absolute gap.

No additional characterization run is planned; if the frozen prediction is falsified, the model is re‑derived and a new Verification Plan version is issued before any re‑run.

---

## 7. Traceability
- SYS‑1 (max speed): `v_max` 494 mm/s, command at straight‑line ceiling — closed.
- SYS‑2 (no contact): guaranteed by g_target margin + independent B backstop — argued; verified at Gate C.
- SYS‑3 (minimize gap): scheme §5 targets the smallest gap the reliable channels support — pending verification.
- SYS‑5 (straightness): [−4.5°, +3.2°] measured — closed.
- Model params (`v_max`, `k_gain`, sensor floors) feed `03_wall_stop_model.py` (priors updated).
