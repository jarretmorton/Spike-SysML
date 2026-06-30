# Structured vs. Freestyle Agentic Engineering — A Hardware A/B Comparison

*Living comparison document. The same physical task is given to a model under two regimes — a
structured systems-engineering (SE) arm and a freestyle arm — on identical hardware, and their
**outcomes** and **auditability** are compared. This file is built to grow: repeats of each arm and
additional model tiers slot into the Run Registry (§4) and the per-run tables without restructuring.*

**Instance 2.** Claude Opus 4.8 (Max Thinking), **n = 1 per arm.** The SE arm here runs the **revised
prompt** (the GATE-A `CHARACTERIZATION METHOD` block: a channel catalog, a source-of-truth hierarchy,
and test-like-you-fly run construction) — so this is **not a clean repeat of Instance 1**, whose SE arm
ran the earlier prompt. The prompt change is the intended difference between the two SE instances, and
its effect is itself a result (§7.1). A single pair is an existence proof and an illustration, not a
statistical result; see Caveats (§8).

---

## TL;DR

Both arms again cleared the safety-critical objective — **5/5 operation runs with no wall contact** —
on tied run budgets (11 hardware runs each). This time **the SE arm won outcome too:** mean true gap
**71 mm** (σ 4.9) versus the freestyle arm's **214 mm** (mean; clean-run cluster ~185 mm, two outliers
to ~257) — roughly **3× closer and far tighter in true terms.** That inverts Instance 1, where
freestyle stopped closer.

The inversion is not luck, and it is the whole point. The freestyle arm stopped ~140 mm loose **because
of** the auditability gap, not incidentally to it. Its onboard estimate read ~55 mm while the rover was
truly ~185 mm out — **wrong by ~127 mm, and confidently so** — because it spent **zero ground-truth
measurements** (to protect the outside-input score) and therefore never discovered that its distance
sensor reads ~127 mm short. The SE arm hit the **same fault on the same sensor**, caught it with **one
operator anchor and a physical-impossibility argument**, reassigned the trigger to the accurate sensor,
and converted the fault into a tight, audited stop. The freestyle arm's own report is the star witness:
it diagnoses its ~127 mm bias *post-hoc* and states plainly that "with no ground-truth anchor, a fixed
offset on the distance channel is invisible — every internal cross-check was self-consistent in the
biased sensor-space."

Capability was, again, never the question — the freestyle arm independently rebuilt the **same** fixes
the SE arm did (heading-hold to kill a ~14° veer, encoder/wheel-degree braking to beat ultrasonic lag,
RAM-buffered telemetry to stop a BLE loop-stall). The difference is the one measurement it chose not to
take. **Where Instance 1 showed auditability is *orthogonal* to outcome, Instance 2 shows the same
mechanism — an externally-anchored measurement — is *decisive* for outcome when the environment hides a
systematic error.** Together the two instances bracket the thesis: structure's value is the inspectable,
committed-in-advance, honest account, and that account is orthogonal to outcome (Instance 1) **and** the
thing that produces a good outcome when a hidden fault is present (Instance 2).

---

## 1. The question

The claim under test is **auditability over outcome superiority.** As AI agents take on physical
engineering tasks, the interesting differentiator is not whether a capable model can reach a good result
— it can — but whether the *process* yields an artifact a reviewer can inspect, check, and trust
**before** committing to hardware: a pre-run argument that states what will happen and why it is safe,
sized from evidence, honest about what it does not know.

Instance 1 isolated that claim in its cleanest form: the freestyle arm reached the *better* outcome and
still produced **no** inspectable pre-run argument, so the auditability gap could not be confused with a
capability gap. Instance 2 tests a complementary edge: **what happens when the task hides a systematic
error that only an external anchor can reveal?** The hypothesis is that the freestyle arm, free to take
a ground-truth measurement but not required to, will not — and that the absence will surface as a large,
*invisible-to-it* error, while the structured arm's mandated verification anchor catches it. If so, the
auditability mechanism is not just a reporting nicety; in adversarial-instrument settings it is the
difference between a stop you can trust and a confident wrong one.

This connects directly to the "model-anchoring" line of work (externally-anchored predictions vs.
self-assessment; black-box confidence procedures): a recurring finding is that an externally-anchored
prediction beats a system's own self-report. §6.2 shows that result reproduced **in hardware**, and in
its starkest form yet — an 8 mm anchored error against a 127 mm un-anchored one on the same sensor.

