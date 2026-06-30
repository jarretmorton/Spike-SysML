#!/usr/bin/env python3
"""spiketelem — CLI front end to the Spike SysML tool surface.

Drives the evaluator-optimizer right-half of the architecture by hand: load
a requirements model, validate it, deploy a hub program, run it with
live-plotted telemetry, and grade each requirement via ``test_eval``.

This is a developer cockpit, not a tool the orchestrator calls. The
orchestrator and draft agent call the functions in ``tools/`` directly.

Wire contract and schemas: ``docs/wire_contract.md``.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import random
import sys

from tools import sysml_validate, test_eval
from tools._runtime import (
    CaptureBuffer,
    ConsoleSink,
    JsonlLogger,
    LivePlot,
    StdoutFramer,
    TelemetryBus,
    connect_hub,
    deploy_program,
    run_program,
)


# --------------------------------------------------------------------------- #
# Orchestration                                                               #
# --------------------------------------------------------------------------- #
async def _real_run(program_path: str, hub_id, model: dict,
                    bus: TelemetryBus, framer: StdoutFramer,
                    plot: LivePlot | None, timeout: float) -> dict:
    """Deploy + run a program on a real hub, returning a spike_run-shaped
    dict. Live plot (if any) runs concurrently with the run."""
    capture = next(s for s in bus._sinks if isinstance(s, CaptureBuffer))
    hub = None
    try:
        hub, _device = await connect_hub(hub_id=hub_id)
        with open(program_path, "r", encoding="utf-8") as f:
            code = f.read()
        await deploy_program(hub, code)
        summary = await run_program(
            hub, bus, framer, timeout_seconds=timeout, plot=plot
        )
        return {
            "completed": summary["completed"],
            "duration_seconds": summary["duration_seconds"],
            "telemetry": capture.events,
            "stdout": "\n".join(capture.stdout_lines),
            "error": None,
        }
    except Exception as e:
        return {
            "completed": False,
            "duration_seconds": 0.0,
            "telemetry": capture.events,
            "stdout": "\n".join(capture.stdout_lines),
            "error": f"{type(e).__name__}: {e}",
        }
    finally:
        if hub is not None:
            try: await hub.disconnect()
            except Exception: pass


def _synth_sample(t: int, end: int) -> dict:
    """One synthetic telemetry sample for the demo path, keyed by sensor.

    Emits the sensors named in ``examples/requirements_example.json``
    (``distance_on_the_right``, ``distance_on_the_left``, ``reflection``,
    plus ``speed_mps`` for fidelity with the hub program), shaped to stay
    inside their pass_criteria bands — distances above the 50 mm floor and
    reflection above the 20% floor — so a hardware-free demo shows a passing
    run with the live plots populated.

    ``t`` and ``end`` are milliseconds on the hub clock.
    """
    span = max(1, end)
    frac = t / span
    # gentle forward speed that eases in and tapers off (not gated by any req)
    speed = max(0.0, round(0.4 * math.sin(math.pi * frac) + random.uniform(-0.01, 0.01), 4))
    # right obstacle: closest approach mid-run, dips toward ~160 mm, never <50
    sig_r = max(1.0, span * 0.18)
    right = 600 - 440 * math.exp(-((t - span * 0.5) ** 2) / (2 * sig_r ** 2))
    right = round(max(120.0, right + random.uniform(-8, 8)), 1)
    # left obstacle: a later, shallower approach
    sig_l = max(1.0, span * 0.15)
    left = 700 - 380 * math.exp(-((t - span * 0.7) ** 2) / (2 * sig_l ** 2))
    left = round(max(140.0, left + random.uniform(-8, 8)), 1)
    # edge reflection: hovers ~45%, mild texture, stays above the 20% floor
    reflection = max(25.0, round(45 + 8 * math.sin(t / 700.0) + random.uniform(-2, 2), 1))
    return {
        "speed_mps": speed,
        "distance_on_the_right": right,
        "distance_on_the_left": left,
        "reflection": reflection,
    }


async def _demo_run(framer: StdoutFramer, bus: TelemetryBus,
                    plot: LivePlot | None, seconds: float) -> dict:
    """Synthesize a plausible rover telemetry trace (two distances, reflection,
    and speed) through the same framer/bus path so the full pipeline is
    exercised without hardware."""
    capture = next(s for s in bus._sinks if isinstance(s, CaptureBuffer))

    async def feeder():
        t, dt, end = 0, 50, int(seconds * 1000)
        while t <= end:
            for sensor, value in _synth_sample(t, end).items():
                line = json.dumps({"timestamp_ms": t, "sensor": sensor, "value": value})
                framer.feed((line + "\n").encode())
            t += dt
            await asyncio.sleep(dt / 1000.0)
        framer.feed(b'{"event":"end"}\n')

    task = asyncio.create_task(feeder())
    if plot is not None:
        await plot.render_until(task)
    await task
    return {
        "completed": True,
        "duration_seconds": seconds,
        "telemetry": capture.events,
        "stdout": "\n".join(capture.stdout_lines),
        "error": None,
    }


# --------------------------------------------------------------------------- #
# Reporting                                                                   #
# --------------------------------------------------------------------------- #
def _report(model: dict, run_result: dict) -> int:
    """Print a verdict table, return process exit code (0 = all pass)."""
    reqs = model.get("requirements", [])
    if not reqs:
        print(f"\ncaptured {len(run_result['telemetry'])} events "
              f"(no requirements to evaluate).")
        return 0
    print("\n=== requirement verdict ===")
    fails = 0
    for r in reqs:
        v = test_eval(run_result, r)
        mark = "PASS" if v["passed"] else "FAIL"
        if not v["passed"]:
            fails += 1
        print(f"  {mark}  {r['id']:<8} {r.get('type','?'):<11} {v['reasoning']}")
    print(f"\n{len(reqs) - fails}/{len(reqs)} requirements satisfied.")
    return 0 if fails == 0 else 1


# --------------------------------------------------------------------------- #
# CLI                                                                         #
# --------------------------------------------------------------------------- #
def _load_model(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _validate_or_die(model: dict) -> None:
    result = sysml_validate(model)
    for w in result["warnings"]:
        print(f"warn  {w['path']}: {w['message']}", file=sys.stderr)
    for e in result["errors"]:
        print(f"error {e['path']}: {e['message']}", file=sys.stderr)
    if not result["valid"]:
        print("requirements model failed validation; aborting.", file=sys.stderr)
        sys.exit(2)


def _build_pipeline(model: dict, args):
    bus = TelemetryBus()
    framer = StdoutFramer(bus)
    bus.add(ConsoleSink())
    bus.add(CaptureBuffer())
    if getattr(args, "log", None):
        bus.add(JsonlLogger(args.log))
    plot = None
    if not getattr(args, "no_plot", False):
        plot = LivePlot(model)
        bus.add(plot)
    return bus, framer, plot


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="spiketelem", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("run", help="deploy + run a program on the hub, then evaluate")
    pr.add_argument("program", help="path to the Pybricks .py program to run")
    pr.add_argument("requirements", help="path to the requirements model JSON")
    pr.add_argument("--name", dest="hub_id", help="hub BLE name (omit for first found)")
    pr.add_argument("--timeout", type=float, default=30.0)
    pr.add_argument("--log", help="write telemetry events to this JSONL file")
    pr.add_argument("--no-plot", action="store_true")

    pd = sub.add_parser("demo", help="synthesize telemetry without a hub")
    pd.add_argument("requirements", help="path to the requirements model JSON")
    pd.add_argument("--log")
    pd.add_argument("--no-plot", action="store_true")
    pd.add_argument("--seconds", type=float, default=15.0)
    pd.add_argument("--snapshot", help="headless: render a PNG instead of a live window")

    pv = sub.add_parser("validate", help="run sysml_validate on a requirements model")
    pv.add_argument("requirements")

    args = p.parse_args(argv)
    model = _load_model(args.requirements)

    if args.cmd == "validate":
        result = sysml_validate(model)
        print(json.dumps(result, indent=2))
        return 0 if result["valid"] else 2

    _validate_or_die(model)
    bus, framer, plot = _build_pipeline(model, args)

    if args.cmd == "run":
        run_result = asyncio.run(
            _real_run(args.program, args.hub_id, model, bus, framer, plot, args.timeout)
        )
    else:  # demo
        if getattr(args, "snapshot", None):
            import matplotlib
            matplotlib.use("Agg")
            plot = plot or LivePlot(model)
            if plot not in bus._sinks:
                bus.add(plot)
            # synchronous synthetic feed for headless render
            t, dt, end = 0, 50, int(args.seconds * 1000)
            while t <= end:
                for sensor, value in _synth_sample(t, end).items():
                    framer.feed((json.dumps({"timestamp_ms": t, "sensor": sensor,
                                              "value": value}) + "\n").encode())
                t += dt
            framer.feed(b'{"event":"end"}\n')
            capture = next(s for s in bus._sinks if isinstance(s, CaptureBuffer))
            run_result = {
                "completed": True,
                "duration_seconds": args.seconds,
                "telemetry": capture.events,
                "stdout": "\n".join(capture.stdout_lines),
                "error": None,
            }
            print("snapshot ->", plot.save_snapshot(args.snapshot))
        else:
            run_result = asyncio.run(_demo_run(framer, bus, plot, args.seconds))

    return _report(model, run_result)


if __name__ == "__main__":
    sys.exit(main())
