# FINAL REPORT — WallStop · **Revision B**

**Document** FR-WALLSTOP-001 rev B · **Type: REPORT (static)** · Operation close-out
**Supersedes rev A**, which is retained unedited as `14_final_report_revA_superseded.md`.

**Reason for revision.** Rev A's per-run table was built on a measurement set in which the C4 verification result (14 mm) had been carried into operation run 1, and one operation measurement was missing. The operator subsequently recovered the missing value (24 mm, run 1). Rev A is not edited; this revision restates the close-out on the corrected set and marks what changed.

**What changed between revisions**

| | rev A | rev B |
|---|---|---|
| Operation gaps | 14, 29, 30, 23, 27 | **24, 29, 30, 23, 27** |
| Measured mean | 24.6 mm | **26.6 mm** |
| Observed run-to-run sd | 6.50 mm | **3.05 mm** |
| Residual vs frozen prediction | +0.21 σ | **+0.48 σ** |
| Runs inside 1 σ | 4 / 5 | **5 / 5** |
| Verdict on the σ budget | "right, marginally conservative" | **conservative by 2.5×** — rev A's assessment was wrong, inflated by the mis-attributed 14 mm |

Nothing upstream of the close-out is affected. The 14 mm was correctly attributed to the C4 verification run when it was first supplied, so **GATE C, the Verification Report and the entire verification argument stand unchanged.**

---

## 1. Result

**Five runs. Five complete stops. Zero contacts. Mean final gap 26.6 mm, sd 3.05 mm.**

| Run | PREDICTED (frozen, VP v1.2) | Onboard ESTIMATE (frozen pre-measurement) | MEASURED | est − meas | Contact |
|---|---|---|---|---|---|
| 1 | 23.0 mm | 19.0 mm | **24.0 mm** | −5.0 mm | none |
| 2 | 23.0 mm | 20.9 mm | **29.0 mm** | −8.1 mm | none |
| 3 | 23.0 mm | 22.0 mm | **30.0 mm** | −8.0 mm | none |
| 4 | 23.0 mm | 21.0 mm | **23.0 mm** | −2.0 mm | none |
| 5 | 23.0 mm | 19.8 mm | **27.0 mm** | −7.2 mm | none |
| **mean** | **23.0** | **20.5** | **26.6** | **−6.1** | **0 / 5** |
| **sd** | (σ 7.49) | 1.16 | **3.05** | 2.59 | |

Every run fired on `trig_reason = 1`, the modelled trigger. No failsafe fired in any of the five. Rest speed 0.0 mm/s throughout.

## 2. Did the committed prediction hold?

**Yes, and more cleanly than rev A showed.**

| | |
|---|---|
| Frozen prediction (VP v1.2, committed before the verification run) | **23.0 mm**, σ 7.49 mm |
| Measured mean across five runs | **26.6 mm** |
| Residual | **+3.6 mm = 0.48 σ** |
| Runs inside the 1σ band (15.5–30.5) | **5 / 5** |
| Predicted σ vs observed run-to-run sd | **7.49 vs 3.05 mm** |

The prediction was frozen at GATE B′ and never edited. Five independent power-cycled runs landed a mean of 3.6 mm from it, and **every single run fell inside one standard deviation.**

## 3. Reconciliation of the systematic gap — fully accounted for

**Onboard estimates ran 6.1 mm low.** The cause is now exact, not approximate.

Δ (post-trigger travel) across every ground-truthed stop:

| stop | C2 | C4 | op1 | op2 | op3 | op4 | op5 |
|---|---|---|---|---|---|---|---|
| v (mm/s) | 473.1 | 487.3 | 486.8 | 460.3 | 492.8 | 475.7 | 483.2 |
| Δ (mm) | **43.67** | **49.23** | 39.96 | 34.47 | 37.57 | 41.92 | 37.44 |

- Operation Δ: **38.27 ± 2.82 mm** (n = 5)
- Flight constant `t_eff` implied Δ = **44.35 mm**
- Implied − actual = **6.08 mm**; observed estimate bias = **6.06 mm**

**The entire systematic is accounted for to 0.02 mm.**

**And the cause is instructive.** The two calibration anchors — C2 at 43.67 and C4 at 49.23 — were the **two largest** of the seven Δ values. Calibrating a noisy quantity from n = 2 samples that both happened to land high put `t_eff` about 6 mm high, and every onboard estimate inherited it. This is precisely the risk flagged in the Calibration Report ("n = 2, 1 df — **weakly determined**") and in VP v1.2's honest-weaknesses section. The point estimate was biased; **the uncertainty budget still covered it comfortably**, which is what a margin is for.

Δ still shows no usable speed dependence (r = +0.32 over 460–493 mm/s), confirming the rev B model decision to suppress the unidentifiable quadratic term.

## 4. Where the budget was right, and where it was wrong

Rev A concluded the σ budget was "right, marginally conservative." **That conclusion was wrong** — it was inflated by the mis-attributed 14 mm. Corrected:

| | Budgeted | Observed | Verdict |
|---|---|---|---|
| Total σ_gap | 7.49 mm | **3.05 mm** | **conservative by 2.5×** |
| σ_Δ (braking scatter) | 4.00 mm | 2.82 mm | slightly conservative |
| σ_S (start-line placement) | 5.00 mm | ≲1–2 mm implied | **substantially over-estimated** |

