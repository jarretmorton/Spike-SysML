"""Execute a deployed program on the SPIKE Prime hub and capture telemetry."""
from __future__ import annotations

import asyncio
from typing import Optional

from ._runtime import (
    CaptureBuffer,
    StdoutFramer,
    TelemetryBus,
    connect_hub,
    run_program,
)


def spike_run(
    slot: int = 0,
    timeout_seconds: float = 30.0,
    hub_id: Optional[str] = None,
) -> dict:
    """Run a program on the SPIKE Prime hub and stream sensor telemetry.

    Use this tool after a successful :func:`spike_deploy`. The tool blocks
    until the program completes, the timeout expires, or the hub
    disconnects. Telemetry is captured for the entire run window. Used in
    both hardware loops — calibration tests (whose telemetry feeds the
    deterministic constant-fitter) and integration tests (whose telemetry
    feeds test_eval).

    Args:
        slot: Program slot to execute. Defaults to ``0``, which matches
            :func:`spike_deploy`'s default slot. Slot routing is a v0.2
            item; v0.1 starts whichever program was last deployed.
        timeout_seconds: Maximum runtime before the run is terminated from
            the host side. Defaults to 30 seconds.
        hub_id: Optional hub identifier; see :func:`spike_deploy`.

    Returns:
        A dict with the keys:

        - ``completed`` (bool): True if the program ran to its own end,
          False if the host timed it out or the hub disconnected.
        - ``duration_seconds`` (float): Wall-clock duration from the start
          of execution to the end of the run window.
        - ``telemetry`` (list): Time-ordered list of telemetry events. Each
          event is a dict with ``timestamp_ms`` (int, hub clock since
          program start), ``sensor`` (str), and ``value`` (any
          JSON-serialisable type appropriate to the sensor). See
          ``docs/wire_contract.md`` for the canonical format.
        - ``stdout`` (str): Anything the program wrote to stdout that was
          not a telemetry event (tracebacks, prints, debug lines).
        - ``error`` (str | None): Human-readable error if the run did not
          start. A program that runs to completion but fails its test
          condition is *not* an error here — that distinction is made by
          :func:`test_eval`.
    """

    async def _go() -> dict:
        hub = None
        bus = TelemetryBus()
        framer = StdoutFramer(bus)
        capture = bus.add(CaptureBuffer())
        try:
            hub, _device = await connect_hub(hub_id=hub_id)
            summary = await run_program(
                hub, bus, framer, timeout_seconds=timeout_seconds, plot=None
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
                try:
                    await hub.disconnect()
                except Exception:
                    pass

    return asyncio.run(_go())
