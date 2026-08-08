# =============================================================================
# R-CAL v1.0 - Wall-Approach Rover characterization program (Pybricks)
# Strict superset of the operation skeleton: identical tick (read -> validate
# -> fuse/DR -> trigger -> actuate), buffered logging off the hot path,
# sentinel guaranteed under finally. Onboard safety logic uses WORST-CASE
# prior edges only (never nominal guesses).
# Stages: S0 census+static | S1 sign ladder | S2..S4 full-speed brake events
# (reverse-runway recovery between) | S5 creep to near-wall | S6 dump.
# =============================================================================
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

# ---- worst-case prior edges (CP-WAR v1.0 section 4.2) ----------------------
O_MAX = 50            # mm   offset upper edge
TAU_MAX = 80          # ms   US data-age upper edge
TCH_MAX = 35          # ms   reaction-chain upper edge
A_MIN = 1500          # mm/s^2 braking decel lower edge
K_HI = 1.0            # mm/deg odometry upper edge (0.0573 m/rad)
K_LO = 0.30           # mm/deg odometry lower edge
# ---- run constants ----------------------------------------------------------
LOOP_MS = 10
BUF_EVERY = 2
NBUF = 1300
V_CMD = 2000          # deg/s target; controller clamps to physical ceiling
PULSE_SP = 250        # deg/s S1 pulses
CREEP_SP = 150        # deg/s S5 creep
REV_SP = 700          # deg/s reverse recovery
THR2 = 600            # mm raw trigger, segment 2 (worst-case rest >= 245)
THR3 = 500            # mm raw trigger, segment 3 (worst-case rest >= 145)
S4_FLOOR = 120        # mm raw floor for adaptive segment 4
CREEP_THR = 90        # mm raw trigger, creep (worst-case rest >= ~21)
REV_RAW = 950         # mm raw reverse-recovery target (never behind start)
US_LO = 25            # mm validity window
US_HI = 1600
STALE_CAP = 250       # ms staleness ceiling
REST_DPS = 8          # deg/s "at rest" threshold

# ---- telemetry --------------------------------------------------------------
EMITN = [0]

def emit(sensor, value):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'
                 % (clock.time(), sensor, value))
    EMITN[0] += 1

def emit_at(ts, sensor, value):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'
                 % (ts, sensor, value))
    EMITN[0] += 1

def median(xs):
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return -1
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) // 2

# ---- ring buffer (pre-allocated; no I/O on hot path) ------------------------
B_t = [0] * NBUF
B_a = [0] * NBUF
B_b = [0] * NBUF
B_r = [0] * NBUF
B_al = [0] * NBUF
B_ar = [0] * NBUF
B_h = [0] * NBUF
B_s = [0] * NBUF
BI = [0]              # write index
OVF = [0]

def buf(t, ua, ub, ur, al, ar, h10, st):
    i = BI[0]
    if i >= NBUF:
        OVF[0] = 1
        return
    B_t[i] = t; B_a[i] = ua; B_b[i] = ub; B_r[i] = ur
    B_al[i] = al; B_ar[i] = ar; B_h[i] = h10; B_s[i] = st
    BI[0] = i + 1

# ---- device state ------------------------------------------------------------
DEV = {"mot": [], "rng": [], "col": [], "map": [0] * 6}
CFG = {"s0": 0, "s1": 0, "front": [], "rear": -1, "yawsign0": 0,
       "u_est": 60, "call_ms": 3}
EVT = []              # (name, t, v) event records
SUM = []              # (name, value) summary records
FLAGS = {"abort": 0, "hot": 0, "stale_ep": 0, "leak": 0}
WIN = []              # (t_lo, t_hi) full-res emit windows

def note(name, v):
    SUM.append((name, float(v)))

def event(name, v):
    EVT.append((name, clock.time(), float(v)))

class Abort(Exception):
    pass

