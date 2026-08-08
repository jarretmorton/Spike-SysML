# =============================================================================
# rover_wallstop.py  --  ONE program, two modes.
#
#   MODE = "CAL"  characterization run CAL-1 (phases P0..P8)
#   MODE = "OP"   the operation / verification program (phases P0, P1, P4, P8)
#
# The OP mode is a strict SUBSET of the CAL mode: same file, same approach()
# function, same trigger arithmetic, same loop period, same buffer skeleton.
# Nothing in the hot path differs between calibration and operation -- the extra
# characterization work is in ADDITIONAL PHASES and in a dump that happens only
# after the motors have stopped (test-like-you-fly, CHARACTERIZATION METHOD 3).
#
# CALIBRATED PARAMETERS are all in the PARAMS block. At CAL-1 they hold PRIOR
# NOMINALS (marked #PRIOR); GATE B replaces them with bound values (#BOUND).
# Nothing else in the file changes between runs.
#
# SAFETY OF CAL-2 (wallstop_model.backstop_worst_case, exact closed form):
#   the max-speed brake event is triggered by the ODOMETRIC BACKSTOP, not by the
#   ranging chain, so its safety depends only on k_eff -- which CAL-1 bound at T4
#   to 0.4858 mm/deg (+-1%). With psi_brake now MEASURED at 12.9 mm rather than a
#   prior spanning 570 mm, a 450 mm backstop lands at ~480 mm of clearance even at
#   4x the measured stopping travel. CAL-1 used 250 mm, when psi was still a prior.
#
# CAL-1 FINDINGS DRIVING THIS VERSION (see AR-01): both motors at run(10000) meant
#   each ran to ITS OWN ceiling, 6.2% apart, driving a 1961 mm arc -- 25 deg of yaw
#   over a full approach, which loses the specular echo entirely. Hence a COMMON
#   regulated cruise speed plus an IMU heading-hold, and no-echo rejection at every
#   point where a range is consumed.
# =============================================================================

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

MODE = "OP"      # LOCKED for the verification run and the five scored runs

# ------------------------------- PARAMS --------------------------------------
K_EFF      = 0.4858   # BOUND  T4  mm of range per degree. CAL-1 staircase A: 6-point
                      #   regression over 620 mm, slope -0.9935, residuals +-6.3 mm
                      #   (implies a 55.7 mm wheel). Was 0.489 as a prior.
L_SENSOR   = 50       # BOUND  T4  ms ranger staleness. CAL-2: o_consistency in two
                      #   approaches gave 62 and 69 ms, confirmed independently by
                      #   psi_ranger - psi_odo. REVISED after VER-1: at the operational
                      #   configuration (985 mm approach) the residual o-bias was +6.57 mm,
                      #   which corresponds to an EFFECTIVE staleness of 50 ms. This is a
                      #   composite: true sensor latency plus odometric drift over the
                      #   operational approach length. It is bound AT the operating point,
                      #   which is the only place it has to be right.
PSI_CAL    = 12.64    # BOUND  T4  mm brake travel at V_CAL. THREE events across two runs:
                      #   12.9, 12.87, 12.14 mm -> sd 0.43 mm.
V_CAL      = 418.0    # BOUND  T4  mm/s the speed those were measured at (860 deg/s x K_EFF)
T_CHAIN    = 12       # BOUND  T3  ms  command-to-torque lag, from the theta trace onset
A_BRAKE    = 7425.0   # BOUND  T3  mm/s^2 = 0.76 g, back-solved from PSI_CAL at V_CAL.
                      #   Used ONLY for the first-order speed correction to psi, not for
                      #   psi itself (StoppingDistance template guidance).
B_OFF      = -17.00   # BOUND  T5-external, from M2 = 31 mm at a reported 48.0 mm with
                      #   0.83 deg of yaw. The leading CORNER is the front-most point and the
                      #   ranger reads along its own line of sight.
                      #   VER-1 falsified the v1.0 prediction: I had bound the operational
                      #   stop yaw from CAL-2's approaches, which ran AFTER staircases that
                      #   had drifted the heading. OP mode goes straight from the yaw-null
                      #   to the approach and stays square, so the 8.04 deg correction was
                      #   7.9 mm of pure error. At 0.83 deg every yaw term vanishes and
                      #   b_eff = G - r = -17.0 mm, needing no yaw model at all.
                      #   (M1 at 11.11 deg implies b_perp = -21.04 vs M2's -16.13: the two
                      #   T5 anchors disagree by 4.9 mm, which is a missing LATERAL sensor
                      #   offset term. Immaterial at the operational yaw; recorded, not fitted.)
