# Characterization run 1 of 4 — DISCOVERY
#
# Nothing about the rover's wiring or drive convention was known. This single program:
#   1. scans all six ports, trying Motor -> UltrasonicSensor -> ColorSensor on each
#   2. resolves the drivetrain convention from IMU rotation during motor pulses
#   3. identifies the forward sensor pair by which readings move together
#   4. runs a slow segment then a full-speed segment, then brakes at 500 mm
#
# Derived on-hub (to keep telemetry small): mm-per-motor-degree, sensor lag by a
# two-speed offset method, braking distance, sensor update rate, straightness.
#
# FINDINGS: motors on C/D (mirrored), ultrasonics on A/B (forward) and E (rear),
# colour sensor on F. Toward-wall = C negative, D positive. Heading collapsed -18 deg
# in 1 s at full speed (speed controller saturated). Ports A and B cross-talk.

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

def emit(s, v):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n' % (clock.time(), s, v))

PN = ("A", "B", "C", "D", "E", "F")
PP = (Port.A, Port.B, Port.C, Port.D, Port.E, Port.F)

mot = []; mport = []
uss = []; uport = []
col = []; cport = []
kind = [0, 0, 0, 0, 0, 0]

for i in range(6):
    ok = 0
    try:
        d = Motor(PP[i]); mot.append(d); mport.append(i); kind[i] = 1; ok = 1
    except Exception:
        pass
    if ok == 0:
        try:
            d = UltrasonicSensor(PP[i]); uss.append(d); uport.append(i); kind[i] = 2; ok = 1
        except Exception:
            pass
    if ok == 0:
        try:
            d = ColorSensor(PP[i]); col.append(d); cport.append(i); kind[i] = 3; ok = 1
        except Exception:
            pass

for i in range(6):
    emit("port_kind_" + PN[i], kind[i])
emit("n_motor", len(mot))
emit("n_ultra", len(uss))
emit("n_color", len(col))

LOG = []

