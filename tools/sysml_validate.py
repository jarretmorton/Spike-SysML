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
            ``requirements`` (list of requirement objects, each with at least
            ``id``, ``type``, ``text``, and either ``pass_criteria`` or
            ``verified_by``), an optional ``parts`` list, and ``metadata``
            (dict with ``source_spec`` and ``generated_at``). The
            traceability-spine fields (``unit_model``, ``depends_on_parts``,
            ``implemented_by``, ``depends_on_params``, ``verified_by``) are
            optional here and integrity-checked when present; whether they must
            be *present* is a separate, stage-aware question answered by
            ``check_trace_complete``.
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

    # ----- collected up front for referential-integrity checks -----
    all_req_ids = {
        r["id"] for r in (model.get("requirements") or [])
        if isinstance(r, dict) and isinstance(r.get("id"), str)
    }
    all_part_ids = {
        p["part_id"] for p in (model.get("parts") or [])
        if isinstance(p, dict) and isinstance(p.get("part_id"), str)
    }

    # ----- per-requirement checks -----
    seen_ids: set[str] = set()
    for i, r in enumerate(model.get("requirements", []) or []):
        base = f"/requirements/{i}"
        if not isinstance(r, dict):
            errors.append({"path": base, "message": "requirement must be a dict."})
            continue

        # required fields (pass_criteria is no longer unconditional — a
        # requirement may instead be verified indirectly via verified_by)
        for key in ("id", "type", "text"):
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

        # verifiability: a requirement needs either a non-null pass_criteria or
        # a verified_by pointing at another requirement that carries one
        if pc is None and r.get("verified_by") is None:
            errors.append({
                "path": base,
                "message": "requirement must have a non-null 'pass_criteria' or a 'verified_by'.",
            })

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

        # traceability-spine fields — all optional (presence is stage-dependent;
        # see check_trace_complete), but integrity-checked whenever present
        _validate_spine_fields(r, base, rid, all_req_ids, all_part_ids, errors, warnings)

    # ----- parts block (optional; validated when present) -----
    if "parts" in model:
        if not isinstance(model["parts"], list):
            errors.append({"path": "/parts", "message": "'parts' must be a list."})
        else:
            seen_parts: set[str] = set()
            for pi, part in enumerate(model["parts"]):
                pbase = f"/parts/{pi}"
                if not isinstance(part, dict):
                    errors.append({"path": pbase, "message": "part must be a dict."})
                    continue
                pid = part.get("part_id")
                if not isinstance(pid, str):
                    errors.append({"path": f"{pbase}/part_id", "message": "part missing string 'part_id'."})
                else:
                    if pid in seen_parts:
                        errors.append({"path": f"{pbase}/part_id", "message": f"duplicate part_id {pid!r}."})
                    seen_parts.add(pid)
                for k in ("ports", "emits"):
                    if k in part and not isinstance(part[k], list):
                        errors.append({"path": f"{pbase}/{k}", "message": f"'{k}' must be a list."})

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


def _validate_spine_fields(r, base, rid, all_req_ids, all_part_ids, errors, warnings) -> None:
    """Structural + referential checks for the optional traceability-spine
    fields. Presence is optional (the spine fills progressively through the
    pipeline — see check_trace_complete); correctness is enforced here whenever
    a field is present."""
    if "unit_model" in r and not isinstance(r["unit_model"], str):
        errors.append({"path": f"{base}/unit_model", "message": "'unit_model' must be a string."})

    if "implemented_by" in r and not isinstance(r["implemented_by"], (str, type(None))):
        errors.append({"path": f"{base}/implemented_by", "message": "'implemented_by' must be a string or null."})

    dop = r.get("depends_on_parts")
    if dop is not None:
        if not isinstance(dop, list):
            errors.append({"path": f"{base}/depends_on_parts", "message": "'depends_on_parts' must be a list."})
        else:
            for j, pid in enumerate(dop):
                if not isinstance(pid, str):
                    errors.append({"path": f"{base}/depends_on_parts/{j}", "message": "part reference must be a string."})
                elif pid not in all_part_ids:
                    errors.append({
                        "path": f"{base}/depends_on_parts/{j}",
                        "message": f"depends_on_parts references {pid!r}, not defined in the top-level 'parts' block.",
                    })

    dpp = r.get("depends_on_params")
    if dpp is not None:
        if not isinstance(dpp, list):
            errors.append({"path": f"{base}/depends_on_params", "message": "'depends_on_params' must be a list."})
        else:
            for j, p in enumerate(dpp):
                if not isinstance(p, dict):
                    errors.append({"path": f"{base}/depends_on_params/{j}", "message": "each depends_on_params entry must be an object."})
                elif "param" not in p:
                    warnings.append({"path": f"{base}/depends_on_params/{j}", "message": "depends_on_params entry missing 'param'."})

    vb = r.get("verified_by")
    if vb is not None:
        if not isinstance(vb, str):
            errors.append({"path": f"{base}/verified_by", "message": "'verified_by' must be a string."})
        elif vb == rid:
            errors.append({"path": f"{base}/verified_by", "message": "a requirement cannot verify itself."})
        elif vb not in all_req_ids:
            errors.append({
                "path": f"{base}/verified_by",
                "message": f"verified_by references {vb!r}, not an existing requirement id.",
            })


def check_trace_complete(model: dict, stage: str = "composed") -> dict:
    """Traceability-completeness gate — a verdict distinct from sysml_validate.

    sysml_validate answers "is this well-formed"; this answers "is the spine
    present for this pipeline stage". They are deliberately kept separate so a
    model's structural validity never silently depends on how far through the
    pipeline it is. Run this *after* sysml_validate passes.

    At the ``composed`` stage — where sysml_validate runs, before the code step
    — every requirement must already carry the joins that exist by then:
    ``unit_model`` and a non-empty ``depends_on_parts``. The code-side joins
    (``implemented_by`` and pass_criteria/emit coverage) belong to a later
    ``verified``-stage gate that is not implemented in v0.1.

    Args:
        model: the requirements model (same shape sysml_validate takes).
        stage: which pipeline stage to enforce. Only ``composed`` is
            implemented in v0.1.

    Returns:
        ``{"complete": bool, "errors": list, "warnings": list}`` — note the
        verdict key is ``complete``, not ``valid``.
    """
    errors: list[dict] = []
    warnings: list[dict] = []

    if stage != "composed":
        warnings.append({
            "path": "/",
            "message": f"stage={stage!r} is not implemented in v0.1; using 'composed'.",
        })

    if not isinstance(model, dict):
        return {"complete": False, "errors": [{"path": "/", "message": "model must be a dict."}], "warnings": warnings}

    for i, r in enumerate(model.get("requirements", []) or []):
        base = f"/requirements/{i}"
        if not isinstance(r, dict):
            continue
        if not r.get("unit_model"):
            errors.append({"path": f"{base}/unit_model", "message": "composed-stage requirement missing 'unit_model'."})
        dop = r.get("depends_on_parts")
        if not (isinstance(dop, list) and len(dop) > 0):
            errors.append({"path": f"{base}/depends_on_parts", "message": "composed-stage requirement missing non-empty 'depends_on_parts'."})

    return {"complete": not errors, "errors": errors, "warnings": warnings}