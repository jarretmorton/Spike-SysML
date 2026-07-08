# =============================================================================
# VERIFICATION / OPERATION PROGRAM  v4  --  Wall-Approach Rover
# =============================================================================
# STATUS: STAGED FOR REVIEW. NOT FLASHED.
#
# WHY v4 (V1 falsified the v1 prediction): the ultrasonic-based trigger fired
# LATE when the control loop stalled (ultrasonic echo timeout + slow BLE ->
# ~471 ms loop near the trigger), so the rover stopped at 28 mm vs a predicted
# 60 mm. No contact that run, but unsafe by luck. Root cause: the trigger
# depended on the ultrasonic, whose read can block, inside the hot loop.
#
# FIX: trigger on ENCODER TRAVEL. The fast approach reads only .angle()/.speed()
# (fast, non-blocking) and NO ultrasonic and NO telemetry on the hot path, so
# the loop period is bounded regardless of ultrasonic echo or BLE. Sensor A is
# read ONCE at the fast-approach start (reliable ~930 mm range) to fix the start
# distance; the crawl supplies a per-run k. The trigger fires when wheel travel
# reaches target_travel = true_start - TARGET_TRUE_TRIGGER. Verified: the encoder
# tracks ROLLING travel almost exactly (C2 740 vs 737 mm true); slip is only in
# the post-trigger brake, which is captured in D_STOP_EFF.
#
# Calibrated (C1-v2/C2/C3/V1 + operators 196,28): b=+7 mm, k~28 mm/rad (per-run
# from crawl), D_STOP_EFF~58 mm (true trigger->rest; 66/42/65), sigma_stop~15 mm
# (braking spread). Trigger-position jitter is now ~0 (encoder), so the final gap
# spread is dominated by braking. TARGET_GAP set for 3-sigma no-contact.
#
# Wire contract unchanged; try/finally guarantees motors stop + sentinel.
# Telemetry minimized (BLE can be ~240 ms/line) so the run completes.
# =============================================================================

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import wait, StopWatch

try:
    from usys import stdout
except ImportError:
    from sys import stdout

PI = 3.14159265

MOTOR_A_PORT = Port.C
MOTOR_B_PORT = Port.D
SA = -1.0
SB = +1.0
ULTRA_PORTS  = [Port.A, Port.B, Port.E]
TRIG_IDX     = 0
PORT_LABEL   = {Port.A: 0, Port.B: 1, Port.C: 2, Port.D: 3, Port.E: 4, Port.F: 5}

# ---- calibrated ----
B_OFFSET       = 7.0      # sensor A offset (reports true + b)
D_STOP_EFF     = 58.0     # true stopping distance, trigger -> rest (mm)
K_FIXED        = 27.5     # mm/rad, long-baseline rolling k (C2/C3/V1: 27.47 +-0.8%)
K_FALLBACK     = 27.5     # (crawl k is only a sanity monitor now)

# ---- design ----
TARGET_GAP        = 55.0  # desired true final gap (3-sigma no-contact)
TARGET_TRUE_TRIG  = TARGET_GAP + D_STOP_EFF     # = 113 mm true at trigger
TARGET_TRAVEL_MAX = 830.0 # safety clamp on target_travel (bounds an A_start over-read)
A_START_LO        = 700.0 # sanity band for the start reading
A_START_HI        = 1200.0

R_TRIGGER      = 121.0    # (legacy A-threshold; used ONLY as a late secondary safety)
SAFE_FLOOR_A   = 80.0
NO_ECHO        = 2000.0
STANDOFF_LO    = 300.0
STANDOFF_HI    = 1400.0
CRAWL_SPEED    = 150.0
CRAWL_MS       = 1200
CRAWL_SETTLE   = 250
CRAWL_DROP_MM  = 40.0
MAX_CMD        = 1000.0
LIM_SPEED      = 1400.0
LIM_ACCEL      = 12000.0
LOOP_MS        = 5        # pure-encoder hot loop -> short, bounded period
MAX_RUN_MS     = 2500
REST_EPS       = 20.0
SETTLE_MAX_MS  = 1500

hub   = PrimeHub()
clock = StopWatch()
DRIVE_MOTORS = []


def emit(sensor, value):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'
                 % (clock.time(), sensor, value))


def dist_of(u):
    try:
        v = float(u.distance())
        if v <= 0.0:
            return NO_ECHO
        return v
    except Exception:
        return NO_ECHO


