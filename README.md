# Systems Engineering method for self-learning robotics with Claude, Lego Spike Prime and SysML v2

## Executive Summary

Large language models are better with language than with three-dimensional space, physics, or robotics. This work investigates whether a structured systems-engineering method can close that gap. The approach is not to make the model better at physics, but to convert a physical control problem into the kind of problem LLMs are already good at: writing down a claim precisely enough that it can be tested and improved upon.

The test in this investigation uses an LLM to learn to drive a robotic rover towards a wall at full speed and then stop as close as possible without contacting the wall. Each test series is a fresh LLM session with no memory and no web access. Rover control is achieved wirelessly via MCP. The investigation ran 23 test series comprising 246 rover runs, using 4 different LLM models, testing 2 distinct approaches. One approach uses a governed path following a gated systems engineering (SE) method. The second approach uses a “freestyle” path given the identical task and no prescribed method. The freestyle prompt is identical across all 10 of its test series. The SE method evolved through 3 versions on Opus 4.8 over the first 4 test series, holding the last version fixed at SE v2 from the fourth test series onward, for 10 test series across Opus 4.8, Fable 5, Sonnet 4.6, and Opus 5.

<img width="975" height="238" alt="image" src="https://github.com/user-attachments/assets/9e7fe705-48eb-42d7-8b1d-0f149c45162f" />

*Figure 1: Test series and approaches over 23 test series, 4 models and 2 approaches*

Since each test series learns from scratch, differences in what the LLM discovers first compound into a variety of solutions. Even on the more structured SE path, four identical SE v2 prompts on Opus 4.8 with the same rover hardware produced four different rover stopping algorithms. Despite this, the rover never hits the wall in 115 operational runs, on any model, on either path.

However, the closeness, predictability and variability of the remaining gap differed widely between test series. During operational runs (after the LLM has decided it is done learning) the worst-case results for the Opus model family using the SE v2 approach vs freestyle achieved stopping distances from the wall that were nearly 6x closer, with 16x less error between the predicted and actual gap, and 8x less variability.

On the Opus models the governed SE v2 path delivered closer operational stops almost every time. The one exception is an Opus 5 freestyle test series which produced the closest average operational stopping distance (and a subsequent Opus 5 freestyle series produced the farthest). More importantly, for physical hardware control the SE v2 path was more repeatable and made much better predictions of its own performance. For performance to be useful in the physical world you need to know where you are. The SE v2 path also provides several other important artifacts required for the control and auditability of physical systems: engineering requirements, an engineering model, a calibration record, a performance prediction and a verification report. As LLMs continue to improve and need less harnessing, the SE process and these artifacts will still be valuable for physical systems, providing falsifiable predictions and the record that enables diagnosis and improvement.

## Test Architecture

The test architecture consists of first a characterization phase where the LLM develops and tests its approach to the task. The LLM is instructed that analysis is free, and so is repositioning and rebooting the rover between runs. Each flashing of a new program onto the rover, and all other requests for human measurement or observational information about the rover, count against its score. After as many characterization runs as the LLM needs to figure out how to control the rover to do the task, the program is locked and run 5 times in an operation phase. This architecture and the task definition are provided identically to the LLMs across all 23 test series and the only variable is the addition of either a freestyle or SE method prompt.

The hardware configuration under test is a Lego rover based on the Spike Prime/Mindstorms architecture running Pybricks firmware. Program loading, start commands and telemetry are sent via Bluetooth using an MCP developed for this testing. Each LLM tested used max effort, thinking on (or on auto for Fable 5 and Opus 5), incognito mode and no web search. Each test series is isolated from all others and there is no sharing of programs or results. All testing uses the exact same MCP, rover hardware, test location, measuring device, LLM settings, and the same two-phase test architecture.

<img width="1970" height="692" alt="image" src="https://github.com/user-attachments/assets/b79f03a6-3853-465d-87b3-e46a237def21" />

*Figure 2: Lego Spike Prime/Mindstorms rover*

## The Task

