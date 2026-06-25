# Evaluation: structured vs. freestyle

> **Status:** experiment design, locked. The freestyle (control) arm has been
> piloted on hardware; the scored comparison is pending. This document is the
> reference for the comparison; the README's *Evaluation* section is a summary
> that points here. The runnable instruments live in [`../experiments/`](../experiments):
> `task_core.md` (the shared apparatus — the source of truth for the task, packet,
> and scoring restated below), `freestyle_arm_prompt.md`, and `se_arm_prompt.md`.

## The claim under test

The structured pipeline exists to make a claim — that systems-engineering rigor
buys you something before you let expensive equipment loose — and the claim is
worth *demonstrating*, not asserting. So the project is framed as a head-to-head
between a governed pipeline and an ungoverned one, on one shared hardware seam,
with the **same model and the same model configuration** on both sides so that
the only thing varying is the governance layer.

The durable differentiator is **verification**, not outcome. A capable model may
close the outcome gap by trial and error — it may even reach a tighter stop than
the structured arm — but only the structured arm can produce, *before the
verifying run*, an inspectable argument that the rover will satisfy the
requirement across its operating envelope. Outcome may converge; the predictive
argument does not come for free. The experiment measures the cost of each path
to a working result, and surfaces the one thing only the structured path
produces.

## The two arms

- **Freestyle (control).** A free-text request handed to the model with only the
`spike-prime-mcp` tools (`flash_program` → `run_program` → `get_telemetry`).
No requirements, no SysML model, no calibration discipline, no gates — the
model reasons, writes code, runs it, and iterates.
- **Structured (treatment).** The requirements → effector-selection → unit-model →
calibration → verification pipeline: derive and document requirements top-down to
the single-effector level, select the effectors those leaves call for, compose a
SysML v2 model from generic templates, calibrate both its free model parameters
and the requirement TBDs against the hardware with designed tests, commit a
pre-run verification argument, take one integrated confirmation run, then lock and
run the campaign.


**Both arms run through the same MCP seam.** This is settled (it was previously
an open routing choice). Routing both arms through `spike-prime-mcp` isolates the
governance layer as the only variable — "only governance varies." The structured
arm's calibration consumes the run's telemetry at end-of-run rather than as a
live stream (the MCP returns a complete trace, not a streaming feed); on-hub
buffering with a throttle loop supplies enough decay points for a fit. Live
plotting is preserved separately on the in-process diagnostic path
(`spiketelem.py`) for development use; it is not part of the scored comparison.

## Model and configuration

- **Primary model: Claude Opus 4.8**, on both arms. The capable-model regime is
deliberate: Opus will likely *succeed* freestyle on a LEGO-scale task, so the
separation between the arms is carried by verification, not outcome.
- **Second capability point: a lower-power model** (freestyle), to probe whether
the structured scaffolding earns its place more clearly as capability drops.
- **Configuration is a controlled variable.** Effort level and extended thinking
are held constant across both arms (and ideally across models), because
"only governance varies" includes the config. Thinking is left on — a weaker
model in particular does its discovery and physics reasoning there. The
initial Opus Max-effort + thinking run is treated as a **pilot** (it validated
the task and produced rich qualitative data); the scored runs use one
sustainable config (moderate effort, thinking on) on both arms.


## The task

**Drive at the drive motors' maximum speed straight at a wall and stop as close
to it as possible without touching it.** Hard constraints: full speed (no
slowing for margin) and no contact. Objective: minimize the final gap. (The
canonical statement, with the code primitives and telemetry wire format, is
[`../experiments/task_core.md`](../experiments/task_core.md).)

