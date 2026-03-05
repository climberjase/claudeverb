"""Tests for impulse response generation from reverb algorithms."""

import numpy as np
import pytest

from claudeverb.algorithms.freeverb import Freeverb
from claudeverb.audio.impulse import generate_impulse_response
from claudeverb.config import SAMPLE_RATE


class TestImpulseResponseGeneration:
    """Test generate_impulse_response() function."""

    def test_ir_mono_shape_dtype(self):
        """Mono IR has correct shape (N,), dtype float32, and length."""
        algo = Freeverb()
        ir = generate_impulse_response(algo)
        expected_length = int(3.0 * SAMPLE_RATE)
        assert ir.shape == (expected_length,)
        assert ir.dtype == np.float32

    def test_ir_stereo_shape(self):
        """Stereo IR has shape (2, N) with correct length."""
        algo = Freeverb()
        ir = generate_impulse_response(algo, mono=False)
        expected_length = int(3.0 * SAMPLE_RATE)
        assert ir.shape == (2, expected_length)
        assert ir.dtype == np.float32

    def test_ir_has_reverb_tail(self):
        """IR has nonzero energy beyond sample 1000 (reverb tail captured)."""
        algo = Freeverb()
        ir = generate_impulse_response(algo)
        tail_energy = np.sum(ir[1000:] ** 2)
        assert tail_energy > 0, "IR has no reverb tail beyond sample 1000"

    def test_ir_deterministic(self):
        """Two calls with same algorithm produce identical output (reset works)."""
        algo = Freeverb()
        ir1 = generate_impulse_response(algo)
        ir2 = generate_impulse_response(algo)
        np.testing.assert_array_equal(ir1, ir2)

    def test_ir_custom_duration(self):
        """Custom duration produces correct length."""
        algo = Freeverb()
        ir = generate_impulse_response(algo, duration_seconds=1.0)
        assert len(ir) == SAMPLE_RATE  # 48000 samples

    def test_ir_tail_decays(self):
        """Last 10% of IR has lower RMS than first 10% (tail is decaying)."""
        algo = Freeverb()
        ir = generate_impulse_response(algo)
        n = len(ir)
        first_10 = ir[: n // 10]
        last_10 = ir[-n // 10 :]
        rms_first = np.sqrt(np.mean(first_10 ** 2))
        rms_last = np.sqrt(np.mean(last_10 ** 2))
        assert rms_last < rms_first, (
            f"Tail RMS ({rms_last:.6f}) should be less than head RMS ({rms_first:.6f})"
        )
