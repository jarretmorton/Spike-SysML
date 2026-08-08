# ================= PHASE 1 - CHARACTERIZATION RUN 1 =================
# Self-contained: discovers ports, drive direction, steering sign,
# calibrates mm/deg + ultrasonic zero-gap offsets by stepped approach to
# a gentle touch-off, then performs 3 full-speed dashes with braking to
# measure the effective stopping distance and its repeatability.
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clk = StopWatch()


def em(n, v):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%.2f}\n' % (clk.time(), n, v))


BUF = []
SEG = 0


def rec(a, h):
    if len(BUF) < 1600:
        BUF.append((clk.time(), int(a), int(h * 10), SEG))


def dump(per):
    d = {}
    for r in BUF:
        k = r[3]
        if k in d:
            d[k].append(r)
        else:
            d[k] = [r]
    for k in d:
        L = d[k]
        n = len(L)
        s = n // per + 1
        i = 0
        while i < n:
            r = L[i]
            stdout.write('{"timestamp_ms":%d,"sensor":"dist_fwd","value":%.1f}\n' % (r[0], r[1]))
            stdout.write('{"timestamp_ms":%d,"sensor":"heading","value":%.1f}\n' % (r[0], r[2] * 0.1))
            i += s


# ---------------- S1: port discovery ----------------
PL = (Port.A, Port.B, Port.C, Port.D, Port.E, Port.F)
MOT = []
USS = []
UPT = []
NCS = 0
for i in range(6):
    t = 0
    try:
        MOT.append(Motor(PL[i]))
        t = 1
    except Exception:
        try:
            USS.append(UltrasonicSensor(PL[i]))
            UPT.append(i)
            t = 2
        except Exception:
            try:
                ColorSensor(PL[i])
                NCS += 1
                t = 3
            except Exception:
                t = 0
    em("port%d" % i, t)

em("n_motor", len(MOT))
em("n_ultra", len(USS))
em("n_color", NCS)
em("vbat_mv", hub.battery.voltage())

G1 = 1
G2 = 1
HS = 1
KPD = 2.2
KPR = 9.0
K = 0.45
OF1 = 0.0
OF2 = 0.0
F1 = None
F2 = None
GO = 1

if len(MOT) < 2 or len(USS) < 2:
    GO = 0
    em("abort_code", 1)

for m in MOT:
    try:
        m.control.limits(acceleration=8000)
    except Exception:
        pass


def rd(s):
    try:
        v = s.distance()
    except Exception:
        v = 2000
    return v


def rdavg(s, n):
    t = 0.0
    c = 0
    for i in range(n):
        v = rd(s)
        if 0 < v < 1900:
            t += v
            c += 1
        wait(22)
    if c == 0:
        return 2000.0
    return t / c


def brk():
    for m in MOT:
        m.brake()


def theta():
    return (G1 * MOT[0].angle() + G2 * MOT[1].angle()) * 0.5


def cmd(v, T):
    if T > 0:
        v1 = v
        v2 = v - T
    else:
        v1 = v + T
        v2 = v
    MOT[0].run(G1 * v1)
    MOT[1].run(G2 * v2)


def cmddc(T):
    if T > 0:
        d1 = 100.0
        d2 = 100.0 - T
    else:
        d1 = 100.0 + T
        d2 = 100.0
    MOT[0].dc(G1 * d1)
    MOT[1].dc(G2 * d2)


def trimT(kp, mx):
    T = -kp * hub.imu.heading() * HS
    if T > mx:
        T = mx
    if T < -mx:
        T = -mx
    return T


def gapm(a, b):
    va = 0 < a < 1900
    vb = 0 < b < 1900
    if va and vb:
        return ((a - OF1) + (b - OF2)) * 0.5
    if va:
        return a - OF1
    if vb:
        return b - OF2
    return -1.0


def rawm():
    a = rd(F1)
    b = rd(F2)
    va = 0 < a < 1900
    vb = 0 < b < 1900
    if va and vb:
        return (a + b) * 0.5
    if va:
        return a
    if vb:
        return b
    return -1.0


