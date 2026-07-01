# =====================================================================
# Run 1 - CALIBRATION program  (single flash, single run)
# ---------------------------------------------------------------------
# Phase 0  enumerate ports (construct each device ONCE, catch failures)
# Phase 1  static: identify forward ranger pair vs rear; noise floor;
#          heading0 reference
# Phase 1.5 low-speed polarity nudge: forward sign per motor via distance
#          feedback (+ heading), confirmed BEFORE ramping to max
# Phase 2  logged MAX-speed approach; SAFE trigger at 500 mm so Run 1
#          cannot touch the wall; brake; keep logging ~1.2 s to rest
#
# Test-like-you-fly: the Phase-2 while-loop (read forward distance ->
# min() -> trigger check -> buffered append -> wait) is IDENTICAL to the
# operation hot loop. Logging is buffered (NOT emitted) in-loop and
# flushed only AFTER the motors stop. try/finally => motors always brake
# and {"event":"end"} (telemetry flush sentinel) is always emitted.
#
# Wire contract: every telemetry sample is one JSON line
#   {"timestamp_ms": <int hub clock>, "sensor": "<name>", "value": <scalar>}
# retrieved per-channel via get_telemetry. Coded channels:
#   portkind{0..5}: 0 empty,1 motor,2 ultrasonic,3 color   (index = A..F)
#   polarity_mode : 0 same_fwd,1 same_rev,2 opp_LposRneg,3 opp_LnegRpos,-1 inconclusive
#   stop_reason   : 0 trigger,1 failsafe_floor,2 failsafe_time
# Port letters map to index via ord(nm)-65 (A=0 .. F=5).
# =====================================================================
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import wait, StopWatch

hub = PrimeHub()
watch = StopWatch()            # hub clock (ms); resets at program start
motors = []                    # defined before try so finally is always safe

def tel(t, name, v, nd=2):
    # one wire-contract telemetry line; skip Nones; round floats
    if v is None:
        return
    if isinstance(v, float):
        v = round(v, nd)
    print('{"timestamp_ms":%d,"sensor":"%s","value":%s}' % (int(t), name, v))