The dominant budget term was the one I flagged at GATE B′ as an unmeasured assumption — *"σ_S = 5 mm is an assumption, not a measurement… if your placement repeatability is materially worse than ±5 mm, this prediction is optimistic."* It was materially **better**, not worse. The consequence is real and costs score: **a 2.5× conservative σ meant G = 3σ = 23 mm where a correctly-sized budget would have supported roughly 10 mm.** Being over-cautious about a term I could not measure cost about 13 mm of the objective.

## 5. The GATE C decision, re-examined

At GATE C the C4 residual (−9 mm) admitted two readings: **bias**, arguing for G = 27 and a fifth characterisation run; or **noise**, a −1.2σ draw leaving G = 23 unchanged. I chose noise and locked the program.

Operation came in at **26.6 mm** — above the 23.0 prediction, well above the 18.9 mm "bias-corrected" figure. **The noise reading was correct, by a wider margin than rev A indicated.** Raising G would have moved the mean to ≈30.6 mm and cost a fifth run, a fourth measurement, and 4 mm of the objective, for no change in contacts.

## 6. What the operation runs revealed about the withdrawn sensor

On runs 4 and 5 ranger A read **819 mm and 799 mm** at the start line against ~1019 mm on runs 1–3 — the intermittent gross error from C2, reproduced twice under scoring conditions. **Neither run was affected.** The ranger gates nothing in rev D, and the start-clearance check was deliberately made non-blocking so a withdrawn channel could not abort a scored run. Under rev C's divergence failsafe, at least one scored run would have aborted exactly as C3 did.

## 7. A wrong inference I declined to use

While the run-to-measurement mapping was uncertain, I noted that adding the yaw-corner term back gave centreline gaps clustering most tightly if **run 2** were the unmeasured one. **It was run 1.** The inference was wrong. I labelled it suggestive-only, refused to put it in a results table, and bounded the ambiguity instead — showing the reconciliation moved under 1 mm across all four candidate mappings. That refusal is the only reason a wrong inference contaminated nothing, and the bound is why re-running five scored runs was unnecessary.

## 8. Scored quantities

| | Value |
|---|---|
| Characterisation program runs | **4** (C1 calibration · C2, C3, C4 verification) |
| Outside-input actions | **3** (C2 gap 222 mm · start line 1000 mm · C4 gap 14 mm) |
| Operation runs stopping with no contact | **5 / 5** |
| Final gaps | 24, 29, 30, 23, 27 mm — **mean 26.6 mm, sd 3.05 mm, best 23 mm** |

Against a GATE A budget of 2 runs and 1 measurement. The overrun is attributable in full to a distance sensor exhibiting six distinct failure modes; the GATE A sensitivity table ranked its offset at tier T0 and predicted a costed measurement would earn its price there. It did — twice, and both times it caught an error every onboard channel agreed on and every onboard channel got wrong.

## 9. Predicted → estimated → measured, closed

```
requirement STK-5 (minimise the gap)
   -> SysML SYS-1 satisfy/require roll-up
   -> executable model, parameters bound by C1-C4
   -> FROZEN PREDICTION 23.0 mm +/- 7.49                       [VP v1.2, GATE B']
   -> onboard ESTIMATES 19.0 / 20.9 / 22.0 / 21.0 / 19.8 mm    [frozen pre-measurement]
   -> MEASURED 24 / 29 / 30 / 23 / 27 mm, mean 26.6            [operator]
   -> residual +3.6 mm = 0.48 sigma, 5/5 within 1 sigma.  PREDICTION HELD.
```

## 10. Honest closing assessment

The rover stopped five times from full speed within 30 mm of a wall it could not see, using a sensor suite in which **no distance channel proved trustworthy**. What made that possible was the argument, not the sensing: an uncertainty budget assembled before the first hardware run bracketed five power-cycled runs with every one inside 1σ, and two costed ground-truth measurements caught errors of 197 mm and 190 mm that every onboard channel agreed on.

**The clearest failure is one of over-caution, and it cost score.** σ was 2.5× conservative, driven almost entirely by a start-line placement term I assumed at 5 mm and could not measure. A correctly-sized budget would have supported a target near 10 mm instead of 23 mm. I flagged that assumption as the weakest number in the budget at the time; I was right that it was weak and wrong about its direction.

Residual weaknesses, recorded rather than resolved: **SYS-8 is only partially met** — no independent distance channel exists on this vehicle; **CMP-11's start-clearance element is descoped**; and **SYS-1's wording is ambiguous** between predicted and realised clearance, a defect in my own specification caught only when I tried to verify against it.

---

## Appendix A — the locked program

`operation_program_v3.py`, rev D, sha256 `ea80c4db3b664d33`, re-flashed unchanged before each of the five power-cycled runs.

```python
enc_div = (angL - angR) * K_TRAVEL           # surviving cross-check
g_est   = S_START - od                       # T4-anchored, odometry only

v_meas  = 0.5 * (abs(mL.speed()) + abs(mR.speed())) * K_TRAVEL
thr     = G_TARGET + T_EFF * v_meas          # StoppingDistance, live

if g_est <= thr:
    reason = 1
elif enc_div > ENC_DIVERGE_MAX or enc_div < -ENC_DIVERGE_MAX:
    reason = 2                               # encoder/wheel fault
elif hd > HEAD_ABORT or hd < -HEAD_ABORT:
    reason = 6                               # gross heading excursion
elif od >= (S_START - FAILSAFE_MIN):
    reason = 3
...
if reason:
    brake_all()
```

Bound constants: `S_START = 1000.0` (T4) · `G_TARGET = 23.0` (= 3σ) · `T_EFF = 0.09239` (T4-anchored) · `K_TRAVEL = 0.482` · ranger A monitor-only, gating nothing.

Full source accompanies this report as `operation_program_v3.py`.
