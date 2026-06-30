# =============================================================================
# C1 - Calibration & unit-verification run  (the SAFE characterization run)
# Wall-approach rover. Realises Calibration Plan v1.0, Run C1.
#
# SAFE BY DESIGN: brakes at a conservative 400 mm trigger. Expected final gap
# ~200-300 mm => zero contact risk. Requires NO operator input during the run.
#
# What it does, in order:
#   1. Wait for IMU calibration (hub must be still on the start line).
#   2. Discover which port holds which device (try-construct ladder; each
#      device is constructed exactly ONCE, per the Pybricks port-claim rule).
#   3. Identify the two FORWARD ultrasonics (they see the same wall and agree;
#      the rear one is the odd reading out).
#   4. Discover motor command signs so the robot drives FORWARD (front distance
#      must decrease), handling a mirror-mounted motor pair.
#   5. Drive at commanded max speed straight at the wall, logging richly.
#   6. brake() at the 400 mm trigger, log the deceleration tail + rest distance,
#      then hold() to lock position.
#
# Telemetry wire contract: one JSON line per reading
#   {"timestamp_ms": <hub clock ms>, "sensor": "<name>", "value": <scalar>}
# and the run ends with the flush sentinel {"event": "end"}.
# Plain (non-JSON) lines are operator notes -> they surface in stdout_tail.
# =============================================================================

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port, Axis
from pybricks.tools import StopWatch, wait

sw = StopWatch()  # hub clock; t = 0 at program start

def emit(sensor, value):
    # value must be a JSON scalar (int / float)
    print('{"timestamp_ms": %d, "sensor": "%s", "value": %s}' % (sw.time(), sensor, value))

def note(msg):
    print(msg)  # non-telemetry -> stdout_tail

# ---- tunables (C1 is the SAFE run) ------------------------------------------
D_TRIG   = 400     # mm  brake threshold (conservative, big margin to wall)
D_FLOOR  = 120     # mm  hard safety floor
FUSE_TOL = 60      # mm  forward-sensor agreement tolerance
SPEED    = 2000    # deg/s commanded (saturates to physical max)
LIM_SPD  = 2000    # deg/s speed limit raised so nothing caps below max
LIM_ACC  = 8000    # deg/s^2 accel limit (reach top speed quickly)
T_MAX    = 6000    # ms  approach guard
TAIL_MS  = 1500    # ms  post-brake logging window
NUDGE_SP = 300     # deg/s discovery nudge speed
NUDGE_T  = 400     # ms  discovery nudge duration

PORTS = [Port.A, Port.B, Port.C, Port.D, Port.E, Port.F]

def detect(port):
    # try-construct ladder: a failed typed construction does not claim the port
    try:
        return ('motor', Motor(port))
    except Exception:
        pass
    try:
        return ('ultra', UltrasonicSensor(port))
    except Exception:
        pass
    try:
        return ('color', ColorSensor(port))
    except Exception:
        pass
    return ('none', None)

