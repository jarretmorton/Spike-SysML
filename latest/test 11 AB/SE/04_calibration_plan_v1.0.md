# Calibration Plan — Wall-Approach Rover (WAR)
**Document:** CP-WAR | **Version:** 1.0 | **Type:** PLAN (forward-looking; revised and re-issued — prior versions retained — whenever a characterization run reveals something this version did not anticipate) | **Gate:** A
**Inputs:** RS-WAR v1.0 (requirements, TBD register) · 02_wall_rover_model_v1.0.sysml · 03_wall_rover_eam_v1.0.py (EAM; structural audit PASS: 52 requirements, 45 edges ≡ spec tree, all reachable)
**Planned spend:** **2 program runs** (R-CAL, R-VER) + **1 operator measurement** (M1). Anything beyond arrives only via a revised plan version or an approved Anomaly Report.

---

## 0. Sensitivity analysis (required table)

Produced by the EAM (`SWEEP`): each parameter varied one-at-a-time across its **stated prior** (the assumed ranges below are inputs to this review) while the controller's beliefs stay at prior midpoints — except where the design measures the value in-run (adaptive rules, marked). Objective = final gap; every negative shift is simultaneously erosion of the no-contact margin. Baseline: all parameters at prior midpoints with correct beliefs → final gap = `G_target` (35 mm used for the sweep). Dispersion-role parameters shift nothing on average and enter `σ_stop` by RSS; their entry shows the ±1σ contribution at the prior's high edge.

| Parameter | Assumed range (prior) | Objective/margin sensitivity (gap shift at lo / hi edge, mm) | Current-knowledge tier | Resulting priority |
|---|---|---|---|---|
| `k_odo` (odometry, m/rad) | 0.0172 – 0.0573 | **+197.5 / −36.8** (span 234) | T0 (prior only) | **P1 — bind first.** Contaminates in-run `v̂` (linearly) and the braking-belief term (quadratically), and drives DR. Bound onboard: US-vs-encoder slope fit + rest-delta cross-check (T2). |
| `v_max` **if NOT adapted** (design row) | 0.25 – 0.80 m/s | +51.2 / −74.5 (span 126) | — | Design justification: a fixed-speed-assumption trigger is untenable across the prior (and across battery drift). **FUN-3 therefore computes the trigger from in-run measured `v̂` every tick** — see the `v_max` row below for the result. |
| `a_brake` (effective decel) | 1.5 – 5.0 m/s² | −49.5 / +14.8 (span 64) | T0 | **P1 — bind.** Three full-speed brake events in R-CAL, distance measured on the US channel (true distance, slip included) (T2). |
| `o_us` (US mounting offset) | −10 – +50 mm | +30.0 / −30.0 (span 60) | T0 | **P1 — the ONLY quantity no onboard channel observes absolutely.** Biases the scored gap 1:1. This is where the single costed operator measurement (M1) is spent, at the operating point (T3). |
| `tau_us` (US data age) | 10 – 80 ms | +18.4 / −18.4 (span 37) | T0 | **P2 — bind.** Dynamic cross-correlation of US-position vs encoder-position during cruise (T2). |
| `U_refresh` (US update interval) | 10 – 100 ms | +11.8 / −11.8 (span 24, **naive trigger**) | T0 | **P2 — designed out:** FUN-3 dead-reckons the fused gap between US samples, collapsing update-interval quantization to the loop rate (residual < 1 mm). Value still bound in R-CAL S0 (T2) to validate the design. |
| `t_chain` (loop-half + command latency) | 9 – 35 ms | +6.8 / −6.8 (span 14) | T0 | P3 — bind (trigger-tick → decel-onset timing, tick log) (T2). |
| `sigma_b` (braking dispersion) | 3 – 10 mm | dispersion ± up to 10 (RSS) | T0 | **P2 — the floor of `σ_stop`.** 3 samples in R-CAL, +1 at R-VER; small-sample inflation applied. |
| `T_loop` (loop period → trigger jitter) | 8 – 30 ms | dispersion ± up to 4.5 (RSS) | T0 | P3 — bind (tick log). Mean effect lives in `t_chain`. |
| `psi_run` (heading deviation) | 0 – 3° | 0 / −4.2 (corner-clearance erosion) | T0 | P3 — margin erosion via `halfWidth·ψ`; R-CAL heading data decides the trim gain `k_p` (TBD-12; 0 if drift within allocation). |
| `sigma_us` (US noise) | 1 – 5 mm | dispersion ± up to 3.5 (RSS; 2-sample trigger confirm ÷ √2) | T0 | P3 — bind (static window + rest windows). |
| `half_width` (corner arm) | 60 – 100 mm | −1.6 / −2.6 (span 1.0, at nominal ψ) | T0 | P4 — bounded prior suffices; enters only multiplied by ψ. No measurement requested. |
| `v_max` (with in-run adaptation, as designed) | 0.25 – 0.80 m/s | +0.0 / −0.0 | T0 | P2 — gap-insensitive once adapted (the point of FUN-3); still bound (plateau ×3) for CMP-M1/STK-2 closure and battery-drift tracking. |
| `r_min` (US validity floor) | 40 – 80 mm | 0 / 0 (validity only) | T0 | P3 — gates the rest-estimate channel, not the stopping physics; DR fallback (SYS-12) removes criticality. Lower-bounded in R-CAL S5. |
| `G0_start` (start distance) | 900 – 1100 mm | **0 / 0** | context | P4 — **zero leverage: the trigger is absolute in gap, so the start distance cancels. No operator measurement of it is requested (absence by sensitivity).** |

