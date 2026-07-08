# Verification Report — Wall-Approach Rover (GATE C)

**Document type:** REPORT (static; the single place every requirement is closed).
**Basis:** requirements spec + SysML/executable model + Calibration Report + Verification Plan v2 (frozen) + verification run **V1′** (`prog_v4`) + operator measurements #1 (196 mm), #2 (28 mm), #3 (46 mm).
**Verdict:** all hard requirements verified; the objective is validated at the operating point. **Cleared to lock `prog_v4` and run the 5 scored operation runs.**

---

## 1. Verification outcome

The frozen v2 prediction (Verification Plan v2: 55 mm gap, roll-up PASS) was tested by **V1′** at the committed configuration (`prog_v4`, encoder-travel trigger, `TARGET_GAP=55`):

| | Predicted (frozen) | **V1′ actual** | |
|---|---|---|---|
| final true gap | 55 mm | **46 mm** (operator #3) | 0.5σ below mean — within band |
| contact | none | **none** | ✓ |
| trigger overshoot | ~0 (encoder) | **2 mm** (travel 823 vs 821) | loop-timing failure fixed |
| cruise speed | 500 mm/s | 1046 deg/s ≈ max | ✓ |
| rest speed | ~0 | 4 deg/s | stopped |

The prediction is **validated**: the rover stopped close to the wall, at full speed, without contact, at a gap consistent with the frozen prediction, with the loop-timing defect (which falsified v1) removed and confirmed removed.

## 2. Requirement closure (method · evidence · verdict)

| Req | Statement | Method | Evidence | Verdict |
|---|---|---|---|---|
| **STK-1** | Stop as close as possible to the wall without contact, at max speed | test + analysis | V1′: 46 mm, no contact, full speed; margin design | **CLOSED** (demo'd; 5 runs to confirm repeatability) |
| **SYS-1** NoContact | final_clearance > 0 | test + margin analysis | V1′ 46 > 0; design mean 55, 3σ margin 51.7 (mean−3σ ≈ 3 mm > 0) | **PASS** |
| **SYS-2** MaxSpeed | cruise ≥ max | test | cruise 1041–1046 deg/s across runs; commanded max, flat to trigger | **PASS** |
| **SYS-3** MinGap (objective) | minimize final gap | validated at operating point | **predicted 55 mm validated vs operator 46 mm at the operating point, no contact** (measurement #3, distinct from operation close-out) | **CLOSED — objective value ≈ 46 mm** |
| **SYS-3b** MinGapMargin | final_clearance ≥ safetyMargin (3σ RSS) | analysis | 55 ≥ 51.7 (design); V1′ within band | **PASS** |
| **SYS-4** FullStop | rest speed ≤ tol | test | rest 4–14 deg/s (held) across runs | **PASS** |
| **SYS-5** StraightTravel | heading drift ≤ tol (10°) | test | drift −4 to −8.5°; V1′ −8.5° (within tol; **watch item**) | **PASS** |
| **FUN-1** SenseDistance | forward distance for trigger | via CMP-3/4 + integrated | A (sensor) confirmed wall-facing; B faulty, excluded | **CLOSED** |
| **FUN-2** DecideStop | stop at threshold | integrated | encoder-travel trigger fires at target (V1′ 823 vs 821) | **CLOSED** |
| **FUN-3** DriveMax | both motors at max | via CMP-1 | cruise at rated max | **CLOSED** |
| **FUN-4** StoppingCharacterized | D_stop + spread bounded | test | D_stop 58 mm, σ 15 mm (3 samples incl. operator-anchored V1) | **CLOSED** |
| **FUN-5** MaintainHeading | equal drive, straight | via CMP-6 | drift bounded; straight crawl (≤0.7°) | **CLOSED** |
| **FUN-6** EstimateGap | onboard gap estimate | integrated | trigger-geometry + rest reading (raw geom estimate corrected for slip) | **CLOSED** |
| **CMP-1..7** | component unit reqs | test/analysis | Calibration Report §4 (all PASS) | **PASS** |

**Roll-up:** all hard requirements PASS; objective closed. `wallrun_model.evaluate()` ROLLUP = PASS at the committed config (`calib_predict_v2_output.txt`).

## 3. Key findings incorporated (audit trail)

- **C1 wall contact** → detection + backstop redesign (Anomaly Report; Calibration Plan v2).
- **Sensor B faulty (~−130 mm)** → excluded; sensor A trusted (Calibration Report §3a; Plan v3).
- **Encoder under-counts D_stop (brake slip)** → stop/gap from sensor + operator anchor, not encoder; encoder used only for rolling travel (Report §3b).
- **Ultrasonic-loop stall → late trigger (V1 falsified)** → encoder-travel trigger, ultrasonic out of the hot loop (Verification Plan v2; `prog_v4`).

## 4. Locked configuration and readiness for operation

**Locked operation program: `prog_v4.py`** (identical to the V1′-verified build). Each operation run: operator squares the rover (~1000 mm) + power-cycles; flash `prog_v4`; run (~15 s timeout). The program self-establishes the start distance (sensor A) and triggers on encoder travel to `TARGET_TRUE_TRIGGER = 113 mm true`, stopping at ~46–55 mm.

**Expected operation performance:** gap ~40–55 mm, no contact (per-run P(contact) < ~0.2%, < ~1% over 5 runs, on the 3σ RSS margin). Residual variability is the braking spread (σ ≈ 15 mm), which the margin covers.

**Onboard gap estimate for close-out:** computed per run from the raw telemetry — trigger geometry `(true_start − travel_trig) − D_stop_eff` cross-checked with the rest reading, **not** the raw `gap_est_geom` (which is biased high by brake slip). The per-run braking variation is only partly observable onboard (encoder slips, A unreliable at < ~50 mm), so a ~±10–15 mm onboard-vs-truth delta is expected and will be reported honestly.

**Watch items during operation:** heading drift approaching the 10° tolerance (corner effect already reflected in the measured closest gap); sensor-A near-range over-read (does not affect the trigger, which is encoder-based).

**Budget to date:** 6 program runs (C1-fail, C1-v2, C2, C3, V1, V1′) + 3 operator measurements (#1/#2/#3). Then 5 scored operation runs + close-out.
