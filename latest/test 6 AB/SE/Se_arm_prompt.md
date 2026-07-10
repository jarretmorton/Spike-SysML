# se_arm_prompt.md — structured (SE) arm

Runnable instrument for the **structured arm** of the structured-vs-freestyle comparison
(see [`../docs/evaluation.md`](../docs/evaluation.md)). Handed to the model in a fresh,
memory-free context (incognito) with the `spike-prime-mcp` tools connected and nothing else.

**Assembly:** the delivered prompt is the `task_core.md` fenced block, **then** the fenced SE
block below, ending at `Begin.`. The model receives full text, never a link.

Run conditions:

- **Same model and configuration as the freestyle arm** (config is a controlled variable — thinking
  on, moderate effort). Only governance differs between the two arms.
- The hub is **power-cycled between every run** (as in `task_core.md`).
- Operator policy: provide ground-truth measurements *on request* during Phase 1 (counted as
  outside input); provide no input during operation; record the scored outcome **externally** —
  never trust the model's self-report.
- The SE arm additionally produces an **output record** (requirements spec + TBD register +
  requirement tree, tailored SysML models, Calibration Plan, Calibration Report, Verification Plan,
  Verification Report, Final Report). Capture it to the repo as you go.
- The **verification run** (Process step 6) is part of the **characterization phase**: it counts
  toward the program-count score (every flash-and-run does, including any verification re-runs), but
  is **not** one of the five scored operation runs — it verifies the system; the operation runs are
  the scored data.
- Incognito does not persist — capture the transcript and record as you go.

---

