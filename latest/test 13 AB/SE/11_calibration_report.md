# CALIBRATION REPORT — Wall-Approach Rover

**Type:** report (static; not edited once written) · **Closes:** GATE B, calibration half
**Evidence base:** CAL-1 (run-20260729-195903), CAL-2 (run-20260729-203131), M1
**Cost consumed:** 2 characterization runs, 1 outside-input action

---

## 1. TBD register — closed

Tier key: T5 external ground truth > T4 anchored/multi-point onboard > T3 single onboard
sample > T1 vendor > T2 prior. A lower tier never overwrote a higher one; `wallstop_model.bind()`
enforces this and refuses the write.

| TBD | Parameter | Bound value | Tier | Producing test | Evidence basis |
|---|---|---|---|---|---|
| 1 | `omega_cruise` | 860 deg/s commanded, 418 mm/s achieved | T0/T4 | CAL-2 P4/P6 | common regulated speed; achieved speed measured 410.5 and 424.6 mm/s |
| 2 | `k_eff` | **0.4858 mm/deg** | T4 | CAL-1 P2 | 6-point regression of range vs odometry over 620 mm, slope −0.9935, residuals ±6.3 mm; implies a 55.7 mm wheel |
| 3 | `b_offset` | **−29.83 mm** | **T5** | **M1** | 93 mm measured at a reported 128.0 mm, 11.11° yaw → `b_perp` = −21.04 mm, corrected to the 8.04° operational stop yaw |
| 4 | `psi_brake` | **12.64 mm** | T4 | CAL-1 P4, CAL-2 P4+P6 | 3 events, two runs: 12.9, 12.87, 12.14 mm |
| 5 | `sigma_psi` | 0.43 mm | T4 | as above | sample sd of those three |
| 6 | `l_sensor` | **66 ms** | T4 | CAL-2 P4+P6 | `o_consistency` → 62 and 69 ms; independently confirmed by `psi_ranger − psi_odo` = 16.6 and 20.1 mm |
| 7 | `sigma_ls` | 4.95 ms | T4 | as above | sd of the two estimates |
| 8 | `t_refresh` | 21.8 ms | T4 | CAL-1 P4 | 37 fresh samples in 808 ms |
| 9 | `q_range` | 2 mm | T4 | CAL-1, CAL-2 | minimum nonzero step between consecutive fresh samples |
| 10 | `a_brake` | 7425 mm/s² (0.76 g) | T3 | CAL-1 P4 | back-solved from psi at cruise; used only for the first-order speed correction |
| 11 | `t_chain` | 12 ms | T3 | CAL-1 P4 | deceleration onset in the theta trace |
| 12 | `psi_head` (stop yaw) | 8.04° | T4 | CAL-2 P4+P6 | −8.27° and −7.80° |
| 13 | `d_psi_head` | 0.33° | T4 | as above | half-range |
| 14 | `sigma_est` | see §3 | T4 | derived | two independent estimators, both emitted per run |
| 15 | `eps_scale` | 0 by construction | T4 | CAL-1 P2 | folded into `k_eff`; the model works in reading space |
| 16 | `d_odo_drift` | 0.007 | T4 | CAL-1/CAL-2 staircases | residual scatter over sweep length |
| 17 | `slip_brake` | 0 | T4 | CAL-2 | odometry and ranger agree over the brake once latency is removed |
| 18 | `d_agree` | 312 mm, erratic | T4 | CAL-1, CAL-2 | port B: −158, −312, −693 mm and a final no-echo → **monitor only** |
| 19 | `r_min_valid` | 40 mm | **T1 vendor** | **not verified** | CAL-2's fine staircase stopped at 128 mm reported; below that is unexercised |
| 20 | `w_half` | 60 mm | **T2 prior** | not measured | deliberately unmeasured (low leverage); enters only the yaw correction, ±20 mm → ±1.06 mm |

Two entries are **not** closed at a satisfactory tier and are carried forward openly: `r_min_valid`
(T1, unexercised below 128 mm) and `w_half` (T2). Both are argued in §3 and §4 rather than hidden.

## 2. The two findings that mattered

**`l_sensor` was wrong by 3× and was hiding an 18.6 mm systematic.** The GATE A prior was 0–120 ms;
I tightened it to 22 ms before CAL-2 on the physical argument that staleness cannot much exceed one
sample period. That argument was wrong — the true value is 66 ms, about three periods. Running with
22 ms, CAL-2's approach 2 stopped 20 mm closer than its 220 mm command. At the 12 mm operating target
that same bias is contact on every run. It was invisible in any single channel: it surfaced only
because two independent estimators of the same stop disagreed (odometric 219.9 mm, static 199.9 mm),
and was then confirmed by a second, unrelated channel pair. This is the case cross-sourcing exists for.

