#!/usr/bin/env python3
"""No-hardware smoke test for spike-prime-mcp.

Run before the Loom / after any change:

    python spike_prime_mcp/smoke_test.py

What it does:
1. Writes a synthetic braking-curve trace + meta to runs/run-smoketest.*
2. Launches server.py as a real stdio MCP subprocess, performs the MCP
   handshake, lists tools, and calls get_telemetry in all three formats
   plus the error paths.
3. Prints PASS/FAIL per check with payload sizes, then deletes the
   synthetic run files (pass --keep to keep them).

flash_program / run_program need a hub and are exercised on hardware.
"""
from __future__ import annotations

import asyncio
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
RUNS = REPO_ROOT / "runs"
RID = "run-smoketest"

from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402


def make_trace() -> int:
    """Synthetic 8 s run: decaying speed, shrinking distance, force spike."""
    RUNS.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(RUNS / f"{RID}.jsonl", "w", encoding="utf-8") as f:
        for i in range(0, 8000, 25):  # 40 Hz
            t = i / 1000.0
            rows = [
                {"timestamp_ms": i, "sensor": "speed_mps", "value": round(0.5 * math.exp(-t / 3), 4)},
                {"timestamp_ms": i, "sensor": "distance_mm", "value": round(400 - 45 * t + 2 * math.sin(t * 7), 2)},
            ]
            if 5000 <= i <= 5200:
                rows.append({"timestamp_ms": i, "sensor": "force_n", "value": round(8.3 * math.exp(-((i - 5100) / 60) ** 2), 3)})
            for r in rows:
                f.write(json.dumps(r, separators=(",", ":")) + "\n")
                n += 1
    (RUNS / f"{RID}.meta.json").write_text(json.dumps({
        "run_id": RID, "completed": True, "duration_seconds": 8.0,
        "created_at": "2026-06-11T00:00:00-07:00", "slot": 0,
        "hub_id": "smoketest", "end_sentinel_seen": True,
    }), encoding="utf-8")
    return n


def check(name: str, ok: bool, detail: str = "") -> bool:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))
    return ok


async def run_checks() -> bool:
    params = StdioServerParameters(
        command=sys.executable, args=[str(HERE / "server.py")]
    )
    all_ok = True
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()

            tools = await s.list_tools()
            names = sorted(t.name for t in tools.tools)
            all_ok &= check(
                "tool surface", names == ["flash_program", "get_telemetry", "run_program"],
                ",".join(names),
            )

            async def call(args: dict) -> tuple[dict, int]:
                res = await s.call_tool("get_telemetry", args)
                text = res.content[0].text
                return json.loads(text), len(text)

            out, size = await call({"run_id": RID})
            ok = "sensors" in out and out["sensors"]["force_n"]["max"] > 8.0 \
                and out["sensors"]["speed_mps"]["count"] == 320
            all_ok &= check("summary", ok, f"{size} chars")

            out, size = await call({"run_id": RID, "response_format": "downsampled"})
            sp = out.get("series", {}).get("speed_mps", {})
            ok = sp.get("points", 999) <= 100 and sp.get("source_events") == 320 \
                and len(sp.get("t_ms", [])) == len(sp.get("value", []))
            all_ok &= check("downsampled", ok, f"{size} chars, {sp.get('points')} pts/sensor")

            out, size = await call({"run_id": RID, "response_format": "full",
                                    "sensors": ["force_n"]})
            ok = out.get("returned", 0) == 9 and not out.get("truncated", True)
            all_ok &= check("full (filtered)", ok, f"{size} chars, {out.get('returned')} events")

            out, _ = await call({"run_id": RID, "response_format": "full"})
            all_ok &= check("full without filter -> error", "error" in out)

            out, _ = await call({"run_id": RID, "response_format": "full",
                                 "sensors": ["speed_mps", "distance_mm"]})
            all_ok &= check("full truncation cap", out.get("returned") == 500
                            and out.get("truncated") is True)

            out, _ = await call({"run_id": "latest"})
            all_ok &= check("latest resolution", out.get("run", {}).get("run_id") == RID)

            out, _ = await call({"run_id": "run-nope"})
            all_ok &= check("unknown run -> error + known_runs",
                            "error" in out and "known_runs" in out)

            out, _ = await call({"run_id": RID, "time_window": [4900, 5300]})
            ok = out.get("sensors", {}).get("force_n", {}).get("count") == 9
            all_ok &= check("time_window filter", ok)
    return all_ok


def main() -> int:
    print(f"smoke_test: synthetic trace = {make_trace()} events")
    ok = asyncio.run(run_checks())
    if "--keep" not in sys.argv:
        for p in (RUNS / f"{RID}.jsonl", RUNS / f"{RID}.meta.json"):
            p.unlink(missing_ok=True)
    print("ALL PASS" if ok else "FAILURES — see above")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
