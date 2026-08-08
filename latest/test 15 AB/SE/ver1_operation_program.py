# =====================================================================
# VER-1 / OPERATION PROGRAM -- committed configuration, Verification Plan v1
#
# Trigger: fused estimate of TRUE position <= 81.0 mm.
# Estimator: ranger A through true = 0.9091*A - 2.5, gated against
#            odometry propagation. A frozen or outlying reading is
#            rejected and the estimate propagates; that is what makes
#            this robust to the 600 ms freeze seen in CAL-4.
# Brake is issued BEFORE any telemetry write (AR-002).
# If VER-1 confirms the frozen prediction this file is LOCKED unchanged
# for the five scored runs.
# =====================================================================
try:
    from usys import stdout
except ImportError:
    from sys import stdout

import math
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import wait, StopWatch

# ---- committed constants (Verification Plan v1 S1) ------------------
S_M1 = -1
S_M2 = 1
VMAX = 1000
LOOP_MS = 10

CAL_M = 0.9091           # true = CAL_M * A + CAL_C, anchored OP-MEAS-1/2
CAL_C = -2.5
BRACKET_HI = 250.0       # map trusted below this reading
P_TRIG = 81.0            # trigger on estimated true position, mm
D_TOTAL = 45.0           # composite trigger->rest travel, mm  (VER-1 test subject)
HALF_W = 90.0            # chassis half-width, conservative prior
K_ODO = 0.470            # mm/deg, centre of the bound range
K_HI = 0.505             # largest credible -- used for protective budgets
TOL_FAR = 40.0           # reading-vs-propagation gate, mm
TOL_NEAR = 20.0
P_TOL_SWITCH = 150.0
PROP_LIMIT_MM = 60.0     # max propagation without an accepted reading
STALE_N = 6              # identical raw readings = frozen channel; refresh is 24 ms
                         # so at cruise a genuine value repeats at most ~3 samples
FAR_ANG_LIMIT = 1900     # deg, backstop if the estimator never initialises
FAR_B_FLOOR = 300.0      # abort if B says we are this close and A has not initialised
C_B_CONS = 60.0          # conservative B offset (smallest observed)
YAW_ABORT_MDEG = 15000
T_LIMIT_MS = 8000
KP_TRIM = 40
TRIM_MAX = 120
FLIP_MDEG = 6000

GATE_A_LO = 800.0
GATE_A_HI = 1300.0
GATE_HD_MDEG = 3000
CLOSING_MS = 400
CLOSING_MIN_MM = 25.0

STATIC_N = 10
STATIC_MS = 40
SETTLE_MS = 700
NI = 500
MAX_LINES = 300

lines = 0

def emit(t, name, v):
    global lines
    if lines >= MAX_LINES:
        return
    lines += 1
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%d}\n' % (t, name, v))

bt = [0]*NI; bA = [0]*NI; bB = [0]*NI; bam = [0]*NI; bhd = [0]*NI; bpe = [0]*NI
bi = 0

def cap(t, a, b, am, hd, pe):
    global bi
    if bi >= NI:
        return
    i = bi
    bt[i] = t; bA[i] = a; bB[i] = b; bam[i] = am; bhd[i] = hd; bpe[i] = pe
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

def calib(a):
    return CAL_M * a + CAL_C

