# =============================================================================
# CHARACTERIZATION PROGRAM  v3  --  Wall-Approach Rover   (role: C2)
# =============================================================================
# STATUS: STAGED FOR REVIEW. NOT FLASHED. Re-flash only on operator go-ahead
#         with the rover re-squared at the start line.
#
# CHANGES FROM v2 (see chat / plan v3), driven by the C1-v2 findings:
#   * Sensor B is FAULTY (reads ~130 mm low; operator confirmed the front is
#     flush and the true closest gap was 196 mm, matching sensor A). B is
#     EXCLUDED from the trigger and logged only for monitoring.
#   * TRIGGER on sensor A ONLY (trusted; offset ~+7 mm). A read on the hot path
#     alone -> faster loop (~25-30 ms vs ~63 ms) -> less trigger-sampling jitter.
#   * INDEPENDENT crash backstop that does NOT rely on any ultrasonic: an
#     encoder FORWARD-TRAVEL CAP (stop if wheel travel exceeds a bound safely
#     short of the ~1000 mm start). Plus an A emergency floor. Plus MAX_RUN_MS.
#   * D_stop is now trusted from the encoder (hold() stop is sharp, ~6 mm; no
#     significant skid per the whole-approach cross-check).
#
# Confirmed constants (C1-v2 + operator): k_speed ~27.6 mm/rad, omega ~1042
#   deg/s, A offset ~+7 mm. Port map hard-coded (motors C/D; ultrasonic A/B/E).
#
# This program is the locked superset for C2 and the basis for V1/operation:
#   only R_TRIGGER changes downstream. Wire contract unchanged; try/finally
#   guarantees motors stop + {"event":"end"} sentinel; light telemetry.
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

# ---- Hard-coded map + forward signs (from C1) ----
MOTOR_A_PORT = Port.C
MOTOR_B_PORT = Port.D
SA = -1.0
SB = +1.0
# ultrasonic ports: index 0 = A (TRIGGER, trusted), 1 = B (faulty, log only),
#                    2 = E (rear, log only)
ULTRA_PORTS  = [Port.A, Port.B, Port.E]
TRIG_IDX     = 0     # sensor A
PORT_LABEL   = {Port.A: 0, Port.B: 1, Port.C: 2, Port.D: 3, Port.E: 4, Port.F: 5}

KSPEED       = 27.6   # mm/rad, confirmed (crawl + stop segment)

# ---- Tunables ----
R_TRIGGER      = 200.0    # C2 conservative trigger on A (reported mm)
SAFE_FLOOR_A   = 80.0     # A emergency floor (reported mm)
TRAVEL_CAP_MM  = 850.0    # encoder crash backstop: max forward travel, mm
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
LOOP_MS        = 10       # A-only hot path -> tighter loop
EMIT_EVERY     = 2
MAX_RUN_MS     = 2500
REST_EPS       = 20.0
SETTLE_MAX_MS  = 1500

hub   = PrimeHub()
clock = StopWatch()
DRIVE_MOTORS = []


def emit(sensor, value):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'
                 % (clock.time(), sensor, value))


def emit_at(t_ms, sensor, value):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'
                 % (t_ms, sensor, value))


def dist_of(u):
    try:
        v = float(u.distance())
        if v <= 0.0:
            return NO_ECHO
        return v
    except Exception:
        return NO_ECHO


