"""Dattorro Triple-Diffuser presets.

Named parameter sets covering the Triple-Diffuser reverb parameter space.
Each preset is a dict whose keys match DattorroTripleDiffuser.param_specs.

All knob values are 0-100 integers; switch values are -1, 0, or 1.
"""

from __future__ import annotations

TRIPLE_DIFFUSER_PRESETS: dict[str, dict] = {
    "Smooth Pad": {
        "decay": 80,
        "diffusion_density": 90,
        "damping": 25,
        "mod": 40,
        "mix": 55,
        "pre_delay": 15,
        "switch1": 0,   # Normal
        "switch2": 0,   # Stereo
    },
    "Soft Vocal": {
        "decay": 50,
        "diffusion_density": 60,
        "damping": 15,
        "mod": 20,
        "mix": 40,
        "pre_delay": 20,
        "switch1": 0,   # Normal
        "switch2": 0,   # Stereo
    },
    "Ultra-Smooth": {
        "decay": 90,
        "diffusion_density": 100,
        "damping": 20,
        "mod": 50,
        "mix": 60,
        "pre_delay": 10,
        "switch1": 0,   # Normal
        "switch2": 1,   # Wide
    },
}


def list_presets() -> list[str]:
    """Return sorted list of all preset names."""
    return sorted(TRIPLE_DIFFUSER_PRESETS.keys())


def get_preset(name: str) -> dict:
    """Return a copy of the named preset's parameter dict.

    Args:
        name: Preset name (e.g. "Smooth Pad", "Soft Vocal").

    Returns:
        Dict of parameter name -> value.

    Raises:
        KeyError: If name is not a known preset.
    """
    return dict(TRIPLE_DIFFUSER_PRESETS[name])
