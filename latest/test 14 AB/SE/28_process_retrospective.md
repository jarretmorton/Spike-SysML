# PROCESS RETROSPECTIVE — proposed additions to the SE guidance
**Document:** `28_process_retrospective.md` · **Type: REPORT**
**Basis:** 7 characterization runs, 6 operator measurements, 5 scored runs, 4 anomaly reports,
3 verification-plan versions (2 falsified), 6 calibration-plan versions.

Planned at GATE A: 2 runs, 2 measurements. Actual: 7 and 6. This retrospective asks which
of that overrun was a **process gap** rather than simply my error, and what guidance would
have closed it.

---

## 0. What the existing process already caught

Listing this first so the proposals below are targeted rather than wholesale.

- **Sensitivity analysis before hardware** correctly ranked `b` as the top risk and sent the
  first measurement there. That measurement found a prior wrong by 79 mm — unreachable from
  onboard data, because every onboard channel was self-consistent with the wrong value.
- **The impossible-reading rule** caught a −1032 mm stop distance instantly and forced
  escalation rather than a plausible-sounding explanation.
- **Frozen predictions with pre-committed disposition rules** stopped me shipping a
  12–15 mm systematic *toward the wall* on two separate occasions. Both times the headline
  gap clause passed and a tighter clause failed.
- **Absence by traceability** correctly dropped the rear ranger and reflectance sensor on
  evidence rather than assumption.

The additions below are all things that discipline did *not* reach.

---

## 1. Parameter validity envelope
**Cost incurred: ~2 runs, ~2 measurements.** The single most expensive gap.

**What happened.** `b` was measured at a 178 mm true gap, correct when the ranger was going
to *measure the final gap*. The architecture then changed and the ranger became the *anchor
at ~900 mm* — a different regime — and I carried the calibration across unexamined. It was
range-dependent (−119 mm at 178 mm, ≈−90 mm at 984 mm). Separately, `k` was calibrated on a
run that was 45% slow creep and applied to fast-only runs; creep slips less, so the blended
scale was 1.7% high. That error convinced me the start line scattered by 8.3 mm, and I
hard-coded an anchor to match my own artifact — costing a run and a measurement.

**Why the process missed it.** The source-of-truth rule says a value must be validated *at
the operating point*, which I followed. It does not say what happens when **the operating
point moves underneath a value that was already validated**.

**Proposed clause.**
> Every bound value carries a **validity envelope**: the range, speed, and motion profile
> under which it was measured. A value used outside its envelope is de-tiered to
> **hypothesis** and must be re-anchored. Any architecture change triggers a re-check of
> every calibrated parameter's envelope against its new usage — a change of *role* is a
> change of operating point.

---

## 2. Test-like-you-fly must extend past the program to the operating context
**Cost incurred: the objective itself — an 8× variance underestimate.**

**What happened.** Verification-phase start placements had sd ≈0.6 mm; operation-phase
placements had sd 7.8 mm — **13× wider**. I predicted σ_g = 1.03 mm and measured 8.35 mm.
The entire operation error, bias and scatter, was start-line placement.

Plausibly I caused it: during verification I asked for a measurement after every run, which
made those resets more deliberate than the five rapid operation resets. **My act of
measuring changed the process I was characterizing.**

**Why the process missed it.** Test-like-you-fly is defined purely as a property of the
software: *"the characterization program is a strict SUPERSET of the operation program —
identical control loop, trigger, and buffer skeleton."* I honoured that byte-for-byte across
seven runs. Nothing extends it to the operator's procedure, the setup, or the environment.

**Proposed clauses.**
> Test-like-you-fly applies to the **full operating context**, not the program: the reset and
> setup procedure, the operator's actions, and the environment must match operation, and the
> Verification Plan must state explicitly **which operating conditions were not reproduced**
> during verification.
>
> **Measurement is an intervention.** Where a human is in the loop, requesting data may
> perturb the process being characterized. Any measurement taken inside the loop must be
> assessed for whether it changed the condition it was measuring.

---

