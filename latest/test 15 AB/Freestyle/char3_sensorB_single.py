# char3 — single-sensor operation, stall-immune estimator, S measured directly
# Run id: run-20260806-095951   (48.3 s, 860 telemetry events)
#
# Changes from char2:
#   * construct ONLY the Port B sensor. Pybricks starts a sensor pinging on
#     construction, so merely constructing A and E was enough to corrupt B.
#   * stall-immune estimator: re-anchor only on a reading that BOTH changed
#     AND agrees with dead reckoning within TOL. A frozen sensor fails the
#     first test, a multi-path spike fails the second.
#   * S measured on ONE channel end to end: S = B_est_at_trigger - B_settled.
#     No cross-sensor offset assumptions, and the brake slide is captured.
#   * three identical approaches, to get run-to-run spread at the operating point.
#
# HEADLINE RESULT — crosstalk confirmed:
#   With A silenced, B alone read 1006 mm at the start line, exactly what A used
#   to read. The apparent "126 mm mounting offset" between A and B never existed;
#   it was B mishearing A's pings. scale_chk then came back 0.98/0.99/1.00,
#   confirming mmpd = 0.489 over the full 900 mm.
#
# MEASURED (three approaches, all fired at 154 mm within 0.4 mm):
#   S_true      51.9   52.6   65.4  mm
#   B_settled  102    102     89    mm
#   encoder      16.4  15.2   14.7  mm   <- wheels stop in ~60 ms
#   slide        35.5  37.4   50.8  mm   <- unseen by encoder, the variance source
# Deceleration works out to ~0.21 g, i.e. a slippery floor; the wheels lock and
# the chassis slides, and floor friction variation moves S between 52 and 65.
#
# NOTE: B still stalls even with A silenced (591 mm for ~80 ms, 279 mm for
# ~125 ms before jumping to 198). The estimator absorbed both: stale_mm at
# trigger was only 3-9 mm.

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
KS = 0.090
SMIN = 30.0
SMAX = 60.0
TARGET = 110.0
FLOOR = 60.0
KP = 1.8
KD = 0.10
CAP = 16.0
TOL = 60.0

m0 = None
m1 = None
uB = None
B0 = 880.0


def dmm():
    x = uB.distance()
    if x <= 0:
        return -1.0
    return float(x)


def medB(n):
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
        if t - tl >= 200:
            if d > 0:
                lg("fwd_mm", d)
            tl = t
        wait(10)
    halt()
    wait(500)


def approach(tag):
    e_start = enc()
    d_start = medB(7)
    lg(tag + "_B_start", d_start)
    anchor_d = d_start
    anchor_e = e_start
    last_raw = d_start
    maxmm = d_start - FLOOR
    t0 = clock.time()
    tl1 = 0
    tl2 = 0
    vf = 0.0
    n_loop = 0
    n_fresh = 0
    fired = 0
    reason = 0
    d_fire = 0.0
    raw_fire = 0.0
    e_fire = 0.0
    v_fire = 0.0
    stale_mm = 0.0
    hp = hd()
    tp = t0
    while True:
        t = clock.time()
        if t - t0 > 6000:
            reason = 3
            break
        raw = dmm()
        ee = enc()
        d_est = anchor_d - (ee - anchor_e)
        n_loop += 1
        if raw > 0 and raw != last_raw and abs(raw - d_est) < TOL:
            anchor_d = raw
            anchor_e = ee
            last_raw = raw
            d_est = raw
            n_fresh += 1
        v = vel()
        vf = 0.7 * vf + 0.3 * v
        per = 60
        if d_est < 700:
            per = 20
        if t - tl1 >= per:
            if raw > 0:
                lg("usB", raw)
            lg("enc_mm", ee - e_start)
            lg("est_mm", d_est)
            tl1 = t
        h = hd()
        if t - tl2 >= 100:
            lg("head_deg", h)
            tl2 = t
        if (ee - e_start) > maxmm:
            reason = 2
            break
        if d_est <= FLOOR:
            reason = 1
            break
        s = KS * vf
        if s < SMIN: s = SMIN
        if s > SMAX: s = SMAX
        if d_est - s <= TARGET:
            fired = 1
            d_fire = d_est
            raw_fire = last_raw
            e_fire = ee
            v_fire = vf
            stale_mm = ee - anchor_e
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
        stale_mm = enc() - anchor_e
    while clock.time() - t_stop < 700:
        r = dmm()
        if r > 0:
            lg("usB", r)
        lg("enc_mm", enc() - e_start)
        wait(40)
    e_rest = enc()
    B_rest = medB(9)
    lg(tag + "_fired", fired)
    lg(tag + "_reason", reason)
    lg(tag + "_B_fire_est", d_fire)
    lg(tag + "_B_fire_raw", raw_fire)
    lg(tag + "_stale_mm", stale_mm)
    lg(tag + "_v_fire", v_fire)
    lg(tag + "_B_rest", B_rest)
    lg(tag + "_S_true", d_fire - B_rest)
    lg(tag + "_enc_after", e_rest - e_fire)
    lg(tag + "_skid_mm", (d_fire - B_rest) - (e_rest - e_fire))
    lg(tag + "_head_end", hd())
    lg(tag + "_freshfrac", 100.0 * n_fresh / n_loop)
    tot = e_rest - e_start
    if tot > 200:
        lg(tag + "_scale_chk", (d_start - B_rest) / tot)
    return B_rest


def main():
    global m0, m1, uB, B0
    wait(700)
    try:
        hub.imu.reset_heading(0)
    except Exception:
        pass
    try:
        m0 = Motor(Port.C)
        m1 = Motor(Port.D)
        uB = UltrasonicSensor(Port.B)
    except Exception:
        lg("ABORT_ports", 1)
        return
    try:
        m0.reset_angle(0)
        m1.reset_angle(0)
    except Exception:
        pass

    b0 = medB(9)
    lg("B_startline", b0)
    if b0 < 600 or b0 > 1300:
        lg("ABORT_range", b0)
        return
    B0 = b0

    e0 = enc()
    drive(30, 0)
    wait(300)
    halt()
    wait(500)
    b1 = medB(7)
    moved = enc() - e0
    lg("creep_dB", b1 - b0)
    lg("creep_enc", moved)
    if not (b1 > 0 and (b0 - b1) > 8 and moved > 8):
        lg("ABORT_creep", 1)
        return
    lg("creep_scale", (b0 - b1) / moved)
    dump()

    r1 = approach("k1")
    dump()
    go_back(B0 - 10)
    square_up(1.5, 2200)

    r2 = approach("k2")
    dump()
    go_back(B0 - 10)
    square_up(1.5, 2200)

    r3 = approach("k3")
    lg("park_B", medB(11))
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
