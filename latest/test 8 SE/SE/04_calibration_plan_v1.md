# CALIBRATION PLAN — WallRun — Issue 1 (PLAN)
**Type:** PLAN (forward-looking; will be re-issued if a characterization run reveals something this version did not anticipate).
**Gate:** GATE A — produced after the requirements spec + SysML model + executable model, **before any hardware**.
**Precedence:** the Requirements Specification governs; this plan operationalises it.

---

## Section 0 — SENSITIVITY ANALYSIS (justifies everything below)

Computed by the executable model (`sensitivity_table()`), evaluated at the stated priors‑nominal operating point (v=600 mm/s, t_lat=0.06 s, a=2000 mm/s², c=15 mm, Δt_s=0.04 s, σ_S=3 mm; k=3). "Objective" = final bumper gap `G`. "Margin" = `M = k·σ_G`. Objective‑swing = ΔG when the parameter moves across its **assumed range** (linearised). M‑contribution = that parameter's prior‑σ contribution to `M`.

**Knowledge‑tier legend:** T0 = external ground truth · T1 = anchored/multi‑point onboard · T2 = single onboard sample · **T3 = prior/datasheet only (no calibration yet).** All parameters are currently **T3** (nothing measured); the column shows the *best tier reachable* by an available channel.

| Parameter | Assumed range | Objective swing / M‑contribution (mm) | Current tier → reachable | Resulting priority |
|---|---|---|---|---|
| **`v_max`** | 390–850 mm/s | **165.6** / 124.2 | T3 → **T1** (onboard slope) | **HIGH** — bind in C1 (onboard, free). Hits reaction *and* braking (quadratic). |
| **`a_brake`** | 1000–4000 mm/s² | **135.0** / 101.2 | T3 → **T1** (braking‑phase slope + IMU) | **HIGH** — bind in C1 (onboard, free). |
| **`t_lat`** | 0.02–0.12 s | **60.0** / 45.0 | T3 → **T1** (telemetry timing) | **HIGH** — bind in C1 (onboard, free). |
| **`c` (sensor offset)** | −10–40 mm | **50.0** / 37.5 | T3 → **T0 only** (no onboard channel) | **HIGH — the costed operator measurement.** 1:1 on the gap; *nothing onboard observes it.* Spend the single ground‑truth measurement here, **at the operating point** (RULE, §Source‑of‑truth). |
| `sample_interval` (Δt_s) | 0.02–0.06 s | 6.9 / 5.2 | T3 → T1 (timestamps) | MED — free byproduct of C1; sets the quantisation floor. |
| `σ_S` | 1–6 mm | 5.0 / 3.8 | T3 → T1 (rest variance) | LOW — free byproduct of C1; affects the onboard *estimate*, not the physical gap. |

