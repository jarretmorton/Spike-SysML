# spike_prime_direct/hub_program_example.py
#
# Runs ON the SPIKE Prime hub under Pybricks firmware. This is the shape of
# program the draft agent is expected to produce — a self-contained
# MicroPython script that exercises one or more requirements and emits
# telemetry in the canonical wire format.
#
# Wire contract (see docs/wire_contract.md):
#   {"timestamp_ms": <int, hub clock>, "sensor": "<name>", "value": <number>}
# Plus a flush sentinel at the end of the run:
#   {"event": "end"}
#
# The JSON line is built with % formatting on purpose — Pybricks firmware is
# size-constrained and a json module is not guaranteed to be present. The
# host side parses with full CPython json.loads.

# Pybricks device classes. These resolve only on the hub firmware; importing
# them on a desktop CPython will fail, which is why this script is run on-hub.
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout                     # MicroPython's sys; stdout is the BLE pipe

# --- physical configuration (edit to match your build) ---
# Each device is bound to the physical port it's plugged into. The names below
# describe the robot's chassis layout, not the Pybricks defaults.
hub   = PrimeHub()
left_wheel  = Motor(Port.C)
right_wheel = Motor(Port.D)
right_eye = UltrasonicSensor(Port.B)       # forward-right distance sensor
left_eye = UltrasonicSensor(Port.A)        # forward-left distance sensor
back_eye = UltrasonicSensor(Port.E)        # rear distance sensor (declared, unused here)
edge_sensor = ColorSensor(Port.F)          # downward sensor; reflection() finds table edges/lines
WHEEL_CIRC_M = 0.055 * 3.1416              # wheel circumference in metres (55 mm diameter)

clock = StopWatch()                        # hub-local millisecond clock, started at import


def emit(sensor, value):
    """One canonical telemetry line. Hub clock is the only timestamp
    that's valid for time-bound requirements — BLE arrival times are
    buffered and chunked, so the host can't reconstruct them."""
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'
                 % (clock.time(), sensor, value))


# --- commands ---
# Start both wheels spinning. run() takes a speed in degrees/second and is
# non-blocking, so execution falls straight through to the loop below. The
# opposite signs reflect the motors being mounted as mirror images.
left_wheel.run(-80)                              # 80 deg/s forward (signs depend on chassis)
right_wheel.run(80)

# --- measurement loop ---
# Runs forever, sampling sensors and emitting telemetry. The try/finally
# guarantees the motors stop and an end sentinel is sent even if the program
# is interrupted (e.g. the user hits stop on the hub).
try:
    motors_stopped = False                  # latch so we only issue stop() once
    while True:
        # Combine the two wheel speeds (deg/s) into a ground speed. The wheels
        # are mounted mirror-image and driven with opposite signs, so the LEFT
        # reading is negated into the chassis-forward convention before
        # averaging -- summing the raw signed values cancels them to ~0, which
        # is the long-standing "speed reads near zero" artifact. Direction is
        # preserved (negative = reversing), so no outer abs() is needed.
        deg_per_s = (-left_wheel.speed() + right_wheel.speed()) / 2
        speed_mps = deg_per_s / 360.0 * WHEEL_CIRC_M
        distance_on_the_right = right_eye.distance()   # mm to nearest obstacle
        distance_on_the_left = left_eye.distance()     # mm to nearest obstacle
        reflection = edge_sensor.reflection()          # 0-100% surface reflectivity

        # Stream one telemetry line per reading in the canonical wire format.
        emit("speed_mps", speed_mps)
        emit("distance_on_the_right", distance_on_the_right)
        emit("distance_on_the_left", distance_on_the_left)
        emit("reflection", reflection)

        # behavioural rule wired into the program: stop if too close
        # Trip on either side getting within 50 mm, or the floor going dark
        # (reflection < 20, i.e. an edge or black line). Guarded by the latch
        # so the motors are commanded to stop exactly once.
        if (distance_on_the_left < 50 or distance_on_the_right < 50 or reflection < 20) and not motors_stopped:
            left_wheel.stop()
            right_wheel.stop()
            motors_stopped = True

        wait(50)                            # 20 Hz; keep this off any critical control path
finally:
    # Always leave the hardware safe and signal the host that the run is over.
    left_wheel.stop()
    right_wheel.stop()
    stdout.write('{"event":"end"}\n')       # flush sentinel
