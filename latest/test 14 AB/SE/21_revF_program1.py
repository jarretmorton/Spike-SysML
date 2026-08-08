# =============================================================================
# REV F  --  verification / operation candidate      (Pybricks MicroPython)
#
# The forward ranger is NOT CONSTRUCTED. It has been the proximate cause of
# three of four anomalies (A/B crosstalk, 196 mm dynamic lag, +325 mm in-motion
# error) and, with the start distance measured directly, it has no remaining job.
# Not constructing it also removes it as an interference source.
#
#   anchor  : G, hard-coded from operator measurement (setup fixed across runs)
#   scale   : k, from the M1 + G ground-truth pair over a 1646.5 deg baseline
#   trigger : d_go = G - travel*k  <=  TRIG_GAP        (lag-free, high rate)
#   attitude: IMU heading hold, correction sign MEASURED (never assumed)
#   guards  : gross-yaw abort, absolute travel cap, time limit
#
# Odometry is referenced to o_ref taken BEFORE any motion, so the yaw probe's
# net displacement is carried in the trigger arithmetic rather than corrupting
# the anchor.
# =============================================================================

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

G_MM          = 990.0    # mean of three measured start placements (986.7/984.7/1000.0)
K_MM_PER_DEG  = 0.491192 # RUN-5 same-run T3 pair: (1000-52)/1930
TRIG_GAP      = 44.0     # solved from E[gap] >= 3*sigma_g, not tuned
                         # -> predicted final gap 35.3 mm (S = 11.0, loop bias 1.8)

P_ML, P_MR    = Port.C, Port.D
SGN_L, SGN_R  = -1, 1    # translating configuration, confirmed in RUNs 2, 3 and 4

SPEED_CMD     = 750      # deg/s, below saturation so the controllers regulate
HEAD_GAIN     = 7.0      # deg/s per deg, from a 0.3 s closed-loop time constant
CORR_MAX      = 120.0
YAW_PROBE_CMD = 250
YAW_PROBE_MS  = 200
HEAD_ABORT    = 15.0
ACCEL_LIM     = 3000
LOOP_MS       = 10
STOP_MS       = 5
TRAVEL_MARGIN = 40.0     # mm beyond the trigger point before the hard cap fires
T_LIMIT_MULT  = 3.0
V_NOM_MM_S    = 368
CRUISE_FROM   = 300
NBUF          = 200

hub   = PrimeHub()
clock = StopWatch()


def emit(sensor, value):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'
                 % (clock.time(), sensor, value))


bt = [0] * NBUF
bo = [0] * NBUF
n  = 0

mL = mR = None
yaw_sign = 1.0


def odo():
    return 0.5 * (SGN_L * mL.angle() + SGN_R * mR.angle())


def stop_motors():
    try:
        mL.brake()
        mR.brake()
    except Exception:
        pass


def drive(v_cmd):
    c = yaw_sign * HEAD_GAIN * hub.imu.heading()
    if c > CORR_MAX:
        c = CORR_MAX
    elif c < -CORR_MAX:
        c = -CORR_MAX
    mL.run(SGN_L * (v_cmd - c))
    mR.run(SGN_R * (v_cmd + c))


