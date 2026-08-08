# Maximum-Speed Wall Approach — Final Engineering Report

LEGO SPIKE Prime rover, Pybricks firmware. Task: drive straight at a wall at maximum
speed from ~1000 mm and stop as close as possible without contact.

---

## 1. Result

**5 of 5 operation runs stopped with no contact.**

| Metric | Value |
|---|---|
| Runs with no contact | **5 / 5** |
| Mean measured gap | **28.8 mm** |
| Best run | **19 mm** |
| Worst run | 35 mm |
| Run-to-run spread (σ) | 6.7 mm |
| Approach speed at brake | 424–458 mm/s (full motor duty) |
| Heading error at brake | ≤ 0.1° on every run |
| Trigger source | Normal fused trigger on all five (abort code 0) — no safety backstop ever fired |

## 2. Scores

| Score | Value |
|---|---|
| Characterization program runs | **4** |
| Outside-input actions | **1** (one ground-truth gap measurement) |
| Operation runs with no contact | **5 / 5** |
| Closeness | mean 28.8 mm, best 19 mm |

---

## 3. Discovered rover configuration

Nothing about the wiring or drive convention was given; all of it was determined in
characterization run 1.

| Port | Device | Role |
|---|---|---|
| A | UltrasonicSensor | Forward — **the only sensor used in the locked program** |
| B | UltrasonicSensor | Forward, second unit — deliberately left unconstructed |
| C | Motor | Drive, commanded **negative** toward the wall |
| D | Motor | Drive, commanded **positive** toward the wall |
| E | UltrasonicSensor | Rear (read 2000 mm at the start line — open space) |
| F | ColorSensor | Downward, unused |

The drivetrain is **mirrored**: commanding both motors the same sign produced a −60.9°
rotation, not translation. The translating configuration then showed distance
*increasing*, which fixed the toward-wall convention as `C:−v, D:+v`.

Motor rated ceiling is 1000 deg/s; at full duty the rover achieved ~870–890 deg/s,
i.e. **the speed controller was saturated** — the single most consequential discovery
of the exercise (see §5).

---

## 4. Control architecture

Four ideas do the work.

**1. Full duty, steered by IMU.** Because `run()` saturates at full speed, speed
regulation silently switches off and the natural ~9% mismatch between the two motors
goes uncorrected. The locked program therefore uses `dc(±100)` — true maximum duty —
and closes a PID loop on hub heading that *trims only the inner wheel*:

```
u    = Kp·θ + Ki·∫θ + Kd·θ̇
dutyC = −100 + u   (clamped ±100)
dutyD = +100 + u   (clamped ±100)
```

At zero heading error both sides sit at 100%, so no speed is sacrificed. Clamping means
correction can only ever subtract from the inside wheel — exactly the right structure.

**2. Sensor/odometry fusion.** The ultrasonic updates at only 31–41 Hz, lags reality by
tens of milliseconds, and intermittently freezes or drops out entirely. Every *fresh*
reading becomes an anchor, lag-corrected by `v·τ`, and between updates the estimate is
carried forward on wheel odometry:

```
on a new reading:  anchor_d = pred + α·((d_raw − v·τ) − pred);  anchor_e = epos
every loop:        d_true   = anchor_d − (epos − anchor_e)·MMPD
```

**3. Asymmetric outlier gate.** A spuriously *high* reading near the wall is the one
error that causes contact, so a candidate may sit at most +25 mm above the odometry
prediction but up to −70 mm below. A low reading brakes early — the safe direction.

**4. Speed-adaptive trigger.** Braking distance is computed from the *live measured*
speed, so battery droop shortens the trigger distance automatically instead of running
the rover long:

```
brake when   d_true − ( v²/(2·A_DEC) + v·T_LAT )  ≤  TARGET
```

---

## 5. Characterization log — 4 runs

### Run 1 — discovery
One program that scanned all six ports, pulsed the motors to resolve the drivetrain
convention from IMU rotation, identified the forward sensor pair by which readings moved
together, then made a full-speed braking test. Yielded the port map, drive signs,
mm-per-degree, sensor update rate, sensor lag (47 ms by a two-speed offset method), and
braking distance.

It also exposed two failure modes that would have wrecked the operation:

