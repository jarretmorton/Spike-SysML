# se_arm_prompt.md — structured (SE) arm  ·  method v2

Runnable instrument for the **structured arm** of the structured-vs-freestyle comparison
(see [`../docs/evaluation.md`](../docs/evaluation.md)). Handed to the model in a fresh,
memory-free context (incognito) with the `spike-prime-mcp` tools connected and nothing else.

**Assembly:** the delivered prompt is the `task_core.md` fenced block, **then** the fenced SE
block below, ending at `Begin.`. The model receives full text, never a link.

Run conditions:

- **Same model and configuration as the freestyle arm** (config is a controlled variable — thinking
  on, max effort). Only governance differs between the two arms.
- The hub is **power-cycled between every run** (as in `task_core.md`).
- Operator policy: provide ground-truth measurements *on request* during Phase 1 (counted as
  outside input); provide no input during operation; record the scored outcome **externally** —
  never trust the model's self-report.
- The SE arm additionally produces an **output record**: requirements spec (+ TBD register +
  requirement tree), tailored SysML model, **executable analysis model (Python)**, Calibration Plan,
  Calibration Report, Verification Plan, Verification Report, Final Report, and any Anomaly Reports.
  Capture it to the repo as you go.
- The **verification run** (Process step 6) is part of the **characterization phase**: it counts
  toward the program-count score, but is **not** one of the five scored operation runs.
- Incognito does not persist — capture the transcript and record as you go.

**Changes from v1 (for review; not delivered to the model):**
1. Executable Python analysis model added as a Gate-A deliverable, traced 1:1 to the SysML.
2. Sensitivity analysis (a required table) opens the Calibration Plan and justifies the run design.
3. Frozen verification prediction is now the executable model's output; computational-≠-mutable
   guardrail added.
4. Verification Report is the single complete requirement ledger; the **objective closes at Gate C**
   via operating-point ground-truth validation of the objective's predicted gap — the arm decides
   *when* in characterization to spend that measurement, distinct from the operation close-out measurements; no operation data needed
   to verify anything. Operation close-out (step 7) now spells out the order: freeze and present per-run
   onboard results, THEN request the measured distance for each of the five runs, THEN issue the Final
   Report.
5. Anomaly-disposition block added: judgment governs whether a *possible* anomaly is significant, but
   leverage is defined by the sensitivity analysis (section 0); *impossible* anomalies escalate
   unconditionally; the free Anomaly Report always ends in a recommendation.
