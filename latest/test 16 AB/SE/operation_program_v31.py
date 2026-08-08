# =============================================================================
# WALLSTOP -- OPERATION PROGRAM  (locked candidate, rev D)
# sha of rev B predecessor: b172aed14c71b5ec (FALSIFIED, see VP v1.0 / AR-003)
#
# Verified by the re-verification run, then run UNCHANGED for the five scored
# operation runs.  Every constant is a calibrated value; nothing is tuned by feel.
#
# ESTIMATOR (rev D).  Ranger A is withdrawn ENTIRELY from the control path.
# Six distinct failure modes across three runs (AR-004): clamp, freeze, a
# ~190 mm zero error, a 9.4 % scale error, a +391 mm single-sample spike, and
# dropouts.  Its travel property, which rev C relied on, failed in C3.
#
#       g_est = S_START - odometry_travel                <- S operator-measured
#       brake when  g_est <= G + v * t_eff               <- StoppingDistance, live
#
# The C2 ground truth anchors the WHOLE chain end to end, so acceleration slip,
# braking skid and odometry scale error are all absorbed into the single
# calibrated constant t_eff, provided the profile repeats -- and it does:
# same commanded speed, same acceleration limit, same distance, every run.
#
# The C2 ground truth anchors the chain exactly:
#       1000 - 734.3 - 43.7 = 222.0 mm   vs 222 mm measured.
#
# FAILSAFES: left/right encoder divergence (the only surviving independent
# cross-check), heading sanity, odometry hard floor, watchdog, no-motion abort.
# NO ranger-based failsafe: a channel with six failure modes cannot gate a stop,
# and in C3 exactly such a check aborted a good run on one spurious sample.
#
# All logging is off the hot path; post-trigger emits sit after the rest loop
# so the braking transient is captured at full rate (AR-001 A-4).
# =============================================================================
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()


def emit(s, v):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'
                 % (clock.time(), s, v))


# ---------------------------------------------- CALIBRATED VALUES (GATE B) --
S_START = 1000.0    # TBD-20 start-line gap, OPERATOR-MEASURED (T4)   [mm]
G_TARGET = 23.0     # TBD-12 = 3 sigma per SYS-1                     [mm]
T_EFF = 0.09239     # TBD-06 Delta/v, anchored by the 222 mm truth    [s]
K_TRAVEL = 0.482    # TBD-03 travel per motor degree              [mm/deg]
U_CLAMP = 45.0      # TBD-09 ranger valid only ABOVE this            [mm]
ENC_DIVERGE_MAX = 60.0  # left/right encoder disagreement limit     [mm]
HEAD_ABORT = 15.0   # heading sanity abort                          [deg]
C_A = None          # WITHDRAWN (AR-003): zero moved 190 mm between runs
U_MAX_VALID = 1900.0
ACC_LIM = 4000      # deg/s^2, set explicitly for run-to-run repeatability
DIR_L = -1          # TBD-14 discovered in C1
DIR_R = 1
YAW_SIGN = 1.0      # TBD-14 driving motor L alone yaws heading positive
KP_HEAD = 8.0
TRIM_MAX = 200.0
DT_MS = 10

# --------------------------------------------------------------- failsafes --
FAILSAFE_MIN = 15.0  # odometry hard floor referenced to S
T_MAX_MS = 6000
U0_LO, U0_HI = 700.0, 1400.0     # DIAGNOSTIC band only -- non-blocking

# ----------------------------------------------------------------- buffers --
N = 500
try:
    from array import array
    def mkbuf(n):
        return array('f', [0.0] * n)
except Exception:
    def mkbuf(n):
        return [0.0] * n

T_ = mkbuf(N)
D1_ = mkbuf(N)
D2_ = mkbuf(N)
OD_ = mkbuf(N)
HD_ = mkbuf(N)
bi = 0


def logrow(t, d1, d2, od, hd):
    global bi
    if bi < N:
        T_[bi] = t
        D1_[bi] = d1
        D2_[bi] = d2
        OD_[bi] = od
        HD_[bi] = hd
        bi += 1


