"""Internal async runtime shared by ``spike_deploy`` and ``spike_run``.

Not part of the public tool surface. Provides:

- ``TelemetryBus`` and the ``Sink`` protocol — one source, many subscribers.
- ``StdoutFramer`` — reassembles BLE-chunked stdout bytes into JSON lines and
  emits canonical telemetry events ``{"timestamp_ms", "sensor", "value"}``.
- Concrete sinks: ``CaptureBuffer``, ``JsonlLogger``, ``ConsoleSink``,
  ``LivePlot`` (matplotlib, optional).
- ``connect_hub`` / ``deploy_program`` / ``run_program`` — async primitives
  the tool wrappers call.

The wire contract is documented in ``docs/wire_contract.md``.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from typing import Any, Optional, Protocol


# --------------------------------------------------------------------------- #
# Bus + sinks                                                                 #
# --------------------------------------------------------------------------- #
class Sink(Protocol):
    """A telemetry consumer. All methods are optional; default to no-ops via
    duck typing on the bus side."""

    def on_event(self, event: dict) -> None: ...
    def on_raw(self, line: str) -> None: ...
    def on_end(self) -> None: ...


class TelemetryBus:
    """Synchronous fan-out. Everything runs in one asyncio thread, so a plain
    callback list is enough — no locks, no cross-thread queue."""

    def __init__(self) -> None:
        self._sinks: list[Any] = []

    def add(self, sink: Any) -> Any:
        self._sinks.append(sink)
        return sink

    def event(self, ev: dict) -> None:
        for s in self._sinks:
            if hasattr(s, "on_event"):
                s.on_event(ev)

    def raw(self, line: str) -> None:
        for s in self._sinks:
            if hasattr(s, "on_raw"):
                s.on_raw(line)

    def end(self) -> None:
        for s in self._sinks:
            if hasattr(s, "on_end"):
                s.on_end()


# --------------------------------------------------------------------------- #
# Framer                                                                      #
# --------------------------------------------------------------------------- #
class StdoutFramer:
    """Reassembles the hub's BLE-chunked byte stream into JSON lines.

    Recognized line shapes:

    - ``{"timestamp_ms": <int>, "sensor": <str>, "value": <any>}`` — a
      telemetry event; routed to ``bus.event``.
    - ``{"event": "end"}`` — flush sentinel; routes to ``bus.end``.

    Any other stdout line (hub tracebacks, BlocklyPy ``plot:`` lines,
    accidental ``print`` calls) is routed to ``bus.raw`` and never parsed as
    telemetry.
    """

    def __init__(self, bus: TelemetryBus) -> None:
        self.bus = bus
        self._buf = bytearray()

    def feed(self, data: bytes) -> None:
        self._buf.extend(data)
        while True:
            nl = self._buf.find(b"\n")
            if nl < 0:
                break
            line = bytes(self._buf[:nl]).rstrip(b"\r")
            del self._buf[: nl + 1]
            self._dispatch(line.decode("utf-8", errors="replace"))

    def _dispatch(self, text: str) -> None:
        s = text.strip()
        if not s:
            return
        if not (s.startswith("{") and s.endswith("}")):
            self.bus.raw(s)
            return
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            self.bus.raw(s)
            return
        if obj.get("event") == "end":
            self.bus.end()
        elif "sensor" in obj and "value" in obj and "timestamp_ms" in obj:
            self.bus.event(obj)
        else:
            self.bus.raw(s)


# --------------------------------------------------------------------------- #
# Concrete sinks                                                              #
# --------------------------------------------------------------------------- #
class ConsoleSink:
    """Echoes hub prints / tracebacks to stderr so errors are never swallowed."""

    def on_raw(self, line: str) -> None:
        print(f"  hub| {line}", file=sys.stderr)


class CaptureBuffer:
    """Accumulates the full run trace in memory. The list this exposes is the
    ``telemetry`` field returned by ``spike_run``."""

    def __init__(self) -> None:
        self.events: list[dict] = []
        self.stdout_lines: list[str] = []
        self.ended: bool = False

    def on_event(self, ev: dict) -> None:
        self.events.append(ev)

    def on_raw(self, line: str) -> None:
        self.stdout_lines.append(line)

    def on_end(self) -> None:
        self.ended = True


class JsonlLogger:
    """Writes each telemetry event as a line of JSON to a file. Useful for
    audit, replay, and offline re-grading."""

    def __init__(self, path: str) -> None:
        self._f = open(path, "w", encoding="utf-8")
        self.path = path

    def on_event(self, ev: dict) -> None:
        self._f.write(json.dumps(ev, separators=(",", ":")) + "\n")
        self._f.flush()

    def on_end(self) -> None:
        self._f.close()


class LivePlot:
    """matplotlib live charts, one panel per sensor that appears in a
    requirement, with the requirement's pass_criteria visualized as a band.

    The plot is a dev-only sink — the agent reads ``CaptureBuffer.events``.
    """

    def __init__(self, requirements_model: dict, refresh_hz: float = 20.0) -> None:
        self.refresh = 1.0 / refresh_hz
        # collect sensors named by requirements, preserve order, dedupe
        seen, sensors = set(), []
        self._bands: dict[str, tuple[Optional[float], Optional[float]]] = {}
        self._units: dict[str, str] = {}
        self._labels: dict[str, str] = {}
        for r in requirements_model.get("requirements", []):
            pc = r.get("pass_criteria") or {}
            sensor = pc.get("sensor")
            if not sensor or sensor in seen:
                continue
            seen.add(sensor)
            sensors.append(sensor)
            self._bands[sensor] = _band_of(pc)
            self._units[sensor] = pc.get("unit", "")
            self._labels[sensor] = r.get("id", "")
        self.sensors = sensors
        self.data: dict[str, list[tuple[float, float]]] = {s: [] for s in sensors}
        self._t0: Optional[float] = None
        self._fig = None
        self._axes: dict[str, Any] = {}
        self._lines: dict[str, Any] = {}
        self._bandspans: dict[str, Any] = {}

    def on_event(self, ev: dict) -> None:
        sensor = ev.get("sensor")
        if sensor not in self.data:
            return
        t = ev["timestamp_ms"] / 1000.0
        if self._t0 is None:
            self._t0 = t
        try:
            v = float(ev["value"])
        except (TypeError, ValueError):
            return
        self.data[sensor].append((t - self._t0, v))

    def _ensure_fig(self):
        import matplotlib.pyplot as plt

        if self._fig is not None:
            return
        n = max(1, len(self.sensors))
        self._fig, axs = plt.subplots(n, 1, figsize=(9, 2.4 * n), squeeze=False, sharex=True)
        for ax, sensor in zip(axs[:, 0], self.sensors):
            unit = self._units.get(sensor, "")
            ax.set_ylabel(f"{sensor}" + (f" ({unit})" if unit else ""))
            ax.grid(True, alpha=0.3)
            lo, hi = self._bands.get(sensor, (None, None))
            # The dashed threshold lines sit at fixed values, so draw them once.
            # The filled span's open edge must follow the live y-limits, so it is
            # (re)drawn each frame in _redraw rather than frozen here against the
            # still-empty axes default of (0, 1).
            if lo is not None:
                ax.axhline(lo, color="tab:green", lw=0.8, ls="--", alpha=0.6)
            if hi is not None:
                ax.axhline(hi, color="tab:green", lw=0.8, ls="--", alpha=0.6)
            (line,) = ax.plot([], [], lw=1.4, color="tab:blue")
            self._axes[sensor] = ax
            self._lines[sensor] = line
        axs[-1, 0].set_xlabel("t (s, hub clock)")
        self._fig.tight_layout()

    def _redraw(self):
        for sensor in self.sensors:
            xs = [p[0] for p in self.data[sensor]]
            ys = [p[1] for p in self.data[sensor]]
            self._lines[sensor].set_data(xs, ys)
            ax = self._axes[sensor]
            # Drop last frame's band before relim so the fill (whose open edge
            # equals the padded y-limit) can't feed back into autoscale and walk
            # the axis off toward infinity. Autoscale sees line data only.
            old = self._bandspans.pop(sensor, None)
            if old is not None:
                old.remove()
            ax.relim(); ax.autoscale_view()
            self._draw_band(sensor, ax)
            if ys:
                v = ys[-1]
                lo, hi = self._bands.get(sensor, (None, None))
                ok = (lo is None or v >= lo) and (hi is None or v <= hi)
                ax.set_title(f"{sensor} = {v:.3g}   {'PASS' if ok else 'OUT OF BAND'}",
                             color=("tab:green" if ok else "tab:red"),
                             fontsize=10, loc="left")

    def _draw_band(self, sensor: str, ax) -> None:
        """(Re)draw the green pass band for ``sensor`` against the axes' current
        y-limits, so an open-ended requirement fills the live visible range and
        flips sides when the operator flips. Called every frame after autoscale."""
        lo, hi = self._bands.get(sensor, (None, None))
        if lo is None and hi is None:
            return
        y0, y1 = ax.get_ylim()
        ylo = lo if lo is not None else y0
        yhi = hi if hi is not None else y1
        self._bandspans[sensor] = ax.axhspan(
            ylo, yhi, color="tab:green", alpha=0.12, zorder=0,
            label=f"{self._labels[sensor]} band")

    async def render_until(self, task: asyncio.Task):
        import matplotlib.pyplot as plt

        plt.ion()
        self._ensure_fig()
        self._fig.show()
        while not task.done():
            self._redraw()
            self._fig.canvas.draw_idle()
            self._fig.canvas.flush_events()
            await asyncio.sleep(self.refresh)
        self._redraw()
        self._fig.canvas.draw_idle()
        self._fig.canvas.flush_events()

    def save_snapshot(self, path: str) -> str:
        self._ensure_fig()
        self._redraw()
        self._fig.savefig(path, dpi=130, bbox_inches="tight")
        return path


def _band_of(pc: dict) -> tuple[Optional[float], Optional[float]]:
    """Extract (min, max) visualization band from a pass_criteria block.

    Returns (None, None) for ops that don't have a natural band (e.g. ``==``,
    ``reaches``); the sensor still plots, just without a shaded zone.
    """
    op = pc.get("op")
    if op == "in_range":
        return (pc.get("min"), pc.get("max"))
    if op in ("<=", "<"):
        return (None, pc.get("value"))
    if op in (">=", ">"):
        return (pc.get("value"), None)
    return (None, None)


# --------------------------------------------------------------------------- #
# Async BLE primitives (used by spike_deploy and spike_run)                   #
# --------------------------------------------------------------------------- #
async def connect_hub(hub_id: Optional[str] = None, timeout: float = 10.0):
    """Find and connect to a Pybricks hub. ``hub_id`` is the BLE advertised
    name; ``None`` selects the first hub advertising the Pybricks service."""
    from pybricksdev.ble import find_device
    from pybricksdev.connections.pybricks import PybricksHubBLE

    device = await find_device(name=hub_id, timeout=timeout)
    hub = PybricksHubBLE(device)
    await hub.connect()
    return hub, device


async def deploy_program(hub, code: str, slot: int = 0) -> None:
    """Compile and download ``code`` to the hub's program slot without
    starting it. Caller is responsible for the hub connection lifecycle."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        path = f.name
    try:
        await hub.download(path)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


async def run_program(
    hub,
    bus: TelemetryBus,
    framer: StdoutFramer,
    timeout_seconds: float = 30.0,
    plot: Optional[LivePlot] = None,
) -> dict:
    """Start the deployed program, stream telemetry through the bus, return a
    completion summary. Returns ``{"completed": bool, "duration_seconds": float}``.

    The bus and framer must already be wired up by the caller, so they can
    install whichever sinks they need (capture, log, plot)."""
    sub = hub.stdout_observable.subscribe(framer.feed)
    started = time.monotonic()
    completed = False
    try:
        await hub.start_user_program()
        wait_task = asyncio.create_task(hub._wait_for_user_program_stop())
        try:
            if plot is not None:
                await plot.render_until(wait_task)
            await asyncio.wait_for(wait_task, timeout=timeout_seconds)
            completed = True
        except asyncio.TimeoutError:
            try:
                await hub.stop_user_program()
            except Exception:
                pass
            completed = False
    finally:
        sub.dispose()
        bus.end()
    return {
        "completed": completed,
        "duration_seconds": time.monotonic() - started,
    }
