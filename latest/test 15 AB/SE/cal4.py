# =====================================================================
# CAL-4 -- near-range characterization.
# Purpose: (a) map ranger A's noise and validity floor down to ~85 mm,
# the region an A-based trigger would use; (b) a second, low-speed
# odometry scale over ~900 mm against a T1-anchored channel; (c) park
# the rover near the wall for OP-MEAS-2, which gives the SECOND anchor
# point for c_A -- currently anchored at exactly one distance (212 mm).
# Slow throughout: stopping distance is a few mm, so the interlocks
# stay protective.
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

C_A = -24              # OP-MEAS-1: true gap = A + C_A
C_B = 76               # derived: true gap = B + C_B
LOOP_MS = 20
US_SENTINEL = 1900
STOP_FLOOR_MM = 45     # never travel closer than this in true gap
K_LIM0_X1000 = 510     # mm/deg x1000, largest credible -- until measured
KP_TRIM = 40
FLIP_MDEG = 6000
YAW_ABORT_MDEG = 15000
DEBOUNCE = 2
STATIC_N = 15
STATIC_MS = 40
NI = 1000
MAX_LINES = 420
T_TOTAL_MS = 40000

# (A-target, speed dps)
STAGES = ((400, 300), (250, 150), (160, 80), (110, 80), (85, 80))

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
k_x1000 = K_LIM0_X1000

def now():
    return clock.time()

def rd(u):
    try:
        v = u.distance()
    except Exception:
        return US_SENTINEL
    if v is None or v < 0:
        return US_SENTINEL
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

def p_est(a, b):
    """Conservative true-gap estimate: the smallest of the valid channels."""
    p = 99999
    if a < US_SENTINEL and a > 40:
        p = a + C_A
    if b < US_SENTINEL and b > 60:
        q = b + C_B
        if q < p:
            p = q
    return p

