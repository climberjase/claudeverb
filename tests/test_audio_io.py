"""Tests for audio I/O module (load/save)."""

import numpy as np
import soundfile as sf
import pytest

from claudeverb.audio.io import load, save
from claudeverb.config import SAMPLE_RATE


class TestLoad:
    """Tests for the load() function."""

    def test_load_mono_wav(self, tmp_path):
        """Load a mono WAV file and verify shape (N,) and dtype float32."""
        # Create a short mono WAV at 48 kHz
        duration_s = 0.1
        n_samples = int(SAMPLE_RATE * duration_s)
        mono = np.random.default_rng(0).uniform(-0.5, 0.5, n_samples).astype(np.float32)
        path = tmp_path / "mono.wav"
        sf.write(str(path), mono, SAMPLE_RATE, subtype="FLOAT")

        result = load(str(path))

        assert result.ndim == 1
        assert result.shape == (n_samples,)
        assert result.dtype == np.float32

    def test_load_stereo_wav(self, tmp_path):
        """Load a stereo WAV file and verify shape (2, N) and dtype float32."""
        duration_s = 0.1
        n_samples = int(SAMPLE_RATE * duration_s)
        # soundfile expects (N, 2) for stereo
        stereo_sf = np.random.default_rng(1).uniform(-0.5, 0.5, (n_samples, 2)).astype(np.float32)
        path = tmp_path / "stereo.wav"
        sf.write(str(path), stereo_sf, SAMPLE_RATE, subtype="FLOAT")

        result = load(str(path))

        assert result.ndim == 2
        assert result.shape == (2, n_samples)
        assert result.dtype == np.float32

    def test_load_resamples_to_48k(self, tmp_path):
        """Load a file at 22050 Hz and verify it gets resampled to 48 kHz."""
        orig_sr = 22050
        duration_s = 0.5
        n_orig = int(orig_sr * duration_s)
        mono = np.random.default_rng(2).uniform(-0.5, 0.5, n_orig).astype(np.float32)
        path = tmp_path / "low_sr.wav"
        sf.write(str(path), mono, orig_sr, subtype="FLOAT")

        result = load(str(path))

        expected_n = int(SAMPLE_RATE * duration_s)
        # Allow small tolerance for resampling length
        assert abs(result.shape[-1] - expected_n) <= 2
        assert result.dtype == np.float32

    def test_load_multichannel_takes_first_two(self, tmp_path):
        """Load a 4-channel WAV and verify only first 2 channels are returned."""
        duration_s = 0.1
        n_samples = int(SAMPLE_RATE * duration_s)
        # soundfile expects (N, channels)
        multi = np.random.default_rng(3).uniform(-0.5, 0.5, (n_samples, 4)).astype(np.float32)
        path = tmp_path / "multi.wav"
        sf.write(str(path), multi, SAMPLE_RATE, subtype="FLOAT")

        result = load(str(path))

        assert result.ndim == 2
        assert result.shape == (2, n_samples)
        assert result.dtype == np.float32

    def test_load_returns_float32_not_float64(self, tmp_path):
        """Verify dtype is always np.float32 even from librosa edge cases."""
        duration_s = 0.1
        n_samples = int(SAMPLE_RATE * duration_s)
        # Write as 16-bit PCM which librosa may return as float64
        mono = np.random.default_rng(4).uniform(-0.5, 0.5, n_samples).astype(np.float32)
        path = tmp_path / "pcm16.wav"
        sf.write(str(path), mono, SAMPLE_RATE, subtype="PCM_16")

        result = load(str(path))

        assert result.dtype == np.float32


class TestSave:
    """Tests for the save() function."""

    def test_save_and_reload_roundtrip(self, tmp_path):
        """Save a float32 array and reload it, verify data matches within tolerance."""
        n_samples = 4800
        audio = np.random.default_rng(5).uniform(-0.5, 0.5, n_samples).astype(np.float32)
        path = tmp_path / "roundtrip.wav"

        save(str(path), audio)
        result = load(str(path))

        np.testing.assert_allclose(result, audio, atol=1e-6)

    def test_save_stereo_transposes(self, tmp_path):
        """Save a (2, N) stereo array and verify it's readable and correct."""
        n_samples = 4800
        stereo = np.random.default_rng(6).uniform(-0.5, 0.5, (2, n_samples)).astype(np.float32)
        path = tmp_path / "stereo_out.wav"

        save(str(path), stereo)

        # Read back with soundfile directly to check shape
        data, sr = sf.read(str(path))
        assert sr == SAMPLE_RATE
        assert data.shape == (n_samples, 2)  # soundfile convention is (N, channels)
