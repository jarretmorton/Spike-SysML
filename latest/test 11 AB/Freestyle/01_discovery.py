# Characterization run 1 (run-20260729-234458): discovery.
# Probes all six ports, samples sensors at rest, then four small nudges
# (+/+, -/-, +/-, -/+) to classify drivetrain geometry and sign conventions.
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

def emit(sensor, value):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'
                 % (clock.time(), sensor, value))

motors = {}
uss = {}
cols = {}

def probe(p, n):
    try:
        motors[n] = Motor(p)
        return 1.0
    except Exception:
        pass
    try:
        uss[n] = UltrasonicSensor(p)
        return 2.0
    except Exception:
        pass
    try:
        cols[n] = ColorSensor(p)
        return 3.0
    except Exception:
        return 0.0

def rd(n):
    d = uss[n].distance()
    return -1.0 if d is None else float(d)

def rc(n):
    try:
        return float(cols[n].reflection())
    except Exception:
        return -1.0

try:
    ports = [(Port.A, "A"), (Port.B, "B"), (Port.C, "C"),
             (Port.D, "D"), (Port.E, "E"), (Port.F, "F")]
    types = {}
    for p, n in ports:
        types[n] = probe(p, n)
    todo = [pn for pn in ports if types[pn[1]] == 0.0]
    if todo:
        wait(700)
        for p, n in todo:
            types[n] = probe(p, n)
    for n in "ABCDEF":
        emit("ptype_%s" % n, types[n])
    emit("batt_mv", float(hub.battery.voltage()))

    mlets = sorted(motors.keys())
    ulets = sorted(uss.keys())
    clets = sorted(cols.keys())

    for n in mlets:
        try:
            emit("lim_spd_%s" % n, float(motors[n].control.limits()[0]))
        except Exception:
            pass

    last = {}

    def stream(dur_ms, head_every):
        t0 = clock.time()
        th = t0 - head_every
        while clock.time() - t0 < dur_ms:
            for n in ulets:
                d = rd(n)
                if last.get("u" + n) != d:
                    last["u" + n] = d
                    emit("us_%s" % n, d)
            for n in clets:
                r = rc(n)
                if last.get("c" + n) != r:
                    last["c" + n] = r
                    emit("refl_%s" % n, r)
            if clock.time() - th >= head_every:
                th = clock.time()
                emit("head", float(hub.imu.heading()))
            wait(10)

    emit("phase", 0.0)
    stream(2500, 100)

    if len(mlets) >= 2:
        mA = motors[mlets[0]]
        mB = motors[mlets[1]]
        combos = [(300, 300), (-300, -300), (300, -300), (-300, 300)]
        for i in range(4):
            sa, sb = combos[i]
            emit("phase", float(i + 1))
            b_us = {}
            for n in ulets:
                b_us[n] = rd(n)
            b_h = hub.imu.heading()
            b_a = {}
            for n in mlets:
                b_a[n] = motors[n].angle()
            mA.run(sa)
            mB.run(sb)
            stream(450, 60)
            mA.brake()
            mB.brake()
            wait(650)
            for n in ulets:
                emit("dus_%s_%d" % (n, i + 1), rd(n) - b_us[n])
            emit("dhead_%d" % (i + 1), float(hub.imu.heading() - b_h))
            for n in mlets:
                emit("dang_%s_%d" % (n, i + 1), float(motors[n].angle() - b_a[n]))

    emit("phase", 9.0)
    for n in ulets:
        emit("us_%s" % n, rd(n))
    emit("head", float(hub.imu.heading()))
finally:
    for m in motors.values():
        try:
            m.stop()
        except Exception:
            pass
    stdout.write('{"event":"end"}\n')
