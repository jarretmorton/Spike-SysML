# Calibration Plan — Wall-Approach Rover (WAR)
**Document:** CP-WAR | **Version:** 1.1 (supersedes v1.0, which is retained; changes marked **[v1.1]**) | **Type:** PLAN | **Trigger for revision:** AR-001 (run-1 sign-ladder non-resolution + ground-side BLE start timeout)

This revision changes **procedure, priors, and budgets only**. The requirement set (RS-WAR v1.0), the model (02), the EAM (03), the channel catalog, the source-of-truth hierarchy, the M1 definition and wording, and the verification-argument structure are unchanged from v1.0 and are not repeated here — v1.0 §§1–3, 5–7 remain in force except as amended below.

## 0. Sensitivity table — knowledge-tier updates **[v1.1]**

Run 1 (a safe abort) still bound several rows. Updated tiers; leverage rankings unchanged:

| Parameter | v1.0 tier | v1.1 tier & value | Note |
|---|---|---|---|
| `k_odo` | T0 | T0→**T1 hint**: ~0.2–0.35 mm/deg (12 mm translation / 300 ms 250 dps pulse) | **Prior extended to [0.18, 1.0] mm/deg** — the v1.0 floor (0.30) is likely violated; K_HI = 1.0 remains a valid overestimate everywhere it protects. |
| `o_us` (per sensor) | T0 | T0, **prior extended to [−60, +90] mm** | Rest spread A−B = 118 mm exceeds the v1.0 spread ceiling (60). M1 unchanged as the binding measurement; min-fusion keeps negative offsets conservative; both-high case guarded by CREEP_THR 90→110 and O_MAX 50→90 onboard. |
| `U_refresh` | T0 | **T2: 20–24 ms** (S0 change-interval statistics, 2 s, all three sensors) | Far better than prior; staleness bound tightens to ~3×22 ms. |
| `sigma_us` (static) | T0 | **T2: MAD 2 mm ⇒ σ ≈ 3 mm** at ~1 m | Dynamic component still open (R-CAL v1.1). |
| IMU drift (TBD-18 input) | T0 | **T2: ≤ 0.01°/2 s static** | Excellent; trim-gain decision (TBD-12) still awaits under-load data. |
| Port map / device census (TBD-14/15 partial) | T0 | **T2:** A=US, B=US, C=motor, D=motor, E=US(rear), F=color | Rotation parity = same-sign (twice confirmed) ⇒ forward parity = opposite-sign; which of (+,−)/(−,+) is forward still open. |
| Rear channel validity (TBD-20) | T0 | **T1: invalid at start pose** (no echo, 2000 pegged) | CMP-R1 heading toward drop-by-traceability unless motion segments show tracking. |
| BLE throughput (model-completion) | assumed 3 kB/s | **T2: ≈ 2.2 kB/s** (1263 ms for ~2.8 kB) | Emission re-budgeted at 2.0 kB/s. |
| Battery | — | **T2: 7.59 V** run-1 covariate | Logged per run as planned. |
| `tau_us`, `a_brake`, `v_max`, `t_chain`, `T_loop`, `sigma_b`, `psi_run`, `r_min` | T0 | T0 (unchanged) | Bind in R-CAL v1.1 S2–S5 as planned. |

## 4.2-A. S1 redesign (replaces v1.0 sign-ladder procedure) **[v1.1]**

Root causes per AR-001: (1) translation authority ~0–12 mm vs a ±12 mm threshold (small k + `run()` acceleration ramp); (2) rotations accumulated un-recovered until all rangers lost the wall; (3) a known-rotation hypothesis was re-fired.

