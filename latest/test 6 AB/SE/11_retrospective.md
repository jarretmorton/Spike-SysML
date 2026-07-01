# Retrospective — Systems-Engineering Process Guidance

**Scope:** What additional SE *process* discipline, had it been in place at the start,
would have changed the outcome of the wall-approach task — specifically, would have caught
the ~97 mm ranging bias before it cost ~100 mm of closeness across five runs. This is a
reflection on process, not a request for information.

---

## The one root failure, stated plainly

Every guidance item below reduces to a single mistake:

> I let a **repeatable-but-unvalidated** instrument define ground truth for the exact
> quantity I was optimizing, and when the instrument produced the one anomaly that would
> have exposed the error (rest readings of 141 mm and 176 mm that my own model called
> impossible), I **explained it away** instead of treating it as a falsification.

The no-contact constraint was protected the whole time because the error happened to bias
*away* from the wall. The closeness objective was quietly wrecked by the same error. The
process gaps below are the ones that let a load-bearing assumption (δ = 0) survive from a
single far-field data point all the way through five scored runs.

---

## A. Measurement discipline — the heart of the miss

**A1. Characterize the measurement system for *bias*, not just *repeatability*, before
trusting it.** My error budget was built entirely from repeatability terms (skid σ 1.5 mm,
overshoot σ 10 mm, sensor σ 4 mm, lip 2 mm → σ_total ~11 mm, margin 33 mm). Every term was
a *precision* term. The actual dominant error was a *systematic ~97 mm accuracy offset* that
appeared in none of them — an order of magnitude larger than the entire budget. Guidance to
add up front: *precision is not accuracy; a low σ tells you nothing about whether the number
is correct. Before any sensor is allowed to drive a scored quantity, run a Measurement
System Analysis that compares it against an independent reference and reports bias, not just
spread.* The first question of any error budget should be "what is the largest error I have
**not** measured?"

**A2. Calibrate at the operating point, not by extrapolation.** The δ = 0 anchor was taken
at ~425–530 mm (chassis 530 / sensor 425). The decision point was ~40–150 mm — deep in the
ultrasonic near field where reflection and crosstalk artifacts live. A single far-field
anchor extrapolated into the near field is an *assumption*, not a calibration. Guidance:
*calibrate where you operate; an anchor taken far from the operating point remains an
untested hypothesis until it is validated near the operating point.*

**A3. Test-like-you-fly must include the full sensor operating configuration, not just
timing.** I correctly timing-matched the calibration and operation hot loops (a good
test-like-you-fly instinct). But the failure mode — two ultrasonic sensors pinging
simultaneously in a tight loop, inducing a crosstalk / side-lobe phantom — only manifests
in the *dual-sensor operating configuration*. A single-sensor bench check would never show
it. Guidance: *test-like-you-fly extends to the complete sensor configuration under
operating cadence and geometry, because common failure modes (crosstalk, EMI, thermal) are
invisible outside the flight configuration.*

---

## B. Independence in verification & validation

**B1. Verify a quantity against an *independent* path — never against the sensor that
produced it.** No-contact (the hard constraint) was verified against an external reference:
operator confirmation. Good. But the *gap* (the soft objective) was "verified" only against
the same ranger that drove the controller — a circular check in which the controller and the
verifier shared a common-mode fault. It passed silently. Guidance: *V&V independence is not
optional for the primary objective; a metric checked with the same instrument that generated
it will pass through any common-mode error undetected.*

**B2. Validation (right thing, real world) is a distinct step from verification (built
right, per spec) — run it per-requirement, and especially for the objective.**
Verification passed: the trigger fired at ≤ 125 mm, brake engaged, no contact. Validation of
the *closeness objective* — does the rover actually end up close to the real wall? — was
never performed until the operator measured after the fact. The objective is exactly the
requirement that most needed a ground-truth validation step and got none. Guidance: *assign
every requirement an explicit V *and* V step; the objective function gets a validation
against physical ground truth, not merely a verification against its own telemetry.*

