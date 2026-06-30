# Rover Wall-Stop Mission — Engineering Report

**Task:** Drive a LEGO SPIKE Prime rover straight at maximum speed toward a wall ~1000 mm away and stop as close as possible without touching it. Develop and calibrate a program (characterization), then lock one program and run it five times unchanged (operation).

**Outcome:** **5 / 5 operation runs stopped without contact**, gaps 81–99 mm, every approach straight. All calibration was done from onboard telemetry only — zero operator measurements were requested during characterization.

---

## 1. Result summary (scored dimensions)

| Dimension | Result |
|---|---|
| No-contact on the 5 operation runs (paramount) | **5 / 5 — no contact** |
| Operator-measured gaps | 99, 87, 95, 81, 97 mm (mean **91.8**, σ 6.8) |
| Approach straightness | Heading bounded to a few degrees every run, mean ≈ 0° |
| Outside-input / operator actions during characterization | **0** (telemetry-only; re-squaring between runs is free) |
| Characterization program runs | 8 |

The rover stopped reliably ~9 cm short of the wall with no contact across all five scored runs, and stop-to-stop repeatability was ±~7 mm.

---

## 2. The locked operation program

This exact program was flashed and run, unchanged, for all five operation runs.

```python
# ===== LOCKED OPERATION PROGRAM - run unchanged x5 =====
# Drive straight at max controllable speed, brake via wheel-encoder at a
# calibrated trigger to stop short of the wall without contact.
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

def emitt(ts, s, v):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n' % (ts, s, v))
def emit(s, v):
    emitt(clock.time(), s, v)

mC = Motor(Port.C); mD = Motor(Port.D)
sA = UltrasonicSensor(Port.A); sB = UltrasonicSensor(Port.B)

cC = -1; cD = 1
VMAX = 1020          # just below physical max -> gyro retains steering authority
Kc = 18.0            # gyro-hold gain
GCLAMP = 500.0
MMPD = 0.4846        # mm per averaged wheel-degree (calibrated)
FT_OP = 1821.0       # brake trigger (deg of avg wheel travel)
aC0 = 0; aD0 = 0

def read_pair_n(n, gap=8):
    ta = 0.0; tb = 0.0
    for _ in range(n):
        ta += sA.distance(); tb += sB.distance(); wait(gap)
    return ta / n, tb / n

def setref():
    global aC0, aD0
    aC0 = mC.angle(); aD0 = mD.angle()

def ftravel():
    return (cC * (mC.angle() - aC0) + cD * (mD.angle() - aD0)) / 2.0

def gdrive(v):
    g = Kc * hub.imu.heading()
    if g > GCLAMP: g = GCLAMP
    if g < -GCLAMP: g = -GCLAMP
    vc = cC * v + g
    vd = cD * v + g
    if vc > 1100: vc = 1100
    if vc < -1100: vc = -1100
    if vd > 1100: vd = 1100
    if vd < -1100: vd = -1100
    mC.run(vc); mD.run(vd)

def stop_hold():
    mC.hold(); mD.hold()

def flush_log(xn, hn, ts, xs, hs, maxp):
    n = len(ts)
    if n == 0:
        return
    step = n // maxp
    if step < 1:
        step = 1
    i = 0
    while i < n:
        emitt(ts[i], xn, xs[i]); emitt(ts[i], hn, hs[i])
        i += step

try:
    mC.control.limits(speed=1100, acceleration=12000)
    mD.control.limits(speed=1100, acceleration=12000)

    # start distance (log/sanity only; trigger is encoder-based)
    wait(300)
    ia, ib = read_pair_n(15)
    D0 = (ia + ib) / 2.0
    emit("initA", ia); emit("initB", ib); emit("D0", D0)

    # full-speed straight approach, gyro-held, encoder brake
    hub.imu.reset_heading(0); wait(150)
    setref()
    bt = []; bx = []; bh = []
    ls = clock.time(); t0 = clock.time()
    while True:
        gdrive(VMAX)
        ft = ftravel()
        now = clock.time()
        if now - ls >= 12:
            bt.append(now); bx.append(D0 - ft * MMPD); bh.append(hub.imu.heading()); ls = now
        if ft >= FT_OP:
            break
        if now - t0 > 4000:
            break
        wait(3)
    ft_brake = ftravel()
    stop_hold()
    wait(900)
    ft_stop = ftravel()
    ea, eb = read_pair_n(12)
    onboard_gap = 64.45 - (ft_brake - 1825.5) * MMPD
    emit("ft_brake", ft_brake); emit("ft_stop", ft_stop)
    emit("bEndA", ea); emit("bEndB", eb)
    emit("onboard_gap_est", onboard_gap)
    flush_log("cRem", "cHead", bt, bx, bh, 18)
finally:
    mC.stop(); mD.stop()
    stdout.write('{"event":"end"}\n')
```

**How it works.** It commands both drive motors at 1020 deg/s (deliberately just under the ~1067 deg/s physical ceiling so the gyro controller has room to steer), holds heading at 0° with a proportional gyro correction, integrates forward travel from the wheel encoders, and brakes hard (`hold()`) the instant integrated travel reaches 1821°. The brake point is a **fixed wheel-travel count**, calibrated against the wall — it does not depend on the unreliable ultrasonic reading.

---

## 3. Per-run results: onboard estimate vs operator measurement

