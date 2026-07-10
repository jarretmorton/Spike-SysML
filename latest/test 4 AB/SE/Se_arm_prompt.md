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
  requirement tree, tailored SysML models, Calibration & Verification Plan, Calibration Report,
  Pre-Verification Report, Post-Verification Report, Final Engineering Report). Capture it to the
  repo as you go — it is not pasted back to the model.
- The **verification run** (Process step 6) is recorded *separately* from operation, and is **not** 
  counted as one of the operation runs — the verification run verifies the system; the operation runs
  are the scored data.
- Incognito does not persist — capture the transcript and record as you go.

> Pending: the **tenets** below are the current candidate set, not yet trimmed. The model
> artifact paths are now filled (see Process 3 / Model strategy: `models/rover_generic.sysml`).

---

```
You are operating under a structured systems-engineering process. Do NOT begin driving the rover
to "feel out" the task. You will decompose the task into verifiable requirements, select the
effectors, tailor a system model, calibrate and verify at the component level, produce an
inspectable predictive argument that the requirements will hold, and ONLY THEN run the scored
operation. The discipline is the point: the deliverable is not merely a rover that completes the
task, but an auditable argument - produced before the task is run - that it will.

PROCESS (in order). Each phase ends at a GATE: produce the named deliverable(s) as downloadable
markdown artifacts (files I can save, not just chat replies), present them, and WAIT for my review
before the next phase - never proceed past a gate on your own.
1. Requirements - decompose the task top-down to the single-effector level.
2. Effector selection - from the lowest-level (CMP) requirements, identify the effectors the system
   needs. Any effector with no requirement tracing to it drops out (absence by traceability).
3. System model - tailor a model from the validated template library to the selected effectors and
   their requirements; instantiate only the templates the requirements call for.
   GATE A (after spec + model, before any hardware): produce the CALIBRATION & VERIFICATION PLAN -
   the calibration input list (model-completion parameters + the requirement-TBD register), the
   characterization-run design, any outside-input requests, and the STRUCTURE of the pre-run
   argument (the satisfy/require roll-up with predictions left open). Present it and WAIT for my review.
4. Calibration & unit verification - design characterization runs that bind BOTH (a) the free model
   parameters the model needs to predict but that no requirement names (model completion) and
   (b) the requirement-TBD register. Verify each component at the single-effector level before any
   integrated test.
5. Integration & pre-run verification artifact - analytically compose the calibrated unit models
   into predicted integrated behaviour, and commit the predictive argument (requirement -> model ->
   calibrated parameters -> predicted performance + margin) BEFORE any integrated run. This artifact is
   the centerpiece - it is the argument the unstructured approach cannot produce.
   GATE B (after calibration, before the verification run): produce the CALIBRATION REPORT (the
   TBD register closed - each bound value with its producing test) AND the PRE-VERIFICATION REPORT
   (the pre-run argument now numeric). The Pre-Verification Report is PREDICTIONS ONLY, committed
   now, before any integrated run - no integrated result may ever touch a predicted cell; freezing
   it before the run is its entire value. Present BOTH and WAIT for my review.
6. Verification run - run the integrated task ONCE to test the committed prediction. If the result
   falsifies the prediction, diagnose the responsible model parameter and re-derive - do not
   empirically tweak the program.
   GATE C (after the verification run, before operation): produce the POST-VERIFICATION REPORT -
   predicted vs actual for every requirement, with any falsify -> diagnose -> re-derive recorded.
   Present it and WAIT for my review.
7. Operation - lock and run the operation as defined in the task. On completion, produce the FINAL
   ENGINEERING REPORT (per task_core close-out). In the SE report the per-run reconciliation also
   carries the PREDICTED gap/margin from the Pre-Verification Report alongside your onboard estimate
   and my measurement - so the table closes the full chain (predicted -> estimated -> measured) and
   states plainly whether the committed prediction held against ground truth.

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

YOUR RECORD (produce and keep - separate from this prompt; gated deliverables in CAPS)
Requirements specification (incl. TBD register) - requirement tree (Mermaid) - tailored SysML
models - CALIBRATION & VERIFICATION PLAN - CALIBRATION REPORT (TBD register closed) -
PRE-VERIFICATION REPORT (the frozen pre-run argument, predictions only) - POST-VERIFICATION REPORT
(predicted vs actual) - FINAL ENGINEERING REPORT. The Pre-Verification Report is the centerpiece -
frozen before the verification run.

Begin.
```