"""Spike SysML tool surface.

Five tools spanning the pipeline's validation and hardware-in-the-loop
stages:

- ``sysml_validate`` schema-checks the composed SysML v2 model before
  the code step; ``check_trace_complete`` is its companion gate,
  confirming the traceability spine is present at the composed stage.
- ``spike_deploy`` and ``spike_run`` drive the hardware in both the
  calibration loop (stage 5) and the integration loop (stage 6);
  ``test_eval`` is the critic for the integration loop, with the SPIKE
  Prime hub as the evaluator.

Status (v0.1):

- ``sysml_validate`` — implemented for the ``lego`` subset.
- ``spike_deploy``, ``spike_run`` — implemented over Bluetooth via
  ``pybricksdev``.
- ``test_eval`` — implemented for the v0.1 pass_criteria operator grammar
  (``<=``, ``>=``, ``<``, ``>``, ``==``, ``!=``, ``in_range``, ``reaches``).

The hub-to-host wire format and the requirements model schema are defined
in ``docs/wire_contract.md``.
"""

from .sysml_validate import sysml_validate, check_trace_complete
from .spike_deploy import spike_deploy
from .spike_run import spike_run
from .test_eval import test_eval

__all__ = [
    "sysml_validate",
    "check_trace_complete",
    "spike_deploy",
    "spike_run",
    "test_eval",
]