"""Tests for bundled test sample generation."""

import numpy as np
import pytest

from claudeverb.audio.samples import (
    generate_impulse_click,
    generate_white_noise_burst,
    generate_sine_sweep,
    generate_drum_transient,
    generate_guitar_pluck,
    generate_vocal_tone,
    get_sample,
    list_samples,
)
from claudeverb.config import SAMPLE_RATE


class TestAnalysisSignals:
    """Tests for analysis-oriented signal generators."""

    def test_impulse_click_shape_and_value(self):
        """Impulse: correct length, dtype, value at [0] == 1.0, rest zeros."""
        duration_s = 1.0
        result = generate_impulse_click(duration_s=duration_s)
        expected_len = int(SAMPLE_RATE * duration_s)

        assert result.shape == (expected_len,)
        assert result.dtype == np.float32
        assert result[0] == 1.0
        assert np.all(result[1:] == 0.0)

    def test_white_noise_burst_shape_and_silence(self):
        """White noise burst: correct length, dtype, burst has energy, tail is silent."""
        duration_s = 0.5
        burst_s = 0.1
        result = generate_white_noise_burst(duration_s=duration_s, burst_s=burst_s)
        expected_len = int(SAMPLE_RATE * duration_s)
        burst_samples = int(SAMPLE_RATE * burst_s)

        assert result.shape == (expected_len,)
        assert result.dtype == np.float32
        # Burst section should have nonzero values
        assert np.any(result[:burst_samples] != 0.0)
        # Tail section should be zeros
        assert np.all(result[burst_samples:] == 0.0)

    def test_sine_sweep_shape_and_range(self):
        """Sine sweep: correct length, dtype, values within [-1, 1]."""
        duration_s = 2.0
        result = generate_sine_sweep(duration_s=duration_s)
        expected_len = int(SAMPLE_RATE * duration_s)

        assert result.shape == (expected_len,)
        assert result.dtype == np.float32
        assert np.all(result >= -1.0)
        assert np.all(result <= 1.0)


