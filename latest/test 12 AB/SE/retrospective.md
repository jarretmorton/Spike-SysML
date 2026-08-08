# Retrospective — Rover Wall-Stop Systems Engineering
**Date:** 2026-07-21  
**Context:** Post-operation analysis of process gaps revealed during execution.

---

## What additional systems engineering guidance would have helped

### 1. Trigger noise-immunity is a requirement, not a design choice

The single largest failure (Run 5, 236 mm) came from a false trigger: one USS reading at 99 mm from a lateral surface fired the brake. The current process decomposes requirements down to CMP-5 (stopping distance) and produces a clean trigger-distance equation, but it **never requires the trigger to be robust against a single false reading**. Debounce — require N consecutive readings ≤ TRIGGER\_MM — is standard control practice and would have prevented Run 5 entirely at zero cost in characterisation runs.

The gap: the requirements method, the characterisation method, and the channel catalog all focus on the *nominal trigger condition* and its distance accuracy. None of them ask "under what conditions does the trigger fire incorrectly?" This should be an explicit FUN-level robustness requirement, specified before hardware, derived from the physical noise profile of the USS channel that the calibration plan already catalogues.

---

### 2. Channel directness hierarchy must govern conclusions, not just inform them

The characterisation method asks you to rank channels by directness and confidence, but it does not specify what to do when a lower-confidence indirect channel (heading, easy to interpret) contradicts a higher-confidence direct channel (USS range change, harder to notice). In the motor-direction analysis, heading angle (indirect: could be rotation without translation) was used to conclude direction, while USS-E range change (direct: monotone decrease = rearward displacement) was there and ignored. This cost one run.

The fix: the source-of-truth hierarchy already exists for sensor values; it should extend explicitly to *derived inferences*. Any conclusion about rover motion direction should be required to cite the most direct channel that observes the quantity (range change, not angle), and flag when a secondary channel disagrees — even if the secondary channel is the one that was mentally foregrounded.

---

### 3. API call stability must be characterised before it enters the hot loop

The process specifies test-like-you-fly architecture for *timing and data fidelity*, but has no rule about *API call reliability under operational conditions*. `motor.speed()` was added to the hot loop of Verif-Run-1 because it provided useful calibration data (v\_max\_dps), but its stability at high speed under non-nominal correction commands was unknown and untested. It threw a transient exception at iteration 22, costing one run.

The fix: any Pybricks API call that did not appear in a prior successful run and is now being introduced to a test-like-you-fly or operation-adjacent programme should require an explicit "API stability check" — a deliberate single-call probe in isolation — before it is embedded in the hot loop. This is analogous to unit verification for effectors: characterise the component before integrating it.

---

### 4. Post-trigger execution time needs a worst-case budget before the first operation run

The buffer-then-flush architecture is correctly motivated and the process mandates it. But the process has no requirement to compute the *worst-case execution time* of the flush phase and set the host timeout accordingly. That calculation is simple: n\_entries × n\_channels × worst\_BLE\_latency + settle\_ms. If this had been done at the time the characterisation run design was committed (Gate A), the 15 s timeout for Run 2 would have been set to ≥ 30 s from the start and no data would have been lost. The BLE latency distribution is itself a calibrated parameter (observable from Cal-Run-2 write timestamps vs event counts) that belongs in the channel catalog.

---

### 5. Closed-loop controller design requires a formal equilibrium prediction before the verification run

The heading P-controller was designed with a gain (KP = 5) chosen from first principles and confirmed to reduce drift, but its *steady-state heading error* was never formally derived. The prediction in Verification Plan v1 said "expected drift < 5°" without a derivation. The equilibrium is:

```
h_eq = drift_rate / (KP × effective_correction_authority)
```

where effective\_correction\_authority depends on whether the motor command can actually move below its hardware ceiling — exactly the issue with MAX\_CMD = 1100 vs actual ceiling 929. That formula would have:
- predicted the ~3° equilibrium that was consistently observed
- immediately flagged that MAX\_CMD above the actual ceiling reduces authority by half (only one motor of the pair can be corrected at a time)
- revealed that if a run starts with heading error > 2×h\_eq (e.g., from a slight start-line skew), the controller may not converge before the wall

A requirement that the controller's steady-state error be derived and bounded analytically — not just empirically hoped for — would have made this analysis mandatory before the verification run.

---

### 6. The sensitivity analysis should include sensor-controller coupling, not just open-loop parameters

Section 0 of the calibration plan sweeps d\_stop, d\_combo, tResponse, and v\_max — all parameters of the open-loop stopping model. It does not sweep heading error, even though the heading correction is part of the control architecture and the USS-A reading depends on the rover's heading via geometry. The relevant sensitivity question is: *at what heading angle does USS-A begin to see lateral obstacles at the trigger distance rather than the wall?* This is a deterministic geometric calculation (wall width, obstacle clearance, beam angle, approach distance), not a stochastic one. It produces a *hard limit on the heading tolerance* that should then constrain SYS-5, rather than leaving SYS-5's TBD to be calibrated empirically from approach data. Putting this in the sensitivity table would have made the false-trigger risk visible at Gate A.

---

### Summary framing

The process is strong on the *static model* (stopping distance, sensor offset, trigger distance) and on calibration discipline. The gaps are almost entirely in the *closed-loop and robustness* dimensions: the heading controller's interaction with the sensor model, the trigger's immunity to single-sample errors, the reliability of individual API calls, and the execution-time budget of the telemetry architecture. A future revision that adds:

1. A **trigger-robustness requirement shape** to the requirement templates
2. A **controller-equilibrium prediction** to the verification plan template
3. An **API stability check** to the characterisation method
4. A **post-trigger WCET (worst-case execution time) analysis** to the calibration plan template
5. **Sensor-controller coupling** to the sensitivity analysis table

would close all five failure modes from this run.
