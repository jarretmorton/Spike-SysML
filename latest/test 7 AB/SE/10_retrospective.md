# Retrospective — Process Guidance That Would Have Helped

**Framing.** The governing process was strong where this task's risk was *low* — specification and logic — and thin where its risk was *high* — physical reality and real-time execution. The requirements decomposition, the SysML/executable roll-up, the freeze-predict-then-test discipline, and the gated review pauses all worked. But **every actual failure was empirical or real-time**, and none was visible to the model:

- C1 drove into the wall (trigger sensor mis-identified; no independent barrier);
- sensor B was silently ~130 mm biased;
- the encoder under-counted the stopping distance because the wheels slip under the hard brake — biased *exactly* in the regime being measured;
- the control loop stalled on a sensor timeout and fired the trigger 21 mm late (no contact, but by luck).

The process's blind spot is the **transition from analysis to hardware**. It said "argue before you run" and "tailor the model," but it did not equip me for the specific ways physics and timing defeat a clean model. The additions below are grouped by theme, each tied to the event it would have prevented.

---

## 1. Getting onto hardware safely (would have prevented C1, and surfaced B and the slip early)

**1a. Require a hazard analysis and an independent safety barrier before the first powered run.** The process had an anomaly-disposition framework for *reacting* to surprises, but nothing requiring me to enumerate hazards and provide a barrier *before* the first at-speed motion. The single most costly event — the wall strike — happened because the only thing between the rover and the wall was the trigger sensor, and when that sensor was mis-identified there was no backstop (the 8 s timeout permitted ~4 m of travel against a 1 m wall). Missing guidance: *"Before the first powered run, enumerate how the run could end badly and provide at least one abort that does not depend on the sensor the control law relies on. Margin protects against variability; a barrier protects against being wrong."* The independent encoder-travel limit I eventually added belonged in the very first program.

**1b. Earn the operating envelope incrementally.** My first hardware exposure was the maximum-consequence maneuver — full speed at the wall with an unvalidated sense→decide→stop chain. A "walk before you run" principle — validate each link at low speed / low consequence and expand speed and proximity only as each is confirmed — would have exposed the sensor mis-ID, the B fault, and the encoder slip at 150 mm/s in open space instead of at 500 mm/s into a wall. This is routine in flight test and field robotics; the process never called for it.

**1c. Name the tension between run-economy and safe exploration.** The scoring penalized program runs and operator measurements, which actively pushed me to bake everything into the operation program and to first-try the high-consequence maneuver rather than spend a couple of cheap shakedown runs. That incentive is backwards under a hard safety constraint. The process should state plainly: *"A few low-consequence exploratory runs are a sound investment against one catastrophic run; run-economy is subordinate to the hard constraint."* Naming it would have freed me to do the safe thing without feeling I was violating the cost discipline.

## 2. Trusting instruments (would have prevented the B and encoder surprises, and the close-out estimator scramble)

**2a. Qualify each instrument against an independent reference before it carries load.** Cross-sourcing told me the sensors disagreed but not which to believe — I couldn't adjudicate without spending a tier-4 operator measurement. A required *instrument-qualification* step (check each sensor against geometry, the known ~1000 mm start, or another sensor) before it is allowed onto the critical path would have caught B's bias before it fired a stop and before I committed it as a trigger channel. Guidance: *"Disagreement detection is not adjudication. Don't put an instrument on the critical path until it has been checked against something you already trust."*

**2b. Characterize an instrument's error modes in the regime you will use it, not just its nominal accuracy.** "Measure D_stop directly" was the right strategy, but the measuring instrument — the encoder — was biased by the very maneuver being measured: the wheels slip under the hard brake, so the encoder under-counts exactly the distance I cared about. Its nominal accuracy (excellent while rolling) hid a large regime-specific bias. Guidance: *"An instrument's error can be correlated with the event you are measuring. Validate it against an independent channel under the actual operating regime — especially at the extremes (hard braking, near-range)."*

**2c. Propagate quarantine.** I correctly suspected the encoder slip, then wrongly dismissed it using sensor B's data — after B was already flagged faulty — then had to re-confirm it, costing a wrong turn on a safety-relevant parameter. A one-line rule would have prevented it: *"Once an instrument is suspect, every inference that depends on it is suspect. Do not overturn a finding using data from a channel you have quarantined."*

**2d. The onboard estimate you will report is itself an instrument.** FUN-6 (EstimateGap) existed but had no accuracy target and was never verified before operation; at close-out I found that neither of my two estimators was fully trustworthy and sorted out their biases only after the fact. Guidance: *"Any onboard estimate you will report or act on is a measurement claim — give it an accuracy requirement and validate it against ground truth before it matters, ideally at the same operating-point check used to close the objective."*

## 3. Real-time behavior and failure modes (would have prevented V1)

**3a. Treat the control loop's real-time behavior as a first-class, characterized quantity.** Latency lived in the model as a parameter, but the loop's *worst-case* execution time was never characterized, and a blocking sensor read sat on the safety-critical timing path. When the ultrasonic hit a no-echo timeout and BLE congested, the loop stalled and the trigger fired late. Guidance: *"Characterize worst-case loop time, not just typical. A control law that assumes a bounded loop period must guarantee that bound; keep blocking I/O off the safety-critical timing path."* This is basic real-time hygiene the process omitted.

**3b. Separate common-cause variability from special-cause failure modes.** My frozen 3σ margin covered random run-to-run stopping spread but said nothing about the rare loop-stall — a fault mode, not noise — and I implicitly trusted the margin to cover a hazard it cannot. Guidance: *"Margin is for common-cause variability; rare/special-cause fault modes need barriers or design changes, not a bigger sigma. Keep a failure-mode list separate from the noise budget."* A lightweight FMEA/STPA step would have carried both.

## 4. Calibration and modeling judgment (efficiency and the tighter-than-designed result)

**4a. Use robust estimators for safety-critical parameters under small samples.** I set `D_stop_eff` to the mean of three samples, one of which (42 mm) was a low outlier that pulled the estimate down and made the operation stops ~11 mm closer than designed. For a safety parameter, the mean of a tiny, noisy sample is the wrong estimator. Guidance: *"For safety-critical parameters calibrated from few samples, prefer a conservative estimator (e.g., the worst credible value) over the sample mean, and treat small-N uncertainty explicitly rather than folding it into a point value."* The runs stayed safe only because my σ was conservative in the *other* direction — luck partly covering for the estimator choice.

**4b. Match modeling investment to where the risk concentrates.** The SysML model, structural checker, and roll-up were rigorous and worth doing, but the dominant risks here were physical and empirical — none of them predictable from the model. A step to classify early whether the dominant risks are *specification/logic* (model-heavy payoff) or *physical/empirical* (test-heavy payoff) would have shifted some up-front modeling energy toward earlier, safe, physical probing — which is where every real problem turned out to be. Guidance: *"Decide early where your risk lives. Invest modeling where logic dominates and hardware time where physics dominates."*

---

## One-line summary

The process was built to keep me honest about **what I predict**; it was light on keeping me safe about **what I don't yet know**. Adding a pre-hardware hazard analysis with an independent barrier, an incremental-envelope rule, instrument qualification (including of the encoder's braking-regime bias and of my own onboard estimate), worst-case loop-timing characterization, and a common-cause/special-cause split would have prevented the wall strike outright, caught the sensor and slip issues at low speed, and averted the V1 late-trigger — most likely turning six characterization runs and a crash into two or three uneventful ones.
