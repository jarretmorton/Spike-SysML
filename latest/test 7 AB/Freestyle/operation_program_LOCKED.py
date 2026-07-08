# OPERATION PROGRAM — LOCKED (flashed unchanged for all 5 scored runs)
# Full 1000 deg/s at the wall; brake when the odometry-bridged distance estimate <= 110 mm;
# hard brake both motors (~50 mm coast); odometry anti-crash failsafe backstop.
# Result across 5 runs: 5/5 no contact; measured gaps 153/184/176/179/185 mm.
# Note: the forward ultrasonic reads ~125 mm short of true distance and floors at 40 mm,
# so ~165 mm bumper gap is the tightest a sensor-based stop can safely reach here.
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

THR = 110
MMPD_BR = 0.46
FAIL_B = 70
MMPD_FL = 0.42

bt = []; bb = []; bh = []; be = []
btrig = 0.0; atrig = 0.0; ttrig = 0; estrig = 0.0; trig_src = 0

try:
    bs = []
    for i in range(4):
        b = sB.distance(); a = sA.distance()
        emit("B_dist", b); emit("A_dist", a); emit("heading", hub.imu.heading())
        bs.append(b); wait(30)
    bs.sort()
    B_start = bs[len(bs) // 2]
    fail_prog = (B_start - FAIL_B) / MMPD_FL
    emit("B_start", B_start); emit("fail_prog", fail_prog)

    last_fresh = B_start; prog_fresh = 0.0
    aC0 = mC.angle(); aD0 = mD.angle()
    drive(1000)
    t0 = clock.time(); last_ap = -100
    while clock.time() - t0 < 3500:
        b = sB.distance(); a = sA.distance(); t = clock.time()
        prog = (abs(mC.angle() - aC0) + abs(mD.angle() - aD0)) / 2.0
        if b < last_fresh - 3:
            last_fresh = b; prog_fresh = prog
        est = last_fresh - (prog - prog_fresh) * MMPD_BR
        if est <= THR:
            btrig = b; atrig = a; ttrig = t; estrig = est; trig_src = 1
            if len(bt) < 200:
                bt.append(t); bb.append(b); bh.append(hub.imu.heading()); be.append(est)
            break
        if prog >= fail_prog:
            btrig = b; atrig = a; ttrig = t; estrig = est; trig_src = 2
            break
        if t - last_ap >= 30 and len(bt) < 200:
            last_ap = t
            bt.append(t); bb.append(b); bh.append(hub.imu.heading()); be.append(est)
    stop()

    tb = clock.time()
    while clock.time() - tb < 1200:
        t = clock.time()
        if len(bt) < 260:
            bt.append(t); bb.append(sB.distance()); bh.append(hub.imu.heading()); be.append(-1.0)
        wait(40)
    brest = sB.distance(); arest = sA.distance()

    emit("B_trig", btrig); emit("A_trig", atrig); emit("est_trig", estrig)
    emit("t_trig", ttrig); emit("trig_src", trig_src)
    emit("B_rest", brest); emit("A_rest", arest)
    emit("coast_B", btrig - brest); emit("coast_est", estrig - brest)
    emit("loop_n", len(bt))

    n = len(bt)
    for i in range(n):
        emit_at(bt[i], "B_dist", bb[i]); emit_at(bt[i], "est", be[i]); emit_at(bt[i], "heading", bh[i])
finally:
    stop()
    stdout.write('{"event":"end"}\n')
