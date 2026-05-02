"""Deploy generated MicroPython to a SPIKE Prime hub."""


def spike_deploy(
    code: str,
    hub_id: str | None = None,
    slot: int = 0,
) -> dict:
    """Push generated MicroPython source to the SPIKE Prime hub.

    Use this tool to upload code produced by the draft agent. The code is
    not executed by this tool — call ``spike_run`` after a successful
    deploy.

    Args:
        code: MicroPython source to deploy. Must be syntactically valid
            for the SPIKE Prime hub's MicroPython runtime. The draft
            agent is responsible for syntactic correctness; this tool
            does not lint or transform the source.
        hub_id: Optional hub identifier when more than one hub is paired.
            If ``None``, the tool uses the default connected hub. Hub
            identifiers can be discovered out-of-band via the SPIKE App
            or ``pybricksdev``.
        slot: Program slot on the hub (0–19) to write into. Defaults to
            ``0``. Reusing a slot overwrites any program previously
            stored there.

    Returns:
        A dict with the keys:

        - ``deployed`` (bool): True if the upload completed.
        - ``slot`` (int): The slot the program was written to.
        - ``hub_id`` (str): The hub the program was written to.
        - ``error`` (str | None): Human-readable error message if the
          deploy failed, otherwise ``None``.

    Raises:
        NotImplementedError: This tool is a Week 1 stub.
    """
    raise NotImplementedError("spike_deploy is a Week 1 stub.")
