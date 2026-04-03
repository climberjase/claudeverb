"""LargeRoom reverb algorithm for claudeverb.

Spacious room reverb with 8-tap early reflections, 2 allpass diffusers,
and a 4-channel FDN with large prime delays for extended decay.

Decay range: 1.0 - 3.5 seconds.
"""

from __future__ import annotations

from claudeverb.algorithms.room_base import RoomReverbBase


class LargeRoom(RoomReverbBase):
    """Large Room reverb -- spacious, balanced character with 8-tap ER.

    8 taps, 2 allpass diffusers, 4-channel FDN with larger prime delays.
    Longer decay range than SmallRoom for bigger acoustic spaces.
    """

    def _get_config(self) -> dict:
        """Return Large Room configuration."""
        return {
            # 8 taps: ~4ms to ~31ms at 48kHz (wider spread for spaciousness)
            "tap_delays": [192, 311, 431, 587, 769, 953, 1201, 1487],
            "tap_gains": [0.80, 0.72, 0.64, 0.55, 0.47, 0.40, 0.33, 0.27],
            "tap_lpf_coeffs": [0.93, 0.89, 0.85, 0.80, 0.75, 0.70, 0.64, 0.58],
            # 2 allpass diffusers
            "diffuser_delays": [83, 127],
            "diffuser_feedback": 0.5,
            # FDN with larger primes (~18-39ms at 48kHz)
            "fdn_delays": [887, 1151, 1493, 1879],
            # Decay range in seconds (longer than SmallRoom)
            "decay_range": (1.0, 3.5),
            # Default parameter values
            "default_params": {
                "decay": 50,
                "size": 60,
                "damping": 40,
                "er_level": 35,
                "mix": 50,
                "pre_delay": 20,
                "switch1": 0,   # Normal
                "switch2": 0,   # Stereo
            },
        }

    @property
    def name(self) -> str:
        """Algorithm display name."""
        return "Large Room"
