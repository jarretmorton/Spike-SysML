# =============================================================================
# C1 CHARACTERIZATION PROGRAM  --  Wall-Approach Rover
# =============================================================================
# STATUS: STAGED FOR REVIEW. NOT YET FLASHED. Awaiting explicit operator
#         go-ahead AND confirmation the rover is power-cycled + squared up at
#         the start line (~1000 mm from the wall) before any flash_program.
#
# ROLE (per Calibration Plan v1, run schedule 2.6):
#   C1 = first characterization run at a CONSERVATIVE trigger (~180 mm reported).
#   This program is the LOCKED SUPERSET: identical port/direction detection,
#   acceleration-to-max, paced control loop, trigger mechanism, hold()-both
#   stop, and try/finally (motors stop + sentinel) that the operation program
#   will use. The ONLY things that change for V1/operation are (a) the trigger
#   THRESHOLD value and (b) extra characterization logging is trimmed. Extra
#   logging here is buffered and dumped AFTER the motors stop, never on the hot
#   path, so hot-path timing (hence t_response and D_stop) matches operation.
#
# WIRE CONTRACT (docs/wire_contract.md, enforced by the host):
#   one JSON line per reading: {"timestamp_ms":<int hub clock>,"sensor":<str>,
#   "value":<float>} ; end EVERY run with {"event":"end"} or the last samples
#   are lost to BLE buffering. The hub clock (StopWatch) is the only valid time.
#
# HARDWARE (ports + drivetrain sign UNKNOWN -> detected below):
#   2 drive motors (differential), 3 ultrasonic (2 forward + 1 rear),
#   1 downward color/reflectance (dropped effector, ignored). 6 devices/6 ports.
# =============================================================================

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import wait, StopWatch

try:
    from usys import stdout
except ImportError:
    from sys import stdout

# ----------------------------------------------------------------------------
# Tunables (LOCKED for the program; only R_TRIGGER changes across runs)
# ----------------------------------------------------------------------------
R_TRIGGER      = 180.0   # C1 conservative trigger, reported mm (>= r_min prior)
MAX_CMD        = 1000.0  # commanded drive speed, deg/s (near SPIKE motor max)
LIM_SPEED      = 1400.0  # raised control speed limit so run() regulates at max
LIM_ACCEL      = 12000.0 # deg/s^2, snappy accel -> reach flat cruise fast
LOOP_MS        = 20      # paced control-loop period (hot path)
EMIT_EVERY     = 3       # live-emit every Nth loop (downsample hot path ~17 Hz)
MAX_RUN_MS     = 8000    # safety: abort approach if it runs this long
REST_EPS       = 20.0    # deg/s below which a motor counts as stopped
SETTLE_MAX_MS  = 1500    # max wait for full stop after hold()
NUDGE_SPEED    = 150.0   # deg/s detection-nudge speed
NUDGE_MS       = 250     # detection-nudge duration
NUDGE_SETTLE   = 200     # settle after each nudge before reading
HEAD_SPIN_DEG  = 8.0     # |dheading| above this => that combo is a SPIN
MOVE_THRESH_MM = 8.0     # |ddistance| above this => that sensor clearly moved

hub   = PrimeHub()
clock = StopWatch()

PORTS      = [Port.A, Port.B, Port.C, Port.D, Port.E, Port.F]
PORT_INDEX = {Port.A: 0, Port.B: 1, Port.C: 2, Port.D: 3, Port.E: 4, Port.F: 5}


DRIVE_MOTORS = []  # module-level so the finally-block safety stop can reach them


def emit(sensor, value):
    # one telemetry line, hub-clock timestamp
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'
                 % (clock.time(), sensor, value))


def emit_at(t_ms, sensor, value):
    # telemetry line at a specific (buffered) hub-clock timestamp
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'
                 % (t_ms, sensor, value))


def read_accel_axes():
    # Non-load-bearing cross-check channel. Robust to API shape differences.
    try:
        a = hub.imu.acceleration()
        return float(a[0]), float(a[1]), float(a[2])
    except Exception:
        return None


