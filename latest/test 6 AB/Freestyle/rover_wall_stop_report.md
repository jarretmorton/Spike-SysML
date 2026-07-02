# Max‑Speed Wall‑Stop — Engineering Report

**Platform:** LEGO SPIKE Prime rover, Pybricks MicroPython, driven over BLE via MCP tools
**Objective:** Drive straight at a wall at maximum speed and stop as close as possible **without contact**.
**Constraints:** Run at full speed; do not slow for a safety margin; no wall contact.

---

## 1. Results at a glance

Five locked‑program runs at full speed (~510 mm/s), each from an independently power‑cycled, re‑squared start.

| Run | Start (true, mm) | Max speed (mm/s) | Onboard estimate (mm) | Measured gap (mm) | Δ (est − meas) | Contact |
|----:|-----------------:|-----------------:|----------------------:|------------------:|---------------:|:-------:|
| 1 | 965 | 509 | 44 | **39** | +5 | No |
| 2 | 973 | 512 | 43 | **49** | −6 | No |
| 3 | 972 | 509 | 44 | **239** | −195 | No |
| 4 | 970 | 515 | 44 | **248** | −204 | No |
| 5 | 976 | 513 | 45 | **262** | −217 | No |

- **No contact on any run (5/5)** — the hard constraint was met on every run.
- **Runs 1–2: on target** — 39 mm and 49 mm, matching the onboard estimate within ±6 mm.
- **Runs 3–5: stopped ~200 mm short** — caused by a faulty ultrasonic *start* reading (Section 6), not by the stopping method.

---

## 2. Scorecard

