# Characterization run 4 (run-20260730-001608): tight brake + offset pin.
# Soft 360 ms six-step ramp (slip 32 -> 11 mm), OFFA=40, trigger 80 mm remaining,
# then GYRO-STEERED duty-30 creep to gentle stall + 130 mm retreat.
# Yielded off_A = 9.5 mm; stop at 101.5 mm (predicted 101.5 - model closed).
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

K = 0.498
OFFA = 40.0
TRIG = 80.0
KS = 3.0

c0 = mc.angle()
d0 = md.angle()

def xf():
    return K * ((c0 - mc.angle()) + (md.angle() - d0)) / 2.0

def vf():
    return K * (md.speed() - mc.speed()) / 2.0

def rdA():
    d = ua.distance()
    return -1.0 if d is None else float(d)

def rdB():
    d = ub.distance()
    return -1.0 if d is None else float(d)

def ranger(tag):
    va = []
    vb = []
    for i in range(16):
        da = rdA()
        db = rdB()
        va.append(da)
        vb.append(db)
        emit("us_A", da)
        emit("us_B", db)
        wait(45)
    va.sort()
    vb.sort()
    ma = (va[7] + va[8]) / 2.0
    mb = (vb[7] + vb[8]) / 2.0
    emit("medA_" + tag, ma)
    emit("medB_" + tag, mb)
    return ma, mb

try:
    emit("batt_mv", float(hub.battery.voltage()))
    emit("phase", 0.0)
    medA0, medB0 = ranger("0")
    g = medA0
    if g < 900.0:
        g = 900.0
    if g > 1150.0:
        g = 1150.0
    gap0 = g - OFFA
    emit("gap0", gap0)

    emit("phase", 1.0)
    t1 = clock.time()
    for du in (30, 45, 60, 75, 90):
        mc.dc(-du)
        md.dc(du)
        wait(60)
    mc.dc(-100)
    md.dc(100)
    te = clock.time()
    th = clock.time()
    vmax = 0.0
    xtrig = -1.0
    vtrig = -1.0
    hardbrake = 0.0
    while True:
        now = clock.time()
        xx = xf()
        rem = gap0 - xx
        if rem <= TRIG and xx > 200.0:
            xtrig = xx
            vtrig = vf()
            break
        e = hub.imu.heading()
        if e > 0.0:
            c = KS * e
            if c > 18.0:
                c = 18.0
            mc.dc(-100.0 + c)
            md.dc(100.0)
        else:
            c = KS * e
            if c < -18.0:
                c = -18.0
            mc.dc(-100.0)
            md.dc(100.0 + c)
        if now - te >= 100:
            te = now
            vv = vf()
            if vv > vmax:
                vmax = vv
            emit("x", xx)
            emit("v", vv)
            da = rdA()
            if 0.0 < da < 160.0:
                hardbrake = 1.0
                xtrig = xx
                vtrig = vv
                break
            emit("us_A", da)
        if now - th >= 200:
            th = now
            emit("head", float(hub.imu.heading()))
        if now - t1 > 6000:
            hardbrake = 2.0
            xtrig = xx
            vtrig = vf()
            break
        wait(5)
    mc.dc(100)
    md.dc(-100)
    tb = clock.time()
    emit("x_trig", xtrig)
    emit("v_trig", vtrig)
    emit("vmax", vmax)
    emit("hardbrake", hardbrake)
    emit("t_trig", float(tb - t1))
    tbe = tb
    while True:
        now = clock.time()
        vv = vf()
        if vv <= 25.0:
            break
        if now - tb > 1500:
            break
        if now - tbe >= 50:
            tbe = now
            emit("x", xf())
            emit("v", vv)
        wait(5)
    mc.hold()
    md.hold()
    emit("t_brake", float(clock.time() - tb))
    wait(450)
    emit("phase", 2.0)
    emit("x_stop", xf())
    emit("head", float(hub.imu.heading()))
    medAs, medBs = ranger("s")

    emit("phase", 3.0)
    xc0 = xf()
    tc0 = clock.time()
    tmove = clock.time()
    armed = False
    hit = 0.0
    mc.dc(-30)
    md.dc(30)
    emit("duty", 30.0)
    tl = clock.time()
    thc = clock.time()
    while True:
        now = clock.time()
        s = abs(mc.speed()) + abs(md.speed())
        if s > 60:
            tmove = now
            if s > 150:
                armed = True
        if armed and now - tmove > 350 and xf() - xc0 > 15.0:
            hit = 1.0
            break
        e = hub.imu.heading()
        if e > 0.0:
            c = 2.5 * e
            if c > 8.0:
                c = 8.0
            mc.dc(-30.0 + c)
            md.dc(30.0)
        else:
            c = 2.5 * e
            if c < -8.0:
                c = -8.0
            mc.dc(-30.0)
            md.dc(30.0 + c)
        if (not armed) and now - tc0 > 5000:
            break
        if now - tc0 > 9000:
            break
        if xf() - xc0 > 250.0:
            break
        if now - tl >= 150:
            tl = now
            emit("x", xf())
            emit("us_A", rdA())
        if now - thc >= 300:
            thc = now
            emit("head", float(hub.imu.heading()))
        wait(10)
    mc.stop()
    md.stop()
    emit("hit", hit)
    wait(450)
    emit("phase", 4.0)
    xw = xf()
    emit("x_wall", xw)
    emit("head", float(hub.imu.heading()))
    medAw, medBw = ranger("w")

    emit("phase", 5.0)
    mc.run(200)
    md.run(-200)
    t5 = clock.time()
    while xf() > xw - 130.0 and clock.time() - t5 < 3500:
        if clock.time() - tl >= 150:
            tl = clock.time()
            emit("x", xf())
            emit("us_A", rdA())
        wait(10)
    mc.brake()
    md.brake()
    wait(450)
    xe = xf()
    emit("x_end", xe)
    emit("head", float(hub.imu.heading()))
    medAr, medBr = ranger("r")
    emit("phase", 9.0)
finally:
    try:
        mc.stop()
        md.stop()
    except Exception:
        pass
    stdout.write('{"event":"end"}\n')
