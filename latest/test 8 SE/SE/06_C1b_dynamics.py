"""
C1b — CHARACTERIZATION RUN 2 (clean dynamics). Map is hard-coded from C1's
successful discovery, so there is NO creep and NO rotation. The rover drives
straight at max speed from a squared start, brakes on a conservative trigger
(500 mm, valid readings only), then dwells at rest. Binds v_max, a_brake, t_lat,
D_stop, Δt_s, σ_S, straightness. Telemetry is buffered on the hot path and dumped
in batched writes afterward (fixes C1's slow-dump timeout).

Discovered map (C1): motorL=Port.C (CCW=fwd), motorR=Port.D (CW=fwd),
forward ultrasonics = Port.A, Port.B. run() forward = both +MAX_CMD.
"""
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port, Direction
from pybricks.tools import StopWatch, wait
from usys import stdout

MAX_CMD = 1200
TRIG = 500
FLOOR = 120
CAP_MS = 3500
LOOP_MS = 10
POST_BRAKE_MS = 900
REST_MS = 500

hub = PrimeHub()
mL = None
mR = None

try:
    mL = Motor(Port.C, Direction.COUNTERCLOCKWISE)
    mR = Motor(Port.D, Direction.CLOCKWISE)
    uA = UltrasonicSensor(Port.A)
    uB = UltrasonicSensor(Port.B)
    try:
        mL.control.limits(acceleration=20000)
        mR.control.limits(acceleration=20000)
    except Exception:
        pass

    buf = []
    sw = StopWatch()
    mL.run(MAX_CMD)
    mR.run(MAX_CMD)
    triggered = False
    t_trig = -1
    brake_t = -1
    while True:
        t = sw.time()
        dA = uA.distance()
        dB = uB.distance()
        ac = hub.imu.acceleration()
        hd = hub.imu.heading()
        buf.append((t, dA, dB, ac[0], ac[1], hd))
        vA = dA if dA < 1900 else 99999
        vB = dB if dB < 1900 else 99999
        dmin = vA if vA < vB else vB
        if (not triggered) and dmin <= TRIG:
            triggered = True
            t_trig = t
            brake_t = t
            mL.brake()
            mR.brake()
        elif (not triggered) and dmin <= FLOOR:
            triggered = True
            t_trig = t
            brake_t = t
            mL.brake()
            mR.brake()
        if triggered and (t - brake_t) >= POST_BRAKE_MS:
            break
        if t >= CAP_MS:
            mL.brake()
            mR.brake()
            break
        wait(LOOP_MS)

    mL.brake()
    mR.brake()

    rt0 = sw.time()
    while sw.time() - rt0 < REST_MS:
        t = sw.time()
        dA = uA.distance()
        dB = uB.distance()
        ac = hub.imu.acceleration()
        hd = hub.imu.heading()
        buf.append((t, dA, dB, ac[0], ac[1], hd))
        wait(15)

    lines = []
    lines.append('{"timestamp_ms":0,"sensor":"trigger_ms","value":%d}\n' % t_trig)
    lines.append('{"timestamp_ms":0,"sensor":"max_cmd","value":%d}\n' % MAX_CMD)
    n = len(buf)
    i = 0
    while i < n:
        r = buf[i]
        tt = int(r[0])
        if (i % 2) == 0:
            lines.append('{"timestamp_ms":%d,"sensor":"dist_A","value":%d}\n' % (tt, r[1]))
            lines.append('{"timestamp_ms":%d,"sensor":"dist_B","value":%d}\n' % (tt, r[2]))
        if (i % 6) == 0:
            lines.append('{"timestamp_ms":%d,"sensor":"imu_ax","value":%.1f}\n' % (tt, r[3]))
            lines.append('{"timestamp_ms":%d,"sensor":"imu_ay","value":%.1f}\n' % (tt, r[4]))
        if (i % 8) == 0:
            lines.append('{"timestamp_ms":%d,"sensor":"heading","value":%.2f}\n' % (tt, r[5]))
        i += 1
    j = 0
    m = len(lines)
    while j < m:
        stdout.write("".join(lines[j:j + 40]))
        j += 40

except Exception:
    try:
        stdout.write('{"timestamp_ms":0,"sensor":"exception","value":1}\n')
    except Exception:
        pass
finally:
    try:
        if mL is not None:
            mL.brake()
        if mR is not None:
            mR.brake()
    except Exception:
        pass
    stdout.write('{"event":"end"}\n')
