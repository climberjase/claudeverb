"""Dattorro Asymmetric Tank presets.

Named parameter sets covering the Asymmetric Tank reverb parameter space.
Each preset is a dict whose keys match DattorroAsymmetric.param_specs.

All knob values are 0-100 integers; switch values are -1, 0, or 1.
"""

from __future__ import annotations

ASYMMETRIC_PRESETS: dict[str, dict] = {
    "Wide Plate": {
        "decay": 60,
        "spread": 60,
        "damping": 30,
        "mod": 30,
        "mix": 50,
        "pre_delay": 15,
        "switch1": 0,   # Normal
        "switch2": 0,   # Stereo
    },
    "Ultra-Wide": {
        "decay": 80,
        "spread": 100,
        "damping": 25,
        "mod": 40,
        "mix": 55,
        "pre_delay": 10,
        "switch1": 0,   # Normal
        "switch2": 1,   # Wide
    },
    "Subtle Width": {
        "decay": 45,
        "spread": 25,
        "damping": 40,
        "mod": 20,
        "mix": 40,
        "pre_delay": 10,
        "switch1": 0,   # Normal
        "switch2": 0,   # Stereo
    },
}


def list_presets() -> list[str]:
    """Return sorted list of all preset names."""
    return sorted(ASYMMETRIC_PRESETS.keys())


def get_preset(name: str) -> dict:
    """Return a copy of the named preset's parameter dict.

    Args:
        name: Preset name (e.g. "Wide Plate", "Ultra-Wide").

    Returns:
        Dict of parameter name -> value.

    Raises:
        KeyError: If name is not a known preset.
    """
    return dict(ASYMMETRIC_PRESETS[name])
