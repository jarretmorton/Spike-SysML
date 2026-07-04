# Final Engineering Report — Wall-Approach Rover

**Task:** drive a LEGO SPIKE Prime rover straight at a wall (~1000 mm away) at maximum speed and stop as close as possible **without contact**. Hard constraint: no contact. Objective: minimize the final gap.

**Result:** **5 / 5 operation runs with no contact.** Final gaps **46, 45, 32, 51, 46 mm** (mean **44.0 mm**, best **32 mm**, sd 7.1 mm), each at full commanded speed (~1040–1067 deg/s) with heading held within tolerance.

---

## 1. Scoring summary

| Dimension | Result |
|---|---|
| Characterization/verification program runs (fewer better) | **6** (C1 failed, C1-v2, C2, C3, V1, V1′) |
| Costed characterization operator measurements (fewer better) | **3** (196, 28, 46 mm) |
| Operation runs with **no contact** (more better) | **5 / 5** |
| Closeness of the 5 stops | **mean 44 mm, best 32 mm, all 32–51 mm** |
| Operation close-out measurements | 5 (protocol-required) |

The characterization cost (6 runs, 3 measurements) exceeded the initial 3-run/2-measurement plan; the overage came from two genuine safety events — the C1 wall contact and the V1 falsification — each of which was diagnosed and fixed rather than worked around.

## 2. Per-run results (onboard estimate | operator measurement | delta)

Onboard estimate = **sensor-A near-range fit** `0.643·rest_A + 1.03` (frozen before ground truth). Cross-check = **trigger geometry** `(true_start − travel_trig) − D_stop_eff`.

| Run | Onboard estimate (frozen) | Operator truth | Delta (est−truth) | Trigger-geom xcheck | Contact |
|:--:|:--:|:--:|:--:|:--:|:--:|
| 1 | 43 mm | 46 mm | −3 | 52 | none |
| 2 | 39 mm | 45 mm | −6 | 54 | none |
| 3 | 37 mm | 32 mm | +5 | 53 | none |
| 4 | 43 mm | 51 mm | −8 | 54 | none |
| 5 | 44 mm | 46 mm | −2 | 53 | none |
| **mean** | **41.2** | **44.0** | **−2.8** | 53.2 | **0/5 contact** |

Onboard-estimate accuracy: **RMS 5.25 mm, max 8 mm** (A-fit). The trigger-geometry cross-check ran systematically high (mean +9.2 mm, RMS 11 mm).

## 3. Reconciliation

**(a) Which onboard estimator was better, and why.** The **sensor-A near-range fit tracked truth to ±5 mm** — the best onboard channel. The **trigger-geometry estimate ran ~9 mm high** because it assumes the calibrated `D_stop_eff = 58 mm`, whereas the *actual* stopping distance in operation was larger (below). Neither channel is perfect near the wall: the encoder under-counts the braking travel (wheel slip during the aggressive `hold()` brake), and sensor A over-reads near its ~40 mm floor. The A-fit wins because it was calibrated directly against near-range ground truth (V1/V1′).

**(b) Why the gaps landed at 44 mm vs the 55 mm design target.** The committed design placed the trigger at a true 113 mm and subtracted a calibrated `D_stop_eff = 58 mm`, predicting a 55 mm gap. The **implied actual stopping distance was ~69 mm** (113 − measured gap, per run: 67/68/81/62/67), so the rover stopped ~11 mm closer than designed. The calibrated 58 mm was low because the C3 characterization sample (42 mm) was an outlier that pulled the mean down; the true value clustered near 65–69 mm.

**(c) Why this stayed safe.** The no-contact margin was sized conservatively — design `σ_stop = 15 mm` against an **actual run-to-run spread of only 7 mm** — and the 3σ margin (52 mm) more than absorbed the 11 mm `D_stop` under-estimate. The closest stop (Run 3, 32 mm) remained well within the design envelope (mean 55 ± 3σ) and far from contact. Net: the objective *benefited* (gaps tighter than the 55 mm target) while the hard no-contact constraint held on every run — the intended trade, achieved on the safe side.

**(d) Trigger fidelity.** The encoder-travel trigger fired within **1–3 mm** of its target on all five runs and was completely immune to the ultrasonic/BLE loop stalls that had derailed the earlier ultrasonic-based trigger (V1). This is what made the five runs repeatable.

## 4. Locked operation program (`prog_v4.py`)

Encoder-travel trigger; sensor A read once at the start to fix the distance; fixed long-baseline `k = 27.5 mm/rad`; `hold()` stop; layered aborts/clamps; minimal telemetry. Flashed identically for all five runs.

