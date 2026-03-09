"""Dattorro Plate reverb presets.

Named parameter sets covering the Dattorro reverb parameter space.
Each preset is a dict whose keys match DattorroPlate.param_specs
(minus 'mix', which is controlled by the engine).

All knob values are 0-100 integers; switch values are -1, 0, or 1.
"""

from __future__ import annotations

DATTORRO_PRESETS: dict[str, dict] = {
    "Small Plate": {
        "decay": 30,
        "bandwidth": 85,
        "tank_damping": 45,
        "diffusion": 90,
        "pre_delay": 3,
        "mod_depth": 15,
        "switch1": 0,
        "switch2": 0,
    },
    "Large Hall": {
        "decay": 80,
        "bandwidth": 55,
        "tank_damping": 15,
        "diffusion": 65,
        "pre_delay": 35,
        "mod_depth": 45,
        "switch1": 0,
        "switch2": 1,
    },
    "Bright Room": {
        "decay": 40,
        "bandwidth": 95,
        "tank_damping": 10,
        "diffusion": 80,
        "pre_delay": 8,
        "mod_depth": 25,
        "switch1": 0,
        "switch2": 0,
    },
    "Dark Chamber": {
        "decay": 65,
        "bandwidth": 40,
        "tank_damping": 60,
        "diffusion": 75,
        "pre_delay": 15,
        "mod_depth": 30,
        "switch1": 0,
        "switch2": 0,
    },
    "Shimmer Pad": {
        "decay": 90,
        "bandwidth": 70,
        "tank_damping": 25,
        "diffusion": 85,
        "pre_delay": 20,
        "mod_depth": 50,
        "switch1": 1,
        "switch2": 1,
    },
    "Frozen Space": {
        "decay": 95,
        "bandwidth": 60,
        "tank_damping": 20,
        "diffusion": 80,
        "pre_delay": 0,
        "mod_depth": 60,
        "switch1": -1,
        "switch2": 1,
    },
}


def list_presets() -> list[str]:
    """Return sorted list of all preset names."""
    return sorted(DATTORRO_PRESETS.keys())


def get_preset(name: str) -> dict:
    """Return a copy of the named preset's parameter dict.

    Args:
        name: Preset name (e.g. "Small Plate", "Large Hall").

    Returns:
        Dict of parameter name -> value.

    Raises:
        KeyError: If name is not a known preset.
    """
    return dict(DATTORRO_PRESETS[name])
