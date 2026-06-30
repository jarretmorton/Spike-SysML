# Calibration Report — Wall-Approach Rover (GATE B)

**Status:** Calibration complete. Every TBD from the requirements spec is closed below with its
measured value and the test that produced it. This report and the Pre-Verification Report
(`05_pre_verification_report.md`) together constitute GATE B. The single most important — and
unexpected — result is the **forward-distance sensor offset** (TBD‑01/TBD‑05), which dominates the
achievable closeness.

---

## 1. Calibration runs actually used

The lean plan budgeted one characterization run; hardware reality required more, each fixing a real
defect that would otherwise have caused a contact or a crash in the scored phase. All counts are
honest and carried into the final report.

| # | Run | Outcome | What it produced / fixed |
|---|---|---|---|
| 1 | CHAR‑1 v1 | Failed (veered off wall) | Revealed motor polarity is non-obvious and open-loop driving veers badly |
| 2 | CHAR‑1 v2 | Partial (32° wander) | Heading must be chosen by IMU, not distance; needs closed-loop hold |
| 3 | CHAR‑1 v3 | Clean | Confirmed config; vMax, σ_meas, decel; heading hold to ~9° |
| 4 | Anchor (buffered) | Crashed (MemoryError) | Hub RAM can't hold an unbounded buffer |
| 5 | Anchor v2 (1 emit/loop) | Clean stop | Revealed irregular BLE loop stalls (~240 ms) |
| 6 | Anchor v3 (velocity-aided) | Stalled trigger | Showed the stall is in the *loop*, not the sensor |
| 7 | Anchor v4 (`array`) | Crashed (no `array` module) | Pybricks build lacks `array` |
| 8 | Anchor v5 (pre-alloc lists) | **Clean — the anchor** | Stall-free loop; the calibration anchor + ground-truth measurement |

**Counted characterization program runs: 8. Outside-input measurements: 1** (the true gap at the v5
anchor rest; a 2nd is requested at verification to confirm the offset at close range).

---

## 2. Fixed configuration (determined live, identical across all clean runs)

| Item | Value | Producing test |
|---|---|---|
| Drive motors | 2 (the only motors present) | Port scan (construct-and-catch) |
| Forward sensors | ports **A** (`sL`/"L") and **B** (`sR`/"R") | Closest-agreeing ultrasonic pair |
| Rear sensor (dropped) | port **E** | Outlier of the three ultrasonics |
| Color sensor (dropped) | 1, present | Port scan |
| Straight axis | motor signs **(1, −1)** | Smaller IMU heading change of the two axes |
| Spin axis | motor signs **(1, 1)** | Larger IMU heading change |
| Forward direction | **(−1, +1)** on (A‑motor, B‑motor) | Heading-held direction probe (distance increased on (1,−1) ⇒ flip) |
| Steering sign | slowing motor B **raises** heading | Forward nudge with B slowed (`dB ≈ +20°`) |

Because the wiring is physical and constant, these are **hardcoded** in the locked program (no
re-probing per run), which removes probe-induced disturbance and run-to-run variance.

---

## 3. TBD register — closed

| TBD | Quantity | Calibrated value | Producing test |
|---|---|---|---|
| **TBD‑01** | True gap at anchor rest, `g_char` | **469 mm** (sensor read 346 mm) | Operator ruler at v5 anchor rest |
| **TBD‑02** | Max ground speed, `vMax` | **≈ 443–450 mm/s** | Slope of distance(t) on the clean v5 approach (e.g. 863→458 mm over 354 ms) |
| **TBD‑03** | Sensor refresh / cadence | **variable ≈ 16–60 ms, with occasional ~200–265 ms plateaus** | Inter-update spacing in the raw trace |
| **TBD‑04** | Sensor noise, `σ_meas` | **≈ 1–3 mm** (1σ) | Stationary spread (CHAR‑1 window: A 1015–1019, B 886–905) |
| **TBD‑05** | Braking distance at vMax, `B` | **≈ 54 mm** (true) | Anchor: trigger reading 400 → rest reading 346, offset-corrected |
| **TBD‑06** | Braking variability, `σ_brake` | **est. ≈ 10–12 mm** (to be refined) | Single clean stop; multi-sample deferred to operation |
| **TBD‑07** | Heading drift over approach, `yawDrift` | **≤ 4°** peak (v5), held closed-loop | IMU yaw min/max on the v5 approach (−4° to 0°) |
| **TBD‑08** | Forward-sensor disagreement | **≈ 120 mm** (A reads ~accurate, B reads ~123 mm short) | A vs B at the same true distance (start + rest) |
| **TBD‑09** | Motor `maxSpeed` | **≈ 1015–1066 deg/s** | `Motor.speed()` at full command |
| **TBD‑10** | Min reliable reading, `d_min` | **untested below 343 mm**; flagged | Anchor stopped at reading 343–349; closer range probed at verification |

### The headline result — sensor offset (TBD‑01 with TBD‑08)

The control signal is `min(A, B)`, which is sensor **B**. B reads about **123 mm short** of the true
gap, consistently (additive, slope ≈ 1):

> **true gap ≈ min-reading + 123 mm.** Equivalently, after braking,
> **true rest gap ≈ trigger threshold + 69 mm** (= +123 mm offset − 54 mm braking).

This was verified at two distances (true ~1000 mm ↔ read ~882; true 469 mm ↔ read 346) and is the
binding constraint on closeness (§4 of the C&V plan revisited).

---

## 4. Why this caps closeness (and why that is the safe choice)

`min(A,B)` is the **fail-safe cross-source rule** (FUN‑2): it protects against either sensor ever
reading *long*, which is the failure mode that would cause contact. Here the nearer sensor (B) reads
*short*, so `min` is doubly conservative — the rover always stops ~123 mm farther than the reading
says. The price is that the reading floors out (and is untested) below ~343 mm, so the nearest the
rover can be *commanded* to stop, while still triggering on real sensor data, is roughly **true
120–170 mm**. Going nearer would require either dropping the fail-safe (use only the accurate sensor
A, losing redundancy) or trusting blind dead-reckoning below the sensor floor. Against a hard
no-contact constraint, neither is justified. **Closeness is therefore sensor-limited, not
control-limited** — and the limit is set by a deliberate, documented safety choice.

---

## 5. Locked control law (values fixed; only `THRESH` set at GATE B)

```
trigger when  eff <= THRESH
  where eff = min(raw, est),  est = last_changed_reading − VEL_EST·Δt   (velocity-aided)
        raw = min(sensorA, sensorB),  VEL_EST = 455 mm/s
predicted true rest gap = THRESH + 69 mm
```

Heading hold (PD, KP=24, KD=2.5) on IMU, lead wheel at max, trailing wheel trimmed. Safety: abort on
|heading| > 30°, double-sensor-loss brake, 2.6 s runaway cap, try/finally stop + telemetry sentinel.
Telemetry buffered in pre-allocated lists and dumped after the stop (stall-free loop).

`THRESH` for the verification run is set in the Pre-Verification Report, with its prediction frozen
there.
