"""FDN (Feedback Delay Network) reverb algorithm for claudeverb.

Implements a 4-channel Hadamard FDN with coprime delay lines,
per-channel damping, LFO modulation, and DC blocking.

FDNCore is the composable DSP engine; FDNReverb wraps it as a
ReverbAlgorithm for the UI/registry (implemented in Plan 02).

C struct equivalent:
    typedef struct {
        // 4 delay line buffers (circular, fixed-size)
        float delay_buf_0[MAX_DELAY_0];
        float delay_buf_1[MAX_DELAY_1];
        float delay_buf_2[MAX_DELAY_2];
        float delay_buf_3[MAX_DELAY_3];
        int delay_write_idx[4];
        int delay_max[4];

        // 4 one-pole damping filter states
        float damp_coeff[4];
        float damp_state[4];

        // 4 DC blocker states
        float dc_r;
        float dc_x_prev[4];
        float dc_y_prev[4];

        // LFO state
        float lfo_phase;
        float lfo_phase_inc;
        float mod_depth;

        // Gains and delays
        float channel_gains[4];
        int base_delays[4];
        int current_delays[4];
        float rt60;

        // Config
        int sample_rate;
        int frozen;
    } FDNCore;
"""

from __future__ import annotations

import math

import numpy as np

from claudeverb.algorithms.filters import DelayLine
from claudeverb.algorithms.dattorro_plate import OnePole, DCBlocker


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

BASE_DELAYS = [601, 773, 1009, 1249]  # all prime, coprime, ~12-26ms at 48kHz
SAMPLE_RATE = 48000
MAX_MOD_EXCURSION = 16  # max LFO excursion in samples


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def hadamard_4(a: float, b: float, c: float, d: float) -> tuple[float, float, float, float]:
    """Fast 4-point Walsh-Hadamard Transform (butterfly).

    Two-stage butterfly with 0.5 normalization factor.
    The transform is its own inverse: H(H(x)) = x.

    Returns:
        Tuple of 4 floats after Hadamard mixing.
    """
    # Stage 1: pairs
    s0 = a + b
    s1 = a - b
    s2 = c + d
    s3 = c - d

    # Stage 2: cross-pairs + normalize by 0.5
    r0 = (s0 + s2) * 0.5
    r1 = (s1 + s3) * 0.5
    r2 = (s0 - s2) * 0.5
    r3 = (s1 - s3) * 0.5

    return (r0, r1, r2, r3)


def rt60_to_gain(rt60_seconds: float, delay_samples: int, sample_rate: int = 48000) -> float:
    """Convert RT60 decay time to per-loop feedback gain.

    Formula: 10^(-3 * delay_samples / (rt60_seconds * sample_rate))

    Args:
        rt60_seconds: Desired RT60 in seconds.
        delay_samples: Delay line length in samples.
        sample_rate: Sample rate in Hz.

    Returns:
        Feedback gain clamped to [0.0, 0.9999].
    """
    if rt60_seconds <= 0.0:
        return 0.0
    gain = 10.0 ** (-3.0 * delay_samples / (rt60_seconds * sample_rate))
    return min(gain, 0.9999)


# ---------------------------------------------------------------------------
# FDNCore class
# ---------------------------------------------------------------------------

