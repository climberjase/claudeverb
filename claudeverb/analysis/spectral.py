"""Spectral visualization functions for reverb analysis.

Provides mel spectrogram comparison and FFT magnitude overlay plots
for comparing input vs. output audio signals.

All functions accept mono (N,) or stereo (2, N) float32 arrays.
Stereo inputs are averaged to mono before analysis.

Functions:
    plot_mel_comparison  -- Side-by-side mel spectrograms of input and output.
    plot_fft_comparison  -- Overlaid FFT magnitude spectra on log frequency axis.
"""

from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt


def _ensure_mono(audio: np.ndarray) -> np.ndarray:
    """Average stereo (2, N) to mono (N,). Pass mono through unchanged."""
    if audio.ndim == 2 and audio.shape[0] == 2:
        return np.mean(audio, axis=0).astype(np.float32)
    return audio


def plot_mel_comparison(
    input_audio: np.ndarray,
    output_audio: np.ndarray,
    sr: int = 48000,
    n_mels: int = 128,
    fmax: float = 8000.0,
) -> plt.Figure:
    """Plot side-by-side mel spectrograms of input and output audio.

    Args:
        input_audio: Input signal, mono (N,) or stereo (2, N), float32.
        output_audio: Output signal, mono (N,) or stereo (2, N), float32.
        sr: Sample rate in Hz.
        n_mels: Number of mel bands.
        fmax: Maximum frequency for mel filterbank in Hz.

    Returns:
        matplotlib Figure with two subplots titled "Input" and "Output".
    """
    import librosa
    import librosa.display

    inp = _ensure_mono(input_audio).astype(np.float32)
    out = _ensure_mono(output_audio).astype(np.float32)

    fig, axes = plt.subplots(1, 2, figsize=(10, 3), sharey=True)

    for ax, audio, title in zip(axes, [inp, out], ["Input", "Output"]):
        S = librosa.feature.melspectrogram(
            y=audio, sr=sr, n_mels=n_mels, fmax=fmax
        )
        S_db = librosa.power_to_db(S, ref=np.max)
        img = librosa.display.specshow(
            S_db, sr=sr, x_axis="time", y_axis="mel", fmax=fmax, ax=ax
        )
        ax.set_title(title)

    fig.colorbar(img, ax=axes, format="%+2.0f dB")
    return fig


def plot_fft_comparison(
    input_audio: np.ndarray,
    output_audio: np.ndarray,
    sr: int = 48000,
) -> plt.Figure:
    """Plot overlaid FFT magnitude spectra of input and output audio.

    Args:
        input_audio: Input signal, mono (N,) or stereo (2, N), float32.
        output_audio: Output signal, mono (N,) or stereo (2, N), float32.
        sr: Sample rate in Hz.

    Returns:
        matplotlib Figure with single axes containing two line traces
        on a log-frequency x-axis.
    """
    inp = _ensure_mono(input_audio).astype(np.float32)
    out = _ensure_mono(output_audio).astype(np.float32)

    fig, ax = plt.subplots(figsize=(10, 3))

    for audio, label, alpha in [(inp, "Input", 0.8), (out, "Output", 0.7)]:
        spectrum = np.abs(np.fft.rfft(audio))
        freqs = np.fft.rfftfreq(len(audio), d=1.0 / sr)
        magnitude_db = 20.0 * np.log10(spectrum + 1e-12)
        ax.plot(freqs, magnitude_db, label=label, alpha=alpha)

    ax.set_xscale("log")
    ax.set_xlim(20, sr / 2)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Magnitude (dB)")
    ax.set_title("FFT Magnitude Comparison")
    ax.legend()
    fig.tight_layout()
    return fig
