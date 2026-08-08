# Characterization run 1 of 5
# Purpose: discover ports, motor mirroring and drive polarity, identify the
# forward-facing ultrasonic pair, fit mm-per-encoder-degree, then perform one
# full-speed sprint braking at a deliberately safe 400 mm threshold to measure
# the lumped stopping constant S.
#
# Result: A/B disagreement (+114 mm) found; S = 65.2 mm (in B's frame, later
# shown to be the wrong frame); exposed the 2000 mm dropout and freeze faults.

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

def emit(name, val):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n' % (clock.time(), name, val))

PORTS = (Port.A, Port.B, Port.C, Port.D, Port.E, Port.F)
PN = "ABCDEF"

motors = []
ultras = []
colors = []

try:
    # ---------------- PORT DISCOVERY ----------------
    for i in range(6):
        p = PORTS[i]
        k = 0
        try:
            d = Motor(p); motors.append(d); k = 1
        except Exception:
            try:
                d = UltrasonicSensor(p); ultras.append(d); k = 2
            except Exception:
                try:
                    d = ColorSensor(p); colors.append(d); k = 3
                except Exception:
                    k = 0
        emit("port_" + PN[i], k)

    nu = len(ultras)
    emit("n_motor", len(motors))
    emit("n_ultra", nu)
    emit("n_color", len(colors))

    if len(motors) < 2 or nu < 2:
        emit("fatal_missing_devices", 1)
    else:
        m1 = motors[0]; m2 = motors[1]
        for m in motors:
            try:
                m.control.limits(acceleration=12000)
            except Exception:
                pass
        try:
            SPMAX = m1.control.limits()[0]
        except Exception:
            SPMAX = 1000.0
        if SPMAX < 100 or SPMAX > 3000:
            SPMAX = 1000.0
        emit("motor_max_speed", SPMAX)
        m1.reset_angle(0); m2.reset_angle(0)

        def allread():
            return [u.distance() for u in ultras]

        # ---------------- MIRROR TEST (one wheel at a time) ----------------
        # Pulse each motor alone and watch heading. Same-sign heading change
        # from both means the motors are mirror-mounted.
        def pulse(m, spd, ms):
            h0 = hub.imu.heading()
            m.run(spd); wait(ms); m.brake(); wait(400)
            return hub.imu.heading() - h0

        m2.hold()
        d1 = pulse(m1, 300, 300)
        pulse(m1, -300, 300)
        m1.hold(); m2.brake()
        d2 = pulse(m2, 300, 300)
        pulse(m2, -300, 300)
        m1.brake()
        wait(300)
        emit("dh_m1", d1); emit("dh_m2", d2)
        s2 = -1 if (d1 * d2 > 0) else 1
        emit("s2_mirror", s2)
        if abs(d1) < 4 or abs(d2) < 4:
            emit("warn_weak_turn", 1)

        def trav():
            return (m1.angle() + s2 * m2.angle()) * 0.5

        # ---------------- STRAIGHT CALIBRATION BURST ----------------
        wait(200)
        base = allread()
        for i in range(nu):
            emit("u%d_base" % i, base[i])

        m1.reset_angle(0); m2.reset_angle(0)
        sx_ = []; sd_ = []
        m1.run(400); m2.run(400 * s2)
        t0 = clock.time()
        while clock.time() - t0 < 800:
            sx_.append(trav())
            sd_.append(allread())
            wait(12)
        m1.brake(); m2.brake()
        cal_trav = trav()
        wait(600)
        after = allread()
        for i in range(nu):
            emit("u%d_after" % i, after[i])
        emit("cal_trav_deg", cal_trav)

        dlt = [after[i] - base[i] for i in range(nu)]
        for i in range(nu):
            emit("u%d_delta" % i, dlt[i])

        # Forward pair = the two sensors that move together and read alike.
        best = 1000000.0; ia = 0; ib = 1
        for i in range(nu):
            for j in range(i + 1, nu):
                sc = abs(dlt[i] - dlt[j]) + 0.5 * abs(base[i] - base[j])
                if abs(dlt[i]) < 8 or abs(dlt[j]) < 8:
                    sc = sc + 500.0
                if sc < best:
                    best = sc; ia = i; ib = j
        emit("fwd_idx_a", ia); emit("fwd_idx_b", ib); emit("pair_score", best)

        pair_ok = 1 if (dlt[ia] * dlt[ib] > 0 and abs(dlt[ia]) > 8) else 0
        emit("pair_ok", pair_ok)

        mean_delta = 0.5 * (dlt[ia] + dlt[ib])
        fwd_sign = 1 if mean_delta < 0 else -1
        emit("fwd_sign", fwd_sign)

        # ---------------- mm per encoder degree (least squares) ----------------
        n = 0; sx = 0.0; sy = 0.0; sxx = 0.0; sxy = 0.0
        for k in range(len(sx_)):
            y = sd_[k][ia]
            yb = sd_[k][ib]
            if yb < y:
                y = yb
            if y >= 1990 or y <= 40:
                continue
            x = sx_[k] * fwd_sign
            n += 1; sx += x; sy += y; sxx += x * x; sxy += x * y
        den = n * sxx - sx * sx
        mmpd = 0.0
        if n >= 6 and den != 0:
            mmpd = -(n * sxy - sx * sy) / den
        emit("mmpd_fit", mmpd); emit("mmpd_n", n)
        mmpd_ok = 1
        if mmpd < 0.05 or mmpd > 5.0:
            mmpd_ok = 0
            if abs(cal_trav) > 20:
                mmpd = abs(mean_delta) / abs(cal_trav)
                emit("mmpd_fallback", mmpd)
        if mmpd < 0.05 or mmpd > 5.0:
            mmpd = 0.49
            emit("mmpd_default", mmpd)
        emit("mmpd_used", mmpd)
        emit("mmpd_fit_ok", mmpd_ok)

        def drive(v1, v2):
            m1.run(v1 * fwd_sign)
            m2.run(v2 * s2 * fwd_sign)

        TS = 1 if (d1 * fwd_sign) > 0 else -1
        emit("turn_sign", TS)

        def fmin():
            a = ultras[ia].distance()
            b = ultras[ib].distance()
            return a if a < b else b

        if pair_ok == 0:
            emit("abort_sprint_pair", 1)
        else:
            # ---------------- REPOSITION FOR RUNWAY ----------------
            d0 = fmin()
            emit("dist_before_repos", d0)
            t0 = clock.time()
            if d0 < 870:
                drive(-350, -350)
                while clock.time() - t0 < 5000:
                    if fmin() >= 910:
                        break
                    wait(10)
                m1.brake(); m2.brake(); wait(700)
            elif d0 > 1150:
                drive(350, 350)
                while clock.time() - t0 < 5000:
                    if fmin() <= 1100:
                        break
                    wait(10)
                m1.brake(); m2.brake(); wait(700)

            # ---------------- SQUARE UP TO ORIGINAL HEADING ----------------
            t0 = clock.time()
            while clock.time() - t0 < 3500:
                e = hub.imu.heading()
                if -1.5 < e < 1.5:
                    break
                w = -3.0 * e * TS
                if w > 200: w = 200
                if w < -200: w = -200
                if -60 < w < 0: w = -60
                if 0 < w < 60: w = 60
                drive(w, -w)
                wait(15)
            m1.brake(); m2.brake(); wait(600)
            emit("heading_after_square", hub.imu.heading())
            emit("dist_start", fmin())

            try:
                hub.imu.reset_heading(0)
            except Exception:
                pass
            wait(300)
            m1.reset_angle(0); m2.reset_angle(0)

            # ---------------- FULL-SPEED SPRINT + BRAKE PROBE ----------------
            SP = SPMAX
            TRIG = 400.0
            KP = 10.0
            bt = []; bd = []; be = []; bh = []; bx = []
            last = fmin()
            an_d = last; an_x = 0.0
            nchg = 0; it = 0
            lastcmd = 0.0
            tb = 0; eb = 0.0; xb = 0.0
            t0 = clock.time()
            drive(SP, SP)
            while True:
                now = clock.time()
                x = trav() * fwd_sign
                r = fmin()
                if r != last:
                    last = r; an_d = r; an_x = x; nchg += 1
                est = an_d - (x - an_x) * mmpd
                if est <= TRIG or r <= 130 or (now - t0) > 5000:
                    m1.brake(); m2.brake()
                    tb = now; eb = est; xb = x
                    break
                h = hub.imu.heading()
                c = 0.0
                if h > 2.0 or h < -2.0:
                    c = -KP * h * TS
                    if c > 70: c = 70
                    if c < -70: c = -70
                if abs(c - lastcmd) > 4:
                    drive(SP + c, SP - c)
                    lastcmd = c
                it += 1
                if (it & 1) == 0 and len(bt) < 420:
                    bt.append(now); bd.append(r); be.append(est); bh.append(h); bx.append(x)
                wait(3)

            # ---------------- POST-BRAKE ----------------
            t1 = clock.time()
            while clock.time() - t1 < 900:
                now = clock.time()
                x = trav() * fwd_sign
                r = fmin()
                if r != last:
                    last = r; an_d = r; an_x = x
                est = an_d - (x - an_x) * mmpd
                if len(bt) < 700:
                    bt.append(now); bd.append(r); be.append(est)
                    bh.append(hub.imu.heading()); bx.append(x)
                wait(8)
            try:
                m1.hold(); m2.hold()
            except Exception:
                pass
            wait(500)
            x_end = trav() * fwd_sign

            va = []; vb = []; vm = []
            for i in range(41):
                aa = ultras[ia].distance(); bb = ultras[ib].distance()
                va.append(aa); vb.append(bb)
                vm.append(aa if aa < bb else bb)
                wait(15)
            va.sort(); vb.sort(); vm.sort()
            fin = vm[len(vm) // 2]

            emit("final_min_mm", fin)
            emit("final_a_mm", va[len(va) // 2])
            emit("final_b_mm", vb[len(vb) // 2])
            for i in range(nu):
                if i != ia and i != ib:
                    emit("final_rear_mm", ultras[i].distance())
            emit("est_at_brake", eb)
            emit("S_lump_mm", eb - fin)
            emit("brake_roll_enc_mm", (x_end - xb) * mmpd)
            emit("t_brake_ms", tb - t0)
            emit("heading_end", hub.imu.heading())
            emit("n_sensor_changes", nchg)
            emit("sprint_iters", it)
            if it > 0:
                emit("loop_period_ms", (tb - t0) * 1.0 / it)
            if nchg > 0:
                emit("sensor_update_ms", (tb - t0) * 1.0 / nchg)

            ta = tb - 260; tc = tb - 60
            k0 = -1; k1 = -1
            for k in range(len(bt)):
                if bt[k] >= ta and k0 < 0:
                    k0 = k
                if bt[k] <= tc:
                    k1 = k
            v = 0.0
            if k0 >= 0 and k1 > k0 and bt[k1] > bt[k0]:
                v = (bx[k1] - bx[k0]) * mmpd / (bt[k1] - bt[k0]) * 1000.0
            emit("top_speed_mm_s", v)

            # ---------------- DUMP TRACE ----------------
            nn = len(bt)
            step = 1
            while nn / step > 150:
                step += 1
            for k in range(0, nn, step):
                stdout.write('{"timestamp_ms":%d,"sensor":"fwd_mm","value":%f}\n' % (bt[k], bd[k]))
                stdout.write('{"timestamp_ms":%d,"sensor":"est_mm","value":%f}\n' % (bt[k], be[k]))
                stdout.write('{"timestamp_ms":%d,"sensor":"heading_deg","value":%f}\n' % (bt[k], bh[k]))
                stdout.write('{"timestamp_ms":%d,"sensor":"travel_mm","value":%f}\n' % (bt[k], bx[k] * mmpd))
                wait(1)

finally:
    try:
        for m in motors:
            m.stop()
    except Exception:
        pass
    stdout.write('{"event":"end"}\n')
