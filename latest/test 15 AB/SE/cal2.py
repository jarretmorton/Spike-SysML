# =====================================================================
# CAL-2 -- characterization program (supersedes CAL-1 after AR-001)
# Port map and motor signs are now KNOWN (CAL-1, tier T2) and hard-coded.
# Discovery deleted; replaced by a straight confirmation nudge + gates.
# S3 is the flight loop: operation = this loop, new constants, no S1/S2/S5/S6.
# =====================================================================
try:
    from usys import stdout
except ImportError:
    from sys import stdout

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import wait, StopWatch

# ---- established by CAL-1 -------------------------------------------
S_M1 = -1                # Port C sign for forward
S_M2 = 1                 # Port D sign for forward
VMAX = 1000              # deg/s, device ceiling

LOOP_MS       = 10
R_TRIG_MM     = 450
DISAGREE_MM   = 300      # AR-001 A-3: rangers differ ~124 mm by geometry
STALE_MS      = 500
US_SENTINEL   = 1900
GATE_LO_MM    = 600      # start-line validity gate
GATE_HI_MM    = 1500
GATE_HEAD_MDEG = 3000
NUDGE_DPS     = 250
NUDGE_MS      = 300
CREEP_F1      = 0.20
CREEP_F2      = 0.08
R_CREEP1_MM   = 250
R_ANCHOR_MM   = 130
STATIC_N      = 15
STATIC_MS     = 40
SETTLE_MS     = 700
NI            = 900
MAX_LINES     = 900
T_APPROACH_MS = 6000

lines = 0

def emit(t, name, v):
    global lines
    if lines >= MAX_LINES:
        return
    lines += 1
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%d}\n' % (t, name, v))

bt = [0]*NI; bph = [0]*NI
bra = [0]*NI; brb = [0]*NI; brc = [0]*NI
bal = [0]*NI; bar = [0]*NI; bsl = [0]*NI; bsr = [0]*NI
bhd = [0]*NI; bax = [0]*NI
bi = 0

def cap(t, ph, ra, rb, rc, al, ar, sl, sr, hd, ax):
    global bi
    if bi >= NI:
        return
    i = bi
    bt[i] = t; bph[i] = ph
    bra[i] = ra; brb[i] = rb; brc[i] = rc
    bal[i] = al; bar[i] = ar; bsl[i] = sl; bsr[i] = sr
    bhd[i] = hd; bax[i] = ax
    bi = i + 1

def dump(i0, i1, step, full):
    i = i0
    if i < 0:
        i = 0
    while i < i1 and i < bi:
        t = bt[i]
        emit(t, "ra", bra[i]); emit(t, "rb", brb[i])
        emit(t, "al", bal[i]); emit(t, "ar", bar[i])
        emit(t, "hd", bhd[i])
        if full:
            emit(t, "rc", brc[i]); emit(t, "sl", bsl[i]); emit(t, "sr", bsr[i])
            emit(t, "ph", bph[i]); emit(t, "ax", bax[i])
        i += step

hub = PrimeHub()
clock = StopWatch()
m1 = None; m2 = None
s1 = S_M1; s2 = S_M2
i_trig = -1; i_stop = -1
fault = 0
r = US_SENTINEL

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

def accx():
    try:
        return int(hub.imu.acceleration()[0])
    except Exception:
        return 0

def hdg():
    try:
        return int(hub.imu.heading() * 1000.0)
    except Exception:
        return 0

def drive(v):
    m1.run(s1 * v); m2.run(s2 * v)

def brake_both():
    m1.brake(); m2.brake()

def odo():
    return (s1 * m1.angle() + s2 * m2.angle()) * 0.5

def sample(ph, ax):
    ra = rd(uf1); rb = rd(uf2); rc = rd(ur)
    try:
        al = int(s1 * m1.angle()); ar = int(s2 * m2.angle())
        sl = int(s1 * m1.speed()); sr = int(s2 * m2.speed())
    except Exception:
        al = 0; ar = 0; sl = 0; sr = 0
    cap(now(), ph, ra, rb, rc, al, ar, sl, sr, hdg(), ax)
    return ra, rb, al, ar