def main():
    try:
        mA = Motor(MOTOR_A_PORT)
        mB = Motor(MOTOR_B_PORT)
    except Exception:
        emit('err_motor_construct', 1.0)
        return
    DRIVE_MOTORS.append(mA)
    DRIVE_MOTORS.append(mB)

    ultras = []
    for p in ULTRA_PORTS:
        try:
            ultras.append((p, UltrasonicSensor(p)))
        except Exception:
            emit('err_ultra_construct', float(PORT_LABEL[p]))
    if len(ultras) <= TRIG_IDX:
        emit('err_no_trigger_sensor', 1.0)
        return
    uTrig = ultras[TRIG_IDX][1]

    def fwd_angle():
        return 0.5 * (SA * mA.angle() + SB * mB.angle())

    for m in (mA, mB):
        try:
            m.control.limits(speed=LIM_SPEED, acceleration=LIM_ACCEL)
        except Exception:
            pass

    # --- CONFIRMING CRAWL (verify A faces wall; per-run k; start distance) ---
    mA.reset_angle(0)
    mB.reset_angle(0)
    h_base = hub.imu.heading()
    pre = [dist_of(u) for (_, u) in ultras]
    ang_pre = fwd_angle()
    emit('crawl_pre_A', pre[TRIG_IDX])

    mA.run(SA * CRAWL_SPEED)
    mB.run(SB * CRAWL_SPEED)
    t_crawl0 = clock.time()
    crawl_aborted = False
    while (clock.time() - t_crawl0) < CRAWL_MS:
        if dist_of(uTrig) <= SAFE_FLOOR_A:
            crawl_aborted = True
            break
        wait(30)
    mA.hold(); mB.hold()
    wait(CRAWL_SETTLE)

    post = [dist_of(u) for (_, u) in ultras]
    ang_post = fwd_angle()
    emit('crawl_post_A', post[TRIG_IDX])
    emit('crawl_dhead', hub.imu.heading() - h_base)

    if crawl_aborted:
        emit('abort_crawl_floor', 1.0)
        return

    dropA = pre[TRIG_IDX] - post[TRIG_IDX]
    if not (dropA >= CRAWL_DROP_MM and STANDOFF_LO <= pre[TRIG_IDX] <= STANDOFF_HI):
        emit('abort_A_not_facing_wall', 1.0)
        return

    dang_deg = ang_post - ang_pre
    k_run = (dropA / (dang_deg * PI / 180.0)) if dang_deg > 1.0 else K_FIXED
    emit('k_run_mm_per_rad', k_run)      # monitor only; trigger uses K_FIXED
    if not (0.80 * K_FIXED <= k_run <= 1.20 * K_FIXED):
        emit('abort_k_run_off', k_run)   # crawl / wheels anomalous -> safe abort
        return

    # --- ENCODER-TRAVEL TARGET (the key change) ---
    a_start = post[TRIG_IDX]                      # reliable-range A reading
    if not (A_START_LO <= a_start <= A_START_HI):
        emit('abort_a_start_range', a_start)
        return
    true_start = a_start - B_OFFSET
    target_travel = true_start - TARGET_TRUE_TRIG
    if target_travel > TARGET_TRAVEL_MAX:         # safety clamp (over-read guard)
        target_travel = TARGET_TRAVEL_MAX
    if target_travel <= 50.0:                     # nonsense -> abort
        emit('abort_target_travel', target_travel)
        return
    emit('a_start', a_start)
    emit('target_travel_mm', target_travel)

    # --- FAST APPROACH: pure-encoder trigger, no ultrasonic, no hot-path emit ---
    mA.reset_angle(0)
    mB.reset_angle(0)
    mA.run(SA * MAX_CMD)
    mB.run(SB * MAX_CMD)

    omega_max_obs = 0.0
    t0 = clock.time()
    triggered = False
    emerg = False
    ang_trig = 0.0
    travel_trig = 0.0
    cap = target_travel + 40.0                    # redundant hard cap

    while True:
        t = clock.time()
        fdeg = fwd_angle()
        fmm = fdeg * PI / 180.0 * K_FIXED
        sp = 0.5 * (abs(mA.speed()) + abs(mB.speed()))
        if sp > omega_max_obs:
            omega_max_obs = sp

        if fmm >= target_travel:
            triggered = True
            ang_trig = fdeg; travel_trig = fmm
            break
        if fmm >= cap:
            emerg = True
            ang_trig = fdeg; travel_trig = fmm
            break
        if (t - t0) > MAX_RUN_MS:
            break
        wait(LOOP_MS)

    # --- STOP ---
    mA.hold(); mB.hold()
    settle_start = clock.time()
    while (clock.time() - settle_start) < SETTLE_MAX_MS:
        if abs(mA.speed()) < REST_EPS and abs(mB.speed()) < REST_EPS:
            break
        wait(20)
    ang_rest = fwd_angle()
    rest_vals = [dist_of(u) for (_, u) in ultras]     # ultrasonic only at rest
    rest_speed = max(abs(mA.speed()), abs(mB.speed()))
    h_rest = hub.imu.heading()
    D_stop_deg = ang_rest - ang_trig
    travel_rest = ang_rest * PI / 180.0 * K_FIXED

    # onboard gap estimate (geometry): true_start - travel_rest
    gap_est_geom = true_start - travel_rest

    # --- MINIMAL LATCHED TELEMETRY ---
    emit('triggered', 1.0 if triggered else 0.0)
    emit('emerg', 1.0 if emerg else 0.0)
    emit('travel_trig_mm', travel_trig)
    emit('travel_rest_mm', travel_rest)
    emit('D_stop_mm', D_stop_deg * PI / 180.0 * K_FIXED)
    emit('gap_est_geom_mm', gap_est_geom)
    emit('rest_A', rest_vals[TRIG_IDX])
    emit('rest_B', rest_vals[1] if len(rest_vals) > 1 else -1.0)
    emit('rest_speed_deg_s', rest_speed)
    emit('omega_cruise_deg_s', omega_max_obs)
    emit('heading_rest', h_rest)


try:
    main()
finally:
    for _mm in DRIVE_MOTORS:
        try:
            _mm.stop()
        except Exception:
            pass
    stdout.write('{"event":"end"}\n')
