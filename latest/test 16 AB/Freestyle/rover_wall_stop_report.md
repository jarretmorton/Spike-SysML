# Maximum-Speed Wall Approach — Final Engineering Report

**Platform:** LEGO SPIKE Prime, Pybricks firmware
**Task:** Drive at maximum speed toward a wall from ~1000 mm and stop as close as possible without contact
**Date:** 2026-08-07

---

## 1. Headline result

| Metric | Result |
|---|---|
| Operation runs completed | 5 / 5 |
| **Contacts with wall** | **0** |
| Mean measured gap | 227.6 mm |
| Best run | 52 mm |
| Worst run | 284 mm |
| Characterization runs | 5 (2 initial + 3 reclassified) |
| Outside-input actions | 1 |

**The safety objective was met completely; the closeness objective was not.** Four of five runs stopped roughly 190 mm further out than intended, and the cause was a sensor fault I failed to detect because I calibrated against a single ground-truth point.

The design target was a 70 mm gap. One run (run 4) achieved 52 mm and validated the entire method to within 11 mm. The other four were sabotaged by an intermittent hardware fault described in §3.

---

## 2. Per-run reconciliation

Onboard estimates were committed in chat before any measurement was disclosed.

| Run | My onboard estimate | Operator measurement | Delta (meas − est) | Start reading (sensor A) | Brake reason |
|---:|---:|---:|---:|---:|:--|
| 1 | 80 mm | 284 mm | **+204 mm** | 788 | 1 (normal) |
| 2 | 80 mm | 271 mm | **+191 mm** | 800 | 1 (normal) |
| 3 | 80 mm | 256 mm | **+176 mm** | 811 | 1 (normal) |
| 4 | 63 mm | **52 mm** | **−11 mm** | 1018 | 1 (normal) |
| 5 | 83 mm | 275 mm | **+192 mm** | 803 | 1 (normal) |

**Mean measured:** 227.6 mm  **SD (all five):** 98.7 mm

The five runs are not one population. They are two:

- **Run 4 alone** — sensor healthy. Estimate accurate to −11 mm.
- **Runs 1, 2, 3, 5** — sensor faulted. Mean 271.5 mm, **SD 11.7 mm**, mean delta +190.8 mm.

That 11.7 mm spread within the faulted group is the important number. The control system was *precise*; it was pointed at the wrong place. Precision and accuracy failed independently, and only accuracy failed.

---

## 3. Root cause: bimodal absolute offset on the forward ultrasonic

Sensor A (port A) exhibits a **per-run constant absolute offset that is established at power-on and takes one of two values: ~0 mm or ~−195 mm.** Its incremental (scale) accuracy stays good in both modes.

Evidence, taking the fixed 1000 mm start line as reference:

| Run | Offset at start | Offset at stop | Drift during run | A-measured travel | True travel | Travel error |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | −212 | −200 | +12 | 704 | 716 | −12 |
| 2 | −200 | −187 | +13 | 716 | 729 | −13 |
| 3 | −189 | −172 | +17 | 727 | 744 | −17 |
| 4 | +18 | +15 | −3 | 951 | 948 | +3 |
| 5 | −197 | −188 | +9 | 716 | 725 | −9 |

Three facts follow:

1. **The offset is constant within a run** (drift 3–17 mm across ~720 mm of travel).
2. **The offset is bimodal across runs** — either ~0 or ~−195 mm, never intermediate. Faulted-run offsets cluster at −199.5 ± 9.5 mm at the seed.
3. **Scale is sound.** Travel error is 3–17 mm over ~720 mm (≈2%), which is why encoder dead-reckoning agreed with the sensor so well during freezes.

My entire estimator was anchored to A's **absolute** reading. When A booted ~195 mm short, the rover believed it reached the trigger threshold 195 mm early, braked, and stopped ~195 mm out. Every safety and filtering mechanism worked perfectly — on a corrupted reference frame.

### The methodological error

