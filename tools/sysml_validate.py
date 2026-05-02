"""Schema validation for SysML v2 requirements models."""

from typing import Literal


def sysml_validate(
    model: dict,
    schema_subset: Literal["lego", "full"] = "lego",
) -> dict:
    """Validate a structured requirements model against the SysML v2 schema.

    Use this tool after the orchestrator has merged worker outputs into a
    single requirements model, and before passing the model to the draft
    agent. A model that fails validation should be returned to the
    orchestrator with the error list, not passed downstream.

    Args:
        model: The requirements model as a dict. Expected top-level keys:
            ``requirements`` (list of requirement objects, each with at
            least ``id``, ``type``, ``text``, and ``pass_criteria``) and
            ``metadata`` (dict with ``source_spec`` and ``generated_at``).
        schema_subset: Which SysML v2 subset to validate against. ``lego``
            is the constrained subset suitable for SPIKE Prime
            demonstrations; ``full`` is the OMG draft. Defaults to
            ``lego``.

    Returns:
        A dict with the keys:

        - ``valid`` (bool): True if the model conforms to the schema.
        - ``errors`` (list): List of dicts with ``path`` (JSON pointer
          into ``model``) and ``message`` (human-readable explanation).
          Empty when ``valid`` is True.
        - ``warnings`` (list): List of dicts in the same shape as
          ``errors``. Warnings do not cause ``valid`` to be False.

    Raises:
        NotImplementedError: This tool is a Week 1 stub.
    """
    raise NotImplementedError("sysml_validate is a Week 1 stub.")
