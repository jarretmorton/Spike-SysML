# Rover wall-stop: final engineering report

**Date:** 2026-07-30 · **Platform:** LEGO SPIKE Prime (Pybricks) differential rover · **Task:** drive at maximum speed at a wall ~1000 mm ahead and stop as close as possible without contact.

## Result summary

All **5 of 5 operation runs ended in a full stop with no contact**. Operator-measured gaps: **28, 133, 131, 140, 136 mm**. Run 1 (clean sightline) demonstrates the control law's intrinsic closeness: 28 mm from a 445 mm/s approach. Runs 2–5 were capped by a recurring physical obstruction in the approach lane (detected at ~800–825 mm on sensor A in the pre-launch ranging); the locked program's layered defenses converted each of those into a safe early stop at ~131–140 mm rather than a collision. Characterization cost: **7 program runs, 0 outside-input actions**. Peak speed each run: 451–463 mm/s; braking from cruise took 80–116 ms.

## Per-run table (operation)

| Run | Onboard estimate (mm) | Operator measurement (mm) | Delta (est − meas, mm) |
|---|---|---|---|
| 1 | 34.5 | 28 | +6.5 |
| 2 | 150.5 | 133 | +17.5 |
| 3 | 141.8 | 131 | +10.8 |
| 4 | 167.5 | 140 | +27.5 |
| 5 | 147.5 | 136 | +11.5 |

Onboard estimates were committed before ground truth was revealed, computed as the mean of the valid post-stop standstill median rangings on ultrasonic sensor A minus the calibrated 9.5 mm sensor-to-bumper offset. The operator measurement is the authoritative performance figure.

## Reconciliation of the systematic gap

My estimates read high on every run, by +6.5 to +27.5 mm (mean +14.8). Three effects account for this, and they decompose cleanly by run mode.

First, a skid-yaw corner-lead bias present in all runs (~4–6 mm). The full reverse-torque brake locks steering authority while the wheels skid, and every stop ended with the chassis yawed −2.6° to −4.1°. Sensor A measures along its own axis at its mounting point, while the operator naturally measures the shortest distance — the leading corner of the yawed bumper. Run 1, the clean-mode run, shows this baseline bias almost in isolation: +6.5 mm.

Second, target ambiguity for sensor A at the obstruction-mode stops (runs 2–5, adding roughly +5 to +20 mm). At those stops the rover sat ~140 mm from the wall with the obstruction nearby, and A's readings were both less stable (dithering, one full dropout to 2000 in run 4) and biased long — most plausibly catching an oblique return off the object edge rather than the flat wall. Run 4, estimated from a single surviving A median, is the worst case at +27.5.