def fuse(ra, rb):
    a_ok = ra < US_SENTINEL
    b_ok = rb < US_SENTINEL
    if a_ok and b_ok:
        return (ra if ra < rb else rb), 1
    if a_ok:
        return ra, 0
    if b_ok:
        return rb, 0
    return US_SENTINEL, -1

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

    # ---------------- S1: static pre-roll + validity gate -------------
    ax = accx()
    for _n in range(STATIC_N):
        sample(1, ax)
        wait(STATIC_MS)
    a0 = rd(uf1); b0 = rd(uf2); c0 = rd(ur)
    emit(now(), "start_ra", a0); emit(now(), "start_rb", b0)
    emit(now(), "start_rc", c0); emit(now(), "start_hd", hdg())

    ok_a = (a0 > GATE_LO_MM) and (a0 < GATE_HI_MM)
    ok_b = (b0 > GATE_LO_MM) and (b0 < GATE_HI_MM)
    h_now = hdg()
    ok_h = (h_now < GATE_HEAD_MDEG) and (h_now > -GATE_HEAD_MDEG)
    if not (ok_a and ok_b and ok_h):
        fault = 10
        emit(now(), "gate_ok_a", 1 if ok_a else 0)
        emit(now(), "gate_ok_b", 1 if ok_b else 0)
        emit(now(), "gate_ok_h", 1 if ok_h else 0)
        emit(now(), "fault", fault)

    # ---------------- S2: straight confirmation nudge -----------------
    if fault == 0:
        drive(NUDGE_DPS)
        t_end = now() + NUDGE_MS
        while now() < t_end:
            sample(2, ax)
            wait(LOOP_MS)
        brake_both(); wait(300)
        a1 = rd(uf1); b1 = rd(uf2); c1 = rd(ur)
        d_ang = odo()
        emit(now(), "nudge_dra", a1 - a0); emit(now(), "nudge_drb", b1 - b0)
        emit(now(), "nudge_drc", c1 - c0)
        emit(now(), "nudge_dhd", hdg())
        emit(now(), "nudge_dang", int(d_ang))

        fwd_ok = 0
        if (a1 < a0 - 10) or (b1 < b0 - 10):
            fwd_ok = 1
        elif (a1 > a0 + 10) and (b1 > b0 + 10):
            s1 = -s1; s2 = -s2          # signs inverted: correct and continue
            fwd_ok = -1
        else:
            fault = 11
        emit(now(), "fwd_ok", fwd_ok)
        emit(now(), "sign_m1", s1); emit(now(), "sign_m2", s2)

        # return to the start line by odometry
        if fault == 0:
            a_now = odo()
            drive(-NUDGE_DPS if a_now > 0 else NUDGE_DPS)
            t_end = now() + 2500
            while now() < t_end:
                sample(2, ax)
                a_cur = odo()
                if (a_now > 0 and a_cur <= 0) or (a_now <= 0 and a_cur >= 0):
                    break
                wait(LOOP_MS)
            brake_both(); wait(300)
            emit(now(), "return_ang", int(odo()))
            emit(now(), "return_hd", hdg())
            m1.reset_angle(0); m2.reset_angle(0)
            # re-gate after the nudge: the rangers must still see the wall
            a2 = rd(uf1); b2 = rd(uf2)
            emit(now(), "pre_ra", a2); emit(now(), "pre_rb", b2)
            if not ((a2 < GATE_HI_MM) or (b2 < GATE_HI_MM)):
                fault = 12
                emit(now(), "fault", fault)

    # ---------------- S3: full-speed approach (FLIGHT LOOP) -----------
    if fault == 0:
        t0 = now(); t_lastchange = t0; r_last = -1
        triggered = False; k = 0
        drive(VMAX)
        while True:
            if k % 3 == 0:
                ax = accx()
            ra, rb, al, ar = sample(3, ax)
            r, both = fuse(ra, rb)
            t = now()
            if both == 1 and (ra - rb > DISAGREE_MM or rb - ra > DISAGREE_MM):
                fault = 3; break
            if both == -1:
                fault = 4; break
            if r != r_last:
                r_last = r; t_lastchange = t
            elif t - t_lastchange > STALE_MS:
                fault = 5; break
            if t - t0 > T_APPROACH_MS:
                fault = 7; break
            if r <= R_TRIG_MM:
                triggered = True; break
            k += 1
            wait(LOOP_MS)

        i_trig = bi
        emit(now(), "trig_r", r); emit(now(), "trig_ra", ra); emit(now(), "trig_rb", rb)
        emit(now(), "trig_ang", int(odo()))
        emit(now(), "trig_ok", 1 if triggered else 0)
        emit(now(), "trig_fault", fault)
        m1.brake(); m2.brake()
        t_brake = now()
        emit(t_brake, "brake_cmd", 1)

        while now() - t_brake < SETTLE_MS:
            sample(4, ax)
            wait(LOOP_MS)
        i_stop = bi

        # ---------------- S4: post-stop static ------------------------
        for _n in range(STATIC_N):
            sample(5, ax)
            wait(STATIC_MS)
        emit(now(), "rest_ra", rd(uf1)); emit(now(), "rest_rb", rd(uf2))
        emit(now(), "rest_rc", rd(ur))
        emit(now(), "rest_ang", int(odo())); emit(now(), "rest_hd", hdg())

        # ---------------- S5: two-stage creep to the anchor ------------
        for frac, r_tgt, ph in ((CREEP_F1, R_CREEP1_MM, 6), (CREEP_F2, R_ANCHOR_MM, 7)):
            v = int(VMAX * frac)
            drive(v)
            t_c = now()
            while True:
                ra, rb, al, ar = sample(ph, ax)
                r, both = fuse(ra, rb)
                if both == -1:
                    fault = 13; break
                if r <= r_tgt:
                    break
                if now() - t_c > 9000:
                    fault = 8; break
                wait(LOOP_MS)
            m1.brake(); m2.brake()
            wait(400)
            emit(now(), "creep%d_r" % ph, r)
            emit(now(), "creep%d_ang" % ph, int(odo()))
            emit(now(), "creep%d_fault" % ph, fault)
            if fault != 0:
                break

        # ---------------- S6: anchor hold -----------------------------
        for _n in range(STATIC_N):
            sample(8, ax)
            wait(STATIC_MS)
        emit(now(), "anchor_ra", rd(uf1)); emit(now(), "anchor_rb", rd(uf2))
        emit(now(), "anchor_rc", rd(ur))
        emit(now(), "anchor_ang", int(odo())); emit(now(), "anchor_hd", hdg())
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
        if i_trig >= 0:
            hi = i_stop if i_stop > 0 else bi
            dump(i_trig - 30, hi, 1, True)     # braking window, all channels
            dump(0, i_trig - 30, 10, False)    # statics + nudge + cruise
            dump(hi, bi, 10, False)            # settle + creep + anchor
        else:
            dump(0, bi, 6, False)
        emit(clock.time(), "lines_used", lines)
        emit(clock.time(), "buf_used", bi)
    except Exception:
        pass
    stdout.write('{"event":"end"}\n')
