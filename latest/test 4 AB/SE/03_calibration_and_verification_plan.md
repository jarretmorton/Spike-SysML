# Calibration & Verification Plan — Wall-Approach Rover

**Gate:** GATE A — produced after the requirements spec and tailored model, **before any hardware is
touched**. Its job is to fix *what we will measure, with how many runs and how much operator input,
and the exact STRUCTURE of the pre-run argument* — with every predicted number deliberately left
**OPEN** (predictions are committed at GATE B, never here).

**Inputs governed by this plan**
1. the *calibration input list* — every free parameter the model needs a value for, plus the
   requirement TBD register (§1);
2. the *characterization-run design* — one batched program, CHAR‑1 (§2);
3. the *outside-input requests* — exactly one operator measurement, with its cross-checks (§3);
4. the *pre-run argument structure* — the satisfy/require roll-up as a table with predictions TBD
   (§4);
5. the *margin-sizing method* — the A6 root-sum-square and the choice of `k` (§5);
6. *run-count accounting* and the lean-path recommendation (§6);
7. *verification sequencing* (§7).

---

## 1. Calibration input list

Two sources feed calibration: **(A)** the parameters the *model* leaves free (the operands of the
`StoppingDistance` reproduction and the σ-terms of the margin), and **(B)** the requirement **TBD
register** from the spec. They overlap by design; the cross-reference column ties them together.

### 1.A Model-completion parameters

| Param | Symbol | Role in model | How bound | Spec TBD |
|---|---|---|---|---|
| Max ground speed | `vMax` | `WallRover.vMax`; SYS‑1 check; sets sampling-jitter term | CHAR‑1 approach slope of distance(t) | TBD‑02 |
| Sensor refresh interval | `refreshInterval` | `CMP‑RNG‑1`; sampling-jitter term | CHAR‑1 reading-step cadence (Δt between value changes) | TBD‑03 |
| Sensor noise (stationary) | `σ_meas` | margin term | CHAR‑1 motors-off stationary window | TBD‑04 |
| Stopping distance @ vMax | `Σ` | `WallRover.stoppingDistance`; FUN‑5/CMP‑MOT‑2; trigger threshold | CHAR‑1 **direct** (reported ref) + TBD‑01 anchor | TBD‑05 |
| Braking variability | `σ_brake` | margin term (run-to-run) | CHAR‑1 decel-profile cleanliness (bounded); confirmed at verification run | TBD‑06 |
| Sensor static bias | `b` | converts reported↔true at rest | from TBD‑01: `b = reported_final_char − g_char` | (via TBD‑01) |

### 1.B Requirement TBD register (cross-reference)

| TBD | Quantity | Bound by | Closes requirement |
|---|---|---|---|
| TBD‑01 | true gap at CHAR‑1 rest, `g_char` | **operator measurement** (the one outside input) | anchors Σ/`b`; SYS‑2 scale |
| TBD‑02 | `vMax` | CHAR‑1 slope | SYS‑1 / CMP‑MOT‑1 |
| TBD‑03 | `refreshInterval` | CHAR‑1 cadence | CMP‑RNG‑1 |
| TBD‑04 | `σ_meas` | CHAR‑1 stationary window | designMargin (SYS‑5) |
| TBD‑05 | `Σ` | CHAR‑1 direct | FUN‑5 / CMP‑MOT‑2 |
| TBD‑06 | `σ_brake` | CHAR‑1 + verification run | designMargin (SYS‑5) |
| TBD‑07 | `yawDrift` | CHAR‑1 IMU yaw at trigger | SYS‑4 / CMP‑IMU‑1 |
| TBD‑08 | sensor disagreement | CHAR‑1 (both logged) | CMP‑RNG‑2 |
| TBD‑09 | motor `maxSpeed` | CHAR‑1 commanded-vs-clamped | CMP‑MOT‑1 |
| TBD‑10 | min reliable range, `d_min` | CHAR‑1 lowest clean reading | feasibility floor on threshold |

