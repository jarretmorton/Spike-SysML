# VERIFICATION REPORT — WallStop

**Document** VR-WALLSTOP-001 · **Type: REPORT (static)** · **GATE C** · Evidence: C1–C4 + 3 operator measurements
**This is the single place every requirement is closed.**

---

## 1. Result of the verification run (C4, `run-20260807-124956`)

| | |
|---|---|
| Trigger | **reason 1** — the modelled trigger. No failsafe fired. |
| Trigger at odometry | 936.8 mm (predicted 933.3) |
| Speed at trigger | 487.3 mm/s |
| **Predicted final gap (frozen, VP v1.2)** | **23.0 mm** |
| **Operator-measured final gap** | **14.0 mm** |
| Residual | −9.0 mm = **−1.20 σ** |
| 1σ band 15.5–30.5 | outside |
| 3σ band 0.5–45.5 | **inside → HELD AT 3σ** |
| Contact | **none** |
| Heading at rest | −2.88° · encoder divergence −1.4 mm · rest speed 0.0 mm/s |

**VP v1.2 is NOT falsified.** A −1.2σ residual is what a correctly-sized σ produces; it is not evidence of bias. This is the first prediction in the programme to survive contact with ground truth.

## 2. What the second anchor did to the model

| | C2 | C4 |
|---|---|---|
| Δ (post-trigger travel) | 43.67 mm at 473.1 mm/s | 49.23 mm at 487.3 mm/s |

Mean **46.45 mm, sd 3.93 mm (n = 2)** — against a σ_Δ of **4.00 mm** budgeted at GATE B′ before either value was known. The budget was right.

**A speed law was NOT fitted to these two points.** The implied exponent is Δ ∝ v⁴, which is unphysical: a 3 % speed change cannot produce a 13 % change in braking travel. The difference is run-to-run scatter, and fitting it would be exactly the unfalsifiable elaboration tenet A2 forbids. Δ is carried as a constant plus noise.

**Updated expectation at the locked configuration:** realised gap = G + t_eff·v − sampling overshoot − Δ = 23.0 + 45.0 − 2.7 − 46.45 = **18.9 mm**, σ = 7.47 mm, P(contact) = 0.57 % per run, **2.8 % across five runs**.

## 3. Decision: the locked program is NOT changed

| Option | E[gap] | P(≥1 contact in 5) | Cost |
|---|---|---|---|
| **G = 23 (as verified)** | **18.9 mm** | **2.8 %** | none |
| G = 27 | 22.9 mm | 0.6 % | +1 run, +1 measurement, unverified artifact |
| G = 31 | 26.9 mm | 0.08 % | +1 run, +1 measurement, unverified artifact |

Raising G buys ~2 % of contact probability at the cost of a fifth characterisation run, a fourth measurement, 4–8 mm of the objective, **and** operating an artifact different from the one that was verified. **rev D is locked unchanged.** The five operation runs will execute the exact binary that produced the 14 mm result.

## 4. A specification defect I have to own

**SYS-1 as written is ambiguous.** "The rover's final clearance shall be no less than the contact margin" does not say whether *final clearance* means the predicted value or the realised one.

- On the **realised** reading: 14.0 < 22.4 → FAIL.
- On the **design** reading (predicted clearance ≥ 3σ): 23.0 ≥ 22.4 → PASS.

The realised reading is **incoherent as a requirement**: when the design sets the expected gap equal to 3σ, roughly half of all realisations fall below 3σ by construction. A requirement that every realisation exceed the margin cannot be satisfied by any margin-based design. So the design reading is the only self-consistent one, and it is what the model evaluates.

I record this as a defect in my own specification rather than quietly picking the reading that passes. The requirement should have read: *"the **predicted** final clearance shall be no less than the contact margin."* The realised value (14.0 mm) is stated explicitly here so no reader has to take the verdict on trust.

## 5. Requirement closure — every requirement, with method, evidence, verdict

Method: **T** test · **A** analysis · **I** inspection · **GT** external ground truth

### Stakeholder
| ID | Method | Evidence | Verdict |
|---|---|---|---|
| STK-1 | A+T | roll-up of all children below | **PASS** |
| STK-2 no contact | GT | C4 measured 14.0 mm clearance; no contact in any of C1–C4 at speed | **PASS** |
| STK-3 complete stop | T | rest speed 0.0 mm/s; odometry static for 900 ms; IMU at rest | **PASS** |
| STK-4 maximum speed | T+I | commanded 1000 deg/s = rated ceiling; achieved 473–498 mm/s; source inspected | **PASS** |
| STK-5 minimise gap (objective) | GT | 14.0 mm measured, from 222 mm at the previous configuration | **PASS (graded)** |
| STK-6 repeatable ×5 | A | run-to-run σ measured, not assumed: Δ sd 3.93 mm (n=2), braking odometry sd 0.6 mm (n=5) | **PASS** |

