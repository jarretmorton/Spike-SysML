# Maximum-speed wall approach — engineering report

**Platform:** LEGO SPIKE Prime rover, Pybricks firmware
**Task:** drive straight at a wall at maximum speed from ~1000 mm and stop as close as possible without contact
**Date:** 2026-08-06

---

## 1. Headline result

**5 of 5 operation runs stopped with no contact.**

| Metric | Value |
|---|---|
| Contact events | **0 / 5** |
| Best gap | **24 mm** |
| Median gap | **29 mm** |
| Gaps on nominally-healthy runs (3, 4, 5) | 29, 24, 27 mm |
| Gaps on sensor-fault runs (1, 2) | 145, 148 mm |
| Approach speed at trigger | 489–517 mm/s (100% duty throughout) |
| Characterization program runs | **3** |
| Outside-input actions | **1** |

Runs 3–5 landed in a 5 mm band at a mean gap of 26.7 mm. Runs 1 and 2 were degraded by an
intermittent distance-sensor fault that biased the rover to stop ~120 mm short — a safe
failure, but a large loss of closeness.

---

## 2. Per-run results: prediction vs. measurement

Estimates below were committed in chat **before** any operator measurement was disclosed.

| Run | My onboard estimate | Operator measurement | Delta (est − meas) | Trigger source |
|---:|---:|---:|---:|---|
| 1 | 130 mm | **145 mm** | −15 mm | odometry backstop |
| 2 | 132 mm | **148 mm** | −16 mm | odometry backstop |
| 3 | 29 mm | **29 mm** | 0 mm | distance trigger |
| 4 | 29 mm | **24 mm** | +5 mm | distance trigger |
| 5 | 29 mm | **27 mm** | +2 mm | distance trigger |

Mean absolute error across all five: **7.6 mm**.
Mean absolute error on runs 3–5: **2.3 mm**.

### 2.1 Reconciliation of the systematic gap

Three distinct effects account for the deltas.

**(a) Runs 3–5: +2.3 mm mean over-prediction — sensor-to-bumper offset slightly too small.**

The onboard estimate is `gap = B_settled − K`, with `K = 11 mm` derived from the single
calibration measurement (sensor read 89 mm, true gap 78 mm). All three runs settled at
`B = 40`, so all three predicted 29 mm, while true gaps were 29 / 24 / 27 mm (mean 26.7).
Back-solving gives **K ≈ 13.3 mm** rather than 11 mm. This is a one-sample calibration
carrying its own ±2–3 mm of reading and ruler error, so a 2.3 mm bias is exactly the
expected residual. Not a modelling error — a precision limit of spending only one
measurement.

**(b) Runs 3–5: 5 mm of spread despite an identical sensor reading.**

Sensor B reported precisely 40 mm on all three runs (15/15 valid samples each), yet true
gaps spanned 24–29 mm. The sensor cannot resolve better than ~5 mm at this range, so
identical readings map to a 5 mm band of real positions. This sets a floor on achievable
onboard accuracy that no amount of modelling removes.

**(c) Runs 1–2: −15/−16 mm — the right diagnosis, an under-estimated magnitude.**

I correctly identified that sensor B was reading low and that the rover had *not* been
misplaced, and correctly predicted a far stop rather than a graze. But I inferred the
offset from the start-line reading (892 vs. ~1018 healthy ⇒ ~126 mm, rounded to 128 mm),
whereas back-solving from the measurements gives the true bias:

| Run | Reported start | Implied true start | Actual bias |
|---:|---:|---:|---:|
| 1 | 863 | 1005.7 | 142.7 mm |
| 2 | 868 | 1011.4 | 143.4 mm |

The real bias was **~143 mm**, consistent to 0.7 mm between the two runs. Using 128 mm
under-predicted both by ~15 mm. The two independent estimates of the bias (126 mm from the
pre-creep reading, 143 mm from the post-creep reading) differing by 17 mm indicates the
fault is closer to a **~14% scale error** than a fixed offset: `892/1018 = 0.876` and
`863/1005.7 = 0.858`. A proportional model would have predicted runs 1–2 within a few mm.

---

## 3. The rover as characterized

