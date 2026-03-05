"""End-to-end integration tests for the complete Phase 2 signal path.

Proves: load WAV -> process through Freeverb -> save WAV works correctly.
"""

import numpy as np
import pytest

from claudeverb.algorithms import ALGORITHM_REGISTRY
from claudeverb.algorithms.freeverb import Freeverb
from claudeverb.audio.io import load, save
from claudeverb.audio.samples import (
    generate_impulse_click,
    get_sample,
    list_samples,
)
from claudeverb.config import SAMPLE_RATE


class TestEndToEnd:
    """Integration tests for the full audio pipeline."""

    def test_load_process_save_roundtrip(self, tmp_path):
        """Full signal path: generate -> save -> load -> Freeverb -> save -> load."""
        # Generate a short test signal
        signal = generate_impulse_click(duration_s=0.5)

        # Save to temp WAV
        input_path = str(tmp_path / "input.wav")
        save(input_path, signal)

        # Load it back
        loaded = load(input_path)
        assert loaded.dtype == np.float32

        # Process through Freeverb
        algo = Freeverb()
        processed = algo.process(loaded)

        # Save processed output
        output_path = str(tmp_path / "output.wav")
        save(output_path, processed)

        # Load processed file back
        result = load(output_path)

        # Verify output properties
        assert result.dtype == np.float32
        assert result.shape == loaded.shape
        # Reverb should add energy beyond the impulse
        # Check that tail region (after first 1000 samples) has content
        tail_rms = np.sqrt(np.mean(result[1000:] ** 2))
        assert tail_rms > 0, "Processed output has no reverb tail"

    def test_registry_lookup_and_process(self):
        """Algorithm registry lookup and processing works end-to-end."""
        # Look up freeverb from registry
        assert "freeverb" in ALGORITHM_REGISTRY
        algo_class = ALGORITHM_REGISTRY["freeverb"]
        algo = algo_class()

        # Process a bundled test sample
        impulse = get_sample("impulse")
        output = algo.process(impulse)

        # Verify output is valid
        assert output.dtype == np.float32
        assert output.ndim == 1
        assert len(output) == len(impulse)

    def test_param_change_affects_output(self):
        """Changing parameters produces different output."""
        algo = Freeverb()
        impulse = generate_impulse_click(duration_s=0.5)

        # Process with default settings
        output_default = algo.process(impulse)

        # Reset, change room_size to small value
        algo.reset()
        algo.update_params({"room_size": 10})
        output_small_room = algo.process(impulse)

        # Outputs should differ
        assert not np.allclose(output_default, output_small_room), (
            "Different room_size settings should produce different output"
        )

    def test_stereo_file_roundtrip(self, tmp_path):
        """Stereo signal preserves shape through full pipeline."""
        # Create stereo test signal
        mono = generate_impulse_click(duration_s=0.3)
        stereo = np.stack([mono, mono * 0.8], dtype=np.float32)
        assert stereo.shape == (2, len(mono))

        # Save -> load -> process -> save -> load
        input_path = str(tmp_path / "stereo_in.wav")
        save(input_path, stereo)

        loaded = load(input_path)
        assert loaded.shape[0] == 2, "Loaded stereo should have 2 channels"

        algo = Freeverb()
        processed = algo.process(loaded)
        assert processed.shape[0] == 2, "Processed stereo should have 2 channels"

        output_path = str(tmp_path / "stereo_out.wav")
        save(output_path, processed)

        result = load(output_path)
        assert result.shape[0] == 2, "Final loaded stereo should have 2 channels"
        assert result.shape[1] == loaded.shape[1]

    def test_all_samples_through_freeverb(self):
        """All bundled samples process through Freeverb without errors."""
        algo = Freeverb()
        samples = list_samples()
        assert len(samples) > 0, "No samples available"

        for name in samples:
            sample = get_sample(name)
            algo.reset()
            output = algo.process(sample)

            # Verify output is valid
            assert output.dtype == np.float32, f"{name}: wrong dtype"
            assert not np.any(np.isnan(output)), f"{name}: output contains NaN"
            assert not np.any(np.isinf(output)), f"{name}: output contains Inf"
            assert np.all(np.abs(output) <= 1.0), f"{name}: output exceeds [-1, 1]"
