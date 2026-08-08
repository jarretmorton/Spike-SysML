# Process Retrospective — what guidance would have helped

**Scope:** the systems-engineering process document, not the rover. Each item below names a gap,
cites the evidence from this session, and proposes a rule that could be added.

---

## 0. The shape of the failures

Thirteen flash-and-runs: 8 characterization, 5 operation. Two runs were lost to genuine
falsifications that improved the design. **Four were lost to defects of mine, and three of those
four share one shape:**

| Defect | The check that existed | The failure it could not see |
|---|---|---|
| AR-004b, closing check | reading above threshold ⇒ fault | a *single* outlier among good samples |
| AR-005, fused estimator | reading vs odometry propagation | a *constant offset*, because the propagation was seeded from the reading being tested |
| VER-1 freeze guard (caught offline) | residual between reading and prediction | a *frozen* reading, which anchors its own prediction |

In each case I verified the property that was easy to compute rather than the property that could
actually fail. The process asks for cross-sourcing and gets it; it does not ask what each
cross-check is *capable of detecting*. That is the single largest gap.

---

## 1. Require a detection-capability matrix for every cross-check

**Gap.** The Calibration Plan template asks for a channel catalog and cross-source pairs. It asks
which channels observe a quantity, never which error modes a given pairing can discriminate.

**Evidence.** My cross-source table listed "forward range: primary C1, cross-source C2" and
"travel: odometry vs ranging". Both entries are true and neither would have predicted that the
fused estimator accepts 37 of 37 readings while the channel is 155 mm wrong.

**Proposed rule.** For each cross-check, fill a row against a fixed column set — *bias, scale,
drift, freeze, dropout, single outlier, common-mode* — marking detect / cannot-detect / partial.
Require that the union of checks covers every column for any quantity on the scored path, and
that blank cells are stated as accepted risks. A blank cell under "bias" for the estimator, and
under "single outlier" for the closing check, would have been visible on paper at Gate A.

---

## 2. Separate calibration *tier* from calibration *identifiability*

**Gap.** The source-of-truth hierarchy (T1 external / T2 multi-point / T3 single sample) grades
the **provenance** of a value. It says nothing about whether the model being fitted is
determined. I fitted a one-parameter offset model to **one** T1 anchor and the process rated the
result T1 — the highest tier available — with zero degrees of freedom and no residual.

**Evidence.** AR-003: predicted 91 mm, measured 102 mm. The offset was not constant, and one
anchor could never have revealed that. AR-005 repeated the error one level up: two anchors fitted
a two-parameter line, again with zero residual, and the line was invalid on the next run.

**Proposed rule.** Record tier and degrees of freedom as separate attributes. A model with N free
parameters requires **at least N+1 independent anchors**, with the surplus reserved as a residual
check that is reported and never absorbed into the fit. No parameter may be marked "bound" while
its model has zero residual degrees of freedom.

---

## 3. Require a stability-across-runs check before any parameter is treated as bound

**Gap.** Characterization is framed per-run. Nothing requires confirming that a bound value is
still bound in a *later, independent* run.

**Evidence.** Ranger A was clean **within** every run — smooth, monotonic, ±5 mm static spread —
and unstable **between** runs: offsets of +24, +13 and −155 mm against three ground-truth anchors,
and absolute readings that flipped between two distinct states on an unchanged setup, visible even
during the scored operation phase (runs 1–4 inverted, run 5 not). Every piece of characterization I
did was within-run, so nothing could have caught this until it caused a 175 mm miss.

**Proposed rule.** Every characterization run after the first must re-measure at least one
previously bound quantity and report the drift. Cheap — it is folded into a run that is happening
anyway — and it converts a whole class of latent cross-run instability into an early, visible
number.

---

## 4. Verify guards by fault injection, at design time

**Gap.** The process is detailed on verifying requirements and near-silent on verifying
*protective* logic. Interlocks are specified, then discovered to work or not work when they fire
for real.

**Evidence.** Of my guards: the odometry budget fired correctly and prevented contact twice; the
closing check fired spuriously and destroyed a run; the freeze detector was structurally incapable
of firing. I only found the third because I chose to replay the estimator against recorded
telemetry with an injected freeze — offline, free, and it found a real defect before hardware.
I did that because it occurred to me, not because anything required it.

**Proposed rule.** No guard ships without a **demonstrated trip and a demonstrated non-trip**,
executed offline against recorded telemetry with the fault injected. Both directions matter: a
guard that cannot fire is as bad as one that fires on noise.

---

## 5. Make the verification target the flight target, and pre-declare the tightening rule

**Gap.** Two rules interact badly. "The objective closes only on ground truth at the operating
point" and "the operating point must be the point that was verified" jointly imply the
verification run must be flown at the intended operating value — but that implication is never
stated. Separately, the process forbids post-hoc adjustment and offers **no legitimate mechanism
for using information the verification produces.**