**Reading.** Pre-calibration, the stop point is uncertain by ~±100+ mm — dominated by `k_odo`, `a_brake`, `o_us`, `tau_us`. All but `o_us` are bindable onboard at T2 in one instrumented run; `o_us` is exactly the "high-leverage, no-onboard-channel" case the method reserves the costed measurement for. Two design consequences are locked in by this table and carried into the program skeleton: **(a)** the trigger law spends latency and braking distance from in-run measured `v̂` (kills the 126 mm no-adaptation span; residual sensitivity flows into `k_odo`, which we bind), and **(b)** the fused gap is DR-propagated between US samples (kills the 24 mm update-interval span). A sensitivity sweep ranks WHERE TO LOOK; it does not validate the model — only the M1 operating-point anchor and the impossible-reading rule do that.

**Margin-sizing preview** (EAM `size_margin`, illustrative until Gate B binds real values): contributors {offset-anchor residual 3.0, brake run-to-run 7.0, τ residual 3.0, k residual 1.8, trigger quantization 2.9, US noise at trigger 2.1, corner residual 1.4, unmodeled floor/battery 3.0} mm → RSS `σ_stop` ≈ 9.7 mm → `G_target = 3σ` ≈ **29 mm**; Monte-Carlo cross-check: P(contact per run) ≈ 0.12 %, P(any contact in 5) ≈ 0.60 %.

## 1. Calibration input list

**(a) Requirement-TBD register** — the 20 TBDs of RS-WAR §6, each already bound to an activity in this plan; closure evidence lands in the Calibration Report at Gate B. (Not repeated here; §6 of the spec is normative.)

**(b) Model-completion parameters** — needed by the EAM to predict, named by no requirement:

| Parameter | Why the model needs it | Binding |
|---|---|---|
| `σ_v` run-to-run speed dispersion | Feeds `σ_stop` (residual after adaptation) | 3 plateaus in R-CAL + R-VER plateau |
| Battery voltage per run | Covariate explaining plateau drift across runs | Logged each run (S0) |
| Launch-slip disposition | Whether DR is trusted during the ramp (it need not be — US is live there) | S2–S4: US-vs-ENC residual during ramp |
| US range-linearity residual (80–1000 mm) | Whether one offset constant serves the whole range | S2–S4 slopes + S5 creep map |
| BLE emission throughput | Sizes telemetry decimation vs `emissionBudget` | Measured from S6 dump duration |
| Hold-vs-rest settle time | Sizes the rest-window start delay | S2–S5 rest windows |

## 2. Channel catalog & cross-sourcing

Every quantity to calibrate, ALL independent onboard channels observing it (derived from the rover inventory), ranked by directness and confidence. Every characterization run logs **every** catalogued channel bearing on the quantities that run touches; disagreement is the fault-agnostic fault detector — never assume which channel is wrong.

