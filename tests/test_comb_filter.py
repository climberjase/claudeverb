"""Tests for CombFilter DSP primitive."""

import numpy as np
import pytest

from claudeverb.algorithms.filters import CombFilter
from claudeverb.config import BUFFER_SIZE


class TestCombFilterImpulseResponse:
    """Verify CombFilter impulse response structure."""

    def test_impulse_echoes_at_delay_intervals(self):
        """Impulse at t=0 produces echoes at t=delay, t=2*delay, etc."""
        delay_length = 10
        feedback = 0.7
        comb = CombFilter(delay_length, feedback=feedback, damp=0.0)

        # Process impulse through comb filter
        impulse = np.zeros(delay_length * 5, dtype=np.float32)
        impulse[0] = 1.0
        output = comb.process(impulse)

        # Input appears at t=0
        assert output[0] == pytest.approx(1.0), "Input should appear at t=0"

        # Echoes at multiples of delay_length should be nonzero
        for n in range(1, 4):
            idx = delay_length * n
            assert abs(output[idx]) > 0.01, (
                f"Echo at t={idx} should be nonzero, got {output[idx]}"
            )

        # Between echoes should be zero (within tolerance)
        for i in range(1, delay_length):
            assert output[i] == pytest.approx(0.0, abs=1e-6), (
                f"Output at t={i} should be ~0 (between echoes), got {output[i]}"
            )

    def test_echo_decay_follows_feedback(self):
        """Echo amplitudes decay approximately geometrically by feedback^n (damp=0)."""
        delay_length = 20
        feedback = 0.6
        comb = CombFilter(delay_length, feedback=feedback, damp=0.0)

        impulse = np.zeros(delay_length * 6, dtype=np.float32)
        impulse[0] = 1.0
        output = comb.process(impulse)

        # With damp=0, echoes should decay geometrically
        # First echo at t=delay_length should be ~ feedback
        # Second echo at t=2*delay_length should be ~ feedback^2
        first_echo = output[delay_length]
        second_echo = output[delay_length * 2]

        # Ratio between consecutive echoes should be approximately feedback
        ratio = second_echo / first_echo if first_echo != 0 else 0
        assert ratio == pytest.approx(feedback, abs=0.05), (
            f"Echo decay ratio should be ~{feedback}, got {ratio}"
        )


class TestCombFilterDamping:
    """Verify damping affects frequency content."""

    def test_no_damping_preserves_high_frequencies(self):
        """With damp=0.0, high frequencies in echoes are preserved."""
        delay_length = 20
        comb = CombFilter(delay_length, feedback=0.7, damp=0.0)

        impulse = np.zeros(4096, dtype=np.float32)
        impulse[0] = 1.0
        output = comb.process(impulse)

        # Compute FFT -- check that high frequency content is present
        spectrum = np.abs(np.fft.rfft(output))
        # With no damping, spectrum should have significant energy at high freqs
        midpoint = len(spectrum) // 2
        high_freq_energy = np.sum(spectrum[midpoint:] ** 2)
        assert high_freq_energy > 0.01, (
            "High frequency energy should be significant with damp=0.0"
        )

    def test_full_damping_reduces_high_frequencies(self):
        """With damp=1.0, echoes are progressively lowpass filtered."""
        delay_length = 20
        comb_damped = CombFilter(delay_length, feedback=0.7, damp=1.0)
        comb_clean = CombFilter(delay_length, feedback=0.7, damp=0.0)

        impulse = np.zeros(4096, dtype=np.float32)
        impulse[0] = 1.0

        output_damped = comb_damped.process(impulse)
        output_clean = comb_clean.process(impulse)

        # Compare high frequency energy
        spectrum_damped = np.abs(np.fft.rfft(output_damped))
        spectrum_clean = np.abs(np.fft.rfft(output_clean))

        midpoint = len(spectrum_damped) // 2
        hf_damped = np.sum(spectrum_damped[midpoint:] ** 2)
        hf_clean = np.sum(spectrum_clean[midpoint:] ** 2)

        assert hf_damped < hf_clean, (
            "Damped comb should have less high-frequency energy than undamped"
        )


class TestCombFilterProcessing:
    """Verify process modes and type enforcement."""

    def test_process_sample_matches_process_block(self):
        """process_sample and process(block) produce identical results."""
        delay_length = 10
        feedback = 0.5
        damp = 0.3

        comb_sample = CombFilter(delay_length, feedback=feedback, damp=damp)
        comb_block = CombFilter(delay_length, feedback=feedback, damp=damp)

        input_data = np.random.default_rng(42).random(100).astype(np.float32)

        # Sample-by-sample
        sample_output = np.empty(len(input_data), dtype=np.float32)
        for i, x in enumerate(input_data):
            sample_output[i] = comb_sample.process_sample(float(x))

        # Block
        block_output = comb_block.process(input_data)

        np.testing.assert_allclose(
            sample_output, block_output, atol=1e-7,
            err_msg="process_sample and process(block) must produce identical output"
        )

    def test_reset_clears_state(self):
        """After reset, output matches a fresh instance."""
        delay_length = 10
        feedback = 0.5
        damp = 0.5

        comb = CombFilter(delay_length, feedback=feedback, damp=damp)
        comb_fresh = CombFilter(delay_length, feedback=feedback, damp=damp)

        # Process some data
        noise = np.random.default_rng(0).random(50).astype(np.float32)
        comb.process(noise)

        # Reset
        comb.reset()

        # Now process more data -- should match fresh instance
        test_data = np.random.default_rng(1).random(30).astype(np.float32)
        output_reset = comb.process(test_data)
        output_fresh = comb_fresh.process(test_data)

        np.testing.assert_allclose(
            output_reset, output_fresh, atol=1e-7,
            err_msg="After reset, output should match fresh instance"
        )

    def test_rejects_float64(self):
        """process() with float64 input raises TypeError."""
        comb = CombFilter(10, feedback=0.5, damp=0.5)
        block = np.zeros(16, dtype=np.float64)

        with pytest.raises(TypeError):
            comb.process(block)

    def test_block_processing_matches_single_buffer(self):
        """Processing in 48-sample chunks matches processing as one large buffer (DSP-07)."""
        delay_length = 30
        feedback = 0.6
        damp = 0.4

        comb_chunked = CombFilter(delay_length, feedback=feedback, damp=damp)
        comb_single = CombFilter(delay_length, feedback=feedback, damp=damp)

        total_samples = BUFFER_SIZE * 4  # 192 samples
        input_data = np.random.default_rng(99).random(total_samples).astype(np.float32)

        # Process as one buffer
        single_output = comb_single.process(input_data)

        # Process in BUFFER_SIZE chunks
        chunked_output = np.empty(total_samples, dtype=np.float32)
        for i in range(0, total_samples, BUFFER_SIZE):
            chunk = input_data[i : i + BUFFER_SIZE]
            chunked_output[i : i + BUFFER_SIZE] = comb_chunked.process(chunk)

        np.testing.assert_allclose(
            chunked_output, single_output, atol=1e-7,
            err_msg="Block processing in 48-sample chunks must match single-buffer"
        )