class TestInstrumentSignals:
    """Tests for instrument-like synthesized clips."""

    def test_drum_transient_shape_and_envelope(self):
        """Drum transient: correct shape, dtype, values in [-1, 1], decaying envelope."""
        duration_s = 0.5
        result = generate_drum_transient(duration_s=duration_s)
        expected_len = int(SAMPLE_RATE * duration_s)

        assert result.shape == (expected_len,)
        assert result.dtype == np.float32
        assert np.all(result >= -1.0)
        assert np.all(result <= 1.0)

        # First 10ms should have higher RMS than last 10ms (decaying)
        n_10ms = int(SAMPLE_RATE * 0.01)
        rms_start = np.sqrt(np.mean(result[:n_10ms] ** 2))
        rms_end = np.sqrt(np.mean(result[-n_10ms:] ** 2))
        assert rms_start > rms_end

    def test_guitar_pluck_shape_and_pitch(self):
        """Guitar pluck: correct shape, dtype, values in [-1, 1], clear periodicity."""
        frequency = 220.0
        duration_s = 1.5
        result = generate_guitar_pluck(duration_s=duration_s, frequency=frequency)
        expected_len = int(SAMPLE_RATE * duration_s)

        assert result.shape == (expected_len,)
        assert result.dtype == np.float32
        assert np.all(result >= -1.0)
        assert np.all(result <= 1.0)

        # Autocorrelation should have a peak near the expected period
        # Use a segment from the middle where the signal is stable
        seg_start = int(SAMPLE_RATE * 0.1)
        seg_end = int(SAMPLE_RATE * 0.5)
        segment = result[seg_start:seg_end]
        corr = np.correlate(segment, segment, mode="full")
        corr = corr[len(corr) // 2:]  # positive lags only
        # Expected period in samples
        expected_period = int(SAMPLE_RATE / frequency)
        # Find first peak after lag 0 (skip first few samples)
        search_start = expected_period - 20
        search_end = expected_period + 20
        peak_lag = search_start + np.argmax(corr[search_start:search_end])
        assert abs(peak_lag - expected_period) <= 5

    def test_vocal_tone_shape_and_formants(self):
        """Vocal tone: correct shape, dtype, values in [-1, 1], formant energy."""
        duration_s = 2.0
        result = generate_vocal_tone(duration_s=duration_s)
        expected_len = int(SAMPLE_RATE * duration_s)

        assert result.shape == (expected_len,)
        assert result.dtype == np.float32
        assert np.all(result >= -1.0)
        assert np.all(result <= 1.0)

        # FFT check: should have energy near formant regions (700 Hz and 1200 Hz)
        fft_mag = np.abs(np.fft.rfft(result))
        freqs = np.fft.rfftfreq(len(result), 1.0 / SAMPLE_RATE)

        # Find energy in formant bands
        f1_band = (freqs >= 600) & (freqs <= 800)
        f2_band = (freqs >= 1100) & (freqs <= 1300)
        # And a comparison band far from formants
        null_band = (freqs >= 4000) & (freqs <= 5000)

        f1_energy = np.mean(fft_mag[f1_band])
        f2_energy = np.mean(fft_mag[f2_band])
        null_energy = np.mean(fft_mag[null_band])

        # Formant regions should have more energy than null band
        assert f1_energy > null_energy * 2
        assert f2_energy > null_energy * 2


class TestSampleRegistry:
    """Tests for the sample registry (get_sample, list_samples)."""

    def test_get_sample_returns_correct_type(self):
        """Each registered sample returns a float32 ndarray."""
        for name in list_samples():
            result = get_sample(name)
            assert isinstance(result, np.ndarray), f"{name} is not ndarray"
            assert result.dtype == np.float32, f"{name} is not float32"

    def test_list_samples_returns_all(self):
        """All 6 sample names should be present."""
        names = list_samples()
        expected = ["drum", "guitar", "impulse", "sine_sweep", "vocal", "white_noise_burst"]
        assert names == expected

    def test_get_sample_unknown_raises(self):
        """ValueError for unknown sample name."""
        with pytest.raises(ValueError, match="Unknown sample"):
            get_sample("nonexistent_sample")


class TestWavDiscovery:
    """Tests for WAV file discovery and loading (06-02)."""

    def test_list_wav_samples_non_empty(self):
        """list_wav_samples() returns a non-empty list (WAV files exist)."""
        from claudeverb.audio.samples import list_wav_samples

        wavs = list_wav_samples()
        assert len(wavs) > 0

    def test_list_wav_samples_returns_stems(self):
        """list_wav_samples() returns stems without .wav extension."""
        from claudeverb.audio.samples import list_wav_samples

        for name in list_wav_samples():
            assert not name.endswith(".wav"), f"'{name}' still has .wav extension"

    def test_list_all_samples_includes_both(self):
        """list_all_samples() returns both synthesized and WAV samples."""
        from claudeverb.audio.samples import list_all_samples

        all_names = list_all_samples()
        # Should have synthesized samples
        assert any("[WAV]" not in n for n in all_names), "No synthesized samples"
        # Should have WAV samples
        assert any("[WAV]" in n for n in all_names), "No WAV samples"

    def test_wav_entries_have_label(self):
        """WAV entries in list_all_samples() include '[WAV]' label."""
        from claudeverb.audio.samples import list_all_samples, list_wav_samples

        all_names = list_all_samples()
        wav_stems = list_wav_samples()
        for stem in wav_stems:
            assert f"{stem} [WAV]" in all_names, \
                f"WAV sample '{stem}' missing [WAV] label in list_all_samples()"

    def test_get_sample_wav_returns_float32(self):
        """get_sample('audio1-acoustic [WAV]') returns float32 ndarray."""
        result = get_sample("audio1-acoustic [WAV]")
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32
        assert len(result) > 0

    def test_get_sample_synthesized_still_works(self):
        """get_sample('guitar') still works for synthesized samples."""
        result = get_sample("guitar")
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32