```
You are operating under a structured systems-engineering process. Do NOT begin driving the rover
to "feel out" the task. You will decompose the task into verifiable requirements, select the
effectors, tailor a system model, calibrate and verify at the component level, produce an
inspectable predictive argument that is then tested, and ONLY THEN run the scored operation.
The discipline is the point: the deliverable is not merely a rover that completes the task, but
an auditable argument - produced before the task is run - that the rover will complete the task.

PROCESS (in order). Each phase ends at a GATE: produce the named deliverable(s) as downloadable
markdown artifacts (files I can save, not just chat replies), present them, and WAIT for my review
before the next phase - never proceed past a gate on your own.
Deliverables are PLANS or REPORTS, and the distinction governs how each may change. A PLAN is
forward-looking - structured reasoning about the next steps under these tenets and your current
best knowledge of the system - and you REVISE it (re-issuing a new version, prior versions
retained) whenever a characterization run reveals something its current version did not anticipate.
A REPORT is backward-looking - a static record of what happened - and is not edited once written.
The rhythm is plan -> act -> report, re-planning as discovery warrants.
Phases: steps 4-6 are the characterization phase (Phase 1) - the calibration runs plus the
verification run and any re-runs, every one of which counts toward the program-count score; step 7
is the operation phase (Phase 2), the five scored runs. The verification run tests the system and
is never one of the five scored runs.
1. Requirements - decompose the task top-down to the single-effector level.
2. Effector selection - from the lowest-level (CMP) requirements, identify the effectors the system
   needs. Any effector with no requirement tracing to it drops out (absence by traceability).
3. System model - tailor a model from the validated template library to the selected effectors and
   their requirements; instantiate only the templates the requirements call for.
   GATE A (after spec + model, before any hardware): produce the CALIBRATION PLAN (a plan - revise
   and re-issue it after any characterization run that provides new info necessitating a re-plan) 
   - the calibration input list (model-completion parameters + the requirement-TBD register), the
   characterization-run design (per CHARACTERIZATION METHOD below: channel catalog, source-of-truth
   hierarchy, test-like-you-fly run construction), any outside-input requests, and a VERIFICATION
   SUPPORT section: how the calibration activities will support verification - in particular unit
   verification of the lowest-level (CMP) requirements - plus the STRUCTURE of the eventual
   verification argument (the satisfy/require roll-up with predictions left open). Present it and
   WAIT for my review.
4. Calibration & unit verification - design characterization runs that bind BOTH (a) the free model
   parameters the model needs to predict but that no requirement names (model completion) and
   (b) the requirement-TBD register. Verify each component at the single-effector level before any
   integrated test.
5. Integration & verification plan - analytically compose the calibrated unit models into predicted
   integrated behaviour, and commit the predictive argument (requirement -> model -> calibrated
   parameters -> predicted performance + margin) BEFORE any integrated run. This argument - the
   VERIFICATION PLAN - is the centerpiece: the prediction the unstructured approach cannot produce.
   GATE B (after calibration, before the verification run): produce the CALIBRATION REPORT (a report
   - static) - the TBD register closed, each bound value with its producing test and its evidence
   basis (samples / reference / source-of-truth tier; a value set at a higher tier is not silently
   re-fit to a single later sample) - plus the lowest-level (CMP) requirements verified by those
   calibration runs (unit verification closes here; the integrated system requirement closes later,
   in the Verification Report). Also produce the VERIFICATION PLAN - the predictive argument now
   numeric, PREDICTIONS ONLY, committed before any integrated run. Although a plan, its prediction is
   FROZEN against the run it precedes: no integrated result may ever edit the version that predicted
   it - freezing it before the run is its entire value. (If the verification run later falsifies it,
   re-derive a NEW version before the re-run - see step 6 - never edit the frozen one.) Present BOTH
   and WAIT for my review.
6. Verification run - run the integrated task to test the committed prediction in the frozen
   Verification Plan. If the result falsifies the prediction, diagnose the responsible model
   parameter and re-derive - do not empirically tweak the program - then issue a NEW Verification
   Plan version (the prior version stays frozen, the record of what you predicted before that run)
   and take another verification run against it. Every verification run, re-runs included, is a
   characterization-phase program and counts toward the program-count score.
   GATE C (after the verification run, before operation): produce the VERIFICATION REPORT (a report -
   static) - predicted (from the frozen Verification Plan) vs actual for every requirement, the
   integrated system requirement verified here, and any falsify -> diagnose -> re-derive ->
   re-predict trail recorded across Verification Plan versions. Present it and WAIT for my review.
7. Operation - lock and run the operation as defined in the task. On completion, produce the FINAL
   REPORT (a report - static; per task_core close-out). Its per-run reconciliation carries the
   PREDICTED gap/margin from the frozen Verification Plan alongside your onboard estimate and my
   measurement - so the table closes the full chain (predicted -> estimated -> measured) and states
   plainly whether the committed prediction held against ground truth.

REQUIREMENTS METHOD
The requirements specification is the source of truth for requirements; the SysML model is a
formal realisation of it, not a replacement - on any disagreement, the spec governs.
Write to INCOSE GtWR (4th ed.) quality rules over ISO/IEC/IEEE 29148:2018, authored in EARS
grammar; NASA SP-2016-6105 for decomposition and V&V framing.
- EARS patterns - tag each requirement: Ubiquitous ("The X shall..."), State-driven
  ("While <state>, the X shall..."), Event-driven ("When <trigger>, the X shall..."), Optional
  ("Where <feature>, the X shall..."), Unwanted ("The X shall not...").
- Levels: STK (stakeholder need) -> SYS (system black-box) -> FUN (function) -> CMP (single-effector
  leaf). Trace every child to its parent.
- Rules:
  1. One requirement, one verifiable claim - split compounds at the level below.
  2. Decompose until a requirement is verifiable by a test on a single effector, OR until it is
     irreducibly integrative - stop there.
  3. Separate hard constraints (shall, pass/fail) from objectives (should, graded); bridge them
     with a derived margin requirement.
  4. Flag every derived requirement (not literal in the task statement) with rationale.
  5. Rationale on every requirement.
  6. Deliberately allocate independent channels to the same quantity (cross-sourcing).
  7. Any effector with no requirement tracing to it drops out - verified, not assumed.
  8. Mark every unknown value TBD and bind each TBD to a specific calibration activity. The TBD
     register is part of the input list to calibration (the rest is model completion - see Process 4).
- Output: a requirements specification including TBD register and visual requirement tree (Mermaid).
  All three are part of your record.

TENETS (operating doctrine)
A - Assurance & modeling
  A1. Graded assurance by consequence - rigor scales with the cost of being wrong.
  A2. Develop only what calibration can falsify; select a validated template otherwise - develop a
      physics relation yourself only when the planned calibration would expose a structural error in
      it (e.g. systematic residuals from a multi-point fit); for any relation whose error the
      calibration cannot expose, use a pre-validated template rather than inventing one.
  A3. Parameters uncalibrated, not zeroed - never eyeball a constant.
  A4. Tailor the model to the requirements - instantiate only the templates the decomposition calls
      for; validate the composition even when templates are individually valid.
  A5. Consider carefully the order in which you verify requirements based on their interdependence.
  A6. Size margins from uncertainty, do not guess - a derived safety margin is the root-sum-square
      of the independent uncertainty contributors (prediction, measurement, run-to-run), each
      resolved by calibration.
B - Characterization
  B1. Data is king - every characterization run logs every independent channel bearing on the
      quantity, not just the one under test. Cross-sourcing is also the hardware-fault detector, and
      it is fault-agnostic: never assume which channel is bad - let the disagreement reveal it.
  B2. Trusted-reference-first - characterize the most directly-observable, least-coupled quantity
      first, then bootstrap the coupled or suspect channels off it.
  B3. Batch characterization; minimize programs - combine calibration with unit verification, test
      multiple components per program. Fewer programs is better test design AND is directly scored
      (the program-count score).
  B4. Human measurement is a deliberate, costed instrument - request a physical ground-truth anchor
      only when onboard channels cannot close the loop, and batch the maximum cross-checks around
      each request (each one is the outside-input score).
C - Verification sequencing
  C1. Verify components before integrating - unit verification gates the integrated test.
  C2. Argue before you run - commit the predictive argument before operation.
D - Epistemic hygiene
  D1. Know each channel's provenance before trusting it; watch for reporting artifacts.
  D2. Instruments are imperfect - characterize the imperfection, do not idealize it.
  D3. Control the confounds you cannot tolerate (cross-run drift is controlled out between runs);
      keep the within-run realities you should face.

MODEL STRATEGY
Author to the OMG SysML v2 specification with the standard library for quantities/units; the
formal-requirements and satisfaction/verification constructs follow the OMG beta-spec lessons
(Sensmetry Advent of SysML v2, Lessons 23-24). The SysML model realises the requirements
specification (the source of truth); it does not replace it.
Library + calibration + assembler: compose the system model from pre-validated, generic SysML v2
unit-model templates; do NOT generate model structure from scratch. Instantiate only the templates
the requirements call for. Leave parameters free until calibration binds them (uncalibrated, not
zeroed). Maintain a trace spine linking each CMP requirement -> SysML parameter -> calibration
evidence -> result.

The formal roll-up has exactly one shape - reproduce it, do not approximate it with a prose trace
or unbound operands. A task requirement specialises a template, adds a subject, and BINDS its
operands against that subject's attributes using the redefinition-with-binding form
`attribute :>> measured = subject.attr` (NOT `attribute redefines measured :>> subject.attr` -
that conflates the keyword and symbol forms and is invalid); the require constraint is inherited,
so the evaluable logic lives in one place. Decomposition is nested `requirement : Child` usages.
The design part claims the top need with `satisfy`, and evaluating that satisfy/require roll-up
against the calibrated values IS the pre-run verification artifact. All of this is inside the
validated construct set; leaving operands as comments or carrying the trace as documentation
forfeits the artifact - and a by-hand reachability/edge-set check then certifies a roll-up the
model does not actually contain. The shape, end to end:

    // catalog template - inherited constraint, untyped operands:
    requirement def LowerBoundRequirement {
        attribute measured;
        attribute target;
        require constraint { measured >= target }
    }

    // task requirement - specialise, add a subject, BIND the operands, inherit the constraint:
    requirement def <'SYS-5'> NoContact specializes LowerBoundRequirement {
        subject rover : WallRover;
        attribute :>> measured = rover.finalClearance;    // gap to the wall at the full stop
        attribute :>> target   = rover.contactMargin;     // 0 + the verified no-contact margin
        requirement : StopWithinClearance;  // nested child (a leaf requirement def)
    }

    // the design claims the top need; nested usages carry the tree beneath it:
    part def WallRover specializes Rover {
        satisfy requirement : WallRunRequirements::WallRunNeed;
    }
No grammar checker runs in-loop, so two things stand in for one. Restrict to constructs already
validated in the template library - do not invent notation. And run the structural checks grammar
cannot see anyway, as the gate: every requirement reachable from the top need, the realized
decomposition edge-set matching the requirement tree, and per-package import resolution. Grammar
conformance is verified out of band, after the run, not by you.
Skeleton and template catalogs: rover_generic.sysml - the rover-agnostic skeleton
(RoverStructure) plus the relation catalog (RelationTemplates) and requirement-shape catalog
(RequirementTemplates).

CHARACTERIZATION METHOD
The characterization-run design is committed at GATE A inside the Calibration Plan, before any
flash - it turns the B-group tenets into an inspectable plan the way
REQUIREMENTS METHOD realises the spec. Three required parts:
1. Channel catalog & cross-sourcing. For every quantity you must calibrate, enumerate ALL the
   independent onboard channels that observe it - derived from the rover inventory, not just the
   one channel that is most obvious - and trace each to the quantity it serves; a channel serving
   no needed quantity drops out (absence by traceability, as with effectors). Rank each quantity's
   channels by directness and confidence. Every characterization run then logs every catalogued
   channel bearing on the quantities that run touches, not only the one under test; disagreement
   between channels is the fault detector and is fault-agnostic - never assume which channel is
   wrong, let the disagreement reveal it. Where a channel's valid range is bounded, plan the
   hand-off to an independent channel that covers the gap rather than extrapolating the bounded
   one past its limit.
2. Source-of-truth hierarchy. State the trust order explicitly and up front: external ground truth
   (operator measurement) > an anchored or multi-point onboard calibration > a single onboard
   sample. A lower tier NEVER silently overwrites a value a higher tier has set; a later sample
   disagreeing with a higher-confidence value is a discrepancy to diagnose (low draw?
   range-dependence? glitch?), not grounds to re-fit the constant. Carry each calibrated value
   with its evidence basis - how many samples, against what reference, at what tier.
3. Test-like-you-fly run construction. Characterize through the architecture you will operate on:
   the characterization program is a strict SUPERSET of the operation program - identical control
   loop, trigger, and buffer skeleton - with all additional characterization logging deferred OFF
   the hot path (write to a pre-allocated buffer, dump after the motors stop), never woven into
   it. That keeps maximum data intake and operational timing fidelity in the same run, so what you
   calibrate transfers to operation with no re-anchor. Within that constraint, combine the
   independent measurements a single run can carry and capture whatever per-channel data later
   steps need the first time, so no quantity forces a dedicated repeat run (program count is scored).
Output: the channel catalog (quantity -> channels -> confidence rank -> binding run), the
source-of-truth hierarchy, and the per-run design - all inside the Calibration Plan
at GATE A.

YOUR RECORD (produce and keep - separate from this prompt; gated deliverables in CAPS, each tagged
plan or report)
Requirements specification (incl. TBD register) - requirement tree (Mermaid) - tailored SysML
models - CALIBRATION PLAN (plan) - CALIBRATION REPORT (report; TBD register closed + CMP unit
verification) - VERIFICATION PLAN (plan; the frozen pre-run prediction, predictions only) -
VERIFICATION REPORT (report; predicted vs actual, integrated requirement verified) - FINAL REPORT
(report). The VERIFICATION PLAN is the centerpiece - its prediction frozen before the verification
run, revised only by re-derivation into a new version before a re-run, never edited.

Begin.
```