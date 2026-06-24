# Spike SysML

> AI-assisted, requirements-to-hardware test pipeline and feedback loop via SysML v2, demonstrated on LEGO SPIKE Prime.

Spike SysML is a multi-agent system that takes a free-text engineering specification, decomposes it into structured SysML v2 requirements, generates control code for the LEGO SPIKE Prime hub, runs that code on hardware, and feeds sensor results back to the agents for revision. The loop closes on a physical robot: the agent doesn't just produce plausible code — it produces code that has to make a real motor turn, a real sensor read, and a real test condition pass.

The choice of SPIKE Prime is deliberate. It's cheap enough to easily test, and constrained enough that the requirements-to-test loop is interesting rather than overwhelming.

## What this is not

Spike SysML is not a SPIKE programming environment and not a competitor to SPIKE App or Pybricks. It does not generate certifiable artifacts and does not perform V&V — it is a tooling layer that produces inputs to a human-led verification process, with LEGO hardware standing in for a target system. It is a scoped engineering project rather than a research program — though it deliberately measures itself against an unstructured baseline (see [Evaluation](#evaluation-structured-vs-freestyle)).

## Architecture

Built around two patterns from [*Building Effective Agents*](https://www.anthropic.com/research/building-effective-agents):

- **Orchestrator-workers** for requirements decomposition. A planning agent reads the spec and decomposes it top-down — STK→SYS→FUN→CMP, to the single-effector level — dispatching a worker per function area to derive the leaf requirements in parallel. Each is authored in EARS to INCOSE GtWR / ISO-29148 (the functional/behavioral/interface/constraint categories become requirement *types*), and the pass yields a TBD register and a visual requirement tree. A selection-and-composition step then assembles a SysML v2 model by composing generic relation templates and binding calibrated parameters.
- **Evaluator-optimizer** for code generation, with the hardware as the evaluator. A draft agent generates MicroPython for the SPIKE hub; the code runs on the robot; telemetry and pass/fail signals come back; the loop iterates until tests pass or a budget is hit.
- **Parameter calibration, verification, and human review gates.** Calibration binds both the model's free parameters and the requirement TBDs against the hardware; the structured arm then commits a **pre-run verification artifact** — an inspectable argument that the requirement holds with margin, *before* any integrated run — and tests it with a single confirmation run. A human reviews each test design before it runs, signs off that the calibration fit is *sufficient* before the expensive confirmation run, and accepts the *results* before the run is declared done — the costly steps are gated behind cheap verification.


Tool surface (v0.1):

- `sysml_validate` — schema-check structured requirements against the `lego` subset of SysML v2.
- `check_trace_complete` — confirm the traceability spine is present (not just well-formed) at the composed stage.
- `spike_deploy` — push generated MicroPython to the SPIKE Prime hub over Bluetooth.
- `spike_run` — execute a deployed program and stream sensor telemetry.
- `test_eval` — score a run against the requirement it implements.


See [`docs/architecture.md`](docs/architecture.md) for the current sketch, and [`docs/wire_contract.md`](docs/wire_contract.md) for the telemetry wire format and requirements model schema.

For interactive, conversational hardware control, the `spike-prime-mcp` server exposes `flash_program`, `run_program`, and `get_telemetry` over MCP — the shared hardware seam both arms of the Evaluation comparison below run through. See [`spike_prime_mcp/README.md`](spike_prime_mcp/README.md).

Rover-specific exemplar models live in [`models/`](models): `rover_common` (shared value types and the actuation-chain latency), `m1_motor_to_rover_speed` (the motor→speed characterization), and the two safety models `m2_collision_stop` (R-COL-1) and `m3_fall_stop` (R-FALL-1). They are reference for the generic template catalog the structured arm composes from, not the catalog itself. Each validates clean in Syside (the SysML v2 VSCode tooling); they are not yet validated through the in-pipeline grammar loop.

## Evaluation: structured vs. freestyle

The point of the structured pipeline is a claim — that systems-engineering rigor buys you something before you let expensive equipment loose — and a claim like that is worth *demonstrating*, not asserting. So the project is a two-arm comparison on one shared hardware seam, with the same model and configuration on both sides so the only variable is governance:

- **Freestyle (control):** a free-text request handed to the model with only the `spike-prime-mcp` tools (`flash_program` → `run_program` → `get_telemetry`). No model, no gates — it reasons, writes code, runs it, iterates.
- **Structured (treatment):** the requirements → effector-selection → unit-model → calibration → verification pipeline above.


**Both arms run through the same MCP seam** — this is settled — so the comparison isolates the governance layer. The task is a max-speed wall approach (full speed, stop as close to the wall as possible without contact), chosen because a *calibrated* stopping parameter is the difference between a tight safe stop and a contact, which makes the structured arm's speed-sweep calibration load-bearing. Each arm runs a counted characterization phase, then locks one program and runs it five times. The metrics are characterization cost, runs-to-first-success, no-contact rate over the five, the gap distribution, and outside-input count — plus the one thing only the structured arm produces: an inspectable argument, *before the run*, that the rover will stop within its envelope. (The structured arm commits that argument and tests it with a single confirmation run before locking the campaign.) Better models may close the outcome gap, but that argument doesn't come for free.

The full design — information diet, the two-phase protocol, the generation-vs-selection rule, and the metrics — is in [`docs/evaluation.md`](docs/evaluation.md), and the runnable instruments are in [`experiments/`](experiments): a shared `task_core.md` both arms prepend, plus the arm-specific `freestyle_arm_prompt.md` and `se_arm_prompt.md`. `spike-prime-mcp` is load-bearing rather than a demo: it is the shared seam both arms drive through.

## Setup

Requires Python 3.10+, and for hardware runs a SPIKE Prime hub on Pybricks
firmware. Install the dependencies:

```
pip install pybricksdev matplotlib mcp
```

- `pybricksdev` — BLE communication with the hub (deploy + run).
- `matplotlib` — live telemetry plots in `spiketelem.py`. Required unless you
pass `--no-plot`.
- `mcp` — only needed for the `spike_prime_mcp` server (see
[`spike_prime_mcp/README.md`](spike_prime_mcp/README.md)).


## Quickstart

```
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

Implementation v0.1. (Docs may carry their own version — e.g. `docs/architecture.md` is at doc-v0.4, describing the full intended pipeline ahead of the build.) Tool surface implemented; the evaluator-optimizer right-half (deploy → run → eval) runs end-to-end against hardware via `spiketelem.py` and via the `spike-prime-mcp` server. Orchestrator-workers left-half is in prompts only. The seed unit models in `models/` validate clean in Syside (the SysML v2 VSCode tooling), but are not yet validated through the in-pipeline grammar loop. The structured-vs-freestyle comparison that frames the project is specified in [`docs/evaluation.md`](docs/evaluation.md); the structured arm's left half — requirements derivation, effector selection, generic-template composition, and the calibration stage — is the next build.

### Known issues

- **`reaches` crossing precision.** `test_eval` scores `reaches` by attainment-or-crossing (a sign change in `value - target` between samples), which fixes the prior exact-float-equality bug. Sub-sample crossing time is not interpolated; see the TODO in `tools/test_eval.py`.


## License

MIT. See [LICENSE](LICENSE).