try:
    if len(mot) < 2 or len(uss) < 2:
        emit("fatal_scan", 1)
    else:
        m0 = mot[0]; m1 = mot[1]
        nu = len(uss)
        try:
            emit("motor_speed_limit", m0.control.limits()[0])
        except Exception:
            pass
        try:
            m0.control.limits(acceleration=6000)
            m1.control.limits(acceleration=6000)
        except Exception:
            pass

        def snap():
            return [u.distance() for u in uss]

        wait(300)
        base = snap()
        for k in range(nu):
            emit("base_u%d_port%d" % (k, uport[k]), base[k])

        # Each probe drives, measures, then reverses to return to the start pose.
        def probe(a, b, ms):
            h0 = hub.imu.heading()
            d0 = snap()
            m0.run(a); m1.run(b)
            wait(ms)
            m0.brake(); m1.brake()
            wait(350)
            dh = hub.imu.heading() - h0
            d1 = snap()
            dd = [d1[k] - d0[k] for k in range(nu)]
            m0.run(-a); m1.run(-b)
            wait(ms)
            m0.brake(); m1.brake()
            wait(350)
            return dh, dd

        # Probe 1: same-sign. Large heading change => motors are mirrored.
        dh1, dd1 = probe(300, 300, 400)
        emit("probe1_dheading", dh1)
        for k in range(nu):
            emit("probe1_dd_u%d" % k, dd1[k])

        if abs(dh1) > 12:
            sB = -1
            dh2, dd2 = probe(300, -300, 400)
            emit("probe2_dheading", dh2)
            for k in range(nu):
                emit("probe2_dd_u%d" % k, dd2[k])
            dd = dd2
        else:
            sB = 1
            dd = dd1
        emit("sign_B", sB)

        # Forward pair = the two sensors whose deltas agree and whose baselines agree.
        best = 1e12; bi = 0; bj = 1
        for i in range(nu):
            for j in range(i + 1, nu):
                sc = abs(dd[i] - dd[j]) + 0.5 * abs(base[i] - base[j])
                if sc < best:
                    best = sc; bi = i; bj = j
        emit("fwd_idx_a", bi)
        emit("fwd_idx_b", bj)
        emit("fwd_port_a", uport[bi])
        emit("fwd_port_b", uport[bj])

        mean_dd = 0.5 * (dd[bi] + dd[bj])
        emit("fwd_mean_delta", mean_dd)
        drive_sign = 1 if mean_dd < 0 else -1
        emit("drive_sign", drive_sign)

        uf0 = uss[bi]; uf1 = uss[bj]
        sgnA = drive_sign
        sgnB = drive_sign * sB

        wait(300)
        m0.reset_angle(0); m1.reset_angle(0)
        h_ref = hub.imu.heading()

        V_SLOW = 300
        V_MAX = 1200
        D_FAST = 820
        D_BRAKE = 500

        def drv(v):
            m0.run(sgnA * v); m1.run(sgnB * v)

        t0 = clock.time()
        drv(V_SLOW)
        phase = 0
        i_fast = -1
        i_brake = -1
        far_count = 0
        abort = 0

        while True:
            t = clock.time() - t0
            d0v = uf0.distance()
            d1v = uf1.distance()
            ep = (sgnA * m0.angle() + sgnB * m1.angle()) // 2
            hd = hub.imu.heading() - h_ref
            LOG.append((t, d0v, d1v, ep, int(hd * 10)))
            f = d0v if d0v < d1v else d1v

            if phase == 0:
                if f > 1400:
                    far_count += 1
                    if far_count > 4:
                        abort = 1
                else:
                    far_count = 0
                if abs(hd) > 30:
                    abort = 2
                if t > 7000:
                    abort = 3
                if abort:
                    m0.hold(); m1.hold()
                    i_brake = len(LOG) - 1
                    phase = 2
                    t_brake = t
                elif f < D_FAST:
                    drv(V_MAX)
                    i_fast = len(LOG) - 1
                    phase = 1
            elif phase == 1:
                if abs(hd) > 30:
                    abort = 2
                if t > 7000:
                    abort = 3
                if f < D_BRAKE or abort:
                    m0.hold(); m1.hold()
                    i_brake = len(LOG) - 1
                    t_brake = t
                    phase = 2
            else:
                if t - t_brake > 1600:
                    break
            wait(6)

        m0.brake(); m1.brake()
        emit("abort_code", abort)
        emit("i_fast", i_fast)
        emit("i_brake", i_brake)
        emit("n_log", len(LOG))

        n = len(LOG)
        fin = min(20, n)
        sd0 = 0.0; sd1 = 0.0; sep = 0.0
        for k in range(n - fin, n):
            sd0 += LOG[k][1]; sd1 += LOG[k][2]; sep += LOG[k][3]
        f0f = sd0 / fin; f1f = sd1 / fin; epf = sep / fin
        emit("final_d0", f0f)
        emit("final_d1", f1f)
        emit("final_heading", LOG[n - 1][4] / 10.0)

        mmpd = 0.0
        if i_fast > 20:
            ia = 0
            for k in range(i_fast):
                if LOG[k][0] > 450:
                    ia = k; break
            ib2 = i_fast - 1
            de = LOG[ib2][3] - LOG[ia][3]
            du = (LOG[ia][1] + LOG[ia][2]) - (LOG[ib2][1] + LOG[ib2][2])
            du = du / 2.0
            if de > 5:
                mmpd = du / de
            dt = LOG[ib2][0] - LOG[ia][0]
            emit("cal_mm_per_deg", mmpd)
            emit("cal_span_deg", de)
            emit("cal_span_mm", du)
            if dt > 0:
                emit("v_slow_degs", de * 1000.0 / dt)
                emit("v_slow_mms", du * 1000.0 / dt)

        if i_brake > 0 and i_fast > 0 and mmpd > 0:
            tb = LOG[i_brake][0]
            ka = i_fast
            for k in range(i_fast, i_brake):
                if LOG[k][0] >= tb - 220:
                    ka = k; break
            dtf = LOG[i_brake][0] - LOG[ka][0]
            def_ = LOG[i_brake][3] - LOG[ka][3]
            vfd = 0.0; vfm = 0.0
            if dtf > 0:
                vfd = def_ * 1000.0 / dtf
                vfm = vfd * mmpd
            emit("v_fast_degs", vfd)
            emit("v_fast_mms", vfm)

            # Two-speed lag: offset = d_us + mmpd*epos is constant at constant speed,
            # and differs between the slow and fast segments by tau * delta_v.
            oS = 0.0; cS = 0
            for k in range(n):
                if LOG[k][0] > 450 and k < i_fast:
                    oS += 0.5 * (LOG[k][1] + LOG[k][2]) + mmpd * LOG[k][3]; cS += 1
            oF = 0.0; cF = 0
            for k in range(ka, i_brake + 1):
                oF += 0.5 * (LOG[k][1] + LOG[k][2]) + mmpd * LOG[k][3]; cF += 1
            if cS > 0 and cF > 0:
                oS = oS / cS; oF = oF / cF
                emit("offset_slow_mm", oS)
                emit("offset_fast_mm", oF)
                dts = LOG[i_fast - 1][0] - LOG[0][0]
                dvv = vfm - (mmpd * (LOG[i_fast - 1][3] - LOG[0][3]) * 1000.0 / dts if dts > 0 else 0)
                if dvv > 30:
                    emit("lag_ms_two_speed", (oF - oS) * 1000.0 / dvv)

            emit("d_us_at_brake", 0.5 * (LOG[i_brake][1] + LOG[i_brake][2]))
            emit("brake_travel_mm", (epf - LOG[i_brake][3]) * mmpd)
            emit("brake_travel_deg", epf - LOG[i_brake][3])
            emit("heading_at_brake", LOG[i_brake][4] / 10.0)

            te = tb; tu = tb
            for k in range(i_brake, n):
                if abs(LOG[k][3] - epf) > 2:
                    te = LOG[k][0]
                if abs(0.5 * (LOG[k][1] + LOG[k][2]) - 0.5 * (f0f + f1f)) > 6:
                    tu = LOG[k][0]
            emit("t_enc_stop_ms", te - tb)
            emit("t_us_stop_ms", tu - tb)
            emit("lag_ms_settle", tu - te)

            ch0 = 0; ch1 = 0
            for k in range(i_fast + 1, i_brake + 1):
                if LOG[k][1] != LOG[k - 1][1]:
                    ch0 += 1
                if LOG[k][2] != LOG[k - 1][2]:
                    ch1 += 1
            dtp = LOG[i_brake][0] - LOG[i_fast][0]
            if dtp > 0:
                emit("us0_hz", ch0 * 1000.0 / dtp)
                emit("us1_hz", ch1 * 1000.0 / dtp)
                emit("loop_hz", (i_brake - i_fast) * 1000.0 / dtp)

        step = 3
        for k in range(0, n, step):
            r = LOG[k]
            stdout.write('{"timestamp_ms":%d,"sensor":"fwd0_mm","value":%f}\n' % (r[0], r[1]))
            stdout.write('{"timestamp_ms":%d,"sensor":"fwd1_mm","value":%f}\n' % (r[0], r[2]))
            stdout.write('{"timestamp_ms":%d,"sensor":"enc_deg","value":%f}\n' % (r[0], r[3]))
            stdout.write('{"timestamp_ms":%d,"sensor":"heading_deg","value":%f}\n' % (r[0], r[4] / 10.0))

except Exception as e:
    emit("exception", 1)
    stdout.write("ERR %s\n" % repr(e))
finally:
    for m in mot:
        try:
            m.brake()
        except Exception:
            pass
    stdout.write('{"event":"end"}\n')
