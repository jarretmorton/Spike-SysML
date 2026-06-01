"""Score a hardware run against the requirement it implements."""
from __future__ import annotations

import math
from typing import Any, Optional


# pass_criteria operators understood by v0.1.
_NUMERIC_OPS = {"<=", ">=", "<", ">", "==", "!=", "in_range"}
_DERIVED_OPS = {"reaches"}
_ALL_OPS = _NUMERIC_OPS | _DERIVED_OPS


def test_eval(
    run_result: dict,
    requirement: dict,
) -> dict:
    """Decide whether a run satisfies the requirement it was built to test.

    This tool is the critic in the evaluator-optimizer loop. It is the only
    place where a pass/fail verdict is produced; no other tool should infer
    success from telemetry. If the verdict is ``passed=False`` and the
    iteration budget is not exhausted, the loop returns to the draft agent
    with the reasoning attached.

    Args:
        run_result: The full dict returned by :func:`spike_run`. Must
            include the ``telemetry`` and ``completed`` fields.
        requirement: A single requirement object from a validated SysML v2
            model. Must include ``id``, ``text``, and ``pass_criteria``.
            The ``pass_criteria`` is the machine-checkable condition the
            run must satisfy; see ``docs/wire_contract.md`` for the
            supported operator grammar.

    Returns:
        A dict with the keys:

        - ``passed`` (bool): True if the run satisfied the requirement.
        - ``requirement_id`` (str): Echoes ``requirement["id"]`` for
          traceability.
        - ``reasoning`` (str): Human-readable explanation of how the
          verdict was reached. This text is the most useful signal back to
          the draft agent on a failure.
        - ``evidence`` (dict): References into ``run_result["telemetry"]``
          that support the verdict — indices and the events at those
          indices that triggered the pass, or the lack thereof.
    """
    req_id = requirement.get("id", "?")
    pc = requirement.get("pass_criteria") or {}
    op = pc.get("op")
    sensor = pc.get("sensor")

    if op is None or sensor is None:
        return {
            "passed": False,
            "requirement_id": req_id,
            "reasoning": "pass_criteria missing required keys 'op' and/or 'sensor'.",
            "evidence": {},
        }
    if op not in _ALL_OPS:
        return {
            "passed": False,
            "requirement_id": req_id,
            "reasoning": f"unsupported pass_criteria operator: {op!r}.",
            "evidence": {},
        }

    telemetry = run_result.get("telemetry", []) or []
    indexed = [(i, ev) for i, ev in enumerate(telemetry) if ev.get("sensor") == sensor]
    samples = [(i, ev["value"]) for i, ev in indexed]
    n = len(samples)
    if n == 0:
        return {
            "passed": False,
            "requirement_id": req_id,
            "reasoning": (
                f"no telemetry samples for sensor {sensor!r} in the run. "
                f"Check that the deployed program emits this sensor (the "
                f"signal-name contract between the requirement and the "
                f"program is not validated by sysml_validate yet)."
            ),
            "evidence": {"sample_count": 0},
        }

    if op in _NUMERIC_OPS:
        return _eval_numeric(req_id, pc, sensor, samples, n)
    return _eval_reaches(req_id, pc, sensor, samples, telemetry)


def _eval_numeric(req_id: str, pc: dict, sensor: str,
                  samples: list[tuple[int, Any]], n: int) -> dict:
    op = pc["op"]
    violations: list[tuple[int, Any]] = []
    if op == "in_range":
        lo, hi = pc.get("min"), pc.get("max")
        for i, v in samples:
            try:
                fv = float(v)
            except (TypeError, ValueError):
                continue
            if (lo is not None and fv < lo) or (hi is not None and fv > hi):
                violations.append((i, fv))
        bound_desc = f"in [{lo}, {hi}]"
    else:
        target = pc.get("value")
        for i, v in samples:
            try:
                fv = float(v)
            except (TypeError, ValueError):
                continue
            ok = {
                "<=": fv <= target,
                ">=": fv >= target,
                "<":  fv <  target,
                ">":  fv >  target,
                "==": fv == target,
                "!=": fv != target,
            }[op]
            if not ok:
                violations.append((i, fv))
        bound_desc = f"{op} {target}"

    passed = not violations
    if passed:
        reasoning = (
            f"all {n} samples of {sensor!r} satisfy {bound_desc}."
        )
        evidence = {"sample_count": n, "violation_count": 0}
    else:
        # worst = furthest outside the constraint
        def excess(item):
            i, v = item
            if op == "in_range":
                lo, hi = pc.get("min"), pc.get("max")
                lo_e = (lo - v) if lo is not None else -math.inf
                hi_e = (v - hi) if hi is not None else -math.inf
                return max(lo_e, hi_e)
            target = pc.get("value")
            return abs(v - target)
        wi, wv = max(violations, key=excess)
        wev = {"index": wi, "event": _safe_event(samples, wi, wv, sensor)}
        reasoning = (
            f"{len(violations)} of {n} samples of {sensor!r} violated {bound_desc}; "
            f"worst was v={wv} at sample index {wi}."
        )
        evidence = {
            "sample_count": n,
            "violation_count": len(violations),
            "worst": wev,
        }
    return {
        "passed": passed,
        "requirement_id": req_id,
        "reasoning": reasoning,
        "evidence": evidence,
    }


def _eval_reaches(req_id: str, pc: dict, sensor: str,
                  samples: list[tuple[int, Any]], telemetry: list[dict]) -> dict:
    """The "reaches" operator: pass iff the sensor attains ``value`` within
    ``within_seconds`` from the start of the run (or from the start of the
    matching sensor's first sample if hub-clock origin differs)."""
    target = pc.get("value")
    within = pc.get("within_seconds")
    if target is None or within is None:
        return {
            "passed": False,
            "requirement_id": req_id,
            "reasoning": "'reaches' requires 'value' and 'within_seconds' in pass_criteria.",
            "evidence": {},
        }
    # use absolute hub timestamp; run typically starts at t=0
    t0 = samples[0][0]  # index of first sample, not time — fetch event for time
    t0_ms = telemetry[t0]["timestamp_ms"]
    deadline_ms = t0_ms + int(within * 1000)
    for i, v in samples:
        ts = telemetry[i]["timestamp_ms"]
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if fv == target and ts <= deadline_ms:
            return {
                "passed": True,
                "requirement_id": req_id,
                "reasoning": (
                    f"{sensor!r} reached {target} at t={ts} ms, within "
                    f"the {within}s deadline."
                ),
                "evidence": {"index": i, "event": telemetry[i]},
            }
    return {
        "passed": False,
        "requirement_id": req_id,
        "reasoning": (
            f"{sensor!r} did not reach {target} within {within}s "
            f"(checked {len(samples)} samples)."
        ),
        "evidence": {"sample_count": len(samples)},
    }


def _safe_event(samples, index, value, sensor) -> dict:
    # rebuild a minimal event view from what we have
    return {"index": index, "sensor": sensor, "value": value}