Nothing below was given; all of it was determined on-hub.

| Property | Value | How established |
|---|---|---|
| Port A | Ultrasonic (forward) | type probe |
| Port B | Ultrasonic (forward) — **control sensor** | type probe |
| Port C | Motor (`m0`) | type probe |
| Port D | Motor (`m1`) | type probe |
| Port E | Ultrasonic (rear) | type probe |
| Port F | Colour sensor (36% floor reflectance) | type probe |
| Forward polarity | `f = (−1, +1)` on C/D | paired duty bursts + Δdistance sign |
| Heading sign | `turn_sign = +1` | spin burst vs. differential sign |
| Wheel calibration | **0.489 mm/deg** (56 mm wheel, direct drive) | encoder vs. distance over 900 mm, agrees to 1% |
| Max speed | ~500 mm/s at 100% duty | encoder derivative |
| Post-brake wheel travel | 14.7–16.4 mm | encoder, highly repeatable |
| Total stopping distance S | 51.9 / 52.6 / 65.4 mm | single-channel measurement |
| Floor friction | µ ≈ 0.21–0.36 | from slide distance |
| Sensor update period | ~30 ms | fresh-anchor fraction |

---

## 4. How the stop works

The stop is a fixed-latency, fixed-speed event. Because every approach is at the same
maximum speed, sensor lag, loop period, braking and slide collapse into one empirical
constant `S`, and the control law reduces to:

```
fire the brake when   d_est − S(v) ≤ TARGET
```

Two refinements were required by the hardware.

**Odometry-propagated distance estimate.** The sensor updates only every ~30 ms — 15 mm of
travel at 500 mm/s — and *freezes* unpredictably for 80–125 ms at a time. Rather than
trusting raw readings, the estimator holds an anchor `(d, encoder)` and dead-reckons between
updates:

```
d_est = anchor_d − (encoder_now − anchor_encoder)
```

**Gated re-anchoring.** A new reading is accepted only if it both *changed* and agrees with
dead reckoning within 60 mm. A frozen sensor fails the first test; a multi-path jump fails
the second. In run 3's k1 this rejected a spurious 227 mm spike and correctly re-acquired at
198 mm when dead reckoning had the rover at 217 mm. Across the operation runs, `stale_mm` at
trigger was 0–7.6 mm — the estimator was never coasting far.

The result: the trigger fired at 93.0, 94.1, 94.4 mm on the three healthy runs — a **1.4 mm
spread**. Essentially all remaining error is downstream of the brake command.

---

## 5. Characterization narrative

Three program runs, each driven by a specific unknown.

**Run 1 — discovery.** Probed all six ports, sampled all three ultrasonics, ran paired duty
bursts to resolve drivetrain conventions, then three max-speed approach-and-stop cycles with
self-return. Established the port map and polarity. Two design faults surfaced: the spin test
ran *before* the translation test, leaving the rover 40° off-square so the translation
measurement was taken at an angle, producing a nonsense wheel calibration (0.16 mm/deg) that
propagated a negative stopping distance into later cycles. Using `min(A, B)` as the forward
distance also meant the control rode whichever sensor was misbehaving.

**Run 2 — precision attempt on sensor A.** Hard-coded the geometry, controlled on A alone,
logged at 20 ms through the stop. This produced the key insight, from the invariant
`usA + encoder`, which held constant to **±1.5 mm** through cruise: the odometry and the
distance sensor agree almost perfectly, `mmpd = 0.489` is right, and there is no significant
lag. It also exposed that **sensor A freezes hard at ~290 mm** and never recovers — in all
three cycles.

**Run 3 — single-sensor operation.** Constructing only Port B removed acoustic crosstalk.
The effect was dramatic: B alone read **1006 mm** at the start line, exactly what A read,
proving the apparent "126 mm mounting offset" between the two sensors was never geometric —
it was B mishearing A's pings. With crosstalk gone, `scale_chk` came back 0.98/0.99/1.00 and
S was measured cleanly on a single channel at 51.9 / 52.6 / 65.4 mm.

### 5.1 The instrumentation was the hard part

Almost all difficulty came from the distance sensors, not the control problem:

