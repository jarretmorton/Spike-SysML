"""Score a hardware run against the requirement it implements."""


def test_eval(
    run_result: dict,
    requirement: dict,
) -> dict:
    """Decide whether a run satisfies the requirement it was built to test.

    This tool is the critic in the evaluator-optimizer loop. It is the
    only place where a pass/fail verdict is produced; no other tool
    should infer success from telemetry. If the verdict is ``failed``
    and the iteration budget is not exhausted, the loop returns to the
    draft agent with the reasoning attached.

    Args:
        run_result: The full dict returned by ``spike_run``. Must
            include the ``telemetry`` and ``completed`` fields.
        requirement: A single requirement object from the validated
            SysML v2 model. Must include ``id``, ``text``, and
            ``pass_criteria``. The ``pass_criteria`` field is the
            machine-checkable condition the run must satisfy
            (e.g., ``{"sensor": "color_1", "op": "==", "value": "red",
            "within_seconds": 5.0}``).

    Returns:
        A dict with the keys:

        - ``passed`` (bool): True if the run satisfied the requirement.
        - ``requirement_id`` (str): Echoes ``requirement["id"]`` for
          traceability.
        - ``reasoning`` (str): Human-readable explanation of how the
          verdict was reached. This text is the most useful signal back
          to the draft agent on a failure.
        - ``evidence`` (dict): References into ``run_result["telemetry"]``
          that support the verdict — e.g., the indices of telemetry
          events that triggered the pass, or the lack thereof.

    Raises:
        NotImplementedError: This tool is a Week 1 stub.
    """
    raise NotImplementedError("test_eval is a Week 1 stub.")
