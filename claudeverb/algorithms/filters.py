"""DSP filter primitives for claudeverb.

This module contains the fundamental building blocks used by reverb algorithms:
delay lines, comb filters, allpass filters, and biquad EQ filters.
"""

from __future__ import annotations

import math

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


class AllpassFilter:
    """Schroeder allpass filter.

    Signal flow (Freeverb topology):
        v[n] = x[n] + feedback * delay_out
        y[n] = delay_out - feedback * v[n]
        delay writes v[n]

    Key property: |H(z)| = 1 for all frequencies (allpass), but phase
    varies with frequency, creating time-smearing that adds density
    to reverb tails.

    Args:
        delay_length: Delay in samples.
        feedback: Feedback/feedforward coefficient (default 0.5, Freeverb default).
    """

    __slots__ = ("_delay", "_feedback")

    def __init__(self, delay_length: int, feedback: float = 0.5) -> None:
        self._delay = DelayLine(delay_length)
        self._feedback = np.float32(feedback)

    def process_sample(self, x: float) -> float:
        """Process a single sample through the allpass filter.

        Args:
            x: Input sample.

        Returns:
            Filtered output sample as Python float.
        """
        delay_out = self._delay.read(self._delay._max_delay)
        v = np.float32(x + self._feedback * delay_out)
        y = np.float32(delay_out - self._feedback * v)
        self._delay.write(float(v))
        return float(y)

    def process(self, block: np.ndarray) -> np.ndarray:
        """Process a block of samples through the allpass filter.

        Args:
            block: Input samples, MUST be float32.

        Returns:
            Filtered output block as float32 ndarray.

        Raises:
            TypeError: If block is not float32.
        """
        if block.dtype != np.float32:
            raise TypeError(
                f"AllpassFilter.process() requires float32 input, got {block.dtype}"
            )
        output = np.empty(len(block), dtype=np.float32)
        for i in range(len(block)):
            output[i] = self.process_sample(float(block[i]))
        return output

    def reset(self) -> None:
        """Reset filter to initial state."""
        self._delay.reset()

    @property
    def feedback(self) -> float:
        """Feedback coefficient."""
        return float(self._feedback)

    @feedback.setter
    def feedback(self, value: float) -> None:
        self._feedback = np.float32(value)


