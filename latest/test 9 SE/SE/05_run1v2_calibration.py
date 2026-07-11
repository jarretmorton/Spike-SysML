# =====================================================================
# Run 1 v2 -- CALIBRATION   (Pybricks / SPIKE Prime)  [Calibration Plan v1.1]
# Core built-ins only (no 'sys'/'array').  Telemetry via print(), buffered
# and dumped per cycle within the ~30 lines/s BLE budget.
#
# Config HARD-CODED from Run 1 (motors C/D; fwd rangers A primary, B check;
# rear E; polarity (sL,sR)=(-1,+1)), gated by a baseline sanity check.
# Heading held ~0 (closed loop) so the path is straight and ranger A keeps
# lock; trigger on ranger A; k-independent min(A,B) backstop for safety.
# =====================================================================
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port, Axis
from pybricks.tools import wait, StopWatch

clock = StopWatch()
hub = PrimeHub()

# ---------------- tunables ----------------
DT_MS            = 12
LOG_EVERY        = 3            # log every Nth approach iteration (downsample)
BASE_CMD         = 1000        # near motor max -> trim is effective
KP_HEAD          = 20          # heading P-gain (cmd per degree)
TRIM_CAP         = 300         # max heading trim
SPIN             = 250         # square-up rotation speed
D_THR            = (350, 300, 250)   # mm on ranger A (conservative)
HARD_RANGER_MIN  = 150         # mm on min(A,B): k-independent backstop
HARD_TIME_MS     = 2000
HARD_ENC_APPARENT= 1400        # deg
SETTLE_MS        = 700
REST_DT_MS       = 50
REV_CMD          = 500
REPOS_TARGET     = 800
REPOS_TIMEOUT_MS = 3500
TIME_GUARD_MS    = 42000       # ensure clean sentinel before 50s host timeout
N_CYCLES         = 3
SL               = -1          # left = motor C
SR               = 1           # right = motor D

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
    print('{"timestamp_ms": %d, "sensor": "%s", "value": %s}'
          % (t, sensor, _fmt(value)))

BUF_N = 1200
_bt = [0] * BUF_N
_bc = [0] * BUF_N
_bv = [0] * BUF_N
_bi = 0
# heading stored as int tenths of a degree (code 4)
CODE = {2:"d_f0", 3:"d_f1", 4:"heading_dx10", 5:"acc_x", 6:"acc_y", 7:"acc_z",
        8:"ml_deg", 9:"mr_deg", 12:"phase"}

def logbuf(code, value, t):
    global _bi
    if _bi < BUF_N:
        _bt[_bi] = t; _bc[_bi] = code; _bv[_bi] = value; _bi += 1

def dumpbuf():
    global _bi
    n = _bi
    for k in range(n):
        emit(CODE.get(_bc[k], "c%d" % _bc[k]), _bv[k], _bt[k])
    _bi = 0

class AbortRun(Exception):
    pass

# ---------------- hard-coded devices (constructed once) ----------------
m_left  = Motor(Port.C)          # left, sign SL
m_right = Motor(Port.D)          # right, sign SR
motors_list = [m_left, m_right]
rf0 = UltrasonicSensor(Port.A)   # forward primary (baselined ~true)
rf1 = UltrasonicSensor(Port.B)   # forward cross-check (reads short)
rr  = UltrasonicSensor(Port.E)   # rear (sanity only)

def clampc(v):
    if v > BASE_CMD + TRIM_CAP: return BASE_CMD + TRIM_CAP
    if v < BASE_CMD - TRIM_CAP: return BASE_CMD - TRIM_CAP
    return v

def drive_straight():
    # hold heading ~0 by trimming the faster wheel; both near max
    h = hub.imu.heading()
    adj = KP_HEAD * h
    if adj > TRIM_CAP: adj = TRIM_CAP
    elif adj < -TRIM_CAP: adj = -TRIM_CAP
    lc = clampc(BASE_CMD - adj)
    rc = clampc(BASE_CMD + adj)
    m_left.run(SL * lc); m_right.run(SR * rc)