G_TARGET   = 26.0     # FROZEN mm   commanded target clearance. m_contact = 3*RSS = 15.3 mm.
                      #   v3.0: RAISED to 26.0 to buy OBSERVABILITY, not margin. Below ~23 mm
                      #   of clearance this rover cannot measure its own gap: the static
                      #   estimator clips at the ranger's 40 mm floor (VER-2 returned exactly
                      #   40.00 on both forward rangers) and clearance_est_odo reduces
                      #   algebraically to T + (psi_belief - psi_odo), i.e. the target plus a
                      #   ~1 mm psi error -- it cannot detect a clearance error at all.
                      #   At 26 mm the static reading is ~43 mm, valid, and independent, so a
                      #   fourth modelling error would be VISIBLE during the scored runs
                      #   instead of surfacing only in the operator's close-out measurements.
                      #   Costs ~12 mm of closeness. SYS-7 (a shall) beats OBJ-1 (a should).
S_BACKSTOP = 450.0    # DESIGN mm   absolute odometric brake limit (CMP-10), CAL-2/P4.
                      #   Raised from 250: psi_brake is now MEASURED at 12.9 mm (not a prior),
                      #   so even at 4x that value the exact worst-case landing is ~480 mm.
                      #   The longer cruise segment is what binds l_sensor.
S_BACKSTOP_OLD = 250.0  # CAL-1 value, retained for the record: correct when psi_brake
                      #   was still an unbound prior (ceiling was then 345 mm).
S_BACKSTOP_OP = 2000.0  # DESIGN mm  SLACK in OP/P6: the backstop is a fail-safe there,
                      #   NOT the trigger. The ranging chain must fire first.
G_FLOOR    = 120.0    # DESIGN mm   dead-reckoning clearance backstop (CAL-1)
G_FLOOR_OP = 0.0      # FROZEN mm   dead-reckoning backstop. At a 12 mm target it CANNOT be
                      #   set as a useful net without pre-empting the primary: odometric
                      #   drift over the approach is +-21 mm at 3 sigma, which exceeds the
                      #   target. Set to 0 as a last resort only. If the ranger dies mid-
                      #   approach the real protection is that o_bar stops updating, so the
                      #   brake threshold holds at its last VALID value -- which is safe.
OMEGA_CMD  = 10000    # DESIGN deg/s used ONLY for the ceiling measurement, not for driving
OMEGA_RUN  = 860      # BOUND  deg/s COMMON regulated cruise speed for both wheels.
                      #   CAL-1 ran both motors at run(10000), i.e. each at ITS OWN ceiling:
                      #   they differed by 6.2% (872 vs 928 deg/s), which drove the rover along
                      #   a 1961 mm arc -- 25 deg of yaw and 181 mm of lateral offset over a full
                      #   approach, enough to lose the wall echo entirely. Commanding a COMMON
                      #   regulated speed just below the slower ceiling is the maximum STRAIGHT-LINE
                      #   speed the vehicle has; running the faster wheel harder adds rotation,
                      #   not forward speed.
KP_TRIM    = 0.010    # BOUND  fraction of speed per degree of heading error. Derived, not
                      #   guessed: CAL-1 showed a 6.2% differential produces 2.92 deg/100 mm
                      #   with a 121 mm track, so nulling 1 deg over 100 mm needs 1.01%.
TRIM_MAX   = 0.08     # DESIGN clamp on the steering trim
R_NOECHO   = 1900     # GUARD  mm at/above this the ranger reports NO ECHO, not a distance.
                      #   CAL-1 fed 2000 straight into the estimator and the guards.
N_BAD_MAX  = 20       # GUARD  consecutive invalid ranger samples before falling back
N_ODRIFT   = 3        # GUARD  consecutive o-drift violations required before aborting
A_LIMIT    = 2000     # DESIGN deg/s^2 commanded acceleration limit
DT_LOOP    = 5        # DESIGN ms   hot-loop period
N_LOOK     = 4        # DESIGN loop periods of trigger look-ahead
N_FUSE     = 6        # DESIGN fresh samples averaged for the range offset
NF_MIN     = 3        # DESIGN fused samples before the primary trigger arms
R_FLOOR    = 200      # GUARD  mm   reported-range floor during fast CAL phases
R_FLOOR_OP = 25       # GUARD  mm   in OP the stop reading is BELOW any useful floor,
                      #             so this is only an "impossibly close" abort;
                      #             the dead-reckoning and odometric backstops are
                      #             what actually protect the operating approach
