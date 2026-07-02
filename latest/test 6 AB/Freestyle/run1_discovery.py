from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

def emit(sensor, value):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n' % (clock.time(), sensor, float(value)))

KIND = {"none": 0.0, "motor": 1.0, "ultra": 2.0, "color": 3.0}
ports = [("A", Port.A), ("B", Port.B), ("C", Port.C), ("D", Port.D), ("E", Port.E), ("F", Port.F)]
kind = {}
motors = {}
ultras = {}
colors = {}

for nm, p in ports:
    k = "none"
    try:
        m = Motor(p)
        motors[nm] = m
        k = "motor"
    except Exception:
        pass
    if k == "none":
        try:
            s = UltrasonicSensor(p)
            ultras[nm] = s
            k = "ultra"
        except Exception:
            pass
    if k == "none":
        try:
            c = ColorSensor(p)
            colors[nm] = c
            k = "color"
        except Exception:
            pass
    kind[nm] = k

def dist(s):
    try:
        d = s.distance()
    except Exception:
        return -1
    if d is None:
        return -1
    return d

for _ in range(3):
    for nm, _p in ports:
        emit("portcode_" + nm, KIND[kind[nm]])
    wait(10)

sums = {nm: 0 for nm in ultras}
cnts = {nm: 0 for nm in ultras}
for i in range(12):
    for nm, s in ultras.items():
        d = dist(s)
        emit("dist_" + nm, d)
        if d >= 0:
            sums[nm] += d
            cnts[nm] += 1
    for nm, c in colors.items():
        try:
            r = c.reflection()
        except Exception:
            r = -1
        emit("refl_" + nm, r if r is not None else -1)
    emit("heading", hub.imu.heading())
    wait(40)

base = {}
for nm in ultras:
    base[nm] = (sums[nm] / cnts[nm]) if cnts[nm] else -1.0

far_set = [nm for nm in ultras if base[nm] > 700]
SAFE_MIN = 550

mnames = list(motors.keys())
results = []

def guarded(sa, sb, label):
    if len(mnames) < 2:
        return None
    m0 = motors[mnames[0]]
    m1 = motors[mnames[1]]
    d0 = {nm: dist(ultras[nm]) for nm in ultras}
    h0 = hub.imu.heading()
    emit("phase", 10 + label)
    m0.run(sa * 400)
    m1.run(sb * 400)
    t0 = clock.time()
    aborted = 0
    while clock.time() - t0 < 500:
        stop = False
        for nm, s in ultras.items():
            d = dist(s)
            emit("dist_" + nm, d)
            if nm in far_set and 0 <= d < SAFE_MIN:
                stop = True
        emit("heading", hub.imu.heading())
        if stop:
            aborted = 1
            break
        wait(20)
    m0.stop()
    m1.stop()
    wait(400)
    d1 = {nm: dist(ultras[nm]) for nm in ultras}
    h1 = hub.imu.heading()
    dd = {}
    for nm in ultras:
        if d0[nm] >= 0 and d1[nm] >= 0:
            dd[nm] = d1[nm] - d0[nm]
        else:
            dd[nm] = 0
    r = {"sa": sa, "sb": sb, "dhead": h1 - h0, "dd": dd, "ab": aborted}
    results.append(r)
    return r

try:
    guarded(1, 1, 1)
    guarded(1, -1, 2)
finally:
    for nm, m in motors.items():
        try:
            m.stop()
        except Exception:
            pass

print("=== PORTMAP ===")
for nm, _p in ports:
    print("PORT %s = %s" % (nm, kind[nm]))
print("ULTRA_BASE_MM " + " ".join("%s=%d" % (nm, int(base[nm])) for nm in ultras))
print("MOTOR_PORTS " + ",".join(mnames))
print("COLOR_PORTS " + ",".join(colors.keys()))
for r in results:
    dstr = " ".join("%s:%+d" % (nm, int(r["dd"][nm])) for nm in r["dd"])
    print("TEST m0=%+d m1=%+d dHead=%+d [%s] abort=%d" % (r["sa"], r["sb"], int(r["dhead"]), dstr, r["ab"]))

if len(results) == 2:
    tsame, topp = results[0], results[1]
    straight = tsame if abs(tsame["dhead"]) <= abs(topp["dhead"]) else topp
    order = sorted(ultras.keys(), key=lambda nm: -abs(straight["dd"][nm]))
    front = order[:2]
    rear = [nm for nm in ultras if nm not in front]
    fmove = 0
    for nm in front:
        fmove += straight["dd"][nm]
    if fmove < 0:
        fm0, fm1 = straight["sa"], straight["sb"]
    else:
        fm0, fm1 = -straight["sa"], -straight["sb"]
    print("=== DEDUCTION ===")
    print("FORWARD_CMD m0(%s)=%+d m1(%s)=%+d" % (mnames[0], fm0, mnames[1], fm1))
    print("FRONT_PORTS " + ",".join(front))
    print("REAR_PORTS " + ",".join(rear))
    for _ in range(3):
        emit("fwd_sign_m0", fm0)
        emit("fwd_sign_m1", fm1)
        for nm in front:
            emit("role_" + nm, 1)
        for nm in rear:
            emit("role_" + nm, 2)
        wait(10)

stdout.write('{"event":"end"}\n')