**Reading of the table (this is the plan's spine).**
1. The objective is most sensitive to **`v_max`, `a_brake`, `t_lat`** — all high‑leverage *and* all onboard‑observable in a single max‑speed approach. → **one calibration run (C1) binds all three for free.**
2. **`c` is the highest‑leverage parameter with no onboard channel at all.** It is exactly where a costed operator measurement earns its price, and the source‑of‑truth RULE independently requires the *scored* quantity (the gap, which `c` drives) to be validated against tier‑0 ground truth **at the operating point**. → **the single operator measurement is spent on a near‑wall, max‑speed stop.**
3. `Δt_s`, `σ_S` are low‑leverage and fall out of C1 at no extra cost.
4. **Uncalibrated, the model can only promise `M ≈ 172 mm` clearance** (σ_G ≈ 57 mm at priors). After C1 collapses σ_v/σ_t/σ_a and the operator anchors σ_c, the projected σ_G ≈ **11–12 mm → M ≈ 34 mm** (k=3). Post‑calibration the leading residuals become **quantisation (`v·Δt_s/√12`) and `a_brake`** — noted for the verification design. *(This sweep ranks where to look; it does not validate the model — only the operating‑point ground‑truth anchor and the impossible‑reading rule do that.)*

---

## Section 1 — Calibration input list

### 1a. Model‑completion parameters (needed to predict; not a requirement threshold)
| Param | SysML | Bind by |
|---|---|---|
| `v_max` | `vMax` | C1 constant‑speed phase (ultrasonic Δ`S`/Δt); cross‑check motor‑angle |
| `t_lat` | `tResponse` | C1 timing: interpolated true threshold crossing → decel onset (captures mean sampling delay; no double‑count with quantisation σ) |
| `a_brake` | `aBrake` | C1 braking‑phase velocity slope; cross‑check IMU forward accel |
| `c` | `sensorOffset` | **C2 operator ground truth at operating point** |
| `σ_S`, `Δt_s` | `rangeNoise`,`sampleInterval` | C1 rest variance / timestamp spacing |
| `d_min`,`d_max` | `dMin`,`dMax` | C1 close‑range behaviour + datasheet |
| `σ_v,σ_t,σ_a,σ_c` | (uncertainties) | fit residuals (C1) / operator precision (C2) |

### 1b. Requirement‑TBD register (from spec §6, bound here)
TBD‑1…TBD‑12 as tabled in the spec. Binding activities: **C1** → TBD‑1,2,3,5,6,8,9,10,12; **C2 (operator)** → TBD‑4; **derivation post‑C1/C2** → TBD‑7 (σ_D from quantisation + velocity noise; drift controlled between runs, D3), TBD‑11 (`k`,`M`,`G_target` from calibrated σ_G — set in the Verification Plan).

---

## Section 2 — CHARACTERIZATION METHOD

### 2.1 Channel catalog & cross‑sourcing (every run logs every catalogued channel bearing on the quantities it touches)

| Quantity | Ch‑1 (rank 1) | Ch‑2 | Ch‑3 | Binding run | Range hand‑off |
|---|---|---|---|---|---|
| Distance to wall | Ultrasonic **A** `distance()` | Ultrasonic **B** `distance()` | — | C1 (both logged) | below `d_min` at rest → hand to model‑predicted (FUN‑4) |
| Forward speed `v` | Ultrasonic Δ`S`/Δt (gap‑units) | Motor angle × wheel const / Δt | IMU accel ∫ (weak) | C1 | ultrasonic saturates >~2 m; irrelevant here (≤1 m) |
| Deceleration `a_brake` | Ultrasonic Δ`v`/Δt (braking) | **IMU fwd accel (direct)** | Motor speed‑readback slope | C1 | — |
| Heading / straightness | IMU `heading()` | IMU `angular_velocity` ∫ | — | C1 | — |
| Final gap `G` / offset `c` | **Operator ground truth (T0)** | Ultrasonic rest `S − c` (T1/T2) | Model‑predicted `G_target` | **C2** | rest `S` invalid <`d_min` → predicted |

Disagreement between channels is the **fault‑agnostic** detector (B1): never assume which channel is wrong — let the disagreement reveal it. A physical‑plausibility bound is placed on every logged channel (see §Anomaly bounds) so impossible readings surface automatically.

### 2.2 Source‑of‑truth hierarchy (trust order, stated up front)
**T0 external ground truth (operator measurement) > T1 anchored / multi‑point onboard calibration > T2 single onboard sample > T3 prior/datasheet.**
- A lower tier **never silently overwrites** a higher‑tier value; a later sample disagreeing with a higher‑confidence value is a **discrepancy to diagnose** (low draw? range‑dependence? glitch?), not grounds to re‑fit the constant.
- **RULE (objective):** a sensor value that drives a scored quantity — the gap above all — is a **HYPOTHESIS until confirmed against an independent higher‑tier source at the operating point.** `c` (hence `G`) is therefore anchored by the T0 operator measurement at a near‑wall, max‑speed stop (C2). On any disagreement your judgment finds significant, or any physically impossible reading, **escalate** to better data rather than arbitrating between suspect channels.

### 2.3 Test‑like‑you‑fly run construction (the characterization program is a strict SUPERSET of the operation program)

Common skeleton (identical across C1/C2/verification/operation): construct each device **once** at top; a single non‑blocking control loop `run(max) → poll distance → on trigger, brake()`; a pre‑allocated telemetry buffer written **on** the hot path only for the essentials (timestamp + both forward distances), with all extra channels (IMU heading/accel, motor angles) written to the buffer too but **dumped after the motors stop**; `try/finally` guaranteeing motors stop and the `{"event":"end"}` sentinel; loop paced with `wait(ms)`. Discovery/creep logic and extra logging live at **startup / off the hot path**, never woven into the trigger loop.

**Safety rails on every run:** absolute distance‑floor emergency brake (`if min(A,B) < FLOOR: brake`), a time cap, and — in C1 only — a conservative trigger. A characterization contact is a **re‑run risk, not a scoring failure** (the no‑contact hard constraint governs the operation task); the rails make hard contact unlikely.

**C1 — dynamics calibration + discovery (max speed, conservative trigger).**
- *Discovery (startup, logged):* type‑probe ports (Motor / UltrasonicSensor / ColorSensor, each constructed once) → identify the two drive motors, the three ultrasonics, the color sensor. Then a brief **low‑speed forward creep**: the ultrasonics whose readings **decrease** are the forward pair (A/B, and they should agree ≈ wall distance); the one that does not is the rear (drops out). The motor sign that makes the forward distance decrease with heading ≈ constant is "forward". **C1 reports the port map + forward sign**, which C2/verification/operation hard‑code (constructed once each; no creep on scored runs → clean test‑like‑you‑fly).
- *Maneuver:* accelerate to max, hold, and brake on an ultrasonic trigger set **generously high (≈ 500 mm)** with a **floor ≈ 120 mm** and a **≈ 3 s cap**. Realistic `D_stop` ≈ 100–150 mm ⇒ stops ≈ 350 mm from the wall (safe); the floor nets the unlikely extreme.
- *Binds:* `v_max` (constant‑phase slope), `a_brake` (braking slope + IMU accel), `t_lat` (crossing→decel onset), **`D_stop` directly at max speed** (trigger→rest travel — zero‑extrapolation, calibration point = operating point), `Δt_s`, `σ_S` (rest dwell), heading drift, A/B agreement, close‑range behaviour. **No operator input.**

**C2 — operating‑point stop + the single operator measurement (max speed, near‑wall).**
- Trigger set from C1 dynamics + `c` prior to target a **deliberately conservative** gap (≈ 60–80 mm; wide because `c` is still T3, σ_c≈12.5 mm ⇒ 2σ≈25 mm ⇒ actual gap ≈ 45–95 mm, no contact). Identical skeleton to operation.
- Rover stops, dwells, logs rest `S` (both sensors). **Operator measures the physical gap `G` once** → `c = S_rest − G`. This **anchors `c` (T0) and validates the objective at the operating point** (the RULE), closing the objective's ground‑truth check. This is the **only** operator data exchange of the whole build.

**Verification run (step 6, dress rehearsal of the LOCKED operation program).** With `c` anchored and dynamics calibrated, the operation `d_trig = c + D_stop + M_op` is finalised (M_op tightened, ≈ 34 mm). The verification run executes that exact locked program to test the **frozen** prediction **onboard** (rest `S − c` vs predicted `M_op`); no new operator input. Falsification → diagnose → re‑derive → new frozen Verification Plan version → re‑run (each counts).

*Why C1 and C2 are distinct (and not merged):* a single conservative trigger cannot be both worst‑case‑safe and near‑wall, because the pre‑C1 dynamics uncertainty spans `D_stop` ≈ 27–460 mm. C1 must first collapse that uncertainty; only then can C2 stop near the wall safely. *Why the operator measurement is at C2 (near‑wall), not C1:* the RULE requires the gap validated **at the operating point** — a close‑range, max‑speed stop — which exercises the sensor's near‑`d_min` regime that a far stop would not.

**Run budget (program‑count score):** C1 + C2 + verification = **3** characterization runs (+ re‑runs only on falsification). **Operator measurements = 1** (C2). *Lower‑run alternative for your consideration:* collapse C2 and the verification run by locking the operation program on the **prior `c`** (operation ≡ verification), spending the operator measurement at that single near‑wall run — **2** characterization runs, but the operation gap then carries the full prior‑`c` uncertainty (`M ≈ 50 mm`, looser) and the anchor only validates rather than tightens. I recommend the 3‑run path (tighter, properly exploits the anchor); tell me if you prefer the 2‑run trade.

### 2.4 Anomaly plausibility bounds (logged per channel; impossible ⇒ unconditional escalate)
Distance ∈ [0, 2500] mm and monotone‑non‑increasing on approach (a rest reading *farther* than the trigger reading is impossible → escalate). |heading drift| < 45° over a ≤1 m run. Forward accel sign during braking opposes motion. A/B agreement within a few×σ_S. Any breach → Anomaly Report (free), classified via the executable model; escalate unconditionally on impossibility.

---

## Section 3 — VERIFICATION SUPPORT

### 3.1 How the calibration runs unit‑verify the CMP (lowest‑level) requirements
| CMP | Unit‑verification evidence (from calibration) | Method |
|---|---|---|
| CMP‑1a/1b (motors fwd at max) | C1: commanded ≥ rated ceiling (`run()` clamps); forward sign confirmed by distance‑decrease during creep | Test + inspection |
| CMP‑1c (brake→0, a_brake) | C1: residual speed ≈ 0 at rest; `a_brake` from braking slope, cross‑checked by IMU accel | Test |
| CMP‑2a (ultrasonic A: range/noise/rate) | C1: σ_S from rest variance ≤ σ_S_max; Δt_s from timestamps ≤ Δt_s_max; valid window mapped | Test |
| CMP‑2b (ultrasonic B: indep., agrees Δ_AB) | C1: |A−B| over approach ≤ Δ_AB | Test |
| CMP‑5 (IMU yaw + accel) | C1: heading drift logged (bounds SYS‑6); IMU accel present and sign‑correct (cross‑source a_brake) | Test + inspection |

CMP unit verification **gates** the integrated (verification) run (C1 tenet).

### 3.2 Structure of the eventual verification argument (predictions left OPEN here)
The frozen Verification Plan (GATE B) will present the executable model's **EVALUATE()** roll‑up at the committed (locked‑operation) configuration and bound values — the exact satisfy/require set in the SysML STRUCTURAL CHECKS block:

- HARD, evaluable: **SYS‑1** (finalClearance ≥ 0), **SYS‑3** (predictedClearance ≥ M), **SYS‑4** (commanded ≥ ceiling), **SYS‑6** (headingDrift ≤ θ_max), **SYS‑7** (finalSpeed ≤ v_stop_tol), **FUN‑4** (|G_est−G| ≤ tol), **CMP‑1a/1b/1c/2a/2b**.
- Graded/functional‑parent (excluded from pass/fail): SYS‑2, SYS‑5, FUN‑1/2/3/5, CMP‑5.
- Roll‑up chain per requirement: *requirement → SysML parameter → Python variable → calibrated value → predicted margin* → predicted PASS/FAIL. The **prediction** (numeric G, σ_G, M, and each PASS/FAIL) is filled and **frozen** at GATE B, then tested by the verification run. The **objective (SYS‑2/3)** is closed at GATE C on the evidence that its predicted gap was validated against the C2 operator ground truth at the operating point.

---

## Section 4 — What I need from you at this gate
Please review: the priors/ranges in §0 (they are an input to your review), the source‑of‑truth hierarchy and the decision to spend the single operator measurement on `c` at a near‑wall stop (C2), the 3‑run vs 2‑run trade (§2.3), and the C1 safety rails. **No hardware will be touched until you approve this plan.** On approval, I will ask the readiness handshake before the first flash (C1).