## 3. Statistical requirements cannot close on n = 1
**Cost incurred: SYS-8 verified PASS at 0.19 mm, then failed on 2 of 5 operation runs.**

**What happened.** GATE C closed every requirement on a single verification run. SYS-8's
operand is an *error*, and its behaviour is a distribution. One sample said 0.19 mm; service
said 13.4 and 15.9 mm.

**Why the process missed it.** The guidance states that *"the ENTIRE verification argument
closes at GATE C"* and that no requirement needs the operation runs. That is right for
deterministic requirements and wrong for statistical ones, and the process does not
distinguish them.

**Proposed clause.**
> Classify each requirement as **deterministic** (a threshold on a single event — verifiable
> by one test) or **statistical** (a spread, repeatability, or rate). A statistical
> requirement may not be closed on n = 1. It closes on a stated sample-size rationale, or by
> analysis with the sample-size limitation recorded as **residual risk carried into
> operation** — never as an unqualified PASS.

---

## 4. Small-*n* variance estimates must be inflated, and priors defended
**Cost incurred: the margin misestimate that made §2 dangerous rather than merely untidy.**

**What happened.** My Calibration Report named start-line repeatability as *"the weakest
number in the budget"* and assigned it a conservative **8 mm**. The true value was **7.8 mm**
— the prior was right. I then replaced it with 1.03 mm, a point estimate from three runs
that happened to agree, and that number set the margin the scored runs flew on.

**Why the process missed it.** Tenet A6 requires margins be sized from uncertainty rather
than guessed, and A3 forbids eyeballing constants. Neither addresses **replacing a defensible
prior with a small-sample point estimate**, which is the more seductive error — it looks like
rigour.

**Proposed clauses.**
> A variance entering a margin must be an **upper confidence bound**, not a sample point
> estimate. For n < 10 the inflation is material and must be shown.
>
> A prior may be replaced by data only when the data's confidence interval lies **inside**
> the prior. Otherwise **carry the wider of the two.** Replacing a conservative prior with a
> tighter small-sample estimate requires the same justification as relaxing a requirement.

---

## 5. Effector disposition must be per-role, not per-device
**Cost incurred: the largest lost opportunity in the campaign.**

**What happened.** The forward ranger failed badly in motion — 196 mm dynamic lag, +325 mm
in-motion error, crosstalk — and I retired the device entirely. But its **static, motors-off
reading** was its one good mode, and it was the only channel on the rover capable of
observing the start position. Dropping it removed the sole witness to the quantity that then
dominated the result. Keeping it as a static-only anchor would plausibly have collapsed most
of the 8.35 mm operation scatter.

**Why the process missed it.** Rule 7 — *"any effector with no requirement tracing to it
drops out"* — is framed around devices and around *absence*. There is no corresponding rule
for a device that fails **one** of several roles.

**Proposed clause.**
> Traceability is to **roles**, not devices. A device drops out only when no role traces to
> it. A device that fails one role is **re-evaluated against its remaining roles**, and its
> retirement from those must be argued separately and recorded.

---

## 6. Cross-sourcing must survive into the operational architecture
**Cost incurred: same root as §5; the scored quantity ended with no witness.**

**What happened.** REV F shipped with odometry setting the trigger, reporting the gap, and
having no independent check. I recorded this as residual risk and flew it. When placement
moved 18 mm, nothing onboard saw it, and the onboard estimates were tightly clustered
(sd 0.76 mm) while the truth spanned 19 mm — *confidently wrong, five times*.

**Why the process missed it.** Rule 6 and tenet B1 make cross-sourcing a **characterization**
principle: log every channel bearing on a quantity. Nothing requires the redundancy to
persist into the delivered design.

**Proposed clause.**
> A scored or safety-relevant quantity that has a **single observer in the operational
> configuration** is a design defect. It may be accepted only under an explicit waiver
> naming the failure it cannot detect, and that waiver is a gate item — not a residual-risk
> footnote.

---

## 7. Bootstrap and configuration-discovery logic is part of the system
**Cost incurred: 1 run.**