- **Crosstalk.** Two ultrasonics aimed at one flat wall corrupt each other. Pybricks starts a
  sensor pinging on construction, so merely *constructing* an unused sensor was enough. Fix:
  construct exactly one.
- **Sensor A floor.** Freezes at ~290 mm, permanently, every time.
- **Sensor B stalls.** Holds a stale value for 80–125 ms at specific ranges (~590, ~290,
  ~170 mm), even with A silenced. Handled by the gated estimator rather than by trusting the
  sensor.
- **Close-range multi-path.** Below ~40 mm B returns echoes around 150 mm. The plausibility
  guard (`b_rest < d_fire + 20`) correctly rejected these on runs 1–2.
- **Intermittent ~14% scale fault.** The cause of runs 1–2. Observed in five separate
  readings clustered at 880–894 against four at 1006–1020, same physical placement.

The single most useful technique was cross-checking the sensor against wheel odometry via the
invariant `distance + encoder`, which is constant when both are healthy. Every sensor
pathology above was found that way.

---

## 6. Locked operation program

Flashed unchanged before each of the five runs (the hub is power-cycled between runs, wiping
the program).

```python
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

BUF = []
BUFMAX = 2000

def lg(n, v):
    if len(BUF) < BUFMAX:
        BUF.append((clock.time(), n, float(v)))

def dump():
    global BUF
    b = BUF
    BUF = []
    for i in range(len(b)):
        e = b[i]
        stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%.2f}\n' % (e[0], e[1], e[2]))

MMPD = 0.489      # mm of travel per motor degree
F0 = -1           # forward polarity, motor on port C
F1 = 1            # forward polarity, motor on port D
TS = 1.0          # heading sign convention
KS = 0.090        # S(v) = KS * v
SMIN = 30.0
SMAX = 60.0
TARGET = 50.0     # desired settled sensor reading
FLOOR = 28.0      # dead-reckoned safety floor
KOFF = 11.0       # sensor face -> frontmost point of rover
SNOM = 57.0       # nominal S, used only for the fallback estimate
KP = 1.8
KD = 0.10
CAP = 16.0        # max steering differential, % duty
TOL = 60.0        # anchor acceptance gate

m0 = None
m1 = None
uB = None


def dmm():
    x = uB.distance()
    if x <= 0:
        return -1.0
    return float(x)


def medB(n):
    vals = []
    for i in range(n):
        x = dmm()
        if x > 0:
            vals.append(x)
        wait(20)
    if not vals:
        return -1.0
    vals.sort()
    return vals[len(vals) // 2]


def enc():
    return (F0 * m0.angle() + F1 * m1.angle()) * 0.5 * MMPD


def vel():
    return (F0 * m0.speed() + F1 * m1.speed()) * 0.5 * MMPD


def hd():
    try:
        return hub.imu.heading()
    except Exception:
        return 0.0


def drive(duty, corr):
    d0 = duty + corr
    d1 = duty - corr
    if d0 > 100: d0 = 100
    if d0 < -100: d0 = -100
    if d1 > 100: d1 = 100
    if d1 < -100: d1 = -100
    m0.dc(F0 * d0)
    m1.dc(F1 * d1)


def drive_max(corr):
    # hold the faster wheel at 100% and trim the other, so steering
    # never costs approach speed
    if corr > CAP: corr = CAP
    if corr < -CAP: corr = -CAP
    if corr >= 0:
        d0 = 100.0
        d1 = 100.0 - 2.0 * corr
    else:
        d0 = 100.0 + 2.0 * corr
        d1 = 100.0
    m0.dc(F0 * d0)
    m1.dc(F1 * d1)


def halt():
    m0.brake()
    m1.brake()


def main():
    global m0, m1, uB
    wait(700)
    try:
        hub.imu.reset_heading(0)
    except Exception:
        pass
    try:
        m0 = Motor(Port.C)
        m1 = Motor(Port.D)
        uB = UltrasonicSensor(Port.B)   # ONLY this sensor: avoids crosstalk
    except Exception:
        lg("ABORT_ports", 1)
        return
    try:
        m0.reset_angle(0)
        m1.reset_angle(0)
    except Exception:
        pass

    b0 = medB(9)
    lg("B_startline", b0)
    if b0 < 600 or b0 > 1300:
        lg("ABORT_range", b0)
        return

    # creep test: confirm we are pointed at the wall before going to full speed
    e0 = enc()
    drive(30, 0)
    wait(300)
    halt()
    wait(500)
    b1 = medB(7)
    moved = enc() - e0
    lg("creep_dB", b1 - b0)
    lg("creep_enc", moved)
    if not (b1 > 0 and (b0 - b1) > 8 and moved > 8):
        lg("ABORT_creep", 1)
        return

    e_start = enc()
    d_start = medB(7)
    lg("op_B_start", d_start)
    anchor_d = d_start
    anchor_e = e_start
    last_raw = d_start
    maxmm = d_start - FLOOR
    t0 = clock.time()
    tl1 = 0
    tl2 = 0
    vf = 0.0
    n_loop = 0
    n_fresh = 0
    fired = 0
    reason = 0
    d_fire = 0.0
    raw_fire = 0.0
    e_fire = 0.0
    v_fire = 0.0
    stale_mm = 0.0
    hp = hd()
    tp = t0
    while True:
        t = clock.time()
        if t - t0 > 6000:
            reason = 3
            break
        raw = dmm()
        ee = enc()
        d_est = anchor_d - (ee - anchor_e)
        n_loop += 1
        # re-anchor only on a reading that both changed and agrees with odometry
        if raw > 0 and raw != last_raw and abs(raw - d_est) < TOL:
            anchor_d = raw
            anchor_e = ee
            last_raw = raw
            d_est = raw
            n_fresh += 1
        v = vel()
        vf = 0.7 * vf + 0.3 * v
        per = 60
        if d_est < 700:
            per = 20
        if t - tl1 >= per:
            if raw > 0:
                lg("usB", raw)
            lg("enc_mm", ee - e_start)
            lg("est_mm", d_est)
            tl1 = t
        h = hd()
        if t - tl2 >= 100:
            lg("head_deg", h)
            tl2 = t
        if (ee - e_start) > maxmm:
            reason = 2
            break
        if d_est <= FLOOR:
            reason = 1
            break
        s = KS * vf
        if s < SMIN: s = SMIN
        if s > SMAX: s = SMAX
        if d_est - s <= TARGET:
            fired = 1
            d_fire = d_est
            raw_fire = last_raw
            e_fire = ee
            v_fire = vf
            stale_mm = ee - anchor_e
            break
        dt = t - tp
        hdot = 0.0
        if dt >= 25:
            hdot = (h - hp) * 1000.0 / dt
            hp = h
            tp = t
        drive_max(-(KP * h + KD * hdot) * TS)
        wait(4)
    halt()
    t_stop = clock.time()
    if not fired:
        d_fire = anchor_d - (enc() - anchor_e)
        raw_fire = last_raw
        e_fire = enc()
        v_fire = vf
        stale_mm = enc() - anchor_e
    while clock.time() - t_stop < 900:
        r = dmm()
        if r > 0:
            lg("usB", r)
        lg("enc_mm", enc() - e_start)
        wait(40)
    e_rest = enc()

    vals = []
    for i in range(15):
        x = dmm()
        if x > 0:
            vals.append(x)
        wait(20)
    nv = len(vals)
    if nv > 0:
        vals.sort()
        b_rest = vals[nv // 2]
    else:
        b_rest = -1.0

    lg("op_fired", fired)
    lg("op_reason", reason)
    lg("op_B_fire_est", d_fire)
    lg("op_B_fire_raw", raw_fire)
    lg("op_stale_mm", stale_mm)
    lg("op_v_fire", v_fire)
    lg("op_B_rest", b_rest)
    lg("op_n_valid", nv)
    lg("op_enc_after", e_rest - e_fire)
    lg("op_head_end", hd())
    lg("op_freshfrac", 100.0 * n_fresh / n_loop)
    tot = e_rest - e_start
    if tot > 200:
        lg("op_enc_total", tot)

    fb = d_fire - SNOM - KOFF
    lg("op_gap_fallback", fb)
    if b_rest > 0 and b_rest < d_fire + 20:
        lg("op_S_true", d_fire - b_rest)
        lg("op_gap_est", b_rest - KOFF)
    else:
        lg("op_S_true", -1.0)
        lg("op_gap_est", fb)
    dump()


try:
    main()
except Exception as ex:
    lg("EXC", 1)
finally:
    try:
        m0.stop()
        m1.stop()
    except Exception:
        pass
    dump()
    stdout.write('{"event":"end"}\n')
```

