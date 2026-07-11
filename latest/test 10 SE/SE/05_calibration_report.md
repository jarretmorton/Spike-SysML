# Calibration Report — Wall-Approach Rover
**Document type:** REPORT (backward-looking, static — never edited once issued) · **Version:** v1
· **Gate:** GATE B · **Basis:** runs CHAR-1 (`run-20260710-233646`) and CHAR-1b
(`run-20260711-000237`)

This report records what the hardware actually is and does, as measured. It supersedes the
priors in the Calibration Plan where they conflict. Predictions remain the model's job; this is
evidence.

---

## 1. Platform configuration (discovered, run CHAR-1b)

| Item | Value | How determined |
|------|-------|----------------|
| Motors | port **C** (m0), port **D** (m1) | construct-and-catch probe |
| Front ultrasonics | **us0 = port A**, **us1 = port B** | two mutually-closest standoffs ≈ setup distance |
| Rear ultrasonic | **us2 = port E** | odd-one-out standoff; open (2000) at start line |
| Floor reflectance | port **F** | construct-and-catch probe |
| Drivetrain | mirror-mounted differential | (1,1)/(−1,−1) spin ±34°; (1,−1)/(−1,1) straight ±1° |
| **Forward (toward wall)** | **m0 = −1, m1 = +1** | verify move: front pair read −62 mm (got closer) |
| Front-sensor geometry | **us1 mounted ≈ 130–155 mm ahead of us0** | us1 reads that much less at every range (base 1027 vs 895; rest 409 vs 252) |
| Rear / reflectance | **uninformative** for front approach | us2 open; reflectance ≈ 30–50 (floor), no wall signal |

**Note on CHAR-1 (the first run):** its prelude drove the rover *backward*. Root cause: the
forward test used a 34 mm move and "which sensor reads smaller" as the oracle; at ~1 m the front
ultrasonics are noisier than 34 mm, so the logic locked onto the only clean signal — the *rear*
sensor — and called "toward the rear wall" forward. CHAR-1 also over-emitted telemetry (~377
lines against a ~6 line/s BLE drain), timed out at 60 s, and truncated its buffer dump. **Fix
applied in CHAR-1b:** identify front/rear by absolute standoff, verify forward with a longer
low-speed move that must make the front pair *decrease*, and emit a small downsampled trace.
CHAR-1b completed cleanly in 20.6 s with the flush sentinel.

## 2. Calibrated parameters (run CHAR-1b)

| Parameter | Calibrated value | Prior | Source | Confidence |
|-----------|------------------|-------|--------|------------|
| `k_rot` | **0.50 mm/deg** (⌀ ≈ 57 mm) | — | ultrasonic slope vs odometry, clean cruise (532 mm / 1068°) | high (matches stock wheel) |
| `v_cruise` | **≈ 450 mm/s** | 380 | ultrasonic slope ≈ 490; odometry×k_rot ≈ 440 | medium (±~30) |
| brake time | **≈ 209 ms** | — | t_rest − t_trigger | high |
| peak decel | **≈ 4000 mm/s²** (avg ≈ 2200) | 1600 | IMU acc_x spike at brake | medium |
| `refresh` | ultrasonic updates present each loop; some quantization/dropouts observed | 0.04 | trace | low-medium |
| `ranger_floor` | assumed ~40 mm (not exercised; stops stayed ≥ 250 mm) | 40 | datasheet | low |
| heading (low speed) | drift ≈ **−0.64°** over the verify move | — | IMU heading | high (low speed only) |
| **`sensor_bias` / skid** | **UNRESOLVED — see §3** | ±20 | — | — |

## 3. ANOMALY — stopping-distance discrepancy (disposition: escalate to ground truth)

**Observation (CHAR-1b, full-speed brake from ~450 mm/s):**
- Odometry over the whole approach (rolling faithful during cruise) predicts the rover stopped at
  **≈ 285 mm** (start us1 ≈ 832 mm, travel 1095° × 0.50 = 547 mm).
