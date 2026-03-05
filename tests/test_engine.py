"""Tests for the processing engine facade (claudeverb.engine).

Covers process_audio(), blend_wet_dry(), and plot_waveform_comparison().
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest

from claudeverb.audio.samples import get_sample
from claudeverb.engine import blend_wet_dry, plot_waveform_comparison, process_audio


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
