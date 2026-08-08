"""
OPERATION PROGRAM (LOCKED) — Wall approach at maximum speed
Used for all 5 official operation runs. Results: 5/5 no contact, 113–129mm measured gap.

HARDWARE:
  Port C: left drive motor  (C- = toward wall)
  Port D: right drive motor (D+ = toward wall)
  Port A: forward ultrasonic sensor (primary)
  Port B: forward ultrasonic sensor (secondary)

CONTROL STRATEGY:
  - C held constant at max forward (-1000 deg/s)
  - D varied by heading feedback: md.run(clamp(1000 + heading × 30, 0, 1050))
  - When heading drifts left (negative), D reduces → less rightward pull → heading corrects
  - Clamp [0, 1050] prevents D going backward, eliminating runaway instability
  - 500ms IMU warm-up before drive loop starts
  - Brake: hold() both motors when min(A, B) ≤ 130mm
  - Emergency brake at 50mm

RESULTS:
  Run | final_dist | final_hdg | gap_est | Measured gap
  1   | 40mm       | -2.6°     | 40mm    | 129mm
  2   | 40mm       | -3.4°     | 40mm    | 128mm
  3   | 40mm       | -3.1°     | 40mm    | 113mm
  4   | 40mm       | -4.8°     | 40mm    | 127mm
  5   | 40mm       | -3.4°     | 40mm    | 124mm

  Systematic offset ~84mm: sensor face protrudes ~84mm ahead of bumper.
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

BASE_C = -1000   # left motor constant at max toward-wall speed
KP = 30          # heading correction gain applied to D (right motor)
BRAKE_AT = 130   # mm — sensor threshold to trigger hold() brake
EMERGENCY = 50   # mm — safety floor (emergency brake)

_last_d = 1000

def fwd():
    """Return min of A and B sensor readings; hold last valid on dropout."""
    global _last_d
    try:
        a = sa.distance()
        b = sb.distance()
        vals = [v for v in [a, b] if v is not None and v > 0]
        if vals:
            _last_d = min(vals)
    except:
        pass
    return _last_d

try:
    emit('d0', float(fwd()))
    emit('h0', float(hub.imu.heading()))
    wait(500)   # IMU warm-up to prevent spurious initial heading readings

    t0 = clock.time()
    while True:
        d = fwd()
        h = hub.imu.heading()
        emit('dist', float(d))
        emit('hdg', float(h))

        if d <= EMERGENCY:
            emit('stop_cause', 0.0)   # emergency
            break
        if d <= BRAKE_AT:
            emit('stop_cause', 1.0)   # normal brake
            break
        if clock.time() - t0 > 6000:
            emit('stop_cause', 2.0)   # timeout (safety)
            break

        # D-motor heading correction: clamp to [0, 1050] — never backward
        raw_d = 1000 + h * KP
        d_speed = max(0, min(1050, raw_d))
        mc.run(BASE_C)
        md.run(d_speed)
        wait(20)

    # Hard stop: hold() provides active braking against residual momentum
    mc.hold()
    md.hold()
    wait(1500)   # settle time

    df = fwd()
    hf = hub.imu.heading()
    emit('final_dist', float(df))
    emit('final_hdg', float(hf))
    # Onboard gap estimate: project sensor reading onto forward axis
    hf_rad = hf * 3.14159265 / 180.0
    cos_hf = 1.0 - hf_rad * hf_rad / 2.0   # cos approximation (no math module needed)
    emit('gap_est', float(df * cos_hf))

finally:
    mc.brake()
    md.brake()
    stdout.write('{"event":"end"}\n')
