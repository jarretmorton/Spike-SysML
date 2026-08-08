# char1 — discovery, drivetrain conventions, and three max-speed approach cycles
# Run id: run-20260806-094342   (44.2 s, 483 telemetry events)
#
# Goal: learn everything about an unknown rover in ONE flash-and-run.
#   Stage A  probe all six ports for Motor / UltrasonicSensor / ColorSensor
#   Stage B  two paired duty bursts to resolve which motor polarity drives
#            straight, which direction is "forward", which ultrasonics face
#            forward, and the sign convention for heading trim
#   Stage C  three max-speed approach-and-stop cycles with self-return
#
# OUTCOME / KNOWN FAULTS (retained for the record):
#   * Port map and forward polarity resolved correctly:
#       A,B,E = ultrasonic, C,D = motor, F = colour;  f = (-1,+1);  turn_sign = +1
#   * BUG: the (+,+) burst turned out to be the SPIN and ran first, leaving the
#     rover ~40 deg off-square. The translation burst that followed was therefore
#     measured at an angle with sensor A off the wall, producing a nonsense wheel
#     calibration (mmpd_init = 0.16 instead of 0.489). That propagated a negative
#     stopping distance from cycle 1 into cycle 2, which drove to 49 mm.
#     FIX: run the translation test first, or hard-code geometry once known.
#   * BUG: front() returned min(A,B), so control rode whichever sensor was
#     misbehaving. Sensor B stalls; sensor A floors at ~290 mm.
#     FIX: use exactly one sensor (see char3).

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

BUF = []
BUFMAX = 2000

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

mmpd = 0.49
f0 = 1
f1 = 1
turn_sign = 1.0
m0 = None
m1 = None
uA = None
uB = None
FLOOR = 100.0


def drive(duty, corr):
    d0 = duty + corr
    d1 = duty - corr
    if d0 > 100: d0 = 100
    if d0 < -100: d0 = -100
    if d1 > 100: d1 = 100
    if d1 < -100: d1 = -100
    m0.dc(f0 * d0)
    m1.dc(f1 * d1)


def drive_max(corr):
    if corr > 12: corr = 12
    if corr < -12: corr = -12
    if corr >= 0:
        d0 = 100.0
        d1 = 100.0 - 2.0 * corr
    else:
        d0 = 100.0 + 2.0 * corr
        d1 = 100.0
    m0.dc(f0 * d0)
    m1.dc(f1 * d1)


def halt():
    m0.brake()
    m1.brake()


def ang():
    return (f0 * m0.angle() + f1 * m1.angle()) / 2.0


def spd():
    return (f0 * m0.speed() + f1 * m1.speed()) / 2.0


def front():
    a = uA.distance()
    b = uB.distance()
    if a <= 0: a = 2000
    if b <= 0: b = 2000
    if a < b:
        return a, a, b
    return b, a, b


def hd():
    try:
        return hub.imu.heading()
    except Exception:
        return 0.0


def square_up(tol, tmax):
    t0 = clock.time()
    while clock.time() - t0 < tmax:
        h = hd()
        if abs(h) < tol:
            break
        c = -1.5 * h * turn_sign
        if c > 45: c = 45
        if c < -45: c = -45
        if 0.0 <= c < 18.0: c = 18.0
        if -18.0 < c < 0.0: c = -18.0
        drive(0, c)
        wait(10)
    halt()
    wait(400)
    lg("sq_head", hd())


def go_back(target):
    t0 = clock.time()
    tl = 0
    while clock.time() - t0 < 7000:
        d, da, db = front()
        if d >= target:
            break
        h = hd()
        c = -0.9 * h * turn_sign
        if c > 15: c = 15
        if c < -15: c = -15
        drive(-70, c)
        t = clock.time()
        if t - tl >= 120:
            lg("fwd_mm", d)
            lg("head_deg", h)
            tl = t
        wait(10)
    halt()
    wait(600)


def s_model(v, sref, vref):
    if vref <= 1.0:
        return sref
    r = v / vref
    if r < 0.5: r = 0.5
    if r > 1.6: r = 1.6
    return sref * r


def settled_dist():
    vals = []
    for i in range(7):
        d, a, b = front()
        vals.append(d)
        wait(25)
    vals.sort()
    return vals[3]


