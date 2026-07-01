# =====================================================================
# Run 1 - CALIBRATION program  (single flash, single run)
# ---------------------------------------------------------------------
# Phase 0  enumerate ports (construct each device ONCE, catch failures)
# Phase 1  static: identify forward ranger pair vs rear; noise floor;
#          heading0; accel(gravity) reference
# Phase 1.5 low-speed polarity nudge: forward sign per motor via distance
#          feedback (+ heading), confirmed BEFORE ramping to max
# Phase 2  logged MAX-speed approach; SAFE trigger at 500 mm so Run 1
#          cannot touch the wall; brake; keep logging ~1.2 s to rest
#
# Test-like-you-fly: the Phase-2 while-loop (read forward distance ->
# min() -> trigger check -> buffered append -> wait) is IDENTICAL to the
# operation hot loop. Logging is buffered (not printed) in-loop and
# dumped only AFTER the motors stop. try/finally => motors always brake
# and {"event":"end"} is always emitted (telemetry flush sentinel).
#
# Emits JSON lines with hub-clock timestamps (ms). Reads-back are done
# off-board via get_telemetry (downsampled). Nothing here is hard-coded
# about ports or polarity - all discovered.
# =====================================================================
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port, Axis
from pybricks.tools import wait, StopWatch

hub = PrimeHub()
watch = StopWatch()            # hub clock (ms); resets at program start
motors = []                    # defined before try so finally is always safe

def emit(s):
    print(s)

def r(x, n=1):                 # round that tolerates None (accel may fail)
    if x is None:
        return None
    return round(x, n)

def jn(x):                     # JSON number / null
    if x is None:
        return "null"
    return str(x)

# ---- SAFE calibration constants ----
S_TRIG_CAL = 500               # mm SAFE trigger (reaches max speed; big buffer to wall)
HARD_FLOOR = 300               # mm failsafe if primary trigger is missed
TIME_CAP   = 5000              # ms failsafe from approach start
NUDGE_SPD  = 150               # deg/s low-speed polarity nudge
NUDGE_MS   = 350               # ms per nudge sub-test
ROT_TH     = 8                 # deg |heading change| above this => rotating (motors opposed)
MOVE_TH    = 15                # mm |distance change| above this => real translation
CMD_MAX    = 2000              # deg/s large command => clamps to motor ceiling