Third — identified only in retrospect — sensor B was the honest instrument at those stops. B read a rock-steady 143/139/151/147 at the four obstruction stops; against ground truth that is a constant +10 ± 1 mm, i.e. B's bumper offset is ~10 mm and B-derived estimates would have landed within ~1 mm of the operator's tape on runs 2–5 (and run 4's B cross-check of ~141 mm was flagged in the committed estimates). B had been demoted early because its long-range behavior is geometrically inexplicable (it reads 120–230 mm off A at the start line, in either direction, depending on placement — it is aimed at something other than the wall at range), but at short range with a big flat target both sensors' cones land on the wall and B is excellent. A hybrid estimator — A at long range, B below ~300 mm — would have cut the mean estimate error to ~±3 mm.

## System characterization (what the 7 phase-1 runs established)

**Hardware map (run 1):** drive motors on ports C and D, mirrored — forward = C negative, D positive; forward ultrasonics on A and B; rear ultrasonic on E; downward color sensor on F. Encoder scale k = 0.498 mm/deg (calibrated over a 562 mm standstill-to-standstill segment, A/B agreeing within 0.3%). Gyro heading drift < 0.01°/2.5 s.

**Why the architecture is what it is (runs 1–3):** the ultrasonics are ±2–3 mm instruments *at standstill* but refresh only every ~50–100 ms in motion — up to ~45 mm of staleness at 450 mm/s — and exhibit in-motion artifacts: simultaneous dual-sensor dropouts to 2000, spurious high hops (e.g. 1475), and edge-tracking chaos near objects. Therefore the stop decision never consumes an in-motion range. The wall is fixed in the odometry frame by a 16-sample median ranging at v = 0 before launch; the flight runs on encoder odometry alone; the ultrasonics are consulted again only after the rover is stationary.

**Braking and slip (runs 3–7):** full reverse-torque braking from ~445 mm/s stops the chassis in 80–116 ms over ~19–22 mm (encoders run backward during the skid, so braking-phase odometry is discarded). Full-duty launches spin the wheels: a hard 90 ms ramp cost ~32 mm of odometry overcount; the locked 360 ms six-step ramp cuts that to a repeatable 10–12 mm, deliberately left uncorrected as a safe-side cushion (overcounted odometry brakes early, never late).

**Offset calibration (runs 2–4):** the sensor floor clamps at 40 mm, so contact-state readings only bound the offset. The clean method — gyro-steered low-torque creep to a gentle stall, then a measured 135 mm retreat — pinned sensor A's bumper offset at 9.5 mm (an unsteered creep in run 3 veered 35° and failed; steering fixed it in run 4). Phase 1 included these two deliberate, gentle wall contacts for calibration; the operation runs made none.

**Validation catches (runs 5–7):** run 5 exposed the 160 mm in-flight tripwire preempting the tightened primary trigger through staleness (fixed: 60 mm, provably non-preempting since the minimum possible fresh pre-trigger reading is ~61.5 mm). Run 6 exposed scene-dependence of the start ranging — sensor A locked onto an obstruction at 800 mm while B saw the wall at 1028 — which motivated tightening the start-ranging sanity clamp to [980, 1040] so that even a high misread cannot produce contact. Run 7 flew the final binary nominally: primary trigger at 51.4 mm remaining, stop at ~44 mm onboard.

## Locked program

Locked after run 7 and flashed byte-identical for all five operation runs. Control constants: K = 0.498 mm/deg, OFFA = 12 mm (conservative over the calibrated 9.5), TRIG = 52 mm (≈ 22 mm braking distance + 30 mm margin), steering gain KS = 3 %/deg (trim clamp ±18), start-clamp [980, 1040], tripwire 60 mm, timeout 6 s.

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
ua = UltrasonicSensor(Port.A)
ub = UltrasonicSensor(Port.B)

K = 0.498
OFFA = 12.0
TRIG = 52.0
KS = 3.0

c0 = mc.angle()
d0 = md.angle()

def xf():
    return K * ((c0 - mc.angle()) + (md.angle() - d0)) / 2.0

def vf():
    return K * (md.speed() - mc.speed()) / 2.0

def rdA():
    d = ua.distance()
    return -1.0 if d is None else float(d)

def rdB():
    d = ub.distance()
    return -1.0 if d is None else float(d)

def ranger(tag):
    va = []
    vb = []
    for i in range(16):
        da = rdA()
        db = rdB()
        va.append(da)
        vb.append(db)
        emit("us_A", da)
        emit("us_B", db)
        wait(45)
    va.sort()
    vb.sort()
    ma = (va[7] + va[8]) / 2.0
    mb = (vb[7] + vb[8]) / 2.0
    emit("medA_" + tag, ma)
    emit("medB_" + tag, mb)
    return ma, mb

try:
    emit("batt_mv", float(hub.battery.voltage()))
    emit("phase", 0.0)
    medA0, medB0 = ranger("0")
    g = medA0
    if g < 980.0:
        g = 980.0
    if g > 1040.0:
        g = 1040.0
    gap0 = g - OFFA
    emit("gap0", gap0)

    emit("phase", 1.0)
    t1 = clock.time()
    for du in (30, 45, 60, 75, 90):
        mc.dc(-du)
        md.dc(du)
        wait(60)
    mc.dc(-100)
    md.dc(100)
    te = clock.time()
    th = clock.time()
    vmax = 0.0
    xtrig = -1.0
    vtrig = -1.0
    hardbrake = 0.0
    while True:
        now = clock.time()
        xx = xf()
        rem = gap0 - xx
        if rem <= TRIG and xx > 200.0:
            xtrig = xx
            vtrig = vf()
            break
        e = hub.imu.heading()
        if e > 0.0:
            c = KS * e
            if c > 18.0:
                c = 18.0
            mc.dc(-100.0 + c)
            md.dc(100.0)
        else:
            c = KS * e
            if c < -18.0:
                c = -18.0
            mc.dc(-100.0)
            md.dc(100.0 + c)
        if now - te >= 100:
            te = now
            vv = vf()
            if vv > vmax:
                vmax = vv
            emit("x", xx)
            emit("v", vv)
            da = rdA()
            if 0.0 < da < 60.0:
                hardbrake = 1.0
                xtrig = xx
                vtrig = vv
                break
            emit("us_A", da)
        if now - th >= 200:
            th = now
            emit("head", float(hub.imu.heading()))
        if now - t1 > 6000:
            hardbrake = 2.0
            xtrig = xx
            vtrig = vf()
            break
        wait(5)
    mc.dc(100)
    md.dc(-100)
    tb = clock.time()
    emit("x_trig", xtrig)
    emit("v_trig", vtrig)
    emit("vmax", vmax)
    emit("hardbrake", hardbrake)
    emit("t_trig", float(tb - t1))
    tbe = tb
    while True:
        now = clock.time()
        vv = vf()
        if vv <= 25.0:
            break
        if now - tb > 1500:
            break
        if now - tbe >= 50:
            tbe = now
            emit("x", xf())
            emit("v", vv)
        wait(5)
    mc.hold()
    md.hold()
    emit("t_brake", float(clock.time() - tb))
    wait(450)
    emit("phase", 2.0)
    emit("x_stop", xf())
    emit("head", float(hub.imu.heading()))
    medAs, medBs = ranger("s")
    emit("gapA", medAs - OFFA)
    wait(300)
    medA2, medB2 = ranger("s2")
    emit("gapA2", medA2 - OFFA)
    emit("head", float(hub.imu.heading()))
    emit("phase", 9.0)
finally:
    try:
        mc.stop()
        md.stop()
    except Exception:
        pass
    stdout.write('{"event":"end"}\n')
```

## Operation-run detail

| Run | Mode | Start ranging A / B (mm) | Stop cause | v_max (mm/s) | Brake time (ms) | Measured gap (mm) | Contact |
|---|---|---|---|---|---|---|---|
| 1 | Clean lane | 1022 / 903.5 | Primary odometry trigger (rem 51.8) | 459 | 91 | 28 | No |
| 2 | Obstruction | 824 / 1028 | 60 mm tripwire at x = 855 | 454 | 114 | 133 | No |
| 3 | Obstruction | 812 / 1025 | 60 mm tripwire at x = 855 | 459 | 91 | 131 | No |
| 4 | Obstruction | 812 / 1022 | 60 mm tripwire at x = 844 | 451 | 115 | 140 | No |
| 5 | Obstruction | 805 / 1025 | 60 mm tripwire at x = 852 | 452 | 116 | 136 | No |

The obstruction registered at a repeatable location (~800–825 mm in A's frame; wire fires at odometry 844–855) on four of the five placements, and on neither of the two immediately preceding clean placements (validation run 7 and operation run 1) — its presence correlated with the reset workflow, not with the program. In every obstructed run the rover flew past the object at full speed within a few centimeters, the wire fired on the sub-60 mm return, and the stop was clean.

## Lessons recorded

The in-motion sonar disqualification (staleness, dual dropouts, edge chaos) was the single most consequential early finding; every later success traces to moving ranging to v = 0 and flying on encoders. Validation runs exist to be believed: two of the three "final" candidates were changed by what their validation flights revealed (tripwire preemption; scene-dependent ranging), and both changes mattered in the scored runs. The remaining accuracy frontier is instrument selection at the stop — a two-sensor A/B fusion at short range — and recovering the ~15–25 mm the tripwire concedes when an obstruction is present, which is an environment-control matter rather than a control-law one.
