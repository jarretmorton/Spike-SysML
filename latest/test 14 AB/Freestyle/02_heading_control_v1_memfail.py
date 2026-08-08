# Characterization run 2 of 4 - FAILED with MemoryError, no data recovered.
# Archived because the failure is part of the engineering record.
#
# Identical to 03_heading_control_v2.py except for the logging strategy:
#   - unbounded list with .append() instead of a preallocated buffer
#   - logged EVERY control iteration (~200 Hz) instead of every 4th (~50 Hz)
#   - 6 fields per sample instead of 5
#   - 1300 ms settle instead of 800 ms
#   - no gc.collect() before the drive
#
# Failure: 'memory allocation failed, allocating 4096 bytes' ~3.3 s into the
# drive loop, as the list's backing array tried to grow. The physical run was
# unaffected - the finally block braked the motors - but all analysis was lost.
# Peak use was ~115 KB; the fix in v2 brought it to ~20 KB.

# Characterization run 3 of 4 — HEADING CONTROL + FUSED ESTIMATOR
#
# This is run 2's program with the memory fault fixed (see 02_heading_control_v1_memfail.py):
# preallocated log buffer, logging decimated to ~50 Hz from a ~200 Hz control loop,
# 5 fields per sample instead of 6, shorter settle, gc.collect() before the drive.
#
# Changes vs discovery (01):
#   - dc(+/-100) full duty instead of run(), because run() saturates and silently
#     abandons speed regulation, which is what caused the -18 deg heading collapse
#   - IMU heading PID trimming only the inner wheel (clamping does this automatically)
#   - port A only; port B left unconstructed so it cannot ping and cross-talk
#   - lag-corrected anchor + encoder extrapolation between sensor updates
#   - trigger from live measured speed, not a fixed distance
#
# FINDINGS: heading 0.0 deg at trigger (vs -19 before). A bogus 939 mm reading was
# accepted as an anchor and threw the estimate 110 mm too far -> motivated the
# asymmetric outlier gate in the locked program. Stopping model was far too
# pessimistic: predicted 46 mm, actual 14 mm. Stop is ~80% skid.
# Calibration point for the operator measurement: settled at 174.05 mm reading.

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

MMPD = 0.472          # provisional, refined to 0.49 after this run
TAU = 0.035
A_DEC = 2200.0        # deliberately pessimistic; measured far too low afterwards
T_LAT = 0.012
TARGET = 150.0        # safe calibration target, not the operating point
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

LOG = []
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

    HN = 6
    ht = [0] * HN
    he = [0.0] * HN
    hh = [0.0] * HN

    anchor_d = d_start
    anchor_e = 0.0
    have = 0
    last_raw = -1
    t_valid = 0
    n_bad = 0
    stale_max = 0
    k = 0
    I = 0.0
    t_prev = 0
    th_max = 0.0
    v_max = 0.0
    phase = 0

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

        d = us.distance()
        if d >= 45 and d <= 1900:
            t_valid = t
            if d != last_raw:
                last_raw = d
                anchor_d = d - v * TAU
                anchor_e = epos
                have = 1
        else:
            n_bad += 1
        st = t - t_valid
        if st > stale_max:
            stale_max = st

        dtrue = anchor_d - (epos - anchor_e) * MMPD

        ath = th if th > 0 else -th
        if ath > th_max:
            th_max = ath

        LOG.append((t, d, int(dtrue * 10), int(epos), int(th * 10), int(v)))
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
            if have and (dtrue - sd) <= TARGET:
                fire = 1
            if have and st > 250 and dtrue < 450:
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
            if t - t_trig > 1300:
                break
        wait(5)

    n = len(LOG)
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
    emit("final_epos", LOG[n - 1][3])
    emit("final_heading", LOG[n - 1][4] / 10.0)
    emit("th_max", th_max)
    emit("v_max_mms", v_max)
    emit("n_bad", n_bad)
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

        ef = LOG[n - 1][3]
        tstop = t_trig
        for i in range(trig, n):
            df = LOG[i][3] - ef
            if df < 0:
                df = -df
            if df > 2:
                tstop = LOG[i][0]
        emit("t_stop_ms", tstop - t_trig)

        # mm-per-degree from a clean straight cruise span (lag cancels at constant speed)
        i1 = -1
        i2 = -1
        for i in range(n):
            if LOG[i][0] > 600 and LOG[i][1] >= 45 and LOG[i][1] <= 1900:
                i1 = i
                break
        for i in range(trig, 0, -1):
            if LOG[i][1] >= 45 and LOG[i][1] <= 1900:
                i2 = i
                break
        if i1 > 0 and i2 > i1:
            de = LOG[i2][3] - LOG[i1][3]
            du = LOG[i1][1] - LOG[i2][1]
            if de > 100:
                emit("mmpd_cruise", du * 1.0 / de)
                emit("cruise_span_mm", du)
                emit("cruise_span_deg", de)
                dt2 = LOG[i2][0] - LOG[i1][0]
                if dt2 > 0:
                    emit("v_cruise_mms", du * 1000.0 / dt2)

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
