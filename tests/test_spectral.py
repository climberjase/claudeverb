"""Tests for spectral visualization functions."""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest

from claudeverb.analysis.spectral import plot_fft_comparison, plot_mel_comparison


class TestPlotMelComparison:
    """Tests for plot_mel_comparison."""

    def test_mel_spectrogram_mono(self, mono_sine: np.ndarray) -> None:
        """plot_mel_comparison returns a Figure with 2 axes for mono input."""
        fig = plot_mel_comparison(mono_sine, mono_sine)
        assert isinstance(fig, plt.Figure)
        assert len(fig.axes) >= 2
        plt.close(fig)

    def test_mel_spectrogram_stereo(self, stereo_sine: np.ndarray) -> None:
        """plot_mel_comparison works for stereo input, returns Figure with 2 axes."""
        fig = plot_mel_comparison(stereo_sine, stereo_sine)
        assert isinstance(fig, plt.Figure)
        assert len(fig.axes) >= 2
        plt.close(fig)

    def test_mel_spectrogram_titles(self, mono_sine: np.ndarray) -> None:
        """The two main axes have titles 'Input' and 'Output'."""
        fig = plot_mel_comparison(mono_sine, mono_sine)
        # Get non-colorbar axes (axes with titles)
        titled_axes = [ax for ax in fig.axes if ax.get_title()]
        titles = [ax.get_title() for ax in titled_axes]
        assert "Input" in titles
        assert "Output" in titles
        plt.close(fig)


class TestPlotFFTComparison:
    """Tests for plot_fft_comparison."""

    def test_fft_comparison_returns_figure(self, mono_sine: np.ndarray) -> None:
        """plot_fft_comparison returns a matplotlib Figure."""
        fig = plot_fft_comparison(mono_sine, mono_sine)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_fft_comparison_two_traces(self, mono_sine: np.ndarray) -> None:
        """The axes contain 2 line traces (input and output)."""
        fig = plot_fft_comparison(mono_sine, mono_sine)
        ax = fig.axes[0]
        lines = ax.get_lines()
        assert len(lines) == 2
        plt.close(fig)

    def test_fft_comparison_log_scale(self, mono_sine: np.ndarray) -> None:
        """The x-axis uses log scale."""
        fig = plot_fft_comparison(mono_sine, mono_sine)
        ax = fig.axes[0]
        assert ax.get_xscale() == "log"
        plt.close(fig)

    def test_fft_comparison_stereo(self, stereo_sine: np.ndarray) -> None:
        """plot_fft_comparison works for stereo input without error."""
        fig = plot_fft_comparison(stereo_sine, stereo_sine)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)
