# =============================================================================
# C1 -- characterisation run 1.   TEST LIKE YOU FLY.
#
# Structure:   [discovery preamble]  CORE  [reverse]  CORE  [creep]  [dump]
#
# CORE() is the operation program's control loop, byte-identical.  The operation
# program is exactly:  init -> CORE(literal ports/dirs, calibrated params) -> dump.
# Everything else in this file is characterisation-only and lives OUTSIDE the
# hot path.  No telemetry is written while the motors turn: samples go to
# pre-allocated buffers and are emitted after the wheels stop.
#
# All design parameters below are the CONSERVATIVE PRIOR set (Calibration Plan
# section 0), not calibrated values.  Worst-case-corner safety is analysed in
# the plan; nothing here is tuned by feel.
# =============================================================================
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()


def emit(s, v):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'
                 % (clock.time(), s, v))


# ----------------------------------------------------------------- buffers --
N = 1000
try:
    from array import array
    def mkbuf(n):
        return array('f', [0.0] * n)
except Exception:
    def mkbuf(n):
        return [0.0] * n

T_ = mkbuf(N)
D1_ = mkbuf(N)
D2_ = mkbuf(N)
OD_ = mkbuf(N)
HD_ = mkbuf(N)
bi = 0
marks = {}


def logrow(t, d1, d2, od, hd):
    global bi
    if bi < N:
        T_[bi] = t
        D1_[bi] = d1
        D2_[bi] = d2
        OD_[bi] = od
        HD_[bi] = hd
        bi += 1


def mark(name):
    marks[name] = bi
    emit("mark_" + name, bi)