# ---- S0: census + static -----------------------------------------------------
def s0_census():
    ports = [Port.A, Port.B, Port.C, Port.D, Port.E, Port.F]
    for i in range(6):
        p = ports[i]
        try:
            m = Motor(p); DEV["mot"].append(m); DEV["map"][i] = 1
            continue
        except OSError:
            pass
        try:
            s = UltrasonicSensor(p); DEV["rng"].append(s); DEV["map"][i] = 2
            continue
        except OSError:
            pass
        try:
            c = ColorSensor(p); DEV["col"].append(c); DEV["map"][i] = 3
            continue
        except OSError:
            DEV["map"][i] = 0
    if len(DEV["mot"]) != 2 or len(DEV["rng"]) != 3 or len(DEV["col"]) != 1:
        event("abort_census", len(DEV["mot"]) * 100
              + len(DEV["rng"]) * 10 + len(DEV["col"]))
        raise Abort()

def s0_static():
    t0 = clock.time()
    samp = [[], [], []]
    chint = [[], [], []]
    last = [-1, -1, -1]
    lastt = [t0, t0, t0]
    callms = [0, 0, 0]
    ncall = 0
    h0 = hub.imu.heading()
    hmax = 0.0
    while clock.time() - t0 < 2000:
        for j in range(3):
            ta = clock.time()
            d = DEV["rng"][j].distance()
            tb = clock.time()
            callms[j] += (tb - ta)
            if d != last[j]:
                if last[j] >= 0:
                    chint[j].append(tb - lastt[j])
                last[j] = d
                lastt[j] = tb
            if len(samp[j]) < 80:
                samp[j].append(d)
        ncall += 1
        hd = hub.imu.heading() - h0
        if hd < 0:
            hd = -hd
        if hd > hmax:
            hmax = hd
        wait(4)
    meds = [median(samp[j]) for j in range(3)]
    for j in range(3):
        dev = sorted([abs(x - meds[j]) for x in samp[j]])
        mad = dev[len(dev) // 2] if dev else -1
        u = median(chint[j]) if len(chint[j]) >= 3 else 999
        note("s0.us%d_med" % j, meds[j])
        note("s0.us%d_mad" % j, mad)
        note("s0.us%d_uint" % j, u)
        note("s0.us%d_call" % j, callms[j] / max(1, ncall))
    note("s0.imu_drift_x10", hmax * 10)
    try:
        note("s0.batt_mv", hub.battery.voltage())
    except AttributeError:
        note("s0.batt_mv", -1)
    # provisional front pair: prefer in-window medians, else closest pair
    inw = [j for j in range(3) if 600 <= meds[j] <= 1400]
    if len(inw) == 2:
        CFG["front"] = inw
    else:
        best = (99999, 0, 1)
        for a in range(3):
            for b in range(a + 1, 3):
                d = abs(meds[a] - meds[b])
                if d < best[0]:
                    best = (d, a, b)
        CFG["front"] = [best[1], best[2]]
    for j in range(3):
        if j not in CFG["front"]:
            CFG["rear"] = j
    CFG["u_all"] = [median(chint[j]) if len(chint[j]) >= 3 else 60
                    for j in range(3)]
    us = [CFG["u_all"][j] for j in CFG["front"]]
    CFG["u_est"] = min(120, max(15, median(us) if us else 60))
    CFG["samp_gap"] = max(25, min(60, CFG["u_est"]))
    CFG["s0"] = 1
    note("s0.ok", 1)

# ---- helpers -----------------------------------------------------------------
def front_read():
    a = DEV["rng"][CFG["front"][0]].distance()
    b = DEV["rng"][CFG["front"][1]].distance()
    return a, b

def front_med5():
    va, vb = [], []
    for _ in range(5):
        a, b = front_read()
        va.append(a); vb.append(b)
        wait(12)
    return median(va), median(vb)

def hold_all():
    for m in DEV["mot"]:
        m.hold()

def stop_all():
    for m in DEV["mot"]:
        try:
            m.stop()
        except Exception:
            pass

# ---- S1: sign ladder ----------------------------------------------------------
def all_med5():
    # 7 samples spaced by ~half the measured US update interval (>=25 ms):
    # spans >=4 distinct sensor updates so the median rejects glitches
    gp = CFG.get("samp_gap", 25)
    v0, v1, v2 = [], [], []
    for _ in range(7):
        v0.append(DEV["rng"][0].distance())
        v1.append(DEV["rng"][1].distance())
        v2.append(DEV["rng"][2].distance())
        wait(gp)
    return [median(v0), median(v1), median(v2)]

def pulse(s0, s1, sp, ms):
    m0 = all_med5()
    h0 = hub.imu.heading()
    DEV["mot"][0].run(s0 * sp)
    DEV["mot"][1].run(s1 * sp)
    wait(ms)
    hold_all()
    wait(250)
    m1 = all_med5()
    dh = hub.imu.heading() - h0
    return [m1[0] - m0[0], m1[1] - m0[1], m1[2] - m0[2]], dh

def s1_signs():
    # per-ranger motion classification: the two rangers that DECREASE
    # together under a translation ARE the front pair (definitionally),
    # and the commanded signs are forward; two INCREASING -> front pair,
    # signs reversed. Robust to the rear scene aliasing the wall range.
    resolved = False
    for attempt in range(2):
        ms = 300 if attempt == 0 else 450
        for hy in ((1, 1), (1, -1)):
            d, dh = pulse(hy[0], hy[1], PULSE_SP, ms)
            event("s1_d0", d[0])
            event("s1_d1", d[1])
            event("s1_d2", d[2])
            event("s1_dh_x10", dh * 10)
            if dh > 6 or dh < -6:
                continue  # rotation pulse: cannot classify translation
            dec = [j for j in range(3) if -400 <= d[j] <= -12]
            inc = [j for j in range(3) if 12 <= d[j] <= 400]
            if len(dec) == 2:
                CFG["front"] = dec
                CFG["sL"], CFG["sR"] = hy[0], hy[1]
                resolved = True
            elif len(inc) == 2:
                CFG["front"] = inc
                CFG["sL"], CFG["sR"] = -hy[0], -hy[1]
                resolved = True
            if resolved:
                break
        if resolved:
            break
    if not resolved:
        event("abort_signs", 0)
        raise Abort()
    CFG["rear"] = -1
    for j in range(3):
        if j not in CFG["front"]:
            CFG["rear"] = j
    us = [CFG["u_all"][j] for j in CFG["front"]]
    CFG["u_est"] = min(120, max(15, median(us) if us else 60))
    # identity pulse: motor0 solo, forward -> yaw sign for trim mapping
    h0 = hub.imu.heading()
    DEV["mot"][0].run(CFG["sL"] * PULSE_SP)
    wait(250)
    hold_all()
    wait(200)
    dh = hub.imu.heading() - h0
    CFG["yawsign0"] = 1 if dh > 1.5 else (-1 if dh < -1.5 else 0)
    note("s1.yawsign0", CFG["yawsign0"])
    # confirmation creep on the derived fronts (glitch-aware, one retry)
    f0 = CFG["front"][0]
    f1 = CFG["front"][1]
    confirmed = False
    for c in range(2):
        d, dh = pulse(CFG["sL"], CFG["sR"], PULSE_SP, 300)
        event("s1_conf0", d[f0])
        event("s1_conf1", d[f1])
        if abs(d[f0]) > 400 or abs(d[f1]) > 400:
            continue  # glitched median: retry
        if d[f0] <= -6 and d[f1] <= -6:
            confirmed = True
            break
    if not confirmed:
        event("abort_confirm", d[f0])
        raise Abort()
    CFG["s1"] = 1
    note("s1.sL", CFG["sL"])
    note("s1.sR", CFG["sR"])
    note("s1.front0", f0)
    note("s1.front1", f1)
    note("s1.ok", 1)

# ---- shared drive tick machinery (operation skeleton) --------------------------
class Drive:
    def __init__(self):
        self.m0 = DEV["mot"][0]
        self.m1 = DEV["mot"][1]
        self.r0 = DEV["rng"][CFG["front"][0]]
        self.r1 = DEV["rng"][CFG["front"][1]]
        self.rr = DEV["rng"][CFG["rear"]] if CFG["rear"] >= 0 else None
        self.stale_ms = max(120, 3 * CFG["u_est"])
        self.reset_fix(2000)

    def reset_fix(self, raw):
        self.fixraw = raw
        self.fixang = self.avg_ang()
        self.la = -1; self.lb = -1
        self.lta = clock.time(); self.ltb = clock.time()

    def avg_ang(self):
        return (self.m0.angle() * (1 if CFG["sL"] > 0 else -1)
                + self.m1.angle() * (1 if CFG["sR"] > 0 else -1)) // 2

    def sense(self):
        t = clock.time()
        a = self.r0.distance()
        b = self.r1.distance()
        r = self.rr.distance() if self.rr else -1
        if a != self.la:
            self.la = a; self.lta = t
        if b != self.lb:
            self.lb = b; self.ltb = t
        va = (US_LO <= a <= US_HI) and (t - self.lta <= self.stale_ms)
        vb = (US_LO <= b <= US_HI) and (t - self.ltb <= self.stale_ms)
        raw = -1
        if va and vb:
            raw = a if a < b else b
        elif va:
            raw = a
        elif vb:
            raw = b
        ang = self.avg_ang()
        if raw > 0:
            self.fixraw = raw
            self.fixang = ang
            fused = raw
        else:
            fused = self.fixraw - int(K_HI * (ang - self.fixang))
        return t, a, b, r, ang, fused, (1 if raw > 0 else 0)

DR = [None]

def tick_wait(next_t):
    d = next_t - clock.time()
    late = -d if d < 0 else 0
    if d > 0:
        wait(d)
    return next_t + LOOP_MS, late

# ---- full-speed brake segment ---------------------------------------------------
def segment(segid, thr):
    dv = DR[0]
    dv.reset_fix(2000)
    t0 = clock.time()
    dv.m0.run(CFG["sL"] * V_CMD)
    dv.m1.run(CFG["sR"] * V_CMD)
    nxt = clock.time() + LOOP_MS
    n = 0
    start_f = -1
    sp_hist = []
    jit_max = 0
    plateau = 0
    trig = None
    h_start = hub.imu.heading()
    while True:
        t, a, b, r, ang, fused, fresh = dv.sense()
        s0 = dv.m0.speed(); s1 = dv.m1.speed()
        w = (abs(s0) + abs(s1)) // 2
        sp_hist.append(w)
        if len(sp_hist) > 30:
            sp_hist.pop(0)
            lo = min(sp_hist); hi = max(sp_hist)
            if hi > 200 and (hi - lo) * 100 <= 6 * hi:
                plateau = 1
        if start_f < 0 and fresh:
            start_f = fused
        if n == 40 and start_f < 0:
            event("abort_no_us", segid)
            hold_all()
            raise Abort()
        if n % BUF_EVERY == 0:
            buf(t, a, b, r, dv.m0.angle(), dv.m1.angle(),
                int(hub.imu.heading() * 10), segid * 10 + 1)
        if n == 60 and start_f > 0 and fused > start_f - 15:
            event("abort_progress", segid)
            hold_all()
            raise Abort()
        if fused <= thr:
            vtrig = w
            trig = (t, a, b, fused, w, ang)
            hold_all()
            tcmd = clock.time()
            break
        if t - t0 > 6000:
            event("abort_seg_timeout", segid)
            hold_all()
            raise Abort()
        n += 1
        nxt, late = tick_wait(nxt)
        if late > jit_max:
            jit_max = late
    # braking watch (full-rate buffering) + contact-witness arm (CMP-I2)
    onset = -1
    restt = -1
    calm = 0
    amax = 0
    while True:
        t, a, b, r, ang, fused, fresh = dv.sense()
        s0 = abs(dv.m0.speed()); s1 = abs(dv.m1.speed())
        buf(t, a, b, r, dv.m0.angle(), dv.m1.angle(),
            int(hub.imu.heading() * 10), segid * 10 + 2)
        try:
            ac = hub.imu.acceleration()
            am = abs(ac[0]) + abs(ac[1])
            if am > amax:
                amax = am
        except Exception:
            amax = -1
        if onset < 0 and (s0 + s1) // 2 < (vtrig * 85) // 100:
            onset = t
        if s0 < REST_DPS and s1 < REST_DPS:
            calm += 1
            if calm >= 3:
                restt = t
                break
        else:
            calm = 0
        if t - tcmd > 2500:
            restt = t
            break
        wait(LOOP_MS)
    # rest window
    ra, rb, rr = [], [], []
    ang_r0 = dv.avg_ang()
    tw = clock.time()
    while clock.time() - tw < 900:
        a, bb = front_read()
        ra.append(a); rb.append(bb)
        if dv.rr:
            rr.append(dv.rr.distance())
        wait(45)
    ang_r1 = dv.avg_ang()
    rest_a = median(ra); rest_b = median(rb)
    rest_raw = rest_a if rest_a < rest_b else rest_b
    db_raw = trig[3] - rest_raw
    h_end = hub.imu.heading()
    WIN.append((trig[0] - 250, restt + 150))
    pre = "seg%d." % segid
    note(pre + "thr", thr)
    note(pre + "trig_t", trig[0])
    note(pre + "trig_a", trig[1])
    note(pre + "trig_b", trig[2])
    note(pre + "trig_fused", trig[3])
    note(pre + "trig_w_dps", trig[4])
    note(pre + "plateau", plateau)
    note(pre + "onset_ms", (onset - tcmd) if onset > 0 else -1)
    note(pre + "rest_t", restt)
    note(pre + "rest_a", rest_a)
    note(pre + "rest_b", rest_b)
    note(pre + "rest_r", median(rr) if rr else -1)
    note(pre + "db_raw", db_raw)
    note(pre + "db_encdeg", abs(dv.avg_ang() - trig[5]))
    note(pre + "creep_deg", abs(ang_r1 - ang_r0))
    note(pre + "dh_x10", (h_end - h_start) * 10)
    note(pre + "jit_max", jit_max)
    note(pre + "amax", amax)
    return trig[4], db_raw, rest_raw, plateau

# ---- reverse-runway recovery ------------------------------------------------------
def reverse(rest_raw, start_raw):
    dv = DR[0]
    tgt = REV_RAW
    if start_raw > 0 and start_raw - 30 < tgt:
        tgt = start_raw - 30
    if tgt - rest_raw < 120:
        return rest_raw
    dv.m0.run(-CFG["sL"] * REV_SP)
    dv.m1.run(-CFG["sR"] * REV_SP)
    ang0 = dv.avg_ang()
    cap_deg = int((tgt - rest_raw + 120) / K_LO)
    t0 = clock.time()
    lastraw = rest_raw
    lastup = t0
    n = 0
    while True:
        t, a, b, r, ang, fused, fresh = dv.sense()
        raw = fused if fresh else -1
        if n % BUF_EVERY == 0:
            buf(t, a, b, r, dv.m0.angle(), dv.m1.angle(),
                int(hub.imu.heading() * 10), 5)
        if raw > 0:
            if raw > lastraw + 5:
                lastraw = raw
                lastup = t
            if raw >= tgt:
                break
        if abs(ang - ang0) >= cap_deg:
            break
        if dv.rr:
            rd = dv.rr.distance()
            if US_LO <= rd < 140:
                event("rev_rear_block", rd)
                break
        if t - lastup > 900:
            event("rev_stall", lastraw)
            break
        if t - t0 > 3500:
            break
        n += 1
        wait(LOOP_MS)
    hold_all()
    wait(300)
    a, b = front_med5()
    return a if a < b else b

# ---- creep to near-wall -------------------------------------------------------------
def creep():
    dv = DR[0]
    dv.m0.run(CFG["sL"] * CREEP_SP)
    dv.m1.run(CFG["sR"] * CREEP_SP)
    t0 = clock.time()
    cfix_raw = -1
    cfix_ang = 0
    cmin = 100000
    blind = 0
    tmo = 0
    n = 0
    tc = -1
    gear_hi = 0
    tlimit = 9000
    while True:
        t, a, b, r, ang, fused, fresh = dv.sense()
        if n % BUF_EVERY == 0:
            buf(t, a, b, r, dv.m0.angle(), dv.m1.angle(),
                int(hub.imu.heading() * 10), 6)
        # plausibility-gated local fix: a fresh reading may only refresh the
        # fix if it is not implausibly HIGHER than the best seen (near-range
        # garbage defeat); implausibly-low readings are accepted (fail-early).
        if fresh:
            if fused <= cmin + 25:
                cfix_raw = fused
                cfix_ang = ang
                if fused < cmin:
                    cmin = fused
        if cfix_raw > 0:
            eff = cfix_raw - int(K_HI * (ang - cfix_ang))
            travel_blind = int(K_HI * (ang - cfix_ang))
        else:
            eff = 100000
            travel_blind = 0
        if n == 50 and cfix_raw < 0:
            event("abort_creep_no_us", 0)
            hold_all()
            raise Abort()
        if eff < 100000 and tlimit == 9000:
            tlimit = 3000 + 25 * (eff - CREEP_THR)
            if tlimit > 25000:
                tlimit = 25000
            if tlimit < 4000:
                tlimit = 4000
        # two gears: far away, close in faster (still gentle); near, creep
        if eff < 100000:
            g = 1 if eff > 300 else 0
            if g != gear_hi:
                gear_hi = g
                sp = 450 if g else CREEP_SP
                dv.m0.run(CFG["sL"] * sp)
                dv.m1.run(CFG["sR"] * sp)
        if eff <= CREEP_THR:
            hold_all()
            tc = clock.time()
            break
        if travel_blind > 55:
            blind = 1
            event("s5_blind_stop", eff)
            hold_all()
            tc = clock.time()
            break
        if t - t0 > tlimit:
            tmo = 1
            event("s5_timeout_stop", eff)
            hold_all()
            tc = clock.time()
            break
        n += 1
        wait(LOOP_MS)
    note("s5.timeout", tmo)
    note("s5.blind", blind)
    amax = 0
    ta = clock.time()
    while clock.time() - ta < 400:
        try:
            ac = hub.imu.acceleration()
            am = abs(ac[0]) + abs(ac[1])
            if am > amax:
                amax = am
        except Exception:
            amax = -1
            break
        wait(20)
    note("s5.amax", amax)
    ra, rb, rr = [], [], []
    ang0 = dv.avg_ang()
    tw = clock.time()
    while clock.time() - tw < 1500:
        a, b = front_read()
        ra.append(a); rb.append(b)
        if dv.rr:
            rr.append(dv.rr.distance())
        wait(40)
    note("s5.rest_a", median(ra))
    note("s5.rest_b", median(rb))
    note("s5.rest_r", median(rr) if rr else -1)
    note("s5.n_rest", len(ra))
    note("s5.creep_deg", abs(dv.avg_ang() - ang0))
    WIN.append((tc - 350, tc + 150))

# ---- dump ----------------------------------------------------------------------------
def in_win(t):
    for lo, hi in WIN:
        if lo <= t <= hi:
            return True
    return False

def dump():
    td0 = clock.time()
    emit("rcal.version", 1.0)
    for i in range(6):
        emit("cfg.port%d" % i, DEV["map"][i])
    emit("cfg.front0", CFG["front"][0] if CFG["front"] else -1)
    emit("cfg.front1", CFG["front"][1] if len(CFG["front"]) > 1 else -1)
    emit("cfg.rear", CFG["rear"])
    emit("cfg.sL", CFG.get("sL", 0))
    emit("cfg.sR", CFG.get("sR", 0))
    emit("cfg.u_est", CFG["u_est"])
    for name, v in SUM:
        emit(name, v)
    for name, t, v in EVT:
        emit_at(t, "evt." + name, v)
    emit("rcal.buf_rows", BI[0])
    emit("rcal.buf_ovf", OVF[0])
    # series keys: ua/ub/ur=front A,B + rear ultrasonic mm; el/er=encoders
    # deg; em=encoder mean deg; hd=heading deci-deg; st=stage code
    n = BI[0]
    i = 0
    while i < n:
        t = B_t[i]
        w = in_win(t)
        if w:
            emit_at(t, "ua", B_a[i])
            emit_at(t, "ub", B_b[i])
            emit_at(t, "el", B_al[i])
            emit_at(t, "er", B_ar[i])
            if i % 2 == 0:
                emit_at(t, "hd", B_h[i])
            if i % 4 == 0:
                emit_at(t, "ur", B_r[i])
                emit_at(t, "st", B_s[i])
        elif i % 8 == 0:
            emit_at(t, "ua", B_a[i])
            emit_at(t, "ub", B_b[i])
            emit_at(t, "em", (B_al[i] + B_ar[i]) // 2)
            if i % 24 == 0:
                emit_at(t, "hd", B_h[i])
                emit_at(t, "st", B_s[i])
        i += 1
    emit("rcal.emit_lines", EMITN[0])
    emit("rcal.dump_ms", clock.time() - td0)

# ---- main -----------------------------------------------------------------------------
def main():
    s0_census()
    s0_static()
    s1_signs()
    DR[0] = Drive()
    a, b = front_med5()
    start_raw = a if a < b else b
    note("start_raw", start_raw)
    v2, db2, rest2, pl2 = segment(2, THR2)
    raw = reverse(rest2, start_raw)
    note("rev1_raw", raw)
    v3, db3, rest3, pl3 = segment(3, THR3)
    dbs = []
    if pl2:
        dbs.append(db2)
    if pl3:
        dbs.append(db3)
    vhi = max(v2, v3)  # dps; K_HI=1.0 -> mm/s upper bound
    do_s4 = (len(dbs) >= 1
             and (len(dbs) < 2 or abs(db2 - db3) <= 20))
    if do_s4:
        thr4 = S4_FLOOR + O_MAX + (vhi * (TAU_MAX + TCH_MAX)) // 1000 \
               + (3 * max(dbs)) // 2
        raw = reverse(rest3, start_raw)
        note("rev2_raw", raw)
        if raw - thr4 >= 200:
            v4, db4, rest4, pl4 = segment(4, thr4)
        else:
            note("s4.skipped_runway", thr4)
    else:
        note("s4.skipped_db", len(dbs))
    creep()
    note("run.ok", 1)

try:
    try:
        main()
    except Abort:
        FLAGS["abort"] = 1
        note("run.abort", 1)
    except Exception as e:
        FLAGS["abort"] = 2
        note("run.exc", 1)
finally:
    try:
        hold_all()
    except Exception:
        pass
    try:
        dump()
    except Exception:
        pass
    try:
        wait(1500)
        stop_all()
    except Exception:
        pass
    stdout.write('{"event":"end"}\n')
