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
# SAFETY OF CAL-1 (argued over the joint prior box by wallstop_model.py):
#   the max-speed brake event is triggered by the ODOMETRIC BACKSTOP at 250 mm of
#   travel, not by the ranging chain, so its safety depends only on k_eff, which
#   the static staircase (P2) binds BEFORE the pass runs. Exact worst case over
#   the joint prior box: landing >= +106 mm of clearance. No prior on stopping
#   travel enters that argument.
# =============================================================================

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

MODE = "CAL"

# ------------------------------- PARAMS --------------------------------------
K_EFF      = 0.489    # PRIOR  mm of reported range per degree of wheel rotation
L_SENSOR   = 40       # PRIOR  ms   ranger staleness
PSI_CAL    = 26.4     # PRIOR  mm   brake travel at V_CAL
V_CAL      = 396.0    # PRIOR  mm/s cruise speed the PSI_CAL was measured at
T_CHAIN    = 12       # PRIOR  ms   command-to-torque lag (psi speed correction)
A_BRAKE    = 3500.0   # PRIOR  mm/s^2 deceleration      (psi speed correction)
B_OFF      = -30.0    # PRIOR  mm   G = reported range + B_OFF   <-- TBD-3, needs M1
G_TARGET   = 220.0    # DESIGN mm   commanded target clearance (CAL-1 value)
S_BACKSTOP = 250.0    # DESIGN mm   absolute odometric brake limit (CMP-10), CAL-1/P4.
                      #   250 mm is the exact-worst-case choice: with k_eff bound to
                      #   +-2% by P2 the true travel is <=266 mm, worst-case stopping
                      #   travel 570 mm, so landing >= +106 mm over the whole prior box.
                      #   (>=400 mm would permit contact; ceiling is 345 mm.)
S_BACKSTOP_OP = 2000.0  # DESIGN mm  SLACK in OP/P6: the backstop is a fail-safe there,
                      #   NOT the trigger. The ranging chain must fire first.
G_FLOOR    = 120.0    # DESIGN mm   dead-reckoning clearance backstop (CAL-1)
G_FLOOR_OP = 25.0     # DESIGN mm   dead-reckoning backstop in OP (set at GATE B)
OMEGA_CMD  = 10000    # DESIGN deg/s commanded speed: above the ceiling on purpose
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
O_DRIFT_MAX = 50.0    # GUARD  mm   max rise of the range offset o=r+s before abort:
                      #   o is CONSTANT on a correct approach, and rises at ~2x the
                      #   travel rate if we are driving AWAY from the wall
HEAD_MAX   = 12.0     # GUARD  deg  heading deviation abort
T_WATCHDOG = 30000    # GUARD  ms   global motion watchdog
SLOW       = 220      # deg/s  staircase / reverse speed
STAIR_A    = 120.0    # mm     coarse staircase step
STAIR_A_N  = 5        # coarse staircase steps
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
      10: "d_fwd2_static", 11: "clearance_est"}


def buf(code, val):
    if len(BT) < 4000:
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


def statics(n=10, tag=0):
    """Static block: every catalogued channel, at rest. Latency-free, so this is
    the trusted reference the dynamic channels are bootstrapped off (tenet B2)."""
    a1 = 0.0
    a2 = 0.0
    for i in range(n):
        v1 = rangers[0].distance()
        v2 = rangers[1].distance()
        a1 += v1
        a2 += v2
        buf(9, v1)
        buf(10, v2)
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
    if abs(dh) > 4.0:
        SGN_R = -1
        summ("polarity_mirrored", 1)
    else:
        summ("polarity_mirrored", 0)

    # ---- stage B: translation probe -- classify rangers, then fix sign -------
    v1 = read_all()
    h1 = hub.imu.heading()
    t1 = theta()
    drive(300)
    wait(400)
    rest(400)
    v2 = read_all()
    dth = theta() - t1
    summ("polarity_dheadingB", hub.imu.heading() - h1)
    summ("polarity_dtheta", dth)
    d = [v2[i] - v1[i] for i in range(len(v1))]
    for i in range(len(d)):
        summ("probe_dr_port_" + PNAME[rports[i]], d[i])
    dfwd = d[0]               # pre-reorder default if classification is inconclusive
    if len(d) >= 3:
        # the odd-one-out in sign is the rear ranger
        pos = [i for i in range(len(d)) if d[i] > 6]
        neg = [i for i in range(len(d)) if d[i] < -6]
        fwd, rear = None, None
        if len(neg) >= 2 and len(pos) >= 1:
            fwd, rear = neg, pos[0]
        elif len(pos) >= 2 and len(neg) >= 1:
            fwd, rear = pos, neg[0]
        if fwd is not None:
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
    for i in range(60):
        h = hub.imu.heading()
        if abs(h) < 1.2:
            break
        ml.run(SGN_L * (-90 if h > 0 else 90))
        mr.run(SGN_R * (90 if h > 0 else -90))
        wait(40)
    rest(350)
    summ("heading_after_null", hub.imu.heading())
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
    drive(OMEGA_CMD)
    while True:
        t = clock.time()
        s = K_EFF * theta()
        v = K_EFF * omega()
        ht[hi] = t
        hs[hi] = s
        hi = (hi + 1) % 40
        r = rangers[0].distance()
        if r != r_prev:
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
            break
        if o_bar - o_init > O_DRIFT_MAX:
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
        if abs(hub.imu.heading() - h0) > HEAD_MAX:
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
    while clock.time() - t_cmd < 1500:
        sp = omega()
        buf(4, theta())
        buf(6, K_EFF * sp)
        a = hub.imu.acceleration()
        buf(7, a[0])
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
    while rangers[0].distance() < r_target:
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
        if r_stop > 0.0 and r_before <= r_stop:
            summ("stair%d_stopped_at" % tag, i)
            break
        d = step_forward(step_mm, r_floor)
        tot += d
        r1, r2 = statics(10)
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
    a0 = hub.imu.acceleration()
    summ("accel_rest_x", a0[0])
    summ("accel_rest_y", a0[1])
    summ("accel_rest_z", a0[2])
    r_a, r_b = statics(12)                      # P0 static baseline
    summ("P0_r1", r_a)
    summ("P0_r2", r_b)
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
        statics(12)
        approach(G_TARGET, S_BACKSTOP, R_FLOOR, G_FLOOR, 1)   # P4 max speed, backstop
        reverse_to(r_line - 25.0)                          # P5 back to start line
        statics(12)
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
