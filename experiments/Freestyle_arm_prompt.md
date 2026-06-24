# freestyle_arm_prompt.md — freestyle arm

Runnable instrument for the **freestyle arm** of the structured-vs-freestyle comparison
(see [`../docs/evaluation.md`](../docs/evaluation.md)). Handed to the model in a fresh, memory-free
context (incognito) with the `spike-prime-mcp` tools connected and nothing else — no project
knowledge, no prior design, so the arm starts genuinely blind.

**Assembly:** the delivered prompt is the `task_core.md` fenced block, **then** the fenced freestyle
block below, ending at `Begin.`. The model receives full text, never a link.

What `task_core` deliberately gives the model: the task, the effector inventory, the
port-parameterized code primitives, the IMU, and the telemetry wire format. What it withholds: the
port mapping, the drivetrain sign convention, the stopping physics, and anything calibrated — those
are the model's to discover or solve. The freestyle block below adds **no method**: the arm iterates
as it sees fit.

Run conditions:

- **Same model and configuration as the structured arm** (config is a controlled variable). Thinking
  on; moderate effort.
- Fill in the measured start distance in `task_core` (~1000 mm).
- The hub is **power-cycled between every run** to clear accumulated gyro/sensor drift, so each run
  starts from a clean hub state.
- Operator policy: provide offline characterization measurements *on request* during Phase 1
  (counted as outside input); provide no input during the campaign; record contact and gap
  **externally** for scoring — never trust the model's self-reported closeness.
- Incognito does not persist — capture the transcript and report as you go.

> **As-run pin:** the completed pilots ran against the earlier self-contained (inlined) version of
> this file, which also requested total thinking time / tokens and is **not** byte-identical to
> `task_core` + the block below. Pin that version (tag or commit) for pilot traceability. For a
> clean final A/B, re-run the freestyle arm against this `task_core`-based prompt so both arms share
> identical apparatus.

---

```
You have no prescribed method. Use Phase 1 to understand the rover and develop your stopping
approach however you see fit - flash, run, read telemetry, and iterate until you can do the task
reliably. Then lock your program and run the campaign.

Begin.
```