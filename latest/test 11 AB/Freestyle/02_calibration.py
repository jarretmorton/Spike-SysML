# Characterization run 2 (run-20260729-235155): calibration.
# Standstill ranging -> 500 deg/s drive ~520 mm (encoder scale k) ->
# adaptive-duty creep to wall (stalled/ground; hit=0) -> 150 mm retreat.
# Yielded k = 0.498 mm/deg; offset bracketed 12-40 mm.
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

def emit(sensor, value):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'
                 % (clock.time(), sensor, value))

mc = Motor(Port.C)
md = Motor(Port.D)
ua = UltrasonicSensor(Port.A)
ub = UltrasonicSensor(Port.B)

KG = 0.46
c0 = mc.angle()
d0 = md.angle()

def rdA():
    d = ua.distance()
    return -1.0 if d is None else float(d)

def rdB():
    d = ub.distance()
    return -1.0 if d is None else float(d)

def x():
    return KG * ((c0 - mc.angle()) + (md.angle() - d0)) / 2.0

def snap():
    emit("angC", float(mc.angle()))
    emit("angD", float(md.angle()))
    emit("x", x())

def ranger(tag):
    va = []
    vb = []
    for i in range(14):
        da = rdA()
        db = rdB()
        va.append(da)
        vb.append(db)
        emit("us_A", da)
        emit("us_B", db)
        wait(50)
    va.sort()
    vb.sort()
    ma = (va[6] + va[7]) / 2.0
    mb = (vb[6] + vb[7]) / 2.0
    emit("medA_" + tag, ma)
    emit("medB_" + tag, mb)
    return ma, mb

lastu = {}

def stream_step(tm):
    da = rdA()
    if lastu.get("a") != da:
        lastu["a"] = da
        emit("us_A", da)
    db = rdB()
    if lastu.get("b") != db:
        lastu["b"] = db
        emit("us_B", db)
    if clock.time() - tm[0] >= 40:
        tm[0] = clock.time()
        emit("x", x())
    if clock.time() - tm[1] >= 100:
        tm[1] = clock.time()
        emit("head", float(hub.imu.heading()))
    if clock.time() - tm[2] >= 80:
        tm[2] = clock.time()
        emit("spd", (abs(mc.speed()) + abs(md.speed())) / 2.0)
    return db

try:
    emit("batt_mv", float(hub.battery.voltage()))
    emit("phase", 0.0)
    snap()
    ranger("0")

    emit("phase", 1.0)
    snap()
    tm = [clock.time(), clock.time(), clock.time()]
    mc.run(-500)
    md.run(500)
    t1 = clock.time()
    while True:
        db = stream_step(tm)
        if x() >= 500.0:
            break
        if 0.0 < db < 380.0:
            break
        if clock.time() - t1 > 6000:
            break
        wait(15)
    mc.brake()
    md.brake()
    wait(500)

    emit("phase", 2.0)
    snap()
    ranger("1")

    emit("phase", 3.0)
    snap()
    xc0 = x()
    duty = 20
    armed = False
    cnt = 0
    mc.dc(-duty)
    md.dc(duty)
    emit("duty", float(duty))
    t3 = clock.time()
    la = clock.time()
    hit = False
    while True:
        s = abs(mc.speed()) + abs(md.speed())
        if s > 150:
            armed = True
        if armed and s < 50:
            cnt += 1
        else:
            cnt = 0
        if armed and cnt >= 15 and (x() - xc0) > 30.0:
            hit = True
            break
        if clock.time() - t3 > 12000:
            break
        if clock.time() - la > 500 and s < 60 and cnt < 10 and duty < 45:
            duty += 4
            la = clock.time()
            mc.dc(-duty)
            md.dc(duty)
            emit("duty", float(duty))
        stream_step(tm)
        wait(20)
    mc.stop()
    md.stop()
    emit("hit", 1.0 if hit else 0.0)
    wait(450)

    emit("phase", 4.0)
    snap()
    ranger("c")
    xct = x()
    emit("x", xct)

    emit("phase", 5.0)
    mc.run(300)
    md.run(-300)
    t5 = clock.time()
    while x() > xct - 150.0 and clock.time() - t5 < 4000:
        stream_step(tm)
        wait(15)
    mc.brake()
    md.brake()
    wait(500)

    emit("phase", 6.0)
    snap()
    ranger("r")
    emit("phase", 9.0)
finally:
    try:
        mc.stop()
        md.stop()
    except Exception:
        pass
    stdout.write('{"event":"end"}\n')