The task is to drive the rover at full speed towards a wall 1 meter away and stop as close as possible to the wall without contacting it. The rover hardware includes several characteristics that must be discovered, such as which sensor and motor are on which port. Each differential drive motor has different top speeds creating rover yaw at full power. The wheel encoder can slip when starting and stopping abruptly. The ultrasonic sensors degrade from around 100mm and saturate below about 40mm. The Bluetooth connection is too slow for real-time control. The hardware also has some intermittent issues that are harder to diagnose. One of the two forward-facing ultrasonic sensors inconsistently reads closer (the offset is set at power-on and on some runs is absent entirely). The two forward sensors can also pick up each other's pings and both experience temporary dropouts. Finally, there are two extra sensors: a third ultrasonic sensor pointing aft and a color reflectivity sensor pointing down, neither of which are needed for this task. The LLM must discover, diagnose and then work around ambiguous data in each test series.

https://github.com/user-attachments/assets/d1444142-e2e6-4237-92bc-74951fa99ef1

*Figure 3: Spike-SysML SE test 10 program*

## Systems Engineering Method

The systems engineering method has been used successfully over time to help engineers predict, control and improve the performance of complex systems. This investigation explores whether the same method can provide the same uplift and discipline when the engineer is an AI. The SE method used in this investigation was developed and refined on Opus 4.8 across three versions, each written after the previous one exposed a gap, roughly doubling the prompt length from v0 to v2. Gates are introduced with the SE prompt requiring specific tasks and artifacts before the LLM may proceed. The LLM is told these artifacts are for human review and approval, but in practice the human operator in this investigation never modified the plan or provided helpful feedback at the gate; instead the LLM was told to proceed in all but one case where a gate was rejected (discussed more below in the Fable 5 and Sonnet 4.6 performance section).

The SE v0 prompt at 2,049 words set the baseline instructing the LLM to break the task into requirements, create an engineering model in SysML v2, and pass three gates: a plan before touching hardware, a calibration report before the verification run, and a report on verification before operation. It asked the LLM to commit to a predicted stopping gap; however whether to check that prediction against a real measurement, and where, was left to judgement. The single v0 test series stopped at an average of 192mm from the wall. After finding its two forward sensors 120mm apart, it identified which read short but kept triggering on whichever read nearer as a fail-safe. It waived the 'sensors agree' requirement and accepted the 120mm offset. The subsequent SE v1 and v2 methods added features to address both these issues: specifically surfacing and resolving sensor disagreement and mandating each requirement close with evidence visible at a gate review.

<img width="966" height="317" alt="image" src="https://github.com/user-attachments/assets/3c793768-ab27-4177-802d-b4a3ded279aa" />

*Figure 4: Requirements and SysML v2 models generated in SE test 7*

The SE v1 prompt at 2,808 words added the requirement to freeze the stopping gap prediction. It also asked the LLM to rank its measurement channels by confidence, with operator ground truth at the top; however no measurement was required. The two v1 test series had very different results. One requested a measurement, found a faulty sensor with it, and finished 71mm from the wall within 1mm of its own prediction. The second took its only ground-truth gap measurement far from the wall, never re-checked at the operating point, shipped a 97mm sensor bias (due to near-field phantom echo) into operation, and finished 148mm out and 105mm from its prediction. On this hardware a single far-field measurement extrapolated into the near-field is an assumption, not a calibration. As a result, SE v2 added focus on ground truth at the stopping target.

The SE v2 prompt at 3,977 words added the requirement to develop a Python executable version of the SysML v2 model. This was then used to run a sensitivity check on each unknown variable so that measurement effort and anomaly resolution would focus where most valuable to the objective. It also raised the standard of evidence, requiring any sensor reading that drives the stopping distance to be treated as a hypothesis until independently confirmed at the operating point, prior to the last gate. The Verification Report was made the single place every requirement closes, each with a verification method, its evidence, and a verdict. No requirement may be asserted without evidence, and a report missing any verdict is a blocker at the final gate. The four SE v2 test series on Opus 4.8 stopped at average distances of 44mm, 43mm, 20mm and 36mm, with prediction errors of 3.5mm, 1.7mm, 10.0mm and 1.6mm.

<img width="975" height="751" alt="image" src="https://github.com/user-attachments/assets/621d87f7-6c08-412f-8864-4159e53cfadd" />