```python
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import wait, StopWatch
try:
    from usys import stdout
except ImportError:
    from sys import stdout

PI = 3.14159265
MOTOR_A_PORT = Port.C; MOTOR_B_PORT = Port.D
SA = -1.0; SB = +1.0                 # forward motor signs (from C1)
ULTRA_PORTS = [Port.A, Port.B, Port.E]; TRIG_IDX = 0   # A trusted; B faulty; E rear

B_OFFSET = 7.0            # sensor-A offset (reports true + b)
D_STOP_EFF = 58.0         # calibrated stopping distance (trigger->rest)
K_FIXED = 27.5            # long-baseline rolling k (mm/rad)
TARGET_GAP = 55.0
TARGET_TRUE_TRIG = TARGET_GAP + D_STOP_EFF   # 113 mm true at trigger
TARGET_TRAVEL_MAX = 830.0; A_START_LO = 700.0; A_START_HI = 1200.0
SAFE_FLOOR_A = 80.0; NO_ECHO = 2000.0; STANDOFF_LO = 300.0; STANDOFF_HI = 1400.0
CRAWL_SPEED = 150.0; CRAWL_MS = 1200; CRAWL_SETTLE = 250; CRAWL_DROP_MM = 40.0
MAX_CMD = 1000.0; LIM_SPEED = 1400.0; LIM_ACCEL = 12000.0
LOOP_MS = 5; MAX_RUN_MS = 2500; REST_EPS = 20.0; SETTLE_MAX_MS = 1500

hub = PrimeHub(); clock = StopWatch(); DRIVE_MOTORS = []

def emit(sensor, value):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n' % (clock.time(), sensor, value))

def dist_of(u):
    try:
        v = float(u.distance())
        return NO_ECHO if v <= 0.0 else v
    except Exception:
        return NO_ECHO

def main():
    try:
        mA = Motor(MOTOR_A_PORT); mB = Motor(MOTOR_B_PORT)
    except Exception:
        emit('err_motor_construct', 1.0); return
    DRIVE_MOTORS.append(mA); DRIVE_MOTORS.append(mB)
    ultras = []
    for p in ULTRA_PORTS:
        try: ultras.append((p, UltrasonicSensor(p)))
        except Exception: emit('err_ultra_construct', 1.0)
    if len(ultras) <= TRIG_IDX:
        emit('err_no_trigger_sensor', 1.0); return
    uTrig = ultras[TRIG_IDX][1]
    def fwd_angle(): return 0.5 * (SA * mA.angle() + SB * mB.angle())
    for m in (mA, mB):
        try: m.control.limits(speed=LIM_SPEED, acceleration=LIM_ACCEL)
        except Exception: pass

    # confirming crawl: verify A faces wall; sanity-check k; fix start distance
    mA.reset_angle(0); mB.reset_angle(0)
    h_base = hub.imu.heading()
    pre = [dist_of(u) for (_, u) in ultras]; ang_pre = fwd_angle()
    emit('crawl_pre_A', pre[TRIG_IDX])
    mA.run(SA * CRAWL_SPEED); mB.run(SB * CRAWL_SPEED)
    t0 = clock.time(); crawl_aborted = False
    while (clock.time() - t0) < CRAWL_MS:
        if dist_of(uTrig) <= SAFE_FLOOR_A: crawl_aborted = True; break
        wait(30)
    mA.hold(); mB.hold(); wait(CRAWL_SETTLE)
    post = [dist_of(u) for (_, u) in ultras]; ang_post = fwd_angle()
    emit('crawl_post_A', post[TRIG_IDX]); emit('crawl_dhead', hub.imu.heading() - h_base)
    if crawl_aborted: emit('abort_crawl_floor', 1.0); return
    dropA = pre[TRIG_IDX] - post[TRIG_IDX]
    if not (dropA >= CRAWL_DROP_MM and STANDOFF_LO <= pre[TRIG_IDX] <= STANDOFF_HI):
        emit('abort_A_not_facing_wall', 1.0); return
    dang = ang_post - ang_pre
    k_run = (dropA / (dang * PI / 180.0)) if dang > 1.0 else K_FIXED
    emit('k_run_mm_per_rad', k_run)
    if not (0.80 * K_FIXED <= k_run <= 1.20 * K_FIXED):
        emit('abort_k_run_off', k_run); return

    a_start = post[TRIG_IDX]
    if not (A_START_LO <= a_start <= A_START_HI): emit('abort_a_start_range', a_start); return
    true_start = a_start - B_OFFSET
    target_travel = true_start - TARGET_TRUE_TRIG
    if target_travel > TARGET_TRAVEL_MAX: target_travel = TARGET_TRAVEL_MAX
    if target_travel <= 50.0: emit('abort_target_travel', target_travel); return
    emit('a_start', a_start); emit('target_travel_mm', target_travel)

    # fast approach: pure-encoder trigger, NO ultrasonic / telemetry in the hot loop
    mA.reset_angle(0); mB.reset_angle(0)
    mA.run(SA * MAX_CMD); mB.run(SB * MAX_CMD)
    omega = 0.0; t0 = clock.time(); triggered = False; emerg = False
    ang_trig = 0.0; travel_trig = 0.0; cap = target_travel + 40.0
    while True:
        t = clock.time(); fdeg = fwd_angle(); fmm = fdeg * PI / 180.0 * K_FIXED
        sp = 0.5 * (abs(mA.speed()) + abs(mB.speed()))
        if sp > omega: omega = sp
        if fmm >= target_travel: triggered = True; ang_trig = fdeg; travel_trig = fmm; break
        if fmm >= cap: emerg = True; ang_trig = fdeg; travel_trig = fmm; break
        if (t - t0) > MAX_RUN_MS: break
        wait(LOOP_MS)

    mA.hold(); mB.hold()
    ss = clock.time()
    while (clock.time() - ss) < SETTLE_MAX_MS:
        if abs(mA.speed()) < REST_EPS and abs(mB.speed()) < REST_EPS: break
        wait(20)
    ang_rest = fwd_angle(); rest_vals = [dist_of(u) for (_, u) in ultras]
    rest_speed = max(abs(mA.speed()), abs(mB.speed())); h_rest = hub.imu.heading()
    travel_rest = ang_rest * PI / 180.0 * K_FIXED
    emit('triggered', 1.0 if triggered else 0.0); emit('emerg', 1.0 if emerg else 0.0)
    emit('travel_trig_mm', travel_trig); emit('travel_rest_mm', travel_rest)
    emit('D_stop_mm', (ang_rest - ang_trig) * PI / 180.0 * K_FIXED)
    emit('gap_est_geom_mm', true_start - travel_rest)
    emit('rest_A', rest_vals[TRIG_IDX]); emit('rest_B', rest_vals[1] if len(rest_vals) > 1 else -1.0)
    emit('rest_speed_deg_s', rest_speed); emit('omega_cruise_deg_s', omega)
    emit('heading_rest', h_rest)

try:
    main()
finally:
    for _m in DRIVE_MOTORS:
        try: _m.stop()
        except Exception: pass
    stdout.write('{"event":"end"}\n')
```

