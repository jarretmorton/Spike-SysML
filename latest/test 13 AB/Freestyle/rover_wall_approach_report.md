# SPIKE Prime rover — maximum-speed wall approach

**Engineering report — Phase 1 characterisation and Phase 2 operation**
Date: 28 July 2026 · Hub: Pybricks Hub (SPIKE Prime, Pybricks firmware)

---

## 1. Result

Five operation runs at maximum speed from a ~1000 mm start line.

| Metric | Result |
|---|---|
| Runs completing a full stop with **no contact** | **5 / 5** |
| Mean final gap (operator-measured) | **5.2 mm** |
| Best run | **1.0 mm** |
| Worst run | 9.0 mm |
| Spread (sd) | 3.35 mm |
| Characterisation program runs | **4** |
| Outside-input actions during characterisation | **0** |

Approach speed was 433–459 mm/s (`dc(100)` on both motors — full duty, no speed
governor), with no deceleration before the braking command.

The mission objective was met. My *prediction* of where the rover stopped was not:
it was optimistic by 8.1 mm on average, and carried no usable per-run resolution.
Section 6 treats that as the primary finding of this report, because the true
safety margin on run 5 was 1 mm rather than the ~15 mm the design assumed.

---

## 2. Rover characterisation

Nothing about the rover was given; all of the following was determined onboard.

| Property | Value | How determined |
|---|---|---|
| Port A | Ultrasonic (primary forward) | try/except device probe |
| Port B | Ultrasonic (forward, unused) | probe |
| Port C | Motor (left of pair) | probe |
| Port D | Motor | probe |
| Port E | Ultrasonic (rear) | probe |
| Port F | Colour sensor (unused) | probe |
| Drivetrain | **Mirrored** — straight line needs opposite signs | both-positive command produced −73° and −60.5° rotations |
| Forward direction | MOT[C] negative, MOT[D] positive | straight probe: +46 mm away, then −50 mm toward |
| Steering sign | HS = +1 | asymmetric drive, +7.73° heading response |
| Encoder scale (cruise) | **0.492 mm/deg** | sensor-A travel ÷ encoder degrees at constant speed |
| Braking distance | **~12 mm** (11.6–14.0) | encoder travel from brake command to rest |
| Sensor lag bias | 21–40 mm, speed-dependent | wall estimate minus lag-free stationary reading |
| Sensor A zero point | reads gap **+3 mm** (assumed) / **+8.7 mm** (correct) | touch-off; see §6 |
| Sensor A floor | 40 mm — unusable below ~55 mm true gap | stepped calibration to contact |
| Sensor B | Unreliable below ~500 mm — **excluded** | read 180 mm where truth was 136 mm |
| Battery | 7280 → 7239 mV across the session | `hub.battery.voltage()` |

### Self-calibration without operator input

The zero point of the distance sensor — what it reads when the gap is truly zero —
is the single constant that decides how close the rover can safely stop. Rather than
request a ground-truth measurement, the rover **measured it itself**: it crept the
last stretch at ~34 mm/s under closed-loop stall detection, made deliberate light
contact, and took the contact encoder angle from 90 ms *before* stall was detected
so the reference is biased short rather than long. This is why the outside-input
score is zero.

---

## 3. Method

The approach is a hybrid estimator. The ultrasonic sensor is accurate but slow and
coarse; the encoder is fast and fine but has no absolute reference. So:

1. Every **fresh** sensor-A reading anchors the wall's position in *encoder* space:
   `wall = gap + travel`. An EMA (alpha 0.30) with +/-90 mm outlier rejection smooths
   it. Typically 64–77 fixes per run.
2. Fixes continue until only 45 mm before the trigger, so dead-reckoning spans a
   short distance and scale error cannot accumulate.
3. The final 45 mm runs in a **tight encoder-only loop**, giving ~1 mm trigger
   resolution instead of the ~4 mm the 10 ms main loop would allow.
4. `brake()` on both motors.

