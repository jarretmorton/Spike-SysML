# 10 — CALIBRATION REPORT, Wall-Approach Rover — v1.0 (Gate B)

**Basis:** R-CAL v1.0 run-20260712-231537 (safe abort, AR-001) · R-CAL v1.1
run-20260712-233644 (full success) · Operator measurement **M1 = 218 mm**
(taken at the run-2 creep rest, before repositioning — the 1 planned operator
input, now consumed).
**Status:** REPORT (static). The companion Verification Plan (doc 11) is the
frozen-prediction document.
**Score state:** 2 characterization program runs consumed · 1 operator
measurement consumed.

---

## 1. Parameter bindings

| Param | Value | Tier | Evidence |
|---|---|---|---|
| o_B (mount offset, sensor B, port B) | **−46 mm** | **T3** | M1 218 vs 38-sample rest median 172 |
| o_A (mount offset, sensor A, port A) | **+68 mm** | **T3** | M1 218 vs rest median 286; range-dependent (see §3.4) |
| k_odo | **0.64 ± 0.04 mm/deg** (0.0367 m/rad) | T2 | cruise fits B-vs-encoder 0.656 (seg2), 0.66–0.69 (seg3 fresh interval); pulse fit 0.44 rejected (launch wheelspin); rest-delta fits rejected (brake skid) |
| v_max | **610 ± 25 mm/s** | T2 | plateau 954/954/966 dps × k̂, battery 7.57 V |
| t_chain (cmd → decel onset) | **41 ms** | T2 | measured 3×, identical |
| t_chain_eff (design, incl. detection) | 71 ms | design | 41 + 20 (median-of-3 lag) + 10 (confirm tick) |
| a_brake (effective, hold()) | **9 000 mm/s²** | T2 | post-onset brake distance ≈ 19 mm from 610 mm/s; amax 0.89–1.16 g corroborates |
| stop advance (cmd → rest, at 610) | **44 ± 7 mm** | T2 | seg2 ≈ 41, seg3 ≈ 46 (fresh-trend decomposition) |
| τ_US (data age, B) | **10 ± 8 ms** | T2 | advance decomposition bounds 2–18 ms |
| U_refresh | B **20 ms**, A 32 ms | T2 | S0 change-interval statistics |
| σ_US (static) | 1.5 mm | T2 | MAD 0–1 mm both sensors |
| σ_b (advance dispersion) | 7 mm | T2 | 2 clean samples, small-sample inflated |
| ψ_run (heading drift under load) | −3.2° / 0.85 m approach (0.056 rad) | T2 | −1.1° per ~0.3 m segment, consistent sign, ×3 |
| T_loop | 10 ms, jitter 0 | T2 | jit_max = 0 all segments |
| half_width | 100 mm (ceiling) | T0 prior | unmeasured by design (absence-by-sensitivity) |
| r_min (US validity floor) | validated clean to **reading 172**; below **unknown** | T1/T2 | creep rest 38 samples stable; no data below (TBD-4 partially open — see §3.5) |
| G0_start | unbound | T0 | context row; zero leverage (sweep) |
| IMU drift | 0.006°/2 s static | T2 | S0 |
| Battery | 7 574 mV (run 2) vs 7 594 (run 1) | T2 | plateau-vs-battery watch item for op runs |
| BLE throughput | **0.37–2.2 kB/s across sessions** | T2 | run-1 vs run-2 dump pacing → AR-002 |

## 2. Channel decisions

**B (port B) = primary ranging channel.** Fastest updates (20 ms), MAD 1 mm
static, self-consistent cruise slope, M1-anchored offset. Known defect:
at speed it emits **single low-glitches (−60…−180 mm)** and occasional
freezes (~180 ms observed). Two of the three R-CAL triggers fired 95–150 mm
early on such glitches. Operation countermeasures (all in OP-WAR v1.0):
trend-rate intake gate (reject fresh jumps beyond 2.2× speed-scaled
allowance, two-sided, allowance grows with time-since-last-accept so
freeze-recovery passes), median-of-3 accepted samples, 2-tick confirm,
DR propagation between accepted fixes.

**A (port A) = demoted to validity/fallback + rest diagnostic.** Slow
(32 ms), dropout bursts at speed (no-echo runs through the seg2 brake),
anomalous cruise slope (0.47 mm/deg vs B's 0.66 — unresolved, so its
in-motion readings are not trusted as distance), offset range-dependent
(§3.4). Used only before the first B fix and as a rest-window diagnostic.

**E (rear, port E) = DROPPED by traceability.** Pegged 2000 through the
entire run including motion; never valid in scene. CMP-R1 dispositioned
(see §5). **F (color) = unused** (per Gate A).

## 3. Physics findings

