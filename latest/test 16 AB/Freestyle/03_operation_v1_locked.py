# Operation program v1 (LOCKED for operation attempts 1-3, later superseded)
# Identical control path to the rehearsal, with four constants updated from
# that run's measurements and the sensor-B fallback pinned off so every run
# follows the exact code path that was validated.
#
#   MMPD   0.4391 -> 0.482   (corrected from sensor-A closure rate)
#   S_LUMP 65.2   -> 46.0    (re-measured in sensor A's frame)
#   PENR   0.109  -> 0.120   (rescaled to the corrected speed)
#   useB   auto   -> 0       (pinned; B's offset is not stable run to run)
#
# Attempts 1 and 2 stopped at 70 mm and 78 mm (sensor A). Attempt 3 hit the
# re-anchor escape bug: a 483 ms freeze caused a re-anchor onto the stale
# value, 15 consecutive gate lock-outs, and a blind brake at 147 mm. The
# escape rule was deleted for the final program.

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

def emit(name, val):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n' % (clock.time(), name, val))

MMPD    = 0.482
S_LUMP  = 46.0
BIAS_A  = 4.0
TARGET  = 70.0
TRIG    = TARGET + BIAS_A + S_LUMP
S2      = -1
FWD     = -1
TS      = 1
SP      = 1000.0
KP      = 4.0
DB      = 2.0
CAP     = 50.0
GATE    = 75.0
VLO     = 40.0
VHI     = 1900.0
STALE   = 55.0
PENR    = 0.120
BFALL   = 70.0
BMINP   = 250.0
BLIND   = 300.0

PORTS = (Port.A, Port.B, Port.C, Port.D, Port.E, Port.F)
PN = "ABCDEF"
EXPECT = (2, 2, 1, 1, 2, 3)

motors = []
ultras = []
colors = []
ok = 1

