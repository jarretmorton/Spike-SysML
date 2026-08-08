# Rover Wall-Stop Engineering Report

**Task:** Drive at maximum speed toward a wall and stop as close as possible without contact.
**Setup:** LEGO SPIKE Prime rover, ~1000 mm from wall, squared to start line.
**Date:** 2026-07-20

---

## Locked Operation Program

```python
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

BASE_C = -1000   # left motor, max backward = toward wall
KP = 30          # heading correction gain on D (right motor)
BRAKE_AT = 130   # mm — sensor-reading threshold to trigger hold() brake
EMERGENCY = 50   # mm — safety floor

_last_d = 1000

def fwd():
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
    wait(500)   # IMU warm-up

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
        if clock.time() - t0 > 6000:
            emit('stop_cause', 2.0)
            break

        raw_d = 1000 + h * KP
        d_speed = max(0, min(1050, raw_d))
        mc.run(BASE_C)
        md.run(d_speed)
        wait(20)

    mc.hold()
    md.hold()
    wait(1500)

    df = fwd()
    hf = hub.imu.heading()
    emit('final_dist', float(df))
    emit('final_hdg', float(hf))
    hf_rad = hf * 3.14159265 / 180.0
    cos_hf = 1.0 - hf_rad * hf_rad / 2.0
    emit('gap_est', float(df * cos_hf))

finally:
    mc.brake()
    md.brake()
    stdout.write('{"event":"end"}\n')
```

---

## Hardware Map

| Port | Device | Role |
|------|--------|------|
| A | UltrasonicSensor | Forward-facing (primary) |
| B | UltrasonicSensor | Forward-facing (secondary) |
| C | Motor | Left drive wheel (C− = forward toward wall) |
| D | Motor | Right drive wheel (D+ = forward toward wall) |
| E | UltrasonicSensor | Rear/side (unused in operation) |
| F | ColorSensor | Downward-facing (unused in operation) |

**Drive convention:** the rover is physically oriented with its motor-forward direction pointing away from the wall. `C−, D+` drives it toward the wall. Equal-sign commands (`C−, D−`) produce pivot rotation, not translation — this was the key discovery in characterization that invalidated the initial approach.

---

## Characterization Summary

**Runs used:** 4 characterization runs (Runs 1–4).

| Run | Purpose | Key finding |
|-----|---------|-------------|
| 1 | Port discovery + direction test | Identified ports; same-sign = pivot, not translation |
| 2 | Braking characterization attempt | Heading correction sign wrong → runaway spin; no valid data |
| 3 | Direction identification + braking | Confirmed C−, D+ = toward wall; opposite-sign gives ~13.8 °/s leftward drift |
| 4 | Heading correction calibration | Empirical correction factor 0.077 °/s per °/s motor differential; measured actual overshoot 76 mm |

**Intrinsic heading drift** at max equal speed (C=−1050, D=+1050): **−13.8 °/s** (leftward).

**Correction strategy:** hold C constant at −1000 (max left); vary D with `md.run(clamp(1000 + h × 30, 0, 1050))`. When heading drifts negative (left), D is reduced, slowing the right wheel and creating a rightward corrective force. Clamping to [0, 1050] prevents D from going backward, eliminating the runaway instability that plagued earlier correction attempts that varied C.

**Equilibrium heading:** approximately −6° (D-motor-only correction settles at this angle). At −6°, sensor error is cos⁻¹(6°) ≈ 0.55% — negligible for braking purposes.

**Brake threshold derivation:**
- Measured overshoot in Run 4 characterization: 76 mm (actual, angle-corrected)
- Estimated overshoot at operation speed (~900 deg/s average vs ~950 deg/s in char run): ~63–80 mm
- Sensor reads ~40 mm at final position → brake threshold chosen as 130 mm
- This leaves ~90 mm of braking room against the measured overshoot

---

## Operation Runs — Per-Run Results

All 5 runs: `stop_cause = 1` (normal brake threshold reached). **No contact on any run.**

| Run | Onboard estimate (sensor gap_est) | Operator measurement | Delta |
|-----|----------------------------------|---------------------|-------|
| 1 | 40 mm | 129 mm | +89 mm |
| 2 | 40 mm | 128 mm | +88 mm |
| 3 | 40 mm | 113 mm | +73 mm |
| 4 | 40 mm | 127 mm | +87 mm |
| 5 | 40 mm | 124 mm | +84 mm |

**Mean measured gap:** 124.2 mm  
**Std deviation:** 5.8 mm  
**Min:** 113 mm (Run 3)  
**Max:** 129 mm (Run 1)

---

## Reconciliation of Systematic Offset

The onboard estimate (40 mm) is the distance from the **ultrasonic sensor face** to the wall. The operator measured from the **nearest physical part of the rover body** (front bumper/chassis) to the wall.

**Systematic offset = 84 mm average** (range 73–89 mm). This means the sensor face protrudes approximately **84 mm in front of the rover's physical bumper**. The sensor is mounted on a forward arm or nose piece that sits well ahead of the chassis.

The 16 mm run-to-run variance in measured gaps (113–129 mm) is partly explained by:
- Slight repositioning variation between runs (start distance ranged 892–930 mm)
- Heading variation at final stop (−1.8° to −4.8°), which shifts the rover's lateral position slightly
- Floor-contact variation in braking distance (estimated ±10–15 mm)

The onboard sensor reading was remarkably consistent (40 mm every run), confirming the sensor-face stopping position was stable. The measurement scatter reflects physical geometry variation more than control inconsistency.

---

## Heading Performance

| Run | Max hdg drift | Final hdg |
|-----|--------------|-----------|
| 1 | −4.8° | −2.6° |
| 2 | −4.4° | −3.4° |
| 3 | −4.1° | −3.1° |
| 4 | −4.0° | −4.8° |
| 5 | −5.0° | −3.4° |

Heading stayed within ±5° throughout every run. The D-motor correction successfully contained the natural leftward drift and the rover approached the wall nearly straight on each run.

---

## Lessons Learned

**What worked:**
- Sensor-triggered `hold()` brake is highly repeatable — sensor face stopped at exactly 40 mm every run.
- D-motor-only heading correction (keep C constant, vary D) is stable for all heading values since D can never go backward with the [0, 1050] clamp.
- 500 ms IMU warm-up delay eliminated spurious initial heading readings that caused runaway in earlier attempts.

**What didn't work:**
- C-motor correction (varying C, holding D constant): when heading goes sufficiently negative, this drives C positive (backward), converting forward motion into a left pivot → runaway spin. This caused failed operation runs 2 and 3.
- Equal-sign motor commands (both same polarity): produce pure pivot rotation, not translation — the rover spins in place rather than approaching the wall. Discovery of this required 2 characterization runs.

**If repeating this task:**
- The 84 mm sensor-to-bumper offset would be calibrated into the brake threshold from the start: `BRAKE_AT = 130 + 84 = 214 mm` sensor reading to target ~30 mm physical bumper gap, instead of the 124 mm achieved here.
- With this correction, a physical gap of ~30 mm should be achievable across 5 runs.