R_FLOOR_SL = 112      # GUARD  mm   reported-range floor during slow phases
O_DRIFT_MAX = 80.0    # GUARD  mm   max rise of the range offset o=r+s before abort:
                      #   o is CONSTANT on a correct approach, and rises at ~2x the
                      #   travel rate if we are driving AWAY from the wall
HEAD_MAX   = 12.0     # GUARD  deg  heading deviation abort
T_WATCHDOG = 45000    # GUARD  ms   global motion watchdog. CAL-1 motion ran to 30.8 s
                      #   against a 30 s watchdog -- it very nearly truncated the fine
                      #   staircase, which is the phase that parks the rover for M1.
SLOW       = 220      # deg/s  staircase / reverse speed
STAIR_A    = 140.0    # mm     coarse staircase step
STAIR_A_N  = 3        # coarse staircase steps (k_eff is already bound at T4 by CAL-1;
                      #   3 points over 420 mm is a linearity CONFIRMATION, and the time
                      #   saved pays for the brake-yaw diagnostics)
STAIR_B    = 18.0     # mm     fine staircase step
STAIR_B_N  = 8        # fine staircase steps
R_STAIR_B  = 130.0    # mm     fine staircase target reported range (>=112 floor +
                      #   one 18 mm step keeps >=28 mm true clearance even at b=-80)
MAX_RAW    = 300      # cap on raw telemetry lines (BLE budget)

# ------------------------------- runtime -------------------------------------
hub = PrimeHub()
clock = StopWatch()
BT = []          # buffer: times
BC = []          # buffer: channel codes
BV = []          # buffer: values
SUM = []         # (name, value) summary pairs, emitted FIRST
FLAGS = 0
CH = {1: "d_fwd", 2: "d_fwd2", 3: "d_rear", 4: "theta", 5: "heading",
      6: "speed", 7: "accel_x", 8: "reflect", 9: "d_fwd_static",
      10: "d_fwd2_static", 11: "clearance_est", 12: "theta_l", 13: "theta_r"}


def buf(code, val):
    # 3 parallel lists; on the hub each record costs ~3 pointers + a boxed float,
    # so 4000 records is a plausible MemoryError. 1600 is ample for this run
    # (worst realistic case ~1100) and the parameter-binding values live in SUM,
    # which is emitted FIRST and is unaffected by raw truncation.
    if len(BT) < 1600:
        BT.append(clock.time())
        BC.append(code)
        BV.append(val)


def summ(name, val):
    SUM.append((name, val))


def flag(bit):
    global FLAGS
    FLAGS |= bit


# ------------------------- P0a: device discovery (CMP-15) --------------------
wait(400)
PORTS = [Port.A, Port.B, Port.C, Port.D, Port.E, Port.F]
PNAME = ["A", "B", "C", "D", "E", "F"]
motors = []
mports = []
rangers = []
rports = []
colors = []
cports = []
for i in range(6):
    try:
        motors.append(Motor(PORTS[i]))
        mports.append(i)
        continue
    except Exception:
        pass
    try:
        rangers.append(UltrasonicSensor(PORTS[i]))
        rports.append(i)
        continue
    except Exception:
        pass
    try:
        colors.append(ColorSensor(PORTS[i]))
        cports.append(i)
    except Exception:
        pass
summ("n_motors", len(motors))
summ("n_rangers", len(rangers))
summ("n_colors", len(colors))
for i in range(len(mports)):
    summ("motor_port_" + PNAME[mports[i]], 1)
for i in range(len(rports)):
    summ("ranger_port_" + PNAME[rports[i]], 1)
for i in range(len(cports)):
    summ("color_port_" + PNAME[cports[i]], 1)
if len(motors) < 2 or len(rangers) < 2:
    flag(1)
    stdout.write('{"timestamp_ms":%d,"sensor":"fatal_discovery","value":%d}\n'
                 % (clock.time(), len(motors) * 10 + len(rangers)))
    stdout.write('{"event":"end"}\n')
    raise SystemExit

ml = motors[0]
mr = motors[1]
for m in (ml, mr):
    try:
        m.control.limits(speed=OMEGA_CMD, acceleration=A_LIMIT)
    except Exception:
        try:
            m.control.limits(acceleration=A_LIMIT)
        except Exception:
            flag(2)
    m.reset_angle(0)
col = colors[0] if colors else None