def reposraw(tgt, tol, tmax):
    t0 = clk.time()
    while clk.time() - t0 < tmax:
        d = rawm()
        if d < 0:
            brk()
            wait(300)
            return -1
        e = d - tgt
        if -tol < e < tol:
            break
        v = 650.0
        if abs(e) < 200:
            v = 300.0
        if abs(e) < 60:
            v = 140.0
        if e < 0:
            v = -v
        cmd(v, trimT(KPR, 120))
        wait(20)
    brk()
    wait(500)
    return 0


def fitk(CAL, idx):
    sx = 0.0
    sy = 0.0
    c = 0
    for p in CAL:
        v = p[idx]
        if 150 < v < 1250:
            sx += p[1]
            sy += v
            c += 1
    if c < 3:
        return -1.0
    mx = sx / c
    my = sy / c
    sxy = 0.0
    sxx = 0.0
    for p in CAL:
        v = p[idx]
        if 150 < v < 1250:
            dx = p[1] - mx
            sxy += dx * (v - my)
            sxx += dx * dx
    if sxx <= 0:
        return -1.0
    return -sxy / sxx


def offs(CAL, idx, thc, kk, lo, hi):
    s = 0.0
    c = 0
    mn = 9e9
    mx = -9e9
    for p in CAL:
        v = p[idx]
        if lo < v < hi:
            o = v - kk * (thc - p[1])
            s += o
            c += 1
            if o < mn:
                mn = o
            if o > mx:
                mx = o
    if c < 2:
        return (0.0, -1.0, 0)
    return (s / c, mx - mn, c)


def dash(trig, tag):
    MOT[0].reset_angle(0)
    MOT[1].reset_angle(0)
    hub.imu.reset_heading(0)
    wait(300)
    pa = rdavg(F1, 6)
    pb = rdavg(F2, 6)
    g0 = gapm(pa, pb)
    em("g0_%d" % tag, g0)
    if g0 < 300:
        em("dashskip_%d" % tag, 1)
        return -1.0
    wall = g0
    nfix = 0
    la = -1.0
    lb = -1.0
    t0 = clk.time()
    lastlog = -100
    ab = 0
    while True:
        el = clk.time() - t0
        if el > 4500:
            ab = 1
            break
        trav = theta() * K
        e = hub.imu.heading()
        T = -KPD * e * HS
        if T > 35:
            T = 35
        if T < -35:
            T = -35
        cmddc(T)
        a = rd(F1)
        b = rd(F2)
        if a != la or b != lb:
            la = a
            lb = b
            g = gapm(a, b)
            if g > 0:
                est = g + trav
                if 250 < g < 830 and -110 < (est - wall) < 110:
                    wall += 0.35 * (est - wall)
                    nfix += 1
        if el - lastlog >= 22:
            lastlog = el
            gg = gapm(a, b)
            rec(gg if gg > 0 else 1999, e)
        if el > 800 and trav < 80:
            ab = 1
            break
        if trav >= wall - trig - 160.0:
            tgt = (wall - trig) / K
            while theta() < tgt:
                if clk.time() - t0 > 4500:
                    ab = 1
                    break
            break
        wait(6)
    thb = theta()
    vb = (G1 * MOT[0].speed() + G2 * MOT[1].speed()) * 0.5
    brk()
    tb = clk.time()
    while clk.time() - tb < 900:
        gg = gapm(rd(F1), rd(F2))
        rec(gg if gg > 0 else 1999, hub.imu.heading())
        wait(14)
    thf = theta()
    fa = rdavg(F1, 6)
    fb = rdavg(F2, 6)
    gf = gapm(fa, fb)
    em("trig_%d" % tag, trig)
    em("wall_%d" % tag, wall)
    em("nfix_%d" % tag, nfix)
    em("tbrake_%d" % tag, tb)
    em("vbrk_dps_%d" % tag, vb)
    em("vbrk_mms_%d" % tag, vb * K)
    em("gfin_us_%d" % tag, gf)
    em("gfin_enc_%d" % tag, g0 - K * thf)
    em("stopdist_%d" % tag, K * (thf - thb))
    em("hend_%d" % tag, hub.imu.heading())
    em("sensdiff_%d" % tag, (fa - OF1) - (fb - OF2))
    em("abort_%d" % tag, ab)
    se = trig - gf
    em("seff_%d" % tag, se)
    return se


