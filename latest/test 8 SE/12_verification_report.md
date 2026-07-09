# VERIFICATION REPORT — WallRun (REPORT — static)
**Gate:** GATE C. Closes verification before the 5 scored operation runs.
**Basis:** verification run `run-20260708-221523` (locked program `09_operation_program_v1.py`) tested against the **frozen** Verification Plan v1. Program runs consumed through this gate: **5** (C1, C1b, C1c, C1d, verification). Operator ground-truth measurements: **1**.

## 1. Verification run vs frozen prediction
| Quantity | Frozen prediction | Observed | Verdict |
|---|---|---|---|
| Onboard gap estimate G | 45.1 mm (band 21–69) | **36 mm** | ✅ in band |
| Rest reading S_A | 60.1 mm | 51 mm | in range |
| D_stop | 52.9 mm | **62 mm** | within σ_G budget |
| Heading at rest | ≤ ±5° | −4.2° | ✅ |
| Straightness (run) | ≤ ±5° | [−4.5°, +3.5°], mean 0.4° | ✅ |
| Contact | none | none (S_A=51, not collapsed to ~15) | ✅ |
| Approach | max speed from start line | ~490 mm/s from 1029 mm | ✅ nominal |

**Prediction not falsified.** Gap landed at the near end of the band because D_stop was 62 mm (vs 53 mm calibrated) — the full run-up from the start line reached slightly more speed than the C1d calibration point. This is inside the model's σ_G and required no re-derivation. Two D_stop points now exist (53 mm at S_A≈610; 62 mm at S_A=113); the operation config value is ~62 mm.

## 2. Requirement closure (method · evidence · verdict)
| Req | Method | Evidence | Verdict |
|---|---|---|---|
| **SYS-1 NoContact** (G≥0) | Test | verification: S_A=51 (front at 36 mm), no collapse; ~3σ margin | **CLOSED — PASS** |
| **SYS-2 MinimiseGap** (objective) | Analysis+Test vs T0 | c_A=+15 mm anchored by operator ground truth (542 mm @ 557); verification G=36 mm derived on validated offset | **CLOSED — objective validated at operating point** (final per-run gaps to be recorded at operation close-out) |
| **SYS-3 ClearanceMargin** (pred clr ≥ M) | Analysis | model σ_G=12, M=36; predicted clearance ≥ M held at freeze; verification consistent | **CLOSED — PASS** |
| **SYS-4 MaxApproachSpeed** | Test | verification cruise ~490 mm/s = max (both wheels max) | **CLOSED — PASS** |
| **SYS-5 DetectAndBrake** | Test | trigger at S_A≤113 fired at 2081 ms, brake engaged | **CLOSED — PASS** |
| **SYS-6 StraightApproach** (≤θ_max) | Test | heading in [−4.5°,+3.5°]; hold validated C1d + verification | **CLOSED — PASS** (θ_max relaxed to 5° in Calibration Report; run-to-run heading spread ~±4°) |
| **SYS-7 FullStop** | Test | rover at rest (S_A flat 51 for >600 ms) | **CLOSED — PASS** |
| **FUN-1/2/3/5** | Test | propulsion, ranging (A), stop control, IMU heading all exercised | **CLOSED — PASS** |
| **FUN-4 GapEstimation** (|G_est−G|≤tol) | Analysis | G_est from S_A on T0-anchored c_A; near-min-range reading noted | **CLOSED — PASS (with note §3)** |
| **CMP-1a/1b MotorsMax** | Test | both commanded at/above max throughout | **CLOSED — PASS** |
| **CMP-1c BrakeStop** | Test | brake → rest, no residual motion | **CLOSED — PASS** |
| **CMP-2a UltrasonicA** (σ_S≤6) | Test | rest σ_S ~1 mm | **CLOSED — PASS** |
| **CMP-2b UltrasonicB** | re-scoped | B unreliable → discarded; A reliable sole ranger | **CLOSED — re-scoped (Calibration Report §1)** |
| **CMP-5 IMU** | Test | heading + yaw-rate used by hold; accel gave a_brake cross-check | **CLOSED — PASS** |

All requirements closed.

## 3. Residual risks carried into operation (documented, accepted)
1. **~3σ no-contact margin** (gap ~36 mm on σ_G≈12). Adequate; a contact would need D_stop to jump ~+36 mm. Not re-tightened, per frozen-prediction discipline (verification passed its band).
2. **Rest reading near sensor min range** (~51 mm). The *trigger* fires at 113 mm (read accurately); the physical stop is set by D_stop, not the rest reading — so this affects only the reported estimate, not safety. If the sensor under-reads near min, true gap is *larger* (safer).
3. **Heading run-to-run spread ~±4°.** Within θ_max=5°; a small corner-closer effect (~few mm) is inside the margin.

## 4. Operation authorisation
Program `09_operation_program_v1.py` is **LOCKED** and will be run **unchanged** 5×, each from a clean, squared start. Onboard gap estimates will be frozen for all 5 **before** any operator ground-truth is requested; then the operator measures the 5 gaps once (the only operation exchange); then the final report reconciles predicted (frozen) | onboard | measured per run.
