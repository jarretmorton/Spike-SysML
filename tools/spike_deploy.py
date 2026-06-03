"""Deploy generated MicroPython to a SPIKE Prime hub."""
from __future__ import annotations

import asyncio
from typing import Optional

from ._runtime import connect_hub, deploy_program


def spike_deploy(
    code: str,
    hub_id: Optional[str] = None,
    slot: int = 0,
) -> dict:
    """Push generated MicroPython source to the SPIKE Prime hub.

    Use this tool to upload code produced by the code step (templated hardware
    primitives plus generated mission orchestration). The code is not executed
    here — call :func:`spike_run` after a successful deploy. Used in both
    hardware loops: calibration (stage 5) and integration (stage 6).

    Args:
        code: MicroPython source to deploy. Must be syntactically valid for
            the SPIKE Prime hub's MicroPython runtime. The code generator is
            responsible for syntactic correctness; this tool does not lint
            or transform the source.
        hub_id: Optional hub identifier (the BLE advertised name) when more
            than one hub is paired. If ``None``, the tool uses the first
            hub advertising the Pybricks service.
        slot: Program slot on the hub (0-19) to write into. Defaults to
            ``0``. Reusing a slot overwrites any program previously stored
            there. The slot is accepted but not yet routed through to the
            hub in v0.1 — all deploys land in slot 0; revisit when the
            agent needs to address multiple slots concurrently.

    Returns:
        A dict with the keys:

        - ``deployed`` (bool): True if the upload completed.
        - ``slot`` (int): The slot the program was written to.
        - ``hub_id`` (str | None): The hub the program was written to (the
          BLE name discovered during connect).
        - ``error`` (str | None): Human-readable error message if the deploy
          failed, otherwise ``None``.
    """

    async def _go() -> dict:
        hub = None
        try:
            hub, device = await connect_hub(hub_id=hub_id)
            await deploy_program(hub, code, slot=slot)
            return {
                "deployed": True,
                "slot": slot,
                "hub_id": getattr(device, "name", None) or hub_id,
                "error": None,
            }
        except Exception as e:
            return {
                "deployed": False,
                "slot": slot,
                "hub_id": hub_id,
                "error": f"{type(e).__name__}: {e}",
            }
        finally:
            if hub is not None:
                try:
                    await hub.disconnect()
                except Exception:
                    pass

    return asyncio.run(_go())
