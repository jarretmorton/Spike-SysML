# spike-prime-mcp

MCP server exposing the SPIKE Prime hardware seam of the Spike SysML
pipeline — the deploy-and-run hardware steps inside the calibration
(stage 5) and integration (stage 6) loops of
[`docs/architecture.md`](../docs/architecture.md). Three tools over stdio:

| Tool | Purpose |
|------|---------|
| `flash_program` | Compile + download MicroPython to the hub (no execution). |
| `run_program` | Execute the deployed program; persist the telemetry trace to `runs/<run_id>.jsonl`; return run metadata only. |
| `get_telemetry` | Read a persisted trace back at `summary` (default), `downsampled`, or `full` detail. |

The host-side pipeline tools (`sysml_validate`, `test_eval`) deliberately
stay out of the MCP surface — the server exposes hardware, not pipeline
logic. The normal agent sequence is `flash_program` → `run_program` →
`get_telemetry`.

## Design

- **Per-call BLE lifecycle.** Every tool call scans, connects, works, and
  disconnects. No connection state survives between calls, so a hub that
  slept or power-cycled produces a clean, retryable error rather than a
  stale-connection failure.
- **Token-efficient telemetry** (per *Writing Effective Tools for AI
  Agents*). `run_program` returns metadata and per-sensor record counts
  only; the trace persists to disk. `get_telemetry` then shapes retrieval:
  on a representative 650-event trace, raw JSONL is ~9,500 tokens, the
  `summary` format is ~240 (40× smaller), and `downsampled` is ~1,800.
  Traces are re-queryable — summary first, then drill into a window —
  without re-running hardware.
- Composes the async primitives in [`tools/_runtime.py`](../tools/_runtime.py)
  directly (bus, framer, sinks, `connect_hub`/`deploy_program`/`run_program`).
  Wire contract: [`docs/wire_contract.md`](../docs/wire_contract.md).

## Setup

Requires Python 3.10+, the hub on Pybricks firmware, and:

```bash
pip install mcp pybricksdev
```

Claude Desktop — add to `%APPDATA%\Claude\claude_desktop_config.json`
(Windows; macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`),
then restart Claude Desktop:

```json
{
  "mcpServers": {
    "spike-prime": {
      "command": "C:\\Users\\Jarret\\Documents\\GitHub\\Spike-SysML\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\Jarret\\Documents\\GitHub\\Spike-SysML\\spike_prime_mcp\\server.py"]
    }
  }
}
```

Paths must be absolute. Use the interpreter that has `mcp` and
`pybricksdev` installed (a venv's `Scripts\python.exe` is fine). The
server self-locates the repo root from its own path, so no `PYTHONPATH`
or working-directory configuration is needed; traces land in `runs/` at
the repo root.

## Verify without hardware

```bash
python spike_prime_mcp/smoke_test.py
```

Launches the server as a real stdio subprocess, performs the MCP
handshake, and exercises `get_telemetry` (all three formats, filters, and
error paths) against a synthetic braking-curve trace. `flash_program` and
`run_program` need a hub; with one powered on, ask Claude Desktop to
*"flash this program and tell me what the telemetry shows."*

## Troubleshooting

- Server not listed after restart: the config JSON must be valid — Claude
  Desktop silently skips a corrupt file.
- Connect errors: hub powered on, running Pybricks firmware, and not
  already connected to another app (Pybricks accepts one BLE client at a
  time).
- Server stderr (including hub tracebacks echoed by `run_program`) is
  captured in Claude Desktop's `logs/mcp-server-spike-prime.log`.