### System
| ID | Method | Evidence | Verdict |
|---|---|---|---|
| SYS-1 clearance ≥ margin | A+GT | predicted 23.0 ≥ 3σ 22.4 (design reading, §4). Realised 14.0 mm — below the margin, above zero | **PASS** (design reading; defect recorded) |
| SYS-2 trigger on prediction | T | C4 fired on reason 1 at odo 936.8 vs 933.3 predicted | **PASS** |
| SYS-3 at rest | T | 0.0 mm/s, cross-checked by IMU accel | **PASS** |
| SYS-4 approach at maximum | I+T | reduce-only trim; no speed reduction for safety anywhere in the source | **PASS** |
| SYS-5 heading | T | rev C bounds corner advance ≤12 mm; C4 = 3.3 mm at 2.88°. **Rev B FAILED at C2 (7.43°)** — relaxation justified in VP v1.1 §4 | **PASS at rev C** |
| SYS-6 onboard estimate | T | three estimates emitted per run; primary chain 18.2 mm vs 14.0 measured (+4.2 mm) | **PASS** |
| SYS-7 no cross-run state | I | every reference established at run start; no persisted state read | **PASS** |
| SYS-8 independent fallback | I+T | **no independent distance channel exists** — three ultrasonic sensors, none trustworthy (AR-004). Retained: encoder L/R cross-check (−1.4 mm at C4), gross-heading abort | **PARTIALLY MET** |

### Function
| ID | Method | Evidence | Verdict |
|---|---|---|---|
| FUN-1 sense clearance | T | 189 cycles at 11–12 ms, zero invalid samples | **PASS** |
| FUN-2 estimate speed | T | v_meas logged every cycle | **PASS** |
| FUN-3 stopping distance | I+A | StoppingDistance reproduced in flight code | **PASS** |
| FUN-4 assert trigger | T | fired within one cycle; sampling overshoot 4.79 mm ≈ one cycle of travel | **PASS** |
| FUN-5 command at maximum | I | `run(DIR*VCMD)` at the rated ceiling | **PASS** |
| FUN-6 apply braking | T | brake() on trigger; Δ = 46.5 mm mean | **PASS** |
| FUN-7 hold heading | T | peak 2.4°, rest −2.88° | **PASS** |
| FUN-8 log off hot path | I | zero stdout writes in the control loop, verified programmatically | **PASS** |
| FUN-9 validity-check channel | I+T | clamp gate active; ranger cannot gate the stop | **PASS** |
| FUN-10 references at start | I | angles, heading, clock all zeroed at run start | **PASS** |

### Component
| ID | Method | Evidence | Verdict |
|---|---|---|---|
| CMP-1/2/3/4 ranger offset, refresh, clamp gate | — | effector withdrawn from the design (AR-004); no requirement traces to ranger A's measurements | **N/A — absence by traceability** |
| CMP-5 travel scale | T+GT | k = 0.482 mm/deg; chain validated end-to-end against two ground-truth points | **PASS** |
| CMP-6 max speed achieved | T | 487.3 mm/s at C4 | **PASS** |
| CMP-7 stopping lump | T+GT | Δ = 46.45 ± 3.93 mm, two T4 anchors | **PASS** |
| CMP-8 response latency | T | within bound | **PASS** |
| CMP-9 heading drift | T | 2.88° at C4 | **PASS** |
| CMP-10 loop period | T | 11–12 ms ≤ 25 ms | **PASS** |
| CMP-11 port/polarity self-check | I+T | devices confirmed; no-motion abort armed. **Start-clearance element descoped** — it used the withdrawn ranger and could abort a scored run | **PARTIALLY MET** |
| CMP-12 trim reduce-only | I | `cl = VCMD − max(0,red)` | **PASS** |
| CMP-13 rear ranger | — | deleted at spec rev B | **N/A** |
| CMP-14 IMU at-rest indicator | T | 3-axis accel at rest | **PASS** |

**No requirement is left asserted-without-evidence.** Two are honestly short of full satisfaction — SYS-8 and CMP-11 — both for the same cause: the rover's ultrasonic sensors are not trustworthy enough to gate a stop, and I would rather record an architecture limitation than claim a redundancy that does not exist.

## 6. Objective closure

The objective is closed **here**, on GT evidence at the operating point: predicted 23.0 mm, **measured 14.0 mm**, no contact, residual −1.20σ. It is not deferred to operation.

## 7. Falsify → diagnose → re-derive trail

| Version | Prediction | Outcome | Root cause | Response |
|---|---|---|---|---|
| VP v1.0 | 37.0 mm | **FALSIFIED** — measured 222 mm | ranger A's zero unstable (AR-003) | withdrew the zero, dead-reckon from a measured start line |
| VP v1.1 | 23.0 mm | **FALSIFIED** — failsafe at 700 mm | spurious ranger sample tripped the cross-check (AR-004) | withdrew the ranger entirely |
| VP v1.2 | 23.0 mm | **HELD at 3σ** — measured 14.0 mm | — | lock unchanged |

Four anomaly reports, three plan revisions, one specification revision, and one requirement relaxation — each recorded with its evidence.

## 8. Budget

| | GATE A plan | Actual |
|---|---|---|
| Characterisation runs | 2 | **4** |
| Outside-input actions | 1 | **3** |

The overrun is attributable to a distance sensor that failed six distinct ways. The GATE A sensitivity analysis put the ranger offset at priority 4 with tier T0 and said a costed measurement would earn its price there; it did — twice.
