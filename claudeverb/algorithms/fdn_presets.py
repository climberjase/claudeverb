"""FDN Reverb presets.

Named parameter sets covering the FDN reverb parameter space.
Each preset is a dict whose keys match FDNReverb.param_specs.

All knob values are 0-100 integers; switch values are -1, 0, or 1.
"""

from __future__ import annotations

FDN_PRESETS: dict[str, dict] = {
    "Small Hall": {
        "decay_time": 35,
        "size": 30,
        "damping": 55,
        "modulation": 20,
        "mix": 60,
        "pre_delay": 10,
        "switch1": 0,   # Normal
        "switch2": 0,   # Stereo
    },
    "Large Hall": {
        "decay_time": 70,
        "size": 65,
        "damping": 35,
        "modulation": 40,
        "mix": 50,
        "pre_delay": 25,
        "switch1": 0,   # Normal
        "switch2": 1,   # Wide
    },
    "Cathedral": {
        "decay_time": 85,
        "size": 85,
        "damping": 20,
        "modulation": 50,
        "mix": 45,
        "pre_delay": 35,
        "switch1": 0,   # Normal
        "switch2": 1,   # Wide
    },
    "Ambient": {
        "decay_time": 90,
        "size": 50,
        "damping": 60,
        "modulation": 70,
        "mix": 70,
        "pre_delay": 15,
        "switch1": 0,   # Normal
        "switch2": 0,   # Stereo
    },
}


def list_presets() -> list[str]:
    """Return sorted list of all preset names."""
    return sorted(FDN_PRESETS.keys())


def get_preset(name: str) -> dict:
    """Return a copy of the named preset's parameter dict.

    Args:
        name: Preset name (e.g. "Small Hall", "Cathedral").

    Returns:
        Dict of parameter name -> value.

    Raises:
        KeyError: If name is not a known preset.
    """
    return dict(FDN_PRESETS[name])