**Every TBD is closed by CHAR‑1 except TBD‑01**, which requires the single operator measurement, and
the *run-to-run* half of TBD‑06, which is confirmed at the verification run. This is what makes the
lean path (§6) sufficient.

---

## 2. Characterization-run design — CHAR‑1 (one batched program)

**Principle (Tenet B3):** one program binds every parameter it can. CHAR‑1 self-determines ports and
motor polarity *live* (it cannot assume conventions), takes a stationary noise window, then performs
one full max-speed approach to a **safe** reported trigger and logs to rest. Telemetry is for
post-hoc analysis only; the *control* uses live reads.

### 2.1 What CHAR‑1 binds

| Step | Action | Binds |
|---|---|---|
| 0 | **Port/role ID** — try-construct each device type on each port, catch failures, build a port→device map; the two forward rangers are the pair reading ≈ start distance (rear ranger reads short/saturated and is excluded). | port map; identity of `fwdSensorL/R` |
| 1 | **Polarity ID** — pulse both motors forward at low speed ~0.3 s, read Δ(min forward distance): closing ⇒ (+,+); opening ⇒ (−,−); ~no net change ⇒ opposite wiring, retry (+,−)/(−,+). ≤2 probe pulses cover all four sign combinations. | drive sign per motor |
| 2 | **Stationary window** — motors off ~0.5 s, sample both forward sensors. | `σ_meas` (TBD‑04); `d_min` sanity (TBD‑10) |
| 3 | **Max-speed approach** — both motors commanded past clamp (max), each loop read `min(fwdSensorL,fwdSensorR)`, **brake both** when ≤ `d_trigger_char`; keep logging distance, heading, accel through to rest. | `vMax` (TBD‑02), `refreshInterval` (TBD‑03), `Σ` (TBD‑05), `σ_brake` seed (TBD‑06), `yawDrift` (TBD‑07), disagreement (TBD‑08), `maxSpeed` (TBD‑09) |

`d_trigger_char` (the CHAR‑1 reported trigger) is set **deliberately large and safe**: **400 mm**. The
safety argument (§2.4) shows the rover stops with a large positive gap there, so CHAR‑1 cannot contact
the wall even though it runs at full speed.

### 2.2 Program logic (pseudocode — single program, try/finally, end sentinel)

```text
emit(name,val):  stdout.write JSON {timestamp_ms: hub_clock, sensor: name, value: val}

# ---- one-time construction (each device claimed ONCE) ----
hub = PrimeHub()
build port->device map by trying Motor/UltrasonicSensor/ColorSensor per port,
    catching errors; classify ports; never re-construct a claimed port.
motors  = the two DriveMotor ports
fwdL,fwdR = the two UltrasonicSensor ports reading ~start distance (exclude the short/rear one)
watch = StopWatch()

try:
    # (1) polarity probe
    for signs in [(+,+), (+,-)]:           # second only if first shows no closing
        d0 = min(fwdL.distance(), fwdR.distance())
        run both motors at signs * LOW for 0.3 s; stop
        d1 = min(fwdL.distance(), fwdR.distance())
        if d1 < d0 - noiseband: FORWARD = signs; break
    # if neither closes, invert: FORWARD = (-,-)

    # (2) stationary noise window
    motors off; for ~0.5 s sample both sensors every loop; emit("d_stat_L"/"d_stat_R", ...)

    # (3) max-speed approach
    command both motors at FORWARD * MAXSPEED      # run(BIG) clamps to ceiling
    loop:
        dL = fwdL.distance(); dR = fwdR.distance(); d = min(dL,dR)
        emit("fwd_min", d); emit("fwd_L", dL); emit("fwd_R", dR)
        emit("yaw", hub.imu.heading()); emit("fwd_accel", hub.imu.acceleration()[forward])
        if d <= D_TRIGGER_CHAR (=400):  break
    brake leftMotor; brake rightMotor          # SAME stop method used in operation
    # settle + log to rest
    for ~0.8 s: emit("fwd_min", min(fwdL.distance(),fwdR.distance())); emit("yaw",...); emit("fwd_accel",...)
finally:
    motors stop
    stdout.write '{"event":"end"}\n'           # sentinel — REQUIRED or samples are lost
```

