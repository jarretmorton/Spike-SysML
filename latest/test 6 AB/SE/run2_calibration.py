# =====================================================================
# Run 2 - CALIBRATION program (clean straight approach)
# ---------------------------------------------------------------------
# Hard-coded from Run 1 (run-20260630-231316):
#   forward ultrasonics : A, B      rear (unused) : E
#   drive motors        : C, D      forward signs : C=-1, D=+1 (opposed)
# NO discovery, NO nudge  -> no in-place spin -> squared straight approach.
#
# Sequence: construct known devices -> pre-approach static A/B check ->
# straight open-loop MAX approach (safe 500 mm trigger) -> brake ->
# settle -> on-hub headline compute -> lean downsampled flush.
#
# Test-like-you-fly: the control path each loop is exactly
#   read dA,dB -> min() w/ dropout fallback -> trigger check -> wait(5)
# identical to the operation hot loop. Logging is buffered every 3rd
# (approach) / 2nd (settle), flushed only after the motors stop.
# try/finally: motors always brake; {"event":"end"} always emitted.
#
# Wire contract: {"timestamp_ms":<int>,"sensor":"<name>","value":<scalar>}
#   stop_reason: 0 trigger, 1 failsafe_floor, 2 failsafe_time
# =====================================================================
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import wait, StopWatch

hub = PrimeHub()
watch = StopWatch()
motors = []

def tel(t, name, v, nd=2):
    if v is None:
        return
    if isinstance(v, float):
        v = round(v, nd)
    print('{"timestamp_ms":%d,"sensor":"%s","value":%s}' % (int(t), name, v))

S_TRIG_CAL = 500     # mm SAFE trigger (reaches max; big buffer to wall)
HARD_FLOOR = 300     # mm failsafe if primary trigger missed
TIME_CAP   = 5000    # ms failsafe from approach start
CMD_MAX    = 2000    # deg/s -> clamps to motor ceiling
SIGN_C     = -1      # forward sign, motor C (opposed mount)
SIGN_D     = 1       # forward sign, motor D

try:
    mC = Motor(Port.C); motors.append(("C", mC))
    mD = Motor(Port.D); motors.append(("D", mD))
    fA = UltrasonicSensor(Port.A)
    fB = UltrasonicSensor(Port.B)

    heading0 = hub.imu.heading()
    tel(watch.time(), "heading0", heading0)

    # pre-approach static A/B check: classify the 133 mm A-B offset
    for i in range(10):
        tel(watch.time(), "pre_A", fA.distance())
        tel(watch.time(), "pre_B", fB.distance())
        wait(20)

    buf = []                 # (t, dA, dB, h, aC, aD)
    last_valid_min = 3000
    mC.run(SIGN_C * CMD_MAX); mD.run(SIGN_D * CMD_MAX)
    t0 = watch.time()
    stop_reason = -1; t_trig = -1
    s_trig_actual = None; aC_trig = None; aD_trig = None
    i_loop = 0
    while True:
        t = watch.time() - t0
        dA = fA.distance(); dB = fB.distance()
        dmin = dA if dA < dB else dB
        # dropout protection: both out of range -> use last valid (never delays stop)
        if dmin < 2000:
            last_valid_min = dmin
            ctrl = dmin
        else:
            ctrl = last_valid_min
        if ctrl <= S_TRIG_CAL:
            stop_reason = 0
        elif ctrl <= HARD_FLOOR:
            stop_reason = 1
        elif t >= TIME_CAP:
            stop_reason = 2
        if stop_reason >= 0:
            s_trig_actual = ctrl
            aC_trig = mC.angle(); aD_trig = mD.angle(); t_trig = t
            break
        if i_loop % 3 == 0:
            h = hub.imu.heading()
            buf.append((t, dA, dB, h, mC.angle(), mD.angle()))
        i_loop += 1
        wait(5)
    # STOP: brake = short, repeatable, no reverse creep
    mC.brake(); mD.brake()
    # settle ~1.2 s to capture coast-to-rest
    settle_until = (watch.time() - t0) + 1200
    j = 0
    while (watch.time() - t0) < settle_until:
        t = watch.time() - t0
        dA = fA.distance(); dB = fB.distance()
        h = hub.imu.heading()
        if j % 2 == 0:
            buf.append((t, dA, dB, h, mC.angle(), mD.angle()))
        j += 1
        wait(10)
    # on-hub rest estimate (last 6 rows, skip 2000 dropouts)
    tail = buf[-6:] if len(buf) >= 6 else buf
    sr = 0; kk = 0; hr = 0
    for row in tail:
        dm = row[1] if row[1] < row[2] else row[2]
        if dm < 2000:
            sr += dm; kk += 1
        hr += row[3]
    s_rest = (sr / kk) if kk > 0 else float(last_valid_min)
    heading_rest = hr / len(tail)
    aC_rest = tail[-1][4]; aD_rest = tail[-1][5]
    tw = watch.time()
    tel(tw, "s_trig_cal", S_TRIG_CAL)
    tel(tw, "stop_reason", stop_reason)
    tel(tw, "t_trigger_ms", t_trig)
    tel(tw, "s_trig_actual", float(s_trig_actual))
    tel(tw, "s_rest", float(s_rest))
    tel(tw, "D_ranger", float(s_trig_actual - s_rest))
    tel(tw, "aC_trig", float(aC_trig))
    tel(tw, "aD_trig", float(aD_trig))
    tel(tw, "aC_rest", float(aC_rest))
    tel(tw, "aD_rest", float(aD_rest))
    tel(tw, "heading_rest", float(heading_rest))
    tel(tw, "heading_drift", float(heading_rest - heading0))
    tel(tw, "n_samples", len(buf))
    # lean flush (already downsampled at source)
    for row in buf:
        t = row[0]
        tel(t, "dA", row[1])
        tel(t, "dB", row[2])
        tel(t, "heading", row[3])
        tel(t, "aC", row[4], 1)
        tel(t, "aD", row[5], 1)
    print("SUMMARY D=%.1f s_trig=%.1f s_rest=%.1f drift=%.1f stop=%d n=%d" % (
        s_trig_actual - s_rest, s_trig_actual, s_rest,
        heading_rest - heading0, stop_reason, len(buf)))
finally:
    try:
        for _n, _m in motors:
            _m.brake()
    except Exception:
        pass
    print('{"event":"end"}')