| Quantity | Channels (ranked) | Bounded validity → hand-off | Binding |
|---|---|---|---|
| Forward gap | 1 usFrontA (direct) · 2 usFrontB (direct, independent) · 3 ENC dead-reckoning from last valid fused fix · 4 usRear delta (conditional — uncontrolled rear scene) | US valid on [`r_min`, ~2000 mm] and fresh; below floor / stale / no-echo → **hand off to DR** (SYS-12), never extrapolate the US | All stages |
| Ground speed | 1 ENC windowed `ω·k̂` · 2 US slope (k-independent, noisier — the cross-check on `k̂`) · 3 IMU accel integral (drifty; logged, never used for control) | — | S2–S4 |
| Distance traveled | 1 ENC · 2 Δ front US · 3 Δ rear US (conditional) | — | S2–S5 |
| Heading | 1 IMU yaw · 2 differential ENC (sign-level cross-check) | — | All |
| Contact witness | 1 IMU forwardAccel spike · 2 US-floor + ENC-stall pattern | — | Armed every run |
| Loop timing | Hub clock (sole channel; jitter statistics) | — | All |

Channels serving no needed quantity drop out (the color sensor already did, at requirements level). `usRear` earns its keep at S0/S2 or is dropped (CMP-R1 verdict at Gate B).

**Physical-plausibility bounds (auto-flagged on every logged channel):** US ∈ [20, 2100] mm and |Δreading|/Δt ≤ 1.5·v̂ + 0.3 m/s; ω ∈ [0, 25] rad/s; |ψ| ≤ 0.35 rad; |accel| ≤ 30 m/s²; clock strictly monotone. Violations are logged as anomalies; impossible-class violations escalate unconditionally (Anomaly Disposition).

## 3. Source-of-truth hierarchy

Trust order, explicit and up front: **T3 operator ground truth > T2 anchored / multi-point onboard calibration > T1 single onboard sample > T0 prior.** Rules in force for the whole campaign:

1. A value set at a higher tier is never silently re-fit to a lower-tier sample; a later disagreeing sample is a **discrepancy to diagnose** (low draw? range dependence? glitch?), not grounds to re-fit.
2. Every calibrated value is carried with its evidence basis: sample count, reference, tier.
3. Any sensor value driving a scored quantity — the final gap above all — is a **hypothesis until confirmed against an independent higher-tier source at the operating point.** M1 is that confirmation.
4. On significant disagreement or any physically impossible reading: **escalate** to better data (higher tier or added independent channel), never arbitrate between suspect channels or explain the anomaly away.

## 4. Characterization-run design

### 4.1 Test-like-you-fly construction

The R-CAL program is a **strict superset of the operation program**: identical control-tick skeleton (read sensors → validate → fuse/DR → trigger check → actuate), identical trigger and braking code path, identical buffered-logging discipline — no stream I/O while motors are commanded (SYS-9); all rows go to a pre-allocated RAM buffer and are emitted after rest (SYS-10, try/finally). R-CAL differs only in: multiple segments, characterization-conservative trigger constants, and richer post-run summaries. What is calibrated therefore transfers to operation with no re-anchor.

Before any flash, the exact MicroPython source is qualified against a **host-side mock harness** (free analysis): a pybricks-API stub driven by the EAM plant, with injected faults — port permutations, opposed/reversed motor signs, census mismatch, US freeze, sub-floor garbage, no-echo ceiling, slow BLE. Pass criteria: no simulated contact in any scenario, correct abort behavior, sentinel on every exit path. This is also the test evidence for SYS-11/SYS-12/FUN-7 logic coverage.

### 4.2 R-CAL stage design (one flash, one run)

Onboard worst-case constants used by R-CAL's own safety logic (pessimal prior edges, hard-coded): `o ≤ +50 mm`, `τ ≤ 80 ms`, `t_chain ≤ 35 ms`, `a ≥ 1.5 m/s²`, `v̂_hi = ω_measured · k_hi` with `k_hi = 0.0573 m/rad`.

