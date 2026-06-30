# Wire Contract

> **Status:** v0.1 — first canonical interface document. Pinned by the v0.1
> tool implementations and the example artifacts in `spike_prime_direct/`.

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

Every requirement has three required fields, plus a verifiability rule:

- `id` (str): a unique, stable identifier. House convention is
  `R-<CONCERN>-<n>` (e.g. `R-COL-1`), where the prefix is a human-readable
  concern tag and carries no validated meaning — the type lives in `type`,
  not the id. Only uniqueness is enforced; the format is a documented
  convention, not a validator rule.
- `type` (str): one of `functional`, `behavioral`, `interface`,
  `constraint`. This field is the sole source of a requirement's type; it is
  not encoded in the id.
- `text` (str): the requirement, written in the form the relevant worker
  produces (see `docs/system_prompts.md`).

A requirement must also be **verifiable**: it carries either a `pass_criteria`
object (§2.1) or a `verified_by` (§2.3) naming the requirement that grades it.
Most requirements have `pass_criteria`; an objective checked only via a
stricter sibling constraint uses `verified_by` instead. A requirement with
neither is rejected.

Optional fields:

- `source` (str): the substring of the input spec this requirement was
  derived from. Carried through for traceability.
- Traceability-spine fields (`unit_model`, `depends_on_parts`,
  `implemented_by`, `depends_on_params`, `verified_by`) and the top-level
  `parts` block — see §2.3.

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
is not used by `test_eval`. The channel's canonical unit (§2.2), not this
field, is what `value` is interpreted in.

**Written at composition, not by the workers.** `pass_criteria` binds to a
`sensor` channel that exists only once unit models are selected and parts are
wired, so it is authored at the composition stage — not by the extracting
worker, which emits only requirement semantics (`text`, `type`, `source`). A
freshly-merged requirements model therefore carries no `pass_criteria`; it
appears by the composed stage, which is why the pass_criteria-or-`verified_by`
rule (§2) is a composed-stage check rather than a decomposition one. Constraint
requirements often take a *negative* criterion here — the absence of a
forbidden event — rather than a positive threshold.

Examples (drawn from `spike_prime_direct/requirements_example.json`):

```json
{"sensor": "distance_on_the_right", "op": ">", "value": 50.0, "unit": "mm"}
{"sensor": "reflection",            "op": ">", "value": 20,    "unit": "%"}
```

Operators beyond this set (time-windowed in-band, derived/cross-signal,
phase-scoped) are deliberately deferred. When you need them, extend the
grammar here first, then the evaluator.

### 2.2 Channel units (canonical)

Every channel has one canonical unit. The telemetry value (§1) and the
`pass_criteria.value` that grades it (§2.1) are BOTH in that unit, so
`test_eval` compares them raw and performs no conversion. The rule, stated
once: **a channel emits in its native sensor unit, and any `pass_criteria`
against it uses that same unit.** Distance sensors report mm, so distance
channels and their criteria are in mm.

| channel        | canonical unit  | notes                                |
| -------------- | --------------- | ------------------------------------ |
| `clearance_mm` | mm              | forward clearance = min(left, right) |
| `distance_*`   | mm              | raw per-sensor distance              |
| `reflection`   | percent (0–100) | dimensionless reflectance            |
| `speed_mps`    | m/s             | ground speed, signed (+ = forward)   |

The SysML models are SI (metres, seconds, m/s**2), so SI→sensor-unit is a
real conversion boundary. It lives in exactly two places, and there is no
single shared converter because they run in different runtimes:

- **host-side**, in `tools/units.py` (the machine-readable mirror of this
  table), used by composition when it emits a `pass_criteria.value` from an
  SI model parameter — e.g. a 0.040 m collision margin against `clearance_mm`
  becomes `40`;
- **on-hub**, in each mission's labelled unit-boundary block, where SI model
  parameters become sensor-unit working constants before the control loop —
  e.g. `threshold_m * 1000 → threshold_mm`.

This table is the declaration both sides convert toward; keep it and
`tools/units.py` in sync.

### 2.3 Traceability-spine fields

These five fields wire each requirement into the rest of the system — the
SysML model it was realised against, the hardware parts it touches, the
program that implements it, the model parameters it binds, and (for
objectives that are not independently graded) the requirement that verifies
it. They are the spine that lets a telemetry failure be traced back to a
specific spec line.

| field               | type        | join it makes                                             |
| ------------------- | ----------- | --------------------------------------------------------- |
| `unit_model`        | str         | the registry model this requirement was realised against  |
| `depends_on_parts`  | list of str | `part_id`s (in the top-level `parts` block) it exercises   |
| `implemented_by`    | str \| null | the program/example that implements it                     |
| `depends_on_params` | list of obj | model parameters it binds (`{param, model, bound_by}`)     |
| `verified_by`       | str \| null | another requirement id that grades this one indirectly     |

A top-level `parts` list accompanies them: each entry is
`{part_id, kind, ports, lego_element, emits}`, with unique `part_id`s.
`depends_on_parts` references resolve against this block.

**Optional about presence, strict about correctness.** The spine fills in
progressively as a requirement moves through the pipeline — it does not all
exist at decomposition time — so every field above is *optional* to
`sysml_validate`: a model missing them is still well-formed. But whenever a
field is present it is integrity-checked, and three rules are enforced:

1. Every `depends_on_parts` entry must name a `part_id` defined in the
   top-level `parts` block (no dangling part references).
2. `verified_by` must name an existing requirement id, and a requirement may
   not verify itself (no dangling or circular verification).
3. Every requirement must be verifiable: a non-null `pass_criteria` **or** a
   `verified_by` (the rule stated in §2). Neither is rejected.

**Presence is a separate, staged question.** Whether the spine is *complete* —
not merely well-formed — depends on how far the model has travelled, so it is
answered by `check_trace_complete(model, stage=...)`, not by `sysml_validate`.
This keeps "valid" meaning strictly "well-formed," never silently "well-formed
*and* fully traced." The stage map:

| stage         | additionally required on every requirement                 |
| ------------- | ---------------------------------------------------------- |
| decomposition | nothing beyond the core object — the spine is not wired yet |
| composed      | `unit_model` and a non-empty `depends_on_parts`            |
| verified      | `implemented_by` and pass_criteria/emit coverage (deferred) |

`sysml_validate` runs at the **composed** stage (after composition, before
code), so the pipeline pairs it with `check_trace_complete(model,
stage="composed")` there. The `verified` stage is defined but not implemented
in v0.1; its emit-coverage half is the §3 agreement checked against live
`parts[].emits`.

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
end-of-file). See `spike_prime_direct/runs/run.jsonl` for a captured trace.