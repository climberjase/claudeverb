"""SmallRoom reverb presets.

Named parameter sets for the SmallRoom algorithm.
Each preset is a dict whose keys match SmallRoom.param_specs.

All knob values are 0-100 integers; switch values are -1, 0, or 1.
"""

from __future__ import annotations

SMALL_ROOM_PRESETS: dict[str, dict] = {
    "Vocal Booth": {
        "decay": 25,
        "size": 25,
        "damping": 60,
        "er_level": 55,
        "mix": 40,
        "pre_delay": 0,
        "switch1": 0,   # Normal
        "switch2": 0,   # Stereo
    },
    "Drum Room": {
        "decay": 55,
        "size": 55,
        "damping": 35,
        "er_level": 35,
        "mix": 55,
        "pre_delay": 8,
        "switch1": 0,   # Normal
        "switch2": 0,   # Stereo
    },
}


def list_presets() -> list[str]:
    """Return sorted list of all preset names."""
    return sorted(SMALL_ROOM_PRESETS.keys())


def get_preset(name: str) -> dict:
    """Return a copy of the named preset's parameter dict.

    Args:
        name: Preset name (e.g. "Vocal Booth", "Drum Room").

    Returns:
        Dict of parameter name -> value.

    Raises:
        KeyError: If name is not a known preset.
    """
    return dict(SMALL_ROOM_PRESETS[name])
