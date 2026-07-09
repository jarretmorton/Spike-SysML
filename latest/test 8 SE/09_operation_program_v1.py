"""
OPERATION PROGRAM v1  (LOCKED CANDIDATE)
Same program is used for the verification run (dress rehearsal) and, if it
validates, for all 5 scored operation runs UNCHANGED.

Calibrated (sensor-A frame, from C1..C1d + operator gap = 542 mm at S_A = 557):
  forward sensor  = A (Port A); B discarded (only a coarse backup)
  c_A             = 15 mm  (front point is 15 mm ahead of S_A)
  D_stop          = 53 mm  at max speed (measured)
  d_trig_A        = 113 mm  ->  predicted rest S_A = 60 mm, gap G = 45 mm
Heading hold (from C1d): gsign=1, MAX_CMD=1000, FF=120, KP=30, KD=4.
Drive straight at max speed; trigger on first valid S_A <= 113; brake.
Floor (S_A <= 80 without trigger) and |heading|>25 deg are safety-only.

Map: motorL=Port.C (CCW=fwd), motorR=Port.D (CW=fwd), ultrasonics A=Port.A,B=Port.B.
"""
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port, Direction
from pybricks.tools import StopWatch, wait
from usys import stdout

MAX_CMD = 1000
GSIGN = 1
FF = 120
KP = 30
KD = 4
DIFF_CAP = 350
C_A = 15
D_TRIG_A = 113
FLOOR_A = 80
ABORT_DEG = 25
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


def median(xs):
    ys = sorted(xs)
    n = len(ys)
    if n == 0:
        return -1
    if n % 2 == 1:
        return ys[n // 2]
    return (ys[n // 2 - 1] + ys[n // 2]) / 2.0


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
        buf.append((t, dA, dB, h))
        vA = dA if dA < 1900 else 99999
        if (not triggered) and vA <= D_TRIG_A:
            triggered = True
            t_trig = t
            brake_t = t
            mL.brake()
            mR.brake()
        elif (not triggered) and vA <= FLOOR_A:
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

    restA = []
    restB = []
    hlast = 0.0
    rt0 = sw.time()
    while sw.time() - rt0 < REST_MS:
        a = uA.distance()
        b = uB.distance()
        hlast = hub.imu.heading()
        if a < 1900:
            restA.append(a)
        if b < 1900:
            restB.append(b)
        wait(15)

    sA = median(restA)
    sB = median(restB)
    gest = (sA - C_A) if sA >= 0 else -1
    emit(0, "trigger_ms", t_trig)
    emit(0, "max_cmd", MAX_CMD)
    emit(0, "aborted", aborted)
    emit(0, "distA_rest", sA if isinstance(sA, float) else float(sA))
    emit(0, "distB_rest", sB if isinstance(sB, float) else float(sB))
    emit(0, "heading_rest", float(hlast))
    emit(0, "gap_est", gest if isinstance(gest, float) else float(gest))

    n = len(buf)
    i = 0
    while i < n:
        r = buf[i]
        if (i % 2) == 0:
            emit(int(r[0]), "dist_A", r[1])
            emit(int(r[0]), "heading", float(r[3]))
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