*Figure 5: Development of the SE method and comparison to freestyle testing*

The SE v2 prompt on Opus 4.8 showed improved performance over v0, v1, and freestyle with closer stops, tighter spread and smaller prediction error. Opus 4.8 SE v2 also maintained the SE path improvement vs freestyle with fewer impacts, and no increase in characterization runs, though it did ask for more human measurements. At this point the SE method was frozen, and everything that follows uses the same unchanged v2 prompt.

## Other Models

With the method frozen, the next question is whether it performs well on other models. Three additional models were given one test series on each path using the identical SE v2 and freestyle prompts.

The results diverged. On Fable 5 the method did not improve closeness or prediction: its SE series finished 160mm from the wall against 114mm freestyle and missed its own frozen prediction by 119mm. On Sonnet 4.6 the method helped similarly to Opus 4.8, roughly halving both the stopping distance and the prediction error against freestyle, but one operational run was stopped early by a false sensor trigger. Opus 5 was the only one of the three to match the Opus 4.8 results and so received three further test series on each path. Fable 5 and Sonnet 4.6 were not tested again and both LLMs’ performance is further discussed in the analysis section.

<img width="975" height="783" alt="image" src="https://github.com/user-attachments/assets/4bda27be-eb61-4c53-87e3-74e852a007fa" />

*Figure 6: Fable 5, Sonnet 4.6 and Opus 5 testing*

## Results

The results below focus on Opus 4.8 and Opus 5, the two models with enough test series to compare usefully with 4 freestyle and 4 SE v2 each. The same metrics were gathered across all four groups.

### Stopping distance
The four SE v2 test series on Opus 5 stopped at average distances of 22mm, 27mm, 30mm and 27mm, closer than Opus 4.8 under the same method. Freestyle improved too, and far more dramatically on average, but not consistently. Opus 5 freestyle produced both the closest operational run in the investigation, stopping 1mm from the wall, and the farthest at 284mm.

<img width="1180" height="196" alt="image" src="https://github.com/user-attachments/assets/ad93caf0-9ea5-43b7-802a-391487bc11b4" />

*Table 1: Operational stopping distance summary*

<img width="975" height="379" alt="image" src="https://github.com/user-attachments/assets/a7f04339-9373-4bdf-acfc-48291564d658" />

*Figure 7: Operational stopping distance overlay*

### Prediction error
This is where the v1 frozen prediction and the v2 evidence standard show up most clearly. Across the eight SE v2 test series on the Opus models, spanning two model generations, the error between predicted and actual stopping distance never exceeded 10mm. Across the eight Opus freestyle test series it ranged from 6mm to 158mm.

### Repeatability
Subtracting the closest stop from the farthest in each configuration, the SE v2 test series are 6x more consistent on Opus 4.8 and 15x on Opus 5 when compared to the corresponding freestyle test series. That grouping tightened between Opus 4.8 and Opus 5 on the SE path, from 37mm to 19mm, and widened on the freestyle path, from 223mm to 283mm.

<img width="1100" height="204" alt="image" src="https://github.com/user-attachments/assets/2a849e30-4868-47c2-96cf-d8b268966cf4" />

*Table 2: Operational error to prediction and stopping range*

<img width="975" height="379" alt="image" src="https://github.com/user-attachments/assets/98a3ce1b-8959-41fd-a347-dcb88acbcece" />

*Figure 8: Operational average stopping distance, max-min and prediction error*

### Cost
The path to these results involved a similar number of characterization runs, with both the Opus freestyle and SE v2 test series generally needing 4-8 runs. In the characterization phase the Opus SE v2 test series had 6x as many human interactions (especially Opus 5 which accounted for 2/3), and Opus freestyle tests had 3x as many wall contacts during characterization. The SE v2 method doesn’t cost more runs vs freestyle, but it does cost more operator measurement time.

<img width="975" height="379" alt="image" src="https://github.com/user-attachments/assets/5fb741ea-1db3-4618-ba8d-f14582eadaca" />

*Figure 9: Human measurements, impacts and number of tests run during characterization*

