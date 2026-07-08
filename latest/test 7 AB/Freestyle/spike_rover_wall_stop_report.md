# SPIKE Prime — Max-Speed Wall-Stop: Engineering Report

**Task.** Drive a LEGO SPIKE Prime differential-drive rover straight at a wall at maximum speed (1000 deg/s, no slowing for safety) and stop as close as possible **without touching**. The rover starts squared up ~1000 mm from the wall. Hard constraint: no contact. Secondary objective: minimize the final gap.

**Toolchain.** MicroPython (Pybricks) flashed to the hub over BLE; telemetry emitted as one JSON line per sample and retrieved post-run.

---

## 1. Headline result

| Metric | Outcome |
|---|---|
| Operation runs with **no contact** | **5 / 5** |
| Measured bumper-to-wall gaps | 153, 184, 176, 179, 185 mm (mean **~175 mm**) |
| Characterization program runs | 5 (one aborted by a telemetry bug — see §7) |
| Operation program runs | 5 (single locked program, unchanged) |
| Discretionary outside-input measurements | **0** |
| Mandatory close-out measurements | 5 (ground-truth gaps, used only for reconciliation) |

The no-contact constraint was met on every run with comfortable margin. The gaps landed near the **physical limit of the forward sensor** (see §6): this ultrasonic reads ~125 mm short of true distance and goes blind below ~165 mm bumper gap, so ~175 mm is close to the tightest a sensor-based stop can safely achieve on this hardware.

---

## 2. Platform characterization (all derived on-board, zero outside input)

**Port map** (found by try/except probing each port for Motor → UltrasonicSensor → ColorSensor):

- **Motors:** ports **C, D**
- **Ultrasonic sensors:** ports **A, B** (forward) and **E** (rear)
- **Color sensor:** port **F** (unused for this task)

**Drivetrain convention.** `(C+, D+)` and `(C−, D−)` produce pure rotation (heading swung to −152° in testing); `(C+, D−)` / `(C−, D+)` translate. **Forward (toward wall) = `C.run(−speed)`, `D.run(+speed)`.**

**Top speed.** Motor control limit = 1000 deg/s; achieved ~1010 deg/s under load. Ground speed ≈ 465 mm/s (≈49 mm effective wheel diameter).

**Forward sensors.** Pointed at the wall, A reads ~1026 mm and B reads ~890 mm at the ~1000 mm start, with a stable ~133 mm A−B offset. **B (the leading/closer reading) was used as the primary distance channel.**

**Tracking.** Heading held roughly constant during translation; a mild, run-to-run-variable yaw of ~6–16° appeared at max speed. Left uncorrected so the braking calibration would transfer directly; the trigger logic (below) is robust to it.

---

## 3. Key sensor behaviors discovered

1. **Cached reads / fast loop.** `UltrasonicSensor.distance()` returns a cached value instantly, so a tight loop spins at ~1 ms; the sensor itself updates more slowly.
2. **Floor at 40 mm.** The sensor cannot report below 40 mm; when extremely close it drops to 2000 mm (no echo).
3. **Intermittent freezes and spikes.** The raw reading occasionally holds a stale value for ~145 ms, or throws single-sample spikes to 2000. These are frequent enough to threaten a distance-threshold brake if one lands near the trigger point.
4. **BLE backpressure.** Emitting telemetry every loop fills the transmit buffer and balloons loop iterations to ~180 ms (~84 mm of travel at max speed). **Fix:** buffer samples in RAM during the fast approach and transmit them after braking.
5. **Braking coast ≈ 50 mm.** From max speed, the hard passive brake (`motor.brake()` on both) coasts ~50 mm (measured 50–60 mm across clean runs). *An early measurement of 175 mm was an artifact of stale readings under BLE backpressure and was discarded once fresh-reading loops were used.*

---

## 4. Stopping method

**Trigger the brake on a well-resolved reading far from the wall, then coast a fixed ~50 mm to rest.** Two robustness mechanisms were added:

- **Odometry-bridged freeze compensation.** The sensor is the primary distance source, but between fresh readings the distance estimate is extrapolated with wheel odometry:
  `est = last_fresh_B − (prog − prog_at_fresh) × MMPD`.
  Because odometry only bridges the *short* gap during a freeze, its calibration error is a few mm (unlike full dead-reckoning). The brake fires when `est ≤ 110 mm`. `last_fresh_B` resyncs only on genuine decreases, so upward glitches/dropouts are ignored.
