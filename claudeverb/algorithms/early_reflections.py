"""Composable Early Reflections class for room/chamber reverb algorithms.

Implements a tapped delay line with per-tap one-pole lowpass filtering
and a cascade of allpass diffusers for density. Produces stereo output
with alternating L/R tap panning.

Designed to be composed with FDNCore in serial: ER -> FDN.

C struct equivalent:
    typedef struct {
        // Tapped delay line (single circular buffer)
        float delay_buf[MAX_TAP_DELAY + 2];
        int delay_write_idx;
        int delay_max;

        // Per-tap configuration (up to 8 taps)
        int tap_delays[8];
        float tap_gains[8];
        int num_taps;

        // Per-tap one-pole lowpass filters
        float tap_lpf_coeffs[8];
        float tap_lpf_states[8];

        // Allpass diffuser cascade (up to 3)
        float diffuser_bufs[3][MAX_DIFFUSER_DELAY];
        int diffuser_write_idx[3];
        int diffuser_delays[3];
        float diffuser_feedback;
        int num_diffusers;

        // Size scaling
        int base_tap_delays[8];
        float size_scale;

        // Normalization
        float output_norm;

        int sample_rate;
    } EarlyReflections;
"""

from __future__ import annotations

import math

import numpy as np

from claudeverb.algorithms.filters import AllpassFilter, DelayLine
from claudeverb.algorithms.dattorro_plate import OnePole


class EarlyReflections:
    """Composable early reflections with tapped delay, per-tap lowpass, and allpass diffusion.

    Produces stereo output from alternating L/R tap panning.
    Designed to be composed with FDNCore by room/chamber algorithms.

    Args:
        tap_delays: Delay in samples for each reflection tap.
        tap_gains: Amplitude gain for each tap (typically decreasing).
        tap_lpf_coeffs: OnePole coefficient per tap (higher = brighter).
        diffuser_delays: Delay lengths for allpass diffuser cascade.
        diffuser_feedback: Feedback coefficient for allpass diffusers.
        sample_rate: Sample rate in Hz.
    """

    __slots__ = (
        "_delay_line", "_tap_delays", "_base_tap_delays",
        "_tap_gains", "_tap_filters", "_diffusers",
        "_num_taps", "_output_norm", "_sample_rate",
    )

    def __init__(
        self,
        tap_delays: list[int],
        tap_gains: list[float],
        tap_lpf_coeffs: list[float],
        diffuser_delays: list[int] | None = None,
        diffuser_feedback: float = 0.5,
        sample_rate: int = 48000,
    ) -> None:
        if diffuser_delays is None:
            diffuser_delays = []

        self._num_taps = len(tap_delays)
        self._base_tap_delays = list(tap_delays)
        self._tap_delays = list(tap_delays)
        self._tap_gains = [np.float32(g) for g in tap_gains]
        self._sample_rate = sample_rate

        # Single delay line sized for max tap delay
        max_delay = max(tap_delays) + 2 if tap_delays else 4
        self._delay_line = DelayLine(max_delay)

        # Per-tap one-pole lowpass filters
        self._tap_filters = [OnePole(coeff=c) for c in tap_lpf_coeffs]

        # Allpass diffuser cascade
        self._diffusers = [
            AllpassFilter(d, feedback=diffuser_feedback)
            for d in diffuser_delays
        ]

        # Normalize output to prevent ER->FDN gain staging issues
        self._output_norm = np.float32(
            1.0 / math.sqrt(self._num_taps) if self._num_taps > 0 else 1.0
        )

    def process_sample(self, x: float) -> tuple[float, float]:
        """Process one input sample and return stereo (left, right) output.

        Tap panning: even-index taps -> right, odd-index taps -> left.
        Diffused signal is added to both channels.

        Args:
            x: Input sample value.

        Returns:
            Tuple of (left, right) output samples.
        """
        # Write input to delay line
        self._delay_line.write(x)

        # Read and process each tap
        left = 0.0
        right = 0.0
        mono_sum = 0.0

        for i in range(self._num_taps):
            # Read from delay line at tap position
            tap_out = self._delay_line.read(self._tap_delays[i])

            # Apply per-tap lowpass filter
            tap_out = self._tap_filters[i].process_sample(tap_out)

            # Apply gain
            tap_out *= float(self._tap_gains[i])

            # Alternating L/R panning: odd -> left, even -> right
            if i % 2 == 1:
                left += tap_out
            else:
                right += tap_out

            mono_sum += tap_out

        # Run mono sum through allpass diffuser cascade for density
        diffused = mono_sum
        for ap in self._diffusers:
            diffused = ap.process_sample(diffused)

        # Add diffused signal to both channels (scaled down)
        diff_contribution = diffused * 0.5
        left += diff_contribution
        right += diff_contribution

        # Normalize
        norm = float(self._output_norm)
        left *= norm
        right *= norm

        return (float(left), float(right))

    def set_size_scale(self, scale: float) -> None:
        """Scale tap positions by a factor, simulating room size change.

        Args:
            scale: Scale factor (e.g., 0.5 = smaller, 2.0 = larger).
        """
        new_delays = [max(1, int(d * scale)) for d in self._base_tap_delays]
        new_max = max(new_delays) + 2 if new_delays else 4

        # Recreate delay line if new max exceeds current capacity
        if new_max > self._delay_line.max_delay:
            self._delay_line = DelayLine(new_max)

        self._tap_delays = new_delays

    def reset(self) -> None:
        """Reset all internal state to initial values."""
        self._delay_line.reset()
        for filt in self._tap_filters:
            filt.reset()
        for ap in self._diffusers:
            ap.reset()
        # Restore base tap delays
        self._tap_delays = list(self._base_tap_delays)