**What happened.** RUN-1 spun at full speed because my polarity test used the rangefinder to
detect a spin, on the assumption that a rotating rover's forward reading stays roughly
constant. It does not — the beam sweeps off the wall. No requirement, no decomposition, no
verification touched that logic, because it felt like scaffolding.

**Why the process missed it.** The decomposition covers the mission function. Code that runs
*before* the hot path and *parameterises* it was never in scope.

**Proposed clause.**
> Any logic whose output parameterises the operational path — port discovery, polarity,
> sign conventions, calibration bootstraps — is **part of the system** and is decomposed and
> verified like any other function. Discovery that cannot be verified must be replaced by a
> measured constant plus a startup assertion.

---

## 8. Simulation epistemics: state what the model can falsify before trusting it
**Cost incurred: contributed to §7; a passing dry run gave false confidence.**

**What happened.** I dry-ran the flight program against a simulator before flashing, and it
passed. It passed because I had written the simulator with a rangefinder that reports
geometric distance regardless of heading — **the same false assumption the flight code held.**
A simulation built from the model can only confirm the model.

Later, adversarial simulation was genuinely productive: modelling beam-loss-on-yaw and
injecting a wrong correction sign found a creep-phase runaway that would have hit the wall.

**Proposed clause.**
> Before a simulation is used as evidence, state **which assumptions it is capable of
> falsifying**. A simulator built from the same model as the flight code is a consistency
> check, not a test. Simulate the **physical mechanism**, not the model; and negative-test —
> inject the failure and confirm the design detects it — before accepting a passing run.

---

## 9. The observation channel is an instrument, and removing one is a design change
**Cost incurred: 1 truncated run, 1 measurement.**

**What happened.** I budgeted ~168 telemetry lines assuming ~1 KB/s. Each `stdout` write
actually blocked ≈240 ms — **20× worse** — truncating RUN-2 and losing exactly the traces
that would have closed two findings. Under the resulting budget pressure I cut
accelerometer logging; that cut is what left AR-04 unresolvable onboard and forced a costed
measurement to settle a direction question.

**Why the process missed it.** Tenet D2 — *characterize the imperfection, do not idealize it*
— was applied to sensors and never to the telemetry link. And the channel catalog is built
once at GATE A; nothing re-checks it when channels are **removed**.

**Proposed clauses.**
> The observation channel is an instrument. Characterize its capacity **before** designing a
> data budget around it, and carry it in the TBD register.
>
> Removing a logged channel is a **design change**, requiring the same traceability argument
> as removing an effector. Cross-sourcing erodes silently under budget pressure.

---

## 10. Configuration control on the flight article
**Cost incurred: two near-misses; almost flashed a program I believed I had changed.**

**What happened.** Twice, a constant edit silently failed to apply — the match string carried
a comment the file did not — so the *usages* were updated and the *constants* were stale. Both
were caught by dry-run behaviour rather than by any check. I then improvised post-condition
asserts and an md5 fingerprint.

**Why the process missed it.** The guidance covers requirements, models, calibration and
verification, but never asks: **how do you know the artifact you flashed is the artifact you
designed?**

**Proposed clause.**
> Every change to the flight article is confirmed by post-condition assertion. The flashed
> artifact is fingerprinted and the fingerprint recorded against the run id, so that "the
> same unchanged program" is a verifiable claim rather than an intention.

---

## 11. Control authority must be budgeted before a closed-loop requirement is written
**Cost incurred: contributed to 1 run and 12.6° of yaw.**

**What happened.** Both motors were commanded above their achievable ceiling, so the speed
controllers were saturated and a heading correction had **zero authority** — subtracting from
an already-clamped command changes nothing. SYS-6 (heading ≤5°) was unachievable by
construction, and no analysis had noticed.

**Proposed clause.**
> A closed-loop requirement must be accompanied by a **control-authority budget**: the
> actuator margin available to the loop at the operating point. A loop with no authority at
> the operating point cannot satisfy a requirement, and this is checkable at design time.

---

