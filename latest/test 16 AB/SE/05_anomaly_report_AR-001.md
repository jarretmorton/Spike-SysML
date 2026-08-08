# ANOMALY REPORT AR-001 — C1 characterisation run

**Document** AR-WALLSTOP-001 · **Type: REPORT (static)** · Issued after run `run-20260807-111521` · Free analysis; any test it proposes is costed only if approved

Four observations conflicted with the model. Each is classified per ANOMALY DISPOSITION and ends with a recommendation.

---

## A-1 — Ranger A **clamps** at 40 mm rather than dropping out
**Branch: model-contradicting → ESCALATED UNCONDITIONALLY**

**Observation.** In the creep sweep, ranger A decreased monotonically and linearly to 44 mm, then reported exactly `40` for seven consecutive samples while odometry advanced a further 23.7 mm into the wall.

**Why this is model-contradicting, not merely surprising.** The GATE A model treated `r_min_valid` as a *validity bound* — below it the channel was assumed to drop out (→2000) and hand off to odometry. It does not. It returns a plausible-looking small number that is **constant and wrong**. A validity gate written as "reject 2000" would have accepted `40` as a real 40 mm and been silently, confidently wrong at the closest point of the entire mission. The plausibility bound that caught it was *ranger monotonicity vs odometry*.

**Consequence.** The reading of 40 mm at contact — which I initially read as a direct measurement of the ranger offset — is not a measurement at all. Taking it at face value would have put `c_A` at 40 mm instead of 10 mm, a **30 mm error placed directly on the final gap**, in the direction of contact.

**Disposition: ESCALATED, resolved by analysis, no new hardware run.** The offset was re-derived by regressing the *linear* region against odometry and referencing the intercept to the contact point. Validity gate re-specified as `42 < u < 1900` (CMP-4).

---

## A-2 — Ranger B implies a physically impossible geometry
**Branch: model-contradicting → ESCALATED UNCONDITIONALLY**

**Observation.** Ranger B reads 95–129 mm *less* than ranger A across seven independent epochs. Ranger A's offset is calibrated at ≈10 mm. Together these place ranger B's sensing face ≈100 mm **ahead of the rover's foremost point**.

**Why this is impossible, not odd.** The sensor is part of the rover. Nothing can be ahead of the foremost point. This is proof that a load-bearing assumption is false — specifically the GATE A assumption that *"both forward rangers are independent channels observing the same quantity."*

**Corroborating misbehaviour** (each individually only "suspicious"; jointly decisive):
- returned `2000` at the **core-1 trigger instant**, at 650 mm — mid-range, where it should be at its best;
- in the creep it produced excursions of 40 → 160 → 40 mm within 150 ms;
- long `2000` dropout runs between 91 mm and 58 mm of true clearance;
- its A−B difference varies by 34 mm, where a rigid pair on a flat wall must be constant.

Ranger A over the same run: zero dropouts, residual sd 2.7 mm about a straight line over 44–176 mm, rest-reading sd 1.47 mm.

**It did affect a result.** The C1 CORE fused the pair as `min(d1,d2) − c_off` with a *single* offset. Because B reads ~117 mm low, B won the `min()` in core 2 and triggered the stop ~117 mm early. Core 2 is therefore not a clean replicate of core 1 — though the quantity I actually needed from it (Δu measured on ranger A) is unaffected, since it is referenced to A at both ends.

**Disposition: ESCALATED. Ranger B is DISQUALIFIED as a trigger channel.** This is a requirements change, not a code tweak: CMP-2 is rewritten from *"ranger B's offset shall be known"* to the Unwanted form *"the stop decision shall not depend on ranger B"*, verified by inspection of the locked source. B remains logged as a monitor (tenet B1 — a channel that misbehaves is still evidence). No re-run: the diagnosis is complete from existing data.

---

## A-3 — `t_response` and `a_brake` are not separately identifiable
**Branch: model-contradicting (impossible parameter value) → ESCALATED**

