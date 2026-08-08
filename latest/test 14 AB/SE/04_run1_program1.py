# =============================================================================
# RUN-1  --  Calibration + unit-verification program   (Pybricks MicroPython)
#
# TEST-LIKE-YOU-FLY STRUCTURE.  Phase B below is the OPERATION program's hot path,
# byte-for-byte.  Everything else is characterization scaffolding that runs either
# BEFORE the motors are first commanded (Phase 0/A) or AFTER they have stopped
# (Phase C/E/F).  No characterization logging is woven into the hot path (FUN-10):
# the loop writes to pre-allocated buffers and every byte of stdout is emitted
# after motion ceases.
#
# The operation program differs from this file in exactly these ways:
#   1. Phase 0 (discovery) is replaced by the constant device map this run yields,
#      plus an assertion that the map still holds.
#   2. Phase E (creep to close range) is deleted.
#   3. Four constants take their calibrated values: R_TRIG, TRAVEL_LIM_D,
#      K_MM_PER_DEG, FWD_AXIS.
# The control loop, trigger rule, stop maneuver and buffer skeleton are identical.
#
# RUN-1 RISK POSTURE.  k is unbound, so the odometric backstop cannot yet be sized
# (it is either pre-emptive or useless depending on k).  RUN-1 protection is
# therefore carried by: a very conservative R_TRIG (600 mm, above the worst-case
# prior stop distance of 457 mm), the ranger-staleness guard (k-free), the
# wrong-way guard, and the time limit.  SYS-7 is verified at the verification run,
# with k bound.
# =============================================================================

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

# ------------------------------------------------------------------ constants
R_TRIG        = 600      # mm    * calibrated for operation
K_MM_PER_DEG  = 0.575    # mm/deg* calibrated for operation (prior mid here)
V_NOM_MM_S    = 517      # mm/s  * calibrated for operation (prior mid here)
S_CAL_MM      = 61       # mm    * calibrated for operation; fallback estimate only
DELTA_BS_MM   = 25       # mm      backstop allowance beyond the nominal trigger
K_BACK_MM_PER_DEG = 0.35 # mm/deg* LOWER BOUND of k, used ONLY to convert the backstop
                         #         allowance into motor degrees.  Using the lower bound
                         #         makes the odometric backstop conservative in the
                         #         NON-PRE-EMPTING direction.  In RUN-1, k spans 2.3x, so
                         #         the backstop cannot be both non-pre-empting and
                         #         protective; it is deliberately made the former, and
                         #         RUN-1 protection is carried by the k-free staleness
                         #         guard.  In operation this takes the calibrated k.
FWD_AXIS      = -1       # index * discovered in Phase 0 here, constant in operation

# The travel and time backstops are NOT flashed constants.  They are derived in
# Phase A from the rover's own static R0 measurement, because the travel to the
# trigger is (R0 - R_TRIG) in the SENSOR frame -- sizing them from an assumed
# start gap silently mis-sizes them by the range offset b and lets a backstop
# pre-empt the primary trigger.

ARM_DEG       = 150      # arm the trigger only after this much rotation
LOOP_MS       = 10       # hot-path period
STOP_MS       = 5        # stop-window sampling period
T_LIMIT_MULT  = 3.0      # hot-path time backstop = this x nominal approach time
STALE_MS      = 250      # no valid ranger sample for this long -> stop (FUN-3/6)
WRONGWAY_MM   = 25       # must have closed at least this much by ARM (FUN-3)
SPEED_CMD     = 2000     # deg/s, saturates to the controller ceiling (SYS-4)
ACCEL_LIM     = 3000     # deg/s^2, so max speed is reached early in the run-up
D_MIN         = 20       # mm, plausibility bounds on any ranger sample
D_MAX         = 1990
NBUF          = 260

CREEP1_CMD    = 600      # deg/s, RUN-1 only, coarse descent
CREEP1_TARGET = 250      # mm reading, RUN-1 only
CREEP2_CMD    = 150      # deg/s, RUN-1 only, fine descent -> second-speed stop point
CREEP2_TARGET = 55       # mm reading, RUN-1 only
CREEP_MS      = 2600     # per stage

hub   = PrimeHub()
clock = StopWatch()


def emit(sensor, value):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'
                 % (clock.time(), sensor, value))