6. Source-of-truth hierarchy strengthened from a ranking into an actionable escalation rule.
7. Unscored-vs-costed statement added (SE-side restatement of task_core's scoring).
8. Redundant statements consolidated (frozen prediction, cross-sourcing, source-of-truth,
   program-count) to one canonical location each. SysML notation notes kept in full.

---

```
You are operating under a structured systems-engineering process. Do NOT begin driving the rover to
"feel out" the task. You will decompose the task into verifiable requirements, select the effectors,
tailor a system model AND its executable realization, calibrate and verify at the component level,
produce an inspectable predictive argument that is then tested, and ONLY THEN run the scored
operation. The discipline is the point: the deliverable is not merely a rover that completes the
task, but an auditable argument - produced before the task is run - that the rover will complete it.

WHAT COSTS AND WHAT DOES NOT
Analysis, simulation, evaluation of your model, and document revision are UNLIMITED and UNSCORED - do
them freely and often. The scores in task_core count only when you TOUCH THE ROVER: a program
flash-and-run, or an operator measurement/observation. Whenever free analysis can answer a question,
prefer it to a hardware run or a measurement.

PROCESS (in order). Each phase ends at a GATE: produce the named deliverable(s) as downloadable
markdown artifacts (files I can save, not just chat replies), present them, and WAIT for my review
before the next phase - never proceed past a gate on your own.
Deliverables are PLANS or REPORTS, and the distinction governs how each may change. A PLAN is
forward-looking - structured reasoning about next steps under these tenets and your current best
knowledge of the system - and you REVISE it (re-issuing a new version, prior versions retained)
whenever a characterization run reveals something its current version did not anticipate. A REPORT is
backward-looking - a static record of what happened - and is not edited once written. The rhythm is
plan -> act -> report, re-planning as discovery warrants.
Phases: steps 4-6 are the characterization phase (Phase 1) - the calibration runs plus the
verification run and any re-runs, every one of which counts toward the program-count score; step 7 is
the operation phase (Phase 2), the five scored runs. The verification run tests the system and is
never one of the five scored runs. No requirement needs the scored operation runs to be verified:
operation is a scored demonstration and a repeatability sample, and the ENTIRE verification argument
closes at GATE C.
1. Requirements - decompose the task top-down to the single-effector level.
2. Effector selection - from the lowest-level (CMP) requirements, identify the effectors the system
   needs. Any effector with no requirement tracing to it drops out (absence by traceability).
3. System model + executable model - tailor a model from the validated template library to the
   selected effectors and their requirements; instantiate only the templates the requirements call
   for. Alongside it, produce the EXECUTABLE ANALYSIS MODEL (a plain-Python module, standard library)
   that realises the same model computationally: every parameter, relation, and requirement
   constraint in the SysML model maps 1:1 to a named Python variable/function, so the two are two
   views of one model - the SysML carries the formal satisfy/require argument, the Python carries the
   arithmetic. It must expose (a) PREDICT: compute the performance quantities (gap, overshoot,
   clearance, ...) from bound parameter values; (b) EVALUATE: return pass/fail for each requirement
   given those values (the computational satisfy/require roll-up); (c) SWEEP: vary parameters over
   stated ranges for the sensitivity analysis. Leave parameters free (uncalibrated, not zeroed) until
   calibration binds them.
   GATE A (after spec + SysML model + executable model, before any hardware): produce the CALIBRATION
   PLAN (a plan - revise and re-issue after any characterization run that necessitates a re-plan). It
   OPENS with the SENSITIVITY ANALYSIS (section 0): using the executable model, sweep each
   free/uncertain parameter over an explicitly stated assumed range (state your priors - the ranges
   are an input to my review) and report, as a REQUIRED TABLE, how much the objective and each
   hard-constraint margin move in response. Columns: parameter | assumed range | objective/margin
   sensitivity | current-knowledge tier | resulting priority. This table JUSTIFIES the rest of the
   plan: characterize the highest-leverage, least-known parameters first, and anchor them with the
   highest-trust source available (source-of-truth hierarchy, CHARACTERIZATION METHOD 2). A parameter
   the objective is highly sensitive to, that no onboard channel can pin down, is exactly where a
   costed operator measurement earns its price. Note: a sensitivity sweep ranks WHERE TO LOOK; it
   does NOT validate the model against reality - only the operating-point ground-truth anchor and the
   impossible-reading rule do that. After section 0: the calibration input list (model-completion
   parameters + the requirement-TBD register), the characterization-run design (per CHARACTERIZATION
   METHOD: channel catalog, source-of-truth hierarchy, test-like-you-fly run construction), any
   outside-input requests, and a VERIFICATION SUPPORT section - how the calibration activities support
   verification, in particular unit verification of the lowest-level (CMP) requirements, plus the
   STRUCTURE of the eventual verification argument (the satisfy/require roll-up with predictions left
   open). Present it and WAIT for my review.
4. Calibration & unit verification - design characterization runs that bind BOTH (a) the free model
   parameters the model needs to predict but that no requirement names (model completion) and (b) the
   requirement-TBD register. Verify each component at the single-effector level before any integrated
   test.
5. Integration & verification plan - analytically compose the calibrated unit models into predicted
   integrated behaviour, and commit the predictive argument (requirement -> model -> calibrated
   parameters -> predicted performance + margin) BEFORE any integrated run.
   GATE B (after calibration, before the verification run): produce the CALIBRATION REPORT (a report -
   static) - the TBD register closed, each bound value with its producing test and its evidence basis
   (samples / reference / source-of-truth tier; a value set at a higher tier is NOT silently re-fit to
   a single later sample) - plus the lowest-level (CMP) requirements unit-verified by those
   calibration runs. Also produce the VERIFICATION PLAN (a plan) - the predictive argument now
   numeric, PREDICTIONS ONLY. Its frozen prediction is the OUTPUT of the executable analysis model
   evaluated at the committed configuration and bound values, presented with the roll-up result (each
   requirement's predicted pass/fail) and the analysis that produced it. FREEZE it before the run -
   that is its entire value: no integrated result may ever edit the version that predicted it. The
   model is re-runnable, but this frozen output is NOT editable (computational is not mutable): if the
   verification run falsifies it, diagnose the responsible parameter, re-bind, re-run the model, and
   issue a NEW Verification Plan version - the prior stays frozen as the record of what you predicted.
   Present BOTH and WAIT for my review.
6. Verification run - run the integrated task to test the frozen prediction. If falsified, diagnose
   the responsible parameter and re-derive - do NOT empirically tweak the program - issue a new frozen
   Verification Plan version, and take another verification run against it. Every verification run,
   re-runs included, counts toward the program-count score.
   GATE C (after the verification run, before operation): produce the VERIFICATION REPORT (a report -
   static). This is the SINGLE place every requirement is closed. For each requirement (STK / SYS /
   FUN / CMP) give the verification METHOD (test / analysis / inspection), the EVIDENCE, and a
   VERDICT. Pull the CMP unit-verification results forward from the Calibration Report; add all
   remaining system-level verification here. No requirement may be left asserted-without-evidence; if
   any lacks a verdict, the report is incomplete and is reissued. The OBJECTIVE requirement - the
   highest-consequence scored quantity - is closed HERE, not deferred to operation, and only on
   evidence that its predicted final gap was validated against operator ground truth at the operating
   point (per the source-of-truth rule, CHARACTERIZATION METHOD 2). YOU decide when in characterization
   to spend that costed measurement. This validation is DISTINCT from the operation close-out
   measurements in step 7. The point is not where you take it, but that the objective is never closed
   on an unvalidated sensor - that is how a systematic bias ships. Record any falsify ->
   diagnose -> re-derive -> re-predict trail across Verification Plan versions. Present it and WAIT for
   my review.
7. Operation - lock and run the operation as defined in the task. CLOSE-OUT (per task_core), in this
   order: after the five runs, FIRST freeze and present your per-run results based on operation - your
   onboard estimate of the gap for each of the five runs - committed BEFORE you receive any
   measurement; THEN request from me the measured distance value for each of the five runs; ONLY THEN
   produce the FINAL REPORT (a report - static). Its per-run reconciliation carries the PREDICTED
   gap/margin from the frozen Verification Plan alongside your frozen onboard estimate and my measured
   value - closing the chain (predicted -> estimated -> measured) and stating plainly whether the
   committed prediction held against ground truth. This CONFIRMS the objective's scored performance
   across the five runs; it does not first-verify any requirement (that closed at GATE C).

REQUIREMENTS METHOD
The requirements specification is the source of truth for requirements; the SysML model is a formal
realisation of it, not a replacement - on any disagreement, the spec governs.
Write to INCOSE GtWR (4th ed.) quality rules over ISO/IEC/IEEE 29148:2018, authored in EARS grammar;
NASA SP-2016-6105 for decomposition and V&V framing.
- EARS patterns - tag each requirement: Ubiquitous ("The X shall..."), State-driven ("While <state>,
  the X shall..."), Event-driven ("When <trigger>, the X shall..."), Optional ("Where <feature>, the
  X shall..."), Unwanted ("The X shall not...").
- Levels: STK (stakeholder need) -> SYS (system black-box) -> FUN (function) -> CMP (single-effector
  leaf). Trace every child to its parent.
- Rules:
  1. One requirement, one verifiable claim - split compounds at the level below.
  2. Decompose until a requirement is verifiable by a test on a single effector, OR until it is
     irreducibly integrative - stop there.
  3. Separate hard constraints (shall, pass/fail) from objectives (should, graded); bridge them with a
     derived margin requirement.
  4. Flag every derived requirement (not literal in the task statement) with rationale.
  5. Rationale on every requirement.
  6. Deliberately allocate independent channels to the same quantity (cross-sourcing - see
     CHARACTERIZATION METHOD 1).
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
  A6. Size margins from uncertainty, do not guess - a derived safety margin is the root-sum-square of
      the independent uncertainty contributors (prediction, measurement, run-to-run), each resolved
      by calibration.
B - Characterization
  B1. Data is king - every characterization run logs every independent channel bearing on the
      quantity, not just the one under test (cross-sourcing is the fault-agnostic fault detector -
      see CHARACTERIZATION METHOD 1).
  B2. Trusted-reference-first - characterize the most directly-observable, least-coupled quantity
      first, then bootstrap the coupled or suspect channels off it.
  B3. Batch characterization; minimize programs - combine calibration with unit verification, test
      multiple components per program.
  B4. Human measurement is a deliberate, costed instrument - spend it where the sensitivity analysis
      says it matters most (CHARACTERIZATION METHOD 0, 2), and batch the maximum cross-checks around
      each request.
C - Verification sequencing
  C1. Verify components before integrating - unit verification gates the integrated test.
  C2. Argue before you run - commit the predictive argument before operation.
D - Epistemic hygiene
  D1. Know each channel's provenance before trusting it; watch for reporting artifacts.
  D2. Instruments are imperfect - characterize the imperfection, do not idealize it.
  D3. Control the confounds you cannot tolerate (cross-run drift is controlled out between runs); keep
      the within-run realities you should face.

MODEL STRATEGY
Author to the OMG SysML v2 specification with the standard library for quantities/units; the
formal-requirements and satisfaction/verification constructs follow the OMG beta-spec lessons
(Sensmetry Advent of SysML v2, Lessons 23-24). The SysML model realises the requirements
specification (the source of truth); it does not replace it.
Library + calibration + assembler: compose the system model from pre-validated, generic SysML v2
unit-model templates; do NOT generate model structure from scratch. Instantiate only the templates
the requirements call for. Leave parameters free until calibration binds them (uncalibrated, not
zeroed). Maintain a trace spine linking each CMP requirement -> SysML parameter -> Python variable
(executable model) -> calibration evidence -> result. The SysML model is the formal argument; the
executable Python model is its computation; they must agree, and a mismatch between the SysML roll-up
and the Python evaluation is a defect to fix before the gate.

The formal roll-up has exactly one shape - reproduce it, do not approximate it with a prose trace or
unbound operands. A task requirement specialises a template, adds a subject, and BINDS its operands
against that subject's attributes using the redefinition-with-binding form
`attribute :>> measured = subject.attr` (NOT `attribute redefines measured :>> subject.attr` - that
conflates the keyword and symbol forms and is invalid); the require constraint is inherited, so the
evaluable logic lives in one place. Decomposition is nested `requirement : Child` usages. The design
part claims the top need with `satisfy`, and evaluating that satisfy/require roll-up against the
calibrated values IS the pre-run verification artifact. All of this is inside the validated construct
set; leaving operands as comments or carrying the trace as documentation forfeits the artifact - and a
by-hand reachability/edge-set check then certifies a roll-up the model does not actually contain. The
shape, end to end:

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
Skeleton and template catalogs: rover_generic.sysml - the rover-agnostic skeleton (RoverStructure)
plus the relation catalog (RelationTemplates) and requirement-shape catalog (RequirementTemplates).

CHARACTERIZATION METHOD
The characterization-run design is committed at GATE A inside the Calibration Plan, before any flash -
it turns the B-group tenets into an inspectable plan the way REQUIREMENTS METHOD realises the spec.
Required parts:
0. Sensitivity analysis (the required table; see GATE A / Calibration Plan section 0). Ranks
   parameters by leverage on the objective and hard-constraint margins, and JUSTIFIES the run design
   and where costed data is spent - characterize and anchor the highest-leverage, least-known
   parameters first.
1. Channel catalog & cross-sourcing. For every quantity you must calibrate, enumerate ALL the
   independent onboard channels that observe it - derived from the rover inventory, not just the one
   channel that is most obvious - and trace each to the quantity it serves; a channel serving no
   needed quantity drops out (absence by traceability, as with effectors). Rank each quantity's
   channels by directness and confidence. Every characterization run then logs every catalogued
   channel bearing on the quantities that run touches, not only the one under test; disagreement
   between channels is the fault detector and is fault-agnostic - never assume which channel is wrong,
   let the disagreement reveal it. Where a channel's valid range is bounded, plan the hand-off to an
   independent channel that covers the gap rather than extrapolating the bounded one past its limit.
2. Source-of-truth hierarchy. State the trust order explicitly and up front: external ground truth
   (operator measurement) > an anchored or multi-point onboard calibration > a single onboard sample.
   A lower tier NEVER silently overwrites a value a higher tier has set; a later sample disagreeing
   with a higher-confidence value is a discrepancy to diagnose (low draw? range-dependence? glitch?),
   not grounds to re-fit the constant. Carry each calibrated value with its evidence basis - how many
   samples, against what reference, at what tier. RULE: a sensor value that drives a scored quantity -
   the objective above all - is a HYPOTHESIS until confirmed against an independent higher-tier source
   AT THE OPERATING POINT. On disagreement your judgment finds significant, or on any physically
   impossible reading, ESCALATE to better data (the higher-tier source, or an added independent
   channel) rather than arbitrating between suspect channels or explaining the anomaly away. Where the
   scarce operator measurement is spent is decided by the sensitivity ranking (part 0): front-load the
   highest-leverage, least-known parameter.
3. Test-like-you-fly run construction. Characterize through the architecture you will operate on: the
   characterization program is a strict SUPERSET of the operation program - identical control loop,
   trigger, and buffer skeleton - with all additional characterization logging deferred OFF the hot
   path (write to a pre-allocated buffer, dump after the motors stop), never woven into it. That keeps
   maximum data intake and operational timing fidelity in the same run, so what you calibrate
   transfers to operation with no re-anchor. Within that constraint, combine the independent
   measurements a single run can carry and capture whatever per-channel data later steps need the
   first time, so no quantity forces a dedicated repeat run.
Output: the sensitivity table, the channel catalog (quantity -> channels -> confidence rank ->
binding run), the source-of-truth hierarchy, and the per-run design - all inside the Calibration Plan
at GATE A.

ANOMALY DISPOSITION (applies once hardware testing has started, INCLUDING during operation)
Any observation that conflicts with the model is dispositioned - not ignored, not automatically
chased. Two branches:
- Surprising but physically POSSIBLE (e.g. an overshoot larger than expected, still within physical
  bounds): use the sensitivity ranking as a filter. Chase it only if it bears on a parameter your
  sensitivity analysis (section 0) ranked high-leverage; whether a given disagreement is significant
  enough to weigh at all is your judgment. Otherwise log it and proceed. This keeps
  you from burning runs or measurements where it does not matter.
- Model-contradicting / physically IMPOSSIBLE (e.g. a rest reading farther than the trigger reading;
  any value outside a physical bound): escalate UNCONDITIONALLY, regardless of the sensitivity
  ranking. An impossible reading is proof a load-bearing assumption is false - asking the model
  whether it is worth chasing is asking the wrong model to adjudicate its own falsification. Put a
  physical-plausibility bound on every logged channel so these surface automatically.
When you disposition an anomaly, produce an ANOMALY REPORT (a report; free analysis; may be issued at
any point once testing has started): state the anomaly, classify the branch above using the executable
model, and END WITH A RECOMMENDATION - ignore, retest, or escalate to a higher-tier data source - plus,
when a chase is recommended, a proposed test/measurement plan for my review. The report is free; the
test or measurement it proposes is costed only if I approve it. During operation a recommendation may
be HALT (stop the scored sequence); it may NEVER be modify-and-continue (that breaks the
unchanged-five-runs rule).

YOUR RECORD (produce and keep - separate from this prompt; gated deliverables in CAPS, each tagged
plan or report)
Requirements specification (incl. TBD register) - requirement tree (Mermaid) - tailored SysML model -
EXECUTABLE ANALYSIS MODEL (Python) - CALIBRATION PLAN (plan; opens with the sensitivity table) -
CALIBRATION REPORT (report; TBD register closed + CMP unit verification) - VERIFICATION PLAN (plan;
the frozen model-output prediction, predictions only, frozen per GATE B) - VERIFICATION REPORT
(report; every requirement closed with method/evidence/verdict, objective validated at the operating
point) - FINAL REPORT (report) - ANOMALY REPORT(s) (report; as-needed). The VERIFICATION PLAN is the
centerpiece - its prediction frozen before the verification run, revised only by re-derivation into a
new version before a re-run, never edited.

Begin.
```