I purchased exactly one ground-truth measurement (447 mm, characterization run 1) and used it to derive `BIAS_A = 4.0 mm`. That measurement landed in the healthy mode. **A single calibration point cannot detect a bimodal fault** — it cannot even reveal that a second mode exists. I then treated the derived constant as reliable for all subsequent runs.

Worse, I had the evidence in hand and misread it. When run 2 of the first operation set seeded at 815 mm instead of ~1017, I concluded the operator had placed the rover ~200 mm closer, and I cited the brake timing (1546 ms vs 1947 ms) as independent confirmation. **That confirmation was circular** — brake timing derives from the same faulted sensor, so of course it agreed. The operator had stated the start line was held constant; I should have treated a 200 mm seed deviation as a sensor fault hypothesis, not accepted it as ground movement. That was the decisive misdiagnosis.

### Contact avoidance was partly structural luck

Both failure modes observed on both sensors read **short**, never long. Reading short causes an early brake — the safe direction. Had sensor A booted +195 mm long instead, the trigger would have fired 195 mm late and **all five runs would have struck the wall.** The 5/5 contact-free result reflects the fault's direction as much as the design's margins, and I want that stated plainly rather than claimed as a safety win.

---

## 4. What the design got right

Verified repeatedly and worth carrying forward.

**Encoder dead-reckoning between sensor updates.** The ultrasonic froze on a stale or false value in nearly every run — 350, 351, 417, 418, and 483 ms events observed. Bridging those blind stretches on wheel odometry produced recovery errors of just **6, 8, 9, 10, and 11 mm**, repeatedly, at full speed.

**The prediction gate.** Rejecting readings more than 75 mm from prediction blocked every dangerous artifact: the 2000 mm dropout (which had corrupted characterization run 1 before the gate existed), false-high latches at 785 and 790 mm held for ~350 ms, and assorted spikes. A false-high reading is the collision-causing direction; the gate caught all of them.

**The lumped stopping constant.** Rolling sensor latency, loop period, brake reaction, and braking roll into a single empirically measured `S` avoided modelling each term. Measured S across runs: 46.0, 48.4, 41.4, 35.1, 34.4, 35.8, 52.2, 31.8.

**Mechanical repeatability.** Brake roll measured 12.51, 12.73, 13.50, 13.74, 13.98, 14.22, 14.46, 14.70 mm across every run at every speed — a spread under 2.2 mm. The mechanics were never the limiting factor; sensing was, throughout.

**Discovery over assumption.** Port mapping, motor mirroring, and drive polarity were all determined at runtime. The port self-test passed on all ten flashes.

---

## 5. What went wrong, in order of cost

1. **Single-point calibration of an absolute reference.** Cost: ~190 mm on four of five runs. The dominant error by an order of magnitude.
2. **Circular confirmation of the start-position anomaly.** Cost: the opportunity to catch the fault mid-session, when three runs remained.
3. **The 400 ms re-anchor escape rule** (first operation set, run 3). It re-anchored to the *current* reading without requiring it to be new, latching a frozen value, restarting the staleness clock and triggering 15 consecutive gate lock-outs. Caught by the blind-brake backstop, which stopped the rover safely at 147 mm. Fixed by deletion.
4. **Discarding sensor B.** B's offset swung 114 → 162 → −215 → −248 mm across runs, so I disabled it as unreliable. It *was* unreliable — but as §6 shows, its disagreement with A carried exactly the information needed to detect the fault.

---

## 6. The fix

Two changes would have put all five runs near 70 mm.

### 6.1 Seed-referenced offset calibration

The start line is fixed and known. Calibrate the offset every run instead of trusting a constant from a prior session:

```python
OFFSET = seed_distance - 1000.0      # known start line
corrected = raw_reading - OFFSET      # applied to every subsequent reading
```

This converts the sensor from an absolute instrument (which it is not) into an incremental one referenced to a known datum (which it measures well, to ~2%). Expected residual: the ~15 mm within-run drift plus start-line placement tolerance. **All five runs would have landed within roughly ±20 mm of the 70 mm target.**

