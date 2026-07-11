"""
C1d — CHARACTERIZATION RUN 4 (tight straight-line control + clean dynamics).
Changes vs C1c, from C1c's data:
  - gsign hard-coded = 1 (learned in C1c); the disturbing "kick" is removed.
  - MAX_CMD = 1000 (at the motor's real max) so the inside wheel can actually
    slow to steer (C1c's 1100 pinned both wheels at the clamp -> no authority).
  - Feed-forward bias FF cancels the systematic left drift; P holds heading to 0;
    D (yaw rate from consecutive heading samples, sign-safe) damps the turn rate
    so it is ~0 at brake time (kills C1c's post-trigger coast).
Conservative 500 mm trigger (still a straightness + dynamics run, not near-wall).
Per-line dump, REST rows first, 30 s timeout.

Map (C1): motorL=Port.C (CCW=fwd), motorR=Port.D (CW=fwd),
forward ultrasonics = Port.A, Port.B.
"""
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port, Direction
from pybricks.tools import StopWatch, wait
from usys import stdout

MAX_CMD = 1000
GSIGN = 1
FF = 120          # feed-forward differential to cancel systematic left drift
KP = 30
KD = 4
DIFF_CAP = 350
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
    mL.run(MAX_CMD + FF)
    mR.run(MAX_CMD - FF)
    h_prev = hub.imu.heading()
    t_prev = 0

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
        dt = (t - t_prev) / 1000.0
        wz = (h - h_prev) / dt if dt > 0 else 0.0
        corr = -GSIGN * (KP * h + KD * wz)
        diff = FF + corr
        if diff > DIFF_CAP:
            diff = DIFF_CAP
        if diff < -DIFF_CAP:
            diff = -DIFF_CAP
        if not triggered:
            mL.run(MAX_CMD + diff)
            mR.run(MAX_CMD - diff)
        buf.append((t, dA, dB, h, ac[0], ac[1]))
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
        h_prev = h
        t_prev = t
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

    emit(0, "trigger_ms", t_trig)
    emit(0, "max_cmd", MAX_CMD)
    emit(0, "gsign", GSIGN)
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