Heading is held by a proportional trim on the IMU. The initial gain (2.2) left a
2.4° steady-state droop — a time constant of 2.1 s against a 2 s dash. Raising it
to 8.0 cut cruise yaw to 0.8–1.9°.

Telemetry is buffered in RAM during motion and flushed afterwards, so BLE writes
never stall the control loop. Computed constants are emitted as they are derived,
so they survive a truncated stream.

### Deliberately not done

A post-stop creep would trivially have produced a sub-millimetre gap. It was
rejected: the task requires the rover to *come to a complete stop* from maximum
speed, and sneaking forward afterwards defeats the point of the exercise. Every
number here is a single full-speed approach terminated by one braking command.

---

## 4. Phase 1 — characterisation runs (score: 4)

| Run | Purpose | Outcome |
|---|---|---|
| 1 | Full self-discovery | **Aborted.** Direction probe drove both motors positive; mirrored drivetrain spun 73°, sensors lost the wall, gate caught it. Yielded the port map and the mirrored-drivetrain fact. |
| 2 | Spin-free discovery | **Aborted.** My own error: deleting the spin probe also deleted the line setting `G2 = -1`, so the defaults spun the rover again. Yielded confirmation that both-positive spins negative — later reused to build the recovery turn. |
| 3 | Full characterisation | **Success, 53 s.** Direction, steering sign, 15-point stepped calibration, touch-off, three full-speed dashes. All constants derived. |
| 4 | Operation candidate, 3-point trigger sweep | **Success.** Measured the trigger-to-stop offset C at three points; stopped at 115 / 59 / 45 mm, no contact. |

Two runs were lost to the same class of error: a program that could not *recover*
from an unexpected drivetrain response. Run 3 fixed this properly with `face_zero()`
— a closed-loop in-place turn back to heading zero — and a retry loop that was
simulated against all four possible drivetrain configurations before flashing.
It converged in 2 attempts on the real hardware.

---

## 5. Phase 2 — operation results

Locked program, trigger = 60.0, run unchanged five times.

| Run | My onboard estimate | Operator measurement | Delta (mine − measured) |
|---:|---:|---:|---:|
| 1 | 18.97 mm | 3.0 mm | **+15.97** |
| 2 | 13.56 mm | 5.0 mm | **+8.56** |
| 3 | 11.24 mm | 8.0 mm | **+3.24** |
| 4 | 7.04 mm | 9.0 mm | **−1.96** |
| 5 | 15.49 mm | 1.0 mm | **+14.49** |
| **Mean** | **13.26 mm** | **5.20 mm** | **+8.06** |
| **sd** | 4.48 mm | 3.35 mm | 7.55 |

Supporting telemetry, all five runs `abort=0`:

| Run | Lag bias | Cruise speed | Braking travel | Max yaw | Start position |
|---|---|---|---|---|---|
| 1 | 28.84 mm | 458.8 mm/s | 13.28 mm | 1.25° | 1018.3 mm |
| 2 | 29.91 mm | 433.0 mm/s | 14.02 mm | 1.11° | 1015.1 mm |
| 3 | 30.20 mm | 457.6 mm/s | 13.04 mm | 0.78° | 1013.1 mm |
| 4 | 39.69 mm | 454.6 mm/s | 12.55 mm | 1.25° | 1015.3 mm |
| 5 | 36.25 mm | 446.7 mm/s | 11.81 mm | 1.87° | 1011.6 mm |

### Interruptions

Two events interrupted the set; neither consumed a scored attempt.

- **Flash timeout** before run 4 — `deployed: false`, nothing written to the hub.
  A BLE connection failure, resolved by waking the hub.
- **Two `abort_code 7` refusals** — the start-position gate found sensor A reading
  817.6 mm and then 833.4 mm against an expected ~1016 mm, and refused to release
  the motors. The rear sensor simultaneously changed from 2000 mm (clear) to
  ~555 mm, indicating the surroundings had changed, not just the rover's placement.
  After a reset the start position returned to 1017.9 mm and the run proceeded.
  **The rover did not move on either refusal.** This gate did exactly what it was
  built for.