SGN_L = 1
SGN_R = 1
_a_rest = hub.imu.acceleration()
HEAD_VALID = 1 if abs(_a_rest[2]) > 7800 else 0   # |g| on Z => hub is flat


def theta():
    return (SGN_L * ml.angle() + SGN_R * mr.angle()) / 2.0


def omega():
    return (SGN_L * ml.speed() + SGN_R * mr.speed()) / 2.0


def drive(sp):
    ml.run(SGN_L * sp)
    mr.run(SGN_R * sp)


def brake():
    ml.brake()
    mr.brake()


def rest(settle=600):
    brake()
    wait(settle)


def statics(n=10, tag=0, log=1):
    """Static block: every catalogued channel, at rest. Latency-free, so this is
    the trusted reference the dynamic channels are bootstrapped off (tenet B2)."""
    a1 = 0.0
    a2 = 0.0
    for i in range(n):
        v1 = rangers[0].distance()
        v2 = rangers[1].distance()
        a1 += v1
        a2 += v2
        if log:
            buf(9, v1)      # raw statics are only needed where q_range / noise is
            buf(10, v2)     # being measured; the means always go to SUM
        wait(25)
    if len(rangers) > 2:
        buf(3, rangers[2].distance())
    if col is not None:
        buf(8, col.reflection())
    buf(5, hub.imu.heading() * 10.0)
    ax = hub.imu.acceleration()
    buf(7, ax[0])
    buf(4, theta())
    return a1 / n, a2 / n


# ------- P1: polarity AND forward/rear ranger identification (CMP-15/16) -----
def read_all():
    return [rangers[i].distance() for i in range(len(rangers))]


def identify_polarity():
    """Two-stage probe. Stage A is short and slow, and only asks whether the
    drivetrain is mirrored (a mirrored pair spins in place, which the IMU sees as
    yaw). Stage B is a pure translation, long enough to move several range quanta,
    and it does two jobs at once: it classifies the rangers and it fixes the drive
    sign.

    Ranger classification is by 2-vs-1 MAJORITY, not by port order: the inventory
    has two forward rangers and one rear, so under any translation the two that
    agree in sign are the forward pair and the odd one out is the rear. This is
    independent of drive polarity, which is why it can run before polarity is
    known. rangers[] is then REORDERED to [primary_fwd, secondary_fwd, rear].
    Without this, rangers[0] would be whichever ranger sits on the lowest port --
    possibly the rear one, which would invert every range-based decision."""
    global SGN_L, SGN_R, rangers, rports
    v0 = read_all()
    summ("r_pre_polarity", v0[0])
    h0 = hub.imu.heading()

    # ---- stage A: mirrored-drivetrain test (short, slow, low yaw excursion) ---
    drive(120)
    wait(150)
    rest(300)
    dh = hub.imu.heading() - h0
    summ("polarity_dheadingA", dh)
    if HEAD_VALID and abs(dh) > 4.0:
        SGN_R = -1
        summ("polarity_mirrored", 1)
    else:
        summ("polarity_mirrored", 0)

    # ---- stage B: translation probe -- classify rangers, then fix sign -------
    # Retried ONCE on a ranger-only criterion: if no ranger reading moves at all,
    # the wheels turned but the rover did not translate, i.e. it spun in place,
    # i.e. the drivetrain is mirrored. This is the fallback for a hub whose
    # heading axis is unusable (head_valid == 0), where stage A cannot decide.
    d = [0, 0, 0]
    dth = 0.0
    for attempt in (0, 1):
        v1 = read_all()
        h1 = hub.imu.heading()
        t1 = theta()
        drive(300)
        wait(400)
        rest(400)
        v2 = read_all()
        dth = theta() - t1
        d = [v2[i] - v1[i] for i in range(len(v1))]
        summ("probeB%d_dheading" % attempt, hub.imu.heading() - h1)
        summ("probeB%d_dtheta" % attempt, dth)
        moved = 0
        for i in range(len(d)):
            if abs(d[i]) > 6:
                moved = 1
        summ("probeB%d_moved" % attempt, moved)
        if moved:
            break
        if attempt == 0:
            SGN_R = -SGN_R
            summ("polarity_mirrored_by_ranger", 1)
    for i in range(len(d)):
        summ("probe_dr_port_" + PNAME[rports[i]], d[i])
    dfwd = d[0]               # pre-reorder default if classification is inconclusive
    if len(d) >= 3:
        # CAL-1 lesson: the 2-vs-1 SIGN majority fails because the rear ranger faces an
        # open room, saturates at 2000 and therefore has ZERO delta -- it lands in neither
        # sign bucket and the test gives up. Saturation is itself the decisive evidence:
        # the wall is ~1000 mm away, well inside range, so a ranger reading no-echo at the
        # start line is not looking at the wall. Classify on that, then use sign only to
        # order the forward pair.
        fwd = [i for i in range(len(d)) if v1[i] < R_NOECHO]
        sat = [i for i in range(len(d)) if v1[i] >= R_NOECHO]
        rear = sat[0] if sat else None
        if rear is None and len(fwd) >= 3:
            pos = [i for i in fwd if d[i] > 6]
            neg = [i for i in fwd if d[i] < -6]
            if len(neg) >= 2 and len(pos) >= 1:
                fwd, rear = neg, pos[0]
            elif len(pos) >= 2 and len(neg) >= 1:
                fwd, rear = pos, neg[0]
            else:
                fwd = None
        elif len(fwd) < 2:
            fwd = None
        if fwd is not None and rear is not None:
            dfwd = d[fwd[0]]      # captured BEFORE the reorder: indices change below
            order = [fwd[0], fwd[1], rear] + [i for i in range(len(d))
                                              if i not in (fwd[0], fwd[1], rear)]
            rangers = [rangers[i] for i in order]
            rports = [rports[i] for i in order]
            summ("ranger_classified", 1)
            summ("fwd_ports", 10 * (rports[0] + 1) + (rports[1] + 1))
            summ("rear_port", rports[2] + 1)
        else:
            summ("ranger_classified", 0)
            flag(64)          # inconclusive: escalate, do not guess
    summ("polarity_dr_fwd", dfwd)
    if dfwd > 6:              # forward ranger receded -> we drove away from the wall
        SGN_L = -SGN_L
        SGN_R = -SGN_R
        summ("polarity_flipped", 1)
    summ("sgn_l", SGN_L)
    summ("sgn_r", SGN_R)
    # null the heading the probe may have introduced, so every run starts square
    # CAL-1 left 3.67 deg here against a 1.2 deg deadband: the pulses were too coarse
    # and nothing re-checked after the settle. Smaller pulses, more of them, then a
    # second pass after settling, and BOTH values reported.
    # CAL-2: the two-pass null REGRESSED, +1.78 deg after pass 0 then -3.88 deg after
    # pass 1 -- it overshoots the deadband. Reverted to a single pass.
    for npass in (0,):
        for i in range(90 if HEAD_VALID else 0):
            h = hub.imu.heading()
            if abs(h) < 0.8:
                break
            ml.run(SGN_L * (-60 if h > 0 else 60))
            mr.run(SGN_R * (60 if h > 0 else -60))
            wait(30)
        rest(400)
        summ("heading_after_null%d" % npass, hub.imu.heading())
    ml.reset_angle(0)
    mr.reset_angle(0)


