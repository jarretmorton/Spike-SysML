# =====================================================================
# VERIFICATION / operation-candidate  (Pybricks / SPIKE Prime)
# Scheme: heading-hold straight drive -> ranger-A position fix @450mm
# (A linear there) -> encoder dead-reckon to D_BRAKE -> passive coast.
# Ranger-B (median-3 filtered) is an independent emergency backstop.
# Settle window logs ENCODERS -> sensor-independent d_stop.
# Frozen constants per Verification Plan v1.0.
# =====================================================================
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port, Axis
from pybricks.tools import wait, StopWatch

clock = StopWatch()
hub = PrimeHub()

# ---- frozen calibration / plan constants ----
K_GAIN           = 0.516      # mm per wheel-degree (Tier 1)
A_FIX_TRIP       = 450        # mm; take the A position-fix here (A still linear)
D_BRAKE          = 100        # mm (A/encoder frame): dead-reckon brake point
B_STOP           = 60         # mm on median-filtered ranger B (low insurance net)
MIN_SAFE         = 30         # mm; enc-cap failsafe floor
# ---- drive / loop ----
DT_MS            = 12
LOG_EVERY        = 3
BASE_CMD         = 1000
KP_HEAD          = 20
TRIM_CAP         = 300
SPIN             = 250
HARD_TIME_MS     = 3000
SETTLE_MS        = 700
REST_DT_MS       = 50
REV_CMD          = 500
REPOS_TARGET     = 800
REPOS_TIMEOUT_MS = 3500
TIME_GUARD_MS    = 80000
N_CYCLES         = 3
SL               = -1
SR               = 1

def _fmt(v):
    if isinstance(v, bool): return "true" if v else "false"
    if isinstance(v, float): return "%.4f" % v
    if isinstance(v, str):   return '"%s"' % v
    return str(v)

def emit(sensor, value, t=None):
    if t is None: t = clock.time()
    print('{"timestamp_ms": %d, "sensor": "%s", "value": %s}' % (t, sensor, _fmt(value)))

BUF_N = 1400
_bt = [0]*BUF_N; _bc = [0]*BUF_N; _bv = [0]*BUF_N; _bi = 0
# 2 d_f0,3 d_f1,4 heading_dx10,5 acc_x,8 ml_deg,9 mr_deg,10 dist_est,12 phase
CODE = {2:"d_f0",3:"d_f1",4:"heading_dx10",5:"acc_x",8:"ml_deg",9:"mr_deg",10:"dist_est",12:"phase"}
def logbuf(code, value, t):
    global _bi
    if _bi < BUF_N:
        _bt[_bi]=t; _bc[_bi]=code; _bv[_bi]=value; _bi+=1
def dumpbuf():
    global _bi
    for k in range(_bi):
        emit(CODE.get(_bc[k], "c%d"%_bc[k]), _bv[k], _bt[k])
    _bi = 0

class AbortRun(Exception): pass

m_left  = Motor(Port.C)
m_right = Motor(Port.D)
motors_list = [m_left, m_right]
rf0 = UltrasonicSensor(Port.A)   # forward primary
rf1 = UltrasonicSensor(Port.B)   # forward secondary (backstop)
rr  = UltrasonicSensor(Port.E)   # rear (logged, not gated)

def clampc(v):
    if v > BASE_CMD + TRIM_CAP: return BASE_CMD + TRIM_CAP
    if v < BASE_CMD - TRIM_CAP: return BASE_CMD - TRIM_CAP
    return v

def drive_straight():
    h = hub.imu.heading()
    adj = KP_HEAD * h
    if adj > TRIM_CAP: adj = TRIM_CAP
    elif adj < -TRIM_CAP: adj = -TRIM_CAP
    m_left.run(SL * clampc(BASE_CMD - adj))
    m_right.run(SR * clampc(BASE_CMD + adj))

def square_up():
    t0 = clock.time()
    while (clock.time() - t0) < 1500:
        h = hub.imu.heading()
        if -2 < h < 2: break
        d = 1 if h > 0 else -1
        m_left.run(d*SPIN); m_right.run(d*SPIN)
        wait(20)
    m_left.brake(); m_right.brake(); wait(250)

def reposition():
    t0 = clock.time()
    m_left.run(-SL*REV_CMD); m_right.run(-SR*REV_CMD)
    while rf0.distance() < REPOS_TARGET and (clock.time()-t0) < REPOS_TIMEOUT_MS:
        wait(40)
    m_left.brake(); m_right.brake(); wait(300)

def med3(a,b,c):
    return sorted((a,b,c))[1]

