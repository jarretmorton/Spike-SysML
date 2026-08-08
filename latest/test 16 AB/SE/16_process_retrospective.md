# PROCESS RETROSPECTIVE — WallStop

**Document** PR-WALLSTOP-001 · **Type: REPORT** · Written after operation close-out
**Scope:** what in the *process* would have changed the outcome. Not rover findings — those are in the Final Report.

---

## 0. What the process got right, and what it bought

Stated first because the gaps below should be read against a method that mostly worked.

| Process element | What it bought, concretely |
|---|---|
| **Frozen predictions, versions retained** | C2's failure was *diagnosable*. Without a committed 37 mm on the record, "measured 222" is just a surprise; with it, it is a 185 mm residual that points straight at one parameter. |
| **Source-of-truth hierarchy** | Stopped the 40 mm clamp reading from overwriting a 26-point regression. That single rule prevented a **30 mm error in the contact direction**. |
| **Section-0 sensitivity before any hardware** | Correctly identified the ranger offset as tier-T0, highest-leverage, and pre-authorised the costed measurement that later caught two ~190 mm errors. |
| **B1 — log every channel, not just the one under test** | The odometry chain existed only because the plan required logging it. When the ranger died, the mission had somewhere to go. |
| **A3 — uncalibrated, not zeroed** | `predict()` refusing to run on unbound parameters caught the identifiability collapse loudly instead of silently fitting a negative deceleration. |
| **Plan vs report distinction** | The falsify → diagnose → re-derive trail is auditable because prior versions could not be edited. |

---

## 1. Channel health is not a requirement class — the largest gap

**What happened.** Ranger A produced six distinct failure modes across four runs: a 40 mm clamp, a yaw-induced freeze, a ~190 mm zero error, a 9.4 % scale error, a +391 mm single-sample spike, and dropouts. Each was discovered *serially*, each triggered its own anomaly report, and the cumulative cost was roughly two characterisation runs and one measurement.

**What was missing.** The REQUIREMENTS METHOD produces *parametric* component requirements — offset, refresh interval, minimum range. My CMP set asked "what is this sensor's offset?" and never asked "**is this sensor's output trustworthy, and how often is it not?**" The CHARACTERIZATION METHOD's channel catalog ranks channels by "directness and confidence," but confidence is assessed **once, qualitatively, before any data exists** — which is precisely when it is least knowable.

**Process addition.** A required requirement class — **channel integrity** — authored alongside the parametric ones, with quantitative measurands:

- inter-run reproducibility of every calibration constant (`|Δzero| across runs ≤ x`)
- within-run self-consistency (monotonicity, rate bounds, repeat-value run length)
- fault rate (invalid or implausible samples per 1000)
- behaviour at both ends of the valid range, including *how* it fails — clamp, drop out, freeze, or lie

And a corresponding **channel-health screen as the first characterisation activity**, before any parameter is bound to that channel. C1 already drove the rover through the ranger's entire range; adding "does it repeat, and how does it fail" to that same run would have cost nothing and disqualified ranger A at run 1 instead of run 3.

**The general principle the process is missing:** *characterise the instrument before you trust the instrument to characterise the system.* Tenet D2 says "instruments are imperfect — characterise the imperfection." It is the right instinct with no machinery behind it, and no requirement forcing the result into the verification argument.

---

## 2. No identifiability check on the calibration design

**What happened.** I built the model on `StoppingDistance = v·t_response + v²/(2a)` with both terms free, planned a calibration for them, ran it, and discovered at GATE B that two stops 2.8 % apart in speed cannot separate the terms — the fit returns a **negative deceleration**. The model had to be restructured after the run that was supposed to bind it.

**What was missing.** GATE A's section 0 sweeps each parameter over its prior and reports leverage. That answers *"which parameters matter?"* It never asks *"**given the experiment I am about to run, can I actually determine them?**"* Leverage and identifiability are different questions, and only one of them was required.

**Process addition.** Section 0 gains a second, mandatory half: an **identifiability / observability analysis of the planned run design**. Concretely — for the planned excitation, compute the sensitivity matrix of predicted observables with respect to free parameters, and report its conditioning. Any parameter pair whose columns are near-collinear is flagged **before the gate** as either (a) needing a design change that excites them differently, or (b) not identifiable, therefore to be lumped and never fitted.

Two-line rule: **no parameter enters the model unless the planned calibration can determine it.** Tenet A2 says "develop only what calibration can falsify" — this is the missing machinery for actually checking that, rather than discovering it after spending the run.

The same check catches the deeper problem in §3.

---

## 3. Nothing detects a self-referential calibration chain

