# ANOMALY REPORT AR-003 — ranger A's zero moved between runs

**Document** AR-WALLSTOP-003 · **Type: REPORT (static)** · Triggered by the T4 anchor `g_measured(C2) = 222 mm` · Free analysis

**This is the report of a calibration failure that was mine, and that the ground-truth measurement caught.** My committed onboard estimate was 25 mm. The truth was 222 mm. The error is 197 mm and it was **entirely in the safe direction**, which is the only reason nothing was damaged.

---

## 1. What the anchor forces

Ranger A read **89 mm at the trigger**. The rover then braked and came to rest with the wall measured at **222 mm**. Braking travel `B` is necessarily positive, so the true gap at the trigger was `222 + B`, and

> **c_A = 89 − (222 + B) = −133 − B**

`c_A` is **negative for every physically possible B**. In C2, ranger A under-read the true gap by ≈175 mm. There is no value of the braking distance that rescues the GATE B calibration of `c_A = +10 mm`.

**The ranger's *scale* is sound.** Over the approach it reported 728 mm of travel against odometry's 734.3 mm — 0.86 % apart, and most of that is the known sensor lag. It measures *change* correctly. Only its *zero* is wrong.

## 2. The odometry chain checks out against ground truth

Taking only the operator's guarantee that the start line is a constant ~1000 mm:

| Step | Value |
|---|---|
| Odometry (rolling, validated) to trigger | 734.3 mm |
| ⇒ true gap at trigger | 265.7 mm |
| ⇒ true braking travel | **43.7 mm** |
| Odometry saw of that braking travel | 14.9 mm = **34 %** |
| C1's independently measured skid capture | **37–39 %** |
| ⇒ predicted final gap | **222.0 mm** vs measured **222.0 mm** |

Three quantities that were never fitted to each other agree: the skid fraction from C1, the braking overshoot from the lumped `t_eff` (45.7 mm predicted vs 43.7 mm derived), and the ground truth. **The odometry chain is consistent with reality; the ranger's absolute reading is not.**

## 3. Did `c_A` change, or was C1 wrong?

Reading C1 under the same 1000 mm start line gives `c_A = +15 mm`, and that value independently explains two C1 observations it was not fitted to:

- the creep, starting at ranger 718 (true 703) and driving 698 mm, predicts a stop at a **5 mm** gap — i.e. genuine wall contact, which is what the stall detector reported;
- the 40 mm clamp should begin at odometry 678 mm; observed 657 mm.

So C1 is coherent at `c_A ≈ +15` and C2 is coherent at `c_A ≈ −175`. **Ranger A's zero moved by ≈190 mm between the two runs.**

**Leading hypothesis, and it indicts my own test design:** C1 *ended* by creeping the rover into the wall and stalling the motors against it. That was my deliberate manoeuvre, chosen to obtain a physical zero. The most likely thing that shifted the sensor is the impact I commanded to calibrate it. **The calibration manoeuvre destroyed the calibration it produced** — and because the offset only enters as a constant, nothing in C1's own telemetry could reveal it.

*Alternative not excluded:* C1's start was genuinely ~1190 mm and its creep stalled 195 mm short of the wall. This fits C1's numbers slightly less well and contradicts the operator's constant-setup guarantee. It is recorded, not dismissed — and it does not change the disposition, because both readings say the same thing about what to do next.

## 4. Disposition

**Ranger A is withdrawn as an absolute distance channel.** It has now shown three failure modes — a 40 mm clamp (AR-001), a yaw-induced freeze (AR-002), and a 190 mm zero shift (here). A channel whose calibration constant moves by 190 mm between runs cannot carry a scored quantity.

**It is retained for the one property that survived every test: relative travel.** `u(0) − u(t)` was accurate to 0.86 % in C2 and ~1 % in C1, across both runs, regardless of the zero. The re-derived estimator uses only that:

> **g = S − max( odometry_travel , ranger_travel )**

offset-free by construction, and conservative — it takes whichever channel says the rover has gone further. This restores SYS-8 cross-sourcing on a property the sensor has actually demonstrated, rather than one it was assumed to have.

## 5. Re-bound parameters (T4-anchored)

| Parameter | Was (GATE B) | Now | Basis |
|---|---|---|---|
| `c_A` | +10.0 mm | **withdrawn** | unstable across runs |
| `S` start gap | not modelled | **1000 mm (TBD)** | operator guarantee + C2 anchor |
| `B` braking overshoot | 46.5 mm (ranger units) | **43.7 mm true** | C2 ground truth |
| `t_eff` = B/v | 0.09661 s | **0.09232 s** | as above |
| Odometry rolling scale | 0.482 mm/deg | unchanged, validated 0.86 % | C2 |

## 6. Re-derived margin budget

| Contributor | 1σ (mm) |
|---|---|
| **Start-line repeatability `S`** | **8.0** |
| Odometry rolling over ~900 mm | 4.5 |
| Braking overshoot run-to-run | 3.0 |
| Yaw corner advance (7.4° worst) | 3.0 |
| Trigger phase | 1.4 |
| **RSS σ_gap** | **10.2** |
| **3σ contact margin ⇒ G** | **31 mm** |

`S` now dominates, and it is the **one quantity no onboard channel can observe**. Being wrong about it produces contact directly: if the marked line is really 1035 mm, a design targeting 31 mm lands at −4 mm.

## 7. Recommendation

1. **Do not proceed to operation.** VP v1.0 is falsified; the design is re-derived and must be re-verified.
2. **ESCALATE `S` to the higher tier: request the operator-measured start-line distance.** This is the textbook case from my own GATE A framing — the highest-leverage parameter, at tier T0, that no onboard channel can pin down. My inference bounds it only to ±15 mm, and I have just demonstrated that my inference can be 197 mm wrong.
3. Then issue **VERIFICATION PLAN v1.1** with a frozen prediction, take one re-verification run, and request the final-gap measurement at the new operating point to close the objective.

**Outside-input cost:** 3 total (222 mm gap already taken; start-line distance; final gap after re-verification). Above the plan's budget of 2. I am spending the extra one deliberately: the last time I closed a dominant parameter on onboard evidence alone, the answer was wrong by 197 mm.