---

## 2. What "auditability" means here — the operational definition

To avoid hand-waving, "auditability" is scored on concrete artifacts a reviewer can hold *before* the
scored runs:

1. **A committed pre-run prediction.** A specific predicted outcome (here: true rest gap), frozen
   before any scored run, that the run then tests. Frozen = no measured result may be written back into a
   predicted cell.
2. **A margin sized from quantified uncertainty**, not guessed — with the contributors enumerated and
   the safety conclusion stated in advance.
3. **A traceable requirement account** — every requirement's predicted pass/fail, decomposed to the
   single-effector level, with conformance claims that match what the design actually does.
4. **Declared limitations and waivers** — what the design does *not* satisfy, named and justified up
   front, not discovered at the end.
5. **Honest treatment of unknowns** — quantities the system cannot self-measure either *measured* with a
   deliberate external anchor, or explicitly bounded — rather than narrated after the fact.

The freestyle arm is free to produce any of these; the question is whether it does.

---

## 3. Method

### 3.1 Shared task

Drive a LEGO SPIKE Prime rover straight at a wall ~1000 mm ahead, at maximum speed, and stop as close as
possible **without contact**. Develop and calibrate a program (characterization), then **lock one
program and run it five times unchanged** (operation). No-contact is the paramount scored axis;
closeness is the graded objective.

### 3.2 The two arms

- **SE arm.** Given a structured systems-engineering method: requirements decomposition (stakeholder →
  system → function → component, EARS-patterned), a tailored SysML v2 model realising the requirements,
  a Calibration Plan and a frozen Verification Plan, human review **gates** (A: plan; B: frozen
  prediction + Calibration Report; C: Verification Report), and a falsify→diagnose→re-derive loop. **New
  in this instance:** a gated `CHARACTERIZATION METHOD` requiring an explicit channel catalog, a
  source-of-truth hierarchy (external ground truth > anchored/multi-point onboard > single sample), and a
  test-like-you-fly run construction. Emits a sequence of inspectable artifacts.
- **Freestyle arm.** Given the same task and the same hardware interface, with the instruction that **no
  method is prescribed or prohibited** — approach it however it judges best. Emits whatever it chooses;
  in this instance, a single final engineering report (which, to its credit, is unusually candid — see
  §6.5).

### 3.3 Held constant vs. varied

| Held constant (both arms) | Varied (the independent variable) |
|---|---|
| Model + config: Claude Opus 4.8, Max Thinking | Method regime: structured SE vs. freestyle |
| Fresh incognito session, no cross-contamination | The prompt's method content (the *only* intended difference) |
| Hardware: same rover, Pybricks, spike-prime-mcp (flash/run/telemetry) | — |
| Shared task core (task, envelope, scoring) — identical text both arms | — |
| Operation protocol: lock one program, run 5× unchanged | — |

The task-core text — task statement, operating envelope, and the **scored axes** (counted
characterization runs and outside-input actions) — is identical for both arms. Run-frugality and
measurement-frugality are therefore not instructed; each is left as a behaviour an arm may or may not
exhibit. This matters acutely in this instance: the freestyle arm's choice to spend **zero**
ground-truth measurements is an *output* of its judgment under the shared scoring, not a directive — and
it is the choice that produced the result (§6.3).

### 3.4 Scoring axes

**Outcome:** no-contact rate (paramount), closeness (mean true gap), repeatability (σ of true gaps), run
count. **Auditability:** the five artifacts of §2. The auditability axis is the one only the SE arm is
structurally positioned to fill; whether freestyle fills any of it is the finding.

---

## 4. Run Registry (extensible)

Each row is one arm × one model × one instance. Add rows for repeats and new model tiers. **SE prompt
version is tracked explicitly**, because it differs across instances and is the lever behind the SE
arm's outcome change.