try:
    # =============================================================
    # PHASE 0 - enumerate ports (each device constructed once)
    # =============================================================
    port_list = [(Port.A, "A"), (Port.B, "B"), (Port.C, "C"),
                 (Port.D, "D"), (Port.E, "E"), (Port.F, "F")]
    ultras = []
    colors = []
    kinds = []                 # (name, kind) in port order
    for p, nm in port_list:
        kind = "empty"
        try:
            mo = Motor(p); motors.append((nm, mo)); kind = "motor"
        except Exception:
            try:
                us = UltrasonicSensor(p); ultras.append((nm, us)); kind = "ultrasonic"
            except Exception:
                try:
                    co = ColorSensor(p); colors.append((nm, co)); kind = "color"
                except Exception:
                    kind = "empty"
        kinds.append((nm, kind))
    pm = ""
    for nm, kind in kinds:
        if pm:
            pm += ","
        pm += '"%s":"%s"' % (nm, kind)
    emit('{"event":"portmap","ports":{%s},"n_motor":%d,"n_ultra":%d,"n_color":%d}'
         % (pm, len(motors), len(ultras), len(colors)))

    if len(motors) < 2 or len(ultras) < 2:
        emit('{"event":"abort","reason":"need >=2 motors and >=2 ultrasonics"}')
    else:
        m1n, m1 = motors[0]
        m2n, m2 = motors[1]

        # =========================================================
        # PHASE 1 - static: forward-pair ID + noise floor
        # =========================================================
        N = 20
        means = {}; mins = {}; maxs = {}
        for nm, us in ultras:
            s = 0; mn = 100000; mx = -1
            for i in range(N):
                d = us.distance()
                s += d
                if d < mn: mn = d
                if d > mx: mx = d
                wait(15)
            means[nm] = s / N; mins[nm] = mn; maxs[nm] = mx
        # forward pair = the two mean readings closest together (both ~ start dist,
        # facing the wall); the remaining sensor is the rear one.
        names = [nm for nm, _ in ultras]
        best_diff = None; fa = None; fb = None
        i = 0
        while i < len(names):
            j = i + 1
            while j < len(names):
                d = means[names[i]] - means[names[j]]
                if d < 0: d = -d
                if best_diff is None or d < best_diff:
                    best_diff = d; fa = names[i]; fb = names[j]
                j += 1
            i += 1
        rear = None
        for nm in names:
            if nm != fa and nm != fb:
                rear = nm; break
        f1 = None; f2 = None
        for nm, us in ultras:
            if nm == fa: f1 = us
            if nm == fb: f2 = us
        heading0 = hub.imu.heading()
        try:
            g0x = hub.imu.acceleration(Axis.X)
            g0y = hub.imu.acceleration(Axis.Y)
            g0z = hub.imu.acceleration(Axis.Z)
        except Exception:
            g0x = g0y = g0z = None
        sm = ""; smn = ""; smx = ""
        for nm in names:
            if sm:
                sm += ","; smn += ","; smx += ","
            sm  += '"%s":%s' % (nm, jn(r(means[nm], 1)))
            smn += '"%s":%s' % (nm, jn(mins[nm]))
            smx += '"%s":%s' % (nm, jn(maxs[nm]))
        emit('{"event":"phase1","forward":["%s","%s"],"rear":%s,"means":{%s},"min":{%s},"max":{%s},"heading0":%s,"accel0":[%s,%s,%s]}'
             % (fa, fb, ('"%s"' % rear) if rear else "null", sm, smn, smx,
                jn(r(heading0, 2)), jn(r(g0x, 0)), jn(r(g0y, 0)), jn(r(g0z, 0))))

        def fwd_dist():
            a = f1.distance(); b = f2.distance()
            return a if a < b else b

        # =========================================================
        # PHASE 1.5 - polarity nudge (find forward sign pair)
        # =========================================================
        def nudge(sL, sR):
            d0 = fwd_dist(); h0 = hub.imu.heading()
            m1.run(sL * NUDGE_SPD); m2.run(sR * NUDGE_SPD)
            wait(NUDGE_MS)
            m1.brake(); m2.brake()
            wait(250)
            return (fwd_dist() - d0, hub.imu.heading() - h0)

        signL = None; signR = None; mode = "none"
        dd1, dh1 = nudge(1, 1)
        adh1 = dh1 if dh1 >= 0 else -dh1
        dd2 = None; dh2 = None
        if adh1 <= ROT_TH:
            if dd1 < -MOVE_TH:
                signL, signR, mode = 1, 1, "same_forward"
            elif dd1 > MOVE_TH:
                signL, signR, mode = -1, -1, "same_reverse"
            else:
                mode = "inconclusive_t1"
        else:
            dd2, dh2 = nudge(1, -1)
            if dd2 < -MOVE_TH:
                signL, signR, mode = 1, -1, "opposed_LposRneg"
            elif dd2 > MOVE_TH:
                signL, signR, mode = -1, 1, "opposed_LnegRpos"
            else:
                mode = "inconclusive_t2"
        emit('{"event":"phase15","t1":{"dd":%s,"dh":%s},"t2":{"dd":%s,"dh":%s},"signL":%s,"signR":%s,"mode":"%s"}'
             % (jn(r(dd1, 1)), jn(r(dh1, 2)), jn(r(dd2, 1)), jn(r(dh2, 2)),
                jn(signL), jn(signR), mode))

        if signL is None:
            emit('{"event":"abort","reason":"polarity_inconclusive"}')
        else:
            # =====================================================
            # PHASE 2 - logged MAX-speed approach (operation hot loop)
            # =====================================================
            buf = []           # (t,dL,dR,h,aL,aR,spdL,spdR,ax,ay,az)
            m1.run(signL * CMD_MAX); m2.run(signR * CMD_MAX)
            t0 = watch.time()
            stop_reason = "none"; t_trig = -1
            s_trig_actual = None; aL_trig = None; aR_trig = None
            while True:
                t = watch.time() - t0
                dL = f1.distance(); dR = f2.distance()
                dmin = dL if dL < dR else dR
                # ---- CONTROL DECISION FIRST (minimize trigger latency) ----
                if dmin <= S_TRIG_CAL:
                    stop_reason = "trigger"
                elif dmin <= HARD_FLOOR:
                    stop_reason = "failsafe_floor"
                elif t >= TIME_CAP:
                    stop_reason = "failsafe_time"
                if stop_reason != "none":
                    s_trig_actual = dmin
                    aL_trig = m1.angle(); aR_trig = m2.angle(); t_trig = t
                    break
                # ---- LOGGING (buffered, off the print path) ----
                h = hub.imu.heading()
                aL = m1.angle(); aR = m2.angle()
                sL = m1.speed(); sR = m2.speed()
                try:
                    ax = hub.imu.acceleration(Axis.X)
                    ay = hub.imu.acceleration(Axis.Y)
                    az = hub.imu.acceleration(Axis.Z)
                except Exception:
                    ax = ay = az = None
                buf.append((t, dL, dR, h, aL, aR, sL, sR, ax, ay, az))
                wait(5)
            # ---- STOP: brake = short, repeatable, no reverse creep ----
            m1.brake(); m2.brake()
            # ---- keep logging ~1.2 s to capture coast-to-rest ----
            settle_until = (watch.time() - t0) + 1200
            while (watch.time() - t0) < settle_until:
                t = watch.time() - t0
                dL = f1.distance(); dR = f2.distance()
                h = hub.imu.heading()
                aL = m1.angle(); aR = m2.angle()
                sL = m1.speed(); sR = m2.speed()
                try:
                    ax = hub.imu.acceleration(Axis.X)
                    ay = hub.imu.acceleration(Axis.Y)
                    az = hub.imu.acceleration(Axis.Z)
                except Exception:
                    ax = ay = az = None
                buf.append((t, dL, dR, h, aL, aR, sL, sR, ax, ay, az))
                wait(10)
            # ---- rest estimate from last 5 samples ----
            tail = buf[-5:] if len(buf) >= 5 else buf
            sr = 0; hr = 0; kk = 0
            for row in tail:
                dd = row[1] if row[1] < row[2] else row[2]
                sr += dd; hr += row[3]; kk += 1
            s_rest = sr / kk; heading_rest = hr / kk
            aL_rest = tail[-1][4]; aR_rest = tail[-1][5]
            emit('{"event":"phase2_meta","s_trig_cal":%d,"stop_reason":"%s","t_trigger_ms":%s,"s_trig_actual":%s,"s_rest":%s,"D_ranger":%s,"aL_trig":%s,"aR_trig":%s,"aL_rest":%s,"aR_rest":%s,"heading_rest":%s,"n_samples":%d}'
                 % (S_TRIG_CAL, stop_reason, jn(t_trig),
                    jn(r(s_trig_actual, 1)), jn(r(s_rest, 1)), jn(r(s_trig_actual - s_rest, 1)),
                    jn(r(aL_trig, 1)), jn(r(aR_trig, 1)), jn(r(aL_rest, 1)), jn(r(aR_rest, 1)),
                    jn(r(heading_rest, 2)), len(buf)))
            # ---- dump buffer (off hot path; motors already stopped) ----
            for row in buf:
                emit('{"t":%s,"dL":%s,"dR":%s,"h":%s,"aL":%s,"aR":%s,"spdL":%s,"spdR":%s,"ax":%s,"ay":%s,"az":%s}'
                     % (jn(row[0]), jn(row[1]), jn(row[2]), jn(r(row[3], 2)),
                        jn(r(row[4], 1)), jn(r(row[5], 1)), jn(r(row[6], 1)), jn(r(row[7], 1)),
                        jn(r(row[8], 0)), jn(r(row[9], 0)), jn(r(row[10], 0))))
finally:
    # motors ALWAYS stop; sentinel ALWAYS emitted
    try:
        for _nm, _mo in motors:
            _mo.brake()
    except Exception:
        pass
    emit('{"event":"end"}')