### 2.3 Telemetry channels logged

`fwd_min` (control signal), `fwd_L`, `fwd_R` (for disagreement TBD‑08), `yaw` (TBD‑07 / SYS‑4),
`fwd_accel` (stop-event + collision cross-source, monitor only), all stamped with the hub clock.
After the run I retrieve **down-sampled/summary** telemetry (not the raw stream — context discipline)
and render the forward-distance-vs-time chart.

### 2.4 Safety argument — why CHAR‑1 cannot hit the wall

A-priori platform physics (used only to prove the 400 mm trigger is safe, not as a calibrated value):
SPIKE motors run on the order of ~1000 deg/s; a ~56 mm wheel gives `vMax` on the order of
**0.4–0.5 m/s**. Reaction travel over a worst-case ~75 ms latency is ~30–40 mm; braking from that
speed adds tens of mm. So expected total stop travel `Σ` is on the order of **~80 mm**, an order of
magnitude below the 400 mm trigger. Predicted CHAR‑1 rest gap is therefore **large (~300 mm-class)**
and positive with wide margin — **no contact even at full speed**. The two-sensor `min` rule fails
safe (a spuriously-long reading cannot delay the trigger past the nearer sensor), and the try/finally
guarantees the motors stop and the sentinel is sent regardless of path. (These are *expectations*; the
actual numbers are what CHAR‑1 measures.)

---

## 3. Outside-input requests (Tenet B4 — human measurement is a costed instrument)

**Exactly one** operator measurement is requested in the whole calibration phase:

| # | Request | When | Closes | Batched cross-checks (no extra runs) |
|---|---|---|---|---|
| 1 | **`g_char`** — true gap from rover's forward-most point to the wall at CHAR‑1 rest, by ruler/calipers | once, immediately after CHAR‑1 | TBD‑01 → anchors `Σ` true scale and sensor bias `b` | (a) confirm "no contact" (Boolean, same look); (b) eyeball lateral offset to sanity-check `yawDrift` sign |

The two cross-checks (a,b) are read off the **same** physical inspection, so they cost no additional
run and are bundled into the single measurement event. No operator input is requested at any other
point in calibration or verification; during the five operation runs the operator provides nothing
until close-out.

**Why one measurement suffices.** Σ in *reported* units comes from CHAR‑1 alone
(`Σ_report = d_trigger_char − reported_final`). The only thing the onboard sensor cannot self-supply is
the **true** scale (its static bias `b`). The single `g_char` anchors that bias; everything else
(threshold, predicted gap, margin) then follows analytically.

---

## 4. Pre-run argument — STRUCTURE (predictions left OPEN)

This is the skeleton of the GATE B centerpiece. The control law and roll-up are fixed **now**; every
predicted cell is **TBD** and will be filled *once* at GATE B from calibrated values, then frozen
before the verification run. **No integrated run result may ever touch a predicted cell.**

### 4.1 The calibrated control law (derivation fixed, values TBD)

Operation triggers a stop when the nearer reported distance ≤ `threshold_op`, with

> **`threshold_op = d_trigger_char + M_true − g_char`**, and the executed trigger is
> **`threshold_eff = max(threshold_op, d_min)`**.

*Derivation.* The trigger-reading → true-rest-gap map is invariant across runs (same speed, latency,
brake). CHAR‑1 fixes one point of that map: triggering at reading `d_trigger_char` yields true gap
`g_char`. Lowering the threshold by δ lowers the reported rest reading by δ, and since `reported =
true + b` at rest with `b` constant, the true rest gap shifts by the same δ. Hence
`true_gap(threshold) = g_char + (threshold − d_trigger_char)`; setting it to the design target
`M_true` gives the formula above. **Predicted true final gap = `M_true` = `designMargin`.** If
`threshold_op < d_min` the stop is sensor-limited and the predicted gap becomes
`g_char + (d_min − d_trigger_char)` instead (contingency, flagged in §6).