**3.1 Launch wheelspin.** Aggressive speed steps from rest over-count the
encoder ~20–30 % (pulse k-fit 0.44 vs cruise 0.66). Consequence: encoder DR
during launch is optimistic; irrelevant to the trigger (fires in cruise) but
one reason rest-delta k-fits were rejected.

**3.2 Brake skid.** hold() from ~610 mm/s stops the chassis in ~19 mm of
travel *after* decel onset, but the encoders advance only 13–28° (8–18 mm
rolled): the chassis **slides ~29 ± 8 mm** (2 samples: 23, 35) with wheels
held. Peak |a| up to 1.16 g. Consequences: raw encoder DR across a brake
event under-measures travel (diagnostic channel `est.c_dr` is skid-biased
high); rest-delta k-fits invalid; the *advance* number (44 ± 7 mm) is the
calibrated quantity that matters.

**3.3 Negative "braking distances" explained.** seg2 (−57 mm) and seg4
(−82 mm) db_raw values are artifacts of glitch-triggers: the trigger reading
was a low-glitch ~95–150 mm below trend, so the rest reading sat *above* it.
seg3 (+52 mm) was a clean trigger and reconciles exactly with the advance
model.

**3.4 A-offset range dependence.** A−B spread: 148 mm static at ~1 m,
191/175/180 at the three brake rests, 114 at the 218 mm anchor. o_A drifts
~±30 mm across 0.2–1.0 m; o_A = +68 is the *anchored* value at 218 mm.
o_B is consistent within measurement noise across the same range.

**3.5 Near-range validity (TBD-4, partially open by design).** Readings are
validated clean down to reading 172 (gap 218). The designed stop (gap ≈
36–42 mm) puts B's rest reading at ≈ −4 → **B is blind at the stop**, and A's
rest reading ≈ 104 is *below its anchor* with unknown floor behaviour.
Consequence (mock-demonstrated: stable floor-garbage fooled a naive
estimator by +77 mm): **no ultrasonic rest reading is committed as the
onboard estimate.** The committed estimate is the trigger-state prediction
(§4). Residual risk of unknown sub-172 behaviour on the *approach* is
covered by the trend gate + DR fallback and was stress-tested
(b-dead-below-150/260 scenarios).

**3.6 Creep-stop reconciliation.** The R-CAL creep stopped at reading 172
against a 110 threshold because its DR deliberately used the worst-case
K_HI = 1.0 (safe-early). With the calibrated k̂ this bias is absent in
OP-WAR.

## 4. Operation design values (OP-WAR v1.0)

Trigger law: brake when median-of-3-accepted, DR-projected corrected gap
≤ **G_AIM + v̂·71/1000 + v̂²/18000** for 2 consecutive ticks, with
G_AIM = 42 mm (sensor line) = G_target 36 (corner) + 6 corner-erosion fold.
At v̂ = 610: threshold = 106 mm corrected ⇒ **B reading ≈ 66 mm at
trigger**. Committed onboard estimate `est.c_final` = `est.c_pred` =
gsig_trig − v̂·41/1000 − v̂²/18000 (needs no near-range sensing; immune to
blind zone and skid). Diagnostics emitted: c_b (gated to reading ≥ 110),
c_a_raw, c_dr, disagree flag, glitch_rej count.

## 5. TBD register closure (20/20 dispositioned)

TBD-1 stop_target → 36 mm (doc 11) · TBD-2 post-stop bound → 4 mm (measured
2.6) · TBD-3 heading bound → 4° (predicted 3.2) · TBD-4 r_min → partially
open by design, mitigated (§3.5) · TBD-5/6 offsets → T3 bound · TBD-7 τ →
bound · TBD-8 k → bound · TBD-9/11 chain/loop → bound · TBD-10/10b brake →
bound · TBD-12 trim → **OFF, kp = 0** (drift erosion 5.6 mm folded into
G_AIM; test-like-you-fly with R-CAL) · TBD-13 v_max → bound · TBD-14/15
scene/start → census + static check · TBD-16 noise → bound 4 mm ·
TBD-17 refresh → bound 40 ms · TBD-18 IMU → bound 1°/10 s · TBD-19 jitter →
bound 5 ms · TBD-20 rear → dropped.

## 6. CMP unit verdicts (mechanical roll-up: doc 09 output)

29 PASS / 0 FAIL / 23 OPEN today; the OPEN rows are run-level (close at
R-VER) plus two textual dispositions carried OPEN in the mechanics on
purpose (never faked numerically):
**CMP-U3-A** — data-age tolerance not demonstrable for A; **dispositioned by
demotion** (A carries no gap-correction duty in OP-WAR).
**CMP-R1** — rear tracking; **dispositioned DROPPED-BY-TRACEABILITY**
(channel never valid in scene; Optional clause).
**CMP-H2** (emission ≤ 20 s) closes at R-VER with the operation-sized dump —
R-CAL's own dump violated it under collapsed BLE (AR-002).