## 12. Fusion rules need an explicit failure-mode table
**Cost incurred: contributed to a 119 mm trigger undershoot and one wrong diagnosis.**

**What happened.** `min(A, B)` fusion fails safe against a channel reading *too short*. It
does not protect against the **good channel dropping out and the bad one taking over**, which
is what happened. Worse, I logged the *fused* value rather than its inputs, so the fault was
invisible and I published a wrong root cause in AR-02 before per-channel logging exposed it.

**Proposed clauses.**
> Any fusion rule carries a **failure-mode table**: for each input failure mode, what does
> the fused output do?
>
> Never log a fused or derived quantity **in place of** its inputs. Fusion must be
> reconstructible offline.

---

## 13. Costed resources need an exchange rate and a stopping rule
**Cost incurred: repeated ad-hoc trades made under time pressure.**

Several decisions were "spend a run or spend a measurement" with no stated relative cost, so
I argued each from scratch. And I had no criterion for when a campaign is going badly enough
to re-scope rather than re-derive — I invented one mid-flight ("if v3 falsifies I will not
issue a v4, I will re-open the requirement"), and it was the right call, but it should not
have been improvised.

**Proposed clauses.**
> State the relative cost of each costed resource up front so trades are decidable, and
> require the trade to be argued in the plan rather than in the moment.
>
> The plan includes a **stopping rule**: a budget or falsification-count trigger at which the
> objective is re-scoped rather than the design re-derived again.

---

## 14. One thing the process got right that should be made explicit

The frozen prediction carried **four clauses**, and twice the wide headline clause (gap
within ±3σ) passed while a tight clause (estimate error ≤10 mm) failed. Had I frozen only
the gap, a 15 mm systematic toward the wall would have shipped into the scored runs.

> **Proposed clause.** A frozen prediction must include at least one clause **tight enough to
> fail** when the headline metric is insensitive. A prediction whose only test is a wide
> confidence band is not falsifiable in practice.

---

## 15. The unifying observation

Six of the twelve gaps above (§2, §3, §4, §6, §9, §10) are the same failure: **the system
boundary was drawn around the rover.** The operator's reset procedure, the telemetry link,
my own build process, and the statistical character of the requirements all sat outside it —
and every one of them ended up on the critical path. The rover's own behaviour was, in the
end, the most predictable thing in the campaign: odometry at rest varied by 1.72 mm across
five runs while the result varied by 19 mm.

> **Proposed clause.** Define the system boundary explicitly, then enumerate everything
> outside it that performance depends on. Each such item must be **controlled, measured, or
> declared as an assumption with a validity check**. An assumption about something outside
> the boundary is exactly as load-bearing as a parameter inside it, and it is far less likely
> to be instrumented.

---

## 16. Ranked summary

| # | proposed addition | cost this campaign |
|---|---|---|
| 1 | Parameter validity envelope; architecture change re-checks calibrations | ~2 runs, ~2 measurements |
| 2 | Test-like-you-fly covers the operating context; measurement is an intervention | the objective — 8× variance |
| 3 | Statistical requirements cannot close on n = 1 | SYS-8 failed in service |
| 4 | Small-n variance inflation; priors replaced only by tighter evidence | the margin the scored runs flew on |
| 5 | Per-role effector disposition | largest lost opportunity |
| 6 | Cross-sourcing survives into the operational architecture | scored quantity unwitnessed |
| 7 | Bootstrap/discovery logic is part of the system | 1 run |
| 8 | Simulation must state what it can falsify | contributed to 1 run |
| 9 | Observation channel is an instrument; removing one is a design change | 1 run truncated, 1 measurement |
| 10 | Configuration control on the flight article | 2 near-misses |
| 11 | Control-authority budget for closed-loop requirements | contributed to 1 run |
| 12 | Fusion failure-mode table; never log fused in place of inputs | 1 wrong root cause |
| 13 | Exchange rate between costed resources; stopping rule | decision friction |
| 14 | Frozen predictions need a clause tight enough to fail | *worked* — keep and make explicit |
| 15 | Explicit system boundary with assumption register | unifies 1–6, 9, 10 |
