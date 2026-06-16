# Examples

Concrete instances of the artifacts the Spike SysML pipeline produces and
consumes. Useful as fixtures, as references for the wire contract, and as
the input/output of the v0.1 prototype.

## Files

- **`requirements_example.json`** — a small requirements model in the
  schema defined by `docs/wire_contract.md`. Three constraint
  requirements (CN-001, CN-002, CN-003) from a fictional rover spec
  (`rover_test_v1.txt`): stay clear of obstacles on the right and left
  (distance > 50 mm) and stop at a table edge (reflection > 20%). This
  is the shape the orchestrator-workers pipeline merges to and that
  `sysml_validate` checks.

- **`hub_program_example.py`** — a hand-written stand-in for the draft
  agent's output. Drives two wheel motors, reads left/right ultrasonic
  distance sensors and a color (reflection) sensor, and emits speed, both
  distances, and reflection at 20 Hz in the canonical wire format. It
  stops the motors when an obstacle comes within 50 mm or the edge
  sensor drops below 20%. Runs on the SPIKE Prime hub under Pybricks
  firmware.

- **`runs/run.jsonl`** — a captured telemetry trace (~15 s) from running
  `hub_program_example.py` on hardware. Each line is one event per the
  wire contract. All three requirements fail in this run: both distance
  sensors close to 40 mm before the program's stop latch fires (it trips on
  `< 50`, so the `> 50` clearance constraint is already breached — CN-001 and
  CN-002 fail), and the reflection sensor falls to ~3% through the second half
  as the rover reaches an edge (CN-003 fails). The distance failures are the
  instructive part: a stop rule that reacts *at* 50 mm cannot satisfy a
  constraint that forbids *reaching* it — that gap is the reaction + braking
  + margin the stop constraint exists to cover. A useful input for re-grading
  offline via `test_eval` as the pass_criteria grammar evolves. (Captured
  before the speed-aggregation fix, so its `speed_mps` values are the
  near-zero artifact — re-capture for a clean speed trace.)

- **`drive_until_blocked.py`** — the traceability-spine worked example (paired
  with `drive_until_blocked.requirements.json`). Implements R-COL-1 (forward
  collision avoidance) and R-PERF-1 (drive at the maximum speed for which
  R-COL-1 holds) from the spec line *"drive as fast as it can without running
  into anything."* Computes v_max and the stop threshold on-hub from the m2
  model relations, drives clamped to v_max, emits `clearance_mm` (the graded
  channel) plus the two raw forward distances, and triggers the collision stop
  at the threshold. Runs on the SPIKE Prime hub under Pybricks.

- **`drive_until_blocked.requirements.json`** — the requirements model for the
  above, carrying the traceability-spine joins: each requirement links to its
  unit model (`unit_model`), the parts it depends on (`depends_on_parts`), and
  the program that implements it (`implemented_by`); R-COL-1 also lists the
  calibrated parameters behind it (`depends_on_params`), and R-PERF-1 is
  `verified_by` R-COL-1. The `parts` block keys each part to its hub port.

## Quickstart against these examples

```bash
# validate the model on its own
python spiketelem.py validate examples/requirements_example.json

# synthetic run (no hardware) — exercises the full pipeline including
# the live plot and the per-requirement verdict
python spiketelem.py demo examples/requirements_example.json --seconds 8

# real hub (Pybricks firmware required)
python spiketelem.py run examples/hub_program_example.py \
                        examples/requirements_example.json \
                        --log run.jsonl
```
