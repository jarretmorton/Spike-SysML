# Run 2 — Max-speed calibration dash (safe 450 mm trigger).
# Auto-detects toward-wall direction, then sprints at full rated speed and brakes
# early. Records top speed, mm-per-wheel-degree, heading drift, and stopping distance.
# Findings: ~490 mm/s top speed, 0.489 mm/deg, brake ~67-74 mm, ultrasonic lags
# ~75 mm during motion, rover veers ~-14 deg unaided.

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

def emit(s, v):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n' % (clock.time(), s, v))

mC = Motor(Port.C); mD = Motor(Port.D)
usA = UltrasonicSensor(Port.A); usB = UltrasonicSensor(Port.B)

RUNCMD = 2000          # clamps to the motor's rated max -> maximum speed
TRIGGER = 450.0        # safe brake threshold (mm), min of the two forward sensors

mC.control.limits(acceleration=8000)
mD.control.limits(acceleration=8000)

def reads():
    a = usA.distance(); b = usB.distance()
    return a, b, (a if a < b else b)

dir = 1; triggered = 0; t_trig = -1
try:
    try: emit("max_speed_rated", mC.control.limits()[0])
    except Exception: emit("max_speed_rated", -1.0)

    mC.reset_angle(0); mD.reset_angle(0)
    a,b,m = reads(); emit("dist_A",a); emit("dist_B",b); emit("dist_min",m); emit("d0",m)
    d_pre = m

    # forward-direction auto-detect using the straight pair (C+, D-)
    mC.run(200); mD.run(-200); wait(300); mC.brake(); mD.brake(); wait(300)
    a,b,m = reads(); emit("dir_test_dist", m)
    if m < d_pre - 8: dir = 1
    elif m > d_pre + 8: dir = -1
    else: dir = 1
    emit("dir_chosen", float(dir))

    mC.reset_angle(0); mD.reset_angle(0); wait(150)
    a,b,m = reads(); emit("d_start_main", m)

    def fdeg(): return dir*0.5*(mC.angle() - mD.angle())
    def fspd(): return dir*0.5*(mC.speed() - mD.speed())

    # MAX-SPEED DASH
    mC.run(dir*RUNCMD); mD.run(-dir*RUNCMD)
    loopn = 0
    while True:
        t = clock.time()
        a = usA.distance(); b = usB.distance(); m = a if a < b else b
        if (loopn % 3) == 0:
            emit("dist_min",m); emit("dist_A",a); emit("dist_B",b)
            emit("heading",hub.imu.heading()); emit("fdeg",fdeg()); emit("fspd",fspd())
        if (not triggered) and (m <= TRIGGER):
            triggered = 1; t_trig = t
            emit("brake_t",float(t)); emit("brake_dist",m); emit("brake_fdeg",fdeg())
            mC.brake(); mD.brake()
        if triggered and (t - t_trig) > 1200: break
        if t > 9000:
            mC.brake(); mD.brake(); break
        loopn += 1; wait(4)

    wait(300)
    for i in range(6):
        a,b,m = reads(); emit("dist_min",m); emit("dist_A",a); emit("dist_B",b); wait(25)
    a,b,m = reads()
    emit("d_final_min",m); emit("d_final_A",a); emit("d_final_B",b)
    emit("fdeg_final",fdeg()); emit("heading_final",hub.imu.heading())
finally:
    mC.brake(); mD.brake()
    stdout.write('{"event":"end"}\n')
