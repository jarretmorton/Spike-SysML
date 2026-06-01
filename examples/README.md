# Examples

Concrete instances of the artifacts the Spike SysML pipeline produces and
consumes. Useful as fixtures, as references for the wire contract, and as
the input/output of the v0.1 prototype.

## Files

- **`requirements_example.json`** — a small requirements model in the
  schema defined by `docs/wire_contract.md`. Two constraint requirements
  (CN-003 and CN-007) sourced from a fictional rover spec. This is the
  shape the orchestrator-workers pipeline merges to and that
  `sysml_validate` checks.

- **`hub_program_example.py`** — a hand-written stand-in for the draft
  agent's output. Drives two motors, reads a force sensor, emits speed
  and force telemetry at 20 Hz in the canonical wire format, and stops
  the motors on first contact. Runs on the SPIKE Prime hub under
  Pybricks firmware.

- **`runs/press_run.jsonl`** and **`runs/run_example.jsonl`** — two
  captured telemetry traces from running `hub_program_example.py` on
  hardware. Each line is one event per the wire contract. The traces
  differ in the physical event the rover encountered:
  - `press_run.jsonl` — hard contact, peak ~8.3 N (well outside CN-007's
    1 N ceiling).
  - `run_example.jsonl` — gentler contact, peak ~1.9 N (still outside
    CN-007).
  Both are useful inputs for re-grading offline via `test_eval` as the
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