1. **Characterization program runs used: 6** (discovery, direction, high‑speed brake, encoder validation #1, backward calibration, forward validation). One additional flash failed to connect and never ran, so it is not counted.
2. **Ground‑truth measurements requested during characterization: 1** (a single front‑bumper distance, used to expose the sensor problem in Section 4). The five end‑of‑run measurements are the mandated close‑out reconciliation, not mid‑task input.
3. **No‑contact runs: 5 / 5.**
4. **Closeness:** excellent on the two runs with a valid start reading (39, 49 mm; mean 44 mm); 239–262 mm on the three runs corrupted by the start‑reading fault.

---

## 3. Hardware characterization

**Port map (all six ports populated):** A = front ultrasonic, B = front ultrasonic, C = drive motor, D = drive motor, E = rear ultrasonic, F = colour sensor.

**Drive direction & geometry:** forward = motor C run negative, motor D run positive (motors are mirror‑mounted, so equal‑sign commands spin them opposite). Straight‑line tracking is good: net heading drift over a full‑speed run was only −1° to −6°.

**Speed:** maximum ≈ **1050 °/s at the wheels ≈ 510–560 mm/s** at the ground.

**Distance calibration:** **0.484 mm per degree** of wheel rotation. This was hard‑won — an early value (0.529) was corrupted by bad sensor readings and later corrected using a clean linear fit of a reliable sensor against wheel rotation, and independently confirmed forward (the encoder‑predicted position tracked the measured distance to <1% through the reliable sensing band).

**Braking:** an active `brake()` from full speed adds only ~13–15 mm of travel and is monotonic (no lunge toward the wall), which is why it was chosen over `hold()`.

---

## 4. The sensing problem (the crux of this task)

The ultrasonic sensors proved **unreliable**, and understanding exactly how drove every design decision:

- **Sensor B** reads low and turns to garbage below ~180 mm (values bounce, e.g. 119 → 259 → 237). It is not trustworthy for absolute distance.
- **Sensor A** is far better and reads solidly (±1.5 mm) at the ~1 m start, but it **reads progressively low as it approaches the wall** and, critically, exhibits an **intermittent large absolute bias** — on 3 of the 5 final runs it under‑read the ~970 mm start by ~200 mm while looking perfectly stable.
- **BLE telemetry is the real throughput bottleneck**, not the sensor calls. Distance reads take ~1 ms; the radio sustains only ~5 telemetry lines/second. The control loops therefore **buffer samples in RAM and stream them only after the rover stops.**
- A single ground‑truth reading during characterization (bumper at 224 mm while sensor A read 285 and B read 156) exposed that B was unusable and pinned the sensor‑mount‑to‑bumper offset at ~55–61 mm.

**Conclusion:** the **wheel encoder is the only fully reliable channel.** The stop must be executed by encoder dead‑reckoning, using the ultrasonic only as a coarse start reference.

---

## 5. Stopping strategy and the locked program

**Strategy:** measure the start distance once with sensor A (reliable at ~1 m), then drive at full speed and trigger a hard `brake()` purely on **encoder travel**, computed to leave the sensor‑mount ~100 mm from the wall (front bumper ≈ 45 mm, given the ~55 mm mount offset). No live ultrasonic braking — the sensor lags ~80 ms and steps in ~40–90 mm jumps, which would add large timing jitter, whereas the encoder is smooth and lag‑free. Backstops can only make it stop *earlier*: an encoder over‑travel limit, wheel‑stall contact detection, and a time cap. No ultrasonic floor (unreliable up close).

**The locked program (run unchanged for all five operation runs):**

```python
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

def emit(s, v):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n' % (clock.time(), s, float(v)))

FWD_C = -1          # forward = C negative, D positive
FWD_D = 1
MMPD = 0.484        # mm of travel per degree of wheel rotation
BRAKEDIST = 14.0    # mm coasted after brake() from full speed
T_AMOUNT = 100.0    # target sensor-mount distance to wall (mm)
A_OFFSET = 55.0     # sensor-mount-to-bumper offset (mm), for reporting only
SPEED = 1400        # commanded (saturates to true max)

C = Motor(Port.C); D = Motor(Port.D)
A = UltrasonicSensor(Port.A); B = UltrasonicSensor(Port.B)

def rd(s):
    d = s.distance()
    return 9999 if d is None else d

# --- start reference: average sensor A (reliable at ~1 m) ---
sa = 0.0; n = 0; amn = 99999.0; amx = 0.0
for i in range(12):
    a = rd(A)
    sa += a; n += 1
    if a < amn: amn = a
    if a > amx: amx = a
    wait(12)
A0 = sa / n
Ltrig = A0 - T_AMOUNT - BRAKEDIST     # encoder-travel trigger
BACKSTOP = A0 - 75.0                  # emergency: never travel past this

C0 = C.angle(); Dg0 = D.angle()
h0 = hub.imu.heading()

buf_t = []; buf_a = []; buf_tr = []
last_rec = -1000
braked = False; brake_travel = 0.0; brake_reason = 0; brake_t = 0
maxsp = 0.0
last_ct = 0; last_ct_tr = 0.0; contact = 0

# --- full-speed run at the wall ---
C.run(FWD_C * SPEED); D.run(FWD_D * SPEED)
t0 = clock.time()
while True:
    a = rd(A)
    rot = (FWD_C * (C.angle() - C0) + FWD_D * (D.angle() - Dg0)) / 2.0
    travel = rot * MMPD
    sp = C.speed(); asp = sp if sp >= 0 else -sp
    if asp > maxsp: maxsp = asp
    now = clock.time()
    if now - last_rec >= 12:                       # buffer, don't emit (BLE is slow)
        buf_t.append(now); buf_a.append(a); buf_tr.append(travel)
        last_rec = now
    if not braked:
        if now - last_ct >= 40:                    # wheel-stall contact detection
            if travel > 150 and (travel - last_ct_tr) < 4:
                contact = 1; brake_reason = 4
                C.brake(); D.brake(); braked = True; brake_travel = travel; brake_t = now
            last_ct = now; last_ct_tr = travel
        if not braked and travel >= Ltrig:         # PRIMARY: encoder trigger
            brake_reason = 1
            C.brake(); D.brake(); braked = True; brake_travel = travel; brake_t = now
        if not braked and travel >= BACKSTOP:      # emergency backstop
            brake_reason = 3
            C.brake(); D.brake(); braked = True; brake_travel = travel; brake_t = now
        if not braked and (now - t0) >= 3500:      # time cap
            brake_reason = 5
            C.brake(); D.brake(); braked = True; brake_travel = travel; brake_t = now
    else:
        if (now - brake_t) >= 700:
            break
    wait(1)

C.brake(); D.brake()
wait(250)
# --- final reads + onboard estimate ---
sa = 0.0; n = 0; fmn = 99999.0; fmx = 0.0
for i in range(12):
    a = rd(A)
    sa += a; n += 1
    if a < fmn: fmn = a
    if a > fmx: fmx = a
    wait(12)
Afin = sa / n
rotf = (FWD_C * (C.angle() - C0) + FWD_D * (D.angle() - Dg0)) / 2.0
final_travel = rotf * MMPD
amount_final = A0 - final_travel            # encoder estimate of mount distance
pred_bumper = amount_final - A_OFFSET       # onboard gap estimate
max_mms = maxsp * MMPD
dhead = hub.imu.heading() - h0
encbrake = final_travel - brake_travel

for _ in range(2):                          # summary first (survives BLE cutoff)
    emit("R_A0", A0); emit("R_A0min", amn); emit("R_A0max", amx)
    emit("R_finaltravel", final_travel); emit("R_amountfinal", amount_final)
    emit("R_predbump", pred_bumper); emit("R_Afin", Afin)
    emit("R_maxmms", max_mms); emit("R_dhead", dhead)
    emit("R_reason", brake_reason); emit("R_contact", contact)
    emit("R_encbrake", encbrake)
    wait(5)

# ... prints + downsampled buffer emit + {"event":"end"} sentinel ...
```

Every run braked on the **primary encoder trigger (reason 1)** with the stall detector never firing — mechanically, the program did exactly what it was told.

---

## 6. Reconciliation and root cause

Back‑computing the true start of each run as **`measured gap + encoder travel`** gives 965, 973, 972, 970, 976 mm — i.e. the rover started at the **same ~970 mm every run**, and the **encoder travel was accurate on all five** (that consistency is only possible if the odometry is right).

That isolates the fault precisely:

| Run | Start reading A0 (mount, mm) | True start (mount ≈ bumper+55, mm) | A0 error |
|----:|-----------------------------:|-----------------------------------:|---------:|
| 1 | 1025 | ~1020 | ok |
| 2 | 1023 | ~1028 | ok |
| 3 | 833 | ~1027 | **−194** |
| 4 | 822 | ~1025 | **−203** |
| 5 | 815 | ~1031 | **−216** |

- The **stopping method (encoder dead‑reckoning) worked perfectly** — verified by the consistent implied start and by runs 1–2 landing within ±6 mm of truth.
- The **mount‑to‑bumper offset assumption (55 mm) was correct** — runs 1–2 imply 49–60 mm.
- On **runs 3–5 the ultrasonic start reading under‑read the true ~970 mm start by ~195–216 mm.** Because the brake trigger is anchored to that reading, the rover stopped ~200 mm too early. A's per‑run spread was tight (e.g. [813–818]) yet **confidently wrong** — the worst kind of sensor failure, and one a within‑run consistency check cannot catch because a constant offset cancels out of rate/slope comparisons.
- Every error was in the **safe direction** (stop farther), so no run contacted the wall.

---

## 7. Lessons / what I would change

1. **The start reading was a single point of failure.** The whole stop hinged on one absolute ultrasonic sample of a channel I already knew was flaky. That is the correct thing to change first.
2. **The adaptivity backfired.** I sampled the start every run to absorb start‑position variation — but the start barely varied (~970 mm ± a few mm across all five), and the sampling depended on the unreliable sensor. **A fixed dead‑reckoning travel, calibrated once against ground truth, would have landed all five runs at ~44 mm**, because the start was consistent and the encoder is accurate. Adding complexity to solve a problem that wasn't really there introduced the failure.
3. **Cross‑check the absolute reference.** Options: require agreement between A, B, and the rear sensor E (E→wall + measured wheelbase should reconstruct the front distance); reject a start reading that disagrees with the operator's nominal start by more than a threshold; or add a physical start‑line switch. Any of these would have flagged the ~200 mm under‑reads on runs 3–5.
4. **A mid‑approach *absolute* gate** (not just a slope check) comparing A's value to the encoder‑predicted position at a known point would catch a constant bias; a slope/rate check alone does not.

---

## 8. Bottom line

The rover met the hard constraint on every run (**5/5 no contact**) at full speed, and when its start reference was valid it stopped **~40–50 mm from the wall** — close, controlled, and accurately self‑estimated. The dead‑reckoning and calibration were sound and the encoder was flawless. Three runs were spoiled not by the stopping logic but by an intermittent, confidently‑wrong absolute reading from a sensor known to be unreliable — a vulnerability that a fixed (rather than per‑run‑sensed) stopping distance, or a cross‑checked start reference, would remove.