# --------------------------- the HOT PATH (shared) ---------------------------
def approach(g_target, s_backstop, r_floor, g_floor, tag):
    """Identical in CAL and OP. Accelerates to the ceiling, fuses ranger and
    odometry into an absolute range offset, and brakes at the instant whose
    predicted rest clearance equals g_target. Logging is buffered only."""
    ml.reset_angle(0)
    mr.reset_angle(0)
    r_static, r_static2 = statics(12)
    summ("r_static_%d" % tag, r_static)
    summ("r_static2_%d" % tag, r_static2)
    summ("d_agree_%d" % tag, r_static2 - r_static)
    h0 = hub.imu.heading()

    ht = [0] * 40          # ring of times   (for the staleness lookback)
    hs = [0.0] * 40        # ring of s
    hi = 0
    o_ring = [r_static]
    o_bar = r_static
    o_init = r_static
    n_fresh = 0
    r_prev = -1
    t_start = clock.time()
    t_next = t_start
    s = 0.0
    v = 0.0
    t_cmd = -1
    s_cmd = 0.0
    o_cmd = 0.0
    v_cmd = 0.0
    psi_b = PSI_CAL
    src = 0
    n_bad = 0
    n_od = 0
    trim_pk = 0.0
    ml.run(SGN_L * OMEGA_RUN)
    mr.run(SGN_R * OMEGA_RUN)
    while True:
        t = clock.time()
        s = K_EFF * theta()
        v = K_EFF * omega()
        ht[hi] = t
        hs[hi] = s
        hi = (hi + 1) % 40
        # ---- heading hold. Subtractive only: the correction always SLOWS the outer
        # wheel, never commands past OMEGA_RUN, so both motors stay inside the
        # regulated regime where run() actually tracks its target.
        hnow = hub.imu.heading()
        e_h = hnow - h0
        tl = 0.0
        tr = 0.0
        if HEAD_VALID:
            if e_h < 0.0:
                tr = -KP_TRIM * e_h
                if tr > TRIM_MAX:
                    tr = TRIM_MAX
            else:
                tl = KP_TRIM * e_h
                if tl > TRIM_MAX:
                    tl = TRIM_MAX
            if tl > trim_pk:
                trim_pk = tl
            if tr > trim_pk:
                trim_pk = tr
            ml.run(SGN_L * OMEGA_RUN * (1.0 - tl))
            mr.run(SGN_R * OMEGA_RUN * (1.0 - tr))
        r = rangers[0].distance()
        if r >= R_NOECHO:
            # NO ECHO is not a distance. Do not feed it to the estimator or the guards.
            n_bad += 1
            if n_bad == N_BAD_MAX:
                flag(256)
            r_prev = -1
        elif r != r_prev:
            n_bad = 0
            r_prev = r
            n_fresh += 1
            tq = t - L_SENSOR
            sv = s
            for k in range(40):
                j = (hi - 1 - k) % 40
                if ht[j] <= tq and ht[j] > 0:
                    sv = hs[j]
                    break
            o_ring.append(r + sv)
            if len(o_ring) > N_FUSE:
                o_ring.pop(0)
            o_bar = sum(o_ring) / len(o_ring)
            buf(1, r)
            buf(4, theta())
            if (n_fresh & 3) == 0:
                buf(2, rangers[1].distance())
        psi_b = PSI_CAL + (v - V_CAL) * (T_CHAIN / 1000.0 + V_CAL / A_BRAKE)
        s_br = o_bar + B_OFF - g_target - psi_b
        src = 1
        if s_backstop < s_br:
            s_br = s_backstop
            src = 2
        s_dr = (r_static + B_OFF) - g_floor - psi_b
        if s_dr < s_br:
            s_br = s_dr
            src = 3
        armed = (n_fresh >= NF_MIN) or (src != 1)
        if armed and (s_br - s) <= v * DT_LOOP * N_LOOK / 1000.0:
            rem = s_br - s
            if rem > 0.0 and v > 1.0:
                w = int(1000.0 * rem / v)
                if w > 0:
                    wait(w)
            brake()
            t_cmd = clock.time()
            s_cmd = K_EFF * theta()
            o_cmd = o_bar
            v_cmd = v
            summ("head_at_cmd_%d" % tag, hnow)
            summ("theta_l_at_cmd_%d" % tag, SGN_L * ml.angle())
            summ("theta_r_at_cmd_%d" % tag, SGN_R * mr.angle())
            summ("trim_peak_%d" % tag, trim_pk)
            summ("n_bad_%d" % tag, n_bad)
            break
        if o_bar - o_init > O_DRIFT_MAX and n_bad == 0:
            n_od += 1
        else:
            n_od = 0
        if n_od >= N_ODRIFT:
            # o = r + s is constant on a correct approach and climbs at ~2x the
            # travel rate if the drive sign is wrong. Physically-impossible rise:
            # escalate unconditionally rather than keep driving.
            flag(64)
            brake()
            t_cmd = clock.time()
            s_cmd = K_EFF * theta()
            o_cmd = o_bar
            v_cmd = v
            src = 7
            break
        if r < r_floor:
            flag(4)
            brake()
            t_cmd = clock.time()
            s_cmd = K_EFF * theta()
            o_cmd = o_bar
            v_cmd = v
            src = 4
            break
        if HEAD_VALID and abs(hub.imu.heading() - h0) > HEAD_MAX:
            flag(8)
            brake()
            t_cmd = clock.time()
            s_cmd = K_EFF * theta()
            o_cmd = o_bar
            v_cmd = v
            src = 5
            break
        if t - t_start > 6000 or t > T_WATCHDOG:
            flag(16)
            brake()
            t_cmd = clock.time()
            s_cmd = K_EFF * theta()
            o_cmd = o_bar
            v_cmd = v
            src = 6
            break
        if (t - t_start) % 150 < DT_LOOP:
            buf(5, hub.imu.heading() * 10.0)
            buf(6, v)
        t_next += DT_LOOP
        d = t_next - clock.time()
        if d > 0:
            wait(d)

    # ---- brake transient, still buffered only ----
    nz = 0
    while clock.time() - t_cmd < 700:
        sp = omega()
        buf(4, theta())
        buf(6, K_EFF * sp)
        a = hub.imu.acceleration()
        buf(7, a[0])
        # CAL-1 logged no heading inside the brake transient, so a further -8.3 deg of
        # apparent yaw across the stop could not be separated into real asymmetric
        # braking versus an IMU artifact from the 0.76 g shock. Both channels now.
        buf(5, hub.imu.heading() * 10.0)
        buf(12, SGN_L * ml.angle())
        buf(13, SGN_R * mr.angle())
        if abs(sp) < 3:
            nz += 1
            if nz > 6:
                break
        else:
            nz = 0
        wait(10)
    t_stop = clock.time()
    wait(700)
    r_rest, r_rest2 = statics(14)
    s_rest = K_EFF * theta()
    summ("trigger_src_%d" % tag, src)
    summ("v_cmd_%d" % tag, v_cmd)
    summ("psi_belief_%d" % tag, psi_b)
    summ("o_cmd_%d" % tag, o_cmd)
    summ("s_cmd_%d" % tag, s_cmd)
    summ("s_rest_%d" % tag, s_rest)
    summ("psi_odo_%d" % tag, s_rest - s_cmd)
    summ("r_rest_%d" % tag, r_rest)
    summ("r_rest2_%d" % tag, r_rest2)
    summ("psi_ranger_%d" % tag, (o_cmd - s_cmd) - r_rest)
    summ("o_rest_%d" % tag, r_rest + s_rest)
    summ("o_consistency_%d" % tag, (r_rest + s_rest) - o_cmd)
    summ("t_brake_ms_%d" % tag, t_stop - t_cmd)
    summ("t_approach_ms_%d" % tag, t_cmd - t_start)
    summ("n_fresh_%d" % tag, n_fresh)
    summ("heading_end_%d" % tag, hub.imu.heading())
    summ("theta_l_%d" % tag, SGN_L * ml.angle())
    summ("theta_r_%d" % tag, SGN_R * mr.angle())
    summ("clearance_est_static_%d" % tag, r_rest + B_OFF)
    summ("clearance_est_odo_%d" % tag, (o_cmd + B_OFF) - s_rest)
    summ("head_settled_%d" % tag, hub.imu.heading())
    buf(11, r_rest + B_OFF)
    return r_rest


