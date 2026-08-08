# =============================================================================
# RUN-3  --  Calibration + unit-verification program, REV C   (Pybricks MicroPython)
#
# Supersedes RUN-2 (AR-02). Four changes, one per finding:
#   1. Ranger A is NOT CONSTRUCTED. B is the sole forward channel. Not
#      constructing A also stops the runtime polling it, which tests the
#      crosstalk hypothesis for free.            (AR-02 findings A, B)
#   2. SPEED_CMD is set BELOW motor saturation so the speed controllers have
#      headroom, plus proportional heading hold. Above saturation a heading
#      correction has no authority at all -- that is the saturation trap.
#      The correction SIGN is unknown a priori (which motor is on which side is
#      not known), so it is measured by a differential probe. A wrong sign would
#      be positive feedback; the gross-yaw guard is the backstop against that.
#                                                 (AR-02 finding C)
#   3. Passive brake() replaces plugging. 59 mm of wheel slip made S
#      unrepeatable and destroyed the odometric cross-check. (AR-02 finding D)
#   4. Telemetry cut to ~43 lines. Each stdout write blocks ~240 ms, so lines
#      are a hard budget, not an afterthought.     (AR-02 finding E)
#
# Values are emitted in RAW units (motor degrees, mm of reading) wherever the
# host would otherwise need K_MM_PER_DEG, so that no prior is baked into the
# data K is being calibrated FROM.
# =============================================================================

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

TRIG_GAP      = 100.0    # mm TRUE gap. Detuned for RUN-4 (design point is 46 mm);
                         # n_S_samples = 1, so the low tail is not yet worth betting.
B_OFFSET      = -119.125 # mm  M1: g = r - b, so R0_true = R0_reading - B_OFFSET
K_MM_PER_DEG  = 0.5030   # mm/deg  M1-anchored over an 828 mm baseline
V_NOM_MM_S    = 381
XCHECK_MM     = 200.0    # ranger may sit this far ABOVE the prediction (its lag);
                         # falling BELOW it by that much is the fault signature
TRAVEL_MARGIN = 60.0     # mm  absolute travel cap beyond the trigger point

P_RB, P_ML, P_MR = Port.B, Port.C, Port.D   # ranger A, rear ranger, colour NOT constructed

SPEED_CMD     = 750      # deg/s  BELOW the ~820 deg/s saturated speed, so both regulate
HEAD_GAIN     = 7.0      # deg/s of motor speed per deg of heading error;
                         # derived from a 0.3 s closed-loop time constant,
                         # tau = W_t / (2*g*k*57.3), robust over W_t 90-200 mm
CORR_MAX      = 120.0    # deg/s  correction authority clamp
PROBE_CMD     = 300
PROBE_MS      = 300
YAW_PROBE_CMD = 250
YAW_PROBE_MS  = 200
PROBE_YAW_MAX = 8.0
PROBE_DD_MIN  = 12.0
HEAD_ABORT    = 15.0

ARM_DEG       = 400      # raised from 150: the wrong-way check reads the RANGER, which lags
LOOP_MS       = 10
STOP_MS       = 5
T_LIMIT_MULT  = 3.0
STALE_MS      = 250
WRONGWAY_MM   = 30       # ranger must show this much closure by ARM
ACCEL_LIM     = 3000
CRUISE_FROM   = 300      # deg of travel after which we count as cruising
D_MIN         = 20
D_MAX         = 1990
NBUF          = 260

hub   = PrimeHub()
clock = StopWatch()


def emit(sensor, value):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'
                 % (clock.time(), sensor, value))


bt = [0] * NBUF
bd = [0] * NBUF
bo = [0] * NBUF
n  = 0

mL = mR = rB = None
sgnL, sgnR = 1, -1
yaw_sign = 1.0


def rng():
    d = rB.distance()
    if d is not None and D_MIN <= d <= D_MAX:
        return d
    return None


invalid_total = 0


def dwell(count):
    """Mean and spread over `count` samples, rejecting implausible readings.

    An unfiltered mean is how a single dropout becomes a 91 mm error in R0 --
    and R0 sizes the backstops. Rejects are counted: with ranger A no longer
    constructed, a reject count of zero is direct evidence for the crosstalk
    hypothesis in AR-02.
    """
    global invalid_total
    acc = 0
    ok = 0
    lo, hi = 9999, 0
    for _ in range(count):
        d = rB.distance()
        if d is not None and D_MIN <= d <= D_MAX:
            acc += d
            ok += 1
            lo = d if d < lo else lo
            hi = d if d > hi else hi
        else:
            invalid_total += 1
        wait(22)
    if ok == 0:
        return None, 0.0, 0
    return acc / ok, hi - lo, ok


def stop_motors():
    try:
        mL.brake()
        mR.brake()
    except Exception:
        pass


