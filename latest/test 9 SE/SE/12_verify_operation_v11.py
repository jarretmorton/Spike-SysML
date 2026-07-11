# =====================================================================
# VERIFICATION v1.1 / operation-candidate  (Pybricks / SPIKE Prime)
# Calibrated: k=0.516 mm/deg, d_stop=15 mm, c_offset=31 mm.
#   true_gap = dist_est_rest - (d_stop + c_offset) = dist_est_rest - 46
# Target true_gap = 35 mm  ->  D_BRAKE = 81 mm  (predicted rest_A=66).
# Dead-reckon (A-fix@450 -> encoder) is PRIMARY. A layered ranger-B
# close-confirm net is armed only below dist_est=65 so it cannot
# pre-empt the 81 mm target. read_D0 rejects A no-echo (2000) spikes.
# Settle logs encoders; ranger B logged all the way in (characterize).
# =====================================================================
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port, Axis
from pybricks.tools import wait, StopWatch

clock = StopWatch()
hub = PrimeHub()

K_GAIN           = 0.516
C_OFFSET         = 31         # (doc) A/encoder frame - true gap
D_STOP           = 15         # (doc) measured coast
A_FIX_TRIP       = 450
D_BRAKE          = 81         # target true_gap 35 mm
B_ARM            = 65         # arm B net only below this dist_est (< D_BRAKE)
B_EMERG          = 40         # B net trips if median B <= this while armed
DT_MS            = 12
LOG_EVERY        = 3
BASE_CMD         = 1000
KP_HEAD          = 20
TRIM_CAP         = 300
SPIN             = 250
HARD_TIME_MS     = 2600
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
_bt=[0]*BUF_N; _bc=[0]*BUF_N; _bv=[0]*BUF_N; _bi=0
CODE={2:"d_f0",3:"d_f1",4:"heading_dx10",5:"acc_x",8:"ml_deg",9:"mr_deg",10:"dist_est",12:"phase"}
def logbuf(code, value, t):
    global _bi
    if _bi < BUF_N:
        _bt[_bi]=t; _bc[_bi]=code; _bv[_bi]=value; _bi+=1
def dumpbuf():
    global _bi
    for k in range(_bi):
        emit(CODE.get(_bc[k],"c%d"%_bc[k]), _bv[k], _bt[k])
    _bi=0

class AbortRun(Exception): pass

m_left  = Motor(Port.C); m_right = Motor(Port.D)
motors_list=[m_left,m_right]
rf0 = UltrasonicSensor(Port.A); rf1 = UltrasonicSensor(Port.B); rr = UltrasonicSensor(Port.E)

def clampc(v):
    if v > BASE_CMD+TRIM_CAP: return BASE_CMD+TRIM_CAP
    if v < BASE_CMD-TRIM_CAP: return BASE_CMD-TRIM_CAP
    return v
def drive_straight():
    h=hub.imu.heading(); adj=KP_HEAD*h
    if adj>TRIM_CAP: adj=TRIM_CAP
    elif adj<-TRIM_CAP: adj=-TRIM_CAP
    m_left.run(SL*clampc(BASE_CMD-adj)); m_right.run(SR*clampc(BASE_CMD+adj))
def square_up():
    t0=clock.time()
    while (clock.time()-t0)<1500:
        h=hub.imu.heading()
        if -2<h<2: break
        d=1 if h>0 else -1
        m_left.run(d*SPIN); m_right.run(d*SPIN); wait(20)
    m_left.brake(); m_right.brake(); wait(250)
def reposition():
    t0=clock.time()
    m_left.run(-SL*REV_CMD); m_right.run(-SR*REV_CMD)
    while rf0.distance()<REPOS_TARGET and (clock.time()-t0)<REPOS_TIMEOUT_MS: wait(40)
    m_left.brake(); m_right.brake(); wait(300)
