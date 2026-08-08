# =====================================================================
# VER-3 / OPERATION PROGRAM  -- odometry dead-reckoning architecture
#
# Ranging is DEMOTED. VER-2 showed ranger A's absolute map is unstable
# across runs (+24, +13, -155 mm against three operator anchors) and
# that a rate-consistency gate is structurally blind to a constant
# offset. Odometry, checked against all three anchors, fits
#     rest_position = 1000 - 0.500 * rest_angle
# with residuals of -1.5 and 0.0 mm on two independent runs.
#
# Primary: brake when mean wheel angle reaches ANG_BRAKE.
# Rangers: gross-failure cross-check only, never in the control path.
# =====================================================================
try:
    from usys import stdout
except ImportError:
    from sys import stdout

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import wait, StopWatch

S_M1 = -1
S_M2 = 1
VMAX = 1000
LOOP_MS = 10

D0_MM = 1000.0            # start line, anchored by CAL-3 and VER-2 ground truth
K_CRUISE = 0.500          # mm/deg at cruise, same two anchors
POST_BRAKE_DEG = 29.0     # mean of 30 (CAL-3) and 28 (VER-2)
G_TARGET = 30.0
ANG_BRAKE = int((D0_MM - G_TARGET) / K_CRUISE - POST_BRAKE_DEG)   # = 1911

CLOSE_CHECK_ANG = 800     # by here a ranger must have closed this much
CLOSE_CHECK_MM = 250
MOVING_MS = 500
MOVING_MIN_DEG = 150
NEAR_WALL_MM = 10         # last-ditch: any ranger this low -> brake
YAW_ABORT_MDEG = 20000
T_LIMIT_MS = 8000
KP_TRIM = 40
TRIM_MAX = 120
FLIP_MDEG = 6000
GATE_R_LO = 600
GATE_R_HI = 1400

STATIC_N = 10
STATIC_MS = 40
SETTLE_MS = 700
NI = 400
MAX_LINES = 260

lines = 0

def emit(t, name, v):
    global lines
    if lines >= MAX_LINES:
        return
    lines += 1
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%d}\n' % (t, name, v))

bt = [0]*NI; bA = [0]*NI; bB = [0]*NI; bam = [0]*NI; bhd = [0]*NI
bi = 0

def cap(t, a, b, am, hd):
    global bi
    if bi >= NI:
        return
    i = bi
    bt[i] = t; bA[i] = a; bB[i] = b; bam[i] = am; bhd[i] = hd
    bi = i + 1

hub = PrimeHub()
clock = StopWatch()
m1 = None; m2 = None
s1 = S_M1; s2 = S_M2
fault = 0
i_trig = -1; i_stop = -1; i_appr = -1

def now():
    return clock.time()

def rd(u):
    try:
        v = u.distance()
    except Exception:
        return 2000
    if v is None or v < 0:
        return 2000
    return int(v)

def hdg():
    try:
        return int(hub.imu.heading() * 1000.0)
    except Exception:
        return 0

def odo():
    return (s1 * m1.angle() + s2 * m2.angle()) // 2

def sample():
    a = rd(uf1); b = rd(uf2)
    am = odo(); hd = hdg()
    cap(now(), a, b, am, hd)
    return a, b, am, hd

def steer(hd, hsign, v):
    trim = (hsign * KP_TRIM * hd) // 1000
    if trim > TRIM_MAX: trim = TRIM_MAX
    if trim < -TRIM_MAX: trim = -TRIM_MAX
    if trim < 0:
        m1.run(s1 * v); m2.run(s2 * (v + trim))
    else:
        m1.run(s1 * (v - trim)); m2.run(s2 * v)