# ------------------------------ slow moves ----------------------------------
def step_forward(mm, r_floor):
    """One odometric step at low speed, then a full stop. Used by both staircases."""
    ml.reset_angle(0)
    mr.reset_angle(0)
    t0 = clock.time()
    drive(SLOW)
    while K_EFF * theta() < mm:
        r = rangers[0].distance()
        if r >= R_NOECHO:
            # No echo while creeping toward the wall means the range floor guard is
            # BLIND. CAL-1's fine staircase stepped 181 mm on exactly this. Stop.
            flag(512)
            break
        if r < r_floor:
            flag(32)
            break
        if clock.time() - t0 > 3000 or clock.time() > T_WATCHDOG:
            flag(16)
            break
        wait(5)
    rest(400)
    return K_EFF * theta()


def reverse_to(r_target):
    ml.reset_angle(0)
    mr.reset_angle(0)
    t0 = clock.time()
    drive(-SLOW)
    while True:
        rv = rangers[0].distance()
        # A no-echo reading must not be read as "far enough away": require a VALID
        # reading to satisfy the target, else fall back to the odometric cap.
        if rv < R_NOECHO and rv >= r_target:
            break
        if -K_EFF * theta() > 600.0:      # odometric cap: never reverse >600 mm
            flag(128)
            break
        if clock.time() - t0 > 6000 or clock.time() > T_WATCHDOG:
            flag(16)
            break
        wait(5)
    rest(500)
    return K_EFF * theta()


