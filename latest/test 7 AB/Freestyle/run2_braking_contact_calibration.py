# Run 2 — BRAKING + CONTACT CALIBRATION (characterization)
# Part A: accelerate to max, hard-brake when B<=400, measure the coast distance and
#         confirm top speed + straightness.
# Part B: creep forward into the wall to characterize contact (this is where the
#         wheel-slip vs stall behavior and the 40 mm sensor floor were discovered).
# NOTE: the Part-A "175 mm coast" from this run was later found to be a stale-reading
# artifact of BLE backpressure; the true coast (~50 mm) was confirmed with fresh-loop runs.
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

def emit(s, v):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n' % (clock.time(), s, v))

mC = Motor(Port.C)
mD = Motor(Port.D)
sA = UltrasonicSensor(Port.A)
sB = UltrasonicSensor(Port.B)

def drive(sp):
    mC.run(-sp); mD.run(sp)

def stop():
    mC.brake(); mD.brake()

TRIG = 400
AB_OFF = 133
btrig = 0.0
atrig = 0.0

try:
    # baseline
    for i in range(4):
        emit("B_dist", sB.distance()); emit("A_dist", sA.distance())
        emit("heading", hub.imu.heading()); wait(30)

    # ---- PART A: max-speed approach + hard brake ----
    drive(1000)
    t0 = clock.time()
    while clock.time() - t0 < 6000:
        b = sB.distance(); a = sA.distance()
        emit("B_dist", b); emit("A_dist", a)
        emit("spd", mC.speed()); emit("heading", hub.imu.heading())
        if b <= TRIG or a <= TRIG + AB_OFF:
            btrig = b; atrig = a
            break
    stop()
    emit("brake_evt", 1)
    emit("B_trig", btrig); emit("A_trig", atrig)
    tb = clock.time()
    while clock.time() - tb < 1300:
        emit("B_dist", sB.distance()); emit("A_dist", sA.distance())
        emit("heading", hub.imu.heading()); wait(40)
    emit("B_rest", sB.distance()); emit("A_rest", sA.distance())
    wait(400)

    # ---- PART B: adaptive approach to contact ----
    aC0 = mC.angle(); aD0 = mD.angle()
    prev_prog = 0.0; prev_t = clock.time(); tB = clock.time()
    contact = 0
    while clock.time() - tB < 9000:
        b = sB.distance(); a = sA.distance()
        prog = (abs(mC.angle() - aC0) + abs(mD.angle() - aD0)) / 2.0
        emit("B_dist", b); emit("A_dist", a); emit("prog", prog)
        if b > 160:
            sp = 300
        elif b > 80:
            sp = 140
        else:
            sp = 80
        mC.run(-sp); mD.run(sp)
        if prog - prev_prog > 5:
            prev_prog = prog; prev_t = clock.time()
        if clock.time() - prev_t > 500 and clock.time() - tB > 800:
            contact = 1
            break
        wait(20)
    stop()
    emit("B_contact", sB.distance()); emit("A_contact", sA.distance())
    emit("prog_contact", (abs(mC.angle() - aC0) + abs(mD.angle() - aD0)) / 2.0)
    emit("contact_flag", contact)
    wait(300)
    # back off ~60 mm (reverse: C+, D-)
    mC.run(200); mD.run(-200); wait(700); stop()
    emit("B_final", sB.distance()); emit("A_final", sA.distance())
finally:
    stop()
    stdout.write('{"event":"end"}\n')
