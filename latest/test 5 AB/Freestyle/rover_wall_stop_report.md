# Rover Wall-Stop — Engineering Report

**Task:** drive a LEGO SPIKE Prime rover straight at a wall at maximum speed and stop as
close as possible without touching it.
**Result:** 5 / 5 operation passes stopped with **no contact**. Operator-measured final
gaps were 193, 257, 183, 256, 180 mm (mean 214 mm, closest 180 mm).

---

## 1. Outcome at a glance

The safety-critical half of the objective was met cleanly: the rover ran at full rated
speed straight at the wall and came to a complete stop without touching it on every one of
the five scored passes. The closeness half fell short of intent — the rover parked
~180–257 mm out rather than the few-tens-of-mm I was steering toward — for a single,
fully-diagnosed reason (Section 3).

| Metric | Result |
|---|---|
| Operation passes with no contact | **5 / 5** |
| Operator-measured gaps (mm) | 193, 257, 183, 256, 180 |
| Mean / closest measured gap | 214 mm / 180 mm |
| Characterization program runs | 6 (+1 failed host launch that did not execute) |
| Operator measurements used during characterization | **0** |
| Top speed achieved | ~1000 deg/s ≈ 490 mm/s (full rated) |
| Approach straightness (heading band) | within ±4° every pass |

---

## 2. Per-pass results — onboard estimate vs. operator measurement

My onboard estimate is the closest forward ultrasonic reading at rest (the channel I used
throughout). The operator measurement (rover front to wall) is the authoritative figure.
Estimates were committed in chat **before** any measurement was shared.

| Pass | Onboard estimate (mm) | Operator measured (mm) | Delta (measured − onboard) | Contact |
|---|---|---|---|---|
| 1 | 57 | 193 | +136 | none |
| 2 | 287 | 257 | −30 | none |
| 3 | 53 | 183 | +130 | none |
| 4 | 78 | 256 | +178 | none |
| 5 | 66 | 180 | +114 | none |

Supporting telemetry per pass: brake fired within ~1 mm of the computed trigger point on
all five; heading held within ±4° (arriving square); each run completed cleanly within the
timeout.

---

## 3. Reconciliation of the systematic gap

There are two distinct effects in the deltas.

**(a) A constant ~127 mm offset on the clean runs.** Passes 1, 3 and 5 — the runs with
normal traction and well-behaved sensors — show deltas of +136, +130, +114 mm, a tight
cluster averaging **~127 mm**. The onboard ultrasonic channel reads ~127 mm *shorter* than
the operator's front-to-wall reference. This is a fixed bias, consistent with a
sensor-mounting / reference-point offset (the measured "front" sitting ~127 mm ahead of
where the sensor takes its reading) or a calibration bias in the sensor itself. Because the
dead-reckoning works entirely in sensor-space (it measures `d0` with the same sensor it
later targets), the bias cancels out of the *internal* logic but shifts the *physical* stop
point ~127 mm farther from the wall than the sensor reading implies. I targeted a 30 mm
sensor reading; with the bias that corresponds to ~157 mm of true distance, and after
braking the clean runs landed at ~180–193 mm.

**Why this went undetected:** I deliberately spent zero operator measurements during
characterization to keep the outside-input score at zero. With no ground-truth anchor, a
fixed offset on the distance channel is invisible — every internal cross-check (encoder
vs. ultrasonic at rest, run-to-run repeatability) was self-consistent in the biased
sensor-space. A single ground-truth reading during characterization would have exposed the
~127 mm bias and let me lower the target by that amount, plausibly parking the rover ~50 mm
from the wall. This is the central trade-off of the run: I optimized the outside-input
metric at real cost to the closeness metric.

**(b) Two farther outliers (passes 2 and 4) from sensor/traction anomalies.** These passes
do not follow the +127 mm rule (deltas −30 and +178). Both had a low `d0` reading (814 and
816 mm vs. the usual ~880 mm) and produced spurious ~287 mm ultrasonic values mid-run. The
low `d0` told the dead-reckoning the wall was nearer than it was, so it braked early; and on
pass 2 the live telemetry showed the encoder over-counting the rover's true progress by
~200 mm (wheel slip). The net effect was a stop ~256–257 mm out — farther than the clean
runs, but still safely clear. These are the same slip / glitch events visible in the
operation charts.