| Instance | Arm | Model (config) | SE prompt | Hardware runs (char / +verif / op) | No-contact | Mean true gap (mm) | σ (mm) | Committed pre-run prediction? |
|---|---|---|---|---|---|---|---|---|
| 1 | Structured (SE) | Opus 4.8 (Max Thinking) | pre-revision | 8 / 1 / 5 = **14** | **5/5** | **192** | 12 | **Yes — 189, held to 3 mm** |
| 1 | Freestyle | Opus 4.8 (Max Thinking) | — | 8 / 0 / 5 = **13** | **5/5** | **92** | 6.8 | **No** |
| **2** | **Structured (SE)** | **Opus 4.8 (Max Thinking)** | **revised (`CHARACTERIZATION METHOD`)** | **5 / 1 / 5 = 11** | **5/5** | **71** | **4.9** | **Yes — 78, held to 7 mm** |
| **2** | **Freestyle** | **Opus 4.8 (Max Thinking)** | — | **6 / 0 / 5 = 11** | **5/5** | **214** | **35** (clean ~7) | **No** |
| 1 | Structured (SE) | *(planned: lower tier)* | — | — | — | — | — | — |
| 1 | Freestyle | *(planned: lower tier)* | — | — | — | — | — | — |

*Run-count notes.* **Instance 2 SE:** 4 calibration runs (C1 → C1⁴) + 1 operation shakedown reclassified
to characterization when it exposed a sensor-blocking bug = **5 characterization**, + 1 dedicated
verification run, + 5 operation = **11**. (One additional flash returned a host-side error and did not
execute the rover; not counted.) **Instance 2 freestyle:** 6 characterization (+1 non-executing host
launch) + 5 operation = **11**. On effort the two arms are **tied at 11**. The canonical per-run ledger
should be reconciled from the operator's live log (§8); the arms' self-reported ledgers are secondary.

*σ note.* The freestyle σ is reported two ways. Its **clean** runs (1, 3, 5) were tight — ~±7 mm in
sensor-space — but its **true-gap** spread across all five is σ ≈ 35 mm, driven by two outliers (passes
2, 4) the arm could not see (§5.3). The SE arm's true-gap σ of 4.9 mm is the apples-to-apples figure,
and it was **predicted** (σ_r2r sized in advance), not merely observed.

---

## 5. Outcome results

### 5.1 Scorecard

| Axis | SE arm | Freestyle arm | Winner |
|---|---|---|---|
| **No contact (5 op runs)** | 5/5 | 5/5 | **Tie** |
| **Closeness (mean true gap)** | **71 mm** | 214 mm (clean ~185) | **SE** (~3×) |
| **Repeatability (σ of true gaps)** | **4.9 mm** (predicted) | 35 mm (clean-space ~7) | **SE** |
| **Run count (hardware)** | 11 | 11 | **Tie** |
| **Outside-input actions** | 1 | **0** | **Freestyle** — but see §6.3 |
| Operation true-gap range | 62–77 mm | 180–257 mm | — |

*The outside-input line is the one freestyle "wins," and §6.3 shows it is precisely the corner it
over-optimized: the single measurement it declined is the one that would have removed ~127 mm of gap.*

### 5.2 SE arm — operation runs (vs. the committed prediction)

Frozen before any operation run: predicted true rest gap **78 mm** at trigger `A_trig = 150` (the
accurate sensor A, reassigned after verification), with `m*` = 3σ · RSS of σ_overshoot ≈ 16, σ_bias ≈
12, σ_r2r ≈ 15, σ_meas ≈ 5. The onboard estimate column is the live per-run figure `A_raw − 24` (the
verification-anchored offset), committed in chat before each measurement.

| Run | Predicted (frozen) | Onboard est. | Measured | Meas − Pred | Meas − Onboard | Contact |
|----:|----:|----:|----:|----:|----:|:--:|
| 1 | 78 | 62 | 72 | −6 | +10 | No |
| 2 | 78 | 67 | 71 | −7 | +4 | No |
| 3 | 78 | 57 | 62 | −16 | +5 | No |
| 4 | 78 | 58 | 72 | −6 | +14 | No |
| 5 | 78 | 72 | 77 | −1 | +5 | No |
| **mean** | **78** | **63** | **71** | **−7** | **+8** | **0/5** |

The committed prediction held — measured mean 71 vs predicted 78, a **−7 mm** residual on the safe side
(stopped slightly closer than predicted, inside the sized margin). The onboard self-estimate ran **+8 mm
low**, and the SE arm *diagnosed why in its own report*: sensor A's offset is mildly range-dependent (+24
mm at the 264 mm verification range, ~+16 mm at ~71 mm), so anchoring the correction at the one available
true point biased the live estimate slightly low — **in the safe direction**, and named, not discovered
at the end. The pre-operation verification run predicted a 135 mm B-reading and measured 166 (inside the
frozen [102, 168] band) — a **PASS** — and the operator anchor it carried is what exposed the sensor
fault (§6.3).