Why this task discriminates. With the effector inventory and the code primitives
shared between both arms, the *entire* difference between them is calibration
plus the verification spine — so the task has to be one where the value of a **calibrated physical parameter** is the difference between success and failure.
A guessed stopping distance must be the failure mode. At top speed the stopping
distance is largest (the quadratic braking term `v²/(2a)` dominates) and a
threshold tuned at any slower, safer speed is far short — a guaranteed contact.
The calibrated parameter (and the stop threshold / max-safe-speed
it feeds) is the whole game, which makes the structured arm's signature move —
calibrating the stopping distance directly at the operating point and committing,
before the run, an argument that the stop fits inside the budget — load-bearing
rather than ceremony. The freestyle arm can only tune the threshold empirically
and has no such argument.

## Hardware realism (kept deliberately)

The rig has real defects, and they are kept on purpose. A forward distance sensor
reads short and intermittently freezes; a smooth wall is a near-specular reflector,
so a few degrees of yaw blinds the ultrasonics through the stop zone; and over a
long uncycled session the hub's state drifts. None of this is engineered out.
Imperfect, drifting, occasionally-faulty instruments are a permanent feature of
physical systems — a comparison run on idealized hardware would be testing a
fiction, and the result would not transfer. Handling these realities is part of
what the structured arm is meant to demonstrate: validating an instrument against
ground truth before trusting it, characterizing the blind-out, accounting for
drift. The freestyle arm being *fooled* by them — trusting the faulty sensor and
reporting a confidently wrong gap (see the second pilot) — is a legitimate result,
not noise to scrub.

One distinction matters, because it draws the line between what we keep and what
we control. The sensor fault and the specular blind-out are *within-run* realities:
they bear on whether a solution works at all, so each arm should have to face them.
The hub's *cross-run* drift is different — it accumulates across the five campaign
runs and makes them non-comparable, so it corrupts the **repeatability metric** rather than testing the solution. We therefore reset it (power-cycle the hub
between runs) while keeping the genuine hardware faults. Cycling also makes the
sensor fault *consistent* run-to-run (a steady short read instead of a drifting
one), so the solution faces a real but repeatable defect and the five-run measure
isolates the solution's own consistency.

## Information diet: symmetric information, asymmetric mandate

The arms must differ in *something* or there is nothing to compare. The rule is **symmetric information, asymmetric mandate**: both arms *know* the same things;
only the structured arm is *required* to do the engineering. Tooling that is a *method affordance* of an approach (a code library, a model catalog) is part of
the approach being tested, not an unfair head start.

**Shared starting packet (both arms):**

- The effector inventory: a SPIKE Prime hub with a built-in IMU, two drive
motors, two forward-facing and one rear ultrasonic distance sensor, a downward
color sensor.
- Code primitives for each effector (port-parameterized; the device is *not* pre-bound to a port).
- A bare SysML v2 component model — the parts as blocks, no relations.
- Both must **discover the port mapping** themselves (told what exists, not
where it is plugged).
- Both are **told the metrics** they are scored on.


**Structured arm additionally has:**

