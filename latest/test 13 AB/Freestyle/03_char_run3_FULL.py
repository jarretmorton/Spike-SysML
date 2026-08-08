# ================= PHASE 1 - CHARACTERIZATION (run 3) =================
# Known: A,B,E = ultrasonic ; C,D = motors (MIRRORED) ; F = colour.
# Straight line therefore needs OPPOSITE motor signs -> G2 defaults to -1.
# Self-healing: any unintended rotation is undone by face_zero().
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
em("vbat_mv", hub.battery.voltage())

G1 = 1
G2 = -1
HS = 1
KPD = 2.2
KPR = 9.0
K = 0.45
OF1 = 0.0
OF2 = 0.0
F1 = None
F2 = None
RS = None
GO = 1

if len(MOT) < 2 or len(USS) < 3:
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
        if v is None:
            v = 2000
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


# in-place turn back to heading 0.  Measured twice: commanding BOTH motors
# positive yields a NEGATIVE heading change, so e>0 -> +s.  Polarity is
# re-checked on the fly and flipped if the error is not shrinking.
def face_zero(tol, tmax):
    pol = 1.0
    t0 = clk.time()
    e0 = hub.imu.heading()
    chk = 0
    while clk.time() - t0 < tmax:
        e = hub.imu.heading()
        if -tol < e < tol:
            break
        s = 200.0
        if abs(e) < 15:
            s = 90.0
        if e < 0:
            s = -s
        MOT[0].run(pol * s)
        MOT[1].run(pol * s)
        wait(20)
        gd = rawm()
        if 0 < gd < 300:
            em("facezero_guard", gd)
            break
        if chk == 0 and clk.time() - t0 > 500:
            chk = 1
            if abs(hub.imu.heading()) > abs(e0) - 1.0:
                pol = -pol
    brk()
    wait(350)
    em("facezero_res", hub.imu.heading())


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
    if rawm() < 0:
        MOT[0].reset_angle(0)
        MOT[1].reset_angle(0)
        tb = clk.time()
        cmd(-400, 0)
        while clk.time() - tb < 2500:
            wait(20)
            if theta() * K < -200.0:
                break
            if 0 < rd(RS) < 150:
                break
        brk()
        wait(450)
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
            if 0 < rd(RS) < 150:
                brk()
                wait(300)
                em("rear_guard", 1)
                return -2
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


# one short straight probe: returns (dist_change, wheel_deg, heading_change)
def probe(ms):
    MOT[0].reset_angle(0)
    MOT[1].reset_angle(0)
    h0 = hub.imu.heading()
    pa = rdavg(F1, 4)
    pb = rdavg(F2, 4)
    cmd(280, 0)
    wait(ms)
    brk()
    wait(450)
    dh = hub.imu.heading() - h0
    qa = rdavg(F1, 4)
    qb = rdavg(F2, 4)
    ds = 0.0
    nn = 0
    if 0 < pa < 1900 and 0 < qa < 1900:
        ds += qa - pa
        nn += 1
    if 0 < pb < 1900 and 0 < qb < 1900:
        ds += qb - pb
        nn += 1
    if nn == 0:
        return (9e9, theta(), dh)
    return (ds / nn, theta(), dh)


def dash(trig, tag):
    MOT[0].reset_angle(0)
    MOT[1].reset_angle(0)
    wait(250)
    pa = rdavg(F1, 6)
    pb = rdavg(F2, 6)
    g0 = gapm(pa, pb)
    em("g0_%d" % tag, g0)
    em("abdiff_%d" % tag, pa - pb)
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
    em("gfin_A_%d" % tag, fa - OF1)
    em("gfin_B_%d" % tag, fb - OF2)
    em("gfin_enc_%d" % tag, g0 - K * thf)
    em("stopdist_%d" % tag, K * (thf - thb))
    em("hend_%d" % tag, hub.imu.heading())
    em("abort_%d" % tag, ab)
    se = trig - gf
    em("seff_%d" % tag, se)
    return se