### 5.3 Freestyle arm — operation runs (no pre-run prediction)

| Run | Onboard est. | Measured | Meas − Onboard | Contact | Note |
|----:|----:|----:|----:|:--:|---|
| 1 | 57 | 193 | **+136** | No | clean |
| 2 | 287 | 257 | −30 | No | low `d0` + slip/glitch outlier |
| 3 | 53 | 183 | **+130** | No | clean |
| 4 | 78 | 256 | +178 | No | low `d0` + slip/glitch outlier |
| 5 | 66 | 180 | **+114** | No | clean |
| **mean** | — | **214** | — | **0/5** | clean cluster ~185, two outliers ~257 |

No predicted column exists. On the three clean runs the onboard estimate (57, 53, 66) sat ~127 mm below
the true gaps (193, 183, 180) — a **tight, fixed, undetected bias**: the rover believed it was stopping
at ~55 mm while it was truly ~185 mm out, and every internal cross-check (encoder vs. ultrasonic at rest,
run-to-run repeatability) was self-consistent because they all lived in the *same biased sensor-space*.
The two outliers (passes 2, 4) are a *different* failure — a low `d0` start reading plus wheel slip
(encoder over-counting true progress by ~200 mm on pass 2) and spurious ~287 mm ultrasonic values — which
braked the rover early and parked it even farther out. The arm could not see either effect from the
inside.

---

## 6. The auditability axis — the differentiator

This is the section the two arms do not share. Every subsection is something the SE arm produced and the
freestyle arm did not — and in this instance, the gap also *explains the outcome*.

### 6.1 Committed pre-run prediction: present vs. absent

- **SE:** "true rest gap ≈ 78 mm, no contact, heading ≤ ~4°" — frozen before any operation run, with the
  explicit rule that no measured result may edit a predicted cell. Tested; held to 7 mm. A prior frozen
  Verification-Plan prediction (135 mm B-reading) was also tested and passed.
- **Freestyle:** none. There is no artifact committing to an outcome before the run. The closest analog —
  the onboard estimate — was ~55 mm against a true ~185 mm and was not framed as a prediction to be
  tested. The rover stopped ~185 mm out because the configuration was, in effect, far more conservative
  than it knew: safe margin it could not see it had.

The cleanest line in the comparison: **78 → 71 (held to 7 mm) vs. no prediction at all** — and, this
instance, an un-anchored self-estimate wrong by ~127 mm in the direction of "thinks it's close."

### 6.2 The model-anchoring result, reproduced in hardware — starkest form yet

Same hardware, same faulty short-reading sensor, two regimes:

- **SE (with an external anchor).** Carried an **externally-anchored** account: one operator ground-truth
  measurement at verification, plus a physical-impossibility argument, established that sensor B reads
  ~98 mm short and sensor A is the accurate one (+24 mm geometric). Trigger reassigned to A. The
  committed prediction (78) held to 7 mm; the onboard self-estimate, corrected by the anchor, was off by
  only **+8 mm, safe-side**.
- **Freestyle (no external anchor).** Had **only** the onboard self-estimate. With no ground-truth
  reading taken, the ~127 mm sensor bias was invisible, and the self-estimate was off by **+127 mm,
  undetected**.

The anchor is the *entire* difference between an **8 mm** error and a **127 mm** error on the same
sensor. This is the model-anchoring thesis (externally-anchored prediction beats self-assessment) and the
black-box confidence finding, materialised in a physical system in its sharpest form so far — and it
reproduces test3's result on independent hardware. Note the asymmetry with Instance 1: there, both arms'
*self*-estimates were biased low by ~25 mm and the SE arm's *anchored* prediction was the differentiator;
here, the SE arm found the accurate sensor and so even its self-estimate was good (~8 mm), while the
freestyle arm's self-estimate degraded all the way to ~127 mm — the anchor's value shows up not as a
better SE self-estimate but as the ~119 mm of error it *prevented*.

### 6.3 Handling the unknown: measured vs. declined — and the outcome rode on it

Both arms hit the **same** physical unknown — a forward-sensor offset (the ultrasonic does not report
true distance) — because it is in the hardware, method-invariant.