def burst(tag):
    amn = 99999; amx = -1; asum = 0
    bmn = 99999; bmx = -1; bsum = 0
    n = 0
    for _i in range(STATIC_N):
        a, b, am, hd = sample()
        if a < amn: amn = a
        if a > amx: amx = a
        asum += a
        if b < bmn: bmn = b
        if b > bmx: bmx = b
        bsum += b
        n += 1
        wait(STATIC_MS)
    t = now()
    emit(t, tag + "_Amn", amn); emit(t, tag + "_Amx", amx)
    emit(t, tag + "_Aav", asum // n)
    emit(t, tag + "_Bmn", bmn); emit(t, tag + "_Bmx", bmx)
    emit(t, tag + "_Bav", bsum // n)
    emit(t, tag + "_ang", odo()); emit(t, tag + "_hd", hdg())
    return asum // n, bsum // n

try:
    m1 = Motor(Port.C); m2 = Motor(Port.D)
    uf1 = UltrasonicSensor(Port.A)
    uf2 = UltrasonicSensor(Port.B)
    ur = UltrasonicSensor(Port.E)
    m1.reset_angle(0); m2.reset_angle(0)
    try:
        hub.imu.reset_heading(0)
    except Exception:
        pass

    a_start, b_start = burst("s0")
    emit(now(), "start_rc", rd(ur))
    if a_start >= US_SENTINEL or b_start >= US_SENTINEL or a_start < 700:
        fault = 10
        emit(now(), "fault", fault)

    t_run = now()
    ang_prev = 0
    a_prev = a_start; b_prev = b_start
    p_track = a_start + C_A
    stage_no = 0

    while fault == 0 and stage_no < len(STAGES):
        target, vcr = STAGES[stage_no]
        stage_no += 1
        a_now, b_now, am0, hd0 = sample()
        p0 = p_track
        if p0 > 9000:
            fault = 15; break
        budget = ((p0 - STOP_FLOOR_MM) * 1000) // k_x1000
        if budget < 0:
            budget = 0
        emit(now(), "st%d_budget" % stage_no, budget)
        emit(now(), "st%d_p0" % stage_no, p0)

        trim_max = vcr // 3
        if trim_max < 20:
            trim_max = 20
        hsign = 1; flipped = 0
        hit = 0; deb = 0
        m1.run(s1 * vcr); m2.run(s2 * vcr)
        while True:
            a, b, am, hd = sample()
            if a < US_SENTINEL and a <= target:
                deb += 1
                if deb >= DEBOUNCE:
                    hit = 1; break
            else:
                deb = 0
            if am - am0 > budget:
                hit = 2; break
            if now() - t_run > T_TOTAL_MS:
                hit = 3; break
            if hd > YAW_ABORT_MDEG or hd < -YAW_ABORT_MDEG:
                hit = 4; break
            if flipped == 0 and (hd > FLIP_MDEG or hd < -FLIP_MDEG):
                hsign = -hsign; flipped = 1
            trim = (hsign * KP_TRIM * hd) // 1000
            if trim > trim_max: trim = trim_max
            if trim < -trim_max: trim = -trim_max
            if trim < 0:
                m1.run(s1 * vcr); m2.run(s2 * (vcr + trim))
            else:
                m1.run(s1 * (vcr - trim)); m2.run(s2 * vcr)
            wait(LOOP_MS)
        m1.brake(); m2.brake()
        wait(500)
        emit(now(), "st%d_hit" % stage_no, hit)
        a_st, b_st = burst("st%d" % stage_no)

        # refine the odometry scale on B where B is valid -- B is anchored
        # independently of A, so this is not circular with A's own linearity
        dang = odo() - ang_prev
        if dang > 100:
            dmm = 0
            if b_st < US_SENTINEL and b_prev < US_SENTINEL and b_st > 60:
                dmm = b_prev - b_st
            elif a_st < US_SENTINEL and a_prev < US_SENTINEL:
                dmm = a_prev - a_st
            if dmm > 40:
                k_new = (dmm * 1000) // dang
                if k_new > 250 and k_new < 800:
                    k_x1000 = (k_new * 103) // 100
                    emit(now(), "st%d_k1000" % stage_no, k_new)

        # position track: sensors may only LOWER it unless cross-validated.
        # A frozen ranger therefore cannot re-grant travel budget; the
        # odometry propagation keeps decrementing.
        pa = (a_st + C_A) if a_st < US_SENTINEL else 99999
        pb = (b_st + C_B) if (b_st < US_SENTINEL and b_st > 60) else 99999
        p_prop = p_track - ((dang * k_x1000) // 1000)
        resync = 0
        if pa < 99999 and pb < 99999:
            d = pa - pb
            if d < 0: d = -d
            if d < 30:
                p_track = pa if pa < pb else pb
                resync = 1
        if resync == 0:
            p_track = p_prop
            if pa < p_track:
                p_track = pa
        emit(now(), "st%d_ptrk" % stage_no, p_track)
        emit(now(), "st%d_sync" % stage_no, resync)
        ang_prev = odo(); a_prev = a_st; b_prev = b_st

        if hit != 1:
            emit(now(), "abort_stage", stage_no)
            break

    emit(now(), "final_ra", rd(uf1)); emit(now(), "final_rb", rd(uf2))
    emit(now(), "final_ang", odo()); emit(now(), "final_hd", hdg())
    emit(now(), "fault", fault)

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
        # decimated linearity trace: A, B and odometry over the whole traverse
        step = bi // 55
        if step < 1:
            step = 1
        i = 0
        while i < bi:
            t = bt[i]
            emit(t, "A", bA[i]); emit(t, "B", bB[i]); emit(t, "am", bam[i])
            i += step
        emit(clock.time(), "lines_used", lines)
        emit(clock.time(), "buf_used", bi)
    except Exception:
        pass
    stdout.write('{"event":"end"}\n')