---

## 6. Reconciliation — why my estimates were wrong

Before seeing the measurements I committed to two predictions. Both failed.

**Prediction 1: "your measurements should run below mine by roughly 2–4 mm."**
Direction correct, magnitude wrong by a factor of two to four. The actual mean bias
was **+8.06 mm**.

**Prediction 2: "the ordering will be 4 < 3 < 2 < 5 < 1, tightest to widest."**
The actual ordering was 5 < 1 < 2 < 3 < 4 — very nearly the reverse. The correlation
between my per-run estimate and truth is **r = −0.854**. With n = 5 that is not
statistically significant (t = −2.85, p ≈ 0.07), so I will not claim my estimator is
reliably *anti*-correlated. What I can say is that it demonstrated **no per-run
resolving power whatsoever**. Its run-to-run variation was noise.

### Root cause of the +8 mm bias: two length scales, mixed

The encoder-to-millimetre scale was measured two ways and they disagreed by ~6%:

- **Stepped calibration**, gentle motion: 0.515–0.532 mm/deg
- **Cruise**, measured during the dashes: 0.490–0.496 mm/deg

I diagnosed the cause correctly during characterisation — each of the 15 calibration
steps ends in a brake, and a few mm of skid per step inflates the apparent scale —
and I correctly used the cruise value (0.492) for dead-reckoning in the dash. **But I
derived the sensor's zero-point offset from the stepped-calibration fit, which used
the inflated scale.** That gave OFA = 3.0 mm.

Recomputing the near-wall calibration points with the cruise scale:

| Encoder deg to contact | True gap @ 0.492 | Sensor A read | Error |
|---|---|---|---|
| 298 | 146.6 mm | 163.8 | +17.2 |
| 214 | 105.3 mm | 114.0 | +8.7 |
| 177.5 | 87.3 mm | 95.0 | +7.7 |
| 142.5 | 70.1 mm | 78.0 | +7.9 |
| 105 | 51.7 mm | 62.0 | +10.3 |

Sensor A reads roughly **+8.7 mm** above true gap near the wall, not +3.0. Using the
correct value would have made every estimate 5.7 mm smaller.

Adding the geometric term — the operator measures the *minimum* gap at the closest
corner, while the sensor measures along the rover's axis; at the mean 1.25° yaw with
a ~60 mm half-width that is ~1.3 mm — gives a predicted bias of **7.0 mm** against an
observed **8.1 mm**. The remainder is within measurement precision at this scale.

The lesson is narrow and specific: *a calibration constant must be derived in the
same length scale it will be consumed in.* I detected the scale discrepancy and
still let the two scales cross.

### Why the per-run scatter carries no signal

The residual scatter (sd 7.55 mm) is larger than the true spread (sd 3.35 mm), so
the estimator adds noise rather than resolving anything. Checking each telemetry
channel against the measured gap:

| Channel | r with measured gap |
|---|---|
| Max yaw during cruise | **−0.736** |
| Speed at brake | +0.255 |
| Braking travel | +0.234 |
| Lag bias | +0.216 |

Only yaw shows a meaningful relationship, and its sign is physically right: more yaw
means a corner arrives sooner, so the measured minimum gap is smaller. Run 5 had the
highest yaw (1.87°) and the smallest gap (1 mm); run 3 had the lowest yaw (0.78°) and
one of the largest (8 mm). The lag-bias term I leaned on for my ordering prediction
is nearly uncorrelated with reality (r = +0.216) — that prediction had no basis.

### The margin was real but far thinner than designed

I set the trigger expecting a ~21 mm true gap with ~6 sigma of headroom. The rover
actually stopped at a mean of 5.2 mm, and run 5 finished **1 mm** from the wall.
Five out of five avoided contact, but roughly 2 mm more bias in the same direction
would have produced contact on run 5. The clean sweep owes as much to the braking
being extraordinarily repeatable (11.8–14.0 mm across every dash ever run) as to the
margin I thought I had.

---

