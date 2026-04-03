"""LargeRoom reverb presets.

Named parameter sets for the LargeRoom algorithm.
Each preset is a dict whose keys match LargeRoom.param_specs.

All knob values are 0-100 integers; switch values are -1, 0, or 1.
"""

from __future__ import annotations

LARGE_ROOM_PRESETS: dict[str, dict] = {
    "Live Room": {
        "decay": 50,
        "size": 65,
        "damping": 40,
        "er_level": 40,
        "mix": 45,
        "pre_delay": 20,
        "switch1": 0,   # Normal
        "switch2": 0,   # Stereo
    },
    "Orchestra Hall": {
        "decay": 75,
        "size": 80,
        "damping": 30,
        "er_level": 25,
        "mix": 55,
        "pre_delay": 35,
        "switch1": 0,   # Normal
        "switch2": 1,   # Wide
    },
}


def list_presets() -> list[str]:
    """Return sorted list of all preset names."""
    return sorted(LARGE_ROOM_PRESETS.keys())


def get_preset(name: str) -> dict:
    """Return a copy of the named preset's parameter dict.

    Args:
        name: Preset name (e.g. "Live Room", "Orchestra Hall").

    Returns:
        Dict of parameter name -> value.

    Raises:
        KeyError: If name is not a known preset.
    """
    return dict(LARGE_ROOM_PRESETS[name])
