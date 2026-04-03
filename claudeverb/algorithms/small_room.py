"""SmallRoom reverb algorithm for claudeverb.

First concrete room algorithm using the RoomReverbBase architecture.
Simulates a small concert space / chapel with moderate ER density
and warm, musical character.

Decay range: 0.5 - 2.0 seconds.
"""

from __future__ import annotations

from claudeverb.algorithms.room_base import RoomReverbBase


class SmallRoom(RoomReverbBase):
    """Small Room reverb -- warm, musical character with moderate ER density.

    6 taps, 2 allpass diffusers, 4-channel FDN with smaller prime delays.
    """

    def _get_config(self) -> dict:
        """Return Small Room configuration."""
        return {
            # 6 taps: ~1.2ms to ~6.4ms at 48kHz
            "tap_delays": [58, 97, 134, 181, 241, 307],
            "tap_gains": [0.84, 0.71, 0.62, 0.53, 0.42, 0.33],
            "tap_lpf_coeffs": [0.95, 0.92, 0.88, 0.84, 0.78, 0.72],
            # 2 allpass diffusers
            "diffuser_delays": [67, 101],
            "diffuser_feedback": 0.5,
            # FDN with smaller primes (~9-20ms at 48kHz)
            "fdn_delays": [443, 577, 751, 941],
            # Decay range in seconds
            "decay_range": (0.5, 2.0),
            # Default parameter values
            "default_params": {
                "decay": 45,
                "size": 40,
                "damping": 45,
                "er_level": 40,
                "mix": 50,
                "pre_delay": 5,
                "switch1": 0,   # Normal
                "switch2": 0,   # Stereo
            },
        }

    @property
    def name(self) -> str:
        """Algorithm display name."""
        return "Small Room"
