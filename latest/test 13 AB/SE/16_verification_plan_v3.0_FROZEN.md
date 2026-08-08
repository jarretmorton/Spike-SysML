# VERIFICATION PLAN v3.0 — FROZEN

**Type:** plan · **PREDICTIONS ONLY** · **Frozen:** before verification run 3
**Supersedes:** v2.0. v1.0 and v2.0 remain frozen and unedited — the falsification trail is the record
**Committed configuration:** `15_rover_wallstop_LOCKED_v3.py`, `MODE = "OP"`, `G_TARGET` = 26.0 mm

---

## 1. Why v2.0 was falsified

| v2.0 criterion | Predicted | VER-2 actual | Verdict |
|---|---|---|---|
| contact | none | none | held |
| clearance 1.1–26.9 mm | 14.0 | ~10.5 (yaw-corrected) | held |
| `trigger_src` = 1 | 1 | 1 | held |
| `o_consistency` ±12 mm | 0 ± 6 | **+9.22** | held, but see below |
| `psi_odo` 12.64 ± 1.05 | 12.64 | **12.63** | held |
| stop yaw −0.8° ± 4° | −0.8° | **−4.9°** | **FALSIFIED by 0.1°** |
| `flags` clean | 0 | 0 | held |

Three findings, in ascending order of consequence.

**(a) The yaw violation is marginal in angle, material in mechanism.** The rover rotated −6.15° *during
the brake transient*; VER-1 rotated −2.95°. M2 anchored `b_offset` at VER-1's post-brake pose, so the
extra 3.2° swings the leading corner ~1.5 mm closer than the estimator believes. v2.0 budgeted 0.72 mm
for yaw. The mechanism — asymmetric braking — was not in the model at all.

**(b) The `L_SENSOR` correction was misattributed.** Reducing 66 → 50 ms should have driven
`o_consistency` from +6.57 to ~0. It rose to +9.22: a 16 ms latency change should move it −6.6 mm, and
it moved +2.7 mm. So the o-bias is odometric, not latency. The value 50 ms is not wrong in *effect*
(it is bound at the operating point), but the reason given for it in v2.0 was wrong, and that is worth
recording as plainly as a wrong number would be.

**(c) The onboard estimator was tautological.** This is the finding that sets the target.
`clearance_est_odo = (o_cmd + B_OFF) − s_rest`, and the trigger fires at
`s_br = o_cmd + B_OFF − T − psi_belief`, so the estimate reduces to **`T + (psi_belief − psi_odo)`** —
the commanded target plus a ~1 mm psi error. It cannot detect a clearance error. And the one
independent channel clipped: `r_rest` and `r_rest2` both returned **exactly 40.00 mm**, the vendor
floor, across 14 and 12 samples. v2.0 predicted that clipping and still failed to notice it left no
valid estimator at all.

## 2. The decision this forces

Below ~23 mm of clearance this rover cannot measure its own gap. With `m_contact` = 15.3 mm:

| Target | SYS-5 (≥15.3) | OBJ-1 (≤18.3) | SYS-7 — independent estimator |
|---|---|---|---|
| 14 (v2.0) | fails | passes | fails, clipped |
| 20 | passes | fails by 1.7 | **fails, still clipped** |
| **26 (chosen)** | passes, 10.7 mm of 3σ slack | fails by 7.7 | **passes**, `r_rest` ≈ 43 mm |

**26 mm is chosen to buy observability, not margin.** Every significant error in this programme — the
yaw mis-binding, the latency mis-attribution, the tautological estimator — was caught by independent
channels disagreeing. At 20 mm there would be no independent channel during the five scored runs, and
a fourth modelling error would surface only in the operator's close-out measurements, after all five
were locked. At 26 mm it stays visible and the anomaly rules can still recommend HALT.

SYS-7 is a *shall*; OBJ-1 is a *should*. The trade costs ~12 mm of closeness and is made deliberately.

## 3. Frozen budget — operational samples only

v1.0 was falsified partly because I trusted an n=2 σ. The two dominant terms here are still n=2, so
they carry an explicit **×1.8 small-sample inflation** rather than a bare sample sd.

| Contributor | σ (mm) |
|---|---|
| o-bias (VER-1 +6.57, VER-2 +9.22; ×1.8) | 4.23 |
| brake-phase yaw (2.95°, 6.15°; 0.48 mm/deg; ×1.8) | 2.45 |
| `b_offset` anchor M2 | 1.20 |
| trigger timing | 0.63 |
| brake travel (n=5, sd 0.30) | 0.30 |
| quantisation | 0.24 |
| **RSS** | **5.09** |
| **m_contact = 3σ** | **15.3** |

## 4. THE FROZEN PREDICTION

| Quantity | Predicted |
|---|---|
| final clearance | **26.0 mm** |
| 3σ band | **10.7 – 41.3 mm** |
| reported range at rest | **43 mm — VALID**, 3 mm above the floor |
| static estimator `r_rest + B_OFF` | **26 ± 5 mm, and genuinely independent** |
| `clearance_est_odo` | 26 ± 1 mm (tautological; reported, not trusted) |
| `trigger_src` | 1 |
| `psi_odo` | 12.64 ± 0.9 mm |
| `o_consistency` | +7.9 ± 4 mm |
| stop yaw | −4.5° ± 5° |
| `flags` | 0 |
| contact | none |

**Falsification criteria:** contact · clearance outside 10.7–41.3 mm · `trigger_src` ≠ 1 ·
`r_rest` clipped at 40.0 (would mean the estimator is *still* blind) · `psi_odo` outside 12.64 ± 0.9 ·
`o_consistency` outside ±16 mm · any flag other than 256/512 recovered.

The fourth criterion is the important one: it is the test of whether this configuration restored the
independent channel that the whole target choice was made to protect.

## 5. No further operator measurement

M2 anchored `b_offset` at a 31 mm clearance; the new operating point is 26 mm, 5 mm away, at the same
yaw regime and in the same configuration. That is the operating point for GATE C's purposes, so the
objective closes on M2 and no M3 is requested. Outside-input actions stay at 2.

## 6. Run

One run of `15_rover_wallstop_LOCKED_v3.py`, bit-for-bit as it will be flashed for all five scored
runs. `timeout_seconds` = 40. If this holds, GATE C closes and operation proceeds unchanged.
