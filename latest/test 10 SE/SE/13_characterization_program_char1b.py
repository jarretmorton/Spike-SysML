# ============================================================================
# characterization_program_char1b.py  —  CHAR-1b (SPIKE Prime / Pybricks)
# The clean characterization run that fixed CHAR-1's wrong-direction bug and
# established: port map, forward direction, k_rot = 0.50 mm/deg, cruise speed,
# and gross stopping dynamics. Front/rear identified by absolute standoff;
# forward verified by a low-speed move; telemetry kept lean to flush cleanly.
# NOTE: this run triggered on the front pair (us1), later found to read ~116 mm
# short near the wall; the flight program uses us0 + odometry instead.
# ============================================================================
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port, Axis
from pybricks.tools import StopWatch, wait

sw = StopWatch()
def now(): return sw.time()

def emit(t, name, v):
    if isinstance(v, bool): s = "1" if v else "0"
    elif isinstance(v, int): s = "%d" % v
    else: s = "%.3f" % v
    print('{"timestamp_ms": %d, "sensor": "%s", "value": %s}' % (t, name, s))

PORTS = [Port.A, Port.B, Port.C, Port.D, Port.E, Port.F]
PIDX = {Port.A:1, Port.B:2, Port.C:3, Port.D:4, Port.E:5, Port.F:6}
hub = PrimeHub()

motors = []; uss = []; colors = []
for p in PORTS:
    try: motors.append((p, Motor(p))); continue
    except Exception: pass
    try: uss.append((p, UltrasonicSensor(p))); continue
    except Exception: pass
    try: colors.append((p, ColorSensor(p))); continue
    except Exception: pass
for _, m in motors:
    try: m.stop()
    except Exception: pass

m0 = motors[0][1] if len(motors) > 0 else None
m1 = motors[1][1] if len(motors) > 1 else None
for _, m in motors:
    try: m.control.limits(speed=1500)
    except Exception: pass

tw = now()
try:
    while (not hub.imu.ready()) and (now() - tw < 3000): wait(50)
except Exception: pass

def rd(u):
    try: return u.distance()
    except Exception: return -1
def rd_avg(u, n=5):
    acc = 0; c = 0
    for _ in range(n):
        d = rd(u)
        if d is not None and 0 < d < 2500: acc += d; c += 1
        wait(15)
    return (acc / c) if c else 9999
def hdg():
    try: return hub.imu.heading()
    except Exception: return 0.0
def accf(a):
    try: return hub.imu.acceleration(a)
    except Exception: return 0.0

t = now()
for i,(p,_) in enumerate(motors): emit(t, "meta_motor%d_port" % i, PIDX[p])
for i,(p,_) in enumerate(uss):    emit(t, "meta_us%d_port" % i, PIDX[p])
for i,(p,_) in enumerate(colors): emit(t, "meta_color%d_port" % i, PIDX[p])
emit(t, "meta_n_motors", len(motors)); emit(t, "meta_n_us", len(uss))
col = colors[0][1] if colors else None

# ---- front/rear identification by absolute standoff (closest pair = front) ----
base = [rd_avg(u) for _, u in uss]
for k in range(len(uss)): emit(now(), "base_us%d" % k, base[k])
front_idx = [0, 1]; rear_idx = []
if len(uss) >= 3:
    best = (0, 1); bestd = 1e9
    for i in range(len(uss)):
        for j in range(i+1, len(uss)):
            d = abs(base[i] - base[j])
            if d < bestd: bestd = d; best = (i, j)
    front_idx = [best[0], best[1]]
    rear_idx = [k for k in range(len(uss)) if k not in front_idx]
elif len(uss) == 2:
    front_idx = [0, 1]
for k in range(len(uss)): emit(now(), "front_flag_us%d" % k, 1 if k in front_idx else 0)

f_us = [uss[k][1] for k in front_idx]
all_us = [u for _, u in uss]

def front_min():
    vals = []
    for u in f_us:
        d = rd(u)
        if d is not None and 0 < d < 2500: vals.append(d)
    return min(vals) if vals else 9999
def all_min():
    vals = []
    for u in all_us:
        d = rd(u)
        if d is not None and 0 < d < 2500: vals.append(d)
    return min(vals) if vals else 9999

