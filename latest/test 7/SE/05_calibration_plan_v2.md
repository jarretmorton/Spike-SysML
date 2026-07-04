# Calibration Plan — Wall-Approach Rover — **v2**

**Document type:** PLAN (living; v1 retained unchanged as the prior record).
**Supersedes:** `05_calibration_plan_v1.md`.
**Revision trigger:** the C1 anomaly (`ANOMALY_C1_report.md`) — a hard No-Contact violation caused by (1) mis-identification of the trigger sensor by the nudge-based detection and (2) an inadequate safety backstop. Plan v1 §5 explicitly listed "detection flaky → hard-code map" and "any impossible reading → Anomaly Report" as revision triggers; this is that revision.

**Scope of this revision.** The anomaly invalidated the *method of execution and safety*, not the *analysis or strategy*. Therefore:

- **Carried forward from v1, unchanged and still valid:** §0.2 sensitivity table, §0.3 the measure-`D_stop`-directly strategy and leverage-collapse, §1 calibration input list, §2.1 channel catalog & cross-sourcing, §2.2 source-of-truth hierarchy, §2.4 `D_stop` channel definition, §2.5 physical-plausibility bounds, §3 the two costed operator measurements, §4 verification support (roll-up/CMP/sequence/margin), §5 commitments. Read v1 for these.
- **Changed here in v2:** §0.1 priors (updated with C1-measured values), §2.3 run construction (nudge detection → hard-coded map + confirming crawl), a new §2.7 layered safety, §2.6 run schedule/budget (the failed C1 counts; re-run added), and a telemetry-budget note.

---

## R.0 What changed and why (C1 anomaly summary)

C1 (v1 program) drove into the wall: the paired-nudge detection produced a sub-threshold signal and fell back to "smallest baseline = forward," selecting a rear/angled sensor (port E) as the trigger channel; the true wall-facing sensor (port B) was only the secondary, so the trigger never fired, and an 8 s backstop allowed the rover to reach and push against the wall. Full evidence and root cause in the Anomaly Report. The three corrective changes:

1. **Detection replaced by a hard-coded map + a confirming forward crawl** (§2.3).
2. **Layered, identity-independent crash prevention** (§2.7): an emergency distance floor on *all* sensors, plus a tightened timeout.
3. **Telemetry budget cut** so runs complete (the v1 full-rate buffer dump exceeded the BLE window; the run timed out mid-dump).

---

## R.0.1 Priors — updated with C1 measurements

Tier: 1 well-known · 2 modelled/onboard-calibratable · 3 unknown-onboard · 4 external ground truth.
"C1" = value observed in the C1 run (trusted onboard reference); still to be reconfirmed on the v2 run before being locked.

| Parameter | v1 nominal [lo,hi] | **v2 update** | Tier | Note |
|---|---|---|---|---|
| `omega_max` (deg/s) | 1030 [900,1117]* | **≈ 1044 (C1)** | 2→known | steady cruise reached; near motor max |
| `k_speed` (mm/rad) | 28 [20,45] | **≈ 27–30 (C1 crawl est.)** | 2 | offset-cancelling Δreport/Δθ; refine on v2 crawl |
| `r_min` (mm) | 45 [30,60] | **≈ 40 (C1)**; no-echo sentinel = 2000 | 2→known | confirms operating rest reading is below floor → encoder-primary vindicated |
| port map | unknown | **motors C,D · ultrasonic A,B,E · color F** | — | probe worked; now hard-coded |
| forward-facing sensors | unknown | **B proven wall-facing; A candidate; E rear** | — | from C1 descent + baselines |
| forward motor signs | unknown | **C:−1, D:+1** (drove at wall) | — | from C1 |
| `b` (sensor offset, mm) | 0 [−20,30] | **still open** — operator meas. #1 at v2-C1 rest | 4 | unchanged; no onboard absolute channel |
| `D_stop` (mm) | model ~47 | **still open** — v1 produced no valid stop | 3 | measured on v2-C1, v2-C2 |
| `sigma_stop` (mm) | 8 [3,20] | **still open** — needs ≥2 valid stops | 3 | dominant margin term; from v2-C1 + C2 |
| `t_response`, `alpha`, `sigma_*`, `heading_drift` | as v1 | as v1 (no valid v1 data) | 2–3 | from v2 runs |

*v1 stated `omega_max` in rad/s (18.0 [15.7,19.5]); shown here in deg/s for direct comparison with the C1 reading (18.22 rad/s ≈ 1044 deg/s).

The **sensitivity ranking (v1 §0.2) is unaffected** — the leverage ordering and the measure-`D_stop`-directly strategy stand. C1 only *narrowed* several tier-2 priors and fixed the port map; the objective-critical unknowns (`b`, `D_stop`, `sigma_stop`) remain exactly where v1 placed them.

---

## R.2.3 Run construction (revised)

The program is still the **locked superset** of the operation program (identical accelerate-to-max → paced loop → `hold()` stop → `try/finally`). The changes:

