# =====================================================================
# CAL-3 -- characterization program (supersedes CAL-2 after AR-002)
# Changes: (1) brake BEFORE any telemetry write; (2) closed-loop heading
# hold that trims only the leading wheel; (3) ranger A demoted to
# cross-check, degrade-not-abort on disagreement; (4) fault latch fixed;
# (5) on-hub aggregation -- scalars, not traces, to fit the ~30 line/s pipe.
# S3 is the flight loop.
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

LOOP_MS       = 10
R_TRIG_MM     = 250
US_SENTINEL   = 1900
GATE_LO_MM    = 600
GATE_HI_MM    = 1500
GATE_HEAD_MDEG = 3000
KP_TRIM       = 40        # deg/s of wheel trim per degree of heading error
TRIM_MAX      = 120       # <= 12% of VMAX
FLIP_MDEG     = 6000      # correction demonstrably wrong -> invert sign once
YAW_ABORT_MDEG = 15000    # rangers degrade badly past ~20 deg
K_ODO_MAX     = 0.513     # largest credible mm/deg -> earliest interlock
NUDGE_DPS     = 250
NUDGE_MS      = 300
CREEP_F1      = 0.35
CREEP_F2      = 0.10
R_CREEP1_MM   = 250
R_ANCHOR_MM   = 130
STATIC_N      = 15
STATIC_MS     = 40
SETTLE_MS     = 700
NI            = 900
MAX_LINES     = 400

lines = 0

def emit(t, name, v):
    global lines
    if lines >= MAX_LINES:
        return
    lines += 1
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%d}\n' % (t, name, v))

bt = [0]*NI; bph = [0]*NI
bra = [0]*NI; brb = [0]*NI; brc = [0]*NI
bal = [0]*NI; bar = [0]*NI; bhd = [0]*NI
bi = 0

def cap(t, ph, ra, rb, rc, al, ar, hd):
    global bi
    if bi >= NI:
        return
    i = bi
    bt[i] = t; bph[i] = ph
    bra[i] = ra; brb[i] = rb; brc[i] = rc
    bal[i] = al; bar[i] = ar; bhd[i] = hd
    bi = i + 1

hub = PrimeHub()
clock = StopWatch()
m1 = None; m2 = None
s1 = S_M1; s2 = S_M2
i_trig = -1; i_stop = -1; i_appr = -1
i_s1 = -1; i_s1e = -1; i_s4 = -1; i_s4e = -1; i_s6 = -1; i_s6e = -1
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

def sample(ph):
    ra = rd(uf1); rb = rd(uf2); rc = rd(ur)
    try:
        al = int(s1 * m1.angle()); ar = int(s2 * m2.angle())
    except Exception:
        al = 0; ar = 0
    hd = hdg()
    cap(now(), ph, ra, rb, rc, al, ar, hd)
    return ra, rb, al, ar, hd

def primary(ra, rb):
    # B is trigger-grade (AR-002); A is cross-check only
    if rb < US_SENTINEL:
        return rb, (0 if ra >= US_SENTINEL else 1)
    if ra < US_SENTINEL:
        return ra, 2
    return US_SENTINEL, -1

