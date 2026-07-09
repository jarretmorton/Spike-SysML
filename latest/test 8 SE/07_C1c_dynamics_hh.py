"""
C1c — CHARACTERIZATION RUN 3 (clean dynamics + straight-line control).
Adds closed-loop HEADING HOLD to fix the ~14 deg veer seen in C1b: an in-run
"kick" learns the sign of (differential -> heading), then a P controller trims
the inside wheel to hold heading ~0 while the outside wheel stays pinned at max
(MAX_CMD above the physical clamp). Conservative 500 mm trigger (valid readings
only), emergency floor, abort if |heading|>25 deg. Per-line telemetry dump with
the REST-dwell rows emitted FIRST so the stop/gap samples survive any tail
truncation. 30 s timeout.

Map (from C1): motorL=Port.C (CCW=fwd), motorR=Port.D (CW=fwd),
forward ultrasonics = Port.A, Port.B.
"""
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port, Direction
from pybricks.tools import StopWatch, wait
from usys import stdout

MAX_CMD = 1100       # above physical clamp -> both wheels at max when straight
KICK = 200
KICK_MS = 150
KP = 25
CORR_CAP = 250
ABORT_DEG = 25
TRIG = 500
FLOOR = 120
CAP_MS = 3500
LOOP_MS = 10
POST_BRAKE_MS = 800
REST_MS = 400

hub = PrimeHub()
mL = None
mR = None


def emit(t, name, val):
    if isinstance(val, float):
        vs = "%.2f" % val
    else:
        vs = str(val)
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%s}\n' % (int(t), name, vs))


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

    sw = StopWatch()
    # ---- sign-learning kick: (mL+, mR-) and see which way heading moves ----
    mL.run(MAX_CMD + KICK)
    mR.run(MAX_CMD - KICK)
    h0 = hub.imu.heading()
    wait(KICK_MS)
    h1 = hub.imu.heading()
    gsign = 1 if (h1 - h0) >= 0 else -1

    buf = []
    triggered = False
    t_trig = -1
    brake_t = -1
    aborted = 0
    while True:
        t = sw.time()
        dA = uA.distance()
        dB = uB.distance()
        h = hub.imu.heading()
        ac = hub.imu.acceleration()
        buf.append((t, dA, dB, h, ac[0], ac[1]))
        corr = -gsign * KP * h
        if corr > CORR_CAP:
            corr = CORR_CAP
        if corr < -CORR_CAP:
            corr = -CORR_CAP
        if not triggered:
            mL.run(MAX_CMD + corr)
            mR.run(MAX_CMD - corr)
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
        elif (not triggered) and (h > ABORT_DEG or h < -ABORT_DEG):
            aborted = 1
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

    n_drive = len(buf)
    rt0 = sw.time()
    while sw.time() - rt0 < REST_MS:
        t = sw.time()
        dA = uA.distance()
        dB = uB.distance()
        h = hub.imu.heading()
        ac = hub.imu.acceleration()
        buf.append((t, dA, dB, h, ac[0], ac[1]))
        wait(15)

    # ---- dump: headers, then REST rows, then APPROACH rows ----
    emit(0, "trigger_ms", t_trig)
    emit(0, "max_cmd", MAX_CMD)
    emit(0, "gsign", gsign)
    emit(0, "aborted", aborted)

    ntot = len(buf)
    k = n_drive
    while k < ntot:
        r = buf[k]
        tt = int(r[0])
        emit(tt, "dist_A", r[1])
        emit(tt, "dist_B", r[2])
        emit(tt, "heading", float(r[3]))
        k += 1

    i = 0
    while i < n_drive:
        r = buf[i]
        tt = int(r[0])
        if (i % 2) == 0:
            emit(tt, "dist_A", r[1])
            emit(tt, "dist_B", r[2])
            emit(tt, "heading", float(r[3]))
        if (i % 6) == 0:
            emit(tt, "imu_ax", float(r[4]))
            emit(tt, "imu_ay", float(r[5]))
        i += 1

except Exception:
    try:
        emit(0, "exception", 1)
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