V_SLOW = 200
# ---- verify forward: drive (-1,+1) briefly; forward = front pair DECREASES ----
S_FWD = (-1, 1); S_BWD = (1, -1)
fwd = S_FWD
if m0 is not None and m1 is not None:
    try: hub.imu.reset_heading(0)
    except Exception: pass
    f0 = front_min(); h0 = hdg()
    m0.run(S_FWD[0]*V_SLOW); m1.run(S_FWD[1]*V_SLOW)
    tv = now()
    while now() - tv < 800:
        if all_min() <= 130:
            break
        wait(10)
    m0.brake(); m1.brake(); wait(250)
    f1 = front_min(); h1 = hdg()
    dh = h1 - h0
    while dh > 180: dh -= 360
    while dh < -180: dh += 360
    emit(now(), "verify_front_delta", f1 - f0)
    emit(now(), "verify_heading_delta", dh)
    if (f1 - f0) > 0:      # front pair got FARTHER -> (-1,1) is backward -> flip
        fwd = S_BWD
    else:
        fwd = S_FWD
emit(now(), "fwd_sign0", fwd[0]); emit(now(), "fwd_sign1", fwd[1])

# ---- full-speed approach toward front wall ----
fast = []
NCAP = 300
t_trig = -1; trig_a0 = 0; trig_a1 = 0
rest_a0 = 0; rest_a1 = 0; t_rest = -1
D_TRIG = 300

try:
    try: hub.imu.reset_heading(0)
    except Exception: pass
    s0f, s1f = fwd
    emit(now(), "marker", 3)
    m0.run(s0f*1500); m1.run(s1f*1500)
    t_app = now(); triggered = False; slow = 0
    while True:
        t = now()
        d0 = rd(f_us[0]) if len(f_us) > 0 else -1
        d1 = rd(f_us[1]) if len(f_us) > 1 else -1
        a0 = m0.angle(); a1 = m1.angle()
        ax = accf(Axis.X)
        if len(fast) < NCAP: fast.append((t, d0, d1, a0, a1, ax))
        fvals = [d for d in (d0, d1) if d is not None and 0 < d < 2500]
        fmin = min(fvals) if fvals else 9999
        amin = all_min()
        if (not triggered) and (fmin <= D_TRIG or amin <= 150):
            triggered = True; t_trig = t; trig_a0 = a0; trig_a1 = a1
            m0.brake(); m1.brake(); emit(t, "marker", 4)
        if triggered:
            sp0 = 0; sp1 = 0
            try: sp0 = m0.speed()
            except Exception: pass
            try: sp1 = m1.speed()
            except Exception: pass
            if abs(sp0) < 20 and abs(sp1) < 20: slow += 1
            else: slow = 0
            if slow >= 3 or (t - t_trig) > 1500:
                rest_a0 = a0; rest_a1 = a1; t_rest = t; break
        if (t - t_app) > 6000:
            m0.brake(); m1.brake(); rest_a0 = a0; rest_a1 = a1; t_rest = t
            emit(t, "marker", 9); break
        wait(8)
    m0.brake(); m1.brake(); emit(now(), "marker", 5)

    # scalars (cheap, drain first)
    tt = now()
    for k,(_,u) in enumerate(uss): emit(tt, "final_us%d" % k, rd(u))
    if col is not None:
        try: emit(tt, "final_reflect", col.reflection())
        except Exception: pass
    emit(tt, "trig_a0", trig_a0); emit(tt, "trig_a1", trig_a1)
    emit(tt, "rest_a0", rest_a0); emit(tt, "rest_a1", rest_a1)
    emit(tt, "t_trigger_ms", t_trig if t_trig > 0 else 0)
    emit(tt, "t_rest_ms", t_rest if t_rest > 0 else 0)
    emit(tt, "n_fast", len(fast))

    # downsampled approach dump (~22 rows, 4 channels) -> keeps total lines low
    n = len(fast)
    target = 22
    stride = 1 if n <= target else (n // target)
    i = 0
    while i < n:
        (t, d0, d1, a0, a1, ax) = fast[i]
        emit(t, "us_f0", d0); emit(t, "us_f1", d1)
        emit(t, "m0_ang", a0); emit(t, "acc_x", ax)
        i += stride
    if (n > 0) and ((n - 1) % stride != 0):
        (t, d0, d1, a0, a1, ax) = fast[n-1]
        emit(t, "us_f0", d0); emit(t, "us_f1", d1)
        emit(t, "m0_ang", a0); emit(t, "acc_x", ax)

    print("DONE motors=%d us=%d fwd=%s front=%s trig=%d rest=%d n=%d" %
          (len(motors), len(uss), str(fwd), str(front_idx), t_trig, t_rest, len(fast)))
finally:
    try: m0.brake()
    except Exception: pass
    try: m1.brake()
    except Exception: pass
    print('{"event": "end"}')
