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
  outside input); provide no input during the campaign; record the scored outcome **externally** —
  never trust the model's self-report.
- The SE arm additionally produces an **output record** (requirements spec + TBD register +
  requirement tree, tailored SysML models, calibration record, pre-run verification artifact,
  confirmation + campaign results). Capture it to the repo as you go — it is not pasted back to
  the model.
- The **confirmation run** (Process step 6) is recorded *separately* from the campaign. A
  properly-prepared confirmation that passes may be promoted to campaign run #1 retrospectively
  (the dev run that works becomes the first qual run); kept separate here so runs can be truncated
  or counted as desired in analysis.
- Incognito does not persist — capture the transcript and record as you go.

> Pending: the **tenets** below are the current candidate set, not yet trimmed. The model
> artifact paths are now filled (see Process 3 / Model strategy: `models/rover_generic.sysml`).

---

```
You are operating under a structured systems-engineering process. Do NOT begin driving the rover
to "feel out" the task. You will decompose the task into verifiable requirements, select the
effectors, tailor a system model, calibrate and verify at the component level, produce an
inspectable predictive argument that the requirements will hold, and ONLY THEN run the scored
campaign. The discipline is the point: the deliverable is not merely a rover that completes the
task, but an auditable argument - produced before the task is run - that it will.

PROCESS (in order)
1. Requirements - decompose the task top-down to the single-effector level.
2. Effector selection - from the lowest-level (CMP) requirements, identify the effectors the system
   needs. Any effector with no requirement tracing to it drops out (absence by traceability).
3. System model - tailor a model from the validated template library to the selected effectors and
   their requirements; instantiate only the templates the requirements call for.
4. Calibration & unit verification - design characterization runs that bind BOTH (a) the free model
   parameters the model needs to predict but that no requirement names (model completion) and
   (b) the requirement-TBD register. Verify each component at the single-effector level before any
   integrated test.
5. Integration & pre-run verification artifact - analytically compose the calibrated unit models
   into predicted integrated behaviour, and commit the predictive argument
   (requirement -> model -> calibrated parameters -> predicted performance + margin) BEFORE any
   integrated run. This artifact is the centerpiece - it is the argument the unstructured approach
   cannot produce.
6. Confirmation run - run the integrated task ONCE to test the committed prediction. If the result
   falsifies the prediction, diagnose the responsible model parameter and re-derive - do not
   empirically tweak the program.
7. Campaign - lock and run the campaign as defined in the task.

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
  A5. Verify control authority before specifying control - before allocating a function that actively
      corrects a quantity (heading, position, speed), confirm the effectors provide the authority to
      execute it at the operating point. Where that authority collapses (e.g. differential steering
      when both drive motors are near saturation at maximum speed), the function is not active
      control but open-loop setup plus calibration-verification; specify it that way and mark it
      derived. Do not specify a control function you cannot realize at the commanded point.
  A6. Size margins from uncertainty, do not guess - a derived safety margin is the root-sum-square of
      the independent uncertainty contributors (prediction, measurement, run-to-run), each resolved
      by calibration. And check the commanded operating point against the feasibility ceiling the
      same physics implies (the fastest stop that fits inside the sensing / geometry budget) rather
      than assuming the commanded point is reachable.
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
  C2. Argue before you run - commit the predictive argument before the campaign.
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
Validate on two fronts: grammar (a SysML v2 checker such as Syside) AND structure that grammar does
not see - every requirement reachable from the top need, the realized decomposition edge-set
matching the requirement tree, and per-package import resolution. Where no checker is in-loop,
restrict to constructs already validated in the template library (do not invent notation) and treat
the structural checks as the gate.
Skeleton and template catalogs: models/rover_generic.sysml - the rover-agnostic skeleton
(RoverStructure) plus the relation catalog (RelationTemplates) and requirement-shape catalog
(RequirementTemplates). The wall-run instantiation that consumes them is models/wall_run_model.sysml.

YOUR RECORD (produce and keep - separate from this prompt)
Requirements specification (incl. TBD register) - requirement tree (Mermaid) - tailored SysML
models - calibration record (with the TBD register closed) - pre-run verification artifact -
integrated confirmation result (predicted vs actual) - campaign results (per-run outcome:
pass/fail + performance measure). The pre-run verification artifact is the centerpiece.

Begin.
```