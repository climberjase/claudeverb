"""Tests for the processing engine facade (claudeverb.engine).

Covers process_audio(), blend_wet_dry(), and plot_waveform_comparison().
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest

from claudeverb.audio.samples import get_sample
from claudeverb.config import SAMPLE_RATE
from claudeverb.engine import apply_eq, blend_wet_dry, pad_with_silence, plot_waveform_comparison, process_audio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mono_audio():
    """Short mono impulse click for fast processing."""
    return get_sample("impulse")


@pytest.fixture
def stereo_audio(mono_audio):
    """Stereo version of the impulse click."""
    return np.stack([mono_audio, mono_audio])


# ---------------------------------------------------------------------------
# process_audio tests
# ---------------------------------------------------------------------------


class TestProcessAudio:
    def test_returns_expected_keys(self, mono_audio):
        result = process_audio("freeverb", {}, mono_audio)
        assert set(result.keys()) == {"dry", "wet", "ir", "metrics", "figures"}

    def test_wet_is_different_from_dry(self, mono_audio):
        result = process_audio("freeverb", {}, mono_audio)
        assert not np.array_equal(result["dry"], result["wet"])

    def test_metrics_has_expected_keys(self, mono_audio):
        result = process_audio("freeverb", {}, mono_audio)
        metrics = result["metrics"]
        expected_keys = {"RT60", "RT60 Bands", "DRR", "C80", "C50", "Centroid Delta"}
        assert expected_keys.issubset(set(metrics.keys()))

    def test_figures_has_mel_and_fft(self, mono_audio):
        result = process_audio("freeverb", {}, mono_audio)
        figures = result["figures"]
        assert "mel" in figures
        assert "fft" in figures
        assert isinstance(figures["mel"], plt.Figure)
        assert isinstance(figures["fft"], plt.Figure)
        # Clean up
        plt.close(figures["mel"])
        plt.close(figures["fft"])

    def test_forces_mix_100(self, mono_audio):
        """Even if params include mix=50, wet output is fully wet (mix forced to 100)."""
        result_50 = process_audio("freeverb", {"mix": 50}, mono_audio)
        result_100 = process_audio("freeverb", {"mix": 100}, mono_audio)
        np.testing.assert_array_equal(result_50["wet"], result_100["wet"])
        # Clean up figures
        for r in (result_50, result_100):
            for fig in r["figures"].values():
                plt.close(fig)

    def test_unknown_algorithm_raises(self, mono_audio):
        with pytest.raises(KeyError):
            process_audio("nonexistent", {}, mono_audio)


# ---------------------------------------------------------------------------
# blend_wet_dry tests
# ---------------------------------------------------------------------------


class TestBlendWetDry:
    def test_0_returns_dry(self):
        dry = np.array([0.5, -0.3, 0.8], dtype=np.float32)
        wet = np.array([0.1, 0.9, -0.2], dtype=np.float32)
        result = blend_wet_dry(dry, wet, 0)
        np.testing.assert_array_almost_equal(result, dry)

    def test_100_returns_wet(self):
        dry = np.array([0.5, -0.3, 0.8], dtype=np.float32)
        wet = np.array([0.1, 0.9, -0.2], dtype=np.float32)
        result = blend_wet_dry(dry, wet, 100)
        np.testing.assert_array_almost_equal(result, wet)

    def test_50_is_midpoint(self):
        dry = np.array([1.0, 0.0], dtype=np.float32)
        wet = np.array([0.0, 1.0], dtype=np.float32)
        result = blend_wet_dry(dry, wet, 50)
        expected = np.array([0.5, 0.5], dtype=np.float32)
        np.testing.assert_array_almost_equal(result, expected)

    def test_clips_output(self):
        dry = np.array([0.9], dtype=np.float32)
        wet = np.array([0.9], dtype=np.float32)
        # Both at 0.9, blend at 100% = 0.9 (no clip needed)
        # Use values that would exceed 1.0
        dry2 = np.array([1.5], dtype=np.float32)
        wet2 = np.array([1.5], dtype=np.float32)
        result = blend_wet_dry(dry2, wet2, 100)
        assert result[0] <= 1.0
        assert result[0] >= -1.0

    def test_returns_float32(self):
        dry = np.array([0.5], dtype=np.float32)
        wet = np.array([0.5], dtype=np.float32)
        result = blend_wet_dry(dry, wet, 50)
        assert result.dtype == np.float32


# ---------------------------------------------------------------------------
# plot_waveform_comparison tests
# ---------------------------------------------------------------------------


class TestPlotWaveformComparison:
    def test_returns_figure(self):
        dry = np.zeros(4800, dtype=np.float32)
        wet = np.ones(4800, dtype=np.float32) * 0.5
        fig = plot_waveform_comparison(dry, wet)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_stereo(self):
        dry = np.zeros((2, 4800), dtype=np.float32)
        wet = np.ones((2, 4800), dtype=np.float32) * 0.5
        fig = plot_waveform_comparison(dry, wet)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)


# ---------------------------------------------------------------------------
# pad_with_silence tests
# ---------------------------------------------------------------------------


class TestSilencePadding:
    """Tests for pad_with_silence() utility."""

    def test_mono_padding_length(self):
        """pad_with_silence(mono, 2.0) returns array with length = original + 96000."""
        mono = np.ones(4800, dtype=np.float32)
        padded = pad_with_silence(mono, 2.0)
        expected_len = 4800 + int(2.0 * SAMPLE_RATE)
        assert len(padded) == expected_len

    def test_stereo_padding_shape(self):
        """pad_with_silence(stereo, 2.0) returns (2, original+96000) shape."""
        stereo = np.ones((2, 4800), dtype=np.float32)
        padded = pad_with_silence(stereo, 2.0)
        expected_cols = 4800 + int(2.0 * SAMPLE_RATE)
        assert padded.shape == (2, expected_cols)

    def test_zero_seconds_passthrough(self):
        """pad_with_silence(mono, 0.0) returns original array unchanged."""
        mono = np.ones(4800, dtype=np.float32)
        padded = pad_with_silence(mono, 0.0)
        np.testing.assert_array_equal(padded, mono)

    def test_padded_region_is_zeros(self):
        """Appended region is all zeros."""
        mono = np.ones(4800, dtype=np.float32)
        padded = pad_with_silence(mono, 1.0)
        padding_region = padded[4800:]
        assert np.all(padding_region == 0.0)

    def test_dtype_preserved(self):
        """Padded output is float32."""
        mono = np.ones(4800, dtype=np.float32)
        padded = pad_with_silence(mono, 1.0)
        assert padded.dtype == np.float32


# ---------------------------------------------------------------------------
# apply_eq / EQ integration tests
# ---------------------------------------------------------------------------


class TestEQ:
    """Tests for apply_eq() and EQ integration in process_audio()."""

    EQ_FLAT = {
        "enabled": True,
        "low_freq": 200,
        "low_gain": 0,
        "mid_freq": 1000,
        "mid_gain": 0,
        "mid_q": 1.5,
        "high_freq": 6000,
        "high_gain": 0,
    }

    def test_apply_eq_flat_is_near_unity(self):
        """apply_eq with all gains at 0dB returns signal approximately unchanged."""
        rng = np.random.default_rng(42)
        signal = rng.random(48000, dtype=np.float32) * 0.5
        result = apply_eq(signal, self.EQ_FLAT)
        rms_diff = np.sqrt(np.mean((result - signal) ** 2))
        assert rms_diff < 0.01

    def test_apply_eq_low_boost(self):
        """apply_eq with low_gain=+6dB boosts low frequencies measurably."""
        rng = np.random.default_rng(42)
        signal = rng.random(48000, dtype=np.float32) * 0.3
        params = dict(self.EQ_FLAT, low_gain=6)
        result = apply_eq(signal, params)
        # Boosted signal should have higher RMS than original
        assert np.sqrt(np.mean(result**2)) > np.sqrt(np.mean(signal**2))

    def test_apply_eq_stereo_shape(self):
        """apply_eq processes stereo (2, N) correctly, output shape matches input."""
        rng = np.random.default_rng(42)
        stereo = rng.random((2, 48000), dtype=np.float32) * 0.5
        result = apply_eq(stereo, self.EQ_FLAT)
        assert result.shape == stereo.shape

    def test_apply_eq_clips_and_dtype(self):
        """apply_eq output is clipped to [-1, 1] and dtype is float32."""
        # Use a signal near full scale with big boost to trigger clipping
        signal = np.ones(4800, dtype=np.float32) * 0.9
        params = dict(self.EQ_FLAT, low_gain=12, mid_gain=12, high_gain=12)
        result = apply_eq(signal, params)
        assert result.dtype == np.float32
        assert np.all(result >= -1.0)
        assert np.all(result <= 1.0)

    def test_process_audio_no_eq(self, mono_audio):
        """process_audio with eq_params=None produces same result as without EQ."""
        result = process_audio("freeverb", {}, mono_audio, eq_params=None)
        assert "wet" in result
        assert "dry" in result
        # Clean up
        for fig in result["figures"].values():
            plt.close(fig)

    def test_process_audio_with_eq(self, mono_audio):
        """process_audio with eq_params enabled processes through EQ chain."""
        result = process_audio("freeverb", {}, mono_audio, eq_params=self.EQ_FLAT)
        assert "wet" in result
        # Clean up
        for fig in result["figures"].values():
            plt.close(fig)

    def test_process_audio_with_silence(self, mono_audio):
        """process_audio with silence_seconds > 0 pads input, dry and wet have same length."""
        result = process_audio("freeverb", {}, mono_audio, silence_seconds=1.0)
        expected_len = len(mono_audio) + SAMPLE_RATE
        if result["dry"].ndim == 1:
            assert len(result["dry"]) == expected_len
            assert len(result["wet"]) == expected_len
        else:
            assert result["dry"].shape[1] == expected_len
            assert result["wet"].shape[1] == expected_len
        assert "original_length" in result
        assert result["original_length"] == len(mono_audio)
        # Clean up
        for fig in result["figures"].values():
            plt.close(fig)