class FDNCore:
    """Composable 4-channel Hadamard Feedback Delay Network.

    Can be used independently or composed into higher-level algorithms.
    Uses coprime prime delay lengths for maximal echo density.

    Args:
        base_delays: List of 4 delay lengths in samples (default: BASE_DELAYS).
        sample_rate: Sample rate in Hz (default: 48000).
    """

    __slots__ = (
        "_delay_lines", "_damping_filters", "_dc_blockers",
        "_base_delays", "_current_delays", "_channel_gains",
        "_lfo_phase", "_lfo_phase_inc", "_mod_depth",
        "_rt60", "_sample_rate", "_frozen",
    )

    def __init__(self, base_delays: list[int] | None = None, sample_rate: int = 48000) -> None:
        if base_delays is None:
            base_delays = list(BASE_DELAYS)

        self._base_delays = list(base_delays)
        self._current_delays = list(base_delays)
        self._sample_rate = sample_rate

        # Create 4 delay lines with extra room for modulation
        self._delay_lines = [
            DelayLine(d + MAX_MOD_EXCURSION + 2) for d in base_delays
        ]

        # Create 4 one-pole damping filters (default coefficient 0.3)
        self._damping_filters = [OnePole(0.3) for _ in range(4)]

        # Create 4 DC blockers
        self._dc_blockers = [DCBlocker() for _ in range(4)]

        # LFO state
        self._lfo_phase = 0.0
        self._lfo_phase_inc = 2.0 * math.pi * 0.7 / sample_rate  # 0.7 Hz
        self._mod_depth = 0.0  # samples

        # Feedback gains
        self._rt60 = 2.0  # default 2 seconds
        self._channel_gains = [0.0] * 4
        self._frozen = False

        # Compute initial gains
        self._recompute_gains()

    def _recompute_gains(self) -> None:
        """Recompute channel gains from current RT60 and delay lengths."""
        if self._frozen:
            self._channel_gains = [1.0] * 4
        else:
            self._channel_gains = [
                rt60_to_gain(self._rt60, d, self._sample_rate)
                for d in self._current_delays
            ]

    def process_sample(self, inputs: list[float]) -> list[float]:
        """Process one sample through the 4-channel FDN.

        Args:
            inputs: List of 4 input samples, one per channel.

        Returns:
            List of 4 output samples (pre-mixing tap points).
        """
        # Compute LFO value
        lfo_val = math.sin(self._lfo_phase) * self._mod_depth

        # Read from delay lines with LFO modulation
        # Channels 0,2 get +lfo, channels 1,3 get -lfo
        outputs = [0.0] * 4
        for ch in range(4):
            delay = float(self._current_delays[ch])
            if ch in (0, 2):
                delay += lfo_val
            else:
                delay -= lfo_val
            delay = max(1.0, delay)
            outputs[ch] = self._delay_lines[ch].read(delay)

        # Advance LFO phase
        self._lfo_phase += self._lfo_phase_inc
        if self._lfo_phase >= 2.0 * math.pi:
            self._lfo_phase -= 2.0 * math.pi

        # Per-channel processing: damping -> DC blocker -> gain
        processed = [0.0] * 4
        for ch in range(4):
            val = self._damping_filters[ch].process_sample(outputs[ch])
            val = self._dc_blockers[ch].process_sample(val)
            val *= self._channel_gains[ch]
            processed[ch] = val

        # Hadamard butterfly mixing
        mixed = hadamard_4(processed[0], processed[1], processed[2], processed[3])

        # Write back to delay lines: input + mixed feedback
        for ch in range(4):
            self._delay_lines[ch].write(inputs[ch] + mixed[ch])

        # Return PRE-mixing outputs (tap points for stereo output)
        return outputs

    def set_decay(self, rt60_seconds: float) -> None:
        """Set the RT60 decay time in seconds."""
        self._rt60 = rt60_seconds
        self._recompute_gains()

    def set_damping(self, coefficient: float) -> None:
        """Set damping for all channels (0=bright, 1=dark)."""
        for f in self._damping_filters:
            f._coeff = np.float32(coefficient)

    def set_modulation(self, depth: float, rate: float) -> None:
        """Set LFO modulation depth and rate.

        Args:
            depth: Modulation depth in samples (0 to MAX_MOD_EXCURSION).
            rate: LFO rate in Hz.
        """
        self._mod_depth = min(depth, MAX_MOD_EXCURSION)
        self._lfo_phase_inc = 2.0 * math.pi * rate / self._sample_rate

    def set_size(self, scale: float) -> None:
        """Scale delay lengths by a factor.

        Args:
            scale: Scale factor (e.g., 0.5 = half size, 2.0 = double).
        """
        self._current_delays = [
            max(1, int(d * scale)) for d in self._base_delays
        ]
        self._recompute_gains()

    def set_freeze(self, frozen: bool) -> None:
        """Enable or disable freeze mode (infinite sustain)."""
        self._frozen = frozen
        self._recompute_gains()

    def reset(self) -> None:
        """Reset all internal state."""
        for dl in self._delay_lines:
            dl.reset()
        for f in self._damping_filters:
            f.reset()
        for dc in self._dc_blockers:
            dc.reset()
        self._lfo_phase = 0.0
        self._current_delays = list(self._base_delays)
        self._recompute_gains()


# ---------------------------------------------------------------------------
# FDNReverb placeholder (full implementation in Plan 02)
# ---------------------------------------------------------------------------

class FDNReverb:
    """Placeholder for FDN ReverbAlgorithm wrapper.

    Full implementation (ReverbAlgorithm subclass with stereo output,
    parameter mapping, presets, and C export) will be added in Plan 02.
    This stub exists so the test scaffold can import the name.
    """

    def __init__(self) -> None:
        raise NotImplementedError(
            "FDNReverb is a placeholder -- full implementation in Plan 02"
        )