def body():
    global G1, G2, HS, K, OF1, OF2, F1, F2, RS, SEG, GO

    if not (len(USS) == 3 and len(MOT) == 2 and UPT[0] == 0 and UPT[1] == 1 and UPT[2] == 4):
        em("abort_code", 6)
        GO = 0
        return
    F1 = USS[0]
    F2 = USS[1]
    RS = USS[2]
    hub.imu.reset_heading(0)
    wait(500)
    pa = rdavg(F1, 6)
    pb = rdavg(F2, 6)
    em("startA", pa)
    em("startB", pb)
    em("startRear", rdavg(RS, 3))
    if not (300 < pa < 1700 and 300 < pb < 1700):
        em("abort_code", 7)
        GO = 0
        return
    GST = (pa + pb) * 0.5
    em("start_raw", GST)

    # ---------------- S2: self-healing direction discovery ----------------
    okdir = 0
    for att in range(4):
        r = probe(380)
        em("pr%d_ds" % att, r[0])
        em("pr%d_dth" % att, r[1])
        em("pr%d_dh" % att, r[2])
        if abs(r[2]) > 10.0:
            # it rotated -> wrong motor pairing.  undo and flip.
            G2 = -G2
            em("pr%d_act" % att, 1)
            face_zero(1.5, 4000)
            continue
        if abs(r[1]) < 30.0:
            em("abort_code", 8)
            GO = 0
            return
        if r[0] < -20.0:
            em("pr%d_act" % att, 0)
            okdir = 1
            break
        if r[0] > 20.0 and r[0] < 8e8:
            G1 = -G1
            G2 = -G2
            em("pr%d_act" % att, 2)
            continue
        em("pr%d_act" % att, 3)
        break
    if okdir == 0:
        em("abort_code", 9)
        GO = 0
        return
    em("G1", G1)
    em("G2", G2)
    K = abs(r[0]) / abs(r[1])
    em("K_rough", K)
    if not (0.15 < K < 1.2):
        K = 0.45
        em("K_forced", 1)

    # ---------------- S2b: steering sign in the final forward frame -------
    face_zero(1.5, 4000)
    MOT[0].reset_angle(0)
    MOT[1].reset_angle(0)
    h0 = hub.imu.heading()
    cmd(300, 90)
    wait(400)
    brk()
    wait(500)
    hsv = hub.imu.heading() - h0
    em("steer_dh", hsv)
    if hsv < 0:
        HS = -1
    else:
        HS = 1
    em("HS", HS)

    # ---------------- S3: square up and return to the start line ----------
    face_zero(1.5, 4000)
    reposraw(GST, 8, 8000)

    # ---------------- S4: stepped calibration + touch-off ----------------
    SEG = 1
    face_zero(1.5, 4000)
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
    lva = -1.0
    lvb = -1.0
    lvt = 0.0
    a0t = theta()
    cmd(75, 0)
    wait(300)
    t0 = clk.time()
    while clk.time() - t0 < 8000:
        wait(15)
        th = theta()
        hist.append(th)
        if len(hist) > 7:
            hist.pop(0)
        ca = rd(F1)
        cb = rd(F2)
        if 0 < ca < 1900:
            lva = ca
            lvt = th
        if 0 < cb < 1900:
            lvb = cb
        sp0 = (abs(MOT[0].speed()) + abs(MOT[1].speed())) * 0.5
        if sp0 < 28:
            thc = hist[0]
            break
        if th - a0t > 420:
            break
    brk()
    wait(400)
    em("creep_lastA", lva)
    em("creep_lastB", lvb)
    em("creep_lastTh", lvt)
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

    # back off toward the start line
    cmd(-500, 0)
    wait(900)
    brk()
    wait(400)
    if reposraw(GST, 8, 10000) < 0:
        em("abort_code", 10)
        return

    # ---------------- S5: staged full-speed dashes ----------------
    trig = 260.0
    s1 = -1.0
    s2 = -1.0
    for di in range(3):
        SEG = 10 + di
        face_zero(1.2, 4000)
        se = dash(trig, di)
        if di == 0:
            s1 = se
            if 5 < se < 220:
                trig = se + 90.0
        elif di == 1:
            s2 = se
            if 5 < se < 220 and abs(s2 - s1) < 15:
                trig = (s1 + s2) * 0.5 + 45.0
            elif 5 < se < 220:
                trig = se + 90.0
        if di < 2:
            if reposraw(GST, 8, 10000) < 0:
                break


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