- **Heading collapse at full speed.** Heading held within ±1° for the entire regulated
  300 deg/s phase, then drifted **−18° in one second** the instant full speed was
  commanded. Diagnosis: controller saturation, as above. At −19° the two forward sensors
  disagreed by 142 mm and the rover's nearest corner was no longer knowable.
- **Cross-talk.** Port B froze at 588 mm for 190 ms then jumped 104 mm; both sensors
  threw sporadic 2000 mm dropouts. Two ultrasonics pinging one flat wall hear each
  other's echoes. Fixed by never constructing port B.

### Run 2 — failed, `MemoryError`
The telemetry log was a Python list appended at 200 Hz; its backing array reallocation
failed mid-run. The physical run was unaffected (the `finally` block braked the motors)
but all analysis was lost. Fixed with a **preallocated** buffer, 50 Hz logging decimated
from a 200 Hz control loop, and fewer fields per sample — ~20 KB instead of ~115 KB.

### Run 3 — heading control validated
Heading **0.0° at the trigger**. Two further findings:

- A **bogus 939 mm reading** passed the validity window, became an anchor, and threw the
  estimate 110 mm too far for 200 ms. It also silently corrupted the on-hub
  mm-per-degree calculation, producing a bogus 0.608 that the clean spans put at ~0.49.
  This motivated the asymmetric gate.
- The stopping model was badly pessimistic: predicted 46 mm, actual **14 mm**.

Sensor-to-bumper offset was calibrated here against the single operator measurement:
sensor read 174.05 mm, measured gap 151 mm → **offset 23.0 mm**. This agreed to within
2.5 mm with an independent inference from the start line (1025.55 mm read at a ~1000 mm
line), which is why it was trusted.

### Run 4 — locked program validated
Predicted final 46.5 mm, actual **46.0 mm — a 0.5 mm model error**. Estimated true gap
23 mm, closest approach 17 mm, no contact. Locked without further edits.

---

## 6. Measured constants

| Constant | Value | How obtained |
|---|---|---|
| mm per motor degree | 0.49 | Clean straight cruise spans, runs 3–4 |
| Sensor lag τ | 47 ms measured; 35 ms used for fresh readings | Two-speed offset method |
| Sensor update rate | 31–41 Hz | Value-change counting during cruise |
| Sensor minimum range | ~40 mm | Observed floor across all runs |
| Control loop rate | 168–176 Hz | Measured on-hub |
| Stopping distance | 13–21 mm from ~445 mm/s | Trigger-to-rest, all runs |
| Braking split | ~3 mm wheel rotation, ~13 mm skid | Encoder vs ultrasonic delta |
| Braking yaw | −4.0° to −6.9° | Heading at rest vs at trigger |
| Sensor-to-bumper offset | 23.0 mm (single-point) | Operator measurement, run 3 |

Note the braking is **~80% skid**. Deceleration is roughly 0.7 g, which is why the stop
is so short — and also why it is the least predictable term in the model.

---

## 7. Operation results

Onboard estimates were frozen and committed in chat before any measurement was
requested. Channel: resting port-A reading (mean of last 20 samples at rest) minus the
23.0 mm offset.

| Run | Sensor at rest | **My estimate** | **Measured** | **Delta (est − meas)** | Contact |
|---|---|---|---|---|---|
| 1 | 51.0 mm | 28 mm | 33 mm | −5 mm | none |
| 2 | 41 mm † | 18 mm | 19 mm | −1 mm | none |
| 3 | 51.0 mm | 28 mm | 32 mm | −4 mm | none |
| 4 | 48.0 mm | 25 mm | 25 mm | **0 mm** | none |
| 5 | 51.0 mm | 28 mm | 35 mm | −7 mm | none |
| | **mean** | **25.4 mm** | **28.8 mm** | **−3.4 mm** | **0 / 5** |

† Run 2's resting readings fell below the program's own 45 mm validity floor, so
`final_valid_n` returned zero and the value was recovered from the raw trace, where it
held steady at 41 mm for 500 ms. The encoder corroborated it independently
(`final_epos` 1988 vs 1982 in validation). This was flagged as the least-trusted
estimate *before* ground truth was seen; it turned out to be the most accurate one.

**Per-run diagnostics**