---

## 7. Raw operation telemetry

| Run | Start reading | Fired | Est. at trigger | Settled B | S | Encoder total | Heading at stop |
|---:|---:|:--|---:|---:|---:|---:|---:|
| 1 | 863 | no (backstop) | 97.6 | 147 *(rejected)* | — | 852.3 | −2.2° |
| 2 | 868 | no (backstop) | 106.9 | 151 *(rejected)* | — | 855.0 | −5.0° |
| 3 | 992 | yes | 94.4 | 40 | 54.4 | 956.5 | −8.2° |
| 4 | 990 | yes | 94.1 | 40 | 54.1 | 953.8 | −9.4° |
| 5 | 993 | yes | 93.0 | 40 | 53.0 | 953.6 | −8.1° |

---

## 8. Assessment and improvements

### What worked

- Treating the stop as one empirical constant `S` measured end-to-end on a single channel,
  rather than modelling lag and braking separately. This absorbed the unmeasurable slide.
- Cross-checking the sensor against odometry. Every sensor fault was found this way.
- The gated estimator. It survived stalls of up to 125 ms and a 57 mm spurious spike without
  a single bad trigger, in every run including the two faulted ones.
- Trimming only the faster wheel, so heading hold never cost approach speed.
- The plausibility guard on the settled reading, which stopped runs 1–2 from reporting
  confidently wrong gaps.