New procedure: **probe → parity elimination → heading-restored translation pulses → confirm.**
1. Reference heading `h_ref` recorded at ladder start; after ANY pulse with |Δψ| > 6°, a closed-loop pivot restores heading to within ±3° of `h_ref` before the next step (pivot direction learned from the observed Δψ sign of the rotation parity; ≤ 3 pivot attempts, each ≤ 900 ms).
2. Probe (+,+) at 250 dps × 300 ms. |Δψ| > 6° ⇒ rotation parity = same-sign; pivot back; translation candidates := {(+,−), (−,+)}. Otherwise classify directly (translation candidates := {(+,+), (−,−)} if under-authority).
3. Translation pulses at **360 dps × 500 ms** (second attempt **480 dps × 600 ms**): per-ranger classification unchanged (two decreasing ⇒ fronts + forward = commanded; two increasing ⇒ fronts + forward = −commanded; ±12 mm thresholds; ±400 glitch windows; rotation veto). **Blind-scene rule:** all |Δ| < 12 while encoder travel ≥ 40° ⇒ pivot to `h_ref`, escalate authority, retry — the attempt is not burned.
4. Worst-case forward travel per translation pulse ≤ 180 mm (K_HI bound); ladder forward budget ≤ 2 translation pulses + confirm ≈ ≤ 470 mm ⇒ S2 start ≥ ~450 mm from wall even in the worst corner; S2's own worst-case rest floor (trigger 600) is unaffected.
5. Identity pulse and glitch-aware confirm (both fronts ≤ −6 mm, one retry) unchanged; final pivot to `h_ref` re-squares the rover before S2.

## 4.2-B. Onboard worst-case constants **[v1.1]**

`O_MAX` 50 → **90 mm**; `CREEP_THR` 90 → **110 mm** (worst-case creep rest ≥ ~25 mm even with both offsets at +90; nominal rest unchanged ~50–70 mm); S4 floor formula inherits the new O_MAX (stops ~40 mm earlier — no data product affected). All other trigger constants unchanged; all remain contact-safe under the extended priors (worst-case rest floors: S2 ≥ 205, S3 ≥ 105, S4 ≥ 120, creep ≥ ~25 mm).

## 4.2-C. Telemetry & timing re-budget **[v1.1]**

BLE modeled at **2.0 kB/s** (measured 2.2). Emission trimmed to ~≤ 45 kB (~≤ 900 lines): event windows (trigger−200 ms … rest+100 ms; creep trigger−350…+150), window channels ua/ub/el/er with hd every 4th and ur/st every 6th row; cruise every 10th row (ua/ub/em, hd+st every 30th). `run_program` timeout **90 s** (motion ~26–34 s incl. the longer S1, dump ≤ ~22 s, margin; the task's 10–15 s guidance continues to apply to the short operation runs, planned at 25 s).

## 4.1-A. Mock-fidelity additions (qualification gate for v1.1) **[v1.1]**

New fault axes, all randomized: run-ramp acceleration 700–2600 dps/s (independent of ceiling); k ∈ [0.18, 1.0]; per-sensor o ∈ [−60, +90]; front-ranger echo loss beyond a yaw threshold drawn from 18–40°; BLE 2.0 kB/s; speed ceiling capped at 1400 dps. Directed **as-built scenario** replicating run 1: mirrored parity, k = 0.25, ramp 1100 dps/s, echo loss 25°, o = (+70, −48), U = 22 ms, MAD 2 mm. Pass criteria unchanged (no contact ever, sentinel always, quiet hot path, data products present) plus: as-built scenario must complete all stages.

## 5-A. Outside-input status **[v1.1]**

M1 **unspent** and unchanged (wording, timing per v1.0 §5). It was correctly not requested after run 1 (rover ~1 m out, rotated — not the operating point). AR-001a retry procedure: on a `run_program` start-timeout with no run id and zero events, retry once before escalating to the operator (no flash, no handshake consumed).

## 8. Budget summary **[v1.1]**

| Score | v1.0 plan | v1.1 plan | Consumed so far |
|---|---|---|---|
| Program runs (characterization + verification) | 2 | **3** (R-CAL₁ ✔ consumed, R-CAL₂ v1.1, R-VER) | 1 |
| Outside-input actions | 1 (M1) | **1 (M1)** | 0 |
| Operation runs | 5 | 5 | 0 |

*End of CP-WAR v1.1.*