def staircase(n, step_mm, tag, r_floor, r_stop=0.0):
    """Quasi-static ranger-vs-odometry sweep: the latency-free calibration of the
    ranging chain (k_eff, scale error, quantisation) -- and, at the fine end, the
    near-range validity floor and the rest pose for the operator anchor."""
    tot = 0.0
    for i in range(n):
        r_before = rangers[0].distance()
        if r_before >= R_NOECHO:
            summ("stair%d_noecho_at" % tag, i)
            flag(512)
            break
        if r_stop > 0.0 and r_before <= r_stop:
            summ("stair%d_stopped_at" % tag, i)
            break
        d = step_forward(step_mm, r_floor)
        tot += d
        r1, r2 = statics(10, 0, 0)
        summ("stair%d_%d_s" % (tag, i), tot)
        summ("stair%d_%d_r1" % (tag, i), r1)
        summ("stair%d_%d_r2" % (tag, i), r2)
        summ("stair%d_%d_head" % (tag, i), hub.imu.heading())
    return tot


# --------------------------------- dump -------------------------------------
def dump():
    t = clock.time()
    stdout.write('{"timestamp_ms":%d,"sensor":"flags","value":%d}\n' % (t, FLAGS))
    stdout.write('{"timestamp_ms":%d,"sensor":"mode_cal","value":%d}\n'
                 % (t, 1 if MODE == "CAL" else 0))
    for nm, vl in SUM:
        stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%.2f}\n' % (t, nm, vl))
    n = len(BT)
    stdout.write('{"timestamp_ms":%d,"sensor":"raw_records","value":%d}\n' % (t, n))
    stp = 1
    if n > MAX_RAW:
        stp = n // MAX_RAW + 1
    stdout.write('{"timestamp_ms":%d,"sensor":"raw_decimation","value":%d}\n' % (t, stp))
    i = 0
    while i < n:
        stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%.1f}\n'
                     % (BT[i], CH.get(BC[i], "ch%d" % BC[i]), BV[i]))
        i += stp
    stdout.write('{"event":"end"}\n')