### What I would change

1. **Tighten the start-of-run sanity gate.** The range check was `600 < b0 < 1300`, which
   happily accepted 892 when the expected value was ~1018. A gate of `950 < b0 < 1100`,
   with a re-read and retry on failure, would have caught the fault on runs 1–2 before
   committing to it. This is the single highest-value fix: it is worth ~120 mm on 40% of runs.
2. **Derive the odometry backstop from a validated datum.** `maxmm = d_start − FLOOR` inherits
   any error in `d_start`, which is exactly how a low reading turned into an early stop.
3. **Replace `brake()` with a controlled deceleration below the friction limit.** The wheels
   currently lock in ~60 ms and the rover slides for another ~180 ms; that slide varied 35–51 mm
   in characterization and is the dominant remaining error. Decelerating at ~0.18 g would keep
   the wheels rolling for a nearly identical total distance but a far more repeatable one,
   which would allow a materially tighter target.
4. **Spend a second calibration measurement.** `K = 11 mm` from one reading carried a ~2.3 mm
   bias. Two measurements at different distances would also separate offset from scale error.
5. **Model the sensor fault proportionally.** The bias is ~14% of range, not a fixed offset;
   this was visible in the data and would have improved the runs 1–2 predictions from −15 mm
   to within a few mm.

### Honest accounting

The chosen target left deliberate margin. With `S` known to ±7 mm and a stochastic slide, I
sized `TARGET = 50` for zero contact rather than chasing a sub-10 mm gap, on the reasoning
that a contact voids a run entirely while an extra 15 mm of clearance costs only closeness.
Runs 3–5 landed at 24–29 mm, close to that design intent. Given the measured spread, a target
of ~35 mm would likely have produced gaps near 12–17 mm still without contact — that margin
was the price of only three characterization runs on badly-behaved instrumentation.

### Scores

| Score | Result |
|---|---|
| Characterization program runs | **3** |
| Outside-input actions | **1** (one gap measurement) |
| Operation runs with no contact | **5 / 5** |
| Closeness | 24, 27, 29 mm (healthy runs); 145, 148 mm (sensor-fault runs) |

Four flash attempts failed to deploy before the first successful run (BLE connection
timeouts, `hub_id: null`); no program executed on those, so they are not counted as runs.
Requests to wake and power-cycle the hub are hardware operation, not outside input.
