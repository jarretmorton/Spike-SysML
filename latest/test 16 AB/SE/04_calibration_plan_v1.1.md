# CALIBRATION PLAN — WallStop · **Version 1.1**

**Document** CP-WALLSTOP · **Type: PLAN** (revised and re-issued after C1; **v1.0 retained** as the record of what was planned before hardware) · **Supersedes:** v1.0

## Change log v1.0 → v1.1

C1 revealed five things v1.0 did not anticipate. Each forces a change to the forward plan.

| # | What v1.0 assumed | What C1 showed | Change to the plan |
|---|---|---|---|
| 1 | The rangers' bounded range would be covered by an **odometry hand-off** | Wheels skid under `brake()`; odometry captures only 37–39 % of braking travel, and the clamp region is entered *during* the skid | **The hand-off does not exist.** The ranger clamp becomes the binding constraint on the objective; the target gap is now set by SYS-6, not SYS-1 |
| 2 | Two forward rangers = two independent channels for one quantity | Ranger B implies a face 100 mm ahead of the rover's foremost point — impossible; drops out mid-range | Single-channel operation on ranger A; **CMP-2 rewritten**, spec to rev B |
| 3 | Out-of-range readings **drop out** (→2000) | Ranger A **clamps** at a constant 40 mm and keeps reporting | Validity gate re-specified `42 < u < 1900`; plausibility bound "monotone vs odometry" retained as the detector that caught it |
| 4 | `t_response` and `a_brake` separately calibratable | Not identifiable at one operating point (yields negative deceleration) | Model collapsed to the identifiable lump `v·t_eff`; `a_brake` left **unbound** |
| 5 | Logging off the hot path was handled | 12 post-trigger `emit()` calls blinded the rover for 311 ms across the braking transient | Emits moved after the rest-logging loop in the locked program |

**Unchanged and vindicated:** the speed-adaptive trigger (§0.2 of v1.0), the batched single-run design, the decision to spend exactly one operator measurement at the operating point, and the plausibility bounds — which are what caught items 1–3.

## 0. Sensitivity analysis — revised ranking

The v1.0 table ranked by prior leverage. C1 has now collapsed most of it. The four top-ranked v1.0 parameters (`a_brake`, `k_travel`, `t_response`, `c_offset`) entered the answer **only** through the lump `Q(v) = c + v·t_response + v²/(2a)`, exactly as v1.0 §0.3 argued — and C1 measured `Q` directly rather than its parts.

| # | Parameter | Post-C1 status | Residual leverage on the objective | Tier | Priority |
|---|---|---|---|---|---|
| 1 | `c_A` ranger A offset | bound 10.0 ± 4.6 mm | **1:1 on the final gap** — largest term | T3 | **anchor at C2 (T4)** |
| 2 | `t_eff` lumped response | bound 0.0966 ± 0.0083 s | ±4.0 mm on the gap; **1 df only** | T3 | anchor at C2 |
| 3 | ranger clamp (40 mm) | bound, hard | **sets the achievable gap floor at 37 mm** | T3 | closed |
| 4 | yaw at rest | 4.91° worst | ±2.5 mm, and SYS-5 passes by 0.09° | T3 | monitor at C2 |
| 5 | `a_brake` | **unbound by decision** | zero — suppressed from the model | — | declined |
| 6 | `k_travel`, `alpha_scale` | co-carried in ranger units | ~0 — the scale cancels in the trigger comparison | T3 | closed |

**What this justifies:** nothing further to characterise. The two remaining soft parameters are both anchored by the *same* single measurement at the operating point, which is the measurement v1.0 already budgeted. No additional characterisation run is planned.

## 1. Calibration inputs — status

All TBDs closed except **TBD-17** (gap at the operating point, T4, pending C2) and **TBD-05** (`a_brake`, deliberately unbound). TBD-02 and TBD-15 are void — their effectors dropped by traceability. See the Calibration Report.

## 2. Characterisation method — amendments

**Channel catalog.** Ranger B: demoted to monitor. Rear ranger: dropped. Colour sensor: remains dropped. The clearance quantity now has ranger A (primary) and odometry (fallback for approach-phase dropout only — explicitly **not** valid through braking).

**Source-of-truth hierarchy: unchanged and load-bearing.** It is what prevented the 40 mm clamp reading from overwriting the 26-point T3 regression — a 30 mm error on the final gap, in the contact direction.

**Plausibility bounds:** all retained; add "ranger reports an identical value on ≥3 consecutive samples while odometry advances" as an explicit clamp detector.

**Test-like-you-fly:** strengthened. C2 runs the *identical artifact* that operation will run, not a superset.

## 3. Remaining run design

| Run | Purpose | Programs | Outside input |
|---|---|---|---|
| C2 | Verification of the frozen prediction, at the operating point | 1 | **1** (TBD-17, the only one) |
| reserve | Only if C2 falsifies VP v1.0 | +1 | +1 |

**Revised total: 2 characterisation runs, 1 outside-input action** — unchanged from the v1.0 budget.

## 4. Verification support — unchanged in structure

CMP leaves are unit-verified in the Calibration Report §3. System-level requirements close at GATE C. The objective (STK-5 / SYS-1) closes **only** on the C2 ground-truth anchor at the operating point.
