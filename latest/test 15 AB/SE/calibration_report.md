# Calibration Report — Wall-Approach Rover

**Type:** REPORT (static; never edited once written) · **Gate:** B
**Characterization programs consumed: 4** (CAL-1 … CAL-4) · **Operator measurements consumed: 2** (OP-MEAS-1, OP-MEAS-2)

*Correction to an earlier statement in this programme: I said "five programs" after CAL-4. The count is four. Recorded here because the program count is a scored quantity and the error was mine.*

## 1. What changed since the Calibration Plan

The plan projected **2 programs and 1–2 measurements**. Actual: **4 and 2**. The overrun is fully attributable to two of my own defects (AR-001, AR-002) and one genuine discovery (AR-003). The plan is not back-edited; the variance is recorded here.

| # | Program | Outcome | Cause |
|---|---|---|---|
| 1 | CAL-1 | **No usable data.** Discovery nudge spun the rover 35.9°; rangers blind at that yaw; approach aborted on its own fail-safe. | My defect (AR-001) |
| 2 | CAL-2 | Partial. First dynamics, but 32 ms of my own logging delayed the brake, and a −9° yaw contaminated everything. | My defect (AR-002) |
| 3 | CAL-3 | **Clean.** All parameters bound, zero faults, full dump in 14.9 s. | — |
| 4 | CAL-4 | **Clean.** Near-range map, ranger floors, second anchor position. | Genuine discovery: the constant-offset model was wrong (AR-003) |

## 2. AR-003 — the constant-offset model was falsified

Before OP-MEAS-2 I committed a prediction: **91 mm**. Measured: **102 mm**. An 11 mm miss, well outside the ~3 mm measurement resolution.

The offset between ranger A's reading and the true front-face gap is **not constant** — −24 mm at A = 236, −13 mm at A = 115. Refitting on both anchors gives a slope of 0.909, i.e. a scale error, not a fixed sensor recess.

**Consequence had this not been caught:** the trigger would have been set believing the gap was 11 mm larger than it is. At a target gap of ~30 mm that is a third of the budget, and the error is in the direction of contact.

**Why the plan caught it:** section 2.2 rule 3 — *a sensor value driving a scored quantity is a hypothesis until confirmed against an independent higher-tier source at the operating point*. One anchor is not a confirmation; it is a fit with zero degrees of freedom. The second anchor was worth its cost precisely because it disagreed.

**Model disposition:** the executable model is **re-derived as v2**, not patched. v1 assumed a single ranging channel with a constant offset; that assumption is dead. v2 estimates position in true millimetres through a two-point interpolation, trusted only inside the bracket its anchors span, with a fused odometry gate.

## 3. TBD register — closure

Tier key: **T1** external ground truth · **T2** anchored/multi-point onboard · **T3** single sample or prior · **T2\*** measured on one channel and transferred to another (the residual risk VER-1 exists to test).

| Parameter | Bound value | Tier | Producing test / evidence |
|---|---|---|---|
| `anchor_lo_read` | 115 | T1 | OP-MEAS-2, ranger A static burst 115-120 |
| `anchor_lo_true` | 102 | T1 | OP-MEAS-2 operator measurement |
| `anchor_hi_read` | 236 | T1 | OP-MEAS-1, ranger A static burst, zero spread |
| `anchor_hi_true` | 212 | T1 | OP-MEAS-1 operator measurement |
| `sigma_anchor_mm` | 3 | T1 | operator measurement resolution, assumed 3 mm |
| `v_cmd_dps` | 1000 | T2 | CAL-3 device ceiling; achieved 986-1004 dps |
| `k_odo_mm_deg` | 0.47 | T2 | CAL-3 cruise 0.503 / CAL-4 statics 0.44-0.49; centre |
| `k_odo_lo` | 0.44 | T2 | CAL-4 in-bracket static fit |
| `k_odo_hi` | 0.505 | T2 | CAL-3 cruise, T1-anchored both ends |
| `loop_dt_ms` | 10 | T2 | CAL-3 on-hub: min 10, max 11, mean 10.0 |
| `t_refresh_ms` | 24 | T2 | CAL-3 on-hub: 70 value changes over 1656 ms |
| `d_total_mm` | 45 | T2* | CAL-3 B-channel 248->203; CAL-2 59-13.5 delay = 45.5. TRANSFERRED to channel A -- the VER-1 test subject |
| `sigma_d_mm` | 8 | T3 | channel-transfer risk: A's lag is not measured at speed |
| `sigma_read_mm` | 2 | T2 | CAL-4 static bursts, spread <=5 mm at every stop |
| `yaw_cruise_deg` | 1.6 | T2 | CAL-3 heading-hold envelope -0.96..+1.60 deg |
| `yaw_trigger_deg` | 0.06 | T2 | CAL-3 heading at the trigger instant |
| `yaw_rest_deg` | 3.3 | T2 | CAL-3 braking skid, heading hold active |
| `sigma_yaw_deg` | 1.5 | T3 | single observation; run-to-run spread not sampled |
| `half_width_mm` | 90 | T3 | conservative prior; deliberately NOT measured (S0.2) |
| `sigma_v_frac` | 0.02 | T2 | CAL-3 within-run speed regulation |
| `sigma_brake_frac` | 0.05 | T3 | prior; the 5 operation runs are the repeatability sample |

