# Structured vs. Freestyle Agentic Engineering — A Hardware A/B Comparison

*Living comparison document. The same physical task is given to a model under two regimes — a
structured systems-engineering (SE) arm and a freestyle arm — on identical hardware, and their
**outcomes** and **auditability** are compared. This file is built to grow: repeats of each arm and
additional model tiers slot into the Run Registry (§4) and the per-run tables without restructuring.*

**Instance 1:** Claude Opus 4.8 (Max Thinking), **n = 1 per arm.** A single pair is an existence
proof and an illustration, not a statistical result; see Caveats (§8).

---

## TL;DR

Both arms succeeded at the safety-critical objective — **5/5 operation runs with no wall contact** —
on comparable run budgets (SE 14 hardware runs, freestyle 13). **The freestyle arm won on outcome:**
mean gap **91.8 mm** (σ 6.8) versus the SE arm's **192 mm** (σ 12) — roughly 2× closer, and tighter.
This was expected: the SE arm was deliberately sensor-limited by a documented fail-safe choice;
freestyle imposed no such constraint.

The arms separate on exactly one axis: **auditability.** The SE arm committed, *before any operation
run*, to a predicted gap of **189 mm** with a margin sized from quantified uncertainty, and the five
runs measured **192 mm — the frozen prediction held to 3 mm**, with every requirement's pass/fail and
its one waiver declared in advance. The freestyle arm produced **no pre-run prediction at all**; its
own onboard estimate was 65 mm against a true 92 mm, a +26 mm bias it discovered only at close-out and
explained after the fact. Capability was never the question. The structured arm's value is the
inspectable, committed-in-advance, honest account — which freestyle did not produce **even while
stopping closer.** That is the thesis in its strongest form: not "structure wins the task," but
"structure produces an argument you can trust, and outcome superiority does not."

---

## 1. The question

The claim under test is **auditability over outcome superiority.** As AI agents take on physical
engineering tasks, the interesting differentiator is not whether a capable model can achieve a good
result — it can — but whether the *process* yields an artifact a reviewer can inspect, check, and
trust **before** committing to hardware: a pre-run argument that states what will happen and why it is
safe, sized from evidence, honest about what it does not know.

A capable model under a freestyle regime is expected to reach a good outcome by empirical iteration.
The hypothesis is that it will **not** produce the inspectable pre-run argument, and that the gap is
visible and consequential. The structured arm is expected to produce that argument — possibly at a
cost in outcome and effort — and the comparison is whether the argument *holds* and whether the
freestyle arm's good outcome comes with any equivalent.

This connects directly to the "model-anchoring" line of work (externally-anchored predictions vs.
self-assessment; black-box confidence procedures): a recurring finding is that an externally-anchored
prediction beats a system's own self-report. §6.2 shows that result reproduced **in hardware**.

---

## 2. What "auditability" means here — the operational definition

To avoid hand-waving, "auditability" is scored on concrete artifacts a reviewer can hold *before* the
scored runs:

1. **A committed pre-run prediction.** A specific predicted outcome (here: true rest gap), frozen
   before any scored run, that the run then tests. Frozen = no measured result may be written back
   into a predicted cell.
2. **A margin sized from quantified uncertainty**, not guessed — with the contributors enumerated and
   the safety conclusion stated in advance.
3. **A traceable requirement account** — every requirement's predicted pass/fail, decomposed to the
   single-effector level, with conformance claims that match what the design actually does.
4. **Declared limitations and waivers** — what the design does *not* satisfy, named and justified up
   front, not discovered at the end.
5. **Honest treatment of unknowns** — quantities the system cannot self-measure either *measured* with
   a deliberate external anchor, or explicitly bounded — rather than narrated after the fact.

The freestyle arm is free to produce any of these; the question is whether it does.

---

## 3. Method

### 3.1 Shared task

Drive a LEGO SPIKE Prime rover straight at a wall ~1000 mm ahead, at maximum speed, and stop as close
as possible **without contact**. Develop and calibrate a program (characterization), then **lock one
program and run it five times unchanged** (operation). No-contact is the paramount scored axis;
closeness is the graded objective.

### 3.2 The two arms

