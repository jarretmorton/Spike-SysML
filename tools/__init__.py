"""Spike SysML tool surface.

Four tools, two for each architectural pattern:

- ``sysml_validate`` supports the orchestrator-workers pattern by
  schema-checking the merged requirements model.
- ``spike_deploy``, ``spike_run``, and ``test_eval`` form the
  evaluator-optimizer loop, with the SPIKE Prime hub as the evaluator.

Status (v0.1):

- ``sysml_validate`` — implemented for the ``lego`` subset.
- ``spike_deploy``, ``spike_run`` — implemented over Bluetooth via
  ``pybricksdev``.
- ``test_eval`` — implemented for the v0.1 pass_criteria operator grammar
  (``<=``, ``>=``, ``<``, ``>``, ``==``, ``!=``, ``in_range``, ``reaches``).

The hub-to-host wire format and the requirements model schema are defined
in ``docs/wire_contract.md``.
"""

from .sysml_validate import sysml_validate
from .spike_deploy import spike_deploy
from .spike_run import spike_run
from .test_eval import test_eval

__all__ = [
    "sysml_validate",
    "spike_deploy",
    "spike_run",
    "test_eval",
]
