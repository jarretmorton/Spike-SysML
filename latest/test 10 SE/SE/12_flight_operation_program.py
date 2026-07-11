# ============================================================================
# flight_operation_program.py  —  LOCKED program for the 5 scored operation runs
# (identical to the VER-4 verification program; test-like-you-fly)
#
# Platform: LEGO SPIKE Prime hub, Pybricks MicroPython.
# Task: drive at ~max speed straight at a wall and stop as close as possible
#       without contact.
#
# Control summary (see Verification Report / Final Report for the rationale):
#   - Ports discovered at runtime; front pair = two mutually-closest standoffs;
#     ANCHOR = the larger-baseline front sensor (port A, "us0", the ACCURATE one).
#   - us1 (port B) is DROPPED: it reads ~116 mm short near the wall.
#   - Forward direction verified each run by a low-speed move (anchor must
#     read smaller). Drivetrain is mirror-mounted; forward = (m0 -1, m1 +1).
#   - Straight-line control: cruise command 850 (BELOW the ~880 deg/s
#     saturation, so a wheel can be slowed to steer), IMU proportional
#     steering Kp=25, correction clamp +/-250, ramped launch. Holds heading
#     within ~3 deg.
#   - Stop control is ODOMETRY (lag-free), anchored by a STANDSTILL us0 average:
#         true_start = us0_avg - 16          (offset from the 166 mm operator anchor)
#         pred_gap   = true_start - mean(|dmotor|) * 0.50 mm/deg
#     brake() when pred_gap <= 40 + 13 (target + brake-roll)  ->  ~34-40 mm true.
#   - Safety: hard cap brake if pred_gap <= 25 (lag-free); us0 close backstop;
#     6 s time cap; motors stop in finally; {"event":"end"} flush sentinel.
#
# Result over 5 runs: true gap 35-36 mm (operator-measured), 0 contact, straight.
#
# Telemetry wire contract: one JSON line per event
#   {"timestamp_ms": <hub ms>, "sensor": "<name>", "value": <scalar>}
#   run ends with {"event": "end"}.
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
    try: m.control.limits(speed=1200)
    except Exception: pass
tw = now()
try:
    while (not hub.imu.ready()) and (now() - tw < 3000): wait(50)
except Exception: pass

def rd(u):
    try: return u.distance()
    except Exception: return -1
def rd_avg(u, n=6):
    a = 0; c = 0
    for _ in range(n):
        d = rd(u)
        if d is not None and 0 < d < 2500: a += d; c += 1
        wait(15)
    return (a / c) if c else 9999
def hdg():
    try: return hub.imu.heading()
    except Exception: return 0.0

t = now()
for i,(p,_) in enumerate(uss): emit(t, "meta_us%d_port" % i, PIDX[p])

base = [rd_avg(u, 4) for _, u in uss]
for k in range(len(uss)): emit(now(), "base_us%d" % k, base[k])
front_idx = [0, 1]
if len(uss) >= 3:
    best = (0, 1); bestd = 1e9
    for i in range(len(uss)):
        for j in range(i+1, len(uss)):
            d = abs(base[i] - base[j])
            if d < bestd: bestd = d; best = (i, j)
    front_idx = [best[0], best[1]]
anchor_k = front_idx[0]
if base[front_idx[1]] > base[anchor_k]: anchor_k = front_idx[1]
anchor = uss[anchor_k][1]
emit(now(), "anchor_port", PIDX[uss[anchor_k][0]])

OFFSET = 16
V_SLOW = 200
S_FWD = (-1, 1); S_BWD = (1, -1)
fwd = S_FWD
if m0 is not None and m1 is not None:
    try: hub.imu.reset_heading(0)
    except Exception: pass
    f0 = rd(anchor)
    m0.run(S_FWD[0]*V_SLOW); m1.run(S_FWD[1]*V_SLOW)
    tv = now()
    while now() - tv < 800:
        wait(10)
    m0.brake(); m1.brake(); wait(300)
    f1 = rd(anchor)
    df = (f1 - f0) if (f0 and f1 and f0 > 0 and f1 > 0) else -1
    emit(now(), "verify_anchor_delta", df)
    if df > 0: fwd = S_BWD
    else: fwd = S_FWD
s0f, s1f = fwd
emit(now(), "fwd_sign0", s0f); emit(now(), "fwd_sign1", s1f)

