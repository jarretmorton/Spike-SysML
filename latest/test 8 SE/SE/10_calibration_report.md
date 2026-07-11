# CALIBRATION REPORT — WallRun (REPORT — static, not revised)
**Gate:** GATE B (with the Verification Plan). Backward-looking record of Phase-1 characterization.
**Runs consumed:** C1, C1b, C1c, C1d (4 characterization program runs). **Operator ground-truth measurements:** 1 (gap = 542 mm at S_A = 557 mm).
**Frame:** all distances in the **sensor-A reading frame** unless noted. Gap `G` = frontmost rover point → wall (the scored quantity). `G = S_A − c_A`.

## 1. What characterization revealed (deviations from the Calibration Plan v1)
Three things the plan did not anticipate, each forcing a program change (all analysed free; hardware cost noted):
1. **Discovery creep corrupted C1.** The same-sign creep spun the hub ~18°; the crooked approach lost the wall (ultrasonic → 2000). *Fix:* hard-code the discovered map, no creep (C1b onward). Cost: C1 salvaged only the map.
2. **BLE dump throughput is ~35 lines/s and batching is ~5× slower.** C1/C1b truncated. *Fix:* per-line dump, REST rows first, ≤ ~30 s timeout (C1c onward). 
3. **The drivetrain veers ~14° left at max speed** (motor imbalance) → straightness impossible open-loop, and it corrupts the ultrasonic geometry. *Fix:* closed-loop heading hold — hard-coded sign, feed-forward + P + D — which holds heading to **[−0.5°, +2.6°]** (C1d). Also: **sensor B is unreliable** (latches, drops out) and reads a physically-impossible offset → **discarded**; sensor A used.

## 2. Calibrated values (source-of-truth tier; producing test; unit verification)
Tiers: T0 external ground truth · T1 anchored/multi-point onboard · T2 single onboard sample.

| Symbol | SysML | Value | Tier | Producing evidence | Unit check |
|---|---|---|---|---|---|
| port map | — | motors C/D, ultrasonics A/B, rear dropped | T1 | C1 type-probe + creep classification | ports resolve; A/B track wall |
| forward sign | — | leftCCW / rightCW (both `run(+)` = fwd) | T1 | C1 creep (Δrange sign) | S_A decreases on forward drive |
| `gsign` | — | +1 | T1 | C1c in-run kick; reused C1d | heading→0 under control |
| **c_A** `sensorOffset` | 15 mm | **+15 mm** | **T0** | operator gap 542 at S_A=557; c=557−542 | mm − mm = mm ✓; matches geometric prior |
| **v_max** | 490 mm/s | ~490 mm/s (±30) | T1 | C1d dist_A slope over cruise (heading straight) | mm/ms→mm/s ✓; wheel≈56 mm consistent w/ cmd |
| **D_stop** `→(t,a)` | 53 mm | **53 mm** at v_max | T1 | C1d: S_A 610→557 trigger→rest | mm ✓; = v·t+v²/2a with t≈0.038 s, a≈3500 |
| `a_brake` | 3500 mm/s² | ~3000–4000 | T1 | C1d IMU decel (~−3000 sustained) + D_stop split | mm/s² ✓ |
| `t_lat` | 0.038 s | ~0.038 s | T1(derived) | closes D_stop given v,a | s ✓ |
| `σ_S` (rest) | rangeNoise | ~1 mm | T1 | C1d rest dwell S_A = 557±1 | mm ✓ (very low) |
| `Δt_s` | sampleInterval | ~0.030 s (est) | T2 | C1d update cadence | s ✓ |
| heading hold | maxHeadingDrift | [−0.5,+2.6]° | T1 | C1d full trace | deg ✓ |
| A−B offset | — | ~124 mm (const) + angle term | T1 | C1c/C1d rest & approach | mm ✓ (B mounted fwd + reads short) |

**Calibration uncertainties (1σ) carried into σ_G:** σ_v=30, σ_t=0.010, σ_a=800, σ_c=3 (operator), plus quantisation v·Δt_s/√12 and rest σ_S.

## 3. TBD register closure (spec §6)
TBD-1 v_max→490 (C1d). TBD-2 t_lat→0.038 (derived). TBD-3 a_brake→3500 (C1d). **TBD-4 c_A→+15 (T0 operator).** TBD-5 Δt_s→0.030. TBD-6 σ_S→1. TBD-7 σ_D→σ_G contributors below. TBD-8 d_min/d_max→50/2000 (A). TBD-9 A/B agreement→~124 mm const offset (B discarded; CMP-2b re-scoped to "A reliable, B backup"). TBD-10 heading behaviour→hold to ±2.6°. TBD-11 k,M,G_target→ k=3, see Verification Plan. TBD-12 sign/map→resolved §2. **All TBDs closed.**

## 4. Residual notes feeding the Verification Plan
- σ_G is dominated by the **a_brake / v split and quantisation**, not by c_A (c_A is now tight, T0). 
- The single biggest *unmeasured* quantity is **run-to-run D_stop scatter** (only one clean stop so far); the Verification Plan's margin is sized conservatively for it, and the verification run supplies the second data point.
- D_stop was measured at the C1d trigger point (S_A≈610); the operation triggers at S_A=113 (closer). The rover reached max speed (~490) well before that point in C1d, so D_stop is expected unchanged — **the verification run tests exactly this** at the operating trigger.