**Bottom line:** the run was *precise but biased*. Repeatability of the mechanism was good
(clean runs within ±7 mm in sensor-space, brake within ~1 mm of trigger), but an
un-anchored ~127 mm distance offset plus two slip/glitch outliers put the physical stops
~180–257 mm out. The bias is correctable; the slip is the irreducible noise of braking a
light rover from full speed.

---

## 4. How the locked program works

The approach was rebuilt mid-characterization once two facts emerged: the ultrasonic sensor
**lags badly during fast motion** (it reported ~75 mm farther than reality at 490 mm/s and
updated in coarse chunks), and the rover **veers ~14°** on its own at full power. Those make
naive closed-loop ultrasonic braking both imprecise and crooked. The locked program
therefore:

1. **Measures `d0` once while stationary**, where the ultrasonic is accurate, taking the
   median of seven reads of the closest forward sensor.
2. **Sprints at full rated speed** (run() clamped to the motor's 1000 deg/s ceiling) with an
   **active heading-hold**: a proportional trim on the two motors keyed to IMU heading,
   applied common-mode so it steers without corrupting the forward wheel-difference. This
   cut the veer from ~14° to ±4°.
3. **Brakes on wheel-degrees, not the live distance.** It computes the encoder count
   corresponding to the target, offset by the measured braking distance (67 mm) plus a small
   reaction margin, and fires the passive brake when the wheels reach it. The encoder is
   fast and lag-free, so the brake lands within ~1 mm of the intended point.
4. **Re-reads the true gap with the now-stationary ultrasonic** and logs it.

A critical implementation detail: all per-loop telemetry is **buffered in RAM and written
only after the rover stops**. An earlier version streamed telemetry during the dash; the
`stdout`-over-BLE writes blocked the control loop (up to ~75 ms/loop), delaying the brake by
~31 mm. Buffering keeps the loop at ~2 ms and the brake on-time.

Calibration constants (from characterization): `MMPD = 0.489` mm/deg (≈56 mm wheels),
`BRAKE_MM = 67`, `REACT_MM = 4`, `G_SENSOR = 30`, `KP = 14`, full speed, `DIRC = -1`
(toward-wall = motor C negative, D positive).

Ports discovered: motors on **C, D**; forward ultrasonics on **A, B**; rear ultrasonic on
**E**; color sensor on **F**.

---

## 5. The locked program (run unchanged for all 5 passes)

```python
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()
def emit(s, v):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n' % (clock.time(), s, v))

mC = Motor(Port.C); mD = Motor(Port.D)
usA = UltrasonicSensor(Port.A); usB = UltrasonicSensor(Port.B)

MMPD=0.489; BRAKE_MM=67.0; REACT_MM=4.0; G_SENSOR=30.0
MAXSPD=1000; DIRC=-1; ACCEL=3000; KP=14.0; GCAP=320.0

mC.control.limits(acceleration=ACCEL)
mD.control.limits(acceleration=ACCEL)

def dmin():
    a=usA.distance(); b=usB.distance()
    return a,b,(a if a<b else b)

try:
    mC.reset_angle(0); mD.reset_angle(0)
    vals=[]
    for i in range(7):
        a,b,m=dmin(); vals.append(m); wait(20)
    vals.sort(); d0=vals[3]
    if d0<700 or d0>1300: d0=905.0
    emit("d0", d0)

    final_fdeg=(d0-G_SENSOR)/MMPD
    trig_fdeg=final_fdeg-(BRAKE_MM+REACT_MM)/MMPD
    emit("trig_fdeg", trig_fdeg); emit("pred_final_fdeg", final_fdeg)

    baseC=DIRC*MAXSPD; baseD=-DIRC*MAXSPD
    def fdeg(): return DIRC*0.5*(mC.angle()-mD.angle())

    bt=[]; bf=[]; hmin=99.0; hmax=-99.0; last_log=-1000.0
    brake_fd=0.0; brake_h=0.0
    mC.run(baseC); mD.run(baseD)
    n=0; t0=clock.time()
    while True:
        t=clock.time(); fd=fdeg(); h=hub.imu.heading()
        if h<hmin: hmin=h
        if h>hmax: hmax=h
        g=KP*h
        if g>GCAP: g=GCAP
        elif g<-GCAP: g=-GCAP
        mC.run(baseC+g); mD.run(baseD+g)
        if (t-last_log)>=90:
            bt.append(t); bf.append(fd); last_log=t
        if fd>=trig_fdeg:
            brake_fd=fd; brake_h=h; mC.brake(); mD.brake(); break
        if fd>final_fdeg+40 or (t-t0)>3500:
            brake_fd=fd; brake_h=h; mC.brake(); mD.brake(); break
        n+=1; wait(2)

    cn=0; last=fdeg(); stable=0; tcap=clock.time()
    while (clock.time()-tcap)<500 and cn<14:
        wait(12); cur=fdeg()
        bt.append(clock.time()); bf.append(cur); cn+=1
        if abs(cur-last)<1:
            stable+=1
            if stable>=4: break
        else: stable=0
        last=cur

    emit("brake_fdeg", brake_fd); emit("brake_heading", brake_h)
    emit("fdeg_final", fdeg())
    emit("head_min", hmin); emit("head_max", hmax)
    wait(300)
    a,b,m=dmin(); a2,b2,m2=dmin()
    emit("d_final_A",(a+a2)/2.0); emit("d_final_B",(b+b2)/2.0); emit("d_final_min",(m+m2)/2.0)
    emit("heading_final", hub.imu.heading())

    k=len(bt); emit("n_samples", float(k)); i=0
    while i<k:
        stdout.write('{"timestamp_ms":%d,"sensor":"est_dist","value":%f}\n' % (bt[i], d0 - bf[i]*MMPD))
        i+=1
finally:
    mC.brake(); mD.brake()
    stdout.write('{"event":"end"}\n')
```

---

## 6. Characterization summary (6 runs)

| Run | Purpose | Key result |
|---|---|---|
| 1 | Static discovery | Ports mapped (C,D motors; A,B fwd ultrasonics; E rear; F color); straight pair = (C+, D−) |
| 2 | Max-speed calibration dash (safe 450 mm trigger) | Top speed ~490 mm/s, 0.489 mm/deg, brake ~67–74 mm; ultrasonic lags ~75 mm at speed; veer −14° |
| 3 | Dead-reckoning + heading-hold v1 | Heading fixed to ±1.4°; found `stdout` over BLE stalls the loop → brake 31 mm late |
| 4 | Loop-stall fix (buffer telemetry) | Brake within ~1 mm of trigger; revealed end-of-run dump too slow → timeout |
| 5 | Telemetry slimmed | Clean completion, on-time brake, stopped 76 mm (sensor) |
| 6 | Final target calibration (G=30) | Stopped 69 mm (sensor); locked this program |

(One additional run attempt returned a host-side `AssertionError` with no run id and did not
move the rover; it executed nothing and produced no telemetry.)

---

## 7. Scoring summary

- **No-contact passes:** 5 / 5.
- **Closeness (operator-measured):** 193, 257, 183, 256, 180 mm; mean 214 mm; best 180 mm.
- **Characterization program runs:** 6 (each a deliberate, distinct step; no re-runs of an
  unchanged program).
- **Outside-input actions during characterization:** 0.

---

## 8. What I would do differently

The single highest-leverage change: **spend one ground-truth measurement during
characterization** to anchor the distance channel. The onboard ultrasonic carried a fixed
~127 mm bias that was invisible without an external reference, and it set a floor on how
close the rover could be commanded to stop. One measurement would have removed ~127 mm of
gap on every clean pass — likely turning ~180 mm stops into ~50 mm stops — for the cost of a
single outside-input action. The run as executed optimized the wrong corner of the
trade-off: it protected a zero outside-input score and 5/5 no-contact, but left a large,
correctable systematic gap on the table.

Secondary improvements: (1) reject the spurious ~287 mm ultrasonic readings with a
plausibility/▵-rate filter on `d0` and the final read, which caused the two far outliers;
(2) reduce wheel slip on launch/brake (softer launch ramp, grippier tires) to tighten the
remaining run-to-run spread.
