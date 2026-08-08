# 21 — VERIFICATION REPORT, Wall-Approach Rover — v2.0 (Gate C resubmission)

**R-VER-2:** run-20260713-004155 · OP-WAR v1.1 byte-identical
(md5 `2d174fe192fb260588fee4bd34ae8592`) · completed 7.36 s · characterization
run 4. **Judged against Verification Plan v2.0 (frozen). Result: all 8
criteria PASS** (criterion 8 with its mandatory analysis note). Supersedes
the withdrawn Verification Report v1.0 (doc 15) per AR-003.

## 1. R-VER-2 vs frozen criteria

| # | Criterion | Evidence | Verdict |
|---|---|---|---|
| 1 | No contact | amax 0.78 g in the no-contact family, no strike spike; encoder travel post-trigger ~20° (13 mm rolled) + calibrated skid 29 ± 8 ⇒ stop 65 ± 8 mm from the 107 mm trigger state; **corner clearance at the measured ≤ 6.4° geometry ≈ 51 mm > 0 — certifiable** | **PASS** |
| 2 | Clean run | census_ok 1, run.ok 1, no abort/exc | **PASS** |
| 3 | Stop quality | rest at 3186; hold_s 2.52 ≥ 2; creep 6° eq ≈ 3.8 mm ≤ 4 | **PASS** |
| 4 | Prediction window | est.c_final **62** ∈ [1, 81]; |62 − 41| = 21 ≤ 40.3 (+1.6σ) | **PASS** |
| 5 | Trigger integrity | gsig 107 ≤ thr 113, Δ6 ≤ 25; glitch_rej 7; est.disagree 1 — analyzed: c_a 108 vs c_pred 62 is the documented A near-range extrapolation bias; committed channel unaffected | **PASS** |
| 6 | Speed | outer wheel full duty; per-motor plateau 944/950 dps (0.6 % matched, was 6.3 % split); ≥ 0.95 × slower ceiling; trim_pct_max 11 ≤ 15 | **PASS** |
| 7 | Telemetry contract | sentinel, emission 2.48 s ≤ 20, 149 lines, ovf 0, jit 0 | **PASS** |
| 8 | Heading (SYS-8, max) | approach-loop max 3.0°; skid transient −6.4° settling −3.8° at rest; whole-run max **6.4° ≤ 10°**. **Analysis note (mandatory for (5°,10°]):** cruise was held at +0.4° by the trim; the 6.4° is entirely the uncontrollable skid swing, partially recovering as the hold servo relaxes; erosion at worst transient 11.1 mm vs 9 folded + 4 var — margin held | **PASS (with note)** |

Three-chain stop consistency: c_pred 62 · encoder+skid 65 ± 8 ·
c_dr − skid 70. Onset 41 ms for the **fifth consecutive** measurement.

## 2. Requirement closure (52/52)

All run-level rows re-closed on run-4 evidence with the corrected SYS-8
methodology (maximum deviation, whole run): STK-1…7, SYS-1…13, FUN-1…7 PASS.
CMP-M1-L/R now 0.6 % (trim); CMP-H2 closed (2.48 s); remaining CMP families
as at Gate B evidence. Dispositions: CMP-U3-A (A demoted — run 4 again
evidences the near-range bias), CMP-R1 (dropped by traceability).
**Objective:** G_target 41 ≤ 60 ceiling [STK-3]; realized estimate 62 ≤
closeness ceiling 81.3 [SYS-4]. **AR-003 status → CLOSED** (corrective
chain executed and verified in flight).

## 3. Residual watch items for operation (no action, monitor only)

Launch transient can reach ~3° before trim authority (bounded, recovers);
skid swing −4…−7° at-wall (inside erosion allowance); B rest readings in
the floor zone are a flickering mix (MAD gate handles); est.disagree may
read 1 whenever A returns near-range values (documented bias, committed
channel immune).

## 4. Request

R-VER-2 verifies the design. Requesting **Gate C approval (resubmission)**:
1. **Lock OP-WAR v1.1** (md5 `2d174fe192fb260588fee4bd34ae8592`), flown
   byte-identical at R-VER-2;
2. Fly the **5 scored operation runs** — hub power-cycled + re-flashed
   before each, hub-ready confirmed each time, 45 s timeout, telemetry +
   chart after each, zero program feedback, HALT-only on anomaly;
3. Close out in strict order (freeze 5 onboard estimates in chat → request
   5 measured gaps → final report with reconciliation).

Score at resubmitted Gate C: **4 characterization runs · 1 operator
measurement · 0/5 operation runs flown.**
