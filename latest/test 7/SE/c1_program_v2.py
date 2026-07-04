# =============================================================================
# C1 CHARACTERIZATION PROGRAM  v2  --  Wall-Approach Rover
# =============================================================================
# STATUS: STAGED FOR REVIEW. NOT FLASHED. Re-flash only after the operator
#         confirms the rover is inspected, undamaged, and re-squared at the
#         start line, AND gives an explicit go-ahead.
#
# WHY v2 (see ANOMALY_C1_report.md): v1 mis-identified the trigger sensor and
# had an 8 s backstop that permitted ~4 m of travel, so the rover drove into
# the wall. v2 removes the fragile nudge detection and adds layered crash
# prevention that does not depend on getting the sensor identity right.
#
# LAYERED SAFETY (crash prevention is independent of sensor selection):
#   L1 primary : stop when the identified wall-facing group reads <= R_TRIGGER.
#   L2 backstop: EMERGENCY stop if ANY ultrasonic reads <= SAFE_FLOOR (~100 mm).
#                Catches a wrong forward/rear identity: whatever truly nears the
#                wall trips it. Invalid/no-echo readings are sanitized to "far".
#   L3 backstop: tightened MAX_RUN_MS ("stuck" catch).
#
# ROBUST WALL-SENSOR ID: a slow, sustained, hard-coded-forward CRAWL (strong
#   signal, unlike v1's tiny paired nudge). Sensors that clearly DECREASE during
#   the confirmed-forward crawl, and read a plausible wall standoff, are the
#   wall-facing group. If none qualify -> SAFE ABORT before the fast approach.
#
# PORT MAP hard-coded from C1 evidence (documented Plan-v1 fallback):
#   motors C(-1 fwd) & D(+1 fwd); ultrasonic A,B,E (B proven wall-facing,
#   E rear); color F dropped. Forward signs from C1 (rover drove at the wall).
#
# TELEMETRY: light live (downsampled) + latched scalars only; NO full-rate
#   buffer dump (that is what timed out v1). Wire contract unchanged; try/finally
#   guarantees motors stop + {"event":"end"} sentinel.
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
SA = -1.0    # motor on C: forward sign (C1: drove toward wall)
SB = +1.0    # motor on D: forward sign
ULTRA_PORTS  = [Port.A, Port.B, Port.E]   # forward group discovered by crawl
PORT_LABEL   = {Port.A: 0, Port.B: 1, Port.C: 2, Port.D: 3, Port.E: 4, Port.F: 5}

# ---- Tunables ----
R_TRIGGER      = 180.0   # C1 conservative primary trigger, reported mm
SAFE_FLOOR     = 100.0   # L2 emergency: any sensor <= this -> stop
NO_ECHO        = 2000.0  # sanitize invalid/no-echo readings to "far"
STANDOFF_LO    = 300.0   # a wall-facing baseline must be within [LO, HI]
STANDOFF_HI    = 1400.0
CRAWL_SPEED    = 150.0    # deg/s slow confirming crawl
CRAWL_MS       = 1200     # crawl duration
CRAWL_SETTLE   = 250
CRAWL_DROP_MM  = 40.0     # min decrease during crawl to count as wall-facing
MAX_CMD        = 1000.0   # fast-approach drive speed, deg/s (near motor max)
LIM_SPEED      = 1400.0
LIM_ACCEL      = 12000.0
LOOP_MS        = 20
EMIT_EVERY     = 3
MAX_RUN_MS     = 2500      # L3 tightened backstop
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
    # sanitized distance: invalid / non-positive -> NO_ECHO ("far"), never small
    try:
        v = float(u.distance())
        if v <= 0.0:
            return NO_ECHO
        return v
    except Exception:
        return NO_ECHO


