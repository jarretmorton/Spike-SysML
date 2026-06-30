# =============================================================================
# C1' - Calibration & unit-verification run, CORRECTED  (safe characterization)
# Supersedes c1_calibration.py. Realises Calibration Plan v1.1.
#
# Fixes vs C1:
#   * Motor-sign discovery is rotation-proof: mirror-vs-aligned is decided from
#     IMU HEADING (not distance); forward direction is read from distance only
#     while the rover is squared and actually TRANSLATING.
#   * Straight max-speed driving via a derived gyro heading-trim (slows the
#     leading wheel only; commanded speed stays at maximum). Trim sign/gain are
#     measured by a yaw-response probe (CMP-3.2, derived).
#   * Dense logging: the hot loop buffers samples in RAM and dumps them AFTER
#     the rover is stopped (no I/O while moving).
#
# SAFE: brake trigger at a conservative 400 mm; expected final gap ~200-300 mm.
# Wire contract: JSON line per reading + final {"event": "end"} sentinel.
# =============================================================================

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port, Axis
from pybricks.tools import StopWatch, wait

sw = StopWatch()

def emit(s, v):
    print('{"timestamp_ms": %d, "sensor": "%s", "value": %s}' % (sw.time(), s, v))

def note(m):
    print(m)

# ---- tunables ----
D_TRIG   = 400      # mm brake threshold (conservative)
D_FLOOR  = 120      # mm hard safety floor
FUSE_TOL = 60       # mm forward-sensor agreement tolerance
SPEED    = 2000     # deg/s commanded (saturates to physical max)
LIM_SPD  = 2000
LIM_ACC  = 8000
T_MAX    = 6000     # ms approach guard
TAIL_MS  = 1500     # ms post-brake logging
NSP      = 300      # deg/s discovery nudge speed
NT       = 300      # ms discovery nudge duration
KP       = 10.0     # gyro trim gain (deg/s per deg)
TRIM_MAX = 500      # deg/s max trim (bounded authority)
LOOP_MS  = 8        # hot-loop pacing
MAXBUF   = 1200

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
        # ---- IMU calibration ----
        t = sw.time()
        while not hub.imu.ready():
            if sw.time() - t > 4000:
                note("WARN imu not ready"); break
            wait(50)

        # ---- device discovery ----
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

        # ---- forward-ultrasonic identification (squared) ----
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

        def fwd_now():
            a = fa.distance(); b = fb.distance()
            if abs(a - b) <= FUSE_TOL:
                return (a + b) / 2, a, b
            return (a if a < b else b), a, b

        hub.imu.reset_heading(0)  # 0 == squared facing wall (operator set)

        def probe(c0, c1, sp, t):
            d0, _, _ = fwd_now(); h0 = hub.imu.heading()
            m0.run(c0 * sp); m1.run(c1 * sp); wait(t); m0.stop(); m1.stop(); wait(250)
            return fwd_now()[0] - d0, hub.imu.heading() - h0

        # ---- mirror-vs-aligned by HEADING ----
        dd_s, dh_s = probe(1, 1, NSP, NT)
        note("same-sign dd=%s dh=%s" % (dd_s, dh_s))
        SPIN_DIR = 1 if dh_s > 0 else -1
        mirror = abs(dh_s) > 20

        def face_wall(tol=4, sp=170, tmax=4000):
            # only valid on a mirror base (same-sign command rotates)
            t0 = sw.time()
            while sw.time() - t0 < tmax:
                h = hub.imu.heading()
                if abs(h) <= tol:
                    break
                cmd = (-1 if h > 0 else 1) * sp * SPIN_DIR
                m0.run(cmd); m1.run(cmd); wait(25)
            m0.stop(); m1.stop(); wait(150)

        # ---- forward direction from a TRANSLATING pulse ----
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

        # ---- yaw-response probe: m0 faster than m1 -> which way does heading go ----
        h0 = hub.imu.heading()
        m0.run(s0 * 400); m1.run(s1 * 200); wait(300); m0.stop(); m1.stop(); wait(200)
        dh_y = hub.imu.heading() - h0
        YAW_DIR = 1 if dh_y > 0 else -1
        emit("yaw_dir", YAW_DIR); note("yaw_dir=%d dh_y=%s" % (YAW_DIR, dh_y))
        if mirror:
            face_wall()

        # ---- timed approach at max speed, gyro-trimmed ----
        m0.reset_angle(0); m1.reset_angle(0); hub.imu.reset_heading(0)
        emit("phase", 0)
        d_start, _, _ = fwd_now(); emit("d_start", d_start)

        buf = []
        m0.run(s0 * SPEED); m1.run(s1 * SPEED)
        t0 = sw.time(); aborted = 0
        while True:
            a = fa.distance(); b = fb.distance()
            d = (a + b) / 2 if abs(a - b) <= FUSE_TOL else (a if a < b else b)
            h = hub.imu.heading()
            try:
                ax = hub.imu.acceleration(Axis.X); ay = hub.imu.acceleration(Axis.Y)
            except Exception:
                ax = 0; ay = 0
            if len(buf) < MAXBUF:
                buf.append((sw.time(), a, b, m0.angle(), m1.angle(), h, ax, ay))
            # gyro trim: slow the leading wheel only
            D = -KP * h * YAW_DIR
            mag = abs(D)
            if mag > TRIM_MAX:
                mag = TRIM_MAX
            u0 = SPEED; u1 = SPEED
            if D > 0:
                u1 = SPEED - mag
            elif D < 0:
                u0 = SPEED - mag
            m0.run(s0 * u0); m1.run(s1 * u1)
            if d <= D_TRIG:
                break
            if d <= D_FLOOR:
                aborted = 1; break
            if sw.time() - t0 > T_MAX:
                aborted = 2; break
            if (d - d_start) > 80 and (sw.time() - t0) > 250:
                aborted = 3; break
            wait(LOOP_MS)

        m0.brake(); m1.brake()
        t_brake = sw.time()

        t1 = sw.time()
        while sw.time() - t1 < TAIL_MS:
            a = fa.distance(); b = fb.distance(); h = hub.imu.heading()
            try:
                ax = hub.imu.acceleration(Axis.X); ay = hub.imu.acceleration(Axis.Y)
            except Exception:
                ax = 0; ay = 0
            if len(buf) < MAXBUF:
                buf.append((sw.time(), a, b, m0.angle(), m1.angle(), h, ax, ay))
            wait(LOOP_MS)

        m0.hold(); m1.hold()
        wait(300)
        fa_f = []; fb_f = []
        for _ in range(6):
            fa_f.append(fa.distance()); fb_f.append(fb.distance()); wait(40)

        # ---- dump buffer off the hot path ----
        emit("abort", aborted); emit("t_brake_ms", t_brake)
        for row in buf:
            t, a, b, a0, a1, h, ax, ay = row
            print('{"timestamp_ms": %d, "sensor": "dist_fwd_a", "value": %s}' % (t, a))
            print('{"timestamp_ms": %d, "sensor": "dist_fwd_b", "value": %s}' % (t, b))
            print('{"timestamp_ms": %d, "sensor": "ang_m0", "value": %s}' % (t, a0))
            print('{"timestamp_ms": %d, "sensor": "ang_m1", "value": %s}' % (t, a1))
            print('{"timestamp_ms": %d, "sensor": "heading", "value": %s}' % (t, h))
            print('{"timestamp_ms": %d, "sensor": "accel_x", "value": %s}' % (t, ax))
            print('{"timestamp_ms": %d, "sensor": "accel_y", "value": %s}' % (t, ay))
        for v in fa_f:
            emit("dist_final_a", v)
        for v in fb_f:
            emit("dist_final_b", v)
        emit("phase", 2)
        if refl is not None:
            try:
                emit("refl", refl.reflection())
            except Exception:
                pass

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
