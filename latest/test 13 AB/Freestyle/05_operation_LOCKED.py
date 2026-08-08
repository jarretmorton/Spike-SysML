# ================= OPERATION PROGRAM (LOCKED) =================
# Wall approach at maximum speed (dc 100) with braking stop.
#
# Calibrated in characterisation run 3:
#   ports  A,B,E = ultrasonic ; C,D = motors (mirrored) ; F = colour
#   forward = MOT[0](C) negative, MOT[1](D) positive
#   steering sign HS = +1 ; cruise scale K = 0.492 mm per encoder degree
#   sensor A reads the true bumper gap directly (intercept +0.9..+5.6 -> OFA 3.0)
#   sensor B is NOT used: it reads erratically below ~500 mm
#   braking distance ~12 mm ; sensor lag bias ~24.5 mm
#   trigger offset C = -36.6 mm measured over a 3-point sweep
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clk = StopWatch()

# ---- locked constants ----
G1 = -1
G2 = 1
HS = 1
K = 0.492
OFA = 3.0
KPD = 8.0
TMAX = 40.0
FIXLO = 65.0
FIXHI = 900.0
MARGIN = 45.0
EMA = 0.30
REJ = 90.0
TRIGS = [60.0]
AIM3 = 40.0


def em(n, v):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%.2f}\n' % (clk.time(), n, v))


BUF = []
SEG = 0


def rec(a, h):
    if len(BUF) < 1500:
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


# ---- port discovery + verification ----
PL = (Port.A, Port.B, Port.C, Port.D, Port.E, Port.F)
MOT = []
USS = []
UPT = []
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
                t = 3
            except Exception:
                t = 0
    em("port%d" % i, t)

em("vbat_mv", hub.battery.voltage())
GO = 1
if not (len(MOT) == 2 and len(USS) == 3 and UPT[0] == 0 and UPT[1] == 1 and UPT[2] == 4):
    GO = 0
    em("abort_code", 6)

F1 = USS[0] if len(USS) > 0 else None
F2 = USS[1] if len(USS) > 1 else None
RS = USS[2] if len(USS) > 2 else None

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


def rdA(n):
    t = 0.0
    c = 0
    for i in range(n):
        v = rd(F1)
        if 0 < v < 1900:
            t += v
            c += 1
        wait(20)
    if c == 0:
        return -1.0
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


def face_zero(tol, tmax):
    pol = 1.0
    t0 = clk.time()
    e0 = hub.imu.heading()
    chk = 0
    while clk.time() - t0 < tmax:
        e = hub.imu.heading()
        if -tol < e < tol:
            break
        s = 180.0
        if abs(e) < 15:
            s = 85.0
        if e < 0:
            s = -s
        MOT[0].run(pol * s)
        MOT[1].run(pol * s)
        wait(20)
        g = rd(F1)
        if 0 < g < 300:
            break
        if chk == 0 and clk.time() - t0 > 500:
            chk = 1
            if abs(hub.imu.heading()) > abs(e0) - 1.0:
                pol = -pol
    brk()
    wait(350)


def repos(tgt, tol, tmax):
    if rd(F1) >= 1900:
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
        d = rd(F1)
        if not (0 < d < 1900):
            brk()
            wait(300)
            return -1
        e = d - tgt
        if -tol < e < tol:
            break
        v = 620.0
        if abs(e) < 200:
            v = 300.0
        if abs(e) < 60:
            v = 140.0
        if e < 0:
            v = -v
            if 0 < rd(RS) < 150:
                brk()
                wait(300)
                return -2
        T = -6.0 * hub.imu.heading() * HS
        if T > 100:
            T = 100
        if T < -100:
            T = -100
        cmd(v, T)
        wait(20)
    brk()
    wait(500)
    return 0