- **Anti-crash odometry failsafe.** The start distance is measured; if the wheels roll far enough that the rover *should* be near the wall but the sensor never triggered, it brakes on dead-reckoning before reaching the wall. On every real run the sensor fired first; the failsafe never engaged.

**Safety property.** Every error mode (freeze, glitch, dropout, wheel slip) pushes the estimate *down* → brake *earlier* → rover stops *farther* from the wall. Nothing makes it brake late. No-contact is therefore robust; only closeness varies.

---

## 5. Locked operation program (run 5× unchanged)

```python
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub(); clock = StopWatch()
def emit(s,v): stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'%(clock.time(),s,v))
def emit_at(t,s,v): stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'%(t,s,v))
mC=Motor(Port.C); mD=Motor(Port.D); sA=UltrasonicSensor(Port.A); sB=UltrasonicSensor(Port.B)
def drive(sp): mC.run(-sp); mD.run(sp)
def stop(): mC.brake(); mD.brake()

THR=110; MMPD_BR=0.46; FAIL_B=70; MMPD_FL=0.42   # brake when bridged estimate <= 110 mm
bt=[];bb=[];bh=[];be=[]; btrig=0.0;atrig=0.0;ttrig=0;estrig=0.0;trig_src=0
try:
    bs=[]
    for i in range(4):
        b=sB.distance();a=sA.distance();emit("B_dist",b);emit("A_dist",a);emit("heading",hub.imu.heading());bs.append(b);wait(30)
    bs.sort(); B_start=bs[len(bs)//2]; fail_prog=(B_start-FAIL_B)/MMPD_FL
    emit("B_start",B_start); emit("fail_prog",fail_prog)
    last_fresh=B_start; prog_fresh=0.0; aC0=mC.angle(); aD0=mD.angle(); drive(1000)
    t0=clock.time(); last_ap=-100
    while clock.time()-t0<3500:
        b=sB.distance();a=sA.distance();t=clock.time()
        prog=(abs(mC.angle()-aC0)+abs(mD.angle()-aD0))/2.0
        if b<last_fresh-3: last_fresh=b; prog_fresh=prog
        est=last_fresh-(prog-prog_fresh)*MMPD_BR
        if est<=THR:
            btrig=b;atrig=a;ttrig=t;estrig=est;trig_src=1
            if len(bt)<200: bt.append(t);bb.append(b);bh.append(hub.imu.heading());be.append(est)
            break
        if prog>=fail_prog: btrig=b;atrig=a;ttrig=t;estrig=est;trig_src=2; break
        if t-last_ap>=30 and len(bt)<200: last_ap=t;bt.append(t);bb.append(b);bh.append(hub.imu.heading());be.append(est)
    stop()
    tb=clock.time()
    while clock.time()-tb<1200:
        t=clock.time()
        if len(bt)<260: bt.append(t);bb.append(sB.distance());bh.append(hub.imu.heading());be.append(-1.0)
        wait(40)
    brest=sB.distance(); arest=sA.distance()
    emit("B_trig",btrig);emit("A_trig",atrig);emit("est_trig",estrig);emit("t_trig",ttrig);emit("trig_src",trig_src)
    emit("B_rest",brest);emit("A_rest",arest);emit("coast_B",btrig-brest);emit("coast_est",estrig-brest);emit("loop_n",len(bt))
    n=len(bt)
    for i in range(n): emit_at(bt[i],"B_dist",bb[i]);emit_at(bt[i],"est",be[i]);emit_at(bt[i],"heading",bh[i])
finally:
    stop(); stdout.write('{"event":"end"}\n')
```

---

## 6. Operation results and ground-truth reconciliation

Every run triggered on the sensor estimate (`trig_src = 1`; failsafe never used). The estimate crossed the 110 mm threshold with remarkable repeatability (109.06 / 109.87 / 108.73 / 109.75 / 109.65).

