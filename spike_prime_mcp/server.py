#!/usr/bin/env python3
"""spike-prime-mcp — MCP server exposing the SPIKE Prime hardware seam.

Three tools over stdio, for Claude Desktop or any MCP client:

- ``flash_program``  — compile + download MicroPython to the hub (no execution).
- ``run_program``    — execute the deployed program; persist the telemetry
  trace to ``runs/<run_id>.jsonl``; return run metadata only.
- ``get_telemetry``  — read a persisted trace back at ``summary`` (default),
  ``downsampled``, or ``full`` detail.

Design notes (see ``docs/architecture.md``, pipeline step 7):

- The MCP surface is the *hardware seam only*. Host-side pipeline logic
  (``sysml_validate``, ``test_eval``) deliberately stays out of it.
- Per-call BLE lifecycle: every tool call scans, connects, works, and
  disconnects. The server holds no connection state, so a hub that slept,
  rebooted, or wandered off between calls produces a clean, retryable error
  instead of a stale-connection failure.
- ``run_program`` returns metadata only (run id, status, duration,
  per-sensor record counts). Traces persist to disk and are retrieved via
  ``get_telemetry`` with token-efficient defaults — the response-format
  pattern from *Writing Effective Tools for AI Agents*.
- This module composes the async primitives in ``tools/_runtime.py``
  directly. The sync wrappers (``tools.spike_deploy`` / ``tools.spike_run``)
  call ``asyncio.run()``, which cannot be invoked from inside the MCP
  server's already-running event loop.
- stdout is the MCP transport. All diagnostics go to stderr, which Claude
  Desktop captures in ``logs/mcp-server-spike-prime.log``.

Wire contract for traces: ``docs/wire_contract.md``.
"""
from __future__ import annotations

import asyncio
import json
import math
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional

# Self-locate the repo root so this file works both as a plain script
# (Claude Desktop config points straight at server.py) and as a module
# (``python -m spike_prime_mcp``), regardless of the launcher's cwd.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from tools._runtime import (  # noqa: E402
    CaptureBuffer,
    ConsoleSink,
    JsonlLogger,
    StdoutFramer,
    TelemetryBus,
    connect_hub,
    deploy_program,
)
from tools._runtime import run_program as _rt_run_program  # noqa: E402

RUNS_DIR = REPO_ROOT / "runs"

# Response-shaping caps. Fixed rather than parameterized in v0.1 — sensible
# defaults over knobs; the truncation notices tell the agent how to narrow.
DOWNSAMPLE_POINTS_PER_SENSOR = 100
FULL_EVENT_CAP = 500
STDOUT_TAIL_LINES = 20
SUMMARY_DISTINCT_CAP = 5

# Reliability budgets (v0.1.1). Every hardware tool call is wrapped in an
# overall asyncio.wait_for so the server ALWAYS answers the MCP request —
# pybricksdev's connect/download awaits have no timeouts of their own, and
# an un-timeboxed BLE stall otherwise wedges the whole server (observed on
# Windows after an aborted connection).
FLASH_TIMEOUT_S = 45.0     # scan (with retry) + connect + compile/download
RUN_GRACE_S = 30.0         # added to timeout_seconds for the whole run call
SCAN_RETRY_DELAY_S = 2.0   # hubs re-advertise a beat after a disconnect
CLEANUP_TIMEOUT_S = 5.0    # best-effort stop/disconnect must not hang either

mcp = FastMCP("spike-prime")


# --------------------------------------------------------------------------- #
# Run-store helpers                                                           #
# --------------------------------------------------------------------------- #
def _new_run_id() -> str:
    """Timestamp-based id, de-duplicated if two runs start in one second."""
    base = "run-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id, n = base, 2
    while (RUNS_DIR / f"{run_id}.jsonl").exists():
        run_id = f"{base}-{n}"
        n += 1
    return run_id


def _meta_path(run_id: str) -> Path:
    return RUNS_DIR / f"{run_id}.meta.json"


def _trace_path(run_id: str) -> Path:
    return RUNS_DIR / f"{run_id}.jsonl"


