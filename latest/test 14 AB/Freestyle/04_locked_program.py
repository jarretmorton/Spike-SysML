# LOCKED PROGRAM - validated in characterization run 4, then run UNCHANGED
# for all five scored operation runs.
#
# Result: 5/5 no contact. Measured gaps 33, 19, 32, 25, 35 mm (mean 28.8).
# Every stop came from the normal fused trigger; no safety backstop ever fired.
#
# Known issues, deliberately NOT patched after validation (see report S9):
#   - the d >= 45 validity floor sits above the operating point and discards
#     good readings at rest; reporting only, never affects control
#   - the forced re-acquire after 250 ms bypasses the outlier gate entirely;
#     it should apply a relaxed gate instead

import gc
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

def emit(s, v):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n' % (clock.time(), s, v))

MMPD = 0.49
TAU = 0.035
A_DEC = 7300.0
T_LAT = 0.006
TARGET = 50.0
OFFSET = 23.0
RAWSTOP = 62
ALPHA = 0.6
GATE_HI = 25.0
GATE_LO = -70.0
KP = 4.0
KI = 8.0
KD = 0.3
UI_MAX = 25.0
BASE = 100
NMAX = 300
LOGEVERY = 4

mC = Motor(Port.C)
mD = Motor(Port.D)
us = UltrasonicSensor(Port.A)

LOG = [None] * NMAX
n = 0
trig = -1
abort = 0
t_trig = 0
d_trig = 0.0
v_trig = 0.0
sd_trig = 0.0