us0_anchor = rd_avg(anchor, 6)
true_start = us0_anchor - OFFSET
emit(now(), "us0_anchor", us0_anchor)
emit(now(), "true_start", true_start)

fast = []
NCAP = 300
TARGET = 40; BROLL = 13; HARD = 25
KP = 25.0; UCLAMP = 250; VBASE = 850
K_ROT = 0.5
t_trig = -1; trig_dist = 0; rest_dist = 0; t_rest = -1
hmax = 0.0
abort = (us0_anchor > 1500 or us0_anchor < 300)

try:
    if abort:
        emit(now(), "marker", 8)
    else:
        try: hub.imu.reset_heading(0)
        except Exception: pass
        a0s = m0.angle(); a1s = m1.angle()
        emit(now(), "marker", 3)
        Vr = 300
        t_app = now(); triggered = False; slow = 0
        while True:
            t = now()
            a0 = m0.angle(); a1 = m1.angle()
            dist = (abs(a0 - a0s) + abs(a1 - a1s)) * 0.5 * K_ROT
            pred = true_start - dist
            da = rd(anchor); h = hdg()
            if abs(h) > hmax: hmax = abs(h)
            if len(fast) < NCAP: fast.append((t, da, a0, dist, h, pred))
            if not triggered:
                if Vr < VBASE:
                    Vr += 25
                    if Vr > VBASE: Vr = VBASE
                u = KP * h
                if u > UCLAMP: u = UCLAMP
                if u < -UCLAMP: u = -UCLAMP
                m0.run(s0f*Vr + u); m1.run(s1f*Vr + u)
            da_gap = (da - OFFSET) if (da is not None and 0 < da < 2500) else 9999
            if (not triggered) and (pred <= TARGET + BROLL or pred <= HARD or da_gap <= 20):
                triggered = True; t_trig = t; trig_dist = dist
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
                    a0 = m0.angle(); a1 = m1.angle()
                    rest_dist = (abs(a0 - a0s) + abs(a1 - a1s)) * 0.5 * K_ROT
                    t_rest = t; break
            if (t - t_app) > 6000:
                m0.brake(); m1.brake()
                a0 = m0.angle(); a1 = m1.angle()
                rest_dist = (abs(a0 - a0s) + abs(a1 - a1s)) * 0.5 * K_ROT
                t_rest = t; emit(t, "marker", 9); break
            wait(8)
        m0.brake(); m1.brake(); emit(now(), "marker", 5)

        tt = now()
        fu = rd_avg(anchor, 5)
        emit(tt, "final_us0", fu)
        emit(tt, "true_rest_us0", fu - OFFSET)
        emit(tt, "odo_final_gap", true_start - rest_dist)
        emit(tt, "trig_dist", trig_dist); emit(tt, "rest_dist", rest_dist)
        emit(tt, "t_trigger_ms", t_trig if t_trig > 0 else 0)
        emit(tt, "t_rest_ms", t_rest if t_rest > 0 else 0)
        emit(tt, "heading_rest", hdg()); emit(tt, "heading_absmax", hmax)
        emit(tt, "n_fast", len(fast))
        for k,(_,u) in enumerate(uss): emit(tt, "endraw_us%d" % k, rd(u))

        n = len(fast); target = 24
        stride = 1 if n <= target else (n // target)
        i = 0
        while i < n:
            (t, da, a0, dist, h, pred) = fast[i]
            emit(t, "us0_read", da); emit(t, "dist", dist)
            emit(t, "heading", h); emit(t, "pred_gap", pred)
            i += stride
        if (n > 0) and ((n - 1) % stride != 0):
            (t, da, a0, dist, h, pred) = fast[n-1]
            emit(t, "us0_read", da); emit(t, "dist", dist)
            emit(t, "heading", h); emit(t, "pred_gap", pred)

    print("OP fwd=%s us0a=%.1f tstart=%.1f trigd=%.1f restd=%.1f n=%d hmax=%.2f hrest=%.2f" %
          (str(fwd), us0_anchor, true_start, trig_dist, rest_dist, len(fast), hmax, hdg()))
finally:
    try: m0.brake()
    except Exception: pass
    try: m1.brake()
    except Exception: pass
    print('{"event": "end"}')