**B3. Instrument two independent estimators of any critical quantity so disagreement
self-surfaces.** I declined encoder fusion *for control* on fail-safety grounds — that was
correct. But I could still have *logged* the encoder-derived distance purely as a monitor.
Ranger-says-gap-Y against encoder-says-traveled-X would have diverged visibly and exposed the
~97 mm bias from onboard data alone, with no operator measurement at all. Guidance: *a
rejected control input can still be a valuable monitor; log at least two independent
estimators of any critical quantity so their disagreement raises a flag without needing an
external reference.*

---

## C. Reasoning under anomaly

**C1. When data contradicts the model, the model is on trial — not the data.** The single
highest-value observations in the whole run were the readings my model declared impossible
(a rest gap larger than the trigger gap). I labeled them "erratic / unreliable" and filtered
them. That was rationalizing away a falsification. An "impossible" reading is the most
information-rich event available — it means an assumption is wrong. Guidance: *adopt a
structured anomaly-disposition discipline (FRACAS-style): any observation the model calls
impossible is root-caused before the design is locked, never discarded as an outlier. "The
sensor is being weird" is a hypothesis to test, not a disposition.*

**C2. Error budgets must carry systematic and unknown-unknown allowances, not only measured
σ.** Related to A1 but distinct in framing: even without knowing the bias's cause, a mature
budget reserves an explicit line for *unmodeled systematic error* and for *unknown unknowns*,
sized by how consequential a surprise would be. My budget's implicit claim was "the only
errors are the four I measured." Guidance: *no error budget is complete with only
repeatability terms; reserve explicit bias and unknown-unknown lines, and treat the objective
as untrustworthy until an independent check bounds them.*

---

## D. Decision framing

**D1. Treat each measurement as a value-of-information decision, not merely a cost to
minimize.** The scoring penalized operator measurements, so I minimized them (the lean
path). But I never ran the trade: one near-wall measurement would have *falsified δ = 0* and
been worth ~100 mm of closeness on five runs — an enormous return, penalty notwithstanding.
Blindly minimizing a penalized resource is not the same as optimizing the objective.
Guidance: *rank candidate measurements by value of information — how much a result could
change the design — and spend the highest-VoI measurements early even under a measurement
penalty. Front-load the ones that can falsify a load-bearing assumption; those are cheap
insurance against exactly this failure.*

**D2. Maintain a register of load-bearing assumptions ranked by consequence-if-wrong, and
scrutinize them in proportion to their leverage.** δ = 0 was the single most load-bearing
assumption in the design — the entire gap objective rode on it — yet it was established
almost incidentally from one data point and never re-tested. I kept a TBD register, but not
an *assumptions-by-leverage* register. The most-leveraged assumption received the *least*
scrutiny, which is exactly backwards. Guidance: *list every load-bearing assumption, rank by
"what breaks if this is wrong," and give each a validation plan proportional to its leverage.
The assumption that most determines the objective earns the most independent checking.*

**D3. Argue the safety case and the performance case separately.** The two got entangled:
the same conservatism (a high trigger threshold) served both no-contact *and* — apparently —
the approach. When I confirmed safety, that success bled into confidence about the whole
design and masked that performance was poor (stopping ~148 mm out). A design can be perfectly
safe and simultaneously far from optimal. Guidance: *keep the safety argument and the
performance argument as separate cases with separate evidence; never let a passing safety
case stand in for a performance case, or the conservatism that buys safety will hide the
distance left on the table.*

---

## What the process got right (worth keeping)

For balance, the disciplines that worked and should be retained: freezing the operation
program at Gate B and running it unchanged through verification and all scored runs (change
control / configuration management); gating with downloadable, reviewable artifacts before
proceeding; the readiness handshake before every flash; timing-matching the calibration and
operation loops; and prioritizing the two hard constraints over the soft objective when they
were in genuine tension. The failure was not a lack of rigor in general — it was rigor
applied to *repeatability and constraint-protection* while the *accuracy of the objective's
measurement* went unexamined.

---

## The through-line, as a single checklist item

If one line were added to the process for next time, it would be:

> **Before locking any design, validate — against an independent reference, at the operating
> point — every sensor that defines a scored quantity; and treat any reading your model calls
> impossible as proof the model is wrong.**

Everything above is a corollary of that.