**Evidence.** I set VER-3 conservatively at 30 mm because σ was inflated at n = 2. It confirmed,
and the three-anchor sample then gave sd = 2.02 mm, which would have justified a target near
8–10 mm. Honouring the freeze cost roughly **20 mm of objective** — about two-thirds of the final
gap. The freeze was the right call given what was written; the writing left no other move.

**Proposed rule.** State that the verification configuration *is* the flight configuration, so if
you are not confident enough to fly the target you are not ready to verify it. Then permit a
**tightening rule frozen before the run**: "if the residual over N anchors is below X, the target
may move to Y, and the new configuration inherits the verification." Pre-committed, so it is a
decision rather than a reaction to the answer.

---

## 6. Add VOID as a first-class anomaly disposition

**Gap.** Dispositions run surprising-but-possible / model-contradicting. There is no category for
*the test article never reached the test condition*.

**Evidence.** VER-1a crashed on an import; VER-1b aborted 660 mm out. Neither tested a single
number in the frozen prediction. I had to invent the distinction to avoid two bad outcomes:
reporting a void run as a passed verification, or re-deriving parameters against evidence that
does not exist.

**Proposed rule.** VOID = the test condition was not reached. A void run re-issues the plan
**unchanged**, records why the condition was not reached, and counts against the program budget.
Explicitly: a void run may not be cited as supporting evidence for anything.

---

## 7. Budget a defect reserve, and cap first-program complexity

**Gap.** The plan states expected program counts. Nothing governs what happens when they are
consumed by one's own bugs, and nothing constrains how much untested logic may ride on a single
flash.

**Evidence.** Planned 2 programs, spent 8. CAL-1 was a 380-line program whose untested discovery
sequence spun the rover 36° and wasted the entire run. A "first program does the minimum needed to
learn the port map and nothing else" rule would have cost one cheap program instead of one
expensive wasted one.

**Proposed rule.** Allocate an explicit defect reserve (say 30% of the program budget) and define
a trigger: when defect-caused runs exceed it, stop flashing and do a review pass. Cap the first
hardware program to a single objective with no dependent stages.

---

## 8. Probe the platform before the first real program

**Gap.** The process assumes the execution environment is characterized. It is not, and it is not
in the requirements either.

**Evidence.** Two environment facts cost real runs: `math` is absent from this Pybricks build
(discovered by crashing), and telemetry throughput is ~30 lines/s (discovered by having two dumps
truncated). Both were free to discover deliberately and expensive to discover accidentally.

**Proposed rule.** A platform capability probe precedes the first functional program: available
modules, achieved loop period, telemetry throughput, buffer limits. Treat the execution
environment as an uncalibrated subsystem, because it is one.

---

## 9. Give requirements an "assumption" field distinct from "rationale"

**Gap.** Rationale records *why a number was chosen*. It does not record *what physical claim the
number depends on*, so there is no link from a falsified assumption to the requirements that rest
on it.

**Evidence.** SYS-6's 5° heading limit came from a corner-lead analysis (90 mm half-width). Ground
truth contradicted that model — two runs at −3.3° and −11.6° yaw produced the same distance line
to within 2 mm — and I had to re-derive the requirement at Gate B. That was the correct move but
it was ad hoc; nothing had flagged the corner-lead model as an assumption requiring validation.

**Proposed rule.** Every derived requirement names the assumption its allocation depends on, and
every named assumption gets a validation activity in the Calibration Plan. When an assumption
falls, the affected requirements are then mechanically identifiable rather than discovered.

---

## 10. Enforce the per-run deliverable checklist

**Gap.** Per-run deliverables are listed but nothing checks completion.

**Evidence.** I did not produce the required chart for VER-2 — the single most consequential run
of the programme. I escalated on the anomaly and went straight to requesting ground truth. The run
is fully analysed in AR-005, but the artifact is missing, and I only noticed at the very end.

**Proposed rule.** A short closure checklist that must be completed before the next flash:
telemetry retrieved, chart produced, anomalies dispositioned, estimate recorded. It costs seconds
and only fails under pressure, which is exactly when it matters.

---

## What the process got right

Worth stating, because these are what kept the programme out of the wall:

- **Cross-sourcing with a conservative-channel-wins rule.** In VER-2 the odometry budget braked at
  an estimated 91 mm when the truth was 199 mm. Zero contacts in thirteen runs is attributable to
  this rule more than to anything else.
- **Freezing predictions before runs.** Every falsification in this programme is legible *because*
  a number was written down first. Without it, AR-003 and AR-005 would have been silent
  recalibrations, and the ranging architecture would have flown.
- **Costed measurements forcing sensitivity-driven spending.** Both architecture-killing
  discoveries came from operator measurements deliberately spent where the sensitivity table said
  the leverage was.
- **Reports static, plans versioned.** Retaining superseded plans made the falsify → diagnose →
  re-derive trail auditable rather than a narrative reconstruction.

---

## Priority

If only three were adopted: **§1 (detection-capability matrix)** — it addresses three of the four
self-inflicted failures. **§2 (degrees of freedom)** — it addresses both architecture collapses.
**§5 (verification target = flight target)** — it is the difference between a 30 mm result and a
10 mm one on an otherwise identical programme.
