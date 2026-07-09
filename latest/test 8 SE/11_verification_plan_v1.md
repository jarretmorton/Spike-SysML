# VERIFICATION PLAN — WallRun — Issue 1 (PLAN, prediction FROZEN)
**Gate:** GATE B (with the Calibration Report). Forward-looking. **The numeric prediction below is frozen before the verification run and will not be edited.** If the run falsifies it, I diagnose → re-derive → issue Verification Plan **Issue 2** (this issue retained) → re-run. I never tune values to match a result.

## 1. Committed configuration (the locked program — `09_operation_program_v1.py`)
Executable-model bound values (sensor-A frame): v_max=490, t_lat=0.038 s, a_brake=3500, **c_A=15 mm**, Δt_s=0.030 s, σ_S=1 mm, σ_v=30, σ_t=0.010, σ_a=800, σ_c=3, **d_trig_A=113 mm**, k=3. Control: heading hold gsign=1, MAX_CMD=1000, FF=120, KP=30, KD=4. Trigger: first valid S_A ≤ 113. Safety-only: floor S_A ≤ 80, |heading| > 25°.

## 2. FROZEN numeric prediction (executable-model output at this config)
| Quantity | Predicted |
|---|---|
| Reaction distance `v·t_lat` | 18.6 mm |
| Braking distance `v²/2a` | 34.3 mm |
| **D_stop** | **52.9 mm** |
| **Rest sensor reading S_A** | **60.1 mm** |
| **Final gap G = S_A − c_A** | **45.1 mm** |
| σ_G (RSS) | 11.9 mm — contribs v 5.3 / t 4.9 / a 7.8 / c 3.0 / quant 4.2 / noise 1.0 |
| Required margin M (k=3) | 35.7 mm |
| No-contact margin | **3.78 σ** |

**Acceptance band for the verification run (frozen):** onboard `gap_est` = S_A,rest − 15 within **45 ± 24 mm (2σ)**, i.e. **21–69 mm**; heading_rest within **±5°**; **no contact** (a rest S_A collapsing toward ~15 mm, or invalid/sub-min readings, indicates contact → falsified). Judgement uses the onboard record (S_A reads ~60 mm at rest, comfortably in-range); the single operator measurement is already spent, so no operator input is requested at the verification run.

## 3. Predicted per-requirement verdicts (evaluated set = SysML STRUCTURAL CHECKS block)
| Req | Claim | Predicted |
|---|---|---|
| SYS-1 NoContact | G ≥ 0 | **PASS** (45.1, 3.78σ) |
| SYS-3 ClearanceMargin | predicted clearance ≥ M | **PASS** (45.1 ≥ 35.7) |
| SYS-4 MaxApproachSpeed | commanded ≥ ceiling | **PASS** (run at max) |
| SYS-6 StraightApproach | |heading| ≤ θ_max(5°) | **PASS** (≤2.6° observed) |
| SYS-7 FullStop | v_final ≈ 0 | **PASS** (brake to rest) |
| FUN-4 GapEstimation | |G_est−G| ≤ 15 | **PASS** (S_A tracks; c_A T0) |
| CMP-1a/1b MotorsMax | commanded ≥ ceiling | **PASS** |
| CMP-1c BrakeStop | residual ≈ 0 | **PASS** |
| CMP-2a UltrasonicA | σ_S ≤ 6 mm | **PASS** (~1 mm) |
| CMP-2b UltrasonicB | (re-scoped) B backup only | N/A — B discarded (Calibration Report §1) |

## 4. What the verification run tests (and the two open risks it closes)
Running the exact locked program near the wall tests the frozen prediction end-to-end. It specifically resolves the two residuals from the Calibration Report:
1. **D_stop at the operating trigger** (S_A=113, closer than the C1d calibration point) — confirms v_max was already saturated there, so D_stop≈53.
2. **A second D_stop data point** toward run-to-run scatter (the margin currently assumes conservative scatter on one clean stop).

## 5. Falsification protocol
- **gap_est outside 21–69 mm, or contact, or heading_rest > 5°** → FALSIFIED. Diagnose (most likely: D_stop larger than 53 because v higher at the closer trigger, or run-to-run scatter). Re-derive d_trig_A / margin in the executable model → Verification Plan **Issue 2** with a new frozen prediction → re-run. No value is hand-tuned to the observed stop.
- **Within band, no contact** → verification PASSED → proceed to GATE C (Verification Report) and lock the program unchanged for the 5 operation runs.

## 6. Note on the objective (SYS-2 / closeness)
The objective's ground-truth anchor (c_A, hence G) was validated at T0 against the operator measurement; the frozen G=45 mm is intentionally conservative (3.78σ) to protect **no-contact** across 5 runs given limited run-to-run data. It is not the tightest achievable gap — tightening would require re-locking + re-verifying (more runs); this plan prioritises guaranteed no-contact, then closeness.
