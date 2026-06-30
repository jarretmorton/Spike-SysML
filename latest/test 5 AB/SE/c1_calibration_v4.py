# =============================================================================
# C1 (v4) - Calibration & unit-verification run  (safe characterization)
# Supersedes v3. Realises Calibration Plan v1.1.
#
# Fixes the two issues v3 exposed:
#   * DROPOUT-ROBUST FUSION: ultrasonic readings >= LOST are "no echo". Use the
#     valid sensor; if BOTH drop, HOLD the last valid distance (a crosstalk blip
#     can no longer spike the fused value). The brittle wrong-direction guard is
#     removed (signs proven over 3 runs); replaced by a "blind too long -> stop".
#   * STEERING WITH AUTHORITY: motors saturate ~986 deg/s, so trimming a wheel
#     from a 2000 command does nothing. Trim now slows the leading wheel BELOW
#     the real max (RMAX) so it actually steers. Non-leading wheel stays at max.
#
# SAFE: 400 mm trigger; expected final gap ~300 mm; floor + timeout + blind guards.
# Wire contract: JSON line per reading + final {"event": "end"} sentinel.
# =============================================================================

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait

sw = StopWatch()

def emit(s, v):
    print('{"timestamp_ms": %d, "sensor": "%s", "value": %s}' % (sw.time(), s, v))

def note(m):
    print(m)

D_TRIG   = 400
D_FLOOR  = 120
FUSE_TOL = 60
LOST     = 1900     # readings >= this are "no echo"
BASE     = 1100     # command (saturates motors -> true max speed)
RMAX     = 950      # ~ measured real max (986); steer by slowing leading wheel below this
LIM_SPD  = 1200
LIM_ACC  = 5000
KP       = 20.0     # steering gain (deg/s per deg)
CORR_MAX = 500      # max slow-down applied to leading wheel
C_FLOOR  = 220      # never command a wheel below this (anti-stall)
T_MAX    = 6000
TAIL_MS  = 1500
NSP      = 300
NT       = 300
LOOP_MS  = 6
MAXBUF   = 600
DUMP_MAX = 55
BLIND_MAX = 18      # consecutive both-lost samples -> safety stop

PORTS = [Port.A, Port.B, Port.C, Port.D, Port.E, Port.F]

def detect(p):
    try:
        return ('motor', Motor(p))
    except Exception:
        pass
    try:
        return ('ultra', UltrasonicSensor(p))
    except Exception:
        pass
    try:
        return ('color', ColorSensor(p))
    except Exception:
        pass
    return ('none', None)