| Run | v at brake | Predicted stop | Actual stop | Heading at brake | Yaw during braking |
|---|---|---|---|---|---|
| 1 | 424 mm/s | 14.8 mm | 13.4 mm | 0.0° | −5.0° |
| 2 | 446 mm/s | 16.3 mm | 20.8 mm | 0.1° | −4.0° |
| 3 | 457 mm/s | 17.0 mm | 15.7 mm | 0.0° | −6.9° |
| 4 | 432 mm/s | 15.4 mm | 15.8 mm | −0.1° | −6.0° |
| 5 | 458 mm/s | 17.1 mm | 14.8 mm | 0.0° | −4.2° |

---

## 8. Reconciliation of the systematic gap

Every estimate was low, by a mean of **−3.4 mm**, with residual scatter of only
**2.9 mm** once the bias is removed. The bias is systematic and explainable.

The 23.0 mm sensor-to-bumper offset was calibrated at a **single point, 174 mm**. A
single point cannot separate a fixed offset from a scale error. With the operation data
at ~48 mm, there are now two widely separated points, and they imply the sensor reads
about **2.8% long** on top of a smaller fixed standoff:

```
R = 1.028 · G + 18.8        (R = sensor reading, G = true bumper gap)
G = (R − 18.8) / 1.028
```

- Calibration point: R = 174.05 → G = 151.0 ✓ (measured 151)
- Operation mean:    R = 48.4  → G = 28.8  ✓ (measured 28.8)

A ~2.8% scale error is consistent with a speed-of-sound calibration mismatch, which is
temperature dependent. Under the single-point model the true offset near 50 mm is ~19 mm
rather than 23 mm, which is precisely the −3.4 mm bias observed.

Re-deriving the per-run estimates with the two-point model:

| Run | Corrected estimate | Measured | Residual |
|---|---|---|---|
| 1 | 31.3 mm | 33 mm | −1.7 mm |
| 2 | 21.6 mm | 19 mm | +2.6 mm |
| 3 | 31.3 mm | 32 mm | −0.7 mm |
| 4 | 28.4 mm | 25 mm | +3.4 mm |
| 5 | 31.3 mm | 35 mm | −3.7 mm |
| | | **mean residual** | **≈ 0.0 mm** |

Residual σ ≈ 3.0 mm, which is about what sensor quantization (±1 mm plus a few mm of
noise) and hand measurement together would produce. **This two-point model is fitted to
these data and is descriptive, not independently validated** — it explains the bias but
has not been tested on a fresh run.

The measurement itself is the authoritative figure; the estimate is the prediction being
checked. The estimator ranked the runs correctly (its lowest estimate was the lowest
measurement, and run 4 landed exactly), so the error is a calibration offset, not a
failure of the sensing chain.

---

## 9. Limitations and what I would change

**Fix first — the validity floor.** `d >= 45` is above the operating point. It discarded
perfectly good 40–44 mm readings on runs 2 and 4, zeroed `final_valid_n`, and inflated
`n_bad` and `stale_max` into false alarms. Lower it to ~35 mm. This is a reporting bug
only; it never touched control, because the brake fires at a raw reading near 85–91 mm.

**Fix second — the forced re-acquire.** After 250 ms without an accepted reading the gate
is bypassed entirely, which is what let the +72 mm jump through at t = 593 ms in the
validation run. It should apply a *relaxed* gate (say ±100 mm) rather than none. It only
ever bit in the far field and recovered well before the trigger, but the failure mode is
the dangerous one.

**Calibrate at two distances.** One measurement at 174 mm could not separate offset from
scale. A second at ~50 mm would have removed the entire −3.4 mm bias — at the cost of a
second outside-input action.

**Consider `brake()` over `hold()`.** The hold servo lunges past its stopping point and
then retracts 6–8 mm, so the resting gap is systematically larger than the closest
approach. `brake()` would make the resting position *be* the closest position and could
score several mm better for the same contact risk. It was not adopted because its
stopping distance was never measured, and swapping an unmeasured term into five scored
runs was not worth the gain.

**Room to go closer.** The closest any run came was ~20 mm, and the trigger never once
needed a safety backstop. With the corrected offset and a lowered validity floor, a
target ~8 mm tighter looks defensible. It was not attempted here because 80% of the
stopping distance is friction-dependent skid and only one sample existed at the
operating point when the program was locked — five clean stops at 29 mm beat four clean
stops at 20 mm.

