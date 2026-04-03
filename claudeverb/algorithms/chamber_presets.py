"""Chamber reverb presets.

Named parameter sets for the Chamber algorithm.
Each preset is a dict whose keys match Chamber.param_specs.

All knob values are 0-100 integers; switch values are -1, 0, or 1.
"""

from __future__ import annotations

CHAMBER_PRESETS: dict[str, dict] = {
    "Echo Chamber": {
        "decay": 60,
        "size": 55,
        "damping": 60,
        "er_level": 25,
        "mix": 50,
        "pre_delay": 10,
        "switch1": 0,   # Normal
        "switch2": 0,   # Stereo
    },
    "Bright Chamber": {
        "decay": 45,
        "size": 50,
        "damping": 30,
        "er_level": 30,
        "mix": 45,
        "pre_delay": 15,
        "switch1": 1,   # Bright
        "switch2": 0,   # Stereo
    },
}


def list_presets() -> list[str]:
    """Return sorted list of all preset names."""
    return sorted(CHAMBER_PRESETS.keys())


def get_preset(name: str) -> dict:
    """Return a copy of the named preset's parameter dict.

    Args:
        name: Preset name (e.g. "Echo Chamber", "Bright Chamber").

    Returns:
        Dict of parameter name -> value.

    Raises:
        KeyError: If name is not a known preset.
    """
    return dict(CHAMBER_PRESETS[name])