def pidx(nm):
    return ord(nm) - 65        # 'A'->0 ... 'F'->5

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
    n_color = 0
    for p, nm in port_list:
        kind = 0
        try:
            mo = Motor(p); motors.append((nm, mo)); kind = 1
        except Exception:
            try:
                us = UltrasonicSensor(p); ultras.append((nm, us)); kind = 2
            except Exception:
                try:
                    co = ColorSensor(p); n_color += 1; kind = 3
                except Exception:
                    kind = 0
        tel(watch.time(), "portkind" + str(pidx(nm)), kind)
    tel(watch.time(), "n_motor", len(motors))
    tel(watch.time(), "n_ultra", len(ultras))
    tel(watch.time(), "n_color", n_color)

    if len(motors) < 2 or len(ultras) < 2:
        tel(watch.time(), "abort", 1)
        print("SUMMARY abort insufficient_devices m=%d u=%d" % (len(motors), len(ultras)))
    else:
        m1n, m1 = motors[0]
        m2n, m2 = motors[1]

        # =========================================================
        # PHASE 1 - static: forward-pair ID + noise floor
        # (static: emitting live is fine, no hot loop)
        # =========================================================
        N = 20
        means = {}
        for nm, us in ultras:
            s = 0
            for i in range(N):
                d = us.distance()
                tel(watch.time(), "static_" + nm, d)
                s += d
                wait(15)
            means[nm] = s / N
        # forward pair = the two mean readings closest together (both facing
        # the wall ~ start distance); remaining sensor is the rear one.
        names = [nm for nm, _ in ultras]
        best = None; fa = None; fb = None
        i = 0
        while i < len(names):
            j = i + 1
            while j < len(names):
                d = means[names[i]] - means[names[j]]
                if d < 0: d = -d
                if best is None or d < best:
                    best = d; fa = names[i]; fb = names[j]
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
        tel(watch.time(), "fwd_idx_1", pidx(fa))
        tel(watch.time(), "fwd_idx_2", pidx(fb))
        tel(watch.time(), "rear_idx", pidx(rear) if rear else -1)
        tel(watch.time(), "heading0", heading0)

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

        signL = None; signR = None; mode = -1
        dd1, dh1 = nudge(1, 1)
        adh1 = dh1 if dh1 >= 0 else -dh1
        tel(watch.time(), "nudge1_dd", float(dd1))
        tel(watch.time(), "nudge1_dh", float(dh1))
        if adh1 <= ROT_TH:
            if dd1 < -MOVE_TH:
                signL, signR, mode = 1, 1, 0        # both + => forward
            elif dd1 > MOVE_TH:
                signL, signR, mode = -1, -1, 1      # both + => backward; forward is both -
            else:
                mode = -1
        else:
            dd2, dh2 = nudge(1, -1)
            tel(watch.time(), "nudge2_dd", float(dd2))
            tel(watch.time(), "nudge2_dh", float(dh2))
            if dd2 < -MOVE_TH:
                signL, signR, mode = 1, -1, 2
            elif dd2 > MOVE_TH:
                signL, signR, mode = -1, 1, 3
            else:
                mode = -1
        tel(watch.time(), "sign_L", signL if signL is not None else 0)
        tel(watch.time(), "sign_R", signR if signR is not None else 0)
        tel(watch.time(), "polarity_mode", mode)

        if signL is None:
            tel(watch.time(), "abort", 2)
            print("SUMMARY abort polarity_inconclusive")
        else:
            # =====================================================
            # PHASE 2 - logged MAX-speed approach (operation hot loop)
            # =====================================================
            buf = []           # (t, dL, dR, h, aL, aR, spdL, spdR)
            m1.run(signL * CMD_MAX); m2.run(signR * CMD_MAX)
            t0 = watch.time()
            stop_reason = -1; t_trig = -1
            s_trig_actual = None; aL_trig = None; aR_trig = None
            while True:
                t = watch.time() - t0
                dL = f1.distance(); dR = f2.distance()
                dmin = dL if dL < dR else dR
                # ---- CONTROL DECISION FIRST (minimize trigger latency) ----
                if dmin <= S_TRIG_CAL:
                    stop_reason = 0
                elif dmin <= HARD_FLOOR:
                    stop_reason = 1
                elif t >= TIME_CAP:
                    stop_reason = 2
                if stop_reason >= 0:
                    s_trig_actual = dmin
                    aL_trig = m1.angle(); aR_trig = m2.angle(); t_trig = t
                    break
                # ---- LOGGING (buffered, off the emit path) ----
                h = hub.imu.heading()
                aL = m1.angle(); aR = m2.angle()
                sL = m1.speed(); sR = m2.speed()
                buf.append((t, dL, dR, h, aL, aR, sL, sR))
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
                buf.append((t, dL, dR, h, aL, aR, sL, sR))
                wait(10)
            # ---- rest estimate from last 5 samples (on-hub) ----
            tail = buf[-5:] if len(buf) >= 5 else buf
            sr = 0; hr = 0; kk = 0
            for row in tail:
                dd = row[1] if row[1] < row[2] else row[2]
                sr += dd; hr += row[3]; kk += 1
            s_rest = sr / kk; heading_rest = hr / kk
            aL_rest = tail[-1][4]; aR_rest = tail[-1][5]
            # ---- one-shot result channels ----
            tw = watch.time()
            tel(tw, "s_trig_cal", S_TRIG_CAL)
            tel(tw, "stop_reason", stop_reason)
            tel(tw, "t_trigger_ms", t_trig)
            tel(tw, "s_trig_actual", float(s_trig_actual))
            tel(tw, "s_rest", float(s_rest))
            tel(tw, "D_ranger", float(s_trig_actual - s_rest))
            tel(tw, "aL_trig", float(aL_trig))
            tel(tw, "aR_trig", float(aR_trig))
            tel(tw, "aL_rest", float(aL_rest))
            tel(tw, "aR_rest", float(aR_rest))
            tel(tw, "heading_rest", float(heading_rest))
            tel(tw, "n_samples", len(buf))
            # ---- flush buffered Phase-2 time series (off hot path) ----
            for row in buf:
                t = row[0]
                tel(t, "dL", row[1])
                tel(t, "dR", row[2])
                tel(t, "heading", row[3])
                tel(t, "aL", row[4], 1)
                tel(t, "aR", row[5], 1)
                tel(t, "spdL", row[6], 1)
                tel(t, "spdR", row[7], 1)
            print("SUMMARY fwd=%s,%s rear=%s signs=%d,%d mode=%d D_ranger=%.1f s_trig=%.1f s_rest=%.1f stop=%d n=%d" % (
                fa, fb, rear if rear else "-", signL, signR, mode,
                s_trig_actual - s_rest, s_trig_actual, s_rest, stop_reason, len(buf)))
finally:
    # motors ALWAYS stop; sentinel ALWAYS emitted
    try:
        for _nm, _mo in motors:
            _mo.brake()
    except Exception:
        pass
    print('{"event":"end"}')