### 4.2 Roll-up table (the require/satisfy evaluation, predictions OPEN)

| Spec req | Relation / derivation | Calibrated param(s) needed | Predicted value | Margin contribution | Pass/fail |
|---|---|---|---|---|---|
| **SYS‑1** command at max | direct (run past clamp) | `vMax`, `maxSpeed` | **TBD** | — | **TBD** |
| **CMP‑MOT‑1** cmd ≥ maxSpeed | LowerBound | `maxSpeed` | **TBD** | — | **TBD** |
| **SYS‑2** no contact (gap>0) | `true_gap = M_true > 0` | `Σ`,`g_char`,`d_trigger_char`,`b` | **TBD** | dominated by `designMargin` | **TBD** |
| **SYS‑5** gap ≥ designMargin (bridge) | `true_gap = M_true` ⇒ equality | `designMargin` | **TBD** | self | **TBD** |
| **SYS‑3** minimise gap (objective) | `= M_true` (graded) | `designMargin` | **TBD** | — | n/a (graded) |
| **FUN‑4 / FUN‑5 / CMP‑MOT‑2** Σ within budget | `Σ ≤ threshold_eff − designMargin` | `Σ`,`threshold_eff` | **TBD** | — | **TBD** |
| **SYS‑6** complete stop | `finalSpeed ≤ stopTolerance` | (decel profile) | **TBD** | — | **TBD** |
| **SYS‑4 / CMP‑IMU‑1** heading | `yawDrift ≤ yawMax` | `yawDrift` | **TBD** | lateral term of gap | **TBD** |
| **CMP‑RNG‑1** refresh bounded | UpperBound | `refreshInterval`,`maxStaleness` | **TBD** | sampling-jitter term | **TBD** |
| **CMP‑RNG‑2** sensors agree | UpperBound | disagreement,`agreementTol` | **TBD** | — | **TBD** |

The single predicted number that the whole task turns on — **predicted final true gap = `designMargin`
(±`k·σ_run` worst case)** — is the cell the verification run will test.

---

## 5. Margin-sizing method (Tenet A6)

`designMargin` (≡ `M_true`) is **not guessed**; it is the root-sum-square of the independent
uncertainty contributors, scaled by an assurance factor:

> **`designMargin = k · √( σ_pred² + σ_meas² + σ_run² )`**

| Contributor | What it is | Source |
|---|---|---|
| `σ_pred` | uncertainty in the Σ estimate + the one human measurement + residual model error | CHAR‑1 fit residual ⊕ ruler resolution of `g_char` |
| `σ_meas` | stationary sensor noise (the reading the trigger acts on) | CHAR‑1 stationary window (TBD‑04) |
| `σ_run` | run-to-run spread = sampling jitter ⊕ braking variability: `√[(vMax·refreshInterval/√12)² + σ_brake²]` | TBD‑02·TBD‑03 (jitter) ⊕ TBD‑06 (`σ_brake`) |

**Choice of `k = 3`.** The dominant run-to-run term is `σ_run`. Over five operation runs, a Gaussian
worst-case downside of `k·σ_run`:
- `k = 2` → per-run contact probability ≈ 2.3%, so ≈ 1 − (1−0.023)⁵ ≈ **11%** chance of **≥1 contact**
  across five runs — too high against a hard no-contact constraint.
- `k = 3` → per-run ≈ 0.13%, so ≈ **0.7%** over five runs — acceptable.

`k = 3` is therefore the plan's default. It also buys headroom against `σ_run` not being multi-sampled
before GATE B (only CHAR‑1 + the verification run inform it on the lean path). `k` is revisited once
the σ's are numeric; if `σ_run` turns out large enough that `designMargin` exceeds the closeness we
could otherwise achieve, that trade is surfaced at GATE B rather than silently absorbed.