def approach(target, sref, vref, tag):
    global mmpd
    a_start = ang()
    d_start = settled_dist()
    lg(tag + "_d_start", d_start)
    anchor_d = d_start
    anchor_a = a_start
    last_raw = d_start
    fa_d = d_start
    fa_a = a_start
    maxdeg = (d_start - FLOOR) / mmpd
    t0 = clock.time()
    tl1 = 0
    tl2 = 0
    tl3 = 0
    fired = 0
    reason = 0
    d_fire = 0.0
    a_fire = 0.0
    v_fire = 0.0
    while True:
        t = clock.time()
        if t - t0 > 6000:
            reason = 3
            break
        dmin, da, db = front()
        aa = ang()
        if dmin != last_raw and 30 < dmin < 1900:
            anchor_d = dmin
            anchor_a = aa
            last_raw = dmin
        d_est = anchor_d - (aa - anchor_a) * mmpd
        v = spd() * mmpd
        if t - tl1 >= 25:
            lg("fwd_mm", d_est)
            tl1 = t
        if t - tl2 >= 50:
            lg("head_deg", hd())
            tl2 = t
        if t - tl3 >= 150:
            lg("usA", da)
            lg("usB", db)
            tl3 = t
        if (aa - a_start) > maxdeg:
            reason = 2
            break
        if d_est <= FLOOR:
            reason = 1
            break
        if d_est - s_model(v, sref, vref) <= target:
            fired = 1
            d_fire = d_est
            a_fire = aa
            v_fire = v
            fa_d = anchor_d
            fa_a = anchor_a
            reason = 0
            break
        h = hd()
        c = -0.9 * h * turn_sign
        drive_max(c)
        wait(4)
    halt()
    if not fired:
        d_fire = anchor_d - (ang() - anchor_a) * mmpd
        a_fire = ang()
        v_fire = 0.0
        fa_d = anchor_d
        fa_a = anchor_a
    wait(900)
    a_rest = ang()
    d_rest = settled_dist()
    lg(tag + "_target", target)
    lg(tag + "_fired", fired)
    lg(tag + "_reason", reason)
    lg(tag + "_d_fire", d_fire)
    lg(tag + "_v_fire", v_fire)
    lg(tag + "_d_rest", d_rest)
    lg(tag + "_S_sensor", d_fire - d_rest)
    lg(tag + "_S_odo", (a_rest - a_fire) * mmpd)
    lg(tag + "_head_end", hd())
    dcru = fa_a - a_start
    if dcru > 200 and (d_start - fa_d) > 100:
        nm = (d_start - fa_d) / dcru
        if 0.15 < nm < 1.5:
            mmpd = 0.4 * mmpd + 0.6 * nm
    dtot = a_rest - a_start
    if dtot > 200:
        lg(tag + "_mmpd_tot", (d_start - d_rest) / dtot)
    lg(tag + "_mmpd", mmpd)
    return d_rest, d_fire - d_rest, v_fire