**What happened.** I calibrated the ranger offset from odometry that was itself scaled against the ranger. Two channels, one of them derived from the other, agreeing with each other and **jointly wrong by ~190 mm**. I noticed the circularity at GATE A and wrote it up — and still had no way to break it except an external measurement.

**What was missing.** The source-of-truth hierarchy ranks channels by *trust*. It contains nothing that checks whether two channels are *independent*. "Cross-sourcing" (GtWR rule 6) is required, but "cross-sourced" is satisfied by any two channels — including two that share a common mode.

**Process addition.** A required **independence audit** in the channel catalog: for every quantity, a dependency graph showing which channels derive from which, with **common-mode links marked explicitly**. Two channels sharing an upstream constant are not two channels. The rule that follows: *a scored quantity may not be closed on a set of channels whose dependency graph has a single root.* That is a mechanical check on a diagram, and it forces the external anchor into the plan by construction rather than by my noticing.

---

## 4. A calibration manoeuvre that perturbs the article

**What happened.** C1 ended by creeping the rover into the wall and stalling the motors against it — my deliberate choice, made to obtain a physical zero for the offset. The most probable cause of the subsequent zero error is the impact I commanded in order to calibrate it. **The calibration destroyed the calibration it produced**, and because an offset enters as a constant, nothing in C1's own telemetry could reveal it.

**What was missing.** "Test like you fly" governs whether the *test* represents *flight*. Nothing governs whether the test **changes the article**.

**Process addition.** A required line in the run design: for each characterisation activity, **what does this manoeuvre do to the system, and what is re-verified afterwards?** Any activity involving contact, stall, impact, thermal excursion or disassembly triggers a mandatory **post-activity configuration re-check** — repeat the cheapest measurement taken *before* the activity and confirm it reproduces. In this case: re-read the static start-line distance after the creep. One second of run time; it would have caught a 190 mm shift immediately.

---

## 5. Replicate count is not tied to sensitivity

**What happened.** `Δ` was bound from **n = 2** anchors. Both happened to be the two largest of the seven Δ values eventually observed. The result was a **6.08 mm systematic** in every onboard estimate, matched to 0.02 mm by the observed bias.

**What was missing.** The process requires evidence basis to be *recorded* ("how many samples, against what reference, at what tier") but never requires it to be *sized*. There is no link from the section-0 sensitivity ranking to a **required replicate count**.

**Process addition.** The section-0 table gains a column: **required replicates, derived from leverage × prior spread × target contribution to the margin.** A parameter with 1:1 leverage on the scored quantity and a wide prior does not get n = 2. C1 already performed two full-speed stops in one run; four would have been free, and Δ's standard error would have halved.

---

## 6. No cost-of-uncertainty analysis — the biggest score loss

**What happened.** `σ_S` (start-line placement) was the **largest term in the margin budget at 5.0 mm, and it was an assumption, not a measurement.** I flagged it as such at GATE B′, in writing, twice. Observed reality was ≲1–2 mm. Total σ came out **2.5× conservative**, and since the design sets the target at 3σ, that cost roughly **13 mm of the objective** — larger than every other error in the programme combined.

**What was missing.** Flagging an assumption is not the same as pricing it. Nothing in the process required me to compute *what the assumption was costing*.

**Process addition.** The Calibration Plan gains a required **value-of-information section**: for each budget term, report **∂(objective) / ∂(that term)** and the **cost of the cheapest measurement that would bind it.** Any term that is (a) assumption-tier and (b) dominant gets an explicit accept-or-measure decision with the objective cost stated in millimetres.

Here that analysis would have read: *"σ_S = 5 mm assumed, dominant, costs 13 mm of objective; three repeated placements measured by the operator would bind it for one costed action."* I would have bought it immediately. Instead I spent a measurement on a parameter the sensitivity table had already ranked, and left the dominant one unmeasured because it never occurred to me to price it.

**This is the single change I would most want.** The section-0 table tells you where to look; it does not tell you what *not knowing* is worth.

---

## 7. Protection systems are not verified separately from function

**What happened.** I added a cross-channel divergence failsafe. It fired on **one spurious sample**, aborted a good run, and cost an entire characterisation run (C3). The failsafe worked exactly as designed and was still a net negative.

**What was missing.** The process verifies that the function meets its requirements. It has nothing on verifying the **protection system as a system**: no false-trip budget, no requirement that protection not reduce mission success, no analysis of trip probability given the *measured* fault rate of the channel the protection reads.

**Process addition.** Failsafes get their own requirements and their own verification, with two measurands: **coverage** (fraction of the hazard it catches) and **spurious trip rate** (per run, computed from the *measured* fault statistics of its input channels). A protection element whose spurious-trip rate exceeds the hazard rate it mitigates is a net negative and must be removed. Had I computed the trip probability from ranger A's *observed* fault rate rather than from an assumption that it was healthy, that failsafe would never have been armed.