- **SE arm.** Given a structured systems-engineering method: requirements decomposition (stakeholder →
  system → function → component, EARS-patterned), a tailored SysML v2 model realising the
  requirements, a calibration & verification plan, human review **gates** (A: plan; B: frozen
  predictions; C: verification), and a falsify→diagnose→re-derive loop. Emits a sequence of inspectable
  artifacts.
- **Freestyle arm.** Given the same task and the same hardware interface, with the instruction that
  **no method is prescribed or prohibited** — approach it however it judges best. Emits whatever it
  chooses; in this instance, a single final engineering report.

### 3.3 Held constant vs. varied

| Held constant (both arms) | Varied (the independent variable) |
|---|---|
| Model + config: Claude Opus 4.8, Max Thinking | Method regime: structured SE vs. freestyle |
| Fresh incognito session, no cross-contamination | The prompt's method content (the *only* intended difference) |
| Hardware: same rover, Pybricks, spike-prime-mcp (flash/run/telemetry) | — |
| Shared task core (task, envelope, scoring) — identical text both arms | — |
| Operation protocol: lock one program, run 5× unchanged | — |

The task-core text — task statement, operating envelope, and the **scored axes** (counted
characterization runs and outside-input actions) — is identical for both arms. Run-frugality is
therefore not instructed; it is left as a behaviour each arm may or may not exhibit. (This matters:
the SE arm's frugality is an *output* of its method, not a directive; instructing the freestyle arm to
economise would have contaminated the run-count axis.)

### 3.4 Scoring axes

**Outcome:** no-contact rate (paramount), closeness (mean gap), repeatability (σ), run count.
**Auditability:** the five artifacts of §2. The auditability axis is the one only the SE arm is
structurally positioned to fill; whether freestyle fills any of it is the finding.

---

## 4. Run Registry (extensible)

Each row is one arm × one model × one instance. Add rows for repeats and new model tiers.

| Instance | Arm | Model (config) | Hardware runs (char / +verif / op) | No-contact | Mean gap (mm) | σ (mm) | Committed pre-run prediction? |
|---|---|---|---|---|---|---|---|
| 1 | Structured (SE) | Opus 4.8 (Max Thinking) | 8 / 1 / 5 = **14** | **5/5** | **192** | 12 | **Yes — 189 mm, held to 3 mm** |
| 1 | Freestyle | Opus 4.8 (Max Thinking) | 8 / 0 / 5 = **13** | **5/5** | **91.8** | 6.8 | **No** |
| 2 | Structured (SE) | *(planned repeat)* | — | — | — | — | — |
| 2 | Freestyle | *(planned repeat)* | — | — | — | — | — |
| 1 | Structured (SE) | *(planned: lower tier)* | — | — | — | — | — |
| 1 | Freestyle | *(planned: lower tier)* | — | — | — | — | — |

*Run-count note:* both arms reached a locked, working program in **8 characterization runs**; the SE
arm additionally spent one dedicated verification run to test its frozen prediction (freestyle folded
verification into its 8th characterization run). On effort, the arms are **roughly tied** — a
correction to the in-the-moment impression that freestyle was struggling; it converged in a comparable
budget. The canonical per-run characterization ledger should be reconciled from the operator's live
log (see §8); the arms' self-reported ledgers are secondary.

---

## 5. Outcome results

### 5.1 Scorecard

| Axis | SE arm | Freestyle arm | Winner |
|---|---|---|---|
| **No contact (5 op runs)** | 5/5 | 5/5 | **Tie** |
| **Closeness (mean gap)** | 192 mm | **91.8 mm** | **Freestyle** (~2×) |
| **Repeatability (σ)** | 12 mm | **6.8 mm** | **Freestyle** — but see note |
| **Run count (hardware)** | 14 | **13** | **~Tie** |
| Operation gap range | 171–200 mm | 81–99 mm | — |

*σ note.* Freestyle's spread is tighter **and** was *discovered* at close-out; the SE arm's spread was
**predicted in advance** (σ_run sized to ~11 mm, measured 12 mm). The same number means different
things on the two sides: an observed property vs. a forecast that held.

### 5.2 SE arm — operation runs (vs. the frozen prediction)

Frozen at Gate B before any operation run: predicted true rest gap **189 mm** (band ~150–220),
`designMargin` = 72 mm (k = 3 · RSS of σ_run≈11, σ_offset≈15, σ_model≈15, σ_meas≈3).

