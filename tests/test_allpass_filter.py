"""Tests for AllpassFilter DSP primitive."""

import numpy as np
import pytest

from claudeverb.algorithms.filters import AllpassFilter
from claudeverb.config import BUFFER_SIZE


class TestAllpassFilterImpulseResponse:
    """Verify AllpassFilter impulse response structure."""

    def test_impulse_response_structure(self):
        """Impulse response: t=0 gives -feedback, t=delay gives (1 - feedback^2)."""
        delay_length = 10
        feedback = 0.5
        ap = AllpassFilter(delay_length, feedback=feedback)

        impulse = np.zeros(delay_length * 3, dtype=np.float32)
        impulse[0] = 1.0
        output = ap.process(impulse)

        # At t=0: output = delay_out(0) - feedback * v = 0 - feedback*(1 + feedback*0) = -feedback
        assert output[0] == pytest.approx(-feedback, abs=1e-5), (
            f"Output at t=0 should be -{feedback}, got {output[0]}"
        )

        # At t=delay_length: output should be (1 - feedback^2)
        expected = 1.0 - feedback ** 2
        assert output[delay_length] == pytest.approx(expected, abs=1e-4), (
            f"Output at t={delay_length} should be ~{expected}, got {output[delay_length]}"
        )

    def test_allpass_magnitude_flat(self):
        """FFT magnitude of impulse response is approximately flat (allpass property).

        |H(z)| = 1 for all frequencies. We check this by verifying that the
        magnitude spectrum of a sufficiently long impulse response is flat
        within 1% tolerance.
        """
        delay_length = 20
        feedback = 0.5
        ap = AllpassFilter(delay_length, feedback=feedback)

        # Long impulse response so the allpass has time to ring out
        impulse = np.zeros(4096, dtype=np.float32)
        impulse[0] = 1.0
        output = ap.process(impulse)

        spectrum = np.abs(np.fft.rfft(output))
        # Normalize to check flatness
        mean_mag = np.mean(spectrum[1:])  # skip DC
        max_deviation = np.max(np.abs(spectrum[1:] - mean_mag)) / mean_mag

        assert max_deviation < 0.01, (
            f"Allpass magnitude should be flat within 1%, max deviation: {max_deviation:.4f}"
        )

    def test_phase_is_modified(self):
        """Allpass modifies phase (output is time-smeared compared to input)."""
        delay_length = 20
        feedback = 0.5
        ap = AllpassFilter(delay_length, feedback=feedback)

        impulse = np.zeros(256, dtype=np.float32)
        impulse[0] = 1.0
        output = ap.process(impulse)

        # Output should have energy spread over multiple samples (not just at t=0)
        nonzero_count = np.sum(np.abs(output) > 1e-6)
        assert nonzero_count > 1, (
            "Allpass should spread energy over multiple samples (phase modification)"
        )


class TestAllpassFilterProcessing:
    """Verify process modes and type enforcement."""

    def test_process_sample_matches_process_block(self):
        """process_sample and process(block) produce identical results."""
        delay_length = 10
        feedback = 0.5

        ap_sample = AllpassFilter(delay_length, feedback=feedback)
        ap_block = AllpassFilter(delay_length, feedback=feedback)

        input_data = np.random.default_rng(42).random(100).astype(np.float32)

        # Sample-by-sample
        sample_output = np.empty(len(input_data), dtype=np.float32)
        for i, x in enumerate(input_data):
            sample_output[i] = ap_sample.process_sample(float(x))

        # Block
        block_output = ap_block.process(input_data)

        np.testing.assert_allclose(
            sample_output, block_output, atol=1e-7,
            err_msg="process_sample and process(block) must produce identical output"
        )

    def test_reset_clears_state(self):
        """After reset, output matches a fresh instance."""
        delay_length = 10
        feedback = 0.5

        ap = AllpassFilter(delay_length, feedback=feedback)
        ap_fresh = AllpassFilter(delay_length, feedback=feedback)

        # Process some data
        noise = np.random.default_rng(0).random(50).astype(np.float32)
        ap.process(noise)

        # Reset
        ap.reset()

        # Process more data -- should match fresh instance
        test_data = np.random.default_rng(1).random(30).astype(np.float32)
        output_reset = ap.process(test_data)
        output_fresh = ap_fresh.process(test_data)

        np.testing.assert_allclose(
            output_reset, output_fresh, atol=1e-7,
            err_msg="After reset, output should match fresh instance"
        )

    def test_rejects_float64(self):
        """process() with float64 input raises TypeError."""
        ap = AllpassFilter(10, feedback=0.5)
        block = np.zeros(16, dtype=np.float64)

        with pytest.raises(TypeError):
            ap.process(block)

    def test_block_processing_matches_single_buffer(self):
        """Processing in 48-sample chunks matches one large buffer (DSP-07)."""
        delay_length = 15
        feedback = 0.5

        ap_chunked = AllpassFilter(delay_length, feedback=feedback)
        ap_single = AllpassFilter(delay_length, feedback=feedback)

        total_samples = BUFFER_SIZE * 4  # 192
        input_data = np.random.default_rng(99).random(total_samples).astype(np.float32)

        # Single buffer
        single_output = ap_single.process(input_data)

        # Chunked
        chunked_output = np.empty(total_samples, dtype=np.float32)
        for i in range(0, total_samples, BUFFER_SIZE):
            chunk = input_data[i : i + BUFFER_SIZE]
            chunked_output[i : i + BUFFER_SIZE] = ap_chunked.process(chunk)

        np.testing.assert_allclose(
            chunked_output, single_output, atol=1e-7,
            err_msg="Block processing in 48-sample chunks must match single-buffer"
        )