def main():
    # -------------------------------------------------------------------
    # 1. Construct hard-coded devices ONCE (no probing -> no EBUSY risk).
    # -------------------------------------------------------------------
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
    if len(ultras) < 2:
        emit('err_too_few_ultras', float(len(ultras)))
        return

    for (p, _) in ultras:
        emit('map_ultra_port', float(PORT_LABEL[p]))
    emit('map_motorA_port', float(PORT_LABEL[MOTOR_A_PORT]))
    emit('map_motorB_port', float(PORT_LABEL[MOTOR_B_PORT]))

    def fwd_angle():
        return 0.5 * (SA * mA.angle() + SB * mB.angle())

    # raise limits so run() regulates both wheels at the same speed (straight)
    for m in (mA, mB):
        try:
            m.control.limits(speed=LIM_SPEED, acceleration=LIM_ACCEL)
        except Exception:
            pass

    # -------------------------------------------------------------------
    # 2. CONFIRMING FORWARD CRAWL (robust wall-facing ID + k_speed).
    #    Hard-coded-forward, slow, sustained -> strong signal.
    # -------------------------------------------------------------------
    mA.reset_angle(0)
    mB.reset_angle(0)
    h_base = hub.imu.heading()

    pre = [dist_of(u) for (_, u) in ultras]
    ang_pre = fwd_angle()
    for i in range(len(ultras)):
        emit('crawl_pre_u%d' % i, pre[i])
    emit('crawl_ang_pre_deg', ang_pre)

    # crawl forward slowly, watching the emergency floor even here
    mA.run(SA * CRAWL_SPEED)
    mB.run(SB * CRAWL_SPEED)
    t_crawl0 = clock.time()
    crawl_aborted = False
    while (clock.time() - t_crawl0) < CRAWL_MS:
        dmin = min([dist_of(u) for (_, u) in ultras])
        if dmin <= SAFE_FLOOR:
            crawl_aborted = True
            break
        wait(30)
    mA.hold(); mB.hold()
    wait(CRAWL_SETTLE)

    post = [dist_of(u) for (_, u) in ultras]
    ang_post = fwd_angle()
    for i in range(len(ultras)):
        emit('crawl_post_u%d' % i, post[i])
    emit('crawl_ang_post_deg', ang_post)
    emit('crawl_dhead', hub.imu.heading() - h_base)

    if crawl_aborted:
        emit('abort_crawl_floor', 1.0)
        return  # rover unexpectedly near something during the slow crawl

    # wall-facing = clearly decreased AND baseline within standoff band
    fwd_ids = []
    for i in range(len(ultras)):
        drop = pre[i] - post[i]
        emit('crawl_drop_u%d' % i, drop)
        if drop >= CRAWL_DROP_MM and STANDOFF_LO <= pre[i] <= STANDOFF_HI:
            fwd_ids.append(i)

    if len(fwd_ids) < 1:
        # No sensor tracked a wall ahead under confirmed-forward motion.
        emit('abort_no_forward_sensor', 1.0)
        return

    for i in fwd_ids:
        emit('fwd_sensor_id', float(PORT_LABEL[ultras[i][0]]))

    # onboard k_speed from the crawl (offset cancels): use the forward sensor
    # with the largest clean drop; convenience only, re-derivable from scalars.
    best = fwd_ids[0]
    for i in fwd_ids:
        if (pre[i] - post[i]) > (pre[best] - post[best]):
            best = i
    dang_deg = ang_post - ang_pre
    ddist = pre[best] - post[best]
    if dang_deg > 1.0:
        k_speed_crawl = ddist / (dang_deg * PI / 180.0)  # mm per rad
        emit('k_speed_crawl_mm_per_rad', k_speed_crawl)

    # -------------------------------------------------------------------
    # 3. FAST APPROACH at max speed, layered safety every loop.
    # -------------------------------------------------------------------
    mA.reset_angle(0)
    mB.reset_angle(0)

    mA.run(SA * MAX_CMD)
    mB.run(SB * MAX_CMD)

    omega_max_obs = 0.0
    i_loop = 0
    t0 = clock.time()
    triggered = False
    emergency = False
    t_trig = ang_trig = 0.0
    dfwd_trig = 0.0

    while True:
        t = clock.time()
        dvals = [dist_of(u) for (_, u) in ultras]
        d_fwd = dvals[fwd_ids[0]]
        for i in fwd_ids:
            if dvals[i] < d_fwd:
                d_fwd = dvals[i]
        d_all_min = min(dvals)
        h = hub.imu.heading()

        sp = 0.5 * (abs(mA.speed()) + abs(mB.speed()))
        if sp > omega_max_obs:
            omega_max_obs = sp

        if (i_loop % EMIT_EVERY) == 0:
            emit_at(t, 'd_fwd', d_fwd)
            emit_at(t, 'd_all_min', d_all_min)
            emit_at(t, 'heading', h)

        # L2 emergency backstop FIRST (crash prevention, identity-independent)
        if d_all_min <= SAFE_FLOOR:
            emergency = True
            t_trig = t; ang_trig = fwd_angle(); dfwd_trig = d_fwd
            break
        # L1 primary trigger
        if d_fwd <= R_TRIGGER:
            triggered = True
            t_trig = t; ang_trig = fwd_angle(); dfwd_trig = d_fwd
            break
        # L3 stuck backstop
        if (t - t0) > MAX_RUN_MS:
            break

        i_loop += 1
        wait(LOOP_MS)

    # -------------------------------------------------------------------
    # 4. STOP: hold() both, settle, latch rest.
    # -------------------------------------------------------------------
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

    # -------------------------------------------------------------------
    # 5. LATCHED SCALARS.
    # -------------------------------------------------------------------
    emit('triggered', 1.0 if triggered else 0.0)
    emit('emergency', 1.0 if emergency else 0.0)
    emit('trigger_report_fwd', dfwd_trig)
    for i in range(len(ultras)):
        emit('rest_u%d' % i, rest_vals[i])
    emit('angle_trigger_deg', ang_trig)
    emit('angle_rest_deg', ang_rest)
    emit('D_stop_deg', D_stop_deg)
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
