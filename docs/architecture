# Architecture

> **Status:** Sketch — Week 1. initial sketch

## Pattern selection

Spike SysML uses two patterns from [*Building Effective Agents*](https://www.anthropic.com/research/building-effective-agents):

1. **Orchestrator-workers** — for requirements decomposition.
2. **Evaluator-optimizer** — for hardware-in-the-loop code generation.

Why these two: requirements decomposition is naturally parallel (functional, behavioral, interface, and constraint requirements can be extracted independently), and the hardware loop has a natural critic — the robot either does the thing or it doesn't. The two other major patterns from the post are less interesting here: prompt chaining is too linear for the parallel decomposition step, and routing implies a choice between specialists where this system has only one path.

## Flow

```mermaid
flowchart TD
    A[free-text spec] --> B[orchestrator]
    B --> W1[worker: functional]
    B --> W2[worker: behavioral]
    B --> W3[worker: interface]
    B --> W4[worker: constraint]
    W1 --> M[merge → SysML v2 model]
    W2 --> M
    W3 --> M
    W4 --> M
    M --> V[sysml_validate]
    V --> D[draft agent]
    D --> DEP[spike_deploy]
    DEP --> H[SPIKE Prime hub]
    H --> R[spike_run]
    R --> E[test_eval]
    E -->|pass| DONE[done]
    E -->|fail| D
```

## Tool surface

| Tool | Purpose | Status |
|------|---------|--------|
| `sysml_validate` | Schema-check structured requirements against SysML v2. | Stub |
| `spike_deploy` | Push generated MicroPython to the SPIKE Prime hub. | Stub |
| `spike_run` | Execute a test program and stream sensor telemetry. | Stub |
| `test_eval` | Score a run against the requirement it implements. | Stub |

## Open questions

- **SysML v2 schema source.** The OMG draft, or a constrained subset suitable for the LEGO domain? Likely the latter — full SysML v2 is overkill for SPIKE Prime, and a subset is easier to validate against.
- **SPIKE communication.** USB serial (Pybricks-style) or Bluetooth? USB is more reliable for an evaluator loop; Bluetooth is more operational.
- **Iteration budget on the evaluator-optimizer loop.** Hard cap (e.g., 5 retries) or cost-aware? A hard cap is simpler; cost-aware is more honest about the production-shaped constraint.
- **Requirements-to-test traceability.** A `req_id` field threaded through every artifact (requirement → generated code → test result) is the obvious answer.
- **Where does the human stay in the loop?** The evaluator is hardware, but a human still has to write the original spec and ultimately accept the result. Worth being explicit about which decisions stay with the human and which are agent-owned.