def main():
    # -------------------------------------------------------------------
    # 1. PORT/DEVICE DETECTION (probe each port once; keep first success).
    #    Order UltrasonicSensor -> Motor -> ColorSensor. A failed wrong-device
    #    construction does not claim the port; a success claims it, so each
    #    device is constructed exactly ONCE (avoids EBUSY double-claim).
    # -------------------------------------------------------------------
    motors = []       # list of (port, Motor)
    ultras = []       # list of (port, UltrasonicSensor)
    colors = []       # list of (port, ColorSensor)  -- dropped effector

    for p in PORTS:
        obj = None
        kind = None
        try:
            obj = UltrasonicSensor(p); kind = 'u'
        except Exception:
            try:
                obj = Motor(p); kind = 'm'
            except Exception:
                try:
                    obj = ColorSensor(p); kind = 'c'
                except Exception:
                    obj = None; kind = None
        if kind == 'u':
            ultras.append((p, obj))
        elif kind == 'm':
            motors.append((p, obj))
        elif kind == 'c':
            colors.append((p, obj))

    emit('det_n_motors', len(motors))
    emit('det_n_ultras', len(ultras))
    emit('det_n_colors', len(colors))
    for (p, _) in motors:
        emit('det_motor_port', PORT_INDEX[p])
    for (p, _) in ultras:
        emit('det_ultra_port', PORT_INDEX[p])
    for (p, _) in colors:
        emit('det_color_port', PORT_INDEX[p])

    # Guard: need at least 2 motors and 2 ultrasonics to proceed safely.
    if len(motors) < 2 or len(ultras) < 2:
        emit('det_error', 1.0)
        return  # finally-block still emits the sentinel

    m0 = motors[0][1]
    m1 = motors[1][1]
    drive = [m0, m1]
    DRIVE_MOTORS.append(m0)
    DRIVE_MOTORS.append(m1)

    # Baseline ultrasonic readings (rover squared up ~1000 mm from wall,
    # open space behind: forward sensors ~1000, rear larger/saturated).
    def read_all_ultras():
        vals = []
        for (_, u) in ultras:
            try:
                vals.append(float(u.distance()))
            except Exception:
                vals.append(-1.0)
        return vals

    base = read_all_ultras()
    for idx in range(len(ultras)):
        emit('det_base_u%d' % idx, base[idx])
    h_base = hub.imu.heading()

    # -------------------------------------------------------------------
    # 2. DIRECTION DETECTION (deterministic; paired nudges cancel net creep).
    #    Nudge A = (+,+); undo (-,-). Nudge B = (+,-); undo (-,+).
    #    Exactly one of A,B translates (small |dheading|), the other spins.
    # -------------------------------------------------------------------
    def nudge(s0, s1, ms):
        m0.run(s0 * NUDGE_SPEED)
        m1.run(s1 * NUDGE_SPEED)
        wait(ms)
        m0.hold(); m1.hold()
        wait(NUDGE_SETTLE)

    # Nudge A (+,+)
    nudge(+1, +1, NUDGE_MS)
    afterA = read_all_ultras()
    hA = hub.imu.heading()
    dA = [afterA[i] - base[i] for i in range(len(ultras))]
    dheadA = hA - h_base
    nudge(-1, -1, NUDGE_MS)          # undo
    wait(NUDGE_SETTLE)

    baseB = read_all_ultras()
    hB0 = hub.imu.heading()
    # Nudge B (+,-)
    nudge(+1, -1, NUDGE_MS)
    afterB = read_all_ultras()
    hB = hub.imu.heading()
    dB = [afterB[i] - baseB[i] for i in range(len(ultras))]
    dheadB = hB - hB0
    nudge(-1, +1, NUDGE_MS)          # undo
    wait(NUDGE_SETTLE)

    for i in range(len(ultras)):
        emit('det_dA_u%d' % i, dA[i])
        emit('det_dB_u%d' % i, dB[i])
    emit('det_dheadA', dheadA)
    emit('det_dheadB', dheadB)

    # Which combo translated? (smaller |dheading| => translation)
    A_is_translation = abs(dheadA) < abs(dheadB)
    if A_is_translation:
        trans_d = dA
        combo = (+1, +1)
    else:
        trans_d = dB
        combo = (+1, -1)
    emit('det_trans_is_A', 1.0 if A_is_translation else 0.0)

    # Within the translation nudge: sensors that DECREASED face the motion
    # direction of the "+" version of the combo.
    n_dec = 0
    n_inc = 0
    dec_idx = []
    inc_idx = []
    for i in range(len(ultras)):
        if trans_d[i] < -MOVE_THRESH_MM:
            n_dec += 1; dec_idx.append(i)
        elif trans_d[i] > MOVE_THRESH_MM:
            n_inc += 1; inc_idx.append(i)

    forward_sign = +1
    fwd_idx = []
    if n_dec >= 2:
        # "+" combo drives FORWARD; the 2 decreasing sensors are forward.
        forward_sign = +1
        fwd_idx = dec_idx
    elif n_dec == 1 and n_inc >= 2:
        # "+" combo drives BACKWARD; the 2 increasing sensors are forward.
        forward_sign = -1
        fwd_idx = inc_idx
    else:
        # Ambiguous nudge -> robust fallback by baseline magnitude:
        # the 2 smallest baseline readings are the forward pair (facing wall).
        order = sorted(range(len(ultras)), key=lambda i: base[i])
        fwd_idx = order[:2]
        # Sign: assume "+" combo forward unless the forward pair increased.
        s = 0.0
        for i in fwd_idx:
            s += trans_d[i]
        forward_sign = -1 if s > 0 else +1
    emit('det_forward_sign', float(forward_sign))
    emit('det_n_fwd_found', float(len(fwd_idx)))

    # Cross-check the nudge classification against baseline magnitude and log
    # any disagreement (forward/rear should also be the 2 smallest baselines).
    order = sorted(range(len(ultras)), key=lambda i: base[i])
    mag_fwd = set(order[:2])
    emit('det_fwd_agrees_magnitude',
         1.0 if set(fwd_idx) == mag_fwd else 0.0)

    if len(fwd_idx) < 2:
        # last-resort: take 2 smallest baselines
        fwd_idx = order[:2]

    # Per-motor forward sign so BOTH wheels propel the rover forward.
    S0 = forward_sign * combo[0]
    S1 = forward_sign * combo[1]
    emit('det_sign0', float(S0))
    emit('det_sign1', float(S1))

    # Primary/secondary forward sensors (deterministic: smaller baseline = primary)
    if base[fwd_idx[0]] <= base[fwd_idx[1]]:
        pi, si = fwd_idx[0], fwd_idx[1]
    else:
        pi, si = fwd_idx[1], fwd_idx[0]
    u_prim = ultras[pi][1]
    u_sec = ultras[si][1]
    emit('det_primary_port', float(PORT_INDEX[ultras[pi][0]]))
    emit('det_secondary_port', float(PORT_INDEX[ultras[si][0]]))
    rear_idx = [i for i in range(len(ultras)) if i not in (pi, si)]
    if rear_idx:
        emit('det_rear_port', float(PORT_INDEX[ultras[rear_idx[0]][0]]))

    # -------------------------------------------------------------------
    # 3. ACCELERATE TO MAX + PACED CONTROL LOOP (hot path minimal).
    # -------------------------------------------------------------------
    # Raise control limits so run() regulates both wheels at the same high
    # speed (straight AND maximal). Best-effort; fall back to plain run().
    for m in drive:
        try:
            m.control.limits(speed=LIM_SPEED, acceleration=LIM_ACCEL)
        except Exception:
            pass

    def fwd_angle():
        # signed so both motors contribute positively to forward travel (deg)
        return 0.5 * (S0 * m0.angle() + S1 * m1.angle())

    m0.reset_angle(0)
    m1.reset_angle(0)

    m0.run(S0 * MAX_CMD)
    m1.run(S1 * MAX_CMD)

    buf = []            # (t, d_prim, d_sec, heading, fwd_angle_deg)
    omega_max_obs = 0.0
    i = 0
    t0 = clock.time()
    triggered = False
    t_trig = ang_trig = d1_trig = d2_trig = h_trig = 0.0

    while True:
        t = clock.time()
        try:
            d1 = float(u_prim.distance())
        except Exception:
            d1 = -1.0
        try:
            d2 = float(u_sec.distance())
        except Exception:
            d2 = -1.0
        h = hub.imu.heading()
        a = fwd_angle()
        buf.append((t, d1, d2, h, a))

        sp = 0.5 * (abs(m0.speed()) + abs(m1.speed()))
        if sp > omega_max_obs:
            omega_max_obs = sp

        if (i % EMIT_EVERY) == 0:
            emit_at(t, 'distance', d1)
            emit_at(t, 'distance2', d2)
            emit_at(t, 'heading', h)

        if d1 >= 0.0 and d1 <= R_TRIGGER:
            triggered = True
            t_trig = t; ang_trig = a; d1_trig = d1; d2_trig = d2; h_trig = h
            break

        if (t - t0) > MAX_RUN_MS:
            break

        i += 1
        wait(LOOP_MS)

    # -------------------------------------------------------------------
    # 4. STOP: hold() both, settle to rest, latch rest state.
    # -------------------------------------------------------------------
    m0.hold()
    m1.hold()
    settle_start = clock.time()
    while (clock.time() - settle_start) < SETTLE_MAX_MS:
        if abs(m0.speed()) < REST_EPS and abs(m1.speed()) < REST_EPS:
            break
        wait(20)
    t_rest = clock.time()
    ang_rest = fwd_angle()
    try:
        d1_rest = float(u_prim.distance())
    except Exception:
        d1_rest = -1.0
    try:
        d2_rest = float(u_sec.distance())
    except Exception:
        d2_rest = -1.0
    rest_speed = max(abs(m0.speed()), abs(m1.speed()))
    h_rest = hub.imu.heading()

    D_stop_deg = ang_rest - ang_trig   # forward degrees, trigger -> rest

    # -------------------------------------------------------------------
    # 5. EMIT LATCHED SCALARS (the objective-critical measurements).
    #    D_stop in mm requires k_speed, derived offline from the approach
    #    (-d(report)/d(angle)); here we report the raw encoder delta + the
    #    reports so the host can compute everything with provenance.
    # -------------------------------------------------------------------
    emit('triggered', 1.0 if triggered else 0.0)
    emit('trigger_report', d1_trig)
    emit('trigger_report2', d2_trig)
    emit('rest_report', d1_rest)
    emit('rest_report2', d2_rest)
    emit('angle_trigger_deg', ang_trig)
    emit('angle_rest_deg', ang_rest)
    emit('D_stop_deg', D_stop_deg)
    emit('rest_speed_deg_s', rest_speed)
    emit('omega_cruise_deg_s', omega_max_obs)
    emit('heading_trigger', h_trig)
    emit('heading_rest', h_rest)
    emit('heading_base', h_base)
    emit('t_trigger_ms', float(t_trig))
    emit('t_rest_ms', float(t_rest))
    # accel cross-check at rest (non-load-bearing)
    acc = read_accel_axes()
    if acc is not None:
        emit('accel_x_rest', acc[0])
        emit('accel_y_rest', acc[1])
        emit('accel_z_rest', acc[2])

    # -------------------------------------------------------------------
    # 6. DUMP FULL-RATE BUFFER (post-stop; off the hot path).
    #    hf_* names keep this provenance-separate from the live downsampled
    #    channels. Each buffered sample -> 4 lines at its buffered timestamp.
    # -------------------------------------------------------------------
    for (t, d1, d2, h, a) in buf:
        emit_at(t, 'hf_distance', d1)
        emit_at(t, 'hf_distance2', d2)
        emit_at(t, 'hf_heading', h)
        emit_at(t, 'hf_angle_deg', a)


# ---------------------------------------------------------------------------
# try/finally guarantees motors are left not-driving and the sentinel is sent,
# even if anything above raises.
# ---------------------------------------------------------------------------
try:
    main()
finally:
    # ensure motors are left not-driving, then always send the sentinel
    for _mm in DRIVE_MOTORS:
        try:
            _mm.stop()
        except Exception:
            pass
    stdout.write('{"event":"end"}\n')