- The forward ultrasonic (us1) read **252 mm** at rest, settled and stable over the last ~100 ms.
- **Disagreement ≈ 33 mm**, all of it accruing during the braking phase (during cruise the two
  channels track).

**Two competing explanations, opposite consequences:**
1. **Brake skid** — the wheels stop rotating (odometry froze 107 ms after trigger) while the body
   slides ~33 mm further. ⇒ odometry *under*-measures stopping distance; the ultrasonic is the
   truth; true `D_dyn` ≈ **48 mm**.
2. **Ultrasonic under-read bias** — us1 reads ~33 mm low. ⇒ odometry is the truth; true `D_dyn` ≈
   **13.5 mm**; the rover actually stops ~33 mm *farther* than us1 says.

**Why it cannot be resolved onboard:** odometry is relative (no absolute zero), and the ultrasonic
is the very sensor whose bias is in question. Distinguishing the two requires an **absolute
external reference** — one operator ground-truth measurement. Per the source-of-truth hierarchy,
`D_dyn` and any final-gap value are **hypotheses** until this anchor exists; the objective will
**not** be closed on either channel alone.

**Safety meanwhile:** both explanations put the rest position at **≥ 252 mm** from the wall, so
CHAR-1b had ≥ 252 mm clearance — no contact, comfortable margin. The ambiguity matters only for
*how close* the operating point can safely be, which is what VER-1 resolves.

**Consequence for control strategy:** because the discrepancy lives entirely in the brake phase,
the operating trigger will be set in the **ultrasonic reading frame** (`d_trig` is a us1 reading,
always above the floor and valid), and the **true** gap it produces will be pinned by the VER-1
operator measurement — never extrapolated from an unvalidated channel.

## 4. Requirement unit-verification status (C1: units gate integration)

| Requirement | Status after CHAR-1b | Evidence |
|-------------|----------------------|----------|
| CMP-1 ranger reads / refresh | **VERIFIED** (with noise caveat) | valid readings each loop; some quantization/dropouts |
| CMP-3 motor at max | **VERIFIED** | commanded 1500; achieved cruise ≈ 875°/s steady |
| CMP-4 motor → 0 | **VERIFIED** | odometry froze at rest |
| CMP-5 odometry → distance via k | **VERIFIED** | k_rot = 0.50, clean cruise agreement with ultrasonic |
| CMP-6 IMU yaw | **VERIFIED (low speed)** | heading drift −0.64° on verify move |
| CMP-7 IMU accel | **VERIFIED** | decel spike ≈ −4000 mm/s² at brake |
| Dropped effectors (rear, reflect) | **CONFIRMED uninformative** | us2 open; reflectance flat ≈ floor |
| SYS-2 max speed | **VERIFIED** | full-speed approach achieved |
| SYS-3 complete stop | **VERIFIED** | rover reached rest |
| SYS-5 straight (full speed) | **OPEN** | only low-speed heading measured → VER-1 logs full-speed heading |
| SYS-1 no-contact / SYS-4 min-gap / SYS-6 margin | **OPEN** | depend on the §3 resolution + operator anchor → VER-1 |

## 5. Model update (priors → calibrated), for the executable model

`v_cruise`: 380 → **450 mm/s**. `k_rot`: → **0.50 mm/deg**. `a_decel` (brake, effective):
1600 → **~2200 mm/s² avg**. `D_dyn`: **48 mm (ultrasonic frame)** pending §3 resolution. New
term to carry explicitly: **`d_skid_or_bias` ≈ 33 mm**, sign/attribution TBD at VER-1. Trigger is
defined on **us1** (forward sensor).

## 6. Run ledger & score-1 accounting

| Run | Outcome | Characterization-run count |
|-----|---------|----------------------------|
| CHAR-1 | wrong direction + truncated dump; unusable dynamics | 1 (counts) |
| CHAR-1b | clean; full config + dynamics + anomaly identified | 2 (counts) |

**Characterization runs spent so far: 2. Operator measurements spent: 0.**
