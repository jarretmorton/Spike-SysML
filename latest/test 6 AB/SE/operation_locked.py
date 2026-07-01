# =====================================================================
# OPERATION program - LOCKED (Verification Plan, GATE B)
# ---------------------------------------------------------------------
# Used UNCHANGED for the verification run and all 5 scored runs.
#
# Design (frozen):
#   ports/polarity hard-coded: fwd US = A,B ; motors C(-1), D(+1)
#   control: open-loop, both motors at CMD_MAX (maximum speed - SYS-1)
#   trigger: brake when min(dA,dB) <= T_OP, last-valid dropout fallback
#   T_OP = 125 mm ; delta = 0 (sensor B is the frontmost point)
#   stop: brake() both (skid-dominated, ~62 mm, characterized)
#   telemetry: headline one-shots only (no per-sample buffer) -> instant flush
#
# Test-like-you-fly: the control path each loop
#   read dA,dB -> min w/ last-valid fallback -> threshold check -> wait(5)
# is identical to the calibration hot loop. The every-3rd auxiliary reads
# (heading + encoders) are retained (discarded here) so the loop TIMING
# matches calibration exactly; only the threshold value and the hard-coded
# (vs discovered) setup differ.
#
# Predicted: frontmost (sensor B) rest gap ~41 mm, nadir ~35 mm, NO CONTACT.
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

# ---- LOCKED parameters ----
T_OP     = 125       # mm trigger threshold on min(dA,dB)
CMD_MAX  = 2000      # deg/s -> clamps to motor ceiling (maximum speed)
SIGN_C   = -1
SIGN_D   = 1
TIME_CAP = 4000      # ms runaway backstop (operator also supervises)

try:
    mC = Motor(Port.C); motors.append(("C", mC))
    mD = Motor(Port.D); motors.append(("D", mD))
    fA = UltrasonicSensor(Port.A)
    fB = UltrasonicSensor(Port.B)

    heading0 = hub.imu.heading()
    tel(watch.time(), "heading0", heading0)

    # pre-approach: record start gap (diagnostic; also seeds last-valid)
    start_gap = 3000
    for i in range(6):
        a = fA.distance(); b = fB.distance()
        m = a if a < b else b
        if m < start_gap:
            start_gap = m
        wait(20)
    tel(watch.time(), "start_gap", start_gap)

    last_valid = start_gap if start_gap < 2000 else 3000
    mC.run(SIGN_C * CMD_MAX); mD.run(SIGN_D * CMD_MAX)
    t0 = watch.time()
    stop_reason = -1; t_trig = -1; s_trig_actual = None
    i_loop = 0
    while True:
        t = watch.time() - t0
        a = fA.distance(); b = fB.distance()
        m = a if a < b else b
        # ---- CONTROL: min w/ last-valid dropout fallback ----
        if m < 2000:
            last_valid = m; ctrl = m
        else:
            ctrl = last_valid
        if ctrl <= T_OP:
            stop_reason = 0
        elif t >= TIME_CAP:
            stop_reason = 2
        if stop_reason >= 0:
            s_trig_actual = ctrl; t_trig = t
            break
        # timing-match to calibration hot loop (aux reads retained, discarded)
        if i_loop % 3 == 0:
            _h = hub.imu.heading(); _c = mC.angle(); _d = mD.angle()
        i_loop += 1
        wait(5)
    # ---- STOP ----
    mC.brake(); mD.brake()
    # settle: track nadir (closest) + read rest (minimal, no buffer)
    s_closest = last_valid
    settle_end = (watch.time() - t0) + 1200
    while (watch.time() - t0) < settle_end:
        a = fA.distance(); b = fB.distance()
        m = a if a < b else b
        if m < 2000 and m < s_closest:
            s_closest = m
        wait(10)
    rest_vals = []
    for i in range(6):
        a = fA.distance(); b = fB.distance()
        m = a if a < b else b
        if m < 2000:
            rest_vals.append(m)
        wait(15)
    if rest_vals:
        rest_vals.sort(); s_rest = rest_vals[len(rest_vals) // 2]
    else:
        s_rest = last_valid
    heading_rest = hub.imu.heading()
    tw = watch.time()
    tel(tw, "T_OP", T_OP)
    tel(tw, "stop_reason", stop_reason)
    tel(tw, "t_trigger_ms", t_trig)
    tel(tw, "s_trig_actual", float(s_trig_actual))
    tel(tw, "s_closest", float(s_closest))
    tel(tw, "s_rest", float(s_rest))
    tel(tw, "heading_rest", float(heading_rest))
    tel(tw, "heading_drift", float(heading_rest - heading0))
    print("SUMMARY T_OP=%d s_trig=%.1f s_close=%.1f s_rest=%.1f drift=%.1f stop=%d start=%d" % (
        T_OP, s_trig_actual, s_closest, s_rest, heading_rest - heading0, stop_reason, start_gap))
finally:
    try:
        for _n, _m in motors:
            _m.brake()
    except Exception:
        pass
    print('{"event":"end"}')