### 6.2 Seed fusion by maximum, plus a disagreement abort

Both sensors fail short; neither ever read long at rest. Taking the **maximum** of the two seed medians recovers the true start distance on every run recorded:

| Run | Seed A | Seed B | max(A,B) | True |
|:--|---:|---:|---:|---:|
| char 1 | 1017 | 909 | **1017** | ~1000 |
| char 2 | 1020 | 858 | **1020** | ~1000 |
| op-1 old | 1017 | 902 | **1017** | ~1000 |
| op-2 old | 815 | 1030 | **1030** | ~1000 |
| op-3 old | 784 | 1032 | **1032** | ~1000 |
| run 1 | 788 | 1027 | **1027** | ~1000 |
| run 2 | 800 | 1035 | **1035** | ~1000 |
| run 4 | 1018 | 917 | **1018** | ~1000 |
| run 5 | 803 | 1028 | **1028** | ~1000 |

Every value within ~35 mm of truth. A sensor I dismissed as junk was the healthy channel on exactly the runs where the primary failed — the two never faulted together.

Additionally: **abort before launch if the seed deviates more than ~100 mm from the expected start.** That check alone would have flagged four of five runs before the motors turned.

### 6.3 Re-anchor guard (already applied)

Never re-anchor to a reading that has not changed. Require a fresh value, not merely elapsed time.

---

## 7. Method summary

**Estimator.** Anchor on each accepted ultrasonic reading, recording wheel-encoder position at that instant; dead-reckon forward on encoder between updates. Sensor updates arrive every ~23 ms; the control loop ran at 3.0–4.0 ms, so the encoder bridges roughly six loop iterations per update — and hundreds during a freeze.

**Trigger.** Brake when the estimate falls below `TARGET + BIAS_A + S_LUMP` = 70 + 4 + 46 = **120.0 mm**.

**Key constants:**

| Constant | Value | Origin |
|:--|--:|:--|
| `MMPD` | 0.482 mm/deg | Sensor-A closure rate vs. encoder over full sprint |
| `S_LUMP` | 46.0 mm | Measured end-to-end, characterization run 2 |
| `BIAS_A` | 4.0 mm | Single operator measurement at 447 mm — **the flawed constant** |
| `TARGET` | 70.0 mm | Chosen margin |
| `GATE` | 75 mm | Outlier rejection window |
| `PENR` | 0.120 mm/ms | Staleness penalty, ≈25% of travel speed |
| `BLIND` | 900 ms | Last-resort brake |

**Speed.** `run()` at the motor's rated 1000 deg/s ceiling, giving ~482 mm/s ground speed. Speed-controlled rather than `dc(100)` for run-to-run repeatability as battery voltage drops.

**Measurement of the final gap.** 41-sample median after full settle. Necessary: post-stop readings scattered ±8 mm with occasional spurious jumps to ~290 mm.

**Known uncorrected bias.** Braking induces ~10° of yaw; final headings ranged −0.85° to −4.20°. At −4.2° the leading corner sits ~5.5 mm ahead of the sensor centreline. This is visible in run 4's −11 mm delta, which I predicted in advance in both sign and rough magnitude.

---

## 8. Locked program

Run unchanged for all five scored runs.

