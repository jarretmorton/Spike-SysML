# task_core.md — shared controlled apparatus (BOTH arms)

Source of truth for the controlled variables of the structured-vs-freestyle A/B: the task,
rover inventory, code primitives, telemetry wire format, two-phase protocol, scoring, and
ground rules. **Edit these here once** — both arms prepend this identical block so "both arms
ran under identical conditions" is true by construction.

Assembly: the prompt delivered to each arm is the fenced block below, **then** that arm's delta
block (`freestyle_arm_prompt.md` or `se_arm_prompt.md`), ending in `Begin.`. The model always
receives full text, never a link.

```
You have direct control of a physical LEGO SPIKE Prime rover through three MCP tools:
flash_program, run_program, and get_telemetry. You write MicroPython (Pybricks firmware),
flash it to the hub, run it, and read back telemetry. The normal sequence is
flash_program -> run_program -> get_telemetry.

TASK
There is a wall directly ahead of the rover. Make the rover drive straight at the wall at the
drive motors' MAXIMUM speed and come to a complete stop as close to it as possible WITHOUT
touching it.

Hard constraints:
- Run the drive motors at maximum speed. Do not slow down for safety margin.
- The rover must not make contact with the wall.

Objective: minimize the final gap between the rover and the wall.

THE ROVER (what's physically on it)
- A SPIKE Prime hub running Pybricks firmware, with a built-in IMU (heading + acceleration).
- Two drive motors (differential drivetrain).
- Ultrasonic distance sensors: two forward-facing ones for obstacles ahead, plus a rear one.
- A downward-facing color/reflectance sensor.

You do NOT know which device is on which port, or the drivetrain's direction conventions.
Determine these yourself before relying on them.

DEVICE PRIMITIVES (Pybricks)
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub   = PrimeHub()
clock = StopWatch()

# IMPORTANT: constructing a device claims its port and does NOT release it. Re-constructing
# the same device raises OSError EBUSY. Construct each device ONCE near the top and reuse it.

# Motor (non-blocking), speed in deg/s. For full speed, command a large target (run() clamps
# to the motor's physical ceiling) or read its rated max.
#   m = Motor(Port.X); m.run(speed_deg_s); m.stop()
# Ultrasonic distance, mm to nearest obstacle:
#   s = UltrasonicSensor(Port.X); d_mm = s.distance()
# Downward reflectance, 0-100%:
#   c = ColorSensor(Port.X); pct = c.reflection()
# Hub IMU (no port - on the hub):
#   hub.imu.heading()           # yaw in degrees, relative to start
#   hub.imu.acceleration()      # 3-axis acceleration
#   hub.imu.angular_velocity()  # 3-axis rotation rate

# Telemetry: one JSON line per reading. The hub-clock timestamp is the only valid one (BLE is
# buffered, so host arrival times mean nothing for timing).
def emit(sensor, value):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'
                 % (clock.time(), sensor, value))

# End EVERY run with the flush sentinel on its own line, or the last samples are lost:
#   stdout.write('{"event":"end"}\n')

Wrap your control loop so the motors always stop and the sentinel is always sent, even on
interruption (e.g. try/finally). Pace the loop with wait(ms). NOTE: the hub is power-cycled
between every run, so the IMU heading and the hub clock reset to zero each time and no state
carries across runs - your program must stand on its own each run.

RUN PROTOCOL - two phases
- Phase 1, Characterization: run programs to understand the rover and prepare your operation
  program. There's no cap, but the NUMBER OF PROGRAM RUNS here is one of your scores - every
  flash-and-run counts, including re-running an unchanged program; fewer is better. Characterize only what you need to make the operation reliable.
- Phase 2, Operation (scored): when you're satisfied, LOCK your final program and tell me. Then
  run that SAME, unchanged program 5 times at maximum speed. The hub is power-cycled and your
  locked program re-flashed unchanged before each of the five, so each is a clean-state run of
  the same program. I record contact and the gap for each run and share nothing back during
  the operation.

TELEMETRY & CHARTS
Emit telemetry as you go - at minimum forward distance; hub heading is useful so we can see if
you drove straight. After a run, retrieve telemetry as a downsampled or summary view (NOT the
raw event stream, to conserve context) and render forward distance vs. time as a simple chart.
Give run_program a generous timeout (~10-15 s). Flashing can take ~45-60 s - wait for it before
assuming it failed. Show telemetry charts after each program in both phases.

GROUND RULES
- Readiness handshake - ASK BEFORE EVERY FLASH: I power-cycle and reposition the rover between
  runs, which takes a moment. Before each flash_program (characterization AND operation), ask me
  whether the hub is ready and WAIT for my explicit go-ahead - do NOT flash until I confirm.
  Flashing while I'm still repositioning wastes the run and may hit a sleeping or mid-reset hub.
- Hub cycling (operational, uncounted): between EVERY run - characterization and operation - I
  power-cycle the hub before you flash. This clears accumulated gyro/sensor/thermal drift, so
  every run starts from a clean hub state (heading and clock reset to zero). It is not help.
- Other free actions - uncounted, ask any time: I'll reset the rover to the start line,
  reposition/square it up, and wake the hub on request. These are hardware operation, not help.
- Outside input - a SECOND score, so minimize it: anything else I do for you during
  characterization - most often a ground-truth measurement you request (e.g. actual stopping
  distance or gap) - is counted, and each distinct measurement or action counts separately even
  when you batch several into one request. During the five operation runs I provide NO input; I only
  power-cycle and reset the rover between them. The sole exception is at close-out, after all five
  are locked and run, when I give you the measured gaps (see OPERATION CLOSE-OUT) - these arrive
  after the fact and cannot influence any run.
- Setup (fixed across all attempts): the rover starts squared up to the wall at a marked start
  line, ~1000 mm out. I keep this constant.
- Your scores: (1) program runs in characterization (every flash-and-run, incl. re-runs of an
  unchanged program) - fewer better; (2) outside-input actions (each distinct measurement/action
  counts, even when batched into one request) - fewer better; (3) how many of the 5 operation runs stop with NO contact - more better; and
  (4) how close those stops are. Success on a run = a full stop with no contact.

OPERATION CLOSE-OUT (after all 5 runs - in this order)
1. Freeze your onboard estimates FIRST: before I give you any measurement, state your own per-run
   final gap for each of the 5 runs (whatever channel you used) and commit them here in the chat. This is your prediction of where you stopped, fixed before
   you see ground truth.
2. Then ASK me for ground truth and WAIT: request the operator-measured gap for each of the 5 runs.
   This is the ONLY operator data exchange in the whole operation phase - nothing during the five
   runs, only these measurements once all five are locked and run, so they cannot influence any run.
   You genuinely cannot finish without them: they are the scored closeness metric and the check on
   your own accuracy.
3. Then produce the final engineering report as a downloadable markdown artifact (a file I can save,
   not just a chat reply), including the locked program code AND a per-run table with three columns -
   your onboard estimate (from step 1), my measurement, and the delta - plus a short reconciliation
   of any systematic gap. My measurement is the authoritative performance figure; your estimate is
   the prediction being checked against it.
```