**Derived calibration:** true gap = **0.9091 × A -2.5 mm**, trusted for A ∈ [100, 250].

### 3.1 Deliberately not bound

| Parameter | Disposition |
|---|---|
| `half_width_mm` | Carried at the conservative prior (90 mm). Sensitivity P3 — 3.5 mm of objective swing across its whole prior range. A costed measurement would buy less than it costs. |
| `sigma_brake_frac` | Prior. Measuring it properly needs 3–4 identical runs; the five operation runs are the repeatability sample and will be reported in the Final Report. |
| `k_odo` | Carried as a **range** 0.440–0.505, not collapsed. Cruise and creep estimates differ by 6% and no onboard channel separates slip from ranging scale. It is used only where a range is sufficient: the protective interlock (sized at the largest value) and short-span propagation in the fused estimator (a few mm of leverage). |
| Ranger B calibration below 260 mm | Not attempted. B is unusable there (spread 158 mm at 196). B is retained as a cross-check above 260 mm only. |

## 4. Component (CMP) unit verification

| CMP | Claim | Evidence | Verdict |
|---|---|---|---|
| CMP-1 | Ranger A residual vs odometry over range | CAL-4: linear fit over 900 mm, residuals +2.6/−9.3/−0.2/+6.3/+0.6 mm at five static stops; no curvature | **PASS with caveat** — two intermittent faults, see CMP-1a |
| CMP-1a | Ranger A fault modes | CAL-4: one sentinel dropout at ~840 mm; one **600 ms freeze** at 286 mm during 43 mm of travel | **FAIL as a raw channel** → mitigated by the fused estimator (FUN-11), re-verified at VER-1 |
| CMP-2 | Ranger B residual | CAL-4: tracks A to 263 mm (spread 8 mm); spread 158 mm at 196 mm | **PASS above 260 mm only** |
| CMP-3 | Near-range floor ≤ reading used | A valid to 116 mm (spread 5); trigger reading 92 mm | **PASS by extrapolation of 25 mm** — flagged, tested at VER-1 |
| CMP-5 | Ranging refresh interval | CAL-3 on-hub: 70 value changes / 1656 ms = 24 ms | **PASS** (≤80) |
| CMP-6/7 | Motor speed sustained at cruise | CAL-3: 986–1004 dps against 1000 commanded | **PASS** |
| CMP-8/9 | Per-motor rotation after brake | CAL-3: 30 deg mean, left/right within 5 deg | **PASS** |
| CMP-10 | Odometry vs ranging residual | CAL-3/CAL-4: 0.440–0.505 mm/deg, 6% spread | **PASS as a bounded range**, not as a point value |
| CMP-11 | IMU heading drift at rest | CAL-3/CAL-4 static bursts: <0.05° over run duration | **PASS** |
| CMP-12 | IMU acceleration cross-source | Logged; not needed once odometry and ranging agreed | **NOT EXERCISED** |
| CMP-13 | Rear ranger travel residual | Rear reference left range early (2000 sentinel) | **VOID** — the Where-precondition is false |
| CMP-14 | Loop period | CAL-3 on-hub: min 10, max 11, mean 10.0 ms | **PASS** (≤20) |
| CMP-15 | Rotation-to-speed constant | As CMP-10 | **PASS as a range** |

## 5. Anomaly trail

| ID | Finding | Disposition |
|---|---|---|
| AR-001 | Discovery nudge spun the rover 35.9°, blinding both rangers at that incidence | Defect removed, not patched: discovery deleted, port map hard-coded, outcome gates added |
| AR-002 | 32 ms of telemetry between trigger and brake = 13.5 mm of untracked travel | Brake now precedes all logging; measurement re-taken and cross-validated (45.0 vs 45.5 mm) |
| AR-003 | Constant-offset calibration falsified by 11 mm | Model re-derived as v2 |
| — | Ranger A 600 ms freeze | Fused estimator; detects in ~20 ms instead of 600 ms |
| — | STK-3 vs STK-4 tension at the speed ceiling | Heading hold trims only the leading wheel; yaw at trigger improved from −3.7° to 0.06° |

## 6. What calibration did not settle

Three things go into VER-1 unresolved, and the Verification Plan is built around them:

1. **`d_total` is a channel transfer.** It was measured on ranger B (45.0 mm, cross-validated against CAL-2's delay-corrected 45.5 mm) but the flight program triggers on ranger A. If A's reporting lag differs from B's, `d_total` differs. This is the single largest term in the budget at **8.0 mm of 10.0 mm total (64%)**, and it is the primary test subject of VER-1.
2. **The trigger reading sits 25 mm below A's proven floor.** A is verified clean to 116 mm; the trigger fires at 92 mm. The fused estimator covers the shortfall by odometry propagation, but that mitigation is untested at speed.
3. **SYS-8 is open by construction.** The objective requirement cannot close on onboard data. It closes at Gate C only against operator ground truth at the operating point.
