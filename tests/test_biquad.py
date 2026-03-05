"""Tests for Biquad EQ filter primitive."""

import numpy as np
import pytest
from scipy.signal import freqz

from claudeverb.algorithms.filters import Biquad
from claudeverb.config import SAMPLE_RATE


def _magnitude_db(biquad: Biquad, freq_hz: float) -> float:
    """Get magnitude in dB at a specific frequency using scipy.signal.freqz."""
    b = [float(biquad.b0), float(biquad.b1), float(biquad.b2)]
    a = [1.0, float(biquad.a1), float(biquad.a2)]
    # Evaluate at a single frequency
    w = 2 * np.pi * freq_hz / SAMPLE_RATE
    _, h = freqz(b, a, worN=[w])
    mag = np.abs(h[0])
    if mag < 1e-15:
        return -300.0  # Avoid log(0)
    return 20 * np.log10(mag)


class TestBiquadLowpass:
    """Lowpass filter frequency response tests."""

    def test_minus_3db_at_cutoff(self):
        """Lowpass has -3dB gain at the cutoff frequency."""
        bq = Biquad.lowpass(1000, 0.707)
        gain = _magnitude_db(bq, 1000)
        assert gain == pytest.approx(-3.0, abs=0.5)

    def test_passes_low_frequencies(self):
        """Lowpass passes frequencies well below cutoff (~0dB at 100 Hz)."""
        bq = Biquad.lowpass(1000, 0.707)
        gain = _magnitude_db(bq, 100)
        assert gain == pytest.approx(0.0, abs=0.5)

    def test_attenuates_high_frequencies(self):
        """Lowpass significantly attenuates frequencies above cutoff."""
        bq = Biquad.lowpass(1000, 0.707)
        gain = _magnitude_db(bq, 10000)
        assert gain < -20.0


class TestBiquadHighpass:
    """Highpass filter frequency response tests."""

    def test_minus_3db_at_cutoff(self):
        """Highpass has -3dB gain at the cutoff frequency."""
        bq = Biquad.highpass(1000, 0.707)
        gain = _magnitude_db(bq, 1000)
        assert gain == pytest.approx(-3.0, abs=0.5)

    def test_passes_high_frequencies(self):
        """Highpass passes frequencies well above cutoff."""
        bq = Biquad.highpass(1000, 0.707)
        gain = _magnitude_db(bq, 10000)
        assert gain == pytest.approx(0.0, abs=0.5)

    def test_attenuates_low_frequencies(self):
        """Highpass significantly attenuates frequencies below cutoff."""
        bq = Biquad.highpass(1000, 0.707)
        gain = _magnitude_db(bq, 100)
        assert gain < -20.0


class TestBiquadNotch:
    """Notch filter frequency response tests."""

    def test_deep_null_at_center(self):
        """Notch has deep null (>-40dB) at center frequency."""
        bq = Biquad.notch(1000, 10)
        gain = _magnitude_db(bq, 1000)
        assert gain < -40.0

    def test_passes_other_frequencies(self):
        """Notch passes frequencies away from center."""
        bq = Biquad.notch(1000, 10)
        gain_low = _magnitude_db(bq, 100)
        gain_high = _magnitude_db(bq, 10000)
        assert gain_low == pytest.approx(0.0, abs=1.0)
        assert gain_high == pytest.approx(0.0, abs=1.0)


class TestBiquadBandpass:
    """Bandpass filter frequency response tests."""

    def test_peaks_at_center(self):
        """Bandpass has maximum gain at center frequency."""
        bq = Biquad.bandpass(1000, 2)
        gain_center = _magnitude_db(bq, 1000)
        gain_low = _magnitude_db(bq, 100)
        gain_high = _magnitude_db(bq, 10000)
        assert gain_center > gain_low
        assert gain_center > gain_high

    def test_attenuates_away_from_center(self):
        """Bandpass attenuates frequencies far from center."""
        bq = Biquad.bandpass(1000, 2)
        gain_low = _magnitude_db(bq, 50)
        gain_high = _magnitude_db(bq, 20000)
        assert gain_low < -10.0
        assert gain_high < -10.0


class TestBiquadParametric:
    """Parametric EQ filter frequency response tests."""

    def test_boost_at_center(self):
        """Parametric with positive gain_db boosts at center frequency."""
        bq = Biquad.parametric(1000, 2, 6.0)
        gain = _magnitude_db(bq, 1000)
        assert gain == pytest.approx(6.0, abs=0.5)

    def test_cut_at_center(self):
        """Parametric with negative gain_db cuts at center frequency."""
        bq = Biquad.parametric(1000, 2, -6.0)
        gain = _magnitude_db(bq, 1000)
        assert gain == pytest.approx(-6.0, abs=0.5)

    def test_unity_away_from_center(self):
        """Parametric returns to ~0dB away from center."""
        bq = Biquad.parametric(1000, 2, 6.0)
        gain_low = _magnitude_db(bq, 50)
        gain_high = _magnitude_db(bq, 20000)
        assert gain_low == pytest.approx(0.0, abs=1.0)
        assert gain_high == pytest.approx(0.0, abs=1.0)


class TestBiquadBehavior:
    """Biquad state and processing tests."""

    def test_set_coefficients_preserves_state(self):
        """set_coefficients() updates coefficients without resetting d1/d2."""
        bq = Biquad.lowpass(1000, 0.707)
        # Process some samples to build up state
        signal = np.random.default_rng(42).random(100).astype(np.float32)
        bq.process(signal)
        d1_before = float(bq.d1)
        d2_before = float(bq.d2)

        # Change coefficients
        bq.set_coefficients(0.5, 0.0, 0.0, 0.0, 0.0)

        # State should be preserved
        assert float(bq.d1) == d1_before
        assert float(bq.d2) == d2_before

    def test_process_sample_returns_float(self):
        """process_sample produces a Python float output."""
        bq = Biquad.lowpass(1000, 0.707)
        result = bq.process_sample(1.0)
        assert isinstance(result, float)

    def test_process_rejects_float64(self):
        """process() rejects float64 input with TypeError."""
        bq = Biquad.lowpass(1000, 0.707)
        block = np.zeros(16, dtype=np.float64)
        with pytest.raises(TypeError):
            bq.process(block)

    def test_process_returns_float32(self):
        """process() returns float32 ndarray."""
        bq = Biquad.lowpass(1000, 0.707)
        block = np.zeros(16, dtype=np.float32)
        block[0] = 1.0
        output = bq.process(block)
        assert output.dtype == np.float32

    def test_reset_zeros_state(self):
        """reset() zeros d1 and d2 state."""
        bq = Biquad.lowpass(1000, 0.707)
        signal = np.random.default_rng(42).random(100).astype(np.float32)
        bq.process(signal)
        # State should be non-zero after processing
        assert float(bq.d1) != 0.0 or float(bq.d2) != 0.0

        bq.reset()
        assert float(bq.d1) == 0.0
        assert float(bq.d2) == 0.0
