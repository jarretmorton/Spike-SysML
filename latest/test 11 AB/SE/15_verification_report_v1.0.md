# 15 — VERIFICATION REPORT, Wall-Approach Rover — v1.0 (Gate C)

**R-VER:** run-20260713-001530 · OP-WAR v1.0 byte-identical
(md5 `eba2d509e2d6d3800347e0a3c3be805c`) · completed 9.72 s inside the 45 s
budget · characterization run 3 of the campaign.
**Judged against:** Verification Plan v1.0 (doc 11, frozen). **Result: all 8
pass criteria PASS — the frozen plan is not falsified.**

## 1. R-VER vs frozen criteria

| # | Criterion | Evidence | Verdict |
|---|---|---|---|
| 1 | No contact | Two independent witnesses: (a) amax 0.99 g — inside the known no-contact brake family 0.89–1.16 g, no strike spike; (b) post-trigger encoder travel 31.5° ⇒ 20 mm rolled + calibrated skid 29 ± 8 ⇒ stop ≈ 52 mm from the trigger's 101 mm state (a strike would need ~80 mm of skid, 6σ out) | **PASS** |
| 2 | Clean run | census_ok 1, run.ok 1, no abort/exc | **PASS** |
| 3 | Stop quality | full rest at t 3484, hold_s 4.46 ≥ 2, creep_deg 0 | **PASS** |
| 4 | Prediction window | est.c_final **54 mm** ∈ [0, 72]; |54 − 36| = 18 ≤ 36 (+1.5σ) | **PASS** |
| 5 | Trigger integrity | gsig 101 ≤ thr 108 (within 25); glitch_rej 14 reported; est.disagree 0 | **PASS** |
| 6 | Speed | plateau 985 dps, full-speed to trigger, no slowdown; v̂ 630 in 580–650 window | **PASS** |
| 7 | Telemetry contract | sentinel present, emission 4.46 s ≤ 20 (**closes CMP-H2**), 156 lines, buf_ovf 0, jit_max 0 | **PASS** |
| 8 | Heading | dh −3.92° ≤ 4° bound (thin — see §3.3) | **PASS** |

Internal consistency: c_pred 54, c_dr 79 (= 54 + 25, matching the ~29 mm
skid bias predicted for the diagnostic DR channel), encoder-reconstructed
stop ≈ 52. Three chains agree within 4 mm.

## 2. Requirement closure (52/52)

Mechanical roll-up at R-VER observations reproduces the frozen view B with
run-level rows now **measured**: STK-1/3/4/5/6/7, SYS-1…13, FUN-1…7 — all
PASS on run-3 evidence (speed plateau 985 dps sustained; brake cmd delay 1
tick; rest achieved; estimates committed src 4; zero operator inputs during
run; sentinel; census; hold 4.46 s; rest samples 30; coverage: gap signal
valid every tick via fix+DR, encoders monotone; fused gap at trigger 101 ≤
budget 108). CMP families: M1-L/R plateau dev 4.2 %/2.1 % ≤ 5 %; M2, M4, M5,
U1, U2, U4, U5, I1, I2, H1 as at Gate B (unchanged evidence); **CMP-H2
CLOSED** on measured 4.46 s; U3-B PASS (τ within tolerance, trigger math
consistent). Dispositions confirmed: **CMP-U3-A** closed by A-demotion
(R-VER re-evidenced: A dropped out for the entire high-speed approach and
produced multipath garbage at rest — the demotion was correct and the mad
gate rejected its rest channel as designed); **CMP-R1** closed
dropped-by-traceability. **Objective (STK-3/SYS-4):** closed on the
M1-validated chain — G_target 36 ≤ 60 ceiling; realized C_final estimate 54
≤ closeness ceiling 72.

## 3. New findings (logged; none falsify the plan)

**3.1 B's validity floor found: reading ≈ 40.** On final approach B clipped
to a hard 40 (with 2000 interleaves) below reading ~100 — TBD-4's unknown is
now bounded: floor behaviour = clip-to-40/no-echo, i.e. *invalid-obvious*,
not plausible-garbage, at this pose. The trend gate rejected the clips; the
trigger rode the median fix + DR exactly as designed.
**3.2 A near-range multipath.** A returned briefly (208–233) post-brake then
wandered to ~1124 during the rest window; the MAD gate rejected it. Confirms
demotion and the no-committed-rest-estimate decision.
**3.3 Brake-skid yaw.** The heading swung ≈ −6° *during* the skid
(−30.8→−39.1 deci-deg×10 across the brake window). Whole-run dh −3.92° meets
the 4° bound as written, but the corner-erosion allowance (6 mm folded into
G_AIM) is consumed mostly by this end-of-run yaw. At the realized ~52 mm
standoff the margin holds (worst-case erosion ~10 mm). Watch item for the
five runs; no change to the locked program (change would violate the freeze
and the test-like-you-fly basis).
**3.4 Glitch environment at 985 dps.** 14 intake rejections in a 2.2 s
approach (both high and low glitches visible in the series) — heavier than
R-CAL's, consistent with the higher plateau. The gate + median + confirm
absorbed all of them.

## 4. Verdict and request

R-VER **PASSES**. Requesting **Gate C approval** to:
1. **Lock OP-WAR v1.0** (byte-identical to the R-VER flash, md5 above) — no
   modifications of any kind hereafter;
2. Execute the **5 scored operation runs**, each preceded by an explicit
   hub-ready confirmation (hub power-cycled + re-flashed each time), 45 s
   host timeout, telemetry + chart after each, **no feedback into the
   program**; anomaly ⇒ HALT recommendation only;
3. Then close out in the strict order: freeze the five onboard estimates in
   chat → request the five measured gaps → final report with per-run
   prediction | estimate | measurement | delta reconciliation.

Score state at Gate C: **3 characterization program runs** (R-CAL v1.0
abort, R-CAL v1.1, R-VER) · **1 operator measurement** (M1) · 0 of 5
operation runs flown.