def main():
    # 1. Construct hard-coded devices ONCE.
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
    uTrig = ultras[TRIG_IDX][1]   # sensor A

    for (p, _) in ultras:
        emit('map_ultra_port', float(PORT_LABEL[p]))

    def fwd_angle():
        return 0.5 * (SA * mA.angle() + SB * mB.angle())

    for m in (mA, mB):
        try:
            m.control.limits(speed=LIM_SPEED, acceleration=LIM_ACCEL)
        except Exception:
            pass

    # 2. CONFIRMING FORWARD CRAWL — verify sensor A faces the wall.
    mA.reset_angle(0)
    mB.reset_angle(0)
    h_base = hub.imu.heading()

    pre = [dist_of(u) for (_, u) in ultras]
    ang_pre = fwd_angle()
    for i in range(len(ultras)):
        emit('crawl_pre_u%d' % i, pre[i])

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
    for i in range(len(ultras)):
        emit('crawl_post_u%d' % i, post[i])
        emit('crawl_drop_u%d' % i, pre[i] - post[i])
    emit('crawl_dhead', hub.imu.heading() - h_base)

    if crawl_aborted:
        emit('abort_crawl_floor', 1.0)
        return

    # Require sensor A to have clearly tracked a wall ahead.
    dropA = pre[TRIG_IDX] - post[TRIG_IDX]
    if not (dropA >= CRAWL_DROP_MM and STANDOFF_LO <= pre[TRIG_IDX] <= STANDOFF_HI):
        emit('abort_A_not_facing_wall', 1.0)
        return

    # onboard k_speed from A (convenience; re-derivable from scalars)
    dang_deg = ang_post - ang_pre
    if dang_deg > 1.0:
        emit('k_speed_crawl_mm_per_rad', dropA / (dang_deg * PI / 180.0))

    # 3. FAST APPROACH — trigger on A only; layered crash backstops.
    mA.reset_angle(0)
    mB.reset_angle(0)
    mA.run(SA * MAX_CMD)
    mB.run(SB * MAX_CMD)

    omega_max_obs = 0.0
    i_loop = 0
    t0 = clock.time()
    triggered = False
    emerg_sensor = False
    emerg_cap = False
    t_trig = ang_trig = 0.0
    a_trig = 0.0

    while True:
        t = clock.time()
        dA = dist_of(uTrig)            # only A on the hot path
        fdeg = fwd_angle()
        fmm = fdeg * PI / 180.0 * KSPEED

        sp = 0.5 * (abs(mA.speed()) + abs(mB.speed()))
        if sp > omega_max_obs:
            omega_max_obs = sp

        if (i_loop % EMIT_EVERY) == 0:
            emit_at(t, 'a_dist', dA)
            emit_at(t, 'fwd_mm', fmm)

        # crash backstops FIRST (encoder cap is ultrasonic-independent)
        if fmm >= TRAVEL_CAP_MM:
            emerg_cap = True
            t_trig = t; ang_trig = fdeg; a_trig = dA
            break
        if dA <= SAFE_FLOOR_A:
            emerg_sensor = True
            t_trig = t; ang_trig = fdeg; a_trig = dA
            break
        # primary trigger on A
        if dA <= R_TRIGGER:
            triggered = True
            t_trig = t; ang_trig = fdeg; a_trig = dA
            break
        if (t - t0) > MAX_RUN_MS:
            break

        i_loop += 1
        wait(LOOP_MS)

    # 4. STOP.
    mA.hold(); mB.hold()
    settle_start = clock.time()
    while (clock.time() - settle_start) < SETTLE_MAX_MS:
        if abs(mA.speed()) < REST_EPS and abs(mB.speed()) < REST_EPS:
            break
        wait(20)
    t_rest = clock.time()
    ang_rest = fwd_angle()
    rest_vals = [dist_of(u) for (_, u) in ultras]
    rest_speed = max(abs(mA.speed()), abs(mB.speed()))
    h_rest = hub.imu.heading()
    D_stop_deg = ang_rest - ang_trig
    D_stop_mm = D_stop_deg * PI / 180.0 * KSPEED

    # 5. LATCHED SCALARS.
    emit('triggered', 1.0 if triggered else 0.0)
    emit('emerg_sensor', 1.0 if emerg_sensor else 0.0)
    emit('emerg_cap', 1.0 if emerg_cap else 0.0)
    emit('a_trigger', a_trig)
    for i in range(len(ultras)):
        emit('rest_u%d' % i, rest_vals[i])
    emit('angle_trigger_deg', ang_trig)
    emit('angle_rest_deg', ang_rest)
    emit('D_stop_deg', D_stop_deg)
    emit('D_stop_mm', D_stop_mm)
    emit('fwd_travel_mm_rest', ang_rest * PI / 180.0 * KSPEED)
    emit('rest_speed_deg_s', rest_speed)
    emit('omega_cruise_deg_s', omega_max_obs)
    emit('heading_base', h_base)
    emit('heading_rest', h_rest)
    emit('t_trigger_ms', float(t_trig))
    emit('t_rest_ms', float(t_rest))


try:
    main()
finally:
    for _mm in DRIVE_MOTORS:
        try:
            _mm.stop()
        except Exception:
            pass
    stdout.write('{"event":"end"}\n')