| Run | Onboard estimate (mm) | Operator measured (mm) | Δ = measured − estimate (mm) | Contact? |
|----:|:---------------------:|:----------------------:|:----------------------------:|:--------:|
| 1 | 65.7 | 99 | +33.3 | No |
| 2 | 64.7 | 87 | +22.3 | No |
| 3 | 64.9 | 95 | +30.1 | No |
| 4 | 66.6 | 81 | +14.4 | No |
| 5 | 64.9 | 97 | +32.1 | No |
| **Mean** | **65.4** | **91.8** | **+26.4** | **0 / 5** |

(σ: onboard 0.8 mm, measured 6.8 mm, Δ 7.1 mm.)

---

## 4. Reconciliation

Two things stand out, and both point the same way — toward safety.

**(a) A systematic +26 mm offset (estimate low, real gap larger).** My onboard estimates clustered at ~65 mm but the true gaps averaged ~92 mm. The cause is in how I calibrated "contact" without operator input: during characterization the rover crept into the wall and detected contact by a **motor-load spike**. That spike fires when the *frontmost* point of the rover loads up against the wall — almost certainly the forward ultrasonic sensors, which protrude ahead of the chassis. The operator measures the gap to the rover's front face, which sits ~26 mm *behind* that contact point. So my contact reference was ~26 mm short of the operator's reference, and every gap estimate inherited that bias. Crucially, the error is in the **safe direction**: the rover always stopped *farther* from the wall than I thought.

**(b) Run-to-run variability of ~±7 mm (σ), 18 mm full spread.** The true gaps ranged 81–99 mm. This matches the ±15–20 mm variability I estimated from the two calibration points before locking, and it comes from the hard stop's locked-wheel skid plus tiny differences in the start position. My onboard estimates couldn't show this spread because the brake trigger is a fixed encoder count — the model produces nearly the same number every run; only the physical stop varies.

**Net:** the locked configuration was even more conservative than intended (~92 mm rather than the ~65 mm target), which is why no-contact held comfortably on all five runs with ~30 mm of margin to spare. The honest lesson is that with operator measurements unavailable during characterization, my absolute zero was off by a fixed geometric offset; a single ground-truth point would have let me close that gap and stop ~3 cm nearer while staying safe.

---

## 5. How the solution was reached

The task looked simple but the hardware hid several traps. Each characterization run isolated and fixed one.

| Run | Purpose | Key finding |
|----:|---|---|
| 1 | Device discovery | Motors on C/D (matched pair); ultrasonics on A/B (forward) and E (rear); color sensor on F. |
| 2 | First full-speed attempt | Failed. At max command the rover **veered to −27°**; the angled forward sensors lost the wall and `distance()` **blocked ~500 ms per read**, so it blew through the brale trigger and nearly hit the wall. |
| 3 | Gyro-hold (first try) | Failed. Reading the ultrasonic inside the control loop (blocking) made the loop run ~1 Hz; at that rate the gyro gain **oscillated ±60°**. Also learned stdout-over-BLE is slow (~5–11 lines/s). |
| 4 | Encoder-balance calibration | Got **mm-per-degree = 0.4846** cleanly. Confirmed the fixes: no ultrasonic in motion loops, log to memory and flush after stopping. Also discovered the hard stop **skids ~37 mm with locked wheels** (encoder-invisible). |
| 5 | Gyro-hold at full command | Failed straightness again — the smoking gun: commanding 2000 **rails both motors at the physical ceiling**, leaving the gyro no headroom to create a steering differential. |
| 6 | **The fix** | Command **1020** (just under the ceiling). Heading held within **±3°, no drift**. Straightness solved. |
| 7 | Contact calibration | Brake-trigger → gap law established by creeping to the wall and measuring with the encoder (motor-load contact detection). Confirmed the ultrasonic is unusable for absolute distance — the two sensors disagree by ~135 mm and the sign of the error flips with range. |
| 8 | Operation candidate, verified | Ran the exact locked approach, then creep-verified the stop. Locked it. |

**The decisive insights:**
- **Never read the ultrasonic while moving** — it blocks for ~0.5 s whenever it loses a clean echo.
- **Steer with the gyro, but leave speed headroom** — at the railed maximum there is no authority to correct; ~5% below max restores it.
- **Trigger braking on the wheel encoders, not the rangefinder** — encoders are instant and never block, and an encoder trigger is inherently wall-safe (if anything goes wrong, the rover stops *farther* out).
- **Reference distance to the wall itself** — the ultrasonic's absolute accuracy is poor, so the wall (via gentle contact) is the only trustworthy zero.

---

## 6. Calibrated constants (final)

| Constant | Value | Source |
|---|---|---|
| Forward motor combo (C, D) | (−1, +1) | Run 2 there-and-back pulse test |
| mm per averaged wheel-degree | 0.4846 | Run 4 (ultrasonic Δ vs encoder Δ, low speed) |
| Physical max wheel speed | ~1067 deg/s (~570 mm/s ground) | Run 4/6 cruise |
| Commanded speed (for steering authority) | 1020 deg/s | Run 6 |
| Gyro-hold gain Kc | 18 | tuned, Run 6–8 |
| Brake trigger (avg wheel travel) | 1821° | Run 7 calibration |
| Hard-stop distance (incl. skid) | ~40–56 mm | Run 4/7 |
| Brake-trigger → gap law | gap ≈ 181.5 − (trigger − 1550)×0.4846 mm | Runs 7–8 |
| Sensor offset at the rover's contact point | ~45–51 mm | Run 7 |

---

## 7. If continued

The five runs stopped ~92 mm out with ~30 mm of unused margin. With one operator measurement to anchor the true front-face zero (closing the +26 mm bias), the trigger could be advanced by ~55° to target ~40–50 mm while preserving a safe margin over the measured ±7 mm variability. No-contact would remain the controlling constraint.