def stats(tag, arr, i0, i1, vmax_ok):
    if i0 < 0 or i1 <= i0:
        return
    n = 0; s = 0; mn = 999999; mx = -999999
    i = i0
    while i < i1 and i < bi:
        v = arr[i]
        if v < vmax_ok:
            n += 1; s += v
            if v < mn: mn = v
            if v > mx: mx = v
        i += 1
    t = now()
    emit(t, tag + "_n", n)
    if n > 0:
        emit(t, tag + "_mn", mn); emit(t, tag + "_mx", mx)
        emit(t, tag + "_av", s // n)

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

    # ---------------- S1: static pre-roll + gates ---------------------
    i_s1 = bi
    for _n in range(STATIC_N):
        sample(1)
        wait(STATIC_MS)
    i_s1e = bi
    a0 = rd(uf1); b0 = rd(uf2); c0 = rd(ur)
    emit(now(), "start_ra", a0); emit(now(), "start_rb", b0)
    emit(now(), "start_rc", c0)

    ok_b = (b0 > GATE_LO_MM) and (b0 < GATE_HI_MM)
    h0 = hdg()
    ok_h = (h0 < GATE_HEAD_MDEG) and (h0 > -GATE_HEAD_MDEG)
    if not (ok_b and ok_h):
        fault = 10
        emit(now(), "gate_b", 1 if ok_b else 0)
        emit(now(), "gate_h", 1 if ok_h else 0)

    # ---------------- S2: straight confirmation nudge -----------------
    if fault == 0:
        drive(NUDGE_DPS)
        t_end = now() + NUDGE_MS
        while now() < t_end:
            sample(2)
            wait(LOOP_MS)
        brake_both(); wait(300)
        b1 = rd(uf2); c1 = rd(ur)
        emit(now(), "nudge_drb", b1 - b0); emit(now(), "nudge_drc", c1 - c0)
        emit(now(), "nudge_dang", int(odo()))
        if b1 < b0 - 10:
            emit(now(), "fwd_ok", 1)
        elif b1 > b0 + 10:
            s1 = -s1; s2 = -s2
            emit(now(), "fwd_ok", -1)
        else:
            fault = 11
            emit(now(), "fwd_ok", 0)

        if fault == 0:
            a_now = odo()
            drive(-NUDGE_DPS if a_now > 0 else NUDGE_DPS)
            t_end = now() + 2500
            while now() < t_end:
                sample(2)
                a_cur = odo()
                if (a_now > 0 and a_cur <= 0) or (a_now <= 0 and a_cur >= 0):
                    break
                wait(LOOP_MS)
            brake_both(); wait(400)
            m1.reset_angle(0); m2.reset_angle(0)
            try:
                hub.imu.reset_heading(0)     # approach starts from zero
            except Exception:
                pass
            b2 = rd(uf2)
            emit(now(), "pre_rb", b2)
            if b2 >= GATE_HI_MM:
                fault = 12

    # ---------------- S3: full-speed approach (FLIGHT LOOP) -----------
    if fault == 0:
        b_start = rd(uf2)
        ang_lim = int((b_start - 60) / K_ODO_MAX)
        emit(now(), "ang_lim", ang_lim)
        i_appr = bi
        t0 = now(); t_lastchange = t0; r_last = -1
        triggered = False
        hsign = 1; flipped = 0
        drive(VMAX)
        while True:
            ra, rb, al, ar, hd = sample(3)
            r, src = primary(ra, rb)
            t = now()

            if src == -1:
                fault = 4; break
            if r != r_last:
                r_last = r; t_lastchange = t
            elif t - t_lastchange > 500:
                fault = 5; break
            if (al + ar) * 0.5 > ang_lim:
                fault = 6; break
            if t - t0 > 6000:
                fault = 7; break
            if hd > YAW_ABORT_MDEG or hd < -YAW_ABORT_MDEG:
                fault = 14; break
            if r <= R_TRIG_MM:
                triggered = True; break

            if flipped == 0 and (hd > FLIP_MDEG or hd < -FLIP_MDEG):
                hsign = -hsign; flipped = 1
            trim = (hsign * KP_TRIM * hd) // 1000
            if trim > TRIM_MAX: trim = TRIM_MAX
            if trim < -TRIM_MAX: trim = -TRIM_MAX
            if trim < 0:
                m1.run(s1 * VMAX); m2.run(s2 * (VMAX + trim))
            else:
                m1.run(s1 * (VMAX - trim)); m2.run(s2 * VMAX)
            wait(LOOP_MS)

        m1.brake(); m2.brake()          # FIRST. no telemetry before this.
        t_brake = now()
        i_trig = bi
        r_trig_seen = r
        ang_trig = int(odo())
        hd_trig = hdg()

        while now() - t_brake < SETTLE_MS:
            sample(4)
            wait(LOOP_MS)
        i_stop = bi
        emit(t_brake, "brake_cmd", 1)
        emit(now(), "trig_r", r_trig_seen); emit(now(), "trig_ang", ang_trig)
        emit(now(), "trig_hd", hd_trig)
        emit(now(), "trig_ok", 1 if triggered else 0)
        emit(now(), "trig_fault", fault)
        emit(now(), "flipped", flipped)

        # ---------------- S4: post-stop static ------------------------
        i_s4 = bi
        for _n in range(STATIC_N):
            sample(5)
            wait(STATIC_MS)
        i_s4e = bi
        emit(now(), "rest_ra", rd(uf1)); emit(now(), "rest_rb", rd(uf2))
        emit(now(), "rest_ang", int(odo())); emit(now(), "rest_hd", hdg())

        # ---------------- S5: creep to the anchor ---------------------
        cfault = 0
        for frac, r_tgt, ph in ((CREEP_F1, R_CREEP1_MM, 6), (CREEP_F2, R_ANCHOR_MM, 7)):
            drive(int(VMAX * frac))
            t_c = now()
            while True:
                ra, rb, al, ar, hd = sample(ph)
                r, src = primary(ra, rb)
                if src == -1:
                    cfault = 13; break
                if r <= r_tgt:
                    break
                if now() - t_c > 12000:
                    cfault = 8; break
                wait(LOOP_MS)
            m1.brake(); m2.brake()
            wait(400)
            emit(now(), "creep%d_r" % ph, r)
            emit(now(), "creep%d_ang" % ph, int(odo()))
            if cfault != 0:
                break
        emit(now(), "creep_fault", cfault)

        # ---------------- S6: anchor hold -----------------------------
        i_s6 = bi
        for _n in range(STATIC_N):
            sample(8)
            wait(STATIC_MS)
        i_s6e = bi
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
        # ---- on-hub aggregates: scalars are ~50x cheaper than traces --
        if i_appr >= 0 and i_trig > i_appr:
            # loop period over the approach
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
            # ranging refresh: spacing of value changes on the trigger channel
            nch = 0; last = -1; first_t = 0; last_t = 0
            i = i_appr
            while i < i_trig:
                v = brb[i]
                if v < US_SENTINEL and v != last:
                    if nch == 0:
                        first_t = bt[i]
                    last_t = bt[i]; nch += 1; last = v
                i += 1
            emit(now(), "rb_changes", nch)
            if nch > 1:
                emit(now(), "rb_refresh10", ((last_t - first_t) * 10) // (nch - 1))
            # A-vs-B offset and A dropout count during the approach
            noff = 0; soff = 0; ndrop = 0
            i = i_appr
            while i < i_trig:
                if bra[i] >= US_SENTINEL:
                    ndrop += 1
                elif brb[i] < US_SENTINEL:
                    soff += (bra[i] - brb[i]); noff += 1
                i += 1
            emit(now(), "a_drops", ndrop)
            if noff > 0:
                emit(now(), "ab_offset", soff // noff)
            # heading extremes during the approach
            mnh = 999999; mxh = -999999
            i = i_appr
            while i < i_trig:
                v = bhd[i]
                if v < mnh: mnh = v
                if v > mxh: mxh = v
                i += 1
            emit(now(), "appr_hd_mn", mnh); emit(now(), "appr_hd_mx", mxh)
            # settle: first index after brake where the wheels stop moving
            i = i_trig + 1
            st = -1
            while i < i_stop:
                if bal[i] == bal[i-1] and bar[i] == bar[i-1]:
                    st = bt[i]; break
                i += 1
            if st > 0:
                emit(now(), "settle_ms", st - bt[i_trig])
        stats("s1rb", brb, i_s1, i_s1e, US_SENTINEL)
        stats("s4rb", brb, i_s4, i_s4e, US_SENTINEL)
        stats("s6rb", brb, i_s6, i_s6e, US_SENTINEL)
        stats("s6ra", bra, i_s6, i_s6e, US_SENTINEL)
        # ---- thin trace: braking transient, then decimated cruise -----
        if i_trig >= 0:
            i = i_trig - 8
            if i < 0: i = 0
            lim = i_trig + 40
            if lim > i_stop: lim = i_stop
            while i < lim:
                t = bt[i]
                emit(t, "rb", brb[i]); emit(t, "am", (bal[i] + bar[i]) // 2)
                emit(t, "hd", bhd[i])
                i += 1
            i = i_appr
            while i < i_trig - 8:
                t = bt[i]
                emit(t, "rb", brb[i]); emit(t, "am", (bal[i] + bar[i]) // 2)
                emit(t, "hd", bhd[i])
                i += 8
        emit(clock.time(), "lines_used", lines)
        emit(clock.time(), "buf_used", bi)
    except Exception:
        pass
    stdout.write('{"event":"end"}\n')