| Stage | What happens | Data products (binds / evidences) |
|---|---|---|
| **S0** Census & static (~3.5 s) | Typed try/except construction on all six ports; expect {2 motors, 3 US, 1 color}. Classify the front pair (the two US agreeing within ±150 mm inside [700, 1300] mm), rear = remaining US. 2 s max-rate static burst on all US; IMU static window; battery voltage. **Abort → safe report** on census mismatch or no front pair. | Port map (SYS-13); `U` update interval (TBD-17); `σ_US` static (TBD-16); IMU drift (TBD-18); rear validity pre-check (TBD-20 gate); battery covariate. CMP-U1(static), CMP-U5, CMP-I1. |
| **S1** Sign resolution (~2.5 s, net travel ≤ 60 mm) | Hypothesis ladder of 25 %-duty pulses (0.3 s): (+,+) → fused front Δ ≥ +8 mm decrease ⇒ resolved; increase ⇒ both flipped; |Δgap| small with |Δψ| > 4° ⇒ opposed signs, test (+,−). L/R identity from pivot heading sign. 0.4 s confirmation creep (gap must decrease). **Abort** if unresolved after the ladder. | Sign maps + identity (TBD-14/15). CMP-M3-L/R. |
| **S2–S4** Three full-speed brake events | Per segment: duty ramp 0→100 % over 0.3 s, cruise at 100 %, brake trigger on **raw** min front reading, `hold()`, 0.9 s rest window (US medians, encoder rest, creep watch). Thresholds: S2 fixed **700 mm** (worst-case rest gap ≥ 345 mm), S3 fixed **480 mm** (≥ 125 mm), S4 **self-scaled from the run's own data**: `thr₄ = 170 + o_max + v̂_hi·(τ_max + t_chain_max) + 2·max(d_b measured in S2,S3)` — worst-case rest gap ≥ 170 mm; S4 skipped (fall through to S5) if the two brake samples disagree > 20 mm or the plateau wasn't reached. | `v_max` plateaus ×3 + `σ_v` (TBD-13); `k̂` slope fits ×3 (TBD-8); `a_eff`, `σ_b` from 3 US-measured brake events (TBD-10/10b); `τ̂` cross-correlation ×3 (TBD-7); `t_chain` trigger-tick→decel-onset (TBD-9); `T_loop` + jitter (TBD-11/19); ψ drift under load (TBD-3 input, TBD-12 decision); rear tracking (TBD-20); slip disposition (ramp US-vs-ENC). CMP-M1, M2, M5, U3, H1, R1; SYS-9 by construction. |
| **S5** Creep to near-wall (~4 s) | 15 % duty (v ≈ 0.08–0.12 m/s) to raw min reading **90 mm**, `hold()`, 1.5 s dense rest window. Worst-case rest gap ≥ 90 − 50 − ~19 ≈ **21 mm** (no contact even at pessimal priors); nominal ≈ 50–60 mm — the operating-point regime. US stays ≥ 90 mm ≥ the prior validity-floor ceiling throughout (no reliance on sub-floor readings). | Near-range US map 420→90 mm vs DR (validates the SYS-12 hand-off chain); `r_min` lower bound (TBD-4); rest medians for offsets — **completed by M1** (TBD-5/6); hold/creep (TBD-2). CMP-U4, CMP-U2 (with M1), CMP-M4. |
| **S6** Dump | Onboard derived summaries first (per-segment plateau, brake distances US & DR, rest medians, timing stats, anomaly flags), then decimated buffer + full-resolution event windows, sentinel in `finally`. Motors held through dump. | Emission duration vs budget (CMP-H2); sentinel path (SYS-10); BLE throughput (model completion). |