def sample(pe):
    a = rd(uf1); b = rd(uf2)
    am = odo(); hd = hdg()
    cap(now(), a, b, am, hd, int(pe))
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

    # ---------------- static pre-roll + gates ------------------------
    amn = 99999; amx = -1; asum = 0
    for _n in range(STATIC_N):
        a, b, am, hd = sample(0)
        if a < amn: amn = a
        if a > amx: amx = a
        asum += a
        wait(STATIC_MS)
    a0 = asum // STATIC_N
    b0 = rd(uf2); h0 = hdg()
    emit(now(), "start_A", a0); emit(now(), "start_Aspread", amx - amn)
    emit(now(), "start_B", b0); emit(now(), "start_hd", h0)
    if a0 < GATE_A_LO or a0 > GATE_A_HI or h0 > GATE_HD_MDEG or h0 < -GATE_HD_MDEG:
        fault = 10
        emit(now(), "fault", fault)

    # ---------------- approach ---------------------------------------
    if fault == 0:
        i_appr = bi
        t0 = now()
        init = 0; deb_a = -1
        p_est = 0.0; ang_last = 0; ang_ref = 0; budget = 0
        prop_mm = 0.0; n_acc = 0; n_rej = 0; prop_max = 0.0
        a_last_raw = -1; same_n = 0; n_stale = 0
        hsign = 1; flipped = 0
        triggered = 0
        m1.run(s1 * VMAX); m2.run(s2 * VMAX)

        while True:
            a, b, ang, hd = sample(p_est)
            t = now()

            if init == 0:
                # far field: ranger B is the reliable channel here
                if a < 1900 and a <= BRACKET_HI:
                    if deb_a >= 0 and abs(a - deb_a) < 30:
                        p_est = calib(a)
                        ang_last = ang; ang_ref = ang
                        budget = int((p_est - 40.0) / K_HI)
                        init = 1
                    else:
                        deb_a = a
                else:
                    deb_a = -1
                if init == 0:
                    if b < 1900 and (b + C_B_CONS) <= FAR_B_FLOOR:
                        fault = 16; break
                    if ang > FAR_ANG_LIMIT:
                        fault = 6; break
                    if t - t0 > T_LIMIT_MS:
                        fault = 7; break
                    if t - t0 > CLOSING_MS and a < 1900 and a > a0 - CLOSING_MIN_MM:
                        fault = 17; break
                    if hd > YAW_ABORT_MDEG or hd < -YAW_ABORT_MDEG:
                        fault = 14; break
                    if flipped == 0 and (hd > FLIP_MDEG or hd < -FLIP_MDEG):
                        hsign = -hsign; flipped = 1
                    steer(hd, hsign, VMAX)
                    wait(LOOP_MS)
                    continue

            # fused update
            d_ang = ang - ang_last
            ang_last = ang
            p_pred = p_est - d_ang * K_ODO
            tol = TOL_FAR if p_pred > P_TOL_SWITCH else TOL_NEAR
            # a frozen channel anchors its own prediction, so the residual
            # gate alone cannot see it: detect the freeze on the RAW value
            if a == a_last_raw:
                same_n += 1
            else:
                same_n = 0
                a_last_raw = a
            stale = 1 if same_n >= STALE_N else 0
            if stale:
                n_stale += 1
            acc = 0
            if a < 1900 and stale == 0:
                p_a = calib(a)
                dd = p_a - p_pred
                if dd < 0: dd = -dd
                if dd <= tol:
                    p_est = p_a; prop_mm = 0.0; acc = 1; n_acc += 1
            if acc == 0:
                p_est = p_pred
                prop_mm += d_ang * K_ODO
                if prop_mm > prop_max: prop_max = prop_mm
                n_rej += 1

            if prop_mm > PROP_LIMIT_MM:
                fault = 5; break
            if ang - ang_ref > budget:
                fault = 6; break
            if t - t0 > T_LIMIT_MS:
                fault = 7; break
            if hd > YAW_ABORT_MDEG or hd < -YAW_ABORT_MDEG:
                fault = 14; break
            if p_est <= P_TRIG:
                triggered = 1; break

            if flipped == 0 and (hd > FLIP_MDEG or hd < -FLIP_MDEG):
                hsign = -hsign; flipped = 1
            steer(hd, hsign, VMAX)
            wait(LOOP_MS)

        m1.brake(); m2.brake()          # FIRST -- no telemetry before this
        t_brake = now()
        i_trig = bi
        p_trig_act = p_est
        a_trig = a; b_trig = b
        ang_trig = odo(); hd_trig = hdg()
        prop_at_trig = prop_mm

        while now() - t_brake < SETTLE_MS:
            sample(p_est)
            wait(LOOP_MS)
        i_stop = bi

        # post-stop static
        rmn = 99999; rmx = -1; rsum = 0
        for _n in range(STATIC_N):
            a, b, am, hd = sample(p_est)
            if a < rmn: rmn = a
            if a > rmx: rmx = a
            rsum += a
            wait(STATIC_MS)
        a_rest = rsum // STATIC_N
        hd_rest = hdg()

        # onboard gap estimate, formed at the TRIGGER (A is expected
        # invalid at rest, so no rest reading is used)
        corner = HALF_W * math.sin(math.radians(abs(hd_rest) / 1000.0))
        gap_est = p_trig_act - D_TOTAL - corner

        emit(t_brake, "brake_cmd", 1)
        emit(now(), "trig_p", int(p_trig_act)); emit(now(), "trig_A", a_trig)
        emit(now(), "trig_B", b_trig); emit(now(), "trig_ang", ang_trig)
        emit(now(), "trig_hd", hd_trig); emit(now(), "trig_ok", triggered)
        emit(now(), "trig_fault", fault)
        emit(now(), "prop_at_trig_x10", int(prop_at_trig * 10))
        emit(now(), "prop_max_x10", int(prop_max * 10))
        emit(now(), "n_acc", n_acc); emit(now(), "n_rej", n_rej)
        emit(now(), "n_stale", n_stale)
        emit(now(), "rest_A", a_rest); emit(now(), "rest_Aspread", rmx - rmn)
        emit(now(), "rest_B", rd(uf2)); emit(now(), "rest_ang", odo())
        emit(now(), "rest_hd", hd_rest)
        emit(now(), "corner_x10", int(corner * 10))
        emit(now(), "GAP_EST_x10", int(gap_est * 10))
        emit(now(), "post_brake_deg", odo() - ang_trig)

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
            i = i_trig + 1
            while i < i_stop:
                if bam[i] == bam[i-1]:
                    emit(now(), "settle_ms", bt[i] - bt[i_trig]); break
                i += 1
        # thin trace: 20 samples before the trigger, then the braking window
        if i_trig >= 0:
            i = i_trig - 20
            if i < 0: i = 0
            lim = i_trig + 50
            if lim > i_stop: lim = i_stop
            while i < lim:
                t = bt[i]
                emit(t, "A", bA[i]); emit(t, "pe", bpe[i]); emit(t, "hd", bhd[i])
                i += 1
        emit(clock.time(), "lines_used", lines)
        emit(clock.time(), "buf_used", bi)
    except Exception:
        pass
    stdout.write('{"event":"end"}\n')
