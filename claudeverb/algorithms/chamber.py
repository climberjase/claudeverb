"""Chamber reverb algorithm for claudeverb.

Dense, warm reverb with fewer early reflection taps but more allpass
diffusers for a smooth, diffuse character with less spatial definition.

Chamber's key distinction from Room algorithms: fewer taps (4 vs 6-8)
plus more diffusers (3 vs 2) = dense, warm character.

Decay range: 1.0 - 4.0 seconds.
"""

from __future__ import annotations

from claudeverb.algorithms.room_base import RoomReverbBase


class Chamber(RoomReverbBase):
    """Chamber reverb -- dense, warm character with heavy diffusion.

    4 taps, 3 allpass diffusers, 4-channel FDN with medium prime delays.
    Fewer taps + more diffusers = smooth, warm, less spatially defined.
    """

    def _get_config(self) -> dict:
        """Return Chamber configuration."""
        return {
            # 4 taps: fewer than rooms for less spatial definition
            "tap_delays": [120, 223, 367, 521],
            "tap_gains": [0.78, 0.65, 0.52, 0.40],
            "tap_lpf_coeffs": [0.88, 0.82, 0.75, 0.68],  # warmer than rooms
            # 3 allpass diffusers: more than rooms for denser diffusion
            "diffuser_delays": [79, 113, 163],
            "diffuser_feedback": 0.55,  # slightly higher for denser diffusion
            # FDN with medium primes (~14-29ms at 48kHz)
            "fdn_delays": [659, 853, 1103, 1381],
            # Decay range in seconds (wider range for versatility)
            "decay_range": (1.0, 4.0),
            # Default parameter values
            "default_params": {
                "decay": 55,
                "size": 50,
                "damping": 55,
                "er_level": 30,
                "mix": 50,
                "pre_delay": 15,
                "switch1": 0,   # Normal
                "switch2": 0,   # Stereo
            },
        }

    @property
    def name(self) -> str:
        """Algorithm display name."""
        return "Chamber"
