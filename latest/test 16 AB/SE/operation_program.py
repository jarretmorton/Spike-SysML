# =============================================================================
# WALLSTOP -- OPERATION PROGRAM  (locked candidate, rev B)
#
# Verified by the C2 verification run and then run UNCHANGED for the five
# scored operation runs.  Every constant below is a calibrated value from the
# Calibration Report or a requirement target; nothing is tuned by feel.
#
# Trigger law (RelationTemplates::StoppingDistance, quadratic term suppressed
# because it is not identifiable at a single operating point -- see rev B note):
#
#       U_thr(v) = c_A + G + v * t_eff        [ranger-A millimetres]
#
# CHANGES vs the C1 CORE, each with a stated no-effect-on-control argument:
#  1. Trigger reads ranger A ONLY.  Ranger B is logged but can never gate the
#     stop (CMP-2 rev B).  C1 showed B's offset is geometrically impossible and
#     that it drops out mid-range.
#  2. All post-trigger emit() calls moved AFTER the rest-logging loop.  In C1
#     they sat between brake_all() and the logging loop and blinded the rover
#     for 311 ms -- exactly across the braking transient.  emit() is downstream
#     of brake_all() either way, so the control path is untouched.
#  3. Readings at or below the ranger's measured 40 mm clamp are rejected
#     (CMP-4).  Below a true clearance of ~30 mm the sensor does not drop out,
#     it LIES with a constant 40.
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
C_A = 10.0          # TBD-01 ranger A longitudinal offset            [mm]
G_TARGET = 37.0     # TBD-12 commanded stand-off, set by SYS-6       [mm]
T_EFF = 0.09661     # TBD-06 lumped response, calibrated at v_ref     [s]
K_TRAVEL = 0.482    # TBD-03 travel per motor degree, ranger units [mm/deg]
U_CLAMP = 42.0      # TBD-09 reject at/below the measured 40 mm clamp [mm]
U_MAX_VALID = 1900.0
ACC_LIM = 4000      # deg/s^2, set explicitly for run-to-run repeatability
DIR_L = -1          # TBD-14 discovered in C1
DIR_R = 1
YAW_SIGN = 1.0      # TBD-14 driving motor L alone yaws heading positive
KP_HEAD = 8.0
TRIM_MAX = 200.0
DT_MS = 10

# --------------------------------------------------------------- failsafes --
RFLOOR = 44.0        # raw ranger floor  (nominal stop reads 47 -> never fires)
FAILSAFE_MIN = 60.0  # odometry floor referenced to the measured start clearance
T_MAX_MS = 6000
U0_LO, U0_HI = 700.0, 1400.0     # start-clearance plausibility gate (CMP-11)

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
g0 = u0 - C_A
if u0 < U0_LO or u0 > U0_HI:
    emit("ABORT_start_implausible", u0)
    stdout.write('{"event":"end"}\n')
    raise SystemExit

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

    valid = U_CLAMP < d1 < U_MAX_VALID          # CMP-4: clamp region rejected
    if valid:
        g_est = d1 - C_A
        u_last_valid = d1
        od_last_valid = od
    else:
        n_invalid += 1
        g_est = g0 - od                          # SYS-8 fallback: odometry

    v_meas = 0.5 * (abs(mL.speed()) + abs(mR.speed())) * K_TRAVEL
    thr = G_TARGET + T_EFF * v_meas              # StoppingDistance, live

    if od > 15.0:
        moved_ok = True

    if g_est <= thr:
        reason = 1
    elif valid and d1 <= RFLOOR:
        reason = 2
    elif od >= (g0 - FAILSAFE_MIN):
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
g_ranger = u_rest - C_A                      # primary
g_model = (trig[1] - trig[5] * T_EFF) - C_A  # model back-out, cross-check
g_odo = g0 - odo_rest                        # odometry, degrades under skid

# ==================================== TELEMETRY =============================
emit("cfg_c_A", C_A)
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
emit("EST_final_gap_ranger", g_ranger)
emit("EST_final_gap_model", g_model)
emit("EST_final_gap_odo", g_odo)


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