try:
    wait(900)
    try:
        hub.imu.reset_heading(0)
    except Exception:
        pass

    ok = 1
    try:
        mL = Motor(P_ML)
        mR = Motor(P_MR)
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

    # Reference odometry BEFORE any motion, so the probe cannot corrupt the anchor.
    o_ref = odo()

    # Yaw-sign probe: which way does a differential command turn us? Assuming this
    # makes the heading correction positive feedback, so it is measured.
    h0 = hub.imu.heading()
    mL.run(SGN_L * YAW_PROBE_CMD)
    mR.run(-SGN_R * YAW_PROBE_CMD)
    wait(YAW_PROBE_MS)
    stop_motors()
    wait(200)
    dhy = hub.imu.heading() - h0
    mL.run(-SGN_L * YAW_PROBE_CMD)
    mR.run(SGN_R * YAW_PROBE_CMD)
    wait(YAW_PROBE_MS)
    stop_motors()
    wait(350)
    yaw_sign = 1.0 if dhy > 0 else -1.0
    emit("yaw_probe_dh", dhy)
    emit("probe_net_deg", odo() - o_ref)
    try:
        hub.imu.reset_heading(0)
    except Exception:
        pass

    travel_lim = (G_MM - TRIG_GAP + TRAVEL_MARGIN) / K_MM_PER_DEG
    t_limit_ms = T_LIMIT_MULT * 1000.0 * (G_MM - TRIG_GAP) / V_NOM_MM_S + 800.0

    # ---------------- HOT PATH ---------------------------------------------
    t_start = clock.time()
    reason = 0
    d_T = 0.0
    t_fire = 0
    hmax = 0.0
    swL = swR = 0.0
    ncr = 0
    ax0 = ax1 = 0.0
    nax = 0

    drive(SPEED_CMD)

    while True:
        t = clock.time()
        dth = odo() - o_ref
        d_go = G_MM - dth * K_MM_PER_DEG
        th = hub.imu.heading()
        if th > hmax:
            hmax = th
        elif -th > hmax:
            hmax = -th

        if dth > CRUISE_FROM:
            swL += SGN_L * mL.speed()
            swR += SGN_R * mR.speed()
            ncr += 1
        elif nax < 30:
            a = hub.imu.acceleration()      # direction witness, restored
            ax0 += a[0]
            ax1 += a[1]
            nax += 1

        if n < NBUF:
            bt[n] = t
            bo[n] = int(dth)
            n += 1

        if d_go <= TRIG_GAP:
            reason = 1
            d_T = d_go
            t_fire = t
            break
        if th > HEAD_ABORT or th < -HEAD_ABORT:
            reason = 6
            d_T = d_go
            t_fire = t
            break
        if dth > travel_lim:
            reason = 3
            d_T = d_go
            t_fire = t
            break
        if t - t_start > t_limit_ms:
            reason = 5
            d_T = d_go
            t_fire = t
            break

        drive(SPEED_CMD)
        wait(LOOP_MS)

    h_trig = hub.imu.heading()
    odo_trig = odo() - o_ref

    stop_motors()
    while clock.time() - t_fire < 500:
        if n < NBUF:
            bt[n] = clock.time()
            bo[n] = int(odo() - o_ref)
            n += 1
        wait(STOP_MS)

    odo_rest = odo() - o_ref

    # ---------------- SCALARS ----------------------------------------------
    emit("trigger_reason", reason)
    emit("d_go_trigger", d_T)
    emit("odo_trigger_deg", odo_trig)
    emit("odo_rest_deg", odo_rest)
    emit("S_mm", (odo_rest - odo_trig) * K_MM_PER_DEG)
    emit("g_est_final", G_MM - odo_rest * K_MM_PER_DEG)   # SYS-8 onboard estimate
    emit("heading_trigger", h_trig)
    emit("heading_rest", hub.imu.heading())
    emit("heading_max", hmax)
    emit("cruise_wL", swL / ncr if ncr else 0.0)
    emit("cruise_wR", swR / ncr if ncr else 0.0)
    emit("accel_x_mean", ax0 / nax if nax else 0.0)
    emit("accel_y_mean", ax1 / nax if nax else 0.0)
    emit("t_trigger", t_fire)
    emit("t_hot_start", t_start)
    emit("samples", n)

    step = n // 6
    if step < 1:
        step = 1
    i = 0
    while i < n:
        stdout.write('{"timestamp_ms":%d,"sensor":"odo_deg","value":%f}\n' % (bt[i], bo[i]))
        i += step

finally:
    stop_motors()
    stdout.write('{"event":"end"}\n')