---

## 8. Requirements have no declared measurand

**What happened.** SYS-1 read *"the rover's final clearance shall be no less than the contact margin."* At verification I discovered it does not say whether *final clearance* means the **predicted** value or the **realised** one — and the two give opposite verdicts (23.0 ≥ 22.4 PASS; 14.0 < 22.4 FAIL). The realised reading is also internally incoherent: with the target set at 3σ, half of all realisations fall below 3σ by construction.

**What was missing.** EARS grammar constrains *sentence form*. It does not require the author to state **what is measured, by what method, at what point in the lifecycle**. A requirement can be perfectly EARS-conformant and still ambiguous about its own measurand.

**Process addition.** Every requirement carries a mandatory **verification statement at authoring time**, not at GATE C: *measurand · method · point of evaluation · pass criterion.* Writing "measurand: predicted final clearance, evaluated by the executable model at bound values" next to SYS-1 at GATE A makes the ambiguity impossible to write down. Cheap, mechanical, and it converts a defect found at verification into one that cannot be authored.

---

## 9. Anomalies are dispositioned individually, never aggregated

**What happened.** AR-001, AR-002, AR-003, AR-004 — four reports, and in hindsight substantially **one finding**: the ranger is not a usable channel. Each disposition was locally correct and locally minimal: fix the validity gate; disqualify B; withdraw A's zero; withdraw A entirely. The pattern was visible by AR-002 and I did not act on it until AR-004, costing about one run.

**What was missing.** ANOMALY DISPOSITION is entirely per-anomaly. There is no trending, no per-component tally, no escalation on repetition.

**Process addition.** A standing **anomaly register keyed by component**, reviewed at every gate, with an explicit escalation rule: **N distinct anomalies on one component within M runs triggers a component-level disposition review** — retain / degrade / withdraw — rather than another local fix. The question changes from *"how do I handle this reading?"* to *"should this component still be in the design?"*, and it gets asked on a schedule instead of when the engineer finally loses patience.

---

## 10. No budget re-baselining trigger

**What happened.** Plan: 2 runs, 1 measurement. Actual: **4 runs, 3 measurements** — 2× and 3× over. Every individual decision was defensible and I justified each in the moment. The overrun was never a *decision*; it accumulated.

**Process addition.** A **re-baselining trigger**: when actuals exceed the gated plan by a stated threshold, the plan is re-issued with a new budget, a new justification, and an explicit stop-or-continue recommendation. This converts drift into a deliberate, reviewable choice. Calibration Plan v1.1 revised the *technical* content after C1 but carried the original budget forward unexamined — exactly the moment a re-baseline should have been forced.

---

## 11. Operator-supplied data has no provenance step

**What happened.** Five measurements arrived; one was the verification result mis-carried into the operation set, and one operation run was missing. Caught only because the close-out reconciliation looked wrong.

**Process addition.** Operator data is **echoed back against run IDs for confirmation at the time it is given** — "recording 222 mm as the C2 verification gap, run-20260807-113932" — before it enters any analysis. The process treats operator measurement as a costed, high-trust instrument; instruments get provenance and confirmation, and this one had neither.

---

## 12. Where the process was fine and I simply failed

Recorded so the retrospective is not entirely a request for more scaffolding:

- **The emit gap (AR-001 A-4).** FUN-8 required logging off the hot path. I applied it to the approach and forgot the stop, blinding the rover for 311 ms across the braking transient. No process gap — I under-applied my own requirement. *(A checklist item "apply the hot-path rule at every phase transition, not just the main loop" would still have caught it.)*
- **Charts.** The protocol said show telemetry charts after each program. I skipped C2, C3 and the individual operation runs until asked.
- **Post-hoc inference.** My yaw-clustering hint about which run was unmeasured was **wrong**. Labelling it suggestive-only and refusing to put it in a results table is the only reason it contaminated nothing — that part worked.

---

## 13. The four changes worth the most

| Rank | Addition | Would have prevented |
|---|---|---|
| 1 | **Cost-of-uncertainty / value-of-information section** in the Calibration Plan | ~13 mm of objective — the largest single loss |
| 2 | **Channel-integrity requirement class + health screen before parameter binding** | ~2 runs, 1 measurement, and most of the programme's churn |
| 3 | **Identifiability check on the planned run design at GATE A** | the model restructure between GATE B and B′; the self-referential offset |
| 4 | **Post-activity configuration re-check after any perturbing manoeuvre** | the 197 mm miss |

The common thread: the method is strong at **ranking what matters** and **freezing what you claimed**, and weak at **checking that the experiment you designed can actually answer the question you asked** — and at **pricing what you have chosen not to measure.**