try:
    wait(400)
    sacc = 0.0
    cacc = 0
    for i in range(20):
        d = us.distance()
        if d >= 45 and d <= 1900:
            sacc += d
            cacc += 1
        wait(15)
    d_start = sacc / cacc if cacc > 0 else 1000.0
    emit("start_d_rest", d_start)
    emit("start_valid_n", cacc)

    mC.reset_angle(0)
    mD.reset_angle(0)
    h0 = hub.imu.heading()
    gc.collect()

    HN = 6
    ht = [0] * HN
    he = [0.0] * HN
    hh = [0.0] * HN

    anchor_d = d_start
    anchor_e = 0.0
    last_raw = -1
    t_valid = 0
    t_accept = 0
    n_bad = 0
    n_rej = 0
    stale_max = 0
    k = 0
    I = 0.0
    t_prev = 0
    th_max = 0.0
    v_max = 0.0
    phase = 0
    min_dt = 9999.0
    min_raw = 9999

    t0 = clock.time()
    mC.dc(-BASE)
    mD.dc(BASE)

    while True:
        t = clock.time() - t0
        aC = mC.angle()
        aD = mD.angle()
        epos = (aD - aC) * 0.5
        th = hub.imu.heading() - h0

        idx = k % HN
        ot = ht[idx]
        oe = he[idx]
        oh = hh[idx]
        dtw = t - ot
        if dtw > 0:
            v = (epos - oe) * MMPD * 1000.0 / dtw
            om = (th - oh) * 1000.0 / dtw
        else:
            v = 0.0
            om = 0.0
        ht[idx] = t
        he[idx] = epos
        hh[idx] = th
        if v < 0:
            v = 0.0
        if v > v_max:
            v_max = v

        pred = anchor_d - (epos - anchor_e) * MMPD
        d = us.distance()
        if d >= 45 and d <= 1900:
            t_valid = t
            if d != last_raw:
                last_raw = d
                cand = d - v * TAU
                diff = cand - pred
                ghi = 60.0 if t < 500 else GATE_HI
                if (diff <= ghi and diff >= GATE_LO) or (t - t_accept) > 250:
                    anchor_d = pred + ALPHA * diff
                    anchor_e = epos
                    t_accept = t
                else:
                    n_rej += 1
        else:
            n_bad += 1
        st = t - t_valid
        if st > stale_max:
            stale_max = st

        dtrue = anchor_d - (epos - anchor_e) * MMPD
        if dtrue < min_dt:
            min_dt = dtrue
        if d >= 45 and d <= 1900 and d < min_raw:
            min_raw = d

        ath = th if th > 0 else -th
        if ath > th_max:
            th_max = ath

        if k % LOGEVERY == 0 and n < NMAX:
            LOG[n] = (t, d, int(dtrue * 10), int(epos), int(th * 10))
            n += 1
        k += 1

        if phase == 0:
            ddt = t - t_prev
            t_prev = t
            if ddt > 0 and ddt < 60:
                I += th * ddt * 0.001
            ui = KI * I
            if ui > UI_MAX:
                ui = UI_MAX
                I = UI_MAX / KI
            if ui < -UI_MAX:
                ui = -UI_MAX
                I = -UI_MAX / KI
            u = KP * th + ui + KD * om
            if u > 60:
                u = 60
            if u < -60:
                u = -60
            cC = -BASE + u
            cD = BASE + u
            if cC > 100:
                cC = 100
            if cC < -100:
                cC = -100
            if cD > 100:
                cD = 100
            if cD < -100:
                cD = -100
            mC.dc(cC)
            mD.dc(cD)

            sd = v * v / (2.0 * A_DEC) + v * T_LAT
            fire = 0
            if (dtrue - sd) <= TARGET:
                fire = 1
            if d >= 45 and d <= RAWSTOP:
                fire = 1
                abort = 6
            if (t - t_accept) > 300 and dtrue < 300:
                fire = 1
                abort = 4
            if th_max > 12:
                fire = 1
                abort = 2
            if t > 6000:
                fire = 1
                abort = 3
            if t > 500 and dtrue > d_start + 80:
                fire = 1
                abort = 5
            if fire:
                mC.hold()
                mD.hold()
                trig = n - 1
                t_trig = t
                d_trig = dtrue
                v_trig = v
                sd_trig = sd
                phase = 1
        else:
            if t - t_trig > 900:
                break
        wait(5)

    emit("abort_code", abort)
    emit("n_log", n)
    emit("ctrl_hz", k * 1000.0 / LOG[n - 1][0])

    fin = 20 if n > 20 else n
    sacc = 0.0
    cacc = 0
    for i in range(n - fin, n):
        dv = LOG[i][1]
        if dv >= 45 and dv <= 1900:
            sacc += dv
            cacc += 1
    d_final = sacc / cacc if cacc > 0 else -1.0
    emit("final_d_rest", d_final)
    emit("final_valid_n", cacc)
    emit("EST_TRUE_GAP", d_final - OFFSET)
    emit("min_dtrue", min_dt)
    emit("min_raw", min_raw)
    emit("min_true_gap", min_raw - OFFSET)
    emit("final_epos", LOG[n - 1][3])
    emit("final_heading", LOG[n - 1][4] / 10.0)
    emit("th_max", th_max)
    emit("v_max_mms", v_max)
    emit("n_bad", n_bad)
    emit("n_rej", n_rej)
    emit("stale_max_ms", stale_max)

    if trig > 0:
        emit("t_trig_ms", t_trig)
        emit("d_true_at_trig", d_trig)
        emit("v_at_trig", v_trig)
        emit("sd_pred_mm", sd_trig)
        emit("d_raw_at_trig", LOG[trig][1])
        emit("th_at_trig", LOG[trig][4] / 10.0)
        emit("brake_enc_mm", (LOG[n - 1][3] - LOG[trig][3]) * MMPD)
        if d_final > 0:
            emit("actual_stop_mm", d_trig - d_final)
            emit("target_err_mm", d_final - TARGET)

    gc.collect()
    for i in range(n):
        r = LOG[i]
        near = trig >= 0 and i >= trig - 2 and r[0] <= t_trig + 400
        if near or i % 3 == 0:
            stdout.write('{"timestamp_ms":%d,"sensor":"raw_mm","value":%f}\n' % (r[0], r[1]))
            stdout.write('{"timestamp_ms":%d,"sensor":"dtrue_mm","value":%f}\n' % (r[0], r[2] / 10.0))
            stdout.write('{"timestamp_ms":%d,"sensor":"heading_deg","value":%f}\n' % (r[0], r[4] / 10.0))
            stdout.write('{"timestamp_ms":%d,"sensor":"enc_deg","value":%f}\n' % (r[0], r[3]))

except Exception as e:
    emit("exception", 1)
    stdout.write("ERR %s\n" % repr(e))
finally:
    try:
        mC.brake()
        mD.brake()
    except Exception:
        pass
    stdout.write('{"event":"end"}\n')