**`b_offset` is yaw-dependent, and the naive reading of M1 is wrong by 5.2 mm.** M1 was taken at
11.11° of yaw; the operation stops at 8.04°. Since the front-most point is the leading corner and the
ranger reads along its own line of sight, `G = r·cos ψ + b_perp − w_half·sin ψ`. The naive `G − r` =
−35.0 mm would have stopped the rover 5.2 mm closer than commanded — a 43% error at a 12 mm target.
The yaw-aware form predicts approach 2's stop, a pose M1 never saw, to **1.4 mm**; that residual is
carried in the budget as a measured term rather than a guessed one.

## 3. CMP unit verification

| Req | Statement | Method | Evidence | Verdict |
|---|---|---|---|---|
| CMP-1 | left motor sustains its ceiling | test | CAL-1: 872 deg/s at `run(10000)` | **PASS** |
| CMP-2 | right motor sustains its ceiling | test | CAL-1: 928 deg/s | **PASS** |
| CMP-3 | reach cruise inside the runway | analysis+test | s_accel ≈ 87 mm of a ~850 mm runway | **PASS** |
| CMP-4 | primary ranger bias vs the front-most point | test | M1, T5, yaw-aware | **PASS** |
| CMP-5 | ranger timing: refresh, staleness, quantisation | test | 21.8 ms, 66 ms, 2 mm | **PASS** |
| CMP-6 | odometry scale | test | `k_eff` 6-point fit, ±1% | **PASS** |
| CMP-7 | secondary ranger agrees within bound | test | port B −312/−693 mm, final no-echo | **FAIL → dropped to monitor-only by traceability** |
| CMP-8 | trigger timing resolution | test | 1 ms wait granularity; CAL-2 fused trigger fired as computed | **PASS** |
| CMP-9 | plausibility bounds fire | inspection+test | CAL-1 flag 64 (o-drift) and CAL-2 flags 256/512 all fired correctly | **PASS** |
| CMP-10 | dead-reckoning / odometric backstop | test | CAL-1 and CAL-2 P4: `trigger_src` = 2, braked at the commanded travel | **PASS** |
| CMP-11 | brake travel and its scatter | test | 12.64 ± 0.43 mm, n=3 | **PASS** |
| CMP-12 | no post-stop motion | test | static blocks after each stop show no drift | **PASS** |
| CMP-13 | heading sensing | test | IMU vs differential odometry across the brake agree to 0.13° | **PASS** |
| CMP-14 | wheel-speed symmetry | test | +0.65% and −0.31% after the fix (was +6.2%) | **PASS** |
| CMP-15 | device type identification | test | 2 motors C/D, 3 rangers A/B/E, 1 colour F, both runs | **PASS** |
| CMP-16 | drive polarity identification | test | mirrored detected, sign flipped, correct both runs | **PASS** |
| CMP-17 | rest-range estimator valid at the stop | test | predicted rest reading 41.8 mm vs a 40 mm floor, and unverified below 128 mm | **MARGINAL — see below** |
| CMP-18 | odometric estimator | test | CAL-2 approach 2: 219.92 mm against a 220 mm command | **PASS** |
| CMP-19 | contact detection channel | test | forward acceleration logged through every brake; 0.76 g decel signature clean | **PASS** |

**CMP-17 is the one genuine weakness.** At a 12 mm target the predicted reported range at rest is
41.8 mm, just above the 40 mm vendor floor, and CAL-2 never exercised the ranger below 128 mm. So the
static estimator may be invalid exactly where it is needed. This does **not** affect the stop itself —
the trigger's last inputs sit at 82–130 mm of range, comfortably valid — only the onboard *estimate*
of where the rover ended up. SYS-7 is therefore closed on the **odometric** estimator, which needs no
rest reading, with the static one demoted to a cross-check that may legitimately read invalid. Both
are emitted every run so the close-out can state which was used.

## 4. Excluded elements — absence verified, not assumed

| Element | Verdict | Evidence |
|---|---|---|
| Rear ranger (port E) | dropped | read 2000 mm (no echo) at every pose in both runs — it observes no quantity the requirements need, and that saturation is what now classifies it |
| Reflectance sensor (port F) | dropped | 36% and 32% floor reflectance; no requirement traces to it, the start pose is operator-fixed |
| Secondary forward ranger (port B) | demoted | CMP-7 failed on evidence; retained as a logged monitor only |

## 5. What CAL-2 leaves open

- `r_min_valid` unverified below 128 mm reported (CMP-17 marginal) — mitigated by the redundant estimator.
- `w_half` unmeasured — ±20 mm of prior contributes ±1.06 mm to the `b_offset` yaw correction, carried in the budget.
- One-pass yaw-null still leaves ~2° and the approach starts ~4–8° off square. Absorbed into `b_offset` because M1 was taken in the same skewed regime; the run-to-run *variation* (0.33°) is what enters the budget.
- `flags` = 768 in CAL-2: a no-echo run inside an approach (recovered, `n_bad` = 0 at both brake commands) and a no-echo during the creep which correctly truncated two staircase-A steps. Both guards behaved as designed; the corrupted staircase-A cost a `k_eff` confirmation, not its binding.