# --------------------------------- main -------------------------------------
try:
    summ("imu_ready", 1 if hub.imu.ready() else 0)
    summ("head_valid", HEAD_VALID)
    a0 = hub.imu.acceleration()
    summ("accel_rest_x", a0[0])
    summ("accel_rest_y", a0[1])
    summ("accel_rest_z", a0[2])
    r_a, r_b = statics(12)                      # P0 static baseline
    summ("P0_r1", r_a)
    summ("P0_r2", r_b)
    # ---- start-position sanity check, BEFORE any motion --------------------
    # The setup is fixed at ~1000 mm (CAL-1 measured 1023 mm here). A start
    # reading well short of that means the rover was not returned to the line;
    # a no-echo reading means it is not square to the wall. Either way every
    # parameter this run would bind is referenced to the wrong pose, so abort
    # now at the cost of a flash instead of a full run -- and in OP mode this
    # is what stops a mis-positioned scored run from returning a plausible
    # but meaningless gap.
    if r_a < 850.0 or r_a >= R_NOECHO:
        flag(1024)
        stdout.write('{"timestamp_ms":%d,"sensor":"fatal_start_pose","value":%.1f}\n'
                     % (clock.time(), r_a))
        raise SystemExit
    if len(rangers) > 2:
        summ("P0_rear", rangers[2].distance())
    if col is not None:
        summ("P0_reflect", col.reflection())

    identify_polarity()                          # P1
    r_line, r_line2 = statics(12)
    summ("P1_r1_startline", r_line)

    if MODE == "CAL":
        staircase(STAIR_A_N, STAIR_A, 1, R_FLOOR, 350.0)   # P2 coarse staircase
        reverse_to(r_line - 25.0)                          # P3 back to start line
        statics(12, 0, 0)
        approach(G_TARGET, S_BACKSTOP, R_FLOOR, G_FLOOR, 1)   # P4 max speed, backstop
        reverse_to(r_line - 25.0)                          # P5 back to start line
        statics(12, 0, 0)
        approach(G_TARGET, S_BACKSTOP_OP, R_FLOOR, G_FLOOR, 2)  # P6 max speed, fused
        staircase(STAIR_B_N, STAIR_B, 2, R_FLOOR_SL, R_STAIR_B)  # P7 fine staircase
        statics(20)                                        # P8 final block
        summ("final_r1", rangers[0].distance())
        summ("final_r2", rangers[1].distance())
        if len(rangers) > 2:
            summ("final_rear", rangers[2].distance())
        if col is not None:
            summ("final_reflect", col.reflection())
        summ("final_heading", hub.imu.heading())
        summ("final_theta", theta())
    else:
        # OP is configured EXACTLY as CAL-1/P6 (the rehearsal): ranging-triggered,
        # backstop slack as a fail-safe. Using the tight CAL backstop here would
        # brake after 250 mm and stop ~700 mm short on every scored run.
        approach(G_TARGET, S_BACKSTOP_OP, R_FLOOR_OP, G_FLOOR_OP, 1)
        summ("final_r1", rangers[0].distance())
        summ("final_r2", rangers[1].distance())
        summ("final_heading", hub.imu.heading())
finally:
    try:
        ml.brake()
        mr.brake()
    except Exception:
        pass
    dump()