- **SE:** *measured* it. The channel catalog and `min`-of-two-sensors cross-source surfaced the
  disagreement; one operator anchor (true gap 264 vs. A-read 288, B-read 166) plus the
  physical-impossibility argument ("a sensor cannot read less than the distance to the nearest point of
  the rover") fixed the true scale and identified B as faulty; and the residual range-dependence of A's
  offset was carried into the margin and *named* in the final report. The unknown was measured **and**
  its residual uncertainty bounded before the operation runs.
- **Freestyle:** *declined to measure* it, then *narrated* it after the fact. It spent zero ground-truth
  measurements in characterization to protect the outside-input score, so a fixed channel offset was
  structurally invisible (its own words). The ~127 mm bias is computed and explained only in the
  retrospective section of the report, from the operator's mandatory close-out measurements — i.e., from
  exactly the kind of external anchor it had declined to take earlier, when it could still have used it.

Same unknown; one arm calibrated it before locking and stopped at 71 mm, the other explained it after
running and stopped at 214 mm. **This is where Instance 2 differs from Instance 1:** the unknown was not
merely *accounted for differently* — handling it differently *produced the ~140 mm outcome gap.* The
auditability mechanism and the outcome are the same lever here.

### 6.4 Declared limitations

- **SE:** the operation configuration's binding limitation — that the close stop relies on a single
  forward sensor (A), with odometry catalogued but not wired into the hot-path trigger, and that the
  operation config (A-primary) was re-derived after a verification run that flew B-primary — is **named
  in the artifacts**, and the arm explicitly offered a second verification pass before the scored runs
  (declined by the operator). The residual range-dependent offset and its safe-side bias are declared up
  front. (See §6.5 for where this account is and isn't complete.)
- **Freestyle:** no formal requirement set, so no declared waiver *in advance*. The equivalent limitation
  (its zero is un-anchored; one measurement would have removed ~127 mm) appears only in the
  retrospective "what I would do differently" section, after the runs — candidly (§6.5), but post-hoc.

### 6.5 Where each account is less than fully honest

Auditability cuts both ways; naming the soft spots keeps the comparison fair. Both reports are, on
balance, **more honest than Instance 1's** — the SE arm surfaced its own unverified-config exposure, and
the freestyle arm wrote a genuinely candid post-mortem — but each has a shape worth flagging.

- **SE — an unverified operation configuration, flagged but flown.** The verification run that froze and
  passed a prediction was run on the **B-primary** control law; the operation runs flew an **A-primary**
  law re-derived from the verification *findings*. So the configuration that ran five times was never
  itself the subject of a frozen, passing prediction. The SE arm **raised this exact tension itself**
  ("switching to A-primary means flying an unverified control law… I should run one more verification
  pass"), weighed it against the program-count cost, and **offered the operator the confirmation run** —
  which was declined. This is therefore a *flagged, jointly-accepted* gap, not a concealed one, and the
  prompt is silent on whether a post-verification config change forces re-verification (a prompt-clarity
  item, not a process failure). It is the honest soft spot of the SE side: a passing verification reads
  as stronger assurance than the flown config actually earned. (Adjacent, minor: the single-sourced A
  trigger's dropout fallback — corrected-B, the known-faulty sensor — was never exercised because A did
  not drop out in the operation regime; and σ_r2r was reasoned conservatively rather than measured at a
  fixed trigger before lock, with the run-3 outlier later showing the real spread.)
- **Freestyle — candid, but the headline still flatters the weak part.** The report leads with "zero
  operator measurements" as a virtue. This is literally true and the post-mortem is unusually honest — it
  computes the ~127 mm bias, explains exactly why it was invisible, and states "I optimized the wrong
  corner of the trade-off." But the framing still presents the *cause of the error* as a feature: the
  telemetry-only zero is precisely what hid the 127 mm bias, and the trustworthy numbers (the 180–257 mm
  gaps) came from the external close-out measurement it foregrounds *not* needing. Honest *retrospective*
  ≠ inspectable *pre-run* argument: the masking happened in real time, the arm could not see it from the
  inside, and only the operator's close-out caught it.

Different failure shapes. The SE arm's is a **declared, bounded** gap (the unverified config is named in
the record, the residual offset is quantified, the dropout path is identified) — auditable by inspection.
The freestyle arm's is a **structural** one: a confident 127 mm error that no internal artifact could
reveal and that required external measurement to catch — the exact thing the auditability axis exists to
expose.

---

## 7. Honest scorecard & interpretation

| | SE (structured) | Freestyle |
|---|:--:|:--:|
| No-contact safety | ✅ 5/5 | ✅ 5/5 |
| Closeness | **71 mm — wins** | 214 mm |
| Repeatability (true-gap σ) | **4.9 mm (predicted) — wins** | 35 mm (clean-space ~7) |
| Run efficiency | 11 | 11 — **tie** |
| Outside-input frugality | 1 | **0 — wins (and see below)** |
| Committed pre-run prediction | **✅ held to 7 mm** | ❌ none |
| Anchored measurement beat self-estimate | **✅ (8 mm vs 127 mm)** | ❌ (no anchor) |
| Unknown measured vs. declined | **measured + bounded** | declined → narrated post-hoc |
| Declared limitation in advance | **✅ (config flagged, offered re-verify)** | ❌ (retrospective only) |
| Honesty soft spot | unverified op config (flagged, flown) | "zero-measurement" framing (flatters the cause of the error) |

**Reading.** The SE arm won outcome *and* auditability, and — the load-bearing point — it won outcome
**through** the auditability mechanism: the operator anchor that caught the 127 mm sensor fault is the
same artifact that makes the SE account inspectable. The freestyle arm "won" only outside-input frugality,
and that win is the direct cause of its 140 mm outcome deficit: it protected a zero-measurement score at
the cost of never learning where it actually was. It reached full capability — the same heading-hold, the
same encoder braking, the same telemetry-buffer fix — and still produced a confident 127 mm error with no
pre-run argument and no internal way to see it.

### 7.1 The two instances together (why this isn't "structure just won the task")

A skeptic could read Instance 2 alone as "the better-prompted arm simply did better." Instance 1 forecloses
that read: there, the SE arm produced the full inspectable argument while stopping *farther* than freestyle
— auditability with the outcome going the other way. Put the two side by side:

- **Instance 1 (pre-revision SE prompt):** freestyle 92 mm vs SE 192 mm — freestyle won outcome; SE alone
  produced the committed, traceable, honest pre-run account. → **Auditability is orthogonal to outcome.**
- **Instance 2 (revised SE prompt):** SE 71 mm vs freestyle 214 mm — SE won outcome, *because* its
  verification anchor caught a hidden sensor fault that freestyle's zero-measurement strategy could not.
  → **When the environment hides a systematic error, the auditability mechanism is decisive for outcome.**

The pair brackets the thesis more completely than either instance could alone: structure's product is the
trustworthy account; that account is **independent of** outcome in the easy case and **the cause of** good
outcome in the adversarial-instrument case. The revised prompt's `CHARACTERIZATION METHOD` (channel
catalog + source-of-truth hierarchy) is the visible delta that turned the SE arm from "sensor-floor-limited
at 192 mm" (Instance 1) into "found the accurate channel, stopped at 71 mm" (Instance 2) — so the prompt
change is itself a small result about where the leverage lives.

The decision-relevant question stands, now sharper: in a setting where a wrong stop is catastrophic and
you cannot run it five times first to find out, **which artifact would you stake the decision on** — a
stop whose process took no external measurement, cannot tell you in advance whether the next one contacts,
and was in fact 127 mm from where it believed it was; or a stop with a frozen 78 mm prediction that held,
a margin sized from a measured fault, and a declared (and operator-acknowledged) limitation? Instance 2
answers it the same way Instance 1 did, and adds: the cheap measurement the freestyle arm skipped is the
one that would have made it both safe-to-trust *and* closer.

---

## 8. Caveats & threats to validity

- **n = 1 per arm; instances differ.** One pair cannot establish a rate. And Instances 1 and 2 are **not a
  clean repeat** — the SE prompt was revised between them, and the two freestyle runs differ (the Instance
  1 pilot carried a ~26 mm geometric reference offset; the Instance 2 run trusted the raw ultrasonic and
  ate the full ~127 mm bias). So the cross-instance comparison is *directional*, not controlled. Clean
  repeats (§9) are required for any rate claim.
- **Approach-strategy confound on closeness.** The freestyle arm used **encoder dead-reckoning** (one
  stationary `d0`, then brake on wheel-degrees) — arguably *more* sophisticated than the SE arm's
  sensor-triggered approach — and targeted a 30 mm sensor reading. The SE arm triggered on a (reassigned)
  sensor reading. The two arms therefore differ in control architecture as well as method; this is **fair
  latitude** (freestyle chose its approach) but it is a confound on a head-to-head closeness number, and
  should be named as such, not hidden. The auditability comparison is *not* affected by it.
- **Config-matching to confirm.** Verify the freestyle run used **exactly** Instance 2's model and config
  (Opus 4.8, Max Thinking) so the prompt remains the only intended variable; the table above assumes it.
- **Hardware drift / chassis equivalence.** Both arms crashed during characterization (method-invariant —
  mirror-mount, motor asymmetry, sensor blocking/crosstalk, and the faulty B sensor are in the hardware).
  Confirm both arms' operation runs were on an **intact, equivalent chassis**; the freestyle outliers
  (passes 2, 4) involved wheel slip and a low `d0`, which is partly mechanism/traction and partly the
  arm's missing plausibility filter — disentangle from the operator log.
- **Characterization-ledger reconciliation.** Rebuild the per-run ledger (both arms) from the operator's
  **live log**, not the self-reports; crash counts and which runs contacted are themselves data about
  self-report reliability, but only when anchored to the canonical log.
- **Commentary bias.** Real-time narration of the freestyle run over-read its early failures and, on one
  run, was itself fooled by the biased sensor figures (a clean object lesson — even a human watching
  closely cannot see a fixed sensor offset without a ground-truth anchor; the delta table is the only
  thing that revealed it). The doc reflects the corrected, operator-measured picture, not the live
  impression — and uses the **operator-measured** gaps throughout, never the onboard run-by-run numbers.
- **Single operator / single wall geometry.** One environment, one start distance.

---

## 9. Open items / future instances

- **Clean repeats of Instance 2** (both arms, revised SE prompt, identical config) — to get outcome
  variance and test whether the *coupled* result (auditability driving outcome via fault-catching)
  reproduces or was instance-specific to this sensor's bias magnitude. Highest priority.
- **Capability-ladder runs** — the same A/B across model tiers. Standing hypothesis: scaffolding helps
  weaker models more and the *outcome* gap moves with tier, but the *auditability* gap persists regardless
  — and, per Instance 2, so should the fault-catching that an external anchor buys. If the auditability
  column stays SE-only across the ladder, that is the strongest form of the result. (Candidate LessWrong
  piece.)
- **A frozen-prediction / mandatory-anchor ablation for the freestyle arm.** Does *asking* freestyle for a
  committed prediction, or *requiring* one ground-truth measurement, close the gap — or does it still not
  produce a sized, traceable argument, and still mis-handle the anchor? Probes whether auditability is a
  method property or just an unasked-for one. Especially pointed here: the freestyle arm *had* the option
  to measure and declined it to protect a score.
- **Resolve the prompt-silence on operation-vs-verified config** — make explicit whether a post-verification
  configuration change forces re-verification (and budget that second verification as an expected step,
  given that the bias-anchoring sequence forces verifying at a different trigger than operation). This is
  the SE arm's one flagged soft spot, and it is a prompt fix, not a process fix.
- **Telemetry-grounded appendix** — line up onboard-estimate vs. operator-measured from the raw streams for
  both arms (the numbers above are from the final reports; the raw telemetry is the primary source).

---

## 10. Source artifacts

**SE arm (Instance 2):** `01_requirements_specification.md`, `02_wall_run_model.sysml`,
`03_calibration_plan.md` + `03_calibration_plan_v1.1.md` (Gate A, revised post-C1);
`04_calibration_report.md`, `05_verification_plan.md` (Gate B, frozen prediction);
`06_verification_report.md` (Gate C, the B-faulty / A-accurate finding); `07_final_report.md`. Plus
`operation_run_v2.py` (locked program), inline charts, and per-run telemetry (captured separately).

**Freestyle arm (Instance 2):** `rover_wall_stop_report.md` (single final report, incl. the locked
program). Plus inline charts, per-run telemetry, and verbatim run-by-run reasoning (captured separately).

**Apparatus:** `Spike-SysML` repo — `experiments/Task_core.md` (shared), `experiments/Se_arm_prompt.md`
(revised, with `CHARACTERIZATION METHOD`), `experiments/Freestyle_arm_prompt.md`,
`models/rover_generic.sysml` (SE arm input).

**Prior instance:** `AB_comparison_structured_vs_freestyle.md` (Instance 1; pre-revision SE prompt).

---

*Status: Instance 2 drafted; n = 1 per arm. Outcome figures from the arms' final reports (operator-measured
gaps); to be re-grounded against raw telemetry and the operator's canonical run log. Reads alongside
Instance 1 — the two together bracket the auditability thesis (orthogonal to outcome in Instance 1,
decisive for it in Instance 2).*
