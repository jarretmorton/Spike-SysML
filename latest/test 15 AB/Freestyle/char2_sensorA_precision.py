# char2 — precision attempt controlling on sensor A alone
# Run id: run-20260806-095340   (81.9 s, 947 telemetry events)
#
# Changes from char1:
#   * geometry hard-coded (ports, f = (-1,+1), turn_sign = +1, mmpd = 0.489)
#   * control on sensor A only, never min(A,B)
#   * a 300 ms low-speed creep test that aborts if A does not DECREASE
#   * raw A and encoder logged at 20 ms THROUGH the stop and 900 ms after
#   * three identical approaches to one target, to measure run-to-run spread
#
# KEY RESULT — the invariant (usA + enc_mm) through cruise:
#   1074.8 1074.9 1074.4 1073.4 1071.4 1070.7 1070.7 1071.2
#   1071.5 1071.5 1071.3 1070.1 1071.4 1071.4      -> constant to +/-1.5 mm
# This proved mmpd = 0.489 is correct and that there is no significant sensor
# lag; the apparent "9% wheel slip" seen elsewhere was an artifact.
#
# FAULT FOUND: sensor A FREEZES at ~290 mm and never recovers (288/295/287 on
# the three cycles) while the encoder keeps advancing 27+ mm. S_raw came out
# exactly 0.00 on all three cycles, which is what exposed it.
# A also read ~128 mm longer than B throughout -- later shown to be crosstalk,
# not a mounting offset.

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

BUF = []
BUFMAX = 2600

def lg(n, v):
    if len(BUF) < BUFMAX:
        BUF.append((clock.time(), n, float(v)))

def dump():
    global BUF
    b = BUF
    BUF = []
    for i in range(len(b)):
        e = b[i]
        stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%.2f}\n' % (e[0], e[1], e[2]))

MMPD = 0.489
F0 = -1
F1 = 1
TS = 1.0
TLAG = 0.060
BRAKE = 14.5
TARGET = 230.0
FLOOR = 210.0
KP = 1.8
KD = 0.10
CAP = 16.0

m0 = None
m1 = None
uA = None
uB = None
A0 = 1000.0


def dmm():
    x = uA.distance()
    if x <= 0:
        return -1.0
    return float(x)