## 5. Methodology and audit trail

The work followed a gated systems-engineering process (requirements → SysML/executable model → calibration plan → calibration → verification → operation), with hardware touched only after free analysis was exhausted. Four findings shaped the outcome, each surfaced by data and dispositioned with a record:

1. **C1 drove into the wall** (nudge-based sensor detection picked the wrong trigger sensor; the 8 s backstop was useless at 0.5 m/s). → Redesigned detection + layered crash prevention (Anomaly Report; Calibration Plan v2).
2. **Sensor B is faulty** (reads ~130 mm low; front confirmed flush). → Excluded; sensor A trusted (Report §3a; Plan v3).
3. **The encoder under-counts stopping distance** (wheel slip during the hard brake). → Stop/gap taken from sensor + operator anchor, not the encoder (Report §3b).
4. **The ultrasonic trigger fired late under a stalled loop** (V1 stopped at 28 mm vs 60 mm predicted — no contact, but unsafe by luck). → **Encoder-travel trigger**, ultrasonic removed from the hot loop (Verification Plan v2; `prog_v4`), verified at V1′ and used for all five operation runs.

The predictive discipline held throughout: predictions were frozen before each verification run and, when V1 falsified one, the model was re-derived (not tweaked) and a new frozen prediction was issued and re-tested.

## 6. Deliverables index

Requirements & model: `01_requirements_spec.md`, `wallrun_model.sysml`, `wallrun_model.py`, `03_structural_check.py`, `04_collapse_demo.py`.
Plans (living): `05_calibration_plan_v1/v2/v3.md`, `07_verification_plan_v1/v2.md`.
Reports (static): `ANOMALY_C1_report.md`, `06_calibration_report.md`, `08_verification_report.md`, this report.
Prediction computations: `calib_predict.py`/`_v2.py` (+ outputs).
Programs: `c1_program.py` (v1, failed), `c1_program_v2.py`, `prog_v3.py`, **`prog_v4.py` (locked operation program)**.
Operation record: `operation_log.md`.