def _resolve_run_id(run_id: str) -> Optional[str]:
    """Resolve ``"latest"`` to the most recent trace on disk; otherwise
    return ``run_id`` if its trace exists, else ``None``."""
    if run_id == "latest":
        traces = sorted(
            RUNS_DIR.glob("run-*.jsonl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return traces[0].stem if traces else None
    return run_id if _trace_path(run_id).exists() else None


def _known_runs(limit: int = 5) -> list[str]:
    if not RUNS_DIR.exists():
        return []
    traces = sorted(
        RUNS_DIR.glob("run-*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return [p.stem for p in traces[:limit]]


def _load_events(run_id: str) -> list[dict]:
    events: list[dict] = []
    with open(_trace_path(run_id), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "sensor" in ev and "value" in ev and "timestamp_ms" in ev:
                events.append(ev)
    events.sort(key=lambda e: e["timestamp_ms"])
    return events


def _load_meta(run_id: str) -> dict:
    p = _meta_path(run_id)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _is_number(v: Any) -> bool:
    # bool is an int subclass; treat it as categorical, not numeric.
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _apply_filters(
    events: list[dict],
    sensors: Optional[list[str]],
    time_window: Optional[list[float]],
) -> list[dict]:
    if sensors:
        wanted = set(sensors)
        events = [e for e in events if e["sensor"] in wanted]
    if time_window:
        t0, t1 = time_window[0], time_window[1]
        events = [e for e in events if t0 <= e["timestamp_ms"] <= t1]
    return events


# --------------------------------------------------------------------------- #
# Telemetry shaping (summary / downsampled / full)                            #
# --------------------------------------------------------------------------- #
def _summarize(events: list[dict]) -> dict:
    """Per-sensor statistics. Constant-size output regardless of trace length."""
    by_sensor: dict[str, list[dict]] = {}
    for e in events:
        by_sensor.setdefault(e["sensor"], []).append(e)
    out: dict[str, dict] = {}
    for sensor, evs in by_sensor.items():
        entry: dict[str, Any] = {
            "count": len(evs),
            "first_ms": evs[0]["timestamp_ms"],
            "last_ms": evs[-1]["timestamp_ms"],
        }
        numeric = [(e["timestamp_ms"], e["value"]) for e in evs if _is_number(e["value"])]
        if numeric:
            t_min, v_min = min(numeric, key=lambda tv: tv[1])
            t_max, v_max = max(numeric, key=lambda tv: tv[1])
            entry.update(
                min=v_min,
                t_at_min_ms=t_min,
                max=v_max,
                t_at_max_ms=t_max,
                mean=round(sum(v for _, v in numeric) / len(numeric), 6),
            )
        non_numeric = [e["value"] for e in evs if not _is_number(e["value"])]
        if non_numeric:
            distinct: list[Any] = []
            for v in non_numeric:
                if v not in distinct:
                    distinct.append(v)
                if len(distinct) > SUMMARY_DISTINCT_CAP:
                    break
            entry["distinct_values"] = distinct[:SUMMARY_DISTINCT_CAP]
        out[sensor] = entry
    return out


def _downsample(events: list[dict]) -> dict:
    """Time-bucketed, columnar series per sensor — numeric values are
    bucket-averaged, categorical values take the bucket's last sample."""
    by_sensor: dict[str, list[dict]] = {}
    for e in events:
        by_sensor.setdefault(e["sensor"], []).append(e)
    out: dict[str, dict] = {}
    for sensor, evs in by_sensor.items():
        n = len(evs)
        if n <= DOWNSAMPLE_POINTS_PER_SENSOR:
            out[sensor] = {
                "t_ms": [e["timestamp_ms"] for e in evs],
                "value": [e["value"] for e in evs],
                "points": n,
                "source_events": n,
                "bucket_ms": 0,
            }
            continue
        t0 = evs[0]["timestamp_ms"]
        t1 = evs[-1]["timestamp_ms"]
        span = max(t1 - t0, 1)
        bucket_ms = math.ceil(span / DOWNSAMPLE_POINTS_PER_SENSOR)
        buckets: dict[int, list[dict]] = {}
        for e in evs:
            buckets.setdefault(int((e["timestamp_ms"] - t0) // bucket_ms), []).append(e)
        t_out: list[float] = []
        v_out: list[Any] = []
        for b in sorted(buckets):
            bevs = buckets[b]
            t_out.append(t0 + b * bucket_ms + bucket_ms // 2)
            nums = [e["value"] for e in bevs if _is_number(e["value"])]
            if nums:
                v_out.append(round(sum(nums) / len(nums), 6))
            else:
                v_out.append(bevs[-1]["value"])
        out[sensor] = {
            "t_ms": t_out,
            "value": v_out,
            "points": len(t_out),
            "source_events": n,
            "bucket_ms": bucket_ms,
        }
    return out


def _run_envelope(run_id: str, meta: dict) -> dict:
    env = {"run_id": run_id}
    for key in ("completed", "duration_seconds", "created_at", "slot", "hub_id"):
        if key in meta:
            env[key] = meta[key]
    return env


# --------------------------------------------------------------------------- #
# Hardware-call reliability helpers (v0.1.1)                                   #
# --------------------------------------------------------------------------- #
class _HubHolder:
    """Carries the live hub reference out of a wait_for-wrapped inner task so
    the cleanup path can still reach it after a cancellation."""

    def __init__(self) -> None:
        self.hub = None


async def _connect_with_retry(hub_id: Optional[str], holder: _HubHolder):
    """connect_hub with one scan retry and an actionable no-hub message.

    Hubs take a beat to resume advertising after a disconnect, and Windows
    BLE is slow to notice — a single 10 s scan window can miss a hub that is
    sitting right there. One retry after a short pause covers that gap."""
    last: Optional[BaseException] = None
    for attempt in (1, 2):
        try:
            hub, device = await connect_hub(hub_id=hub_id)
            holder.hub = hub
            return hub, device
        except (asyncio.TimeoutError, TimeoutError) as e:
            last = e
            if attempt == 1:
                await asyncio.sleep(SCAN_RETRY_DELAY_S)
    raise RuntimeError(
        "No Pybricks hub found after 2 scans. Check: hub powered on, running "
        "Pybricks firmware, and not connected to another app (Pybricks "
        "accepts one BLE client at a time)."
    ) from last


async def _safe_cleanup(holder: _HubHolder, stop_program: bool = False) -> None:
    """Best-effort, time-boxed stop/disconnect. Never raises, never hangs."""
    hub = holder.hub
    if hub is None:
        return
    if stop_program:
        try:
            await asyncio.wait_for(hub.stop_user_program(), CLEANUP_TIMEOUT_S)
        except Exception:
            pass
    try:
        await asyncio.wait_for(hub.disconnect(), CLEANUP_TIMEOUT_S)
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# MCP tools                                                                   #
# --------------------------------------------------------------------------- #
@mcp.tool()
async def flash_program(
    code: str,
    hub_id: Optional[str] = None,
    slot: int = 0,
) -> dict:
    """Compile and download MicroPython source to the SPIKE Prime hub.

    Use this to put a program on the hub. The program is NOT executed —
    call run_program afterwards. The normal sequence is:
    flash_program -> run_program -> get_telemetry.

    The program must follow the telemetry wire contract
    (docs/wire_contract.md): emit one JSON line per telemetry event
    {"timestamp_ms": <int, hub clock>, "sensor": "<name>", "value": <scalar>}
    and end with the flush sentinel {"event": "end"}. Without the sentinel,
    the last samples of a run can be lost to BLE buffering.

    Connects to the hub for this call only and disconnects afterwards. The
    whole call is time-boxed (~45 s): a stalled BLE connect or transfer
    returns a structured error instead of hanging. The scan retries once. The
    flashed program stays resident on the hub while it remains powered; if
    run_program later reports no program, the hub power-cycled — re-flash.

    Args:
        code: MicroPython source for the Pybricks runtime on the hub. Must
            be syntactically valid; this tool does not lint or transform it.
        hub_id: BLE advertised name, only needed when more than one hub is
            powered on nearby. None selects the first Pybricks hub found.
        slot: Program slot (0-19). v0.1 accepts but does not route this —
            all deploys land in slot 0.

    Returns:
        deployed (bool), slot (int), hub_id (str | None — the BLE name
        actually connected to), error (str | None). On error: check the hub
        is powered on, running Pybricks firmware, and not connected to
        another app (Pybricks allows one BLE client at a time), then retry.
    """
    holder = _HubHolder()

    async def _do() -> dict:
        hub, device = await _connect_with_retry(hub_id, holder)
        await deploy_program(hub, code, slot=slot)
        return {
            "deployed": True,
            "slot": slot,
            "hub_id": getattr(device, "name", None) or hub_id,
            "error": None,
        }

    try:
        return await asyncio.wait_for(_do(), timeout=FLASH_TIMEOUT_S)
    except asyncio.TimeoutError:
        return {
            "deployed": False,
            "slot": slot,
            "hub_id": hub_id,
            "error": (
                f"Hardware operation timed out after {FLASH_TIMEOUT_S:.0f} s — "
                "the hub was likely found but the BLE connect or transfer "
                "stalled. Power-cycle the hub and retry."
            ),
        }
    except Exception as e:  # noqa: BLE001 — boundary tool, report don't raise
        return {
            "deployed": False,
            "slot": slot,
            "hub_id": hub_id,
            "error": f"{type(e).__name__}: {e}",
        }
    finally:
        await _safe_cleanup(holder)


@mcp.tool()
async def run_program(
    timeout_seconds: float = 30.0,
    hub_id: Optional[str] = None,
    slot: int = 0,
) -> dict:
    """Execute the program last flashed to the SPIKE Prime hub.

    Use after a successful flash_program. Blocks until the program ends on
    its own or timeout_seconds elapses (the host then stops it). Telemetry
    is captured for the whole run and persisted to runs/<run_id>.jsonl —
    it is deliberately NOT returned here. To read it, call get_telemetry
    with the returned run_id (start with the default summary format).

    The per-sensor record counts below tell you what is available to
    retrieve. A run that completes but violates a requirement is NOT an
    error here — grading happens downstream (test_eval, host-side).

    Args:
        timeout_seconds: Max runtime before the host stops the program.
            Size it to the mission: a calibration sweep needs more than a
            single stop test. Default 30.
        hub_id: BLE advertised name; see flash_program.
        slot: Program slot to run. v0.1 runs whatever was last flashed.

    Returns:
        run_id (str — pass to get_telemetry; "latest" also works),
        completed (bool — False means timeout or disconnect),
        duration_seconds (float),
        sensors (dict sensor -> record count),
        total_events (int),
        stdout_tail (list[str] — last lines of non-telemetry hub stdout;
        a MicroPython traceback here means the program crashed on-hub),
        trace_file (str, repo-relative), error (str | None — only for
        runs that failed to start).
    """
    holder = _HubHolder()
    bus = TelemetryBus()
    framer = StdoutFramer(bus)
    capture = bus.add(CaptureBuffer())
    bus.add(ConsoleSink())  # hub prints/tracebacks -> stderr -> CD server log
    run_id: Optional[str] = None
    ok = False

    def _counts() -> dict[str, int]:
        c: dict[str, int] = {}
        for ev in capture.events:
            c[ev["sensor"]] = c.get(ev["sensor"], 0) + 1
        return c

    def _write_meta(completed: bool, duration: float, hub_name) -> None:
        if run_id is None:
            return
        meta = {
            "run_id": run_id,
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "completed": completed,
            "duration_seconds": round(duration, 3),
            "slot": slot,
            "hub_id": hub_name,
            "sensors": _counts(),
            "total_events": len(capture.events),
            "end_sentinel_seen": capture.ended,
            "stdout_lines": capture.stdout_lines,
        }
        try:
            _meta_path(run_id).write_text(json.dumps(meta, indent=1), encoding="utf-8")
        except OSError:
            pass

    async def _do() -> dict:
        nonlocal run_id
        hub, device = await _connect_with_retry(hub_id, holder)
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        run_id = _new_run_id()
        bus.add(JsonlLogger(str(_trace_path(run_id))))
        summary = await _rt_run_program(
            hub, bus, framer, timeout_seconds=timeout_seconds, plot=None
        )
        hub_name = getattr(device, "name", None) or hub_id
        _write_meta(summary["completed"], summary["duration_seconds"], hub_name)
        return {
            "run_id": run_id,
            "completed": summary["completed"],
            "duration_seconds": round(summary["duration_seconds"], 3),
            "sensors": _counts(),
            "total_events": len(capture.events),
            "stdout_tail": capture.stdout_lines[-STDOUT_TAIL_LINES:],
            "trace_file": f"runs/{run_id}.jsonl",
            "error": None,
        }

    try:
        result = await asyncio.wait_for(_do(), timeout=timeout_seconds + RUN_GRACE_S)
        ok = True
        return result
    except asyncio.TimeoutError:
        _write_meta(False, timeout_seconds + RUN_GRACE_S, hub_id)
        return {
            "run_id": run_id,
            "completed": False,
            "duration_seconds": 0.0,
            "sensors": _counts(),
            "total_events": len(capture.events),
            "stdout_tail": capture.stdout_lines[-STDOUT_TAIL_LINES:],
            "trace_file": f"runs/{run_id}.jsonl" if run_id else None,
            "error": (
                f"Hardware call exceeded its overall budget "
                f"({timeout_seconds:.0f} s run + {RUN_GRACE_S:.0f} s grace) — "
                "a BLE operation stalled. The program was sent a stop; any "
                "captured telemetry persisted. Power-cycle the hub if the "
                "next call also fails."
            ),
        }
    except Exception as e:  # noqa: BLE001
        return {
            "run_id": run_id,
            "completed": False,
            "duration_seconds": 0.0,
            "sensors": _counts(),
            "total_events": len(capture.events),
            "stdout_tail": capture.stdout_lines[-STDOUT_TAIL_LINES:],
            "trace_file": f"runs/{run_id}.jsonl" if run_id else None,
            "error": f"{type(e).__name__}: {e}",
        }
    finally:
        await _safe_cleanup(holder, stop_program=not ok)


@mcp.tool()
async def get_telemetry(
    run_id: str,
    response_format: Literal["summary", "downsampled", "full"] = "summary",
    sensors: Optional[list[str]] = None,
    time_window: Optional[list[float]] = None,
) -> dict:
    """Read back the telemetry trace of a past run, at chosen detail.

    Use after run_program. Traces persist on disk, so you can call this
    repeatedly against one run — summary first, then drill down — without
    re-running hardware. Timestamps are hub-clock milliseconds throughout
    (docs/wire_contract.md).

    Formats:
    - "summary" (default): per-sensor count, first/last timestamps, and for
      numeric channels min/max with their timestamps and mean. Constant
      size; answers most questions. Start here.
    - "downsampled": per-sensor columnar series {t_ms: [...], value: [...]},
      time-bucketed to at most 100 points per sensor (numeric values
      bucket-averaged, bucket_ms reported). Use to see the shape of a
      curve or fit a trend.
    - "full": raw events. Requires sensors and/or time_window to be set,
      and returns at most 500 events with a truncation notice — narrow the
      window to get finer detail. Use only for precise inspection of a
      specific moment.

    Args:
        run_id: The id returned by run_program, or "latest" for the most
            recent run on disk.
        response_format: "summary" | "downsampled" | "full".
        sensors: Optional channel-name filter, e.g. ["distance_mm"].
            Applies to every format.
        time_window: Optional [start_ms, end_ms] in hub-clock milliseconds.
            Applies to every format.

    Returns:
        A dict with run (id/status/duration), filters_applied, and one of:
        sensors (summary stats), series (downsampled columnar), or events
        (full, with returned/total_matching/truncated). On unknown run_id,
        an error plus the most recent known run ids.
    """
    resolved = _resolve_run_id(run_id)
    if resolved is None:
        return {
            "error": f"No trace found for run_id {run_id!r}.",
            "known_runs": _known_runs(),
            "hint": "Pass a run_id returned by run_program, or \"latest\".",
        }
    if time_window is not None and len(time_window) != 2:
        return {"error": "time_window must be [start_ms, end_ms]."}

    meta = _load_meta(resolved)
    events = _apply_filters(_load_events(resolved), sensors, time_window)
    out: dict[str, Any] = {
        "run": _run_envelope(resolved, meta),
        "response_format": response_format,
        "filters_applied": {
            "sensors": sensors,
            "time_window": time_window,
        },
        "matching_events": len(events),
    }

    if response_format == "summary":
        out["sensors"] = _summarize(events)
        return out

    if response_format == "downsampled":
        out["series"] = _downsample(events)
        return out

    if response_format == "full":
        if not sensors and not time_window:
            return {
                "error": "full requires a sensors and/or time_window filter.",
                "hint": (
                    "Call with response_format=\"summary\" first, then narrow "
                    "to the sensor and window you need."
                ),
                "run": _run_envelope(resolved, meta),
            }
        truncated = len(events) > FULL_EVENT_CAP
        out["events"] = events[:FULL_EVENT_CAP]
        out["returned"] = min(len(events), FULL_EVENT_CAP)
        out["truncated"] = truncated
        if truncated:
            out["note"] = (
                f"Trace has {len(events)} matching events; returned the "
                f"first {FULL_EVENT_CAP}. Narrow time_window for the rest."
            )
        return out

    return {"error": f"Unknown response_format {response_format!r}."}


# --------------------------------------------------------------------------- #
# Entry point                                                                 #
# --------------------------------------------------------------------------- #
def main() -> None:
    print(
        f"spike-prime-mcp: repo root {REPO_ROOT}, runs dir {RUNS_DIR}",
        file=sys.stderr,
    )
    mcp.run()  # stdio transport


if __name__ == "__main__":
    main()