| Run | Predicted (frozen) | Onboard est. (frozen) | Measured | Meas − Pred | Meas − Onboard | Contact |
|----:|----:|----:|----:|----:|----:|:--:|
| 1 | 189 | 166 | 197 | +8 | +31 | No |
| 2 | 189 | 165 | 171 | −18 | +6 | No |
| 3 | 189 | 178 | 198 | +9 | +20 | No |
| 4 | 189 | 169 | 196 | +7 | +27 | No |
| 5 | 189 | 167 | 200 | +11 | +33 | No |
| **mean** | **189** | **169** | **192** | **+3** | **+23** | **0/5** |

The frozen prediction matched the measured mean to **+3 mm**. The separate verification run (pre-op)
predicted 189, measured 173 — a 1.1σ residual inside the stated band, diagnosed (mild distance
dependence of the sensor offset, pre-bounded by σ_model), not retro-fitted.

### 5.3 Freestyle arm — operation runs (no pre-run prediction)

| Run | Onboard est. | Measured | Meas − Onboard | Contact |
|----:|----:|----:|----:|:--:|
| 1 | 65.7 | 99 | +33.3 | No |
| 2 | 64.7 | 87 | +22.3 | No |
| 3 | 64.9 | 95 | +30.1 | No |
| 4 | 66.6 | 81 | +14.4 | No |
| 5 | 64.9 | 97 | +32.1 | No |
| **mean** | **65.4** | **91.8** | **+26.4** | **0/5** |

No predicted column exists. The onboard estimate (σ 0.8 mm) is a near-constant model output — it is
structurally blind to the real ±7 mm run-to-run spread (the encoder-based trigger fires at a fixed
wheel-count, so the *model* barely varies while the *physical* stop does). The +26 mm bias between
onboard estimate and truth was visible only once the operator measured at close-out.

---

## 6. The auditability axis — the differentiator

This is the section the two arms do not share. Every subsection below is something the SE arm produced
and the freestyle arm did not.

### 6.1 Committed pre-run prediction: present vs. absent

- **SE:** "true rest gap ≈ 189 mm, no contact, heading ≤ ~6°" — frozen at Gate B, before any
  close-range run, with the explicit rule that no measured result may edit a predicted cell. Tested;
  held to 3 mm.
- **Freestyle:** none. There is no artifact committing to an outcome before the run. The closest analog
  — the onboard estimate — was 65 mm against a true 92 mm, and was not framed as a prediction to be
  tested. The rover stopped at 92 mm because the configuration was, in the report's own words, "even
  more conservative than intended" — safe margin it did not know it had.

This is the cleanest, most undeniable line in the comparison: **189 → 192 (held to 3 mm) vs. no
prediction at all.**

### 6.2 The model-anchoring result, reproduced in hardware

The SE arm carried **two** estimates of the gap: an **externally-anchored prediction** (189 mm, built
at Gate B from a deliberate ground-truth anchor `g_char` plus the cross-sourced sensor offset) and an
**onboard self-estimate** (per-run, mean 169 mm). The externally-anchored prediction was **unbiased**
(+3 mm); the onboard self-estimate was **biased low by ~23 mm**. The anchor beat the self-report.

The freestyle arm had **only** the onboard self-estimate (mean 65 mm, biased low by ~26 mm) and **no
externally-anchored prediction** to correct it.

So both arms' *self-assessment* was biased low by ~25 mm and both had a self-estimate σ near zero
(blind to their own spread) — a striking parallel. The difference is that the SE arm **also produced
an external anchor that was correct and committed in advance**, while the freestyle arm did not. This
is the model-anchoring thesis (externally-anchored prediction beats self-assessment) and the black-box
confidence finding, materialised in a physical system: the well-anchored prediction held; the
self-report drifted; the arm without an anchor had only the drift. It also reproduces test3's core
result on independent hardware.

