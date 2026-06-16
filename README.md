# Spike SysML

> AI-assisted, requirements-to-hardware test pipeline and feedback loop via SysML v2, demonstrated on LEGO SPIKE Prime.

Spike SysML is a multi-agent system that takes a free-text engineering specification, decomposes it into structured SysML v2 requirements, generates control code for the LEGO SPIKE Prime hub, runs that code on hardware, and feeds sensor results back to the agents for revision. The loop closes on a physical robot: the agent doesn't just produce plausible code — it produces code that has to make a real motor turn, a real sensor read, and a real test condition pass.

The choice of SPIKE Prime is deliberate. It's cheap enough to easily test, and constrained enough that the requirements-to-test loop is interesting rather than overwhelming.

## What this is not

Spike SysML is not a SPIKE programming environment and not a competitor to SPIKE App or Pybricks. It does not generate certifiable artifacts and does not perform V&V — it is a tooling layer that produces inputs to a human-led verification process, with LEGO hardware standing in for a target system. It is a portfolio demonstrator rather than a research program — though it deliberately measures itself against an unstructured baseline (see [Evaluation](#evaluation-structured-vs-zero-shot)).

## Architecture

Built around two patterns from [*Building Effective Agents*](https://www.anthropic.com/research/building-effective-agents):

- **Orchestrator-workers** for requirements decomposition. A planning agent reads the spec and dispatches structured-output sub-agents to extract functional, behavioral, interface, and constraint requirements in parallel; a selection-and-composition step then assembles these into a SysML v2 model from a fixed unit-model registry.
- **Evaluator-optimizer** for code generation, with the hardware as the evaluator. A draft agent generates MicroPython for the SPIKE hub; the code runs on the robot; telemetry and pass/fail signals come back; the loop iterates until tests pass or a budget is hit.
- **Parameter calibration and human review gates.** Unit-level constants are calibrated against the hardware; a human reviews each test design before it runs, signs off that the calibration fit is *sufficient* before the expensive integrated test, and accepts the integration *results* before the run is declared done — the costly steps are gated behind cheap verification.

Tool surface (v0.1):

- `sysml_validate` — schema-check structured requirements against the `lego` subset of SysML v2.
- `spike_deploy` — push generated MicroPython to the SPIKE Prime hub over Bluetooth.
- `spike_run` — execute a deployed program and stream sensor telemetry.
- `test_eval` — score a run against the requirement it implements.

See [`docs/architecture.md`](docs/architecture.md) for the current sketch, and [`docs/wire_contract.md`](docs/wire_contract.md) for the telemetry wire format and requirements model schema.

For interactive, conversational hardware control, the `spike-prime-mcp` server exposes `flash_program`, `run_program`, and `get_telemetry` over MCP — the same seam that backs the control arm of the Evaluation comparison below. See [`spike_prime_mcp/README.md`](spike_prime_mcp/README.md).

The fixed unit-model registry lives in [`models/`](models/): `rover_common` (shared value types and the actuation-chain latency), `m1_motor_to_rover_speed` (the motor→speed characterization), and the two safety models `m2_collision_stop` (R-COL-1) and `m3_fall_stop` (R-FALL-1). These are drafted but not yet grammar-validated.

## Evaluation: structured vs. zero-shot

The point of the structured pipeline is a claim — that systems-engineering rigor buys you something before you let expensive equipment loose — and a claim like that is worth *demonstrating*, not asserting. So the project is framed as a two-arm comparison:

- **Control (zero-shot):** a free-text request handed to Claude with only the `spike-prime-mcp` tools (`flash_program` → `run_program` → `get_telemetry`). No SysML model, no gates — Claude writes code, runs it, reports back.
- **Treatment (structured):** the requirements → unit-model → calibration → verification pipeline above, which drives the hardware through the in-process tool path (`spike_deploy` / `spike_run`, with `spiketelem.py` over the shared `_runtime`).

For the cleanest head-to-head, both arms can be run through the same MCP seam, so the comparison isolates the governance layer as its only variable. Whether to route the structured arm's hardware steps through the MCP — rather than the in-process path it uses today, which the calibration loop's live plotting depends on — is a deliberate design choice still to be settled. Two things get measured either way: **outcome** — does the rover reach the safe-and-fast operating point (this discriminates only when the stopping margin is thin) — and **provenance** — can you produce an auditable argument that it will stop *before* it runs. The second is the durable claim: better models may close the outcome gap, but auditability doesn't come for free. The comparison is also run across Claude versions, to separate "competence scales" from "scaffolding still earns its place."

Either way, `spike-prime-mcp` is load-bearing rather than a demo: it is the apparatus for the control arm, and the candidate shared seam for a controlled head-to-head.

## Setup

Requires Python 3.10+, and for hardware runs a SPIKE Prime hub on Pybricks
firmware. Install the dependencies:

```bash
pip install pybricksdev matplotlib mcp
```

- `pybricksdev` — BLE communication with the hub (deploy + run).
- `matplotlib` — live telemetry plots in `spiketelem.py`. Required unless you
  pass `--no-plot`.
- `mcp` — only needed for the `spike_prime_mcp` server (see
  [`spike_prime_mcp/README.md`](spike_prime_mcp/README.md)).

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

A live plot window opens during `run` and `demo`, one panel per sensor named in
a requirement, with each requirement's pass band shaded. Add `--no-plot` to skip
it (no matplotlib needed), or `--snapshot out.png` on `demo` to render headless.

`spiketelem.py` is a developer cockpit on top of the tool surface; the orchestrator and draft agent call the `tools/` functions directly.

## Status

Implementation v0.1. (Docs may carry their own version — e.g. `docs/architecture.md` is at doc-v0.2, describing the full intended pipeline ahead of the build.) Tool surface implemented; the evaluator-optimizer right-half (deploy → run → eval) runs end-to-end against hardware via `spiketelem.py` and via the `spike-prime-mcp` server. Orchestrator-workers left-half is in prompts only. The seed unit models in `models/` are drafted but not yet grammar-validated.

### Known issues

- **`reaches` crossing precision.** `test_eval` scores `reaches` by attainment-or-crossing (a sign change in `value - target` between samples), which fixes the prior exact-float-equality bug. Sub-sample crossing time is not interpolated; see the TODO in `tools/test_eval.py`.

## License

MIT. See [LICENSE](LICENSE).
