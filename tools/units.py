"""Unit conversion at the SysML(SI) <-> wire(sensor-native) boundary.

The SysML models are SI (metres, seconds, m/s**2). Telemetry channels and the
pass_criteria that grade them are in each channel's native sensor unit (see
docs/wire_contract.md section 2.2 -- that section is the human-readable
authority; the table below mirrors it, keep them in sync). `test_eval` never
converts, so any SI model parameter that becomes a `pass_criteria.value` must
be converted HERE first.

This is the host-side half of the boundary, used by the composition step. The
on-hub half lives inline in each mission's labelled unit-boundary block; a
shared import is impossible across the host-CPython / on-hub-MicroPython split,
so this table (mirrored in the wire contract) is what both sides convert toward.
"""
from __future__ import annotations


# Canonical unit per channel. A key ending in "_" matches a channel family by
# prefix (e.g. "distance_" covers "distance_left", "distance_right").
# Mirrors docs/wire_contract.md section 2.2.
_CHANNEL_UNIT = {
    "clearance_mm": "mm",
    "distance_":    "mm",        # prefix family
    "reflection":   "percent",
    "speed_mps":    "m/s",
}

# SI -> canonical-unit scale factor, keyed by canonical unit.
_SI_TO_UNIT = {
    "mm":      1000.0,           # metres -> millimetres
    "m/s":     1.0,             # already SI
    "percent": 1.0,             # 0..100 dimensionless; sensor already reports %
}


def unit_for(channel: str) -> str:
    """Canonical unit for a telemetry channel.

    Exact channel match first, then the longest matching prefix family
    (so "distance_left" resolves via the "distance_" entry). Raises KeyError
    for an unregistered channel rather than guessing -- an unknown unit is
    exactly the silent-mismatch failure this module exists to prevent.
    """
    if channel in _CHANNEL_UNIT:
        return _CHANNEL_UNIT[channel]
    families = [k for k in _CHANNEL_UNIT if k.endswith("_") and channel.startswith(k)]
    if families:
        return _CHANNEL_UNIT[max(families, key=len)]
    raise KeyError(
        "no canonical unit registered for channel %r; add it to tools/units.py "
        "and docs/wire_contract.md section 2.2." % channel
    )


def to_wire(value_si: float, channel: str) -> float:
    """Convert an SI model quantity to the wire value for `channel`.

    Use when composition emits a `pass_criteria.value` from a SysML model
    parameter, so the criterion lands in the channel's canonical unit and
    `test_eval`'s raw comparison is valid. Example: a 0.040 m collision margin
    graded against ``clearance_mm`` returns ``40.0``.
    """
    return value_si * _SI_TO_UNIT[unit_for(channel)]
