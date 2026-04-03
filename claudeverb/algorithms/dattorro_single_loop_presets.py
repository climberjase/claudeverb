"""Dattorro Single-Loop Tank presets.

Named parameter sets covering the Single-Loop reverb parameter space.
Each preset is a dict whose keys match DattorroSingleLoop.param_specs.

All knob values are 0-100 integers; switch values are -1, 0, or 1.
"""

from __future__ import annotations

SINGLE_LOOP_PRESETS: dict[str, dict] = {
    "Tight Room": {
        "decay": 35,
        "loop_length": 15,
        "damping": 70,
        "mod": 15,
        "mix": 45,
        "pre_delay": 5,
        "switch1": 0,   # Normal
        "switch2": 0,   # Stereo
    },
    "Dense Hall": {
        "decay": 70,
        "loop_length": 80,
        "damping": 35,
        "mod": 40,
        "mix": 50,
        "pre_delay": 20,
        "switch1": 0,   # Normal
        "switch2": 1,   # Wide
    },
    "Infinite Loop": {
        "decay": 95,
        "loop_length": 100,
        "damping": 15,
        "mod": 55,
        "mix": 65,
        "pre_delay": 10,
        "switch1": 0,   # Normal
        "switch2": 0,   # Stereo
    },
}


def list_presets() -> list[str]:
    """Return sorted list of all preset names."""
    return sorted(SINGLE_LOOP_PRESETS.keys())


def get_preset(name: str) -> dict:
    """Return a copy of the named preset's parameter dict.

    Args:
        name: Preset name (e.g. "Tight Room", "Dense Hall").

    Returns:
        Dict of parameter name -> value.

    Raises:
        KeyError: If name is not a known preset.
    """
    return dict(SINGLE_LOOP_PRESETS[name])