def med3(a,b,c): return sorted((a,b,c))[1]
def read_D0():
    vals=[]; tries=0
    while len(vals)<3 and tries<6:
        d=rf0.distance()
        if d<1500: vals.append(d)      # reject A no-echo (2000) spikes
        tries+=1; wait(15)
    if not vals: return 1000
    return sorted(vals)[len(vals)//2]

def approach_and_stop(cycle):
    m_left.reset_angle(0); m_right.reset_angle(0)
    D0=read_D0(); enc_cap=(D0-20)/K_GAIN
    t_start=clock.time()
    fixed=False; A_fix=0.0; enc_fix=0.0; fixcnt=0
    b1=b2=b3=2000; reason=0; i=0
    emit("D0", D0); logbuf(12,1,t_start)
    while True:
        t=clock.time(); drive_straight()
        d0=rf0.distance(); d1=rf1.distance()
        b1=b2; b2=b3; b3=d1; bmed=med3(b1,b2,b3)
        ml=m_left.angle(); mr=m_right.angle(); enc=0.5*(abs(ml)+abs(mr))
        if fixed: dist_est=A_fix-K_GAIN*(enc-enc_fix)
        else:     dist_est=D0-K_GAIN*enc
        if not fixed:
            if d0<=A_FIX_TRIP: fixcnt+=1
            else: fixcnt=0
            if fixcnt>=2:
                fixed=True; A_fix=d0; enc_fix=enc
                emit("afix_d",d0,t); emit("afix_enc",int(enc),t)
        if (i%LOG_EVERY)==0:
            logbuf(2,d0,t); logbuf(3,d1,t)
            logbuf(4,int(hub.imu.heading()*10),t)
            logbuf(8,ml,t); logbuf(9,mr,t); logbuf(10,int(dist_est),t)
        i+=1
        if dist_est<=D_BRAKE: reason=1; break                         # dead-reckon (primary)
        if dist_est<=B_ARM and bmed<=B_EMERG: reason=2; break         # close-confirm net
        if (t-t_start)>=HARD_TIME_MS: reason=3; break
        if enc>=enc_cap: reason=4; break
        wait(DT_MS)
    m_left.brake(); m_right.brake()
    enc_brake=0.5*(abs(m_left.angle())+abs(m_right.angle()))
    dist_brake=dist_est
    logbuf(12,2,clock.time())
    t0=clock.time()
    while (clock.time()-t0)<SETTLE_MS:
        tt=clock.time()
        ml=m_left.angle(); mr=m_right.angle(); enc=0.5*(abs(ml)+abs(mr))
        de=(A_fix-K_GAIN*(enc-enc_fix)) if fixed else (D0-K_GAIN*enc)
        logbuf(2,rf0.distance(),tt); logbuf(3,rf1.distance(),tt)
        logbuf(8,ml,tt); logbuf(9,mr,tt)
        logbuf(5,int(hub.imu.acceleration(Axis.X)),tt); logbuf(10,int(de),tt)
        wait(REST_DT_MS)
    emit("cycle",cycle); emit("stop_reason",reason)
    emit("afix_used",1 if fixed else 0)
    emit("enc_brake",int(enc_brake)); emit("dist_brake",int(dist_brake))
    return reason

try:
    emit("run_id",4); emit("phase",0)
    try: hub.imu.reset_heading(0)
    except Exception: pass
    bA=rf0.distance(); bB=rf1.distance(); bE=rr.distance()
    emit("baseline_A",bA); emit("baseline_B",bB); emit("baseline_E",bE)
    ok=(750<=bA<=1300) and (750<=bB<=1300) and (abs(bA-bB)<=250)
    if not ok:
        emit("abort_reason",7); raise AbortRun()
    for c in range(N_CYCLES):
        if clock.time()>TIME_GUARD_MS:
            emit("time_guard",c); break
        square_up()
        d=rf0.distance(); emit("pre_approach_d",d)
        if d<REPOS_TARGET-50: reposition()
        approach_and_stop(c)
        dumpbuf()
        if c<N_CYCLES-1: reposition()
except AbortRun:
    emit("aborted",1)
except Exception:
    emit("run_error",1)
finally:
    for m in motors_list:
        try: m.brake()
        except Exception: pass
    emit("run_done",1); print('{"event": "end"}')
