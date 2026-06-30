# =====================================================================
# CHAR-1  —  single batched characterization run
# Self-IDs ports + motor polarity LIVE, takes a stationary noise window,
# then ONE max-speed approach braking at a SAFE 400 mm reported trigger,
# logging distance / heading / speed / accel to rest.
# Telemetry is post-hoc only; the stop is driven by live sensor reads.
# =====================================================================
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

def emit(sensor, value):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n' % (clock.time(), sensor, value))

def end_sentinel():
    stdout.write('{"event":"end"}\n')

# ---------------- constants ----------------
D_TRIGGER = 400.0     # mm  — SAFE characterization trigger (predicted rest ~300mm-class)
PROBE     = 250       # deg/s — low polarity-probe speed (~37 mm per 300 ms pulse)
MAXSP     = 2000      # deg/s target -> clamps to motor ceiling = true max
SAT       = 1900.0    # mm  — "both sensors lost the target" threshold
GUARD_MS  = 2200      # ms  — gross-runaway backstop

PORT_NUM = {Port.A:0, Port.B:1, Port.C:2, Port.D:3, Port.E:4, Port.F:5}
ALL_PORTS = (Port.A, Port.B, Port.C, Port.D, Port.E, Port.F)

# ---------------- port / device identification ----------------
# Try each device type per port; a failed construction does NOT claim the
# port, so we fall through to the next type. First success classifies + claims.
motors = []   # [port, Motor]
ultra  = []   # [port, UltrasonicSensor]
colors = []   # [port, ColorSensor]

for p in ALL_PORTS:
    done = False
    try:
        m = Motor(p); motors.append([p, m]); done = True
    except Exception:
        pass
    if done:
        continue
    try:
        u = UltrasonicSensor(p); ultra.append([p, u]); done = True
    except Exception:
        pass
    if done:
        continue
    try:
        c = ColorSensor(p); colors.append([p, c])
    except Exception:
        pass

def read_u(u):
    try:
        return float(u.distance())
    except Exception:
        return 2000.0

# ---------------- pick the two FORWARD ultrasonics ----------------
# Squared up to a flat wall, the two forward sensors AGREE closely (~start
# distance); the rear sees a different surface. Closest-agreeing pair = forward.
fwdL = None
fwdR = None
rear = None
if len(ultra) >= 2:
    reads = [[it[0], it[1], read_u(it[1])] for it in ultra]
    if len(ultra) == 2:
        fwdL, fwdR = reads[0], reads[1]
    else:
        best = None
        n = len(reads)
        for i in range(n):
            for j in range(i + 1, n):
                diff = abs(reads[i][2] - reads[j][2])
                if best is None or diff < best[0]:
                    best = [diff, i, j]
        i, j = best[1], best[2]
        fwdL, fwdR = reads[i], reads[j]
        for k in range(n):
            if k != i and k != j:
                rear = reads[k]; break

cfg_ok = (len(motors) >= 2) and (fwdL is not None) and (fwdR is not None)
mA = motors[0][1] if len(motors) >= 1 else None
mB = motors[1][1] if len(motors) >= 2 else None
sL = fwdL[1] if fwdL else None
sR = fwdR[1] if fwdR else None

def fwd_read():
    a = read_u(sL); b = read_u(sR)
    return (a if a < b else b), a, b

# raise speed limits so run() targets true max (clamps at motor ceiling)
for it in motors:
    try:
        it[1].control.limits(speed=MAXSP)
    except Exception:
        pass

sgnA, sgnB = 1, 1

try:
    # log discovered config as telemetry numbers (survives stdout truncation)
    emit("cfg_motors", len(motors))
    emit("cfg_ultra", len(ultra))
    emit("cfg_colors", len(colors))
    if fwdL: emit("cfg_fwdL_port", PORT_NUM[fwdL[0]]); emit("cfg_fwdL_d0", fwdL[2])
    if fwdR: emit("cfg_fwdR_port", PORT_NUM[fwdR[0]]); emit("cfg_fwdR_d0", fwdR[2])
    if rear: emit("cfg_rear_port", PORT_NUM[rear[0]]); emit("cfg_rear_d0", rear[2])

    if not cfg_ok:
        print("CFG-FAIL motors=%d ultra=%d colors=%d" % (len(motors), len(ultra), len(colors)))
    else:
        # ---- stationary noise window (~0.5 s) at the start position ----
        t0 = clock.time()
        while clock.time() - t0 < 500:
            mn, dL, dR = fwd_read()
            emit("d_stat_L", dL); emit("d_stat_R", dR)
            wait(10)

        # ---- polarity identification (<=2 probe pulses cover all 4 sign combos) ----
        def pulse(sa, sb, ms):
            d0, _, _ = fwd_read()
            h0 = hub.imu.heading()
            mA.run(sa * PROBE); mB.run(sb * PROBE)
            wait(ms)
            mA.brake(); mB.brake()
            wait(150)
            d1, _, _ = fwd_read()
            h1 = hub.imu.heading()
            return (d1 - d0), (h1 - h0)

        NB, HB = 12.0, 12.0   # mm motion band / deg spin band
        dd, dh = pulse(1, 1, 300)
        if dd < -NB and abs(dh) < HB:
            sgnA, sgnB = 1, 1            # (+,+) drives straight forward
        elif dd > NB and abs(dh) < HB:
            sgnA, sgnB = -1, -1         # (+,+) was straight backward
        else:
            dd2, dh2 = pulse(1, -1, 300)   # opposed wiring -> test other axis
            if dd2 < -NB:
                sgnA, sgnB = 1, -1
            elif dd2 > NB:
                sgnA, sgnB = -1, 1
            else:
                sgnA, sgnB = 1, 1       # ambiguous -> safe default (trigger still 400)
        emit("cfg_sgnA", sgnA); emit("cfg_sgnB", sgnB)
        print("CFG signs=(%d,%d) dd=%d dh=%d" % (sgnA, sgnB, int(dd), int(dh)))

        # ---- max-speed approach ----
        mA.run(sgnA * MAXSP); mB.run(sgnB * MAXSP)
        triggered = False
        sat_n = 0
        g0 = clock.time()
        mn = 2000.0
        while True:
            mn, dL, dR = fwd_read()
            emit("fwd_min", mn); emit("fwd_L", dL); emit("fwd_R", dR)
            emit("yaw", hub.imu.heading())
            try:
                emit("spdA", mA.speed()); emit("spdB", mB.speed())
            except Exception:
                pass
            if mn <= D_TRIGGER:
                triggered = True
                break
            # independent fault check: both sensors lost the target
            if mn >= SAT:
                sat_n += 1
                if sat_n >= 3:
                    break
            else:
                sat_n = 0
            # gross-runaway backstop
            if clock.time() - g0 > GUARD_MS:
                break

        # ---- brake both, back to back (SAME stop method as operation) ----
        mA.brake(); mB.brake()
        emit("event_trigger", mn)

        # ---- settle / log to rest (~0.9 s) ----
        t1 = clock.time()
        while clock.time() - t1 < 900:
            mn, dL, dR = fwd_read()
            emit("fwd_min", mn); emit("yaw", hub.imu.heading())
            try:
                acc = hub.imu.acceleration()
                emit("ax", acc[0]); emit("ay", acc[1]); emit("az", acc[2])
            except Exception:
                pass
            wait(15)
        print("CFG done trig=%d restmin=%d" % (int(triggered), int(mn)))
finally:
    try:
        if mA: mA.brake()
        if mB: mB.brake()
    except Exception:
        pass
    end_sentinel()
