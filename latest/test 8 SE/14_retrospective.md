# WALLRUN — SYSTEMS-ENGINEERING RETROSPECTIVE
*What additional process guidance would have helped, ordered by hardware-runs it would have saved.*

**Through-line:** of 5 characterization runs, only one (C1d) actually calibrated the task physics I set out to measure. The other four were spent discovering how the **platform and instrumentation** behaved (I/O mapping, a drivetrain veer, a Bluetooth telemetry limit). Better process guidance would move almost all of that discovery off scored hardware and onto free analysis. A physics-first process tends to assume the platform away; that is exactly where this task bit.

---

## 1. Mandate offline system identification + control design when the scope contains a control loop
The most expensive gap. The process required an executable model of the task *physics* (longitudinal stopping), which I built — but nothing about modeling the *control-relevant plant*. When the rover veered 14° at speed, I tuned the heading controller by trial on hardware (C1c → C1d), spending a run on what was a controls problem.
**Guidance:** if the solution is closed-loop, identify the plant from shakedown data, design and tune the controller against that model offline, and reserve hardware for validation, not tuning. Controller tuning must never touch scored runs.

## 2. Make platform/instrumentation shakedown an explicit first phase, separate from calibration
The "characterization run is a strict superset of the operation program" tenet hurt me: it pushed I/O discovery, a discovery creep, *and* precision dynamics into one run — so when the discovery motion corrupted the pose, the dynamics data died with it.
**Guidance:** budget one explicit shakedown run whose only jobs are I/O mapping, actuation quirks, and a gentle motion, held to *low expectations* — surprises there are the point. Precision calibration follows on a clean platform. Several cheap single-purpose runs beat one fragile everything-run.

## 3. Treat the observability/telemetry channel as a system component to characterize before depending on it
The wire contract specified message *format* but nothing about channel *capacity*. I lost data to a ~35 line/s BLE limit, then made it worse by "optimizing" with batched writes that ran 5× slower.
**Guidance:** verify bandwidth, latency, buffering, and failure modes of the measurement pipeline, and budget telemetry volume against channel capacity, before relying on it. The instrument deserves the same skepticism as the plant.

## 4. Add a plant-assumption register alongside the parameter TBD register; extend sensitivity analysis to cover it
My sensitivity table ranked *parameters* by leverage (correctly sending the one operator measurement to `c_A`) but never surfaced the *structural* assumption "equal wheel commands → straight." A violated structural assumption is a different, often costlier, failure class than a mis-estimated parameter.
**Guidance:** for each effector, enumerate the idealizations the model embeds — symmetry, linearity, decoupling, instantaneous response, time-invariance — and flag each as a hypothesis with a check.

## 5. Treat run-to-run variance as a first-class calibration target, with planned replication
The "minimize runs" pressure is in direct tension with characterizing variance, which needs repeats — and the process never resolved it. I locked the design on one/two clean stops and *guessed* σ_G = 12 mm; the truth was 7.7 mm.
**Guidance:** when the objective or a constraint depends on run-to-run variance, budget the minimum replication to *estimate* that variance and give it its own row in the sensitivity table. Variance should not be a guessed input.

## 6. Provide a symmetric protocol for favorable surprises; separate bias from scatter at verification
The process gave a clean "falsify → diagnose → re-derive" loop for *bad* surprises but nothing for *good* ones. When verification and operation showed tighter scatter than budgeted, the frozen-prediction discipline (rightly) forbade opportunistically tightening the trigger — so I left the gaps ~20 mm looser than achievable.
**Guidance:** pre-register an adaptation rule — commit a tightening formula and a re-verification step *before* the run — so exploiting a favorable result is disciplined, not opportunistic. Relatedly, the verification stop sat consistently below nominal (D_stop 62 vs 53); "in band" counted as pass, but a single point offset in a *consistent direction* is bias, not scatter. Guidance to re-center the prediction on a detected bias (distinct from widening the band) would have sharpened the operation prediction.

## 7. Budget runs by purpose, and state that combining incompatible purposes raises the cost of any single failure
Underlying all the above: "minimize runs" and "test-like-you-fly superset" pulled opposite directions with no arbitration.
**Guidance:** budget runs keyed to purpose — shakedown, sysID, dynamics, variance, verification — and note explicitly that a run serving two incompatible purposes (discovery motion *and* precision measurement) makes every failure twice as expensive.

---

## What the process got right (keep unchanged)
- **A/B/C gates with frozen deliverables** forced honest sequencing and prevented tuning-to-fit.
- **Sensitivity analysis** correctly identified the one un-observable, high-leverage quantity (`c_A`) and sent the single costed measurement exactly there.
- **"Never tune to fit; re-derive into a new frozen version"** kept verification meaningful.

The gaps were all about the platform and the instrument — the parts a physics-first process assumes away. The delivered result (5/5 no contact, mean gap 43.4 mm, onboard estimate accurate to ±2.6 mm, prediction within 1.6 mm of the measured mean) was reached in spite of those gaps, not because the process anticipated them.