---

## 6. Run-count accounting & recommendation

Two scores are being conserved: **counted (characterization) program runs** and **outside-input
actions**. The plan minimises both.

| Phase | Counted program runs | Outside inputs |
|---|---|---|
| Characterization | **1** (CHAR‑1) | **1** (`g_char`, with cross-checks batched) |
| Verification | **1** (the integrated run that tests the GATE B prediction; doubles as the first repeatability sample of `σ_run`) | 0 |
| **Total before operation** | **2** | **1** |
| Operation | 5 (the scored runs; identical locked program) | 0 until close-out |

**Recommended path: lean.** One characterization run + one operator measurement + one verification
run. It is sufficient because CHAR‑1 closes every TBD but TBD‑01 (covered by the single measurement)
and the run-to-run half of TBD‑06 (covered by the verification run), and the conservative `k = 3`
absorbs the fact that `σ_run` is not directly multi-sampled before GATE B.

**Contingency (only if a gate fails):**
- *CHAR‑1 polarity/port ID inconclusive, or telemetry lost* → a single re-run of CHAR‑1 (counts).
- *Verification run falsifies the prediction* → per the SE process, diagnose the responsible model
  parameter and **re-derive** (do not empirically tweak the threshold); a corrected verification run
  may be needed (counts).
- *`threshold_op < d_min`* (sensor can't read close enough) → the stop is sensor-limited; predicted gap
  becomes `g_char + (d_min − d_trigger_char)`, still no-contact, and this is recorded at GATE B rather
  than triggering more runs.
- *Optional second characterization run* is held in reserve **only** if GATE B shows `σ_brake`
  dominating and poorly constrained; not taken by default (it would cost a counted run for marginal σ
  refinement that `k = 3` already covers).

---

## 7. Verification sequencing (Tenet A5 / C — components before integration)

Ordered most-directly-observable first, least-coupled first; all the component checks ride on the
**one** CHAR‑1 program, and integration is argued analytically **before** the single integrated run:

1. **Forward-distance channel** — CMP‑RNG‑1 (refresh), CMP‑RNG‑2 (agreement): most directly observed,
   least coupled (trusted-reference-first, B2).
2. **Speed `vMax`** — SYS‑1 / CMP‑MOT‑1: read off the same trace's approach slope.
3. **Heading** — CMP‑IMU‑1 / SYS‑4: independent IMU channel on the same run.
4. **Stopping distance `Σ`** — CMP‑MOT‑2 / FUN‑5: depends on (1)+(2); measured directly at the single
   max-speed operating point.
5. **Sensor bias `b`** — needs the one outside-input anchor (`g_char`); bootstrapped off (1).
6. **Integrated clearance** — SYS‑2 / SYS‑5: composed analytically from 1–5 into the §4 roll-up
   (the Pre-Verification Report, GATE B), **then** tested once at the verification run (GATE C).

---

## 8. What happens at the next gates (so the operator can see the whole arc)

- **After GATE A approval →** request readiness, flash **CHAR‑1**, run, pull down-sampled telemetry,
  render the forward-distance chart, then request the single `g_char` measurement.
- **GATE B (Calibration + Pre-Verification reports):** close the TBD register with each value's
  producing test; fill and **freeze** the §4 roll-up — predictions only.
- **Verification run → GATE C:** run the integrated task once, compare predicted vs actual per
  requirement; if falsified, diagnose and re-derive (no empirical tweak).
- **Operation:** lock the program, run 5×; freeze onboard gap estimates *before* asking the operator
  for ground truth; deliver the Final Engineering Report carrying predicted → onboard-estimated →
  operator-measured for every run.

**A readiness handshake will be requested before every flash — CHAR‑1 included — and no program will be
flashed without explicit operator go-ahead.**
