# =====================================================================
# CAL-1 -- characterization program, wall-approach rover
# Segments: S0 discovery | S1 static | S2 nudge/polarity | S3 approach
#           S4 static | S5 creep | S6 anchor hold | dump
# The S3 control loop is the flight loop: the operation program is this
# loop with different constants and the other segments deleted.
# =====================================================================
try:
    from usys import stdout
except ImportError:
    from sys import stdout

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import wait, StopWatch

# ------------------------- constants ---------------------------------
LOOP_MS      = 10
R_TRIG_MM    = 500     # CAL-1 conservative trigger; operation value solved at Gate B
ANGLE_LIM    = 1146    # deg: <=900 mm even at the largest plausible mm/deg (0.785)
DISAGREE_MM  = 150     # forward rangers disagreeing by more than this = fault
STALE_MS     = 500     # fused range frozen this long while driving = fault
US_SENTINEL  = 1900    # readings >= this are "no object", not a distance
NUDGE_DPS    = 200
NUDGE_MS     = 350
SPIN_MDEG    = 15000   # |heading| change proving the motors are opposed
MOVE_MM      = 15      # range change proving translation
CREEP_F1     = 0.20    # fraction of vmax, fast creep
CREEP_F2     = 0.08    # fraction of vmax, slow creep
R_CREEP1_MM  = 250
R_ANCHOR_MM  = 130     # anchor in READING space: safe for any c_us in [-100,+20]
STATIC_N     = 12
STATIC_MS    = 50
NI           = 800
MAX_LINES    = 1600
T_APPROACH_MS = 6000

# ------------------------- telemetry ---------------------------------
lines = 0

def emit(t, name, v):
    global lines
    if lines >= MAX_LINES:
        return
    lines += 1
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%d}\n' % (t, name, v))

bt = [0] * NI; bph = [0] * NI
bra = [0] * NI; brb = [0] * NI; brc = [0] * NI
bal = [0] * NI; bar = [0] * NI; bsl = [0] * NI; bsr = [0] * NI
bhd = [0] * NI; bax = [0] * NI; bay = [0] * NI; baz = [0] * NI
bi = 0

def cap(t, ph, ra, rb, rc, al, ar, sl, sr, hd, ax, ay, az):
    global bi
    if bi >= NI:
        return
    i = bi
    bt[i] = t; bph[i] = ph
    bra[i] = ra; brb[i] = rb; brc[i] = rc
    bal[i] = al; bar[i] = ar; bsl[i] = sl; bsr[i] = sr
    bhd[i] = hd; bax[i] = ax; bay[i] = ay; baz[i] = az
    bi = i + 1

def dump(i0, i1, step, full):
    i = i0
    while i < i1 and i < bi:
        t = bt[i]
        emit(t, "ra", bra[i]); emit(t, "rb", brb[i])
        emit(t, "al", bal[i]); emit(t, "ar", bar[i])
        emit(t, "hd", bhd[i]); emit(t, "ph", bph[i])
        if full:
            emit(t, "rc", brc[i])
            emit(t, "sl", bsl[i]); emit(t, "sr", bsr[i])
            emit(t, "ax", bax[i]); emit(t, "ay", bay[i]); emit(t, "az", baz[i])
        i += step

# ------------------------- state -------------------------------------
hub = PrimeHub()
clock = StopWatch()
m1 = None; m2 = None
uf1 = None; uf2 = None; urear = None
s1 = 1; s2 = 1                 # motor sign so that +v drives toward the wall
i_trig = -1; i_stop = -1
fault = 0

def now():
    return clock.time()

def rd(u):
    if u is None:
        return US_SENTINEL
    try:
        v = u.distance()
    except Exception:
        return US_SENTINEL
    if v is None or v < 0:
        return US_SENTINEL
    return int(v)

def imu3():
    try:
        a = hub.imu.acceleration()
        return (int(a[0]), int(a[1]), int(a[2]))
    except Exception:
        return (0, 0, 0)

def hdg():
    try:
        return int(hub.imu.heading() * 1000.0)
    except Exception:
        return 0

def stop_both():
    try:
        m1.brake(); m2.brake()
    except Exception:
        pass

def drive(v):
    m1.run(s1 * v); m2.run(s2 * v)