- **Port map is hard-coded** (motors C/D with forward signs C:−1, D:+1; ultrasonic A/B/E). Each device is constructed exactly once; no probing, no nudge classification. This is the documented v1 fallback, now justified by C1 evidence.
- **A confirming forward crawl replaces detection.** A slow (~150 deg/s), sustained (~1.2 s) *hard-coded-forward* motion produces a strong distance signal. Sensors that clearly **decrease** (≥ 40 mm) during this confirmed-forward motion **and** read a plausible standoff (300–1400 mm) are labelled the **wall-facing group**. This both (a) identifies the trigger channel robustly and (b) yields a clean `k_speed` (offset cancels in Δreport/Δθ). **If no sensor qualifies, the program SAFE-ABORTS before the fast approach** (the rover is not confidently pointed at a wall).
- **Trigger** fires on the *minimum* of the wall-facing group (first to reach threshold → conservative), with both members and the source recorded.
- The only downstream change for V1/operation remains the **trigger threshold value**; the crawl and safety layers stay identical (test-like-you-fly preserved; the crawl consumes ~150 mm of runway deterministically every run, and full cruise is still reached before the trigger).

## R.2.7 Layered safety (new — crash prevention independent of sensor identity)

Because the crash came from trusting a single (mis-identified) channel, v2 does not let sensor-ID error reach the wall:

- **L1 — primary trigger:** stop when the identified wall-facing group ≤ `R_TRIGGER` (C1: 180 mm).
- **L2 — emergency floor (identity-independent):** stop immediately if *any* ultrasonic reads ≤ `SAFE_FLOOR` (100 mm). If the forward/rear identity were somehow inverted, whatever truly approaches the wall trips this. **Invalid / no-echo readings are sanitized to "far" (2000 mm)**, so a dropout can never *cause* a false emergency, and a genuine near reading always trips it. With `SAFE_FLOOR` = 100 mm and `D_stop` ~50 mm, worst-case clearance is still ≈ 50 mm.
- **L3 — stuck backstop:** `MAX_RUN_MS` tightened from 8000 ms to **2500 ms** (physically sane for a ~1 m standoff), catching a stalled loop.

L2 is the real guarantee; L1 sets the (tight, characterizing) stop; L3 is a catch-all. Even a total forward-sensor mis-ID cannot produce contact.

## R.2.6 Run schedule and budget (revised)

The failed C1 (v1) **counts** toward the program-run score (criterion 1 counts re-runs). The revised schedule:

| # | Run | Trigger | Status / binds | Operator input |
|:--:|---|---|---|---|
| ~~0~~ | ~~C1 (v1)~~ | ~~180 mm~~ | **FAILED — wall contact; counts as a run; no valid `D_stop`** | none valid |
| 1 | **C1 (v2)** | conservative 180 mm | port-map/crawl confirmation, `k_speed`, `omega_max`, `r_min`, `heading_drift`, `D_stop` #1, rest_speed | **Measurement #1** (b anchor at rest) |
| 2 | **C2** | conservative 180 mm | `D_stop` #2 → `sigma_stop` spread + repeatability | none |
| — | *compute operating `R_trigger`; freeze Verification Plan (GATE B)* | | | |
| 3 | **V1** | operating (computed) | tests frozen prediction at operating point | **Measurement #2** (objective validation) |
| — | *operation ×5, locked program* | operating | scored | close-out only |

**Program-run total before operation is now 4** (1 failed + C1v2 + C2 + V1), up from the planned 3, plus the 2 operator measurements. This is the unavoidable cost of the anomaly. Options considered to offset it: dropping C2 and modelling `sigma_stop` from within-run jitter (v1's leaner branch). **Not adopted** — the crash argues for *more* conservatism on the hard constraint, and `sigma_stop` is the dominant margin term (v1 §0.2). Re-evaluate only if C1v2 shows `sigma_stop` cleanly bounded from within-run data.

**Telemetry budget (new):** light live channels (downsampled `d_fwd`, `d_all_min`, `heading`) + latched scalars only; **no full-rate buffer dump.** This keeps each run inside the BLE/timeout window so it completes and reaches the sentinel. Full-rate shape is sacrificed; the latched trigger/rest scalars carry the objective-critical `D_stop`, and the live downsampled channels carry the approach shape and the no-contact evidence.

---

## R.5 Commitments (unchanged from v1, plus)

All v1 §5 commitments hold. Added by v2:

- Crash prevention no longer depends on correct sensor identification (L2 emergency floor, sanitized readings).
- The port map and forward signs are fixed from C1 evidence; the crawl re-confirms them every run and safe-aborts if reality disagrees.
- Runs are telemetry-bounded to complete within the timeout.

*Revision triggers for v2 (in addition to v1's):* the confirming crawl fails to find a wall-facing sensor (rover/setup geometry differs from C1) · an emergency-floor stop fires during C1v2 (primary trigger mis-set or a sensor closer than expected) · `sigma_stop` still not bounded after C2.
