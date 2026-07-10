# =====================================================================
# Run 1 -- CALIBRATION + on-hub DISCOVERY   (Pybricks / SPIKE Prime)
#
# Purpose (per Calibration Plan v1.0 sec.4): in ONE flash-and-run,
#   (a) discover port map, drive polarity, and which two rangers face
#       forward -- ON HUB, no operator input, no extra run;
#   (b) run the operation HOT PATH three times (test-like-you-fly) to
#       bind v_max, d_stop_const, a_decel, tChain, refresh, heading drift,
#       sigma_brake, sigma_meas, k_gain.
#
# SAFETY (collision-safe even if discovery is wrong):
#   * forward rangers are identified from the BASELINE reading (~1000 mm
#     at the known squared-up start); the two must read ~equal and in
#     range or the run ABORTS before any fast motion.
#   * the fast approach stops on min(forward rangers) -- and a lower
#     absolute backstop HARD_RANGER_FWD (k-INDEPENDENT) catches a missed
#     trigger; both act on the *forward* rangers so nothing behind the
#     rover can false-abort.
#   * a TIME cap and a generous ENCODER cap bound the backward/runaway
#     case (reversed polarity) so the rover can never roll away unbounded.
#   * conservative triggers (350/300/250 mm) keep every Run-1 rest far
#     from the wall.  d_stop_const is speed-dependent, not trigger-
#     dependent, so it transfers to the tight operation trigger.
#
# TELEMETRY: hot-path readings go to a preallocated array buffer and are
#   DUMPED after the motors stop each cycle (never on the hot path).
#   Every run ends with the flush sentinel.  Timestamps are hub-clock ms.
#
# ASSUMPTION (flagged for review): a failed typed-device construction
#   raises OSError WITHOUT permanently claiming the port (standard
#   Pybricks behavior), so try/except probing is safe.  If violated the
#   run aborts safely (motors never commanded) and we adjust.
# =====================================================================
import sys
from array import array
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port, Axis
from pybricks.tools import wait, StopWatch

clock = StopWatch()
hub = PrimeHub()

# ---------------- tunables ----------------
DT_MS            = 12          # hot-loop period (< expected refresh, to see steps)
MAX_CMD          = 2000        # deg/s command; saturates to motor ceiling
REV_CMD          = 400         # deg/s reverse (reposition between cycles)
D_THR            = (350, 300, 250)   # mm: conservative per-cycle triggers
HARD_RANGER_FWD  = 220         # mm: absolute backstop on forward rangers (k-indep.)
HARD_TIME_MS     = 2500        # per-approach time cap (bounds runaway)
HARD_ENC_APPARENT= 2000        # deg: encoder cap (backstop, backward runaway)
SETTLE_MS        = 700         # rest dwell (dense rest sampling)
REPOS_TARGET     = 800         # mm: reposition distance between cycles
REPOS_TIMEOUT_MS = 4000        # reverse safety timeout
NUDGE_SPEED      = 200         # deg/s discovery nudge
NUDGE_MS         = 300
START_NOM        = 1000        # mm expected start distance
FWD_LO, FWD_HI   = 750, 1300   # mm: acceptable forward-ranger baseline window
FWD_MATCH        = 220         # mm: max diff between the two forward rangers
N_CYCLES         = 3