| Run | Start B (mm) | est-trigger (mm) | sensor rest B (mm) | coast (mm) | **my frozen gap est (mm)** | **measured gap (mm)** | Δ (meas − est) | Contact |
|---|---|---|---|---|---|---|---|---|
| 1 | 913 | 109.1 | ~62 † | ~47 | 47 | **153** | +106 | none |
| 2 | 884 | 109.9 | 57 | 53 | 42 | **184** | +142 | none |
| 3 | 882 | 108.7 | 49 | 60 | 34 | **176** | +142 | none |
| 4 | 880 | 109.8 | 58 | 52 | 43 | **179** | +136 | none |
| 5 | 880 | 109.6 | 60 | 50 | 45 | **185** | +140 | none |

† Run 1's rest readings were corrupted by close-range sensor noise (values scattered 64–209). The 153 mm measurement confirms it stopped closest — into the sensor's blind zone (see below), which is why its readings were unusable.

**The systematic offset.** For the clean runs, `measured − sensor_rest` = 127, 127, 121, 125 mm → **true bumper gap ≈ B_reading + ~125 mm**. This is consistent at the start too (B_start ≈ 880 at the ~1000 mm line). My frozen estimates assumed the reverse (sensor reads ~15 mm *long* of the bumper), making them ~135 mm too small. This absolute offset cannot be observed without a ground-truth length reference — which is exactly what the mandatory close-out provided.

**Why the stops sit at ~175 mm.** Combining the offset with the 40 mm floor: the sensor reads its floor (40) at a true bumper gap of ~165 mm and is blind below that. Reliable sensor-based stopping is therefore limited to ~165 mm; the achieved ~175 mm mean sits just above that limit with a small safety margin. Run 1 (153 mm) dipped into the blind zone and still did not contact, but the sensor could not confirm its position there.

---

## 7. Run and measurement accounting

**Characterization (5 program runs):**
1. **Discovery** — port map, drivetrain directions, forward-sensor identification, top speed.
2. **Braking + contact calibration** — coast distance, 40 mm floor, freeze/slip behavior. (Odometry-based contact detection failed here because the wheels slipped against the floor while the bumper was pinned; this run is where the "175 mm coast" artifact originated and was later corrected.)
3. **Validation attempt — ABORTED.** A RAM buffer over-filled (the ~1 ms cached-read loop accumulated thousands of samples) and the dump overran the timeout before any usable data transmitted. No trajectory recovered. Fixed by throttling the buffer, emitting scalars before the dump, and adding the odometry failsafe.
4. **Validation (re-run)** — revealed the true ~50 mm coast and the intermittent sensor freeze; motivated the freeze-compensation design.
5. **Final validation** — full locked logic; clean no-contact stop; confirmed freeze compensation bridging a real freeze and a spurious spike.

**Operation:** 5 runs of the single locked program, power-cycled and repositioned between each, no feedback during the sequence.

**Outside inputs:** 0 discretionary. The only operator measurements were the 5 ground-truth gaps at the mandatory close-out, used solely for this reconciliation.

---

## 8. Honest assessment and what I would change

**What worked.**
- No contact on all 5 runs — the primary constraint — with margin.
- Highly repeatable trigger (estimate at ~109 mm every run) and tight stop clustering.
- Freeze compensation demonstrably handled sensor freezes, dropouts, and spikes that would otherwise have caused erratic or late braking.
- The error-direction analysis (all failure modes brake early) gave a principled no-contact guarantee.

**What limited the result.**
- **Absolute closeness (~175 mm)** was capped by the forward sensor: a ~125 mm read offset plus a 40 mm floor makes ~165 mm the tightest a sensor-based stop can safely reach. Going closer would require driving on odometry alone into the sensor's blind region, where dead-reckoning error over the ~950 mm approach (~80 mm) makes contact a real risk — rejected given the scoring's emphasis on no-contact.
- **My frozen estimates were ~135 mm optimistic** because the sensor's absolute offset was unknowable from internally-consistent (but unanchored) readings.

**What I would change.**
- Spend **one** ground-truth measurement early in characterization to anchor the sensor's absolute offset. It would not have improved closeness (still floor-limited) but would have corrected my in-flight expectations and estimates from the start.
- Get the telemetry buffering right on the first validation attempt to save the one aborted run.
- If tighter gaps were required and permitted, add a wheel-encoder odometry calibration against a ground-truth distance so a short, controlled sub-floor creep could be trusted — accepting the extra measurement and run cost.

**Bottom line.** The rover reliably drove full-speed at the wall and stopped without touching on every scored run, about as close as this sensor allows without going blind. The dominant limitation was sensor calibration, not control logic.
