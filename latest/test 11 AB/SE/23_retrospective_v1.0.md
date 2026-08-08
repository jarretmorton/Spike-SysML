# 23 — CAMPAIGN RETROSPECTIVE: Process Guidance That Would Have Helped

Each item below is traced to a specific event in this campaign's record, and
states the guidance as a reusable rule — not the answer to this task.

## 1. Keep a systematic-bias ledger separate from the RSS budget
The margin work treated dispersion rigorously (RSS, 3σ, Monte-Carlo check)
and it was *validated in flight* (measured sd 14.6 vs predicted σ 13.4).
Systematics got one 3 mm row and one asserted ±6 mm allowance — and a
+102 mm bias walked straight through. Biases do not RSS; they add, and each
known bias mechanism needs its own ledger line with either (a) an anchor
taken in the operational regime, or (b) a *derived* worst-case bound.
Corollary that would have been decisive here: **a parameter bound from a
single point has zero residual at that point by construction — zero residual
at n=1 is not evidence the transfer model is valid.**

## 2. Ground-truth anchors must satisfy pose-acceptance criteria before
being spent
M1 was consumed at a pose later shown to carry ~28° yaw; the calibration
plan should have specified anchor acceptance conditions (e.g., |heading
deviation| ≤ 2°, checked from telemetry *before* asking for the
measurement) and a re-position-then-measure fallback. When a scarce
measurement carries all systematic risk, its acquisition conditions deserve
the same rigor as its arithmetic. Also: quantify the residual systematic
risk of the minimal-measurement design in the plan itself, as an explicit
reviewer trade — gate reviews can only weigh risks that are surfaced.

## 3. Audit evidence independence the way requirements traceability was
audited
"Three chains agree within 8 mm" was claimed at verification — but c_pred,
encoder+skid, and DR−skid all inherited o_B through the trigger state; they
were independent for braking, common-mode for ranging. Rule: any claim of N
independent confirmations requires a dependency trace per witness; and at
least one verification pass criterion must be causally independent of the
channel under test. Here, the only independent observable (the A channel)
was demoted to a diagnostic — R-VER passed while blind to the very bias
that dominated the outcome.

## 4. A diagnostic that fires on 100 % of runs is a measurement, not a
nuisance
`est.disagree = 1` fired on all six flights, and the channel it pointed at
was the closest to truth every time. Each firing was explained by a bias
estimate that was itself derived under the contaminated offsets — circular.
Rule: repeated identical diagnostics trigger a mandatory written causal
analysis with at least two competing hypotheses, one of which must be "the
committed channel is wrong"; at verification (where investigation is free,
unlike locked operation) the disagreement must be resolved with independent
evidence or *both* hypotheses carried into the prediction as a widened or
bimodal interval. Apply skepticism symmetrically: the case for the demoted
channel being right should be written down before demotion, with the
observation that would reverse it.

## 5. Units and encodings are controlled artifacts; numbers reach reports
only through code
AR-003's root cause was a mental ÷100 of a ×10 encoding — while the same
encoding was decoded correctly two lines away. Guidance: one
channel-dictionary (name, unit, scale, valid range, worked example) shared
by the program, the simulator, and every analysis script; all quoted values
decoded mechanically through it; and a standing cross-channel plausibility
pass (every derived quantity corroborated by an independent channel — the
encoder L/R split was in hand the whole time and pins the yaw in one line
of arithmetic). Verification criteria must name the exact channel *and
statistic* (max vs endpoint vs mean, window, decode) — the endpoint-vs-max
slip was a criterion-specification gap before it was an evaluation error.

## 6. One as-built configuration record; simulator governed like flight
software
Signs, port identities, ceilings, and geometry lived in three places
(program constants, mock, analysis) and diverged three times (yaw sign
convention, half-track units, identity shuffling) — each caught only when
qualification inverted. Guidance: a single as-built record consumed by all
three; every plant change re-runs a *flight-replication regression* (feed a
known flown program through the plant, require reproduction of key
observables within tolerance) — the one such check performed here, after
AR-003, immediately exposed two plant errors.

## 7. Order telemetry by criticality; budget I/O to measured worst case
AR-002: the dump was sized for nominal BLE, a 6× session collapse truncated
it, and the sentinel — the single most safety-relevant byte — was last in
line. Guidance: summaries first, sentinel-able checkpoint early, bulk series
last, so truncation degrades gracefully; budgets sized to the measured
worst-case rate, not the nominal.

## 8. Gate hygiene: adversarial self-review with independent re-derivation
The operator's Gate C rejection was the campaign's most valuable single
input. Institutionalize it: before every gate submission, re-derive two or
three headline numbers from *raw* telemetry by a path independent of the
analysis that produced them (re-deriving heading from the raw hd buffer
would have killed Verification Report v1.0 before submission). Every bound
revision (TBD-3, 4°→10°) carries a rationale-of-change distinguishing
"derived from corrupt data" from "loosened to pass," reviewed as such. And
locked-artifact transfer should be machine-verified end-to-end (payload
checksum echoed by the flash path), not hand-carried.

## What already worked and should be kept
The gated process with frozen, falsifiable predictions (falsification of
Plan v1.0 worked exactly as designed); anomaly reports as first-class
deliverables; worst-case-priors-only onboard safety logic; mock
qualification with fault injection (four latent defects caught pre-flight);
fail-early margin architecture that made the one large unmodeled error land
entirely on the safe side — 0/5 contacts at +8.9σ of mean error is that
choice paying off; and the strict close-out order, which turned the
estimate-vs-truth gap into calibrated knowledge instead of an excuse.