Across all four configurations the pattern is consistent: the method reduces variability in the results and improves how well they are predicted, but it does not always achieve the closest stop to the wall. Explaining why requires looking past which prompt and model was used and focusing on the behavior of the LLM during testing.

## Analysis

Across all 23 test series, three behaviors account for most of the differences in performance. Each traces back to something the prompt did or did not ask for, and each shows up in a different metric.

### Behavior 1: Checking the number the stop depends on
Every SE version asked for a prediction, but only v2 made a ground truth check mandatory, and asked for it to be taken near the target stopping distance. This behavior drives the average stopping gap, because a wrong reference point can shift every run the same way. Test series 9 on Opus SE v2 took a second measurement at 43mm and produced the closest Opus 4.8 SE result at 20mm. Test series 6 on Opus SE v1 checked at 530mm and got a 148mm result. Test series 8 on Opus 4.8 SE v2 was the counterexample taking a measurement at 542mm and still getting a 43mm result. The test 8 sensor offset happened to be stable from 542mm down to the operating point, so the far anchor transferred. Test 6's did not, because its bias was caused by a near-field artifact that does not exist at 530mm. Though a close measurement is not required to get a close stopping distance, it confirms if the architecture can support it.

### Behavior 2: Checking the numbers the prediction depends on
This is supported by both v1's frozen prediction and v2's evidence standard, and it drives prediction error rather than stopping distance. The error is essentially the size of the largest term never anchored and how much that term moves. However, neither SE version asked how many times a term had to be checked. Test series 15 on Opus 5 SE v2 demonstrates this behavior twice. Initially the LLM based its stopping decision on the forward ultrasonic sensors but found the error against three separate operator measurements unstable. Checking the terms the prediction rested on is what surfaced the instability, and an unstable term cannot be calibrated out. The LLM then disqualified the ranging strategy, and the stop was rebuilt on wheel travel from a measured start line. The new prediction was computed from terms that had each been anchored, frozen at 29.5mm before the final verification run and never edited. The five operation runs averaged 29.8mm with a 0.3mm error (the smallest prediction error in the investigation). In contrast, test series 9 on Opus 4.8 SE v2 (the closest Opus 4.8 SE result noted above) chose to base its prediction on a single correction for the rover's own estimate of its stopping gap vs the true gap. It checked that correction twice against a human measurement, at two different stops, and got corrections of 31mm and 21mm. It reasoned that the second stop more closely matched the operating configuration, and locked 21mm. But across the five operation runs the correction averaged 28mm, ranging from 20mm to 34mm, meaning its locked value sat 7mm low. This offset accounts for most of the 10mm gap between its 30mm prediction and its 20mm result (the largest prediction error of the eight Opus SE v2 series). Freestyle test series 14 is the counterexample with one operator measurement and a prediction resting on a single sample the LLM itself flagged as thin. The series finished 6mm from its prediction which was the best freestyle prediction error in the investigation and better than two of the eight Opus SE v2 series. In this case the sensor just happened to hold still enough for the entire test series. Committing to a prediction is not enough. Like checking the number the algorithm depends on, the numbers the prediction rests on have to be checked, and checked enough times to know whether they hold.

### Behavior 3: Protecting the stop from a single bad sensor reading
No version of the prompt ever asked for this. It drives repeatability, because a sensor reading without some sort of backup or guard does not corrupt every run, only some, which splits the results into two populations instead of shifting them all. Test series 13 on Opus 5 SE v2 is the only Opus 5 SE campaign that kept the ultrasonic sensors in the control path, and it guarded them. A repeated value was not treated as a new sample, the brake point came from a six-sample average, and range plus wheel travel had to stay constant or the run aborted. Each guard was fired deliberately in calibration before being relied on, but in operation none of the guards were needed and the ultrasonic sensors triggered all five stops giving a max-min spread of 8mm. On freestyle test series 15 the primary sensor in the stopping algorithm read about 14% short at the start line on some runs. The start-of-run check had a wide band, so the short reading passed unguarded. Because this reading also sets the wheel travel budget the rover twice braked about 120mm early, resulting in a max-min spread of 124mm. Freestyle test series 12 is the counter-example. It locked a sensor it had already flagged into the braking path with no cross-check and still held a max-min spread of 16mm. The fault was constant rather than intermittent, and the sensor sat pinned at its 40mm floor on every run so it shifted all five stops alike instead of splitting them. Guarding the stop is not a matter of adding a check but of checking the property that can actually fail.

