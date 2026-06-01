# examples/hub_program_example.py
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

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, ForceSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout


# --- physical configuration (edit to match your build) ---
hub   = PrimeHub()
left  = Motor(Port.B)
right = Motor(Port.A)
force = ForceSensor(Port.C)
WHEEL_CIRC_M = 0.055 * 3.1416 * 2          # 55 mm radius wheel

clock = StopWatch()


def emit(sensor, value):
    """One canonical telemetry line. Hub clock is the only timestamp
    that's valid for time-bound requirements — BLE arrival times are
    buffered and chunked, so the host can't reconstruct them."""
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'
                 % (clock.time(), sensor, value))


# --- commands ---
left.run(-180)                              # 180 deg/s forward (signs depend on chassis)
right.run(180)

# --- measurement loop ---
try:
    motors_stopped = False
    while clock.time() < 8000:
        deg_per_s = (left.speed() + right.speed()) / 2
        speed_mps = abs(deg_per_s / 360.0 * WHEEL_CIRC_M)
        force_n = force.force()

        emit("speed_mps", speed_mps)
        emit("force_n", force_n)

        # behavioural rule wired into the program: stop on first contact
        if force_n > 0 and not motors_stopped:
            left.stop()
            right.stop()
            motors_stopped = True

        wait(50)                            # 20 Hz; keep this off any critical control path
finally:
    left.stop()
    right.stop()
    stdout.write('{"event":"end"}\n')       # flush sentinel