*(One internal wrinkle, for honesty: the SE arm's onboard per-run estimate was itself made worse by
re-deriving its offset from a single mid-course verification sample instead of trusting the more robust
anchor — the report diagnoses this. So even within the SE arm, fitting to one fresh sample beat the
anchor's robustness exactly nowhere: the anchor won. That is the same lesson again, one level down.)*

### 6.3 Handling the unknown: measured vs. narrated

Both arms hit the **same** physical unknown — a forward-sensor offset (the ultrasonic does not report
true distance) — because it is in the hardware, method-invariant.

- **SE:** *measured* it. Cross-sourcing (`min` of two sensors) surfaced that sensor B reads ~120 mm
  short; one operator anchor (`g_char` = 469 mm true vs. 346 mm read) fixed the true scale; and the
  untested close-range behaviour was **bounded in advance** by a σ_model = 15 mm term — which is
  exactly where the 16 mm verification residual landed (1.1σ). The unknown was measured *and* its
  residual uncertainty was carried into the margin before the run.
- **Freestyle:** *narrated* it, after the fact. Its onboard zero was referenced to a motor-load contact
  point, which sits ~26 mm ahead of the operator's front-face reference. The report explains this as a
  geometric protrusion offset — a plausible, internally coherent story — but it is a **post-hoc
  explanation of a discrepancy it could only see because the operator measured at close-out.** It did
  not measure the offset; it accounted for it afterward.

Same unknown; one arm calibrated it before locking, the other explained it after running.

### 6.4 Declared limitations

- **SE:** the two forward sensors disagree by ~120 mm — this *fails* a "sensors agree" requirement, and
  it is **waived in advance, transparently**: the bias is folded into the calibrated offset, the
  disagreement is repurposed as a health signal, and the consequence (a ~120 mm closeness floor) is
  named as the binding limitation up front.
- **Freestyle:** no formal requirement set, so no declared waiver. The equivalent limitation (its zero
  is uncertain; it could stop ~3 cm closer with one anchor) appears only in the retrospective ("If
  continued") section, after the runs.

### 6.5 Where each account is less than fully honest

Auditability cuts both ways; both reports have a soft spot, and naming them keeps the comparison fair.

- **SE — one papered conformance cell.** The roll-up reports "command at max — PASS," citing the lead
  wheel. But driving straight *requires* trimming the trailing wheel **below its own max**, so the
  requirement as written ("each motor ≥ its own max") is not satisfied by the trim wheel. The honest
  entry is what it did for the sensor disagreement — waive or reformulate to "matched straight-line
  max." This rode through Gates B and C uncorrected. Notably, the arm was scrupulous about the *measured*
  sensor disagreement (impossible to miss) and glossed the *mis-formulated* requirement that no
  measurement directly falsifies — a blind spot a rigorous process can still carry.
- **Freestyle — emphasis that obscures.** The report leads with "telemetry-only, zero operator
  measurements" as a virtue. This is literally true for *characterization* (it used contact-detection,
  not a ruler). But the framing obscures that the telemetry-only zero was **biased by 26 mm** and that
  the reported gaps (91.8 mm) are operator-measured at close-out — i.e., the headline strength is
  precisely the thing that produced the error, and the trustworthy numbers came from external
  measurement. Not a contradiction; a presentation choice that flatters the weak part.

These are different failure shapes: the SE arm's is a **traceable** error (the cell is right there in
the roll-up, checkable against the design), and the freestyle arm's is a **framing** one (the claim is
true but its implication misleads). The first is auditable by inspection; the second requires external
measurement to catch.

---

## 7. Honest scorecard & interpretation

| | SE (structured) | Freestyle |
|---|:--:|:--:|
| No-contact safety | ✅ 5/5 | ✅ 5/5 |
| Closeness | 192 mm | **91.8 mm — wins** |
| Repeatability | σ 12 (predicted) | σ 6.8 (observed) — **wins** |
| Run efficiency | 14 | 13 — **~tie** |
| Committed pre-run prediction | **✅ held to 3 mm** | ❌ none |
| Anchored prediction beat self-estimate | **✅** | ❌ (no anchor) |
| Unknown measured vs. narrated | **measured + bounded** | narrated post-hoc |
| Declared waiver in advance | **✅** | ❌ |
| Honesty soft spot | 1 papered cell (traceable) | "telemetry-only" framing (obscuring) |

**Reading.** Freestyle won outcome and tied efficiency and safety. The SE arm won auditability —
uniquely and completely. The thesis is supported **not** by the structured arm winning the task (it
did not) but by the freestyle arm being *better on outcome and still* failing to produce a committed,
inspectable, honest pre-run account. If the structured arm had also stopped closer, "structure is just
better" would be the lazy read; because freestyle stopped closer, the comparison isolates the real
variable. **Auditability is what the structured method buys, and it is orthogonal to — and was here
purchased at a cost in — outcome.**

