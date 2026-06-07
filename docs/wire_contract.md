# Wire Contract

> **Status:** v0.1 — first canonical interface document. Pinned by the v0.1
> tool implementations and the example artifacts in `examples/`.

This doc defines two contracts the orchestrator, draft agent, and tools all
build against:

1. The **hub-to-host telemetry wire format**, emitted by deployed programs
   and consumed by `spike_run`.
2. The **requirements model schema**, produced by the orchestrator-workers
   pipeline, validated by `sysml_validate`, and read by `test_eval`.

A future open question — the **signal-name agreement** between a deployed
program and the requirements it implements — is also covered here, since
its absence is currently the most common failure mode.

## 1. Telemetry wire format

Programs running on the hub emit one JSON object per line on stdout. Each
line is a **telemetry event** with exactly three fields:

```json
{"timestamp_ms": 1234, "sensor": "force_n", "value": 0.42}
```

- `timestamp_ms` (int): milliseconds from a hub-clock origin (typically the
  start of the program). Hub-side timestamps are mandatory. BLE is buffered
  and chunked, so host arrival times cannot validate anything time-bound.
- `sensor` (str): the name the program uses to identify this measurement.
  Sensors are not types — they are named channels the program emits. The
  signal-name agreement (§3) ties these to requirements.
- `value` (any JSON-serialisable scalar): the measurement. Numeric for the
  v0.1 operator grammar; categorical (string, bool) is reserved for future
  ops.

The program ends its run with a **flush sentinel** on its own line:

```json
{"event": "end"}
```

The sentinel is mandatory. Pybricks stdout is buffered, so without it a
run-to-completion capture can race the buffer drain and silently lose the
last few samples.

Any other stdout content — Python tracebacks, accidental `print` calls,
debug overlays like BlocklyPy's `plot:` lines — is routed to the run
result's `stdout` field unparsed. It is not telemetry.

### Why JSONL and not binary

JSONL is self-describing, human-readable, and trivially line-aligned across
BLE chunk boundaries. Binary `struct` framing is the optimisation reachable
once sample rate or signal count outgrows the channel. v0.1 is well below
that threshold.

## 2. Requirements model schema

The merged output of the orchestrator-workers pipeline is a single JSON
document of this shape:

```json
{
  "requirements": [ ... requirement objects ... ],
  "metadata": {
    "source_spec": "rover_test_v1.txt",
    "generated_at": "2026-05-31T00:00:00Z"
  }
}
```

`metadata` is informational; missing fields produce warnings, not errors.

### Requirement object

Every requirement has four required fields:

- `id` (str): `<TYPE>-###`. The prefix must agree with `type`.
- `type` (str): one of `functional`, `behavioral`, `interface`,
  `constraint`. Prefix convention is `FN`, `BH`, `IF`, `CN` respectively.
- `text` (str): the requirement, written in the form the relevant worker
  produces (see `docs/system_prompts.md`).
- `pass_criteria` (object): the machine-checkable condition (§2.1).

Optional fields:

- `source` (str): the substring of the input spec this requirement was
  derived from. Carried through for traceability.

Type-specific fields:

- `behavioral`: `states` (list), `transitions` (list of `{from, to, trigger}`).
- `interface`: `port` (str | null), `direction` (`input`/`output`/`bidirectional`),
  `signal_type` (str).
- `constraint`: `bound` (number | str, optional, informational).

### 2.1 `pass_criteria` operator grammar (v0.1)

`pass_criteria` is a small object with `sensor`, `op`, and op-dependent
fields. The v0.1 grammar:

| op           | required fields                         | semantics                                                                    |
| ------------ | --------------------------------------- | ---------------------------------------------------------------------------- |
| `<=` `<` `>=` `>` `==` `!=` | `sensor`, `value`         | every sample of `sensor` must satisfy the comparison against `value`.        |
| `in_range`   | `sensor`, at least one of `min`, `max`  | every sample of `sensor` must lie in `[min, max]` (open-ended where absent). |
| `reaches`    | `sensor`, `value`, `within_seconds`     | `sensor` must attain `value` at least once before `within_seconds` elapses.  |

Optional `unit` field is informational; it propagates to the live plot but
is not used by `test_eval`.

Examples (drawn from `examples/requirements_example.json`):

```json
{"sensor": "distance_on_the_right", "op": ">", "value": 50.0, "unit": "mm"}
{"sensor": "reflection",            "op": ">", "value": 20,    "unit": "%"}
```

Operators beyond this set (time-windowed in-band, derived/cross-signal,
phase-scoped) are deliberately deferred. When you need them, extend the
grammar here first, then the evaluator.

## 3. Signal-name agreement

Each `pass_criteria.sensor` names a channel the deployed program is
expected to emit. Mismatches between the requirements model and the
program (typos, untested requirements, untracked emits) are currently a
**runtime failure mode** — `test_eval` returns `passed=false` with
`sample_count: 0` and a hint, but no upstream tool catches it.

The intended fix is a pre-flight check in `sysml_validate` that takes both
the requirements model and the candidate program: every requirement's
`sensor` must appear in the program's emits, and every emit should be
covered by a requirement. This is tracked as an open question in
`docs/architecture.md`.

Until then, the convention is:

- Sensor names are lower-snake-case with a unit suffix where useful
  (`force_n`, `speed_mps`, `gyro_deg`, `color_1`).
- The draft agent generates emits to match exactly the sensors named in
  the requirements model it was given. No renaming, no aliasing.

## 4. Captured trace files

`spike_run` returns telemetry in memory as `run_result["telemetry"]`. The
`spiketelem` CLI also persists each run to a `.jsonl` file when `--log` is
passed. The file format is one telemetry event per line, in the same
schema as §1, without the `{"event":"end"}` sentinel (it's implicit in
end-of-file). See `examples/runs/run.jsonl` for a captured trace.
