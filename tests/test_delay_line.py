"""Tests for DelayLine DSP primitive."""

import numpy as np
import pytest

from claudeverb.algorithms.filters import DelayLine


class TestDelayLineBasic:
    """Core delay line behavior tests."""

    def test_impulse_at_correct_delay(self):
        """Impulse written at sample 0 appears at exactly sample N when reading at delay N."""
        delay_samples = 10
        dl = DelayLine(max_delay=64)

        # Write impulse at sample 0
        dl.write(1.0)

        # Advance by writing zeros for delay_samples - 1 more samples
        # (we already wrote 1 sample), reading each time
        outputs = []
        outputs.append(dl.read(delay_samples))  # read after first write

        for _ in range(delay_samples - 1):
            dl.write(0.0)
            outputs.append(dl.read(delay_samples))

        # After writing exactly delay_samples total samples (1 impulse + N-1 zeros),
        # the impulse should now be at position delay_samples behind write head
        dl.write(0.0)
        result = dl.read(delay_samples)

        assert result == pytest.approx(1.0), (
            f"Impulse should appear at delay {delay_samples}, got {result}"
        )

    def test_fractional_delay_interpolation(self):
        """Reading at fractional delay returns linearly interpolated value."""
        dl = DelayLine(max_delay=64)

        # Write known values
        dl.write(0.0)
        dl.write(1.0)
        dl.write(0.0)

        # Read at fractional position 1.5 should interpolate between
        # the sample at delay 1 (0.0) and delay 2 (1.0)
        result = dl.read(1.5)
        assert result == pytest.approx(0.5), (
            f"Fractional delay 1.5 should interpolate to 0.5, got {result}"
        )

    def test_integer_delay_exact_value(self):
        """Reading at integer delay returns exact stored value (no interpolation artifact)."""
        dl = DelayLine(max_delay=64)

        dl.write(0.0)
        dl.write(0.5)
        dl.write(1.0)

        # Integer delay should return exact value
        assert dl.read(1.0) == pytest.approx(1.0)
        assert dl.read(2.0) == pytest.approx(0.5)
        assert dl.read(3.0) == pytest.approx(0.0)

    def test_process_rejects_float64(self):
        """process() with float64 input raises TypeError."""
        dl = DelayLine(max_delay=64)
        block = np.zeros(16, dtype=np.float64)

        with pytest.raises(TypeError):
            dl.process(block)

    def test_process_float32_output(self):
        """process() with float32 input produces float32 output."""
        dl = DelayLine(max_delay=64)
        block = np.zeros(16, dtype=np.float32)
        block[0] = 1.0

        output = dl.process(block)
        assert output.dtype == np.float32

    def test_reset_zeros_buffer(self):
        """reset() zeros all buffer contents and resets write index."""
        dl = DelayLine(max_delay=64)

        # Write some data
        for i in range(32):
            dl.write(float(i))

        dl.reset()

        # All reads should return 0
        for delay in range(1, 64):
            assert dl.read(float(delay)) == pytest.approx(0.0)

    def test_delayed_sequence(self):
        """Writing and reading N samples produces the same sequence delayed by N."""
        delay_samples = 5
        dl = DelayLine(max_delay=64)

        input_signal = np.arange(20, dtype=np.float32)
        output_signal = np.zeros(20, dtype=np.float32)

        for i, sample in enumerate(input_signal):
            dl.write(sample)
            output_signal[i] = dl.read(float(delay_samples))

        # After delay_samples, output should match input shifted by delay
        for i in range(delay_samples, 20):
            assert output_signal[i] == pytest.approx(
                input_signal[i - delay_samples]
            ), f"Mismatch at index {i}"

    def test_circular_buffer_wrap(self):
        """Circular buffer wraps correctly when write_index exceeds max_delay."""
        max_delay = 16
        dl = DelayLine(max_delay=max_delay)

        # Write more samples than buffer size to force wrap
        for i in range(max_delay * 3):
            dl.write(float(i))

        # Should still read correctly after wrapping
        last_written = float(max_delay * 3 - 1)
        assert dl.read(1.0) == pytest.approx(last_written - 1)
        assert dl.read(2.0) == pytest.approx(last_written - 2)
