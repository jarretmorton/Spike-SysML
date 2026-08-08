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

R_TRIG        = 600      # mm   unchanged: S is still unbound
K_MM_PER_DEG  = 0.482    # mm/deg  RUN-2 creep estimate, used only for backstop sizing
V_NOM_MM_S    = 360
DELTA_BS_MM   = 25
K_BACK_MM_PER_DEG = 0.35

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

ARM_DEG       = 150
LOOP_MS       = 10
STOP_MS       = 5
T_LIMIT_MULT  = 3.0
STALE_MS      = 250
WRONGWAY_MM   = 25
ACCEL_LIM     = 3000
CRUISE_FROM   = 300      # deg of travel after which we count as cruising
D_MIN         = 20
D_MAX         = 1990
NBUF          = 260

CREEP1_CMD    = 500
CREEP1_TARGET = 250
CREEP2_CMD    = 150
CREEP2_TARGET = 60
CREEP_MS      = 2600

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
    sb = 0
    mnb, mxb = 9999, 0
    for _ in range(12):
        db = rB.distance()
        sb += db
        mnb = db if db < mnb else mnb
        mxb = db if db > mxb else mxb
        wait(20)
    R0 = sb / 12.0
    emit("R0_b", R0)
    emit("R0_b_spread", mxb - mnb)

    o0 = 0.5 * (sgnL * mL.angle() + sgnR * mR.angle())
    travel_lim_d = (R0 - R_TRIG + DELTA_BS_MM) / K_BACK_MM_PER_DEG
    if travel_lim_d < 0:
        travel_lim_d = 0
    t_limit_ms = T_LIMIT_MULT * 1000.0 * (R0 - R_TRIG) / V_NOM_MM_S + 800.0
    emit("travel_limit_deg", travel_lim_d)

    # ---------------- PHASE B : HOT PATH ------------------------------------
    last_raw = R0
    last_t = clock.time()
    t_start = last_t
    armed = False
    reason = 0
    d_T = 0.0
    t_fire = 0
    hmax = 0.0
    swL = swR = 0.0
    ncr = 0

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

        d_est = last_raw - v * (t - last_t) * 0.001

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
                d_T = d_est
                t_fire = t
                break
        if armed and d_est <= R_TRIG:
            reason = 1
            d_T = d_est
            t_fire = t
            break
        if stale > STALE_MS:
            reason = 2
            d_T = d_est
            t_fire = t
            break
        if th > HEAD_ABORT or th < -HEAD_ABORT:
            reason = 6
            d_T = d_est
            t_fire = t
            break
        if dth > travel_lim_d:
            reason = 3
            d_T = d_est
            t_fire = t
            break
        if t - t_start > t_limit_ms:
            reason = 5
            d_T = d_est
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
    sb = 0
    mnb, mxb = 9999, 0
    for _ in range(16):
        db = rB.distance()
        sb += db
        mnb = db if db < mnb else mnb
        mxb = db if db > mxb else mxb
        wait(25)
    r_rest = sb / 16.0
    odo_rest = 0.5 * (sgnL * mL.angle() + sgnR * mR.angle()) - o0

    # ---------------- PHASE D : SCALARS (most critical first) ---------------
    emit("trigger_reason", reason)
    emit("d_trigger", d_T)
    emit("r_rest_b", r_rest)
    emit("S_ranger", d_T - r_rest)
    emit("odo_trigger_deg", odo_trig)
    emit("odo_rest_deg", odo_rest)
    emit("S_odo_deg", odo_rest - odo_trig)
    emit("heading_trigger", h_trig)
    emit("heading_rest", hub.imu.heading())
    emit("heading_max", hmax)
    emit("cruise_wL", swL / ncr if ncr else 0.0)
    emit("cruise_wR", swR / ncr if ncr else 0.0)
    emit("cruise_n", ncr)
    emit("rest_b_spread", mxb - mnb)
    emit("t_trigger", t_fire)
    emit("t_hot_start", t_start)
    emit("samples", n)

    # ---------------- PHASE E : CREEP TO CLOSE RANGE ------------------------
    ocreep = 0.5 * (sgnL * mL.angle() + sgnR * mR.angle())
    creep_reason = 0
    for stage in (1, 2):
        cmd = CREEP1_CMD if stage == 1 else CREEP2_CMD
        tgt = CREEP1_TARGET if stage == 1 else CREEP2_TARGET
        base = 0.5 * (sgnL * mL.angle() + sgnR * mR.angle())
        cap_deg = (r_rest - tgt - 5.0) / K_MM_PER_DEG
        if cap_deg < 0:
            cap_deg = 0
        t_creep = clock.time()
        t_valid = t_creep
        drive(cmd, True)
        while True:
            t = clock.time()
            raw = rng()
            if raw is not None:
                t_valid = t
            d = 0.5 * (sgnL * mL.angle() + sgnR * mR.angle()) - base
            th = hub.imu.heading()
            if raw is not None and raw <= tgt:
                creep_reason = stage * 10 + 1
                break
            if d > cap_deg:
                creep_reason = stage * 10 + 2
                break
            if t - t_creep > CREEP_MS:
                creep_reason = stage * 10 + 3
                break
            # The creep runs far longer than the approach, so a slow heading
            # divergence has time to become a runaway.  Guard it here too, and
            # stop if the ranger stops seeing the wall -- losing the target is
            # exactly what a yaw runaway looks like from the ranger's side.
            if th > HEAD_ABORT or th < -HEAD_ABORT:
                creep_reason = stage * 10 + 4
                break
            if t - t_valid > STALE_MS:
                creep_reason = stage * 10 + 5
                break
            drive(cmd, True)
            wait(10)
        stop_motors()
        wait(500 if stage == 2 else 250)

    wait(300)
    sb = 0
    mnb, mxb = 9999, 0
    for _ in range(16):
        db = rB.distance()
        sb += db
        mnb = db if db < mnb else mnb
        mxb = db if db > mxb else mxb
        wait(25)
    emit("creep_reason", creep_reason)
    emit("creep_r_b", sb / 16.0)
    emit("creep_b_spread", mxb - mnb)
    emit("creep_travel_deg",
         0.5 * (sgnL * mL.angle() + sgnR * mR.angle()) - ocreep)
    emit("creep_heading", hub.imu.heading())

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