def drive(v_cmd, use_hold):
    """Command both motors, optionally with proportional heading hold."""
    if use_hold:
        c = yaw_sign * HEAD_GAIN * hub.imu.heading()
        if c > CORR_MAX:
            c = CORR_MAX
        elif c < -CORR_MAX:
            c = -CORR_MAX
    else:
        c = 0.0
    mL.run(sgnL * (v_cmd - c))
    mR.run(sgnR * (v_cmd + c))


try:
    # ---------------- PHASE 0 : CONFIGURATION + PROBES ----------------------
    wait(900)
    try:
        hub.imu.reset_heading(0)
    except Exception:
        pass

    ok = 1
    try:
        mL = Motor(P_ML)
        mR = Motor(P_MR)
        rB = UltrasonicSensor(P_RB)
    except Exception:
        ok = 0
    emit("map_assert", ok)
    if not ok:
        raise SystemExit
    for m in (mL, mR):
        try:
            m.control.limits(acceleration=ACCEL_LIM)
        except Exception:
            pass

    # -- direction probe (heading-gated, as REV B) --------------------------
    h0 = hub.imu.heading()
    d0 = rng()
    if d0 is None:
        d0 = 0
    mL.run(sgnL * PROBE_CMD)
    mR.run(sgnR * PROBE_CMD)
    wait(PROBE_MS)
    stop_motors()
    wait(250)
    dh = hub.imu.heading() - h0
    d1 = rng()
    if d1 is None:
        d1 = d0
    dd = d1 - d0
    mL.run(-sgnL * PROBE_CMD)
    mR.run(-sgnR * PROBE_CMD)
    wait(PROBE_MS)
    stop_motors()
    wait(300)
    emit("probe_dheading", dh)
    emit("probe_ddist", dd)
    if abs(dh) > PROBE_YAW_MAX:
        emit("polarity_fail", 1)
        raise SystemExit
    if dd > PROBE_DD_MIN:
        sgnL = -sgnL
        sgnR = -sgnR
    elif dd > -PROBE_DD_MIN:
        emit("direction_ambiguous", dd)
        raise SystemExit
    emit("sgn_left", sgnL)

    # -- yaw-sign probe: which way does a differential command turn us? -----
    # Without this the heading correction could be positive feedback.
    h0 = hub.imu.heading()
    mL.run(sgnL * YAW_PROBE_CMD)
    mR.run(-sgnR * YAW_PROBE_CMD)
    wait(YAW_PROBE_MS)
    stop_motors()
    wait(200)
    dhy = hub.imu.heading() - h0
    mL.run(-sgnL * YAW_PROBE_CMD)
    mR.run(sgnR * YAW_PROBE_CMD)
    wait(YAW_PROBE_MS)
    stop_motors()
    wait(300)
    yaw_sign = 1.0 if dhy > 0 else -1.0
    emit("yaw_probe_dh", dhy)

    try:
        hub.imu.reset_heading(0)
    except Exception:
        pass

    # ---------------- PHASE A : STATIC PRE-RUN ------------------------------
    wait(300)
    R0, R0_spread, R0_n = dwell(12)
    if R0 is None:
        emit("R0_invalid", 1)
        raise SystemExit
    emit("R0_b", R0)
    emit("R0_b_spread", R0_spread)

    # The anchor. This static, lag-free dwell is now the single most
    # load-bearing measurement in the run (CMP-15).
    R0_true = R0 - B_OFFSET
    emit("R0_true", R0_true)
    o0 = 0.5 * (sgnL * mL.angle() + sgnR * mR.angle())
    trig_odo = (R0_true - TRIG_GAP) / K_MM_PER_DEG
    travel_lim_d = trig_odo + TRAVEL_MARGIN / K_MM_PER_DEG
    t_limit_ms = T_LIMIT_MULT * 1000.0 * (R0_true - TRIG_GAP) / V_NOM_MM_S + 800.0
    emit("trig_odo_deg", trig_odo)

    # ---------------- PHASE B : HOT PATH ------------------------------------
    last_raw = R0
    prev_raw = R0
    last_t = clock.time()
    t_start = last_t
    armed = False
    reason = 0
    d_T = 0.0
    t_fire = 0
    hmax = 0.0
    swL = swR = 0.0
    ncr = 0
    d_go = R0_true
    hold_max = 0
    hold_sum = 0
    jump_max = 0
    n_chg = 0
    t_chg = last_t

    drive(SPEED_CMD, False)

    while True:
        t = clock.time()
        raw = rng()
        if raw is not None:
            if raw != last_raw:
                last_raw = raw
                last_t = t
            stale = 0
        else:
            stale = t - last_t

        aL = mL.angle()
        aR = mR.angle()
        dth = 0.5 * (sgnL * aL + sgnR * aR) - o0
        wL = sgnL * mL.speed()
        wR = sgnR * mR.speed()
        v = 0.5 * (wL + wR) * K_MM_PER_DEG
        th = hub.imu.heading()
        if th > hmax:
            hmax = th
        elif -th > hmax:
            hmax = -th

        # ranger dynamics statistics (AR-03 open question, 4 scalars not a trace)
        if raw is not None and raw != prev_raw:
            hold = t - t_chg
            if hold > hold_max:
                hold_max = hold
            hold_sum += hold
            n_chg += 1
            j = raw - prev_raw
            if j < 0:
                j = -j
            if j > jump_max:
                jump_max = j
            t_chg = t
            prev_raw = raw

        # ODOMETRIC TRIGGER QUANTITY -- lag-free, high rate
        d_go = R0_true - dth * K_MM_PER_DEG

        if dth > CRUISE_FROM:
            swL += wL
            swR += wR
            ncr += 1

        if n < NBUF:
            bt[n] = t
            bd[n] = raw if raw is not None else 0
            bo[n] = int(dth)
            n += 1

        if not armed and dth > ARM_DEG:
            armed = True
            if last_raw > R0 - WRONGWAY_MM:
                reason = 4
                d_T = d_go
                t_fire = t
                break
        if armed and d_go <= TRIG_GAP:
            reason = 1
            d_T = d_go
            t_fire = t
            break
        # ranger one-sided cross-check, applied only while the prediction is
        # still inside the ranger's usable range
        pred_r = d_go + B_OFFSET
        if raw is not None and pred_r > D_MIN + 20 and raw < pred_r - XCHECK_MM:
            reason = 7
            d_T = d_go
            t_fire = t
            break
        if stale > STALE_MS and (d_go + B_OFFSET) > D_MIN + 20:
            reason = 2
            d_T = d_go
            t_fire = t
            break
        if th > HEAD_ABORT or th < -HEAD_ABORT:
            reason = 6
            d_T = d_go
            t_fire = t
            break
        if dth > travel_lim_d:
            reason = 3
            d_T = d_go
            t_fire = t
            break
        if t - t_start > t_limit_ms:
            reason = 5
            d_T = d_go
            t_fire = t
            break

        drive(SPEED_CMD, True)
        wait(LOOP_MS)

    h_trig = hub.imu.heading()
    odo_trig = 0.5 * (sgnL * mL.angle() + sgnR * mR.angle()) - o0

    # ---- FUN-5: passive braking, no retreat --------------------------------
    stop_motors()
    while clock.time() - t_fire < 400:
        if n < NBUF:
            r2 = rng()
            bt[n] = clock.time()
            bd[n] = r2 if r2 is not None else 0
            bo[n] = int(0.5 * (sgnL * mL.angle() + sgnR * mR.angle()) - o0)
            n += 1
        wait(STOP_MS)

    # ---------------- PHASE C : REST DWELL ----------------------------------
    r_rest, rest_spread, rest_n = dwell(16)
    if r_rest is None:
        r_rest, rest_spread, rest_n = 0.0, 0.0, 0
    odo_rest = 0.5 * (sgnL * mL.angle() + sgnR * mR.angle()) - o0

    # ---------------- PHASE D : SCALARS (most critical first) ---------------
    emit("trigger_reason", reason)
    emit("d_go_trigger", d_T)
    emit("r_rest_b", r_rest)
    emit("odo_trigger_deg", odo_trig)
    emit("odo_rest_deg", odo_rest)
    emit("S_odo_deg", odo_rest - odo_trig)
    emit("g_est_final", R0_true - odo_rest * K_MM_PER_DEG)   # SYS-8 onboard estimate
    emit("k_static", (R0 - r_rest) / odo_rest if odo_rest else 0.0)
    emit("rng_hold_max_ms", hold_max)
    emit("rng_hold_mean_ms", hold_sum / n_chg if n_chg else 0.0)
    emit("rng_jump_max_mm", jump_max)
    emit("rng_n_changes", n_chg)
    emit("heading_trigger", h_trig)
    emit("heading_rest", hub.imu.heading())
    emit("heading_max", hmax)
    emit("cruise_wL", swL / ncr if ncr else 0.0)
    emit("cruise_wR", swR / ncr if ncr else 0.0)
    emit("cruise_n", ncr)
    emit("rest_b_spread", rest_spread)
    emit("t_trigger", t_fire)
    emit("t_hot_start", t_start)
    emit("samples", n)
    emit("dwell_invalid", invalid_total)

    # ---------------- PHASE F : SHORT TRACE (12 lines) ----------------------
    step = n // 6
    if step < 1:
        step = 1
    i = 0
    while i < n:
        stdout.write('{"timestamp_ms":%d,"sensor":"d_b","value":%f}\n' % (bt[i], bd[i]))
        i += step
    i = 0
    while i < n:
        stdout.write('{"timestamp_ms":%d,"sensor":"odo_deg","value":%f}\n' % (bt[i], bo[i]))
        i += step

finally:
    stop_motors()
    stdout.write('{"event":"end"}\n')