def sample(ph, ax, ay, az):
    ra = rd(uf1); rb = rd(uf2); rc = rd(urear)
    try:
        al = int(m1.angle()); ar = int(m2.angle())
        sl = int(m1.speed()); sr = int(m2.speed())
    except Exception:
        al = 0; ar = 0; sl = 0; sr = 0
    cap(now(), ph, ra, rb, rc, s1 * al, s2 * ar, s1 * sl, s2 * sr,
        hdg(), ax, ay, az)
    return ra, rb, s1 * al, s2 * ar

def fuse(ra, rb):
    a_ok = ra < US_SENTINEL
    b_ok = rb < US_SENTINEL
    if a_ok and b_ok:
        return ra if ra < rb else rb, 1
    if a_ok:
        return ra, 0
    if b_ok:
        return rb, 0
    return US_SENTINEL, -1

try:
    # ---------------- S0: port discovery -----------------------------
    motors = []; ultras = []
    for letter, port in (("A", Port.A), ("B", Port.B), ("C", Port.C),
                         ("D", Port.D), ("E", Port.E), ("F", Port.F)):
        code = 0
        try:
            motors.append(Motor(port)); code = 1
        except Exception:
            try:
                ultras.append(UltrasonicSensor(port)); code = 2
            except Exception:
                code = 0
        emit(now(), "port_" + letter, code)
    emit(now(), "n_motors", len(motors))
    emit(now(), "n_ultra", len(ultras))

    if len(motors) < 2 or len(ultras) < 2:
        fault = 1
        emit(now(), "fault", fault)
    else:
        m1 = motors[0]; m2 = motors[1]
        try:
            vmax = int(min(m1.control.limits()[0], m2.control.limits()[0]))
        except Exception:
            vmax = 800
        emit(now(), "vmax_dps", vmax)
        m1.reset_angle(0); m2.reset_angle(0)
        try:
            hub.imu.reset_heading(0)
        except Exception:
            pass

        # provisional ranger assignment; corrected by S2
        uf1 = ultras[0]; uf2 = ultras[1]
        urear = ultras[2] if len(ultras) > 2 else None

        # ---------------- S1: static pre-roll -------------------------
        ax, ay, az = imu3()
        for _n in range(STATIC_N):
            sample(1, ax, ay, az)
            wait(STATIC_MS)
        base = [rd(u) for u in ultras]
        for j in range(len(ultras)):
            emit(now(), "static_r%d" % j, base[j])

        # ---------------- S2: nudge / polarity ------------------------
        h0 = hdg()
        drive(NUDGE_DPS)
        t_end = now() + NUDGE_MS
        while now() < t_end:
            sample(2, ax, ay, az)
            wait(LOOP_MS)
        stop_both(); wait(250)
        d_head = hdg() - h0
        emit(now(), "nudge1_dhead_mdeg", d_head)

        if d_head > SPIN_MDEG or d_head < -SPIN_MDEG:
            # motors are opposed: flip one and repeat
            s2 = -1
            emit(now(), "motors_opposed", 1)
            h0 = hdg()
            drive(NUDGE_DPS)
            t_end = now() + NUDGE_MS
            while now() < t_end:
                sample(2, ax, ay, az)
                wait(LOOP_MS)
            stop_both(); wait(250)
            emit(now(), "nudge2_dhead_mdeg", hdg() - h0)
        else:
            emit(now(), "motors_opposed", 0)

        after = [rd(u) for u in ultras]
        delta = [after[j] - base[j] for j in range(len(ultras))]
        for j in range(len(delta)):
            emit(now(), "nudge_dr%d" % j, delta[j])

        # rangers that got CLOSER lead the direction we just drove
        closer = [j for j in range(len(delta)) if delta[j] < -MOVE_MM]
        farther = [j for j in range(len(delta)) if delta[j] > MOVE_MM]
        if len(closer) >= 2:
            fwd = 1; front = closer[:2]
            rear = [j for j in range(len(ultras)) if j not in front]
        elif len(farther) >= 2:
            fwd = -1; front = farther[:2]
            rear = [j for j in range(len(ultras)) if j not in front]
        else:
            fwd = 0; front = [0, 1]
            rear = [j for j in range(len(ultras)) if j not in front]
            fault = 2
        s1 = s1 * (fwd if fwd != 0 else 1)
        s2 = s2 * (fwd if fwd != 0 else 1)
        uf1 = ultras[front[0]]; uf2 = ultras[front[1]]
        urear = ultras[rear[0]] if len(rear) > 0 else None
        emit(now(), "fwd_sign", fwd)
        emit(now(), "front_idx0", front[0]); emit(now(), "front_idx1", front[1])
        emit(now(), "sign_m1", s1); emit(now(), "sign_m2", s2)
        emit(now(), "fault", fault)

        # return to the start line by odometry
        if fault == 0:
            a_now = (s1 * m1.angle() + s2 * m2.angle()) * 0.5
            # the sign convention may have just been inverted by fwd, so the
            # return direction is taken from the odometry, not assumed
            drive(-NUDGE_DPS if a_now > 0 else NUDGE_DPS)
            t_end = now() + 2000
            while now() < t_end:
                sample(2, ax, ay, az)
                a_cur = (s1 * m1.angle() + s2 * m2.angle()) * 0.5
                if (a_now > 0 and a_cur <= 0) or (a_now <= 0 and a_cur >= 0):
                    break
                wait(LOOP_MS)
            stop_both(); wait(300)
            emit(now(), "return_angle_deg", int((s1 * m1.angle() + s2 * m2.angle()) * 0.5))
            m1.reset_angle(0); m2.reset_angle(0)

        # ---------------- S3: full-speed approach (FLIGHT LOOP) -------
        if fault == 0:
            i_start = bi
            t0 = now()
            t_lastchange = t0
            r_last = -1
            triggered = False
            k = 0
            drive(vmax)
            while True:
                if k % 4 == 0:
                    ax, ay, az = imu3()
                ra, rb, al, ar = sample(3, ax, ay, az)
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
                if (al + ar) * 0.5 > ANGLE_LIM:
                    fault = 6; break
                if t - t0 > T_APPROACH_MS:
                    fault = 7; break
                if r <= R_TRIG_MM:
                    triggered = True
                    break
                k += 1
                wait(LOOP_MS)

            i_trig = bi
            emit(now(), "trig_range_mm", r)
            emit(now(), "trig_triggered", 1 if triggered else 0)
            emit(now(), "trig_fault", fault)
            m1.brake(); m2.brake()          # adjacent: minimises brake skew
            t_brake = now()
            emit(t_brake, "brake_cmd", 1)

            while now() - t_brake < 900:
                sample(4, ax, ay, az)
                wait(LOOP_MS)
            i_stop = bi

            # ---------------- S4: post-stop static --------------------
            for _n in range(STATIC_N):
                sample(5, ax, ay, az)
                wait(STATIC_MS)
            emit(now(), "rest_ra", rd(uf1)); emit(now(), "rest_rb", rd(uf2))
            emit(now(), "rest_angle_l", int(s1 * m1.angle()))
            emit(now(), "rest_angle_r", int(s2 * m2.angle()))
            emit(now(), "rest_head_mdeg", hdg())

            # ---------------- S5: two-stage creep to the anchor -------
            for frac, r_target, ph in ((CREEP_F1, R_CREEP1_MM, 6),
                                       (CREEP_F2, R_ANCHOR_MM, 7)):
                v = int(vmax * frac)
                if v < 40:
                    v = 40
                drive(v)
                t_c = now()
                while True:
                    ra, rb, al, ar = sample(ph, ax, ay, az)
                    r, both = fuse(ra, rb)
                    if r <= r_target or both == -1:
                        break
                    if now() - t_c > 8000:
                        fault = 8
                        break
                    wait(LOOP_MS)
                m1.brake(); m2.brake()
                wait(400)
                emit(now(), "creep_stop_ph%d" % ph, r)

            # ---------------- S6: anchor hold -------------------------
            for _n in range(STATIC_N):
                sample(8, ax, ay, az)
                wait(STATIC_MS)
            emit(now(), "anchor_ra", rd(uf1)); emit(now(), "anchor_rb", rd(uf2))
            emit(now(), "anchor_rc", rd(urear))
            emit(now(), "anchor_angle_l", int(s1 * m1.angle()))
            emit(now(), "anchor_angle_r", int(s2 * m2.angle()))
            emit(now(), "anchor_head_mdeg", hdg())
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
    # priority-ordered dump: the critical braking window first, so that a
    # truncated transfer still carries the measurement the run exists for
    try:
        if i_trig >= 0:
            lo = i_trig - 40
            if lo < 0:
                lo = 0
            hi = i_stop if i_stop > 0 else bi
            dump(lo, hi, 1, True)          # full rate, all channels
            dump(0, lo, 8, False)          # cruise, decimated
            dump(hi, bi, 4, False)         # settle + creep + anchor
        else:
            dump(0, bi, 4, True)
        emit(clock.time(), "lines_used", lines)
    except Exception:
        pass
    stdout.write('{"event":"end"}\n')
