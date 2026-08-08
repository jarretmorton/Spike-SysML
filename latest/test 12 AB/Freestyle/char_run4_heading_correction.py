"""
CHARACTERIZATION RUN 4 — Heading correction calibration
Drives C-, D+ (toward wall) with C-motor heading correction (KP=5, BASE_C=-1000).
Result: heading drifted to -19.6° (partially corrected vs -13.8°/s baseline without correction).
Measured actual overshoot: 76mm (angle-corrected). Correction factor: 0.077 deg/s per deg/s differential.
Note: KP=5 was too weak; correction later moved to D-motor for stability.
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

KP = 5
BASE_C = -1000
BASE_D = 1000
BRAKE_AT = 300
EMERGENCY = 70

def fwd():
    try:
        a = sa.distance()
        b = sb.distance()
        vals = [v for v in [a, b] if v is not None]
        return min(vals) if vals else 2000
    except:
        return 2000

try:
    emit('d0', float(fwd()))
    emit('h0', float(hub.imu.heading()))
    wait(200)

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
        mc.run(BASE_C - corr)   # C-motor correction (partially effective)
        md.run(BASE_D)
        wait(20)

    mc.hold()
    md.hold()
    wait(2000)

    df = fwd()
    hf = hub.imu.heading()
    emit('final_dist', float(df))
    emit('final_hdg', float(hf))
    emit('overshoot', float(BRAKE_AT - df))

finally:
    mc.brake()
    md.brake()
    stdout.write('{"event":"end"}\n')