def dash(trig, tag):
    MOT[0].reset_angle(0)
    MOT[1].reset_angle(0)
    wait(250)
    a0 = rdA(8)
    g0 = a0 - OFA
    em("g0_%d" % tag, g0)
    if not (300.0 < g0 < 1400.0):
        em("dashskip_%d" % tag, 1)
        return (-9e9, 0.0)
    wall = g0
    nfix = 0
    la = -1.0
    lfg = -1.0
    lft = 0.0
    hmax = 0.0
    ab = 0
    lastlog = -100
    t0 = clk.time()
    while True:
        el = clk.time() - t0
        if el > 4500:
            ab = 1
            break
        th = theta()
        trav = th * K
        e = hub.imu.heading()
        if el > 400 and abs(e) > hmax:
            hmax = abs(e)
        T = -KPD * e * HS
        if T > TMAX:
            T = TMAX
        if T < -TMAX:
            T = -TMAX
        cmddc(T)
        a = rd(F1)
        if a != la:
            la = a
            if 0 < a < 1900:
                g = a - OFA
                if FIXLO < g < FIXHI:
                    est = g + trav
                    if -REJ < (est - wall) < REJ:
                        wall += EMA * (est - wall)
                        nfix += 1
                        lfg = g
                        lft = th
        if el - lastlog >= 20:
            lastlog = el
            rec(a if 0 < a < 1900 else 1999, e)
        if el > 600 and trav < 60.0:
            ab = 2
            break
        if el > 600 and 0 < a < 1900 and (a - OFA) > g0 + 40.0:
            ab = 3
            break
        if trav >= wall - trig - MARGIN:
            tg = (wall - trig) / K
            while theta() < tg:
                if clk.time() - t0 > 4500:
                    ab = 1
                    break
            break
        wait(5)
    thb = theta()
    vb = (G1 * MOT[0].speed() + G2 * MOT[1].speed()) * 0.5
    brk()
    tb = clk.time()
    while clk.time() - tb < 800:
        rec(rd(F1), hub.imu.heading())
        wait(14)
    thf = theta()
    af = rdA(8)
    dl = wall - g0
    gs = af - OFA if af > 0 else -1.0
    gdr = lfg - dl - K * (thf - lft) if lfg > 0 else -1.0
    em("trig_%d" % tag, trig)
    em("wall_%d" % tag, wall)
    em("lag_%d" % tag, dl)
    em("nfix_%d" % tag, nfix)
    em("vbrk_%d" % tag, vb)
    em("vmms_%d" % tag, vb * K)
    em("thb_%d" % tag, thb)
    em("thf_%d" % tag, thf)
    em("brake_enc_%d" % tag, K * (thf - thb))
    em("lastfix_g_%d" % tag, lfg)
    em("lastfix_th_%d" % tag, lft)
    em("afin_%d" % tag, af)
    em("gfin_sensor_%d" % tag, gs)
    em("gfin_dr_%d" % tag, gdr)
    em("hmax_%d" % tag, hmax)
    em("hend_%d" % tag, hub.imu.heading())
    em("abort_%d" % tag, ab)
    ref = gdr
    if gs > 55.0:
        ref = gs
    em("gfin_%d" % tag, ref)
    em("C_%d" % tag, ref - trig)
    return (ref - trig, ref)


def body():
    global SEG
    hub.imu.reset_heading(0)
    wait(500)
    a0 = rdA(8)
    em("startA", a0)
    em("startRear", rd(RS))
    if not (850.0 < a0 < 1200.0):
        em("abort_code", 7)
        return
    tgt = a0
    cs = []
    for i in range(len(TRIGS)):
        tr = TRIGS[i]
        if tr < 0:
            if len(cs) < 2:
                break
            c = (cs[0] + cs[1]) * 0.5
            if abs(cs[0] - cs[1]) > 12.0:
                em("C_inconsistent", abs(cs[0] - cs[1]))
                break
            tr = AIM3 - c
            if tr < 5.0:
                tr = 5.0
            em("trig_auto", tr)
        SEG = 10 + i
        face_zero(1.2, 4000)
        r = dash(tr, i)
        if r[0] > -8e8:
            cs.append(r[0])
        if i < len(TRIGS) - 1:
            if repos(tgt, 8, 10000) < 0:
                em("repos_fail", i)
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
        dump(30)
    except Exception:
        pass
    stdout.write('{"event":"end"}\n')
