# examples/drive_until_clear.py
#
# Worked example for the traceability spine. Implements R-COL-1 (forward
# collision avoidance) and R-PERF-1 (drive at the max speed for which R-COL-1
# holds) from the spec line: "Rover should drive as fast as it can without
# running into anything." Runs ON the SPIKE Prime hub under Pybricks firmware.
#
# Wire contract (docs/wire_contract.md):
#   {"timestamp_ms": <int, hub clock>, "sensor": "<name>", "value": <number>}
#   {"event": "end"}   <- flush sentinel at end of run
#
# Spine note: this program is the `implemented_by` node for R-COL-1/R-PERF-1.
# The calibrated parameters below are the `depends_on_params` set — each is
# bound by a calibration test, NOT hand-tuned here. v_max and the stop
# threshold are computed on-hub from the model relations so the deployed code
# embodies the SysML physics rather than a baked-in constant.

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout                     # MicroPython sys; stdout is the BLE pipe

# --- physical configuration (matches hub_program_example.py; edit to build) ---
hub         = PrimeHub()
left_wheel  = Motor(Port.C)
right_wheel = Motor(Port.D)
left_eye    = UltrasonicSensor(Port.A)      # forward-left distance sensor  -> P-DIST-F
right_eye   = UltrasonicSensor(Port.B)      # forward-right distance sensor -> P-DIST-F

# --- calibrated / human-set parameters (all SI; from calibration, UNCALIBRATED) ---
# These are placeholders. In the pipeline they arrive from the calibration
# stage (steps 9-11); UNCALIBRATED marks a free parameter not yet bound.
DRIVE_CONSTANT  = 0.030     # m1  driveConstant      UNCALIBRATED - m per rad
DECEL_COLLISION = 0.50      # m2  decelCollision     UNCALIBRATED - m/s**2 (speed-sweep)
T_SENSOR_DIST   = 0.020     # m2  tSensorDistance    UNCALIBRATED - s
MARGIN_COLL     = 0.040     # m2  marginCollision    SET BY HUMAN - m
D_SENSE_MAX     = 0.300     # m2  dSenseMax          UNCALIBRATED - m (reliable range)
T_CHAIN         = 0.060     # rover_common tChain    UNCALIBRATED - s (latency chain)

# --- derived control constants (MaxForwardSpeed + ForwardStopThreshold) ---
# t_response is the full sense->decide->actuate lag: shared chain + this
# sensor's sampling latency.
t_response = T_CHAIN + T_SENSOR_DIST

# v_max = -a*t + sqrt(a^2 t^2 + 2a (D - margin))   (m2 MaxForwardSpeed)
# ** 0.5 mirrors the SysML sqrt-avoidance convention. Guard the discriminant:
# a negative value means the sensing budget can't cover even the margin, so
# there is no safe forward speed and the rover must not move.
_disc = DECEL_COLLISION**2 * t_response**2 + 2*DECEL_COLLISION*(D_SENSE_MAX - MARGIN_COLL)
v_max = (-DECEL_COLLISION*t_response + _disc**0.5) if _disc > 0 else 0.0

# --- UNIT BOUNDARY: SI model -> sensor units ------------------------------
# Everything above is SI (metres, seconds, m/s**2), matching the SysML models.
# Everything the control loop below compares against sensor reads is in sensor
# units. This is the on-hub half of the conversion boundary; the host-side half
# is tools/units.py (see docs/wire_contract.md section 2.2). The only crossing
# the loop needs is the stop threshold in mm, because distance() reports mm.
# At v_max threshold_m == D_SENSE_MAX by construction; computed generally so the
# code tracks the model rather than a baked constant.
threshold_m  = v_max*t_response + v_max**2/(2*DECEL_COLLISION) + MARGIN_COLL
threshold_mm = threshold_m * 1000.0          # metres -> millimetres

# Convert v_max (m/s) to a wheel command (deg/s) through the CALIBRATED
# driveConstant (m per rad) -- not wheel geometry, because driveConstant
# already absorbs slip. v = omega*k -> omega[rad/s] = v/k -> deg/s.
cmd_deg_s = (v_max / DRIVE_CONSTANT) * (180.0 / 3.14159265) if DRIVE_CONSTANT > 0 else 0.0

clock = StopWatch()


def emit(sensor, value):
    """One canonical telemetry line. Hub clock is the only valid timestamp;
    BLE arrival times are buffered and cannot be trusted for time-bound checks."""
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'
                 % (clock.time(), sensor, value))


# --- drive (R-PERF-1: command v_max; mirror signs as in the reference build) ---
left_wheel.run(-cmd_deg_s)
right_wheel.run(cmd_deg_s)

# --- measurement + collision-stop loop (R-COL-1) ---
# Telemetry is intentionally LEAN: clearance_mm is the graded channel
# (pass_criteria joins on it); the two raw forward distances are emitted as
# evidence. speed_mps is deliberately omitted -- Motor.speed() under-reports
# during real motion (a known artifact), so it can't back a pass criterion yet.
try:
    motors_stopped = False
    while True:
        d_left  = left_eye.distance()       # mm to nearest obstacle, forward-left
        d_right = right_eye.distance()       # mm to nearest obstacle, forward-right
        clearance_mm = d_left if d_left < d_right else d_right

        emit("clearance_mm", clearance_mm)   # <- R-COL-1 pass_criteria.sensor
        emit("distance_left", d_left)         # evidence
        emit("distance_right", d_right)       # evidence

        # Trigger the collision-stop maneuver once clearance reaches the
        # speed-dependent threshold. Latched so stop() is issued exactly once.
        if clearance_mm <= threshold_mm and not motors_stopped:
            left_wheel.stop()
            right_wheel.stop()
            motors_stopped = True

        wait(50)                             # 20 Hz; keep off any critical control path
finally:
    left_wheel.stop()
    right_wheel.stop()
    stdout.write('{"event":"end"}\n')        # flush sentinel
