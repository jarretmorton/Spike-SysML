"""Spike SysML tool surface.

Four tools, two for each architectural pattern:

- ``sysml_validate`` supports the orchestrator-workers pattern by
  schema-checking the merged requirements model.
- ``spike_deploy``, ``spike_run``, and ``test_eval`` form the
  evaluator-optimizer loop, with the SPIKE Prime hub as the evaluator.

All tools are stubs as of Week 1.
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