def main():
    hub = PrimeHub()
    m0 = None
    m1 = None
    try:
        # ---- 1. IMU calibration --------------------------------------------
        t_imu = sw.time()
        while not hub.imu.ready():
            if sw.time() - t_imu > 4000:
                note("WARN imu not ready after 4s, continuing")
                break
            wait(50)

        # ---- 2. port discovery (construct each device ONCE) ----------------
        motors = []   # (code, Motor)
        ultras = []   # (code, UltrasonicSensor)
        colors = []   # (code, ColorSensor)
        for i, p in enumerate(PORTS):
            kind, dev = detect(p)
            if kind == 'motor':
                motors.append((i, dev)); emit("disc_motor_port", i)
            elif kind == 'ultra':
                ultras.append((i, dev)); emit("disc_ultra_port", i)
            elif kind == 'color':
                colors.append((i, dev)); emit("disc_color_port", i)
        note("motors=%s ultras=%s colors=%s" % (
            [m[0] for m in motors], [u[0] for u in ultras], [c[0] for c in colors]))

        if len(motors) < 2 or len(ultras) < 2:
            note("FATAL not enough devices: motors=%d ultras=%d" % (len(motors), len(ultras)))
            return

        # ---- 3. identify the two FORWARD ultrasonics -----------------------
        def median_dist(u, n=5):
            vals = []
            for _ in range(n):
                vals.append(u.distance()); wait(20)
            vals.sort()
            return vals[len(vals) // 2]

        meds = [(code, u, median_dist(u)) for (code, u) in ultras]
        for (code, u, mv) in meds:
            emit("disc_ultra_dist", mv)
        best = None
        for a in range(len(meds)):
            for b in range(a + 1, len(meds)):
                ca, ua, va = meds[a]; cb, ub, vb = meds[b]
                if 150 <= va <= 1800 and 150 <= vb <= 1800:
                    diff = abs(va - vb)
                    if best is None or diff < best[0]:
                        best = (diff, (ca, ua), (cb, ub))
        if best is None:
            meds.sort(key=lambda x: x[2])
            fa_code, fa = meds[0][0], meds[0][1]
            fb_code, fb = meds[1][0], meds[1][1]
        else:
            (fa_code, fa), (fb_code, fb) = best[1], best[2]
        emit("fwd_a_port", fa_code); emit("fwd_b_port", fb_code)
        note("forward ultras: a=%d b=%d" % (fa_code, fb_code))

        rear = None
        for (code, u) in ultras:
            if code != fa_code and code != fb_code:
                rear = u; emit("rear_port", code); break
        refl = colors[0][1] if colors else None

        m0 = motors[0][1]; m1 = motors[1][1]
        m0.control.limits(LIM_SPD, LIM_ACC)
        m1.control.limits(LIM_SPD, LIM_ACC)

        def fwd_now():
            a = fa.distance(); b = fb.distance()
            if abs(a - b) <= FUSE_TOL:
                return (a + b) / 2, a, b
            return (a if a < b else b), a, b  # conservative: react to nearer

        # ---- 4. motor sign discovery (front distance must DECREASE) --------
        def nudge(motor_list):
            hub.imu.reset_heading(0)
            d0, _, _ = fwd_now()
            for m in motor_list:
                m.run(NUDGE_SP)
            wait(NUDGE_T)
            for m in motor_list:
                m.stop()
            wait(250)
            d1, _, _ = fwd_now()
            return d1 - d0, hub.imu.heading()

        dd_both, h_both = nudge([m0, m1])
        note("both-nudge dd=%s dh=%s" % (dd_both, h_both))
        if abs(h_both) < 12 and abs(dd_both) > 8:
            s0 = 1 if dd_both < 0 else -1   # '+' moved closer => '+' is forward
            s1 = s0
        else:
            dd0, _ = nudge([m0]); s0 = 1 if dd0 < 0 else -1
            dd1, _ = nudge([m1]); s1 = 1 if dd1 < 0 else -1
        emit("sign_m0", s0); emit("sign_m1", s1)
        note("signs m0=%d m1=%d" % (s0, s1))

        # ---- 5. APPROACH at max speed --------------------------------------
        m0.reset_angle(0); m1.reset_angle(0)
        hub.imu.reset_heading(0)
        emit("phase", 0)

        d_start, _, _ = fwd_now()
        emit("d_start", d_start)
        m0.run(s0 * SPEED)
        m1.run(s1 * SPEED)
        t0 = sw.time()
        aborted = 0
        while True:
            d, a, b = fwd_now()
            emit("dist_fwd", d); emit("dist_fwd_a", a); emit("dist_fwd_b", b)
            emit("ang_m0", m0.angle()); emit("ang_m1", m1.angle())
            emit("heading", hub.imu.heading())
            try:
                emit("accel_x", hub.imu.acceleration(Axis.X))
                emit("accel_y", hub.imu.acceleration(Axis.Y))
            except Exception:
                pass
            if rear is not None:
                try:
                    emit("dist_rear", rear.distance())
                except Exception:
                    pass
            if d <= D_TRIG:
                break
            if d <= D_FLOOR:
                aborted = 1; break
            if sw.time() - t0 > T_MAX:
                aborted = 2; break
            if (d - d_start) > 80 and (sw.time() - t0) > 250:
                aborted = 3; break  # wrong direction (moving away) -> stop
            wait(20)

        # ---- 6. BRAKE + log tail -------------------------------------------
        m0.brake(); m1.brake()
        emit("phase", 1); emit("abort", aborted); emit("t_brake_ms", sw.time())
        t1 = sw.time()
        while sw.time() - t1 < TAIL_MS:
            d, a, b = fwd_now()
            emit("dist_fwd", d); emit("dist_fwd_a", a); emit("dist_fwd_b", b)
            emit("ang_m0", m0.angle()); emit("ang_m1", m1.angle())
            emit("heading", hub.imu.heading())
            try:
                emit("accel_x", hub.imu.acceleration(Axis.X))
                emit("accel_y", hub.imu.acceleration(Axis.Y))
            except Exception:
                pass
            wait(20)

        # ---- lock position, clean final reading ----------------------------
        m0.hold(); m1.hold()
        emit("phase", 2)
        wait(300)
        for _ in range(5):
            d, a, b = fwd_now()
            emit("dist_final", d); emit("dist_final_a", a); emit("dist_final_b", b)
            wait(40)
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