try:
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
        if k != EXPECT[i]:
            ok = 0
    emit("selftest_ports", ok)

    if ok == 0 or len(motors) < 2 or len(ultras) < 3:
        emit("abort_selftest", 1)
    else:
        m1 = motors[0]; m2 = motors[1]
        uA = ultras[0]; uB = ultras[1]
        for m in motors:
            try:
                m.control.limits(acceleration=12000)
            except Exception:
                pass
        m1.reset_angle(0); m2.reset_angle(0)

        def travmm():
            return (m1.angle() + S2 * m2.angle()) * 0.5 * FWD * MMPD

        def drive(v1, v2):
            m1.run(v1 * FWD)
            m2.run(v2 * S2 * FWD)

        # ---------- IMU SETTLE ----------
        wait(1100)
        try:
            hub.imu.reset_heading(0)
        except Exception:
            pass
        wait(200)

        # ---------- SEED / LIVE A-B OFFSET AT REST ----------
        sa = []; sb = []
        for i in range(25):
            sa.append(uA.distance()); sb.append(uB.distance())
            wait(16)
        sa.sort(); sb.sort()
        seedA = sa[12]; seedB = sb[12]
        OFF = seedA - seedB
        emit("seed_A", seedA); emit("seed_B", seedB); emit("off_AB", OFF)
        useB = 0
        emit("useB", useB)

        if seedA < 400 or seedA > 1900:
            emit("abort_seed", seedA)
        else:
            emit("trig_used", TRIG)
            # ---------- SPRINT ----------
            bt = []; ba = []; bb_ = []; be = []; bh = []
            la = seedA; lb = seedB
            an_d = float(seedA); an_x = 0.0
            t0 = clock.time(); t_acc = t0
            nacc = 0; nrej = 0; it = 0
            lastc = 0.0
            tb = 0; eb = 0.0; xb = 0.0
            why = 0
            m1.reset_angle(0); m2.reset_angle(0)
            drive(SP, SP)
            while True:
                now = clock.time()
                x = travmm()
                pred = an_d - (x - an_x)
                a = uA.distance()
                b = uB.distance()
                ca = -1.0; cb = -1.0
                if a != la:
                    la = a
                    if a >= VLO and a <= VHI:
                        df = a - pred
                        if df < 0: df = -df
                        if df <= GATE:
                            ca = a
                        else:
                            nrej += 1
                if useB == 1 and b != lb:
                    lb = b
                    if b >= VLO and b <= VHI:
                        bbv = b + OFF
                        df = bbv - pred
                        if df < 0: df = -df
                        if df <= GATE:
                            cb = bbv
                best = -1.0
                if ca >= 0:
                    best = ca
                elif cb >= 0 and (now - t_acc) > BFALL and pred > BMINP:
                    best = cb
                if best >= 0:
                    an_d = best; an_x = x; t_acc = now; nacc += 1
                stale = now - t_acc
                # NOTE: this re-anchor escape is the bug that broke operation
                # run 3. It does not require the reading to have changed, so a
                # long freeze re-anchors to the stale value. Deleted later.
                if stale > 400 and pred > 400 and a >= VLO and a <= VHI:
                    an_d = a; an_x = x; t_acc = now
                    stale = 0
                est = an_d - (x - an_x)
                pen = 0.0
                if stale > STALE:
                    pen = (stale - STALE) * PENR
                es = est - pen

                if es <= TRIG:
                    why = 1
                elif stale > BLIND and est < 400:
                    why = 2
                elif a >= VLO and a < 95:
                    why = 3
                elif (now - t0) > 5000:
                    why = 4
                elif (now - t0) > 300 and est > seedA - 30:
                    why = 5
                if why > 0:
                    m1.brake(); m2.brake()
                    tb = now; eb = es; xb = x
                    break

                h = hub.imu.heading()
                c = 0.0
                if h > DB or h < -DB:
                    c = -KP * h * TS
                    if c > CAP: c = CAP
                    if c < -CAP: c = -CAP
                if abs(c - lastc) > 4:
                    drive(SP + c, SP - c)
                    lastc = c
                it += 1
                if (it & 1) == 0 and len(bt) < 420:
                    bt.append(now); ba.append(a); bb_.append(b); be.append(es); bh.append(h)
                wait(3)

            emit("brake_reason", why)

            # ---------- POST-BRAKE ----------
            t1 = clock.time()
            while clock.time() - t1 < 900:
                now = clock.time()
                x = travmm()
                a = uA.distance(); b = uB.distance()
                if a != la:
                    la = a
                    if a >= VLO and a <= VHI:
                        an_d = a; an_x = x
                est = an_d - (x - an_x)
                if len(bt) < 700:
                    bt.append(now); ba.append(a); bb_.append(b)
                    be.append(est); bh.append(hub.imu.heading())
                wait(8)
            try:
                m1.hold(); m2.hold()
            except Exception:
                pass
            wait(500)
            xend = travmm()

            va = []; vb = []
            for i in range(41):
                va.append(uA.distance()); vb.append(uB.distance())
                wait(15)
            va.sort(); vb.sort()
            finA = va[20]; finB = vb[20]

            emit("final_A_mm", finA)
            emit("final_B_mm", finB)
            emit("est_at_brake", eb)
            emit("S_measured", eb - finA)
            emit("pred_true_gap", finA - BIAS_A)
            emit("brake_roll_enc_mm", xend - xb)
            emit("t_brake_ms", tb - t0)
            emit("heading_end", hub.imu.heading())
            emit("n_accepted", nacc)
            emit("n_rejected", nrej)
            emit("sprint_iters", it)
            if it > 0:
                emit("loop_period_ms", (tb - t0) * 1.0 / it)
            if nacc > 0:
                emit("update_ms", (tb - t0) * 1.0 / nacc)

            ta = tb - 260; tc = tb - 60
            k0 = -1; k1 = -1
            for k in range(len(bt)):
                if bt[k] >= ta and k0 < 0: k0 = k
                if bt[k] <= tc: k1 = k
            v = 0.0
            if k0 >= 0 and k1 > k0 and bt[k1] > bt[k0]:
                v = (be[k0] - be[k1]) / (bt[k1] - bt[k0]) * 1000.0
            emit("top_speed_mm_s", v)

            nn = len(bt)
            step = 1
            while nn / step > 150:
                step += 1
            for k in range(0, nn, step):
                stdout.write('{"timestamp_ms":%d,"sensor":"fwd_a_mm","value":%f}\n' % (bt[k], ba[k]))
                stdout.write('{"timestamp_ms":%d,"sensor":"fwd_b_mm","value":%f}\n' % (bt[k], bb_[k]))
                stdout.write('{"timestamp_ms":%d,"sensor":"est_mm","value":%f}\n' % (bt[k], be[k]))
                stdout.write('{"timestamp_ms":%d,"sensor":"heading_deg","value":%f}\n' % (bt[k], bh[k]))
                wait(1)

finally:
    try:
        for m in motors:
            m.stop()
    except Exception:
        pass
    stdout.write('{"event":"end"}\n')
