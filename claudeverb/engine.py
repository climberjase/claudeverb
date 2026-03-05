"""Processing engine facade for claudeverb.

Orchestrates algorithm processing, metric computation, and visualization
generation. Decouples all DSP/analysis logic from the UI layer so it can
be tested with plain pytest.

Public API:
    process_audio           -- Run algorithm, compute metrics, generate figures.
    blend_wet_dry           -- Mix dry/wet signals by percentage.
    plot_waveform_comparison -- Two-panel waveform plot (input vs output).
"""

from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt

from claudeverb.algorithms import ALGORITHM_REGISTRY
from claudeverb.analysis.metrics import (
    compute_clarity,
    compute_drr,
    measure_rt60,
    measure_rt60_bands,
    spectral_centroid_delta,
)
from claudeverb.analysis.spectral import plot_fft_comparison, plot_mel_comparison
from claudeverb.audio.impulse import generate_impulse_response
from claudeverb.config import SAMPLE_RATE


def process_audio(
    algorithm_name: str, params: dict, audio: np.ndarray
) -> dict:
    """Run a reverb algorithm and return results for UI consumption.

    Looks up the algorithm by name, forces mix=100 (so the UI wet/dry
    control handles the full blend range), processes audio, generates
    an impulse response, computes metrics, and creates comparison figures.

    Args:
        algorithm_name: Key in ALGORITHM_REGISTRY (e.g. "freeverb").
        params: Algorithm parameter dict (mix is overridden to 100).
        audio: Input audio, mono (N,) or stereo (2, N), float32.

    Returns:
        Dict with keys:
            dry     -- original audio (np.ndarray)
            wet     -- processed audio (np.ndarray)
            ir      -- impulse response (np.ndarray)
            metrics -- dict of str -> str (formatted metric values)
            figures -- dict of str -> matplotlib.figure.Figure

    Raises:
        KeyError: If algorithm_name is not in ALGORITHM_REGISTRY.
    """
    # Look up and instantiate algorithm
    algo_cls = ALGORITHM_REGISTRY[algorithm_name]
    algo = algo_cls()

    # Force mix to 100 so UI wet/dry controls the full blend
    forced_params = dict(params)
    forced_params["mix"] = 100

    # Process audio
    algo.update_params(forced_params)
    algo.reset()
    wet = algo.process(audio.copy())

    # Generate impulse response (reset state first since process() consumed it)
    algo.update_params(forced_params)
    algo.reset()
    ir = generate_impulse_response(algo, duration_seconds=3.0, mono=True)

    # Compute metrics
    rt60 = measure_rt60(ir, sr=SAMPLE_RATE)
    rt60_bands = measure_rt60_bands(ir, sr=SAMPLE_RATE)
    drr = compute_drr(ir, sr=SAMPLE_RATE)
    c80 = compute_clarity(ir, sr=SAMPLE_RATE, early_ms=80.0)
    c50 = compute_clarity(ir, sr=SAMPLE_RATE, early_ms=50.0)
    centroid_delta = spectral_centroid_delta(audio, wet, sr=SAMPLE_RATE)

    metrics = {
        "RT60": f"{rt60:.3f} s",
        "RT60 Bands": ", ".join(
            f"{band}: {val:.3f}s" for band, val in rt60_bands.items()
        ),
        "DRR": f"{drr:.1f} dB",
        "C80": f"{c80:.1f} dB",
        "C50": f"{c50:.1f} dB",
        "Centroid Delta": f"{centroid_delta:.1f} Hz",
    }

    # Generate comparison figures
    figures = {
        "mel": plot_mel_comparison(audio, wet, sr=SAMPLE_RATE),
        "fft": plot_fft_comparison(audio, wet, sr=SAMPLE_RATE),
    }

    return {
        "dry": audio,
        "wet": wet,
        "ir": ir,
        "metrics": metrics,
        "figures": figures,
    }


def blend_wet_dry(
    dry: np.ndarray, wet: np.ndarray, mix_pct: int
) -> np.ndarray:
    """Blend dry and wet signals by percentage.

    Computes (1 - alpha) * dry + alpha * wet where alpha = mix_pct / 100.
    Hard clips result to [-1.0, 1.0].

    Args:
        dry: Dry (original) audio, any shape, float32.
        wet: Wet (processed) audio, same shape as dry, float32.
        mix_pct: Wet mix percentage, 0 = fully dry, 100 = fully wet.

    Returns:
        Blended float32 array, clipped to [-1.0, 1.0].
    """
    alpha = mix_pct / 100.0
    blended = (1.0 - alpha) * dry + alpha * wet
    clipped = np.clip(blended, -1.0, 1.0)
    return clipped.astype(np.float32)


def plot_waveform_comparison(
    dry: np.ndarray, wet: np.ndarray, sr: int = SAMPLE_RATE
) -> plt.Figure:
    """Create a two-panel waveform comparison plot.

    Top panel shows input waveform, bottom panel shows output waveform.
    Stereo inputs are averaged to mono for display.

    Args:
        dry: Input audio, mono (N,) or stereo (2, N), float32.
        wet: Output audio, mono (N,) or stereo (2, N), float32.
        sr: Sample rate in Hz.

    Returns:
        matplotlib Figure with two subplots. Caller is responsible for closing.
    """
    # Mono-ize stereo inputs
    dry_mono = _ensure_mono(dry)
    wet_mono = _ensure_mono(wet)

    fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)

    t_dry = np.arange(len(dry_mono)) / sr
    t_wet = np.arange(len(wet_mono)) / sr

    axes[0].plot(t_dry, dry_mono, linewidth=0.5)
    axes[0].set_title("Input")
    axes[0].set_ylabel("Amplitude")
    axes[0].set_ylim(-1, 1)

    axes[1].plot(t_wet, wet_mono, linewidth=0.5)
    axes[1].set_title("Output")
    axes[1].set_ylabel("Amplitude")
    axes[1].set_xlabel("Time (s)")
    axes[1].set_ylim(-1, 1)

    fig.tight_layout()
    return fig


def _ensure_mono(audio: np.ndarray) -> np.ndarray:
    """Average stereo (2, N) to mono (N,). Pass mono through unchanged."""
    if audio.ndim == 2 and audio.shape[0] == 2:
        return np.mean(audio, axis=0).astype(np.float32)
    return audio