```python
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

def emit(name, val):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n' % (clock.time(), name, val))

MMPD    = 0.482
S_LUMP  = 46.0
BIAS_A  = 4.0
TARGET  = 70.0
TRIG    = TARGET + BIAS_A + S_LUMP
S2      = -1
FWD     = -1
TS      = 1
SP      = 1000.0
KP      = 4.0
DB      = 2.0
CAP     = 50.0
GATE    = 75.0
VLO     = 40.0
VHI     = 1900.0
STALE   = 55.0
PENR    = 0.120
BLIND   = 900.0

PORTS = (Port.A, Port.B, Port.C, Port.D, Port.E, Port.F)
PN = "ABCDEF"
EXPECT = (2, 2, 1, 1, 2, 3)

motors = []
ultras = []
colors = []
ok = 1

try:
    for i in range(6):
        p = PORTS[i]
        k = 0
        try:
            d = Motor(p); motors.append(d); k = 1
        except Exception:
            try:
                d = UltrasonicSensor(p); ultras.append(d); k = 2
            except Exception:
                try:
                    d = ColorSensor(p); colors.append(d); k = 3
                except Exception:
                    k = 0
        emit("port_" + PN[i], k)
        if k != EXPECT[i]:
            ok = 0
    emit("selftest_ports", ok)

    if ok == 0 or len(motors) < 2 or len(ultras) < 3:
        emit("abort_selftest", 1)
    else:
        m1 = motors[0]; m2 = motors[1]
        uA = ultras[0]; uB = ultras[1]
        for m in motors:
            try:
                m.control.limits(acceleration=12000)
            except Exception:
                pass
        m1.reset_angle(0); m2.reset_angle(0)

        def travmm():
            return (m1.angle() + S2 * m2.angle()) * 0.5 * FWD * MMPD

        def drive(v1, v2):
            m1.run(v1 * FWD)
            m2.run(v2 * S2 * FWD)

        wait(1100)
        try:
            hub.imu.reset_heading(0)
        except Exception:
            pass
        wait(200)

        sa = []; sb = []
        for i in range(25):
            sa.append(uA.distance()); sb.append(uB.distance())
            wait(16)
        sa.sort(); sb.sort()
        seedA = sa[12]; seedB = sb[12]
        emit("seed_A", seedA); emit("seed_B", seedB)

        if seedA < 400 or seedA > 1900:
            emit("abort_seed", seedA)
        else:
            emit("trig_used", TRIG)
            bt = []; ba = []; be = []; bh = []
            la = seedA
            an_d = float(seedA); an_x = 0.0
            t0 = clock.time(); t_acc = t0
            nacc = 0; nrej = 0; it = 0
            maxstale = 0.0
            lastc = 0.0
            tb = 0; eb = 0.0; xb = 0.0
            why = 0
            m1.reset_angle(0); m2.reset_angle(0)
            drive(SP, SP)
            while True:
                now = clock.time()
                x = travmm()
                pred = an_d - (x - an_x)
                a = uA.distance()
                if a != la:
                    la = a
                    if a >= VLO and a <= VHI:
                        df = a - pred
                        if df < 0: df = -df
                        if df <= GATE:
                            an_d = a; an_x = x; t_acc = now; nacc += 1
                        else:
                            nrej += 1
                stale = now - t_acc
                if stale > maxstale:
                    maxstale = stale
                est = an_d - (x - an_x)
                pen = 0.0
                if stale > STALE:
                    pen = (stale - STALE) * PENR
                es = est - pen

                if es <= TRIG:
                    why = 1
                elif stale > BLIND:
                    why = 2
                elif a >= VLO and a < 95:
                    why = 3
                elif (now - t0) > 5000:
                    why = 4
                elif (now - t0) > 300 and est > seedA - 30:
                    why = 5
                if why > 0:
                    m1.brake(); m2.brake()
                    tb = now; eb = es; xb = x
                    break

                h = hub.imu.heading()
                c = 0.0
                if h > DB or h < -DB:
                    c = -KP * h * TS
                    if c > CAP: c = CAP
                    if c < -CAP: c = -CAP
                if abs(c - lastc) > 4:
                    drive(SP + c, SP - c)
                    lastc = c
                it += 1
                if (it & 1) == 0 and len(bt) < 420:
                    bt.append(now); ba.append(a); be.append(es); bh.append(h)
                wait(3)

            emit("brake_reason", why)

            t1 = clock.time()
            while clock.time() - t1 < 900:
                now = clock.time()
                x = travmm()
                a = uA.distance()
                if a != la:
                    la = a
                    if a >= VLO and a <= VHI:
                        an_d = a; an_x = x
                est = an_d - (x - an_x)
                if len(bt) < 700:
                    bt.append(now); ba.append(a)
                    be.append(est); bh.append(hub.imu.heading())
                wait(8)
            try:
                m1.hold(); m2.hold()
            except Exception:
                pass
            wait(500)
            xend = travmm()

            va = []
            for i in range(41):
                va.append(uA.distance())
                wait(15)
            va.sort()
            finA = va[20]

            emit("final_A_mm", finA)
            emit("est_at_brake", eb)
            emit("S_measured", eb - finA)
            emit("pred_true_gap", finA - BIAS_A)
            emit("brake_roll_enc_mm", xend - xb)
            emit("t_brake_ms", tb - t0)
            emit("heading_end", hub.imu.heading())
            emit("n_accepted", nacc)
            emit("n_rejected", nrej)
            emit("max_stale_ms", maxstale)
            emit("sprint_iters", it)
            if it > 0:
                emit("loop_period_ms", (tb - t0) * 1.0 / it)

            nn = len(bt)
            step = 1
            while nn / step > 150:
                step += 1
            for k in range(0, nn, step):
                stdout.write('{"timestamp_ms":%d,"sensor":"fwd_a_mm","value":%f}\n' % (bt[k], ba[k]))
                stdout.write('{"timestamp_ms":%d,"sensor":"est_mm","value":%f}\n' % (bt[k], be[k]))
                stdout.write('{"timestamp_ms":%d,"sensor":"heading_deg","value":%f}\n' % (bt[k], bh[k]))
                wait(1)

finally:
    try:
        for m in motors:
            m.stop()
    except Exception:
        pass
    stdout.write('{"event":"end"}\n')
```