The decision-relevant question this poses: in a setting where a wrong stop is catastrophic and you
cannot run it 5× first to find out, **which artifact would you stake the decision on** — a 92 mm stop
whose process cannot tell you in advance whether the next one contacts, or a 192 mm stop with a frozen
189 mm prediction, a sized margin, and a declared failure mode? That is the trade the structured arm
is selling, now with one clean hardware instance behind it.

---

## 8. Caveats & threats to validity

- **n = 1 per arm.** One pair cannot establish the thesis. It is an existence proof (a capable
  freestyle agent reached a strong outcome with no inspectable pre-run argument) plus an illustration.
  Repeats (§9) are required for any rate claim — both for outcome variance and for whether the
  auditability gap is consistent or instance-specific.
- **Hardware drift.** Both arms crashed during characterization (method-invariant — the motor
  asymmetry, sensor blocking, and saturation traps are in the hardware). Confirm both arms' operation
  runs were on an **intact, equivalent chassis**; a sensor knocked mid-session would mean an arm's σ is
  partly chassis drift. Freestyle's encoder-based trigger is more robust to ultrasonic-mount drift than
  the SE arm's sensor-based trigger, which is itself a confound on the σ comparison.
- **Characterization-ledger reconciliation.** The per-run characterization narrative should be rebuilt
  from the operator's **live log**, not from the arms' self-reports or from in-the-moment commentary.
  The freestyle report's self-described run ledger in particular should be cross-checked against
  observed events for fidelity (e.g., crash count and which runs contacted) — discrepancies there are
  themselves data about self-report reliability, but only if anchored to the canonical log.
- **Commentary bias.** Real-time narration of the freestyle run over-weighted its visible crashes and
  under-weighted its convergence; the final data shows comparable run efficiency. The doc reflects the
  corrected, log-anchored picture, not the live impression.
- **Single operator / single wall geometry.** One environment, one start distance.

---

## 9. Open items / future instances

- **Repeats of Instance 1** (both arms, same model) — to get outcome variance and test whether the
  auditability gap reproduces. Highest priority.
- **Capability-ladder runs** — the same A/B across model tiers. The standing hypothesis: scaffolding
  helps weaker models more, and the *outcome* gap narrows toward parity at the frontier — but the
  *auditability* gap should persist regardless of tier, because it is a property of the method, not the
  capability. If the auditability column stays SE-only across the ladder while outcomes converge, that
  is the strongest form of the result. (Candidate LessWrong piece.)
- **Resolve the SE arm's CMP-MOT-1 framing** in its final report (waive or reformulate to matched-max)
  so the record-run artifact is fully honest.
- **A frozen-prediction prompt for the freestyle arm?** — i.e., does *asking* freestyle for a committed
  prediction close the gap, or does it still not produce a sized, traceable one? A useful ablation that
  probes whether auditability is a method property or just an unasked-for one.
- **Telemetry-grounded appendix** — line up onboard-estimate vs. operator-measured from the raw streams
  for both arms (the numbers above are from the final reports; the raw telemetry is the primary source).

---

## 10. Source artifacts

**SE arm (Instance 1):** `01_requirements_specification.md`, `02_tailored_sysml_model.md`,
`03_calibration_and_verification_plan.md` (Gate A); `04_calibration_report.md`,
`05_pre_verification_report.md` (Gate B); `06_post_verification_report.md` (Gate C);
`07_final_engineering_report.md`. Plus inline charts and per-run telemetry (captured separately).

**Freestyle arm (Instance 1):** `rover_wall_stop_report.md` (single final report). Plus inline charts,
per-run telemetry, and verbatim run-by-run reasoning (captured separately).

**Apparatus:** `Spike-SysML` repo — `experiments/Task_core.md` (shared), `experiments/Se_arm_prompt.md`,
`experiments/Freestyle_arm_prompt.md`, `models/rover_generic.sysml` (SE arm input).

---

*Status: Instance 1 drafted; n = 1 per arm. Outcome figures from the arms' final reports; to be
re-grounded against raw telemetry and the operator's canonical run log.*
