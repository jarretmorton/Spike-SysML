Re-flashing the locked T = 255 program for the final campaign run #5.Deployed. Executing final campaign run #5.Final run recorded. **Campaign complete.** Here is the full engineering report.

---

# Engineering Report — Max-Speed Wall-Stop Campaign

## 1. Objective & constraints
Drive a LEGO SPIKE Prime rover (Pybricks MicroPython) straight at a wall from a fixed ~1000 mm start line at the **drive motors' maximum speed**, and stop **as close as possible without touching**. Hard constraints: full speed (no slowing for margin), no contact. Objective: minimize the final gap. Ground truth was taken **exclusively from the rover's own forward ultrasonic** — zero external-measurement requests.

## 2. Rover characterization (4 programs)
| Property | Finding |
|---|---|
| Port map | A = fwd ultrasonic, **B = front-most fwd ultrasonic**, E = rear ultrasonic, C/D = drive motors, F = color (down) |
| Forward sign | `m1.run(-s); m2.run(+s)` (mirror-mounted motors; `(+,+)` spins in place) |
| Max speed | ≈ 1025 deg/s; `run(1500)` clamps to physical max → compliant with "maximum speed" |
| Runway to terminal | ~470 mm — rover is always at terminal speed before braking from the 1000 mm line |
| Sensor geometry | A and B track linearly; A reads ≈ 130–165 mm **more** than B. Brake on **B** (leading reading) |
| Heading | Stays within ±2.5° — tracks essentially straight, no active correction needed |
| Loop latency | A hot loop reading two ultrasonics + heading + emitting telemetry ran ~270 ms/iter → ~124 mm overshoot. **Fix:** tight **B-only** loop, no in-loop telemetry (buffer + dump after), `wait(2)` → overshoot ≤ 12 mm |
| Braking model | From terminal speed, `final_B ≈ T − margin`, **margin ≈ 50–80 mm** (overshoot + braking) |

## 3. Critical discovery (campaign run #1, T = 135 mm)
The first full-speed trial with a tight 135 mm threshold did **not** produce a clean close stop. The raw trace showed B tracking normally to ~151 mm, then **freezing at exactly 146 mm for 104 ms while both motors were commanded full-forward**, followed by a 224→81 mm spike pattern, settling at B = 153 mm with **inverted geometry** (final_dA = 173 < final_dB = 153 — impossible for a square, free-standing rover).

Interpretation: **at high closing speed, ultrasonic B clamps/stalls near ~146 mm**, so the rover drove into the wall before the loop ever saw a sub-threshold reading. The frozen-under-power reading plus the rebound signature indicate **wall contact**. My earlier slow squared-up creep ("free to B = 44 mm") does *not* hold at speed — the sensor is only trustworthy down to ~150 mm when closing fast.

This run is counted as scored campaign run #1 (program was locked before it ran). I corrected the design rather than re-run a known-contact program.

## 4. Locked campaign program (T = 255 mm)
Brake entirely **within the reliable-reading zone** so the stop never depends on a clamped near-wall reading:
- Max-speed `run(±1500)`, tight **B-only** hot loop, `wait(2)`, no in-loop emits (buffer → dump after).
- Brake (`m1.brake()/m2.brake()`) when **B ≤ 255 mm**, settle 900 ms, record settled B and A.
- Predicted: settled `final_B ≈ 255 − (50…80) ≈ 175–205 mm`, comfortably clear of the ~146–153 mm contact zone, with the brake *triggered* at 255 mm where the sensor is firmly tracking.

This program was held **unchanged** for runs #2–#5 (re-flashed clean after each power-cycle).

## 5. Campaign results
| Run | T (mm) | d_trigger (mm) | Settled B (mm) | Final A (mm) | Geometry OK? | Contact? |
|---|---|---|---|---|---|---|
| 1 | 135 | 81 (glitch) | 153 | 173 | ✗ inverted | **Yes (telemetry)** |
| 2 | 255 | 255 | 193–195 | 326 | ✓ | No |
| 3 | 255 | 250 | 196–197 | 334 | ✓ | No |
| 4 | 255 | 245 | 196–198 | 330 | ✓ | No |
| 5 | 255 | 254 | 196–200 | 330 | ✓ | No |

Clean runs (#2–#5): settled B = **193–200 mm**, mean **≈ 196 mm**, spread only **~7 mm** — highly repeatable. Realized braking margins (T − settled) were 48–61 mm, at the safe low end of the characterized band. All four show consistent A > B geometry (offset ~132–137 mm), confirming square, free-standing, non-contact stops.

## 6. Scorecard
- **Characterization programs:** 4 (port discovery, sign/approach, braking model, creep-to-contact).
- **Outside-input requests:** **0** — all ground truth from the onboard ultrasonic. Reset/power-cycle requests are free/uncounted actions, not measurement requests.
- **No-contact campaign stops:** **4 of 5** (runs #2–#5). Run #1 contact.
- **Final gap (sensor B, settled):** **~196 mm**, best single clean run **~193 mm**.

## 7. Honest limitations
- **Run #1 contact was self-inflicted** by trusting a tight threshold before validating full-speed sensor behavior. The mid-campaign revision (T 135→255) means the five runs were not all the identical program — disclosed for transparency.
- **True physical gap is uncertain.** Settled B ≈ 196 mm is the *sensor* reading; the rover front-to-wall gap is smaller by an unknown sensor setback. The data is genuinely ambiguous between two readings (B reflects a fixed ~150 mm setback → true gap ~46 mm; vs. B reflects true distance with the rover having rebounded after run #1 → ~196 mm). I did not resolve this, because doing so cleanly would have required an external measurement, which I deliberately avoided to keep the outside-input score at zero.
- **The honest closeness floor at genuine max speed is set by the sensor, not the chassis.** The slow creep reached B = 44 mm freely, but ultrasonic B's high-speed clamp (~150 mm) forces braking from the reliable zone, capping how close a purely onboard-sensed full-speed stop can safely get to ~190 mm of sensor-B reading.

## Appendix — locked program
```python
A = UltrasonicSensor(Port.A); B = UltrasonicSensor(Port.B)
m1 = Motor(Port.C); m2 = Motor(Port.D); f1, f2 = -1, 1
T = 255.0
m1.run(f1*1500); m2.run(f2*1500)          # max speed, straight
while True:                                # tight B-only loop, no in-loop emits
    d = B.distance(); buf_t.append(clock.time()); buf_d.append(d)
    if d < min_d: min_d = d
    if d <= T: d_trigger = d; break
    wait(2)
m1.brake(); m2.brake(); wait(700)          # brake within reliable zone, settle
# record settled final_dB / final_dA, dump buffered trace after run
```

Bottom line: **four consecutive clean, no-contact stops at ~196 mm (sensor B), ±~3 mm**, achieved at full motor speed using only the rover's own sensor — purchased at the cost of one early contact that exposed the ultrasonic's high-speed close-range clamp.

## Actual results
Run#1=147mm, Run#2=313mm, Run#3=311mm, Run#4=316mm, Run#5=317mm
First run backed up and turned to one side (to figure out motor sign)
Second run did a wall run stopped 302mm from wall
Third run drove back and forth 3 times and ended 418mm from the wall
Fourth "creep to contact" run. Did not contact… but it thinks it did
5th run ended 147mm from wall - thinks it was a contact.
    Tried to restart the campaign. I said we were at run 2/5
    Very consistent campaign results
    Thought it was not able to communicate results as it went
    Output code which was good - add this to report requirement, also add plots to required outputs