# ------------------------------------------------------- pre-allocated buffers
bt = [0] * NBUF      # hub ms
ba = [0] * NBUF      # ranger A raw
bb = [0] * NBUF      # ranger B raw
bo = [0] * NBUF      # odometry, deg (forward-positive, both-motor mean)
bh = [0] * NBUF      # heading, centideg
bx = [0] * NBUF      # forward-axis acceleration, mm/s^2
n  = 0

motors = []
rangers = []
colors = []
mL = mR = None
sgnL = sgnR = 1
rA = rB = rRear = cSense = None


def valid(d):
    return d is not None and D_MIN <= d <= D_MAX


def fused():
    """min() of the plausible forward readings; None if neither is plausible.

    min() fails safe: a spuriously low reading triggers early, a spuriously high
    one is over-ridden by its partner.  The constant bias of min-fusion is
    absorbed by the calibration of the range offset b.
    """
    a = rA.distance()
    b = rB.distance()
    va, vb = valid(a), valid(b)
    if va and vb:
        return a if a < b else b
    if va:
        return a
    if vb:
        return b
    return None


def stop_motors():
    try:
        mL.brake()
        mR.brake()
    except Exception:
        pass


try:
    # =========================================================================
    # PHASE 0 -- DISCOVERY                                   (RUN-1 ONLY)
    # =========================================================================
    wait(900)                        # let the IMU settle before it is trusted
    try:
        hub.imu.reset_heading(0)
    except Exception:
        pass

    for pt in (Port.A, Port.B, Port.C, Port.D, Port.E, Port.F):
        got = 0
        try:
            motors.append((pt, Motor(pt)))
            got = 1
        except Exception:
            pass
        if not got:
            try:
                rangers.append((pt, UltrasonicSensor(pt)))
                got = 2
            except Exception:
                pass
        if not got:
            try:
                colors.append((pt, ColorSensor(pt)))
                got = 3
            except Exception:
                pass
        emit("port_kind", got)

    emit("n_motors", len(motors))
    emit("n_rangers", len(rangers))
    emit("n_colors", len(colors))
    if len(motors) < 2 or len(rangers) < 2:
        # Port-claim semantics or a cable fault. The port map has already been
        # emitted, so this run still yields the one thing needed to hard-code the
        # map next time -- a diagnostic, not a wasted run.
        emit("discovery_fail", 1)
        raise SystemExit

    mL = motors[0][1]
    mR = motors[1][1]
    for _, m in motors:
        try:
            m.control.limits(acceleration=ACCEL_LIM)
        except Exception:
            pass
    try:
        lim = mL.control.limits()
        emit("ctrl_speed_limit", lim[0])
        emit("ctrl_accel_limit", lim[1])
    except Exception:
        pass
    if colors:
        cSense = colors[0][1]

    # -- identify the forward pair: the two rangers that agree at rest ---------
    rd = []
    bi, bj = 0, 1
    for pt, s in rangers:
        acc = 0
        for _ in range(5):
            acc += s.distance()
            wait(20)
        rd.append(acc / 5.0)
        emit("scan_range", rd[-1])

    if len(rangers) >= 3:
        best, bi, bj = 1e9, 0, 1
        for i in range(len(rd)):
            for j in range(i + 1, len(rd)):
                dif = abs(rd[i] - rd[j])
                if dif < best:
                    best, bi, bj = dif, i, j
        rA = rangers[bi][1]
        rB = rangers[bj][1]
        for kx in range(len(rangers)):
            if kx != bi and kx != bj:
                rRear = rangers[kx][1]
    else:
        rA = rangers[0][1]
        rB = rangers[-1][1]
    emit("pair_idx_a", bi)
    emit("pair_idx_b", bj)

    # -- relative polarity and forward direction ------------------------------
    def probe(sl, sr, ms, spd):
        h0 = hub.imu.heading()
        d0 = fused()
        if d0 is None:
            d0 = 0
        mL.run(sl * spd)
        mR.run(sr * spd)
        wait(ms)
        stop_motors()
        wait(200)
        h1 = hub.imu.heading()
        d1 = fused()
        if d1 is None:
            d1 = d0
        mL.run(-sl * spd)          # undo
        mR.run(-sr * spd)
        wait(ms)
        stop_motors()
        wait(250)
        return h1 - h0, d1 - d0

    dh, dd = probe(1, 1, 250, 200)
    emit("probe1_dheading", dh)
    emit("probe1_ddist", dd)
    if abs(dh) > 10 and abs(dd) < 10:
        sgnR = -1                                   # mirrored mounting
        dh, dd = probe(sgnL, sgnR, 250, 200)
        emit("probe2_dheading", dh)
        emit("probe2_ddist", dd)
    if dd > 10:                                     # positive drove us away
        sgnL = -sgnL
        sgnR = -sgnR
    emit("sgn_left", sgnL)
    emit("sgn_right", sgnR)

    # -- IMU provenance: which axis responds to a deliberate yaw? -------------
    w0 = hub.imu.angular_velocity()
    mL.run(sgnL * 250)
    mR.run(-sgnR * 250)
    wmax, widx = 0, 0
    for _ in range(6):
        w = hub.imu.angular_velocity()
        for i in range(3):
            if abs(w[i]) > wmax:
                wmax, widx = abs(w[i]), i
        wait(25)
    stop_motors()
    wait(120)
    hy = hub.imu.heading()
    mL.run(-sgnL * 250)
    mR.run(sgnR * 250)
    wait(150)
    stop_motors()
    wait(250)
    emit("yaw_axis_idx", widx)
    emit("yaw_axis_rate", wmax)
    emit("yaw_probe_heading", hy)

    # forward acceleration axis: the one that moved during the translation probe
    ax = hub.imu.acceleration()
    for i in range(3):
        emit("accel_rest_axis", ax[i])
    FWD_AXIS = 0 if widx != 0 else 1     # yaw axis is vertical; pick a horizontal one

    # =========================================================================
    # PHASE A -- STATIC PRE-RUN SAMPLING                     (BOTH PROGRAMS)
    # =========================================================================
    try:
        hub.imu.reset_heading(0)
    except Exception:
        pass
    wait(300)
    sa = sb = 0
    mna, mxa, mnb, mxb = 9999, 0, 9999, 0
    for _ in range(12):
        da = rA.distance()
        db = rB.distance()
        sa += da
        sb += db
        mna = da if da < mna else mna
        mxa = da if da > mxa else mxa
        mnb = db if db < mnb else mnb
        mxb = db if db > mxb else mxb
        wait(20)
    R0a = sa / 12.0
    R0b = sb / 12.0
    R0 = R0a if R0a < R0b else R0b
    emit("R0_a", R0a)
    emit("R0_b", R0b)
    emit("R0_fused", R0)
    emit("R0_a_spread", mxa - mna)
    emit("R0_b_spread", mxb - mnb)
    emit("R0_pair_offset", R0b - R0a)
    if rRear is not None:
        emit("rear_start", rRear.distance())
    if cSense is not None:
        emit("reflect_start", cSense.reflection())

    a0L = mL.angle()
    a0R = mR.angle()
    o0 = 0.5 * (sgnL * a0L + sgnR * a0R)

    # runtime-derived backstops (FUN-6, FUN-7), sized in the sensor frame
    travel_lim_d = (R0 - R_TRIG + DELTA_BS_MM) / K_BACK_MM_PER_DEG
    if travel_lim_d < 0:
        travel_lim_d = 0
    t_limit_ms = T_LIMIT_MULT * 1000.0 * (R0 - R_TRIG) / V_NOM_MM_S + 800.0
    emit("travel_limit_deg", travel_lim_d)
    emit("time_limit_ms", t_limit_ms)

    # =========================================================================
    # PHASE B -- HOT PATH                    (IDENTICAL IN THE OPERATION PROGRAM)
    # =========================================================================
    last_raw = R0
    last_t = clock.time()
    t_start = last_t
    armed = False
    reason = 0
    d_T = 0.0
    t_fire = 0

    mL.run(sgnL * SPEED_CMD)
    mR.run(sgnR * SPEED_CMD)

    while True:
        t = clock.time()
        raw = fused()
        if raw is not None:
            if raw != last_raw:
                last_raw = raw
                last_t = t
            stale = 0
        else:
            stale = t - last_t

        dth = 0.5 * (sgnL * mL.angle() + sgnR * mR.angle()) - o0
        w = 0.5 * (sgnL * mL.speed() + sgnR * mR.speed())
        v = w * K_MM_PER_DEG                                   # mm/s

        # FUN-2: current-instant estimate -- the last raw sample, advanced by the
        # travel since that sample was taken.  Always <= last_raw, so any error in
        # v triggers EARLY.
        d_est = last_raw - v * (t - last_t) * 0.001

        if n < NBUF:
            bt[n] = t
            ba[n] = rA.distance()
            bb[n] = rB.distance()
            bo[n] = int(dth)
            bh[n] = int(hub.imu.heading() * 100)
            bx[n] = int(hub.imu.acceleration()[FWD_AXIS])
            n += 1

        if not armed and dth > ARM_DEG:
            armed = True
            if last_raw > R0 - WRONGWAY_MM:      # not closing on anything
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
        wait(LOOP_MS)

    # ---- FUN-5: maximum braking effort, no retreat --------------------------
    # Plugging (full reverse duty) until wheel speed reaches zero, then a passive
    # brake.  Chosen over a position hold because a hold retreats after stopping,
    # which would separate the minimum clearance (SYS-1) from the final gap
    # (SYS-3) and force the objective to be scored on the worse of the two.
    mL.dc(-100 * sgnL)
    mR.dc(-100 * sgnR)
    while True:
        t = clock.time()
        if n < NBUF:
            bt[n] = t
            ba[n] = rA.distance()
            bb[n] = rB.distance()
            bo[n] = int(0.5 * (sgnL * mL.angle() + sgnR * mR.angle()) - o0)
            bh[n] = int(hub.imu.heading() * 100)
            bx[n] = int(hub.imu.acceleration()[FWD_AXIS])
            n += 1
        wl = sgnL * mL.speed()
        wr = sgnR * mR.speed()
        if (wl <= 0 and wr <= 0) or (t - t_fire) > 500:
            break
        wait(STOP_MS)
    stop_motors()

    # =========================================================================
    # PHASE C -- REST DWELL                                  (BOTH PROGRAMS)
    # =========================================================================
    wait(400)
    sa = sb = 0
    mna, mxa, mnb, mxb = 9999, 0, 9999, 0
    for _ in range(16):
        da = rA.distance()
        db = rB.distance()
        sa += da
        sb += db
        mna = da if da < mna else mna
        mxa = da if da > mxa else mxa
        mnb = db if db < mnb else mnb
        mxb = db if db > mxb else mxb
        wait(25)
    ra_rest = sa / 16.0
    rb_rest = sb / 16.0
    r_rest = ra_rest if ra_rest < rb_rest else rb_rest
    o_rest = 0.5 * (sgnL * mL.angle() + sgnR * mR.angle()) - o0
    h_rest = hub.imu.heading()

    # =========================================================================
    # PHASE D -- PRIMARY SCALARS FIRST (truncation-tolerant emission order)
    # =========================================================================
    emit("trigger_reason", reason)
    emit("d_trigger", d_T)
    emit("t_trigger", t_fire)
    emit("r_rest_a", ra_rest)
    emit("r_rest_b", rb_rest)
    emit("r_rest_fused", r_rest)
    emit("rest_a_spread", mxa - mna)
    emit("rest_b_spread", mxb - mnb)
    emit("rest_pair_offset", rb_rest - ra_rest)
    emit("S_ranger", d_T - r_rest)                    # composite stop distance
    # SYS-8 estimate channels.  The fallback MUST use the calibrated S constant:
    # using this run's own (d_T - r_rest) would be circular, because that quantity
    # is computed FROM r_rest and collapses back to it when the ranger has floored.
    emit("gap_est_primary_raw", r_rest)               # host subtracts b
    emit("gap_est_fallback_raw", d_T - S_CAL_MM)      # host subtracts b
    emit("gap_est_channel", 1 if r_rest > D_MIN + 20 else 2)
    emit("odo_at_trigger_deg", bo[n - 1] if n else 0)
    emit("odo_at_rest_deg", o_rest)
    emit("heading_at_rest", h_rest)
    emit("samples_buffered", n)
    if rRear is not None:
        emit("rear_rest", rRear.distance())
    if cSense is not None:
        emit("reflect_rest", cSense.reflection())

    # find the trigger index and report the stop window from odometry
    itrig = 0
    for i in range(n):
        if bt[i] >= t_fire:
            itrig = i
            break
    emit("odo_trigger_idx", itrig)
    emit("S_odometry", (o_rest - bo[itrig]) * K_MM_PER_DEG)
    emit("heading_at_trigger", bh[itrig] / 100.0)

    # =========================================================================
    # PHASE E -- CREEP TO CLOSE RANGE                        (RUN-1 ONLY)
    # =========================================================================
    ocreep = 0.5 * (sgnL * mL.angle() + sgnR * mR.angle())
    creep_reason = 0
    d2_trigger = 0.0

    for stage in (1, 2):
        cmd = CREEP1_CMD if stage == 1 else CREEP2_CMD
        tgt = CREEP1_TARGET if stage == 1 else CREEP2_TARGET
        base = 0.5 * (sgnL * mL.angle() + sgnR * mR.angle())
        cap_deg = (r_rest - tgt - 5.0) / K_MM_PER_DEG
        if cap_deg < 0:
            cap_deg = 0
        t_creep = clock.time()
        mL.run(sgnL * cmd)
        mR.run(sgnR * cmd)
        while True:
            t = clock.time()
            raw = fused()
            d = 0.5 * (sgnL * mL.angle() + sgnR * mR.angle()) - base
            if raw is not None and raw <= tgt:
                creep_reason = stage * 10 + 1
                d2_trigger = raw
                break
            if d > cap_deg:
                creep_reason = stage * 10 + 2
                break
            if t - t_creep > CREEP_MS:
                creep_reason = stage * 10 + 3
                break
            wait(10)
        stop_motors()
        wait(500 if stage == 2 else 250)

    wait(200)
    sa = sb = 0
    mna, mxa, mnb, mxb = 9999, 0, 9999, 0
    for _ in range(16):
        da = rA.distance()
        db = rB.distance()
        sa += da
        sb += db
        mna = da if da < mna else mna
        mxa = da if da > mxa else mxa
        mnb = db if db < mnb else mnb
        mxb = db if db > mxb else mxb
        wait(25)
    creep_a = sa / 16.0
    creep_b = sb / 16.0
    emit("creep_reason", creep_reason)
    emit("creep_r_a", creep_a)
    emit("creep_r_b", creep_b)
    emit("creep_r_fused", creep_a if creep_a < creep_b else creep_b)
    emit("creep_a_spread", mxa - mna)
    emit("creep_b_spread", mxb - mnb)
    emit("creep_pair_offset", creep_b - creep_a)
    emit("creep2_d_trigger", d2_trigger)
    emit("creep_travel_mm",
         (0.5 * (sgnL * mL.angle() + sgnR * mR.angle()) - ocreep) * K_MM_PER_DEG)
    emit("creep_heading", hub.imu.heading())
    if rRear is not None:
        emit("rear_creep", rRear.distance())
    if cSense is not None:
        emit("reflect_creep", cSense.reflection())

    # =========================================================================
    # PHASE F -- BUFFER DUMP (downsampled; least critical, emitted last)
    # =========================================================================
    stepA = 4 if itrig > 60 else 2

    i = 0
    while i < n:
        st = 2 if i >= itrig else stepA
        va = ba[i]
        vb = bb[i]
        f = va if (D_MIN <= va <= D_MAX and va < vb) else vb
        stdout.write('{"timestamp_ms":%d,"sensor":"d_fwd","value":%f}\n' % (bt[i], f))
        i += st

    i = 0
    while i < n:
        st = 4 if i >= itrig else stepA * 2
        stdout.write('{"timestamp_ms":%d,"sensor":"odo_deg","value":%f}\n' % (bt[i], bo[i]))
        i += st

    i = 0
    while i < n:
        stdout.write('{"timestamp_ms":%d,"sensor":"heading","value":%f}\n'
                     % (bt[i], bh[i] / 100.0))
        i += 12

    i = itrig
    while i < n:
        stdout.write('{"timestamp_ms":%d,"sensor":"accel_fwd","value":%f}\n' % (bt[i], bx[i]))
        i += 3

finally:
    stop_motors()
    stdout.write('{"event":"end"}\n')