def main():
    global mmpd, f0, f1, turn_sign, m0, m1, uA, uB
    wait(700)
    try:
        hub.imu.reset_heading(0)
    except Exception:
        pass

    ports = (Port.A, Port.B, Port.C, Port.D, Port.E, Port.F)
    pn = "ABCDEF"
    mots = []
    uls = []
    cols = []
    for i in range(6):
        p = ports[i]
        got = 0
        try:
            o = Motor(p)
            mots.append(o)
            got = 1
        except Exception:
            pass
        if got == 0:
            try:
                o = UltrasonicSensor(p)
                uls.append(o)
                got = 2
            except Exception:
                pass
        if got == 0:
            try:
                o = ColorSensor(p)
                cols.append(o)
                got = 3
            except Exception:
                pass
        lg("port_" + pn[i], got)
    lg("n_motor", len(mots))
    lg("n_ultra", len(uls))
    lg("n_color", len(cols))
    if len(mots) < 2 or len(uls) < 2:
        lg("ABORT", 1)
        return
    m0 = mots[0]
    m1 = mots[1]
    try:
        m0.reset_angle(0)
        m1.reset_angle(0)
    except Exception:
        pass
    if len(cols) > 0:
        try:
            lg("refl_pct", cols[0].reflection())
        except Exception:
            pass

    nu = len(uls)
    med = []
    for k in range(nu):
        vals = []
        for j in range(7):
            try:
                x = uls[k].distance()
            except Exception:
                x = 2000
            if x <= 0: x = 2000
            vals.append(x)
            wait(12)
        vals.sort()
        med.append(vals[3])
        lg("us%d_med" % k, vals[3])
        lg("us%d_spread" % k, vals[6] - vals[0])

    def usall():
        out = []
        for k in range(nu):
            x = uls[k].distance()
            if x <= 0: x = 2000
            out.append(x)
        return out

    def burst(s0, s1, ms):
        db = usall()
        hb = hd()
        e0 = m0.angle()
        e1 = m1.angle()
        m0.dc(s0)
        m1.dc(s1)
        wait(ms)
        halt()
        wait(600)
        da = usall()
        ha = hd()
        dd = []
        for k in range(nu):
            dd.append(da[k] - db[k])
        return dd, ha - hb, m0.angle() - e0, m1.angle() - e1

    dd1, dh1, p01, p11 = burst(35, 35, 350)
    wait(250)
    dd2, dh2, p02, p12 = burst(35, -35, 350)
    wait(250)
    for k in range(nu):
        lg("t1_dd%d" % k, dd1[k])
        lg("t2_dd%d" % k, dd2[k])
    lg("t1_dh", dh1)
    lg("t2_dh", dh2)
    lg("t1_enc0", p01)
    lg("t1_enc1", p11)
    lg("t2_enc0", p02)
    lg("t2_enc1", p12)

    if abs(dh1) < abs(dh2):
        a0 = 1; a1 = 1
        ddt = dd1; et0 = p01; et1 = p11
        sc0 = 1; sc1 = -1; dhs = dh2
    else:
        a0 = 1; a1 = -1
        ddt = dd2; et0 = p02; et1 = p12
        sc0 = 1; sc1 = 1; dhs = dh1

    neg = []
    pos = []
    for k in range(nu):
        if ddt[k] < -8: neg.append(k)
        if ddt[k] > 8: pos.append(k)
    fr = None
    sgn = 0
    if len(neg) == 2:
        fr = neg; sgn = -1
    elif len(pos) == 2:
        fr = pos; sgn = 1
    if fr is None:
        best = None
        for i in range(nu):
            for j in range(i + 1, nu):
                if med[i] < 1800 and med[j] < 1800:
                    dv = abs(med[i] - med[j])
                    if best is None or dv < best[0]:
                        best = (dv, i, j)
        if best is None:
            lg("ABORT", 2)
            return
        fr = [best[1], best[2]]
        sgn = -1 if (ddt[fr[0]] + ddt[fr[1]]) < 0 else 1
    lg("front_i", fr[0])
    lg("front_j", fr[1])
    lg("front_sgn", sgn)
    uA = uls[fr[0]]
    uB = uls[fr[1]]

    if sgn < 0:
        f0 = a0; f1 = a1
    else:
        f0 = -a0; f1 = -a1
    lg("f0", f0)
    lg("f1", f1)

    dang = (f0 * et0 + f1 * et1) / 2.0
    dfr = (ddt[fr[0]] + ddt[fr[1]]) / 2.0
    if abs(dang) > 20:
        nm = abs(dfr) / abs(dang)
        if 0.15 < nm < 1.5:
            mmpd = nm
    lg("mmpd_init", mmpd)

    w0 = f0 * sc0 * 35.0
    w1 = f1 * sc1 * 35.0
    cs = (w0 - w1) / 2.0
    turn_sign = 1.0 if (dhs * cs) > 0 else -1.0
    lg("turn_sign", turn_sign)
    lg("spin_dh", dhs)

    square_up(1.5, 2500)
    go_back(950)
    square_up(1.5, 2000)
    dump()

    r1, s1, v1 = approach(500.0, 150.0, 0.0, "c1")
    dump()
    go_back(950)
    square_up(1.5, 2000)

    r2, s2, v2 = approach(250.0, s1, v1, "c2")
    dump()
    go_back(950)
    square_up(1.5, 2000)

    sa = (s1 + s2) / 2.0
    va = (v1 + v2) / 2.0
    r3, s3, v3 = approach(150.0, sa, va, "c3")
    lg("park_mm", settled_dist())
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
