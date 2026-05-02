# Spike SysML

> AI-assisted, requirements-to-hardware test pipeline and feedback loop via SysML v2, demonstrated on LEGO SPIKE Prime.

Spike SysML is a multi-agent system that takes a free-text engineering specification, decomposes it into structured SysML v2 requirements, generates control code for the LEGO SPIKE Prime hub, runs that code on hardware, and feeds sensor results back to the agents for revision. The loop closes on a physical robot: the agent doesn't just produce plausible code — it produces code that has to make a real motor turn, a real sensor read, and a real test condition pass.

The choice of SPIKE Prime is deliberate. It's cheap enough to easily test, and constrained enough that the requirements-to-test loop is interesting rather than overwhelming.

## What this is not

Spike SysML is not a SPIKE programming environment and not a competitor to SPIKE App or Pybricks. It does not generate certifiable artifacts and does not perform V&V — it is a tooling layer that produces inputs to a human-led verification process, with LEGO hardware standing in for a target system. It is not a research project.

## Architecture

Built around two patterns from [*Building Effective Agents*](https://www.anthropic.com/research/building-effective-agents):

- **Orchestrator-workers** for requirements decomposition. A planning agent reads the spec and dispatches structured-output sub-agents to extract functional, behavioral, interface, and constraint requirements in parallel, emitted as SysML v2.
- **Evaluator-optimizer** for code generation, with the hardware as the evaluator. A draft agent generates MicroPython for the SPIKE hub; the code runs on the robot; telemetry and pass/fail signals come back; the loop iterates until tests pass or a budget is hit.

Tool surface (planned):

- `sysml_validate` — schema-check structured requirements against SysML v2.
- `spike_deploy` — push generated code to the SPIKE Prime hub.
- `spike_run` — execute a test program and stream sensor telemetry.
- `test_eval` — score a run against the requirement it implements.

See [`docs/architecture.md`](docs/architecture.md) for the current sketch.

## Status

Pre-v0.1. README and architecture sketch only.

## License

MIT. See [LICENSE](LICENSE).
