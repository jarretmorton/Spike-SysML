# Run 3 — VALIDATION ATTEMPT (ABORTED — kept for the record)
# First buffered-loop design. BUG: because UltrasonicSensor.distance() returns a cached
# value instantly, the loop spun at ~1 ms and the un-throttled RAM buffer accumulated
# thousands of samples; dumping them overran the timeout before any scalar transmitted,
# so no usable stopping data was captured. Fixed in run4 (throttle + scalars-first + failsafe).
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
bt = []; bb = []; ba = []; bh = []
btrig = 0.0; atrig = 0.0; ttrig = 0

try:
    # baseline (direct emit, timing not critical)
    for i in range(3):
        emit("B_dist", sB.distance()); emit("A_dist", sA.distance())
        emit("heading", hub.imu.heading()); wait(30)

    # ---- max-speed approach, buffered tight loop (no transmit in loop) ----
    drive(1000)
    t0 = clock.time()
    while clock.time() - t0 < 5000:
        b = sB.distance(); a = sA.distance(); h = hub.imu.heading(); t = clock.time()
        bt.append(t); bb.append(b); ba.append(a); bh.append(h)
        if b <= THR_B or a <= THR_B + AB_OFF:
            btrig = b; atrig = a; ttrig = t
            break
    stop()

    # ---- settle, buffered ----
    tb = clock.time()
    while clock.time() - tb < 1400:
        t = clock.time()
        bt.append(t); bb.append(sB.distance()); ba.append(sA.distance()); bh.append(hub.imu.heading())
        wait(40)
    brest = sB.distance(); arest = sA.distance()

    # ---- dump buffer with true timestamps (this is what overran the timeout) ----
    n = len(bt)
    for i in range(n):
        emit_at(bt[i], "B_dist", bb[i])
        emit_at(bt[i], "A_dist", ba[i])
        emit_at(bt[i], "heading", bh[i])

    # ---- scalars (never reached before timeout) ----
    emit("B_trig", btrig); emit("A_trig", atrig); emit("t_trig", ttrig)
    emit("B_rest", brest); emit("A_rest", arest)
    emit("coast_B", btrig - brest)
    emit("loop_n", n)
finally:
    stop()
    stdout.write('{"event":"end"}\n')