def read_D0():
    # median of 3 A reads at approach start (reject a lone spike)
    a = rf0.distance(); wait(15)
    b = rf0.distance(); wait(15)
    c = rf0.distance()
    return med3(a,b,c)

def approach_and_stop(cycle):
    m_left.reset_angle(0); m_right.reset_angle(0)
    D0 = read_D0()
    enc_cap = (D0 - MIN_SAFE) / K_GAIN
    t_start = clock.time()
    fixed = False; A_fix = 0.0; enc_fix = 0.0; fixcnt = 0
    b1 = b2 = b3 = 2000
    reason = 0; i = 0
    enc_brake = 0.0; dist_brake = 0.0
    emit("D0", D0); logbuf(12, 1, t_start)
    while True:
        t = clock.time()
        drive_straight()
        d0 = rf0.distance(); d1 = rf1.distance()
        b1 = b2; b2 = b3; b3 = d1
        bmed = med3(b1, b2, b3)
        ml = m_left.angle(); mr = m_right.angle()
        enc = 0.5*(abs(ml) + abs(mr))
        if fixed:
            dist_est = A_fix - K_GAIN*(enc - enc_fix)
        else:
            dist_est = D0 - K_GAIN*enc
        # ranger-A position fix (2 consecutive below trip -> reject lone low spike)
        if not fixed:
            if d0 <= A_FIX_TRIP: fixcnt += 1
            else: fixcnt = 0
            if fixcnt >= 2:
                fixed = True; A_fix = d0; enc_fix = enc
                emit("afix_d", d0, t); emit("afix_enc", int(enc), t)
        if (i % LOG_EVERY) == 0:
            logbuf(2, d0, t); logbuf(3, d1, t)
            logbuf(4, int(hub.imu.heading()*10), t)
            logbuf(8, ml, t); logbuf(9, mr, t)
            logbuf(10, int(dist_est), t)
        i += 1
        if dist_est <= D_BRAKE: reason = 1; break     # dead-reckon (normal)
        if bmed <= B_STOP:      reason = 2; break     # independent B backstop
        if (t - t_start) >= HARD_TIME_MS: reason = 3; break
        if enc >= enc_cap:      reason = 4; break     # runaway failsafe
        wait(DT_MS)
    m_left.brake(); m_right.brake()
    enc_brake = 0.5*(abs(m_left.angle())+abs(m_right.angle()))
    dist_brake = dist_est
    logbuf(12, 2, clock.time())
    t_rest0 = clock.time()
    while (clock.time() - t_rest0) < SETTLE_MS:
        tt = clock.time()
        ml = m_left.angle(); mr = m_right.angle()
        enc = 0.5*(abs(ml)+abs(mr))
        if fixed: de = A_fix - K_GAIN*(enc - enc_fix)
        else:     de = D0 - K_GAIN*enc
        logbuf(2, rf0.distance(), tt)
        logbuf(3, rf1.distance(), tt)
        logbuf(8, ml, tt); logbuf(9, mr, tt)
        logbuf(5, int(hub.imu.acceleration(Axis.X)), tt)
        logbuf(10, int(de), tt)          # settle dist_est -> rest & coast
        wait(REST_DT_MS)
    emit("cycle", cycle)
    emit("stop_reason", reason)
    emit("afix_used", 1 if fixed else 0)
    emit("enc_brake", int(enc_brake))
    emit("dist_brake", int(dist_brake))
    return reason

# ============================ main ============================
try:
    emit("run_id", 3)                    # verification
    emit("phase", 0)
    try: hub.imu.reset_heading(0)
    except Exception: pass
    bA = rf0.distance(); bB = rf1.distance(); bE = rr.distance()
    emit("baseline_A", bA); emit("baseline_B", bB); emit("baseline_E", bE)
    ok = (750 <= bA <= 1300) and (750 <= bB <= 1300) and (abs(bA - bB) <= 250)
    if not ok:
        emit("abort_reason", 7); raise AbortRun()
    for c in range(N_CYCLES):
        if clock.time() > TIME_GUARD_MS:
            emit("time_guard", c); break
        square_up()
        d = rf0.distance()
        emit("pre_approach_d", d)
        if d < REPOS_TARGET - 50: reposition()
        approach_and_stop(c)
        dumpbuf()
        if c < N_CYCLES - 1: reposition()
except AbortRun:
    emit("aborted", 1)
except Exception:
    emit("run_error", 1)
finally:
    for m in motors_list:
        try: m.brake()
        except Exception: pass
    emit("run_done", 1)
    print('{"event": "end"}')
