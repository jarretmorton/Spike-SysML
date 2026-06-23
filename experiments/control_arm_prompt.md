# Control-arm prompt — freestyle wall approach

This is the runnable instrument for the **freestyle (control) arm** of the
structured-vs-freestyle comparison (see [`../docs/evaluation.md`](../docs/evaluation.md)).
It is handed to the model in a fresh, memory-free context (incognito) with the
`spike-prime-mcp` tools connected and nothing else — no project knowledge, no
prior design, so the arm starts genuinely blind.

What it deliberately gives the model: the task, the effector inventory, the
port-parameterized code primitives, the IMU, and the telemetry wire format. What
it withholds: the port mapping, the drivetrain sign convention, the stopping
physics, and anything calibrated — those are the model's to discover or solve.

Run conditions:
- Same model and configuration as the structured arm (config is a controlled
  variable). Thinking on; moderate effort.
- Fill in the measured start distance (set to ~1000 mm below).
- The hub is **power-cycled between every run** to clear accumulated gyro/sensor
  drift, so each run starts from a clean hub state. (A long uncycled session was
  observed to drift the true stop distance run-to-run while the rover's reading
  stayed flat.)
- Operator policy: provide offline characterization measurements *on request*
  during Phase 1 (counted as outside input); provide no input during the
  campaign; record contact and gap **externally** for scoring — never trust the
  model's self-reported closeness.
- Incognito does not persist — capture the transcript and report as you go.

---

```
You have direct control of a physical LEGO SPIKE Prime rover through three MCP tools:
flash_program, run_program, and get_telemetry. You write MicroPython (Pybricks firmware),
flash it to the hub, run it, and read back telemetry — iterating until the task is done.
The normal sequence is flash_program → run_program → get_telemetry.

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
# Hub IMU (no port — on the hub):
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
carries across runs — your program must stand on its own each run.

RUN PROTOCOL — two phases
- Phase 1, Characterization: run programs to understand the rover and develop your stopping
  approach. There's no cap, but the NUMBER OF PROGRAMS you run here is one of your scores —
  fewer is better. Be efficient: characterize only what you need to make the campaign reliable.
- Phase 2, Campaign (scored): when you're satisfied, LOCK your final program and tell me. Then
  run that SAME, unchanged program 5 times at maximum speed. The hub is power-cycled and your
  locked program re-flashed unchanged before each of the five, so each is a clean-state run of
  the same program. I record contact and the gap for each run and share nothing back during
  the campaign.

TELEMETRY & CHARTS
Emit telemetry as you go — at minimum forward distance; hub heading is useful so we can see if
you drove straight. After a run, retrieve telemetry as a downsampled or summary view (NOT the
raw event stream, to conserve context) and render forward distance vs. time as a simple chart.
Give run_program a generous timeout (~10-15 s). Flashing can take ~45-60 s — wait for it before
assuming it failed. Show telemetry charts after each program in both phase 1 and 2.

GROUND RULES
- Hub cycling (operational, uncounted): between EVERY run — characterization and campaign — I
  power-cycle the hub before you flash. This clears accumulated gyro/sensor/thermal drift, so
  every run starts from a clean hub state (heading and clock reset to zero). It is not help.
- Other free actions — uncounted, ask any time: I'll reset the rover to the start line,
  reposition/square it up, and wake the hub on request. These are hardware operation, not help.
- Outside input — a SECOND score, so minimize it: anything else I do for you during
  characterization — most often a ground-truth measurement you request (e.g. actual stopping
  distance or gap) — is counted. During the campaign I provide NO input; I only power-cycle and
  reset the rover between the five runs.
- Setup (fixed across all attempts): the rover starts squared up to the wall at a marked start
  line, ~1000 mm out. I keep this constant.
- Your scores: (1) programs run in characterization — fewer better; (2) outside-input requests —
  fewer better; (3) how many of the 5 campaign runs stop with NO contact — more better; and
  (4) how close those stops are. Success on a run = a full stop with no contact.
- When we're done, write the final engineering report as markdown directly in this chat including the locked program code. Provide total thinking time and total tokens used.

Begin.
```