def main():
    hub = PrimeHub()
    m0 = None
    m1 = None
    try:
        t = sw.time()
        while not hub.imu.ready():
            if sw.time() - t > 4000:
                note("WARN imu not ready"); break
            wait(50)

        motors = []; ultras = []; colors = []
        for i, p in enumerate(PORTS):
            k, dev = detect(p)
            if k == 'motor':
                motors.append((i, dev)); emit("disc_motor_port", i)
            elif k == 'ultra':
                ultras.append((i, dev)); emit("disc_ultra_port", i)
            elif k == 'color':
                colors.append((i, dev)); emit("disc_color_port", i)
        note("motors=%s ultras=%s colors=%s" % (
            [m[0] for m in motors], [u[0] for u in ultras], [c[0] for c in colors]))
        if len(motors) < 2 or len(ultras) < 2:
            note("FATAL devices motors=%d ultras=%d" % (len(motors), len(ultras))); return

        def med(u, n=5):
            v = []
            for _ in range(n):
                v.append(u.distance()); wait(20)
            v.sort(); return v[len(v) // 2]
        meds = [(c, u, med(u)) for (c, u) in ultras]
        for (c, u, mv) in meds:
            emit("disc_ultra_dist", mv)
        best = None
        for a in range(len(meds)):
            for b in range(a + 1, len(meds)):
                ca, ua, va = meds[a]; cb, ub, vb = meds[b]
                if 150 <= va <= 1800 and 150 <= vb <= 1800:
                    df = abs(va - vb)
                    if best is None or df < best[0]:
                        best = (df, (ca, ua), (cb, ub))
        if best is None:
            meds.sort(key=lambda x: x[2])
            fa_c, fa = meds[0][0], meds[0][1]; fb_c, fb = meds[1][0], meds[1][1]
        else:
            (fa_c, fa), (fb_c, fb) = best[1], best[2]
        emit("fwd_a_port", fa_c); emit("fwd_b_port", fb_c)
        note("forward a=%d b=%d" % (fa_c, fb_c))
        rear = None
        for (c, u) in ultras:
            if c != fa_c and c != fb_c:
                rear = u; emit("rear_port", c); break
        refl = colors[0][1] if colors else None

        m0 = motors[0][1]; m1 = motors[1][1]
        m0.control.limits(LIM_SPD, LIM_ACC); m1.control.limits(LIM_SPD, LIM_ACC)

        def fuse(last):
            a = fa.distance(); b = fb.distance()
            va = a < LOST; vb = b < LOST
            if va and vb:
                d = (a + b) / 2 if abs(a - b) <= FUSE_TOL else (a if a < b else b)
                return d, a, b, True
            if va:
                return a, a, b, True
            if vb:
                return b, a, b, True
            return last, a, b, False

        hub.imu.reset_heading(0)

        def probe(c0, c1, sp, t):
            d0, _, _, _ = fuse(900); h0 = hub.imu.heading()
            m0.run(c0 * sp); m1.run(c1 * sp); wait(t); m0.stop(); m1.stop(); wait(250)
            d1, _, _, _ = fuse(d0)
            return d1 - d0, hub.imu.heading() - h0

        dd_s, dh_s = probe(1, 1, NSP, NT)
        note("same-sign dd=%s dh=%s" % (dd_s, dh_s))
        SPIN_DIR = 1 if dh_s > 0 else -1
        mirror = abs(dh_s) > 20

        def face_wall(tol=4, sp=170, tmax=4000):
            t0 = sw.time()
            while sw.time() - t0 < tmax:
                h = hub.imu.heading()
                if abs(h) <= tol:
                    break
                cmd = (-1 if h > 0 else 1) * sp * SPIN_DIR
                m0.run(cmd); m1.run(cmd); wait(25)
            m0.stop(); m1.stop(); wait(150)

        if mirror:
            face_wall()
            dd_o, dh_o = probe(1, -1, NSP, NT)
            note("opp dd=%s dh=%s" % (dd_o, dh_o))
            if abs(dd_o) < 15:
                dd_o, dh_o = probe(1, -1, NSP + 250, NT)
                note("opp2 dd=%s dh=%s" % (dd_o, dh_o))
            if dd_o < 0:
                s0, s1 = 1, -1
            else:
                s0, s1 = -1, 1
            face_wall()
        else:
            if dd_s < 0:
                s0, s1 = 1, 1
            else:
                s0, s1 = -1, -1
        emit("sign_m0", s0); emit("sign_m1", s1)
        note("signs m0=%d m1=%d" % (s0, s1))

        h0 = hub.imu.heading()
        m0.run(s0 * 400); m1.run(s1 * 200); wait(300); m0.stop(); m1.stop(); wait(200)
        dh_y = hub.imu.heading() - h0
        YAW_DIR = 1 if dh_y > 0 else -1
        emit("yaw_dir", YAW_DIR); note("yaw_dir=%d dh_y=%s" % (YAW_DIR, dh_y))
        if mirror:
            face_wall()

        # ---- timed approach at max speed, steering-trimmed; buffer in RAM ----
        m0.reset_angle(0); m1.reset_angle(0); hub.imu.reset_heading(0)
        emit("phase", 0)
        d_start, _, _, _ = fuse(900); emit("d_start", d_start)

        buf = []
        last = d_start
        blind = 0
        m0.run(s0 * BASE); m1.run(s1 * BASE)
        t0 = sw.time(); aborted = 0; t_trig = 0
        while True:
            d, a, b, ok = fuse(last)
            if ok:
                last = d; blind = 0
            else:
                blind += 1
            h = hub.imu.heading()
            if len(buf) < MAXBUF:
                buf.append((sw.time(), a, b, m0.angle(), m1.angle(), h))
            # steering: slow the leading wheel BELOW real max
            corr = KP * (h if h > 0 else -h)
            if corr > CORR_MAX:
                corr = CORR_MAX
            c0 = BASE; c1 = BASE
            if h > 0.5 or h < -0.5:
                desired = -1 if h > 0 else 1          # yaw sign that reduces |h|
                if desired == YAW_DIR:
                    c1 = RMAX - corr                  # slow m1 -> m0 relatively faster
                else:
                    c0 = RMAX - corr                  # slow m0
                if c0 < C_FLOOR:
                    c0 = C_FLOOR
                if c1 < C_FLOOR:
                    c1 = C_FLOOR
            m0.run(s0 * c0); m1.run(s1 * c1)
            if d <= D_TRIG:
                t_trig = sw.time(); break
            if d <= D_FLOOR:
                aborted = 1; t_trig = sw.time(); break
            if sw.time() - t0 > T_MAX:
                aborted = 2; break
            if blind > BLIND_MAX:
                aborted = 4; break
            wait(LOOP_MS)

        m0.brake(); m1.brake()
        t_brake = sw.time()

        t1 = sw.time()
        while sw.time() - t1 < TAIL_MS:
            d, a, b, ok = fuse(last)
            if ok:
                last = d
            h = hub.imu.heading()
            if len(buf) < MAXBUF:
                buf.append((sw.time(), a, b, m0.angle(), m1.angle(), h))
            wait(LOOP_MS)

        m0.hold(); m1.hold()
        wait(300)

        # ---- FINALS FIRST (critical for O) ----
        for _ in range(6):
            a = fa.distance(); b = fb.distance()
            emit("dist_final_a", a); emit("dist_final_b", b); wait(40)
        emit("abort", aborted); emit("t_brake_ms", t_brake); emit("t_trig_ms", t_trig)
        if refl is not None:
            try:
                emit("refl", refl.reflection())
            except Exception:
                pass

        # ---- DOWNSAMPLED curve dump (bulk, last) ----
        n = len(buf)
        stride = 1 if n <= DUMP_MAX else (n // DUMP_MAX) + 1
        emit("buf_n", n); emit("buf_stride", stride)
        i = 0
        while i < n:
            t, a, b, a0, a1, h = buf[i]
            print('{"timestamp_ms": %d, "sensor": "dist_fwd_a", "value": %s}' % (t, a))
            print('{"timestamp_ms": %d, "sensor": "dist_fwd_b", "value": %s}' % (t, b))
            print('{"timestamp_ms": %d, "sensor": "ang_m0", "value": %s}' % (t, a0))
            print('{"timestamp_ms": %d, "sensor": "ang_m1", "value": %s}' % (t, a1))
            print('{"timestamp_ms": %d, "sensor": "heading", "value": %s}' % (t, h))
            i += stride
        emit("phase", 2)

    finally:
        try:
            if m0:
                m0.stop()
            if m1:
                m1.stop()
        except Exception:
            pass
        print('{"event": "end"}')

main()
