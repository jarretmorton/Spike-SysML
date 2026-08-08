"""
CHARACTERIZATION RUN 2 — Braking characterization attempt
Drives at max speed (C=-2000, D=+2000) with heading correction applied to C.
NOTE: Correction sign was wrong for this drivetrain — heading ran away.
Result: heading reached -1946° (5+ rotations). No valid braking data collected.
Lesson: same-sign motor commands produce pivot, not translation; correction was on wrong motor.
"""
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

def emit(sensor, value):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'
                 % (clock.time(), sensor, value))

mc = Motor(Port.C)
md = Motor(Port.D)
sa = UltrasonicSensor(Port.A)
sb = UltrasonicSensor(Port.B)

BASE = -2000   # toward wall (both negative, based on Run 1 findings)
KP = 5.0       # heading correction gain (WRONG SIGN — worsened spin)
BRAKE_AT = 400
EMERGENCY = 80

def fwd():
    try:
        a = sa.distance()
        b = sb.distance()
        vals = [v for v in [a, b] if v is not None]
        return min(vals) if vals else 2000
    except:
        return 2000

try:
    d0 = fwd()
    h0 = hub.imu.heading()
    emit('d0', float(d0))
    emit('h0', float(h0))
    wait(300)

    t0 = clock.time()
    while True:
        d = fwd()
        h = hub.imu.heading()
        emit('dist', float(d))
        emit('hdg', float(h))

        if d <= EMERGENCY:
            emit('stop_cause', 0.0)
            break
        if d <= BRAKE_AT:
            emit('stop_cause', 1.0)
            break
        if clock.time() - t0 > 5000:
            emit('stop_cause', 2.0)
            break

        corr = h * KP
        mc.run(BASE + corr)   # C-motor correction (wrong motor)
        md.run(BASE - corr)
        wait(20)

    mc.hold()
    md.hold()
    wait(1500)

    df = fwd()
    hf = hub.imu.heading()
    emit('final_dist', float(df))
    emit('final_hdg', float(hf))
    emit('overshoot', float(BRAKE_AT - df))

finally:
    mc.brake()
    md.brake()
    stdout.write('{"event":"end"}\n')