def body():
    global G1, G2, HS, K, OF1, OF2, F1, F2, SEG, GO

    # ---------------- S2: drive direction + sensor pairing ----------------
    hub.imu.reset_heading(0)
    wait(400)
    A0 = []
    for s in USS:
        A0.append(rdavg(s, 4))
    h0 = hub.imu.heading()
    MOT[0].run(300)
    MOT[1].run(300)
    wait(450)
    brk()
    wait(500)
    A1 = []
    for s in USS:
        A1.append(rdavg(s, 4))
    h1 = hub.imu.heading()
    em("dh_test1", h1 - h0)
    if abs(h1 - h0) > 12:
        MOT[0].run(300)
        MOT[1].run(-300)
        wait(450)
        brk()
        wait(500)
        A2 = []
        for s in USS:
            A2.append(rdavg(s, 4))
        h2 = hub.imu.heading()
        G2 = -1
        base = A1
        new = A2
        dh = h2 - h1
    else:
        base = A0
        new = A1
        dh = h1 - h0
    em("dh_straight", dh)
    if abs(dh) > 12:
        em("abort_code", 2)
        GO = 0
        return

    n = len(USS)
    dl = []
    for i in range(n):
        dl.append(new[i] - base[i])
        em("us_p%d_start" % UPT[i], A0[i])
        em("us_p%d_delta" % UPT[i], dl[i])
    bi = -1
    bj = -1
    bs = 9e9
    for i in range(n):
        for j in range(i + 1, n):
            if 0 < A0[i] < 1900 and 0 < A0[j] < 1900:
                sc = abs(A0[i] - A0[j]) + abs(dl[i] - dl[j])
                if dl[i] * dl[j] > 0:
                    sc -= 150
                if sc < bs:
                    bs = sc
                    bi = i
                    bj = j
    if bi < 0:
        em("abort_code", 3)
        GO = 0
        return
    F1 = USS[bi]
    F2 = USS[bj]
    em("fwd_port_a", UPT[bi])
    em("fwd_port_b", UPT[bj])
    if dl[bi] + dl[bj] > 0:
        G1 = -G1
        G2 = -G2
    em("G1", G1)
    em("G2", G2)

    # ---------------- S2b: steering sign + rough mm/deg ----------------
    hub.imu.reset_heading(0)
    wait(300)
    MOT[0].reset_angle(0)
    MOT[1].reset_angle(0)
    pa = rdavg(F1, 4)
    pb = rdavg(F2, 4)
    cmd(320, 90)
    wait(500)
    brk()
    wait(500)
    hsv = hub.imu.heading()
    qa = rdavg(F1, 4)
    qb = rdavg(F2, 4)
    dth = theta()
    em("steer_dh", hsv)
    em("conf_da", qa - pa)
    em("conf_db", qb - pb)
    em("conf_dtheta", dth)
    if hsv < 0:
        HS = -1
    else:
        HS = 1
    ok1 = (0 < pa < 1900 and 0 < qa < 1900 and (qa - pa) < -12)
    ok2 = (0 < pb < 1900 and 0 < qb < 1900 and (qb - pb) < -12)
    if (not (ok1 or ok2)) or dth < 20:
        em("abort_code", 4)
        GO = 0
        return
    kk = []
    if ok1:
        kk.append(-(qa - pa) / dth)
    if ok2:
        kk.append(-(qb - pb) / dth)
    tk = 0.0
    for q in kk:
        tk += q
    kr = tk / len(kk)
    em("K_rough", kr)
    if 0.15 < kr < 1.2:
        K = kr

    # ---------------- S3: back to the marked start ----------------
    GST = (A0[bi] + A0[bj]) * 0.5
    em("start_raw", GST)
    reposraw(GST, 8, 7000)

    # ---------------- S4: stepped calibration + touch-off ----------------
    SEG = 1
    MOT[0].reset_angle(0)
    MOT[1].reset_angle(0)
    CAL = []
    for st in range(30):
        a = rdavg(F1, 4)
        b = rdavg(F2, 4)
        t = theta()
        CAL.append((clk.time(), t, a, b))
        rec(a if 0 < a < 1900 else 1999, hub.imu.heading())
        r = -1.0
        if 0 < a < 1900 and 0 < b < 1900:
            r = (a + b) * 0.5
        elif 0 < a < 1900:
            r = a
        elif 0 < b < 1900:
            r = b
        if r < 0 or r < 75:
            break
        if r > 520:
            sp = 700
            ms = 400
        elif r > 260:
            sp = 500
            ms = 330
        elif r > 130:
            sp = 300
            ms = 260
        else:
            sp = 150
            ms = 220
        t0 = clk.time()
        cmd(sp, trimT(KPR, 100))
        bad = 0
        while clk.time() - t0 < ms:
            wait(15)
            if clk.time() - t0 > 190:
                if abs(MOT[0].speed()) < 0.35 * sp and abs(MOT[1].speed()) < 0.35 * sp:
                    bad = 1
                    break
        brk()
        wait(320)
        if bad:
            break
    em("cal_points", len(CAL))

    # gentle creep to contact
    hist = []
    thc = -1.0
    a0t = theta()
    cmd(75, 0)
    wait(300)
    t0 = clk.time()
    while clk.time() - t0 < 6000:
        wait(15)
        th = theta()
        hist.append(th)
        if len(hist) > 7:
            hist.pop(0)
        sp0 = (abs(MOT[0].speed()) + abs(MOT[1].speed())) * 0.5
        if sp0 < 28:
            thc = hist[0]
            break
        if th - a0t > 300:
            break
    brk()
    wait(400)
    em("touch_ok", 1 if thc > 0 else 0)
    em("theta_contact", thc)
    for p in CAL:
        stdout.write('{"timestamp_ms":%d,"sensor":"cal_r1","value":%.1f}\n' % (p[0], p[2]))
        stdout.write('{"timestamp_ms":%d,"sensor":"cal_r2","value":%.1f}\n' % (p[0], p[3]))
        stdout.write('{"timestamp_ms":%d,"sensor":"cal_th","value":%.1f}\n' % (p[0], p[1]))

    if thc > 0:
        k1 = fitk(CAL, 2)
        k2 = fitk(CAL, 3)
        em("K1", k1)
        em("K2", k2)
        kk = []
        if 0.2 < k1 < 1.2:
            kk.append(k1)
        if 0.2 < k2 < 1.2:
            kk.append(k2)
        if len(kk) > 0:
            tk = 0.0
            for q in kk:
                tk += q
            K = tk / len(kk)
        em("K_final", K)
        r1 = offs(CAL, 2, thc, K, 40, 900)
        r2 = offs(CAL, 3, thc, K, 40, 900)
        OF1 = r1[0]
        OF2 = r2[0]
        em("OF1", OF1)
        em("OF1_spread", r1[1])
        em("OF1_n", r1[2])
        em("OF2", OF2)
        em("OF2_spread", r2[1])
        em("OF2_n", r2[2])
        n1 = offs(CAL, 2, thc, K, 40, 320)
        n2 = offs(CAL, 3, thc, K, 40, 320)
        em("OF1_near", n1[0])
        em("OF2_near", n2[0])
    else:
        em("abort_code", 5)

    # back off to the start line
    cmd(-500, 0)
    wait(900)
    brk()
    wait(400)
    reposraw(GST, 8, 10000)

    # ---------------- S5: full-speed dashes ----------------
    trig = 260.0
    for di in range(3):
        SEG = 10 + di
        se = dash(trig, di)
        if 5 < se < 220:
            trig = se + 50.0
        if di < 2:
            reposraw(GST, 8, 10000)


try:
    if GO:
        body()
except Exception as exc:
    em("exception", 1)
    print("EXC:", exc)
finally:
    try:
        for m in MOT:
            m.brake()
    except Exception:
        pass
    try:
        dump(35)
    except Exception:
        pass
    stdout.write('{"event":"end"}\n')
