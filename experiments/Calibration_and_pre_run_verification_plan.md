# Calibration & Pre-Run Verification Plan — Wall-Approach Rover

**Status:** Pre-flash design (SCAFFOLD). This commits *what* will be calibrated and *how* the
predictive argument will be evaluated — **before any hub is flashed**. Numeric values are TBD; the
structure, channels, run design, and pass logic are fixed here. The numeric evaluation (the
committed prediction) is filled into the calibration record and locked **before** the verification
run (C2 — argue before you run).

**Built against:** `models/wall_run_model.sysml` (the CALIBRATION SURFACE is the intake index) and
`experiments/Wall_run_requirements_spec.md` (the requirement tree). The requirements spec governs;
this plan and the model are realisations of it.

**Vocabulary (this project's framing):** *calibration* binds the surface and verifies CMP/unit
requirements; the **verification run** is the single integrated run that verifies the system-level
requirements against the committed prediction; **operations** is the 5× scored run of the verified
program. Operations is *not* a verification step — no requirement in the set asks for a
repeatability rate, so the 5× runs exercise the verified system rather than verifying a requirement.
(Had we written a "no-contact rate ≥ X over N" requirement, the 5× would sit inside verification.)

**Measure-direct:** the stopping distance is calibrated **directly at the single operating point
v_max** (calibration point = operating point ⇒ zero extrapolation); the deceleration `a`
(`decelCollision`) is back-solved from that point for the feasibility ceiling only. No speed sweep.

---

## A. Calibration input list (Process 4 — two parts)

Calibration must bind **both** origins, exactly the CALIBRATION SURFACE in the model:

**(a) Model-completion** — free parameters the model needs to predict but no requirement names:
| Parameter (model attr) | Meaning | Bound by |
|---|---|---|
| `driveConstant` | m per motor-rad | CMP-M1 — cruise: ultrasonic distance slope ÷ encoder rate |
| `maxMotorSpeed` | matched straight-line max (slower motor) | CMP-M2 — max-speed cruise |
| `tSensorDistance` | forward-sensor sampling latency | CMP-U4 — loop/refresh timing |
| `decelCollision` | deceleration, **back-solved** from Δ_stop at v_max | CMP-M3 — direct stop-distance measure |
| `dSenseMax` | reliable forward sensing range | CMP-U1 — near/far range characterisation |
| `latency.tChain` | compute + BLE + actuation lag (platform) | timing test (no CMP — inherited) |
| *discovery:* port↔device | which device on which port | port probe |
| *discovery:* drive sign / L-R | forward direction + motor labels | CMP-M4 — sign-agnostic motion probe |

**(b) Requirement-TBD register** — a requirement names them (model surface "Requirement TBDs"):
| TBD (model attr) | Requirement | Bound by |
|---|---|---|
| `thetaMax` | SYS-3 | **budget**, set from lateral-clearance geometry; CMP-I1 measures achieved drift *against* it (not itself measured) |
| `sigmaDStop` | SYS-7a | SEM of the direct CMP-M3 stop-distance measurement + latency |
| `sigmaDMeas` | SYS-7b | CMP-U1 range bias/scale + FUN-S4 cross-check residual |
| `sigmaRun` | SYS-7c | **verification-run spread** (system-level, no CMP) — see §E |
| derived `marginM`, `kSigma` | SYS-7/SYS-4 | `marginM` resolves once the σ's bind; `kSigma` is human-set (§D) |

**Not calibration targets** (resolve or are set elsewhere): `brakingThreshold` (SYS-4, derived);
`kSigma` (human-set); run-time/telemetry quantities (`commandedMotorSpeed`, `forwardClearance`,
`finalClearance`, `headingDrift`).

---

## B. Characterisation program — ONE self-contained program, run N× (N≈3–4 for σ_run)

**Program-count rationale (B3, scored).** A single program does discovery **and** the max-speed
calibration; it is re-run only to estimate `sigmaRun`. Note the scoring counts **every flash-and-run
including re-runs of the unchanged program**, so N re-runs cost N on the program-count score —
budget N as the smallest count that gives a usable run-to-run spread. The hub power-cycles between
runs (no carried state), so the program self-discovers every run.

**Per-run sequence (all logged on the hub clock):**
1. **Probe ports.** For each port attempt `Motor()` / `UltrasonicSensor()` / `ColorSensor()`; catch
   the type/`EBUSY` errors; build and emit the device→port map. Construct each device **once**
   (re-construction raises `OSError EBUSY`).
2. **Identify the forward pair vs. the rear — sign-agnostically.** Drive a small motion in an
   *arbitrary* direction and watch the three ultrasonics: the two that **co-vary** (track each other
   as the rover moves relative to the wall) are the forward pair; the odd one out is the rear.
   *This is deliberately independent of drive sign* — the forward pair is identified by mutual
   agreement, not by assuming which way "forward" is.
3. **Drive sign & L/R (CMP-M4).** From the same motion, the sign that **decreases** the forward-pair
   distance is forward; encoder signs label L/R. **Gate:** the max-speed phase begins only after a
   forward direction is confirmed, so a wrong-sign run never drives at the wall at speed.
4. **Max-speed cruise (CMP-M2, CMP-M1).** Command both motors at the ceiling; sustain. Yields
   `maxMotorSpeed`, the cruise slope (→ `driveConstant` against encoder rate), and `tSensorDistance`.
5. **Log every independent channel (B1):** ultrasonic-L, ultrasonic-R, **ultrasonic-rear**, IMU yaw,
   IMU forward-accel, encoder-L, encoder-R, clock.
6. **Safe trigger.** Brake (locked stop) when fused forward distance ≤ **d_trig_cal** (chosen
   ≫ expected Δ_stop, so **no contact risk during characterisation**).
7. **Measure Δ_stop directly (CMP-M3).** The stop distance from detection→rest at v_max, per run;
   the across-run spread is `sigmaRun`; `decelCollision` is back-solved from Δ_stop and the
   independently-timed `tResponse` for the feasibility check only.
8. **At rest,** keep logging forward + rear ~1.5 s (rest readings, `dSenseMax` floor).
9. **End sentinel** `{"event":"end"}`.

**Rear channel (CMP-U5) — the cross-source test2 dropped, kept here.** During the run the rear
ultrasonic is logged alongside the forward pair. If a stable rear reference is present, the rear
delta tracks the forward delta in magnitude (opposite sign) over the approach: calibrate its
bias/scale and **enrol it as an independent distance channel** feeding FUN-S2 / the FUN-S4
cross-check (forward-pair vs. rear vs. encoder odometry). If no usable rear reference is found, the
calibration **flags U5 unavailable** and the cross-source set falls back to forward-pair + encoder
odometry + IMU integration. Either way the result is recorded — keeping U5 means the calibration
*tests* for the rear reference rather than assuming it away.

**What one run yields:** `maxMotorSpeed`, `driveConstant`, `tSensorDistance`, `Δ_stop`
(→ `decelCollision`), `dSenseMax`, forward-channel agreement (CMP-U1 / FUN-S4), rear-channel
calibration or unavailable-flag (CMP-U5), heading drift over the run (CMP-I1), forward-accel
bias/noise (CMP-I2). Repeats give `sigmaRun`.

**Telemetry/chart:** after each run retrieve a downsampled/summary view (not the raw stream) and
chart forward distance vs. time.

---

## C. Closing the sensor bias `b` — two valid methods

Onboard channels close everything except the **sensor-frame-to-true-gap offset** (the CMP-U1 range
bias `b` — what the forward sensor reads at zero physical gap), which no onboard channel can
determine on its own. Straightness is **not** in this gap: the task guarantees a squared start at the
marked line, and IMU yaw + integrated lateral deviation cover SYS-3/SYS-7 onboard. So `b` is the one
quantity needing a deliberate move, and there are two legitimate ways to close it — they trade the
two scored quantities against each other, and either binds `b` to the same value:

- **Method 1 — ruler gap (outside-input).** After a characterisation run leaves the rover stopped,
  request one ground-truth measurement: the gap between the rover's nearest forward point and the
  wall. Closes `b` (incl. mounting offset) and cross-checks the ultrasonic absolute scale against
  odometry. Cost: **one counted outside-input action** (distinct measurements count separately even
  when batched, so only the genuinely un-onboardable one is requested); zero contact risk.
- **Method 2 — creep-to-contact (self-calibration).** Drive the rover slowly to a gentle, controlled
  touch; the forward-sensor reading at contact **is** `b`, self-calibrated with **zero outside
  input**. Cost: a deliberate characterisation touch — which is **not** the scored no-contact metric
  (that is operations-only, §F), so it is permissible — against the small risk of a non-gentle
  contact. Trades the outside-input score to zero for that exposure.

Both are sound; the choice is a score trade (one outside-input vs. one deliberate characterisation
touch). The reference baseline here is **Method 1** for its zero contact exposure; **Method 2** is
the legitimate zero-outside-input alternative an arm optimising the score may well prefer — and a
good example of opportunism the structure channels rather than forbids.

---

## D. Pre-run verification artifact (the centerpiece) — structure now, numbers before the verification run

The artifact **is** the evaluation of the `satisfy`/`require` roll-up in `wall_run_model.sysml`
against calibrated values. Each `□` is filled at calibration; each margin = value − target, signed.

**Predictive chain (relations reproduced from the catalog, evaluated at the operating point):**
```
groundSpeed        = maxMotorSpeed · driveConstant                        [RotationToSpeed]
Δ_stop(v_max)      = measured directly  (≡ groundSpeed·tResponse
                       + groundSpeed²/(2·decelCollision))                  [StoppingDistance @ op. pt]
marginM            = kSigma · √(sigmaDStop² + sigmaDMeas² + sigmaRun²)     [A6 RSS, SYS-7]
brakingThreshold   = Δ_stop + marginM            (sensor trigger = +b)     [SYS-4 trigger def]
predicted finalClearance = marginM               (by construction)
maxFeasibleSpeed   = MaxSpeedFromBudget(tResponse, decelCollision,
                       dSenseMax, marginM)                                 [feasibility ceiling]
```

**Requirement roll-up — verified-by, predicted result, signed margin.** The *verified-by* column is
the layered-verification ledger: CMP rows are **verified at calibration**; SYS rows are **predicted
here** and **verified by the run in §E**.
| Req | Constraint | Verified by | Predicted result | Margin |
|---|---|---|---|---|
| SYS-1 / CMP-M2 | `commandedMotorSpeed ≥ maxMotorSpeed` | calibration | PASS (command the ceiling) | ≥ 0 by construction |
| SYS-3 / CMP-I1 | `headingDrift ≤ thetaMax` | cal (drift) + run | PASS iff drift ≤ budget | `thetaMax − drift □` |
| SYS-4 | trigger at `brakingThreshold` | derived | PASS (predicted) | `□` |
| SYS-5 | `finalClearance ≥ 0` (no contact) | **verification run** + ops | PASS at confidence Φ(kSigma) | `marginM □` |
| SYS-6 | minimise `finalClearance` | operations | graded (objective) | `finalClearance □` |
| SYS-7 | `finalClearance ≥ marginM` | **verification run** | PASS (predicted equality) | `□ ≈ 0` (floor) |
| CMP-M1/M2/M3/M4 | calibrated drive/brake/sign | calibration | PASS iff calibrated values in range | per-CMP `□` |
| CMP-U1/U2/U4/U5 | range bias/scale, min(L,R), refresh, rear channel | calibration | PASS iff calibrated / U5-available | per-CMP `□` |
| CMP-I1/I2 | yaw drift, forward-accel bias/noise | calibration | PASS iff within characterised bounds | per-CMP `□` |
| feasibility | `groundSpeed ≤ maxFeasibleSpeed` | calibration | PASS (else max-straight speed cannot stop in budget) | `maxFeasibleSpeed − groundSpeed □` |
| sensing budget (A6) | `brakingThreshold ≤ dSenseMax` | calibration | PASS | `dSenseMax − brakingThreshold □` |

**Coverage factor `kSigma` (carried prominently — it is the multi-run prediction operations test).**
`kSigma` is chosen so the per-run contact probability Φ(−kSigma) keeps the operations contact
probability acceptably low while trading against gap — e.g. k≈3 → ~0.13%/run → ~0.7% over the 5
operations runs. The committed value, the predicted per-run Φ(−kSigma), and the **predicted
no-contact rate over 5** are stated here as a falsifiable prediction that operations (§F) confirms or
breaks. Final `kSigma` set once the σ's are known.

**Commitment:** the filled table (all `□` numeric, all margins signed, `kSigma` and its predicted
operations coverage stated) is **locked as the committed prediction before the verification run**,
and is never edited afterward (see Records — the frozen artifact).

> **Human gate (merged, two distinct goals).** Before the verification run, one review covers
> **(1) calibration sufficiency** — is each fit physical and adequate to build a prediction on (the
> σ's real, U5 resolved, no eyeballed constants)? — and **(2) the committed argument and the
> verification-run design**. The two are merged for proximity but must be *both* consciously
> discharged; approving the tidy artifact does not stand in for judging calibration quality. No
> hardware actuates on an unreviewed plan.

---

## E. Verification run (Process 6) — one integrated run, verifies the system level

Run the integrated task **once** at v_max with the locked trigger. This is the system-level
verification event: compare actual `finalClearance` to predicted `marginM`, actual `headingDrift` to
`thetaMax`, and the other SYS rows to their committed predictions. Verifying these **adds the
system level to the component level already verified at calibration** — together, all requirements
verified.

**Falsification is real.** If any actual lands outside its predicted band, the run has **falsified**
the prediction: diagnose the responsible parameter (`Δ_stop`? a σ? the bias `b`?) and **re-derive**
— do not empirically tweak the program (A3). Re-run only after the re-derivation.

**Produces the verification record** — the predicted-vs-actual mirror of the §D roll-up (same rows,
plus actual, delta, verdict). This is a **separate** artifact from the frozen pre-run argument.

> **Human gate.** After the verification run, a results-acceptance review confirms the prediction
> held non-spuriously (evidence sound, requirements actually exercised) before operations is locked.

---

## F. Operations (Process 7) — lock and run 5×

Lock the verified program unchanged. It is re-flashed and the hub power-cycled before each of 5
runs. Record per run: **contact (pass/fail)** and **gap**. No outside input during operations.

Operations is not a requirement-verification step — it runs the verified system. It does two things:
it is the **A/B scored data** (no-contact count over 5, gap distribution), and it **tests the
committed coverage prediction** from §D. The **operations report** compares committed vs. achieved
coverage (predicted per-run Φ(−kSigma) and predicted 5-run no-contact rate vs. observed), turning
the coverage factor from an assumption into a confirmed-or-falsified prediction.

---

## G. Record index (the audit trail — each established at a different time, by different evidence)

| Record | Contents | When |
|---|---|---|
| `Wall_run_requirements_spec.md` | requirements, tree, effector selection, structural validation | **done** |
| `wall_run_model.sysml` | tailored model; carries the calibration surface + the **predicted** roll-up | **done** |
| `Calibration_and_pre_run_verification_plan.md` | this document | **done** |
| **Calibration record** | TBD register closed — each value + spread + the test behind it; values bound into the model surface, procedure/raw stay here + logs | after characterisation |
| **Pre-run verification artifact (numeric, FROZEN)** | the §D roll-up filled; **predictions only, never actuals** | committed before the verification run |
| **Verification record** | predicted-vs-actual for the verification run; SYS-level verified | after the verification run |
| **Operations report** | per-run contact + gap; committed-vs-achieved coverage | after operations |

**On where "verified" lives.** The model carries the *predicted* roll-up (structural, legitimately
model-resident). *Demonstrated* status lives in the records above; if the `.sysml` is back-annotated
with verified-status, it carries a flag that **points to** the verification/operations records, not a
transcription of their numbers — so the model and the records cannot drift.