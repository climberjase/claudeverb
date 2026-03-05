"""DSP filter primitives for claudeverb.

This module contains the fundamental building blocks used by reverb algorithms:
delay lines, comb filters, and allpass filters.
"""

from __future__ import annotations

import numpy as np


class DelayLine:
    """Fixed-size circular buffer delay line.

    Supports integer and fractional delay via linear interpolation.
    All audio must be float32 -- float64 is explicitly rejected.

    Convention: In each sample cycle of process(), read BEFORE write,
    so a delay of N means output appears N samples after input.

    Args:
        max_delay: Maximum delay in samples. Buffer is allocated once
                   at this size (no dynamic allocation).
    """

    __slots__ = ("_buffer", "_write_index", "_max_delay")

    def __init__(self, max_delay: int) -> None:
        if max_delay < 1:
            raise ValueError("max_delay must be >= 1")
        self._max_delay = max_delay
        self._buffer = np.zeros(max_delay, dtype=np.float32)
        self._write_index = 0

    def write(self, sample: float) -> None:
        """Write a single sample into the delay line and advance the write head."""
        self._buffer[self._write_index] = np.float32(sample)
        self._write_index = (self._write_index + 1) % self._max_delay

    def read(self, delay: float) -> float:
        """Read from the delay line at a (possibly fractional) delay.

        For integer delays, returns the exact stored value.
        For fractional delays, linearly interpolates between adjacent samples.

        Args:
            delay: Delay in samples (1.0 = one sample ago). Must be >= 0
                   and <= max_delay.

        Returns:
            Interpolated sample value as a Python float.
        """
        # Compute read position relative to write head
        # _write_index points to the NEXT write position, so the most
        # recently written sample is at _write_index - 1.
        # A delay of 1 should read _write_index - 1 (last written).
        read_pos = self._write_index - delay

        # Integer and fractional parts
        idx0 = int(np.floor(read_pos))
        frac = read_pos - idx0

        # Wrap indices into valid buffer range
        idx0_wrapped = idx0 % self._max_delay
        idx1_wrapped = (idx0 + 1) % self._max_delay

        # Linear interpolation
        s0 = self._buffer[idx0_wrapped]
        s1 = self._buffer[idx1_wrapped]
        return float(s0 + frac * (s1 - s0))

    def process(self, block: np.ndarray, delay: float | None = None) -> np.ndarray:
        """Process a block of samples through the delay line.

        Reads before writing each sample (so delay of N means output is
        N samples behind input).

        Args:
            block: Input samples, MUST be float32. TypeError raised otherwise.
            delay: Delay in samples. Defaults to max_delay if not specified.

        Returns:
            Delayed output block as float32 ndarray.

        Raises:
            TypeError: If block is not float32.
        """
        if block.dtype != np.float32:
            raise TypeError(
                f"DelayLine.process() requires float32 input, got {block.dtype}"
            )

        if delay is None:
            delay = float(self._max_delay)

        output = np.empty(len(block), dtype=np.float32)
        for i in range(len(block)):
            output[i] = self.read(delay)
            self.write(block[i])

        return output

    def reset(self) -> None:
        """Zero the buffer and reset the write index."""
        self._buffer[:] = 0.0
        self._write_index = 0

    @property
    def max_delay(self) -> int:
        """Maximum delay in samples."""
        return self._max_delay


class CombFilter:
    """Lowpass-feedback comb filter (Freeverb topology).

    Signal flow: y[n] = x[n] + feedback * lp[n]
    where lp[n] is a one-pole lowpass of the delay output,
    and the delay line stores y[n] (the output).

    This produces decaying echoes at multiples of delay_length,
    with the damp parameter controlling high-frequency rolloff in echoes.

    Args:
        delay_length: Delay in samples (sets echo interval).
        feedback: Feedback coefficient controlling decay rate (0..1).
        damp: Damping coefficient for one-pole lowpass (0=none, 1=full).
    """

    __slots__ = ("_delay", "_feedback", "_damp1", "_damp2", "_filterstore")

    def __init__(self, delay_length: int, feedback: float = 0.5, damp: float = 0.5) -> None:
        self._delay = DelayLine(delay_length)
        self._feedback = np.float32(feedback)
        self._damp1 = np.float32(1.0 - damp)
        self._damp2 = np.float32(damp)
        self._filterstore = np.float32(0.0)

    def process_sample(self, x: float) -> float:
        """Process a single sample through the comb filter.

        Args:
            x: Input sample.

        Returns:
            Filtered output sample as Python float.
        """
        delay_out = self._delay.read(self._delay._max_delay)
        self._filterstore = np.float32(
            delay_out * self._damp1 + self._filterstore * self._damp2
        )
        output = np.float32(x + self._feedback * self._filterstore)
        self._delay.write(float(output))
        return float(output)

    def process(self, block: np.ndarray) -> np.ndarray:
        """Process a block of samples through the comb filter.

        Args:
            block: Input samples, MUST be float32.

        Returns:
            Filtered output block as float32 ndarray.

        Raises:
            TypeError: If block is not float32.
        """
        if block.dtype != np.float32:
            raise TypeError(
                f"CombFilter.process() requires float32 input, got {block.dtype}"
            )
        output = np.empty(len(block), dtype=np.float32)
        for i in range(len(block)):
            output[i] = self.process_sample(float(block[i]))
        return output

    def reset(self) -> None:
        """Reset filter to initial state."""
        self._delay.reset()
        self._filterstore = np.float32(0.0)

    @property
    def feedback(self) -> float:
        """Feedback coefficient."""
        return float(self._feedback)

    @feedback.setter
    def feedback(self, value: float) -> None:
        self._feedback = np.float32(value)

    @property
    def damp(self) -> float:
        """Damping coefficient."""
        return float(self._damp2)

    @damp.setter
    def damp(self, value: float) -> None:
        self._damp1 = np.float32(1.0 - value)
        self._damp2 = np.float32(value)