def medA(n):
    vals = []
    for i in range(n):
        x = dmm()
        if x > 0:
            vals.append(x)
        wait(20)
    if not vals:
        return -1.0
    vals.sort()
    return vals[len(vals) // 2]


def enc():
    return (F0 * m0.angle() + F1 * m1.angle()) * 0.5 * MMPD


def vel():
    return (F0 * m0.speed() + F1 * m1.speed()) * 0.5 * MMPD


def hd():
    try:
        return hub.imu.heading()
    except Exception:
        return 0.0


def drive(duty, corr):
    d0 = duty + corr
    d1 = duty - corr
    if d0 > 100: d0 = 100
    if d0 < -100: d0 = -100
    if d1 > 100: d1 = 100
    if d1 < -100: d1 = -100
    m0.dc(F0 * d0)
    m1.dc(F1 * d1)


def drive_max(corr):
    if corr > CAP: corr = CAP
    if corr < -CAP: corr = -CAP
    if corr >= 0:
        d0 = 100.0
        d1 = 100.0 - 2.0 * corr
    else:
        d0 = 100.0 + 2.0 * corr
        d1 = 100.0
    m0.dc(F0 * d0)
    m1.dc(F1 * d1)


def halt():
    m0.brake()
    m1.brake()


def square_up(tol, tmax):
    t0 = clock.time()
    while clock.time() - t0 < tmax:
        h = hd()
        if abs(h) < tol:
            break
        c = -1.6 * h * TS
        if c > 45: c = 45
        if c < -45: c = -45
        if 0.0 <= c < 19.0: c = 19.0
        if -19.0 < c < 0.0: c = -19.0
        drive(0, c)
        wait(10)
    halt()
    wait(350)


def go_back(target):
    t0 = clock.time()
    tl = 0
    hp = hd()
    tp = clock.time()
    while clock.time() - t0 < 8000:
        d = dmm()
        if d > 0 and d >= target:
            break
        t = clock.time()
        h = hd()
        dt = t - tp
        hdot = 0.0
        if dt >= 25:
            hdot = (h - hp) * 1000.0 / dt
            hp = h
            tp = t
        c = -(KP * h + KD * hdot) * TS
        if c > CAP: c = CAP
        if c < -CAP: c = -CAP
        drive(-70, c)
        if t - tl >= 150:
            if d > 0:
                lg("fwd_mm", d)
            lg("head_deg", h)
            tl = t
        wait(10)
    halt()
    wait(500)


def approach(tag):
    global MMPD
    e_start = enc()
    d_start = medA(7)
    lg(tag + "_A_start", d_start)
    anchor_d = d_start
    anchor_e = e_start
    last_raw = d_start
    maxmm = d_start - FLOOR
    t0 = clock.time()
    tl1 = 0
    tl2 = 0
    vf = 0.0
    fired = 0
    reason = 0
    d_fire = 0.0
    raw_fire = 0.0
    e_fire = 0.0
    v_fire = 0.0
    hp = hd()
    tp = t0
    while True:
        t = clock.time()
        if t - t0 > 6000:
            reason = 3
            break
        raw = dmm()
        ee = enc()
        if raw > 60 and raw < 1900 and raw != last_raw:
            anchor_d = raw
            anchor_e = ee
            last_raw = raw
        d_est = anchor_d - (ee - anchor_e)
        v = vel()
        vf = 0.7 * vf + 0.3 * v
        if t - tl1 >= 20:
            if raw > 0:
                lg("usA", raw)
            lg("enc_mm", ee - e_start)
            tl1 = t
        h = hd()
        if t - tl2 >= 60:
            lg("head_deg", h)
            lg("fwd_mm", d_est)
            tl2 = t
        if (ee - e_start) > maxmm:
            reason = 2
            break
        if d_est <= FLOOR:
            reason = 1
            break
        if d_est - (TLAG * vf + BRAKE) <= TARGET:
            fired = 1
            d_fire = d_est
            raw_fire = last_raw
            e_fire = ee
            v_fire = vf
            break
        dt = t - tp
        hdot = 0.0
        if dt >= 25:
            hdot = (h - hp) * 1000.0 / dt
            hp = h
            tp = t
        drive_max(-(KP * h + KD * hdot) * TS)
        wait(4)
    halt()
    t_stop = clock.time()
    if not fired:
        d_fire = anchor_d - (enc() - anchor_e)
        raw_fire = last_raw
        e_fire = enc()
        v_fire = vf
    while clock.time() - t_stop < 900:
        r = dmm()
        if r > 0:
            lg("usA", r)
        lg("enc_mm", enc() - e_start)
        wait(30)
    e_rest = enc()
    A_rest = medA(9)
    lg(tag + "_fired", fired)
    lg(tag + "_reason", reason)
    lg(tag + "_A_fire_est", d_fire)
    lg(tag + "_A_fire_raw", raw_fire)
    lg(tag + "_v_fire", v_fire)
    lg(tag + "_A_rest", A_rest)
    lg(tag + "_S_est", d_fire - A_rest)
    lg(tag + "_S_raw", raw_fire - A_rest)
    lg(tag + "_brake_mm", e_rest - e_fire)
    lg(tag + "_lag_mm", (d_fire - A_rest) - (e_rest - e_fire))
    lg(tag + "_head_end", hd())
    tot = e_rest - e_start
    if tot > 200:
        lg(tag + "_scale_chk", (d_start - A_rest) / tot)
    return A_rest


def main():
    global m0, m1, uA, uB, A0
    wait(700)
    try:
        hub.imu.reset_heading(0)
    except Exception:
        pass
    try:
        m0 = Motor(Port.C)
        m1 = Motor(Port.D)
        uA = UltrasonicSensor(Port.A)
        uB = UltrasonicSensor(Port.B)
    except Exception:
        lg("ABORT_ports", 1)
        return
    try:
        m0.reset_angle(0)
        m1.reset_angle(0)
    except Exception:
        pass

    a0 = medA(9)
    b0 = uB.distance()
    lg("A_startline", a0)
    lg("B_startline", b0)
    if a0 < 700 or a0 > 1400:
        lg("ABORT_range", a0)
        return
    A0 = a0

    e0 = enc()
    drive(30, 0)
    wait(300)
    halt()
    wait(500)
    a1 = medA(7)
    moved = enc() - e0
    lg("creep_dA", a1 - a0)
    lg("creep_enc", moved)
    if not (a1 > 0 and (a0 - a1) > 8 and moved > 8):
        lg("ABORT_creep", 1)
        return
    lg("creep_scale", (a0 - a1) / moved)
    dump()

    r1 = approach("k1")
    dump()
    go_back(A0 - 10)
    square_up(1.5, 2200)

    r2 = approach("k2")
    dump()
    go_back(A0 - 10)
    square_up(1.5, 2200)

    r3 = approach("k3")
    lg("park_A", medA(11))
    lg("park_B", uB.distance())
    lg("park_head", hd())
    dump()


try:
    main()
except Exception as ex:
    lg("EXC", 1)
finally:
    try:
        m0.stop()
        m1.stop()
    except Exception:
        pass
    dump()
    stdout.write('{"event":"end"}\n')