<img width="974" height="1033" alt="image" src="https://github.com/user-attachments/assets/aea2fb82-376a-449c-9f97-57e4b40d015a" />

*Figure 10: Prompt requirements, model behaviors and rover outcomes across all 23 test series*

Scored one metric at a time, the three behaviors agree with the results in 17, 19 and 16 of 23 series. The third behavior is actually a stronger match when considered as a pass/fail. Every one of the six series whose stopping distances fell into two separate groups failed the behavior, and no series that performed the behavior ever split. Combining the three measures into a single composite score is a harder test, because a good score requires doing well on all behaviors at once. The relationship holds at a correlation of −0.88 across all 23 series, with the scores spreading widest among the test series that performed all three behaviors and flattening out among those that performed the fewest.

<img width="974" height="543" alt="image" src="https://github.com/user-attachments/assets/44ed8ea2-3375-4ce8-aa2d-c73ebd80553f" />

*Figure 11: Composite performance score vs sum or key behaviors*

### The freestyle path supports the three behaviors
An interesting test of whether these behaviors cause the outcomes comes from the path never told to perform them. Freestyle test series 13 supplied all three unprompted. It measured its own zero point and caught a faulty sensor with it, committed to roughly 21mm before locking its program, and removed the unreliable sensor from its control path. It beat the SE path on closeness and was very similar in terms of repeatability. No other freestyle series did this well on these two metrics however its prediction error was over 3x its average distance from the wall and was lucky not to have contacted. Freestyle test series 16, the same model on the same unchanged prompt, supplied almost none of these behaviors and produced the worst result on record.

### What did not correlate
Four things that look like they should predict performance do not. Within either path the number of human measurements correlates with none of the three metrics. Test series requesting zero measurements produced both the best and second worst results, and one SE series requested 6 measurements and finished further from its prediction than two SE v2 tests that only requested 1. Closeness of the rover to the wall during measurement matters, not count. Both paths generally used four to eight characterization runs, and within either path the count predicts nothing. Freestyle hit the wall nine times to the SE v2 path's three, but within either path contact is not predictive. The freestyle series with the most contacts produced the best Opus 4.8 freestyle result, and another used three deliberate contacts to find its sensor offset. Code length tracks the model, not the method. Opus 4.8's locked programs ran a median of 119 lines and Opus 5's 251, while the SE and freestyle medians were 179 and 159. The longer, more prescriptive SE prompt did not produce longer or more complicated code.

The models are clearly capable of all three behaviors with and without the prompts. What the method changes is how often the behaviors occur, regardless of number of operator measurements, characterization runs, wall contacts or the length of code.

## Other Observations

Several other observations are worth noting here as they contribute to the results not explained cleanly by the three behaviors.

### Freestyle 13 deeper look
At first glance the Freestyle 13 result may seem like a win, but its performance is more complicated than that, involving the unprompted behavior noted above, a catch, a miss, and a little luck. After removing the faulty sensor from the control path noted above, the LLM switched to a wheel encoder travel algorithm. It then measured its wheel-travel conversion at two speeds and correctly diagnosed why they disagreed. It used the right value for distance tracking but derived the sensor's zero point from the wrong one. That single substitution accounted for most of the error that left the LLM thinking it was 8mm farther from the wall than reality. The rover got close, but it didn’t really know how close. Had the wheel encoder error resulted in 2mm further offset, or the operational braking performance been less consistent, the rover would have contacted the wall. This was the only test series that performed all three behaviors and still had a failure that was saved by luck.