**Consistent environmental artifact.** Every single run showed ultrasonic dropouts in the
500–1000 mm band and clean data below 800 mm. This is reproducible enough to be a fixed
feature of the setup rather than random noise, and it is the reason odometry fusion was
necessary rather than merely nice.

---

## Appendix A — The locked program

Run unchanged for all five operation runs.

```python
import gc
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

def emit(s, v):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n' % (clock.time(), s, v))

MMPD = 0.49
TAU = 0.035
A_DEC = 7300.0
T_LAT = 0.006
TARGET = 50.0
OFFSET = 23.0
RAWSTOP = 62
ALPHA = 0.6
GATE_HI = 25.0
GATE_LO = -70.0
KP = 4.0
KI = 8.0
KD = 0.3
UI_MAX = 25.0
BASE = 100
NMAX = 300
LOGEVERY = 4

mC = Motor(Port.C)
mD = Motor(Port.D)
us = UltrasonicSensor(Port.A)

LOG = [None] * NMAX
n = 0
trig = -1
abort = 0
t_trig = 0
d_trig = 0.0
v_trig = 0.0
sd_trig = 0.0

try:
    wait(400)
    sacc = 0.0
    cacc = 0
    for i in range(20):
        d = us.distance()
        if d >= 45 and d <= 1900:
            sacc += d
            cacc += 1
        wait(15)
    d_start = sacc / cacc if cacc > 0 else 1000.0
    emit("start_d_rest", d_start)
    emit("start_valid_n", cacc)

    mC.reset_angle(0)
    mD.reset_angle(0)
    h0 = hub.imu.heading()
    gc.collect()

    HN = 6
    ht = [0] * HN
    he = [0.0] * HN
    hh = [0.0] * HN

    anchor_d = d_start
    anchor_e = 0.0
    last_raw = -1
    t_valid = 0
    t_accept = 0
    n_bad = 0
    n_rej = 0
    stale_max = 0
    k = 0
    I = 0.0
    t_prev = 0
    th_max = 0.0
    v_max = 0.0
    phase = 0
    min_dt = 9999.0
    min_raw = 9999

    t0 = clock.time()
    mC.dc(-BASE)
    mD.dc(BASE)

    while True:
        t = clock.time() - t0
        aC = mC.angle()
        aD = mD.angle()
        epos = (aD - aC) * 0.5
        th = hub.imu.heading() - h0

        idx = k % HN
        ot = ht[idx]
        oe = he[idx]
        oh = hh[idx]
        dtw = t - ot
        if dtw > 0:
            v = (epos - oe) * MMPD * 1000.0 / dtw
            om = (th - oh) * 1000.0 / dtw
        else:
            v = 0.0
            om = 0.0
        ht[idx] = t
        he[idx] = epos
        hh[idx] = th
        if v < 0:
            v = 0.0
        if v > v_max:
            v_max = v

        pred = anchor_d - (epos - anchor_e) * MMPD
        d = us.distance()
        if d >= 45 and d <= 1900:
            t_valid = t
            if d != last_raw:
                last_raw = d
                cand = d - v * TAU
                diff = cand - pred
                ghi = 60.0 if t < 500 else GATE_HI
                if (diff <= ghi and diff >= GATE_LO) or (t - t_accept) > 250:
                    anchor_d = pred + ALPHA * diff
                    anchor_e = epos
                    t_accept = t
                else:
                    n_rej += 1
        else:
            n_bad += 1
        st = t - t_valid
        if st > stale_max:
            stale_max = st

        dtrue = anchor_d - (epos - anchor_e) * MMPD
        if dtrue < min_dt:
            min_dt = dtrue
        if d >= 45 and d <= 1900 and d < min_raw:
            min_raw = d

        ath = th if th > 0 else -th
        if ath > th_max:
            th_max = ath

        if k % LOGEVERY == 0 and n < NMAX:
            LOG[n] = (t, d, int(dtrue * 10), int(epos), int(th * 10))
            n += 1
        k += 1

        if phase == 0:
            ddt = t - t_prev
            t_prev = t
            if ddt > 0 and ddt < 60:
                I += th * ddt * 0.001
            ui = KI * I
            if ui > UI_MAX:
                ui = UI_MAX
                I = UI_MAX / KI
            if ui < -UI_MAX:
                ui = -UI_MAX
                I = -UI_MAX / KI
            u = KP * th + ui + KD * om
            if u > 60:
                u = 60
            if u < -60:
                u = -60
            cC = -BASE + u
            cD = BASE + u
            if cC > 100:
                cC = 100
            if cC < -100:
                cC = -100
            if cD > 100:
                cD = 100
            if cD < -100:
                cD = -100
            mC.dc(cC)
            mD.dc(cD)

            sd = v * v / (2.0 * A_DEC) + v * T_LAT
            fire = 0
            if (dtrue - sd) <= TARGET:
                fire = 1
            if d >= 45 and d <= RAWSTOP:
                fire = 1
                abort = 6
            if (t - t_accept) > 300 and dtrue < 300:
                fire = 1
                abort = 4
            if th_max > 12:
                fire = 1
                abort = 2
            if t > 6000:
                fire = 1
                abort = 3
            if t > 500 and dtrue > d_start + 80:
                fire = 1
                abort = 5
            if fire:
                mC.hold()
                mD.hold()
                trig = n - 1
                t_trig = t
                d_trig = dtrue
                v_trig = v
                sd_trig = sd
                phase = 1
        else:
            if t - t_trig > 900:
                break
        wait(5)

    emit("abort_code", abort)
    emit("n_log", n)
    emit("ctrl_hz", k * 1000.0 / LOG[n - 1][0])

    fin = 20 if n > 20 else n
    sacc = 0.0
    cacc = 0
    for i in range(n - fin, n):
        dv = LOG[i][1]
        if dv >= 45 and dv <= 1900:
            sacc += dv
            cacc += 1
    d_final = sacc / cacc if cacc > 0 else -1.0
    emit("final_d_rest", d_final)
    emit("final_valid_n", cacc)
    emit("EST_TRUE_GAP", d_final - OFFSET)
    emit("min_dtrue", min_dt)
    emit("min_raw", min_raw)
    emit("min_true_gap", min_raw - OFFSET)
    emit("final_epos", LOG[n - 1][3])
    emit("final_heading", LOG[n - 1][4] / 10.0)
    emit("th_max", th_max)
    emit("v_max_mms", v_max)
    emit("n_bad", n_bad)
    emit("n_rej", n_rej)
    emit("stale_max_ms", stale_max)

    if trig > 0:
        emit("t_trig_ms", t_trig)
        emit("d_true_at_trig", d_trig)
        emit("v_at_trig", v_trig)
        emit("sd_pred_mm", sd_trig)
        emit("d_raw_at_trig", LOG[trig][1])
        emit("th_at_trig", LOG[trig][4] / 10.0)
        emit("brake_enc_mm", (LOG[n - 1][3] - LOG[trig][3]) * MMPD)
        if d_final > 0:
            emit("actual_stop_mm", d_trig - d_final)
            emit("target_err_mm", d_final - TARGET)

    gc.collect()
    for i in range(n):
        r = LOG[i]
        near = trig >= 0 and i >= trig - 2 and r[0] <= t_trig + 400
        if near or i % 3 == 0:
            stdout.write('{"timestamp_ms":%d,"sensor":"raw_mm","value":%f}\n' % (r[0], r[1]))
            stdout.write('{"timestamp_ms":%d,"sensor":"dtrue_mm","value":%f}\n' % (r[0], r[2] / 10.0))
            stdout.write('{"timestamp_ms":%d,"sensor":"heading_deg","value":%f}\n' % (r[0], r[4] / 10.0))
            stdout.write('{"timestamp_ms":%d,"sensor":"enc_deg","value":%f}\n' % (r[0], r[3]))

except Exception as e:
    emit("exception", 1)
    stdout.write("ERR %s\n" % repr(e))
finally:
    try:
        mC.brake()
        mD.brake()
    except Exception:
        pass
    stdout.write('{"event":"end"}\n')
```

### Safety backstops (none fired in any operation run)

| Code | Condition | Purpose |
|---|---|---|
| 6 | raw reading ≤ 62 mm | Hard floor if the estimator diverges |
| 4 | no accepted anchor for 300 ms while below 300 mm | Blind near the wall |
| 2 | \|heading\| > 12° | Steering failure |
| 5 | distance increasing past start + 80 mm | Wrong drive direction |
| 3 | elapsed > 6000 ms | Runaway |