**Telemetry/BLE budget:** loop target 10 ms; pre-allocated buffer ~2200 rows × {t, usA, usB, usR, θL, θR, ψ, state}. Emission ≈ 900–1200 lines (cruise decimated to ~10 Hz on fused-gap/odometry/heading; 50 Hz windows ±0.25 s around each trigger and 0.6 s into each rest; ~80 summary lines) ≈ 50–65 KB → within the 20 s `emissionBudget` at a conservative 3 KB/s. `run_program` timeout **75 s** for R-CAL (motion ~20 s + emission ≤ 20 s + margin; the task's 10–15 s guidance is applied to the short operation runs, which get 25 s). Charts of forward distance vs time will be rendered from the downsampled telemetry after the run, per protocol.

### 4.3 After R-CAL (free analysis)

Bind all parameters with evidence bases → close the TBD register → compute `σ_stop` (RSS, Tenet A6) → set `G_target = 3·σ_stop` (TBD-1) → freeze the operation program constants → issue **Calibration Report** (static) + **Verification Plan** (frozen EAM output at bound values, predictions only) at **Gate B**.

## 5. Outside-input requests (costed — minimized)

**M1 — the single planned operator measurement.** Timing: immediately after R-CAL ends, **before the rover is moved**. Request, verbatim: *"Without moving the rover from where it stopped: the horizontal distance, in millimetres, from the wall face to the rover's closest forward-most point — one number."*

What this one number buys, per the sensitivity ranking: `ô_A` and `ô_B` at T3 (rest medians minus M1) — the P1 quantity with no onboard absolute channel; validation of the DR final-estimate chain at the same instant (DR estimate vs M1); closure evidence for CMP-U2-A/B; and the **operating-point ground-truth anchor** the objective's Gate C closure requires. Justified absences (no request made): start distance (zero-leverage row), wheel/track geometry (`k̂` bound onboard; `halfWidth` prior suffices), battery (onboard).

Contingency: a second measurement is requested only via an approved Anomaly Report (trigger: M1 vs onboard chain residual > 10 mm, or an impossible-reading escalation).

## 6. Verification support

**Unit verification (CMP) closed by calibration:** every CMP requirement's evidence is produced inside R-CAL — S0: U1(static)/U5/I1; S1: M3-L/R; S2–S4: M1-L/R, M2-L/R, M5-L/R, U3-A/B, H1, R1; S5(+M1): U2-A/B, U4-A/B, M4-L/R; S6: H2. Mock harness: I2 armed-path, plus SYS-11/12 and FUN-7 logic coverage. All roll into the Calibration Report at Gate B — unit verification gates the integrated test (Tenet C1).

**Structure of the verification argument** (predictions open until Gate B): the EAM `EVALUATE` roll-up — all 52 requirement rows, currently 52 OPEN — evaluated at the bound values and the committed configuration IS the frozen Verification Plan prediction: requirement → model → calibrated parameters → predicted performance + margin, with per-requirement predicted PASS/FAIL. The frozen output is not editable; falsification at R-VER → diagnose the responsible parameter, re-bind, re-run the model, issue a NEW Verification Plan version (prior retained), re-run R-VER.

**R-VER construction:** the final operation program, byte-identical to what will be locked — full-speed approach, calibrated trigger `Ĝ ≤ G_target + v̂·t̂_chain + v̂²/(2â)`, hold, rest estimates, emit. One run, testing the frozen prediction. Its brake event also adds the fourth `σ_b` sample.

## 7. Re-plan triggers & anomaly hooks

Issue CP-WAR v1.1+ (this plan revised, prior retained) on any of: census ≠ {2 motors, 3 US, 1 color}; sign ladder unresolved; plateau not reached in ≥ 2 segments; |d_b(US) − d_b(DR)| > 15 mm (slip signature — DR chain demoted); `τ̂` > 90 ms or `U` > 120 ms (loop redesign); more than one US freeze episode; S5 rest reading invalid (offset anchoring falls to the DR chain — plan amended); |ψ| > 3° (trim gain forced on); buffer overflow or emission > budget; |M1 − onboard chain| > 10 mm. Anomaly Reports (free) disposition anything model-conflicting per the standing rule: possible-but-surprising → sensitivity-filtered; impossible → unconditional escalation.

## 8. Budget summary

| Score | Planned | Notes |
|---|---|---|
| Program runs (characterization phase, incl. verification) | **2** (R-CAL, R-VER) | Contingent additions only via revised plan / approved anomaly report |
| Outside-input actions | **1** (M1) | Single number; second only via approved anomaly report |
| Operation runs | 5 (fixed by protocol) | Locked program, unchanged |

*End of CP-WAR v1.0. Awaiting Gate A review.*