class Biquad:
    """Biquad EQ filter using Direct Form II Transposed.

    Implements five standard EQ filter types via factory classmethods,
    using the Bristow-Johnson Audio EQ Cookbook formulas.

    All coefficient math uses Python's ``math`` module (maps to C math.h).
    No scipy or numpy trig functions are used in production code.

    State consists only of float32 scalars and a sample_rate int,
    ensuring direct portability to a C struct.

    Args:
        b0, b1, b2: Numerator (feedforward) coefficients.
        a1, a2: Denominator (feedback) coefficients (a0 is normalized to 1).
        sample_rate: Sample rate in Hz (default 48000).
    """

    __slots__ = ("b0", "b1", "b2", "a1", "a2", "d1", "d2", "sample_rate")

    def __init__(
        self,
        b0: float,
        b1: float,
        b2: float,
        a1: float,
        a2: float,
        sample_rate: int = 48000,
    ) -> None:
        self.b0 = np.float32(b0)
        self.b1 = np.float32(b1)
        self.b2 = np.float32(b2)
        self.a1 = np.float32(a1)
        self.a2 = np.float32(a2)
        self.d1 = np.float32(0.0)
        self.d2 = np.float32(0.0)
        self.sample_rate = sample_rate

    def process_sample(self, x: float) -> float:
        """Process a single sample through the biquad filter (DF2T).

        Args:
            x: Input sample value.

        Returns:
            Filtered output sample as Python float.
        """
        y = self.b0 * x + self.d1
        self.d1 = np.float32(self.b1 * x - self.a1 * y + self.d2)
        self.d2 = np.float32(self.b2 * x - self.a2 * y)
        return float(y)

    def process(self, block: np.ndarray) -> np.ndarray:
        """Process a block of samples through the biquad filter.

        Args:
            block: Input samples, MUST be float32.

        Returns:
            Filtered output block as float32 ndarray.

        Raises:
            TypeError: If block is not float32.
        """
        if block.dtype != np.float32:
            raise TypeError(
                f"Biquad.process() requires float32 input, got {block.dtype}"
            )
        output = np.empty(len(block), dtype=np.float32)
        for i in range(len(block)):
            output[i] = self.process_sample(float(block[i]))
        return output

    def reset(self) -> None:
        """Zero d1 and d2 filter state."""
        self.d1 = np.float32(0.0)
        self.d2 = np.float32(0.0)

    def set_coefficients(
        self, b0: float, b1: float, b2: float, a1: float, a2: float
    ) -> None:
        """Update filter coefficients without resetting state.

        This allows smooth parameter changes (e.g. EQ sweeps) without
        audible clicks from resetting the delay elements.

        Args:
            b0, b1, b2: Numerator coefficients.
            a1, a2: Denominator coefficients (a0 normalized to 1).
        """
        self.b0 = np.float32(b0)
        self.b1 = np.float32(b1)
        self.b2 = np.float32(b2)
        self.a1 = np.float32(a1)
        self.a2 = np.float32(a2)

    # -- Factory classmethods (Bristow-Johnson Audio EQ Cookbook) --

    @classmethod
    def lowpass(cls, freq: float, q: float, sample_rate: int = 48000) -> Biquad:
        """Create a lowpass biquad filter.

        Args:
            freq: Cutoff frequency in Hz.
            q: Quality factor (0.707 = Butterworth).
            sample_rate: Sample rate in Hz.

        Returns:
            Configured Biquad instance.
        """
        w0 = 2.0 * math.pi * freq / sample_rate
        cos_w0 = math.cos(w0)
        alpha = math.sin(w0) / (2.0 * q)

        b0 = (1.0 - cos_w0) / 2.0
        b1 = 1.0 - cos_w0
        b2 = (1.0 - cos_w0) / 2.0
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha

        return cls(b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0, sample_rate)

    @classmethod
    def highpass(cls, freq: float, q: float, sample_rate: int = 48000) -> Biquad:
        """Create a highpass biquad filter.

        Args:
            freq: Cutoff frequency in Hz.
            q: Quality factor (0.707 = Butterworth).
            sample_rate: Sample rate in Hz.

        Returns:
            Configured Biquad instance.
        """
        w0 = 2.0 * math.pi * freq / sample_rate
        cos_w0 = math.cos(w0)
        alpha = math.sin(w0) / (2.0 * q)

        b0 = (1.0 + cos_w0) / 2.0
        b1 = -(1.0 + cos_w0)
        b2 = (1.0 + cos_w0) / 2.0
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha

        return cls(b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0, sample_rate)

    @classmethod
    def notch(cls, freq: float, q: float, sample_rate: int = 48000) -> Biquad:
        """Create a notch (band-reject) biquad filter.

        Args:
            freq: Center frequency in Hz.
            q: Quality factor (higher = narrower notch).
            sample_rate: Sample rate in Hz.

        Returns:
            Configured Biquad instance.
        """
        w0 = 2.0 * math.pi * freq / sample_rate
        cos_w0 = math.cos(w0)
        alpha = math.sin(w0) / (2.0 * q)

        b0 = 1.0
        b1 = -2.0 * cos_w0
        b2 = 1.0
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha

        return cls(b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0, sample_rate)

    @classmethod
    def bandpass(cls, freq: float, q: float, sample_rate: int = 48000) -> Biquad:
        """Create a bandpass biquad filter.

        Args:
            freq: Center frequency in Hz.
            q: Quality factor (higher = narrower pass band).
            sample_rate: Sample rate in Hz.

        Returns:
            Configured Biquad instance.
        """
        w0 = 2.0 * math.pi * freq / sample_rate
        cos_w0 = math.cos(w0)
        alpha = math.sin(w0) / (2.0 * q)

        b0 = alpha
        b1 = 0.0
        b2 = -alpha
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha

        return cls(b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0, sample_rate)

    @classmethod
    def parametric(
        cls,
        freq: float,
        q: float,
        gain_db: float,
        sample_rate: int = 48000,
    ) -> Biquad:
        """Create a parametric (peaking) EQ biquad filter.

        Args:
            freq: Center frequency in Hz.
            q: Quality factor (higher = narrower bandwidth).
            gain_db: Boost/cut in dB at center frequency.
            sample_rate: Sample rate in Hz.

        Returns:
            Configured Biquad instance.
        """
        a_lin = 10.0 ** (gain_db / 40.0)
        w0 = 2.0 * math.pi * freq / sample_rate
        cos_w0 = math.cos(w0)
        alpha = math.sin(w0) / (2.0 * q)

        b0 = 1.0 + alpha * a_lin
        b1 = -2.0 * cos_w0
        b2 = 1.0 - alpha * a_lin
        a0 = 1.0 + alpha / a_lin
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha / a_lin

        return cls(b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0, sample_rate)
