# Examples

Concrete instances of the artifacts the Spike SysML pipeline produces and
consumes. Useful as fixtures, as references for the wire contract, and as
the input/output of the v0.1 prototype.

## Files

- **`requirements_example.json`** — a small requirements model in the
  schema defined by `docs/wire_contract.md`. Three constraint
  requirements (CN-001, CN-002, CN-003) from a fictional rover spec
  (`rover_test_v1.txt`): stay clear of obstacles on the right and left
  (distance > 100 mm) and stop at a table edge (reflection > 20%). This
  is the shape the orchestrator-workers pipeline merges to and that
  `sysml_validate` checks.

- **`hub_program_example.py`** — a hand-written stand-in for the draft
  agent's output. Drives two wheel motors, reads left/right ultrasonic
  distance sensors and a color (reflection) sensor, and emits speed, both
  distances, and reflection at 20 Hz in the canonical wire format. It
  stops the motors when an obstacle comes within 100 mm or the edge
  sensor drops below 20%. Runs on the SPIKE Prime hub under Pybricks
  firmware.

- **`runs/run.jsonl`** — a captured telemetry trace (~16 s) from running
  `hub_program_example.py` on hardware. Each line is one event per the
  wire contract. In this run both distance sensors stay above the 100 mm
  floor (CN-001 and CN-002 pass) while the reflection sensor reads
  near-zero through the second half (CN-003 fails — the rover reached an
  edge). A useful input for re-grading offline via `test_eval` as the
  pass_criteria grammar evolves.

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