def med(xs):
    ys = sorted(xs)
    return ys[len(ys) // 2]


# ------------------------------------------------- CONSERVATIVE PRIOR PARAMS
VCMD = 0            # filled from motor rated max
ACC_LIM = 4000      # deg/s^2, set explicitly so acceleration is reproducible
K_TRAVEL = 0.47     # mm per motor degree     PRIOR nominal   (TBD-03)
C_OFF = 120.0       # mm ranger offset        PRIOR UPPER     (TBD-01/02)
T_RESP = 0.150      # s effective latency     PRIOR UPPER     (TBD-06)
A_BRK = 1000.0      # mm/s^2 deceleration     PRIOR LOWER     (TBD-05)
TARGET_C1 = 350.0   # mm commanded stand-off  worst-corner safe (see plan s.0)
RFLOOR = 150.0      # mm raw-ranger floor failsafe
FAILSAFE_MIN = 120.0  # mm odometry floor failsafe
T_MAX_MS = 6000     # ms per-core watchdog
R_MIN_VALID = 20.0  # mm below this a reading is not a distance
R_MAX_VALID = 1900.0
KP_HEAD = 8.0       # deg/s of trim per degree of heading error
TRIM_MAX = 200.0    # deg/s, trim only ever REDUCES a command (CMP-12)
DT_MS = 10

# ------------------------------------------------------------ port discovery
PORTS = [Port.A, Port.B, Port.C, Port.D, Port.E, Port.F]
PNAME = ["A", "B", "C", "D", "E", "F"]
motors = []
rangers = []
colors = []
for i in range(6):
    dev = None
    try:
        dev = Motor(PORTS[i])
        motors.append((PNAME[i], dev))
        emit("port_motor_" + PNAME[i], 1)
        continue
    except Exception:
        pass
    try:
        dev = UltrasonicSensor(PORTS[i])
        rangers.append((PNAME[i], dev))
        emit("port_ranger_" + PNAME[i], 1)
        continue
    except Exception:
        pass
    try:
        dev = ColorSensor(PORTS[i])
        colors.append((PNAME[i], dev))
        emit("port_color_" + PNAME[i], 1)
    except Exception:
        emit("port_empty_" + PNAME[i], 1)

emit("n_motors", len(motors))
emit("n_rangers", len(rangers))
emit("n_colors", len(colors))

if len(motors) < 2 or len(rangers) < 2:
    emit("ABORT_inventory", 1)
    stdout.write('{"event":"end"}\n')
    raise SystemExit

mL = motors[0][1]
mR = motors[1][1]
for m in (mL, mR):
    try:
        m.control.limits(acceleration=ACC_LIM)
    except Exception:
        emit("warn_accel_limit", 0)
lim = mL.control.limits()
VCMD = lim[0]
emit("rated_max_speed_deg_s", VCMD)
emit("accel_limit_deg_s2", lim[1] if not isinstance(lim[1], tuple) else lim[1][0])
emit("torque_limit", lim[2])


def brake_all():
    try:
        mL.brake()
        mR.brake()
    except AttributeError:
        mL.stop()
        mR.stop()


def stop_all():
    mL.stop()
    mR.stop()


# --------------------------------------------- static classification of rangers
wait(200)
snap = []
for _ in range(15):
    snap.append([r[1].distance() for r in rangers])
    wait(20)
statics = []
for j in range(len(rangers)):
    vals = [s[j] for s in snap]
    mv = med(vals)
    sd = max(vals) - min(vals)
    statics.append(mv)
    emit("static_ranger_%s_med" % rangers[j][0], mv)
    emit("static_ranger_%s_spread" % rangers[j][0], sd)
for c in colors:
    emit("static_color_%s" % c[0], c[1].reflection())
a0 = hub.imu.acceleration()
for k in range(3):
    emit("static_accel_axis%d" % k, a0[k])
emit("static_heading", hub.imu.heading())

# the two in-range rangers that agree most closely look at the wall
best = (1e9, 0, 1)
for i in range(len(rangers)):
    for j in range(i + 1, len(rangers)):
        if statics[i] < R_MAX_VALID and statics[j] < R_MAX_VALID:
            d = abs(statics[i] - statics[j])
            if d < best[0]:
                best = (d, i, j)
iA, iB = best[1], best[2]
sA = rangers[iA][1]
sB = rangers[iB][1]
emit("fwd_pair_i", iA)
emit("fwd_pair_j", iB)
emit("fwd_pair_delta", best[0])
iRear = -1
for i in range(len(rangers)):
    if i != iA and i != iB:
        iRear = i
if iRear >= 0:
    emit("rear_ranger_static", statics[iRear])
    emit("rear_ranger_valid", 1.0 if statics[iRear] < R_MAX_VALID else 0.0)


def fwd_med(n=5):
    a = []
    b = []
    for _ in range(n):
        a.append(sA.distance())
        b.append(sB.distance())
        wait(6)
    return med(a), med(b)


# ------------------------------------------------------- polarity discovery --
S0 = 300


def pulse(sl, sr, ms):
    d0a, d0b = fwd_med()
    h0 = hub.imu.heading()
    mL.run(sl)
    mR.run(sr)
    wait(ms)
    brake_all()
    wait(250)
    d1a, d1b = fwd_med()
    h1 = hub.imu.heading()
    return (0.5 * ((d1a - d0a) + (d1b - d0b)), h1 - h0)


dd1, dh1 = pulse(S0, S0, 350)
emit("probe1_dd", dd1)
emit("probe1_dh", dh1)
pulse(-S0, -S0, 350)                       # undo

mirrored = abs(dh1) > 25.0
emit("probe_mirrored", 1.0 if mirrored else 0.0)
if not mirrored:
    s = -1 if dd1 > 0 else 1
    dirL, dirR = s, s
else:
    dd2, dh2 = pulse(S0, -S0, 350)
    emit("probe2_dd", dd2)
    emit("probe2_dh", dh2)
    pulse(-S0, S0, 350)                    # undo
    if dd2 < 0:
        dirL, dirR = 1, -1
    else:
        dirL, dirR = -1, 1
emit("dirL", dirL)
emit("dirR", dirR)

# which motor yaws which way (sets the steering-trim sign)
h0 = hub.imu.heading()
mL.run(dirL * S0)
wait(300)
brake_all()
wait(250)
dh3 = hub.imu.heading() - h0
mL.run(-dirL * S0)
wait(300)
brake_all()
wait(300)
yaw_sign = 1.0 if dh3 > 0 else -1.0
emit("probe3_dh_motorL_only", dh3)
emit("yaw_sign", yaw_sign)


# =============================================================================
# CORE -- the operation control loop.  Identical in the operation program.
# =============================================================================
def CORE(tag, dirL, dirR, target, c_off, t_resp, a_brk, k_travel,
         rfloor, failsafe_min):
    mL.reset_angle(0)
    mR.reset_angle(0)
    hub.imu.reset_heading(0)
    wait(250)

    a = []
    b = []
    for _ in range(11):
        a.append(sA.distance())
        b.append(sB.distance())
        wait(15)
    u0a, u0b = med(a), med(b)
    emit(tag + "_u0_A", u0a)
    emit(tag + "_u0_B", u0b)
    g0 = 0.5 * (u0a + u0b) - c_off              # start clearance estimate
    emit(tag + "_g0", g0)
    if u0a > 1500 or u0b > 1500 or u0a < 400 or u0b < 400:
        emit(tag + "_ABORT_start_implausible", 1)
        return None

    mark(tag + "_start")
    t0 = clock.time()
    mL.run(dirL * VCMD)
    mR.run(dirR * VCMD)

    trig = None
    reason = 0
    moved_ok = False
    nloop = 0
    dtmin = 1e9
    dtmax = 0.0
    tprev = t0
    while True:
        t = clock.time()
        dt = t - tprev
        if nloop > 2:
            if dt < dtmin:
                dtmin = dt
            if dt > dtmax:
                dtmax = dt
        tprev = t
        nloop += 1

        d1 = sA.distance()
        d2 = sB.distance()
        angL = mL.angle() * dirL
        angR = mR.angle() * dirR
        od = 0.5 * (angL + angR) * k_travel
        hd = hub.imu.heading()
        logrow(t, d1, d2, od, hd)

        v1 = R_MIN_VALID < d1 < R_MAX_VALID
        v2 = R_MIN_VALID < d2 < R_MAX_VALID
        if v1 and v2:
            g_us = min(d1, d2) - c_off
        elif v1:
            g_us = d1 - c_off
        elif v2:
            g_us = d2 - c_off
        else:
            g_us = None
        g_odo = g0 - od
        g_est = g_us if g_us is not None else g_odo

        v_meas = 0.5 * (abs(mL.speed()) + abs(mR.speed())) * k_travel
        thr = target + t_resp * v_meas + v_meas * v_meas / (2.0 * a_brk)

        if od > 15.0:
            moved_ok = True

        if g_est <= thr:
            reason = 1
        elif (v1 and d1 <= rfloor) or (v2 and d2 <= rfloor):
            reason = 2
        elif od >= (g0 - failsafe_min):
            reason = 3
        elif (t - t0) > T_MAX_MS:
            reason = 4
        elif (t - t0) > 400 and not moved_ok:
            reason = 5

        if reason:
            brake_all()
            trig = (t, d1, d2, od, hd, v_meas, thr, g_est)
            break

        e = hd
        red = KP_HEAD * e * yaw_sign
        if red > TRIM_MAX:
            red = TRIM_MAX
        if red < -TRIM_MAX:
            red = -TRIM_MAX
        cl = VCMD - (red if red > 0 else 0.0)
        cr = VCMD - (-red if red < 0 else 0.0)
        mL.run(dirL * cl)
        mR.run(dirR * cr)

        wait(DT_MS)

    mark(tag + "_trigger")
    emit(tag + "_trig_reason", reason)
    emit(tag + "_trig_t_ms", trig[0] - t0)
    emit(tag + "_trig_u_A", trig[1])
    emit(tag + "_trig_u_B", trig[2])
    emit(tag + "_trig_odo", trig[3])
    emit(tag + "_trig_heading", trig[4])
    emit(tag + "_trig_v_meas", trig[5])
    emit(tag + "_trig_thr", trig[6])
    emit(tag + "_trig_g_est", trig[7])
    emit(tag + "_loop_dt_min", dtmin)
    emit(tag + "_loop_dt_max", dtmax)
    emit(tag + "_loop_n", nloop)

    tb = clock.time()
    while clock.time() - tb < 900:
        angL = mL.angle() * dirL
        angR = mR.angle() * dirR
        logrow(clock.time(), sA.distance(), sB.distance(),
               0.5 * (angL + angR) * k_travel, hub.imu.heading())
        wait(DT_MS)
    mark(tag + "_rest")

    ra = []
    rb = []
    for _ in range(15):
        ra.append(sA.distance())
        rb.append(sB.distance())
        wait(15)
    odo_rest = 0.5 * (mL.angle() * dirL + mR.angle() * dirR) * k_travel
    emit(tag + "_rest_u_A", med(ra))
    emit(tag + "_rest_u_B", med(rb))
    emit(tag + "_rest_spread_A", max(ra) - min(ra))
    emit(tag + "_rest_odo", odo_rest)
    emit(tag + "_rest_heading", hub.imu.heading())
    emit(tag + "_rest_speed_L", mL.speed())
    emit(tag + "_rest_speed_R", mR.speed())
    ar = hub.imu.acceleration()
    for k in range(3):
        emit(tag + "_rest_accel_axis%d" % k, ar[k])
    emit(tag + "_overshoot_odo", odo_rest - trig[3])
    return (med(ra), med(rb), odo_rest, trig)


# --------------------------------------------------------------- run CORE x2
r1 = CORE("c1", dirL, dirR, TARGET_C1, C_OFF, T_RESP, A_BRK, K_TRAVEL,
          RFLOOR, FAILSAFE_MIN)

if r1 is not None:
    # reverse back toward the start line (characterisation-only)
    mark("rev_start")
    a0m = 0.5 * (mL.angle() * dirL + mR.angle() * dirR)
    mL.run(-dirL * 650)
    mR.run(-dirR * 650)
    tb = clock.time()
    while clock.time() - tb < 4000:
        back = (a0m - 0.5 * (mL.angle() * dirL + mR.angle() * dirR)) * K_TRAVEL
        d1 = sA.distance()
        logrow(clock.time(), d1, sB.distance(),
               0.5 * (mL.angle() * dirL + mR.angle() * dirR) * K_TRAVEL,
               hub.imu.heading())
        if back > 480 or d1 > 1150:
            break
        wait(25)
    brake_all()
    wait(700)
    emit("rev_done_u_A", sA.distance())

    r2 = CORE("c2", dirL, dirR, TARGET_C1, C_OFF, T_RESP, A_BRK, K_TRAVEL,
              RFLOOR, FAILSAFE_MIN)

    # ------------------------------------------------ creep to contact ------
    # Bounds the ranger's near field and gives an onboard zero: at contact the
    # true clearance is 0, so c = u(start of creep) - travel(creep).
    mark("creep_start")
    mL.reset_angle(0)
    mR.reset_angle(0)
    u_creep0_A = med([sA.distance() for _ in range(9)])
    u_creep0_B = med([sB.distance() for _ in range(9)])
    emit("creep_u0_A", u_creep0_A)
    emit("creep_u0_B", u_creep0_B)

    FAST = int(200.0 / K_TRAVEL)
    SLOW = int(60.0 / K_TRAVEL)
    mL.run(dirL * FAST)
    mR.run(dirR * FAST)
    slowed = False
    stall = 0
    last = 0.0
    tb = clock.time()
    contact_odo = None
    while clock.time() - tb < 12000:
        d1 = sA.distance()
        d2 = sB.distance()
        od = 0.5 * (mL.angle() * dirL + mR.angle() * dirR) * K_TRAVEL
        logrow(clock.time(), d1, d2, od, hub.imu.heading())
        if not slowed and min(d1, d2) < 220:
            mL.run(dirL * SLOW)
            mR.run(dirR * SLOW)
            slowed = True
            mark("creep_slow")
        if slowed:
            if od - last < 0.6:
                stall += 1
            else:
                stall = 0
            if stall >= 4:
                contact_odo = od
                break
        last = od
        if od > 700:
            break
        wait(25)
    brake_all()
    wait(400)
    od_end = 0.5 * (mL.angle() * dirL + mR.angle() * dirR) * K_TRAVEL
    ac = hub.imu.acceleration()
    emit("creep_contact_detected", 1.0 if contact_odo is not None else 0.0)
    emit("creep_travel_to_contact", od_end)
    emit("creep_contact_u_A", med([sA.distance() for _ in range(9)]))
    emit("creep_contact_u_B", med([sB.distance() for _ in range(9)]))
    emit("creep_contact_heading", hub.imu.heading())
    for k in range(3):
        emit("creep_contact_accel_axis%d" % k, ac[k])
    mark("creep_end")

stop_all()

# ------------------------------------------------------------------ dump ----
# Scalars have already been emitted (most valuable first).  Series last, with a
# stride budget so the BLE dump stays short.
def dump(name, arr, i0, i1, stride):
    if i1 > bi:
        i1 = bi
    i = i0
    while i < i1:
        stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%.1f}\n'
                     % (int(T_[i]), name, arr[i]))
        i += stride


emit("buffer_used", bi)
segs = []
for tag in ("c1", "c2"):
    s = marks.get(tag + "_start")
    g = marks.get(tag + "_trigger")
    r = marks.get(tag + "_rest")
    if s is not None and g is not None and r is not None:
        segs.append((s, g, r))
for (s, g, r) in segs:
    dump("d1", D1_, s, g, 5)
    dump("od", OD_, s, g, 5)
    dump("hd", HD_, s, g, 20)
    dump("d1", D1_, g, r, 1)
    dump("d2", D2_, g, r, 1)
    dump("od", OD_, g, r, 1)
cs = marks.get("creep_start")
ce = marks.get("creep_end", bi)
if cs is not None:
    dump("d1", D1_, cs, ce, 3)
    dump("d2", D2_, cs, ce, 3)
    dump("od", OD_, cs, ce, 3)

stdout.write('{"event":"end"}\n')
