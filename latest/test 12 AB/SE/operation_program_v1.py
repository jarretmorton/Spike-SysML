"""
OPERATION PROGRAMME — Rover Wall-Stop System
Version: 1.0   Status: LOCKED at Gate C   Date: 2026-07-21

DO NOT MODIFY — Run 5 times, unchanged, with hub power-cycled between runs.

Committed constants (Verification Report v1.0):
  MAX_CMD    = 929 deg/s  — confirmed ceiling (Verif-Run-1 speed plateau)
  TRIGGER_MM = 100 mm     — USS-A reading at brake; worst-case gap ≥ 12 mm
  HEADING_KP = 5          — heading P-gain (deg/s per degree)
  LOOP_MS    = 50 ms      — matches calibrated tResponse
  SETTLE_MS  = 3000 ms    — settle after braking

Predicted average gap: ~26 mm.  Worst-case gap: 12 mm.
Onboard gap estimate per run: final_f1_mm − 21 (dCombo = 21 mm, T1-bound).

Motor convention (calibrated Cal-Run-1/2):
  Port C (motor_right): run(-speed) = right wheel forward
  Port D (motor_left):  run(+speed) = left wheel forward
  Heading correction: corr = KP * heading; right runs at -MAX+corr, left at +MAX+corr

Sensor convention:
  Port A (USS-F1): forward primary, trigger sensor
  Port B (USS-F2): forward secondary, logged for post-hoc reference only (AR-01)
"""

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

# === LOCKED CONSTANTS =====================================================
MAX_CMD    = 929    # deg/s — confirmed motor ceiling
TRIGGER_MM = 100    # mm   — USS-A threshold for brake command
HEADING_KP = 5      # deg/s correction per degree of heading error
LOOP_MS    = 50     # ms
SETTLE_MS  = 3000   # ms
D_COMBO    = 21.0   # mm  — T1-bound combined sensor offset (for onboard gap estimate)
# =========================================================================

motor_right = Motor(Port.C)
motor_left  = Motor(Port.D)
uss_f1      = UltrasonicSensor(Port.A)
uss_f2      = UltrasonicSensor(Port.B)

buf        = []   # (timestamp_ms, fwd1_mm, fwd2_mm, heading_deg)
trigger_t  = -1
trigger_f1 = -1.0

try:
    motor_right.run(-MAX_CMD)
    motor_left.run( MAX_CMD)

    # Hot control loop — buffer only, no I/O on hot path
    while True:
        t  = clock.time()
        f1 = uss_f1.distance()
        f2 = uss_f2.distance()
        h  = hub.imu.heading()

        # Heading P-correction (full effect because commands are at actual ceiling)
        corr = HEADING_KP * h
        motor_right.run(-MAX_CMD + corr)
        motor_left.run( MAX_CMD + corr)

        buf.append((t,
                    float(f1) if f1 is not None else -1.0,
                    float(f2) if f2 is not None else -1.0,
                    float(h)))

        if f1 is not None and f1 <= TRIGGER_MM:
            trigger_t  = t
            trigger_f1 = float(f1)
            motor_right.brake()
            motor_left.brake()
            break

        wait(LOOP_MS)

    # Settle
    wait(SETTLE_MS)
    ff1 = uss_f1.distance()
    ff2 = uss_f2.distance()
    fh  = hub.imu.heading()

    # Onboard gap estimate: final_f1 - D_COMBO
    gap_estimate = (float(ff1) - D_COMBO) if ff1 is not None else -1.0

    # Dump buffer with original hub-clock timestamps
    for (t, f1, f2, h) in buf:
        stdout.write('{"timestamp_ms":%d,"sensor":"fwd1","value":%f}\n'    % (t, f1))
        stdout.write('{"timestamp_ms":%d,"sensor":"fwd2","value":%f}\n'    % (t, f2))
        stdout.write('{"timestamp_ms":%d,"sensor":"heading","value":%f}\n' % (t, h))

    # Key scalars
    stdout.write('{"timestamp_ms":%d,"sensor":"trigger_f1_mm","value":%f}\n'
                 % (trigger_t, trigger_f1))
    t_now = clock.time()
    stdout.write('{"timestamp_ms":%d,"sensor":"final_f1_mm","value":%f}\n'
                 % (t_now, float(ff1) if ff1 is not None else -1.0))
    stdout.write('{"timestamp_ms":%d,"sensor":"final_f2_mm","value":%f}\n'
                 % (t_now, float(ff2) if ff2 is not None else -1.0))
    stdout.write('{"timestamp_ms":%d,"sensor":"final_heading","value":%f}\n'
                 % (t_now, float(fh)))
    stdout.write('{"timestamp_ms":%d,"sensor":"gap_estimate_mm","value":%f}\n'
                 % (t_now, gap_estimate))

except Exception:
    pass
finally:
    try: motor_right.brake()
    except Exception: pass
    try: motor_left.brake()
    except Exception: pass
    stdout.write('{"event":"end"}\n')