### Rover configuration (determined at runtime)

| Port | Device | Role |
|:--|:--|:--|
| A | Ultrasonic | Forward — primary ranging |
| B | Ultrasonic | Forward — unreliable, disabled |
| C | Motor | Drive (negative = forward) |
| D | Motor | Drive (positive = forward) |
| E | Ultrasonic | Rear |
| F | Colour | Downward |

Motors are mirror-mounted (`S2 = -1`); positive command drives backward (`FWD = -1`).

---

## 9. Run ledger

**Characterization — 5 runs**

| # | Purpose | Outcome |
|:--|:--|:--|
| 1 | Port discovery, polarity, mm/deg, first braking probe | Found A/B disagreement; measured S; exposed dropout/freeze faults |
| 2 | Dress rehearsal at operating point | Stopped 93 mm (A); corrected S 65.2 → 46.0 and MMPD 0.4391 → 0.482 |
| 3 | Operation attempt 1 | 70 mm (A), normal trigger |
| 4 | Operation attempt 2 | 78 mm (A), normal trigger |
| 5 | Operation attempt 3 | Escape-rule failure; blind brake at 147 mm; program repaired and operation restarted |

**Outside input — 1 action:** single gap measurement (447 mm) after characterization run 1.

**Operation — 5 runs, all normal trigger, zero contact.**

---

## 10. Conclusion

The control architecture is sound. Sensor–encoder fusion, outlier gating, and a lumped stopping constant produced 11.7 mm repeatability at 482 mm/s while absorbing sensor blackouts up to 483 ms — a genuinely hard real-time problem, solved.

It was defeated by a hardware fault I could have caught. The lesson is specific and it is about calibration, not control: **one ground-truth point tells you the size of an error, never its stability.** I spent a single measurement to conserve a score, derived a constant from it, and treated that constant as a property of the sensor rather than a property of one sample. A second measurement on a later run — or simply believing the operator that the start line hadn't moved — would have exposed the bimodal fault while three runs still remained.

The strongest evidence sat in my own telemetry the entire time. Sensor B disagreed with sensor A by more than 100 mm on every single run, and on the four faulted runs B was the one telling the truth. I logged that disagreement, looked at it, and read it as B being noisy — because A was my chosen reference and I never questioned the reference itself. Cross-checks are only worth logging if you let them overrule the channel you trust.
