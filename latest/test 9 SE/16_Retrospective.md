# Retrospective — Process Guidance That Would Have Helped
**Task:** gated V&V of a physical SPIKE‑Prime rover (drive at a wall at max speed, stop as close as possible without contact).
**Outcome:** 5/5 runs no contact, mean gap 20 mm (best 14). This retrospective is about the *process*, not the result — where clearer or additional up‑front methodology would have changed how the work went. Items are ordered roughly by leverage.

What already worked and is worth keeping: the **gated structure** (never proceed past a gate alone), **"argue before you run,"** **"characterize before integrating,"** and **margin as an RSS of independent uncertainties**. Those were load‑bearing. The gaps below are refinements.

---

### 1. Mandate a zero‑cost platform/observability probe as the first hardware step, before any motion.
The first three hardware runs were wasted: two import‑crashes on a minimal MicroPython runtime (no `sys`, no `array`) and one over‑strict gate abort. "Characterize before integrating" wasn't operationalized into a *required smoke test*: a no‑motion, telemetry‑only probe that confirms the runtime's built‑ins, the I/O path, and the timing/throughput budget — plus a rule that no program touches hardware until it has passed a validated offline harness. Both the dry‑run harness and the "confirm the environment first" habit were adopted mid‑stream rather than mandated from the start.

### 2. Require an explicit measurement / observability plan as a Gate‑A deliverable.
Map every parameter you intend to *estimate* to the specific telemetry channel and sampling regime that will estimate it, plus its uncertainty. I discovered mid‑verification that I hadn't logged encoders through the settle window — the only clean way to get the stopping distance `d_stop` — which cost a re‑run. "Instrument for the estimator you need" should be a stated tenet. It would also have forced early attention to the parameter with *no* onboard channel at all (`c_offset`), flagging it as a single point of failure before it became one.

### 3. Separate within‑run repeatability from between‑run reproducibility, and budget the latter.
This was the biggest miss. The process allowed binding `c_offset` from a **single** verification run and treating its uncertainty as effectively a point value. The true run‑to‑run offset averaged **27.6 mm (range 20–34)** versus the **21 mm** I locked in, biasing every onboard estimate **6.6 mm high**. Guidance that would have caught it: any objective‑critical parameter must be estimated from *N* samples taken under the *same* resets the operation will use (power‑cycle, re‑square), and **its variance must be measured, not assumed**. A "reproducibility budget," distinct from the repeatability I did measure (±2 mm within a run), belongs in the method.

### 4. Operationalize "test‑like‑you‑fly" into "calibrate‑like‑you‑fly," and forbid cross‑regime extrapolation without a validity check.
My two `c_offset` values (31 vs 21) were confounded — different stop mechanisms *and* different distances — and I extrapolated across that change. The method should require calibration at the operating point, in the operating configuration, changing one variable at a time, and should explicitly forbid carrying a calibration across a regime change until a check confirms it transfers.

### 5. Require a formal error budget with a "measure or justify — never assume" rule.
Every term listed and annotated with how it was measured or bounded; any term derived from fewer than *N* samples flagged; the whole thing propagated to the setpoint with the required margin. My budgets were right in form, but the dominant term's variance was assumed small. A hard rule that no term may be *assumed* would have surfaced that the one parameter I hadn't sampled enough was also the one driving the margin.

### 6. State an objective hierarchy and a value‑of‑information rule for spending runs.
The four scored dimensions (fewer characterization runs, fewer human measurements, no contact, closeness) compete with no stated weighting, so real deliberation went into trade‑offs and into "is one more verification run worth it." Two additions make those calls fast and defensible: declare **no‑contact a hard constraint** dominating a cost function of runs + gap, and adopt an explicit **value‑of‑information** criterion — run an additional confirming test only when its expected information exceeds its cost. (In hindsight the extra verification *was* justified and produced the conservative setpoint that saved all five runs — but I got there by argument, not by rule.)

### 7. Provide a prediction pre‑registration template and an anomaly root‑cause taxonomy.
I invented my frozen‑prediction format and acceptance bands ad hoc. A standard record — predicted value, derivation, assumptions, a `k·σ` acceptance band computed from the stated uncertainties, and the exact telemetry that will adjudicate it — makes falsification principled rather than judgment‑by‑feel. Paired with a taxonomy separating **model error / parameter error / configuration‑threshold error / environment change**, it would have made the one falsification I hit cleaner: the safety‑net pre‑emption was a *threshold* problem, not a *model* problem, and recognizing that class is what let me re‑derive without discarding the model.

### 8. Require each run to self‑validate its pre‑conditions and self‑identify its exact configuration.
A run was voided because the hub had been powered too long — a stale‑state condition discovered only afterward. The process treats resets as "free" but doesn't require the program to *check and log* the assumed initial state (fresh IMU, start distance in band) or to emit a version/hash of the exact source flashed. Machine‑checked pre‑conditions would auto‑flag a bad‑state run instead of relying on the operator to notice; a configuration fingerprint in the telemetry would make every flash unambiguously traceable to source.

---

## Through‑line
The given process was strong on **structure and argument** but light on **measurement discipline** — how many samples, under which resets, observed through which channel, with variance *measured* rather than assumed. Nearly everything that went wrong traces to estimating a critical, poorly‑observable parameter (`c_offset`) from too few samples in the wrong regime. Guidance items 2–5 target exactly that, and would have had the highest leverage.
