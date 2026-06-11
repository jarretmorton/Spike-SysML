# Spike SysML

> AI-assisted, requirements-to-hardware test pipeline and feedback loop via SysML v2, demonstrated on LEGO SPIKE Prime.

Spike SysML is a multi-agent system that takes a free-text engineering specification, decomposes it into structured SysML v2 requirements, generates control code for the LEGO SPIKE Prime hub, runs that code on hardware, and feeds sensor results back to the agents for revision. The loop closes on a physical robot: the agent doesn't just produce plausible code — it produces code that has to make a real motor turn, a real sensor read, and a real test condition pass.

The choice of SPIKE Prime is deliberate. It's cheap enough to easily test, and constrained enough that the requirements-to-test loop is interesting rather than overwhelming.

## What this is not

Spike SysML is not a SPIKE programming environment and not a competitor to SPIKE App or Pybricks. It does not generate certifiable artifacts and does not perform V&V — it is a tooling layer that produces inputs to a human-led verification process, with LEGO hardware standing in for a target system. It is not a research project.

## Architecture

Built around two patterns from [*Building Effective Agents*](https://www.anthropic.com/research/building-effective-agents):

- **Orchestrator-workers** for requirements decomposition. A planning agent reads the spec and dispatches structured-output sub-agents to extract functional, behavioral, interface, and constraint requirements in parallel; a selection-and-composition step then assembles these into a SysML v2 model from a fixed unit-model registry.
- **Evaluator-optimizer** for code generation, with the hardware as the evaluator. A draft agent generates MicroPython for the SPIKE hub; the code runs on the robot; telemetry and pass/fail signals come back; the loop iterates until tests pass or a budget is hit.
- **Parameter calibration and a human gate.** Before the integrated test, unit-level constants are calibrated against the hardware and a human signs off on sufficiency — the one expensive step is gated behind cheap verification.

Tool surface (v0.1):

- `sysml_validate` — schema-check structured requirements against the `lego` subset of SysML v2.
- `spike_deploy` — push generated MicroPython to the SPIKE Prime hub over Bluetooth.
- `spike_run` — execute a deployed program and stream sensor telemetry.
- `test_eval` — score a run against the requirement it implements.

See [`docs/architecture.md`](docs/architecture.md) for the current sketch, and [`docs/wire_contract.md`](docs/wire_contract.md) for the telemetry wire format and requirements model schema.

## Quickstart

```bash
# validate a requirements model
python spiketelem.py validate examples/requirements_example.json

# run the full pipeline against a real hub (Pybricks firmware required)
python spiketelem.py run examples/hub_program_example.py \
                        examples/requirements_example.json \
                        --log run.jsonl

# or synthesize telemetry without hardware to exercise the pipeline
python spiketelem.py demo examples/requirements_example.json --seconds 8
```

`spiketelem.py` is a developer cockpit on top of the tool surface; the orchestrator and draft agent call the `tools/` functions directly.

## Status

v0.1. Tool surface implemented; evaluator-optimizer right-half runs end-to-end against hardware via `spiketelem.py`. Orchestrator-workers left-half is in prompts only.

## License

MIT. See [LICENSE](LICENSE).
