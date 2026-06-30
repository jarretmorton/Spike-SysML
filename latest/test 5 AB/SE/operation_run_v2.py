# =============================================================================
# OPERATION RUN v2  -  runs 2..5 of the 5 scored runs.
# Identical control + setpoint to operation_run.py. ONE fix from run 1:
#   est_true polls the ACCURATE sensor A FIRST and only falls back to B if A
#   drops out. Near the wall B has no echo and fb.distance() BLOCKS (~0.5 s),
#   which in run 1 stalled the loop/finals and caused the 36 s overrun. Polling
#   A first avoids ever calling fb when A is valid (which it is at close range).
#   Trigger behaviour is unchanged (A and corrected-B agree near the trigger).
#
# Setpoint unchanged: T_TRIG = 125 mm estimated true distance (~78 mm target,
# ~58-78 mm observed band incl. overshoot scatter; all comfortably no-contact).
# =============================================================================

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait

sw = StopWatch()

def emit(s, v):
    print('{"timestamp_ms": %d, "sensor": "%s", "value": %s}' % (sw.time(), s, v))

A_BIAS   = 24
B_BIAS   = 98
S0       = -1
S1       = 1
YAW_DIR  = 1

T_TRIG   = 125
T_FLOOR  = 45
LOST     = 1900

BASE     = 1100
RMAX     = 950
LIM_SPD  = 1200
LIM_ACC  = 5000
KP       = 20.0
CORR_MAX = 500
C_FLOOR  = 220
T_MAX    = 6000
TAIL_MS  = 1500
LOOP_MS  = 6
MAXBUF   = 600
DUMP_MAX = 45
BLIND_MAX = 25     # A rarely drops; a few extra before the blind-stop

def main():
    hub = PrimeHub()
    m0 = None
    m1 = None
    try:
        m0 = Motor(Port.C)
        m1 = Motor(Port.D)
        fa = UltrasonicSensor(Port.A)   # accurate (primary)
        fb = UltrasonicSensor(Port.B)   # reads short (fallback only)
        m0.control.limits(LIM_SPD, LIM_ACC); m1.control.limits(LIM_SPD, LIM_ACC)

        t = sw.time()
        while not hub.imu.ready():
            if sw.time() - t > 4000:
                break
            wait(50)

        def est_true(last):
            araw = fa.distance()                 # poll accurate sensor FIRST
            if araw < LOST:
                return araw - A_BIAS, araw, -1, True   # A valid -> do NOT poll B
            braw = fb.distance()                 # only if A dropped out
            if braw < LOST:
                return braw + B_BIAS, -1, braw, True
            return last, -1, -1, False

        hub.imu.reset_heading(0)
        emit("phase", 0)
        e0, a0r, b0r, _ = est_true(900)
        emit("est_start", e0); emit("a_start", a0r)

        buf = []
        last = e0
        blind = 0
        m0.run(S0 * BASE); m1.run(S1 * BASE)
        t0 = sw.time(); aborted = 0; t_trig = 0
        while True:
            est, araw, braw, ok = est_true(last)
            if ok:
                last = est; blind = 0
            else:
                blind += 1
            h = hub.imu.heading()
            if len(buf) < MAXBUF:
                buf.append((sw.time(), araw, braw, h, est))
            corr = KP * (h if h > 0 else -h)
            if corr > CORR_MAX:
                corr = CORR_MAX
            c0 = BASE; c1 = BASE
            if h > 0.5 or h < -0.5:
                desired = -1 if h > 0 else 1
                if desired == YAW_DIR:
                    c1 = RMAX - corr
                else:
                    c0 = RMAX - corr
                if c0 < C_FLOOR:
                    c0 = C_FLOOR
                if c1 < C_FLOOR:
                    c1 = C_FLOOR
            m0.run(S0 * c0); m1.run(S1 * c1)
            if est <= T_TRIG:
                t_trig = sw.time(); break
            if est <= T_FLOOR:
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
            est, araw, braw, ok = est_true(last)
            if ok:
                last = est
            h = hub.imu.heading()
            if len(buf) < MAXBUF:
                buf.append((sw.time(), araw, braw, h, est))
            wait(LOOP_MS)

        m0.hold(); m1.hold()
        wait(300)

        # ---- FINALS: A is primary and reliable at rest; poll A 8x (fast),
        #      and B just twice for the record (it will be no-echo here) ----
        for _ in range(8):
            araw = fa.distance()
            emit("final_a_raw", araw)
            if araw < LOST:
                emit("final_est_true", araw - A_BIAS)
            wait(40)
        emit("final_b_raw", fb.distance())
        emit("final_b_raw", fb.distance())
        emit("abort", aborted); emit("t_brake_ms", t_brake); emit("t_trig_ms", t_trig)

        hmin = 999.0; hmax = -999.0
        for row in buf:
            hh = row[3]
            if hh < hmin: hmin = hh
            if hh > hmax: hmax = hh
        emit("head_min", hmin); emit("head_max", hmax)

        n = len(buf)
        stride = 1 if n <= DUMP_MAX else (n // DUMP_MAX) + 1
        emit("buf_n", n); emit("buf_stride", stride)
        i = 0
        while i < n:
            t, araw, braw, h, est = buf[i]
            print('{"timestamp_ms": %d, "sensor": "a_raw", "value": %s}' % (t, araw))
            print('{"timestamp_ms": %d, "sensor": "est_true", "value": %s}' % (t, est))
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