- **Rules for requirements decomposition** — top-down **STK → SYS → FUN → CMP** to
the single-effector level, authored in **EARS** to **INCOSE GtWR / ISO-29148**
quality rules (the familiar functional / behavioral / interface / constraint
categories survive as requirement *types* on the leaves), with a **TBD register**
and a **visual requirement tree** as outputs. The method, not rover-specific facts.
- The SysML v2 specification plus generic (rover-agnostic) examples.
- A generic physics-relation template catalog (e.g. speed-from-rotation,
stopping-distance = reaction + braking) with parameters left free — engineering
knowledge, not facts about this rover.
- A mandate to **develop** the model: derive requirements, select effectors,
compose the SysML model on top of the component skeleton, calibrate (binding both
the model's free parameters and the requirement TBDs), commit the pre-run
verification argument, confirm with one integrated run, and report.


Both arms are handed the bare component model; only the structured arm is *required* to develop it. The freestyle arm will typically ignore it.

## Generation vs. selection (refined)

The structured arm **composes** the model — selects generic templates,
instantiates them, binds derived requirements and calibrated parameters, and
grammar-validates the result. It does not generate models from scratch (the
Iserte approach, declined). The refinement of that rule:
> **The structured arm may *develop* a relation whose error its calibration can
> independently expose; it must *select* (from a validated template) any relation
> the calibration cannot check.**

For the stop relation the license is real but conditional on the envelope.
Across a speed range, a structurally wrong relation — a linear-only stop that
drops the quadratic term — shows up as residual curvature in the sweep fit, so
the calibration is itself the error detector: a *stronger* demonstration than
handing over the equation, because the process derives the relation and the
calibration catches its own structural error and converges. The wall-run, though,
runs at a single operating point, where there is no range to extrapolate across
and so no form error for calibration to expose; it therefore *selects* the
validated stop template and calibrates its stopping distance directly at v_max.
The develop branch — and its cost, moving verification integrity off "safe by
construction" and onto "safe if the calibration design and the human gate catch
a structurally-wrong relation," a backstop that is partial — is the principle's
other half, demonstrable on a speed-spanning variant rather than exercised here.

**Graded assurance.** This is where the assurance line moves with consequence.
For the LEGO demonstration, develop-with-calibration-backstop is the right call.
For flight hardware it would not be — you would not let an analyst invent the
governing equation and trust the test to catch it; you would use validated,
reviewed relations and confirm margin inside a known-correct model. The LEGO arm
is deliberately more permissive than the real analog, and the report says so.
(This is the DO-178C DAL idea — graded assurance by consequence — shown in
motion.)

## Protocol: two phases

The run is structured so that *characterization cost* and *task reliability* are
separate, measurable line items.

1. **Characterization (counted, uncapped).** Run as many programs as needed to
understand the rover and develop the stopping approach. The **number of
programs** here is a score — fewer is better. Offline ground-truth
measurements are available *on request* (the model designs a test and asks
for a measured response — e.g. actual stopping distance from a given speed);
this is symmetric with how the structured arm's calibration binds a
parameter, and it is counted as **outside input** (a second score, minimized).
2. **Lock.** The model fixes its final program.
3. **Campaign (scored).** Run that **same, unchanged** program 5 times at maximum
speed. Contact and gap are recorded externally and **not fed back** during the
campaign — the task must stand on the rover's own perception. Locking before
the five makes the success rate a *repeatability* measure (the qualification
analogy: you do not change the design between qualification runs).


**Free actions** (uncounted, either phase): power-cycle the hub between every run
(clearing accumulated gyro/sensor/thermal drift so each run starts from a clean
hub state — heading and clock reset to zero, no state carried across runs; the
locked program is re-flashed unchanged in the campaign), reset to the start line,
reposition, and wake the hub. These are hardware operation, not help, and identical
overhead for both arms. **Outside input** (measurements, assistance the model
requests) is counted during characterization and unavailable during the campaign.
The campaign provides only operational power-cycles and resets between runs.

The same two-phase structure applies to the structured arm: its calibration and
unit-verification runs are the characterization-program count; after it commits
the verification artifact it takes **one integrated confirmation run** (also
counted as a characterization program) to test the committed prediction; its
locked program is the campaign, and the prediction is that it goes 5/5 with a
tight gap spread. A confirmation run that *passes* with the program locked
unchanged may be **promoted to campaign run #1** (truncating one of the five) —
kept separate by default so the runs can be counted either way in analysis. On a
confirmation run that *falsifies* the prediction, the structured arm diagnoses the
responsible model parameter and re-derives, rather than empirically tweaking the
program (the move the freestyle arm makes).

## Metrics

| Metric                | What it captures                                                            |
| --------------------- | --------------------------------------------------------------------------- |
| Characterization cost | # programs run before the campaign (the structured arm's confirmation run counts here) |
| Runs-to-first-success | # integrated runs to the first no-contact stop — for the structured arm, the confirmation run is that first integrated run, and the prediction is that it succeeds (= 1) |
| Outside-input count   | human measurements/assists requested during characterization                |
| Reliability           | # of the 5 campaign runs with no contact                                    |
| Performance           | the gap distribution across the 5 (closeness *and* consistency)             |
| Verification artifact | qualitative; present for the structured arm, absent or ad hoc for freestyle |


The first metrics are quantitative cost/outcome. The verification artifact is not
just another number — it is the deliverable only the structured arm produces, and
the report must make it *legible*: show the derived argument, not just assert that
rigor is virtuous. The structured arm is expected to post a higher
characterization and outside-input cost (calibration requires measured
responses) and a higher reliability with a tighter gap spread, plus the
artifact. That trade — more upfront cost, more reliability, plus provenance — is
the result. The thesis was never that the structured path is cheaper.

## Verification and the argument-before-it-ran

The structured arm's deliverable is an argument it would pass *before it ran*: a
predictive, inspectable claim that the requirement holds across the operating
envelope, produced before the verifying run and traceable to the tests that
anchored each parameter. Freestyle ends with *it worked* — posterior, empirical,
silent about any speed it did not try. The structured arm ends with *here is why
it will work, and the envelope within which it will* — the calibrated relation,
the measured parameters with residuals, and the test behind each number. It is
the difference between test-to-success (light it and see) and analysis-backed
qualification (anchor a model with component tests; the model gives margin before
the test confirms it).

## Pilot result — freestyle, Opus 4.8 (Max effort + thinking)

A pilot freestyle run validated the task and produced the freestyle-arm signature
in detail. Summary (full report in the run artifacts):

- It reached a no-contact stop, eventually closing to ~35–60 mm, but only after
~8 programs (port discovery, drive-sign calibration, sensor identification,
several max-speed attempts, one contact).
- The obvious sensor-based stop is **unsafe** for this task: a smooth wall is a
near-specular reflector, so a few degrees of yaw under a fast launch steers the
ultrasonic echo away and the forward sensors go blind exactly through the stop
zone. The robust answer it found was **wheel odometry**, independent of what
the sensors can see.
- One forward sensor was **faulty** (read short, froze) — caught only by checking
a reading against a physical ruler.
- Odometry needed **slip calibration** (effective wheel circumference varies with
the acceleration profile), biased conservatively to keep stops on the safe side.
- The close stop was reached by empirical tuning with roughly ±30 mm variance and
growing skew; the report's own words — it "cleared the wall by luck of timing,
not by control" — and the fact that it **could not tell when it had contacted** are the absence of a predictive argument, in plain view.


This is a pilot (Max effort + thinking, no fixed run budget, no two-phase
structure), not a scored result. The scored comparison uses the protocol above.

## A second pilot — freestyle, Opus 4.8 (High effort + thinking)

A second freestyle pilot ran the full two-phase protocol: 5 characterization
programs, 1 outside-input request, and **5/5 no-contact** in the campaign. It is
the sharpest single illustration of why outcome is not the metric that matters.

- The model's **performance self-assessment was confidently wrong**. It reported a
mean final gap of ~112 mm with "true gap ≤ this under conservative model," while
the externally measured gaps were 273, 283, 315, 322, 365 mm — more than double,
and the error model was *sign-reversed*: it stopped on a sensor that reads
*short*, so the true gap is *greater* than the reading, not less. It trusted a
faulty instrument it never validated against ground truth, and was precisely,
confidently wrong about how close it got.
- The three metrics it could *count* — program count, input count, no-contact rate
— were all correct. The one metric requiring it to know its own true state
(closeness) was the one it got wrong. This is the case for measuring performance
**externally**, never from the model's self-report.
- The campaign also exposed a **hub-drift confound**: across the five runs the true
gap climbed (273 → 365) while the sensor reading stayed flat (~110), reset by a
power cycle (252 mm on a cycled run). The protocol now power-cycles the hub
between every run; the systematic ~160 mm under-read is a separate faulty-sensor
issue (the sensor is kept deliberately — see *Hardware realism*), not the drift.


Both pilots are freestyle. Neither is a scored result; together they fix the
protocol (two phases, hub-cycling, external measurement) and preview the freestyle
arm's signature — a working result with no trustworthy account of how well it
worked.