try:
    m1 = Motor(Port.C); m2 = Motor(Port.D)
    uf1 = UltrasonicSensor(Port.A)
    uf2 = UltrasonicSensor(Port.B)
    m1.reset_angle(0); m2.reset_angle(0)
    try:
        hub.imu.reset_heading(0)
    except Exception:
        pass

    asum = 0; bsum = 0
    for _n in range(STATIC_N):
        a, b, am, hd = sample()
        asum += a; bsum += b
        wait(STATIC_MS)
    a0 = asum // STATIC_N
    b0 = bsum // STATIC_N
    emit(now(), "start_A", a0); emit(now(), "start_B", b0)
    emit(now(), "start_hd", hdg())
    emit(now(), "ANG_BRAKE", ANG_BRAKE)
    if (a0 < GATE_R_LO or a0 > GATE_R_HI) and (b0 < GATE_R_LO or b0 > GATE_R_HI):
        fault = 10
        emit(now(), "fault", fault)

    if fault == 0:
        i_appr = bi
        t0 = now()
        hsign = 1; flipped = 0
        braked_by = 0
        m1.run(s1 * VMAX); m2.run(s2 * VMAX)

        while True:
            a, b, ang, hd = sample()
            t = now()

            if ang >= ANG_BRAKE:
                braked_by = 1; break
            if a < NEAR_WALL_MM or b < NEAR_WALL_MM:
                braked_by = 2; fault = 18; break
            if t - t0 > MOVING_MS and ang < MOVING_MIN_DEG:
                braked_by = 3; fault = 17; break
            if ang > CLOSE_CHECK_ANG:
                if (a > a0 - CLOSE_CHECK_MM) and (b > b0 - CLOSE_CHECK_MM):
                    braked_by = 4; fault = 19; break
            if t - t0 > T_LIMIT_MS:
                braked_by = 5; fault = 7; break
            if hd > YAW_ABORT_MDEG or hd < -YAW_ABORT_MDEG:
                braked_by = 6; fault = 14; break

            if flipped == 0 and (hd > FLIP_MDEG or hd < -FLIP_MDEG):
                hsign = -hsign; flipped = 1
            steer(hd, hsign, VMAX)
            wait(LOOP_MS)

        m1.brake(); m2.brake()          # FIRST -- no telemetry before this
        t_brake = now()
        i_trig = bi
        ang_brake_act = odo()
        hd_brake = hdg()

        while now() - t_brake < SETTLE_MS:
            sample()
            wait(LOOP_MS)
        i_stop = bi

        rasum = 0; rbsum = 0
        for _n in range(STATIC_N):
            a, b, am, hd = sample()
            rasum += a; rbsum += b
            wait(STATIC_MS)
        rest_ang = odo()
        gap_est = D0_MM - K_CRUISE * rest_ang

        emit(t_brake, "brake_cmd", 1)
        emit(now(), "brake_ang", ang_brake_act); emit(now(), "brake_hd", hd_brake)
        emit(now(), "braked_by", braked_by); emit(now(), "fault", fault)
        emit(now(), "rest_ang", rest_ang)
        emit(now(), "post_brake_deg", rest_ang - ang_brake_act)
        emit(now(), "rest_A", rasum // STATIC_N); emit(now(), "rest_B", rbsum // STATIC_N)
        emit(now(), "rest_hd", hdg())
        emit(now(), "GAP_EST_x10", int(gap_est * 10))

except Exception as e:
    try:
        stdout.write('{"timestamp_ms":%d,"sensor":"exception","value":-1}\n' % clock.time())
        stdout.write("TRACE %s\n" % repr(e))
    except Exception:
        pass

finally:
    try:
        if m1 is not None:
            m1.brake()
        if m2 is not None:
            m2.brake()
    except Exception:
        pass
    try:
        if i_appr >= 0 and i_trig > i_appr:
            n = 0; s = 0; mn = 9999; mx = 0
            i = i_appr + 1
            while i < i_trig:
                d = bt[i] - bt[i-1]
                n += 1; s += d
                if d < mn: mn = d
                if d > mx: mx = d
                i += 1
            if n > 0:
                emit(now(), "loop_mn", mn); emit(now(), "loop_mx", mx)
                emit(now(), "loop_av10", (s * 10) // n)
            mnh = 999999; mxh = -999999
            i = i_appr
            while i < i_trig:
                v = bhd[i]
                if v < mnh: mnh = v
                if v > mxh: mxh = v
                i += 1
            emit(now(), "appr_hd_mn", mnh); emit(now(), "appr_hd_mx", mxh)
        if i_trig >= 0:
            i = i_trig - 15
            if i < 0: i = 0
            lim = i_trig + 40
            if lim > i_stop: lim = i_stop
            while i < lim:
                t = bt[i]
                emit(t, "am", bam[i]); emit(t, "hd", bhd[i]); emit(t, "A", bA[i])
                i += 1
        emit(clock.time(), "lines_used", lines)
        emit(clock.time(), "buf_used", bi)
    except Exception:
        pass
    stdout.write('{"event":"end"}\n')