### Fable 5 and Sonnet 4.6 performance
Every Opus SE v2 series performed two and a half to three behaviors. Fable 5 SE v2 performed one, Sonnet 4.6 SE v2 one and a half. Fable 5 took the required measurement with the rover ~28° off square, left over from its calibration maneuvers. A correction computed at that angle does not transfer to driving straight: the primary sensor read ~100mm short of what the correction assumed, so the rover braked early and stopped at 160mm against its own 41mm prediction. The operator also rejected Fable 5's steering gate after the LLM misread its own heading log by a factor of ten, reporting 3.9° where the rover had arced 39°. Sonnet 4.6 simply left one unguarded sensor in the control path, and one run needed the guard. Both land on the Opus based trend for their behavior count despite SE v2 being written specifically against the gaps Opus 4.8 exposed. The method did not fail on these models; the models did not execute the method and were left with issues the method was not designed to protect against.

### Opus 5 convergence
Under SE v2, Opus 4.8's four campaigns produced four different stopping algorithms. Three of Opus 5's four runs converged on the same architecture: dead reckoning on wheel encoders from an operator-measured start line, with ultrasonics out of the stopping decision. Test series 13 was the exception. The campaigns ran isolated, so this is independent convergence rather than a shared idea. It may also be that Opus 5 diagnosed the untrustworthy sensors more consistently, and the architecture is simply the right response. Freestyle showed no matching convergence producing four different stopping strategies. Prediction errors spanned 6mm to 158mm, the widest range of any model on either path. That asymmetry explains the repeatability result. The SE path converged on a strategy covering all three behaviors and its spread halved; freestyle converged on nothing and its spread widened.

## Next Steps

Rather than write a new SE v3 by hand, the plan is to ask Opus 5 to design it, twice, from two different starting points. The first pass receives only the primary record. Specifically, only the LLM inputs and direct outputs: the three SE prompt versions, the freestyle prompt, the task definition, the measured outcomes for all 23 test series, and the reports each LLM wrote in session at the time. The second pass receives everything, including this document. The first pass has to find the patterns; the second is handed a reading of them. The difference between the two v3s measures how much of any improvement came from the record and how much from operator analysis.

Two constraints apply to both. SE v3 must remain scorable against the same task, hardware and criteria as v0 through v2, so a new series compares directly against the 23 already run. And it must be scored on all five measures — characterization runs, human measurements, stopping distance, prediction error and repeatability. A method that buys accuracy by spending more of the operator's time is not an obvious improvement.

## Conclusion

Twenty-three campaigns on four models produced one result that holds regardless of which arm won: the rover never touched the wall in 115 operation runs. The two paths got there differently. Freestyle found a working algorithm and could not say how it knew. The SE path produced a written argument for the stop before any scored run, and that argument is what makes its errors findable.

The method is not why any single campaign came closest to the wall, freestyle test 13 is evidence of that. What it changes is how often the three behaviors happen, and what is left behind when they don't. An unstructured miss produces a number and no way to locate the error; a structured miss produces the number, the term that was wrong, and the gate where it should have been caught. Both paths end with a rover stopping near a wall. Only one of them leaves something to build on.

## Repository guide

- [`latest/`](latest) — per-campaign artifacts for tests 4–16 (23 test series across four models), plus [`Spike-SysML Summary Rev A.xlsx`](latest/Spike-SysML%20Summary%20Rev%20A.xlsx), the campaign summary workbook the results above are drawn from.
- [`prompts/`](prompts) — the runnable instruments: the shared `Task_core.md` both arms prepend, plus `Se_arm_prompt_v2.md` and `Freestyle_arm_prompt.md`.
- [`docs/`](docs) — [`evaluation.md`](docs/evaluation.md) (the locked experiment design: information diet, two-phase protocol, metrics), [`architecture.md`](docs/architecture.md), [`wire_contract.md`](docs/wire_contract.md), and [`system_prompts.md`](docs/system_prompts.md).
- [`models/`](models) — `rover_generic`, the rover-agnostic SysML v2 starting point the SE arm composes from: a bare component skeleton, a free-parameter physics-relation catalog, and requirement templates. The worked wall-run instantiation is produced per campaign under `latest/`.
- [`spike_prime_mcp/`](spike_prime_mcp) — the MCP server (`flash_program`, `run_program`, `get_telemetry`): the shared hardware seam both arms drive through. See [`spike_prime_mcp/README.md`](spike_prime_mcp/README.md).
- [`spike_prime_direct/`](spike_prime_direct) and [`tools/`](tools) — the developer cockpit (`spiketelem.py`) and the tool surface beneath it.

