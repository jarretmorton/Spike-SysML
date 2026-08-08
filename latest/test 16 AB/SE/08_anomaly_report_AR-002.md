# ANOMALY REPORT AR-002 — C2 verification run

**Document** AR-WALLSTOP-002 · **Type: REPORT (static)** · Run `run-20260807-113932` · Issued before any ground-truth data is requested

**RECOMMENDATION UP FRONT: HALT the progression to operation. Escalate to the higher-tier source, then re-derive and re-verify.** The frozen prediction in VP v1.0 is falsified on three of its four stated criteria.

---

## 1. The impossible observation

| | Trigger | Rest | Change |
|---|---|---|---|
| Ranger A reported | 89 mm | **92 mm** | **+3 mm** |
| Odometry | 734.3 mm | 749.3 mm | +14.9 mm |
| Heading | +1.11° | **−7.43°** | 8.5° of yaw |

The rover advanced at least 14.9 mm after the brake command — and odometry *under*-reports braking travel (it captured 38 % of it in C1), so true travel was ≈39 mm. Ranger A reported the wall getting **farther away**.

A rest reading beyond the trigger reading is named explicitly in ANOMALY DISPOSITION as physically impossible. **Escalated unconditionally**, without consulting the sensitivity ranking — asking the model whether its own falsification is worth chasing is asking the wrong model.

## 2. When the channel failed

The full-rate braking trace — which exists only because AR-001 A-4 was fixed before this run — localises it exactly.

Approach, per ~42 ms sample: `20, 25, 20, 18, 20, 25, 15, 19, 20, 19, 16, 13` mm. Ranger A tracked cleanly at ~20 mm/sample right up to the trigger.

After the trigger: `89, 89, 92, 92, 92 …` — **92 for ~60 consecutive samples over 600 ms, spread exactly 0.0 mm.** The channel did not drift, drop out, or clamp to its 40 mm floor. It **froze**.

This is a third distinct failure mode for the same device, after the 40 mm clamp (A-1) and B's dropouts (A-2). It is not the clamp: the clamp value is 40, this is 92.

## 3. Root cause — one cause, two failed requirements

Braking yaw grew from +1.1° to −7.4°, because one wheel locks before the other under `brake()` (already logged in C1 as A-5, at 3.5° and 1.0°). A forward ultrasonic ranger tilted 7.4° off the wall normal reflects its specular return away at ~14.9°. At ~43 mm of sensor-face range the returned energy collapses and the device stops updating.

**SYS-5 and SYS-6 did not fail independently — the heading failure caused the sensing failure.** The GATE B analysis treated the yaw only as an 8 mm geometric term on the gap; it did not model yaw as a *sensing* failure mode. That is the modelling error.

**Why C1 could not have caught it:** C1's stops were at ~600 mm, where the same tilt still returns a usable echo. The failure exists only at the operating point. This is what a verification run at the operating point is *for*, and it is the argument for never closing the objective on characterisation data alone.

## 4. Frozen prediction vs outcome (VP v1.0)

| Quantity | Predicted | Actual | Verdict |
|---|---|---|---|
| Final clearance | 37.0 mm | ~24.9 mm (est.) | within 3σ — **pending ground truth** |
| Rest reading `u_A` | 47.0 mm | **92.0 mm** | **FALSIFIED** |
| Heading at rest | 4.91° | **7.43°** | **FALSIFIED — SYS-5 exceeded by 2.43°** |
| Valid onboard estimate | yes | **no** | **FALSIFIED — SYS-6 not met** |

VP v1.0 flagged SYS-5's 0.09° of margin as one of four honest weaknesses: *"a slightly harder skid on one wheel could push heading past the limit… it will not be waved through."* It did, and it is not being waved through.

## 5. Onboard estimates — reconciliation

| Channel | Estimate | Status |
|---|---|---|
| Ranger A at rest | 82.0 mm | **REJECTED** — frozen channel |
| Odometry, uncorrected | 57.7 mm | ignores the measured skid |
| Odometry, C1 skid factor applied | **33.4 mm** | independent of the rest reading |
| Model back-out from the trigger | **33.3 mm** | independent of the rest reading |

The two channels that do **not** use the rest reading agree to **0.1 mm**. The rejected channel disagrees with them by 49 mm. Under the source-of-truth rule the frozen single reading does not overwrite two converging independent estimates — but neither is above a T4 check, which is precisely what is now required.

## 6. Requirement status after C2

| Req | Verdict | Basis |
|---|---|---|
| SYS-1 no contact | **UNCONFIRMED** — believed held (~25 mm), cannot be closed onboard | ranger unusable at the operating point |
| SYS-5 heading ≤ 5° | **FAIL** | −7.43° measured |
| SYS-6 valid onboard estimate | **FAIL** | rest channel frozen |
| SYS-3 complete stop | PASS | rest speed 0.72 mm/s |
| SYS-4 maximum speed | PASS | 473 mm/s at the rated ceiling |
| CMP-4 clamp gate | PASS but **insufficient** | gate rejects ≤42 mm; a freeze at 92 passes it |

## 7. Recommendation

1. **HALT.** Do not proceed to the five operation runs. Running an unchanged program whose onboard estimate is known-invalid would produce five close-out estimates that are wrong by ~50 mm, and would rest SYS-1 on an unverified channel.
2. **ESCALATE to the higher-tier source now.** Two onboard channels agree at ~33 mm and one says 82 mm; no further onboard reasoning can adjudicate that. This is the budgeted single operator measurement, requested at the planned point — after the verification run, at the operating point.
3. **Then re-derive** (not tweak): add a staleness/freeze detector to the validity gate, reduce braking yaw, and re-issue **VERIFICATION PLAN v1.1** with a new frozen prediction, followed by one more verification run.

Estimated additional cost: **1 run + 0 further measurements** beyond the one now requested — the reserve already carried in Calibration Plan v1.1 §3.