# ---------------- telemetry ----------------
def _fmt(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return "%.4f" % v
    if isinstance(v, str):
        return '"%s"' % v
    return str(v)

def emit(sensor, value, t=None):
    if t is None:
        t = clock.time()
    sys.stdout.write('{"timestamp_ms": %d, "sensor": "%s", "value": %s}\n'
                     % (t, sensor, _fmt(value)))

# preallocated hot-path buffer (array-backed: memory-light, no GC churn)
BUF_N = 5000
_bt = array('i', [0]) * BUF_N      # timestamp ms
_bc = array('B', [0]) * BUF_N      # channel code
_bv = array('f', [0.0]) * BUF_N    # value
_bi = 0
CODE = {1:"d_fwd_min", 2:"d_f0", 3:"d_f1", 4:"heading", 5:"acc_x", 6:"acc_y",
        7:"acc_z", 8:"ml_deg", 9:"mr_deg", 10:"ml_dps", 11:"mr_dps", 12:"phase"}

def logbuf(code, value, t):
    global _bi
    if _bi < BUF_N:
        _bt[_bi] = t; _bc[_bi] = code; _bv[_bi] = value; _bi += 1

def dumpbuf():
    global _bi
    for k in range(_bi):
        emit(CODE.get(_bc[k], "c%d" % _bc[k]), _bv[k], _bt[k])
    _bi = 0

class AbortRun(Exception):
    pass

# ---------------- device handles (filled by discovery) ----------------
motors_list = []
m_left = None
m_right = None
rf0 = rf1 = rr = None
all_fwd = []

PORTS = ((Port.A, "A"), (Port.B, "B"), (Port.C, "C"),
         (Port.D, "D"), (Port.E, "E"), (Port.F, "F"))

def discover_ports():
    """Identify device on each port via try/except probing."""
    global m_left, m_right, rf0, rf1, rr, all_fwd
    motors = []
    rangers = []      # list of (obj, name)
    colors = []
    for port, name in PORTS:
        obj = None
        code = 0                       # 0=empty 1=motor 2=ranger 3=color
        try:
            obj = Motor(port)
            motors.append(obj); motors_list.append(obj)
            code = 1
        except OSError:
            pass
        if code == 0:
            try:
                obj = UltrasonicSensor(port)
                rangers.append((obj, name))
                code = 2
            except OSError:
                pass
        if code == 0:
            try:
                obj = ColorSensor(port)
                colors.append((obj, name))
                code = 3
            except OSError:
                pass
        emit("port_type_%s" % name, code)

    emit("n_motors", len(motors))
    emit("n_rangers", len(rangers))
    emit("n_colors", len(colors))
    if len(motors) != 2 or len(rangers) != 3:
        emit("abort_reason", 1)   # 1 = unexpected device inventory
        raise AbortRun()
    m_left, m_right = motors[0], motors[1]

    # identify forward rangers from baseline (~START_NOM, squared up)
    rd = []
    for obj, name in rangers:
        d = obj.distance()
        rd.append((d, obj, name))
        emit("ranger_baseline_%s" % name, d)
    inrange = [x for x in rd if FWD_LO <= x[0] <= FWD_HI]
    if len(inrange) < 2:
        emit("abort_reason", 2)   # 2 = cannot find two forward rangers near start
        raise AbortRun()
    inrange.sort(key=lambda x: abs(x[0] - START_NOM))
    fwd = inrange[:2]
    if abs(fwd[0][0] - fwd[1][0]) > FWD_MATCH:
        emit("abort_reason", 3)   # 3 = forward rangers disagree (not squared / misID)
        raise AbortRun()
    rf0, rf1 = fwd[0][1], fwd[1][1]
    all_fwd = [rf0, rf1]
    fwd_names = set([fwd[0][2], fwd[1][2]])
    for d, obj, name in rd:
        role = 1 if name in fwd_names else 2      # 1=forward, 2=rear
        emit("ranger_role_%s" % name, role)
        if role == 2:
            rr = obj

def fwd_min():
    a = rf0.distance(); b = rf1.distance()
    return a if a < b else b

def nudge(s0, s1, ms):
    m_left.run(s0 * NUDGE_SPEED); m_right.run(s1 * NUDGE_SPEED)
    wait(ms)
    m_left.brake(); m_right.brake()
    wait(150)

def discover_polarity():
    """Determine (sL,sR) so commanding + drives the rover FORWARD.
       Forward rangers already identified; use their change under a nudge."""
    # baseline
    f0 = 0.5 * (rf0.distance() + rf1.distance())
    h0 = hub.imu.heading()
    # safety: only nudge forward-testing if we have room
    if f0 < 500:
        emit("abort_reason", 4)   # too close to test safely
        raise AbortRun()
    # step 1: (+,+)
    nudge(+1, +1, NUDGE_MS)
    f1 = 0.5 * (rf0.distance() + rf1.distance())
    h1 = hub.imu.heading()
    dF = f1 - f0; dH = h1 - h0
    nudge(-1, -1, NUDGE_MS)         # return
    emit("nudge_pp_dF", dF); emit("nudge_pp_dH", dH)
    if abs(dH) < 15:
        if dF < -8:
            return (+1, +1)
        if dF > 8:
            return (-1, -1)
        emit("abort_reason", 5)     # no measurable motion
        raise AbortRun()
    # step 2: opposed -> try (+,-)
    f0b = 0.5 * (rf0.distance() + rf1.distance())
    h0b = hub.imu.heading()
    nudge(+1, -1, NUDGE_MS)
    f1b = 0.5 * (rf0.distance() + rf1.distance())
    h1b = hub.imu.heading()
    dF2 = f1b - f0b; dH2 = h1b - h0b
    nudge(-1, +1, NUDGE_MS)         # return
    emit("nudge_pm_dF", dF2); emit("nudge_pm_dH", dH2)
    if abs(dH2) < 15:
        if dF2 < -8:
            return (+1, -1)
        if dF2 > 8:
            return (-1, +1)
    emit("abort_reason", 6)         # polarity ambiguous
    raise AbortRun()

def reposition(sL, sR):
    """Reverse (using forward ranger) until ~REPOS_TARGET mm, with timeout."""
    t0 = clock.time()
    m_left.run(-sL * REV_CMD); m_right.run(-sR * REV_CMD)
    while fwd_min() < REPOS_TARGET and (clock.time() - t0) < REPOS_TIMEOUT_MS:
        emit("repos_d", fwd_min())
        wait(40)
    m_left.brake(); m_right.brake()
    wait(400)

def approach_and_stop(cycle, sL, sR):
    """The OPERATION hot path (buffered). Returns stop_reason code."""
    thr = D_THR[cycle]
    m_left.reset_angle(0); m_right.reset_angle(0)
    t_start = clock.time()
    reason = 0
    logbuf(12, 1.0, t_start)               # phase 1 = approach
    m_left.run(sL * MAX_CMD); m_right.run(sR * MAX_CMD)
    while True:
        t = clock.time()
        d0 = rf0.distance(); d1 = rf1.distance()
        dmin = d0 if d0 < d1 else d1
        ml = m_left.angle(); mr = m_right.angle()
        enc_app = 0.5 * (abs(ml) + abs(mr))     # apparent (deg) travel
        # log (hot path -> buffer only)
        logbuf(1, float(dmin), t); logbuf(2, float(d0), t); logbuf(3, float(d1), t)
        logbuf(4, hub.imu.heading(), t)
        logbuf(5, hub.imu.acceleration(Axis.X), t)
        logbuf(6, hub.imu.acceleration(Axis.Y), t)
        logbuf(7, hub.imu.acceleration(Axis.Z), t)
        logbuf(8, float(ml), t); logbuf(9, float(mr), t)
        logbuf(10, m_left.speed(), t); logbuf(11, m_right.speed(), t)
        # triggers (priority: normal, then failsafes)
        if dmin <= thr:
            reason = 1; break                    # normal trigger
        if dmin <= HARD_RANGER_FWD:
            reason = 2; break                    # absolute forward backstop
        if (t - t_start) >= HARD_TIME_MS:
            reason = 3; break                    # time cap
        if enc_app >= HARD_ENC_APPARENT:
            reason = 4; break                    # encoder cap
        wait(DT_MS)
    # brake: passive, monotonic (rest = closest approach)
    m_left.brake(); m_right.brake()
    logbuf(12, 2.0, clock.time())               # phase 2 = brake/settle
    # dense rest sampling (off hot path -> direct emit)
    t_rest0 = clock.time()
    while (clock.time() - t_rest0) < SETTLE_MS:
        emit("rest_d_f0", rf0.distance())
        emit("rest_d_f1", rf1.distance())
        emit("rest_heading", hub.imu.heading())
        emit("rest_acc_x", hub.imu.acceleration(Axis.X))
        wait(25)
    emit("cycle", cycle)
    emit("stop_reason", reason)
    emit("trigger_thr", thr)
    return reason

# ============================ main ============================
try:
    emit("run_id", 1)                 # Run 1 = calibration
    emit("phase", 0.0)                # discovery
    discover_ports()
    sL, sR = discover_polarity()
    emit("sign_left", sL); emit("sign_right", sR)

    for c in range(N_CYCLES):
        # ensure a good start distance before each approach
        d0 = fwd_min()
        emit("pre_approach_d", d0)
        if d0 < REPOS_TARGET - 50:
            reposition(sL, sR)
        approach_and_stop(c, sL, sR)
        dumpbuf()                     # flush this cycle's hot-path buffer
        if c < N_CYCLES - 1:
            logbuf(12, 4.0, clock.time())   # phase 4 = reverse (marker)
            reposition(sL, sR)
            dumpbuf()

except AbortRun:
    emit("aborted", 1)
except Exception:
    emit("run_error", 1)
finally:
    for m in motors_list:
        try:
            m.brake()
        except Exception:
            pass
    emit("run_done", 1)
    sys.stdout.write('{"event": "end"}\n')