## Architecture and tool surface

The build follows two patterns from [*Building Effective Agents*](https://www.anthropic.com/research/building-effective-agents), plus human review gates. **Prompt-chaining** carries the requirements-and-modeling thread: a single governed sequence works the spec top-down — STK→SYS→FUN→CMP to the single-effector level, authored in EARS to INCOSE GtWR / ISO-29148 — then composes a SysML v2 model by binding calibrated parameters into generic relation templates. **Evaluator-optimizer** carries the hardware-in-the-loop stages, with the hardware as the evaluator: calibration and verification iterate against real telemetry until the fit is sufficient or the prediction holds. **Human review gates** sit before the costly hardware steps; the gate delivers artifacts and decides continue-or-stop on the evidence they carry — it never modifies the test.

Tool surface (v0.1): `sysml_validate`, `check_trace_complete`, `spike_deploy`, `spike_run`, `test_eval`. See [`docs/architecture.md`](docs/architecture.md) for the pipeline sketch and [`docs/wire_contract.md`](docs/wire_contract.md) for the telemetry wire format and requirements model schema.

## Setup

Requires Python 3.10+, and for hardware runs a SPIKE Prime hub on Pybricks firmware. Install the dependencies:

```
pip install pybricksdev matplotlib mcp
```

- `pybricksdev` — BLE communication with the hub (deploy + run).
- `matplotlib` — live telemetry plots in `spiketelem.py`. Required unless you pass `--no-plot`.
- `mcp` — only needed for the `spike_prime_mcp` server (see [`spike_prime_mcp/README.md`](spike_prime_mcp/README.md)).

## Quickstart

```
# validate a requirements model
python spike_prime_direct/spiketelem.py validate spike_prime_direct/requirements_example.json

# run the full pipeline against a real hub (Pybricks firmware required)
python spike_prime_direct/spiketelem.py run spike_prime_direct/hub_program_example.py \
                        spike_prime_direct/requirements_example.json \
                        --log run.jsonl

# or synthesize telemetry without hardware to exercise the pipeline
python spike_prime_direct/spiketelem.py demo spike_prime_direct/requirements_example.json --seconds 8
```

A live plot window opens during `run` and `demo`, one panel per sensor named in a requirement, with each requirement's pass band shaded. Add `--no-plot` to skip it, or `--snapshot out.png` on `demo` to render headless. `spiketelem.py` is a developer cockpit on top of the tool surface; the automated pipeline's agents would call the `tools/` functions directly.

## Status

Implementation v0.1. **Built:** the tool surface, and the evaluator-optimizer right-half (deploy → run → eval) running end-to-end against hardware via `spiketelem.py` and via the `spike-prime-mcp` server. The committed `models/` SysML v2 model validates clean in Syside (the SysML v2 VSCode tooling), though not yet through the in-pipeline grammar loop. **Run in-context, not yet automated:** the structured-vs-freestyle comparison itself — 23 test series complete across tests 4–16 on four models, performed by the model under the [`prompts/`](prompts) instruments through the MCP, with artifacts under [`latest/`](latest). **Not yet built:** the automated requirements-and-modeling left-half — see [Planned](#planned).

### Known issues

- **`reaches` crossing precision.** `test_eval` scores `reaches` by attainment-or-crossing (a sign change in `value - target` between samples), which fixes the prior exact-float-equality bug. Sub-sample crossing time is not interpolated; see the TODO in `tools/test_eval.py`.

## Planned

The direction is a **fully automated pipeline**: a model takes a free-text spec and runs the whole loop — requirements decomposition, effector selection, SysML model composition, calibration, the pre-run verification argument, and the integrated verification run — with the human gates preserved but the requirements-and-modeling left-half executed in code rather than in-context. Today that left-half exists as design ([`docs/architecture.md`](docs/architecture.md)) and draft prompts ([`docs/system_prompts.md`](docs/system_prompts.md)). Also planned: the `verified`-stage checks, the `full` SysML v2 grammar mode, and the calibration/verification tool surface the pipeline's hardware loops will add.

## License

MIT. See [LICENSE](LICENSE).
