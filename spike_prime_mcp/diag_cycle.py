#!/usr/bin/env python3
"""End-to-end check through the real MCP server: flash -> run -> get_telemetry.

    .venv/Scripts/python.exe spike_prime_mcp/diag_cycle.py

Confirms both offloaded hardware tools (flash_program, run_program) work in the
real stdio runtime, and that telemetry round-trips. Hub must be on, Pybricks
firmware, not connected to another app.
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

# Emits a few telemetry events over ~1s, then the flush sentinel and exits.
# Kept deliberately minimal so a hub-side error can't be the cause.
PROGRAM = (
    "from pybricks.tools import wait\n"
    "from usys import stdout\n"
    "t = 0\n"
    "for i in range(10):\n"
    "    stdout.write('{\"timestamp_ms\":' + str(t) + ',\"sensor\":\"counter\",\"value\":' + str(i) + '}\\n')\n"
    "    t = t + 100\n"
    "    wait(100)\n"
    "stdout.write('{\"event\":\"end\"}\\n')\n"
)


async def main() -> None:
    params = StdioServerParameters(command=sys.executable, args=[str(HERE / "server.py")])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()

            print("1) flash_program ...", flush=True)
            t = time.monotonic()
            r = await s.call_tool("flash_program", {"code": PROGRAM})
            print(f"   ({time.monotonic() - t:.1f}s) {r.content[0].text}", flush=True)

            print("2) run_program (timeout 15s) ...", flush=True)
            t = time.monotonic()
            r = await s.call_tool("run_program", {"timeout_seconds": 15.0})
            print(f"   ({time.monotonic() - t:.1f}s) {r.content[0].text}", flush=True)

            print("3) get_telemetry (latest, summary) ...", flush=True)
            r = await s.call_tool("get_telemetry", {"run_id": "latest"})
            print(f"   {r.content[0].text}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