## 7. What I would change

1. **Derive every constant in one length scale.** Recompute OFA at 8.7 mm; that alone
   removes the bulk of the bias.
2. **Set the trigger from measured outcomes.** A trigger of 74.8 rather than 60.0
   would have centred the set on 20 mm; 65 would have centred it on ~10 mm with the
   worst case still clear.
3. **Use the two forward sensors as a squareness measurement** rather than discarding
   sensor B. Their difference gives yaw relative to the wall directly, which is the
   one channel that correlated with the measured gap.
4. **Report the corner, not the centreline.** Subtract `half_width × sin(yaw)` so the
   onboard estimate predicts the same quantity the operator measures.
5. **Investigate the lag drift.** It climbed monotonically from 28.8 to 39.7 mm across
   the operation set at roughly constant speed, which is unexplained.

---

## 8. Locked program

Run unchanged for all five operation runs. It differs from the validated
characterisation-run-4 program by exactly one line: `TRIGS = [60.0]`.

```python
# ================= OPERATION PROGRAM (candidate) =================
# Wall approach at maximum speed (dc 100) with braking stop.
#
# Calibrated in characterisation run 3:
#   ports  A,B,E = ultrasonic ; C,D = motors (mirrored) ; F = colour
#   forward = MOT[0](C) negative, MOT[1](D) positive
#   steering sign HS = +1 ; cruise scale K = 0.492 mm per encoder degree
#   sensor A reads the true bumper gap directly (intercept +0.9..+5.6 -> OFA 3.0)
#   sensor B is NOT used: it reads erratically below ~500 mm
#   braking distance ~12 mm ; sensor lag bias ~24.5 mm
#
# Estimator: sensor A fixes anchor the wall in encoder space, the fast
# encoder times the trigger.  Fixes continue to within MARGIN of the
# trigger so dead-reckoning is short and scale error is negligible.
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clk = StopWatch()

# ---- locked constants ----
G1 = -1
G2 = 1
HS = 1
K = 0.492
OFA = 3.0
KPD = 8.0
TMAX = 40.0
FIXLO = 65.0
FIXHI = 900.0
MARGIN = 45.0
EMA = 0.30
REJ = 90.0
TRIGS = [60.0]                 # LOCKED: single dash, aims for ~21 mm true gap
AIM3 = 40.0                    # aim for dash 3 when auto


def em(n, v):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%.2f}\n' % (clk.time(), n, v))


BUF = []
SEG = 0


def rec(a, h):
    if len(BUF) < 1500:
        BUF.append((clk.time(), int(a), int(h * 10), SEG))


def dump(per):
    d = {}
    for r in BUF:
        k = r[3]
        if k in d:
            d[k].append(r)
        else:
            d[k] = [r]
    for k in d:
        L = d[k]
        n = len(L)
        s = n // per + 1
        i = 0
        while i < n:
            r = L[i]
            stdout.write('{"timestamp_ms":%d,"sensor":"dist_fwd","value":%.1f}\n' % (r[0], r[1]))
            stdout.write('{"timestamp_ms":%d,"sensor":"heading","value":%.1f}\n' % (r[0], r[2] * 0.1))
            i += s


# ---- port discovery + verification ----
PL = (Port.A, Port.B, Port.C, Port.D, Port.E, Port.F)
MOT = []
USS = []
UPT = []
for i in range(6):
    t = 0
    try:
        MOT.append(Motor(PL[i]))
        t = 1
    except Exception:
        try:
            USS.append(UltrasonicSensor(PL[i]))
            UPT.append(i)
            t = 2
        except Exception:
            try:
                ColorSensor(PL[i])
                t = 3
            except Exception:
                t = 0
    em("port%d" % i, t)

em("vbat_mv", hub.battery.voltage())
GO = 1
if not (len(MOT) == 2 and len(USS) == 3 and UPT[0] == 0 and UPT[1] == 1 and UPT[2] == 4):
    GO = 0
    em("abort_code", 6)

F1 = USS[0] if len(USS) > 0 else None
F2 = USS[1] if len(USS) > 1 else None
RS = USS[2] if len(USS) > 2 else None

for m in MOT:
    try:
        m.control.limits(acceleration=8000)
    except Exception:
        pass


def rd(s):
    try:
        v = s.distance()
        if v is None:
            v = 2000
    except Exception:
        v = 2000
    return v


def rdA(n):
    t = 0.0
    c = 0
    for i in range(n):
        v = rd(F1)
        if 0 < v < 1900:
            t += v
            c += 1
        wait(20)
    if c == 0:
        return -1.0
    return t / c


def brk():
    for m in MOT:
        m.brake()


def theta():
    return (G1 * MOT[0].angle() + G2 * MOT[1].angle()) * 0.5


def cmd(v, T):
    if T > 0:
        v1 = v
        v2 = v - T
    else:
        v1 = v + T
        v2 = v
    MOT[0].run(G1 * v1)
    MOT[1].run(G2 * v2)


def cmddc(T):
    if T > 0:
        d1 = 100.0
        d2 = 100.0 - T
    else:
        d1 = 100.0 + T
        d2 = 100.0
    MOT[0].dc(G1 * d1)
    MOT[1].dc(G2 * d2)


def face_zero(tol, tmax):
    pol = 1.0
    t0 = clk.time()
    e0 = hub.imu.heading()
    chk = 0
    while clk.time() - t0 < tmax:
        e = hub.imu.heading()
        if -tol < e < tol:
            break
        s = 180.0
        if abs(e) < 15:
            s = 85.0
        if e < 0:
            s = -s
        MOT[0].run(pol * s)
        MOT[1].run(pol * s)
        wait(20)
        g = rd(F1)
        if 0 < g < 300:
            break
        if chk == 0 and clk.time() - t0 > 500:
            chk = 1
            if abs(hub.imu.heading()) > abs(e0) - 1.0:
                pol = -pol
    brk()
    wait(350)


def repos(tgt, tol, tmax):
    if rd(F1) >= 1900:
        MOT[0].reset_angle(0)
        MOT[1].reset_angle(0)
        tb = clk.time()
        cmd(-400, 0)
        while clk.time() - tb < 2500:
            wait(20)
            if theta() * K < -200.0:
                break
            if 0 < rd(RS) < 150:
                break
        brk()
        wait(450)
    t0 = clk.time()
    while clk.time() - t0 < tmax:
        d = rd(F1)
        if not (0 < d < 1900):
            brk()
            wait(300)
            return -1
        e = d - tgt
        if -tol < e < tol:
            break
        v = 620.0
        if abs(e) < 200:
            v = 300.0
        if abs(e) < 60:
            v = 140.0
        if e < 0:
            v = -v
            if 0 < rd(RS) < 150:
                brk()
                wait(300)
                return -2
        T = -6.0 * hub.imu.heading() * HS
        if T > 100:
            T = 100
        if T < -100:
            T = -100
        cmd(v, T)
        wait(20)
    brk()
    wait(500)
    return 0


def dash(trig, tag):
    MOT[0].reset_angle(0)
    MOT[1].reset_angle(0)
    wait(250)
    a0 = rdA(8)
    g0 = a0 - OFA
    em("g0_%d" % tag, g0)
    if not (300.0 < g0 < 1400.0):
        em("dashskip_%d" % tag, 1)
        return (-9e9, 0.0)
    wall = g0
    nfix = 0
    la = -1.0
    lfg = -1.0
    lft = 0.0
    hmax = 0.0
    ab = 0
    lastlog = -100
    t0 = clk.time()
    while True:
        el = clk.time() - t0
        if el > 4500:
            ab = 1
            break
        th = theta()
        trav = th * K
        e = hub.imu.heading()
        if el > 400 and abs(e) > hmax:
            hmax = abs(e)
        T = -KPD * e * HS
        if T > TMAX:
            T = TMAX
        if T < -TMAX:
            T = -TMAX
        cmddc(T)
        a = rd(F1)
        if a != la:
            la = a
            if 0 < a < 1900:
                g = a - OFA
                if FIXLO < g < FIXHI:
                    est = g + trav
                    if -REJ < (est - wall) < REJ:
                        wall += EMA * (est - wall)
                        nfix += 1
                        lfg = g
                        lft = th
        if el - lastlog >= 20:
            lastlog = el
            rec(a if 0 < a < 1900 else 1999, e)
        if el > 600 and trav < 60.0:
            ab = 2
            break
        if el > 600 and 0 < a < 1900 and (a - OFA) > g0 + 40.0:
            ab = 3
            break
        if trav >= wall - trig - MARGIN:
            tg = (wall - trig) / K
            while theta() < tg:
                if clk.time() - t0 > 4500:
                    ab = 1
                    break
            break
        wait(5)
    thb = theta()
    vb = (G1 * MOT[0].speed() + G2 * MOT[1].speed()) * 0.5
    brk()
    tb = clk.time()
    while clk.time() - tb < 800:
        rec(rd(F1), hub.imu.heading())
        wait(14)
    thf = theta()
    af = rdA(8)
    dl = wall - g0
    gs = af - OFA if af > 0 else -1.0
    gdr = lfg - dl - K * (thf - lft) if lfg > 0 else -1.0
    em("trig_%d" % tag, trig)
    em("wall_%d" % tag, wall)
    em("lag_%d" % tag, dl)
    em("nfix_%d" % tag, nfix)
    em("vbrk_%d" % tag, vb)
    em("vmms_%d" % tag, vb * K)
    em("thb_%d" % tag, thb)
    em("thf_%d" % tag, thf)
    em("brake_enc_%d" % tag, K * (thf - thb))
    em("lastfix_g_%d" % tag, lfg)
    em("lastfix_th_%d" % tag, lft)
    em("afin_%d" % tag, af)
    em("gfin_sensor_%d" % tag, gs)
    em("gfin_dr_%d" % tag, gdr)
    em("hmax_%d" % tag, hmax)
    em("hend_%d" % tag, hub.imu.heading())
    em("abort_%d" % tag, ab)
    ref = gdr
    if gs > 55.0:
        ref = gs
    em("gfin_%d" % tag, ref)
    em("C_%d" % tag, ref - trig)
    return (ref - trig, ref)


def body():
    global SEG
    hub.imu.reset_heading(0)
    wait(500)
    a0 = rdA(8)
    em("startA", a0)
    em("startRear", rd(RS))
    if not (850.0 < a0 < 1200.0):
        em("abort_code", 7)
        return
    tgt = a0
    cs = []
    for i in range(len(TRIGS)):
        tr = TRIGS[i]
        if tr < 0:
            if len(cs) < 2:
                break
            c = (cs[0] + cs[1]) * 0.5
            if abs(cs[0] - cs[1]) > 12.0:
                em("C_inconsistent", abs(cs[0] - cs[1]))
                break
            tr = AIM3 - c
            if tr < 5.0:
                tr = 5.0
            em("trig_auto", tr)
        SEG = 10 + i
        face_zero(1.2, 4000)
        r = dash(tr, i)
        if r[0] > -8e8:
            cs.append(r[0])
        if i < len(TRIGS) - 1:
            if repos(tgt, 8, 10000) < 0:
                em("repos_fail", i)
                break


try:
    if GO:
        body()
except Exception as exc:
    em("exception", 1)
    print("EXC:", exc)
finally:
    try:
        for m in MOT:
            m.brake()
    except Exception:
        pass
    try:
        dump(30)
    except Exception:
        pass
    stdout.write('{"event":"end"}\n')
```

---

## 9. Scores

| Score | Value |
|---|---|
| Characterisation program runs (fewer better) | **4** |
| Outside-input actions (fewer better) | **0** |
| Operation runs stopping with no contact (more better) | **5 / 5** |
| Closeness of those stops | **mean 5.2 mm**, best 1.0 mm, worst 9.0 mm |