def med(xs):
    ys = sorted(xs)
    return ys[len(ys) // 2]


# ============================ INITIALISATION / SELF-CHECK (CMP-11, FUN-10) ===
ok = 1
try:
    mL = Motor(Port.C)
    mR = Motor(Port.D)
    sA = UltrasonicSensor(Port.A)
except Exception:
    ok = 0
    emit("ABORT_device_missing", 1)
    stdout.write('{"event":"end"}\n')
    raise SystemExit

sB = None
try:
    sB = UltrasonicSensor(Port.B)      # MONITOR ONLY -- never gates the stop
except Exception:
    emit("warn_rangerB_absent", 1)

for m in (mL, mR):
    try:
        m.control.limits(acceleration=ACC_LIM)
    except Exception:
        emit("warn_accel_limit", 0)
VCMD = mL.control.limits()[0]
emit("rated_max_speed_deg_s", VCMD)


def brake_all():
    try:
        mL.brake()
        mR.brake()
    except AttributeError:
        mL.stop()
        mR.stop()


def rB():
    if sB is None:
        return 2000.0
    try:
        return sB.distance()
    except Exception:
        return 2000.0


# ================================== CORE =====================================
mL.reset_angle(0)
mR.reset_angle(0)
hub.imu.reset_heading(0)
wait(250)

a = []
for _ in range(11):
    a.append(sA.distance())
    wait(15)
u0 = med(a)
g0 = S_START                      # absolute reference is the MEASURED start line
# rev D fix: the start-clearance gate is NON-BLOCKING.  It used the ranger,
# which is withdrawn; letting a channel with six failure modes abort a scored
# run contradicts the reason it was withdrawn.  In C2 it read 817 mm at a true
# 1000 mm, so it cannot detect mis-placement anyway.  Logged, never gated.
u0_flag = 1.0 if (u0 < U0_LO or u0 > U0_HI) else 0.0

t0 = clock.time()
mL.run(DIR_L * VCMD)
mR.run(DIR_R * VCMD)

reason = 0
moved_ok = False
nloop = 0
dtmin = 1e9
dtmax = 0.0
tprev = t0
u_last_valid = u0
od_last_valid = 0.0
n_invalid = 0
trig = None

while True:
    t = clock.time()
    dt = t - tprev
    if nloop > 2:
        if dt < dtmin:
            dtmin = dt
        if dt > dtmax:
            dtmax = dt
    tprev = t
    nloop += 1

    d1 = sA.distance()
    d2 = rB()
    angL = mL.angle() * DIR_L
    angR = mR.angle() * DIR_R
    od = 0.5 * (angL + angR) * K_TRAVEL
    hd = hub.imu.heading()
    logrow(t, d1, d2, od, hd)

    # rev D: the ranger is a MONITOR ONLY.  It gates nothing.
    valid = U_CLAMP < d1 < U_MAX_VALID
    if valid:
        u_last_valid = d1
        od_last_valid = od
    else:
        n_invalid += 1
    enc_div = (angL - angR) * K_TRAVEL           # surviving cross-check
    g_est = S_START - od                         # T4-anchored, odometry only

    v_meas = 0.5 * (abs(mL.speed()) + abs(mR.speed())) * K_TRAVEL
    thr = G_TARGET + T_EFF * v_meas              # StoppingDistance, live

    if od > 15.0:
        moved_ok = True

    if g_est <= thr:
        reason = 1
    elif enc_div > ENC_DIVERGE_MAX or enc_div < -ENC_DIVERGE_MAX:
        reason = 2                               # encoder/wheel fault
    elif hd > HEAD_ABORT or hd < -HEAD_ABORT:
        reason = 6                               # gross heading excursion
    elif od >= (S_START - FAILSAFE_MIN):
        reason = 3
    elif (t - t0) > T_MAX_MS:
        reason = 4
    elif (t - t0) > 400 and not moved_ok:
        reason = 5

    if reason:
        brake_all()
        trig = (t, d1, d2, od, hd, v_meas, thr, g_est)
        break

    red = KP_HEAD * hd * YAW_SIGN
    if red > TRIM_MAX:
        red = TRIM_MAX
    if red < -TRIM_MAX:
        red = -TRIM_MAX
    cl = VCMD - (red if red > 0 else 0.0)        # CMP-12: reduce-only trim
    cr = VCMD - (-red if red < 0 else 0.0)
    mL.run(DIR_L * cl)
    mR.run(DIR_R * cr)
    wait(DT_MS)

# ---- braking transient captured at FULL RATE, no emits on this path ---------
i_trig = bi - 1
tb = clock.time()
while clock.time() - tb < 900:
    logrow(clock.time(), sA.distance(), rB(),
           0.5 * (mL.angle() * DIR_L + mR.angle() * DIR_R) * K_TRAVEL,
           hub.imu.heading())
    wait(DT_MS)
i_rest = bi

ra = []
rbv = []
for _ in range(15):
    ra.append(sA.distance())
    rbv.append(rB())
    wait(15)
u_rest = med(ra)
odo_rest = 0.5 * (mL.angle() * DIR_L + mR.angle() * DIR_R) * K_TRAVEL
hd_rest = hub.imu.heading()
sp_rest = 0.5 * (abs(mL.speed()) + abs(mR.speed())) * K_TRAVEL
acc = hub.imu.acceleration()
mL.stop()
mR.stop()

# ------------------------------- ONBOARD FINAL-GAP ESTIMATE (SYS-6) ---------
rest_valid = 1.0 if u_rest > U_CLAMP else 0.0
g_primary = S_START - trig[3] - trig[5] * T_EFF   # PRIMARY: T4-anchored chain
g_odo_raw = S_START - odo_rest                    # upper bound (skid unmodelled)
# ranger-travel cross-check: ranger travel while valid, then odometry.
# Known bias: the odometry tail under-reads the skid, so this reads HIGH.
g_ranger_rel = S_START - (u0 - u_last_valid) - (odo_rest - od_last_valid)
enc_div_final = (mL.angle() * DIR_L - mR.angle() * DIR_R) * K_TRAVEL

# ==================================== TELEMETRY =============================
emit("cfg_S_start", S_START)
emit("cfg_G_target", G_TARGET)
emit("cfg_t_eff", T_EFF)
emit("cfg_k_travel", K_TRAVEL)
emit("u0_A", u0)
emit("g0", g0)
emit("trig_reason", reason)
emit("trig_t_ms", trig[0] - t0)
emit("trig_u_A", trig[1])
emit("trig_u_B", trig[2])
emit("trig_odo", trig[3])
emit("trig_heading", trig[4])
emit("trig_v_meas", trig[5])
emit("trig_thr", trig[6])
emit("trig_g_est", trig[7])
emit("loop_dt_min", dtmin)
emit("loop_dt_max", dtmax)
emit("loop_n", nloop)
emit("n_invalid_samples", n_invalid)
emit("u_last_valid", u_last_valid)
emit("odo_last_valid", od_last_valid)
emit("rest_u_A", u_rest)
emit("rest_u_A_spread", max(ra) - min(ra))
emit("rest_u_B", med(rbv))
emit("rest_valid", rest_valid)
emit("rest_odo", odo_rest)
emit("rest_heading", hd_rest)
emit("rest_speed", sp_rest)
emit("overshoot_u_A", trig[1] - u_rest)
emit("overshoot_odo", odo_rest - trig[3])
for k in range(3):
    emit("rest_accel_axis%d" % k, acc[k])
emit("EST_final_gap_PRIMARY", g_primary)
emit("EST_final_gap_odo_bound", g_odo_raw)
emit("EST_final_gap_ranger_rel", g_ranger_rel)
emit("diag_u0_monitor", u0)
emit("diag_u0_out_of_band", u0_flag)
emit("diag_enc_divergence", enc_div_final)


def dump(name, arr, i0, i1, stride):
    if i1 > bi:
        i1 = bi
    i = i0
    while i < i1:
        stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%.1f}\n'
                     % (int(T_[i]), name, arr[i]))
        i += stride


emit("buffer_used", bi)
dump("d1", D1_, 0, i_trig, 4)
dump("od", OD_, 0, i_trig, 4)
dump("hd", HD_, 0, i_trig, 12)
dump("d1", D1_, i_trig, i_rest, 1)
dump("d2", D2_, i_trig, i_rest, 2)
dump("od", OD_, i_trig, i_rest, 1)
dump("hd", HD_, i_trig, i_rest, 4)
stdout.write('{"event":"end"}\n')