def square_up():
    t0 = clock.time()
    while (clock.time() - t0) < 1500:
        h = hub.imu.heading()
        if -2 < h < 2:
            break
        d = 1 if h > 0 else -1        # (+,+) decreases heading
        m_left.run(d * SPIN); m_right.run(d * SPIN)
        wait(20)
    m_left.brake(); m_right.brake()
    wait(250)

def reposition():
    t0 = clock.time()
    m_left.run(-SL * REV_CMD); m_right.run(-SR * REV_CMD)   # straight reverse
    while rf0.distance() < REPOS_TARGET and (clock.time() - t0) < REPOS_TIMEOUT_MS:
        wait(40)
    m_left.brake(); m_right.brake()
    wait(300)

def approach_and_stop(cycle):
    thr = D_THR[cycle]
    m_left.reset_angle(0); m_right.reset_angle(0)
    t_start = clock.time()
    reason = 0
    i = 0
    logbuf(12, 1, t_start)                # phase 1 = approach
    while True:
        t = clock.time()
        drive_straight()
        d0 = rf0.distance(); d1 = rf1.distance()
        dmin = d0 if d0 < d1 else d1
        ml = m_left.angle(); mr = m_right.angle()
        enc_app = 0.5 * (abs(ml) + abs(mr))
        if (i % LOG_EVERY) == 0:
            logbuf(2, d0, t); logbuf(3, d1, t)
            logbuf(4, int(hub.imu.heading() * 10), t)
            logbuf(8, ml, t); logbuf(9, mr, t)
        i += 1
        if d0 <= thr:
            reason = 1; break             # normal trigger (ranger A)
        if dmin <= HARD_RANGER_MIN:
            reason = 2; break             # k-independent min(A,B) backstop
        if (t - t_start) >= HARD_TIME_MS:
            reason = 3; break
        if enc_app >= HARD_ENC_APPARENT:
            reason = 4; break
        wait(DT_MS)
    m_left.brake(); m_right.brake()
    logbuf(12, 2, clock.time())           # phase 2 = brake/settle
    t_rest0 = clock.time()
    while (clock.time() - t_rest0) < SETTLE_MS:
        tt = clock.time()
        logbuf(2, rf0.distance(), tt)
        logbuf(3, rf1.distance(), tt)
        logbuf(5, int(hub.imu.acceleration(Axis.X)), tt)
        logbuf(6, int(hub.imu.acceleration(Axis.Y)), tt)
        logbuf(7, int(hub.imu.acceleration(Axis.Z)), tt)
        wait(REST_DT_MS)
    emit("cycle", cycle)
    emit("stop_reason", reason)
    emit("trigger_thr", thr)
    return reason

# ============================ main ============================
try:
    emit("run_id", 2)                     # Run 1 v2
    emit("phase", 0)
    try:
        hub.imu.reset_heading(0)
    except Exception:
        pass
    bA = rf0.distance(); bB = rf1.distance(); bE = rr.distance()
    emit("baseline_A", bA); emit("baseline_B", bB); emit("baseline_E", bE)
    ok = (750 <= bA <= 1300) and (750 <= bB <= 1300) and (abs(bA - bB) <= 250) and (bE > 1500)
    if not ok:
        emit("abort_reason", 7)           # 7 = baseline sanity failed
        raise AbortRun()

    for c in range(N_CYCLES):
        if clock.time() > TIME_GUARD_MS:
            emit("time_guard", c)
            break
        square_up()
        d = rf0.distance()
        emit("pre_approach_d", d)
        if d < REPOS_TARGET - 50:
            reposition()
        approach_and_stop(c)
        dumpbuf()
        if c < N_CYCLES - 1:
            reposition()

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
    print('{"event": "end"}')
