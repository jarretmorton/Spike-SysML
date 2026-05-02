"""Execute a deployed program on the SPIKE Prime hub and capture telemetry."""


def spike_run(
    slot: int = 0,
    timeout_seconds: float = 30.0,
    hub_id: str | None = None,
) -> dict:
    """Run a program on the SPIKE Prime hub and stream sensor telemetry.

    Use this tool after a successful ``spike_deploy``. The tool blocks
    until the program completes, the timeout expires, or the hub
    disconnects. Telemetry is captured for the entire run window.

    Args:
        slot: Program slot to execute. Defaults to ``0``, which matches
            ``spike_deploy``'s default slot.
        timeout_seconds: Maximum runtime before the run is terminated
            from the host side. Defaults to 30 seconds. Use a longer
            timeout for tests that involve waits or long traverses.
        hub_id: Optional hub identifier; see ``spike_deploy``.

    Returns:
        A dict with the keys:

        - ``completed`` (bool): True if the program ran to its own end,
          False if the host timed it out or the hub disconnected.
        - ``duration_seconds`` (float): Wall-clock duration from the
          start of execution to the end of the run window.
        - ``telemetry`` (list): Time-ordered list of telemetry events.
          Each event is a dict with ``timestamp_ms`` (int, since run
          start), ``sensor`` (str, e.g. ``"motor_a"``, ``"color_1"``),
          and ``value`` (any JSON-serialisable type appropriate to the
          sensor).
        - ``stdout`` (str): Anything the program wrote to standard
          output during the run.
        - ``error`` (str | None): Human-readable error if the run did
          not start, otherwise ``None``. A program that runs to
          completion but fails its test condition is *not* an error
          here — that distinction is made by ``test_eval``.

    Raises:
        NotImplementedError: This tool is a Week 1 stub.
    """
    raise NotImplementedError("spike_run is a Week 1 stub.")
