# Run 1 Report & Calibration Plan v2

**Part A is a REPORT** — a static record of characterization Run 1 (`run-20260630-231316`); it is not edited after issue.
**Part B is the PLAN revision** (Calibration Plan **v2**) — supersedes the Run-1 design in `03_calibration_plan.md` §2.3; v1 is retained.

---

## Part A — Run 1 Report (what happened)

**Program:** `run1_calibration.py` (Phase 0 enumerate → Phase 1 static ID/noise → Phase 1.5 polarity nudge → Phase 2 logged max approach, safe 500 mm trigger).
**Run outcome:** all phases executed; 285 Phase-2 samples captured; the rover braked safely far from the wall. The run was reported `completed:false` only because the post-stop telemetry flush overran the 60 s host cap (see Finding 5); all 2086 events persisted to disk.

### Findings

| # | Finding | Evidence | Status |
|---|---|---|---|
| 1 | **Port map:** A,B = forward ultrasonics; E = rear ultrasonic; C,D = drive motors; F = color. | `portkind`: A=2,B=2,C=1,D=1,E=2,F=3; `n_motor`=2,`n_ultra`=3,`n_color`=1; only A/B/E emit `static_*`; E reads 2000 (open space) ⇒ rear. | **Locked** (hard-code) |
| 2 | **Polarity:** forward = C:−1, D:+1 (motors opposed-mounted). | Phase-2 encoders monotonic & clean: aC 47→−1051, aD −105→+1008. Nudge 2 (C+/D−) translated with ~0 heading change (dh=+0.7°) ⇒ opposed signs drive straight. | **Locked** (hard-code) |
| 3 | **Motor ceiling** ≈ 1040–1090 °/s; ~1.4% L/R travel imbalance ⇒ ~5° natural drift over the approach. | peak `spd` ≈ −1039 (C), +1091 (D); total travel 1098° vs 1113°; heading drifted −28.5°→−33.9° during Phase 2 (~5.4°, the part **not** from the nudge). | Preliminary; re-measure clean |
| 4 | **Braking wheel-travel D ≈ 30° ≈ ~14 mm** (heading-independent). | Encoder Δ after trigger: aC −1021→−1051 (30°), aD +978→+1008 (30°). Short, tight stop via `brake()`. | Preliminary; confirm w/ ranger |
| 5 | **Telemetry flush too slow.** Full-res dump (~2000 lines over BLE) overran the 60 s cap and cut the `{"event":"end"}` sentinel. | `completed:false`, `duration 60.3 s`, `stdout_tail` empty, spdR 284 vs 285 (last row truncated). | **Fix in v2** |
| 6 | **Forward sensors read 133 mm apart at the "squared" start** (A≈1021, B≈888). Likely a fore-aft mount offset (B mounted ~133 mm forward) or an imperfect square. | `static_A` mean 1021 (1017–1025), `static_B` mean 888 (884–891) — both tight, so not noise. | Classify in Run 2 |

### Root cause of the invalid distance data
The Phase 1.5 nudge commanded **both motors `+`**, which on an opposed-mounted base **spins the rover in place**: nudge 1 rotated it **−28.5°**, and nothing undid that rotation before Phase 2. The approach therefore ran at ~28–34° off-square. Consequences: the forward ultrasonics repeatedly dropped to 2000 (wall out of beam at that angle), and after the trigger fired (B ≤ 500 mm) the min-reading *rose* to 554 mm as the angled body settled — yielding `D_ranger = −54 mm`, which is a geometry artifact, not a physical stopping distance. **The distance channel from Run 1 is discarded; the port map (Finding 1) and polarity (Finding 2) are kept.**

---

## Part B — Calibration Plan v2 (revision)

**Scope of change:** replaces the Run-1 characterization design. Rationale for each change traces to a Finding above. Budget note: Run 1 is spent (score #1); it was diagnostic and yielded the port map + polarity, which v2 hard-codes instead of re-discovering. The δ outside-input anchor (score #2) is **still 1, still unspent** — deferred to a clean squared rest.

### B.1 Changes vs v1

1. **Hard-code the platform map & polarity (Findings 1, 2).** Run 2 constructs only the known devices — forward ultrasonics A, B; motors C, D — and drives with signs C:−1, D:+1. **Phase 0/1/1.5 are removed.** This directly eliminates the nudge, hence the −28.5° spin (root cause).
2. **Straight open-loop max approach from a squared start.** No nudge to corrupt orientation; the rover begins squared and drives straight at max. The residual ~5° imbalance drift (Finding 3) is measured, not corrected — small enough that the ultrasonics keep the wall in beam (unlike 28–34°). *Decision:* operation control law = open-loop max (no heading hold), so calibration matches it (test-like-you-fly). Revisit only if the measured drift proves large enough to threaten the sensor-to-gap relationship or corner clearance.
3. **Dropout-robust trigger (Finding 6 behavior under angle; defensive).** The control uses `min(dA, dB)`; if *both* read 2000 in a cycle, it falls back to the last valid min (never delays the stop — safe for no-contact).
4. **Lean, downsampled telemetry (Finding 5).** The buffer is emitted at every 3rd sample (approach) / every 2nd (settle); headline numbers (D, s_trig, s_rest, drift, ceiling) are computed **on-hub** and emitted as one-shot channels. This keeps the flush well under the host cap. Run 2 timeout set to 40 s.
5. **Pre-approach static A/B check.** 10 static samples of A and B before moving, to classify the 133 mm offset (Finding 6): parallel ⇒ fore-aft mount offset (min() = the forward sensor, and δ is calibrated for it); convergent/divergent under motion ⇒ residual angle.

### B.2 What Run 2 binds (unchanged intent from v1 §1, now on a clean straight approach)
- **cruiseSpeed v_max** — ranger slope of the fused forward distance in the steady region; cross-checked by encoder rate (aC, aD slopes). 
- **D (stopping distance)** — `s_trig_actual − s_rest` (ranger), cross-checked by encoder Δ after trigger × kRot (Finding 4 ⇒ expect ~14 mm).
- **motorCeiling** — peak `motor.speed()` (emitted on-hub), cross-checked by encoder rate.
- **headingDrift** — `heading_rest − heading0` over the straight approach (CMP-5).
- **ranger noise / accuracy (precision part)** — from the pre-approach static A/B samples; **accuracy** still needs the δ anchor.

### B.3 Outside-input (unchanged: 1 planned, unspent)
The single δ ground-truth anchor is taken at a **clean, squared rest** (Run 2's rest if the approach is clean, else a dedicated squared stop), pairing the operator's front-most-point-to-wall measurement with the concurrent onboard forward reading. Still batched with a squareness confirmation. Justification unchanged (no onboard channel observes δ).

### B.4 Unchanged
Everything else in `03_calibration_plan.md` stands: the source-of-truth hierarchy (B.2), the verification-support structure (§4), the operation-program construction (§5, which already assumed hard-coded ports/polarity), and the plan-revision discipline (§6).
