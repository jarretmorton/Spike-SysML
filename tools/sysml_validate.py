"""Schema validation for SysML v2 requirements models."""
from __future__ import annotations

from typing import Literal


# Valid requirement types. The type is carried in the `type` field; it is NOT
# encoded in the id (see wire_contract.md section 2 — ids are stable, opaque
# handles and only uniqueness is enforced).
_VALID_TYPES = {"functional", "behavioral", "interface", "constraint"}

# pass_criteria operator grammar supported by test_eval v0.1.
_PC_NUMERIC_OPS = {"<=", ">=", "<", ">", "==", "!="}
_PC_RANGE_OPS = {"in_range"}
_PC_DERIVED_OPS = {"reaches"}
_PC_ALL_OPS = _PC_NUMERIC_OPS | _PC_RANGE_OPS | _PC_DERIVED_OPS


def sysml_validate(
    model: dict,
    schema_subset: Literal["lego", "full"] = "lego",
) -> dict:
    """Validate a structured requirements model against the SysML v2 schema.

    Use this tool on the *composed* SysML v2 model — after requirements have
    been used to select and connect unit models from the registry, and before
    the code step. Validate the composed model, not just the merged
    requirements: composition (the interconnections and bound parameters) is
    where invalidity is introduced even when unit models are individually
    valid. A model that fails validation returns to the composition step with
    the error list, not downstream.

    Args:
        model: The requirements model as a dict. Expected top-level keys:
            ``requirements`` (list of requirement objects, each with at
            least ``id``, ``type``, ``text``, and ``pass_criteria``) and
            ``metadata`` (dict with ``source_spec`` and ``generated_at``).
        schema_subset: Which SysML v2 subset to validate against. ``lego``
            is the constrained subset suitable for SPIKE Prime
            demonstrations; ``full`` is the OMG draft. Defaults to
            ``lego``. The ``full`` mode is not implemented in v0.1.

    Returns:
        A dict with the keys:

        - ``valid`` (bool): True if the model conforms to the schema.
        - ``errors`` (list): List of dicts with ``path`` (JSON pointer
          into ``model``) and ``message`` (human-readable explanation).
          Empty when ``valid`` is True.
        - ``warnings`` (list): List of dicts in the same shape as
          ``errors``. Warnings do not cause ``valid`` to be False.
    """
    errors: list[dict] = []
    warnings: list[dict] = []

    if schema_subset == "full":
        warnings.append({
            "path": "/",
            "message": "schema_subset='full' is not implemented in v0.1; using 'lego'.",
        })

    # ----- top-level structure -----
    if not isinstance(model, dict):
        return {"valid": False, "errors": [{"path": "/", "message": "model must be a dict."}], "warnings": warnings}

    if "requirements" not in model:
        errors.append({"path": "/requirements", "message": "missing 'requirements' key."})
    elif not isinstance(model["requirements"], list):
        errors.append({"path": "/requirements", "message": "'requirements' must be a list."})

    if "metadata" not in model:
        warnings.append({"path": "/metadata", "message": "missing 'metadata' block."})
    elif not isinstance(model["metadata"], dict):
        warnings.append({"path": "/metadata", "message": "'metadata' should be a dict."})
    else:
        for k in ("source_spec", "generated_at"):
            if k not in model["metadata"]:
                warnings.append({"path": f"/metadata/{k}", "message": f"metadata missing '{k}'."})

    # ----- per-requirement checks -----
    seen_ids: set[str] = set()
    for i, r in enumerate(model.get("requirements", []) or []):
        base = f"/requirements/{i}"
        if not isinstance(r, dict):
            errors.append({"path": base, "message": "requirement must be a dict."})
            continue

        # required fields
        for key in ("id", "type", "text", "pass_criteria"):
            if key not in r:
                errors.append({"path": f"{base}/{key}", "message": f"missing required key '{key}'."})

        rid = r.get("id")
        rtype = r.get("type")

        # id uniqueness
        if isinstance(rid, str):
            if rid in seen_ids:
                errors.append({"path": f"{base}/id", "message": f"duplicate id {rid!r}."})
            seen_ids.add(rid)

        # type must be a known value (the id prefix carries no validated
        # meaning — type lives in this field; ids are opaque, unique handles)
        if rtype not in _VALID_TYPES:
            errors.append({
                "path": f"{base}/type",
                "message": (
                    f"type must be one of {sorted(_VALID_TYPES)} (got {rtype!r})."
                ),
            })

        # pass_criteria shape
        pc = r.get("pass_criteria")
        if pc is not None:
            _validate_pass_criteria(pc, base + "/pass_criteria", errors, warnings)

        # type-specific fields (from system_prompts.md)
        if rtype == "behavioral":
            for k in ("states", "transitions"):
                if k in r and not isinstance(r[k], list):
                    errors.append({"path": f"{base}/{k}", "message": f"'{k}' must be a list."})
        elif rtype == "interface":
            for k, expected_type in (("port", (str, type(None))),
                                      ("direction", str),
                                      ("signal_type", str)):
                if k in r and not isinstance(r[k], expected_type):
                    errors.append({
                        "path": f"{base}/{k}",
                        "message": f"'{k}' has wrong type.",
                    })
            if r.get("direction") not in (None, "input", "output", "bidirectional"):
                errors.append({
                    "path": f"{base}/direction",
                    "message": "direction must be 'input', 'output', or 'bidirectional'.",
                })

    return {"valid": not errors, "errors": errors, "warnings": warnings}


def _validate_pass_criteria(pc, path: str, errors: list, warnings: list) -> None:
    if not isinstance(pc, dict):
        errors.append({"path": path, "message": "pass_criteria must be a dict."})
        return
    op = pc.get("op")
    if op is None:
        errors.append({"path": f"{path}/op", "message": "missing 'op'."})
    elif op not in _PC_ALL_OPS:
        errors.append({
            "path": f"{path}/op",
            "message": f"op {op!r} not in supported set {sorted(_PC_ALL_OPS)}.",
        })
    if "sensor" not in pc:
        errors.append({"path": f"{path}/sensor", "message": "missing 'sensor'."})
    if op in _PC_NUMERIC_OPS and "value" not in pc:
        errors.append({"path": f"{path}/value", "message": f"op {op!r} requires 'value'."})
    if op == "in_range":
        if "min" not in pc and "max" not in pc:
            errors.append({"path": path, "message": "'in_range' needs at least one of 'min' or 'max'."})
    if op == "reaches":
        for k in ("value", "within_seconds"):
            if k not in pc:
                errors.append({"path": f"{path}/{k}", "message": f"'reaches' requires '{k}'."})