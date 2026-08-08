"""
CHARACTERIZATION RUN 3 — Direction identification + braking test
Phase 1: tests C=+700, D=-700 for 400ms to determine which motor sign goes toward wall.
Phase 2: drives at max speed in the confirmed toward-wall direction, brakes at 300mm.
Result: confirmed C-, D+ = toward wall; heading drifted -29° at max speed (no correction).
Overshoot at 300mm threshold: ~76mm actual (angle-corrected).
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

BRAKE_AT = 300
EMERGENCY = 70
MAX_HDG = 45
TEST_SPEED = 700
MAX_SPEED = 2000

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
    emit('d0', float(d0))
    emit('h0', float(hub.imu.heading()))
    wait(200)

    # Phase 1: Direction test (C=+, D=-)
    mc.run(TEST_SPEED)
    md.run(-TEST_SPEED)
    for _ in range(20):  # 400ms
        emit('dist', float(fwd()))
        emit('hdg', float(hub.imu.heading()))
        wait(20)
    mc.brake()
    md.brake()
    wait(400)

    d_test = fwd()
    h_test = hub.imu.heading()
    emit('d_test', float(d_test))
    emit('h_test', float(h_test))

    # Determine forward direction from result
    if d_test < d0:
        fwd_mc, fwd_md = MAX_SPEED, -MAX_SPEED   # C+, D- toward wall
        emit('fwd_dir', 1.0)
    else:
        fwd_mc, fwd_md = -MAX_SPEED, MAX_SPEED   # C-, D+ toward wall
        emit('fwd_dir', -1.0)

    wait(300)

    # Phase 2: Full speed approach + brake
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
        if abs(h) > MAX_HDG:
            emit('stop_cause', 3.0)
            break
        if clock.time() - t0 > 5000:
            emit('stop_cause', 2.0)
            break

        mc.run(fwd_mc)
        md.run(fwd_md)
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
