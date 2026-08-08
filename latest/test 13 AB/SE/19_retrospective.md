# RETROSPECTIVE — process guidance that would have helped

**Type:** report (static) · Written after operation close-out
Working backwards from what actually went wrong, not from what felt uncomfortable.

---

## 1. The doctrine covered relations but not estimators

Tenets A2/A3 gave strong discipline about *physics relations* — validated templates, never eyeball a
constant. Nothing told me to audit my **estimators for independence**. `clearance_est_odo` was
algebraically `T + (psi_belief − psi_odo)` from the moment I wrote it: the commanded target plus a
~1 mm error term. I found that by inspection three frozen plans later, and it made the five close-out
numbers nearly content-free.

**Guidance:** at GATE A, require every channel claimed as a cross-source to be shown **symbolically
independent** of the control law it checks — expand it algebraically and demonstrate the trigger's
terms do not cancel. The existing cross-sourcing rule assumes two channels are independent because
they come from different sensors; it never asks whether the *arithmetic* re-entangles them.

## 2. Nothing forced sensor limits into the characterization plan

`r_min_valid` = 40 mm was inherited from a datasheet at T1 and never measured, because CAL-2's fine
staircase stopped at 130 mm reported. That one unmeasured number defeated the v3.0 target choice: the
real usable floor is ~44 mm, so the 26 mm target sat 1 mm below where observability begins.

**Guidance:** the channel catalog should require every channel's **valid range to be exercised to its
boundary**, not merely stated, whenever the operating point sits near that boundary. The plan says to
hand off to another channel where a range is bounded — it never says *measure where the bound is*.
Mine was 10% off, and 10% was the entire margin.

## 3. Test-like-you-fly was scoped to code, not to parameter binding

The doctrine polices the program: identical loop, identical trigger, logging off the hot path. I
followed that scrupulously, then bound `b_offset`'s yaw correction from CAL-2's approaches — which ran
*after* staircases that had drifted the heading 4°. Operation goes straight from the yaw-null to the
approach. That mis-binding falsified v1.0 and cost a run.

**Guidance:** extend test-like-you-fly explicitly to **every calibrated value**, with a mandatory
field in the calibration record: *the phase sequence and pose regime this value was measured in, and
whether operation reproduces them*. Filling that field for `b_offset` would have exposed the mismatch
as I wrote it. Configuration fidelity of code is the easy half; fidelity of the conditions under
which constants were measured is the half that bit me.

## 4. No small-sample discipline

I sized the v1.0 margin from an n=2 sigma, it was falsified, and I re-derived from n=2 again. Only at
v3.0 did I add a ×1.8 inflation — which I invented rather than derived.

**Guidance:** A6 should add that a contributor estimated from fewer than ~5 samples **carries a stated
inflation with a stated basis, or the plan names the additional run that will supply the samples**.
Either is fine; a raw n=2 sd used silently is not. This would have pushed one cheap characterization
run into repeat brake events early, instead of two falsified verification cycles later.

## 5. Falsification criteria needed severity tiers

v2.0 was falsified by 0.1° on a 4° yaw band — inside IMU resolution — while the material problem was a
yaw budget 4× too small. v3.0 was falsified by a clipped reading that mattered enormously. Both were
"falsified", and the process prescribes the same response to each.

**Guidance:** require each frozen criterion to be tagged **performance-bearing** or
**observability/monitoring**, with different dispositions. Performance-bearing failure demands
re-verification; monitoring failure demands a documented decision, which may legitimately be "proceed
with reduced observability". I invented that distinction under pressure at GATE C and had to argue for
it; in the doctrine it would be auditable rather than improvised.

## 6. The artifact-integrity gap

Two near-misses had nothing to do with engineering judgement. A string replacement on `MODE = "CAL"`
hit a header *comment* instead of the assignment, and my verification — a substring grep — passed. The
locked program approved at GATE B would have re-run the entire eight-phase calibration sequence as a
scored run; I caught it only by reading the file byte-for-byte before flashing. Separately, three
stale comments in the flight artifact stated safety margins that no longer matched their constants.

**Guidance:** mandate that the flight artifact's **parameter block be verified by parsing, not text
search**, against an explicit expected-value table immediately before every flash; and that a value's
rationale comment be treated as part of the value, invalid if the value changes. The gated
deliverables all had review discipline. The executable had none, and it is the only artifact that can
crash the rover.

## 7. Costed-measurement placement needed a required argument

M1 was spent at a pose the operation never revisits (11° of yaw), making its yaw correction 7.9 mm of
pure error. M2, taken in the operational configuration, was accurate to 1.4 mm out of sample. Same
instrument, same cost, wildly different value.

**Guidance:** before a costed measurement is approved, require a stated argument for **why the
measurement pose is the operating point**, alongside the committed prediction and interval. Committing
predictions was valuable (both landed inside); nothing forced me to justify the *pose*, which is where
the value actually came from.

---

## What worked and should stay

**Cross-sourcing with hard plausibility bounds was decisive.** Both systematics that would have caused
contact — an 18.6 mm latency bias and a 7.9 mm yaw mis-binding — surfaced only because two estimators
of the same stop disagreed. Neither was visible in any single channel.

**Freezing predictions before running.** It was uncomfortable exactly when it was working. v1.0 being
visibly wrong is worth more than a plan quietly edited to match its result.

**The executable model refusing to compute with unbound parameters.** Twice it stopped me proceeding
on a guess — once on `sigma_psi`, once on `l_sensor`, which is what proved a second characterization
run was unavoidable. That is a mechanism rather than a discipline, which is why it held.

## A structural note on cost

Re-flashing an unchanged ~800-line program before each of five power-cycled runs consumed a large
fixed share of the working budget, which is why later runs got one-line summaries and a single
consolidated figure set rather than per-run analysis. If the harness could flash from a stored
artifact by reference, or verify a hash against what is already resident, that budget would go into
analysis instead of retransmission. It did not degrade the scored outcome, but it constrained
inspection between runs, and over a longer sequence it would have.