**Observation.** Solving `Δu = v·t_response + v²/(2a)` on the two C1 stops (475.6 and 462.2 mm/s) returns **t_response = +0.534 s and a_brake = −554 mm/s²**. A negative deceleration is physically impossible.

**Diagnosis.** The two operating points differ by 2.8 %. The quadratic term has essentially no leverage over that span, so the system is numerically degenerate: the fit trades the linear and quadratic terms against each other without constraint. This is not bad data — it is a **structurally unidentifiable model at a single operating point**.

**Disposition: model revised, not data chased.** Tenet A2 says develop only what calibration can falsify; the split cannot be falsified here, so it is removed rather than fitted. The `RelationTemplates::StoppingDistance` doc note anticipated exactly this case — *"At a SINGLE operating point, measure the stopping distance directly at that point (calibration point = operating point ⇒ zero extrapolation) and back-solve `a` only if a feasibility check needs it."* No feasibility check needs `a`, so **`a_brake` is left UNBOUND and reported as such** (tenet A3 — uncalibrated, not zeroed), and the lump `Δu = v·t_eff` is calibrated directly at the operating point.

**Recommendation: IGNORE (no chase).** Separating the terms would need a deliberate multi-speed sweep, which costs a run and buys nothing: operation runs at one speed, and at that speed the lump is exact by construction. **Explicitly declined.**

---

## A-4 — The braking transient was never sampled (instrumentation defect, mine)
**Branch: surprising but possible → chased, because it bears on a top-ranked parameter**

**Observation.** In the C1 CORE I placed twelve `emit()` calls between `brake_all()` and the post-brake logging loop. Those BLE writes took **311 ms**, during which nothing was buffered. The rover braked and stopped inside that window. The braking profile — the data I intended to use to bind `a_brake` — does not exist.

**Assessment.** This did not corrupt any result: `Δu` is measured from the trigger-instant sample (logged before the emits) and the rest medians (measured after), and both are intact. It cost me the deceleration profile, which A-3 has independently made unnecessary. It is nonetheless a self-inflicted violation of my own "logging off the hot path" rule (FUN-8): I applied it to the *approach* and forgot the *stop*.

**Disposition: FIXED IN THE LOCKED PROGRAM, no re-run.** All post-trigger emits moved after the rest-logging loop. Argument that this cannot affect control: every `emit()` is downstream of `brake_all()` in both versions, so the actuation path and its timing are untouched; only the buffering window changes.

---

## A-5 — Wheels skid under `brake()` (logged, no action)
**Branch: surprising but physically possible → logged and proceeded**

The ranger/odometry travel ratio is 1.019–1.029 while rolling and during the slow creep, but 1.083–1.088 over the whole run. The excess is confined to the braking phase: odometry captures only **37–39 %** of the braking travel. The wheels lock and slide.

**Consequence, which is the one that matters:** the odometry hand-off planned at GATE A to cover the ranger's near-field blind spot **does not exist**. Odometry cannot bridge the clamp, because the clamp region is entered precisely during the skid. The ranger's 40 mm floor therefore **binds the achievable objective**, and the target gap is set by it (SYS-6) rather than by the contact margin (SYS-1). This is the single most consequential finding of C1.

No chase: the effect is fully absorbed in the lumped `Δu`, which is measured through the skid.

---

## Recommendations

| # | Recommendation | Costs a run? |
|---|---|---|
| A-1 | Re-derive `c_A` from the linear region; re-specify the validity gate as `42 < u < 1900` | No |
| A-2 | **Disqualify ranger B** as a trigger channel; rewrite CMP-2; re-issue the spec at rev B | No |
| A-3 | **Decline the chase.** Collapse to the identifiable lump; leave `a_brake` unbound | No |
| A-4 | Move post-trigger emits after the logging loop | No |
| A-5 | Log and proceed; accept the ranger floor as the binding constraint on the objective | No |

**None of the five requires an additional characterisation run.** All are dispositioned by analysis on data C1 already produced — which is what batching the run design bought.
