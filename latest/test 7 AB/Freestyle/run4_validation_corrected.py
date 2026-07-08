# Run 4 — VALIDATION (corrected re-run of the aborted run 3)
# Fixes: throttle the RAM buffer to ~15 ms, emit scalars BEFORE the dump, add an
# odometry anti-crash failsafe, shorten the approach cap. This run confirmed the true
# ~50-55 mm coast and revealed the intermittent ~145 ms sensor freeze, which motivated
# the odometry-bridged freeze compensation used in run5 and the locked program.
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

def emit(s, v):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n' % (clock.time(), s, v))

def emit_at(t, s, v):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n' % (t, s, v))

mC = Motor(Port.C)
mD = Motor(Port.D)
sA = UltrasonicSensor(Port.A)
sB = UltrasonicSensor(Port.B)

def drive(sp):
    mC.run(-sp); mD.run(sp)

def stop():
    mC.brake(); mD.brake()

THR_B = 270
AB_OFF = 133
MMPD = 0.42     # mm per motor-degree (Run 2 Part B)
FAIL_B = 220    # failsafe brake position (sensor mm), below THR so sensor wins normally

bt = []; bb = []; ba = []; bh = []
btrig = 0.0; atrig = 0.0; ttrig = 0
trig_src = 0

try:
    # ---- baseline: measure start distance ----
    bs = []
    for i in range(4):
        b = sB.distance(); a = sA.distance()
        emit("B_dist", b); emit("A_dist", a); emit("heading", hub.imu.heading())
        bs.append(b); wait(30)
    bs.sort()
    B_start = bs[len(bs) // 2]
    fail_prog = (B_start - FAIL_B) / MMPD
    emit("B_start", B_start); emit("fail_prog", fail_prog)

    # ---- max-speed approach (throttled buffer, trigger every iteration) ----
    aC0 = mC.angle(); aD0 = mD.angle()
    drive(1000)
    t0 = clock.time(); last_ap = -100
    while clock.time() - t0 < 3500:
        b = sB.distance(); a = sA.distance(); t = clock.time()
        prog = (abs(mC.angle() - aC0) + abs(mD.angle() - aD0)) / 2.0
        if b <= THR_B or a <= THR_B + AB_OFF:
            btrig = b; atrig = a; ttrig = t; trig_src = 1
            if len(bt) < 320:
                bt.append(t); bb.append(b); ba.append(a); bh.append(hub.imu.heading())
            break
        if prog >= fail_prog:
            btrig = b; atrig = a; ttrig = t; trig_src = 2
            break
        if t - last_ap >= 15 and len(bt) < 320:
            last_ap = t
            bt.append(t); bb.append(b); ba.append(a); bh.append(hub.imu.heading())
    stop()

    # ---- settle ----
    tb = clock.time()
    while clock.time() - tb < 1200:
        t = clock.time()
        if len(bt) < 420:
            bt.append(t); bb.append(sB.distance()); ba.append(sA.distance()); bh.append(hub.imu.heading())
        wait(40)
    brest = sB.distance(); arest = sA.distance()

    # ---- SCALARS FIRST (survive any dump truncation) ----
    emit("B_trig", btrig); emit("A_trig", atrig); emit("t_trig", ttrig)
    emit("trig_src", trig_src)
    emit("B_rest", brest); emit("A_rest", arest)
    emit("coast_B", btrig - brest)
    emit("loop_n", len(bt))

    # ---- dump throttled buffer (B + heading) ----
    n = len(bt)
    for i in range(n):
        emit_at(bt[i], "B_dist", bb[i])
        emit_at(bt[i], "heading", bh[i])
finally:
    stop()
    stdout.write('{"event":"end"}\n')
