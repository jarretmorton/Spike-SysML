"""
C1 — CHARACTERIZATION RUN 1 (SPIKE Prime / Pybricks / MicroPython)
Purpose: discover port map + forward drive sign + forward-vs-rear ultrasonics,
then a max-speed approach with a CONSERVATIVE trigger (500 mm) + emergency floor
(120 mm) + time cap, then a rest dwell. Binds v_max, a_brake, t_lat, D_stop,
Δt_s, σ_S, heading drift, A/B agreement, close-range behaviour.

Wire contract: essentials buffered on the hot path; buffer dumped AFTER motors
stop; every telemetry line is {"timestamp_ms","sensor","value"}; run ends with
{"event":"end"}. Hub-clock timestamps only. try/finally guarantees motors stop
and the sentinel is written.
"""
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

# ---- config ----
CREEP = 110          # deg/s, low-speed discovery
CREEP_MS = 300
SETTLE_MS = 150
MAX_CMD = 1200       # deg/s command (clamps to physical max; SAME constant in operation)
TRIG = 500           # mm, conservative approach trigger (min of A,B)
FLOOR = 120          # mm, emergency brake floor
CAP_MS = 3500        # ms, hard time cap
LOOP_MS = 10         # ms, control-loop pacing
POST_BRAKE_MS = 1000 # ms to keep logging after brake command
REST_MS = 600        # ms rest dwell

PORT_LIST = [Port.A, Port.B, Port.C, Port.D, Port.E, Port.F]


def emit(t, name, val):
    if isinstance(val, float):
        vs = "%.3f" % val
    else:
        vs = str(val)
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%s}\n' % (int(t), name, vs))


def pidx(p):
    i = 0
    for q in PORT_LIST:
        if q == p:
            return i
        i += 1
    return -1


hub = PrimeHub()
mL = None
mR = None
motors = {}
ultras = {}

try:
    # ---- type-probe each port exactly once ----
    for p in PORT_LIST:
        got = False
        try:
            m = Motor(p)
            motors[pidx(p)] = m
            got = True
        except Exception:
            got = False
        if got:
            continue
        try:
            u = UltrasonicSensor(p)
            ultras[pidx(p)] = u
        except Exception:
            pass

    mkeys = sorted(motors.keys())
    ukeys = sorted(ultras.keys())
    emit(0, "n_motors", len(mkeys))
    emit(0, "n_ultra", len(ukeys))

    if len(mkeys) < 2 or len(ukeys) < 2:
        emit(0, "error_discovery", 1)
    else:
        mL = motors[mkeys[0]]
        mR = motors[mkeys[1]]

        def read_ultra():
            d = {}
            for k in ukeys:
                d[k] = ultras[k].distance()
            return d

        def creep(a, b):
            u0 = read_ultra()
            h0 = hub.imu.heading()
            mL.run(a * CREEP)
            mR.run(b * CREEP)
            wait(CREEP_MS)
            mL.brake()
            mR.brake()
            wait(SETTLE_MS)
            u1 = read_ultra()
            h1 = hub.imu.heading()
            du = {}
            for k in ukeys:
                du[k] = u1[k] - u0[k]
            return (h1 - h0), du

        dh_same, du_same = creep(1, 1)
        dh_opp, du_opp = creep(1, -1)
        emit(0, "dh_same", float(dh_same))
        emit(0, "dh_opp", float(dh_opp))

        if abs(dh_same) <= abs(dh_opp):
            base = (1, 1)
            du = du_same
        else:
            base = (1, -1)
            du = du_opp

        neg = []
        pos = []
        for k in ukeys:
            if du[k] < 0:
                neg.append(k)
            else:
                pos.append(k)

        if len(neg) >= 2:
            fwd = [neg[0], neg[1]]
            rear = pos[0] if len(pos) > 0 else -1
            fcombo = (base[0], base[1])
        elif len(pos) >= 2:
            fwd = [pos[0], pos[1]]
            rear = neg[0] if len(neg) > 0 else -1
            fcombo = (-base[0], -base[1])
        else:
            fwd = [ukeys[0], ukeys[1]]
            rear = -1
            fcombo = (base[0], base[1])

        sL = fcombo[0]
        sR = fcombo[1]
        fa = fwd[0]
        fb = fwd[1]

        emit(0, "map_motorL_port", mkeys[0])
        emit(0, "map_motorR_port", mkeys[1])
        emit(0, "map_fwdA_port", fa)
        emit(0, "map_fwdB_port", fb)
        emit(0, "map_rear_port", rear)
        emit(0, "map_signL", sL)
        emit(0, "map_signR", sR)
        emit(0, "max_cmd", MAX_CMD)

        try:
            mL.control.limits(acceleration=20000)
            mR.control.limits(acceleration=20000)
        except Exception:
            pass

        # ---- max-speed approach ----
        buf = []
        sw = StopWatch()
        mL.run(sL * MAX_CMD)
        mR.run(sR * MAX_CMD)
        triggered = False
        t_trig = -1
        brake_t = -1
        while True:
            t = sw.time()
            dA = ultras[fa].distance()
            dB = ultras[fb].distance()
            ac = hub.imu.acceleration()
            hd = hub.imu.heading()
            buf.append((t, dA, dB, ac[0], ac[1], ac[2], hd, mL.angle(), mR.angle()))
            dmin = dA if dA < dB else dB
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

        # ---- rest dwell ----
        rt0 = sw.time()
        while sw.time() - rt0 < REST_MS:
            t = sw.time()
            dA = ultras[fa].distance()
            dB = ultras[fb].distance()
            ac = hub.imu.acceleration()
            hd = hub.imu.heading()
            buf.append((t, dA, dB, ac[0], ac[1], ac[2], hd, mL.angle(), mR.angle()))
            wait(15)

        emit(0, "trigger_ms", t_trig)

        # ---- dump buffer (motors already stopped) ----
        n = len(buf)
        i = 0
        while i < n:
            r = buf[i]
            emit(r[0], "dist_A", r[1])
            emit(r[0], "dist_B", r[2])
            if (i % 4) == 0:
                emit(r[0], "imu_ax", float(r[3]))
                emit(r[0], "imu_ay", float(r[4]))
                emit(r[0], "imu_az", float(r[5]))
            if (i % 8) == 0:
                emit(r[0], "heading", float(r[6]))
                emit(r[0], "ang_L", r[7])
                emit(r[0], "ang_R", r[8])
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
